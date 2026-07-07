#!/usr/bin/env python3
import json
import time
import uuid
import re

import splunk.rest as rest

_IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

def _now():
    return int(time.time())

def _safe_json_dumps(obj, max_len=50000):
    try:
        s = json.dumps(obj, ensure_ascii=False)
    except Exception:
        s = json.dumps({"payload_unserializable": True})
    if len(s) > max_len:
        return s[:max_len] + "...(truncated)"
    return s

def _infer_entity_type(v: str) -> str:
    v = (v or "").strip()
    if not v:
        return "unknown"
    if _IPV4_RE.match(v):
        return "ip"
    if v.startswith("http://") or v.startswith("https://"):
        return "url"
    if re.fullmatch(r"[A-Fa-f0-9]{64}", v) or re.fullmatch(r"[A-Fa-f0-9]{40}", v) or re.fullmatch(r"[A-Fa-f0-9]{32}", v):
        return "hash"
    if "." in v and " " not in v and "/" not in v:
        return "domain"
    return "unknown"

def _pick_primary_entity(payload: dict):
    priority = [
        "risk_object",
        "dest_ip", "src_ip",
        "dest", "src",
        "host", "dest_host", "src_host",
        "user", "src_user", "dest_user",
        "process_name", "process", "parent_process",
        "url", "uri", "domain",
        "file_hash", "sha256", "md5",
    ]
    for k in priority:
        val = payload.get(k)
        if val is None:
            continue
        if isinstance(val, (list, tuple)):
            val = next((x for x in val if x), None)
        if val is None:
            continue
        sval = str(val).strip()
        if sval:
            return _infer_entity_type(sval), sval
    return "unknown", "unknown"

def process_event(helper, *args, **kwargs):
    """
    helper: CIM Modular Action helper.
    - helper.get_session_key()
    - helper.get_param()
    - helper.get_events()
    """
    session_key = helper.get_session_key()

    # For payload_format=json, CIM helper gives you event dicts
    events = helper.get_events() or []
    # We’ll create ONE signal per invocation; use the first event as payload anchor.
    payload = events[0] if events else {}

    signal_id = str(uuid.uuid4())
    created_time = _now()

    es_source_guid = str(payload.get("source_guid", "") or "").strip()
    es_detection_name = str(payload.get("rule_name", payload.get("detection_name", "")) or "").strip()
    es_severity = str(payload.get("severity", "") or "").strip()
    es_urgency = str(payload.get("urgency", "") or "").strip()

    entity_type, entity_value = _pick_primary_entity(payload)

    # Grouping rule: if source_guid present, it IS the group/thread id.
    group_id = es_source_guid
    group_origin = "es" if es_source_guid else "falconer"

    record = {
        "signal_id": signal_id,
        "signal_type": "es_seed",
        "entity_type": entity_type,
        "entity_value": entity_value,
        "category": str(payload.get("category", "") or ""),
        "confidence": "low",
        "status": "open",
        "title": f"ES Seed: {es_detection_name}" if es_detection_name else "ES Seed Signal",
        "description": f"Seeded from ES. source_guid={es_source_guid}" if es_source_guid else "Seeded from ES.",
        "created_time": created_time,
        "created_by": helper.get_user() if hasattr(helper, "get_user") else "",
        "updated_time": created_time,
        "updated_by": helper.get_user() if hasattr(helper, "get_user") else "",

        "group_id": group_id,
        "group_origin": group_origin,
        "root_signal": 1,

        "es_source_guid": es_source_guid,
        "es_detection_name": es_detection_name,
        "es_severity": es_severity,
        "es_urgency": es_urgency,
        "es_payload_json": _safe_json_dumps(payload),

        "app_managed": 1,
        "app_version": "vNext",
        "user_modified": 0,
    }

    # KVStore write
    url = "/servicesNS/nobody/apt-falconer/storage/collections/data/falconer_signals"
    rest.simpleRequest(
        url,
        sessionKey=session_key,
        method="POST",
        postargs={"data": json.dumps(record)},
        raiseAllErrors=True
    )

    helper.log_info(f"[Falconer] Seeded signal_id={signal_id} group_id={group_id} entity={entity_type}:{entity_value}")

