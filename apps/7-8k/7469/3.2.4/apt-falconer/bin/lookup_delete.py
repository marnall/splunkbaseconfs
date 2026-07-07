# bin/lookup_delete.py

import os
import json
import datetime
import urllib.parse

from splunk.persistconn.application import PersistentServerConnectionApplication
import splunk.rest as rest

APP_NAME        = "apt-falconer"
COLLECTION_NAME = "falconer_signals"
DEBUG_ENABLED   = True

DEBUG_PATH = os.path.join(
    os.environ.get("SPLUNK_HOME", "/opt/splunk"),
    "var", "log", "splunk", "falconer_lookup_debug.log",
)


class LookupDelete(PersistentServerConnectionApplication):
    """
    Delete one or more signals from the falconer_signals KV store.

    Expected JSON payload:
    {
      "signals": ["10.57.64.15", "1.2.3.4"]
    }
    """

    def __init__(self, command_line, command_arg):
        super(LookupDelete, self).__init__()

    def log(self, msg: str):
        if not DEBUG_ENABLED:
            return
        try:
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            with open(DEBUG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [lookup_delete] {msg}\n")
        except Exception:
            pass

    def _parse_args(self, in_string):
        try:
            args = json.loads(in_string) if in_string else {}
        except Exception as e:
            self.log(f"Failed to parse in_string as JSON: {e}")
            args = {}

        method = (args.get("method") or "GET").upper()
        raw_payload = args.get("payload")

        if isinstance(raw_payload, str):
            try:
                payload = json.loads(raw_payload)
            except Exception as e:
                self.log(f"Failed to parse payload JSON: {e}")
                payload = {}
        elif isinstance(raw_payload, dict):
            payload = raw_payload
        else:
            payload = {}

        return method, payload, args

    def _kv_get_by_signal(self, session_key, signal):
        sig_str = str(signal)
        query = json.dumps({"signal": sig_str})
        getargs = {"output_mode": "json", "query": query}

        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{COLLECTION_NAME}"
        self.log(f"KV GET {uri} query={query}")

        _, content = rest.simpleRequest(
            uri,
            method="GET",
            getargs=getargs,
            sessionKey=session_key,
        )
        docs = json.loads(content.decode("utf-8"))
        self.log(f"KV GET returned {len(docs)} docs for signal={signal}")
        return docs

    def _kv_get_by_signal_id(self, session_key, signal_id):
        sig_id = str(signal_id)
        query = json.dumps({"signal_id": sig_id})
        getargs = {"output_mode": "json", "query": query}

        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{COLLECTION_NAME}"
        self.log(f"KV GET {uri} query={query}")

        _, content = rest.simpleRequest(
            uri,
            method="GET",
            getargs=getargs,
            sessionKey=session_key,
        )
        docs = json.loads(content.decode("utf-8"))
        self.log(f"KV GET returned {len(docs)} docs for signal_id={signal_id}")
        return docs

    def _kv_delete_doc(self, session_key, key):
        uri = (
            f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/"
            f"{COLLECTION_NAME}/{urllib.parse.quote(key)}"
        )
        self.log(f"KV DELETE {uri}")
        rest.simpleRequest(
            uri,
            method="DELETE",
            sessionKey=session_key,
        )

    def handle(self, in_string):
        try:
            method, payload, args = self._parse_args(in_string)
            self.log(f"📥 /falconer/lookup_delete method={method} payload={payload}")

            if method != "POST":
                return {
                    "payload": {"status": "error", "error": "Only POST supported"},
                    "status": 405,
                }

            session_key = (args.get("session", {}) or {}).get("authtoken")
            if not session_key:
                raise ValueError("Missing sessionKey/authtoken")

            signal_ids = payload.get("signal_ids")
            signals = payload.get("signals")
            if not isinstance(signal_ids, list):
                signal_ids = []
            if not isinstance(signals, list):
                signals = []
            if not signal_ids and not signals:
                raise ValueError("No signals provided to delete")

            signal_ids = [str(s) for s in signal_ids if s is not None]
            signals = [str(s) for s in signals if s is not None]

            deleted = []

            for sig_id in signal_ids:
                docs = self._kv_get_by_signal_id(session_key, sig_id)
                for doc in docs:
                    key = doc.get("_key")
                    if not key:
                        continue
                    self._kv_delete_doc(session_key, key)
                    deleted.append(sig_id)

            for sig in signals:
                docs = self._kv_get_by_signal(session_key, sig)
                for doc in docs:
                    key = doc.get("_key")
                    if not key:
                        continue
                    self._kv_delete_doc(session_key, key)
                    deleted.append(sig)


            self.log(f"✅ Deleted signals: {deleted}")
            return {
                "payload": {"status": "success", "deleted": deleted},
                "status": 200,
            }

        except Exception as e:
            self.log(f"❌ Exception in LookupDelete: {e}")
            return {
                "payload": {"status": "error", "error": str(e)},
                "status": 500,
            }

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
