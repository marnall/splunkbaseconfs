import os
import json
import datetime

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


class AllowlistListHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(AllowlistListHandler, self).__init__()

    def log(self, message: str):
        if not DEBUG_ENABLED:
            return
        try:
            with open(DEBUG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.utcnow().isoformat()}] [allowlist_list] {message}\n")
        except Exception:
            pass

    def kv_list(self, session_key):
        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{COLLECTION_NAME}"
        resp, content = rest.simpleRequest(
            uri,
            method="GET",
            getargs={"output_mode": "json", "count": 0},
            raiseAllErrors=True,
            sessionKey=session_key,
        )
        self.log(f"KV list HTTP status: {resp.get('status', '')}")
        docs = json.loads(content.decode("utf-8")) if content else []
        return docs

    def handle(self, in_string):
        try:
            request = json.loads(in_string or "{}")
            session = request.get("session") or {}
            session_key = ""
            if isinstance(session, dict):
                session_key = session.get("authtoken") or session.get("sessionKey") or ""
            session_key = session_key or request.get("sessionKey") or ""
            if not session_key:
                raise ValueError("Missing session key")

            docs = self.kv_list(session_key)
            docs.sort(
                key=lambda d: (
                    str(d.get("status") or ""),
                    -(int(d.get("updated_time") or d.get("created_time") or 0)),
                    str(d.get("value") or ""),
                )
            )
            for doc in docs:
                doc.pop("_key", None)

            return {"payload": docs, "status": 200}
        except Exception as e:
            self.log(f"Exception: {e}")
            return {"payload": {"status": "error", "error": str(e)}, "status": 500}

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
