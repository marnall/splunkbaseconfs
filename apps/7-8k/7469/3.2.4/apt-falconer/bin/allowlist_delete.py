import os
import json
import datetime
import urllib.parse

from splunk.persistconn.application import PersistentServerConnectionApplication
import splunk.rest as rest

APP_NAME = "apt-falconer"
COLLECTION_NAME = "falconer_allowlist_lookup"
DEBUG_ENABLED = True

DEBUG_PATH = os.path.join(
    os.environ.get("SPLUNK_HOME", "/opt/splunk"),
    "var",
    "log",
    "splunk",
    "falconer_lookup_debug.log",
)


class AllowlistDelete(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(AllowlistDelete, self).__init__()

    def log(self, msg: str):
        if not DEBUG_ENABLED:
            return
        try:
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            with open(DEBUG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [allowlist_delete] {msg}\n")
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

    def _kv_delete(self, session_key, key):
        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{COLLECTION_NAME}/{urllib.parse.quote(key)}"
        return rest.simpleRequest(uri, method="DELETE", sessionKey=session_key)

    def handle(self, in_string):
        try:
            method, payload, args = self._parse_args(in_string)
            if method != "POST":
                return {"payload": {"status": "error", "error": "Only POST supported"}, "status": 405}

            session_key = (args.get("session", {}) or {}).get("authtoken")
            if not session_key:
                raise ValueError("Missing sessionKey/authtoken")

            entries = payload.get("entries")
            if not isinstance(entries, list) or not entries:
                raise ValueError("No allowlist entries provided to delete")

            deleted = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                value = entry.get("value")
                entity_type = entry.get("entity_type")
                if not value or not entity_type:
                    continue
                docs = self._kv_get(session_key, value, entity_type)
                for doc in docs:
                    key = doc.get("_key")
                    if not key:
                        continue
                    self._kv_delete(session_key, key)
                    deleted.append({"value": str(value).lower(), "entity_type": str(entity_type).lower()})

            return {"payload": {"status": "success", "deleted": deleted}, "status": 200}
        except Exception as e:
            self.log(f"Exception: {e}")
            return {"payload": {"status": "error", "error": str(e)}, "status": 500}

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
