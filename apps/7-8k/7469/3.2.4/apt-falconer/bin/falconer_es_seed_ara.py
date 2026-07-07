#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import uuid
import re

import splunk
import splunk.rest as rest

# ----------------------------
# Helpers
# ----------------------------

_IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
# quick/lenient v6 check (good enough for entity classification)
_IPV6_RE = re.compile(r"^[0-9a-fA-F:]+$")

def _now():
    return int(time.time())

def _safe_json_dumps(obj, max_len=50000):
    """
    Store raw payload for debugging/future refinement, but cap size.
    """
    try:
        s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        s = json.dumps({"payload_unserializable": True}, separators=(",", ":"))
    if len(s) > max_len:
        return s[:max_len] + "...(truncated)"
    return s

def _infer_entity_type(value: str) -> str:
    if not value:
        return "unknown"
    v = value.strip()

    # IPv4 basic check
    if _IPV4_RE.match(v):
        return "ip"

    # IPv6 basic check (avoid classifying timestamps/guids by requiring ':')
    if ":" in v and _IPV6_RE.match(v):
        return "ip"

    # URL-ish
    if v.startswith("http://") or v.startswith("https://"):
        return "url"

    # hash-ish (very rough)
    if re.fullmatch(r"[A-Fa-f0-9]{32}", v):
        return "hash"
    if re.fullmatch(r"[A-Fa-f0-9]{40}", v):
        return "hash"
    if re.fullmatch(r"[A-Fa-f0-9]{64}", v):
        return "hash"

    # domain-ish
    if "." in v and " " not in v and "/" not in v and len(v) <= 253:
        return "domain"

    # default
    return "unknown"

def _pick_primary_entity(payload: dict) -> (str, str):
    """
    Deterministic extraction: first match wins.
    """
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
            # pick first non-empty
            val = next((x for x in val if x), None)
        if val is None:
            continue
        sval = str(val).strip()
        if sval:
            return _infer_entity_type(sval), sval

    return "unknown", "unknown"

def _get_first(payload: dict, keys):
    for k in keys:
        v = payload.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""

# ----------------------------
# Adaptive Response entrypoint
# ----------------------------

def process(event, session_key, **kwargs):
    """
    Splunk ES Adaptive Response Framework entry point.
    ES passes a dict-like payload ('event') and the current session_key.
    """
    created_time = _now()
    signal_id = str(uuid.uuid4())

    payload = event if isinstance(event, dict) else {"raw_event": str(event)}

    # ES linkage fields (best effort)
    es_source_guid = _get_first(payload, ["source_guid", "es_source_guid"])
    es_detection_name = _get_first(payload, ["rule_name", "detection_name", "search_name", "name"])
    es_severity = _get_first(payload, ["severity", "es_severity"])
    es_urgency = _get_first(payload, ["urgency", "es_urgency"])
    es_link = _get_first(payload, ["notable_url", "link", "es_link"])

    entity_type, entity_value = _pick_primary_entity(payload)

    # Grouping rule:
    # If ES provides source_guid, use it as group_id so all related signals can thread together.
    group_origin = "es" if es_source_guid else "falconer"
    group_id = es_source_guid if es_source_guid else ""  # leave blank for now if not present
    root_signal = 1  # this is the seed record

    title = f"ES Seed: {es_detection_name}" if es_detection_name else "ES Seed Signal"
    desc_bits = []
    if es_detection_name:
        desc_bits.append(f"Seeded from ES detection '{es_detection_name}'.")
    if es_source_guid:
        desc_bits.append(f"source_guid={es_source_guid}.")
    if entity_value and entity_value != "unknown":
        desc_bits.append(f"Primary entity: {entity_type}={entity_value}.")
    description = " ".join(desc_bits) if desc_bits else "Seeded from ES via Adaptive Response Action."

    record = {
        "signal_id": signal_id,
        "signal_type": "es_seed",
        "entity_type": entity_type,
        "entity_value": entity_value,
        "category": payload.get("category", "") or "",
        "confidence": "low",
        "status": "open",
        "title": title,
        "description": description,

        "created_time": created_time,
        "created_by": payload.get("user", "") or payload.get("created_by", "") or "",

        "updated_time": created_time,
        "updated_by": payload.get("user", "") or payload.get("updated_by", "") or "",

        "group_id": group_id,
        "group_origin": group_origin,
        "root_signal": root_signal,

        "es_source_guid": es_source_guid,
        "es_detection_name": es_detection_name,
        "es_severity": es_severity,
        "es_urgency": es_urgency,
        "es_link": es_link,
        "es_payload_json": _safe_json_dumps(payload),
        "app_managed": 1,
        "app_version": "vNext",
        "user_modified": 0,
    }

    # Write to KVStore collection falconer_signals
    # Endpoint: /servicesNS/nobody/<app>/storage/collections/data/<collection>
    app = kwargs.get("app", "apt-falconer")
    url = f"/servicesNS/nobody/{app}/storage/collections/data/falconer_signals"

    try:
        # POST record to KVStore
        rest.simpleRequest(
            url,
            sessionKey=session_key,
            method="POST",
            postargs={"data": json.dumps(record)},
            raiseAllErrors=True
        )
        return {"status": "success", "signal_id": signal_id, "group_id": group_id}
    except Exception as e:
        return {"status": "error", "message": str(e), "signal_id": signal_id}

