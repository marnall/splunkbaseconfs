import datetime
import json
import os
import urllib.parse
import uuid
from urllib.parse import parse_qs, unquote_plus

import splunk.rest as rest

APP_NAME = "apt-falconer"
COLLECTION_NAME = "falconer_intel_builder"
DEBUG_ENABLED = True

DEBUG_PATH = os.path.join(
    os.environ.get("SPLUNK_HOME", "/opt/splunk"),
    "var",
    "log",
    "splunk",
    "falconer_lookup_debug.log",
)


def log(component, msg):
    if not DEBUG_ENABLED:
        return
    try:
        ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(DEBUG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [{component}] {msg}\n")
    except Exception:
        pass


def json_response(payload, status=200):
    return {
        "payload": json.dumps(payload),
        "status": status,
        "headers": [("Content-Type", "application/json")],
    }


def error_response(message, status=500):
    return json_response({"status": "error", "error": str(message)}, status=status)


def _list_to_dict(maybe_list):
    out = {}
    if isinstance(maybe_list, list):
        for item in maybe_list:
            if isinstance(item, dict) and "name" in item:
                out[item["name"]] = item.get("value")
    return out


def _parse_string_payload(value):
    value = (value or "").strip()
    if not value:
        return {}

    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return _list_to_dict(parsed)
    except Exception:
        pass

    try:
        qs = parse_qs(value, keep_blank_values=True)
        if "payload" in qs:
            inner = unquote_plus(qs["payload"][0])
            return _parse_string_payload(inner)
        return {k: v[0] for k, v in qs.items() if v}
    except Exception:
        return {}


def parse_args(in_string):
    try:
        if isinstance(in_string, bytes):
            in_string = in_string.decode("utf-8")
        args = json.loads(in_string) if in_string else {}
    except Exception:
        args = {}

    if isinstance(args, list):
        args = _list_to_dict(args)
    if not isinstance(args, dict):
        args = {}

    method = (args.get("method") or "GET").upper()
    raw_payload = args.get("payload")
    payload = {}

    if isinstance(raw_payload, dict):
        payload = raw_payload
    elif isinstance(raw_payload, str):
        payload = _parse_string_payload(raw_payload)
    else:
        payload = dict(args)

    if isinstance(payload, list):
        payload = _list_to_dict(payload)
    if not isinstance(payload, dict):
        payload = {}

    return method, payload, args


def now_epoch():
    return int(datetime.datetime.utcnow().timestamp())


def session_key_from_args(args):
    session = args.get("session") or {}
    if isinstance(session, dict):
        return session.get("authtoken") or session.get("sessionKey") or ""
    if isinstance(session, str):
        return session.replace("Splunk ", "").strip()
    return args.get("sessionKey") or ""


def collection_uri():
    return f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{COLLECTION_NAME}"


def kv_list(session_key):
    _, content = rest.simpleRequest(
        collection_uri(),
        method="GET",
        getargs={"output_mode": "json", "count": 0},
        raiseAllErrors=True,
        sessionKey=session_key,
    )
    return json.loads(content.decode("utf-8")) if content else []


def kv_query(session_key, query):
    _, content = rest.simpleRequest(
        collection_uri(),
        method="GET",
        getargs={"output_mode": "json", "query": json.dumps(query)},
        raiseAllErrors=True,
        sessionKey=session_key,
    )
    return json.loads(content.decode("utf-8")) if content else []


def kv_insert(session_key, doc):
    return rest.simpleRequest(
        collection_uri(),
        method="POST",
        jsonargs=json.dumps(doc).encode("utf-8"),
        raiseAllErrors=True,
        sessionKey=session_key,
    )


def kv_update(session_key, key, doc):
    uri = f"{collection_uri()}/{urllib.parse.quote(key)}"
    return rest.simpleRequest(
        uri,
        method="POST",
        jsonargs=json.dumps(doc).encode("utf-8"),
        raiseAllErrors=True,
        sessionKey=session_key,
    )


def kv_delete(session_key, key):
    uri = f"{collection_uri()}/{urllib.parse.quote(key)}"
    return rest.simpleRequest(uri, method="DELETE", sessionKey=session_key)


def normalize_text(value):
    return str(value or "").strip()


def normalize_indicator_type(value):
    from intel_schema import canonical_type
    return canonical_type(value)


def normalize_status(value):
    status = normalize_text(value).lower() or "ready"
    if status not in ("draft", "ready", "published", "disabled"):
        raise ValueError("status must be one of draft, ready, published, disabled")
    return status


def build_doc(payload):
    indicator_type = normalize_indicator_type(payload.get("indicator_type"))
    status = normalize_status(payload.get("status"))
    from intel_schema import INTEL_TYPES, primary_observable, validate_doc

    row = {}
    row.update(payload)
    row["indicator_type"] = indicator_type
    observable_aliases = {
        "file": "file_hash",
        "http": "url",
        "ip": "ip",
        "domain": "domain",
        "email": "src_user",
        "process": "process",
        "registry": "registry_path",
        "service": "service",
        "user": "user",
        "certificate": "certificate_serial",
    }
    indicator = normalize_text(payload.get("indicator"))
    if indicator and not normalize_text(row.get(observable_aliases[indicator_type])):
        row[observable_aliases[indicator_type]] = indicator

    row, errors = validate_doc(row, require_all_headers=False)
    if errors:
        raise ValueError("; ".join(errors))
    _, indicator = primary_observable(row, indicator_type)
    if not indicator:
        raise ValueError("Missing required observable field for " + indicator_type)

    now = now_epoch()
    created_by = normalize_text(payload.get("created_by")) or "intel_builder"
    doc = {
        field: normalize_text(row.get(field))
        for field in sorted(set(sum((spec["required"] for spec in INTEL_TYPES.values()), [])))
    }

    doc.update({
        "entry_id": normalize_text(payload.get("entry_id")) or str(uuid.uuid4()),
        "indicator": indicator,
        "indicator_type": indicator_type,
        "status": status,
        "description": normalize_text(row.get("description")),
        "weight": int(row.get("weight") or 60),
        "confidence": normalize_text(payload.get("confidence")) or "medium",
        "source": normalize_text(payload.get("source")) or "Falconer Intel Builder",
        "threat_group": normalize_text(payload.get("threat_group")),
        "expiration": normalize_text(payload.get("expiration")),
        "notes": normalize_text(payload.get("notes")),
        "created_time": now,
        "created_by": created_by,
        "updated_time": now,
        "updated_by": created_by,
    })
    doc["email_sender"] = doc.get("src_user", "")
    return doc
