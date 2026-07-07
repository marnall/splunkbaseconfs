# coding=utf-8
"""
TrackMe API autodocs catalog — builder.

Catalog construction was historically embedded inside the
``trackmeapiautodocs`` custom search command (one big ``generate()``
that imported every REST handler, declared the per-handler
resource-group dict, walked each handler's methods via ``dir()``, and
fired an HTTPS loopback to splunkd against each one with
``describe=true`` to extract the self-documentation block).

That works for the SPL pipeline (the REST API Reference UI ingests
the SPL output) but is the wrong shape for a Concierge Advisor MCP
tool: the agent runs in a Python process, not in a search context,
and has no way to invoke a custom search command directly. We need
the same data via a programmatic API.

This module owns the catalog-building logic. It is callable from:

  * The ``trackmeapiautodocs`` search command (refactored to a thin
    SPL-yielding wrapper).
  * A new REST endpoint ``GET /trackme/v2/configuration/api_catalog``
    that returns the structured catalog as JSON.
  * The Concierge Advisor's MCP tool layer (future PR).

Behaviour is preserved exactly — the search command's output shape
does not change, dashboards reading the SPL output keep working.

See ``ai-context/integrations/concierge-advisor-implementation-plan.md``
for the wider plan and ``trackme_libs_autodocs_catalog`` for the pure
helpers (filter / rank / format / inference) that complement this
module.
"""

from __future__ import annotations

import configparser
import json
import logging
from trackme_libs_logging import get_effective_logger
import os
import re
import threading
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote_plus

import requests
import urllib3

# Disable insecure-request warnings — the loopback to splunkd is over
# self-signed HTTPS by design (we trust the local management interface).
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ---------------------------------------------------------------------------
# Handler imports — one entry per registered REST handler. Conditional
# imports cover handlers that may not be present in every build (the AI
# advisors are gated behind py3.13 + ai-sdk availability).
# ---------------------------------------------------------------------------

# Standard handlers — must always import successfully.
from trackme_rest_handler_alerting_user import (
    TrackMeHandlerAlertingReadOps_v2 as handler_alerting_user,
)
from trackme_rest_handler_alerting_admin import (
    TrackMeHandlerAlertingWriteOps_v2 as handler_alerting_admin,
)
from trackme_rest_handler_ack_user import TrackMeHandlerAckReadOps_v2 as handler_ack_user
from trackme_rest_handler_ack_power import TrackMeHandlerAckWriteOps_v2 as handler_ack_power
from trackme_rest_handler_audit import TrackMeHandlerAudit_v2 as handler_audit
from trackme_rest_handler_backup_and_restore import (
    TrackMeHandlerBackupAndRestore_v2 as handler_backup_and_restore,
)
from trackme_rest_handler_support_diag_power import (
    TrackMeHandlerSupportDiag_v2 as handler_support_diag,
)
from trackme_rest_handler_configuration import (
    TrackMeHandlerConfigurationRead_v2 as handler_configuration,
)
from trackme_rest_handler_configuration_admin import (
    TrackMeHandlerConfigurationAdmin_v2 as handler_configuration_admin,
)
from trackme_rest_handler_maintenance import (
    TrackMeHandlerMaintenance_v2 as handler_maintenance,
)
from trackme_rest_handler_maintenance_kdb_user import (
    TrackMeHandlerMaintenanceKdbRead_v2 as handler_maintenance_kdb_user,
)
from trackme_rest_handler_maintenance_kdb_admin import (
    TrackMeHandlerMaintenanceKdbAdmin_v2 as handler_maintenance_kdb_admin,
)
from trackme_rest_handler_bank_holidays_user import (
    TrackMeHandlerBankHolidaysRead_v2 as handler_bank_holidays_user,
)
from trackme_rest_handler_bank_holidays_admin import (
    TrackMeHandlerBankHolidaysAdmin_v2 as handler_bank_holidays_admin,
)
from trackme_rest_handler_splk_flx_user import (
    TrackMeHandlerSplkFlxTrackingRead_v2 as handler_splk_flx_user,
)
from trackme_rest_handler_splk_flx_power import (
    TrackMeHandlerSplkFlxTrackingWrite_v2 as handler_splk_flx_power,
)
from trackme_rest_handler_splk_flx_admin import (
    TrackMeHandlerSplkFlxTrackingAdmin_v2 as handler_splk_flx_admin,
)
from trackme_rest_handler_splk_fqm_user import (
    TrackMeHandlerSplkFqmTrackingRead_v2 as handler_splk_fqm_user,
)
from trackme_rest_handler_splk_fqm_power import (
    TrackMeHandlerSplkFqmTrackingWrite_v2 as handler_splk_fqm_power,
)
from trackme_rest_handler_splk_fqm_admin import (
    TrackMeHandlerSplkFqmTrackingAdmin_v2 as handler_splk_fqm_admin,
)
from trackme_rest_handler_splk_wlk_user import (
    TrackMeHandlerSplkWlkRead_v2 as handler_splk_wlk_user,
)
from trackme_rest_handler_splk_wlk_power import (
    TrackMeHandlerSplkWlkWrite_v2 as handler_splk_wlk_power,
)
from trackme_rest_handler_splk_wlk_admin import (
    TrackMeHandlerSplkWlkAdmin_v2 as handler_splk_wlk_admin,
)
from trackme_rest_handler_splk_data_sampling_user import (
    TrackMeHandlerSplkDataSamplingRead_v2 as handler_spk_data_sampling_user,
)
from trackme_rest_handler_splk_data_sampling_power import (
    TrackMeHandlerSplkDataSamplingWrite_v2 as handler_spk_data_sampling_power,
)
from trackme_rest_handler_splk_blocklist_user import (
    TrackMeHandlerSplkBlocklistRead_v2 as handler_splk_blocklist_user,
)
from trackme_rest_handler_splk_blocklist_power import (
    TrackMeHandlerSplkBlocklistWrite_v2 as handler_splk_blocklist_power,
)
from trackme_rest_handler_splk_dhm_user import (
    TrackMeHandlerSplkDhmRead_v2 as handler_splk_dhm_user,
)
from trackme_rest_handler_splk_dhm_power import (
    TrackMeHandlerSplkDhmWrite_v2 as handler_splk_dhm_power,
)
from trackme_rest_handler_splk_dsm_user import (
    TrackMeHandlerSplkDsmRead_v2 as handler_splk_dsm_user,
)
from trackme_rest_handler_splk_dsm_power import (
    TrackMeHandlerSplkDsmWrite_v2 as handler_splk_dsm_power,
)
from trackme_rest_handler_splk_disruption_user import (
    TrackMeHandlerSplkDisruptionRead_v2 as handler_splk_disruption_user,
)
from trackme_rest_handler_splk_disruption_power import (
    TrackMeHandlerSplkDisruptionWrite_v2 as handler_splk_disruption_power,
)
from trackme_rest_handler_entity_maintenance_user import (
    TrackMeHandlerEntityMaintenanceRead_v2 as handler_entity_maintenance_user,
)
from trackme_rest_handler_entity_maintenance_power import (
    TrackMeHandlerEntityMaintenanceWrite_v2 as handler_entity_maintenance_power,
)
from trackme_rest_handler_splk_elastic_sources_user import (
    TrackMeHandlerSplkElasticSourcesRead_v2 as handler_splk_elastic_sources_user,
)
from trackme_rest_handler_splk_elastic_sources_admin import (
    TrackMeHandlerSplkElasticSourcesAdmin_v2 as handler_splk_elastic_sources_admin,
)
from trackme_rest_handler_splk_hybrid_trackers_user import (
    TrackMeHandlerSplkHybridTrackerRead_v2 as handler_splk_hybrid_trackers_user,
)
from trackme_rest_handler_splk_hybrid_trackers_admin import (
    TrackMeHandlerSplkHybridTrackerAdmin_v2 as handler_splk_hybrid_trackers_admin,
)
from trackme_rest_handler_splk_replica_trackers_user import (
    TrackMeHandlerSplkReplicaTrackerRead_v2 as handler_splk_replica_trackers_user,
)
from trackme_rest_handler_splk_replica_trackers_admin import (
    TrackMeHandlerSplkReplicaTrackerAdmin_v2 as handler_splk_replica_trackers_admin,
)
from trackme_rest_handler_splk_lagging_classes_user import (
    TrackMeHandlerSplkLaggingClassesRead_v2 as handler_splk_lagging_classes_user,
)
from trackme_rest_handler_splk_lagging_classes_power import (
    TrackMeHandlerSplkLaggingClassesWrite_v2 as handler_splk_lagging_classes_power,
)
from trackme_rest_handler_splk_variable_delay_user import (
    TrackMeHandlerSplkVariableDelayRead_v2 as handler_splk_variable_delay_user,
)
from trackme_rest_handler_splk_variable_delay_power import (
    TrackMeHandlerSplkVariableDelayWrite_v2 as handler_splk_variable_delay_power,
)
from trackme_rest_handler_splk_variable_delay_admin import (
    TrackMeHandlerSplkVariableDelayAdmin_v2 as handler_splk_variable_delay_admin,
)
from trackme_rest_handler_splk_logical_groups_user import (
    TrackMeHandlerSplkLogicalGroupsRead_v2 as handler_splk_logical_groups_user,
)
from trackme_rest_handler_splk_logical_groups_power import (
    TrackMeHandlerSplkLogicalGroupsWrite_v2 as handler_splk_logical_groups_power,
)
from trackme_rest_handler_splk_mhm_user import (
    TrackMeHandlerSplkMhmRead_v2 as handler_splk_mhm_user,
)
from trackme_rest_handler_splk_mhm_power import (
    TrackMeHandlerSplkMhmWrite_v2 as handler_splk_mhm_power,
)
from trackme_rest_handler_splk_outliers_engine_user import (
    TrackMeHandlerSplkOutliersEngineRead_v2 as handler_splk_outliers_engine_user,
)
from trackme_rest_handler_splk_outliers_engine_power import (
    TrackMeHandlerSplkOutliersEngineWrite_v2 as handler_splk_outliers_engine_power,
)
from trackme_rest_handler_splk_tag_policies_user import (
    TrackMeHandlerSplkTagPoliciesRead_v2 as handler_splk_lag_policies_user,
)
from trackme_rest_handler_splk_tag_policies_power import (
    TrackMeHandlerSplkTagPoliciesWrite_v2 as handler_splk_lag_policies_power,
)
from trackme_rest_handler_splk_priority_policies_user import (
    TrackMeHandlerSplkPriorityPoliciesRead_v2 as handler_splk_priority_policies_user,
)
from trackme_rest_handler_splk_priority_policies_power import (
    TrackMeHandlerSplkPriorityPoliciesWrite_v2 as handler_splk_priority_policies_power,
)
from trackme_rest_handler_splk_sla_policies_user import (
    TrackMeHandlerSplkSlaPoliciesRead_v2 as handler_splk_sla_policies_user,
)
from trackme_rest_handler_splk_sla_policies_power import (
    TrackMeHandlerSplkSlaPoliciesWrite_v2 as handler_splk_sla_policies_power,
)
from trackme_rest_handler_vtenants_user import (
    TrackMeHandlerVtenantsRead_v2 as handler_vtenants_user,
)
from trackme_rest_handler_vtenants_power import (
    TrackMeHandlerVtenantsWrite_v2 as handler_vtenants_power,
)
from trackme_rest_handler_vtenants_admin import (
    TrackMeHandlerVtenantsAdmin_v2 as handler_vtenants_admin,
)
from trackme_rest_handler_licensing_admin import (
    TrackMeHandlerLicensingAdmin_v2 as handler_licensing_admin,
)
from trackme_rest_handler_licensing_user import (
    TrackMeHandlerLicensingRead_v2 as handler_licensing_user,
)
from trackme_rest_handler_splk_deleted_entities_user import (
    TrackMeHandlerSplkDeletedEntitiesRead_v2 as handler_splk_deleted_entities_user,
)
from trackme_rest_handler_splk_deleted_entities_power import (
    TrackMeHandlerSplkDeletedEntitiesPower_v2 as handler_splk_deleted_entities_power,
)
from trackme_rest_handler_component_user import (
    TrackMeHandlerComponentRead_v2 as handler_component_user,
)
from trackme_rest_handler_component_power import (
    TrackMeHandlerComponentPower_v2 as handler_component_power,
)
from trackme_rest_handler_notes_user import (
    TrackMeHandlerNotesRead_v2 as handler_notes_user,
)
from trackme_rest_handler_notes_power import (
    TrackMeHandlerNotesWrite_v2 as handler_notes_power,
)
from trackme_rest_handler_describe import (
    TrackMeHandlerDescribe_v2 as handler_describe,
)
from trackme_rest_handler_ai_chat import (
    TrackMeHandlerAiChat_v2 as handler_ai_chat,
)
from trackme_rest_handler_ai_config_admin import (
    TrackMeHandlerAiConfigAdmin_v2 as handler_ai_admin,
)
from trackme_rest_handler_restricted_searches import (
    TrackMeHandlerRestrictedSearches_v2 as handler_restricted_searches,
)
from trackme_rest_handler_virtual_groups_user import (
    TrackMeHandlerVirtualGroupsRead_v2 as handler_virtual_groups_user,
)
from trackme_rest_handler_virtual_groups_admin import (
    TrackMeHandlerVirtualGroupsAdmin_v2 as handler_virtual_groups_admin,
)
from trackme_rest_handler_labels_user import (
    TrackMeHandlerLabelsRead_v2 as handler_labels_user,
)
from trackme_rest_handler_labels_power import (
    TrackMeHandlerLabelsWrite_v2 as handler_labels_power,
)
from trackme_rest_handler_component_admin import (
    TrackMeHandlerComponentAdmin_v2 as handler_component_admin,
)
from trackme_rest_handler_splk_inject_expected_user import (
    TrackMeHandlerSplkInjectExpectedRead_v2 as handler_splk_inject_expected_user,
)
from trackme_rest_handler_splk_inject_expected_admin import (
    TrackMeHandlerSplkInjectExpectedAdmin_v2 as handler_splk_inject_expected_admin,
)


# Conditional handlers — present only when their dependencies are
# available. Identical pattern to the historical search-command code.
try:
    from trackme_rest_handler_splk_soar_user import (
        TrackMeHandlerSplkSoarRead_v2 as handler_splk_soar_user,
    )
    from trackme_rest_handler_splk_soar_admin import (
        TrackMeHandlerSplkSoarAdmin_v2 as handler_splk_soar_admin,
    )
except ImportError:
    handler_splk_soar_user = None
    handler_splk_soar_admin = None
    get_effective_logger().warning(
        "Could not import TrackMeHandlerSplkSoar_v2 handlers. "
        "Some features may not be available."
    )

try:
    from trackme_rest_handler_ai_ml_advisor import (
        TrackMeHandlerAiMlAdvisor_v2 as handler_ai_ml_advisor,
    )
except ImportError:
    handler_ai_ml_advisor = None
    get_effective_logger().warning(
        "Could not import TrackMeHandlerAiMlAdvisor_v2. "
        "AI ML Advisor endpoints will not appear in API docs."
    )

try:
    from trackme_rest_handler_ai_feed_lifecycle import (
        TrackMeHandlerAiFeedLifecycle_v2 as handler_ai_feed_lifecycle,
    )
except ImportError:
    handler_ai_feed_lifecycle = None
    get_effective_logger().warning(
        "Could not import TrackMeHandlerAiFeedLifecycle_v2. "
        "AI Feed Lifecycle endpoints will not appear in API docs."
    )

try:
    from trackme_rest_handler_ai_flx_threshold import (
        TrackMeHandlerAiFlxThreshold_v2 as handler_ai_flx_threshold,
    )
except ImportError:
    handler_ai_flx_threshold = None
    get_effective_logger().warning(
        "Could not import TrackMeHandlerAiFlxThreshold_v2. "
        "AI FLX Threshold endpoints will not appear in API docs."
    )

try:
    from trackme_rest_handler_ai_component_health import (
        TrackMeHandlerAiComponentHealth_v2 as handler_ai_component_health,
    )
except ImportError:
    handler_ai_component_health = None

try:
    from trackme_rest_handler_ai_fqm_advisor import (
        TrackMeHandlerAiFqmAdvisor_v2 as handler_ai_fqm_advisor,
    )
except ImportError:
    handler_ai_fqm_advisor = None
    get_effective_logger().warning(
        "Could not import TrackMeHandlerAiFqmAdvisor_v2. "
        "AI FQM Advisor endpoints will not appear in API docs."
    )

try:
    from trackme_rest_handler_ai_concierge_advisor import (
        TrackMeHandlerAiConciergeAdvisor_v2 as handler_ai_concierge_advisor,
    )
except ImportError:
    handler_ai_concierge_advisor = None
    get_effective_logger().warning(
        "Could not import TrackMeHandlerAiConciergeAdvisor_v2. "
        "AI Concierge Advisor endpoints will not appear in API docs."
    )


# ---------------------------------------------------------------------------
# Catalog — the canonical handler-to-resource-group map.
# ---------------------------------------------------------------------------

def _build_handlers_api_catalog() -> Dict[Any, Dict[str, str]]:
    """Construct the handler → metadata catalog dict.

    Lifted verbatim from the original search-command implementation so
    behaviour is preserved exactly. Conditional handlers are only added
    when their import succeeded.

    Returns:
        Dict mapping handler class → ``{"resource_group": "..."}``.
    """
    catalog: Dict[Any, Dict[str, str]] = {
        handler_alerting_user: {"resource_group": "alerting"},
        handler_alerting_admin: {"resource_group": "alerting/admin"},
        handler_ack_user: {"resource_group": "ack"},
        handler_ack_power: {"resource_group": "ack/write"},
        handler_audit: {"resource_group": "audit"},
        handler_backup_and_restore: {"resource_group": "backup_and_restore"},
        handler_support_diag: {"resource_group": "support_diag"},
        handler_configuration: {"resource_group": "configuration"},
        handler_configuration_admin: {"resource_group": "configuration/admin"},
        handler_maintenance: {"resource_group": "maintenance"},
        handler_maintenance_kdb_user: {"resource_group": "maintenance_kdb"},
        handler_maintenance_kdb_admin: {"resource_group": "maintenance_kdb/admin"},
        handler_bank_holidays_user: {"resource_group": "bank_holidays"},
        handler_bank_holidays_admin: {"resource_group": "bank_holidays/admin"},
        handler_splk_flx_user: {"resource_group": "splk_flx"},
        handler_splk_flx_power: {"resource_group": "splk_flx/write"},
        handler_splk_flx_admin: {"resource_group": "splk_flx/admin"},
        handler_splk_fqm_user: {"resource_group": "splk_fqm"},
        handler_splk_fqm_power: {"resource_group": "splk_fqm/write"},
        handler_splk_fqm_admin: {"resource_group": "splk_fqm/admin"},
        handler_spk_data_sampling_user: {"resource_group": "splk_data_sampling"},
        handler_spk_data_sampling_power: {"resource_group": "splk_data_sampling/write"},
        handler_splk_blocklist_user: {"resource_group": "splk_blocklist"},
        handler_splk_blocklist_power: {"resource_group": "splk_blocklist/write"},
        handler_splk_dhm_user: {"resource_group": "splk_dhm"},
        handler_splk_dhm_power: {"resource_group": "splk_dhm/write"},
        handler_splk_dsm_user: {"resource_group": "splk_dsm"},
        handler_splk_dsm_power: {"resource_group": "splk_dsm/write"},
        handler_splk_wlk_user: {"resource_group": "splk_wlk"},
        handler_splk_wlk_power: {"resource_group": "splk_wlk/write"},
        handler_splk_wlk_admin: {"resource_group": "splk_wlk/admin"},
        handler_splk_disruption_user: {"resource_group": "splk_disruption"},
        handler_splk_disruption_power: {"resource_group": "splk_disruption/write"},
        handler_entity_maintenance_user: {"resource_group": "entity_maintenance"},
        handler_entity_maintenance_power: {
            "resource_group": "entity_maintenance/write"
        },
        handler_splk_elastic_sources_user: {"resource_group": "splk_elastic_sources"},
        handler_splk_elastic_sources_admin: {"resource_group": "splk_elastic_sources/admin"},
        handler_splk_hybrid_trackers_user: {"resource_group": "splk_hybrid_trackers"},
        handler_splk_hybrid_trackers_admin: {"resource_group": "splk_hybrid_trackers/admin"},
        handler_splk_replica_trackers_user: {"resource_group": "splk_replica_trackers"},
        handler_splk_replica_trackers_admin: {"resource_group": "splk_replica_trackers/admin"},
        handler_splk_lagging_classes_user: {"resource_group": "splk_lagging_classes"},
        handler_splk_lagging_classes_power: {"resource_group": "splk_lagging_classes/write"},
        handler_splk_variable_delay_user: {"resource_group": "splk_variable_delay"},
        handler_splk_variable_delay_power: {"resource_group": "splk_variable_delay/write"},
        handler_splk_variable_delay_admin: {"resource_group": "splk_variable_delay/admin"},
        handler_splk_logical_groups_user: {"resource_group": "splk_logical_groups"},
        handler_splk_logical_groups_power: {"resource_group": "splk_logical_groups/write"},
        handler_splk_mhm_user: {"resource_group": "splk_mhm"},
        handler_splk_mhm_power: {"resource_group": "splk_mhm/write"},
        handler_splk_outliers_engine_user: {"resource_group": "splk_outliers_engine"},
        handler_splk_outliers_engine_power: {"resource_group": "splk_outliers_engine/write"},
        handler_splk_lag_policies_user: {"resource_group": "splk_tag_policies"},
        handler_splk_lag_policies_power: {"resource_group": "splk_tag_policies/write"},
        handler_splk_priority_policies_user: {"resource_group": "splk_priority_policies"},
        handler_splk_priority_policies_power: {"resource_group": "splk_priority_policies/write"},
        handler_splk_sla_policies_user: {"resource_group": "splk_sla_policies"},
        handler_splk_sla_policies_power: {"resource_group": "splk_sla_policies/write"},
        handler_vtenants_user: {"resource_group": "vtenants"},
        handler_vtenants_power: {"resource_group": "vtenants/write"},
        handler_vtenants_admin: {"resource_group": "vtenants/admin"},
        handler_licensing_admin: {"resource_group": "licensing/admin"},
        handler_licensing_user: {"resource_group": "licensing"},
        handler_splk_deleted_entities_user: {"resource_group": "splk_deleted_entities"},
        handler_splk_deleted_entities_power: {"resource_group": "splk_deleted_entities/write"},
        handler_component_user: {"resource_group": "component"},
        handler_component_power: {"resource_group": "component/write"},
        handler_notes_user: {"resource_group": "notes"},
        handler_notes_power: {"resource_group": "notes/write"},
        handler_describe: {"resource_group": "describe"},
        handler_ai_chat: {"resource_group": "ai"},
        handler_ai_admin: {"resource_group": "ai/admin"},
        handler_restricted_searches: {"resource_group": "restricted_searches"},
        handler_virtual_groups_user: {"resource_group": "virtual_groups"},
        handler_virtual_groups_admin: {"resource_group": "virtual_groups/admin"},
        handler_labels_user: {"resource_group": "labels"},
        handler_labels_power: {"resource_group": "labels/write"},
        handler_component_admin: {"resource_group": "component/admin"},
        handler_splk_inject_expected_user: {"resource_group": "splk_inject_expected"},
        handler_splk_inject_expected_admin: {"resource_group": "splk_inject_expected/admin"},
    }

    # Conditional handlers — only added when their import succeeded.
    if handler_splk_soar_user is not None:
        catalog[handler_splk_soar_user] = {"resource_group": "splk_soar"}
    if handler_splk_soar_admin is not None:
        catalog[handler_splk_soar_admin] = {"resource_group": "splk_soar/admin"}
    if handler_ai_ml_advisor is not None:
        catalog[handler_ai_ml_advisor] = {"resource_group": "ai_ml_advisor"}
    if handler_ai_feed_lifecycle is not None:
        catalog[handler_ai_feed_lifecycle] = {"resource_group": "ai_feed_lifecycle"}
    if handler_ai_flx_threshold is not None:
        catalog[handler_ai_flx_threshold] = {"resource_group": "ai_flx_threshold"}
    if handler_ai_component_health is not None:
        catalog[handler_ai_component_health] = {"resource_group": "ai_component_health"}
    if handler_ai_fqm_advisor is not None:
        catalog[handler_ai_fqm_advisor] = {"resource_group": "ai_fqm_advisor"}
    if handler_ai_concierge_advisor is not None:
        catalog[handler_ai_concierge_advisor] = {"resource_group": "ai_concierge_advisor"}

    return catalog


# Module-level constant — built once at import time. Stable across all
# callers within the same Python process; both the search command and
# the REST endpoint consume this single instance.
HANDLERS_API_CATALOG: Dict[Any, Dict[str, str]] = _build_handlers_api_catalog()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Methods that should never appear in the catalog — these are framework
# helpers, not user-facing endpoints.
_EXCLUDED_FUNCTIONS = frozenset({
    "get_forms_args_as_dict",
    "get_function_signature",
})


def _get_handler_functions(handler: Any, target: str) -> List[str]:
    """List the handler's user-facing methods for the given target.

    Args:
        handler: REST handler class.
        target: ``"groups"`` (return only ``get_resource_group_desc_*``
            methods, used for the resource-group description rows) or
            ``"endpoints"`` (return all ``post_*`` / ``get_*`` /
            ``delete_*`` methods EXCEPT ``get_resource_group_desc_*``).

    Returns:
        Ordered list of method names. Order follows ``dir()`` —
        alphabetical, which gives stable output across runs.
    """
    handler_functions: List[str] = []
    for item in dir(handler):
        if not (
            item.startswith("post_")
            or item.startswith("get_")
            or item.startswith("delete_")
        ):
            continue
        if item in _EXCLUDED_FUNCTIONS:
            continue
        if target == "groups":
            if item.startswith("get_resource_group_desc"):
                handler_functions.append(item)
        elif target == "endpoints":
            if not item.startswith("get_resource_group_desc"):
                handler_functions.append(item)
    return handler_functions


def spl_to_curl(spl_example: Optional[str]) -> Optional[str]:
    """Convert a TrackMe SPL command example to an equivalent ``curl`` example.

    Best-effort — falls back to ``"Not available"`` (passthrough) when
    the SPL string is missing or in an unrecognised shape. The output is
    purely illustrative; users are expected to substitute their own
    Splunk endpoint, credentials, and body fields. The ``mysplunk:8089``
    placeholder is intentional.

    Lifted verbatim from the historical search-command implementation
    (``trackmeapiautodocs.TrackMeApiAutoDocs.spl_to_curl``); preserves
    behaviour exactly so SPL output rows remain identical.
    """
    if spl_example == "Not available" or not spl_example:
        return spl_example

    url: Optional[str] = None
    mode: str = "GET"
    body: Optional[str] = None

    parts = spl_example.split()
    in_body = False
    in_params = False
    body_parts: List[str] = []
    params_parts: List[str] = []

    for part in parts:
        if "url=" in part:
            url = part.split("url=")[1].strip('"')
        elif "mode=" in part:
            mode = part.split("mode=")[1].strip('"')
        elif "body=" in part:
            in_body = True
            body_parts.append(part.split("body=", 1)[1])
        elif "params=" in part:
            in_params = True
            params_parts.append(part.split("params=", 1)[1])
        elif in_body:
            body_parts.append(part)
        elif in_params:
            params_parts.append(part)

    if body_parts:
        body_str = " ".join(body_parts).strip('"')
        body = body_str.replace("'", '"').replace('"', '\\"')

    encoded_params = ""
    if params_parts:
        params_str = " ".join(params_parts).strip('"')
        try:
            params_dict = json.loads(params_str.replace("'", '"'))
        except json.JSONDecodeError:
            params_dict = {}
        encoded_params = "&".join(
            f"{key}={quote_plus(str(value))}" for key, value in params_dict.items()
        )

    curl_example = f"curl -u username https://mysplunk:8089{url}"
    if mode.upper() != "GET":
        curl_example += f' -X "{mode.upper()}"'
    if body:
        curl_example += f' -d "{body}"'
    if params_parts and mode.upper() == "GET":
        curl_example += f"?{encoded_params}"
    return curl_example


def _describe_endpoint_via_loopback(
    splunkd_uri: str,
    session_key: str,
    function_name: str,
    resource_group: str,
    target: str,
    timeout: int = 600,
) -> Dict[str, Any]:
    """Call one handler method with ``describe=true`` over splunkd loopback.

    The handler methods expose their self-documentation through the
    ``describe=true`` query flag — calling them programmatically
    requires the same HTTP path the SPL search command takes. We loop
    back over splunkd's management interface (HTTPS, self-signed cert
    is fine for local loopback).

    Args:
        splunkd_uri: Splunkd management URI (e.g. ``https://localhost:8089``).
        session_key: Session token for the calling user.
        function_name: Method name on the handler (e.g.
            ``"post_get_ack_for_object"``).
        resource_group: Resource group label from ``HANDLERS_API_CATALOG``
            (e.g. ``"ack"``).
        target: ``"groups"`` (extract only the group description) or
            ``"endpoints"`` (full per-endpoint describe block).
        timeout: HTTP timeout in seconds.

    Returns:
        Dict with the same keys the historical search command produced,
        ready to embed in the SPL output or the REST endpoint JSON
        response. Raises on transport / HTTP errors so the caller can
        decide whether to surface the failure or skip the row.
    """
    headers = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/json",
    }

    # Extract the HTTP method from the function name prefix.
    match = re.search(r"^(?:(post|get|delete))_(.*)", function_name)
    if not match:
        raise Exception(
            f"failed to extract the HTTP mode for function='{function_name}' "
            f"in resource_group='{resource_group}'"
        )

    resource_mode = match.group(1)
    resource_target = match.group(2)
    resource_api = f"services/trackme/v2/{resource_group}/{resource_target}"
    target_url = f"{splunkd_uri}/{resource_api}"
    request_data = {"describe": "true"}

    method_map = {
        "get": requests.get,
        "post": requests.post,
        "delete": requests.delete,
    }
    response = method_map[resource_mode](
        target_url,
        headers=headers,
        data=json.dumps(request_data, indent=0),
        verify=False,
        timeout=timeout,
    )

    # Parse the response, decorating any JSON failure with the actual
    # HTTP status + body preview. Without this, the caller's catch-all
    # (``except Exception`` in ``build_catalog``) only sees
    # ``"Expecting value: line 1 column 1 (char 0)"`` — which doesn't
    # tell you whether splunkd returned an empty body, an HTML error
    # page, a 404 (probable missing restmap.conf entry), a 401, etc.
    # Operators have to enable debug logging on splunkd to figure it
    # out. Surfacing the status + body preview at error time turns a
    # 30-minute investigation into a glance at the log line.
    try:
        response_json = json.loads(response.text)
    except (json.JSONDecodeError, ValueError) as exc:
        body_preview = (response.text or "")[:500].replace("\n", "\\n")
        # 404 in particular almost always means the restmap.conf entry
        # for this handler is missing — splunkd has nothing to dispatch
        # to. Call that out explicitly so the next person doesn't have
        # to re-derive it (this is exactly the failure mode that hit
        # ``ai_concierge_advisor`` between PR #1314 — handler added —
        # and PR #1334 — restmap entry added).
        hint = ""
        if response.status_code == 404:
            hint = (
                " — HTTP 404 most likely means there is no "
                "restmap.conf entry whose ``match`` covers this URL "
                "prefix; splunkd has no handler to dispatch to. Check "
                "``package/default/restmap.conf`` for a ``[script:...]`` "
                f"section with ``match = /trackme/v2/{resource_group}``."
            )
        elif response.status_code == 401 or response.status_code == 403:
            hint = (
                f" — HTTP {response.status_code} most likely means the "
                "calling user lacks the capability declared in the "
                "handler's restmap entry "
                "(``capability``/``capability.<method>``)."
            )
        elif not response.text:
            hint = (
                f" — empty response body with status "
                f"{response.status_code}. If this is a fresh restmap "
                "entry, splunkd may not have reloaded; restart splunkd "
                "or hit ``$SPLUNK_HOME/bin/splunk _internal call "
                "/services/admin/conf-restmap/_reload``."
            )
        raise RuntimeError(
            f"non-JSON response from splunkd loopback "
            f"(method={resource_mode!r}, url={target_url!r}, "
            f"status={response.status_code}, "
            f"body_preview={body_preview!r}, original_error={exc!s})"
            + hint
        ) from exc

    if target == "groups":
        # ``resource_group`` is the value from ``HANDLERS_API_CATALOG`` —
        # NOT ``response_json.get("resource_group_name")``. The historical
        # search command's outer ``yield`` deliberately overrode the API-
        # reported name with the catalog-dict value: the catalog is the
        # canonical source of truth (it's what the REST API Reference
        # page filters / groups by), and a handler whose
        # ``get_resource_group_desc_*`` method returns a slightly
        # different label (or returns nothing) shouldn't drift the
        # catalog rows. Bugbot caught this regression on commit
        # 7a759132 — my first refactor pass forwarded the API name,
        # which would silently produce ``None`` rows when a handler's
        # describe block omitted ``resource_group_name``.
        return {
            "resource_group": resource_group,
            "resource_desc": response_json.get("resource_group_desc"),
            "python_function": function_name,
        }

    # target == "endpoints"
    resource_desc = response_json.get("resource_desc")
    resource_spl_example = response_json.get("resource_spl_example")
    resource_curl_example = (
        spl_to_curl(resource_spl_example) if resource_spl_example else None
    )

    return {
        "resource_group": resource_group,
        "resource_desc": resource_desc,
        "resource_api": resource_api,
        "resource_describe": response_json,
        "resource_mode": resource_mode,
        "resource_spl_example": resource_spl_example,
        "resource_curl_example": resource_curl_example,
        "python_function": function_name,
    }


def _strip_redundant_keys(resource_describe: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Drop fields already surfaced at the top level of the response.

    Mirrors the historical search-command logic: the per-endpoint
    ``resource_describe`` block carries ``resource_spl_example`` /
    ``resource_curl_example`` / ``resource_desc`` that are also lifted
    to top-level keys. The duplicates would inflate the output for no
    semantic gain.

    Note: the function MUTATES the input in place AND returns it. The
    historical code did the same — kept for behavioural parity. Callers
    pass a freshly-built dict per row so in-place mutation is safe.
    """
    if not resource_describe:
        return resource_describe
    for key in ("resource_spl_example", "resource_curl_example", "resource_desc"):
        resource_describe.pop(key, None)
    return resource_describe


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_catalog(
    splunkd_uri: str,
    session_key: str,
    target: str = "endpoints",
) -> Iterable[Dict[str, Any]]:
    """Yield catalog entries for every registered handler / function.

    Walks ``HANDLERS_API_CATALOG`` and, for each handler, every method
    that matches the ``target`` filter. Each method is exercised via
    HTTPS loopback against splunkd with ``describe=true`` to extract its
    self-documentation block.

    Failures on individual entries are surfaced as ``{"error": "..."}``
    rows rather than aborting the build — partial catalogs are more
    useful than no catalog when one handler misbehaves.

    Args:
        splunkd_uri: Splunkd management URI from the search-command
            metadata or the REST handler request_info.
        session_key: Session token of the calling user. The loopback
            uses this token, so RBAC is enforced on the way back in —
            users only see endpoints their roles can actually call.
        target: ``"groups"`` for resource-group rows;
            ``"endpoints"`` for full per-endpoint detail.

    Yields:
        One dict per row, in the same shape the historical search
        command produced. Dashboards / consumers reading the SPL output
        keep working unchanged.
    """
    start = time.time()
    yielded = 0
    failed = 0

    for handler_api, meta in HANDLERS_API_CATALOG.items():
        resource_group = meta.get("resource_group", "")

        for function_name in _get_handler_functions(handler_api, target):
            try:
                response = _describe_endpoint_via_loopback(
                    splunkd_uri,
                    session_key,
                    function_name,
                    resource_group,
                    target,
                )
            except Exception as exc:
                get_effective_logger().error(
                    f"failed to generate API doc result for "
                    f"function={function_name!r} in "
                    f"resource_group={resource_group!r}: {exc}"
                )
                failed += 1
                # Yield a diagnostic error row but DO NOT include
                # ``resource_group``. The legacy SPL consumer flow
                # filtered drill-in results with
                # ``search resource_group="<group>"`` which excluded
                # error rows naturally (they had no
                # ``resource_group`` field). The REST/JS consumer flow
                # introduced in May 2026 (PR #1464) filters in-memory
                # with ``e.resource_group === groupName``; if the
                # error row carried ``resource_group`` it would pass
                # that filter, reach the modal, and crash on
                # ``endpoint.resource_mode.toUpperCase()`` because
                # error rows lack ``resource_mode`` / ``resource_api``
                # / etc. Bugbot caught this regression on PR #1472
                # (Medium severity). Keeping ``resource_group`` off
                # the error row preserves the legacy contract for
                # both consumer flows. The frontend also filters
                # malformed rows defensively (belt & braces).
                yield {
                    "error": (
                        f"failed to generate API doc result for "
                        f"function={function_name!r} with exception={exc}"
                    ),
                    "python_function": function_name,
                }
                continue

            if target == "endpoints":
                # Matches the historical SPL output: drop duplicate
                # keys from the embedded ``resource_describe`` block.
                response["resource_describe"] = _strip_redundant_keys(
                    response.get("resource_describe")
                )

            yielded += 1
            yield response

    run_time = round(time.time() - start, 3)
    get_effective_logger().info(
        f"build_catalog done: target={target!r} yielded={yielded} "
        f"failed={failed} run_time={run_time}s"
    )


def build_catalog_as_list(
    splunkd_uri: str,
    session_key: str,
    target: str = "endpoints",
) -> List[Dict[str, Any]]:
    """Materialise ``build_catalog`` to a list (for REST endpoint use).

    The REST endpoint returns the whole catalog as one JSON response,
    so the generator's lazy-yield value goes unused there. This helper
    is sugar for ``list(build_catalog(...))`` with a clear intent.
    """
    return list(build_catalog(splunkd_uri, session_key, target))


# ---------------------------------------------------------------------------
# Filesystem cache (keyed by app version)
# ---------------------------------------------------------------------------
#
# The catalog content only changes when the TrackMe app is upgraded
# (new endpoints registered, describe blocks edited, RBAC tags
# adjusted). The build itself takes ~19s on a typical deployment
# because it does ~400 splunkd HTTPS loopbacks back-to-back. Rebuilding
# on every catalog read is wasteful — the result is identical until
# the next app deploy.
#
# This cache stores the materialised catalog list as a JSON file on
# disk, keyed by ``(target, app_version)``. Cache hit = sub-second.
# Cache miss (first call after a deploy, or first call ever) =
# build + write, then return. The on-disk file is rewritten atomically
# (write tmp, ``os.replace``) so concurrent readers either see the old
# or new file fully — never a partial JSON document.
#
# RBAC trade-off: ``build_catalog`` filters per the calling user's
# session token (splunkd-side RBAC on the loopback). The cache is
# shared across users, so the FIRST cache-builder's RBAC view is what
# every subsequent reader sees until the next deploy. This is
# acceptable in practice because:
#
#   1. The catalog is a documentation surface, not a permission
#      boundary. Splunkd RBAC enforces actual endpoint access at call
#      time — seeing an endpoint in the catalog confers no capability.
#   2. The Concierge agent (the primary consumer) runs as the user but
#      only proposes actions; the user clicks Confirm, which fires the
#      REST call through their own credentials and is RBAC-checked
#      there. Catalog visibility never bypasses authorization.
#   3. The first cache-builder is typically an admin (catalog requests
#      tend to come from agent runs initiated by admin users); their
#      view is the maximal one.
#
# If a more conservative model is needed later, the cache key can be
# extended with a hash of the calling user's effective roles (one
# cache file per role-set instead of per-version). Today's choice is
# the simplest one that solves the 19s-rebuild problem.
_CACHE_SUBDIR = "var/run/trackme"
_CACHE_FILENAME_FMT = "api_catalog_{target}_v{version}.json"


def _read_app_version() -> Optional[str]:
    """Read the app's version string from the deployed app.

    Sources, in priority order:
      1. ``$SPLUNK_HOME/etc/apps/trackme/local/app.conf`` (operator override)
      2. ``$SPLUNK_HOME/etc/apps/trackme/default/app.conf`` (shipped value)
      3. ``<this_file>/../../version.json`` (development tree only)

    Mirrors the ``trackme_get_version`` helper in ``trackme_libs.py``:
    the build pipeline injects the version into ``[id] version`` of
    ``app.conf``; ``version.json`` lives at the repo root and is NOT
    shipped inside the ``.tgz`` (only ``package/`` is packaged), so the
    deployed app does not have a ``version.json`` to read. Reading the
    repo-root ``version.json`` only works in the development tree.

    Returns the ``version`` value as a string, or ``None`` if no
    candidate is readable / parseable. Caller must treat ``None`` as
    "no caching available" — never assume a default version (a stale
    cache survives across upgrades and is far worse than a rebuild).
    """
    splunk_home = os.environ.get("SPLUNK_HOME", "")

    # 1) + 2) — read app.conf in the deployed app. ``local/`` wins over
    # ``default/`` per Splunk's standard layered conf precedence (the
    # operator may have overridden version locally; respect that).
    if splunk_home:
        for sub in ("local", "default"):
            app_conf_path = os.path.join(
                splunk_home, "etc", "apps", "trackme", sub, "app.conf"
            )
            if not os.path.isfile(app_conf_path):
                continue
            try:
                config = configparser.ConfigParser()
                # Preserve case sensitivity for option names — Splunk
                # conf keys are case-sensitive in some sections (mirror
                # the ``trackme_libs.trackme_get_version`` helper).
                config.optionxform = str
                config.read(app_conf_path)
                # Prefer ``[id] version`` (the canonical app-version
                # location); fall back to ``[launcher] version`` which
                # the ucc-gen pipeline also populates.
                for section in ("id", "launcher"):
                    if config.has_section(section) and config.has_option(
                        section, "version"
                    ):
                        version = config.get(section, "version").strip()
                        if version:
                            return version
            except (IOError, OSError, configparser.Error, ValueError) as exc:
                get_effective_logger().debug(
                    f"_read_app_version: failed to parse {app_conf_path}: {exc}"
                )
                continue

    # 3) — repo-root version.json (development tree fallback)
    dev_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "version.json")
    )
    try:
        with open(dev_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        version = data.get("version")
        if isinstance(version, str) and version:
            return version
    except (IOError, OSError, ValueError, json.JSONDecodeError):
        pass

    return None


def _cache_dir() -> str:
    """Directory holding the catalog cache files."""
    return os.path.join(
        os.environ.get("SPLUNK_HOME", "/tmp"),
        _CACHE_SUBDIR,
    )


def _cache_path(target: str, version: str) -> str:
    """Cache file path for one ``(target, version)`` pair."""
    safe_target = re.sub(r"[^a-z0-9_]", "_", target.lower())
    safe_version = re.sub(r"[^a-zA-Z0-9._-]", "_", version)
    return os.path.join(
        _cache_dir(),
        _CACHE_FILENAME_FMT.format(target=safe_target, version=safe_version),
    )


def _read_cache(path: str) -> Optional[List[Dict[str, Any]]]:
    """Load a cached catalog list. ``None`` on any failure."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            return data
        # Wrong shape — log and ignore. A future schema change writing
        # a dict instead of a list shouldn't poison every reader.
        get_effective_logger().warning(
            f"catalog cache at {path!r} has unexpected shape "
            f"{type(data).__name__}, ignoring"
        )
    except FileNotFoundError:
        # Cold cache — normal on first call after deploy.
        pass
    except (IOError, OSError, ValueError, json.JSONDecodeError) as exc:
        get_effective_logger().warning(f"catalog cache at {path!r} unreadable: {exc}")
    return None


def _write_cache(path: str, catalog: List[Dict[str, Any]]) -> None:
    """Write the catalog atomically (tmp + ``os.replace``).

    Best-effort — failures are logged but not raised. A failed write
    means the next call rebuilds, which is annoying but not broken.
    """
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except (IOError, OSError) as exc:
        get_effective_logger().warning(f"failed to create catalog cache dir: {exc}")
        return

    # tmp suffix combines PID + thread-ident so two concurrent cache
    # misses inside the same Splunk process don't race on the same
    # tmp file (multiple worker threads share PID; without
    # ``threading.get_ident()`` thread A could truncate thread B's
    # partial write and ``os.replace`` would then swap a half-written
    # JSON file as the cache, served to all subsequent readers until
    # the next deploy). Bugbot caught this on PR #1329 cycle 2 (Low
    # severity).
    tmp_path = f"{path}.tmp.{os.getpid()}.{threading.get_ident()}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(catalog, fh)
        # ``os.replace`` is atomic on POSIX and Windows for same-FS
        # rename. Concurrent readers either see the old file or the
        # new one — never a half-written one.
        os.replace(tmp_path, path)
    except (IOError, OSError, TypeError) as exc:
        get_effective_logger().warning(f"failed to write catalog cache at {path!r}: {exc}")
        # Clean up tmp file if it leaked.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def build_catalog_as_list_cached(
    splunkd_uri: str,
    session_key: str,
    target: str = "endpoints",
    *,
    force_rebuild: bool = False,
) -> List[Dict[str, Any]]:
    """Cached version of ``build_catalog_as_list`` keyed by app version.

    First call after an app deploy: builds the catalog (~19s) and
    writes it to disk. Subsequent calls (until the next app deploy):
    read from disk (sub-second).

    Args:
        splunkd_uri / session_key / target: same as
            ``build_catalog_as_list``.
        force_rebuild: bypass the cache and rebuild even if a hit
            exists. The fresh catalog overwrites the cache. Useful for
            REST handlers that want to expose a "rebuild now" knob.

    Returns:
        List of catalog row dicts, identical shape to
        ``build_catalog_as_list``. On any cache infrastructure failure
        (unreadable ``version.json``, write-protected cache dir,
        corrupted cache file) the function falls back to a live build
        — caching is an optimisation, not a correctness requirement.
    """
    version = _read_app_version()
    if not version:
        get_effective_logger().warning(
            "catalog cache disabled: could not read app version from "
            "version.json. Falling back to live build (no caching this run)."
        )
        return build_catalog_as_list(splunkd_uri, session_key, target)

    cache_path = _cache_path(target, version)

    if not force_rebuild:
        cached = _read_cache(cache_path)
        if cached is not None:
            get_effective_logger().info(
                f"catalog cache HIT: target={target!r}, version={version!r}, "
                f"path={cache_path!r}, entries={len(cached)}"
            )
            return cached

    # Cold cache, force rebuild, or unreadable cache file.
    t0 = time.time()
    catalog = build_catalog_as_list(splunkd_uri, session_key, target)
    build_time = round(time.time() - t0, 3)
    get_effective_logger().info(
        f"catalog cache MISS: built {len(catalog)} entries in "
        f"{build_time}s, target={target!r}, version={version!r}; writing "
        f"cache to {cache_path!r}"
    )
    _write_cache(cache_path, catalog)
    return catalog


def warmup_api_catalog_cache(
    splunkd_uri: str,
    session_key: str,
    target: str = "endpoints",
) -> Tuple[bool, str]:
    """Opportunistically warm the API catalog filesystem cache.

    Wraps ``build_catalog_as_list_cached`` in a never-raising envelope
    so callers (typically scheduled trackers, schema migrations, or
    similar background tasks) can pay the catalog rebuild cost
    proactively without coupling their own correctness to a successful
    catalog build. The chat / agent path that consumes the catalog is
    fully fail-soft on its own (it falls back to "no grounding,
    training-data guesses" when the catalog is unavailable), so
    a warmup failure here is never load-bearing for product
    behaviour — it only affects the latency of the first chat call
    after an upgrade.

    Behaviour:

      - Cold cache (e.g. immediately after an app upgrade —
        ``api_catalog_endpoints_v<version>.json`` does not yet exist
        for the new version): builds the catalog (~19s on a typical
        SH) and writes it to disk. The next chat / agent call hits
        the cache.
      - Warm cache (the cache file already exists for the current
        version): sub-second filesystem read. Calling repeatedly is
        cheap and safe.

    Both paths are exercised by ``build_catalog_as_list_cached`` —
    this wrapper only handles the exception envelope and the
    success/failure return contract. The underlying helper already
    logs INFO ``catalog cache HIT`` or ``catalog cache MISS`` at
    write time, so callers don't need to log entries / build_time
    themselves.

    Args:
        splunkd_uri: Local management URI (e.g. ``https://127.0.0.1:8089``).
            Same shape as ``build_catalog_as_list_cached``.
        session_key: Splunk session token for the loopback HTTPS calls.
        target: ``"endpoints"`` (default) for the per-endpoint catalog,
            or ``"groups"`` for the resource-groups projection. Both
            targets have known consumers: ``"endpoints"`` is read by
            the Concierge describe payload AND the REST API
            Reference UI; ``"groups"`` is read by the REST API
            Reference UI for the group-level descriptions on the
            landing page. To warm both in one call, prefer
            ``warmup_api_catalog_cache_all_targets`` below — calling
            this helper with only the default target leaves the
            ``"groups"`` cache cold and the first UI user still
            pays the rebuild cost for that target.

    Returns:
        ``(success, message)`` tuple where ``success`` is ``True`` on
        a cache hit or successful rebuild and ``False`` on any
        exception during build / write. ``message`` is a short
        human-readable status string the caller can include in its
        own log line for traceability. The helper NEVER raises — a
        failure here must not break the caller's primary task.

    Bug history:

      Added in May 2026 to support pro-active warmup from the
      per-tenant schema migration in ``trackmetrackerhealth.py``.
      Previously the catalog was built lazily on the first chat /
      agent call after an app upgrade — that user paid the ~19s
      wait interactively and typically read it as "the AI Assistant
      is broken / very slow". The schema migration window is the
      natural moment to pay the rebuild: the upgrade is already
      doing heavyweight work (KV shape changes, savedsearch
      refresh, lookup maintenance), an extra ~19s on the first
      tenant of the upgrade is invisible inside that window, and
      every other tenant migrating in the same window hits the
      cache. See PR adding this helper for the wiring details.
    """
    try:
        t0 = time.time()
        catalog = build_catalog_as_list_cached(
            splunkd_uri=splunkd_uri,
            session_key=session_key,
            target=target,
        )
        elapsed = round(time.time() - t0, 3)
        return (
            True,
            f"warmup ok, target={target!r}, entries={len(catalog)}, "
            f"elapsed_s={elapsed}",
        )
    except Exception as e:
        # Catch-all is intentional. The caller MUST be able to keep
        # going regardless of why the warmup failed (network glitch,
        # disk full, REST endpoint not yet ready on a freshly-restarted
        # SH, missing app version metadata, etc.). The chat / agent
        # path will rebuild lazily on its own first call if the cache
        # is still cold by then.
        return (
            False,
            f"warmup_failed, target={target!r}, "
            f"exception={type(e).__name__}: {e}",
        )


# Targets the schema-migration warmup path should pre-populate. Both
# have known consumers in production:
#
#   - ``"endpoints"`` — read by the Concierge describe payload (chat
#     LLM grounding), the ``/configuration/api_catalog`` REST endpoint
#     (with default target), and the REST API Reference UI's per-
#     endpoint drill-in modal. Largest of the two by far (~423 entries
#     × ~1-2KB).
#   - ``"groups"`` — read by the REST API Reference UI's landing
#     page for the group-level descriptions, and by the
#     ``/configuration/api_catalog`` REST endpoint when callers
#     pass ``target="groups"``. Cheap (~30 entries) but has its own
#     cache file because the projection shape is different.
#
# Bug history (low-severity bugbot finding on PR #1469): the original
# warmup hook only called ``warmup_api_catalog_cache`` with the
# default ``target="endpoints"``, leaving the ``"groups"`` cache
# cold. The first user opening the REST API Reference UI after an
# upgrade still paid the groups rebuild cost interactively — the
# whole point of the warmup was to avoid exactly this on the
# user-visible path. Adding ``"groups"`` to the warmed set closes
# the gap.
_WARMUP_TARGETS: Tuple[str, ...] = ("endpoints", "groups")


def warmup_api_catalog_cache_all_targets(
    splunkd_uri: str,
    session_key: str,
) -> List[Tuple[str, bool, str]]:
    """Warm every catalog cache target the application knows about.

    Iterates ``_WARMUP_TARGETS`` and calls
    ``warmup_api_catalog_cache`` once per entry. Returns a list of
    ``(target, success, message)`` tuples, one per target, in the
    same order. The helper NEVER raises — failure of one target's
    warmup is reported in its own tuple and does not short-circuit
    the loop, so a transient failure on (say) ``endpoints`` doesn't
    prevent ``groups`` from being warmed (or vice-versa).

    Caller pattern:

        for target, ok, msg in warmup_api_catalog_cache_all_targets(
            splunkd_uri=...,
            session_key=...,
        ):
            if ok:
                get_effective_logger().info(f"api_catalog_warmup target={target}: {msg}")
            else:
                get_effective_logger().warning(f"api_catalog_warmup target={target}: {msg}")

    The first cache miss in the loop pays the ~19s build for that
    target; subsequent calls (within the same cycle, and from any
    later consumer) hit the on-disk file in sub-second time. The
    second target's miss is independent of the first because the
    cache is keyed by ``(target, app_version)`` — rebuilding
    ``"endpoints"`` doesn't help ``"groups"`` and vice-versa, which
    is precisely why this multi-target wrapper exists.

    Args / behaviour: same as ``warmup_api_catalog_cache`` for each
    individual target call.
    """
    results: List[Tuple[str, bool, str]] = []
    for target in _WARMUP_TARGETS:
        ok, msg = warmup_api_catalog_cache(
            splunkd_uri=splunkd_uri,
            session_key=session_key,
            target=target,
        )
        results.append((target, ok, msg))
    return results
