#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import hashlib
import json
import re
import time
import logging
from trackme_libs_logging import get_effective_logger

# import TrackMe splk-feeds libs
from trackme_libs_splk_feeds import (
    splk_dsm_return_entity_info,
    splk_dsm_return_elastic_info,
    splk_dsm_return_searches,
    splk_dhm_return_entity_info,
    splk_dhm_return_searches,
    splk_mhm_return_entity_info,
    splk_mhm_return_searches,
)

# import TrackMe FLX/FQM/WLK libs
from trackme_libs_splk_flx import splk_flx_return_searches
from trackme_libs_splk_fqm import splk_fqm_return_searches
from trackme_libs_splk_wlk import splk_wlk_return_searches

# import trackme_libs_utils
from trackme_libs_utils import remove_leading_spaces

# AI Assistant ↔ AI Advisor bridge (Phase 1) — per-entity describes carry a
# component-filtered advisor reference and the entity's recent advisor runs so
# the chat LLM can propose relevant invocations without surfacing irrelevant
# advisors.
from trackme_libs_describe_ai_advisors import (
    build_ai_advisor_knowledge,
    load_recent_ai_advisor_runs,
)
from trackme_libs_describe_concierge import (
    build_concierge_knowledge,
)
from trackme_libs_describe_maintenance import (
    build_entity_maintenance_knowledge,
)


# ---- Anonymization helpers ----


def get_anonymize_setting(service):
    """
    Read the ai_anonymize_entity_names flag from trackme_settings.conf.

    Args:
        service: A Splunk service connection.

    Returns:
        bool: True when anonymization is enabled, False otherwise.
    """
    try:
        for stanza in service.confs["trackme_settings"]:
            if stanza.name == "trackme_general":
                return stanza.content.get("ai_anonymize_entity_names", "0") == "1"
    except Exception:
        pass
    return False


def get_anonymize_index_setting(service):
    """
    Read the ai_anonymize_index_names flag from trackme_settings.conf.

    Args:
        service: A Splunk service connection.

    Returns:
        bool: True when index name anonymization is enabled, False otherwise.
    """
    try:
        for stanza in service.confs["trackme_settings"]:
            if stanza.name == "trackme_general":
                return stanza.content.get("ai_anonymize_index_names", "0") == "1"
    except Exception:
        pass
    return False


def _anonymize_value(value):
    """Return a consistent SHA256 hash for anonymization."""
    if not value:
        return value
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _anonymize_values_deep(data, replacements):
    """
    Recursively walk a dict/list and replace all occurrences of
    sensitive values in strings with their hashed equivalents.

    Replacements are applied longest-first so that a longer value
    (e.g. alias="host1.domain.com") is fully replaced before a
    shorter substring (e.g. object="host1") is considered.

    Args:
        data: dict, list, or primitive value
        replacements: dict mapping {real_value: hashed_value}
    Returns:
        The data structure with all sensitive strings replaced.
    """
    if isinstance(data, dict):
        return {k: _anonymize_values_deep(v, replacements) for k, v in data.items()}
    elif isinstance(data, list):
        return [_anonymize_values_deep(item, replacements) for item in data]
    elif isinstance(data, str):
        result = data
        # Sort longest-first to prevent partial substring corruption
        for real_val, hashed_val in sorted(
            replacements.items(), key=lambda kv: len(kv[0]), reverse=True
        ):
            if real_val and real_val in result:
                result = result.replace(real_val, hashed_val)
        return result
    return data


def _anonymize_index_values_deep(data, replacements):
    """
    Recursively walk a dict/list and replace index names in strings using
    boundary-aware matching so that short index names (e.g. "main") are NOT
    replaced when they appear as substrings of unrelated values (e.g. "domain").

    Two patterns are applied per index name:

    1. **Plain-text boundary**: the characters immediately before/after the
       index name are not valid Splunk index-name characters
       ([a-zA-Z0-9._:-]).  The colon is included because DSM object
       identifiers use the ``<index>:<sourcetype>`` format; without it
       the index portion would be matched and corrupted.
    2. **URL-encoded boundary**: the index name is preceded (and optionally
       followed) by a percent-encoded sequence (``%XX``).  Investigation
       searches are URL-encoded via ``urllib.parse.quote``, turning
       surrounding delimiters like ``"`` into ``%22``.  Without this second
       pass the trailing hex digit of ``%22`` would satisfy the plain-text
       lookbehind and the index name would leak unhashed.

    Args:
        data: dict, list, or primitive value
        replacements: dict mapping {real_index_name: hashed_value}
    Returns:
        The data structure with index name strings replaced.
    """
    if isinstance(data, dict):
        return {k: _anonymize_index_values_deep(v, replacements) for k, v in data.items()}
    elif isinstance(data, list):
        return [_anonymize_index_values_deep(item, replacements) for item in data]
    elif isinstance(data, str):
        result = data
        # Sort longest-first to prevent partial substring corruption
        for real_val, hashed_val in sorted(
            replacements.items(), key=lambda kv: len(kv[0]), reverse=True
        ):
            if real_val and real_val in result:
                # Pass 1: plain-text boundary (colon included to protect DSM object refs like "main:syslog")
                pattern = r"(?<![a-zA-Z0-9._:-])" + re.escape(real_val) + r"(?![a-zA-Z0-9._:-])"
                result = re.sub(pattern, hashed_val, result)
                # Pass 2: URL-encoded boundary (preceded by %XX, followed by %XX or end)
                url_pattern = r"(?<=%[0-9A-Fa-f]{2})" + re.escape(real_val) + r"(?=%[0-9A-Fa-f]{2}|$)"
                result = re.sub(url_pattern, hashed_val, result)
        return result
    return data


def _extract_index_names(kvrecord, object_category):
    """
    Extract individual Splunk index names from an entity record.

    Args:
        kvrecord: The raw KV store record for the entity.
        object_category: The entity type (e.g. "splk-dsm").

    Returns:
        list: Distinct, non-empty index name strings.
    """
    raw = ""
    if object_category == "splk-dsm":
        raw = kvrecord.get("data_index", "")
    elif object_category == "splk-dhm":
        raw = kvrecord.get("data_index", "")
    elif object_category == "splk-mhm":
        raw = kvrecord.get("metric_index", "")

    if not raw:
        return []
    return list(dict.fromkeys(idx.strip() for idx in raw.split(",") if idx.strip()))


# Entity type configuration map
ENTITY_TYPE_MAP = {
    "splk-dsm": {
        "collection_prefix": "kv_trackme_dsm_tenant_",
        "label": "Data Source Monitoring",
        "short": "dsm",
    },
    "splk-dhm": {
        "collection_prefix": "kv_trackme_dhm_tenant_",
        "label": "Data Host Monitoring",
        "short": "dhm",
    },
    "splk-mhm": {
        "collection_prefix": "kv_trackme_mhm_tenant_",
        "label": "Metrics Host Monitoring",
        "short": "mhm",
    },
    "splk-flx": {
        "collection_prefix": "kv_trackme_flx_tenant_",
        "label": "Flexible Monitoring",
        "short": "flx",
    },
    "splk-fqm": {
        "collection_prefix": "kv_trackme_fqm_tenant_",
        "label": "Fields Quality Monitoring",
        "short": "fqm",
    },
    "splk-wlk": {
        "collection_prefix": "kv_trackme_wlk_tenant_",
        "label": "Workflow/Saved Search Monitoring",
        "short": "wlk",
    },
}

# State labels for human-readable descriptions
STATE_LABELS = {
    "green": "healthy - no anomalies detected",
    "red": "alert - anomalies detected",
    "orange": "out of monitoring scope or score below threshold",
    "blue": "info - logical group override, entity is part of a logical group and the group-level conditions are not met",
}


def _safe_parse_json_field(value, default=None):
    """Safely parse a field that may be a JSON string, list, dict, or plain string."""
    if default is None:
        default = []
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        # Try JSON parse first
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            pass
        # For non-JSON strings, only split/wrap as list if the caller expects a list
        # If the caller passed default={} (expecting dict), return the default
        if isinstance(default, dict):
            return default
        # Try pipe-delimited string
        if "|" in value:
            return [v.strip() for v in value.split("|") if v.strip()]
        # Single value
        if value and value != "none":
            return [value]
        return default
    return default


def _safe_get_numeric(record, field, default=None):
    """Safely extract a numeric value from a record field."""
    value = record.get(field)
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _collect_dhm_extras_dimensions(parsed_summary):
    """Surface the breakby_extra_fields dimensions an extras-aware DHM
    tracker is currently emitting on this entity.

    The trackmedhmpipeline parses the SPL emitter's URL-encoded extras
    string into a structured `extras: {field: value}` dict per combo in
    splk_dhm_st_summary. We walk the parsed summary, collect the union
    of `extras` dict keys across all combos (preserving first-seen
    order for stable describe output), and return them as a list.

    Returns: an ordered list of distinct extras field names, or [] if
    the entity has no extras (legacy non-extras tracker).
    """
    if not isinstance(parsed_summary, dict) or not parsed_summary:
        return []
    seen = []
    seen_set = set()
    for combo in parsed_summary.values():
        if not isinstance(combo, dict):
            continue
        extras = combo.get("extras")
        if not isinstance(extras, dict):
            continue
        for key in extras.keys():
            key_str = str(key) if key is not None else ""
            if key_str and key_str not in seen_set:
                seen.append(key_str)
                seen_set.add(key_str)
    return seen


def _build_meta(tenant_id, object_category):
    """Build the meta section of the describe response."""
    type_config = ENTITY_TYPE_MAP.get(object_category, {})
    return {
        "api_version": "2.0",
        "generated_at": time.time(),
        "object_category": object_category,
        "object_category_label": type_config.get("label", object_category),
        "tenant_id": tenant_id,
    }


def _build_identity(kvrecord, service, tenant_id, object_category):
    """Build the identity section from the KV record."""
    identity = {
        "object": kvrecord.get("object"),
        "object_id": kvrecord.get("_key"),
        "object_category": object_category,
        "tenant_id": tenant_id,
        "alias": kvrecord.get("alias", kvrecord.get("object")),
        "priority": kvrecord.get("priority", "medium"),
        "priority_reason": kvrecord.get("priority_reason"),
        "monitored_state": kvrecord.get("monitored_state", "enabled"),
        "sla_class": kvrecord.get("sla_class"),
        "sla_class_reason": kvrecord.get("sla_class_reason"),
        "sla_policy_id": kvrecord.get("sla_policy_id"),
        "sla_policy_value": kvrecord.get("sla_policy_value"),
        "sla_updated": kvrecord.get("sla_updated"),
        "tags": _safe_parse_json_field(kvrecord.get("tags"), []),
        "tags_auto": _safe_parse_json_field(kvrecord.get("tags_auto"), []),
        "tags_auto_policies": _safe_parse_json_field(kvrecord.get("tags_auto_policies"), []),
        "tags_manual": _safe_parse_json_field(kvrecord.get("tags_manual"), []),
        # Entity labels (GitHub-style lightweight tags introduced in 2.3.19, PR #1024).
        # Populated by load_component_data via dynamic_labels_lookup():
        #   labels:          flat sorted list of label names (for filtering / Virtual Groups)
        #   labels_objects:  full JSON list of {label_id, label_name, label_color} (for rendering)
        # Propagate both so the AI context sees lifecycle markers (under-review,
        # in-progress, resolved, maintenance, acknowledged, noise, decommissioned, etc.).
        "labels": _safe_parse_json_field(kvrecord.get("labels"), []),
        "labels_objects": _safe_parse_json_field(kvrecord.get("labels_objects"), []),
    }

    # Type-specific identity fields
    if object_category == "splk-dsm":
        identity["data_index"] = kvrecord.get("data_index")
        identity["data_sourcetype"] = kvrecord.get("data_sourcetype")
        identity["search_mode"] = kvrecord.get("search_mode")
    elif object_category == "splk-dhm":
        identity["data_index"] = kvrecord.get("data_index")
        identity["data_sourcetype"] = kvrecord.get("data_sourcetype")
        identity["data_host"] = kvrecord.get("data_host")
        identity["search_mode"] = kvrecord.get("search_mode")
    elif object_category == "splk-mhm":
        identity["metric_index"] = kvrecord.get("metric_index")
        identity["metric_category"] = kvrecord.get("metric_category")
    elif object_category == "splk-flx":
        identity["tracker_name"] = kvrecord.get("tracker_name")
        identity["uc_ref"] = kvrecord.get("uc_ref")
        identity["object_description"] = kvrecord.get("object_description")
        identity["group"] = kvrecord.get("group")
        identity["subgroup"] = kvrecord.get("subgroup")
    elif object_category == "splk-fqm":
        identity["fieldname"] = kvrecord.get("fieldname")
        identity["object_description"] = kvrecord.get("object_description")
        identity["metadata_datamodel"] = kvrecord.get("metadata_datamodel")
        identity["metadata_nodename"] = kvrecord.get("metadata_nodename")
        identity["metadata_index"] = kvrecord.get("metadata_index")
        identity["metadata_sourcetype"] = kvrecord.get("metadata_sourcetype")
        identity["tracker_name"] = kvrecord.get("tracker_name")
    elif object_category == "splk-wlk":
        identity["savedsearch_name"] = kvrecord.get("savedsearch_name")
        identity["app"] = kvrecord.get("app")
        identity["owner"] = kvrecord.get("owner")
        identity["user"] = kvrecord.get("user")
        identity["object_description"] = kvrecord.get("object_description")
        identity["overgroup"] = kvrecord.get("overgroup")
        identity["group"] = kvrecord.get("group")

    # Look up notes for this entity (schema introduced/expanded in 2.3.19, PR #1048).
    # Notes carry operational context (investigation status, runbook pointers, owner
    # comments) that is valuable for the LLM when explaining an entity's situation.
    try:
        notes_collection_name = f"kv_trackme_notes_tenant_{tenant_id}"
        notes_collection = service.kvstore[notes_collection_name]
        notes_records = notes_collection.data.query(
            query=json.dumps({"object_id": kvrecord.get("_key")})
        )
        if notes_records:
            # Sort by mtime descending (newest first)
            notes_list = sorted(notes_records, key=lambda x: x.get("mtime", 0), reverse=True)
            identity["notes"] = notes_list
            identity["notes_count"] = len(notes_list)
        else:
            identity["notes"] = []
            identity["notes_count"] = 0
    except Exception:
        identity["notes"] = []
        identity["notes_count"] = 0

    return identity


def _build_cmdb_integration(service, tenant_id, object_category):
    """
    Build the CMDB integration context for this entity's tenant+component
    (2.3.19 — PR #1035 / #1064).

    CMDB enrichment happens dynamically at alert time by executing the
    per-component CMDB search (optionally on a remote account) — the
    resulting fields are not persisted on the entity record, so we cannot
    echo specific CMDB values here.  Instead we surface the configuration
    so the AI knows *whether* CMDB context is available for this entity
    and *which* search template will run when the entity alerts.

    Returns a dict with:
      - enabled_at_tenant: whether the tenant has the cmdb_lookup toggle on
      - cmdb_account:      the remote account used (empty string = local splunkd)
      - component_search_configured: whether a per-component cmdb search is set
      - component_search_preview:    first 200 chars of the configured search
                                     (for quick sanity-checking by the LLM)
    """
    component = ENTITY_TYPE_MAP.get(object_category, {}).get("short")

    result = {
        "enabled_at_tenant": False,
        "cmdb_account": "",
        "component_search_configured": False,
        "component_search_preview": "",
    }

    # The CMDB toggle and per-component search templates live in the
    # vtenant_account conf (trackme_vtenants.conf), NOT on the
    # kv_trackme_virtual_tenants KV record. Reading them off the KV record
    # always returned the .get() default (cmdb_lookup -> always "enabled",
    # cmdb_account/search -> empty) because nothing syncs them onto the record
    # — see #1888 (same root cause as the shadow-config bug #1886). Read from
    # the conf instead. Lazy import to avoid a module-scope circular import in
    # the describe layer.
    try:
        from trackme_libs import (  # noqa: WPS433 — deferred to avoid circular import
            trackme_vtenant_account_from_service,
        )

        vtenant_conf = trackme_vtenant_account_from_service(service, tenant_id)
    except Exception:
        return result

    # Default cmdb_lookup is 1 so treat a missing value as enabled, matching
    # trackme_libs_cmdb.perform_cmdb_lookup().
    cmdb_toggle = vtenant_conf.get("cmdb_lookup", 1)
    try:
        result["enabled_at_tenant"] = int(str(cmdb_toggle)) == 1
    except (ValueError, TypeError):
        result["enabled_at_tenant"] = True

    result["cmdb_account"] = vtenant_conf.get("cmdb_account", "") or ""

    if component:
        search = vtenant_conf.get(f"splk_{component}_cmdb_search", "") or ""
        if search.strip():
            result["component_search_configured"] = True
            result["component_search_preview"] = search[:200]

    return result


def _build_dsm_entity_info(request_info, service, tenant_id, kvrecord):
    """Build entity_info for DSM entities, reusing existing functions."""
    object_value = kvrecord.get("object")

    # Get elastic source info
    elastic_info = splk_dsm_return_elastic_info(
        request_info.session_key,
        request_info.server_rest_port,
        tenant_id,
        object_value,
    )

    # Get base entity info
    entity_info = splk_dsm_return_entity_info(kvrecord)
    entity_info["object_id"] = kvrecord.get("_key")

    is_elastic = elastic_info.get("is_elastic")

    if is_elastic == 1:
        entity_info["account"] = elastic_info.get("account")
        entity_info["search_mode"] = elastic_info.get("search_mode")
        entity_info["is_elastic"] = 1
        entity_info["search_constraint"] = elastic_info.get("search_constraint")
        entity_info["elastic_search_mode"] = elastic_info.get("elastic_search_mode")
        entity_info.pop("breakby_key", None)
        entity_info.pop("breakby_value", None)
        entity_info.pop("breakby_statement", None)
    else:
        entity_info["is_elastic"] = 0
        entity_info["index"] = kvrecord.get("data_index")

        entity_sourcetype = kvrecord.get("data_sourcetype", "any")
        if entity_sourcetype in ("all", "any", ""):
            entity_info["sourcetype"] = "*"
            if entity_info.get("breakby_key") == "none":
                entity_info["breakby_key"] = "merged"
        else:
            entity_info["sourcetype"] = entity_sourcetype

        # Build search constraint
        breakby_key = entity_info.get("breakby_key", "none")
        if breakby_key not in ("none", "merged"):
            break_by_fields = breakby_key.split(";")
            break_by_values = entity_info.get("breakby_value", "").split(";")
            constraint_parts = [
                f'index="{kvrecord.get("data_index")}" sourcetype="{entity_info["sourcetype"]}"'
            ]
            for i, field in enumerate(break_by_fields):
                if i < len(break_by_values):
                    constraint_parts.append(f'{field}="{break_by_values[i]}"')
            entity_info["search_constraint"] = " ".join(constraint_parts)
        else:
            entity_info["search_constraint"] = (
                f'index="{kvrecord.get("data_index")}" sourcetype="{entity_info["sourcetype"]}"'
            )

    return entity_info


def _build_dhm_entity_info(request_info, service, tenant_id, kvrecord):
    """Build entity_info for DHM entities."""
    entity_info = splk_dhm_return_entity_info(kvrecord)
    entity_info["object_id"] = kvrecord.get("_key")
    entity_info["is_elastic"] = 0
    entity_info["index"] = kvrecord.get("data_index")
    entity_info["sourcetype"] = kvrecord.get("data_sourcetype", "*")
    entity_info["host"] = kvrecord.get("data_host", "")

    # Build search constraint using index IN (...) format
    # data_index and data_sourcetype can be comma-separated lists.
    # In merged mode, data_sourcetype is the "@all" sentinel rather than a
    # real sourcetype — drop the sourcetype clause so the search matches
    # every sourcetype the host actually produces.
    object_value = kvrecord.get("object", "")
    breakby_key = entity_info.get("breakby_key", "none")
    data_sourcetype_raw = kvrecord.get("data_sourcetype", "")
    sourcetype_clause = (
        "" if data_sourcetype_raw == "@all"
        else f' sourcetype IN ({data_sourcetype_raw})'
    )
    if breakby_key != "none":
        entity_info["search_constraint"] = (
            f'index IN ({kvrecord.get("data_index")}){sourcetype_clause} {breakby_key}="{entity_info.get("breakby_value", "")}"'
        )
    else:
        entity_info["search_constraint"] = (
            f'index IN ({kvrecord.get("data_index")}){sourcetype_clause} host="{object_value}"'
        )

    return entity_info


def _build_mhm_entity_info(request_info, service, tenant_id, kvrecord):
    """Build entity_info for MHM entities."""
    entity_info = splk_mhm_return_entity_info(kvrecord)
    entity_info["object_id"] = kvrecord.get("_key")
    entity_info["is_elastic"] = 0
    entity_info["metric_index"] = kvrecord.get("metric_index", "")
    entity_info["metric_category"] = kvrecord.get("metric_category", "")
    entity_info["metric_details"] = kvrecord.get("metric_details", "")

    # Build search constraint using index IN (...) format
    # metric_index can be comma-separated; use breakby_key when present
    object_value = kvrecord.get("object", "")
    breakby_key = entity_info.get("breakby_key", "none")
    if breakby_key != "none":
        entity_info["search_constraint"] = (
            f'index IN ({kvrecord.get("metric_index")}) {breakby_key}="{entity_info.get("breakby_value", "")}"'
        )
    else:
        entity_info["search_constraint"] = (
            f'index IN ({kvrecord.get("metric_index")}) host="{object_value}"'
        )

    return entity_info


def _build_flx_entity_info(request_info, service, tenant_id, kvrecord):
    """Build entity_info for FLX entities (no dedicated return_entity_info function)."""
    return {
        "object_id": kvrecord.get("_key"),
        "object": kvrecord.get("object"),
        "tracker_name": kvrecord.get("tracker_name", ""),
        "uc_ref": kvrecord.get("uc_ref", ""),
        "flx_type": kvrecord.get("flx_type"),
        "object_description": kvrecord.get("object_description"),
        "status": kvrecord.get("status"),
        "status_description": kvrecord.get("status_description"),
        "group": kvrecord.get("group"),
        "subgroup": kvrecord.get("subgroup"),
        "search_mode": "mstats",
        "account": kvrecord.get("account", "local"),
    }


def _build_fqm_entity_info(request_info, service, tenant_id, kvrecord):
    """Build entity_info for FQM entities (no dedicated return_entity_info function)."""
    return {
        "object_id": kvrecord.get("_key"),
        "object": kvrecord.get("object"),
        "fqm_type": kvrecord.get("fqm_type", "field"),
        "fieldname": kvrecord.get("fieldname"),
        "object_description": kvrecord.get("object_description"),
        "status": kvrecord.get("status"),
        "status_description": kvrecord.get("status_description"),
        "metadata_datamodel": kvrecord.get("metadata_datamodel"),
        "metadata_nodename": kvrecord.get("metadata_nodename"),
        "metadata_index": kvrecord.get("metadata_index"),
        "metadata_sourcetype": kvrecord.get("metadata_sourcetype"),
        "tracker_name": kvrecord.get("tracker_name"),
        "tracker_index": kvrecord.get("tracker_index"),
        "fields_quality_summary": kvrecord.get("fields_quality_summary"),
        "search_mode": "mstats",
        "account": kvrecord.get("account", "local"),
    }


def _build_wlk_entity_info(request_info, service, tenant_id, kvrecord):
    """Build entity_info for WLK entities (no dedicated return_entity_info function)."""
    return {
        "object_id": kvrecord.get("_key"),
        "object": kvrecord.get("object"),
        "savedsearch_name": kvrecord.get("savedsearch_name", ""),
        "app": kvrecord.get("app", ""),
        "owner": kvrecord.get("owner", ""),
        "user": kvrecord.get("user", ""),
        "cron_schedule": kvrecord.get("cron_schedule", ""),
        "object_description": kvrecord.get("object_description"),
        "status": kvrecord.get("status"),
        "status_description": kvrecord.get("status_description"),
        "overgroup": kvrecord.get("overgroup"),
        "group": kvrecord.get("group"),
        "search_mode": "mstats",
        "account": kvrecord.get("account", "local"),
    }


def _build_entity_info(request_info, service, tenant_id, object_category, kvrecord):
    """Build entity_info by dispatching to the correct type-specific builder."""
    builders = {
        "splk-dsm": _build_dsm_entity_info,
        "splk-dhm": _build_dhm_entity_info,
        "splk-mhm": _build_mhm_entity_info,
        "splk-flx": _build_flx_entity_info,
        "splk-fqm": _build_fqm_entity_info,
        "splk-wlk": _build_wlk_entity_info,
    }
    builder = builders.get(object_category)
    if builder:
        return builder(request_info, service, tenant_id, kvrecord)
    return {}


def _build_health(kvrecord, service, tenant_id, object_category):
    """Build the health section from the KV record."""
    object_value = kvrecord.get("object")
    object_state = kvrecord.get("object_state", "unknown")

    # Parse anomaly_reason
    anomaly_reason = kvrecord.get("anomaly_reason", "none")
    if not isinstance(anomaly_reason, list):
        if anomaly_reason and anomaly_reason != "none":
            anomaly_reason = [r.strip() for r in anomaly_reason.split("|") if r.strip()]
        else:
            anomaly_reason = []

    # Parse status_message
    status_messages = _safe_parse_json_field(kvrecord.get("status_message"), [])

    # Parse score_definition — guard against None (key exists with null value)
    score_definition = kvrecord.get("score_definition")
    if score_definition is None:
        score_definition = {}
    elif isinstance(score_definition, str):
        try:
            score_definition = json.loads(score_definition)
        except (json.JSONDecodeError, ValueError):
            score_definition = {}

    health = {
        "object_state": object_state,
        "object_state_label": STATE_LABELS.get(object_state, "unknown"),
        "anomaly_reasons": anomaly_reason,
        "status_messages": status_messages,
        "score": {
            "total_score": score_definition.get("total_score", score_definition.get("base_score", 0)),
            "base_score": score_definition.get("base_score", 0),
            "score_outliers": score_definition.get("score_outliers", 0),
            "score_source": score_definition.get("score_source", []),
            "components": score_definition.get("components", []),
        },
        "latest_flip_state": kvrecord.get("latest_flip_state"),
        "latest_flip_time": _safe_get_numeric(kvrecord, "latest_flip_time"),
        "object_previous_state": kvrecord.get("object_previous_state"),
        "isAnomaly": kvrecord.get("isAnomaly"),
        "isOutlier": kvrecord.get("isOutlier"),
        "outliers_readiness": kvrecord.get("outliers_readiness"),
        # Per-entity maintenance: the decision-maker engine forced object_state
        # to "blue" above when a window is active and stamped these fields on
        # the record. When inactive, is_under_maintenance is absent → False.
        "maintenance": {
            "is_under_maintenance": bool(kvrecord.get("is_under_maintenance", 0)),
            "maintenance_start_epoch": kvrecord.get("maintenance_start_epoch"),
            "maintenance_end_epoch": kvrecord.get("maintenance_end_epoch"),
            "maintenance_comment": kvrecord.get("maintenance_comment", ""),
        },
    }

    # Logical group membership lookup
    try:
        lg_collection_name = f"kv_trackme_common_logical_group_tenant_{tenant_id}"
        lg_collection = service.kvstore[lg_collection_name]
        lg_records = lg_collection.data.query(
            query=json.dumps({
                "object": object_value,
                "object_category": object_category,
            })
        )
        if lg_records:
            lg_record = lg_records[0]
            health["logical_group"] = {
                "in_logical_group": True,
                "group_key": lg_record.get("object_group_key"),
                "group_min_green_pct": lg_record.get("object_group_min_green_percent"),
            }
        else:
            health["logical_group"] = {"in_logical_group": False}
    except Exception:
        health["logical_group"] = {"in_logical_group": False}

    # Check acknowledgment state
    try:
        ack_collection_name = f"kv_trackme_common_alerts_ack_tenant_{tenant_id}"
        ack_collection = service.kvstore[ack_collection_name]
        ack_records = ack_collection.data.query(
            query=json.dumps(
                {"object": object_value, "object_category": object_category, "ack_state": "active"}
            )
        )
        if ack_records:
            ack_record = ack_records[0]
            health["ack_state"] = {
                "is_acked": True,
                "ack_mtime": ack_record.get("ack_mtime"),
                "ack_expiration": ack_record.get("ack_expiration"),
            }
        else:
            health["ack_state"] = {"is_acked": False}
    except Exception:
        health["ack_state"] = {"is_acked": False}

    return health


def _build_outliers(service, tenant_id, object_category, kvrecord):
    """Build outliers ML model context for an entity from dedicated KV collections."""
    type_config = ENTITY_TYPE_MAP.get(object_category, {})
    short = type_config.get("short", "")
    object_id = kvrecord.get("_key", "")

    # MHM does not support outliers detection
    if object_category == "splk-mhm":
        return {"has_outliers": False, "supported": False}

    outliers = {"has_outliers": False}

    # Query the outliers rules collection for this entity
    try:
        rules_collection_name = f"kv_trackme_{short}_outliers_entity_rules_tenant_{tenant_id}"
        rules_collection = service.kvstore[rules_collection_name]
        rules_records = rules_collection.data.query(
            query=json.dumps({"_key": object_id})
        )

        if rules_records:
            rules_record = rules_records[0]
            outliers["has_outliers"] = True
            outliers["confidence"] = rules_record.get("confidence")
            outliers["confidence_reason"] = rules_record.get("confidence_reason")
            outliers["is_disabled"] = rules_record.get("is_disabled")
            outliers["last_exec"] = _safe_get_numeric(rules_record, "last_exec")

            # Parse entities_outliers JSON to extract model definitions
            entities_outliers_raw = rules_record.get("entities_outliers", "{}")
            if isinstance(entities_outliers_raw, str):
                try:
                    entities_outliers = json.loads(entities_outliers_raw)
                except (json.JSONDecodeError, ValueError):
                    entities_outliers = {}
            elif isinstance(entities_outliers_raw, dict):
                entities_outliers = entities_outliers_raw
            else:
                entities_outliers = {}

            # Extract key fields per model for AI context
            models = {}
            for model_id, model_def in entities_outliers.items():
                if isinstance(model_def, dict):
                    models[model_id] = {
                        # Model configuration
                        "kpi_metric": model_def.get("kpi_metric"),
                        "kpi_span": model_def.get("kpi_span"),
                        "algorithm": model_def.get("algorithm"),
                        "method_calculation": model_def.get("method_calculation"),
                        # Thresholds
                        "density_lowerthreshold": model_def.get("density_lowerthreshold"),
                        "density_upperthreshold": model_def.get("density_upperthreshold"),
                        "static_lower_threshold": model_def.get("static_lower_threshold"),
                        "static_upper_threshold": model_def.get("static_upper_threshold"),
                        # Alert and correction settings
                        "alert_lower_breached": model_def.get("alert_lower_breached"),
                        "alert_upper_breached": model_def.get("alert_upper_breached"),
                        "auto_correct": model_def.get("auto_correct"),
                        "is_disabled": model_def.get("is_disabled"),
                        # Training period and time factors
                        "period_calculation": model_def.get("period_calculation"),
                        "time_factor": model_def.get("time_factor"),
                        "period_exclusions": model_def.get("period_exclusions"),
                        # Deviation and minimum value thresholds
                        "perc_min_lowerbound_deviation": model_def.get("perc_min_lowerbound_deviation"),
                        "perc_min_upperbound_deviation": model_def.get("perc_min_upperbound_deviation"),
                        "min_value_for_lowerbound_breached": model_def.get("min_value_for_lowerbound_breached"),
                        "min_value_for_upperbound_breached": model_def.get("min_value_for_upperbound_breached"),
                        # User-facing custom command searches (replace raw | fit / | apply SPL
                        # which reference private internal ML models users cannot call directly)
                        "render_search": (
                            f'| trackmesplkoutliersrender tenant_id="{tenant_id}" component="{short}"'
                            f' object_id="{object_id}" model_id="{model_id}"'
                        ),
                        "train_search": (
                            f'| trackmesplkoutlierstrain tenant_id="{tenant_id}" component="{short}"'
                            f' object_id="{object_id}" model_id="{model_id}"'
                        ),
                    }
            outliers["models"] = models

    except Exception as e:
        get_effective_logger().error(
            f'function=_build_outliers, tenant_id="{tenant_id}", '
            f'object_category="{object_category}", object_id="{object_id}", '
            f'section="rules", exception="{str(e)}"'
        )

    # Query the outliers data collection for detection results
    try:
        data_collection_name = f"kv_trackme_{short}_outliers_entity_data_tenant_{tenant_id}"
        data_collection = service.kvstore[data_collection_name]
        data_records = data_collection.data.query(
            query=json.dumps({"_key": object_id})
        )

        if data_records:
            data_record = data_records[0]
            outliers["detection"] = {
                "isOutlier": data_record.get("isOutlier"),
                "isOutlierReason": data_record.get("isOutlierReason"),
                "models_in_anomaly": _safe_parse_json_field(
                    data_record.get("models_in_anomaly"), []
                ),
                "models_summary": _safe_parse_json_field(
                    data_record.get("models_summary"), {}
                ),
            }

    except Exception as e:
        get_effective_logger().error(
            f'function=_build_outliers, tenant_id="{tenant_id}", '
            f'object_category="{object_category}", object_id="{object_id}", '
            f'section="data", exception="{str(e)}"'
        )

    return outliers


def _build_thresholds_help(object_category):
    """
    Return advisory guidance for threshold tuning based on entity type.

    This helps AI assistants explain to users how thresholds work and how
    they can be adjusted for a given entity type, without the AI needing
    to guess or hallucinate configuration details.
    """

    if object_category in ("splk-dsm", "splk-dhm"):
        label = "Data Source" if object_category == "splk-dsm" else "Data Host"
        help_info = {
            "description": (
                f"{label} Monitoring entities use a lagging policy to detect anomalies. "
                "The two main thresholds are the maximum event delay (data_max_delay_allowed) "
                "and the maximum ingestion latency (data_max_lag_allowed), both in seconds."
            ),
            "tunable_thresholds": {
                "data_max_delay_allowed": {
                    "label": "Max event delay",
                    "unit": "seconds",
                    "description": (
                        "Maximum allowed delay between the current time and the latest event "
                        "timestamp (_time). If the delay exceeds this value, the entity enters "
                        "a red (alert) state. Increase this value if the data source legitimately "
                        "sends data in batches or with long intervals. When variable_delay_policy "
                        "is 'variable', this static value is ignored and time-based slot thresholds "
                        "are used instead."
                    ),
                },
                "data_max_lag_allowed": {
                    "label": "Max ingestion latency",
                    "unit": "seconds",
                    "description": (
                        "Maximum allowed latency between an event's timestamp (_time) and when "
                        "it was indexed (_indextime). High latency may indicate forwarding delays "
                        "or queuing issues. Increase this value if the data pipeline has known "
                        "buffering or batching stages."
                    ),
                },
                "future_tolerance": {
                    "label": "Future event tolerance",
                    "unit": "seconds (negative value)",
                    "description": (
                        "Tolerance for events with timestamps in the future. Expressed as a "
                        "negative number of seconds (e.g. -600 means up to 10 minutes in the "
                        "future is tolerated). Adjust if sources have clock skew issues."
                    ),
                },
            },
            "additional_settings": {
                "threshold_lock": (
                    "The single user-facing control (DSM/DHM) for whether TrackMe may auto-adjust "
                    "this entity's delay/lag thresholds. When LOCKED, the operator's thresholds are "
                    "pinned — adaptive delay and lagging-class overrides are disabled and a "
                    "reconcile routine restores the values if any background writer changes them; a "
                    "red lock icon appears next to the entity name in the UI. When UNLOCKED, the "
                    "thresholds are auto-managed. Toggle it from the lag-policy edit modal or in "
                    "bulk; it is the recommended fix for 'my threshold keeps changing by itself'. "
                    "The adaptive_delay and lagging_class settings below are DERIVED from this lock."
                ),
                "adaptive_delay": (
                    "DERIVED from threshold_lock — not edited directly anymore. When the entity is "
                    "unlocked, TrackMe dynamically adjusts the expected delay based on the observed "
                    "data pattern; locking the entity disables it. Mutually exclusive with "
                    "variable_delay."
                ),
                "lagging_class": (
                    "DERIVED from threshold_lock — the per-entity lagging-class override flag. "
                    "Locking the entity makes its own thresholds authoritative over any matched "
                    "lagging class; unlocking lets a matched class apply its shared thresholds."
                ),
                "variable_delay": (
                    "When variable_delay_policy is 'variable', the entity uses time-based delay "
                    "thresholds that vary by day-of-week and hour-of-day. Different slots define "
                    "different max_delay_allowed values (e.g. tighter during business hours, "
                    "relaxed during weekends). The static data_max_delay_allowed is ignored for "
                    "delay monitoring. Adaptive delay is automatically disabled. Use the "
                    "/services/trackme/v2/splk_variable_delay endpoints to configure slots."
                ),
                "variable_delay_timezone": (
                    "Slot days and hours are stored and evaluated in the Splunk server's local "
                    "time (the splunkd timezone; UTC on Splunk Cloud, the host's system zone "
                    "on-prem). Always reason about and write slot hours in server-local time. "
                    "The web UI is the only layer that translates: it displays and edits slot "
                    "hours in the operator's browser-local time for convenience and converts "
                    "them back to server time on save. The KV store and the REST API therefore "
                    "always hold server-local hours, so a browser-vs-API hour difference equal "
                    "to the operator's UTC offset is expected, not a bug. Slot weekday labels "
                    "are never shifted, so a slot whose hours cross midnight under the offset "
                    "keeps its server-calendar weekday."
                ),
            },
            "how_to_tune": (
                "Thresholds can be adjusted via the entity's UI (click on the entity, then "
                "the 'Modify' button in the lagging tab) or via the REST API using the "
                "entity update endpoint. Changes take effect on the next monitoring cycle."
            ),
        }
        if object_category == "splk-dsm":
            help_info["tunable_thresholds"]["min_dcount_host"] = {
                "label": "Minimum distinct host count",
                "unit": "count",
                "description": (
                    "Minimum number of distinct hosts expected to send data for this "
                    "source. If the observed host count drops below this value, the entity "
                    "enters an alert state. Set to 0 to disable host count monitoring."
                ),
            }
        return help_info

    elif object_category == "splk-mhm":
        return {
            "description": (
                "Metrics Host Monitoring entities use a metric category policy to detect "
                "anomalies. The main threshold is the maximum metric lag "
                "(metric_max_lag_allowed) in seconds."
            ),
            "tunable_thresholds": {
                "metric_max_lag_allowed": {
                    "label": "Max metric lag",
                    "unit": "seconds",
                    "description": (
                        "Maximum allowed delay since the last metric data point was received. "
                        "If the metric lag exceeds this value, the entity enters a red (alert) "
                        "state. Increase this value for metrics that are collected at longer "
                        "intervals."
                    ),
                },
                "future_tolerance": {
                    "label": "Future metric tolerance",
                    "unit": "seconds (negative value)",
                    "description": (
                        "Tolerance for metric data points with timestamps in the future. "
                        "Adjust if metric sources have clock synchronization issues."
                    ),
                },
            },
            "how_to_tune": (
                "Thresholds can be adjusted via the entity's UI or via the REST API "
                "using the MHM entity update endpoint. The metric category policy allows "
                "setting shared thresholds across groups of similar metric hosts."
            ),
        }

    elif object_category == "splk-flx":
        return {
            "description": (
                "Flexible Monitoring entities define thresholds at the use case level "
                "(in the FLX tracker definition), not on individual entities. Each use "
                "case specifies metric-based threshold conditions (e.g. CPU > 90%) and "
                "an inactivity timeout (max_sec_inactive)."
            ),
            "tunable_thresholds": {
                "max_sec_inactive": {
                    "label": "Max inactivity period",
                    "unit": "seconds",
                    "description": (
                        "Maximum time without receiving new data before the entity is "
                        "considered inactive and enters an alert state."
                    ),
                },
                "use_case_thresholds": {
                    "label": "Use case threshold conditions",
                    "description": (
                        "Threshold conditions are defined in the FLX use case tracker "
                        "configuration (e.g. metric > value or metric < value). These "
                        "conditions determine when the entity status changes to alert. "
                        "To modify these thresholds, update the FLX use case definition "
                        "in the TrackMe Flex Monitoring configuration page."
                    ),
                },
                "variable_threshold": (
                    "When variable_threshold_enabled is 'true' on a threshold rule, the static "
                    "threshold value is replaced by time-based values that vary by day-of-week "
                    "and hour-of-day. Different slots define different threshold values (e.g. "
                    "tighter during business hours, relaxed during weekends). The static value "
                    "field serves as documentation only when variable threshold is active. "
                    "Use the /services/trackme/v2/splk_flx/write/flx_thresholds_update endpoint "
                    "to configure variable threshold slots per threshold rule."
                ),
                "variable_threshold_timezone": (
                    "Slot days and hours are stored and evaluated in the Splunk server's local "
                    "time (the splunkd timezone; UTC on Splunk Cloud, the host's system zone "
                    "on-prem). Always reason about and write slot hours in server-local time. "
                    "The web UI is the only layer that translates: it displays and edits slot "
                    "hours in the operator's browser-local time for convenience and converts "
                    "them back to server time on save. The KV store and the REST API therefore "
                    "always hold server-local hours, so a browser-vs-API hour difference equal "
                    "to the operator's UTC offset is expected, not a bug. Slot weekday labels "
                    "are never shifted, so a slot whose hours cross midnight under the offset "
                    "keeps its server-calendar weekday."
                ),
            },
            "how_to_tune": (
                "The inactivity timeout (max_sec_inactive) can be adjusted per entity. "
                "Metric threshold conditions must be modified in the FLX use case "
                "tracker definition, which applies to all entities matched by that use case. "
                "Individual threshold rules can optionally use variable (time-based) values "
                "by enabling variable_threshold_enabled and configuring time slots."
            ),
        }

    elif object_category == "splk-fqm":
        return {
            "description": (
                "Fields Quality Monitoring entities track field extraction quality. "
                "Thresholds are defined at the FQM tracker level and control the "
                "minimum acceptable field extraction success rate and coverage."
            ),
            "tunable_thresholds": {
                "tracker_thresholds": {
                    "label": "FQM tracker threshold conditions",
                    "description": (
                        "Threshold conditions (e.g. minimum percent_success or "
                        "percent_coverage) are defined in the FQM tracker configuration. "
                        "To modify these thresholds, update the FQM tracker definition "
                        "in the TrackMe Fields Quality Monitoring configuration page."
                    ),
                },
            },
            "how_to_tune": (
                "FQM thresholds are managed at the tracker level, not per entity. "
                "Adjust the tracker's threshold conditions in the TrackMe FQM "
                "configuration page to change alerting sensitivity for field quality."
            ),
        }

    elif object_category == "splk-wlk":
        return {
            "description": (
                "Workload Monitoring entities support configurable thresholds for "
                "skipping search percentage and execution error counts. Thresholds "
                "can be set at the tenant level (defaults for all entities) and "
                "overridden per entity."
            ),
            "tunable_thresholds": {
                "skipped_pct_thresholds": {
                    "description": (
                        "Configurable thresholds for skipped search percentage "
                        "across time windows (60m, 4h, 24h)."
                    ),
                },
                "count_errors_thresholds": {
                    "description": (
                        "Configurable thresholds for execution error counts "
                        "across time windows (60m, 4h, 24h)."
                    ),
                },
            },
            "how_to_tune": (
                "Use the threshold management interface in Tenant Home to configure "
                "tenant-level defaults, or modify per-entity thresholds from the "
                "entity detail view."
            ),
        }

    # Fallback for unknown entity types
    return {
        "description": "Threshold tuning information is not available for this entity type.",
        "tunable_thresholds": None,
        "how_to_tune": None,
    }


def _build_configuration(kvrecord, object_category):
    """Build the configuration section from the KV record."""
    config = {}

    if object_category in ("splk-dsm", "splk-dhm"):
        config["thresholds"] = {
            "data_max_lag_allowed": _safe_get_numeric(kvrecord, "data_max_lag_allowed"),
            "data_max_delay_allowed": _safe_get_numeric(kvrecord, "data_max_delay_allowed"),
            "future_tolerance": _safe_get_numeric(kvrecord, "future_tolerance"),
        }
        if object_category == "splk-dsm":
            config["thresholds"]["min_dcount_host"] = _safe_get_numeric(
                kvrecord, "min_dcount_host", 0
            )
            config["data_sampling"] = {
                "data_sample_lastrun": _safe_get_numeric(kvrecord, "data_sample_lastrun"),
            }

        config["monitoring_schedule"] = {
            "monitoring_time_policy": kvrecord.get("monitoring_time_policy", "global"),
            "monitoring_time_rules": kvrecord.get("monitoring_time_rules"),
        }

        # Threshold lock — the single user-facing control (DSM/DHM). The two
        # legacy flags below (adaptive_delay / lagging_class) are DERIVED from
        # this lock and kept only for back-compat; the lock is what the UI shows
        # (red lock badge) and what the AI should reason about and act on.
        _lock_raw = str(
            kvrecord.get("data_max_delay_allowed_locked", "false")
        ).strip().lower()
        config["threshold_lock"] = {
            "locked": (_lock_raw in ("true", "1")),
            "locked_raw": kvrecord.get("data_max_delay_allowed_locked", ""),
            "note": (
                "When locked, the operator's delay/lag thresholds are pinned: "
                "adaptive delay and lagging-class overrides are disabled and a "
                "reconcile routine restores any drift. To lock/unlock, call "
                "``update_entity_adaptive_delay`` (allow_adaptive_delay='false' "
                "locks, 'true' unlocks). The adaptive_delay / lagging_class "
                "fields are derived from this lock — do not edit them directly."
            ),
        }

        config["adaptive_delay"] = kvrecord.get("allow_adaptive_delay", "default")
        config["lagging_class"] = kvrecord.get("data_override_lagging_class", kvrecord.get("override_lagging_class", "default"))

        # Matched lagging class metadata — populated by the decision
        # maker on every per-tenant tracker cycle (see
        # ``trackme_rest_handler_component_user.py`` and
        # ``trackme_libs_decisionmaker.py``). Without this block the AI
        # advisors can't see whether a lagging class is currently
        # overriding the entity-level thresholds, which led to the
        # silent "I tuned the slot but it didn't take effect" failure
        # mode (see PR sequence on lagging-class awareness). Fields
        # mirror the names the UI banner reads from the same record.
        config["lagging_class_assignment"] = {
            # ``matched`` is stored as the literal string "true"/"false"
            # on the record — surface the bool here for the LLM's
            # convenience and the original string as ``matched_raw`` for
            # any consumer that wants the exact persisted value.
            "matched": (kvrecord.get("lagging_class_matched", "false") == "true"),
            "matched_raw": kvrecord.get("lagging_class_matched", ""),
            "name": kvrecord.get("lagging_class_name", ""),
            "level": kvrecord.get("lagging_class_level", ""),
            "match_mode": kvrecord.get("lagging_class_match_mode", ""),
            "delay_mode": kvrecord.get("lagging_class_delay_mode", ""),
            "key": kvrecord.get("lagging_class_key", ""),
            # The per-entity opt-out. When ``"true"``, the entity's own
            # thresholds win over any matched lagging class — same
            # field already surfaced as ``config["lagging_class"]`` for
            # back-compat but re-exposed here in the assignment block
            # so the AI advisors see precedence semantics in one place.
            "entity_override": kvrecord.get(
                "data_override_lagging_class",
                kvrecord.get("override_lagging_class", "false"),
            ),
            "precedence_note": (
                "When ``matched`` is true AND the entity is NOT locked "
                "(``entity_override='false'``, which is derived from the "
                "threshold lock), the lagging class's delay (and lag, if "
                "set) thresholds take precedence over this entity's "
                "own ``data_max_delay_allowed`` / variable-delay slots "
                "/ ``data_max_lag_allowed`` values. Updating the "
                "entity-level threshold in that situation is a silent "
                "no-op — the active threshold remains the class's. To "
                "make the entity-level value win, LOCK the entity (via "
                "``set_entity_lagging_class_override`` / "
                "``update_entity_adaptive_delay`` — both send the "
                "unified ``lock_threshold``), or update the lagging "
                "class itself (via ``update_lagging_class``). When "
                "``matched`` is false, lagging-class precedence does not "
                "apply and the entity-level thresholds are authoritative "
                "as usual."
            ),
        }

        # Variable delay policy
        variable_delay_policy = kvrecord.get("variable_delay_policy", "static")
        config["variable_delay_policy"] = variable_delay_policy
        if variable_delay_policy == "variable":
            config["variable_delay"] = {
                "mode": "variable",
                "description": (
                    "This entity uses variable delay thresholds that change based on day-of-week "
                    "and hour-of-day. The static data_max_delay_allowed value shown in thresholds "
                    "is not used for delay monitoring; instead, time-based slots define different "
                    "thresholds for different periods."
                ),
                "active_slot": kvrecord.get("variable_delay_active_slot", ""),
                "active_threshold": _safe_get_numeric(kvrecord, "variable_delay_active_threshold"),
                "note": (
                    "Use the /services/trackme/v2/splk_variable_delay/get endpoint to retrieve "
                    "the full slot configuration for this entity."
                ),
            }

        # DHM-specific alerting and blocklist configuration
        if object_category == "splk-dhm":
            config["alerting_policy"] = kvrecord.get("splk_dhm_alerting_policy")
            config["host_idx_blocklists"] = kvrecord.get("host_idx_blocklists")
            config["host_st_blocklists"] = kvrecord.get("host_st_blocklists")

    elif object_category == "splk-mhm":
        config["thresholds"] = {
            "metric_max_lag_allowed": _safe_get_numeric(kvrecord, "metric_max_lag_allowed"),
            "future_tolerance": _safe_get_numeric(kvrecord, "future_tolerance"),
        }
        config["monitoring_schedule"] = {
            "monitoring_time_policy": kvrecord.get("monitoring_time_policy", "global"),
            "monitoring_time_rules": kvrecord.get("monitoring_time_rules"),
        }

    elif object_category == "splk-flx":
        config["max_sec_inactive"] = _safe_get_numeric(kvrecord, "max_sec_inactive")
        config["monitoring_schedule"] = {
            "monitoring_time_policy": kvrecord.get("monitoring_time_policy", "global"),
            "monitoring_time_rules": kvrecord.get("monitoring_time_rules"),
        }
        config["variable_thresholds"] = {
            "description": (
                "FLX threshold rules can optionally use variable (time-based) values that "
                "change based on day-of-week and hour-of-day. When enabled on a threshold "
                "rule, named time slots define different threshold values for different periods."
            ),
            "note": (
                "Use the /services/trackme/v2/splk_flx/read/flx_thresholds_get endpoint to "
                "retrieve threshold rules for this entity, including variable threshold "
                "configuration (variable_threshold_enabled, variable_threshold_default, "
                "variable_threshold_slots fields)."
            ),
        }

    elif object_category == "splk-wlk":
        config["wlk_config"] = {
            "cron_schedule": kvrecord.get("cron_schedule"),
            "app": kvrecord.get("app"),
            "owner": kvrecord.get("owner"),
            "user": kvrecord.get("user"),
        }
        config["monitoring_schedule"] = {
            "monitoring_time_policy": kvrecord.get("monitoring_time_policy", "global"),
            "monitoring_time_rules": kvrecord.get("monitoring_time_rules"),
        }

    elif object_category == "splk-fqm":
        config["fqm_config"] = {
            "fqm_type": kvrecord.get("fqm_type", "field"),
            "tracker_name": kvrecord.get("tracker_name"),
            "tracker_index": kvrecord.get("tracker_index"),
        }
        config["monitoring_schedule"] = {
            "monitoring_time_policy": kvrecord.get("monitoring_time_policy", "global"),
            "monitoring_time_rules": kvrecord.get("monitoring_time_rules"),
        }

    # Add thresholds_help — advisory guidance for tuning thresholds per entity type
    config["thresholds_help"] = _build_thresholds_help(object_category)

    # Impact score weights (applies to all types)
    impact_score_weights = kvrecord.get("impact_score_weights")
    if impact_score_weights:
        config["impact_score_weights"] = _safe_parse_json_field(
            impact_score_weights, {}
        )

    # SLA class (applies to all types)
    config["sla_class"] = kvrecord.get("sla_class")

    return config


def _build_metrics_summary(kvrecord, object_category):
    """Build the metrics summary from fields already stored in the KV record."""
    metrics = {}

    if object_category in ("splk-dsm", "splk-dhm"):
        metrics["data_last_time_seen"] = _safe_get_numeric(kvrecord, "data_last_time_seen")
        metrics["data_first_time_seen"] = _safe_get_numeric(kvrecord, "data_first_time_seen")
        metrics["data_last_ingest"] = _safe_get_numeric(kvrecord, "data_last_ingest")
        metrics["data_eventcount"] = _safe_get_numeric(kvrecord, "data_eventcount")
        metrics["data_last_lag_seen"] = _safe_get_numeric(kvrecord, "data_last_lag_seen")
        metrics["data_last_ingestion_lag_seen"] = _safe_get_numeric(kvrecord, "data_last_ingestion_lag_seen")

        if object_category == "splk-dsm":
            metrics["dcount_host"] = _safe_get_numeric(kvrecord, "dcount_host")
            metrics["min_dcount_host"] = _safe_get_numeric(kvrecord, "min_dcount_host")
            metrics["avg_dcount_host_5m"] = _safe_get_numeric(kvrecord, "avg_dcount_host_5m")
            metrics["latest_dcount_host_5m"] = _safe_get_numeric(kvrecord, "latest_dcount_host_5m")
            metrics["perc95_dcount_host_5m"] = _safe_get_numeric(kvrecord, "perc95_dcount_host_5m")
            metrics["stdev_dcount_host_5m"] = _safe_get_numeric(kvrecord, "stdev_dcount_host_5m")
            metrics["global_dcount_host"] = _safe_get_numeric(kvrecord, "global_dcount_host")

        if object_category == "splk-dhm":
            # DHM host status summary provides a condensed view of host health
            metrics["splk_dhm_st_summary"] = _safe_parse_json_field(kvrecord.get("splk_dhm_st_summary"), {})
            # Extras-aware tracker signal — surface the union of `extras`
            # dict keys across all combos so the AI Assistant can answer
            # "what dimensions does this entity track beyond (index,
            # sourcetype)?" without re-parsing the raw summary itself.
            # Empty / absent for legacy non-extras trackers.
            _dhm_extras_dims = _collect_dhm_extras_dimensions(
                metrics["splk_dhm_st_summary"]
            )
            if _dhm_extras_dims:
                metrics["extras_dimensions"] = _dhm_extras_dims

    elif object_category == "splk-mhm":
        metrics["metric_last_time_seen"] = _safe_get_numeric(kvrecord, "metric_last_time_seen")
        metrics["metric_first_time_seen"] = _safe_get_numeric(kvrecord, "metric_first_time_seen")
        metrics["metric_last_lag_seen"] = _safe_get_numeric(kvrecord, "metric_last_lag_seen")
        metrics["metric_details"] = kvrecord.get("metric_details")

    elif object_category == "splk-flx":
        metrics["data_last_time_seen"] = _safe_get_numeric(kvrecord, "data_last_time_seen")
        metrics["data_first_time_seen"] = _safe_get_numeric(kvrecord, "data_first_time_seen")
        metrics["status"] = kvrecord.get("status")
        metrics["status_description"] = kvrecord.get("status_description")
        metrics["metrics"] = _safe_parse_json_field(kvrecord.get("metrics"), {})
        metrics["extra_attributes"] = _safe_parse_json_field(kvrecord.get("extra_attributes"), {})
        metrics["upstream_status"] = kvrecord.get("upstream_status")

    elif object_category == "splk-wlk":
        metrics["sec_since_lastexec"] = _safe_get_numeric(kvrecord, "sec_since_lastexec")
        metrics["status"] = kvrecord.get("status")
        metrics["status_description"] = kvrecord.get("status_description")
        # Current window metrics
        metrics["skipped_pct"] = _safe_get_numeric(kvrecord, "skipped_pct")
        metrics["count_errors"] = _safe_get_numeric(kvrecord, "count_errors")
        # Time-windowed metrics for trend analysis
        metrics["skipped_pct_last_60m"] = _safe_get_numeric(kvrecord, "skipped_pct_last_60m")
        metrics["skipped_pct_last_4h"] = _safe_get_numeric(kvrecord, "skipped_pct_last_4h")
        metrics["skipped_pct_last_24h"] = _safe_get_numeric(kvrecord, "skipped_pct_last_24h")
        metrics["count_errors_last_60m"] = _safe_get_numeric(kvrecord, "count_errors_last_60m")
        metrics["count_errors_last_4h"] = _safe_get_numeric(kvrecord, "count_errors_last_4h")
        metrics["count_errors_last_24h"] = _safe_get_numeric(kvrecord, "count_errors_last_24h")
        metrics["metrics_extended"] = _safe_parse_json_field(kvrecord.get("metrics_extended"), {})

    elif object_category == "splk-fqm":
        metrics["data_last_time_seen"] = _safe_get_numeric(kvrecord, "data_last_time_seen")
        metrics["status"] = kvrecord.get("status")
        metrics["status_description"] = kvrecord.get("status_description")
        metrics["percent_success"] = _safe_get_numeric(kvrecord, "percent_success")
        metrics["percent_coverage"] = _safe_get_numeric(kvrecord, "percent_coverage")
        metrics["fields_quality_summary"] = _safe_parse_json_field(kvrecord.get("fields_quality_summary"), {})

    # Common fields
    metrics["tracker_runtime"] = _safe_get_numeric(kvrecord, "tracker_runtime")
    metrics["tracker_health_runtime"] = _safe_get_numeric(kvrecord, "tracker_health_runtime")
    metrics["mtime"] = _safe_get_numeric(kvrecord, "mtime")
    metrics["ctime"] = _safe_get_numeric(kvrecord, "ctime")

    return metrics


# ---------------------------------------------------------------------------
# Anomaly-specific investigation search generators
# ---------------------------------------------------------------------------
# These functions produce component-specific investigation SPL (with
# descriptions and time ranges) for the AI assistant context — they do
# NOT execute any searches themselves. The patterns were originally
# ported from the legacy smart-status investigation library, which has
# since been decommissioned (schema migration 2401).
# ---------------------------------------------------------------------------


def _wrap_remote_search(search, account, earliest, latest):
    """Wrap a local SPL search for remote execution via splunkremotesearch."""
    search = search.replace('"', '\\"')
    return f'| splunkremotesearch account="{account}" search="{search}" earliest="{earliest}" latest="{latest}"'


def _build_dsm_where_constraint(kvrecord, entity_info):
    """Build the where constraint for DSM entities, handling tstats/raw/from/mstats search modes."""
    search_mode = entity_info.get("search_mode")

    if search_mode in ("tstats", "raw"):
        if entity_info.get("is_elastic") == 1:
            where_constraint = entity_info.get("search_constraint", "")
        else:
            where_constraint = f'(index={kvrecord.get("data_index")} sourcetype={kvrecord.get("data_sourcetype")})'
            # breakby key handling
            if entity_info.get("breakby_key") not in ("none", "merged", None):
                breakby_key = entity_info.get("breakby_key")
                breakby_value = entity_info.get("breakby_value")
                where_constraint += f" {breakby_key}={breakby_value}"

        # indexed_constraint at vtenant level
        indexed_constraint = entity_info.get("indexed_constraint", "")
        if indexed_constraint:
            where_constraint = f"{where_constraint} {indexed_constraint}"

        return where_constraint

    elif search_mode == "from":
        return entity_info.get("search_constraint", "")

    elif search_mode == "mstats":
        return entity_info.get("search_constraint", "")

    return ""


def _build_dhm_where_constraint(kvrecord, entity_info):
    """Build the where constraint for DHM entities (index IN (...) format).

    In merged mode, data_sourcetype is the "@all" sentinel rather than a
    real sourcetype — drop the sourcetype clause so the search matches
    every sourcetype the host actually produces.
    """
    data_indexes = " OR ".join(
        [f'index="{idx}"' for idx in kvrecord.get("data_index", "").split(",")]
    )
    data_sourcetype_raw = kvrecord.get("data_sourcetype", "")
    if data_sourcetype_raw == "@all":
        where_constraint = f"({data_indexes})"
    else:
        data_sourcetypes = " OR ".join(
            [f'sourcetype="{st}"' for st in data_sourcetype_raw.split(",")]
        )
        where_constraint = f"({data_indexes}) AND ({data_sourcetypes})"

    indexed_constraint = entity_info.get("indexed_constraint", "")
    if indexed_constraint:
        where_constraint = f"{where_constraint} {indexed_constraint}"

    return where_constraint


def _maybe_wrap_remote(searches, entity_info):
    """If account is remote, wrap all searches in the list with splunkremotesearch."""
    account = entity_info.get("account", "local")
    if account == "local":
        return searches
    wrapped = []
    for s in searches:
        wrapped_search = _wrap_remote_search(s["search"], account, s["earliest"], s["latest"])
        wrapped.append({**s, "search": wrapped_search})
    return wrapped


def _generate_dsm_future_searches(kvrecord, entity_info):
    """Generate investigation searches for DSM future-data anomaly (SPL only, no execution)."""
    search_mode = entity_info.get("search_mode")
    where_constraint = _build_dsm_where_constraint(kvrecord, entity_info)

    try:
        future_tolerance = int(kvrecord.get("future_tolerance", -600))
    except (TypeError, ValueError):
        future_tolerance = -600

    searches = []

    if search_mode == "tstats":
        searches.append({
            "description": "Investigate per-host future data detection",
            "search": remove_leading_spaces(
                f"| tstats max(_time) as latest_event where {where_constraint} by host"
                f" | eval now=now(), event_lag=now-latest_event"
                f" | where (event_lag<{future_tolerance})"
                f' | sort - limit=100 event_lag'
                f' | foreach event_lag [ eval <<FIELD>> = if(\'<<FIELD>>\'>60, tostring(round(\'<<FIELD>>\',0),"duration"), round(\'<<FIELD>>\', 0)) ]'
                f' | foreach latest_event now [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })
        searches.append({
            "description": "Investigate per-source future data detection",
            "search": remove_leading_spaces(
                f"| tstats max(_time) as latest_event where {where_constraint} by source"
                f" | eval now=now(), event_lag=now-latest_event"
                f" | where (event_lag<{future_tolerance})"
                f' | sort - limit=100 event_lag'
                f' | foreach event_lag [ eval <<FIELD>> = if(\'<<FIELD>>\'>60, tostring(round(\'<<FIELD>>\',0),"duration"), round(\'<<FIELD>>\', 0)) ]'
                f' | foreach latest_event now [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })
        searches.append({
            "description": "Sample 10 events with data in the future",
            "search": remove_leading_spaces(
                f"search {where_constraint}"
                f" | eval event_lag=now()-_time, latency=_indextime-_time,"
                f' indextime = strftime(_indextime, "%c"), eventtime = strftime(_time, "%c")'
                f" | sort limit=10 event_lag"
                f" | table eventtime indextime event_lag latency index sourcetype source host _raw"
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })

    elif search_mode == "raw":
        searches.append({
            "description": "Investigate per-host future data detection",
            "search": remove_leading_spaces(
                f"search {where_constraint} | stats max(_time) as latest_event by host"
                f" | eval now=now(), event_lag=now-latest_event"
                f" | where (event_lag<{future_tolerance})"
                f' | sort - limit=100 event_lag'
                f' | foreach event_lag [ eval <<FIELD>> = if(\'<<FIELD>>\'>60, tostring(round(\'<<FIELD>>\',0),"duration"), round(\'<<FIELD>>\', 0)) ]'
                f' | foreach latest_event now [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })
        searches.append({
            "description": "Investigate per-source future data detection",
            "search": remove_leading_spaces(
                f"search {where_constraint} | stats max(_time) as latest_event by source"
                f" | eval now=now(), event_lag=now-latest_event"
                f" | where (event_lag<{future_tolerance})"
                f' | sort - limit=100 event_lag'
                f' | foreach event_lag [ eval <<FIELD>> = if(\'<<FIELD>>\'>60, tostring(round(\'<<FIELD>>\',0),"duration"), round(\'<<FIELD>>\', 0)) ]'
                f' | foreach latest_event now [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })
        searches.append({
            "description": "Sample 10 events with data in the future",
            "search": remove_leading_spaces(
                f"search {where_constraint}"
                f' | eval latency=_indextime-_time, indextime = strftime(_indextime, "%c"), eventtime = strftime(_time, "%c")'
                f" | sort - limit=10 latency"
                f" | table eventtime indextime latency index sourcetype source host _raw"
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })

    elif search_mode == "from":
        searches.append({
            "description": "Investigate per-host future data detection",
            "search": remove_leading_spaces(
                f"| from {where_constraint} | stats max(_time) as latest_event by host"
                f" | eval now=now(), event_lag=now-latest_event"
                f" | where (event_lag<{future_tolerance})"
                f' | sort - limit=100 event_lag'
                f' | foreach event_lag [ eval <<FIELD>> = if(\'<<FIELD>>\'>60, tostring(round(\'<<FIELD>>\',0),"duration"), round(\'<<FIELD>>\', 0)) ]'
                f' | foreach latest_event now [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })
        searches.append({
            "description": "Investigate per-source future data detection",
            "search": remove_leading_spaces(
                f"| from {where_constraint} | stats max(_time) as latest_event by source"
                f" | eval now=now(), event_lag=now-latest_event"
                f" | where (event_lag<{future_tolerance})"
                f' | sort - limit=100 event_lag'
                f' | foreach event_lag [ eval <<FIELD>> = if(\'<<FIELD>>\'>60, tostring(round(\'<<FIELD>>\',0),"duration"), round(\'<<FIELD>>\', 0)) ]'
                f' | foreach latest_event now [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })
        searches.append({
            "description": "Sample 10 events with data in the future",
            "search": remove_leading_spaces(
                f"| from {where_constraint}"
                f" | eval now=now(), event_lag=now-_time, eventtime=_time, indextime=_indextime"
                f" | where (event_lag<{future_tolerance})"
                f' | foreach eventtime now indextime [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
                f" | head 10"
                f" | table eventtime now indextime event_lag index sourcetype source host _raw"
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })

    elif search_mode == "mstats":
        searches.append({
            "description": "Investigate per-host future metric detection",
            "search": remove_leading_spaces(
                f'| mstats latest(_value) as value where {where_constraint} by host, metric_name span=1m'
                f' | rex field=metric_name "(?P<metric_category>[^\\.]*)\\.{{0,1}}"'
                f" | stats max(_time) as latest_metric by host, metric_category"
                f" | eval now=now(), metric_lag=now-latest_metric"
                f" | where (metric_lag<{future_tolerance})"
                f' | sort - limit=100 metric_lag'
                f' | foreach metric_lag [ eval <<FIELD>> = if(\'<<FIELD>>\'>60, tostring(round(\'<<FIELD>>\',0),"duration"), round(\'<<FIELD>>\', 0)) ]'
                f' | foreach latest_metric now [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })
        searches.append({
            "description": "Investigate per-metric-category future metric detection",
            "search": remove_leading_spaces(
                f'| mstats latest(_value) as value where {where_constraint} by metric_name span=1m'
                f' | rex field=metric_name "(?P<metric_category>[^\\.]*)\\.{{0,1}}"'
                f" | stats max(_time) as latest_metric by metric_category"
                f" | eval now=now(), metric_lag=now-latest_metric"
                f" | where (metric_lag<{future_tolerance})"
                f' | sort - limit=100 metric_lag'
                f' | foreach metric_lag [ eval <<FIELD>> = if(\'<<FIELD>>\'>60, tostring(round(\'<<FIELD>>\',0),"duration"), round(\'<<FIELD>>\', 0)) ]'
                f' | foreach latest_metric now [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })
        searches.append({
            "description": "Sample 10 metrics with data in the future",
            "search": remove_leading_spaces(
                f"| mstats latest(_value) as value where {where_constraint} by metric_name span=1m"
                f" | eval future_sec = now()-_time"
                f' | eval metric_time = strftime(_time, "%c"), now = strftime(now(), "%c")'
                f" | sort - limit=10 _time"
                f" | table now metric_name metric_time metric_name future_sec"
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })

    return _maybe_wrap_remote(searches, entity_info)


def _generate_dhm_future_searches(kvrecord, entity_info):
    """Generate investigation searches for DHM future-data anomaly (SPL only, no execution)."""
    search_mode = entity_info.get("search_mode")
    where_constraint = _build_dhm_where_constraint(kvrecord, entity_info)

    try:
        future_tolerance = int(kvrecord.get("future_tolerance", -600))
    except (TypeError, ValueError):
        future_tolerance = -600

    searches = []

    if search_mode == "tstats":
        searches.append({
            "description": "Investigate per-sourcetype future data detection",
            "search": remove_leading_spaces(
                f"| tstats max(_time) as latest_event where {where_constraint} by sourcetype"
                f" | eval now=now(), event_lag=now-latest_event"
                f" | where (event_lag<{future_tolerance})"
                f' | sort - limit=100 event_lag'
                f' | foreach event_lag [ eval <<FIELD>> = if(\'<<FIELD>>\'>60, tostring(round(\'<<FIELD>>\',0),"duration"), round(\'<<FIELD>>\', 0)) ]'
                f' | foreach latest_event now [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })
        searches.append({
            "description": "Investigate per-source future data detection",
            "search": remove_leading_spaces(
                f"| tstats max(_time) as latest_event where {where_constraint} by source"
                f" | eval now=now(), event_lag=now-latest_event"
                f" | where (event_lag<{future_tolerance})"
                f' | sort - limit=100 event_lag'
                f' | foreach event_lag [ eval <<FIELD>> = if(\'<<FIELD>>\'>60, tostring(round(\'<<FIELD>>\',0),"duration"), round(\'<<FIELD>>\', 0)) ]'
                f' | foreach latest_event now [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })
        searches.append({
            "description": "Sample 10 events with data in the future",
            "search": remove_leading_spaces(
                f"search {where_constraint}"
                f' | eval event_lag=now()-_time, latency=_indextime-_time, indextime = strftime(_indextime, "%c"), eventtime = strftime(_time, "%c")'
                f" | sort limit=10 event_lag"
                f" | table eventtime indextime event_lag latency index sourcetype source host _raw"
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })

    elif search_mode == "raw":
        searches.append({
            "description": "Investigate per-sourcetype future data detection",
            "search": remove_leading_spaces(
                f"search {where_constraint} | stats max(_time) as latest_event by sourcetype"
                f" | eval now=now(), event_lag=now-latest_event"
                f" | where (event_lag<{future_tolerance})"
                f' | sort - limit=100 event_lag'
                f' | foreach event_lag [ eval <<FIELD>> = if(\'<<FIELD>>\'>60, tostring(round(\'<<FIELD>>\',0),"duration"), round(\'<<FIELD>>\', 0)) ]'
                f' | foreach latest_event now [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })
        searches.append({
            "description": "Investigate per-source future data detection",
            "search": remove_leading_spaces(
                f"search {where_constraint} | stats max(_time) as latest_event by source"
                f" | eval now=now(), event_lag=now-latest_event"
                f" | where (event_lag<{future_tolerance})"
                f' | sort - limit=100 event_lag'
                f' | foreach event_lag [ eval <<FIELD>> = if(\'<<FIELD>>\'>60, tostring(round(\'<<FIELD>>\',0),"duration"), round(\'<<FIELD>>\', 0)) ]'
                f' | foreach latest_event now [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })
        searches.append({
            "description": "Sample 10 events with data in the future",
            "search": remove_leading_spaces(
                f"search {where_constraint}"
                f' | eval latency=_indextime-_time, indextime = strftime(_indextime, "%c"), eventtime = strftime(_time, "%c")'
                f" | sort - limit=10 latency"
                f" | table eventtime indextime latency index sourcetype source host _raw"
            ),
            "earliest": "-24h",
            "latest": "+24h",
        })

    return _maybe_wrap_remote(searches, entity_info)


def _generate_dsm_latency_searches(kvrecord, entity_info):
    """Generate investigation searches for DSM latency anomaly (SPL only, no execution)."""
    search_mode = entity_info.get("search_mode")

    # Latency is only relevant for tstats/raw/from (not mstats — no indexed time)
    if search_mode not in ("tstats", "raw", "from"):
        return []

    where_constraint = _build_dsm_where_constraint(kvrecord, entity_info)

    try:
        data_last_time_seen = int(kvrecord.get("data_last_time_seen", 0))
    except (TypeError, ValueError):
        data_last_time_seen = 0

    earliest_4h = str(data_last_time_seen - 14400) if data_last_time_seen else "-4h"
    earliest_12h = str(data_last_time_seen - 43200) if data_last_time_seen else "-12h"
    latest = "+4h"
    searches = []

    if search_mode in ("tstats", "raw"):
        searches.append({
            "description": "Latency statistics by index/sourcetype (last 4h around entity activity)",
            "search": remove_leading_spaces(
                f"search {where_constraint} | eval latency=_indextime-_time"
                f" | stats avg(latency) as avg_latency, min(latency) as min_latency, stdev(latency) as stdev_latency, perc95(latency) as perc95_latency, max(latency) as max_latency by index, sourcetype"
                f" | foreach *_latency [ eval <<FIELD>> = round('<<FIELD>>', 3) ]"
            ),
            "earliest": earliest_4h,
            "latest": latest,
        })
    elif search_mode == "from":
        searches.append({
            "description": "Latency statistics by sourcetype (last 4h around entity activity)",
            "search": remove_leading_spaces(
                f"| from {where_constraint} | eval latency=_indextime-_time"
                f" | stats avg(latency) as avg_latency, min(latency) as min_latency, stdev(latency) as stdev_latency, perc95(latency) as perc95_latency, max(latency) as max_latency by sourcetype"
                f" | foreach *_latency [ eval <<FIELD>> = round('<<FIELD>>', 3) ]"
            ),
            "earliest": earliest_4h,
            "latest": latest,
        })

    # Latency timechart (last 12h)
    if search_mode in ("tstats", "raw"):
        searches.append({
            "description": "Latency timechart over the period (last 12h around entity activity)",
            "search": remove_leading_spaces(
                f"search {where_constraint} | eval latency=_indextime-_time"
                f" | timechart bins=1000 minspan=5m avg(latency) as avg_latency, perc95(latency) as perc95_latency, max(latency) as max_latency"
            ),
            "earliest": earliest_12h,
            "latest": latest,
        })
    elif search_mode == "from":
        searches.append({
            "description": "Latency timechart over the period (last 12h around entity activity)",
            "search": remove_leading_spaces(
                f"| from {where_constraint} | eval latency=_indextime-_time"
                f" | timechart bins=1000 minspan=5m avg(latency) as avg_latency, perc95(latency) as perc95_latency, max(latency) as max_latency"
            ),
            "earliest": earliest_12h,
            "latest": latest,
        })

    # Sample high-latency events
    if search_mode in ("tstats", "raw"):
        searches.append({
            "description": "Sample 10 raw events with the highest index time latency (last 4h)",
            "search": remove_leading_spaces(
                f"search {where_constraint}"
                f' | eval latency=_indextime-_time, indextime = strftime(_indextime, "%c"), eventtime = strftime(_time, "%c")'
                f" | sort - limit=10 latency"
                f" | table eventtime indextime latency index sourcetype source host _raw"
            ),
            "earliest": earliest_4h,
            "latest": latest,
        })
    elif search_mode == "from":
        searches.append({
            "description": "Sample 10 raw events with the highest index time latency (last 4h)",
            "search": remove_leading_spaces(
                f"| from {where_constraint}"
                f' | eval latency=_indextime-_time, indextime = strftime(_indextime, "%c"), eventtime = strftime(_time, "%c")'
                f" | sort - limit=10 latency"
                f" | table eventtime indextime latency index sourcetype source host _raw"
            ),
            "earliest": earliest_4h,
            "latest": latest,
        })

    return _maybe_wrap_remote(searches, entity_info)


def _generate_dhm_latency_searches(kvrecord, entity_info):
    """Generate investigation searches for DHM latency anomaly (SPL only, no execution)."""
    search_mode = entity_info.get("search_mode")
    if search_mode not in ("tstats", "raw"):
        return []

    where_constraint = _build_dhm_where_constraint(kvrecord, entity_info)

    try:
        data_last_time_seen = int(kvrecord.get("data_last_time_seen", 0))
    except (TypeError, ValueError):
        data_last_time_seen = 0

    earliest_4h = str(data_last_time_seen - 14400) if data_last_time_seen else "-4h"
    earliest_12h = str(data_last_time_seen - 43200) if data_last_time_seen else "-12h"
    latest = "+4h"
    searches = []

    searches.append({
        "description": "Latency statistics by index/sourcetype (last 4h around entity activity)",
        "search": remove_leading_spaces(
            f"search {where_constraint} | eval latency=_indextime-_time"
            f" | stats avg(latency) as avg_latency, min(latency) as min_latency, stdev(latency) as stdev_latency, perc95(latency) as perc95_latency, max(latency) as max_latency by index, sourcetype"
            f" | foreach *_latency [ eval <<FIELD>> = round('<<FIELD>>', 3) ]"
        ),
        "earliest": earliest_4h,
        "latest": latest,
    })

    # Latency timechart (last 12h)
    searches.append({
        "description": "Latency timechart over the period (last 12h around entity activity)",
        "search": remove_leading_spaces(
            f"search {where_constraint} | eval latency=_indextime-_time"
            f" | timechart bins=1000 minspan=5m avg(latency) as avg_latency, perc95(latency) as perc95_latency, max(latency) as max_latency"
        ),
        "earliest": earliest_12h,
        "latest": latest,
    })

    # Sample high-latency events
    searches.append({
        "description": "Sample 10 raw events with the highest index time latency (last 4h)",
        "search": remove_leading_spaces(
            f"search {where_constraint}"
            f' | eval latency=_indextime-_time, indextime = strftime(_indextime, "%c"), eventtime = strftime(_time, "%c")'
            f" | sort - limit=10 latency"
            f" | table eventtime indextime latency index sourcetype source host _raw"
        ),
        "earliest": earliest_4h,
        "latest": latest,
    })

    return _maybe_wrap_remote(searches, entity_info)


def _generate_dsm_delay_searches(kvrecord, entity_info, tenant_id):
    """Generate investigation searches for DSM delay anomaly (SPL only, no execution)."""
    search_mode = entity_info.get("search_mode")
    if search_mode not in ("tstats", "raw", "from"):
        return []

    where_constraint = _build_dsm_where_constraint(kvrecord, entity_info)
    object_value = kvrecord.get("object", "")

    try:
        data_last_time_seen = int(kvrecord.get("data_last_time_seen", 0))
    except (TypeError, ValueError):
        data_last_time_seen = 0

    earliest_24h = str(data_last_time_seen - 86400) if data_last_time_seen else "-24h"
    searches = []

    # Search 1: current delay status
    if search_mode in ("tstats", "raw"):
        searches.append({
            "description": "Current data flow delay status — last event time and ingest time per index/sourcetype",
            "search": remove_leading_spaces(
                f"| tstats max(_time) as last_time, max(_indextime) as last_ingest where {where_constraint} by index, sourcetype"
                f" | eval current_delay_eventtime=round(now()-last_time, 0), current_delay_ingesttime=round(now()-last_ingest, 0)"
                f' | foreach current_delay_eventtime current_delay_ingesttime [ eval <<FIELD>>_duration = tostring(\'<<FIELD>>\', "duration") ]'
                f' | foreach last_time last_ingest [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
            ),
            "earliest": earliest_24h,
            "latest": "+4h",
        })
    elif search_mode == "from":
        searches.append({
            "description": "Current data flow delay status — last event time and ingest time per index/sourcetype",
            "search": remove_leading_spaces(
                f"| from {where_constraint} | stats max(_time) as last_time, max(_indextime) as last_ingest by index, sourcetype"
                f" | eval current_delay_eventtime=round(now()-last_time, 0), current_delay_ingesttime=round(now()-last_ingest, 0)"
                f' | foreach current_delay_eventtime current_delay_ingesttime [ eval <<FIELD>>_duration = tostring(\'<<FIELD>>\', "duration") ]'
                f' | foreach last_time last_ingest [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
            ),
            "earliest": earliest_24h,
            "latest": "+4h",
        })

    # Search 2: delay metrics over time (TrackMe metrics)
    searches.append({
        "description": "TrackMe delay metrics over time for the entity (last 24h)",
        "search": remove_leading_spaces(
            f'| mstats max(trackme.splk.feeds.lag_event_sec) as lag_event_sec where `trackme_metrics_idx({tenant_id})` tenant_id="{tenant_id}" object_category="splk-dsm" object="{object_value}" by object span=5m'
            f" | timechart span=15m avg(lag_event_sec) as lag_event_sec"
        ),
        "earliest": "-24h",
        "latest": "+4h",
    })

    # Search 3: flip events for delay breaches (last 30d)
    searches.append({
        "description": "Flip events related to delay threshold breaches over the past 30 days",
        "search": remove_leading_spaces(
            f'| search `trackme_idx({tenant_id})` sourcetype="trackme:flip" tenant_id="{tenant_id}" object_category="splk-dsm" object="{object_value}" "delay_threshold_breached"'
            f" | stats count as count_delay_breached, latest(result) as last_result, values(result) as all_flip_results, latest(latest_flip_time) as latest_flip_time"
            f' | eval latest_flip_time = strftime(latest_flip_time, "%c")'
        ),
        "earliest": "-30d",
        "latest": "now",
    })

    # Only search1 needs remote wrapping (searches 2/3 use local TrackMe data)
    account = entity_info.get("account", "local")
    if account != "local" and searches:
        first = searches[0]
        first["search"] = _wrap_remote_search(first["search"], account, first["earliest"], first["latest"])

    return searches


def _generate_dhm_delay_searches(kvrecord, entity_info, tenant_id):
    """Generate investigation searches for DHM delay anomaly (SPL only, no execution)."""
    where_constraint = _build_dhm_where_constraint(kvrecord, entity_info)
    object_value = kvrecord.get("object", "")

    try:
        data_last_time_seen = int(kvrecord.get("data_last_time_seen", 0))
    except (TypeError, ValueError):
        data_last_time_seen = 0

    earliest_24h = str(data_last_time_seen - 86400) if data_last_time_seen else "-24h"
    searches = []

    # Search 1: current delay status
    searches.append({
        "description": "Current data flow delay status — last event time and ingest time per index/sourcetype",
        "search": remove_leading_spaces(
            f"| tstats max(_time) as last_time, max(_indextime) as last_ingest where {where_constraint} by index, sourcetype"
            f" | eval current_delay_eventtime=round(now()-last_time, 0), current_delay_ingesttime=round(now()-last_ingest, 0)"
            f' | foreach current_delay_eventtime current_delay_ingesttime [ eval <<FIELD>>_duration = tostring(\'<<FIELD>>\', "duration") ]'
            f' | foreach last_time last_ingest [ eval <<FIELD>> = strftime(\'<<FIELD>>\', "%c") ]'
        ),
        "earliest": earliest_24h,
        "latest": "+4h",
    })

    # Search 2: delay metrics over time (TrackMe metrics)
    searches.append({
        "description": "TrackMe delay metrics over time for the entity (last 24h)",
        "search": remove_leading_spaces(
            f'| mstats max(trackme.splk.feeds.lag_event_sec) as lag_event_sec where `trackme_metrics_idx({tenant_id})` tenant_id="{tenant_id}" object_category="splk-dhm" object="{object_value}" by object span=5m'
            f" | timechart span=15m avg(lag_event_sec) as lag_event_sec"
        ),
        "earliest": "-24h",
        "latest": "+4h",
    })

    # Search 3: flip events for delay breaches (last 30d)
    searches.append({
        "description": "Flip events related to delay threshold breaches over the past 30 days",
        "search": remove_leading_spaces(
            f'| search `trackme_idx({tenant_id})` sourcetype="trackme:flip" tenant_id="{tenant_id}" object_category="splk-dhm" object="{object_value}" "delay_threshold_breached"'
            f" | stats count as count_delay_breached, latest(result) as last_result, values(result) as all_flip_results, latest(latest_flip_time) as latest_flip_time"
            f' | eval latest_flip_time = strftime(latest_flip_time, "%c")'
        ),
        "earliest": "-30d",
        "latest": "now",
    })

    # Only search1 needs remote wrapping (searches 2/3 use local TrackMe data)
    account = entity_info.get("account", "local")
    if account != "local" and searches:
        first = searches[0]
        first["search"] = _wrap_remote_search(first["search"], account, first["earliest"], first["latest"])

    return searches


def _generate_hosts_dcount_searches(kvrecord, tenant_id):
    """Generate investigation searches for DSM host distinct count anomaly (SPL only, no execution)."""
    object_value = kvrecord.get("object", "")

    try:
        data_last_time_seen = int(kvrecord.get("data_last_time_seen", 0))
    except (TypeError, ValueError):
        data_last_time_seen = 0

    earliest_24h = str(data_last_time_seen - 86400) if data_last_time_seen else "-24h"

    return [
        {
            "description": "Host distinct count statistics from TrackMe metrics (last 24h)",
            "search": remove_leading_spaces(
                f"| mstats min(trackme.splk.feeds.latest_dcount_host_5m) as min_dcount_host_5m,"
                f" avg(trackme.splk.feeds.latest_dcount_host_5m) as avg_dcount_host_5m,"
                f' max(trackme.splk.feeds.latest_dcount_host_5m) as max_dcount_host_5m where `trackme_metrics_idx({tenant_id})`'
                f' tenant_id="{tenant_id}" object_category="splk-dsm" object="{object_value}" by object'
                f" | foreach min_dcount_host_5m, avg_dcount_host_5m, max_dcount_host_5m [ eval <<FIELD>> = round('<<FIELD>>', 2) ]"
            ),
            "earliest": earliest_24h,
            "latest": "+4h",
        },
        {
            "description": "Host distinct count over time from TrackMe metrics (last 24h, 15m buckets)",
            "search": remove_leading_spaces(
                f'| mstats avg(trackme.splk.feeds.latest_dcount_host_5m) as latest_dcount_host_5m where `trackme_metrics_idx({tenant_id})`'
                f' tenant_id="{tenant_id}" object_category="splk-dsm" object="{object_value}" by object span=5m'
                f" | timechart span=15m avg(latest_dcount_host_5m) as latest_dcount_host_5m"
                f" | eval latest_dcount_host_5m=if(isnum(latest_dcount_host_5m), round(latest_dcount_host_5m, 2), 'null')"
            ),
            "earliest": "-24h",
            "latest": "now",
        },
        {
            "description": "Flip events related to minimum host count breaches over the past 30 days",
            "search": remove_leading_spaces(
                f'search `trackme_idx({tenant_id})` sourcetype="trackme:flip" tenant_id="{tenant_id}" object_category="splk-dsm" object="{object_value}" "min_hosts_dcount"'
                f" | stats count as count_min_dcount_hosts_breached, latest(result) as last_result,"
                f" values(result) as all_flip_results, latest(latest_flip_time) as latest_flip_time"
                f' | eval latest_flip_time = strftime(latest_flip_time, "%c")'
            ),
            "earliest": "-30d",
            "latest": "now",
        },
    ]


def _generate_ml_outliers_searches(kvrecord, object_category):
    """Generate investigation search for ML Outliers detection (SPL only, no execution)."""
    tenant_id = kvrecord.get("tenant_id", "")
    object_id = kvrecord.get("_key", "")
    object_value = kvrecord.get("object", "")
    short = ENTITY_TYPE_MAP.get(object_category, {}).get("short", "")
    component = f"splk-{short}" if short else object_category

    if object_id:
        object_param = f'object_id="{object_id}"'
    else:
        object_param = f'object="{object_value}"'

    return [
        {
            "description": "Retrieve ML Outliers model data for the entity",
            "search": f'| trackmesplkoutliersgetdata tenant_id="{tenant_id}" component="{component}" {object_param}',
            "earliest": "-5m",
            "latest": "now",
        }
    ]


def _generate_events_format_recognition_searches(kvrecord, tenant_id):
    """Generate investigation search for events format recognition anomaly (SPL only, no execution)."""
    object_value = kvrecord.get("object", "")

    return [
        {
            "description": "Retrieve current data sampling and events format recognition status for the entity",
            "search": remove_leading_spaces(
                f'| trackme url="/services/trackme/v2/splk_dsm/ds_get_dsm_sampling" mode="post"'
                f" body=\"{{'tenant_id': '{tenant_id}', 'object': '{object_value}'}}\""
            ),
            "earliest": "-5m",
            "latest": "now",
        }
    ]


def _generate_wlk_searches(kvrecord, tenant_id):
    """Generate investigation searches for WLK entity anomalies (SPL only, no execution)."""
    # Use the existing splk_wlk_return_searches to get base WLK search SPL
    try:
        entity_searches = splk_wlk_return_searches(tenant_id, kvrecord)
    except Exception:
        return {}

    result = {}

    # Execution errors
    errors_search = entity_searches.get("splk_wlk_scheduler_errors_search_sample")
    if errors_search:
        result["wlk_execution_errors"] = [{
            "description": "Last 7d errors from the Splunk scheduler for this Workload entity",
            "search": remove_leading_spaces(errors_search),
            "earliest": "-7d",
            "latest": "now",
        }]

    # Skipping
    skipping_search = entity_searches.get("splk_wlk_scheduler_skipping_search_sample")
    if skipping_search:
        result["wlk_skipping"] = [{
            "description": "Last 24h skipping events from the Splunk scheduler for this Workload entity",
            "search": remove_leading_spaces(skipping_search),
            "earliest": "-24h",
            "latest": "now",
        }]

    # Orphan check
    orphan_search = entity_searches.get("splk_wlk_check_orphan")
    if orphan_search:
        result["wlk_orphan"] = [{
            "description": "Check orphan status for this Workload entity via Splunk REST endpoint",
            "search": remove_leading_spaces(orphan_search),
            "earliest": "-5m",
            "latest": "now",
        }]

    # Delayed execution
    metadata_search = entity_searches.get("splk_wlk_get_metadata")
    if metadata_search:
        result["wlk_delayed"] = [{
            "description": "Retrieve metadata and correlate expected cron sequence against latest execution",
            "search": remove_leading_spaces(metadata_search),
            "earliest": "-5m",
            "latest": "now",
        }]

    return result


def _build_anomaly_investigation_searches(object_category, kvrecord, entity_info, tenant_id):
    """
    Build anomaly-specific investigation SPL searches for inclusion in the describe response.

    Returns a dict keyed by anomaly use case, each value being a list of search descriptors:
      { "description": str, "search": str, "earliest": str, "latest": str }

    Only use cases relevant to the entity type are included.
    """
    searches = {}

    try:
        if object_category == "splk-dsm":
            future = _generate_dsm_future_searches(kvrecord, entity_info)
            if future:
                searches["future_data"] = future

            latency = _generate_dsm_latency_searches(kvrecord, entity_info)
            if latency:
                searches["latency"] = latency

            delay = _generate_dsm_delay_searches(kvrecord, entity_info, tenant_id)
            if delay:
                searches["delay"] = delay

            hosts = _generate_hosts_dcount_searches(kvrecord, tenant_id)
            if hosts:
                searches["hosts_dcount"] = hosts

            outliers = _generate_ml_outliers_searches(kvrecord, object_category)
            if outliers:
                searches["ml_outliers"] = outliers

            fmt = _generate_events_format_recognition_searches(kvrecord, tenant_id)
            if fmt:
                searches["events_format_recognition"] = fmt

        elif object_category == "splk-dhm":
            future = _generate_dhm_future_searches(kvrecord, entity_info)
            if future:
                searches["future_data"] = future

            latency = _generate_dhm_latency_searches(kvrecord, entity_info)
            if latency:
                searches["latency"] = latency

            delay = _generate_dhm_delay_searches(kvrecord, entity_info, tenant_id)
            if delay:
                searches["delay"] = delay

            outliers = _generate_ml_outliers_searches(kvrecord, object_category)
            if outliers:
                searches["ml_outliers"] = outliers

        elif object_category == "splk-wlk":
            wlk = _generate_wlk_searches(kvrecord, tenant_id)
            searches.update(wlk)

            outliers = _generate_ml_outliers_searches(kvrecord, object_category)
            if outliers:
                searches["ml_outliers"] = outliers

        # FLX, FQM, MHM: no anomaly-specific investigation searches

    except Exception as e:
        get_effective_logger().error(
            f'function=_build_anomaly_investigation_searches, object_category="{object_category}", '
            f'exception="{str(e)}"'
        )
        searches["error"] = str(e)

    return searches


def _build_investigation(tenant_id, object_value, object_category, entity_info, kvrecord):
    """Build the investigation section with dynamically generated SPL searches and additional context searches."""
    object_id = kvrecord.get("_key")

    investigation = {
        "searches": {},
        "anomaly_investigation_searches": {},
        "context_searches": {},
        "related_endpoints": {},
    }

    # Generate type-specific entity investigation searches
    try:
        if object_category == "splk-dsm":
            entity_searches = splk_dsm_return_searches(tenant_id, object_value, entity_info)
            investigation["searches"] = entity_searches

            investigation["related_endpoints"] = {
                "entity_info": "/services/trackme/v2/splk_dsm/ds_entity_info",
                "get_table": "/services/trackme/v2/splk_dsm/dsm_get_table",
            }

        elif object_category == "splk-dhm":
            entity_searches = splk_dhm_return_searches(tenant_id, object_value, entity_info)
            investigation["searches"] = entity_searches

            investigation["related_endpoints"] = {
                "entity_info": "/services/trackme/v2/splk_dhm/dh_entity_info",
                "get_table": "/services/trackme/v2/splk_dhm/dhm_get_table",
            }

        elif object_category == "splk-mhm":
            entity_searches = splk_mhm_return_searches(tenant_id, object_value, entity_info)
            investigation["searches"] = entity_searches

            investigation["related_endpoints"] = {
                "entity_info": "/services/trackme/v2/splk_mhm/mh_entity_info",
                "get_table": "/services/trackme/v2/splk_mhm/mhm_get_table",
            }

        elif object_category == "splk-flx":
            # FLX passes kvrecord directly to return_searches
            entity_searches = splk_flx_return_searches(tenant_id, kvrecord)
            investigation["searches"] = entity_searches

            investigation["related_endpoints"] = {
                "entity_info": "/services/trackme/v2/splk_flx/flx_entity_info",
                "get_table": "/services/trackme/v2/splk_flx/flx_get_table",
            }

        elif object_category == "splk-fqm":
            # FQM passes kvrecord directly to return_searches
            fqm_type = kvrecord.get("fqm_type", "field")
            entity_searches = splk_fqm_return_searches(tenant_id, fqm_type, kvrecord)
            investigation["searches"] = entity_searches

            investigation["related_endpoints"] = {
                "entity_info": "/services/trackme/v2/splk_fqm/fqm_entity_info",
                "get_table": "/services/trackme/v2/splk_fqm/fqm_get_table",
            }

        elif object_category == "splk-wlk":
            # WLK passes kvrecord directly to return_searches
            entity_searches = splk_wlk_return_searches(tenant_id, kvrecord)
            investigation["searches"] = entity_searches

            investigation["related_endpoints"] = {
                "entity_info": "/services/trackme/v2/splk_wlk/wlk_entity_info",
                "get_table": "/services/trackme/v2/splk_wlk/wlk_get_table",
            }

    except Exception as e:
        get_effective_logger().error(
            f'function=_build_investigation, object_category="{object_category}", '
            f'object="{object_value}", exception="{str(e)}"'
        )
        investigation["searches"] = {"error": str(e)}

    # Add anomaly-specific investigation searches
    try:
        investigation["anomaly_investigation_searches"] = _build_anomaly_investigation_searches(
            object_category, kvrecord, entity_info, tenant_id
        )
    except Exception as e:
        get_effective_logger().error(
            f'function=_build_anomaly_investigation_searches, exception="{str(e)}"'
        )
        investigation["anomaly_investigation_searches"] = {"error": str(e)}

    # Add cross-cutting investigation context searches (SLA, scoring, flipping)
    try:
        investigation["context_searches"] = _build_context_searches(
            tenant_id, object_value, object_id, object_category
        )
    except Exception as e:
        get_effective_logger().error(
            f'function=_build_context_searches, exception="{str(e)}"'
        )
        investigation["context_searches"] = {"error": str(e)}

    return investigation


def _build_context_searches(tenant_id, object_value, object_id, object_category):
    """Build cross-cutting investigation searches for SLA, scoring, flipping, and performance metrics."""

    context = {}

    # SLA compliance search - query the SLA metrics from the metrics index
    context["sla_compliance"] = remove_leading_spaces(
        f"""\
            | mstats latest(trackme.sla.object_state) as object_state where `trackme_metrics_idx({tenant_id})` tenant_id="{tenant_id}" object_category="{object_category}" object="{object_value}" by object, _time span=5m
            | eval isGreen=if(object_state>=2, 1, 0), isNotGreen=if(object_state<2, 1, 0)
            | stats sum(isGreen) as green_count, sum(isNotGreen) as not_green_count, count as total_count
            | eval sla_pct=round((green_count/total_count)*100, 2)
        """
    )

    # SLA timeline search - visualize SLA state over time
    context["sla_timeline"] = remove_leading_spaces(
        f"""\
            | mstats latest(trackme.sla.object_state) as object_state where `trackme_metrics_idx({tenant_id})` tenant_id="{tenant_id}" object_category="{object_category}" object="{object_value}" by _time span=5m
        """
    )

    # Scoring metrics search - understand impact score components over time
    context["scoring_metrics"] = remove_leading_spaces(
        f"""\
            | mstats sum(trackme.scoring.score) as score where `trackme_metrics_idx({tenant_id})` tenant_id="{tenant_id}" object_category="{object_category}" object_id="{object_id}" by object, score_source
        """
    )

    # Status flipping events search - track state transitions
    context["flipping_events"] = remove_leading_spaces(
        f"""\
            | mstats latest(trackme.flip.object_state) as object_state where `trackme_metrics_idx({tenant_id})` tenant_id="{tenant_id}" object_category="{object_category}" object="{object_value}" by _time span=1h
        """
    )

    # Performance metrics timechart - latency and event count trends from TrackMe metrics
    if object_category in ("splk-dsm", "splk-dhm"):
        context["performance_timechart"] = remove_leading_spaces(
            f"""\
                | mstats avg(trackme.splk.feeds.avg_latency_5m) as avg_latency, avg(trackme.splk.feeds.perc95_latency_5m) as perc95_latency, avg(trackme.splk.feeds.latest_eventcount_5m) as eventcount, avg(trackme.splk.feeds.lag_event_sec) as lag_event_sec where `trackme_metrics_idx({tenant_id})` tenant_id="{tenant_id}" object_category="{object_category}" object="{object_value}" by _time span=5m
            """
        )

        if object_category == "splk-dsm":
            context["host_count_timechart"] = remove_leading_spaces(
                f"""\
                    | mstats avg(trackme.splk.feeds.global_dcount_host) as global_dcount_host, avg(trackme.splk.feeds.avg_dcount_host_5m) as avg_dcount_host, avg(trackme.splk.feeds.latest_dcount_host_5m) as latest_dcount_host where `trackme_metrics_idx({tenant_id})` tenant_id="{tenant_id}" object_category="{object_category}" object="{object_value}" by _time span=5m
                """
            )

    return context


def _build_handlers(service, tenant_id, object_category, kvrecord):
    """Build handler/tracker context for an entity — which hybrid trackers manage it."""
    type_config = ENTITY_TYPE_MAP.get(object_category, {})
    short = type_config.get("short", "")
    object_value = kvrecord.get("object", "")

    handlers = {}

    # For FLX/FQM/WLK, tracker_name is stored directly in the entity KV record
    if object_category in ("splk-flx", "splk-fqm", "splk-wlk"):
        handlers["tracker_name"] = kvrecord.get("tracker_name")

    # For DSM/DHM/MHM, list hybrid trackers from the dedicated KV collection
    if object_category in ("splk-dsm", "splk-dhm", "splk-mhm"):
        try:
            trackers_collection_name = f"kv_trackme_{short}_hybrid_trackers_tenant_{tenant_id}"
            trackers_collection = service.kvstore[trackers_collection_name]
            tracker_records = trackers_collection.data.query()
            handlers["hybrid_trackers"] = [
                {"tracker_name": record.get("tracker_name")}
                for record in tracker_records
                if record.get("tracker_name")
            ]
        except Exception:
            handlers["hybrid_trackers"] = []

    # Provide an SPL search for the AI agent to investigate handler activity (not executed)
    handlers["handler_search"] = (
        f'index=trackme_summary sourcetype=trackme:handler tenant_id="{tenant_id}"'
        f' object_category="{object_category}" object="{object_value}" | head 20'
    )

    return handlers


def build_entity_description(request_info, service, tenant_id, object_category, kvrecord, anonymize=False, anonymize_indexes=False):
    """
    Build a comprehensive, AI-consumable description of a TrackMe entity.

    Args:
        request_info: The Splunk REST request info object.
        service: The Splunk service connection.
        tenant_id: The tenant identifier.
        object_category: The entity type (e.g., "splk-dsm").
        kvrecord: The raw KV store record for the entity.
        anonymize: If True, anonymize object and alias values using SHA256 hashing.
        anonymize_indexes: If True, anonymize Splunk index names using SHA256 hashing.

    Returns:
        A structured dictionary with the entity description.
    """
    object_value = kvrecord.get("object")

    # Build entity_info (type-specific)
    entity_info = _build_entity_info(request_info, service, tenant_id, object_category, kvrecord)

    response = {
        "meta": _build_meta(tenant_id, object_category),
        "identity": _build_identity(kvrecord, service, tenant_id, object_category),
        "entity_info": entity_info,
        "health": _build_health(kvrecord, service, tenant_id, object_category),
        "outliers": _build_outliers(service, tenant_id, object_category, kvrecord),
        "configuration": _build_configuration(kvrecord, object_category),
        "cmdb_integration": _build_cmdb_integration(service, tenant_id, object_category),
        "handlers": _build_handlers(service, tenant_id, object_category, kvrecord),
        "metrics_summary": _build_metrics_summary(kvrecord, object_category),
        "investigation": _build_investigation(
            tenant_id, object_value, object_category, entity_info, kvrecord
        ),
    }

    # AI Assistant ↔ AI Advisor bridge (Phase 1).
    #
    # Two channels — same Guardian template the page-level describes use:
    #   * `ai_advisor_recent_runs` — entity-scoped runs from the summary
    #     index (last 30 days, capped at 20). Lets the AI Assistant cite
    #     prior diagnostic / remediation runs instead of proposing a
    #     redundant invocation.
    #   * `knowledge_reference.ai_advisors` — component-filtered static
    #     reference. Surfaces only advisors relevant for THIS entity's
    #     component, plus the action-contract schema + assistant playbook.
    #
    # Both channels are best-effort: failure to resolve the summary index or
    # to load runs returns empty results — the entity describe must keep
    # working. Prompt-tightness wins: surfacing FQM Advisor on a DSM
    # entity context would pollute the LLM's reasoning with irrelevant
    # capabilities.
    object_id_for_advisor = kvrecord.get("_key", "") or ""
    summary_index_for_runs = "trackme_summary"
    try:
        from trackme_libs import trackme_idx_for_tenant  # noqa: WPS433 — deferred
        idx_settings = trackme_idx_for_tenant(
            request_info.session_key,
            request_info.server_rest_uri,
            tenant_id,
        )
        summary_index_for_runs = (idx_settings or {}).get(
            "trackme_summary_idx", "trackme_summary"
        )
    except Exception as e:
        get_effective_logger().warning(
            f'function=build_entity_description, step="resolve_summary_index", '
            f'tenant_id="{tenant_id}", object="{object_value}", '
            f'exception="{str(e)}"'
        )
    response["ai_advisor_recent_runs"] = load_recent_ai_advisor_runs(
        service,
        summary_index=summary_index_for_runs,
        tenant_id_filter=tenant_id,
        object_id_filter=object_id_for_advisor,
        # Per-entity describes are tighter than page describes — 10 most
        # recent runs is plenty for "did we already inspect this?" context.
        limit=10,
    )
    response["knowledge_reference"] = {
        "ai_advisors": build_ai_advisor_knowledge(component_filter=object_category),
        # Concierge Advisor — the generalist. Available at the entity
        # surface so the AI Assistant can propose ack / tag / priority
        # / threshold actions on the current entity by routing them
        # through the catalog-driven Concierge contract when no
        # specialist advisor matches the user's intent. Static
        # knowledge only here; live state (recent Concierge proposals
        # + executions for this entity) flows through the same
        # ``ai_advisor_recent_runs`` lookup as the specialists.
        # Pass the splunkd uri + session key so the knowledge block
        # embeds a compact projection of the live API catalog. Without
        # it, the chat LLM falls back to training-data guesses for
        # endpoint paths and frequently fabricates ones that don't
        # exist (catalog gate at the consent card catches the
        # hallucination, but the user-visible UX is "agent failed").
        # Catalog fetch is cached on disk per app version (PR #1329)
        # so the per-describe-call cost is sub-second after the first
        # build.
        # ``surface="entity"`` — this code path is the entity describe
        # builder, called when the chat is scoped to a single entity row
        # (tenant_id + object + object_id + component all in session
        # scope). The Concierge knowledge block renders the
        # session-injection rule that matches this surface; PR #1389
        # introduced the parameter so each call site ships exactly one
        # rule with no internal contradictions.
        "concierge_advisor": build_concierge_knowledge(
            splunkd_uri=request_info.server_rest_uri,
            session_key=request_info.session_key,
            surface="entity",
        ),
        # Per-entity maintenance — static knowledge so the AI Assistant can
        # explain the feature and propose putting THIS entity into a
        # maintenance window. Live state is in health.maintenance above.
        "entity_maintenance": build_entity_maintenance_knowledge(),
    }

    result = {"entity_description": response}

    # Apply anonymization if enabled (entity names and/or index names)
    if anonymize or anonymize_indexes:

        # Entity name anonymization — applied to the entire result so that
        # object/alias values are replaced everywhere they appear.
        if anonymize:
            entity_replacements = {}
            alias_value = kvrecord.get("alias", object_value)
            if object_value:
                entity_replacements[object_value] = _anonymize_value(object_value)
            if alias_value and alias_value != object_value:
                entity_replacements[alias_value] = _anonymize_value(alias_value)
            if entity_replacements:
                result = _anonymize_values_deep(result, entity_replacements)

        # Index name anonymization — uses boundary-aware replacement
        # (_anonymize_index_values_deep) so short index names like "main"
        # are not replaced when they appear as substrings of unrelated
        # values like "domain".  Applied to subtrees that contain index
        # references; identity is handled field-by-field to avoid
        # corrupting the object/alias (DSM embeds the index name in
        # its object, e.g. "myindex:mysourcetype").
        if anonymize_indexes:
            index_replacements = {}
            for idx_name in _extract_index_names(kvrecord, object_category):
                index_replacements[idx_name] = _anonymize_value(idx_name)
            if index_replacements:
                desc = result["entity_description"]
                # Subtrees safe for full traversal.
                # "handlers" is excluded — its only index reference is
                # handler_search which always targets the internal
                # trackme_summary index, never customer data indexes.
                for key in ("entity_info", "investigation", "metrics_summary"):
                    if key in desc:
                        desc[key] = _anonymize_index_values_deep(desc[key], index_replacements)
                # Identity: only replace index-specific fields to protect object/alias
                identity = desc.get("identity", {})
                for field in ("data_index", "metric_index"):
                    if field in identity and identity[field]:
                        identity[field] = _anonymize_index_values_deep(identity[field], index_replacements)

        # Build anonymization notice
        notice_parts = []
        if anonymize:
            notice_parts.append(
                "Entity names (object and alias fields) have been anonymized using SHA256 hashing "
                "for privacy protection. Use the object_id to reference this entity in TrackMe REST "
                "API calls and SPL searches (e.g. | trackme commands with object_id parameter)."
            )
        if anonymize_indexes:
            notice_parts.append(
                "Splunk index names have been anonymized using SHA256 hashing for privacy protection. "
                "Investigation searches contain hashed index names that must be replaced with actual "
                "index names before execution."
            )
        result["entity_description"]["_anonymization_notice"] = " ".join(notice_parts)

    return result


def build_entities_summary(records, object_category, tenant_id, anonymize=False, anonymize_indexes=False):
    """
    Build a lightweight summary of multiple entities for AI agent discovery.

    Args:
        records: List of KV store records.
        object_category: The entity type.
        tenant_id: The tenant identifier.
        anonymize: If True, anonymize object and alias values using SHA256 hashing.
        anonymize_indexes: If True, anonymize Splunk index names using SHA256 hashing.

    Returns:
        A structured dictionary with entity summary and counts.
    """
    type_config = ENTITY_TYPE_MAP.get(object_category, {})

    # Count states
    state_counts = {"green": 0, "red": 0, "orange": 0, "blue": 0}
    monitored_count = 0
    disabled_count = 0

    entities = []
    for record in records:
        state = record.get("object_state", "unknown")
        if state in state_counts:
            state_counts[state] += 1

        if record.get("monitored_state") == "enabled":
            monitored_count += 1
        else:
            disabled_count += 1

        # Parse anomaly_reason
        anomaly_reason = record.get("anomaly_reason", "none")
        if not isinstance(anomaly_reason, list):
            if anomaly_reason and anomaly_reason != "none":
                anomaly_reason = [r.strip() for r in anomaly_reason.split("|") if r.strip()]
            else:
                anomaly_reason = []

        # Parse score — guard against None (key exists with null value)
        score_definition = record.get("score_definition")
        if score_definition is None:
            score_definition = {}
        elif isinstance(score_definition, str):
            try:
                score_definition = json.loads(score_definition)
            except (json.JSONDecodeError, ValueError):
                score_definition = {}

        total_score = score_definition.get(
            "total_score", score_definition.get("base_score", 0)
        )

        entity_object = record.get("object")
        entity_alias = record.get("alias", entity_object)
        entity_object_id = record.get("_key")

        # Build describe_endpoint_body — use object_id when anonymized
        if anonymize:
            describe_body = {
                "tenant_id": tenant_id,
                "object_id": entity_object_id,
                "object_category": object_category,
            }
        else:
            describe_body = {
                "tenant_id": tenant_id,
                "object": entity_object,
                "object_category": object_category,
            }

        # Labels and notes_count (2.3.19 — PR #1024 / #1048).
        # load_component_data populates these on each record; surfacing them
        # in the summary lets the AI filter "which under-review entities are
        # red" / "which entities have no notes and need documentation" etc.
        labels_flat = record.get("labels")
        if isinstance(labels_flat, str):
            try:
                labels_flat = json.loads(labels_flat)
            except (json.JSONDecodeError, ValueError):
                labels_flat = []
        if not isinstance(labels_flat, list):
            labels_flat = []

        try:
            notes_count = int(record.get("notes_count", 0) or 0)
        except (ValueError, TypeError):
            notes_count = 0

        entity_dict = {
            "object": entity_object,
            "object_id": entity_object_id,
            "alias": entity_alias,
            "object_state": state,
            "priority": record.get("priority", "medium"),
            "priority_reason": record.get("priority_reason"),
            "monitored_state": record.get("monitored_state", "enabled"),
            "anomaly_reasons": anomaly_reason,
            "score": total_score,
            "labels": labels_flat,
            "notes_count": notes_count,
            "describe_endpoint_body": describe_body,
        }

        # Anonymize per-entity values
        if anonymize:
            replacements = {}
            if entity_object:
                replacements[entity_object] = _anonymize_value(entity_object)
            if entity_alias and entity_alias != entity_object:
                replacements[entity_alias] = _anonymize_value(entity_alias)
            if replacements:
                entity_dict = _anonymize_values_deep(entity_dict, replacements)

        entities.append(entity_dict)

    result = {
        "entities_summary": {
            "meta": {
                "api_version": "2.0",
                "generated_at": time.time(),
                "object_category": object_category,
                "object_category_label": type_config.get("label", object_category),
                "tenant_id": tenant_id,
                "total_count": len(records),
                "returned_count": len(entities),
            },
            "summary_stats": {
                "by_state": state_counts,
                "monitored": monitored_count,
                "disabled": disabled_count,
            },
            "entities": entities,
        }
    }

    if anonymize:
        result["entities_summary"]["_anonymization_notice"] = (
            "Entity names (object and alias fields) have been anonymized using SHA256 hashing "
            "for privacy protection. Use the object_id to reference entities in TrackMe REST "
            "API calls and SPL searches. The describe_endpoint_body uses object_id for direct API follow-up."
        )

    return result
