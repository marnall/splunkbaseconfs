import os
import json
import datetime
from urllib.parse import parse_qs, unquote_plus

from splunk.persistconn.application import PersistentServerConnectionApplication
import splunk.rest as rest

APP_NAME = "apt-falconer"
COLLECTION_NAME = "falconer_network_whitelist"
DEBUG_ENABLED = True

DEBUG_PATH = os.path.join(
    os.environ.get("SPLUNK_HOME", "/opt/splunk"),
    "var",
    "log",
    "splunk",
    "falconer_lookup_debug.log",
)


class NetworkWhitelistAppend(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(NetworkWhitelistAppend, self).__init__()

    def log(self, msg: str):
        if not DEBUG_ENABLED:
            return
        try:
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            with open(DEBUG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [network_whitelist_append] {msg}\n")
        except Exception:
            pass

    def _parse_args(self, in_string):
        try:
            args = json.loads(in_string) if in_string else {}
        except Exception:
            args = {}

        method = (args.get("method") or "GET").upper()
        raw_payload = args.get("payload")
        payload = {}

        if isinstance(raw_payload, dict):
            payload = raw_payload
        elif isinstance(raw_payload, str):
            try:
                payload = json.loads(raw_payload)
            except Exception:
                payload = {}

            if not payload:
                try:
                    qs = parse_qs(raw_payload, keep_blank_values=True)
                    if "payload" in qs:
                        inner = unquote_plus(qs["payload"][0])
                        payload = json.loads(inner)
                    else:
                        payload = {k: v[0] for k, v in qs.items() if v}
                except Exception:
                    payload = {}
        else:
            payload = args

        return method, payload, args

    def _kv_get_by_value(self, session_key, value, entity_type):
        query = json.dumps({"value": value, "entity_type": entity_type})
        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{COLLECTION_NAME}"
        resp, content = rest.simpleRequest(
            uri,
            method="GET",
            getargs={"output_mode": "json", "query": query},
            sessionKey=session_key,
        )
        if resp.get("status") == "200" and content:
            return json.loads(content.decode("utf-8"))
        return []

    def _kv_insert_doc(self, session_key, doc):
        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{COLLECTION_NAME}"
        return rest.simpleRequest(
            uri,
            method="POST",
            jsonargs=json.dumps(doc).encode("utf-8"),
            raiseAllErrors=True,
            sessionKey=session_key,
        )

    def handle(self, in_string):
        try:
            method, payload, args = self._parse_args(in_string)
            if method != "POST":
                return {"payload": {"status": "error", "error": "Only POST supported"}, "status": 405}

            session_key = (args.get("session", {}) or {}).get("authtoken")
            if not session_key:
                raise ValueError("Missing sessionKey/authtoken")

            value = str(payload.get("value") or payload.get("signal") or "").strip().lower()
            entity_type = str(payload.get("entity_type") or "domain").strip().lower()
            if not value:
                raise ValueError("Missing required field: value")

            now = int(datetime.datetime.utcnow().timestamp())
            description = payload.get("description") or "Suppressed via allowlist manager"
            created_by = payload.get("created_by") or "allowlist_append"

            existing = self._kv_get_by_value(session_key, value, entity_type)
            if existing:
                return {
                    "payload": {"status": "exists", "value": value, "entity_type": entity_type, "doc": existing[0]},
                    "status": 200,
                }

            doc = {
                "value": value,
                "entity_type": entity_type,
                "status": payload.get("status") or "enabled",
                "description": description,
                "created_time": now,
                "created_by": created_by,
                "updated_time": now,
                "updated_by": created_by,
            }

            resp, _ = self._kv_insert_doc(session_key, doc)
            status_code = int(resp.get("status", "200"))
            if status_code not in (200, 201, 204):
                return {
                    "payload": {"status": "error", "error": f"KV insert failed (HTTP {status_code})"},
                    "status": status_code,
                }

            return {"payload": {"status": "success", "value": value, "entity_type": entity_type, "doc": doc}, "status": 200}

        except Exception as e:
            self.log(f"Exception: {e}")
            return {"payload": {"status": "error", "error": str(e)}, "status": 500}

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
