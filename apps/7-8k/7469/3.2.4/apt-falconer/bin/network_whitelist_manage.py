import os
import json
import datetime
import urllib.parse

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


class NetworkWhitelistManage(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(NetworkWhitelistManage, self).__init__()

    def log(self, msg: str):
        if not DEBUG_ENABLED:
            return
        try:
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            with open(DEBUG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [network_whitelist_manage] {msg}\n")
        except Exception:
            pass

    def _parse_args(self, in_string):
        try:
            args = json.loads(in_string) if in_string else {}
        except Exception:
            args = {}

        method = (args.get("method") or "GET").upper()
        raw_payload = args.get("payload")
        if isinstance(raw_payload, str):
            try:
                payload = json.loads(raw_payload)
            except Exception:
                payload = {}
        elif isinstance(raw_payload, dict):
            payload = raw_payload
        else:
            payload = {}
        return method, payload, args

    def _kv_get(self, session_key, value, entity_type):
        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{COLLECTION_NAME}"
        query = json.dumps({"value": str(value).lower(), "entity_type": str(entity_type).lower()})
        _, content = rest.simpleRequest(
            uri,
            method="GET",
            getargs={"output_mode": "json", "query": query},
            sessionKey=session_key,
        )
        return json.loads(content.decode("utf-8")) if content else []

    def _kv_update(self, session_key, key, doc):
        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{COLLECTION_NAME}/{urllib.parse.quote(key)}"
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

            original_value = payload.get("value") or payload.get("original_value")
            entity_type = payload.get("entity_type") or payload.get("original_entity_type")
            updates = payload.get("updates") or payload.get("updatedRow") or {}

            if not original_value or not entity_type:
                raise ValueError("Missing required fields: value/entity_type")
            if not isinstance(updates, dict) or not updates:
                raise ValueError("Missing or invalid updates / updatedRow")

            docs = self._kv_get(session_key, original_value, entity_type)
            if not docs:
                return {
                    "payload": {"status": "error", "error": f"Whitelist entry '{original_value}' not found"},
                    "status": 404,
                }

            doc = docs[0]
            key = doc.get("_key")
            if not key:
                raise ValueError("KV document missing _key")

            for field, value in updates.items():
                if field == "_key":
                    continue
                if field in ("value", "entity_type") and value:
                    doc[field] = str(value).strip().lower()
                else:
                    doc[field] = value

            now = int(datetime.datetime.utcnow().timestamp())
            doc["updated_time"] = now
            doc["updated_by"] = doc.get("updated_by") or "allowlist_manager"

            resp, _ = self._kv_update(session_key, key, doc)
            status_code = int(resp.get("status", "200"))
            if status_code not in (200, 201, 204):
                return {
                    "payload": {"status": "error", "error": f"KV update failed (HTTP {status_code})"},
                    "status": status_code,
                }

            doc.pop("_key", None)
            return {"payload": {"status": "success", "doc": doc}, "status": 200}

        except Exception as e:
            self.log(f"Exception: {e}")
            return {"payload": {"status": "error", "error": str(e)}, "status": 500}

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
