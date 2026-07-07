#!/usr/bin/env python3
import csv
import gzip
import hashlib
import ipaddress
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

APP_NAME = "apt-falconer"
APP_VERSION = "3.2.2"
HUNTS_COLLECTION = "falconer_hunts"
SIGNALS_COLLECTION = "falconer_signals"

_EMPTY_SENTINELS = {
    "",
    "-",
    "<value not set>",
    "<never>",
    "unknown",
    "n/a",
    "none",
    "null",
}
_SIGNATURE_RE = re.compile(r"\b\d{3,6}\b")
_TECHNIQUE_ID_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b", re.IGNORECASE)
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_FQDN_RE = re.compile(r"\b[a-zA-Z0-9][a-zA-Z0-9._-]*\.[A-Za-z][A-Za-z0-9.-]*\b")
_ACCOUNT_RE = re.compile(r"\b([A-Za-z0-9_.-]+(?:\\\\)+[A-Za-z0-9$_.-]+)\b")
_HOST_SAFE_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_MESSAGE_SECTION_HINTS = (
    "subject:",
    "member:",
    "group:",
    "new account:",
    "additional information:",
    "security id:",
    "account name:",
    "account domain:",
)
_GROUP_HINTS = {
    "administrators",
    "builtin\\administrators",
    "remote desktop users",
    "domain admins",
    "enterprise admins",
    "backup operators",
    "account operators",
    "server operators",
}
_CONCRETE_SIGNAL_TYPES = {"fqdn", "host", "ip", "user", "group", "domain", "process", "file", "hash", "registry", "email"}
_ROOT_ENTITY_PRIORITY = {
    "fqdn": 10,
    "host": 20,
    "user": 30,
    "group": 40,
    "ip": 50,
    "domain": 60,
    "process": 70,
    "file": 80,
    "registry": 90,
    "hash": 100,
    "tactic": 110,
    "technique": 120,
    "technique_id": 130,
    "signature_id": 140,
}
_SOURCE_PRIORITY = {
    "dest": 10,
    "dvc": 10,
    "dest_host": 10,
    "dest_ip": 10,
    "user": 15,
    "src_user": 15,
    "dest_user": 15,
    "src_ip": 20,
    "src": 20,
    "process_name": 25,
    "image": 25,
    "host": 80,
    "message": 90,
    "description": 95,
}

_FIELD_ENTITY_MAP = {
    "dest": ("host_or_ip", False),
    "host": ("host_or_ip", False),
    "dvc": ("host_or_ip", False),
    "dest_host": ("host_or_ip", False),
    "src": ("ip_or_host", False),
    "src_ip": ("ip", False),
    "dest_ip": ("ip", False),
    "ip": ("ip", False),
    "user": ("user", False),
    "src_user": ("user", False),
    "dest_user": ("user", False),
    "account_name": ("user", False),
    "subjectusername": ("user", False),
    "targetusername": ("user", False),
    "membername": ("user", False),
    "group_name": ("group", False),
    "group_domain": ("group_domain", False),
    "security_id": ("account_or_group", True),
    "signature": ("signature_name", False),
    "signature_id": ("signature_id", True),
    "eventcode": ("signature_id", True),
    "tactic": ("tactic", True),
    "technique": ("technique", True),
    "techid": ("technique_id", True),
    "process": ("process", False),
    "process_name": ("process", False),
    "image": ("process", False),
    "file_name": ("file", False),
    "filename": ("file", False),
    "file_path": ("file", False),
    "filepath": ("file", False),
    "sha256": ("hash", False),
    "sha1": ("hash", False),
    "md5": ("hash", False),
    "file_hash": ("hash", False),
    "registry_path": ("registry", False),
    "registry_key_name": ("registry", False),
    "targetobject": ("registry", False),
    "objectname": ("registry", False),
    "domain": ("domain", False),
    "query": ("domain", False),
    "url": ("domain_or_url", False),
    "uri": ("domain_or_url", False),
    "uri_path": ("domain_or_url", False),
}


def now():
    return int(time.time())


def safe_json(obj, max_len=12000):
    try:
        text = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    except Exception:
        text = json.dumps({"payload_unserializable": True})
    return text if len(text) <= max_len else text[:max_len] + "...(truncated)"


def first_non_empty(*values) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def truncate_text(value: str, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def is_meaningful_value(value) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    return text.lower() not in _EMPTY_SENTINELS


def clean_value(value) -> str:
    return str(value or "").strip()


def split_candidates(value, allow_commas: bool = False):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw_parts = [clean_value(v) for v in value]
    else:
        text = clean_value(value)
        if not text:
            return []
        separators = ["\n", ";", "|"]
        if allow_commas:
            separators.append(",")
        raw_parts = [text]
        for sep in separators:
            next_parts = []
            for part in raw_parts:
                next_parts.extend(part.split(sep))
            raw_parts = next_parts
    results = []
    for part in raw_parts:
        candidate = clean_value(part).strip('"').strip("'")
        if is_meaningful_value(candidate):
            results.append(candidate)
    return results


def normalize_entity(entity_type: str, value: str) -> str:
    entity_type = (entity_type or "unknown").lower().strip()
    text = clean_value(value)
    if entity_type in {
        "fqdn",
        "host",
        "ip",
        "user",
        "group",
        "domain",
        "hash",
        "email",
        "tactic",
        "technique",
        "technique_id",
        "signature_id",
    }:
        return text.lower()
    return text


def collapse_backslashes(value: str) -> str:
    return re.sub(r"\\{2,}", r"\\", clean_value(value))


def account_leaf(value: str) -> str:
    text = collapse_backslashes(value)
    if "\\" not in text:
        return text
    parts = [part for part in text.split("\\") if part]
    return parts[-1] if parts else text


def is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(clean_value(value))
        return True
    except Exception:
        return False


def classify_text_value(value: str) -> str:
    text = clean_value(value)
    if not text:
        return "unknown"
    if is_ip(text):
        return "ip"
    if text.startswith(("http://", "https://")):
        return "url"
    if _TECHNIQUE_ID_RE.fullmatch(text):
        return "technique_id"
    if re.fullmatch(r"[A-Fa-f0-9]{64}|[A-Fa-f0-9]{40}|[A-Fa-f0-9]{32}", text):
        return "hash"
    if "@" in text and " " not in text:
        return "email"
    if "." in text and " " not in text and "/" not in text:
        return "domain"
    return "unknown"


def safe_short_host(value: str) -> str:
    text = clean_value(value)
    if not text or not _HOST_SAFE_RE.fullmatch(text):
        return ""
    if "." not in text:
        return ""
    short = text.split(".", 1)[0].strip()
    if not short or not _HOST_SAFE_RE.fullmatch(short):
        return ""
    return short


def title_case_words(values):
    seen = set()
    results = []
    for value in values:
        text = clean_value(value)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append(text)
    return results


def limited_join(values, *, limit=3, chars=120):
    picked = []
    seen = set()
    for value in values:
        text = truncate_text(value, chars)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        picked.append(text)
        if len(picked) >= limit:
            break
    return ", ".join(picked)


def pick_owner(data: dict, configuration: dict, payload: dict) -> str:
    return first_non_empty(
        configuration.get("owner"),
        configuration.get("assignee"),
        configuration.get("assigned_to"),
        payload.get("owner"),
        payload.get("assignee"),
        payload.get("assigned_to"),
        data.get("owner"),
        data.get("user"),
        data.get("username"),
        data.get("userName"),
    )


def _get_splunkd_base_uri(data: dict) -> str:
    base = (
        data.get("server_uri")
        or data.get("serverUri")
        or os.environ.get("SPLUNKD_URI")
        or "https://127.0.0.1:8089"
    )
    return str(base).rstrip("/")


def _first_result_from_results_file(path: str) -> dict:
    path = clean_value(path)
    if not path or not os.path.exists(path):
        return {}
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, mode="rt", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            return {k: v for k, v in row.items() if k}
    return {}


def _extract_first_result(data: dict) -> dict:
    results = data.get("result") or data.get("results") or {}
    if isinstance(results, list) and results:
        return results[0] if isinstance(results[0], dict) else {}
    if isinstance(results, dict) and results:
        return results
    return _first_result_from_results_file(data.get("results_file") or data.get("resultsFile") or "")


def _pick_es_source_guid(payload: dict) -> str:
    for key in ("source_guid", "event_id", "rule_id"):
        value = clean_value(payload.get(key))
        if value:
            return value
    orig_sid = clean_value(payload.get("orig_sid"))
    orig_rid = clean_value(payload.get("orig_rid"))
    if orig_sid or orig_rid:
        return f"{orig_sid}:{orig_rid}"
    return ""


def _pick_detection_name(payload: dict) -> str:
    for key in ("rule_name", "rule_title", "search_name", "detection_name", "source"):
        value = clean_value(payload.get(key))
        if value:
            return value
    return ""


def _splunkd_request_json(session_key: str, splunkd_base_uri: str, path: str, method="GET", obj=None, timeout=30):
    url = splunkd_base_uri + path
    data_bytes = None
    headers = {
        "Authorization": f"Splunk {session_key}",
        "Accept": "application/json",
    }
    if method.upper() == "POST":
        headers["Content-Type"] = "application/json"
        data_bytes = json.dumps(obj or {}).encode("utf-8")
    req = urllib.request.Request(url=url, data=data_bytes, method=method.upper(), headers=headers)
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), body
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return int(exc.code), err_body
    except Exception as exc:
        raise RuntimeError(f"splunkd request failed: {exc}") from exc


def kv_get_by_key(session_key: str, splunkd_base_uri: str, collection: str, key: str):
    quoted = urllib.parse.quote(str(key), safe="")
    path = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{collection}/{quoted}?output_mode=json"
    status, body = _splunkd_request_json(session_key, splunkd_base_uri, path, method="GET")
    if status == 200 and body:
        try:
            return json.loads(body)
        except Exception:
            return None
    return None


def kv_upsert_by_key(session_key: str, splunkd_base_uri: str, collection: str, key: str, record: dict):
    key = str(key)
    record_with_key = dict(record or {})
    record_with_key["_key"] = key
    insert_path = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{collection}?output_mode=json"
    status, body = _splunkd_request_json(session_key, splunkd_base_uri, insert_path, method="POST", obj=record_with_key)
    if status in (200, 201):
        return status, body
    if status == 409:
        quoted = urllib.parse.quote(key, safe="")
        update_path = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{collection}/{quoted}?output_mode=json"
        status2, body2 = _splunkd_request_json(session_key, splunkd_base_uri, update_path, method="POST", obj=record)
        if status2 not in (200, 201):
            raise RuntimeError(
                f"KV update failed collection={collection} key={key} http={status2} body={body2[:500]}"
            )
        return status2, body2
    raise RuntimeError(f"KV upsert failed collection={collection} key={key} http={status} body={body[:500]}")


def _stable_root_seed_key(es_source_guid: str, hunt_id: str, entity_type: str, entity_value: str, detection_name: str) -> str:
    es_source_guid = clean_value(es_source_guid)
    if es_source_guid:
        return f"es_seed:{es_source_guid}"
    base = f"{hunt_id}|{entity_type}|{normalize_entity(entity_type, entity_value)}|{detection_name}"
    return "seed:" + hashlib.sha256(base.encode("utf-8")).hexdigest()


def _stable_entity_seed_key(notable_key: str, entity_type: str, entity_value: str, source_field: str) -> str:
    base = f"{notable_key}|{entity_type}|{normalize_entity(entity_type, entity_value)}|{clean_value(source_field).lower()}"
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
    return f"es_ctx:{digest[:24]}"


def _is_probable_group(value: str) -> bool:
    text = collapse_backslashes(value).lower()
    if not text:
        return False
    return text in _GROUP_HINTS or text.startswith("builtin\\")


def _principal_token_values(value: str):
    text = collapse_backslashes(value)
    return re.findall(r"[A-Za-z0-9_.-]+\\[A-Za-z0-9$_.-]+", text)


def _looks_like_windows_message_concat(value: str) -> bool:
    text = collapse_backslashes(value)
    lowered = text.lower()
    if any(marker in lowered for marker in _MESSAGE_SECTION_HINTS):
        return True
    principals = {collapse_backslashes(token).lower() for token in _principal_token_values(text)}
    if len(principals) > 1 and " " in text:
        return True
    if len(text) > 120 and text.count("\\") >= 2 and " " in text:
        return True
    return False


def _clean_group_signal_value(value: str) -> str:
    text = collapse_backslashes(value)
    if not text or _looks_like_windows_message_concat(text):
        return ""
    principals = {collapse_backslashes(token).lower() for token in _principal_token_values(text)}
    if len(principals) > 1:
        return ""
    if "\\" in text:
        if not _is_probable_group(text):
            return ""
        return account_leaf(text)
    if len(text) > 80:
        return ""
    return text


def _entity_record(entity_type: str, value: str, source_field: str, original_value: str):
    return {
        "entity_type": entity_type,
        "entity_value": clean_value(value),
        "normalized_value": normalize_entity(entity_type, value),
        "source_fields": [clean_value(source_field)] if clean_value(source_field) else [],
        "source_values": [clean_value(original_value)] if clean_value(original_value) else [],
        "source_rank": _SOURCE_PRIORITY.get(clean_value(source_field).lower(), 50),
    }


def _add_entity(entities_by_key: dict, entity_type: str, value: str, source_field: str, original_value: str):
    entity_type = clean_value(entity_type).lower()
    value = clean_value(value)
    source_field = clean_value(source_field)
    original_value = clean_value(original_value or value)
    if not entity_type or not value or not is_meaningful_value(value):
        return
    if entity_type == "user" and value.endswith("$"):
        return
    key = (entity_type, normalize_entity(entity_type, value))
    existing = entities_by_key.get(key)
    if existing:
        if source_field and source_field not in existing["source_fields"]:
            existing["source_fields"].append(source_field)
        if original_value and original_value not in existing["source_values"]:
            existing["source_values"].append(original_value)
        existing["source_rank"] = min(existing.get("source_rank", 50), _SOURCE_PRIORITY.get(source_field.lower(), 50))
        return
    entities_by_key[key] = _entity_record(entity_type, value, source_field, original_value)


def _derive_host_entities(value: str, source_field: str, entities_by_key: dict):
    text = clean_value(value)
    if not text:
        return
    if is_ip(text):
        _add_entity(entities_by_key, "ip", text, source_field, value)
        return
    short = safe_short_host(text)
    if short:
        _add_entity(entities_by_key, "fqdn", text, source_field, value)
        _add_entity(entities_by_key, "host", short, source_field, value)
        return
    if _HOST_SAFE_RE.fullmatch(text):
        _add_entity(entities_by_key, "host", text, source_field, value)


def _derive_domain_or_url(value: str, source_field: str, entities_by_key: dict):
    text = clean_value(value)
    if not text:
        return
    if text.startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse(text)
        if parsed.hostname:
            _add_entity(entities_by_key, "domain", parsed.hostname, source_field, value)
        return
    if "." in text and " " not in text:
        _add_entity(entities_by_key, "domain", text, source_field, value)


def _skip_full_process_value(raw_field: str, raw_value, candidate: str) -> bool:
    field = clean_value(raw_field).lower()
    text = clean_value(candidate)
    if field == "process_name":
        return False
    if isinstance(raw_value, (list, tuple, set)) and len(raw_value) > 1:
        return True
    lowered = text.lower()
    if len(text) > 180:
        return True
    if "-encodedcommand " in lowered or " -enc " in lowered or lowered.endswith(" -enc"):
        return True
    if re.search(r"[A-Za-z0-9+/=]{80,}", text):
        return True
    return False


def _preferred_asset_fields_present(payload: dict) -> bool:
    for key in ("dest", "dvc", "dest_host", "dest_ip", "src_ip", "ip", "src"):
        if is_meaningful_value(payload.get(key)):
            return True
    return False


def _extract_from_known_field(raw_field: str, raw_value, entities_by_key: dict, pending: dict, payload: dict):
    field = clean_value(raw_field).lower()
    if field not in _FIELD_ENTITY_MAP:
        return
    if field == "host" and _preferred_asset_fields_present(payload):
        return
    behavior, allow_commas = _FIELD_ENTITY_MAP[field]
    for candidate in split_candidates(raw_value, allow_commas=allow_commas):
        if behavior == "host_or_ip":
            _derive_host_entities(candidate, raw_field, entities_by_key)
        elif behavior == "ip_or_host":
            if is_ip(candidate):
                _add_entity(entities_by_key, "ip", candidate, raw_field, candidate)
            else:
                _derive_host_entities(candidate, raw_field, entities_by_key)
        elif behavior == "ip":
            if is_ip(candidate):
                _add_entity(entities_by_key, "ip", candidate, raw_field, candidate)
        elif behavior == "user":
            _add_entity(entities_by_key, "user", candidate, raw_field, candidate)
        elif behavior == "group":
            cleaned_group = _clean_group_signal_value(candidate)
            if cleaned_group:
                pending.setdefault("group_names", []).append(cleaned_group)
        elif behavior == "group_domain":
            pending.setdefault("group_domains", []).append(candidate)
        elif behavior == "account_or_group":
            collapsed = collapse_backslashes(candidate)
            if "\\" in collapsed and _is_probable_group(collapsed):
                cleaned_group = _clean_group_signal_value(collapsed)
                if cleaned_group:
                    pending.setdefault("group_names", []).append(cleaned_group)
            elif "\\" in collapsed:
                _add_entity(entities_by_key, "user", account_leaf(collapsed), raw_field, collapsed)
            elif candidate.startswith("S-1-"):
                continue
            else:
                _add_entity(entities_by_key, "user", candidate, raw_field, candidate)
        elif behavior == "signature_name":
            continue
        elif behavior == "signature_id":
            for match in _SIGNATURE_RE.findall(candidate):
                _add_entity(entities_by_key, "signature_id", match, raw_field, candidate)
        elif behavior == "tactic":
            _add_entity(entities_by_key, "tactic", candidate, raw_field, candidate)
        elif behavior == "technique":
            _add_entity(entities_by_key, "technique", candidate, raw_field, candidate)
        elif behavior == "technique_id":
            for match in _TECHNIQUE_ID_RE.findall(candidate):
                _add_entity(entities_by_key, "technique_id", match.upper(), raw_field, candidate)
        elif behavior == "process":
            if _skip_full_process_value(raw_field, raw_value, candidate):
                continue
            _add_entity(entities_by_key, "process", candidate, raw_field, candidate)
        elif behavior == "file":
            _add_entity(entities_by_key, "file", candidate, raw_field, candidate)
        elif behavior == "hash":
            _add_entity(entities_by_key, "hash", candidate, raw_field, candidate)
        elif behavior == "registry":
            _add_entity(entities_by_key, "registry", candidate, raw_field, candidate)
        elif behavior == "domain":
            _derive_domain_or_url(candidate, raw_field, entities_by_key)
        elif behavior == "domain_or_url":
            _derive_domain_or_url(candidate, raw_field, entities_by_key)


def _parse_message_context(payload: dict, entities_by_key: dict):
    raw_text = "\n".join(
        [
            clean_value(payload.get("Message")),
            clean_value(payload.get("message")),
            clean_value(payload.get("Description")),
            clean_value(payload.get("description")),
        ]
    ).strip()
    if not raw_text:
        return
    for ip_value in _IP_RE.findall(raw_text):
        if is_meaningful_value(ip_value):
            _add_entity(entities_by_key, "ip", ip_value, "Message", ip_value)
    for fqdn in _FQDN_RE.findall(raw_text):
        if is_ip(fqdn):
            continue
        _derive_host_entities(fqdn, "Message", entities_by_key)
    for account in _ACCOUNT_RE.findall(raw_text):
        collapsed = collapse_backslashes(account)
        if _is_probable_group(collapsed):
            cleaned_group = _clean_group_signal_value(collapsed)
            if cleaned_group:
                _add_entity(entities_by_key, "group", cleaned_group, "Message", collapsed)
        else:
            _add_entity(entities_by_key, "user", account_leaf(collapsed), "Message", collapsed)
    for technique_id in _TECHNIQUE_ID_RE.findall(raw_text):
        _add_entity(entities_by_key, "technique_id", technique_id.upper(), "Message", technique_id)
    signature_tokens = sorted({token for token in _SIGNATURE_RE.findall(raw_text) if token.startswith(("46", "47", "51"))})
    for token in signature_tokens[:8]:
        _add_entity(entities_by_key, "signature_id", token, "Message", token)


def extract_seed_entities(payload: dict):
    entities_by_key = {}
    pending = {}
    for field, value in payload.items():
        _extract_from_known_field(field, value, entities_by_key, pending, payload)

    group_domains = split_candidates(pending.get("group_domains", []), allow_commas=True)
    group_names = split_candidates(pending.get("group_names", []), allow_commas=True)
    if group_names:
        for group_name in group_names:
            _add_entity(entities_by_key, "group", group_name, "Group_Name", group_name)

    _parse_message_context(payload, entities_by_key)

    entities = list(entities_by_key.values())
    entities.sort(
        key=lambda entity: (
            _ROOT_ENTITY_PRIORITY.get(entity["entity_type"], 999),
            entity["normalized_value"],
        )
    )
    return entities


def seedable_entities(entities: list):
    return [entity for entity in entities if entity.get("entity_type") in _CONCRETE_SIGNAL_TYPES]


def build_root_context(payload: dict, entities: list, es_source_guid: str, es_detection_name: str):
    tactic_values = [entity["entity_value"] for entity in entities if entity["entity_type"] == "tactic"]
    technique_values = [entity["entity_value"] for entity in entities if entity["entity_type"] == "technique"]
    technique_id_values = [entity["entity_value"] for entity in entities if entity["entity_type"] == "technique_id"]
    signature_values = [entity["entity_value"] for entity in entities if entity["entity_type"] == "signature_id"]
    fqdn_values = [entity["entity_value"] for entity in entities if entity["entity_type"] == "fqdn"]
    host_values = [entity["entity_value"] for entity in entities if entity["entity_type"] == "host"]
    user_values = [entity["entity_value"] for entity in entities if entity["entity_type"] == "user"]
    group_values = [entity["entity_value"] for entity in entities if entity["entity_type"] == "group"]
    ip_values = [entity["entity_value"] for entity in entities if entity["entity_type"] == "ip"]
    group_context_values = []
    group_name = first_non_empty(payload.get("Group_Name"), payload.get("group_name"))
    group_domain = first_non_empty(payload.get("Group_Domain"), payload.get("group_domain"))
    if group_name:
        group_context_values.append(group_name)
        if group_domain and "\\" not in group_name:
            group_context_values.append(f"{group_domain}\\{group_name}")
    for candidate in split_candidates(payload.get("Security_ID"), allow_commas=True):
        collapsed = collapse_backslashes(candidate)
        if not collapsed or _looks_like_windows_message_concat(collapsed):
            continue
        principals = {collapse_backslashes(token).lower() for token in _principal_token_values(collapsed)}
        if len(principals) > 1:
            continue
        if _is_probable_group(collapsed):
            group_context_values.append(collapsed)

    context = {
        "search_name": first_non_empty(es_detection_name, payload.get("search_name"), payload.get("rule_name"), payload.get("rule_title")),
        "rule_name": first_non_empty(payload.get("rule_name"), payload.get("rule_title")),
        "description": truncate_text(first_non_empty(payload.get("Description"), payload.get("description")), 320),
        "message": truncate_text(first_non_empty(payload.get("Message"), payload.get("message")), 480),
        "tactic": tactic_values[0] if tactic_values else "",
        "technique": technique_values[0] if technique_values else "",
        "technique_id": technique_id_values[0] if technique_id_values else "",
        "signature_ids": signature_values[:8],
        "notable_time": first_non_empty(payload.get("orig_time"), payload.get("_time"), payload.get("time")),
        "dest": first_non_empty(
            payload.get("dest"),
            payload.get("dest_ip"),
            payload.get("src_ip"),
            payload.get("ip"),
            payload.get("host"),
            payload.get("dvc"),
        ),
        "hosts": title_case_words(fqdn_values + host_values)[:6],
        "users": title_case_words(user_values)[:8],
        "groups": title_case_words(group_values)[:6],
        "group_context": title_case_words(group_context_values)[:6],
        "ips": title_case_words(ip_values)[:8],
        "source_guid": clean_value(es_source_guid),
        "finding_id": first_non_empty(payload.get("finding_id"), payload.get("event_id"), payload.get("rule_id")),
        "orig_sid": clean_value(payload.get("orig_sid")),
        "orig_rid": clean_value(payload.get("orig_rid")),
    }
    context["summary"] = build_context_summary(context)
    return context


def build_context_summary(context: dict) -> str:
    parts = []
    if context.get("search_name"):
        parts.append(context["search_name"])
    if context.get("technique"):
        technique_part = context["technique"]
        if context.get("technique_id"):
            technique_part += f" ({context['technique_id']})"
        parts.append(technique_part)
    elif context.get("technique_id"):
        parts.append(context["technique_id"])
    if context.get("tactic"):
        parts.append(f"Tactic: {context['tactic']}")
    if context.get("hosts"):
        parts.append(f"Hosts: {limited_join(context['hosts'], limit=2, chars=80)}")
    if context.get("users"):
        parts.append(f"Users: {limited_join(context['users'], limit=3, chars=48)}")
    if context.get("groups"):
        parts.append(f"Groups: {limited_join(context['groups'], limit=2, chars=60)}")
    if context.get("signature_ids"):
        parts.append(f"Event IDs: {', '.join(context['signature_ids'][:4])}")
    if context.get("description"):
        parts.append(truncate_text(context["description"], 140))
    elif context.get("message"):
        parts.append(truncate_text(context["message"], 140))
    return " | ".join(part for part in parts if part)


def choose_root_entity(entities: list):
    if not entities:
        return {
            "entity_type": "unknown",
            "entity_value": "unknown",
            "normalized_value": "unknown",
            "source_fields": [],
            "source_values": [],
        }
    return min(
        entities,
        key=lambda entity: (
            _ROOT_ENTITY_PRIORITY.get(entity["entity_type"], 999),
            entity.get("source_rank", 50),
            entity["normalized_value"],
        ),
    )


def _entity_title(entity: dict, detection_name: str) -> str:
    value = entity["entity_value"]
    label = entity["entity_type"].replace("_", " ")
    prefix = "ES Seed" if entity.get("root_signal") else "ES Context"
    if detection_name:
        return f"{prefix}: {detection_name} [{label}: {value}]"
    return f"{prefix}: {label} {value}"


def _entity_description(entity: dict, context: dict) -> str:
    source_fields = ", ".join(entity.get("source_fields") or [])
    detail = f"Seeded from Enterprise Security as {entity['entity_type']}={entity['entity_value']}."
    if source_fields:
        detail += f" Source fields: {source_fields}."
    if context.get("summary"):
        detail += " " + truncate_text(context["summary"], 220)
    return truncate_text(detail, 420)


def _build_signal_doc(
    *,
    signal_id: str,
    hunt_id: str,
    owner: str,
    created_time: int,
    entity: dict,
    detection_name: str,
    payload: dict,
    root_context: dict,
    es_source_guid: str,
    es_severity: str,
    es_urgency: str,
    es_link: str,
    content_hash: str,
    is_root: bool,
):
    source_fields = entity.get("source_fields") or []
    source_values = entity.get("source_values") or []
    signal_doc = {
        "signal_id": signal_id,
        "signal": entity["entity_value"],
        "signal_type": "es_seed" if is_root else "es_context",
        "entity_type": entity["entity_type"],
        "entity_value": entity["entity_value"],
        "entity_normalized": entity["normalized_value"],
        "hunt_id": hunt_id,
        "owner": owner,
        "parent_signal_id": "",
        "root_signal": 1 if is_root else 0,
        "field": source_fields[0] if source_fields else "",
        "value": source_values[0] if source_values else entity["entity_value"],
        "source_field": source_fields[0] if source_fields else "",
        "entity_sources_json": safe_json(source_fields, max_len=512),
        "category": first_non_empty(root_context.get("tactic"), payload.get("category")),
        "confidence": "medium" if entity["entity_type"] in {"fqdn", "host", "user", "group", "technique_id", "signature_id"} else "low",
        "status": "open",
        "title": _entity_title({**entity, "root_signal": is_root}, detection_name),
        "description": _entity_description(entity, root_context),
        "signal_source": "Enterprise Security",
        "page_url": "",
        "view": "",
        "earliest": "",
        "latest": "",
        "es_source_guid": es_source_guid,
        "es_detection_name": detection_name,
        "es_severity": es_severity,
        "es_urgency": es_urgency,
        "es_link": es_link,
        "es_payload_json": safe_json(payload),
        "es_context_json": safe_json(root_context, max_len=3000),
        "notable_context_summary": root_context.get("summary", ""),
        "tactic": root_context.get("tactic", ""),
        "technique": root_context.get("technique", ""),
        "technique_id": root_context.get("technique_id", ""),
        "signature_id": ",".join(root_context.get("signature_ids") or []),
        "created_time": created_time,
        "created_by": owner,
        "updated_time": created_time,
        "updated_by": owner,
        "content_hash": content_hash,
        "app_managed": 1,
        "app_version": APP_VERSION,
        "user_modified": 0,
    }
    return signal_doc


def build_hunt_doc(existing_hunt, *, hunt_id: str, owner: str, created_time: int, detection_name: str, es_source_guid: str, es_severity: str, es_urgency: str, es_link: str, root_entity: dict, root_context: dict, signal_count: int, entity_count: int):
    hunt_title = detection_name or f"Hunt ({root_entity['entity_type']}:{root_entity['entity_value']})"
    if root_entity["entity_type"] != "unknown":
        hunt_title = f"{hunt_title} [{root_entity['entity_type']}: {root_entity['entity_value']}]"

    if existing_hunt:
        hunt_doc = dict(existing_hunt)
        hunt_doc["updated_time"] = created_time
        hunt_doc["updated_by"] = first_non_empty(owner, hunt_doc.get("updated_by"))
        hunt_doc["owner"] = first_non_empty(hunt_doc.get("owner"), owner)
        hunt_doc["last_activity_time"] = created_time
        hunt_doc["signal_count"] = max(int(hunt_doc.get("signal_count") or 0), signal_count)
        hunt_doc["entity_count"] = max(int(hunt_doc.get("entity_count") or 0), entity_count)
        if not hunt_doc.get("title"):
            hunt_doc["title"] = hunt_title
        if not hunt_doc.get("description"):
            hunt_doc["description"] = root_context.get("summary", "")
        if es_source_guid and not hunt_doc.get("es_source_guid"):
            hunt_doc["es_source_guid"] = es_source_guid
        if detection_name and not hunt_doc.get("es_detection_name"):
            hunt_doc["es_detection_name"] = detection_name
        if es_severity and not hunt_doc.get("es_severity"):
            hunt_doc["es_severity"] = es_severity
        if es_urgency and not hunt_doc.get("es_urgency"):
            hunt_doc["es_urgency"] = es_urgency
    else:
        hunt_doc = {
            "hunt_id": hunt_id,
            "origin": "es" if es_source_guid else "falconer",
            "owner": owner,
            "status": "open",
            "title": hunt_title,
            "description": root_context.get("summary", ""),
            "es_source_guid": es_source_guid,
            "es_detection_name": detection_name,
            "es_severity": es_severity,
            "es_urgency": es_urgency,
            "es_link": es_link,
            "created_time": created_time,
            "created_by": owner,
            "updated_time": created_time,
            "updated_by": owner,
            "last_activity_time": created_time,
            "signal_count": signal_count,
            "entity_count": entity_count,
            "app_managed": 1,
            "app_version": APP_VERSION,
            "user_modified": 0,
        }

    hunt_doc["es_context_json"] = safe_json(root_context, max_len=3000)
    hunt_doc["notable_context_summary"] = root_context.get("summary", "")
    hunt_doc["tactic"] = root_context.get("tactic", "")
    hunt_doc["technique"] = root_context.get("technique", "")
    hunt_doc["technique_id"] = root_context.get("technique_id", "")
    hunt_doc["signature_id"] = ",".join(root_context.get("signature_ids") or [])
    hunt_doc["content_hash"] = hashlib.sha256(
        f"{hunt_id}|{hunt_doc.get('signal_count', 0)}|{hunt_doc.get('entity_count', 0)}|{hunt_doc.get('last_activity_time', created_time)}".encode("utf-8")
    ).hexdigest()[:24]
    return hunt_doc


def load_existing_hunt_signals(session_key: str, splunkd_base_uri: str, hunt_id: str):
    query = json.dumps({"hunt_id": hunt_id})
    path = (
        f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{SIGNALS_COLLECTION}"
        f"?query={urllib.parse.quote(query, safe='')}&output_mode=json"
    )
    status, body = _splunkd_request_json(session_key, splunkd_base_uri, path, method="GET")
    if status != 200 or not body:
        return []
    try:
        rows = json.loads(body)
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


def seed_hunt_from_payload(session_key: str, splunkd_base_uri: str, payload: dict, owner: str, created_time: int):
    es_source_guid = _pick_es_source_guid(payload)
    es_detection_name = _pick_detection_name(payload)
    es_severity = clean_value(payload.get("severity"))
    es_urgency = clean_value(payload.get("urgency"))
    es_link = first_non_empty(payload.get("notable_url"), payload.get("link"), payload.get("es_link"))
    hunt_id = es_source_guid if es_source_guid else str(uuid.uuid4())

    extracted_entities = extract_seed_entities(payload)
    root_context = build_root_context(payload, extracted_entities, es_source_guid, es_detection_name)
    concrete_entities = seedable_entities(extracted_entities)
    root_entity = choose_root_entity(concrete_entities or extracted_entities)

    if not concrete_entities and root_entity["entity_type"] in _CONCRETE_SIGNAL_TYPES:
        concrete_entities = [root_entity]
    elif not concrete_entities:
        concrete_entities = []

    root_key = _stable_root_seed_key(es_source_guid, hunt_id, root_entity["entity_type"], root_entity["entity_value"], es_detection_name)
    notable_key = es_source_guid or f"{hunt_id}:{first_non_empty(payload.get('orig_sid'), payload.get('orig_rid'), es_detection_name)}"

    signal_plan = []
    used_keys = set()
    for entity in concrete_entities:
        is_root = entity["entity_type"] == root_entity["entity_type"] and entity["normalized_value"] == root_entity["normalized_value"]
        key = root_key if is_root else _stable_entity_seed_key(notable_key, entity["entity_type"], entity["entity_value"], ",".join(entity.get("source_fields") or []))
        if key in used_keys:
            continue
        used_keys.add(key)
        signal_plan.append((key, entity, is_root))

    existing_rows = load_existing_hunt_signals(session_key, splunkd_base_uri, hunt_id)
    existing_by_key = {str(row.get("_key") or ""): row for row in existing_rows if row.get("_key")}
    existing_entity_keys = {
        (clean_value(row.get("entity_type")).lower(), normalize_entity(clean_value(row.get("entity_type")), row.get("entity_value")))
        for row in existing_rows
        if clean_value(row.get("entity_type")) and clean_value(row.get("entity_value"))
    }

    created_signal_ids = []
    root_signal_id = clean_value(existing_by_key.get(root_key, {}).get("signal_id"))
    for key, entity, is_root in signal_plan:
        existing_signal = existing_by_key.get(key)
        if existing_signal:
            signal_id = clean_value(existing_signal.get("signal_id")) or str(uuid.uuid4())
        else:
            signal_id = str(uuid.uuid4())
        signal_doc = _build_signal_doc(
            signal_id=signal_id,
            hunt_id=hunt_id,
            owner=owner,
            created_time=created_time,
            entity=entity,
            detection_name=es_detection_name,
            payload=payload,
            root_context=root_context,
            es_source_guid=es_source_guid,
            es_severity=es_severity,
            es_urgency=es_urgency,
            es_link=es_link,
            content_hash=key,
            is_root=is_root,
        )
        if existing_signal:
            signal_doc["created_time"] = existing_signal.get("created_time", created_time)
            signal_doc["created_by"] = existing_signal.get("created_by", owner)
        kv_upsert_by_key(session_key, splunkd_base_uri, SIGNALS_COLLECTION, key, signal_doc)
        if is_root:
            root_signal_id = signal_id
        if not existing_signal:
            created_signal_ids.append(signal_id)
        existing_entity_keys.add((entity["entity_type"], entity["normalized_value"]))

    signal_count = len(existing_rows) + len(created_signal_ids)
    entity_count = len(existing_entity_keys)
    existing_hunt = kv_get_by_key(session_key, splunkd_base_uri, HUNTS_COLLECTION, hunt_id)
    hunt_doc = build_hunt_doc(
        existing_hunt,
        hunt_id=hunt_id,
        owner=owner,
        created_time=created_time,
        detection_name=es_detection_name,
        es_source_guid=es_source_guid,
        es_severity=es_severity,
        es_urgency=es_urgency,
        es_link=es_link,
        root_entity=root_entity,
        root_context=root_context,
        signal_count=signal_count,
        entity_count=entity_count,
    )
    kv_upsert_by_key(session_key, splunkd_base_uri, HUNTS_COLLECTION, hunt_id, hunt_doc)
    return {
        "hunt_id": hunt_id,
        "root_signal_id": root_signal_id,
        "root_entity_type": root_entity["entity_type"],
        "root_entity_value": root_entity["entity_value"],
        "signal_count": signal_count,
        "entity_count": entity_count,
        "created_signal_count": len(created_signal_ids),
        "seeded_entities": [
            {
                "entity_type": entity["entity_type"],
                "entity_value": entity["entity_value"],
                "source_fields": entity.get("source_fields") or [],
            }
            for _, entity, _ in signal_plan
        ],
        "root_context": root_context,
    }


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        print("No input received on stdin", file=sys.stderr)
        return 2
    data = json.loads(raw)
    session_key = data.get("session_key") or data.get("sessionKey")
    if not session_key:
        print("Missing session_key in payload", file=sys.stderr)
        return 2
    splunkd_base_uri = _get_splunkd_base_uri(data)
    configuration = data.get("configuration") or {}
    payload = _extract_first_result(data)
    created_time = now()
    owner = pick_owner(data, configuration, payload)
    if not payload:
        print("No result supplied in payload or results_file; nothing to seed", file=sys.stderr)
        return 0

    result = seed_hunt_from_payload(
        session_key=session_key,
        splunkd_base_uri=splunkd_base_uri,
        payload=payload,
        owner=owner,
        created_time=created_time,
    )
    print(
        json.dumps(
            {
                "status": "success",
                "hunt_id": result["hunt_id"],
                "signal_id": result["root_signal_id"],
                "entity_type": result["root_entity_type"],
                "entity_value": result["root_entity_value"],
                "signal_count": result["signal_count"],
                "entity_count": result["entity_count"],
                "created_signal_count": result["created_signal_count"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
