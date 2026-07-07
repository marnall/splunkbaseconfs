import json
import os
import sys

from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.environ.get("SPLUNK_HOME", "/opt/splunk"), "etc", "apps", "apt-falconer", "bin"))


class IntelBuilderListHandler(PersistentServerConnectionApplication):
    def __init__(self, *args, **kwargs):
        super(IntelBuilderListHandler, self).__init__()

    def handle(self, in_string):
        from intel_builder_common import error_response, json_response, kv_list, log, session_key_from_args

        try:
            args = json.loads(in_string or "{}")
            session_key = session_key_from_args(args)
            if not session_key:
                raise ValueError("Missing session key")

            docs = kv_list(session_key)
            docs.sort(
                key=lambda d: (
                    str(d.get("status") or ""),
                    -(int(d.get("updated_time") or d.get("created_time") or 0)),
                    str(d.get("indicator") or ""),
                )
            )
            for doc in docs:
                doc.pop("_key", None)

            return json_response({"status": "success", "entries": docs, "payload": docs}, status=200)
        except Exception as e:
            log("intel_builder_list", f"Exception: {e}")
            return error_response(e, status=500)

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
