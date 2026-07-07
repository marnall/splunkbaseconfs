import os
import sys

from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.environ.get("SPLUNK_HOME", "/opt/splunk"), "etc", "apps", "apt-falconer", "bin"))


class IntelBuilderDelete(PersistentServerConnectionApplication):
    def __init__(self, *args, **kwargs):
        super(IntelBuilderDelete, self).__init__()

    def handle(self, in_string):
        from intel_builder_common import error_response, json_response, kv_delete, kv_query, log, parse_args, session_key_from_args

        try:
            method, payload, args = parse_args(in_string)
            if method != "POST":
                return error_response("Only POST supported", status=405)

            session_key = session_key_from_args(args)
            if not session_key:
                raise ValueError("Missing session key")

            entries = payload.get("entries")
            if not isinstance(entries, list) or not entries:
                raise ValueError("No intel entries provided to delete")

            deleted = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                entry_id = entry.get("entry_id")
                if not entry_id:
                    continue
                docs = kv_query(session_key, {"entry_id": str(entry_id)})
                for doc in docs:
                    key = doc.get("_key")
                    if not key:
                        continue
                    kv_delete(session_key, key)
                    deleted.append({"entry_id": entry_id})

            return json_response({"status": "success", "deleted": deleted}, status=200)
        except Exception as e:
            log("intel_builder_delete", f"Exception: {e}")
            return error_response(e, status=500)

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
