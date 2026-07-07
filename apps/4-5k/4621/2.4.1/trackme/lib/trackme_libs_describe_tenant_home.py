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

import json
import time
import logging
from trackme_libs_logging import get_effective_logger

# import trackme_libs_load utilities
from trackme_libs_load import (
    _parse_csv_or_list,
    has_user_access,
    get_effective_roles,
    get_vtenants_accounts,
)

# Configuration Guardian describe helpers — shared with vtenants. Provides
# both a static knowledge block (what Guardian is, what each check means,
# assistant playbook) and a dynamic, tenant-filtered list of currently-
# active alerts for the AI Assistant to reason about.
from trackme_libs_describe_ai_advisors import (
    build_ai_advisor_knowledge,
    load_recent_ai_advisor_runs,
)
from trackme_libs_describe_concierge import (
    build_concierge_knowledge,
)
from trackme_libs_describe_guardian import (
    build_guardian_knowledge,
    load_active_guardian_alerts,
)
# NOTE: build_entity_maintenance_knowledge is imported LAZILY inside
# _build_knowledge_reference (not here at module scope) to break a circular
# import: trackme_libs_describe_maintenance imports _safe_int from THIS module,
# so a top-level import back into it deadlocks at partial initialisation
# (ImportError: cannot import name ... from partially initialized module).


# Component short names used across KV store collections
COMPONENTS = ("dsm", "dhm", "mhm", "flx", "fqm", "wlk")


def _safe_parse_json_field(value, default=None):
    """Safely parse a field that may be a JSON string, list, dict, or plain string."""
    if default is None:
        default = {}
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            pass
        return default
    return default


def _safe_int(value, default=0):
    """Safely convert a value to int."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _count_collection_records(service, collection_name, query=None):
    """
    Safely count records in a KV store collection.
    Returns int count, or 0 if collection does not exist.
    """
    try:
        collection = service.kvstore[collection_name]
        if query:
            records = collection.data.query(query=json.dumps(query))
        else:
            records = collection.data.query()
        return len(records)
    except Exception:
        return 0


def _build_tenant_identity(record):
    """Build the tenant identity section."""
    tenant_id = record.get("tenant_id", "")

    # Optional per-tenant Splunk username allowlist (from vtenant_account,
    # carried onto the record by the caller). Non-empty = visibility narrowed
    # to listed users + tenant_owner (splunk-system-user always bypasses).
    # `sorted` for deterministic JSON ordering across requests.
    allowed_users_list = sorted(_parse_csv_or_list(record.get("tenant_allowed_users")))

    return {
        "tenant_id": tenant_id,
        "tenant_alias": record.get("tenant_alias", tenant_id),
        "tenant_status": record.get("tenant_status", "unknown"),
        "tenant_description": record.get("tenant_desc", ""),
        "tenant_owner": record.get("tenant_owner", ""),
        "admin_roles": record.get("tenant_roles_admin", []),
        "power_roles": record.get("tenant_roles_power", []),
        "user_roles": record.get("tenant_roles_user", []),
        "tenant_allowed_users": allowed_users_list,
        "visibility_restricted": bool(allowed_users_list),
    }


def _build_components_overview(record, summary_record):
    """Build per-component enablement, entity counts, and alert counts."""
    overview = {}

    for comp in COMPONENTS:
        enabled = _safe_int(record.get(f"tenant_{comp}_enabled")) == 1

        # Entity count
        entity_count = _safe_int(
            summary_record.get(f"{comp}_entities", record.get(f"{comp}_entities"))
        )

        # Alert counts by priority
        alert_counts = {}
        for priority in ("critical", "high", "medium", "low"):
            key = f"{comp}_{priority}_red_priority"
            val = _safe_int(
                summary_record.get(key, record.get(key))
            )
            if val > 0:
                alert_counts[priority] = val

        overview[comp] = {
            "enabled": enabled,
            "entity_count": entity_count,
            "alert_counts": alert_counts,
        }

    return overview


def _build_configuration_summary(record, vtenant_conf):
    """Build the tenant configuration flags and impact scoring.

    These values live in the vtenant_account conf (trackme_vtenants.conf), NOT
    on the kv_trackme_virtual_tenants KV record — the caller enriches the KV
    record with only tenant_alias / tenant_allowed_users. Reading them off
    `record` always returned the hardcoded default (cmdb always enabled, delay
    policy always static, monitoring_time_policy always default, no impact-score
    weights), see #1888 (same root cause as the shadow-config bug #1886).
    `vtenant_conf` is the per-tenant conf dict supplied by the caller.
    """
    vtenant_conf = vtenant_conf or {}

    # cmdb_lookup defaults to enabled (1) in vtenant_account defaults — treat a
    # missing value as enabled to match the decision-maker / alert-time behaviour
    # in trackme_libs_cmdb.perform_cmdb_lookup().
    cmdb_toggle = vtenant_conf.get("cmdb_lookup", 1)
    try:
        cmdb_lookup_enabled = int(str(cmdb_toggle)) == 1
    except (ValueError, TypeError):
        cmdb_lookup_enabled = True

    # Feature flags (read from the conf, with defaults mirroring
    # collections_data.py::vtenant_account_default)
    feature_flags = {
        "sampling_enabled": str(vtenant_conf.get("sampling", "1")) == "1",
        "sampling_obfuscation_enabled": str(vtenant_conf.get("data_sampling_obfuscation", "0")) == "1",
        "adaptive_delay_enabled": str(vtenant_conf.get("adaptive_delay", "1")) == "1",
        "variable_delay_auto_review_enabled": str(vtenant_conf.get("variable_delay_auto_review", "1")) == "1",
        "mloutliers_enabled": str(vtenant_conf.get("mloutliers", "1")) == "1",
        "mloutliers_priority_filter": vtenant_conf.get("mloutliers_priority_filter", "") or "",
        "mloutliers_filter_expression": vtenant_conf.get("mloutliers_filter_expression", "") or "",
        "mloutliers_volume_kpi": vtenant_conf.get("mloutliers_volume_kpi", "") or "",
        "cmdb_lookup_enabled": cmdb_lookup_enabled,
        "dsm_default_delay_policy": vtenant_conf.get("dsm_default_delay_policy", "static"),
        "dhm_default_delay_policy": vtenant_conf.get("dhm_default_delay_policy", "static"),
    }

    # CMDB integration details (2.3.19 — PR #1035 / #1064).
    # Surface which per-component CMDB searches are configured and which
    # remote account they run on, so the AI can reason about alert-time
    # enrichment coverage per entity type.
    cmdb_components_configured = []
    for comp in COMPONENTS:
        search = vtenant_conf.get(f"splk_{comp}_cmdb_search", "") or ""
        if search.strip():
            cmdb_components_configured.append(comp)

    cmdb_integration = {
        "enabled_at_tenant": cmdb_lookup_enabled,
        "cmdb_account": vtenant_conf.get("cmdb_account", "") or "",
        "components_with_search_configured": cmdb_components_configured,
    }

    # Impact scoring
    impact_scoring = {}
    for key, val in vtenant_conf.items():
        if key.startswith("impact_score_"):
            impact_scoring[key] = _safe_int(val)

    return {
        "default_priority": vtenant_conf.get("default_priority", "medium"),
        "monitoring_time_policy": vtenant_conf.get("monitoring_time_policy", "all_time"),
        "feature_flags": feature_flags,
        "cmdb_integration": cmdb_integration,
        "impact_scoring": impact_scoring,
    }


def _build_feature_counts(service, tenant_id, enabled_components):
    """
    Build counts of configured features per component and cross-component features.
    """
    counts = {"per_component": {}, "cross_component": {}}

    for comp in COMPONENTS:
        if not enabled_components.get(comp, False):
            continue

        comp_counts = {}

        # Blocklists
        bl_count = _count_collection_records(
            service, f"kv_trackme_{comp}_allowlist_tenant_{tenant_id}"
        )
        if bl_count > 0:
            comp_counts["blocklist_rules"] = bl_count

        # Hybrid trackers
        ht_count = _count_collection_records(
            service, f"kv_trackme_{comp}_hybrid_trackers_tenant_{tenant_id}"
        )
        if ht_count > 0:
            comp_counts["hybrid_trackers"] = ht_count

        # Outlier rules
        or_count = _count_collection_records(
            service, f"kv_trackme_{comp}_outliers_entity_rules_tenant_{tenant_id}"
        )
        if or_count > 0:
            comp_counts["outlier_rules"] = or_count

        # Tags policies
        tp_count = _count_collection_records(
            service, f"kv_trackme_{comp}_tags_policies_tenant_{tenant_id}"
        )
        if tp_count > 0:
            comp_counts["tag_policies"] = tp_count

        # Priority policies
        pp_count = _count_collection_records(
            service, f"kv_trackme_{comp}_priority_policies_tenant_{tenant_id}"
        )
        if pp_count > 0:
            comp_counts["priority_policies"] = pp_count

        # SLA policies
        sp_count = _count_collection_records(
            service, f"kv_trackme_{comp}_sla_policies_tenant_{tenant_id}"
        )
        if sp_count > 0:
            comp_counts["sla_policies"] = sp_count

        if comp_counts:
            counts["per_component"][comp] = comp_counts

    # DSM-specific: Elastic sources
    if enabled_components.get("dsm", False):
        es_shared = _count_collection_records(
            service, f"kv_trackme_dsm_elastic_shared_tenant_{tenant_id}"
        )
        es_dedicated = _count_collection_records(
            service, f"kv_trackme_dsm_elastic_dedicated_tenant_{tenant_id}"
        )
        if es_shared > 0 or es_dedicated > 0:
            counts["cross_component"]["elastic_sources"] = {
                "shared": es_shared,
                "dedicated": es_dedicated,
            }

    # Cross-component: Logical groups
    lg_count = _count_collection_records(
        service, f"kv_trackme_common_logical_group_tenant_{tenant_id}"
    )
    if lg_count > 0:
        counts["cross_component"]["logical_groups"] = lg_count

    # Cross-component: Active ACKs
    ack_count = _count_collection_records(
        service, f"kv_trackme_common_alerts_ack_tenant_{tenant_id}"
    )
    if ack_count > 0:
        counts["cross_component"]["active_acknowledgments"] = ack_count

    # Cross-component: Notes
    notes_count = _count_collection_records(
        service, f"kv_trackme_notes_tenant_{tenant_id}"
    )
    if notes_count > 0:
        counts["cross_component"]["notes"] = notes_count

    # Cross-component: Labels registry + assignments (2.3.19 — PR #1024).
    # Labels are GitHub-style colour-coded tags defined once per tenant and
    # attached to any number of entities.
    labels_defined = _count_collection_records(
        service, f"kv_trackme_labels_tenant_{tenant_id}"
    )
    labels_assigned = _count_collection_records(
        service, f"kv_trackme_label_assignments_tenant_{tenant_id}"
    )
    if labels_defined > 0 or labels_assigned > 0:
        counts["cross_component"]["labels"] = {
            "defined": labels_defined,
            "assigned_entities": labels_assigned,
        }

    # Cross-component: Variable delay template customisations (2.3.19 — PR #1056).
    # Empty = tenant uses the factory defaults; non-zero means the admin has
    # customised at least one Quick Template (business_hours / weekday_weekend /
    # three_tier) or added a new template for this tenant.
    var_delay_templates = _count_collection_records(
        service, f"kv_trackme_common_variable_delay_templates_tenant_{tenant_id}"
    )
    if var_delay_templates > 0:
        counts["cross_component"]["variable_delay_template_overrides"] = var_delay_templates

    return counts


def _build_alerting_summary(service, tenant_id):
    """Build alerting summary from stateful alerting records."""
    collection_name = f"kv_trackme_stateful_alerting_tenant_{tenant_id}"
    try:
        collection = service.kvstore[collection_name]
        records = collection.data.query()
    except Exception:
        return {"alert_records": 0}

    total = len(records)
    if total == 0:
        return {"alert_records": 0}

    # Count by alert_status
    status_counts = {}
    for rec in records:
        status = rec.get("alert_status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "alert_records": total,
        "by_status": status_counts,
    }


def _build_entity_health_distribution(service, tenant_id, enabled_components):
    """Build per-component entity health state distribution."""
    distribution = {}

    for comp in COMPONENTS:
        if not enabled_components.get(comp, False):
            continue

        collection_name = f"kv_trackme_{comp}_tenant_{tenant_id}"
        try:
            collection = service.kvstore[collection_name]
            records = collection.data.query()
        except Exception:
            continue

        if not records:
            continue

        state_counts = {"green": 0, "red": 0, "orange": 0, "blue": 0}
        priority_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}

        for rec in records:
            state = rec.get("object_state", "unknown")
            if state in state_counts:
                state_counts[state] += 1

            priority = rec.get("priority", "medium")
            if priority in priority_counts:
                priority_counts[priority] += 1

        distribution[comp] = {
            "total_entities": len(records),
            "by_state": state_counts,
            "by_priority": priority_counts,
        }

    return distribution


def _build_hybrid_tracker_creation_guide(enabled_components=None):
    """
    Build detailed hybrid tracker creation knowledge per component family.

    When enabled_components is None (e.g. Virtual Tenants context), all
    component sections are included.  When a dict is provided, only sections
    for enabled components are returned to save tokens.
    """
    include_all = enabled_components is None
    guide = {}

    # ------------------------------------------------------------------ #
    # Feeds family (DSM / DHM / MHM)
    # ------------------------------------------------------------------ #
    feeds_check = {
        "dsm": include_all or (enabled_components or {}).get("dsm", False),
        "dhm": include_all or (enabled_components or {}).get("dhm", False),
        "mhm": include_all or (enabled_components or {}).get("mhm", False),
    }
    if any(feeds_check.values()):
        feeds_section = {
            "family": "Splunk Feeds (DSM / DHM / MHM)",
            "common_wizard_steps": [
                "Step 1: Tracker name and Splunk deployment (local or remote account)",
                "Step 2: Search mode and search constraint (SPL filter)",
                "Step 3: Break-by logic (how entities are split / grouped)",
                "Step 4: Time ranges (earliest / latest, plus index time for tstats)",
                "Step 5: Test and review (simulation run to preview discovered entities)",
                "Step 6: Performance benchmark (optional burn test for search cost)",
                "Step 7: Cron schedule configuration",
                "Step 8: Validate and create the tracker",
            ],
            "common_fields": {
                "tracker_name": "Unique name, auto-generated with random suffix (e.g. tracker-XXXXX)",
                "account": "'local' for the local Splunk instance, or a configured remote account name",
                "search_mode": "Determines the search command: tstats, raw, or mstats",
                "search_constraint": "SPL WHERE-clause filter to narrow the data scope",
                "earliest_time": "Earliest event-time boundary (e.g. '-4h')",
                "latest_time": "Latest event-time boundary (e.g. 'now')",
                "cron_schedule": "Cron expression for execution frequency (default '*/5 * * * *')",
            },
        }

        component_specifics = {}

        if feeds_check["dsm"]:
            component_specifics["dsm"] = {
                "name": "Data Source Monitoring tracker",
                "search_modes": [
                    "tstats (default, most efficient)",
                    "raw (for non-indexed fields)",
                    "lookups (CSV file & KVstore monitoring — DSM-only, see lookups_mode below)",
                ],
                "break_by_modes": {
                    "standard": (
                        "Splits entities by index + sourcetype (default). "
                        "Each unique index:sourcetype pair becomes a separate entity."
                    ),
                    "merged": (
                        "Groups all sourcetypes within an index into one entity. "
                        "Entity key is 'index:@all'. Use when sourcetype granularity is not needed."
                    ),
                    "custom": (
                        "Adds a custom field to the break-by logic. "
                        "Option breakby_field_include_sourcetype (True/False) controls whether "
                        "sourcetype is kept alongside the custom field."
                    ),
                },
                "tstats_options": {
                    "root_time_span": "Time span for tstats bucketing (default '30s'). Smaller = more precise but costlier.",
                    "include_splunk_server": "Include splunk_server in break-by (default False). Useful for multi-indexer tracking.",
                    "include_host": "Include host in break-by (default True). Enables dcount_host metric.",
                },
                "default_constraint_excludes": (
                    "By default excludes internal stash indexes, too_small sourcetypes, "
                    "and modular alert sourcetypes (modular_alerts:trackme*, trackme:*)."
                ),
                "time_ranges": {
                    "typical_earliest": "-4h",
                    "typical_latest": "now",
                    "index_earliest": "-4h",
                    "index_latest": "now",
                },
                "lookups_mode": {
                    "summary": (
                        "DSM-only third search mode that monitors Splunk lookups "
                        "(CSV files and KVstore collections) as first-class DSM "
                        "entities. One entity per discovered lookup, classified "
                        "with data_index=\"lookups\" and "
                        "data_sourcetype=\"<app>:<lookup_name>\"."
                    ),
                    "entity_shape": {
                        "object": "lookups:<app>:<lookup_name>",
                        "data_index": "lookups",
                        "data_sourcetype": "<app>:<lookup_name>",
                        "lookup_type": "csv | kvstore | other",
                        "lookup_path": (
                            "Absolute filesystem path for CSV; "
                            "<app>:<collection_name> for KVstore."
                        ),
                        "mtime_source": (
                            "Where data_last_time_seen came from: 'fs' (CSV "
                            "filesystem mtime), 'kvstore:<field>' (the candidate "
                            "field that yielded the value), or 'unavailable' "
                            "(no candidate field had a parseable value)."
                        ),
                    },
                    "discovery": (
                        "Provided by the | trackmelookupsmonitor generative "
                        "command (TA-trackme-lookupmonitor add-on). Enumerates "
                        "lookups visible to the running user via Splunk REST "
                        "(/services/data/lookup-table-files for CSV, "
                        "/services/storage/collections/config for KVstore) and "
                        "emits one row per lookup. The TA must be installed on "
                        "every search head that the tracker dispatches against "
                        "— including remote SHs when account != 'local'."
                    ),
                    "wizard_fields": {
                        "lookups_app_namespace": (
                            "App namespace filter. Accepts a single name, a glob "
                            "(e.g. 'TA-*'), or a comma-separated list mixing "
                            "both (e.g. 'search, TA-*, Splunk_*'). Use '-' or "
                            "'*' to match every app."
                        ),
                        "lookups_name_pattern": (
                            "Regex (re module syntax) applied to the lookup "
                            "name. Default '.*'. Backslash escapes like \\d, "
                            "\\w, \\. are preserved by the sanitiser."
                        ),
                        "lookups_type": "csv | kvstore | both",
                        "lookups_kvstore_time_fields": (
                            "KVstore-only. Comma-separated, preference-ordered "
                            "list of candidate field names that may carry the "
                            "per-record mtime. KVstore does not auto-maintain "
                            "any timestamp — only _key and _user are populated "
                            "by splunkd. The command tries each candidate in "
                            "order (sort=<field>:-1 limit=1) and the first one "
                            "with a parseable value (epoch number, numeric "
                            "string, or ISO 8601) wins; mtime_source reports "
                            "which field was read. Default: '_time, mtime, "
                            "updated_at, modified, timestamp, last_modified'."
                        ),
                        "data_max_delay_allowed": (
                            "Step 4 'Alert if not updated in last (seconds)' — "
                            "the only alerting hook in lookups mode. Default "
                            "86400 (24h). Must be > 0 (backend clamps to the "
                            "default if non-positive)."
                        ),
                    },
                    "wizard_step_repurposing": {
                        "step3_break_by": (
                            "Disabled with a banner — one entity per lookup, "
                            "no custom break-by applies."
                        ),
                        "step4_time_ranges": (
                            "earliest/latest pickers replaced by a single "
                            "integer input mapped to data_max_delay_allowed. "
                            "Lookups have no _indextime concept; latency "
                            "thresholds are neutralised "
                            "(data_max_lag_allowed=0, avg_latency_5m=0, "
                            "data_last_ingestion_lag_seen=0)."
                        ),
                        "step7_performance_benchmark": (
                            "Runs '| trackmelookupsmonitor ... | stats count' "
                            "non-persistently. Does NOT create a temporary "
                            "saved search (unlike tstats/raw burn test)."
                        ),
                    },
                    "alerting": (
                        "Latency state is forced to a no-op (lookups have no "
                        "ingestion lag). The delay state path is the only one "
                        "that drives alerting: when "
                        "now() - data_last_time_seen > data_max_delay_allowed, "
                        "the entity flips red and the standard DSM notable "
                        "fires."
                    ),
                    "sourcetype_explosion_safeguard": (
                        "data_index='lookups' is explicitly exempt from the "
                        "per-index sourcetype cap. Each sourcetype there is a "
                        "distinct lookup, not a pipeline mis-routing."
                    ),
                    "constraints": [
                        "Only available for component='dsm' — wizard hides the option and backend 400s for dhm/mhm.",
                        "Requires TA-trackme-lookupmonitor on every dispatching SH (local and any remote account targets).",
                        "Companion TA download: https://downloads.trackme-solutions.com/TA-trackme-lookupmonitor/",
                    ],
                    "key_files": {
                        "rest_handler": "package/bin/trackme_rest_handler_splk_hybrid_trackers_admin.py (post_hybrid_tracker_simulation + post_hybrid_tracker_create both have a search_mode=='lookups' short-circuit)",
                        "spl_helper": "package/lib/trackme_libs_splk_feeds.py::generate_lookups_report_search()",
                        "macro": "package/default/macros.conf::trackme_lookups_dedicated_tracker(1) (modelled on trackme_elastic_dedicated_tracker)",
                        "wizard": "splunkui/packages/tenant-home/src/components/SplkFeedsHybridTrackers/Step2-Step7 (Step2 dropdown + conditional fields; Step3 banner; Step4 max-delay input; Step6 simulation; Step7 burn test)",
                    },
                },
            }

        if feeds_check["dhm"]:
            component_specifics["dhm"] = {
                "name": "Data Host Monitoring tracker",
                "search_modes": ["tstats (default)", "raw (for non-indexed fields)"],
                "break_by_modes": {
                    "standard": (
                        "Each host is one entity, broken down per (index, sourcetype). "
                        "Default; entity key is `host`. Per-host `splk_dhm_st_summary` "
                        "carries one combo per (index, sourcetype) pair."
                    ),
                    "merged": (
                        "Sourcetype collapsed to '@all' at the root tstats. Entity is "
                        "still keyed by host, but per-host breakdown is per "
                        "(index, sourcetype=@all) — one combo per index. Cheaper on "
                        "large estates when per-sourcetype granularity isn't needed. "
                        "Added in 2.3.22 (issue #1260). Mutually exclusive with "
                        "`breakby_extra_fields`."
                    ),
                    "custom": (
                        "Replace `host` with an alternative indexed field as the "
                        "entity identifier (e.g. `cmdb_ci`). Entity key becomes the "
                        "value of that field. Custom mode is also the only mode where "
                        "`breakby_extra_fields` is accepted — even if the user does "
                        "NOT want a different host identifier, they pick Custom and "
                        "leave the breakby field as `host` to unlock extras."
                    ),
                },
                "breakby_extra_fields": {
                    "description": (
                        "Optional, ordered list of additional per-host metadata "
                        "dimensions appended to the combo grain on top of "
                        "(index, sourcetype). Available only in Custom mode. Each "
                        "host's `splk_dhm_st_summary` then carries one combo per "
                        "(index, sourcetype, <extras…>) tuple. Added in 2.3.23 "
                        "(issue #1584, PR #1580)."
                    ),
                    "use_cases": [
                        "Track which `source` (log file path) each host emits per (index, sourcetype) — most common use case.",
                        "Track a CMDB-derived attribute (e.g. `vendor_product`, `host_type`) alongside the host data feed.",
                        "Any low-cardinality dimension that should be surfaced per host without forcing the entity key to change.",
                    ],
                    "validation": [
                        "Field names must match `^[A-Za-z_][A-Za-z0-9_.]*$` (server-side AND wizard validate this).",
                        "Reserved names rejected: `host`, `index`, `sourcetype`, `splunk_server`, `_time`.",
                        "Cannot equal the configured `breakby_field` value (the host identifier).",
                        "Hard cap of 5 fields per tracker.",
                        "Submitting extras with `breakby_field=merged` returns a 400 — the validator short-circuits this case with an actionable error.",
                    ],
                    "cardinality_cap": (
                        "Per-host combo cardinality is capped at 100 (LRU by `last_time`). "
                        "If a host's `splk_dhm_st_summary` would exceed 100 entries, "
                        "the oldest combos drop off. Truncations emit an INFO log line "
                        "`event=combo_cap_truncated cap=100 dropped=N host=<host>` to "
                        "`trackme_dhm_pipeline.log` — use that as the diagnostic when a "
                        "user reports 'missing combos'."
                    ),
                    "encoding_note": (
                        "The pipeline parses the extras string and stores it as a "
                        "structured dict on each combo entry (`extras: {field: value}`). "
                        "Values are URL-encoded in the SPL emitter so paths containing "
                        "`|`, `=`, `'`, `\\`, or `%` survive round-trip intact. The AI "
                        "doesn't need to know the encoding details — just that "
                        "`splk_dhm_st_summary.<combo>.extras` is the authoritative "
                        "structured view."
                    ),
                    "ui_surfacing": [
                        "Tenant Home entity table: inspector modal title becomes 'Per-combo summary (index, sourcetype, <extra_fields…>) — raw JSON' when extras present; the modal also exposes a search bar and a state filter (all/green/red) for combo navigation.",
                        "Entity overview tab: one donut chart per extras dimension (e.g. 'Stats per source'). Driven by mstats against `trackme_metrics` — time-range-aware, historical, refreshed via loadPieCharts.",
                        "Decision-maker red-list alert message includes the extras key/value pairs when a combo is in red, e.g. `(idx: webserver, st: nginx:plus:error, source: /var/log/foo.log, anomaly_reason: lag_threshold_breached)`.",
                    ],
                },
                "tstats_options": {
                    "root_time_span": "Time span for tstats bucketing (default '5m'). Larger than DSM for host-level aggregation. Use 'none' to drop time bucketing entirely (cheapest tracker; per-bucket latency calculations are not accurate but entities are still discovered).",
                    "include_splunk_server": "Include `splunk_server` in tstats root break-by (default False). Improves latency calculation accuracy at higher search cost.",
                },
                "time_ranges": {"typical_earliest": "-4h", "typical_latest": "now"},
                "assistant_playbook": {
                    "common_questions": {
                        "user wants to track per-source data per host": (
                            "Create a DHM hybrid tracker in **Custom** mode. Leave "
                            "`breakby_field` as `host` (the default), set "
                            "`breakby_extra_fields = ['source']`. Each host's "
                            "`splk_dhm_st_summary` will then carry one combo per "
                            "(index, sourcetype, source) tuple, and the entity "
                            "overview will render a 'Stats per source' donut. "
                            "Don't suggest Standard mode — extras are gated on Custom."
                        ),
                        "user asks about a 'missing combos' scenario": (
                            "Check `trackme_dhm_pipeline.log` for "
                            "`event=combo_cap_truncated` lines for the host in "
                            "question. The static 100-combo per-host cap drops the "
                            "oldest combos LRU-by-`last_time` when exceeded. If "
                            "truncation is frequent, recommend narrowing "
                            "`breakby_extra_fields` to lower-cardinality fields, or "
                            "removing one dimension."
                        ),
                        "user in Standard mode wants extras": (
                            "Tell them to switch the tracker to **Custom** mode. The "
                            "`breakby_field` stays as `host` (the default) — Custom "
                            "mode just unlocks the extras knob without forcing the "
                            "host identifier to change. This is intentional: "
                            "extras are an 'advanced' surface that consciously opts "
                            "into Custom."
                        ),
                        "server rejects a tracker creation with extras": (
                            "Read the 400 response body — common rejections: "
                            "(a) extras field collides with `breakby_field`; "
                            "(b) extras contains a reserved name (`host`, `index`, "
                            "`sourcetype`, `splunk_server`, `_time`); "
                            "(c) more than 5 extras submitted; "
                            "(d) field name doesn't match the identifier pattern "
                            "(e.g. starts with a digit or has a space); "
                            "(e) extras submitted with `breakby_field=merged`. "
                            "All five are also enforced inline by the wizard; if a "
                            "400 reaches the user, suggest re-checking the wizard's "
                            "inline error first."
                        ),
                        "user asks what dimensions an entity tracks": (
                            "Look at the per-entity `metrics.extras_dimensions` "
                            "field surfaced by the describe response (it's the "
                            "union of `extras` dict keys across the entity's "
                            "`splk_dhm_st_summary`). If empty/absent, the tracker "
                            "is not extras-aware and the host is only broken down "
                            "by (index, sourcetype)."
                        ),
                    },
                    "response_pattern": (
                        "When a user describes a per-host breakdown need that goes "
                        "beyond (index, sourcetype), reach for "
                        "`breakby_extra_fields` first. Don't suggest creating "
                        "multiple trackers or replicas to slice the same hosts by "
                        "another dimension — that's the problem this feature "
                        "solves. Always confirm the field is low-cardinality "
                        "before recommending it (mention the 100-combo cap)."
                    ),
                },
            }

        if feeds_check["mhm"]:
            component_specifics["mhm"] = {
                "name": "Metrics Host Monitoring tracker",
                "search_modes": ["mstats (always, required for metrics indexes)"],
                "break_by": "Single break-by field (default 'host').",
                "constraint_requirement": (
                    "Search constraint must include metric_name=<pattern>. "
                    "MHM always uses the mstats command against metrics indexes."
                ),
                "time_ranges": {
                    "typical_earliest": "-60m",
                    "typical_latest": "-5m",
                    "note": "Shorter windows than DSM/DHM because metrics are near-real-time.",
                },
            }

        feeds_section["component_specifics"] = component_specifics
        guide["feeds_trackers"] = feeds_section

    # ------------------------------------------------------------------ #
    # Flex Objects (FLX)
    # ------------------------------------------------------------------ #
    if include_all or (enabled_components or {}).get("flx", False):
        guide["flx_trackers"] = {
            "family": "Flex Objects Tracking (FLX)",
            "creation_modes": {
                "use_case_wizard": {
                    "description": (
                        "Creates a tracker from the use-case library. "
                        "The library provides vendor-categorised use cases with ready-made searches."
                    ),
                    "wizard_steps": [
                        "Step 1: Tracker name and deployment (local or remote)",
                        "Step 2: Use-case library selection (vendor -> category -> use-case reference)",
                        "Step 3: Search filters (narrow the scope of the use-case search)",
                        "Step 4: Time ranges (earliest / latest)",
                        "Step 5: Cron schedule",
                        "Step 6: Simulation run + tracker options configuration",
                    ],
                    "tracker_options": {
                        "metrics_definition": "Map metric names to result fields for outlier detection",
                        "default_thresholds": "Threshold conditions per metric (operator, value, score)",
                        "max_sec_inactive": "Seconds of inactivity before entity is flagged",
                        "disruption_min_time": "Minimum disruption duration before alerting",
                        "drilldown_search": "Custom SPL for entity investigation drill-down",
                        "outlier_ml_params": "ML outlier-detection parameters per metric",
                    },
                },
                "converging_wizard": {
                    "description": (
                        "Creates a converging tracker that aggregates entities from multiple "
                        "components or tenants into a consolidated service-level view."
                    ),
                    "wizard_steps": [
                        "Step 1: Tracker name, object name, group assignment, tenant+component scope selection",
                        "Step 2: Search filters (optional constraint to narrow converged entities)",
                        "Step 3: Simulation and validation",
                    ],
                    "key_options": {
                        "consider_orange_as_up": "Whether orange (warning) counts as healthy in convergence (default False)",
                        "min_pct_for_green": "Minimum percentage of healthy entities for green status (0-100, default 100)",
                    },
                },
            },
        }

    # ------------------------------------------------------------------ #
    # Fields Quality Monitoring (FQM)
    # ------------------------------------------------------------------ #
    if include_all or (enabled_components or {}).get("fqm", False):
        guide["fqm_trackers"] = {
            "family": "Fields Quality Monitoring (FQM)",
            "tracker_types": {
                "cim": {
                    "description": "Monitors field quality against CIM (Common Information Model) data models.",
                    "wizard_steps": [
                        "Step 1: Environment target (account selection)",
                        "Step 2: Data-model and node selection (loaded from available CIM models)",
                        "Step 3: Dictionary configuration (new or existing, allow_unknown, allow_missing_null, fields_success_threshold)",
                        "Step 4: Dictionary preview (review fields and validation rules)",
                        "Step 5: Thresholds (field-level and global success / coverage thresholds)",
                        "Step 6: Collection strategy (sampling-based or head-based event selection)",
                        "Step 7: Main settings (tracker name, time range, cron schedule, summary index)",
                    ],
                },
                "raw": {
                    "description": "Monitors field quality from raw event field extractions (non-CIM).",
                    "wizard_steps": [
                        "Step 1: Environment target (account selection)",
                        "Step 2: Search configuration (event constraint, event limit for field discovery)",
                        "Step 3: Dictionary configuration (new or existing, allow_unknown, allow_missing_null, fields_success_threshold)",
                        "Step 4: Dictionary preview (review discovered fields)",
                        "Step 5: Thresholds (field-level and global success / coverage thresholds)",
                        "Step 6: Collection strategy (sampling-based or head-based)",
                        "Step 7: Main settings (tracker name, time range, cron schedule, summary index)",
                    ],
                },
                "monitor": {
                    "description": (
                        "Monitor-only tracker: checks existing field-quality entities "
                        "without performing new field extraction. Simplified wizard."
                    ),
                },
            },
            "dictionary_concepts": {
                "description": (
                    "A dictionary defines expected fields and their validation rules. "
                    "Can be created fresh or reuse an existing one."
                ),
                "key_settings": {
                    "allow_unknown": "Accept fields not listed in the dictionary (True/False)",
                    "allow_missing_null": "Accept null / missing values for expected fields (True/False)",
                    "fields_success_threshold": "Minimum success percentage per field (0-100, default 85%)",
                },
                "management": "Dictionaries can be imported / exported for reuse across trackers.",
            },
            "collection_strategies": {
                "sampling": "Randomly samples events within the time window (reduces search cost).",
                "head": "Takes the first N events from the time window (deterministic).",
            },
        }

    # ------------------------------------------------------------------ #
    # Workload Monitoring (WLK)
    # ------------------------------------------------------------------ #
    if include_all or (enabled_components or {}).get("wlk", False):
        guide["wlk_trackers"] = {
            "family": "Workload Monitoring (WLK)",
            "wizard_steps": [
                "Step 1: Tracker type selection and deployment (local or remote)",
                "Step 2: Custom search filters (optional constraint to narrow scope)",
                "Step 3: Optional overgroup field (custom grouping, default 'app')",
                "Step 4: Test and review (simulation of discovered workload entities)",
                "Step 5: Validate and create",
            ],
            "tracker_types": {
                "main": {
                    "description": "Primary tracker monitoring saved-search execution health from scheduler logs.",
                    "constraint_behavior": "Honors custom search filters.",
                },
                "introspection": {
                    "description": "Monitors search activity from Splunk introspection data.",
                    "constraint_behavior": "Honors custom search filters.",
                },
                "scheduler": {
                    "description": "Monitors scheduler-level health metrics (queue depth, concurrency, lag).",
                    "constraint_behavior": "Honors custom search filters.",
                },
                "metadata": {
                    "description": "Collects metadata about saved searches (app, owner, schedule).",
                    "constraint_behavior": "Honors custom search filters.",
                },
                "orphan": {
                    "description": "Detects orphaned searches still in the scheduler but deleted from the app.",
                    "constraint_behavior": "Ignores custom filters (scans all scheduler activity).",
                },
                "inactive_entities": {
                    "description": "Detects entities whose last activity exceeds the inactivity threshold.",
                    "constraint_behavior": "Ignores custom filters.",
                },
                "splunkcloud_svc": {
                    "description": "Monitors Splunk Cloud service-level scheduled searches (sc_admin owned).",
                    "constraint_behavior": "Honors custom search filters.",
                },
                "notable": {
                    "description": "Monitors Enterprise Security notable-event generation searches.",
                    "constraint_behavior": "Ignores custom filters (targets notable searches).",
                },
            },
            "overgroup_field": (
                "Groups entities for higher-level aggregation. Default is 'app' "
                "(group by Splunk app). Can be set to any field from the workload data."
            ),
        }

    return guide


def _build_elastic_sources_creation_guide():
    """
    Build detailed elastic-sources creation knowledge (DSM-specific).
    """
    return {
        "description": (
            "Elastic sources extend DSM monitoring to custom data-source definitions "
            "beyond standard tstats discovery. They allow monitoring of data sources "
            "that may not appear in default index/sourcetype tracking."
        ),
        "types": {
            "shared": {
                "description": (
                    "All shared sources are stored in a lookup and executed by a single "
                    "scheduled report that runs them in parallel (default 3 slots)."
                ),
                "best_for": "Well-performing searches, ideally tstats-based.",
            },
            "dedicated": {
                "description": (
                    "Each dedicated source has its own individual scheduled report. "
                    "Easier to customise and troubleshoot independently."
                ),
                "best_for": "Large-volume sources or advanced use cases with custom logic.",
            },
        },
        "wizard_steps": [
            "Step 1: Identifier and deployment (unique object name, local or remote account)",
            "Step 2: Search mode and search constraint",
            "Step 3: Index and sourcetype definition (elastic_index, elastic_sourcetype)",
            "Step 4: Time ranges (earliest / latest for the search window)",
            "Step 5: Test and review (simulation to verify data is found)",
            "Step 6: Validate and create (choose shared or dedicated)",
        ],
        "search_modes": {
            "local": ["tstats", "raw", "from", "mstats", "mpreview"],
            "remote": ["remote_tstats", "remote_raw", "remote_from", "remote_mstats", "remote_mpreview"],
            "note": "Remote modes execute via splunkremotesearch on a configured remote deployment.",
        },
        "key_fields": {
            "object": "Unique identifier for the elastic source (used as entity key)",
            "search_mode": "One of the 10 supported search modes",
            "search_constraint": "SPL constraint specific to the chosen search mode",
            "elastic_index": "Pseudo index value (subject to blocklist restrictions)",
            "elastic_sourcetype": "Pseudo sourcetype value (subject to blocklist restrictions)",
            "earliest_time": "Earliest time boundary (e.g. '-4h')",
            "latest_time": "Latest time boundary (e.g. '+4h')",
        },
        "use_cases": [
            "Monitoring data from remote Splunk deployments not visible locally",
            "Tracking custom index/sourcetype combinations that default discovery misses",
            "Monitoring data with non-standard naming conventions",
            "Monitoring lookup or data-model sources (using 'from' mode)",
            "Monitoring metrics indexes with mstats/mpreview when standard discovery is insufficient",
        ],
    }


def _build_threshold_management_guide(enabled_components=None):
    """
    Build detailed threshold-management knowledge per component family.

    When enabled_components is None (e.g. Virtual Tenants context), all
    component sections are included.  When a dict is provided, only sections
    for enabled components are returned to save tokens.
    """
    include_all = enabled_components is None
    guide = {}

    # ------------------------------------------------------------------ #
    # DSM / DHM — Lag monitoring policies & lagging classes
    # ------------------------------------------------------------------ #
    dsm_enabled = include_all or (enabled_components or {}).get("dsm", False)
    dhm_enabled = include_all or (enabled_components or {}).get("dhm", False)

    if dsm_enabled or dhm_enabled:
        feeds_section = {
            "family": "Feeds Lag Monitoring (DSM / DHM)",
            "per_entity_lag_policy": {
                "description": (
                    "Each DSM / DHM entity can have individual lag thresholds set "
                    "through the entity detail modal. These override the defaults "
                    "and lagging-class assignments when 'override lagging class' is enabled."
                ),
                "fields": {
                    "data_max_delay_allowed": (
                        "Maximum allowed delay in seconds — time since the last event. "
                        "If no event is received within this window, the entity enters red state."
                    ),
                    "data_max_lag_allowed": (
                        "Maximum allowed ingestion latency in seconds — the difference "
                        "between event time and index time."
                    ),
                    "data_max_delay_allowed_locked": (
                        "The threshold lock — the single user-facing control for how "
                        "TrackMe manages this entity's delay/latency thresholds. "
                        "'true' = LOCKED: the operator manages the thresholds manually; "
                        "TrackMe never auto-adjusts them (adaptive delay and lagging "
                        "classes are bypassed) and a reconcile routine restores the "
                        "requested values if anything changes them. 'false'/absent = "
                        "UNLOCKED: TrackMe auto-manages the thresholds (adaptive delay "
                        "and/or lagging classes). When a user asks why a threshold "
                        "changed, check this first."
                    ),
                    "data_override_lagging_class": (
                        "Internal flag derived from the threshold lock (locked => 'true'). "
                        "When 'true', a matching lagging class does NOT override the "
                        "entity's thresholds. Operators control this via the lock, not "
                        "directly."
                    ),
                    "allow_adaptive_delay": (
                        "Internal flag derived from the threshold lock (locked => 'false'). "
                        "When 'true', the adaptive-delay engine may auto-adjust the delay "
                        "threshold. Operators control this via the lock, not directly."
                    ),
                    "variable_delay_policy": (
                        "Delay policy for the entity: 'static' uses a single "
                        "data_max_delay_allowed threshold, 'variable' uses time-based "
                        "slots with different thresholds for different day/hour periods. "
                        "Defined at entity discovery based on the tenant's default delay "
                        "configuration and can be changed per entity afterward. In "
                        "'variable' mode the delay value comes from the slots and "
                        "lagging-class delay rules are overridden (latency rules still "
                        "apply). Whether automation may touch the thresholds at all is "
                        "governed by the threshold lock (data_max_delay_allowed_locked), "
                        "not by this policy."
                    ),
                    "future_tolerance": (
                        "Tolerance for future-dated events. Events timestamped beyond "
                        "this value ahead of current time trigger alerts. "
                        "Set to 'disabled' to use the default 7-day tolerance."
                    ),
                },
                "impact_score_weights": {
                    "delay_weight": "Custom weight (0-100) for delay-threshold breaches in the impact score.",
                    "latency_weight": "Custom weight (0-100) for latency-threshold breaches in the impact score.",
                    "note": "Defaults come from the tenant score configuration and can be overridden per entity.",
                },
                "advanced_tools": {
                    "thresholds_simulation": "Run a simulation to evaluate how threshold changes would affect the entity state.",
                    "auto_definition_helpers": "Automated helpers that analyse historical patterns and suggest optimal thresholds.",
                },
            },
            "lagging_classes": {
                "description": (
                    "Lagging classes define reusable threshold policies that apply to "
                    "groups of entities. Instead of tuning entities one by one, assign "
                    "them to a class with predefined delay and latency values."
                ),
                "variable_delay_interaction": (
                    "Important: lagging class delay values (value_delay) have no effect on entities "
                    "using variable delay (variable_delay_policy='variable'). These entities manage "
                    "their delay through time-based slots, which automatically override lagging class "
                    "delay rules. Latency values (value_lag) from lagging classes remain effective "
                    "for all entities regardless of their delay policy."
                ),
                "class_fields": {
                    "name": "Unique class name",
                    "level": "Matching level: 'index', 'sourcetype', or 'priority'",
                    "object": "Target component: 'splk-dsm', 'splk-dhm', or 'all'",
                    "value_delay": "Delay threshold for the class (seconds). Not applied to entities using variable delay.",
                    "value_lag": "Latency threshold for the class (seconds). Applied to all entities.",
                },
                "conflict_resolution": {
                    "dsm": (
                        "Applied in order: index → sourcetype → priority. "
                        "First matching class wins."
                    ),
                    "dhm": (
                        "Highest lagging value takes precedence. If a host spans "
                        "multiple sourcetypes, the host global max lag cannot be "
                        "lower than the highest sourcetype value."
                    ),
                },
                "per_entity_override": (
                    "A LOCKED entity (data_max_delay_allowed_locked='true') bypasses all "
                    "lagging-class assignments and adaptive delay, and uses the "
                    "operator's own thresholds. The lock is the single control for "
                    "this; the legacy data_override_lagging_class / allow_adaptive_delay "
                    "flags are derived from it."
                ),
            },
        }
        guide["feeds_lag_monitoring"] = feeds_section

    # ------------------------------------------------------------------ #
    # DSM / DHM — Variable delay thresholds (time-based)
    # ------------------------------------------------------------------ #
    if dsm_enabled or dhm_enabled:
        guide["variable_delay_thresholds"] = {
            "family": "Variable Delay Thresholds (DSM / DHM)",
            "description": (
                "Variable delay is an alternative to static delay thresholds for DSM and DHM entities. "
                "Instead of a single fixed data_max_delay_allowed value, entities can have time-based "
                "delay thresholds that vary by day-of-week and hour-of-day. This is essential for data "
                "sources with natural activity patterns (e.g. batch jobs running only on weekdays, hosts "
                "inactive on weekends, or reduced data flow outside business hours). Without variable "
                "delay, administrators are forced to set overly large static thresholds to avoid false "
                "alerts during quiet periods, which reduces monitoring value during active periods."
            ),
            "threshold_hierarchy": (
                "Variable delay sits at the top of the delay threshold hierarchy. When an entity has "
                "variable_delay_policy='variable': (1) the static data_max_delay_allowed is ignored "
                "for delay monitoring, (2) lagging class delay rules are bypassed (latency rules still "
                "apply), (3) adaptive delay is NOT auto-disabled by variable mode — whether automation "
                "(adaptive delay / lagging classes) may change the thresholds is governed by the "
                "threshold lock (data_max_delay_allowed_locked), not by this policy; when the entity is "
                "unlocked and opted into adaptive delay, the adaptive-delay engine may instead refresh "
                "the variable-delay slot thresholds from history. The decision maker evaluates "
                "the current day-of-week and hour-of-day against the entity's slot configuration to "
                "determine the active delay threshold at each monitoring cycle."
            ),
            "tenant_level_default": {
                "description": (
                    "The default delay policy (static or variable) is configured at the tenant level, "
                    "independently for DSM and DHM. When new entities are discovered by a tracker, "
                    "they inherit the tenant's default delay configuration including the policy, "
                    "time slots, and fallback threshold."
                ),
                "configuration_fields": {
                    "dsm_default_delay_policy": "Default delay policy for DSM entities: 'static' or 'variable'",
                    "dhm_default_delay_policy": "Default delay policy for DHM entities: 'static' or 'variable'",
                    "default_delay_threshold_sec": "Default static threshold (seconds) used as fallback",
                    "variable_delay_default_slots": "Default time slot configuration (JSON) applied to new entities",
                    "variable_delay_default": "Default fallback delay value for variable mode (seconds)",
                },
                "where_to_configure": (
                    "Set during tenant creation via the 'Default Delay Configuration' wizard step, "
                    "or update afterward via 'Manage: Default Delay' in the Tenant Home Actions menu."
                ),
            },
            "slot_model": {
                "description": (
                    "Each variable delay configuration consists of named time slots and a default "
                    "fallback value. Slots are evaluated in order — the first matching slot wins."
                ),
                "slot_fields": {
                    "slot_name": "A descriptive name for the slot (e.g. 'business_hours', 'weekends')",
                    "days": "List of day-of-week numbers (0=Monday through 6=Sunday)",
                    "hours": "List of hour numbers (0-23) during which this slot applies",
                    "max_delay_allowed": "Maximum allowed delay in seconds for this time slot",
                },
                "default_fallback": (
                    "A default max_delay_allowed value covers any day/hour combination not matched "
                    "by any named slot. This ensures there is always a threshold even if no slot "
                    "matches the current time."
                ),
                "evaluation_logic": (
                    "At each monitoring cycle, the decision maker checks the current server time "
                    "against each slot's day+hour ranges. The first slot whose days and hours "
                    "include the current time provides the active max_delay_allowed. If no slot "
                    "matches, the default fallback value is used."
                ),
                "timezone": (
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
            "template_presets": {
                "description": (
                    "Template presets provide ready-made slot configurations for common scenarios. "
                    "They can be applied at the tenant level (default for new entities) or per entity."
                ),
                "available_presets": [
                    "Business hours: tighter thresholds during working hours (Mon-Fri 08-18), relaxed evenings and weekends",
                    "Weekday/weekend: different thresholds for weekdays vs weekend days",
                    "Three-tier: business hours / evenings / weekends with three distinct threshold levels",
                ],
            },
            "auto_compute": (
                "Thresholds can be automatically computed from historical mstats data. The auto-compute "
                "analyzes perc95 or perc99 delay per day-of-week and hour-of-day from the entity's "
                "metrics history and generates optimized slot configurations. This removes the guesswork "
                "from setting initial thresholds."
            ),
            "auto_review": {
                "description": (
                    "When 'Variable delay auto review' is enabled at the tenant level "
                    "(variable_delay_auto_review_enabled), a scheduled review tracker periodically "
                    "re-evaluates each entity's slot thresholds against current data patterns."
                ),
                "mechanism": (
                    "The review tracker compares observed delay metrics against configured slot "
                    "thresholds. If the observed delay has shifted by more than 20%% from the "
                    "configured threshold for a slot, the threshold is automatically updated. "
                    "This ensures thresholds stay aligned with evolving data behavior without "
                    "manual intervention."
                ),
                "enablement": (
                    "Enabled at the tenant level via the tenant configuration. When enabled, "
                    "the review tracker runs on a schedule and processes all entities that have "
                    "variable_delay_policy='variable' and the automatic review flag enabled."
                ),
            },
            "per_entity_override": {
                "description": (
                    "Each entity's variable delay configuration can be overridden independently "
                    "of the tenant default. Per-entity changes do not affect other entities or "
                    "the tenant default."
                ),
                "possible_overrides": [
                    "Switch between static and variable delay policy",
                    "Add, modify, or remove individual time slots",
                    "Change the default fallback threshold",
                    "Apply auto-compute to regenerate thresholds from the entity's own history",
                    "Enable or disable auto-review for the specific entity",
                ],
                "management": (
                    "Per-entity configuration is managed via the entity detail modal (Variable Delay "
                    "tab) or via the REST API at /services/trackme/v2/splk_variable_delay endpoints."
                ),
            },
            "feature_interactions": {
                "adaptive_delay": (
                    "NOT mutually exclusive (since 2.4.1). allow_adaptive_delay is an independent "
                    "per-entity opt-in, derived from the threshold lock; when the entity is unlocked "
                    "and opted in, the adaptive-delay engine refreshes the variable-delay slot "
                    "thresholds from history (the honour-existing-slots path) rather than the static "
                    "value. Reverting to static preserves the stored allow_adaptive_delay — it is NOT "
                    "auto-toggled. To stop adaptive delay (and lagging classes) from changing the "
                    "thresholds, LOCK the entity (data_max_delay_allowed_locked) — that, not the "
                    "variable policy, is the single control."
                ),
                "lagging_classes": (
                    "Variable delay overrides lagging class delay rules for the entity. Latency "
                    "rules (data_max_lag_allowed) from lagging classes still apply normally."
                ),
                "monitoring_time_policy": (
                    "Independent and complementary. Variable delay controls the threshold value "
                    "(how long a gap is tolerable), while monitoring time policy controls when "
                    "monitoring is active (whether to evaluate at all). They coexist without conflict."
                ),
                "static_data_max_delay_allowed": (
                    "When variable delay is active, the static data_max_delay_allowed field on the "
                    "entity stores the default fallback value but is not used for delay evaluation. "
                    "The time-slot thresholds take precedence."
                ),
            },
        }

    # ------------------------------------------------------------------ #
    # MHM — Metric category lagging policies
    # ------------------------------------------------------------------ #
    if include_all or (enabled_components or {}).get("mhm", False):
        guide["mhm_metric_policies"] = {
            "family": "Metrics Host Monitoring (MHM)",
            "description": (
                "MHM uses metric-category-level policies instead of per-entity "
                "thresholds. Each metric category (e.g. system metrics, custom "
                "metrics) can have its own maximum-lag threshold."
            ),
            "policy_fields": {
                "metric_category": "The metric category name (discovered from the tenant's metric data)",
                "metric_max_lag_allowed": "Maximum allowed lag for this metric category (seconds)",
            },
            "behaviour": (
                "All MHM entities whose metric category matches the policy inherit "
                "the configured threshold. Policies are managed through the Metric "
                "Policies management modal."
            ),
        }

    # ------------------------------------------------------------------ #
    # FLX / FQM — Dynamic threshold management
    # ------------------------------------------------------------------ #
    flx_enabled = include_all or (enabled_components or {}).get("flx", False)
    fqm_enabled = include_all or (enabled_components or {}).get("fqm", False)

    if flx_enabled or fqm_enabled:
        components_label = []
        if flx_enabled:
            components_label.append("FLX")
        if fqm_enabled:
            components_label.append("FQM")

        guide["dynamic_thresholds"] = {
            "family": "Dynamic Thresholds (%s)" % " / ".join(components_label),
            "description": (
                "FLX and FQM entities support dynamic threshold conditions that "
                "determine entity health status. Thresholds are configured per entity "
                "and evaluated against the entity's metrics on each tracker run."
            ),
            "threshold_fields": {
                "metric_name": "Name of the metric to evaluate (populated from the entity's search results)",
                "value": "The threshold value to compare against",
                "operator": "Comparison operator: >, <, >=, <=, ==, !=",
                "condition_true": (
                    "True = the condition MUST be met for the entity to be healthy. "
                    "False = the condition must NOT be met for the entity to be healthy."
                ),
                "score": "Impact score weight (0-100, default 100). Higher values increase priority on breach.",
                "comment": "Optional description for auditability",
            },
            "operators": [
                ">= (greater than or equal to)",
                "> (greater than)",
                "< (less than)",
                "<= (less than or equal to)",
                "== (equal to)",
                "!= (not equal to)",
            ],
            "management": (
                "Add, edit, or delete thresholds through the entity detail modal. "
                "Each entity can have multiple threshold conditions. All conditions "
                "are evaluated independently — any single breach can trigger a status change."
            ),
            "initial_thresholds": (
                "When a hybrid tracker is created (FLX use-case wizard or FQM CIM/Raw wizard), "
                "default thresholds are established by the tracker definition. "
                "These can then be refined per entity."
            ),
        }

    return guide


def _build_knowledge_reference(
    enabled_components=None,
    splunkd_uri=None,
    session_key=None,
):
    """
    Build a comprehensive static knowledge reference section that provides
    the AI assistant with deep product knowledge about TrackMe features,
    configuration, and operations. This enables the AI to answer 'how do I'
    questions accurately without additional API calls.

    ``splunkd_uri`` and ``session_key`` are threaded through to
    ``build_concierge_knowledge`` so the Concierge knowledge block can
    embed a compact projection of the live API catalog (the chat LLM's
    sole way of seeing the real path universe — without it, the LLM
    falls back to training-data guesses and fabricates paths that don't
    exist).
    """
    knowledge = {
        "component_types": {
            "splk-dsm": {
                "name": "Data Source Monitoring (DSM)",
                "description": (
                    "Monitors data ingestion health at the index/sourcetype level. "
                    "Tracks event delay (time since last event), ingestion latency "
                    "(difference between event time and index time), and optionally "
                    "distinct host counts. Supports tstats, raw, from, and mstats "
                    "search modes. Part of the Splunk Feeds tracking component."
                ),
                "key_metrics": [
                    "Event delay (data_max_delay_allowed)",
                    "Ingestion latency (data_max_lag_allowed)",
                    "Future event tolerance",
                    "Distinct host count (min_dcount_host)",
                ],
                "specific_features": [
                    "Data sampling for event quality analysis",
                    "Elastic sources (shared and dedicated) for flexible monitoring",
                    "Host distinct count monitoring",
                    "Disruption tracking for data forwarding issues",
                ],
                "use_when": "You need to monitor that specific index/sourcetype combinations are receiving data on time.",
            },
            "splk-dhm": {
                "name": "Data Host Monitoring (DHM)",
                "description": (
                    "Monitors data delivery health at the host level. Tracks the same "
                    "delay and latency metrics as DSM but aggregated per host across "
                    "index/sourcetype combinations. Part of the Splunk Feeds tracking component."
                ),
                "key_metrics": [
                    "Event delay per host",
                    "Ingestion latency per host",
                    "Future event tolerance",
                ],
                "specific_features": [
                    "Host-level aggregation across all sourcetypes",
                    "Disruption tracking for host-level data gaps",
                ],
                "use_when": "You need to monitor that specific hosts are sending data on time.",
            },
            "splk-mhm": {
                "name": "Metrics Host Monitoring (MHM)",
                "description": (
                    "Monitors metrics index health at the host/metric category level. "
                    "Tracks metric lag (time since last metric data point). Part of the "
                    "Splunk Feeds tracking component."
                ),
                "key_metrics": [
                    "Metric lag (metric_max_lag_allowed)",
                    "Future metric tolerance",
                ],
                "specific_features": [
                    "Metrics-specific indexing health",
                    "Metric category grouping",
                ],
                "use_when": "You need to monitor that metrics data (from Splunk metrics indexes) is being collected on time.",
            },
            "splk-flx": {
                "name": "Flex Objects Tracking (FLX)",
                "description": (
                    "Custom use-case based monitoring. Users define 'magic searches' that "
                    "produce entity data with status conditions. Supports any monitoring "
                    "scenario that can be expressed as a Splunk search. Entities can have "
                    "custom status fields and threshold conditions defined in the tracker."
                ),
                "key_metrics": [
                    "Inactivity timeout (max_sec_inactive)",
                    "Custom threshold conditions (defined per use case)",
                ],
                "specific_features": [
                    "Use-case and converging tracker wizards",
                    "Custom default metrics and drilldown searches",
                    "Group renaming and organization",
                    "Flexible status evaluation rules",
                ],
                "use_when": "You need custom monitoring that doesn't fit DSM/DHM/MHM patterns.",
            },
            "splk-fqm": {
                "name": "Fields Quality Monitoring (FQM)",
                "description": (
                    "Monitors field extraction quality for CIM and non-CIM data models. "
                    "Tracks field extraction success rate and coverage percentage. Uses "
                    "data sampling to assess field quality without processing all events."
                ),
                "key_metrics": [
                    "Field extraction success rate (percent_success)",
                    "Field coverage (percent_coverage)",
                ],
                "specific_features": [
                    "CIM-based wizard for automatic field discovery",
                    "Dictionary management for custom field definitions",
                    "Dictionary import/export capabilities",
                ],
                "use_when": "You need to ensure CIM compliance or field extraction quality.",
            },
            "splk-wlk": {
                "name": "Workload Monitoring (WLK)",
                "description": (
                    "Monitors saved search and scheduled job execution health. Tracks "
                    "execution errors, skipping rate, orphaned searches, and execution "
                    "delays by analyzing Splunk scheduler logs and introspection data."
                ),
                "key_metrics": [
                    "Skipping percentage",
                    "Execution error count",
                    "Orphan search detection",
                    "Execution delay detection",
                ],
                "specific_features": [
                    "Search versioning and change detection",
                    "Orphan search identification (deleted but still scheduled)",
                    "Out-of-monitoring-time detection",
                ],
                "use_when": "You need to monitor the health of scheduled searches and reports.",
            },
        },
        "health_states": {
            "green": {
                "label": "Healthy",
                "description": "Entity is healthy, all metrics within expected parameters. No anomalies detected.",
            },
            "red": {
                "label": "Alert",
                "description": (
                    "Anomaly detected. Possible causes: lag threshold breached, data gap, "
                    "missing data, future data tolerance exceeded, host count drop, "
                    "field quality failure, search execution errors, skipping, outlier detection."
                ),
            },
            "orange": {
                "label": "Warning / Out of scope",
                "description": (
                    "Entity is out of monitoring scope (impact score below threshold) "
                    "or in a warning state approaching thresholds."
                ),
            },
            "blue": {
                "label": "Informational",
                "description": (
                    "Entity is acknowledged by a user, in maintenance mode, or part of a "
                    "logical group where the group-level conditions are not met."
                ),
            },
        },
        "configuration_flags": {
            "sampling": {
                "description": "Enables data sampling for DSM entities, reducing search load by analyzing a subset of events.",
                "applies_to": "DSM",
                "how_to_configure": (
                    "Enable at tenant creation or update via the tenant administration endpoint. "
                    "Per-entity sampling settings can be managed via the data sampling management modal."
                ),
                "key_settings": [
                    "sampling iterations interval (min time between samples)",
                    "records per entity (sample size)",
                    "records saved per model (stored results)",
                    "model match percentage thresholds (inclusive/exclusive)",
                ],
            },
            "sampling_obfuscation": {
                "description": "When sampling is enabled, obfuscates sensitive data in sample results to protect PII.",
                "applies_to": "DSM",
                "how_to_configure": "Enable at tenant level. When active, raw event data in samples is masked.",
            },
            "adaptive_delay": {
                "description": (
                    "Dynamically adjusts delay thresholds based on observed data patterns. "
                    "Reduces false alerts by learning normal ingestion timing for each entity."
                ),
                "applies_to": "DSM, DHM",
                "how_to_configure": "Enable at tenant creation or update. Works automatically once enabled.",
            },
            "variable_delay": {
                "description": (
                    "Assigns time-based delay thresholds that vary by day-of-week and hour-of-day "
                    "to DSM/DHM entities, instead of a single static value. Each entity can have "
                    "named time slots (e.g. business hours, nights, weekends) with different "
                    "max_delay_allowed values. The first matching slot wins; a default fallback "
                    "covers unmatched periods. This addresses natural data activity patterns "
                    "(e.g. no activity during weekends) that would otherwise force administrators "
                    "to set overly large static thresholds."
                ),
                "applies_to": "DSM, DHM",
                "how_to_configure": (
                    "1. Set the Default Delay Configuration during tenant creation (wizard step) "
                    "or update it afterward via 'Manage: Default Delay' in the Tenant Home Actions menu. "
                    "2. Choose 'variable' as the default delay policy for DSM and/or DHM. "
                    "3. Configure default time slots (day/hour ranges with thresholds) or use a "
                    "template preset (business hours, weekday/weekend, three-tier). "
                    "4. Optionally use auto-compute to derive thresholds from historical mstats data "
                    "(perc95/perc99 per day/hour). "
                    "5. New entities discovered by trackers inherit the tenant default delay configuration. "
                    "6. Per-entity overrides can be made via the entity detail modal or via the REST API."
                ),
                "key_settings": [
                    "Default delay policy per component: static or variable (dsm_default_delay_policy, dhm_default_delay_policy)",
                    "Default time slots with day-of-week (0=Monday to 6=Sunday), hour ranges (0-23), and max_delay_allowed per slot",
                    "Default fallback threshold for periods not covered by any slot",
                    "Template presets for quick configuration (business hours, weekday/weekend, three-tier)",
                    "Auto-compute from historical data (perc95/perc99 per day/hour)",
                ],
                "feature_interactions": {
                    "adaptive_delay": (
                        "NOT mutually exclusive (since 2.4.1). allow_adaptive_delay is an "
                        "independent per-entity opt-in, derived from the threshold lock; when the "
                        "entity is unlocked and opted in, adaptive delay refreshes the variable-delay "
                        "slot thresholds from history rather than the static value. LOCK the entity "
                        "(data_max_delay_allowed_locked) to stop adaptive delay (and lagging classes) "
                        "from changing the thresholds."
                    ),
                    "lagging_classes": (
                        "Variable delay overrides lagging class delay rules for the entity. "
                        "Latency rules from lagging classes still apply."
                    ),
                    "monitoring_time_policy": (
                        "Independent. Variable delay and monitoring time policy coexist — "
                        "variable delay controls the threshold value, monitoring time controls "
                        "when monitoring is active."
                    ),
                },
                "auto_review": (
                    "When 'Variable delay auto review' is enabled at the tenant level "
                    "(variable_delay_auto_review_enabled), a scheduled review tracker periodically "
                    "re-computes slot thresholds from historical mstats data and updates them "
                    "if data patterns have shifted (>20% deviation). This ensures thresholds "
                    "stay aligned with evolving data behavior without manual intervention."
                ),
            },
            "mloutliers": {
                "description": (
                    "Enables machine learning outlier detection using MLTK DensityFunction algorithm. "
                    "Trains models on entity metrics (event count, latency) to detect abnormal patterns."
                ),
                "applies_to": "DSM, DHM, FLX, WLK, FQM",
                "how_to_configure": (
                    "Enable at tenant level. Per-entity outlier rules can be configured in the "
                    "outlier management modal. Key settings: detection period, time factor, "
                    "density thresholds, alert on upper/lower bounds."
                ),
                "key_settings": [
                    "Min days history for training (default: 7)",
                    "Training frequency (default: weekly)",
                    "Detection period (default: 30 days)",
                    "Density thresholds for lower/upper bounds",
                    "Alert independently on volume/latency increase/decrease",
                ],
                "tenant_scoping_2_3_22": (
                    "From v2.3.22, three tenant-level fields scope which entities outliers detection "
                    "applies to. mloutliers_priority_filter is a comma-separated list of priorities "
                    "(critical, high, medium, low) — empty means all priorities. "
                    "mloutliers_filter_expression is a Virtual-Groups-style filter expression evaluated "
                    "against each entity (priority, tags, labels, object name, sourcetype, index). "
                    "An entity is eligible for outliers detection only if it matches BOTH the priority "
                    "filter AND (when non-empty) the filter expression. mloutliers_volume_kpi is an "
                    "optional per-tenant override for the volume KPI metric used during training "
                    "(empty = inherit global default). Volume KPI applies to dsm and dhm only; flx, "
                    "fqm and wlk ignore it."
                ),
                "tenant_scoping_diagnosis": (
                    "When asked 'why is this entity not in outliers detection?' on a tenant where "
                    "mloutliers is enabled: check the entity's priority against "
                    "mloutliers_priority_filter, then evaluate mloutliers_filter_expression against "
                    "the entity's metadata (priority, tags, labels, data_index, data_sourcetype, object). "
                    "If either gate excludes the entity, the entity Outliers tab in the UI shows an "
                    "explanatory message stating the reason."
                ),
            },
            "cmdb_lookup": {
                "description": (
                    "Enables CMDB integration for entity enrichment with external asset/service "
                    "data. Enrichment happens dynamically at alert time (stateful alerts and "
                    "notable events) — the configured per-component CMDB search runs and its "
                    "output fields (ownership, criticality, contact, etc.) are injected into "
                    "the alert event and into the email notification body. CMDB values are "
                    "NOT persisted on the entity record; they are resolved on demand. "
                    "A simplified 'Manage: CMDB integration' modal provides a guided "
                    "configuration experience, and the cmdb_account field lets the CMDB "
                    "search run on a configured remote account instead of the local Splunk "
                    "instance."
                ),
                "applies_to": "All components (dsm, dhm, mhm, flx, fqm, wlk)",
                "how_to_configure": (
                    "1. Open the tenant home Features actions menu and select "
                    "'Manage: CMDB integration' for the desired component. "
                    "2. Toggle the enable flag (cmdb_lookup at tenant level). "
                    "3. Choose an account: 'local' for the local splunkd or a configured remote "
                    "account name (cmdb_account). "
                    "4. Use the guided lookup builder (with content preview and auto-generated "
                    "SPL) or switch to SPL mode to write the search directly. "
                    "5. The per-component search is stored in splk_{component}_cmdb_search on "
                    "the tenant record (top-level fields, UCC-managed via globalConfig.json)."
                ),
                "key_fields": {
                    "cmdb_lookup": "Tenant-level toggle (1=enabled default, 0=disabled).",
                    "cmdb_account": "Remote account name or empty string for local splunkd.",
                    "splk_dsm_cmdb_search / splk_dhm_cmdb_search / splk_mhm_cmdb_search / "
                    "splk_flx_cmdb_search / splk_fqm_cmdb_search / splk_wlk_cmdb_search":
                        "Per-component SPL returning enrichment fields for matched entities.",
                },
            },
            "labels": {
                "description": (
                    "Entity labels — lightweight GitHub-style colour-coded tags used for "
                    "lifecycle visibility and cross-cutting categorisation. "
                    "Each tenant has its own label registry (kv_trackme_labels_tenant_{tenant_id}) "
                    "and a separate assignments collection "
                    "(kv_trackme_label_assignments_tenant_{tenant_id}) which maps entities to "
                    "the labels they carry. Factory-seeded defaults include: blocked, "
                    "under-review, in-progress, resolved, maintenance, acknowledged, noise, "
                    "decommissioned. Labels are distinct from tags: tags are free-text "
                    "metadata assigned by policies or users and used for filtering; labels "
                    "are a managed, colour-coded, tenant-scoped vocabulary for operational "
                    "state tracking."
                ),
                "applies_to": "All components (dsm, dhm, mhm, flx, fqm, wlk)",
                "surfaced_in": [
                    "Entity tables (Labels column with colour-coded chips)",
                    "Entity describe endpoint (identity.labels + identity.labels_objects)",
                    "Stateful alert events (labels + labels_objects fields)",
                    "Notable events (labels + labels_objects fields)",
                    "Virtual Groups entity filter DSL (labels=<name> syntax)",
                ],
                "management": (
                    "Managed via the 'Manage: Labels' modal. Operators can create/edit/delete "
                    "labels (name, colour, description), and assign/unassign labels to entities "
                    "in bulk or individually from the entity overview."
                ),
                "rest_endpoints": [
                    "GET /services/trackme/v2/labels/list_labels — list tenant labels",
                    "POST /services/trackme/v2/labels/write/create_label — create a label",
                    "POST /services/trackme/v2/labels/write/update_label — update a label",
                    "POST /services/trackme/v2/labels/write/delete_label — delete a label",
                    "POST /services/trackme/v2/labels/write/assign_labels — assign labels to an entity",
                    "POST /services/trackme/v2/labels/write/unassign_labels — remove labels from an entity",
                ],
            },
            "inject_expected_sources_hosts": {
                "description": (
                    "A guided wizard for bulk-declaring entities that should exist — expected "
                    "sources for DSM trackers, expected hosts for DHM trackers — without "
                    "waiting for the next discovery cycle. Operators paste or map a list of "
                    "expected objects and TrackMe immediately creates the matching entity "
                    "records so their absence becomes visible right away rather than "
                    "silently unknown."
                ),
                "applies_to": "DSM (expected sources), DHM (expected hosts)",
                "management": (
                    "Triggered from the Actions menu > 'Inject expected sources' (DSM) or "
                    "'Inject expected hosts' (DHM). Supports lookup-to-entity field mapping "
                    "and simulate-before-execute."
                ),
                "rest_endpoints": [
                    "POST /services/trackme/v2/splk_inject_expected/admin/inject_validate — validate input",
                    "POST /services/trackme/v2/splk_inject_expected/admin/inject_simulate — preview injection",
                    "POST /services/trackme/v2/splk_inject_expected/admin/inject_execute — execute injection",
                ],
            },
            "variable_delay_templates": {
                "description": (
                    "The Quick Templates presets (business_hours, weekday_weekend, three_tier) "
                    "visible in every variable delay slot editor are customisable per tenant. "
                    "Admins can override factory defaults, add new templates, or reset. "
                    "Customisations live in "
                    "kv_trackme_common_variable_delay_templates_tenant_{tenant_id}: a custom "
                    "record whose template_id matches a factory default overrides that "
                    "default; a new template_id is appended. Deleting a custom record reverts "
                    "to factory. Greenfield tenants with no customs see the same factory "
                    "defaults as before — zero regression."
                ),
                "applies_to": "DSM, DHM variable-delay editors; FLX variable-threshold editor",
                "management": (
                    "Open 'Manage: Default Delay Configuration' > 'Manage templates'. "
                    "During tenant creation, any modification made to the variable delay "
                    "template in the wizard is auto-saved as a custom override (fail-open, "
                    "non-blocking)."
                ),
                "rest_endpoints": [
                    "POST /services/trackme/v2/splk_variable_delay/templates_list — list tenant templates (user scope)",
                    "POST /services/trackme/v2/splk_variable_delay/admin/templates_save — save/override a template",
                    "POST /services/trackme/v2/splk_variable_delay/admin/templates_reset — reset a template to factory",
                    "POST /services/trackme/v2/splk_variable_delay/admin/templates_reset_all — reset all templates",
                ],
            },
            "monitoring_time_policy": {
                "description": (
                    "Controls when monitoring is active. 'all_time' monitors continuously. "
                    "Custom policies restrict monitoring to specific hours/weekdays per entity."
                ),
                "applies_to": "All components",
                "how_to_configure": (
                    "Set default policy at tenant level. Per-entity overrides available via "
                    "the entity detail modal (monitoring hours, weekdays settings)."
                ),
            },
        },
        "alerting_concepts": {
            "stateful_alerting": {
                "description": (
                    "TrackMe uses stateful alerting: alert records track the lifecycle of anomalies "
                    "from opened to updated to closed. This prevents duplicate notifications and "
                    "provides clear audit trails of incident progression."
                ),
                "lifecycle": [
                    "opened: New anomaly detected, alert record created, initial notification sent",
                    "updated: Existing anomaly reason changed, update notification sent",
                    "closed: Entity returns to healthy state, closure notification sent",
                ],
                "record_expiration": "Stateful records expire after configurable days (default: 30 days).",
            },
            "delivery_targets": {
                "description": "Alerts can be delivered via email, custom commands, or SOAR integration.",
                "email": (
                    "Configure email account, recipients, and optionally generate charts. "
                    "Supports priority-level routing: different recipients for different priority levels."
                ),
                "commands": (
                    "Execute custom commands on opened/updated/closed events. "
                    "Supports priority-level command routing."
                ),
                "soar": "Integration with SOAR platforms for automated incident response.",
                "ai_status_report": (
                    "When AI providers are configured, an AI-generated entity status report can be included "
                    "in email notifications. The AI analyses entity context and adapts its summary to the "
                    "incident lifecycle: opened (what went wrong), updated (has the situation changed), "
                    "or closed (recovery confirmation). Enabled by default when providers are available. "
                    "Follows fail-open: emails are never blocked by AI failures."
                ),
            },
            "acknowledgment": {
                "description": (
                    "Users can acknowledge alerts to suppress notifications for a configurable duration. "
                    "Acknowledged entities show as blue state."
                ),
                "key_settings": [
                    "Default ACK duration (configurable, default: 24 hours)",
                    "Auto-remove ACK when anomaly reason changes",
                    "Auto-remove ACK when entity returns to green",
                    "Sticky vs unsticky ACK modes",
                ],
            },
            "priority_routing": {
                "description": (
                    "Different alert handling based on entity priority (low/medium/high/critical). "
                    "Email recipients and commands can be configured per priority level."
                ),
            },
            "how_to_setup": (
                "1. Navigate to the Tracking Alerts tab in Tenant Home. "
                "2. Create a new alert using the 'Create a new alert' action. "
                "3. Configure delivery target (email/commands/SOAR). "
                "4. If email delivery is selected and AI providers are configured, "
                "configure the AI Status Report option (enabled by default). "
                "5. Set priority routing if needed. "
                "6. Enable the alert."
            ),
        },
        "features_guide": {
            "data_sampling": {
                "description": (
                    "Data sampling analyzes a subset of events to build data quality models. "
                    "It detects format anomalies, unexpected event structures, and content "
                    "changes without processing all events in an index."
                ),
                "applies_to": "DSM entities",
                "how_it_works": (
                    "At configurable intervals, TrackMe samples events from each entity, "
                    "builds format models (regex patterns), and compares new samples against "
                    "stored models. Anomalies are flagged when match percentage drops below threshold."
                ),
                "management": (
                    "Managed via the Data Sampling tab in the entity detail modal. "
                    "Custom sampling rules can be created for specific index/sourcetype patterns. "
                    "Built-in rules provide baseline coverage."
                ),
            },
            "outlier_detection": {
                "description": (
                    "Machine learning based anomaly detection using MLTK DensityFunction algorithm. "
                    "Trains models on historical entity metrics to establish baselines and detect deviations."
                ),
                "applies_to": (
                    "DSM, DHM, FLX, WLK, FQM (configurable per tenant via mloutliers_allowlist). "
                    "From 2.3.22 the eligible entity set is further narrowed by "
                    "mloutliers_priority_filter and mloutliers_filter_expression."
                ),
                "how_it_works": (
                    "1. Training: Models are trained periodically on historical data (default: weekly). "
                    "2. Detection: New data is compared against the trained model. "
                    "3. Alerting: If data falls outside density thresholds, an outlier is flagged. "
                    "4. Auto-correction: Models can auto-correct with minimum deviation percentage."
                ),
                "management": (
                    "Managed via the Outliers tab in the entity detail modal. "
                    "Per-entity rules can override default settings. "
                    "Models can be manually retrained or their detection disabled."
                ),
            },
            "elastic_sources": {
                "description": (
                    "Elastic sources extend DSM monitoring to cover custom data source definitions. "
                    "They allow monitoring index/sourcetype combinations that don't appear in "
                    "standard tstats discovery."
                ),
                "types": {
                    "shared": "Shared elastic sources apply across all DSM hybrid trackers in the tenant.",
                    "dedicated": "Dedicated elastic sources apply to a specific hybrid tracker only.",
                },
                "management": (
                    "Created via the Elastic Sources wizard. Managed through the dedicated "
                    "elastic sources management modal. Can be executed on demand."
                ),
            },
            "hybrid_trackers": {
                "description": (
                    "Hybrid trackers are the scheduled searches that discover and monitor entities. "
                    "Each component type has its own tracker creation wizard with component-specific options."
                ),
                "dsm_dhm_mhm": (
                    "Feeds-based trackers with configurable search mode (tstats/raw), "
                    "break-by logic (split/merged/custom), time ranges, cron schedule, "
                    "and performance benchmarking."
                ),
                "flx": (
                    "Use-case trackers define 'magic searches' producing entity data. "
                    "Converging trackers combine multiple use cases into a single execution."
                ),
                "fqm": (
                    "CIM-based trackers for field quality monitoring. "
                    "Dictionary-driven field validation against CIM or custom models."
                ),
                "wlk": (
                    "Workload trackers monitor Splunk scheduler logs for saved search health. "
                    "Configurable environment type and grouping."
                ),
                "management": (
                    "Created via component-specific wizard in the Actions menu. "
                    "Managed via the Manage modal. Can be executed on demand."
                ),
            },
            "blocklists": {
                "description": (
                    "Blocklists prevent specific entities from being monitored. "
                    "Entries can be exact matches or regex patterns."
                ),
                "applies_to": "All components",
                "management": (
                    "Managed via the Blocklists management modal in the Actions menu. "
                    "Entries specify: object pattern (exact or regex), action (block), and optional comment."
                ),
            },
            "logical_groups": {
                "description": (
                    "Logical groups combine multiple entities into a group with collective health evaluation. "
                    "If the group-level condition is not met, individual entities show blue state. "
                    "Useful for redundant systems where only some entities need to be healthy."
                ),
                "applies_to": "All components",
                "management": (
                    "Created and managed via the Logical Groups management modal. "
                    "Define group name, member entities, and the minimum number of healthy members required."
                ),
            },
            "lagging_classes": {
                "description": (
                    "Lagging classes define threshold overrides for groups of entities. "
                    "Instead of setting thresholds entity-by-entity, assign entities to a lagging class "
                    "with predefined delay/latency thresholds."
                ),
                "applies_to": "DSM, DHM, MHM",
                "variable_delay_interaction": (
                    "Important: lagging class delay values have no effect on DSM/DHM entities using "
                    "variable delay (variable_delay_policy='variable'). Variable delay automatically "
                    "overrides lagging class delay rules. Latency values from lagging classes remain "
                    "effective for all entities regardless of their delay policy."
                ),
                "management": (
                    "Created and managed via the Lagging Classes management modal. "
                    "Define class name, delay threshold, latency threshold, and optionally "
                    "a matching pattern to auto-assign entities."
                ),
            },
            "variable_delay": {
                "description": (
                    "Variable delay provides time-based delay thresholds that vary by day-of-week "
                    "and hour-of-day. Instead of a single static max_delay_allowed value, entities "
                    "can have multiple named time slots, each with its own threshold. This is "
                    "ideal for data sources with natural activity patterns (e.g. batch jobs that "
                    "run only during business hours, or hosts that are inactive on weekends)."
                ),
                "applies_to": "DSM, DHM entities",
                "slot_model": {
                    "description": (
                        "Each variable delay configuration consists of named time slots and a default "
                        "fallback. Slots are evaluated in order — the first matching slot wins."
                    ),
                    "slot_fields": {
                        "slot_name": "A descriptive name for the slot (e.g. 'business_hours', 'weekends')",
                        "days": "List of day-of-week numbers (0=Monday through 6=Sunday)",
                        "hours": "List of hour numbers (0-23) during which this slot applies",
                        "max_delay_allowed": "Maximum allowed delay in seconds for this time slot",
                    },
                    "default_fallback": (
                        "A default max_delay_allowed value covers any day/hour combination "
                        "not matched by any slot."
                    ),
                    "timezone": (
                        "Slot days and hours are stored and evaluated in the Splunk server's "
                        "local time (the splunkd timezone; UTC on Splunk Cloud, the host's "
                        "system zone on-prem). Always reason about and write slot hours in "
                        "server-local time. The web UI is the only layer that translates: it "
                        "displays and edits slot hours in the operator's browser-local time and "
                        "converts them back to server time on save, so the KV/API always holds "
                        "server-local hours. A browser-vs-API hour difference equal to the "
                        "operator's UTC offset is expected, not a bug. Weekday labels are never "
                        "shifted, so a midnight-crossing slot keeps its server-calendar weekday."
                    ),
                },
                "template_presets": [
                    "Business hours: tighter thresholds during working hours, relaxed evenings/weekends",
                    "Weekday/weekend: different thresholds for weekdays vs weekend days",
                    "Three-tier: business hours / evenings / weekends with three threshold levels",
                ],
                "auto_compute": (
                    "Thresholds can be automatically computed from historical mstats data. "
                    "The auto-compute analyzes perc95 or perc99 delay per day/hour from the "
                    "entity's metrics history and generates optimized slot configurations."
                ),
                "auto_review": (
                    "When enabled at the tenant level (variable_delay_auto_review_enabled), "
                    "a scheduled review tracker periodically re-evaluates each entity's slot "
                    "thresholds against current data patterns. If the observed delay has shifted "
                    "by more than 20%% from the configured threshold, the slot is automatically "
                    "updated. This ensures thresholds stay aligned with evolving data behavior."
                ),
                "how_it_works": (
                    "1. The tenant administrator sets a default delay policy (static or variable) "
                    "for DSM and/or DHM during tenant creation or via 'Manage: Default Delay'. "
                    "2. When a new entity is discovered by a tracker, it inherits the tenant's "
                    "default delay configuration (policy, slots, and fallback threshold). "
                    "3. For entities with variable_delay_policy='variable', the decision maker "
                    "evaluates the current day/hour against the slot configuration to determine "
                    "the active delay threshold. "
                    "4. Per-entity overrides can change the policy, add/remove/modify slots, "
                    "or switch back to static at any time."
                ),
                "management": (
                    "Tenant-level defaults: configured via the Default Delay Configuration step "
                    "during tenant creation, or via 'Manage: Default Delay' in the Actions menu. "
                    "Per-entity configuration: managed via the entity detail modal (Variable Delay "
                    "tab) or via the REST API at /services/trackme/v2/splk_variable_delay endpoints."
                ),
            },
            "variable_threshold": {
                "description": (
                    "Variable thresholds provide time-based threshold values that vary by day-of-week "
                    "and hour-of-day. Instead of a single static threshold value, individual FLX threshold "
                    "rules can have multiple named time slots, each with its own value. This is ideal for "
                    "metrics with natural patterns (e.g. higher CPU during batch windows, lower traffic "
                    "during weekends)."
                ),
                "applies_to": "FLX entities (per threshold rule)",
                "slot_model": {
                    "description": (
                        "Each variable threshold configuration consists of named time slots and a default "
                        "fallback value. Slots are evaluated in order — the first matching slot wins."
                    ),
                    "slot_fields": {
                        "slot_name": "A descriptive name for the slot (e.g. 'business_hours', 'weekends')",
                        "days": "List of day-of-week numbers (0=Monday through 6=Sunday)",
                        "hours": "List of hour numbers (0-23) during which this slot applies",
                        "value": "The threshold value to use during this time slot",
                    },
                    "default_fallback": (
                        "A default threshold value (variable_threshold_default) covers any day/hour "
                        "combination not matched by any slot."
                    ),
                    "timezone": (
                        "Slot days and hours are stored and evaluated in the Splunk server's "
                        "local time (the splunkd timezone; UTC on Splunk Cloud, the host's "
                        "system zone on-prem). Always reason about and write slot hours in "
                        "server-local time. The web UI is the only layer that translates: it "
                        "displays and edits slot hours in the operator's browser-local time and "
                        "converts them back to server time on save, so the KV/API always holds "
                        "server-local hours. A browser-vs-API hour difference equal to the "
                        "operator's UTC offset is expected, not a bug. Weekday labels are never "
                        "shifted, so a midnight-crossing slot keeps its server-calendar weekday."
                    ),
                },
                "template_presets": [
                    "Business hours: tighter thresholds during working hours, relaxed evenings/weekends",
                    "Weekday/weekend: different thresholds for weekdays vs weekend days",
                    "Three-tier: business hours / evenings / weekends with three threshold levels",
                ],
                "how_it_works": (
                    "1. In the FLX tracker creation wizard or entity threshold modal, enable variable "
                    "threshold on a threshold rule by clicking the Clock icon. "
                    "2. Select a template preset or configure custom time slots with day/hour selections. "
                    "3. Set threshold values for each slot and a default fallback value. "
                    "4. At evaluation time, the decision maker resolves the current day/hour against "
                    "the slot configuration to determine the active threshold value. "
                    "5. Per-threshold-rule overrides allow different rules to use static or variable "
                    "values independently."
                ),
                "management": (
                    "Variable thresholds are configured per threshold rule via the entity threshold "
                    "modal (click the Clock icon next to a threshold row) or via the REST API at "
                    "/services/trackme/v2/splk_flx/write/flx_thresholds_update. Default variable "
                    "thresholds can be set during FLX hybrid tracker creation in the wizard."
                ),
            },
            "priority_policies": {
                "description": (
                    "Priority policies automatically assign priority levels (low/medium/high/critical/pending) "
                    "to entities based on matching rules. Two policy types are supported: "
                    "1) Regex-based policies match a regular expression against a configurable entity field "
                    "(default: 'object', but can target 'alias', 'data_index', 'data_sourcetype', or any custom field) "
                    "and assign a fixed priority value. "
                    "2) Lookup-based policies leverage existing Splunk lookups (CSV files or KVstore collections, "
                    "typically CMDB data) to assign priorities through field mappings — each lookup field is mapped "
                    "to an entity field, and a designated priority field in the lookup determines the assigned priority. "
                    "Lookup policies support exact (case-insensitive) and wildcard matching modes, "
                    "and optional priority value mappings to translate foreign values (e.g., P1/P2/P3) into "
                    "TrackMe priorities (critical/high/medium/low). "
                    "When multiple policies match an entity, the highest priority wins across ALL policies "
                    "(both regex and lookup). "
                    "Once applied, priority policies set 'priority_updated=1' on entities, which prevents "
                    "the decision maker from overriding the policy-assigned priority during regular evaluation cycles."
                ),
                "applies_to": "All components (dsm, dhm, mhm, flx, wlk, fqm)",
                "management": (
                    "Created and managed via the Priority Policies management modal accessible from "
                    "the Tenant Home page. The modal provides: "
                    "1) A policy table showing all configured policies with inline editing for regex policies "
                    "and an edit button for lookup policies. "
                    "2) A 'Create new policy' button opening a guided form with mode selection (Regex/Lookup). "
                    "3) A simulation feature that previews which entities would match before committing. "
                    "4) A 'Run policy tracker' button that applies all configured policies across entities. "
                    "5) Bulk selection and deletion of policies. "
                    "REST API endpoints: "
                    "- POST /services/trackme/v2/splk_priority_policies/write/priority_policies_add "
                    "(create or update a policy, supports both regex and lookup types) "
                    "- POST /services/trackme/v2/splk_priority_policies/write/priority_policies_simulate "
                    "(preview matching entities without applying) "
                    "- POST /services/trackme/v2/splk_priority_policies/write/priority_policies_apply "
                    "(apply all policies and persist priority assignments to entities) "
                    "- POST /services/trackme/v2/splk_priority_policies/priority_policies_show "
                    "(list configured policies for a tenant/component)"
                ),
            },
            "tag_policies": {
                "description": (
                    "Tag policies automatically assign tags to entities based on matching rules. "
                    "Two policy types are supported: "
                    "1) Regex-based policies match a regular expression against the entity 'object' field "
                    "and assign a comma-separated list of tag values when matched. "
                    "2) Lookup-based policies leverage existing Splunk lookups (CSV files or KVstore collections, "
                    "typically CMDB data) to assign tags through field mappings — each lookup field is mapped "
                    "to an entity field, and a designated tags field in the lookup determines the assigned tags. "
                    "Lookup policies support exact (case-insensitive) and wildcard matching modes, "
                    "and a configurable tags separator (default comma) for multi-value tag fields. "
                    "Tags assigned by policies are stored in the 'tags' field on entities (as an auto-computed "
                    "list), while manually added tags are stored separately in the 'tags_manual' field. "
                    "The combined tags (auto + manual) provide classification and filtering capabilities "
                    "across the monitoring interface."
                ),
                "applies_to": "All components (dsm, dhm, mhm, flx, wlk, fqm)",
                "management": (
                    "Created and managed via the Tag Policies management modal accessible from "
                    "the Tenant Home page. The modal provides: "
                    "1) A policy table showing all configured policies with inline editing for regex policies "
                    "and an edit button for lookup policies. "
                    "2) A 'Create new policy' button opening a guided form with mode selection (Regex/Lookup). "
                    "3) A simulation feature that previews which entities would match before committing. "
                    "4) A 'Run policy tracker' button that applies all configured policies across entities. "
                    "5) Bulk selection and deletion of policies. "
                    "REST API endpoints: "
                    "- POST /services/trackme/v2/splk_tag_policies/write/tag_policies_add "
                    "(create or update a policy, supports both regex and lookup types) "
                    "- POST /services/trackme/v2/splk_tag_policies/write/tag_policies_simulate "
                    "(preview matching entities without applying) "
                    "- POST /services/trackme/v2/splk_tag_policies/write/tag_policies_apply "
                    "(apply all policies and persist tag assignments to entities) "
                    "- POST /services/trackme/v2/splk_tag_policies/tag_policies_show "
                    "(list configured policies for a tenant/component)"
                ),
            },
            "sla_policies": {
                "description": (
                    "SLA policies assign SLA classes to entities for availability tracking. "
                    "SLA classes are globally defined with availability thresholds (e.g., 'gold' = 99.9%, "
                    "'silver' = 99.5%) and SLA calculations account for maintenance windows and bank holidays. "
                    "Two policy types are supported: "
                    "1) Regex-based policies match a regular expression against the entity 'object' field "
                    "and assign a specific SLA class when matched. "
                    "2) Lookup-based policies leverage existing Splunk lookups (CSV files or KVstore collections, "
                    "typically CMDB data) to assign SLA classes through field mappings — each lookup field is mapped "
                    "to an entity field, and a designated SLA field in the lookup determines the assigned SLA class. "
                    "Lookup policies support exact (case-insensitive) and wildcard matching modes, "
                    "and optional SLA value mappings to translate foreign values into TrackMe SLA classes. "
                    "When multiple policies match an entity, the highest-ranked SLA class wins across ALL policies "
                    "(both regex and lookup). "
                    "Once applied, SLA policies set 'sla_class' and 'sla_class_reason' (the policy ID that matched) "
                    "on entities for traceability."
                ),
                "applies_to": "All components (dsm, dhm, mhm, flx, wlk, fqm)",
                "management": (
                    "Created and managed via the SLA Policies management modal accessible from "
                    "the Tenant Home page. The modal provides: "
                    "1) A policy table showing all configured policies with inline editing for regex policies "
                    "and an edit button for lookup policies. "
                    "2) A 'Create new policy' button opening a guided form with mode selection (Regex/Lookup). "
                    "3) A simulation feature that previews which entities would match before committing. "
                    "4) A 'Run policy tracker' button that applies all configured policies across entities. "
                    "5) Bulk selection and deletion of policies. "
                    "REST API endpoints: "
                    "- POST /services/trackme/v2/splk_sla_policies/write/sla_policies_add "
                    "(create or update a policy, supports both regex and lookup types) "
                    "- POST /services/trackme/v2/splk_sla_policies/write/sla_policies_simulate "
                    "(preview matching entities without applying) "
                    "- POST /services/trackme/v2/splk_sla_policies/write/sla_policies_apply "
                    "(apply all policies and persist SLA class assignments to entities) "
                    "- POST /services/trackme/v2/splk_sla_policies/sla_policies_show "
                    "(list configured policies for a tenant/component)"
                ),
            },
            "notes": {
                "description": (
                    "Notes provide free-text documentation and operational context attached "
                    "to individual entities. Stored in kv_trackme_notes_tenant_{tenant_id} "
                    "keyed by the entity's _key (object_id). Note content supports Markdown. "
                    "Notes surface in a dedicated Notes column on tenant entity tables for "
                    "at-a-glance visibility, in a shared notes modal reused across entity "
                    "overview, tables, and bulk operations, and via a clone-to-entities "
                    "action that pushes one note to many entities at once. Each entity "
                    "record carries a notes_count field so undocumented entities can be "
                    "spotted without loading every note."
                ),
                "applies_to": "All components (dsm, dhm, mhm, flx, fqm, wlk)",
                "management": (
                    "Created and managed via the entity detail modal, the shared notes "
                    "modal (bulk), and the new Notes column in the entity table. "
                    "Clone-to-entities is available from the notes modal and from bulk-select."
                ),
                "rest_endpoints": [
                    "POST /services/trackme/v2/notes/write/create_note — create a note for an entity",
                    "POST /services/trackme/v2/notes/write/clone_note — clone a note to N target entities",
                    "POST /services/trackme/v2/notes/write/update_note — update note content",
                    "POST /services/trackme/v2/notes/write/delete_note — delete a note",
                    "GET /services/trackme/v2/notes/list_notes — list notes (optionally by object_id)",
                ],
            },
            "maintenance_mode": {
                "description": (
                    "Maintenance mode suppresses alerts and monitoring during planned or unplanned windows. "
                    "Can be activated globally or scheduled with specific time windows."
                ),
                "key_settings": [
                    "Global on/off toggle",
                    "Scheduled maintenance windows with start/end times",
                    "Planned vs unplanned designation (affects SLA calculations)",
                ],
            },
            "bank_holidays": {
                "description": (
                    "Bank holidays define periods where different monitoring thresholds or "
                    "alert suppression rules apply. Holidays affect SLA calculations and "
                    "can modify monitoring behavior during non-business periods."
                ),
                "management": "Configured via the bank holidays administration endpoint.",
            },
        },
        "impact_scoring": {
            "description": (
                "Impact scoring assigns numerical weights to different anomaly types. "
                "The total score determines the alert priority (low/medium/high/critical). "
                "Scores are configurable per tenant at creation time or via the update endpoint."
            ),
            "score_components": [
                "Outliers detection anomalies (all components with outliers enabled)",
                "DSM data sampling anomalies",
                "DSM/DHM delay threshold breaches",
                "DSM/DHM latency threshold breaches",
                "DSM minimum hosts distinct count breaches",
                "DSM/DHM/MHM future tolerance breaches",
                "MHM metric alerts",
                "FLX inactive entities",
                "FLX/FQM/WLK status not met conditions",
                "WLK skipping searches, execution errors, orphan searches, execution delays",
            ],
            "priority_mapping": (
                "Total impact score maps to priority: higher scores yield higher priority. "
                "The exact thresholds are configurable. A score of 0 results in orange state "
                "(out of monitoring scope)."
            ),
            "how_to_tune": (
                "Adjust impact_score_* values in tenant configuration. "
                "Set a score to 0 to exclude that anomaly type from alerting. "
                "Higher scores make that anomaly type contribute more to overall priority."
            ),
        },
        "rbac_model": {
            "description": (
                "TrackMe uses a three-tier role-based access control model for tenants. "
                "Users are granted access based on their Splunk role membership matching "
                "the tenant's configured roles."
            ),
            "roles": {
                "admin": (
                    "Full access to the tenant. Can modify configuration, manage components, "
                    "update RBAC, enable/disable/delete the tenant, manage all entities, "
                    "create/manage hybrid trackers, elastic sources, and all policies."
                ),
                "power": (
                    "Operational access. Can modify entity configurations (thresholds, monitoring "
                    "states, tags, priorities, ACKs), manage blocklists and policies, "
                    "but cannot manage the tenant itself (no delete, no RBAC changes, no tracker creation)."
                ),
                "user": (
                    "Read-only access. Can view tenant data, entity statuses, investigation "
                    "results, and use the AI assistant, but cannot modify any configuration."
                ),
            },
            "inheritance": (
                "Splunk role inheritance is respected. If a user has a role that inherits "
                "from an admin role, they get admin-level access to that tenant."
            ),
        },
        "threshold_tuning": {
            "dsm_dhm_mhm": {
                "delay_threshold": (
                    "data_max_delay_allowed: Maximum allowed time (seconds) since the last event. "
                    "If no event is received within this window, the entity enters red state. "
                    "Tunable per entity or via lagging classes."
                ),
                "latency_threshold": (
                    "data_max_lag_allowed: Maximum allowed ingestion latency (seconds) — "
                    "the difference between event time and index time. "
                    "Tunable per entity or via lagging classes."
                ),
                "future_tolerance": (
                    "Tolerance for future-dated events. Events with timestamps ahead of current "
                    "time by more than this threshold trigger alerts."
                ),
                "min_hosts_dcount": (
                    "DSM only: Minimum expected distinct host count. "
                    "If the host count drops below this threshold, the entity enters red state."
                ),
            },
            "flx": {
                "inactivity_timeout": (
                    "max_sec_inactive: Maximum time (seconds) with no data before entity is flagged. "
                    "Configurable per use case in the tracker definition."
                ),
                "custom_thresholds": (
                    "Use-case defined threshold conditions evaluated by the tracker. "
                    "Can include custom fields and comparison operators."
                ),
                "variable_thresholds": (
                    "Individual FLX threshold rules can use time-based variable values that change "
                    "by day-of-week and hour-of-day. Each rule has variable_threshold_enabled, "
                    "variable_threshold_default, and variable_threshold_slots fields. "
                    "Configurable per threshold rule via the entity modal or REST API."
                ),
            },
            "fqm": {
                "field_quality_thresholds": (
                    "percent_success and percent_coverage thresholds for field extraction quality. "
                    "Configurable per tracker dictionary."
                ),
            },
            "wlk": {
                "skipping_threshold": "Maximum percentage of skipped executions before alerting.",
                "error_threshold": "Maximum execution error count before alerting.",
                "delay_threshold": "Maximum execution delay before alerting.",
            },
        },
        "common_workflows": {
            "create_hybrid_tracker": (
                "1. Open the Actions menu in the toolbar. "
                "2. Select 'Create' for the desired component type. "
                "3. Follow the wizard steps: name, search mode, constraints, schedule. "
                "4. Review the configuration and submit. "
                "5. Execute the tracker to begin entity discovery."
            ),
            "setup_stateful_alerting": (
                "1. Navigate to the 'Tracking Alerts' tab. "
                "2. Click 'Create a new alert' from the Actions menu (requires admin role). "
                "3. Configure the alert properties: name, search, delivery target. "
                "4. Set email recipients or command handlers. "
                "5. If email is enabled and AI providers are configured, configure the AI Status Report "
                "(enabled by default; optionally select a specific AI provider). "
                "6. Configure priority-level routing if needed. "
                "7. Enable the alert."
            ),
            "configure_outlier_detection": (
                "1. Ensure mloutliers is enabled at the tenant level. "
                "2. Open an entity's detail modal. "
                "3. Navigate to the Outliers tab. "
                "4. Configure or review the ML model settings: detection period, thresholds. "
                "5. Wait for the model to train (requires minimum 7 days of history). "
                "6. Review detection results and adjust thresholds if needed."
            ),
            "create_elastic_source": (
                "1. Open the Actions menu and select 'Create: Elastic Sources'. "
                "2. Choose shared (applies to all trackers) or dedicated (single tracker). "
                "3. Define the elastic source: index, sourcetype, constraints. "
                "4. Review and submit. "
                "5. Execute the elastic source to begin monitoring."
            ),
            "manage_blocklists": (
                "1. Open the Actions menu and select 'Manage: Blocklists'. "
                "2. Add new entries: specify object pattern (exact match or regex). "
                "3. Entries will be applied on the next tracker execution. "
                "4. Blocked entities are excluded from monitoring."
            ),
            "configure_monitoring_time": (
                "1. Open the entity detail modal. "
                "2. Navigate to the entity configuration section. "
                "3. Set monitoring hours (start/end times). "
                "4. Set monitoring weekdays. "
                "5. Events outside the configured window are excluded from alerting."
            ),
            "tune_impact_scoring": (
                "1. Impact scores are set per tenant via administration. "
                "2. Each anomaly type has a configurable weight (0-100). "
                "3. Set a weight to 0 to exclude that anomaly from priority calculation. "
                "4. Higher weights increase the contribution to overall priority. "
                "5. Manual score influences can be applied per entity for fine-tuning."
            ),
            "configure_variable_delay": (
                "1. Set the default delay policy during tenant creation (Default Delay Configuration step) "
                "or update it afterward via 'Manage: Default Delay' in the Tenant Home Actions menu. "
                "2. Choose 'variable' as the default delay policy for DSM and/or DHM. "
                "3. Configure default time slots (day/hour ranges with thresholds) or use a template preset "
                "(business hours, weekday/weekend, three-tier). "
                "4. Optionally enable auto-compute to derive thresholds from historical mstats data. "
                "5. New entities discovered by trackers will inherit the tenant's default delay configuration. "
                "6. Per-entity overrides can be made via the entity detail modal (Variable Delay tab) "
                "or via the REST API at /services/trackme/v2/splk_variable_delay endpoints. "
                "7. Optionally enable 'Variable delay auto review' at the tenant level to have thresholds "
                "automatically re-evaluated on a schedule when data patterns shift."
            ),
        },
        "operational_status": {
            "scheduler_status": (
                "Shows the completion percentage of TrackMe's internal scheduler. "
                "A low percentage may indicate performance issues or search concurrency limits."
            ),
            "execution_summary": (
                "Per-tenant summary of tracker execution. Shows which components have run "
                "recently, last execution time, and whether all components completed successfully."
            ),
        },
    }

    # Conditionally add detailed creation guides based on enabled components
    hybrid_tracker_guide = _build_hybrid_tracker_creation_guide(enabled_components)
    if hybrid_tracker_guide:
        knowledge["hybrid_tracker_creation_guide"] = hybrid_tracker_guide

    if enabled_components is None or (enabled_components or {}).get("dsm", False):
        knowledge["elastic_sources_creation_guide"] = _build_elastic_sources_creation_guide()

    threshold_guide = _build_threshold_management_guide(enabled_components)
    if threshold_guide:
        knowledge["threshold_management_guide"] = threshold_guide

    # Configuration Guardian knowledge — describes each registered check,
    # severity tiers, remediation workflow, and an assistant playbook so
    # the AI can guide users through Guardian-alert resolution. The live
    # state (`guardian_alerts`, scoped to this tenant + system-wide) is
    # added at the top level of the response in `build_tenant_home_description`.
    knowledge["configuration_guardian"] = build_guardian_knowledge()

    # AI Advisor family knowledge — describes the 5 advisors, modes, tenant
    # gates, REST endpoints, the `advisor_invocation` action-contract schema,
    # and the assistant playbook directing how the AI Assistant should
    # propose advisor invocations inline (Phase 1 of the bridge — emitted
    # but not yet rendered as a consent card). Live state
    # (`ai_advisor_recent_runs`, scoped to this tenant) is added at the top
    # level of the response.
    knowledge["ai_advisors"] = build_ai_advisor_knowledge()

    # Concierge Advisor — the generalist (catalog-driven) advisor. The
    # static knowledge block teaches the AI Assistant when to propose
    # the Concierge versus a specialist, what the
    # ``concierge_invocation`` contract shape looks like, and the
    # safety property (read-only at the SDK level — mutation flows
    # through the consent-card click). Live state (recent Concierge
    # proposals + executions) flows through the same
    # ``ai_advisor_recent_runs`` lookup as the specialist runs, scoped
    # to ``advisor=concierge``.
    # ``surface="tenant_home"`` — only ``tenant_id`` is in session scope
    # on this surface; entity-level identifiers (``object``,
    # ``object_id``, ``component``) are NOT — the chat is bound to the
    # tenant page, not a specific entity within it. PR #1389 introduced
    # the parameter so the Concierge knowledge block ships the surface-
    # appropriate identifier-sourcing rule with no internal
    # contradictions.
    knowledge["concierge_advisor"] = build_concierge_knowledge(
        splunkd_uri=splunkd_uri,
        session_key=session_key,
        surface="tenant_home",
    )

    # Per-entity maintenance — static feature knowledge so the AI Assistant can
    # explain it and propose putting an entity on this tenant into a
    # maintenance window. Imported lazily (see note at the top of this module)
    # to avoid a circular import with trackme_libs_describe_maintenance.
    from trackme_libs_describe_maintenance import build_entity_maintenance_knowledge
    knowledge["entity_maintenance"] = build_entity_maintenance_knowledge()

    return knowledge


def build_tenant_home_description(service, request_info, tenant_id):
    """
    Build a comprehensive, AI-consumable description of a single tenant
    for the Tenant Home AI assistant.

    Args:
        service: Splunk service connection (system-level for KV store access)
        request_info: REST request info (for session key, server URI, user context)
        tenant_id: The tenant identifier to describe

    Returns:
        dict: Structured Tenant Home description
    """

    # Get user info for RBAC filtering
    users = service.users
    roles = service.roles
    username = request_info.user

    # Get effective roles for RBAC
    username_roles = []
    for user in users:
        if user.name == username:
            username_roles = user.roles
            break

    roles_dict = {}
    for role in roles:
        imported_roles_value = role.content.get("imported_roles", [])
        if imported_roles_value:
            roles_dict[role.name] = imported_roles_value

    effective_roles = get_effective_roles(username_roles, roles_dict)

    # Get vtenant accounts for aliases
    try:
        vtenants_account = get_vtenants_accounts(
            request_info.session_key,
            request_info.server_rest_uri,
        )
    except Exception as e:
        get_effective_logger().error(
            f'function=build_tenant_home_description, step="get_vtenants_accounts", '
            f'exception="{str(e)}"'
        )
        vtenants_account = {}

    # Query main tenants collection for this specific tenant
    collection_name = "kv_trackme_virtual_tenants"
    collection = service.kvstore[collection_name]
    records = collection.data.query(query=json.dumps({"tenant_id": tenant_id}))

    if not records:
        raise ValueError(f'tenant_id="{tenant_id}" not found in {collection_name}')

    record = records[0]

    # Carry the per-tenant username allowlist onto the record so the access
    # check below applies it alongside the RBAC role check.
    if tenant_id in vtenants_account:
        record["tenant_allowed_users"] = vtenants_account[tenant_id].get(
            "tenant_allowed_users", ""
        )
    else:
        record["tenant_allowed_users"] = ""

    # Verify RBAC access (role check + optional username allowlist)
    if username != "splunk-system-user" and not has_user_access(
        effective_roles, record, username
    ):
        raise PermissionError(
            f'user="{username}" does not have access to tenant_id="{tenant_id}"'
        )

    # Enrich with alias from accounts
    if tenant_id in vtenants_account:
        record["tenant_alias"] = vtenants_account[tenant_id].get("alias", tenant_id)
    else:
        record["tenant_alias"] = tenant_id

    # Query summary collection
    summary_collection_name = "kv_trackme_virtual_tenants_entities_summary"
    summary_collection = service.kvstore[summary_collection_name]
    summary_records = summary_collection.data.query(
        query=json.dumps({"tenant_id": tenant_id})
    )
    summary_record = summary_records[0] if summary_records else {}

    # Build each section
    tenant_identity = _build_tenant_identity(record)
    components_overview = _build_components_overview(record, summary_record)
    configuration = _build_configuration_summary(
        record, vtenants_account.get(tenant_id, {})
    )

    # Determine which components are enabled for feature count queries
    enabled_components = {
        comp: data["enabled"] for comp, data in components_overview.items()
    }

    feature_counts = _build_feature_counts(service, tenant_id, enabled_components)
    alerting_summary = _build_alerting_summary(service, tenant_id)
    entity_health = _build_entity_health_distribution(service, tenant_id, enabled_components)
    knowledge_reference = _build_knowledge_reference(
        enabled_components,
        splunkd_uri=request_info.server_rest_uri,
        session_key=request_info.session_key,
    )

    # Active Guardian alerts scoped to this tenant PLUS any system-wide
    # alerts (remote-account token/connectivity, AI provider, backup) —
    # those are often the root cause of symptoms surfacing on the tenant
    # (e.g. remote data missing → token expiring). The AI should consider
    # them when troubleshooting any tenant issue.
    guardian_alerts = load_active_guardian_alerts(
        service,
        tenant_id_filter=tenant_id,
    )

    # Recent AI Advisor runs for this tenant — the live-state half of the
    # AI Assistant ↔ AI Advisor bridge. Paired with the
    # `knowledge_reference.ai_advisors` block; the AI uses both to avoid
    # proposing redundant invocations and to construct a valid
    # `advisor_invocation` action-contract when it does propose.
    summary_index_for_runs = "trackme_summary"
    try:
        from trackme_libs import trackme_idx_for_tenant  # noqa: WPS433 — deferred import keeps cold-start light
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
            f'function=build_tenant_home_description, step="resolve_summary_index", '
            f'tenant_id="{tenant_id}", exception="{str(e)}"'
        )
    ai_advisor_recent_runs = load_recent_ai_advisor_runs(
        service,
        summary_index=summary_index_for_runs,
        tenant_id_filter=tenant_id,
    )

    return {
        "tenant_home_description": {
            "meta": {
                "api_version": "2.0",
                "generated_at": time.time(),
                "context_type": "tenant_home",
                "tenant_id": tenant_id,
            },
            "tenant_identity": tenant_identity,
            "components_overview": components_overview,
            "configuration": configuration,
            "feature_counts": feature_counts,
            "alerting_summary": alerting_summary,
            "entity_health_distribution": entity_health,
            # Live Guardian state for THIS tenant + system-wide alerts.
            # Paired with `knowledge_reference.configuration_guardian` (static
            # knowledge + assistant playbook) so the AI has everything it
            # needs to guide remediation.
            "guardian_alerts": guardian_alerts,
            # Recent AI Advisor runs for this tenant. Paired with
            # `knowledge_reference.ai_advisors` (static — what each advisor
            # IS + the action-contract schema + assistant playbook).
            "ai_advisor_recent_runs": ai_advisor_recent_runs,
            "knowledge_reference": knowledge_reference,
        }
    }
