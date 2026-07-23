#!/usr/bin/env python
"""Custom alert action handler for "Send to Mars".

Splunk invokes this script as ``mars_alert.py --execute`` and writes the
alert settings to stdin as a JSON document. The handler runs *inside*
Splunk, so it has local access to everything Mars used to fetch via a
REST callback:

- the full result set (the gzipped ``results_file``, all rows),
- the saved search's SPL and configured ``alert.severity`` (read from
  splunkd over the loopback management port with the supplied session
  key — no external network, no IP allowlist),

and pushes them outbound to the Mars webhook in a single rich JSON POST
with ``Authorization: Bearer <token>``.

Only the Python standard library is used so the app stays dependency-free
across Splunk versions.
"""

from __future__ import annotations

import csv
import gzip
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

APP_NAME = "TA-mars-alerts"
TOKEN_REALM = "TA-mars-alerts"
TOKEN_USERNAME = "mars_webhook_token"
SCHEMA_VERSION = "splunk-app/v1"

# Cap rows shipped per delivery. Mirrors the backend's enrichment cap: the
# agent only samples events for pivots, so a few hundred is ample, and an
# unbounded set would bloat the outbound POST and Mars's stored payload.
# ``result_count`` still reports the true match total.
MAX_RESULTS = 200

# splunkd's management endpoint is loopback with a self-signed cert; the
# session key already authenticates us, so cert verification adds nothing.
_LOCAL_TLS = ssl.create_default_context()
_LOCAL_TLS.check_hostname = False
_LOCAL_TLS.verify_mode = ssl.CERT_NONE


def _log(level: str, message: str) -> None:
    # Splunk captures the alert action's stderr into the job's log and
    # splunkd.log, so a plain prefixed line is the idiomatic channel.
    sys.stderr.write(f"{level} MarsAlert - {message}\n")


def _local_get_json(server_uri: str, path: str, session_key: str) -> dict:
    """GET a JSON entity from the local splunkd management API."""
    url = f"{server_uri.rstrip('/')}/{path.lstrip('/')}"
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}output_mode=json"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Splunk {session_key}")
    with urllib.request.urlopen(req, context=_LOCAL_TLS, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _entry_content(payload: dict) -> dict:
    entries = payload.get("entry") or []
    if entries and isinstance(entries[0], dict):
        content = entries[0].get("content")
        if isinstance(content, dict):
            return content
    return {}


def _read_webhook_url(server_uri: str, session_key: str) -> str:
    content = _entry_content(
        _local_get_json(
            server_uri,
            f"servicesNS/nobody/{APP_NAME}/configs/conf-mars_alerts/settings",
            session_key,
        )
    )
    url = content.get("webhook_url", "")
    return url.strip() if isinstance(url, str) else ""


def _read_webhook_token(server_uri: str, session_key: str) -> str:
    # storage/passwords entity name is "<realm>:<username>:".
    name = urllib.parse.quote(f"{TOKEN_REALM}:{TOKEN_USERNAME}:", safe="")
    content = _entry_content(
        _local_get_json(
            server_uri,
            f"servicesNS/nobody/{APP_NAME}/storage/passwords/{name}",
            session_key,
        )
    )
    token = content.get("clear_password", "")
    return token.strip() if isinstance(token, str) else ""


def _read_saved_search(
    server_uri: str, session_key: str, owner: str, app: str, search_name: str
) -> dict:
    """Read SPL + severity + scheduling metadata for the saved search.

    Returns an empty dict for ad-hoc searches (no name) or if the lookup
    fails — the SPL and severity are best-effort context, not required to
    deliver the alert.
    """
    if not search_name:
        return {}
    name = urllib.parse.quote(search_name, safe="")
    owner = owner or "nobody"
    app = app or "search"
    try:
        content = _entry_content(
            _local_get_json(
                server_uri,
                f"servicesNS/{owner}/{app}/saved/searches/{name}",
                session_key,
            )
        )
    except (urllib.error.URLError, ValueError) as e:
        _log("WARN", f"could not read saved search {search_name!r}: {e}")
        return {}
    return content


def _read_results(results_file: str) -> tuple[list[dict], int]:
    """Load rows from the gzipped results CSV, capped at ``MAX_RESULTS``.

    Returns ``(rows, total)`` where ``rows`` holds at most ``MAX_RESULTS``
    entries and ``total`` is the true match count (so callers can report
    it even when the shipped set is truncated). Splunk adds ``__mv_<field>``
    companion columns for multivalue fields; they're an internal encoding
    the agent doesn't need, so drop them.
    """
    if not results_file:
        return [], 0
    rows: list[dict] = []
    total = 0
    try:
        with gzip.open(results_file, "rt", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                total += 1
                if len(rows) < MAX_RESULTS:
                    rows.append(
                        {
                            k: v
                            for k, v in row.items()
                            if k and not k.startswith("__mv_")
                        }
                    )
    except (OSError, csv.Error) as e:
        _log("WARN", f"could not read results file {results_file!r}: {e}")
    if total > len(rows):
        _log("INFO", f"capped results from {total} to {len(rows)} rows for delivery")
    return rows, total


def _resolve_severity(configuration: dict, saved_search: dict) -> str:
    """Severity precedence: an explicit per-action override wins; otherwise
    the saved search's configured ``alert.severity`` is authoritative. The
    dropdown defaults to "Auto" (blank), so an untouched action inherits the
    search's own tier rather than silently forcing a default. Returned as a
    string on the Splunk 1–5 scale (Mars maps it canonically).
    """
    if isinstance(configuration, dict):
        chosen = str(configuration.get("severity", "")).strip()
        if chosen:
            return chosen
    fallback = saved_search.get("alert.severity", "")
    return str(fallback).strip()


def _build_payload(
    settings: dict,
    saved_search: dict,
    results: list[dict],
    configuration: dict,
    result_count: int,
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "sid": settings.get("sid", ""),
        "search_name": settings.get("search_name", ""),
        "app": settings.get("app", ""),
        "owner": settings.get("owner", ""),
        "results_link": settings.get("results_link", ""),
        "spl": saved_search.get("search", ""),
        "alert_severity": _resolve_severity(configuration, saved_search),
        "description": saved_search.get("description", ""),
        "cron_schedule": saved_search.get("cron_schedule", ""),
        "earliest_time": saved_search.get("dispatch.earliest_time", ""),
        "latest_time": saved_search.get("dispatch.latest_time", ""),
        # True match total; ``results`` is capped at MAX_RESULTS.
        "result_count": result_count,
        "results_truncated": result_count > len(results),
        "results": results,
    }


def _post_to_mars(webhook_url: str, token: str, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(webhook_url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    # Default TLS verification — this is the real outbound call to Mars.
    with urllib.request.urlopen(req, timeout=30) as resp:
        _log("INFO", f"Mars accepted delivery: HTTP {resp.status}")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        _log("FATAL", "unsupported execution mode (expected --execute)")
        return 1

    try:
        settings = json.loads(sys.stdin.read())
    except ValueError as e:
        _log("FATAL", f"could not parse alert settings JSON: {e}")
        return 2

    server_uri = settings.get("server_uri", "")
    session_key = settings.get("session_key", "")
    if not server_uri or not session_key:
        _log("FATAL", "missing server_uri/session_key in alert settings")
        return 2

    try:
        webhook_url = _read_webhook_url(server_uri, session_key)
        token = _read_webhook_token(server_uri, session_key)
    except (urllib.error.URLError, ValueError) as e:
        _log("FATAL", f"could not read Mars webhook settings: {e}")
        return 3
    if not webhook_url or not token:
        _log("FATAL", "Mars webhook URL or token not configured (run app setup)")
        return 3

    saved_search = _read_saved_search(
        server_uri,
        session_key,
        settings.get("owner", ""),
        settings.get("app", ""),
        settings.get("search_name", ""),
    )
    results, result_count = _read_results(settings.get("results_file", ""))
    configuration = settings.get("configuration") or {}
    payload = _build_payload(
        settings, saved_search, results, configuration, result_count
    )

    try:
        _post_to_mars(webhook_url, token, payload)
    except urllib.error.HTTPError as e:
        _log("FATAL", f"Mars rejected delivery: HTTP {e.code} {e.reason}")
        return 4
    except urllib.error.URLError as e:
        _log("FATAL", f"could not reach Mars webhook: {e}")
        return 4

    _log(
        "INFO",
        f"forwarded sid={payload['sid']} "
        f"({payload['result_count']} rows, severity={payload['alert_severity']!r})",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
