#!/usr/bin/env python3
# ITOC360 alert action for Splunk.
# Reads the modular alert payload from stdin and forwards the alert
# to the ITOC360 events API.

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

EVENTS_URL = "https://api.itoc360.app/functions/v1/events"
VALID_SEVERITIES = ("critical", "high", "medium", "low")


def log(msg):
    # stderr ends up in splunkd.log with the alert action's context
    sys.stderr.write("%s\n" % msg)


def build_event(payload):
    config = payload.get("configuration", {})
    result = payload.get("result", {}) or {}

    severity = (config.get("severity") or "medium").lower()
    if severity not in VALID_SEVERITIES:
        severity = "medium"

    host_field = config.get("host_field") or "host"
    host = result.get(host_field) or payload.get("server_host") or "splunk"

    search_name = payload.get("search_name") or "Splunk alert"

    # Compact, human-readable message from the triggering result
    interesting = {
        k: v
        for k, v in result.items()
        if not k.startswith("_") and k != host_field
    }
    message_parts = ["%s=%s" % (k, v) for k, v in list(interesting.items())[:10]]
    raw = result.get("_raw")
    if raw:
        message_parts.append(str(raw)[:500])
    message = "; ".join(message_parts) if message_parts else "Triggered by Splunk alert."

    event = {
        "event_type": "alert",
        "title": search_name,
        "host": str(host),
        "severity": severity,
        "message": message,
        "source": "splunk",
    }
    return event, config.get("token")


def send(event, token):
    url = "%s?%s" % (EVENTS_URL, urllib.parse.urlencode({"token": token}))
    data = json.dumps(event).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8", "replace")
        log("INFO itoc360 event accepted status=%s body=%s" % (resp.status, body[:300]))


def main():
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        log("FATAL Unsupported execution mode (expected --execute)")
        return 1

    try:
        payload = json.load(sys.stdin)
    except ValueError as e:
        log("FATAL Failed to parse alert payload: %s" % e)
        return 2

    event, token = build_event(payload)
    if not token:
        log("FATAL No ITOC360 source token configured")
        return 3

    try:
        send(event, token)
    except urllib.error.HTTPError as e:
        log("ERROR ITOC360 API returned HTTP %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:300]))
        return 4
    except Exception as e:  # noqa: BLE001 - surface everything to splunkd.log
        log("ERROR Failed to send event to ITOC360: %s" % e)
        return 5

    return 0


if __name__ == "__main__":
    sys.exit(main())
