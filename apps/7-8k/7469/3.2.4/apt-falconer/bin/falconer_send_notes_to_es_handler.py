# bin/falconer_send_notes_to_es_handler.py
import json
import os
import datetime
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import parse_qs, unquote_plus

from splunk.persistconn.application import PersistentServerConnectionApplication
import splunk.rest as rest


APP_NAME = "apt-falconer"
KV_STORIES = "falconer_stories"
KV_HUNTS = "falconer_hunts"

DEBUG_ENABLED = True
DEBUG_PATH = os.path.join(
    os.environ.get("SPLUNK_HOME", "/opt/splunk"),
    "var",
    "log",
    "splunk",
    "falconer_lookup_debug.log",
)


def _splunkd_request_json(session_key, base_uri, method, path, payload=None, timeout=30):
    url = urllib.parse.urljoin(base_uri, path.lstrip("/"))
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body) if body.strip() else {}
            except Exception:
                parsed = {}
            return int(getattr(response, "status", 200)), parsed, body
    except urllib.error.HTTPError as e:
        body = (e.read() or b"").decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body.strip() else {}
        except Exception:
            parsed = {}
        return int(e.code), parsed, body
    except Exception as e:
        return 0, {}, str(e)


def _splunkd_request_form(session_key, base_uri, path, form, timeout=30):
    url = urllib.parse.urljoin(base_uri, path.lstrip("/"))
    data = urllib.parse.urlencode(form or {}, doseq=True).encode("utf-8")
    headers = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body) if body.strip() else {}
            except Exception:
                parsed = {}
            return int(getattr(response, "status", 200)), parsed, body
    except urllib.error.HTTPError as e:
        body = (e.read() or b"").decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body.strip() else {}
        except Exception:
            parsed = {}
        return int(e.code), parsed, body
    except Exception as e:
        return 0, {}, str(e)


def _build_note_body(hunt_id, story_rows, hunt_rows):
    hunt_title = ""
    if hunt_rows:
        hunt_title = str(hunt_rows[0].get("title") or hunt_rows[0].get("hunt_title") or "")
    header = f"APT Falconer Hunt: {hunt_title} ({hunt_id})" if hunt_title else f"APT Falconer Hunt: {hunt_id}"

    lines = [header, ""]
    if not story_rows:
        lines.append("No story notes found for this hunt.")
        return "\n".join(lines)

    for row in story_rows:
        story_id = row.get("story_id") or row.get("_key") or ""
        status = row.get("status") or ""
        notes = row.get("notes") or ""
        if not str(notes).strip():
            continue
        lines.append(f"Story {story_id} ({status})" if story_id else f"Story ({status})")
        lines.append(str(notes).rstrip())
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _mc_create_note(session_key, base_uri, target_id, target_kind, note_body, note_title):
    title = str(note_title or "APT Falconer Hunt Notes")[:250]
    content = str(note_body or "")[:10000]
    payload_variants = [
        {"title": title, "content": content, "type": "Incident"},
        {"title": title, "content": content, "type": "Task"},
        {"title": title, "note": content, "target_id": target_id, "target_kind": target_kind},
        {"title": title, "note": content, "target_id": target_id},
        {"title": title, "note": content, "investigation_id": target_id},
        {"title": title, "note": content, "finding_id": target_id},
        {"title": title, "note": content, "id": target_id},
    ]

    target = urllib.parse.quote(str(target_id), safe="")
    candidates = [
        f"/servicesNS/nobody/missioncontrol/public/v2/investigations/{target}/notes?output_mode=json",
        f"/services/mission_control/public/v2/investigation/{target}/notes?output_mode=json",
        f"/services/mission_control/public/v2/investigations/{target}/notes?output_mode=json",
        f"/services/mission_control/public/v2/investigation/{target}/note?output_mode=json",
        f"/services/mission_control/public/v2/notes?output_mode=json",
        f"/services/mission_control/v2/notes?output_mode=json",
        f"/services/mission_control/notes?output_mode=json",
        f"/services/mission_control/public/v2/finding/{target}/notes?output_mode=json",
        f"/services/mission_control/public/v2/findings/{target}/notes?output_mode=json",
    ]

    last_status, last_body = 0, ""
    for path in candidates:
        for payload in payload_variants:
            status, parsed, body = _splunkd_request_json(session_key, base_uri, "POST", path, payload=payload)
            if status in (200, 201):
                return parsed if isinstance(parsed, dict) else {"response": parsed}
            last_status, last_body = status, body
            if status in (401, 403):
                break
    raise RuntimeError(f"Notes API failed (last_status={last_status} last_body={last_body[:400]})")


def _classic_notable_add_comment(session_key, base_uri, rule_uid, comment):
    if not str(rule_uid or "").strip():
        raise RuntimeError("Missing notable rule UID.")
    if not str(comment or "").strip():
        raise RuntimeError("No Falconer notes found to send.")

    status, parsed, body = _splunkd_request_form(
        session_key,
        base_uri,
        "/services/notable_update?output_mode=json",
        {
            "ruleUIDs": rule_uid,
            "comment": comment,
        },
    )
    if status in (200, 201) and (not isinstance(parsed, dict) or parsed.get("success", True) is not False):
        return parsed if isinstance(parsed, dict) else {"response": body}
    raise RuntimeError(f"Classic ES notable_update failed (status={status} body={body[:400]})")


def _resolve_classic_notable_rule_uid(session_key, base_uri, target_id):
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


def send_notes_to_es_target(session_key, base_uri, target_id, target_kind, note_body, note_title):
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
    except Exception as e:
        mission_control_error = e

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


class FalconerSendNotesToESHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(FalconerSendNotesToESHandler, self).__init__()

    def log(self, msg):
        if not DEBUG_ENABLED:
            return
        try:
            ts = datetime.datetime.utcnow().isoformat()
            with open(DEBUG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [send_notes_to_es] {msg}\n")
        except Exception:
            pass

    def _list_to_dict(self, maybe_list):
        out = {}
        if isinstance(maybe_list, list):
            for item in maybe_list:
                if isinstance(item, dict) and "name" in item:
                    out[item["name"]] = item.get("value")
        return out

    def _parse_string_payload(self, value):
        value = (value or "").strip()
        if not value:
            return {}
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                return self._list_to_dict(parsed)
        except Exception:
            pass

        try:
            qs = parse_qs(value, keep_blank_values=True)
            return {k: unquote_plus(vals[0]) for k, vals in qs.items() if vals}
        except Exception:
            return {}

    def _unwrap_payload(self, raw_payload):
        if isinstance(raw_payload, list):
            raw_payload = self._list_to_dict(raw_payload)
        if isinstance(raw_payload, dict):
            inner = raw_payload.get("payload")
            if isinstance(inner, str) and inner.strip():
                outer = {k: v for k, v in raw_payload.items() if k not in ("payload", "output_mode")}
                outer.update(self._parse_string_payload(inner))
                return outer
            return raw_payload
        if isinstance(raw_payload, str):
            return self._parse_string_payload(raw_payload)
        return {}

    def _parse_args(self, in_string):
        try:
            outer = json.loads(in_string or "{}")
        except Exception:
            outer = {}
        if isinstance(outer, list):
            outer = self._list_to_dict(outer)

        body = self._unwrap_payload(outer.get("payload"))
        top_level = {}
        for key, value in outer.items():
            if key in ("method", "payload", "session", "headers", "query", "connection"):
                continue
            top_level[key] = value
        query_payload = self._unwrap_payload(outer.get("query"))

        payload = {}
        if isinstance(query_payload, dict):
            payload.update(query_payload)
        payload.update(top_level)
        if isinstance(body, dict):
            payload.update(body)
        return outer, payload

    def _session_key(self, outer):
        session = outer.get("session") or {}
        if isinstance(session, dict):
            return session.get("authtoken") or session.get("sessionKey") or session.get("token") or ""
        if isinstance(session, str):
            return session.replace("Splunk ", "").strip()
        return outer.get("sessionKey") or ""

    def _kv_query(self, session_key, collection, query, limit=50):
        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{collection}"
        resp, content = rest.simpleRequest(
            uri,
            sessionKey=session_key,
            method="GET",
            getargs={
                "output_mode": "json",
                "count": limit,
                "query": json.dumps(query or {}, separators=(",", ":")),
            },
            raiseAllErrors=True,
        )
        rows = json.loads(content.decode("utf-8")) if content else []
        return rows if isinstance(rows, list) else []

    def _splunkd_base_uri(self, outer):
        connection = outer.get("connection") or {}
        if isinstance(connection, dict):
            server_uri = connection.get("server_uri") or connection.get("serverUri")
            if server_uri:
                return str(server_uri).rstrip("/")
        return "https://127.0.0.1:8089"

    def handle(self, in_string):
        try:
            outer, payload = self._parse_args(in_string)
            session_key = self._session_key(outer)
            if not session_key:
                return {
                    "payload": {"status": "error", "error": "Missing session token"},
                    "status": 401,
                    "headers": {"Content-Type": "application/json"},
                }

            hunt_id = str(payload.get("hunt_id") or payload.get("story_hunt_id") or "").strip()
            story_id = str(payload.get("story_id") or "").strip()
            if not hunt_id:
                return {
                    "payload": {"status": "error", "error": "Missing hunt_id"},
                    "status": 400,
                    "headers": {"Content-Type": "application/json"},
                }

            story_query = {"hunt_id": hunt_id}
            if story_id:
                story_query["story_id"] = story_id
            story_rows = self._kv_query(session_key, KV_STORIES, story_query, limit=25)
            hunt_rows = self._kv_query(session_key, KV_HUNTS, {"hunt_id": hunt_id}, limit=1)
            hunt = hunt_rows[0] if hunt_rows else {}

            note_body = _build_note_body(hunt_id, story_rows, hunt_rows)
            note_title = str(payload.get("note_title") or f"APT Falconer: Hunt Notes ({hunt_id})")

            target_id = str(
                payload.get("target_id")
                or payload.get("ruleUID")
                or payload.get("ruleUIDs")
                or hunt.get("es_source_guid")
                or hunt.get("source_guid")
                or hunt_id
            ).strip()
            target_kind = str(payload.get("target_kind") or "finding").strip().lower()

            response = send_notes_to_es_target(
                session_key,
                self._splunkd_base_uri(outer),
                target_id,
                target_kind,
                note_body,
                note_title,
            )

            return {
                "payload": {
                    "status": "ok",
                    "hunt_id": hunt_id,
                    "story_id": story_id or hunt_id,
                    "target_id": target_id,
                    "target_kind": target_kind,
                    "response": response,
                },
                "status": 200,
                "headers": {"Content-Type": "application/json"},
            }
        except Exception as e:
            self.log(f"ERROR: {e}")
            return {
                "payload": {"status": "error", "error": str(e)},
                "status": 500,
                "headers": {"Content-Type": "application/json"},
            }

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
