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

import requests

# import trackme_libs_load utilities
from trackme_libs_load import (
    _parse_csv_or_list,
    has_user_access,
    get_effective_roles,
    get_vtenants_accounts,
)

# Version helpers for surfacing per-tenant schema upgrade state alongside
# the rest of the vtenants describe payload — same logic the
# `show_tenants` REST endpoint uses to compute `tenant_updated_status`.
from trackme_libs import trackme_get_version
from trackme_libs_schema import trackme_schema_format_version

# import shared helpers from tenant home describe library
from trackme_libs_describe_tenant_home import (
    _safe_parse_json_field,
    _safe_int,
    _build_hybrid_tracker_creation_guide,
    _build_elastic_sources_creation_guide,
    _build_threshold_management_guide,
)

# Configuration Guardian describe helpers — shared with tenant_home. Provides
# both a static knowledge block (what Guardian is, what each check means) and
# a dynamic, RBAC-filtered list of currently-active alerts for the AI
# Assistant to reason about.
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
from trackme_libs_describe_maintenance import (
    build_entity_maintenance_knowledge,
)


def _build_tenant_description(record, summary_record, schema_version_required, vtenant_conf=None):
    """Build a structured description for a single tenant.

    `schema_version_required` is computed once per request from the running
    TrackMe version and passed in here so the AI can answer
    "which tenants are pending schema upgrade?" without an extra round-trip.

    `vtenant_conf` is the per-tenant vtenant_account conf dict (from
    trackme_vtenants.conf, supplied by the caller). The tenant configuration
    flags below live in that conf, NOT on the kv_trackme_virtual_tenants
    record — reading them off `record` always returned the hardcoded default
    (see #1888, same root cause as the shadow-config bug #1886).
    """
    vtenant_conf = vtenant_conf or {}
    tenant_id = record.get("tenant_id", "")

    # Component enablement
    components = {
        "dsm": _safe_int(record.get("tenant_dsm_enabled")) == 1,
        "dhm": _safe_int(record.get("tenant_dhm_enabled")) == 1,
        "mhm": _safe_int(record.get("tenant_mhm_enabled")) == 1,
        "flx": _safe_int(record.get("tenant_flx_enabled")) == 1,
        "fqm": _safe_int(record.get("tenant_fqm_enabled")) == 1,
        "wlk": _safe_int(record.get("tenant_wlk_enabled")) == 1,
    }

    # Entity counts (from summary record)
    entity_counts = {}
    for comp in ("dsm", "dhm", "mhm", "flx", "fqm", "wlk"):
        entity_counts[f"{comp}_entities"] = _safe_int(
            summary_record.get(f"{comp}_entities", record.get(f"{comp}_entities"))
        )

    # Alert counts by component and priority (from summary record)
    alert_counts = {}
    for comp in ("dsm", "dhm", "mhm", "flx", "fqm", "wlk"):
        for priority in ("critical", "high", "medium", "low"):
            key = f"{comp}_{priority}_red_priority"
            val = _safe_int(
                summary_record.get(key, record.get(key))
            )
            if val > 0:
                alert_counts[key] = val

    # cmdb_lookup defaults to enabled (1) in vtenant_account defaults — treat a
    # missing value as enabled to match the decision-maker / alert-time behaviour
    # in trackme_libs_cmdb.perform_cmdb_lookup().
    cmdb_toggle = vtenant_conf.get("cmdb_lookup", 1)
    try:
        cmdb_lookup_enabled = int(str(cmdb_toggle)) == 1
    except (ValueError, TypeError):
        cmdb_lookup_enabled = True

    # Configuration flags — read from the vtenant_account conf, with defaults
    # mirroring collections_data.py::vtenant_account_default.
    configuration = {
        "default_priority": vtenant_conf.get("default_priority", "medium"),
        "sampling_enabled": str(vtenant_conf.get("sampling", "1")) == "1",
        "sampling_obfuscation_enabled": str(vtenant_conf.get("data_sampling_obfuscation", "0")) == "1",
        "adaptive_delay_enabled": str(vtenant_conf.get("adaptive_delay", "1")) == "1",
        "variable_delay_auto_review_enabled": str(vtenant_conf.get("variable_delay_auto_review", "1")) == "1",
        "mloutliers_enabled": str(vtenant_conf.get("mloutliers", "1")) == "1",
        "mloutliers_priority_filter": vtenant_conf.get("mloutliers_priority_filter", "") or "",
        "mloutliers_filter_expression": vtenant_conf.get("mloutliers_filter_expression", "") or "",
        "mloutliers_volume_kpi": vtenant_conf.get("mloutliers_volume_kpi", "") or "",
        "cmdb_lookup_enabled": cmdb_lookup_enabled,
        "cmdb_account": vtenant_conf.get("cmdb_account", "") or "",
        "monitoring_time_policy": vtenant_conf.get("monitoring_time_policy", "all_time"),
        "dsm_default_delay_policy": vtenant_conf.get("dsm_default_delay_policy", "static"),
        "dhm_default_delay_policy": vtenant_conf.get("dhm_default_delay_policy", "static"),
    }

    # Index settings
    idx_settings = _safe_parse_json_field(record.get("tenant_idx_settings"), {})

    # RBAC
    # `tenant_allowed_users` is an optional per-tenant Splunk username allowlist
    # carried onto the record from `vtenant_account` by the caller. When set, it
    # narrows visibility on top of the role-based RBAC (only listed users + the
    # tenant_owner can see the tenant; splunk-system-user always bypasses).
    # Empty/missing = no username restriction (role-only access). `sorted` for
    # deterministic JSON ordering across requests.
    allowed_users_list = sorted(_parse_csv_or_list(record.get("tenant_allowed_users")))
    rbac = {
        "tenant_owner": record.get("tenant_owner", ""),
        "admin_roles": record.get("tenant_roles_admin", []),
        "power_roles": record.get("tenant_roles_power", []),
        "user_roles": record.get("tenant_roles_user", []),
        "tenant_allowed_users": allowed_users_list,
        "visibility_restricted": bool(allowed_users_list),
    }

    # Execution status
    execution = {
        "all_status": _safe_int(summary_record.get("all_status", record.get("all_status"))),
        "all_last_exec": _safe_int(summary_record.get("all_last_exec", record.get("all_last_exec"))),
    }

    # Execution summary (from summary record, if available)
    exec_summary = summary_record.get(
        "tenant_objects_exec_summary",
        record.get("tenant_objects_exec_summary"),
    )
    if exec_summary:
        execution["exec_summary"] = _safe_parse_json_field(exec_summary, {})

    # Schema upgrade state — mirrors the computation in
    # `trackme_rest_handler_vtenants_user.show_tenants` so the AI assistant on
    # the License Information & Tenants Update statuses modal can answer
    # "which tenants are pending schema upgrade?" directly.
    schema_version_raw = record.get("schema_version")
    schema_version = _safe_int(schema_version_raw) if schema_version_raw is not None else None
    if schema_version_required == 0:
        tenant_updated_status = "updated"
    elif schema_version is None:
        # schema_version absent on the record — matches show_tenants' "undetermined"
        # branch (typically a tenant created when version retrieval failed).
        tenant_updated_status = "undetermined"
    elif schema_version == schema_version_required:
        tenant_updated_status = "updated"
    else:
        tenant_updated_status = "pending"

    schema = {
        "schema_version": schema_version,
        "schema_version_required": schema_version_required,
        "tenant_updated_status": tenant_updated_status,
    }

    return {
        "tenant_id": tenant_id,
        "tenant_alias": record.get("tenant_alias", tenant_id),
        "tenant_status": record.get("tenant_status", "unknown"),
        "tenant_description": record.get("tenant_desc", ""),
        "components": components,
        "entity_counts": entity_counts,
        "alert_counts": alert_counts,
        "configuration": configuration,
        "index_settings": idx_settings,
        "rbac": rbac,
        "execution": execution,
        "schema": schema,
    }


def _build_license_summary(request_info):
    """Fetch a compact license summary for the AI assistant.

    The full license describe context exposes everything via its own
    `contextType="license"` channel; here we surface only the headline that
    the License Information & Tenants Update statuses modal banner shows
    (edition, validity, expiration) so the vtenants-context AI can answer
    edition questions directly without redirecting the user. Fail-open: if
    the licensing endpoint is unreachable we return an empty dict and the
    AI simply lacks edition awareness for this turn.
    """
    try:
        session_key = request_info.system_authtoken
        splunkd_uri = request_info.server_rest_uri
        url = "%s/services/trackme/v2/licensing/license_status" % splunkd_uri
        response = requests.get(
            url,
            headers={
                "Authorization": "Splunk %s" % session_key,
                "Content-Type": "application/json",
            },
            verify=False,
            timeout=15,
        )
        if response.status_code not in (200, 201):
            get_effective_logger().warning(
                f'function=_build_license_summary, '
                f'step="fetch_license_status", '
                f'status_code={response.status_code}'
            )
            return {}

        data = json.loads(response.text)
        return {
            "license_is_valid": data.get("license_is_valid"),
            "license_type": data.get("license_type", "unknown"),
            "license_subscription_class": data.get(
                "license_subscription_class", "unknown"
            ),
            "license_expiration": data.get("license_expiration", "unknown"),
            "license_expiration_countdown_sec": data.get(
                "license_expiration_countdown_sec"
            ),
            "license_read_only": data.get("license_read_only", False),
            "trackme_version": data.get("trackme_version", "unknown"),
        }
    except Exception as e:
        get_effective_logger().warning(
            f'function=_build_license_summary, exception="{str(e)}"'
        )
        return {}


def _build_environment_overview(tenant_descriptions):
    """Build aggregate statistics across all tenants."""
    total_entities = 0
    total_alerts = 0
    component_usage = {"dsm": 0, "dhm": 0, "mhm": 0, "flx": 0, "fqm": 0, "wlk": 0}
    enabled_count = 0
    disabled_count = 0
    schema_state_counts = {"updated": 0, "pending": 0, "undetermined": 0}

    for t in tenant_descriptions:
        # Count entities
        for comp in ("dsm", "dhm", "mhm", "flx", "fqm", "wlk"):
            total_entities += t["entity_counts"].get(f"{comp}_entities", 0)

        # Count alerts
        for key, val in t["alert_counts"].items():
            total_alerts += val

        # Count component usage
        for comp, enabled in t["components"].items():
            if enabled:
                component_usage[comp] += 1

        # Count tenant states
        if t["tenant_status"] == "enabled":
            enabled_count += 1
        else:
            disabled_count += 1

        # Schema upgrade state aggregate — mirrors the donut chart on the
        # License Information & Tenants Update statuses modal so the AI can
        # answer "how many tenants are pending?" without iterating the list.
        schema_state = t.get("schema", {}).get("tenant_updated_status")
        if schema_state in schema_state_counts:
            schema_state_counts[schema_state] += 1

    return {
        "total_entities_across_tenants": total_entities,
        "total_alerts_across_tenants": total_alerts,
        "enabled_tenants": enabled_count,
        "disabled_tenants": disabled_count,
        "component_usage": component_usage,
        "schema_upgrade_state": schema_state_counts,
    }


def _build_knowledge_reference(splunkd_uri=None, session_key=None):
    """
    Build a static knowledge reference section that provides the AI assistant
    with comprehensive understanding of Virtual Tenants concepts, operations,
    and workflows. This allows the AI to answer 'how do I' questions accurately.

    ``splunkd_uri`` and ``session_key`` are threaded through to
    ``build_concierge_knowledge`` so the Concierge knowledge block can
    embed a compact projection of the live API catalog (the chat LLM's
    only way of seeing the real path universe — without it, the LLM
    fabricates paths that don't exist).
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
                "use_when": "You need to monitor the health of scheduled searches and reports.",
            },
        },
        "tenant_creation_workflow": {
            "overview": (
                "Creating a new tenant follows a 4-step wizard process. The exact "
                "options available depend on the component type selected."
            ),
            "steps": [
                {
                    "step": 1,
                    "name": "Tenant Basics",
                    "description": (
                        "Define the tenant identity: tenant_id (lowercase, max 20 chars, must be unique), "
                        "optional alias, optional description. Configure defaults: priority level, "
                        "ML outliers enablement, data sampling (DSM only), default delay configuration "
                        "(static or variable delay policy with optional time-based slots for DSM and DHM), "
                        "adaptive delay, CMDB integration, monitoring time policy, and impact scoring weights."
                    ),
                },
                {
                    "step": 2,
                    "name": "Component Configuration",
                    "description": (
                        "Component-specific setup. For DSM: choose tracker type (hybrid/standard), "
                        "search mode (tstats/raw), deployment account (local/remote), break-by logic "
                        "(split/merged/custom), discovery patterns. For WLK: environment type, scheduler "
                        "constraints, grouping. For FLX/FQM: minimal or no configuration needed."
                    ),
                },
                {
                    "step": 3,
                    "name": "Indexes & RBAC",
                    "description": (
                        "Select Splunk indexes for TrackMe data: summary index (trackme_summary), "
                        "audit index (trackme_audit), metrics index (trackme_metrics), notable index "
                        "(trackme_notable). Configure RBAC: tenant owner, admin roles, power roles, "
                        "user roles."
                    ),
                },
                {
                    "step": 4,
                    "name": "Review & Create",
                    "description": (
                        "Review the full JSON configuration payload. Optionally add an update "
                        "comment for the audit trail. Submit to create the tenant."
                    ),
                },
            ],
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
                    "update RBAC, enable/disable/delete the tenant, and manage all entities."
                ),
                "power": (
                    "Operational access. Can modify entity configurations (thresholds, monitoring "
                    "states, etc.) but cannot manage the tenant itself (no delete, no RBAC changes)."
                ),
                "user": (
                    "Read-only access. Can view tenant data, entity statuses, and investigation "
                    "results, but cannot modify any configuration."
                ),
            },
            "inheritance": (
                "Splunk role inheritance is respected. If a user has a role that inherits "
                "from an admin role, they get admin-level access to that tenant."
            ),
        },
        "management_operations": {
            "enable_tenant": "Activates a disabled tenant. Trackers resume execution.",
            "disable_tenant": "Pauses a tenant. All trackers stop running but data is preserved.",
            "delete_tenant": "Permanently removes the tenant and all associated KV store data, knowledge objects, and trackers.",
            "add_component": "Adds a new monitoring component (DSM/DHM/MHM/FLX/FQM/WLK) to an existing tenant.",
            "remove_component": "Removes a component from a tenant. Associated entities and trackers are deleted.",
            "update_rbac": "Modifies the tenant's role assignments (owner, admin, power, user roles).",
            "replica_tenant": (
                "Creates a read-only tenant that mirrors monitoring data from another tenant. "
                "Useful for giving different teams visibility into the same data with different RBAC."
            ),
        },
        "configuration_flags": {
            "sampling": "Enables data sampling for DSM entities, reducing search load by analyzing a subset of events.",
            "sampling_obfuscation": "When sampling is enabled, obfuscates sensitive data in sample results.",
            "adaptive_delay": "Dynamically adjusts delay thresholds based on observed data patterns, reducing false alerts.",
            "variable_delay": (
                "Assigns time-based delay thresholds (day-of-week and hour-of-day slots) to DSM/DHM entities "
                "instead of a single static value. Configured per tenant via the Default Delay Configuration "
                "(at creation or via 'Manage: Default Delay'). Entities inherit the tenant default at discovery "
                "and can be overridden individually. NOT mutually exclusive with adaptive delay (since 2.4.1): "
                "allow_adaptive_delay is an independent per-entity opt-in (derived from the threshold lock), and "
                "when opted in the adaptive-delay engine refreshes the variable-delay slot thresholds from "
                "history rather than the static value; lock an entity to stop automation from touching its "
                "thresholds. When auto-review "
                "is enabled (variable_delay_auto_review_enabled), slot thresholds are periodically re-computed "
                "from historical data. Slot hours are stored and evaluated in the Splunk server's local time "
                "(UTC on Splunk Cloud); the web UI displays/edits them in the operator's browser-local time and "
                "converts back to server time on save, so the KV/API always holds server-local hours."
            ),
            "mloutliers": "Enables machine learning outlier detection for entity metrics (event count, latency, etc.).",
            "mloutliers_priority_filter": (
                "Comma-separated list of priorities for which ML Outliers detection runs (e.g. 'critical,high'). "
                "Empty means all priorities are eligible. Applies to every component listed in mloutliers_allowlist. "
                "Existing tenants migrated to 2.3.22 default to all priorities so behaviour is preserved; new "
                "tenants created via the wizard default to 'critical,high'."
            ),
            "mloutliers_filter_expression": (
                "Filter-expression DSL (same syntax as Virtual Groups) restricting which entities are eligible "
                "for ML Outliers detection — e.g. 'priority=high tags=prod' or 'data_index=siem-* OR data_sourcetype=cisco:*'. "
                "Empty means match all. Applies on top of mloutliers_priority_filter."
            ),
            "mloutliers_volume_kpi": (
                "Tenant-level override for the volume KPI metric used by ML Outliers training. Empty means "
                "fall back to the global default in splk_outliers_detection settings. Applies to dsm and dhm "
                "only; ignored for flx, fqm and wlk."
            ),
            "cmdb_lookup": (
                "Enables CMDB integration for entity enrichment with external asset/service data. "
                "Enrichment is resolved at alert time — the per-component CMDB search runs against "
                "the local splunkd or a configured remote account (cmdb_account) and its output "
                "fields are injected into stateful alert events, notable events, and notification "
                "emails. A guided 'Manage: CMDB integration' modal provides the configuration UI."
            ),
            "monitoring_time_policy": "Controls when monitoring is active: 'global' uses the system-wide schedule, custom policies restrict monitoring to specific time windows.",
        },
        "impact_scoring": {
            "description": (
                "Impact scoring assigns numerical weights to different anomaly types. "
                "The total score determines the alert priority (low/medium/high/critical). "
                "Scores are configurable per tenant at creation time or via the update endpoint."
            ),
            "score_components": [
                "Outliers detection anomalies",
                "DSM data sampling anomalies",
                "DSM/DHM delay threshold breaches",
                "DSM/DHM latency threshold breaches",
                "DSM min hosts distinct count breaches",
                "DSM/DHM/MHM future tolerance breaches",
                "MHM metric alerts",
                "FLX inactive entities",
                "FLX/FQM/WLK status not met conditions",
                "WLK skipping searches, execution errors, orphan searches, execution delays, out of monitoring times",
            ],
        },
        "operational_status": {
            "scheduler_status": (
                "Shows the completion percentage of TrackMe's internal scheduler. "
                "A low percentage may indicate performance issues or search concurrency limits."
            ),
            "ops_status": (
                "Shows the operational health of all virtual tenants. Aggregates the execution "
                "status of all tenant trackers. A degraded status means one or more trackers "
                "are failing or running behind schedule."
            ),
            "execution_summary": (
                "Per-tenant summary of tracker execution. Shows which components have run "
                "recently, last execution time, and whether all components completed successfully."
            ),
        },
    }

    knowledge["virtual_groups"] = {
        "description": (
            "Virtual Groups are read-only cross-tenant aggregation views. They appear as "
            "cards in the Virtual Tenants grid alongside real tenant cards, but are visually "
            "distinct (dashed border). A Virtual Group aggregates entities from multiple "
            "tenants and their components into a single unified view. "
            "Groups can carry an optional group_category so the grid renders groups sharing "
            "a category together — easier to navigate in large deployments with many "
            "cross-tenant views."
        ),
        "key_features": [
            "Select multiple tenants and their components to aggregate",
            "Entities are automatically grouped by component family (DSM, DHM, FLX, etc.)",
            "Optional group_category for sub-grouping the grid",
            "Optional priority filter to show only certain priority levels (e.g., high+critical only)",
            "Optional entity filter: a free-form DSL expression (field=value, wildcards, AND/OR/parentheses) "
            "to further restrict which entities appear (e.g. tags=security, labels=under-review, "
            "index=siem-*-amer, sourcetype=cisco:* OR sourcetype=palo:*). The entity_filter field in the group "
            "definition contains this expression when active.",
            "RBAC controls: define which Splunk roles can see and access each group",
            "Double-click a group card to see the aggregated entity overview",
            "Entity links open directly in TenantHome for the source tenant",
        ],
        "entity_filter_dsl": (
            "The entity filter uses a lightweight DSL. Grammar: field=value conditions joined "
            "by whitespace (implicit AND), the OR keyword, and parentheses for grouping. "
            "Values support glob wildcards (* = any sequence, ? = any single char). "
            "All comparisons are case-insensitive. Quoting values is optional. "
            "Built-in field aliases: data_index/index, data_sourcetype/sourcetype, object, "
            "tags (each tag tested individually, supports arrays), labels (each entity label "
            "tested individually), priority (critical/high/medium/low), "
            "tenant (tenant_id), component (dsm/dhm/mhm/flx/fqm/wlk). "
            "Any other raw entity field name is also supported. "
            "Examples: 'tags=security priority=high', 'labels=under-review', "
            "'(index=siem-* OR index=network-*) sourcetype=cisco:*', "
            "'tenant=cyber-ops component=dsm'."
        ),
        "how_it_works": (
            "Virtual Groups do NOT create new monitoring, trackers, or collections. They are "
            "purely an aggregation view that queries existing entity data from the selected "
            "tenants in real-time. Disabled or deleted tenants in a group's scope are "
            "automatically skipped. If a priority_filter is set, only entities at those "
            "priority levels are shown. If an entity_filter is set, it is applied as a "
            "post-filter on the loaded entities using the DSL described in entity_filter_dsl."
        ),
        "creation": (
            "Admin users can create Virtual Groups via the Actions menu > 'Create a virtual group'. "
            "The wizard has 7 steps: (1) group identity (alias, description, group_id), "
            "(2) tenant and component selection, (3) priority filter (optional — restrict to "
            "critical/high/medium/low), (4) additional entity filter (optional — free-form DSL), "
            "(5) RBAC configuration (allowed roles), (6) simulation preview, (7) review and create."
        ),
        "differences_from_tenants": (
            "Unlike Virtual Tenants, Virtual Groups have no monitoring components, trackers, "
            "alerting, scoring, or knowledge objects. They are simply a read-only grouped "
            "view of entities from existing tenants."
        ),
    }

    # Capability overview for features that have no dedicated top-level section
    # elsewhere in this knowledge reference — labels, notes, CMDB, inject-expected
    # and variable delay templates — so the AI can answer "what can I do with X"
    # questions without having to introspect each handler.
    knowledge["capabilities"] = {
        "labels": {
            "description": (
                "Entity labels — GitHub-style colour-coded tags used for lifecycle "
                "visibility and cross-cutting categorisation. Each tenant has its own "
                "label registry and assignments collection. Labels surface in entity "
                "tables (Labels column), in the entity describe endpoint "
                "(identity.labels + identity.labels_objects), and in stateful alert "
                "events and notable events as labels (flat list) and labels_objects "
                "(JSON). Use the entity-filter DSL keyword 'labels=<name>' to filter "
                "Virtual Groups or tables by label."
            ),
            "factory_defaults": [
                "blocked", "under-review", "in-progress", "resolved",
                "maintenance", "acknowledged", "noise", "decommissioned",
            ],
            "related_rest_endpoints": [
                "GET /services/trackme/v2/labels/list_labels",
                "POST /services/trackme/v2/labels/write/create_label",
                "POST /services/trackme/v2/labels/write/update_label",
                "POST /services/trackme/v2/labels/write/delete_label",
                "POST /services/trackme/v2/labels/write/assign_labels",
                "POST /services/trackme/v2/labels/write/unassign_labels",
            ],
        },
        "notes": {
            "description": (
                "Free-text documentation and operational context attached to individual "
                "entities. Note content supports Markdown. Notes surface in a dedicated "
                "Notes column on tenant entity tables, in a shared notes modal reused "
                "across entity overview / tables / bulk ops, and via a clone-to-entities "
                "action that pushes one note to many entities at once. Each entity "
                "record carries a notes_count field so undocumented entities can be "
                "spotted without loading every note."
            ),
            "related_rest_endpoints": [
                "POST /services/trackme/v2/notes/write/create_note",
                "POST /services/trackme/v2/notes/write/clone_note",
                "POST /services/trackme/v2/notes/write/update_note",
                "POST /services/trackme/v2/notes/write/delete_note",
                "GET /services/trackme/v2/notes/list_notes",
            ],
        },
        "cmdb_integration_modal": {
            "description": (
                "A guided 'Manage: CMDB integration' modal accessible from the "
                "tenant-home Features actions menu for all 6 component types. Provides "
                "an enable/disable toggle, account selector (local or remote via the "
                "cmdb_account field), a guided lookup builder with content preview and "
                "auto-generated SPL, and an SPL editor with Edit/Preview toggle. "
                "Enrichment runs at alert time (stateful alerts and notable events) "
                "and injects CMDB fields into the event payload and email body. "
                "CMDB values are NOT persisted on the entity record."
            ),
            "tenant_record_fields": [
                "cmdb_lookup (1 enabled / 0 disabled, default 1)",
                "cmdb_account (remote account name, empty = local splunkd)",
                "splk_dsm_cmdb_search / splk_dhm_cmdb_search / splk_mhm_cmdb_search / "
                "splk_flx_cmdb_search / splk_fqm_cmdb_search / splk_wlk_cmdb_search",
            ],
        },
        "inject_expected_sources_hosts": {
            "description": (
                "One-shot action wizard to inject expected sources (DSM) or expected "
                "hosts (DHM) via a guided UI. Operators can bulk-declare entities "
                "that should exist so their absence becomes immediately visible, "
                "rather than waiting for the next discovery cycle to either find "
                "them or leave them silently unknown."
            ),
            "applies_to": "DSM (expected sources), DHM (expected hosts)",
            "related_rest_endpoints": [
                "POST /services/trackme/v2/splk_inject_expected/admin/inject_validate",
                "POST /services/trackme/v2/splk_inject_expected/admin/inject_simulate",
                "POST /services/trackme/v2/splk_inject_expected/admin/inject_execute",
            ],
        },
        "variable_delay_templates_per_tenant": {
            "description": (
                "Quick Templates (business_hours, weekday_weekend, three_tier) in "
                "every variable delay slot editor are customisable per tenant. "
                "Overrides live in "
                "kv_trackme_common_variable_delay_templates_tenant_{tenant_id}: a "
                "custom record whose template_id matches a factory default overrides "
                "that default; a new template_id is appended. Deleting a custom "
                "record reverts to factory. Greenfield tenants with no customs see "
                "the factory defaults."
            ),
            "auto_save_on_tenant_creation": (
                "When an admin creates a new tenant and modifies the variable delay "
                "template in the creation wizard, the modification is automatically "
                "persisted as a custom override — runs fail-open after the tenant "
                "and all KV collections are ready."
            ),
            "related_rest_endpoints": [
                "POST /services/trackme/v2/splk_variable_delay/templates_list",
                "POST /services/trackme/v2/splk_variable_delay/admin/templates_save",
                "POST /services/trackme/v2/splk_variable_delay/admin/templates_reset",
                "POST /services/trackme/v2/splk_variable_delay/admin/templates_reset_all",
            ],
        },
        "virtual_groups_sub_categories": {
            "description": (
                "Virtual Groups carry an optional group_category field. Groups "
                "sharing the same category render together in the Virtual Tenants "
                "grid, making large deployments with many cross-tenant views easier "
                "to navigate. Empty string = default 'Uncategorised' bucket."
            ),
        },
    }

    # Include all component creation guides (vtenants is not tenant-specific)
    knowledge["hybrid_tracker_creation_guide"] = _build_hybrid_tracker_creation_guide()
    knowledge["elastic_sources_creation_guide"] = _build_elastic_sources_creation_guide()
    knowledge["threshold_management_guide"] = _build_threshold_management_guide()

    # Configuration Guardian knowledge — describes each registered check,
    # severity tiers, remediation workflow, and assistant playbook so the AI
    # can guide users through Guardian-alert resolution. Separate from the
    # live-state `guardian_alerts` list that lands alongside `tenants` at the
    # top level of the response.
    knowledge["configuration_guardian"] = build_guardian_knowledge()

    # AI Advisor family knowledge — describes the 5 advisors (ML + 4
    # component advisors), modes, tenant gates, REST endpoints, the
    # `advisor_invocation` action-contract schema, and the assistant
    # playbook directing how the AI Assistant should propose advisor
    # invocations inline (Phase 1 of the bridge — emitted but not yet
    # rendered as a consent card). Separate from the live-state
    # `ai_advisor_recent_runs` list at the top level of the response.
    knowledge["ai_advisors"] = build_ai_advisor_knowledge()

    # Concierge Advisor — generalist (catalog-driven). Same shape as
    # the tenant_home wire-in: static knowledge (catalog entry +
    # action-contract schema + assistant playbook + safety property)
    # alongside the specialist advisor block. The vtenants surface
    # gives the LLM access to admin-level Concierge proposals (e.g.
    # tenant-level configuration changes) when the user's intent
    # matches.
    # ``surface="vtenants"`` — the cross-tenant Virtual Tenants page
    # has NO single tenant in session scope, let alone a single entity.
    # Every identifier the LLM proposes (``tenant_id``, ``object``,
    # ``object_id``, ``component``) MUST be a literal value extracted
    # from the user's prompt; the bridge cannot resolve any of them
    # from session context. PR #1389 introduced the parameter so this
    # call site ships exactly the literal-required rule with no
    # session-injection language to contradict it.
    knowledge["concierge_advisor"] = build_concierge_knowledge(
        splunkd_uri=splunkd_uri,
        session_key=session_key,
        surface="vtenants",
    )

    # Per-entity maintenance — static feature knowledge so the AI Assistant can
    # explain it and propose putting an entity (named in the prompt) into a
    # maintenance window.
    knowledge["entity_maintenance"] = build_entity_maintenance_knowledge()

    # Schema upgrade & licensing context — read by the AI Assistant when it's
    # opened from the License Information & Tenants Update statuses modal.
    # Tells the AI which fields carry the live state and how to phrase
    # answers, mirroring the Guardian playbook pattern.
    knowledge["schema_upgrade_and_licensing"] = {
        "description": (
            "After a TrackMe upgrade, each Virtual Tenant's Health Tracker "
            "runs a schema upgrade so its KV collections match what the new "
            "build expects. Until that upgrade lands, that tenant is in "
            "`pending` state and trackers are gated to avoid running against "
            "stale schemas. The License Information & Tenants Update "
            "statuses modal surfaces this for every tenant."
        ),
        "fields_to_read": {
            "per_tenant": (
                "`tenants[].schema.schema_version` (what the tenant has), "
                "`tenants[].schema.schema_version_required` (what the running "
                "build expects), `tenants[].schema.tenant_updated_status` "
                "(`updated` | `pending` | `undetermined`)."
            ),
            "aggregate": (
                "`environment_overview.schema_upgrade_state` is the same "
                "donut the modal renders — counts by state across the "
                "tenants the caller can see."
            ),
            "license": (
                "`license_summary` carries a compact view of the running "
                "license: `license_type`, `license_subscription_class`, "
                "`license_is_valid`, `license_read_only`, `license_expiration`, "
                "`license_expiration_countdown_sec`, `trackme_version`. "
                "For deeper licensing questions (feature matrix, registration "
                "workflow), point the user to the dedicated License "
                "Management AI assistant on the License page."
            ),
        },
        "assistant_playbook": [
            (
                "When the user asks 'which of my tenants are pending?' "
                "or 'what's still upgrading?' — iterate `tenants[]`, list "
                "every entry where `schema.tenant_updated_status == 'pending'`, "
                "sorted by tenant_alias, and quote `schema_version` vs "
                "`schema_version_required` so they can see the gap."
            ),
            (
                "If a tenant's status is `undetermined`, treat it as a "
                "diagnosis hint: the schema_version field is missing on the "
                "record. That usually means the tenant was created in a "
                "window where TrackMe could not resolve its own version "
                "(common when DB Connect is misconfigured). Recommend "
                "running the tenant's Health Tracker manually or "
                "contacting support — do NOT recommend deleting and "
                "recreating the tenant."
            ),
            (
                "When the user opens this modal and asks 'why is my license "
                "showing X edition?' or similar headline questions — answer "
                "from `license_summary`. For 'how do I upgrade my license?' "
                "or feature-matrix questions, redirect them to the License "
                "Management page (which has its own AI assistant context "
                "with the full licensing knowledge base)."
            ),
            (
                "Schema upgrade progress is observable in "
                "`index=_internal sourcetype=trackme:custom_commands:trackmetrackerhealth task=schema_upgrade tenant_id=<tid>` "
                "— offer that SPL when the user wants to know WHY a tenant "
                "is stuck pending."
            ),
        ],
    }

    return knowledge


def build_vtenants_description(service, request_info):
    """
    Build a comprehensive, AI-consumable description of all Virtual Tenants.

    Args:
        service: Splunk service connection (system-level for KV store access)
        request_info: REST request info (for session key, server URI, user context)

    Returns:
        dict: Structured Virtual Tenants description
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
            f'function=build_vtenants_description, step="get_vtenants_accounts", '
            f'exception="{str(e)}"'
        )
        vtenants_account = {}

    # Resolve the schema version required by the running TrackMe build once,
    # then thread it through `_build_tenant_description` so each tenant entry
    # carries its `tenant_updated_status`. Mirrors the computation in the
    # `show_tenants` REST endpoint. Fail-open: on resolver failure we pass 0
    # which forces "updated" everywhere, matching show_tenants' degraded-mode
    # behaviour when DB Connect blocks version retrieval.
    try:
        trackme_version = trackme_get_version(service)
        schema_version_required = trackme_schema_format_version(trackme_version)
    except Exception as e:
        get_effective_logger().warning(
            f'function=build_vtenants_description, step="resolve_schema_version", '
            f'exception="{str(e)}"'
        )
        schema_version_required = 0

    # Query main tenants collection
    collection_name = "kv_trackme_virtual_tenants"
    collection = service.kvstore[collection_name]
    records = collection.data.query()

    # Query summary state collection
    summary_collection_name = "kv_trackme_virtual_tenants_entities_summary"
    summary_collection = service.kvstore[summary_collection_name]
    summary_records = summary_collection.data.query()

    # Index summary records by tenant_id for fast lookup
    summary_by_tenant = {}
    for sr in summary_records:
        tid = sr.get("tenant_id")
        if tid:
            summary_by_tenant[tid] = sr

    # Enrich records with aliases from accounts
    for record in records:
        tid = record.get("tenant_id", "")
        if tid in vtenants_account:
            record["tenant_alias"] = vtenants_account[tid].get("alias", tid)
            record["tenant_allowed_users"] = vtenants_account[tid].get(
                "tenant_allowed_users", ""
            )
        else:
            record["tenant_alias"] = tid
            record["tenant_allowed_users"] = ""

    # Filter by user RBAC access (role check + optional username allowlist)
    filtered_records = [
        record
        for record in records
        if has_user_access(effective_roles, record, username)
        or username == "splunk-system-user"
    ]

    # Sort by alias
    filtered_records.sort(key=lambda x: x.get("tenant_alias", "").lower())

    # Build per-tenant descriptions
    tenant_descriptions = []
    for record in filtered_records:
        tid = record.get("tenant_id", "")
        summary_record = summary_by_tenant.get(tid, {})
        tenant_descriptions.append(
            _build_tenant_description(
                record, summary_record, schema_version_required,
                vtenants_account.get(tid, {})
            )
        )

    # Build environment overview
    environment_overview = _build_environment_overview(tenant_descriptions)

    # Build knowledge reference
    knowledge_reference = _build_knowledge_reference(
        splunkd_uri=request_info.server_rest_uri,
        session_key=request_info.session_key,
    )

    # Load Virtual Groups
    virtual_groups_descriptions = []
    try:
        vg_collection = service.kvstore["kv_trackme_virtual_groups"]
        vg_records = vg_collection.data.query()
        for vg in vg_records:
            try:
                tenants_scope = json.loads(vg.get("tenants_scope", "[]"))
            except (json.JSONDecodeError, TypeError):
                tenants_scope = []
            try:
                priority_filter = json.loads(vg.get("priority_filter", "[]"))
            except (json.JSONDecodeError, TypeError):
                priority_filter = []

            # RBAC: skip groups the calling user cannot access — mirrors has_group_access()
            # splunk-system-user (AI assistant context) always sees all groups, matching the
            # tenant RBAC bypass at line 525.
            # Note: get_effective_roles() always returns a set (never None), so the guard
            # `effective_roles is not None` is omitted here to avoid misleading dead code.
            rbac_allowed_roles_raw = vg.get("rbac_allowed_roles", "")
            if isinstance(rbac_allowed_roles_raw, list):
                allowed = {str(r).strip() for r in rbac_allowed_roles_raw if str(r).strip()}
            else:
                allowed = {r.strip() for r in str(rbac_allowed_roles_raw).split(",") if r.strip()}
            allowed |= {"admin", "trackme_admin", "sc_admin"}
            if not (effective_roles & allowed) and username != "splunk-system-user":
                continue

            entity_filter = str(vg.get("entity_filter", "") or "")
            # group_category introduced in 2.3.19 (PR #1037) — optional sub-grouping
            # label for rendering the Virtual Groups grid by category. Empty string
            # means the group appears in the default "Uncategorised" bucket.
            group_category = str(vg.get("group_category", "") or "")
            virtual_groups_descriptions.append({
                "group_id": vg.get("group_id", ""),
                "group_alias": vg.get("group_alias", ""),
                "group_description": vg.get("group_description", ""),
                "group_category": group_category,
                "tenants_scope": tenants_scope,
                "priority_filter": priority_filter,
                "entity_filter": entity_filter,
                "rbac_allowed_roles": rbac_allowed_roles_raw,
            })
    except Exception as e:
        get_effective_logger().warning(
            f'function=build_vtenants_description, step="load_virtual_groups", '
            f'exception="{str(e)}"'
        )

    # Load active Guardian alerts the caller can see. RBAC: system-scoped
    # alerts (empty tenant_id) are visible to everyone; tenant-scoped alerts
    # are gated by the same set of visible tenants already computed above.
    # splunk-system-user (AI Assistant service account) bypasses the filter
    # so the AI receives the full picture — matches the existing convention
    # for virtual groups (line ~707) and tenant records.
    visible_tenant_ids_for_guardian = (
        None
        if username == "splunk-system-user"
        else {rec.get("tenant_id") for rec in filtered_records if rec.get("tenant_id")}
    )
    guardian_alerts = load_active_guardian_alerts(
        service,
        visible_tenant_ids=visible_tenant_ids_for_guardian,
    )

    # Recent AI Advisor runs across the visible tenants — the live-state
    # half of the AI Assistant ↔ AI Advisor bridge. Same RBAC contract as
    # Guardian alerts: splunk-system-user (the AI Assistant service
    # account) bypasses the per-tenant filter so the AI sees the full
    # picture; everyone else is scoped to the tenants they can already
    # see. Empty index name (no tenant scope resolved yet) returns an
    # empty result rather than failing — the describe endpoint must keep
    # working even if the summary index is transiently unresolvable.
    summary_index_for_runs = ""
    try:
        from trackme_libs import trackme_idx_for_tenant  # noqa: WPS433 — deferred to keep import light
        # The vtenants describe is cross-tenant; the summary index is
        # effectively system-wide (every tenant writes its advisor events to
        # the same configured `trackme_summary` unless explicitly overridden
        # at tenant level). Pick the first accessible tenant_id to resolve
        # the index — falls back to the default `trackme_summary` on error.
        seed_tenant_id = (
            (tenant_descriptions[0].get("tenant_id") if tenant_descriptions else "")
            or ""
        )
        if seed_tenant_id:
            idx_settings = trackme_idx_for_tenant(
                request_info.session_key,
                request_info.server_rest_uri,
                seed_tenant_id,
            )
            summary_index_for_runs = (idx_settings or {}).get(
                "trackme_summary_idx", "trackme_summary"
            )
        else:
            summary_index_for_runs = "trackme_summary"
    except Exception as e:
        get_effective_logger().warning(
            f'function=build_vtenants_description, step="resolve_summary_index", '
            f'exception="{str(e)}"'
        )
        summary_index_for_runs = "trackme_summary"

    ai_advisor_recent_runs = load_recent_ai_advisor_runs(
        service,
        summary_index=summary_index_for_runs,
        visible_tenant_ids=visible_tenant_ids_for_guardian,
    )

    # Compact license headline so the AI on the License Information &
    # Tenants Update statuses modal can answer edition questions without a
    # round-trip to the dedicated `license` context.
    license_summary = _build_license_summary(request_info)

    return {
        "vtenants_description": {
            "meta": {
                "api_version": "2.0",
                "generated_at": time.time(),
                "context_type": "vtenants",
                "total_tenants": len(tenant_descriptions),
                "accessible_tenants": len(tenant_descriptions),
                "total_virtual_groups": len(virtual_groups_descriptions),
            },
            "tenants": tenant_descriptions,
            "virtual_groups": virtual_groups_descriptions,
            "environment_overview": environment_overview,
            "license_summary": license_summary,
            # Live Guardian state — what's firing RIGHT NOW, RBAC-filtered.
            # Paired with `knowledge_reference.configuration_guardian` (static,
            # what Guardian IS + assistant playbook) so the AI has both the
            # current state and the patterns for how to guide the user
            # through remediation.
            "guardian_alerts": guardian_alerts,
            # Recent AI Advisor runs across visible tenants. Paired with
            # `knowledge_reference.ai_advisors` (static — what each advisor
            # IS + the action-contract schema + assistant playbook). The AI
            # Assistant uses both: the recent runs to avoid proposing
            # redundant invocations, and the knowledge to construct a valid
            # `advisor_invocation` contract when proposing.
            "ai_advisor_recent_runs": ai_advisor_recent_runs,
            "knowledge_reference": knowledge_reference,
        }
    }
