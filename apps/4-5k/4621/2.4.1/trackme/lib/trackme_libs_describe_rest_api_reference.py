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

import time
import logging
from trackme_libs_logging import get_effective_logger

from trackme_libs_describe_concierge import build_concierge_knowledge


def get_resource_groups_map():
    """Return just the resource-groups dictionary from the knowledge block.

    Exposed as a public helper so other modules — notably the Concierge
    Advisor system prompt — can import the same hand-curated semantic
    map without duplicating it. The full
    ``_build_knowledge_reference`` block is shipped to the REST API
    Reference's AI Assistant context (heavyweight, includes auth /
    pagination / SPL command details); the Concierge only needs the
    resource-groups portion to scope its discovery tree.

    Each entry has at minimum ``name`` and ``description``; most also
    have ``base_path`` and ``sub_groups``. Keep this consumer-stable —
    if you tweak the structure, update the Concierge system prompt's
    embedded format spec at the same time.
    """
    return _build_knowledge_reference()["resource_groups"]


def _build_knowledge_reference():
    """
    Build a static knowledge reference section that provides the AI assistant
    with comprehensive understanding of the TrackMe REST API v2: resource groups,
    endpoint discovery patterns, authentication, HTTP methods, common patterns,
    and usage examples.

    This is intentionally static — the REST API Reference context provides
    structural knowledge about how the API is organized and how to discover
    endpoint capabilities at runtime using the describe=true pattern, rather
    than fetching every individual endpoint description.
    """
    knowledge = {
        "resource_groups": {
            "alerting": {
                "name": "Alerting",
                "description": (
                    "Manage alerting configuration and alert actions. Includes "
                    "user-level read operations and admin-level management."
                ),
                "base_path": "/services/trackme/v2/alerting",
                "sub_groups": ["alerting", "alerting/admin"],
            },
            "ack": {
                "name": "Acknowledgement",
                "description": (
                    "Manage entity acknowledgements: acknowledge alerts, "
                    "view acknowledgement status, and manage ack records."
                ),
                "base_path": "/services/trackme/v2/ack",
                "sub_groups": ["ack", "ack/write"],
            },
            "audit": {
                "name": "Audit",
                "description": (
                    "Query audit trail records for TrackMe operations, "
                    "configuration changes, and user actions."
                ),
                "base_path": "/services/trackme/v2/audit",
            },
            "backup_and_restore": {
                "name": "Backup & Restore",
                "description": (
                    "Manage backup and restore operations for TrackMe KV store "
                    "collections. Create backups, list available backups, restore "
                    "from snapshots, import/export backup archives."
                ),
                "base_path": "/services/trackme/v2/backup_and_restore",
            },
            "configuration": {
                "name": "Configuration Management",
                "description": (
                    "Manage global TrackMe configuration settings including system-wide "
                    "defaults, feature toggles, and application preferences."
                ),
                "base_path": "/services/trackme/v2/configuration",
                "sub_groups": ["configuration", "configuration/admin"],
            },
            "maintenance": {
                "name": "Maintenance Mode",
                "description": (
                    "Manage global maintenance mode: enable or disable maintenance, "
                    "schedule maintenance windows with start and end times, and "
                    "query current maintenance status."
                ),
                "base_path": "/services/trackme/v2/maintenance",
            },
            "maintenance_kdb": {
                "name": "Maintenance Knowledge Database",
                "description": (
                    "Manage per-entity maintenance records in the knowledge database. "
                    "Add, update, delete, and query maintenance KDB records. "
                    "Supports bulk operations."
                ),
                "base_path": "/services/trackme/v2/maintenance_kdb",
                "sub_groups": ["maintenance_kdb", "maintenance_kdb/admin"],
            },
            "bank_holidays": {
                "name": "Bank Holidays",
                "description": (
                    "Manage bank holiday definitions that affect SLA calculations "
                    "and monitoring behavior. Create, update, and delete holiday "
                    "periods by country."
                ),
                "base_path": "/services/trackme/v2/bank_holidays",
                "sub_groups": ["bank_holidays", "bank_holidays/admin"],
            },
            "licensing": {
                "name": "License Management",
                "description": (
                    "Query and manage TrackMe licensing information. Retrieve current "
                    "license status, register license keys, manage trial and developer modes."
                ),
                "base_path": "/services/trackme/v2/licensing",
                "sub_groups": ["licensing", "licensing/admin"],
            },
            "vtenants": {
                "name": "Virtual Tenants Management",
                "description": (
                    "Manage virtual tenants lifecycle: create, update, enable, disable, "
                    "delete tenants. Includes component management (add/remove DSM, DHM, "
                    "MHM, FLX, FQM, WLK), RBAC configuration, and tenant status operations."
                ),
                "base_path": "/services/trackme/v2/vtenants",
                "sub_groups": ["vtenants", "vtenants/write", "vtenants/admin"],
            },
            "splk_dsm": {
                "name": "Data Source Monitoring (DSM)",
                "description": (
                    "Manage DSM entities: query entity status, update thresholds, "
                    "configure monitoring parameters, manage elastic sources, and "
                    "perform entity-level operations (enable, disable, reset, delete)."
                ),
                "base_path": "/services/trackme/v2/splk_dsm",
                "sub_groups": ["splk_dsm", "splk_dsm/write"],
            },
            "splk_dhm": {
                "name": "Data Host Monitoring (DHM)",
                "description": (
                    "Manage DHM entities: query host-level monitoring status, update "
                    "delay and latency thresholds, and perform entity-level operations."
                ),
                "base_path": "/services/trackme/v2/splk_dhm",
                "sub_groups": ["splk_dhm", "splk_dhm/write"],
            },
            "splk_mhm": {
                "name": "Metrics Host Monitoring (MHM)",
                "description": (
                    "Manage MHM entities: query metrics host status, update metric "
                    "lag thresholds, manage metric category policies, and perform "
                    "entity-level operations."
                ),
                "base_path": "/services/trackme/v2/splk_mhm",
                "sub_groups": ["splk_mhm", "splk_mhm/write"],
            },
            "splk_flx": {
                "name": "Flex Objects Monitoring (FLX)",
                "description": (
                    "Manage FLX entities: query custom use-case entity status, update "
                    "thresholds and inactivity timeouts, manage converging trackers, "
                    "and perform entity-level operations."
                ),
                "base_path": "/services/trackme/v2/splk_flx",
                "sub_groups": ["splk_flx", "splk_flx/write", "splk_flx/admin"],
            },
            "splk_fqm": {
                "name": "Fields Quality Monitoring (FQM)",
                "description": (
                    "Manage FQM entities: query field quality status, manage dictionaries, "
                    "update success and coverage thresholds, and perform entity-level operations."
                ),
                "base_path": "/services/trackme/v2/splk_fqm",
                "sub_groups": ["splk_fqm", "splk_fqm/write", "splk_fqm/admin"],
            },
            "splk_wlk": {
                "name": "Workload Monitoring (WLK)",
                "description": (
                    "Manage WLK entities: query scheduled search execution health, "
                    "manage skipping and error thresholds, and perform entity-level operations."
                ),
                "base_path": "/services/trackme/v2/splk_wlk",
                "sub_groups": ["splk_wlk", "splk_wlk/write", "splk_wlk/admin"],
            },
            "splk_data_sampling": {
                "name": "Data Sampling",
                "description": (
                    "Manage data sampling configuration and results for DSM entities. "
                    "Query sampling models, trigger on-demand samples, and manage "
                    "sampling rules and schedules."
                ),
                "base_path": "/services/trackme/v2/splk_data_sampling",
                "sub_groups": ["splk_data_sampling", "splk_data_sampling/write"],
            },
            "splk_blocklist": {
                "name": "Blocklists",
                "description": (
                    "Manage entity blocklist rules: add, update, and remove blocklist "
                    "entries that prevent specific entities from being monitored. "
                    "Supports exact match and regex patterns."
                ),
                "base_path": "/services/trackme/v2/splk_blocklist",
                "sub_groups": ["splk_blocklist", "splk_blocklist/write"],
            },
            "splk_hybrid_trackers": {
                "name": "Hybrid Trackers",
                "description": (
                    "Manage hybrid tracker lifecycle: create, update, delete, and "
                    "execute trackers across all component types. Query tracker "
                    "status and execution history."
                ),
                "base_path": "/services/trackme/v2/splk_hybrid_trackers",
                "sub_groups": ["splk_hybrid_trackers", "splk_hybrid_trackers/admin"],
            },
            "splk_replica_trackers": {
                "name": "Replica Trackers",
                "description": (
                    "Manage replica tracker configuration for cross-instance "
                    "entity replication and synchronization."
                ),
                "base_path": "/services/trackme/v2/splk_replica_trackers",
                "sub_groups": ["splk_replica_trackers", "splk_replica_trackers/admin"],
            },
            "splk_elastic_sources": {
                "name": "Elastic Sources",
                "description": (
                    "Manage elastic source definitions that dynamically map "
                    "data sources to monitoring entities based on patterns."
                ),
                "base_path": "/services/trackme/v2/splk_elastic_sources",
                "sub_groups": ["splk_elastic_sources", "splk_elastic_sources/admin"],
            },
            "splk_lagging_classes": {
                "name": "Lagging Classes",
                "description": (
                    "Manage lagging class definitions that set default lag "
                    "thresholds for groups of entities based on classification."
                ),
                "base_path": "/services/trackme/v2/splk_lagging_classes",
                "sub_groups": ["splk_lagging_classes", "splk_lagging_classes/write"],
            },
            "splk_logical_groups": {
                "name": "Logical Groups",
                "description": (
                    "Manage logical group definitions that aggregate multiple "
                    "entities into a single monitoring unit."
                ),
                "base_path": "/services/trackme/v2/splk_logical_groups",
                "sub_groups": ["splk_logical_groups", "splk_logical_groups/write"],
            },
            "splk_outliers_engine": {
                "name": "Outliers Engine",
                "description": (
                    "Manage the outliers detection engine configuration and "
                    "query outlier detection results for monitored entities."
                ),
                "base_path": "/services/trackme/v2/splk_outliers_engine",
                "sub_groups": ["splk_outliers_engine", "splk_outliers_engine/write"],
            },
            "splk_disruption": {
                "name": "Disruption Detection",
                "description": (
                    "Query and manage disruption detection results for "
                    "monitoring anomalous patterns across entities."
                ),
                "base_path": "/services/trackme/v2/splk_disruption",
                "sub_groups": ["splk_disruption", "splk_disruption/write"],
            },
            "splk_tag_policies": {
                "name": "Tag Policies",
                "description": (
                    "Manage tag-based policies that automatically assign tags to entities. "
                    "Supports two policy types: regex-based (match a regular expression against the entity "
                    "object field and assign comma-separated tag values) and lookup-based (leverage Splunk "
                    "lookups/CMDB data to assign tags through field mappings with exact or wildcard matching "
                    "and a configurable tags separator). "
                    "Read endpoints list transforms, lookup fields, and entity fields for configuration. "
                    "Write endpoints support add, update, simulate (preview matches), and apply (persist "
                    "tag assignments) operations."
                ),
                "base_path": "/services/trackme/v2/splk_tag_policies",
                "sub_groups": ["splk_tag_policies", "splk_tag_policies/write"],
            },
            "splk_priority_policies": {
                "name": "Priority Policies",
                "description": (
                    "Manage priority-based policies that control entity prioritization. "
                    "Supports two policy types: regex-based (match a regular expression against a "
                    "configurable entity field such as object, alias, data_index, or data_sourcetype) "
                    "and lookup-based (leverage Splunk lookups/CMDB data to assign priorities through "
                    "field mappings with exact or wildcard matching and optional value mappings). "
                    "Read endpoints list transforms, lookup fields, and entity fields for configuration. "
                    "Write endpoints support add, update, simulate (preview matches), and apply (persist "
                    "priority assignments) operations."
                ),
                "base_path": "/services/trackme/v2/splk_priority_policies",
                "sub_groups": ["splk_priority_policies", "splk_priority_policies/write"],
            },
            "splk_sla_policies": {
                "name": "SLA Policies",
                "description": (
                    "Manage SLA policy definitions that assign SLA classes to entities for availability "
                    "tracking. Supports two policy types: regex-based (match a regular expression against "
                    "the entity object field and assign a specific SLA class) and lookup-based (leverage "
                    "Splunk lookups/CMDB data to assign SLA classes through field mappings with exact or "
                    "wildcard matching and optional SLA value mappings). "
                    "Read endpoints list transforms, lookup fields, and entity fields for configuration. "
                    "Write endpoints support add, update, simulate (preview matches), and apply (persist "
                    "SLA class assignments) operations."
                ),
                "base_path": "/services/trackme/v2/splk_sla_policies",
                "sub_groups": ["splk_sla_policies", "splk_sla_policies/write"],
            },
            "splk_deleted_entities": {
                "name": "Deleted Entities",
                "description": (
                    "Query and manage soft-deleted entities that have been "
                    "removed from active monitoring but retained for audit."
                ),
                "base_path": "/services/trackme/v2/splk_deleted_entities",
                "sub_groups": ["splk_deleted_entities", "splk_deleted_entities/write"],
            },
            "splk_soar": {
                "name": "SOAR Integration",
                "description": (
                    "Manage SOAR (Security Orchestration, Automation and Response) "
                    "integration configuration and operations."
                ),
                "base_path": "/services/trackme/v2/splk_soar",
                "sub_groups": ["splk_soar", "splk_soar/admin"],
            },
            "component": {
                "name": "Component Management",
                "description": (
                    "Manage TrackMe components within tenants: query component "
                    "status, configuration, and perform component-level operations."
                ),
                "base_path": "/services/trackme/v2/component",
                "sub_groups": ["component", "component/write"],
            },
            "notes": {
                "name": "Notes",
                "description": (
                    "Manage notes attached to entities for documentation, "
                    "investigation tracking, and team collaboration."
                ),
                "base_path": "/services/trackme/v2/notes",
                "sub_groups": ["notes", "notes/write"],
            },
            "describe": {
                "name": "AI Entity Description",
                "description": (
                    "Generate AI-consumable structured descriptions of tenants, "
                    "entities, and environment state. Used by the AI assistant "
                    "to build context for user interactions."
                ),
                "base_path": "/services/trackme/v2/describe",
            },
            "ai": {
                "name": "AI Assistant Chat",
                "description": (
                    "AI assistant chat endpoints for conversational interaction "
                    "with TrackMe. Handles message routing, context management, "
                    "and response generation."
                ),
                "base_path": "/services/trackme/v2/ai",
                "sub_groups": ["ai", "ai/admin"],
            },
        },
        "endpoint_discovery": {
            "description": (
                "All TrackMe REST API endpoints support runtime self-documentation "
                "via the describe=true pattern. This is the recommended way to discover "
                "the exact endpoints, parameters, and usage examples for any resource group."
            ),
            "how_it_works": (
                "Send a request to any endpoint with {'describe': true} in the body. "
                "The endpoint will return its documentation instead of executing the operation. "
                "The response includes: resource_desc (what the endpoint does), "
                "resource_spl_example (SPL usage example), and options (accepted parameters "
                "with types and descriptions)."
            ),
            "discover_resource_group_endpoints": (
                "To discover all endpoints in a resource group, use the | trackmeapiautodocs "
                "SPL command which iterates over all handler methods and collects their "
                "describe responses. Alternatively, call each endpoint individually with "
                "describe=true."
            ),
            "example_describe_response": {
                "describe": "This endpoint lists all the backup files available on the search head...",
                "resource_desc": "Get the list of backups known to TrackMe",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/backup_and_restore/backup"',
                "options": [
                    {
                        "mode": "(string) OPTIONAL: The output mode, valid values are full | summary",
                    }
                ],
            },
            "resource_group_description": (
                "Each resource group also has a resource_group_desc endpoint that returns "
                "the group name and description. Access it via GET to "
                "/services/trackme/v2/<resource_group>/resource_group_desc_<suffix>."
            ),
        },
        "spl_trackme_command": {
            "description": (
                "The '| trackme' SPL custom command allows calling TrackMe REST API "
                "endpoints directly from Splunk searches. This is useful for automation, "
                "scheduled actions, and integration with Splunk dashboards."
            ),
            "syntax": '| trackme url="<endpoint_path>" mode="<http_method>" body="<json_payload>"',
            "parameters": {
                "url": "The REST API endpoint path (e.g. '/services/trackme/v2/vtenants/trackmeload')",
                "mode": "The HTTP method: 'get', 'post', or 'delete'",
                "body": "JSON payload as a string (required for POST requests, optional for GET)",
            },
            "examples": [
                {
                    "description": "Load all virtual tenants",
                    "spl": "| trackme url=\"/services/trackme/v2/vtenants/trackmeload\" mode=\"post\" body=\"{'mode': 'full'}\"",
                },
                {
                    "description": "Query DSM entities for a specific tenant",
                    "spl": "| trackme url=\"/services/trackme/v2/splk_dsm/get_entities\" mode=\"post\" body=\"{'tenant_id': 'my_tenant'}\"",
                },
                {
                    "description": "Get endpoint self-documentation",
                    "spl": "| trackme url=\"/services/trackme/v2/splk_dsm/get_entities\" mode=\"post\" body=\"{'describe': true}\"",
                },
            ],
            "notes": (
                "The | trackme command inherits the permissions of the executing user. "
                "RBAC rules apply the same way as direct REST API calls."
            ),
        },
        "authentication": {
            "description": (
                "TrackMe REST API endpoints are served through Splunk's splunkd REST "
                "framework. Authentication follows standard Splunk REST API patterns."
            ),
            "methods": {
                "splunk_session_token": {
                    "description": (
                        "Use a Splunk session key obtained via splunkd authentication. "
                        "This is the standard method when calling from within Splunk "
                        "(searches, scripts, apps)."
                    ),
                    "header": "Authorization: Splunk <session_key>",
                },
                "basic_auth": {
                    "description": (
                        "Use HTTP Basic Authentication with Splunk credentials. "
                        "Suitable for external scripts, CI/CD pipelines, and curl-based access."
                    ),
                    "curl_example": (
                        "curl -k -u admin:password "
                        "https://localhost:8089/services/trackme/v2/splk_dsm/get_entities "
                        "-d '{\"tenant_id\": \"my_tenant\"}'"
                    ),
                },
                "bearer_token": {
                    "description": (
                        "Use a Splunk authentication token (Bearer token) for API calls. "
                        "Tokens can be created in Splunk Settings > Tokens."
                    ),
                    "header": "Authorization: Bearer <token>",
                },
            },
            "notes": (
                "All API calls require valid Splunk authentication. The user's Splunk "
                "roles determine RBAC access to TrackMe tenants and operations. "
                "SSL verification can be skipped with -k for self-signed certificates."
            ),
        },
        "http_methods": {
            "GET": {
                "description": "Used for simple read operations and health checks.",
                "typical_use": "Retrieving endpoint documentation, status checks.",
            },
            "POST": {
                "description": (
                    "Used for both create/action operations AND read/query operations. "
                    "In TrackMe, POST is the primary method for querying entities and "
                    "data, not GET. Query parameters are passed in the request body."
                ),
                "typical_use": (
                    "Querying entities, creating resources, updating configurations, "
                    "triggering actions (enable, disable, execute)."
                ),
                "note": (
                    "POST is used for reads/queries because TrackMe passes structured "
                    "JSON payloads (tenant_id, filters, options) that exceed URL parameter limits."
                ),
            },
            "DELETE": {
                "description": "Used for deletion operations.",
                "typical_use": "Removing entities, deleting tenants, removing configurations.",
            },
        },
        "common_patterns": {
            "self_documentation": {
                "description": (
                    "All endpoints support the 'describe=true' parameter in the request "
                    "body. When set, the endpoint returns its own documentation including "
                    "accepted parameters, expected types, and usage examples."
                ),
                "example": '{"describe": true}',
                "note": "This is the recommended way to discover endpoint capabilities at runtime.",
            },
            "response_format": {
                "success": {
                    "structure": '{"payload": {...}, "status": 200}',
                    "description": (
                        "Successful responses return a JSON object with a 'payload' key "
                        "containing the result data and a 'status' key with the HTTP status code."
                    ),
                },
                "error": {
                    "structure": '{"payload": {"action": "failure", "response": "<error_message>"}, "status": 500}',
                    "description": (
                        "Error responses return a JSON object with 'payload' containing "
                        "an 'action' field set to 'failure' and a 'response' field with "
                        "the error description."
                    ),
                },
            },
            "entity_identifiers": {
                "object": (
                    "The entity name (human-readable identifier). Used to reference "
                    "entities by their display name (e.g. 'index:sourcetype' for DSM)."
                ),
                "object_id": (
                    "The KV store internal key (_key). Used as the unique identifier "
                    "for direct record operations. Preferred for programmatic access."
                ),
                "tenant_id": (
                    "Required in most endpoints to scope the operation to a specific "
                    "virtual tenant."
                ),
            },
        },
        "pagination_and_filtering": {
            "description": (
                "TrackMe uses Splunk KV store as its backend. There is no traditional "
                "offset/limit pagination. Large result sets can be filtered using "
                "query parameters passed in the request body."
            ),
            "filtering_approach": (
                "Use the endpoint's supported filter parameters (e.g. tenant_id, "
                "object_state, priority) to narrow results. Some endpoints support "
                "a 'query' parameter accepting KV store query syntax for advanced filtering."
            ),
            "best_practices": [
                "Always scope queries with tenant_id to avoid cross-tenant data leaks",
                "Use object_state filters to focus on entities needing attention (e.g. 'red')",
                "Use the describe=true pattern to discover available filter parameters",
            ],
        },
        "versioning": {
            "description": (
                "All TrackMe REST API endpoints are served under the /services/trackme/v2/ "
                "path prefix. The 'v2' denotes the current stable API version."
            ),
            "base_url": "/services/trackme/v2/",
            "full_url_pattern": "https://<splunk_host>:8089/services/trackme/v2/<resource_group>/<endpoint>",
            "notes": (
                "The v2 API is the only supported version. All integrations should use "
                "the v2 prefix. Endpoint paths are stable and backward-compatible within "
                "the v2 version."
            ),
        },
    }

    return knowledge


def build_rest_api_reference_description(service, request_info):
    """
    Build a comprehensive, AI-consumable description of the TrackMe REST API v2.

    This is a static knowledge reference that documents the API structure,
    resource groups, endpoint discovery patterns, authentication, and usage.
    It does not dynamically fetch endpoint descriptions — instead it teaches
    the AI how to guide users to discover endpoints via the describe=true pattern.

    Args:
        service: Splunk service connection (unused, accepted for consistency)
        request_info: REST request info (unused, accepted for consistency)

    Returns:
        dict: Structured REST API reference description
    """

    knowledge_reference = _build_knowledge_reference()

    # Embed the Concierge advisor knowledge so the chat LLM can propose
    # ``concierge_invocation`` action contracts when the user asks for
    # something actionable on this surface (e.g. "show me how to call
    # endpoint X", "wire up a new tenant via the API"). The Concierge
    # block also ships a compact projection of the live API catalog —
    # without it the LLM falls back to training-data guesses for paths.
    try:
        session_key = request_info.system_authtoken
        splunkd_uri = request_info.server_rest_uri
        # ``feature_context`` is intentionally NOT set on this surface.
        # The REST API Reference panel is a meta-surface — the user is
        # exploring the entire ~423-endpoint catalog, not pinned to a
        # specific resource group's feature page. Setting
        # ``feature_context="rest_api_reference"`` would tell the LLM to
        # prefer entries whose ``resource_group`` matches that string,
        # but no such resource group exists in the catalog (groups are
        # ``licensing`` / ``maintenance`` / ``backup_and_restore`` /
        # ``bank_holidays`` / etc.) so the hint would be misleading,
        # nudging the LLM to filter against an empty match set.
        # Cross-feature surfaces (like this one and the entity /
        # tenant_home / vtenants surfaces) intentionally pass through
        # without a feature_context — the LLM treats every catalog
        # entry as equally relevant.
        knowledge_reference["concierge_advisor"] = build_concierge_knowledge(
            splunkd_uri=splunkd_uri,
            session_key=session_key,
            surface="global",
        )
    except Exception as e:
        get_effective_logger().error(
            f'function=build_rest_api_reference_description, '
            f'step="build_concierge_knowledge", '
            f'exception="{str(e)}"'
        )

    return {
        "rest_api_reference_description": {
            "meta": {
                "api_version": "2.0",
                "generated_at": time.time(),
                "context_type": "rest_api_reference",
            },
            "knowledge_reference": knowledge_reference,
        }
    }
