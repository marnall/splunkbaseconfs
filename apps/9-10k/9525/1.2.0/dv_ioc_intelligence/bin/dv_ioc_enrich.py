import json
import os
import sys

APP_BIN = os.path.dirname(os.path.abspath(__file__))
if APP_BIN not in sys.path:
    sys.path.insert(0, APP_BIN)

from dv_ioc_intelligence_lib import audit
from dv_ioc_intelligence_lib.engine import EnrichmentEngine, as_bool
from dv_ioc_intelligence_lib.splunk_api import SplunkAPI
from dv_ioc_intelligence_lib.store import Store


def server_uri(payload):
    if payload.get("server_uri"):
        return payload["server_uri"]
    config = payload.get("configuration", {})
    if config.get("server_uri"):
        return config["server_uri"]
    host = payload.get("server_host") or "127.0.0.1"
    port = payload.get("server_port") or "8089"
    return "https://%s:%s" % (host, port)


def first(value):
    return value[0] if isinstance(value, list) and value else value


def main():
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        return 0
    try:
        payload = json.loads(sys.stdin.read())
        session_key = payload.get("session_key") or payload.get("sessionKey")
        store = Store(SplunkAPI(session_key, server_uri(payload)))
        config = payload.get("configuration", {})
        result = payload.get("result", {})
        outcome = EnrichmentEngine(store).run(
            result,
            update_notable=as_bool(config.get("update_notable", "1")),
            send_email=as_bool(config.get("send_email", "1")),
        )
        verdict_status = outcome.get("verdict_status", "unknown")
        audit.write(
            "alert_action_finished",
            event_id=outcome.get("event_id"),
            source_ip=first(result.get("src_ip") or result.get("src")),
            destination_ip=first(result.get("dest_ip") or result.get("dest")),
            ioc_values=",".join(item.get("value", "") for item in outcome.get("iocs", [])),
            status=outcome.get("status"),
            verdict_status=verdict_status,
            malicious=outcome.get("malicious") if verdict_status != "unknown" else None,
            error_count=len(outcome.get("errors", [])),
            error_summary=outcome.get("error_summary"),
            ioc_total=outcome.get("ioc_total"),
            batch_offset=outcome.get("batch_offset"),
            next_offset=outcome.get("next_offset"),
            remaining_ioc_count=outcome.get("remaining_ioc_count"),
        )
        return 0
    except Exception as exc:
        audit.write("alert_action_failed", level="ERROR", error=str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
