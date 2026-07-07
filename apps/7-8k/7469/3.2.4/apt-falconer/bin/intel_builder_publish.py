import csv
import datetime
import hashlib
import ipaddress
import json
import os
import re
import sys
from urllib.parse import quote, urlparse

import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.environ.get("SPLUNK_HOME", "/opt/splunk"), "etc", "apps", "apt-falconer", "bin"))

APP_NAME = "apt-falconer"
MANAGED_SOURCE = "Falconer Intel Builder"
ES_APP_CANDIDATES = ("SA-ThreatIntelligence", "DA-ESS-ThreatIntelligence", "SplunkEnterpriseSecuritySuite")

from intel_schema import INTEL_TYPES, MANAGED_HEADERS, canonical_type, primary_observable, validate_doc

FALCONER_LOOKUPS = {
    key: {"lookup": spec["lookup"], "file": spec["file"], "indicator_field": spec["observables"][0]}
    for key, spec in INTEL_TYPES.items()
}

BASE_HEADERS = {key: spec["required"] for key, spec in INTEL_TYPES.items()}


def splunk_home():
    return os.environ.get("SPLUNK_HOME", "/opt/splunk")


def app_lookup_path(app, filename):
    return os.path.join(splunk_home(), "etc", "apps", app, "lookups", filename)


def lookup_path(filename):
    return app_lookup_path(APP_NAME, filename)


def now_epoch():
    return int(datetime.datetime.utcnow().timestamp())


def parse_expiration(value):
    value = str(value or "").strip()
    if not value:
        return None
    candidates = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in candidates:
        try:
            return int(datetime.datetime.strptime(value, fmt).replace(tzinfo=datetime.timezone.utc).timestamp())
        except Exception:
            pass
    try:
        return int(float(value))
    except Exception:
        return None


def is_expired(doc, current_time):
    expiration = str(doc.get("expiration") or "").strip()
    if not expiration:
        return False
    parsed = parse_expiration(expiration)
    return parsed is None or parsed < current_time


def normalize_indicator(indicator_type, value):
    indicator_type = canonical_type(indicator_type)
    value = str(value or "").strip()
    if indicator_type in ("domain", "file", "http", "email", "user"):
        return value.lower()
    return value


def validate_indicator(indicator_type, value):
    indicator_type = canonical_type(indicator_type)
    spec = INTEL_TYPES[indicator_type]
    doc = {"indicator_type": indicator_type, spec["observables"][0]: value, "description": "validation", "weight": 60}
    _, errors = validate_doc(doc, require_all_headers=False)
    return "; ".join(errors)


def deterministic_key(indicator_type, indicator):
    seed = f"{canonical_type(indicator_type)}|{indicator}|{MANAGED_SOURCE}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def get_doc_id(doc):
    return str(doc.get("entry_id") or doc.get("_key") or "").strip()


def row_for_doc(doc, indicator_type, indicator):
    indicator_type = canonical_type(indicator_type)
    row, errors = validate_doc(doc, require_all_headers=True)
    if errors:
        raise ValueError("; ".join(errors))
    _, indicator = primary_observable(row, indicator_type)
    description = str(doc.get("description") or "Falconer-authored intelligence").strip()
    weight = str(doc.get("weight") or 50).strip()
    source = str(doc.get("source") or MANAGED_SOURCE).strip()
    threat_group = str(doc.get("threat_group") or "").strip()
    key = deterministic_key(indicator_type, indicator)
    base = {field: str(row.get(field) or "").strip() for field in INTEL_TYPES[indicator_type]["required"]}
    base.update({
        "description": description,
        "threat_description": description,
        "weight": weight,
        "source": source,
        "threat_collection": f"{MANAGED_SOURCE}: {source}",
        "threat_group": threat_group,
        "confidence": str(doc.get("confidence") or "").strip(),
        "expiration": str(doc.get("expiration") or "").strip(),
        "notes": str(doc.get("notes") or "").strip(),
        "falconer_managed": "1",
        "falconer_key": key,
        "falconer_entry_id": get_doc_id(doc),
        "updated_time": str(now_epoch()),
    })
    return base


def read_csv(path):
    if not os.path.exists(path):
        return [], []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows


def write_csv(path, headers, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def merge_rows(existing_rows, new_rows, indicator_field):
    by_key = {}
    preserved = []
    for row in existing_rows:
        key = str(row.get("falconer_key") or "").strip()
        managed = str(row.get("falconer_managed") or "").strip() in ("1", "true", "True")
        if managed and key:
            by_key[key] = row
        else:
            preserved.append(row)

    for row in new_rows:
        key = row.get("falconer_key")
        previous = by_key.get(key, {})
        merged = dict(previous)
        merged.update(row)
        if not merged.get(indicator_field):
            merged[indicator_field] = row.get(indicator_field, "")
        by_key[key] = merged

    return preserved + list(by_key.values())


def ordered_headers(existing_headers, indicator_type, rows):
    headers = []
    for header in BASE_HEADERS.get(indicator_type, []) + MANAGED_HEADERS:
        if header not in headers:
            headers.append(header)
    for header in existing_headers:
        if header not in headers:
            headers.append(header)
    for row in rows:
        for header in row:
            if header not in headers:
                headers.append(header)
    return headers


def es_installed(session_key):
    try:
        _, content = rest.simpleRequest(
            "/services/apps/local/SplunkEnterpriseSecuritySuite",
            method="GET",
            getargs={"output_mode": "json"},
            raiseAllErrors=True,
            sessionKey=session_key,
        )
        data = json.loads(content.decode("utf-8")) if content else {}
        entry = (data.get("entry") or [{}])[0]
        disabled = str((entry.get("content") or {}).get("disabled") or "0")
        return disabled not in ("1", "true", "True")
    except Exception:
        return False


def resolve_es_lookup(session_key, lookup_name):
    errors = []
    for app in ES_APP_CANDIDATES:
        try:
            uri = f"/servicesNS/nobody/{app}/data/transforms/lookups/{quote(lookup_name, safe='')}"
            _, content = rest.simpleRequest(
                uri,
                method="GET",
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
                sessionKey=session_key,
            )
            data = json.loads(content.decode("utf-8")) if content else {}
            entry = (data.get("entry") or [{}])[0]
            filename = (entry.get("content") or {}).get("filename") or f"{lookup_name}.csv"
            path = app_lookup_path(app, filename)
            if not os.path.isdir(os.path.dirname(path)):
                errors.append(f"{lookup_name}: lookup app {app} has no lookups directory")
                continue
            return {"app": app, "lookup": lookup_name, "file": filename, "path": path}
        except Exception as e:
            errors.append(f"{lookup_name}: {e}")
    raise RuntimeError("Unable to resolve writable ES lookup target. " + "; ".join(errors[:3]))


def target_specs(session_key, publish_mode):
    return {
        ty: {
            "lookup": spec["lookup"],
            "file": spec["file"],
            "path": lookup_path(spec["file"]),
            "indicator_field": spec["indicator_field"],
        }
        for ty, spec in FALCONER_LOOKUPS.items()
    }


class IntelBuilderPublish(PersistentServerConnectionApplication):
    def __init__(self, *args, **kwargs):
        super(IntelBuilderPublish, self).__init__()

    def handle(self, in_string):
        from intel_builder_common import error_response, json_response, kv_list, kv_update, log, parse_args, session_key_from_args

        try:
            method, payload, args = parse_args(in_string)
            if method != "POST":
                return error_response("Only POST supported", status=405)

            session_key = session_key_from_args(args)
            if not session_key:
                raise ValueError("Missing session key")

            publish_mode = "falconer_local_intel_es_compatible" if es_installed(session_key) else "falconer_local_intel"
            targets = target_specs(session_key, publish_mode)
            docs = kv_list(session_key)
            current_time = now_epoch()

            rows_by_type = {key: [] for key in FALCONER_LOOKUPS}
            publishable_docs = []
            skipped = []

            for doc in docs:
                status = str(doc.get("status") or "").strip().lower()
                if status not in ("ready", "published"):
                    if status in ("draft", "disabled"):
                        skipped.append({"entry_id": get_doc_id(doc), "indicator": doc.get("indicator", ""), "reason": f"{status} entries are inactive"})
                    continue

                try:
                    indicator_type = canonical_type(doc.get("indicator_type"))
                except Exception:
                    skipped.append({"entry_id": get_doc_id(doc), "indicator": doc.get("indicator", ""), "reason": "unsupported indicator_type"})
                    continue
                _, indicator = primary_observable(doc, indicator_type)
                if indicator_type not in FALCONER_LOOKUPS:
                    skipped.append({"entry_id": get_doc_id(doc), "indicator": indicator, "reason": "unsupported indicator_type"})
                    continue
                if is_expired(doc, current_time):
                    skipped.append({"entry_id": get_doc_id(doc), "indicator": indicator, "reason": "expired"})
                    continue
                _, validation_errors = validate_doc(doc, require_all_headers=True)
                if validation_errors:
                    skipped.append({"entry_id": get_doc_id(doc), "indicator": indicator, "reason": "; ".join(validation_errors)})
                    continue

                row = row_for_doc(doc, indicator_type, indicator)
                rows_by_type[indicator_type].append(row)
                publishable_docs.append((doc, indicator_type, indicator))

            target_lookup_names = []
            for indicator_type, target in targets.items():
                existing_headers, existing_rows = read_csv(target["path"])
                merged_rows = merge_rows(existing_rows, rows_by_type[indicator_type], target["indicator_field"])
                headers = ordered_headers(existing_headers, indicator_type, merged_rows)
                write_csv(target["path"], headers, merged_rows)
                target_lookup_names.append(target["lookup"])

            published_entry_ids = []
            for doc, _, _ in publishable_docs:
                if str(doc.get("status") or "").strip().lower() != "ready":
                    continue
                key = doc.get("_key")
                if not key:
                    skipped.append({"entry_id": get_doc_id(doc), "indicator": doc.get("indicator", ""), "reason": "missing kv key"})
                    continue
                doc["status"] = "published"
                doc["updated_time"] = current_time
                doc["updated_by"] = "intel_builder_publish"
                resp, _ = kv_update(session_key, key, doc)
                status_code = int(resp.get("status", "200"))
                if status_code not in (200, 201, 204):
                    raise RuntimeError(f"KV update failed for {get_doc_id(doc)} (HTTP {status_code})")
                published_entry_ids.append(get_doc_id(doc))

            counts = {key: len(value) for key, value in rows_by_type.items()}
            return json_response(
                {
                    "status": "success",
                    "publish_mode": publish_mode,
                    "target_lookups": target_lookup_names,
                    "counts_by_type": counts,
                    "skipped_count": len(skipped),
                    "skipped_reasons": skipped,
                    "published_entry_ids": published_entry_ids,
                    "errors": [],
                },
                status=200,
            )
        except Exception as e:
            log("intel_builder_publish", f"Exception: {e}")
            return error_response(e, status=500)

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
