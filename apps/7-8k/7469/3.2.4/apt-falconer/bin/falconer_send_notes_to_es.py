#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Send APT Falconer hunt/story notes back to Splunk ES as a Note.

This is an alert action script for stanza:
  [falconer_send_notes_to_es]

Supported usage:
  - From Falconer Story Review / Workbench (preferred): pass hunt_id (and optionally story_id)
  - From ES Incident Review / ARAs: uses the event's source_guid as the hunt_id key

The script prefers ES 8 Mission Control notes and falls back to classic
notable_update comments for older ES deployments.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


APP = "apt-falconer"
KV_STORIES = "falconer_stories"
KV_HUNTS = "falconer_hunts"


def _eprint(*a: Any) -> None:
    print(*a, file=sys.stderr)


def _read_stdin_json() -> Dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except Exception:
        # Don't crash without context
        _eprint("[Falconer] Could not parse stdin as JSON. Raw length:", len(raw))
        return {}


def _splunkd_request_json(
    session_key: str,
    base_uri: str,
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
) -> Tuple[int, Dict[str, Any], str]:
    """Call local splunkd (management port) and return (status_code, json_or_empty, body_text)."""
    url = urllib.parse.urljoin(base_uri, path.lstrip("/"))
    data = None
    headers = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="replace")
            try:
                j = json.loads(body) if body.strip() else {}
            except Exception:
                j = {}
            return int(getattr(r, "status", 200)), j, body
    except urllib.error.HTTPError as e:
        body = (e.read() or b"").decode("utf-8", errors="replace")
        try:
            j = json.loads(body) if body.strip() else {}
        except Exception:
            j = {}
        return int(e.code), j, body
    except Exception as e:
        return 0, {}, str(e)


def _splunkd_request_form(
    session_key: str,
    base_uri: str,
    path: str,
    form: Dict[str, Any],
    timeout: int = 30,
) -> Tuple[int, Dict[str, Any], str]:
    """Call splunkd with form-encoded POST data."""
    url = urllib.parse.urljoin(base_uri, path.lstrip("/"))
    data = urllib.parse.urlencode(form or {}, doseq=True).encode("utf-8")
    headers = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="replace")
            try:
                j = json.loads(body) if body.strip() else {}
            except Exception:
                j = {}
            return int(getattr(r, "status", 200)), j, body
    except urllib.error.HTTPError as e:
        body = (e.read() or b"").decode("utf-8", errors="replace")
        try:
            j = json.loads(body) if body.strip() else {}
        except Exception:
            j = {}
        return int(e.code), j, body
    except Exception as e:
        return 0, {}, str(e)


def _kv_query(
    session_key: str,
    base_uri: str,
    collection: str,
    query: Dict[str, Any],
    limit: int = 50,
) -> List[Dict[str, Any]]:
    q = urllib.parse.quote(json.dumps(query, separators=(",", ":")))
    path = f"/servicesNS/nobody/{APP}/storage/collections/data/{collection}?query={q}&count={limit}&output_mode=json"
    status, j, body = _splunkd_request_json(session_key, base_uri, "GET", path, payload=None)
    if status not in (200, 201):
        _eprint(f"[Falconer] KV query failed: collection={collection} status={status} body={body[:400]}")
        return []
    if isinstance(j, list):
        return j
    # some Splunk returns a dict wrapper
    if isinstance(j, dict) and "entry" in j:
        out = []
        for e in j.get("entry", []):
            out.append(e.get("content", {}))
        return out
    return []


def _extract_context(data: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
    # session_key / base_uri
    session_key = data.get("session_key") or os.environ.get("SPLUNK_SESSION_KEY") or ""
    base_uri = data.get("server_uri") or os.environ.get("SPLUNKD_URI") or "https://127.0.0.1:8089"
    # payload record (first result)
    results = data.get("result")
    if isinstance(results, list) and results:
        payload = results[0]
    elif isinstance(results, dict):
        payload = results
    else:
        payload = {}
    return session_key, base_uri, payload


def _pick_hunt_id(data: Dict[str, Any], payload: Dict[str, Any]) -> str:
    cfg = data.get("configuration", {}) or {}
    # dashboard invocation can pass param.hunt_id or hunt_id in config
    hunt_id = cfg.get("hunt_id") or cfg.get("story_hunt_id") or ""
    if hunt_id:
        return str(hunt_id)
    # ES invocation: key everything off source_guid
    if payload.get("source_guid"):
        return str(payload.get("source_guid"))
    # fallbacks
    if payload.get("event_id"):
        return str(payload.get("event_id"))
    return ""


def _build_note_body(hunt_id: str, story_rows: List[Dict[str, Any]], hunt_rows: List[Dict[str, Any]]) -> str:
    hunt_title = ""
    if hunt_rows:
        hunt_title = str(hunt_rows[0].get("title") or hunt_rows[0].get("hunt_title") or "")
    if hunt_title:
        header = f"APT Falconer Hunt: {hunt_title} ({hunt_id})"
    else:
        header = f"APT Falconer Hunt: {hunt_id}"

    lines: List[str] = [header, ""]
    if not story_rows:
        lines.append("No story notes found for this hunt.")
        return "\n".join(lines)

    for row in story_rows:
        sid = row.get("story_id") or row.get("_key") or ""
        status = row.get("status") or ""
        notes = row.get("notes") or ""
        if not str(notes).strip():
            continue
        if sid:
            lines.append(f"Story {sid} ({status})")
        else:
            lines.append(f"Story ({status})")
        lines.append(str(notes).rstrip())
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _mc_create_note(
    session_key: str,
    base_uri: str,
    target_id: str,
    target_kind: str,
    note_body: str,
    note_title: str,
) -> Dict[str, Any]:
    """Try multiple candidate endpoints; return response JSON on first success."""

    title = str(note_title or "APT Falconer Hunt Notes")[:250]
    content = str(note_body or "")[:10000]

    # ES 8 public API uses title/content/type. Keep a few older variants as
    # fallback because early Mission Control builds had path/payload drift.
    payload_variants: List[Dict[str, Any]] = [
        {"title": title, "content": content, "type": "Incident"},
        {"title": title, "content": content, "type": "Task"},
        {"title": title, "note": content, "target_id": target_id, "target_kind": target_kind},
        {"title": title, "note": content, "target_id": target_id},
        {"title": title, "note": content, "investigation_id": target_id},
        {"title": title, "note": content, "finding_id": target_id},
        {"title": title, "note": content, "id": target_id},
    ]

    # Path candidates (we'll try in order)
    tid = urllib.parse.quote(str(target_id), safe="")
    candidates: List[str] = []

    # ES 8.x public API. The "investigations" path accepts a finding or
    # investigation GUID/display ID as the id parameter.
    candidates += [
        f"/servicesNS/nobody/missioncontrol/public/v2/investigations/{tid}/notes?output_mode=json",
    ]

    # Older Mission Control path variants retained for compatibility.
    candidates += [
        f"/services/mission_control/public/v2/investigation/{tid}/notes?output_mode=json",
        f"/services/mission_control/public/v2/investigations/{tid}/notes?output_mode=json",
        f"/services/mission_control/public/v2/investigation/{tid}/note?output_mode=json",
        f"/services/mission_control/public/v2/notes?output_mode=json",
        f"/services/mission_control/v2/notes?output_mode=json",
        f"/services/mission_control/notes?output_mode=json",
    ]
    # Finding style (some builds use finding as target)
    candidates += [
        f"/services/mission_control/public/v2/finding/{tid}/notes?output_mode=json",
        f"/services/mission_control/public/v2/findings/{tid}/notes?output_mode=json",
    ]

    last: Tuple[int, str] = (0, "")
    for path in candidates:
        for p in payload_variants:
            status, j, body = _splunkd_request_json(session_key, base_uri, "POST", path, payload=p)
            if status in (200, 201):
                return j if isinstance(j, dict) else {"response": j}
            # If endpoint exists but payload is wrong, we may get 400/409. Keep trying variants.
            last = (status, body)
            if status in (401, 403):
                break
    raise RuntimeError(f"Notes API failed (last_status={last[0]} last_body={last[1][:400]})")


def _classic_notable_add_comment(
    session_key: str,
    base_uri: str,
    rule_uid: str,
    comment: str,
) -> Dict[str, Any]:
    """Add a comment to classic ES Incident Review via /services/notable_update."""
    if not rule_uid:
        raise RuntimeError("Missing notable rule UID.")
    if not str(comment or "").strip():
        raise RuntimeError("No Falconer notes found to send.")

    status, j, body = _splunkd_request_form(
        session_key,
        base_uri,
        "/services/notable_update?output_mode=json",
        {
            "ruleUIDs": rule_uid,
            "comment": comment,
        },
    )
    if status in (200, 201) and (not isinstance(j, dict) or j.get("success", True) is not False):
        return j if isinstance(j, dict) else {"response": body}
    raise RuntimeError(f"Classic ES notable_update failed (status={status} body={body[:400]})")


def _resolve_classic_notable_rule_uid(
    session_key: str,
    base_uri: str,
    target_id: str,
) -> str:
    candidate = str(target_id or "").strip()
    if not candidate:
        return ""
    if "@@notable@@" in candidate:
        return candidate

    search = (
        'search index=notable source_guid="{source_guid}" '
        '| head 1 '
        '| fields source_event_id event_id rule_id'
    ).format(source_guid=candidate.replace('"', '\\"'))
    status, parsed, body = _splunkd_request_form(
        session_key,
        base_uri,
        "/services/search/jobs/export",
        {
            "search": search,
            "output_mode": "json",
        },
    )
    if status != 200 or not body:
        return candidate

    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        result = row.get("result") if isinstance(row, dict) else None
        if not isinstance(result, dict):
            continue
        for field in ("source_event_id", "event_id", "rule_id"):
            value = str(result.get(field) or "").strip()
            if value:
                return value
    return candidate


def send_notes_to_es_target(
    session_key: str,
    base_uri: str,
    target_id: str,
    target_kind: str,
    note_body: str,
    note_title: str,
) -> Dict[str, Any]:
    """
    Send Falconer notes to the best available ES target.

    ES 8.x Mission Control notes are preferred. Classic Incident Review comments
    remain as a compatibility fallback for older ES versions.
    """
    target_kind = (target_kind or "finding").strip().lower()
    mission_control_error = None
    try:
        response = _mc_create_note(session_key, base_uri, target_id, target_kind, note_body, note_title)
        return {
            "destination": "mission_control",
            "target_id": target_id,
            "target_kind": target_kind,
            "response": response,
        }
    except Exception as mc_error:
        mission_control_error = mc_error
        _eprint("[Falconer] Mission Control notes API failed, trying classic notable_update:", str(mc_error))

    if target_kind in ("finding", "notable") or "@@notable@@" in str(target_id):
        classic_rule_uid = _resolve_classic_notable_rule_uid(session_key, base_uri, target_id)
        response = _classic_notable_add_comment(session_key, base_uri, classic_rule_uid, note_body)
        return {
            "destination": "classic_es_notable",
            "target_id": classic_rule_uid,
            "target_kind": "finding",
            "response": response,
        }

    raise RuntimeError(f"Mission Control notes API failed and no classic finding target was available: {mission_control_error}")


def main() -> None:
    data = _read_stdin_json()
    session_key, base_uri, payload = _extract_context(data)
    if not session_key:
        raise RuntimeError("Missing session_key (Splunk did not provide auth context).")

    cfg = data.get("configuration", {}) or {}
    story_id = str(cfg.get("story_id") or "").strip() or None
    hunt_id = _pick_hunt_id(data, payload)
    if not hunt_id:
        raise RuntimeError("Could not determine hunt_id (expected configuration.hunt_id or payload.source_guid).")

    # Pull story notes
    story_query: Dict[str, Any] = {"hunt_id": hunt_id}
    if story_id:
        story_query["story_id"] = story_id
    story_rows = _kv_query(session_key, base_uri, KV_STORIES, story_query, limit=25)

    # Pull hunt metadata (optional)
    hunt_rows = _kv_query(session_key, base_uri, KV_HUNTS, {"hunt_id": hunt_id}, limit=1)

    note_body = _build_note_body(hunt_id, story_rows, hunt_rows)
    note_title = str(cfg.get("note_title") or f"APT Falconer: Hunt Notes ({hunt_id})")

    # Determine target for ES note
    # Prefer explicit target passed by caller
    target_id = str(cfg.get("investigation_id") or cfg.get("target_id") or "").strip()
    target_kind = str(cfg.get("target_kind") or "investigation").strip().lower()
    if not target_id:
        # ES ARA context: attach to finding/source_guid
        if payload.get("investigation_id"):
            target_id = str(payload.get("investigation_id"))
            target_kind = "investigation"
        elif payload.get("investigation_guid"):
            target_id = str(payload.get("investigation_guid"))
            target_kind = "investigation"
        elif payload.get("source_guid"):
            target_id = str(payload.get("source_guid"))
            target_kind = "finding"
        elif payload.get("event_id"):
            target_id = str(payload.get("event_id"))
            target_kind = "finding"
        else:
            # last resort: attach to hunt_id
            target_id = hunt_id
            target_kind = "finding"

    resp = send_notes_to_es_target(session_key, base_uri, target_id, target_kind, note_body, note_title)
    _eprint("[Falconer] Note created successfully.")
    # Write a minimal JSON to stdout for Splunk
    print(json.dumps({"status": "ok", "target_id": target_id, "target_kind": target_kind, "response": resp}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _eprint("[Falconer] ERROR:", str(e))
        raise
