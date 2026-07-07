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

from trackme_libs_describe_tenant_home import _safe_int
from trackme_libs_describe_concierge import build_concierge_knowledge
from trackme_libs_describe_utils import (
    fetch_resource_group_describe,
    fetch_all_endpoint_describes,
)

# Endpoint registries per context type
MAINTENANCE_MODE_ENDPOINTS = [
    {"method": "get", "url": "maintenance/check_global_maintenance_status"},
    {"method": "post", "url": "maintenance/global_maintenance_enable"},
    {"method": "post", "url": "maintenance/maintenance_disable"},
]

MAINTENANCE_KDB_ENDPOINTS = [
    {"method": "post", "url": "maintenance_kdb/admin/maintenance_kdb_add_record"},
    {"method": "post", "url": "maintenance_kdb/admin/maintenance_kdb_manage_record"},
    {"method": "post", "url": "maintenance_kdb/admin/maintenance_kdb_check_expired"},
    {"method": "post", "url": "maintenance_kdb/admin/maintenance_kdb_bulk_edit"},
]

BANK_HOLIDAYS_ENDPOINTS = [
    {"method": "post", "url": "bank_holidays/admin/create"},
    {"method": "post", "url": "bank_holidays/admin/update"},
    {"method": "post", "url": "bank_holidays/admin/delete"},
    {"method": "post", "url": "bank_holidays/admin/delete_all"},
]


def build_entity_maintenance_knowledge():
    """Static knowledge block describing PER-ENTITY maintenance mode.

    Distinct from global maintenance mode (tenant-wide alert suppression) and
    the maintenance KDB (a documentation knowledge base of planned windows).
    Per-entity maintenance is a first-class decision-maker override: while a
    window is active, the entity is FORCED to BLUE (protected) with top
    precedence over every other state and protection layer, and alerting is
    suppressed for that single entity until the window expires.

    Surfaced under ``knowledge_reference.entity_maintenance`` on the entity,
    tenant_home, and vtenants describe payloads so the AI Assistant can explain
    the feature and guide the user (or propose the action via an advisor).
    """
    return {
        "overview": (
            "Per-entity maintenance mode forces a single entity into BLUE "
            "(protected) state for an explicit time window (start + end). "
            "While active, the decision maker overrides the entity's computed "
            "state (green/orange/red) AND every other protection layer "
            "(acknowledgment, disruption grace, logical-group protection) — "
            "maintenance has TOP precedence. Because BLUE is a non-alerting "
            "state, alerting is suppressed for that entity until the window "
            "expires, at which point it returns to normal monitoring "
            "automatically on the next decision-maker cycle."
        ),
        "vs_other_maintenance": (
            "Global/tenant maintenance mode suppresses alerting across an "
            "entire tenant; per-entity maintenance targets ONE entity (or a "
            "bulk selection) without affecting the rest. The maintenance KDB "
            "is a documentation knowledge base of planned windows; per-entity "
            "maintenance is the enforced override that actually flips the "
            "state to blue."
        ),
        "applies_to": "All six components: DSM, DHM, MHM, FLX, FQM, WLK.",
        "state_behavior": {
            "while_active": (
                "object_state is forced to 'blue'; the status message leads "
                "with 'Entity is under scheduled maintenance until <end>'. The "
                "score is still computed and visible, but the entity does not "
                "alert."
            ),
            "after_expiry": (
                "The override is inert the moment now >= maintenance_end_epoch. "
                "The entity flips back to its computed state (green/orange/red) "
                "on the next cycle. Expired records are purged after a grace "
                "period by the general health manager."
            ),
        },
        "configuration": {
            "where": (
                "Tenant Home → per-entity 3-dot Actions menu → 'Maintenance', "
                "or the bulk-edit modal → 'Maintenance' category for many "
                "entities at once."
            ),
            "fields": {
                "maintenance_start_epoch": "Window start. Accepts 'now', a relative offset (+30m/+2h/+1d or bare seconds +1800), an absolute epoch, or an ISO datetime.",
                "maintenance_end_epoch": "Window end, same formats. For 'next N hours' use start='now', end='+Nh'. Must be after start and in the future.",
                "maintenance_comment": "Free-text reason, surfaced in the status message, UI, describe, and audit.",
            },
        },
        "rest_api": {
            "list": "POST /trackme/v2/entity_maintenance/list_maintenance {tenant_id, keys_list?}",
            "set": "POST /trackme/v2/entity_maintenance/write/set_maintenance {tenant_id, component, keys_list, maintenance_start_epoch, maintenance_end_epoch, maintenance_comment?} — start/end accept 'now', relative offsets ('+24h', '+86400'), absolute epoch, or ISO datetime; for 'next 24h' send start='now', end='+24h'",
            "clear": "POST /trackme/v2/entity_maintenance/write/clear_maintenance {tenant_id, keys_list}",
        },
        "ai_tools": {
            "get_entity_maintenance": "Read current maintenance state for an entity (all advisors + Concierge).",
            "set_entity_maintenance": "Put an entity into maintenance for a duration (act-capable advisors).",
            "clear_entity_maintenance": "End an entity's maintenance window immediately (act-capable advisors).",
        },
        "assistant_playbook": (
            "If the user wants to silence/shield a single entity for a known "
            "window (planned upgrade, data backfill, a remediation you are "
            "about to perform), propose per-entity maintenance rather than an "
            "acknowledgment — maintenance protects regardless of the underlying "
            "state and self-clears at the end time. Always state the end time "
            "back to the user. To remove protection early, clear the window. "
            "Use get_entity_maintenance first to check whether a window is "
            "already active before proposing a new one."
        ),
        "reference_docs": [
            "https://docs.trackme-solutions.com/latest/admin_guide_maintenance.html",
        ],
    }


def _build_maintenance_knowledge_reference(
    api_endpoints=None,
    resource_group_info=None,
    request_info=None,
    feature_context=None,
):
    """
    Build a knowledge reference section covering maintenance mode,
    maintenance KDB, and bank holidays concepts. This provides the AI
    assistant with comprehensive understanding of these features, their
    operations, and available API endpoints.

    Args:
        api_endpoints: List of dynamically fetched endpoint describe responses.
                       If None, a fallback note is included.
        resource_group_info: Resource group description dict from the handler.
        request_info: REST request info — when provided, the Concierge
                       advisor knowledge block is embedded under
                       ``concierge_advisor`` so the chat LLM can propose
                       ``concierge_invocation`` action contracts (e.g.
                       "schedule a maintenance window", "add UK bank
                       holidays for 2026"). Failures are logged and don't
                       break the rest of the knowledge reference.
        feature_context: Resource-group hint forwarded to
                       ``build_concierge_knowledge``. Each
                       ``build_*_description`` function passes its own
                       value (``"maintenance"``, ``"maintenance_kdb"``,
                       or ``"bank_holidays"``) so the LLM can scope
                       endpoint selection to the active feature page.
    """
    ref = {
        "maintenance_mode_concepts": {
            "global_maintenance_mode": (
                "Disables all alerting across ALL tenants. Used during planned "
                "maintenance windows such as infrastructure upgrades, Splunk "
                "restarts, or scheduled downtime periods."
            ),
            "scheduling": (
                "Can be enabled immediately or scheduled for a future time window. "
                "Start and end timestamps define the maintenance period. When the "
                "end time is reached, maintenance mode is automatically disabled."
            ),
            "impact_on_alerting": (
                "When active, all alert actions are suppressed. Entities continue "
                "to be monitored and their states are tracked, but no alert "
                "notifications fire. This prevents false-positive alerts during "
                "known disruption periods."
            ),
            "scope": (
                "Global maintenance affects all tenants and all components. "
                "There is no per-tenant or per-component granularity at this "
                "level; use the maintenance KDB for entity-level scheduling."
            ),
        },
        "maintenance_kdb_concepts": {
            "purpose": (
                "Knowledge base of recurring or planned maintenance windows "
                "per entity. Allows fine-grained maintenance scheduling without "
                "affecting the entire environment."
            ),
            "per_entity_scheduling": (
                "Each KDB record targets a specific entity identified by "
                "object + object_category + tenant_id. This enables maintenance "
                "windows for individual data sources, hosts, or flex objects."
            ),
            "when_active": (
                "While a maintenance KDB window is active for an entity, the "
                "entity's state appears as 'blue' (maintenance) instead of "
                "triggering alerts. The entity continues to be tracked."
            ),
            "crud_operations": (
                "Records can be created, updated, and deleted via the UI or "
                "REST API. Each record contains start and end timestamps, "
                "the target entity identifiers, and an optional description."
            ),
            "time_based": (
                "Records have start and end times. Expired records can be "
                "cleaned up. Active records are those where the current time "
                "falls between start and end timestamps."
            ),
        },
        "bank_holidays_concepts": {
            "purpose": (
                "Define holiday periods during which alerting behavior can be "
                "adjusted. Bank holidays represent non-business days where "
                "different monitoring thresholds or suppression rules apply."
            ),
            "country_calendars": (
                "Holidays are organized by country code. Each country can have "
                "its own set of holidays, allowing multinational organizations "
                "to manage region-specific non-business days."
            ),
            "sla_interaction": (
                "Bank holidays can exclude specific dates from SLA calculations. "
                "When computing availability percentages, holiday periods are "
                "factored out to avoid penalizing normal non-business downtime."
            ),
            "automatic_adjustment": (
                "When a bank holiday is active, monitoring thresholds may be "
                "relaxed or alerting suppressed for affected entities. This "
                "prevents false alerts during expected low-activity periods."
            ),
            "recurring": (
                "Holiday calendars can be set up once and reused across years. "
                "Recurring holidays simplify annual calendar management for "
                "organizations with predictable holiday schedules."
            ),
        },
        "per_entity_maintenance_concepts": build_entity_maintenance_knowledge(),
        "reference_docs": [
            "https://docs.trackme-solutions.com/latest/admin_guide_maintenance.html",
            "https://docs.trackme-solutions.com/latest/admin_guide_bank_holidays.html",
        ],
    }

    # Add dynamic API endpoint descriptions
    if api_endpoints:
        ref["api_endpoints"] = api_endpoints
    else:
        ref["api_endpoints"] = {
            "note": "Dynamic endpoint descriptions were not available."
        }

    # Add resource group info
    if resource_group_info:
        ref["resource_group"] = resource_group_info

    # Embed Concierge advisor knowledge so the chat LLM can propose
    # ``concierge_invocation`` action contracts on this surface (e.g.
    # "enable global maintenance for tenant X for 2 hours", "create a
    # KDB record for entity Y", "import UK bank holidays for 2026"). The
    # block also ships a compact projection of the live API catalog —
    # without it the LLM falls back to training-data guesses for paths.
    if request_info is not None:
        try:
            ref["concierge_advisor"] = build_concierge_knowledge(
                splunkd_uri=request_info.server_rest_uri,
                session_key=request_info.system_authtoken,
                surface="global",
                feature_context=feature_context,
            )
        except Exception as e:
            get_effective_logger().error(
                f'function=_build_maintenance_knowledge_reference, '
                f'step="build_concierge_knowledge", '
                f'exception="{str(e)}"'
            )

    return ref


def build_maintenance_mode_description(service, request_info):
    """
    Build a comprehensive, AI-consumable description of the global
    maintenance mode status.

    Args:
        service: Splunk service connection (system-level for KV store access)
        request_info: REST request info (for session key, server URI, user context)

    Returns:
        dict: Structured maintenance mode description
    """

    # Helper to fetch endpoint descriptions for this context type
    def _fetch_maintenance_mode_endpoints():
        api_endpoints = None
        resource_group_info = None
        try:
            session_key = request_info.system_authtoken
            splunkd_uri = request_info.server_rest_uri
            resource_group_info = fetch_resource_group_describe(
                session_key, splunkd_uri, "maintenance", "maintenance"
            )
            api_endpoints = fetch_all_endpoint_describes(
                session_key, splunkd_uri, MAINTENANCE_MODE_ENDPOINTS
            )
        except Exception as ex:
            get_effective_logger().error(
                f'function=build_maintenance_mode_description, '
                f'step="fetch_endpoint_describes", '
                f'exception="{str(ex)}"'
            )
        return api_endpoints, resource_group_info

    collection_name = "kv_trackme_maintenance_mode"
    try:
        collection = service.kvstore[collection_name]
        records = collection.data.query()
    except Exception as e:
        get_effective_logger().error(
            f'function=build_maintenance_mode_description, '
            f'step="query_kv_store", collection="{collection_name}", '
            f'exception="{str(e)}"'
        )
        # KV store failed but endpoint fetch is independent — still attempt it
        api_endpoints, resource_group_info = _fetch_maintenance_mode_endpoints()
        knowledge_reference = _build_maintenance_knowledge_reference(
            api_endpoints=api_endpoints,
            resource_group_info=resource_group_info,
            request_info=request_info,
            feature_context="maintenance",
        )
        return {
            "maintenance_mode_description": {
                "meta": {
                    "api_version": "2.0",
                    "generated_at": time.time(),
                    "context_type": "maintenance_mode",
                },
                "maintenance_summary": {
                    "total_records": 0,
                    "records": [],
                    "error": str(e),
                },
                "knowledge_reference": knowledge_reference,
            }
        }

    # Build per-record summaries
    record_summaries = []
    for record in records:
        record_summaries.append({
            "_key": record.get("_key", ""),
            "tenants_scope": record.get("tenants_scope", ""),
            "maintenance_mode": record.get("maintenance_mode", "disabled"),
            "maintenance_mode_start": _safe_int(record.get("maintenance_mode_start")),
            "maintenance_mode_end": _safe_int(record.get("maintenance_mode_end")),
            "maintenance_message": record.get("maintenance_message", ""),
            "maintenance_comment": record.get("maintenance_comment", ""),
            "src_user": record.get("src_user", ""),
        })

    # Dynamically fetch endpoint descriptions (reuse the helper)
    api_endpoints, resource_group_info = _fetch_maintenance_mode_endpoints()

    knowledge_reference = _build_maintenance_knowledge_reference(
        api_endpoints=api_endpoints,
        resource_group_info=resource_group_info,
        request_info=request_info,
        feature_context="maintenance",
    )

    return {
        "maintenance_mode_description": {
            "meta": {
                "api_version": "2.0",
                "generated_at": time.time(),
                "context_type": "maintenance_mode",
            },
            "maintenance_summary": {
                "total_records": len(record_summaries),
                "records": record_summaries,
            },
            "knowledge_reference": knowledge_reference,
        }
    }


def build_maintenance_kdb_description(service, request_info):
    """
    Build a comprehensive, AI-consumable description of the maintenance
    knowledge base records.

    Args:
        service: Splunk service connection (system-level for KV store access)
        request_info: REST request info (for session key, server URI, user context)

    Returns:
        dict: Structured maintenance KDB description
    """

    # Helper to fetch endpoint descriptions for this context type
    def _fetch_maintenance_kdb_endpoints():
        api_endpoints = None
        resource_group_info = None
        try:
            session_key = request_info.system_authtoken
            splunkd_uri = request_info.server_rest_uri
            resource_group_info = fetch_resource_group_describe(
                session_key, splunkd_uri, "maintenance_kdb/admin", "maintenance_kdb"
            )
            api_endpoints = fetch_all_endpoint_describes(
                session_key, splunkd_uri, MAINTENANCE_KDB_ENDPOINTS
            )
        except Exception as ex:
            get_effective_logger().error(
                f'function=build_maintenance_kdb_description, '
                f'step="fetch_endpoint_describes", '
                f'exception="{str(ex)}"'
            )
        return api_endpoints, resource_group_info

    collection_name = "kv_trackme_maintenance_kdb"
    try:
        collection = service.kvstore[collection_name]
        records = collection.data.query()
    except Exception as e:
        get_effective_logger().error(
            f'function=build_maintenance_kdb_description, '
            f'step="query_kv_store", collection="{collection_name}", '
            f'exception="{str(e)}"'
        )
        # KV store failed but endpoint fetch is independent — still attempt it
        api_endpoints, resource_group_info = _fetch_maintenance_kdb_endpoints()
        knowledge_reference = _build_maintenance_knowledge_reference(
            api_endpoints=api_endpoints,
            resource_group_info=resource_group_info,
            request_info=request_info,
            feature_context="maintenance_kdb",
        )
        return {
            "maintenance_kdb_description": {
                "meta": {
                    "api_version": "2.0",
                    "generated_at": time.time(),
                    "context_type": "maintenance_kdb",
                },
                "kdb_summary": {
                    "total_records": 0,
                    "records": [],
                    "error": str(e),
                },
                "knowledge_reference": knowledge_reference,
            }
        }

    # Sort by time_end descending so most recent entries come first,
    # then limit to 50 records for token efficiency
    records.sort(
        key=lambda r: _safe_int(r.get("time_end", 0)),
        reverse=True,
    )
    limited_records = records[:50]

    # Build per-record summaries
    record_summaries = []
    for record in limited_records:
        record_summaries.append({
            "_key": record.get("_key", ""),
            "tenants_scope": record.get("tenants_scope", ""),
            "type": record.get("type", ""),
            "reason": record.get("reason", ""),
            "is_disabled": record.get("is_disabled", ""),
            "time_start": record.get("time_start", ""),
            "time_end": record.get("time_end", ""),
            "time_expiration": record.get("time_expiration", ""),
            "no_days_validity": record.get("no_days_validity", ""),
            "src_user": record.get("src_user", ""),
        })

    # Dynamically fetch endpoint descriptions (reuse the helper)
    api_endpoints, resource_group_info = _fetch_maintenance_kdb_endpoints()

    knowledge_reference = _build_maintenance_knowledge_reference(
        api_endpoints=api_endpoints,
        resource_group_info=resource_group_info,
        request_info=request_info,
        feature_context="maintenance_kdb",
    )

    return {
        "maintenance_kdb_description": {
            "meta": {
                "api_version": "2.0",
                "generated_at": time.time(),
                "context_type": "maintenance_kdb",
            },
            "kdb_summary": {
                "total_records": len(records),
                "records": record_summaries,
            },
            "knowledge_reference": knowledge_reference,
        }
    }


def build_bank_holidays_description(service, request_info):
    """
    Build a comprehensive, AI-consumable description of the bank holiday
    records.

    Args:
        service: Splunk service connection (system-level for KV store access)
        request_info: REST request info (for session key, server URI, user context)

    Returns:
        dict: Structured bank holidays description
    """

    # Helper to fetch endpoint descriptions for this context type
    def _fetch_bank_holidays_endpoints():
        api_endpoints = None
        resource_group_info = None
        try:
            session_key = request_info.system_authtoken
            splunkd_uri = request_info.server_rest_uri
            resource_group_info = fetch_resource_group_describe(
                session_key, splunkd_uri, "bank_holidays/admin", "bank_holidays"
            )
            api_endpoints = fetch_all_endpoint_describes(
                session_key, splunkd_uri, BANK_HOLIDAYS_ENDPOINTS
            )
        except Exception as ex:
            get_effective_logger().error(
                f'function=build_bank_holidays_description, '
                f'step="fetch_endpoint_describes", '
                f'exception="{str(ex)}"'
            )
        return api_endpoints, resource_group_info

    collection_name = "kv_trackme_bank_holidays"
    try:
        collection = service.kvstore[collection_name]
        records = collection.data.query()
    except Exception as e:
        get_effective_logger().error(
            f'function=build_bank_holidays_description, '
            f'step="query_kv_store", collection="{collection_name}", '
            f'exception="{str(e)}"'
        )
        # KV store failed but endpoint fetch is independent — still attempt it
        api_endpoints, resource_group_info = _fetch_bank_holidays_endpoints()
        knowledge_reference = _build_maintenance_knowledge_reference(
            api_endpoints=api_endpoints,
            resource_group_info=resource_group_info,
            request_info=request_info,
            feature_context="bank_holidays",
        )
        return {
            "bank_holidays_description": {
                "meta": {
                    "api_version": "2.0",
                    "generated_at": time.time(),
                    "context_type": "bank_holidays",
                },
                "holidays_summary": {
                    "total_records": 0,
                    "records": [],
                    "error": str(e),
                },
                "knowledge_reference": knowledge_reference,
            }
        }

    # Sort by end_date descending so most recent holidays come first,
    # then limit to 100 records for token efficiency
    records.sort(
        key=lambda r: _safe_int(r.get("end_date", 0)),
        reverse=True,
    )
    limited_records = records[:100]

    # Build per-record summaries
    record_summaries = []
    for record in limited_records:
        record_summaries.append({
            "_key": record.get("_key", ""),
            "period_name": record.get("period_name", ""),
            "start_date": record.get("start_date", ""),
            "end_date": record.get("end_date", ""),
            "country_code": record.get("country_code", ""),
            "is_recurring": record.get("is_recurring", False),
            "comment": record.get("comment", ""),
        })

    # Dynamically fetch endpoint descriptions (reuse the helper)
    api_endpoints, resource_group_info = _fetch_bank_holidays_endpoints()

    knowledge_reference = _build_maintenance_knowledge_reference(
        api_endpoints=api_endpoints,
        resource_group_info=resource_group_info,
        request_info=request_info,
        feature_context="bank_holidays",
    )

    return {
        "bank_holidays_description": {
            "meta": {
                "api_version": "2.0",
                "generated_at": time.time(),
                "context_type": "bank_holidays",
            },
            "holidays_summary": {
                "total_records": len(records),
                "records": record_summaries,
            },
            "knowledge_reference": knowledge_reference,
        }
    }
