# bin/signals_list.py
import os
import json
import datetime

from splunk.persistconn.application import PersistentServerConnectionApplication
import splunk.rest as rest

APP_NAME        = "apt-falconer"
COLLECTION_NAME = "falconer_signals"
DEBUG_ENABLED   = True

DEBUG_PATH = os.path.join(
    os.environ.get("SPLUNK_HOME", "/opt/splunk"),
    "var",
    "log",
    "splunk",
    "falconer_lookup_debug.log",
)


class SignalsListHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(SignalsListHandler, self).__init__()

    def log(self, message: str):
        if not DEBUG_ENABLED:
            return
        try:
            with open(DEBUG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.utcnow().isoformat()}] {message}\n")
        except Exception:
            # Never let logging break the handler
            pass

    def kv_list(self, session_key=None):
        """Return all docs from the falconer_signals KV collection."""
        uri = (
            f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/"
            f"{COLLECTION_NAME}?output_mode=json"
        )
        self.log(f"KV list URI: {uri}")

        kwargs = {
            "method": "GET",
            "raiseAllErrors": True,
        }
        if session_key:
            kwargs["sessionKey"] = session_key

        resp, content = rest.simpleRequest(uri, **kwargs)
        status = resp.get("status", "")
        self.log(f"KV list HTTP status: {status}")
        self.log(
            f"KV list raw content (first 500 bytes): {content[:500]!r}"
            if content
            else "KV list: empty content"
        )

        docs = json.loads(content.decode("utf-8")) if content else []
        return docs

    def handle(self, in_string):
        """Persistent connection entry point."""
        self.log("📥 /falconer/signals_list hit")

        try:
            # in_string may be bytes or a JSON string. For a simple GET it is
            # often "" or "{}", but can still contain the session info.
            if isinstance(in_string, bytes):
                in_string = in_string.decode("utf-8")

            raw_payload = in_string or "{}"
            self.log(f"Raw in_string: {raw_payload!r}")

            try:
                payload = json.loads(raw_payload)
            except Exception:
                payload = {}
            self.log(f"Parsed payload: {payload}")

            # Try to extract a session key in as many ways as possible
            session_key = None
            if isinstance(payload, dict):
                session = payload.get("session") or {}
                if isinstance(session, dict):
                    session_key = (
                        session.get("authtoken")
                        or session.get("sessionKey")
                        or session.get("token")
                    )
                # Some Splunk versions surface it at top level
                session_key = session_key or payload.get("sessionKey")

            if session_key:
                self.log("Using session key for KV request")
            else:
                self.log("No session key found; using anonymous KV request")

            docs = self.kv_list(session_key=session_key)

            # Sort newest first if possible
            try:
                docs.sort(
                    key=lambda d: d.get("updated_time")
                    or d.get("created_time")
                    or "",
                    reverse=True,
                )
            except Exception as e:
                self.log(f"⚠️ Failed to sort docs: {e}")

            # Strip internal _key to keep the UI clean
            for d in docs:
                d.pop("_key", None)

            return {
                "payload": docs,
                "status": 200,
            }

        except Exception as e:
            self.log(f"❌ Exception in SignalsList: {e}")
            return {
                "payload": {"status": "error", "error": str(e)},
                "status": 500,
            }

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass

