import os
import sys

from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.environ.get("SPLUNK_HOME", "/opt/splunk"), "etc", "apps", "apt-falconer", "bin"))


class IntelBuilderManage(PersistentServerConnectionApplication):
    def __init__(self, *args, **kwargs):
        super(IntelBuilderManage, self).__init__()

    def handle(self, in_string):
        from intel_builder_common import build_doc, error_response, json_response, kv_query, kv_update, log, now_epoch, parse_args, session_key_from_args

        try:
            method, payload, args = parse_args(in_string)
            if method != "POST":
                return error_response("Only POST supported", status=405)

            session_key = session_key_from_args(args)
            if not session_key:
                raise ValueError("Missing session key")

            entry_id = payload.get("entry_id") or payload.get("original_entry_id")
            updates = payload.get("updates") or payload.get("updatedRow") or {}
            if not entry_id:
                raise ValueError("Missing required field: entry_id")
            if not isinstance(updates, dict) or not updates:
                raise ValueError("Missing or invalid updates / updatedRow")

            docs = kv_query(session_key, {"entry_id": str(entry_id)})
            if not docs:
                return error_response("Intel entry not found", status=404)

            existing = docs[0]
            key = existing.get("_key")
            if not key:
                raise ValueError("KV document missing _key")

            merged = dict(existing)
            merged.update(updates)
            merged["entry_id"] = existing.get("entry_id")
            merged["created_time"] = existing.get("created_time")
            merged["created_by"] = existing.get("created_by")
            merged["updated_time"] = now_epoch()
            merged["updated_by"] = updates.get("updated_by") or existing.get("updated_by") or "intel_builder"

            normalized = build_doc(merged)
            normalized["entry_id"] = existing.get("entry_id")
            normalized["created_time"] = existing.get("created_time")
            normalized["created_by"] = existing.get("created_by")
            normalized["updated_time"] = merged["updated_time"]
            normalized["updated_by"] = merged["updated_by"]

            resp, _ = kv_update(session_key, key, normalized)
            status_code = int(resp.get("status", "200"))
            if status_code not in (200, 201, 204):
                return error_response(f"KV update failed (HTTP {status_code})", status=status_code)

            return json_response({"status": "success", "doc": normalized}, status=200)
        except Exception as e:
            log("intel_builder_manage", f"Exception: {e}")
            return error_response(e, status=500)

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
