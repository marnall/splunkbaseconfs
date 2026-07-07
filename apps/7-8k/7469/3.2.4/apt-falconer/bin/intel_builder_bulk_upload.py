import json
import os
import sys

from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.environ.get("SPLUNK_HOME", "/opt/splunk"), "etc", "apps", "apt-falconer", "bin"))


def _records_from_payload(payload):
    records = payload.get("records")
    if isinstance(records, str):
        records = json.loads(records)
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    return [r for r in records if isinstance(r, dict)]


class IntelBuilderBulkUpload(PersistentServerConnectionApplication):
    def __init__(self, *args, **kwargs):
        super(IntelBuilderBulkUpload, self).__init__()

    def handle(self, in_string):
        from intel_builder_common import build_doc, error_response, json_response, kv_insert, kv_query, kv_update, log, parse_args, session_key_from_args
        from intel_schema import primary_observable, validate_doc

        try:
            method, payload, args = parse_args(in_string)
            if method != "POST":
                return error_response("Only POST supported", status=405)

            session_key = session_key_from_args(args)
            if not session_key:
                raise ValueError("Missing session key")

            records = _records_from_payload(payload)
            if len(records) > 1000:
                raise ValueError("Bulk upload is limited to 1000 rows per request")

            created = 0
            updated = 0
            errors = []
            processed = []

            for idx, record in enumerate(records, start=1):
                try:
                    record["created_by"] = record.get("created_by") or "intel_builder_bulk_upload"
                    doc = build_doc(record)
                    doc, validation_errors = validate_doc(doc, require_all_headers=True)
                    if validation_errors:
                        raise ValueError("; ".join(validation_errors))
                    _, doc["indicator"] = primary_observable(doc, doc["indicator_type"])

                    existing = kv_query(session_key, {"indicator": doc["indicator"], "indicator_type": doc["indicator_type"]})
                    if existing:
                        existing_doc = existing[0]
                        key = existing_doc.get("_key")
                        merged = dict(existing_doc)
                        merged.update(doc)
                        merged["entry_id"] = existing_doc.get("entry_id") or doc["entry_id"]
                        merged["created_time"] = existing_doc.get("created_time") or doc["created_time"]
                        merged["created_by"] = existing_doc.get("created_by") or doc["created_by"]
                        merged.pop("_key", None)
                        resp, _ = kv_update(session_key, key, merged)
                        status_code = int(resp.get("status", "200"))
                        if status_code not in (200, 201, 204):
                            raise RuntimeError(f"KV update failed (HTTP {status_code})")
                        updated += 1
                        processed.append({"row": idx, "action": "updated", "indicator": doc["indicator"], "indicator_type": doc["indicator_type"]})
                    else:
                        resp, _ = kv_insert(session_key, doc)
                        status_code = int(resp.get("status", "200"))
                        if status_code not in (200, 201, 204):
                            raise RuntimeError(f"KV insert failed (HTTP {status_code})")
                        created += 1
                        processed.append({"row": idx, "action": "created", "indicator": doc["indicator"], "indicator_type": doc["indicator_type"]})
                except Exception as e:
                    errors.append({"row": idx, "indicator": record.get("indicator", ""), "indicator_type": record.get("indicator_type", ""), "error": str(e)})

            return json_response(
                {
                    "status": "success" if not errors else "partial",
                    "created": created,
                    "updated": updated,
                    "error_count": len(errors),
                    "errors": errors,
                    "processed": processed,
                },
                status=200,
            )
        except Exception as e:
            log("intel_builder_bulk_upload", f"Exception: {e}")
            return error_response(e, status=500)

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
