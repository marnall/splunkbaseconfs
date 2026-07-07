import os
import sys

from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.environ.get("SPLUNK_HOME", "/opt/splunk"), "etc", "apps", "apt-falconer", "bin"))


class IntelBuilderAppend(PersistentServerConnectionApplication):
    def __init__(self, *args, **kwargs):
        super(IntelBuilderAppend, self).__init__()

    def handle(self, in_string):
        from intel_builder_common import build_doc, error_response, json_response, kv_insert, kv_query, log, parse_args, session_key_from_args

        try:
            method, payload, args = parse_args(in_string)
            if method != "POST":
                return error_response("Only POST supported", status=405)

            session_key = session_key_from_args(args)
            if not session_key:
                raise ValueError("Missing session key")

            doc = build_doc(payload)
            existing = kv_query(
                session_key,
                {"indicator": doc["indicator"], "indicator_type": doc["indicator_type"]},
            )
            if existing:
                existing[0].pop("_key", None)
                return json_response({"status": "exists", "doc": existing[0]}, status=200)

            resp, _ = kv_insert(session_key, doc)
            status_code = int(resp.get("status", "200"))
            if status_code not in (200, 201, 204):
                return error_response(f"KV insert failed (HTTP {status_code})", status=status_code)

            return json_response({"status": "success", "doc": doc}, status=200)
        except Exception as e:
            log("intel_builder_append", f"Exception: {e}")
            return error_response(e, status=500)

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
