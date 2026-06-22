# -*- coding: utf-8 -*-
"""
VSP 360 Configuration Modular Input (Splunk Add-on Builder).

- Collects configuration (scalar) metrics from VSP 360 via dbapi.do?action=query
- Emits ONE event per (signature, attribute_name)
- Uses VSP 360 query window endTime as Splunk _time (snapshot-as-of semantics)
- Null-fills missing schema attributes for consistent Splunk field coverage
- Caches array identity (storage_name, storage_model) from raidStorage and injects into all events
- Checkpointed window per resource_type per stanza
- 60s micro-guard against rapid duplicate scheduler triggers

Sourcetype: hitachi:vspblock:config
"""

import json
import time
from typing import Any, Dict, Optional

from vsp360_common import (
    b,
    VSP360Client,
    stanza_name,
    chunk_list,
    mql_for,
    parse_signature,
    format_csad_time,
    parse_csad_time,
    unwrap_scalar,
    vsp360_host_label,
    normalize_utc_offset,
)
from vsp360_schema import CONFIG_ATTRS as ATTRS

_DUPLICATE_GUARD_SEC = 60


def validate_input(helper, definition):
    params = definition.parameters
    collect_all = b(params.get("collect_all_resource_types"), True)
    resource_types = (params.get("resource_types_csv") or "").strip()
    if not collect_all and not resource_types:
        raise ValueError("Either set collect_all_resource_types=true or provide resource_types_csv.")

    v = (params.get("max_attributes_per_request") or "").strip()
    if v:
        int(v)

    lb = (params.get("lookback_minutes") or "").strip()
    if lb:
        int(lb)

    return True


def collect_events(helper, ew):
    base_url_raw = (helper.get_global_setting("vsp360_base_url") or "").strip()
    vsp360_host = vsp360_host_label(base_url_raw)
    client_id = (helper.get_global_setting("client_id") or "").strip()
    client_secret = (helper.get_global_setting("client_secret") or "").strip()
    realm = (helper.get_global_setting("realm") or "vsp360").strip()
    dataset = (helper.get_global_setting("dataset") or "defaultDs").strip()

    timeout = int(helper.get_global_setting("timeout_seconds") or 90)
    process_sync = b(helper.get_global_setting("process_sync"), True)

    utc_offset_raw = (helper.get_global_setting("utc_offset") or "").strip() or None
    utc_offset = None
    if utc_offset_raw:
        utc_offset = normalize_utc_offset(utc_offset_raw)
        if utc_offset != utc_offset_raw.strip():
            helper.log_warning(f"utc_offset reformatted: '{utc_offset_raw}' -> '{utc_offset}'.")

    if not base_url_raw or not client_id or not client_secret:
        helper.log_error("Missing required global settings: vsp360_base_url, client_id, client_secret.")
        return

    collect_all = b(helper.get_arg("collect_all_resource_types"), True)
    resource_types_csv = (helper.get_arg("resource_types_csv") or "").strip()
    max_attrs = int(helper.get_arg("max_attributes_per_request") or 25)
    lookback_minutes = int(helper.get_arg("lookback_minutes") or 60)
    if lookback_minutes <= 0:
        lookback_minutes = 60

    stanza = stanza_name(helper)

    if collect_all:
        resource_types = sorted(list(ATTRS.keys()))
    else:
        resource_types = [x.strip() for x in resource_types_csv.split(",") if x.strip()]

    if "raidStorage" in resource_types:
        resource_types = ["raidStorage"] + [rt for rt in resource_types if rt != "raidStorage"]

    client = VSP360Client(base_url_raw, realm, dataset, client_id, client_secret, timeout)
    try:
        now_epoch = int(time.time())
        end_time = format_csad_time(now_epoch, utc_offset)
        end_epoch = parse_csad_time(end_time, utc_offset)

        COMMON_LABELS: Dict[str, Dict[str, Any]] = {}
        total_events = 0

        for rt in resource_types:
            if rt not in ATTRS:
                helper.log_warning(f"Unknown resource_type '{rt}' (not in embedded schema); skipping.")
                continue

            cp_key = f"configuration::{stanza}::{rt}"
            cp = helper.get_check_point(cp_key) or {}

            last_run_epoch = int(cp.get("last_run_epoch", 0) or 0)
            if last_run_epoch and (now_epoch - last_run_epoch) < _DUPLICATE_GUARD_SEC:
                helper.log_info(
                    f"Skipping {rt}: last run {now_epoch - last_run_epoch}s ago "
                    f"(<{_DUPLICATE_GUARD_SEC}s duplicate guard)."
                )
                continue

            start_time = cp.get("last_end_time")
            if not start_time:
                start_epoch = now_epoch - (lookback_minutes * 60)
                start_time = format_csad_time(start_epoch, utc_offset)

            attrs = sorted(list(set(ATTRS.get(rt) or [])))
            chunks = chunk_list(attrs, max_attrs)

            merged: Dict[str, Dict[str, Any]] = {}
            helper.log_info(
                f"Collecting config {rt}: attrs={len(attrs)} chunks={len(chunks)} "
                f"window={start_time}->{end_time}"
            )

            for ch in chunks:
                try:
                    mql = mql_for("configuration", rt, ch)
                    resp = client.query(
                        mql,
                        start_time,
                        end_time,
                        process_sync=process_sync,
                        utc_offset=utc_offset,
                    )

                    results = resp.get("result") or []
                    if not results:
                        helper.log_warning(f"No results returned for configuration {rt} chunk (attrs={len(ch)})")

                    for item in results:
                        sig = item.get("signature")
                        if not sig:
                            continue
                        merged.setdefault(sig, {"signature": sig})
                        for attr, val in item.items():
                            if attr == "signature":
                                continue
                            merged[sig][attr] = val
                except Exception as e:
                    helper.log_error(f"Chunk failed for configuration {rt} (attrs={len(ch)}): {e}")
                    continue

            expected_attrs = set(ATTRS.get(rt) or [])
            emitted = 0

            for raw_sig, obj in merged.items():
                serial, inst = parse_signature(raw_sig)

                emit_sig = raw_sig.replace("^", ":") if isinstance(raw_sig, str) else raw_sig
                emit_inst = inst.replace("^", ":") if isinstance(inst, str) else inst

                if rt == "raidStorage" and serial:
                    n_val, _, _ = unwrap_scalar(obj.get("name"), numeric_coerce=False)
                    m_val, _, _ = unwrap_scalar(obj.get("modelName"), numeric_coerce=False)
                    COMMON_LABELS[serial] = {
                        "storage_name": n_val,
                        "storage_model": m_val,
                    }

                labels = COMMON_LABELS.get(serial) or {}

                for attr in sorted(expected_attrs):
                    raw_val = obj.get(attr)
                    data, attr_name, unit = unwrap_scalar(raw_val, numeric_coerce=False) if raw_val is not None else (None, None, None)

                    out = {
                        "category": "configuration",
                        "resource_type": rt,
                        "attribute_name": attr,
                        "value": data,
                        "unit": unit,
                        "signature": emit_sig,
                        "storage_serial": serial,
                        "instance_id": emit_inst,
                        "collection_time": end_time,
                        "vsp360_host": vsp360_host,
                        "storage_name": labels.get("storage_name"),
                        "storage_model": labels.get("storage_model"),
                    }

                    event = helper.new_event(
                        source=vsp360_host,
                        index=helper.get_output_index(),
                        sourcetype="hitachi:vspblock:config",
                        time=end_epoch,
                        data=json.dumps(out),
                    )
                    ew.write_event(event)
                    emitted += 1

            total_events += emitted
            helper.log_info(f"Emitted {emitted} config events for {rt}")

            if emitted > 0:
                helper.save_check_point(cp_key, {"last_end_time": end_time, "last_run_epoch": now_epoch})
                helper.log_info(
                    f"Config checkpoint saved {cp_key} last_end_time={end_time} last_run_epoch={now_epoch}"
                )
            else:
                helper.log_warning(
                    f"Not checkpointing {rt} because 0 events were emitted (will retry next run)."
                )

        helper.log_info(f"Total config events emitted this run: {total_events}")

    finally:
        client.close()