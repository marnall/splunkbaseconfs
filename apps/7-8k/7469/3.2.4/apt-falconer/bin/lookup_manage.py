# bin/lookup_manage.py

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
    "var",
    "log",
    "splunk",
    "falconer_lookup_debug.log",
)


class LookupManage(PersistentServerConnectionApplication):
    """
    /falconer/lookup_manage
    """

    def __init__(self, command_line, command_arg):
        super(LookupManage, self).__init__()

    # ------------- Helpers -------------

    def log(self, msg: str):
        if not DEBUG_ENABLED:
            return
        try:
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            with open(DEBUG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [lookup_manage] {msg}\n")
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

        resp, content = rest.simpleRequest(
            uri,
            method="GET",
            getargs=getargs,
            sessionKey=session_key,
        )

        status = resp.get("status", "")
        self.log(f"KV GET HTTP status: {status}")

        docs = json.loads(content.decode("utf-8"))
        self.log(f"KV GET returned {len(docs)} docs for signal={signal}")
        return docs

    def _kv_get_by_signal_id(self, session_key, signal_id):
        sig_id = str(signal_id)
        query = json.dumps({"signal_id": sig_id})
        getargs = {"output_mode": "json", "query": query}

        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{COLLECTION_NAME}"
        self.log(f"KV GET {uri} query={query}")

        resp, content = rest.simpleRequest(
            uri,
            method="GET",
            getargs=getargs,
            sessionKey=session_key,
        )

        status = resp.get("status", "")
        self.log(f"KV GET HTTP status: {status}")

        docs = json.loads(content.decode("utf-8"))
        self.log(f"KV GET returned {len(docs)} docs for signal_id={signal_id}")
        return docs

    def _kv_update_doc(self, session_key, key: str, doc: dict):
        """
        Update a KV document using jsonargs (dict).
        """
        uri = (
            f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/"
            f"{COLLECTION_NAME}/{urllib.parse.quote(key)}"
        )

        json_bytes = json.dumps(doc).encode("utf-8")
       
        self.log(f"KV UPDATE {uri} doc={doc}")

        resp, content = rest.simpleRequest(
            uri,
            method="POST",
            jsonargs=json_bytes,
            raiseAllErrors=True,
            sessionKey=session_key,
        )
        return resp, content 

    # ------------- Main handler -------------

    def handle(self, in_string):
        try:
            method, payload, args = self._parse_args(in_string)
            self.log(f"📥 /falconer/lookup_manage method={method} payload={payload}")

            if method != "POST":
                return {
                    "payload": {"status": "error", "error": "Only POST supported"},
                    "status": 405,
                }

            session_key = (args.get("session", {}) or {}).get("authtoken")
            if not session_key:
                raise ValueError("Missing sessionKey/authtoken")

            signal_id = payload.get("signal_id")
            signal = (
                payload.get("signal")
                or payload.get("original_signal")
            )

            updates = (
                payload.get("updates")
                or payload.get("updatedRow")
                or {}
            )

            if not signal_id and not signal:
                raise ValueError("Missing required field: signal_id or signal / original_signal")

            if not isinstance(updates, dict) or not updates:
                raise ValueError("Missing or invalid updates / updatedRow")

            self.log(f"Updating signal_id={signal_id} signal={signal} with updates={updates}")

            docs = self._kv_get_by_signal_id(session_key, signal_id) if signal_id else []
            if not docs and signal:
                docs = self._kv_get_by_signal(session_key, signal)
            if not docs:
                return {
                    "payload": {
                        "status": "error",
                        "error": f"Signal '{signal_id or signal}' not found",
                    },
                    "status": 404,
                }

            doc = docs[0]
            key = doc.get("_key")
            if not key:
                raise ValueError("KV document missing _key")

            # Apply updates
            for field, value in updates.items():
                if field == "_key":
                    continue
                doc[field] = value

            now = datetime.datetime.utcnow()
            epoch = int(now.timestamp())
            doc["updated_time"] = epoch
            doc.setdefault("updated_by", "signals_dashboard")

            resp, content = self._kv_update_doc(session_key, key, doc)
            status_code = int(resp.get("status", "200"))

            self.log(f"KV UPDATE status={status_code} content={content[:500]}")

            if status_code not in (200, 201, 204):
                return {
                    "payload": {
                        "status": "error",
                        "error": f"KV update failed (HTTP {status_code})",
                    },
                    "status": status_code,
                }

            return {
                "payload": {
                    "status": "success",
                    "signal": signal,
                    "signal_id": signal_id or doc.get("signal_id"),
                    "doc": doc,
                },
                "status": 200,
            }

        except Exception as e:
            self.log(f"❌ Exception in LookupManage: {e}")
            return {
                "payload": {"status": "error", "error": str(e)},
                "status": 500,
            }

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
