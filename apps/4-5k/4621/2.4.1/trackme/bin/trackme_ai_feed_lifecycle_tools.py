"""
TrackMe AI Agent Tools — Feed Lifecycle Advisor

Tool definitions for the Splunk Agent SDK, enabling the Feed Lifecycle Advisor
agent to inspect, analyze, and manage DSM/DHM entity lifecycle configurations.

Tools defined:
    READ (agent's "eyes"):
    1. get_entity_lifecycle_context    — Full entity config + tenant threshold defaults
                                           + matched lagging-class assignment
    2. get_entity_delay_latency_history — 30-day delay/latency trend from summary index
    3. get_entity_alert_flip_history   — State transition history (audit index)
    4. get_entity_peer_comparison      — Same-sourcetype peers and their thresholds
    5. get_entity_variable_delay_schedule — Current variable delay slot config (if any)
    6. get_entity_adaptive_delay_history  — Adaptive delay change history (audit index)
    7. get_lagging_classes             — List all lagging classes for a tenant/component
    8. get_entity_data_sampling_state  — Per-entity data-sampling state (DSM only):
                                           colour, anomaly reason, matched model,
                                           multiformat detection, current detected
                                           format (Phase 1 of issue #1901)
    9. get_data_sampling_models        — OOTB + custom sampling models for a tenant
                                           (DSM only). Use BEFORE recommending a
                                           custom-model add/update to see what already
                                           exists (Phase 1 of issue #1901)

    WRITE (agent's "hands"):
    10. update_entity_thresholds       — Set delay/latency thresholds
    11. update_entity_monitoring_state — Enable/disable entity monitoring
    12. update_entity_adaptive_delay   — Lock/unlock adaptive delay
    13. update_entity_variable_delay   — Create/update variable delay time slots
    14. update_entity_priority_and_tags — Adjust priority and/or manual tags
    15. update_entity_impact_score_weights — Tune per-entity impact score weights
    16. set_entity_lagging_class_override — Flip per-entity opt-out of lagging-class precedence
    17. create_lagging_class           — Add a new lagging class for dsm/dhm
    18. update_lagging_class           — Modify an existing lagging class
    19. delete_lagging_class           — Remove a lagging class
    20. add_data_sampling_model        — Add a custom data-sampling model (DSM only,
                                           Phase 2 of issue #1901)
    21. update_data_sampling_model     — Modify an existing custom data-sampling
                                           model (DSM only, Phase 2 of issue #1901)
    22. delete_data_sampling_model     — Remove a custom data-sampling model (DSM
                                           only, Phase 2 of issue #1901)
"""

import json
import logging
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.ai.registry import ToolContext

from trackme_libs import run_splunk_search

# Share the single MCP registry with the ML Advisor tools so that all
# tools are served through the same tools.py MCP entry point.
# tools.py imports this module to trigger registration on the shared registry.
from trackme_ai_agent_tools import (
    registry,
    _get_trackme_service,
    _call_trackme_api,
    _api_error,
    _get_summary_index,
    _get_audit_index,
)

# Named logger — shares the singleton configured by the parent
# REST handler's setup_logger() call (root logger redirect there means
# `logging.<level>(...)` here would bleed across handlers).
logger = logging.getLogger("trackme.rest.ai.feed_lifecycle")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

COMPONENT_TO_OBJECT_CATEGORY = {
    "dsm": "splk-dsm",
    "dhm": "splk-dhm",
}


# Generic placeholders that satisfy the multi-word check but carry no audit
# value. "api update" is the codebase-wide default update_comment, i.e. the
# exact boilerplate the meaningful-reason gate exists to block.
_BANNED_REASONS = frozenset({"api update"})


def _is_meaningful_reason(reason):
    """Return True iff ``reason`` is a non-empty multi-word audit string.

    The Phase 2 data-sampling write tools (and any future write tool that
    cares about audit trail clarity) reject empty / single-word / whitespace
    reasons before issuing the REST call. The system prompt documents the
    requirement explicitly; this helper enforces it client-side so generic
    entries like ``"fix"`` / ``"API update"`` / ``"   "`` never reach the
    audit log via the advisor path.

    Defensive: non-string input → False, never raises. CodeRabbit PR #1912
    finding (🟠 Major).

    Boilerplate guard: the word-count check alone let ``"API update"`` through
    (it is two words) even though the docstring and error string name it as a
    rejected example. Reject the known boilerplate phrases explicitly
    (CodeRabbit PR #1956 follow-up).
    """
    if not isinstance(reason, str):
        return False
    stripped = reason.strip()
    if not stripped:
        return False
    # Collapse internal whitespace + lowercase so "API   update" / "Api Update"
    # normalise to the same token as "api update".
    normalized = " ".join(stripped.lower().split())
    if normalized in _BANNED_REASONS:
        return False
    words = [w for w in stripped.split() if w]
    return len(words) >= 2


_MEANINGFUL_REASON_ERROR = (
    "reason is required and must be a multi-word audit explanation — "
    "single-word or whitespace-only reasons (e.g. \"fix\", \"API update\") "
    "are rejected client-side so the advisor's audit trail stays useful "
    "to operators. Explain WHAT changed and WHY."
)


# ===========================================================================
# READ TOOLS (1-6)
# ===========================================================================


@registry.tool(name="get_entity_lifecycle_context", tags=["lifecycle_read"])
def get_entity_lifecycle_context(
    tenant_id: str,
    component: str,
    object_id: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Get the full entity lifecycle context including current configuration, thresholds,
    and monitoring state via the TrackMe describe endpoint.

    Returns a comprehensive snapshot: entity name, monitored_state, priority, SLA,
    data_max_delay_allowed, data_max_lag_allowed, threshold_locked (the single
    user-facing lock; allow_adaptive_delay is derived from it and kept for
    back-compat), allow_adaptive_delay, variable_delay_policy,
    monitoring_time_policy, tags, impact_score_weights, tenant-level default
    thresholds, and current health state.

    Parameters:
        tenant_id: The tenant identifier (e.g., "prod-monitoring")
        component: The component type: "dsm" or "dhm"
        object_id: The entity's _key hash in KV Store

    Use this as the FIRST tool to understand an entity's full configuration.
    """
    service = _get_trackme_service(ctx)
    object_category = COMPONENT_TO_OBJECT_CATEGORY.get(component, f"splk-{component}")

    result = _call_trackme_api(service, "trackme/v2/describe/entity", body={
        "tenant_id": tenant_id,
        "object_category": object_category,
        "object_id": object_id,
    })

    if "entity_description" in result:
        desc = result["entity_description"]
        # Extract and surface the most relevant lifecycle fields
        identity = desc.get("identity", {})
        config = desc.get("configuration", {})
        health = desc.get("health", {})

        # Lagging-class assignment — added by the describe layer in
        # ``trackme_libs_describe.py``. When a class matches this entity
        # AND the entity isn't opted out via ``entity_override="true"``,
        # the class's delay (and lag, if set) thresholds OVERRIDE the
        # entity-level values. Without seeing this block the advisor
        # has previously tuned entity-level thresholds that were inert
        # because a class was silently overriding them — see the
        # ``precedence_note`` for the operational rule.
        lagging_class_assignment = config.get("lagging_class_assignment", {})

        lifecycle_config = {
            "object": identity.get("object", ""),
            "object_id": object_id,
            "component": component,
            "tenant_id": tenant_id,
            "monitored_state": config.get("monitored_state", "unknown"),
            "priority": config.get("priority", "unknown"),
            "sla_class": config.get("sla_class", ""),
            "tags": config.get("tags_manual", ""),
            "data_max_delay_allowed": config.get("data_max_delay_allowed", "N/A"),
            "data_max_lag_allowed": config.get("data_max_lag_allowed", "N/A"),
            # Threshold lock — the single user-facing control. When locked, the
            # delay/lag thresholds are pinned (adaptive delay + lagging-class
            # override disabled, reconcile restores drift). allow_adaptive_delay
            # below is DERIVED from this and kept for back-compat only. Sourced
            # from the describe layer's ``configuration.threshold_lock`` block.
            "threshold_locked": bool(
                config.get("threshold_lock", {}).get("locked", False)
            ),
            "allow_adaptive_delay": config.get("allow_adaptive_delay", "N/A"),
            "variable_delay_policy": config.get("variable_delay_policy", "static"),
            "monitoring_time_policy": config.get("monitoring_time_policy", ""),
            "impact_score_weights": config.get("impact_score_weights", ""),
            "current_state": health.get("object_state", "unknown"),
            "anomaly_reasons": health.get("anomaly_reasons", []),
            # is_outlier=1 means the ML model is ACTIVELY contributing to the RED score.
            # is_outlier=0 means ML models are NOT in the score — do not take any ML actions.
            "is_outlier": health.get("isOutlier", 0),
            "outlier_readiness": health.get("outlier_readiness", False),
            "last_event_detected_time": identity.get("last_event_detected_time", ""),
            "last_ingest_time": identity.get("last_ingest_time", ""),
            # Lagging-class assignment block (see comment above).
            "lagging_class_assignment": lagging_class_assignment,
        }

        # Include the full description for reference
        return {
            "lifecycle_config": lifecycle_config,
            "full_description": desc,
        }

    return result


@registry.tool(name="get_entity_delay_latency_history", tags=["lifecycle_read"])
def get_entity_delay_latency_history(
    tenant_id: str,
    component: str,
    object_id: str,
    object_name: str = "",
    earliest: str = "-30d",
    latest: str = "now",
    ctx: ToolContext = None,
) -> dict:
    """
    Get 30-day delay and latency history for a DSM/DHM entity from the summary index.

    Returns timestamped delay/latency values with percentile statistics (p50, p75, p95, p99),
    enabling detection of typical ingestion patterns: continuous feeds, daily batches,
    weekend gaps, and gradual drift. Also computes silent periods (consecutive zero-data gaps).

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm" or "dhm"
        object_id: The entity's _key hash in KV Store
        object_name: Entity name (optional, used for logging)
        earliest: Start time (default: "-30d")
        latest: End time (default: "now")

    Use this to understand the entity's actual ingestion rhythm before recommending thresholds.
    The p95 value is the recommended basis for setting data_max_delay_allowed (with buffer).
    """
    service = _get_trackme_service(ctx)
    summary_idx = _get_summary_index(service, tenant_id)

    search_query = (
        f'search index="{summary_idx}"'
        f' tenant_id="{tenant_id}"'
        f' component="splk-{component}"'
        f' object_id="{object_id}"'
        f' (data_max_delay_allowed=* OR data_max_lag_allowed=* OR current_delay=* OR current_lag=*)'
        f' | eval delay=coalesce(current_delay, data_delay)'
        f' | eval lag=coalesce(current_lag, data_lag)'
        f' | where isnum(delay) OR isnum(lag)'
        f' | eval day=strftime(_time, "%Y-%m-%d")'
        f' | stats avg(delay) as avg_delay max(delay) as max_delay'
        f'        avg(lag) as avg_lag max(lag) as max_lag'
        f'        count as data_points by day'
        f' | sort day'
    )

    search_params = {
        "earliest_time": earliest,
        "latest_time": latest,
        "output_mode": "json",
        "count": 0,
    }

    daily_data = []
    try:
        results_reader = run_splunk_search(service, search_query, search_params, max_retries=3)
        for result in results_reader:
            if isinstance(result, dict):
                try:
                    daily_data.append({
                        "day": result.get("day", ""),
                        "avg_delay_sec": round(float(result.get("avg_delay", 0) or 0), 0),
                        "max_delay_sec": round(float(result.get("max_delay", 0) or 0), 0),
                        "avg_lag_sec": round(float(result.get("avg_lag", 0) or 0), 0),
                        "max_lag_sec": round(float(result.get("max_lag", 0) or 0), 0),
                        "data_points": int(float(result.get("data_points", 0) or 0)),
                    })
                except (ValueError, TypeError):
                    continue
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}

    if not daily_data:
        return {
            "message": "No delay/latency history found for this entity in the specified window.",
            "daily_data": [],
            "statistics": {},
        }

    # Compute statistics over daily max_delay values
    delay_values = [d["max_delay_sec"] for d in daily_data if d["max_delay_sec"] > 0]
    lag_values = [d["max_lag_sec"] for d in daily_data if d["max_lag_sec"] > 0]
    stats = {}

    if delay_values:
        sv = sorted(delay_values)
        n = len(sv)
        stats["delay"] = {
            "p50_sec": sv[min(int(n * 0.50), n - 1)],
            "p75_sec": sv[min(int(n * 0.75), n - 1)],
            "p95_sec": sv[min(int(n * 0.95), n - 1)],
            "p99_sec": sv[min(int(n * 0.99), n - 1)],
            "max_sec": max(sv),
            "mean_sec": round(sum(sv) / n, 0),
            "sample_days": n,
            "recommended_threshold_sec": round(sv[min(int(n * 0.95), n - 1)] * 1.2, 0),
        }

    if lag_values:
        sv = sorted(lag_values)
        n = len(sv)
        stats["lag"] = {
            "p50_sec": sv[min(int(n * 0.50), n - 1)],
            "p75_sec": sv[min(int(n * 0.75), n - 1)],
            "p95_sec": sv[min(int(n * 0.95), n - 1)],
            "p99_sec": sv[min(int(n * 0.99), n - 1)],
            "max_sec": max(sv),
            "mean_sec": round(sum(sv) / n, 0),
            "sample_days": n,
        }

    # Detect silent periods by finding gaps between consecutive days present in results.
    # stats-by-day only emits rows for days with data, so missing days appear as date gaps.
    from datetime import datetime, timedelta

    silent_periods = []
    for i in range(len(daily_data) - 1):
        try:
            day_a = datetime.strptime(daily_data[i]["day"], "%Y-%m-%d")
            day_b = datetime.strptime(daily_data[i + 1]["day"], "%Y-%m-%d")
        except ValueError:
            continue
        gap_days = (day_b - day_a).days - 1  # days between the two present rows
        if gap_days >= 2:
            gap_start = (day_a + timedelta(days=1)).strftime("%Y-%m-%d")
            gap_end = (day_b - timedelta(days=1)).strftime("%Y-%m-%d")
            silent_periods.append({"start": gap_start, "end": gap_end, "days": gap_days})

    return {
        "object_id": object_id,
        "object_name": object_name,
        "earliest": earliest,
        "latest": latest,
        "total_days": len(daily_data),
        "daily_data": daily_data,
        "statistics": stats,
        "silent_periods": silent_periods,
        "longest_silent_days": max((s["days"] for s in silent_periods), default=0),
    }


@registry.tool(name="get_entity_alert_flip_history", tags=["lifecycle_read"])
def get_entity_alert_flip_history(
    tenant_id: str,
    component: str,
    object_id: str,
    earliest: str = "-30d",
    latest: str = "now",
    ctx: ToolContext = None,
) -> dict:
    """
    Get state transition (flip) history for a DSM/DHM entity from the audit index.

    Returns timestamped RED/GREEN transitions with the anomaly reasons. High flip counts
    with delay-related reasons indicate threshold mismatch, not genuine data issues.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm" or "dhm"
        object_id: The entity's _key hash in KV Store
        earliest: Start time for history lookback (default: "-30d")
        latest: End time (default: "now")

    Use this to correlate alert patterns with threshold issues vs. genuine data problems.
    A high flip count with 'delay threshold' reasons strongly suggests the threshold is too tight.
    """
    service = _get_trackme_service(ctx)
    audit_idx = _get_audit_index(service, tenant_id)

    state_transitions = []
    delay_related_reds = 0
    total_reds = 0

    try:
        search_query = (
            f'search index={audit_idx}'
            f' tenant_id="{tenant_id}"'
            f' object_id="{object_id}"'
            f' change_type="state change"'
            f' | sort _time'
            f' | fields _time, previous_state, new_state, anomaly_reason'
            f' | head 200'
        )
        search_params = {
            "earliest_time": earliest,
            "latest_time": latest,
            "output_mode": "json",
            "count": 0,
        }
        results_reader = run_splunk_search(service, search_query, search_params, max_retries=3)
        for result in results_reader:
            if isinstance(result, dict):
                new_state = result.get("new_state", "")
                anomaly_reason = result.get("anomaly_reason", "")
                if new_state in ("red", "RED"):
                    total_reds += 1
                    if any(kw in anomaly_reason.lower() for kw in ("delay", "lag", "latency")):
                        delay_related_reds += 1
                state_transitions.append({
                    "_time": result.get("_time", ""),
                    "from": result.get("previous_state", ""),
                    "to": new_state,
                    "reason": anomaly_reason,
                })
    except Exception as e:
        logger.warning(f"Could not fetch state transitions: {e}")

    # Also get current state via describe
    current_state = "unknown"
    try:
        object_category = COMPONENT_TO_OBJECT_CATEGORY.get(component, f"splk-{component}")
        describe = _call_trackme_api(service, "trackme/v2/describe/entity", body={
            "tenant_id": tenant_id,
            "object_category": object_category,
            "object_id": object_id,
        })
        entity_desc = describe.get("entity_description", describe)
        current_state = entity_desc.get("health", {}).get("object_state", "unknown")
    except Exception:
        pass

    return {
        "object_id": object_id,
        "current_state": current_state,
        "total_transitions": len(state_transitions),
        "total_reds": total_reds,
        "delay_related_reds": delay_related_reds,
        "delay_false_positive_ratio": round(delay_related_reds / total_reds, 2) if total_reds else 0.0,
        "state_transitions": state_transitions[-100:],
    }


@registry.tool(name="get_entity_peer_comparison", tags=["lifecycle_read"])
def get_entity_peer_comparison(
    tenant_id: str,
    component: str,
    object_id: str,
    sourcetype: str = "",
    max_peers: int = 10,
    ctx: ToolContext = None,
) -> dict:
    """
    Compare this entity's thresholds to similar peer entities in the same tenant.

    Returns peer entities with the same sourcetype (DSM) or a sample of same-component
    entities (DHM), showing their threshold configurations for comparison.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm" or "dhm"
        object_id: The entity's _key hash in KV Store
        sourcetype: For DSM — the sourcetype to filter peers (leave empty to auto-detect)
        max_peers: Maximum peers to return (default: 10)

    Use this to understand whether this entity's thresholds are outliers compared to peers.
    """
    service = _get_trackme_service(ctx)

    collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
    try:
        collection = service.kvstore[collection_name]
        # Get this entity first to determine sourcetype
        own_records = collection.data.query(query=json.dumps({"_key": object_id}))
        own_data = own_records[0] if own_records else {}

        own_sourcetype = sourcetype or own_data.get("data_sourcetype", own_data.get("sourcetype", ""))
        own_name = own_data.get("object", own_data.get("data_name", ""))

        # Query peers
        query_filter = {}
        if own_sourcetype and component == "dsm":
            query_filter["data_sourcetype"] = own_sourcetype

        all_records = collection.data.query(query=json.dumps(query_filter))

        peers = []
        for record in all_records:
            if record.get("_key") == object_id:
                continue  # Skip self
            peer = {
                "object": record.get("object", record.get("data_name", "")),
                "monitored_state": record.get("monitored_state", ""),
                "data_max_delay_allowed": record.get("data_max_delay_allowed", ""),
                "data_max_lag_allowed": record.get("data_max_lag_allowed", ""),
                "threshold_locked": (
                    str(record.get("data_max_delay_allowed_locked", "false"))
                    .strip()
                    .lower()
                    in ("true", "1")
                ),
                "allow_adaptive_delay": record.get("allow_adaptive_delay", ""),
                "variable_delay_policy": record.get("variable_delay_policy", "static"),
                "priority": record.get("priority", ""),
                "object_state": record.get("object_state", ""),
            }
            peers.append(peer)
            if len(peers) >= max_peers:
                break

        # Compute median delay threshold across peers for reference
        delay_values = []
        for p in peers:
            v = p["data_max_delay_allowed"]
            if v:
                try:
                    delay_values.append(int(float(v)))
                except (ValueError, TypeError):
                    pass

        peer_delay_median = None
        if delay_values:
            sv = sorted(delay_values)
            peer_delay_median = sv[len(sv) // 2]

        return {
            "own_entity": {
                "object": own_name,
                "sourcetype": own_sourcetype,
                "data_max_delay_allowed": own_data.get("data_max_delay_allowed", ""),
                "data_max_lag_allowed": own_data.get("data_max_lag_allowed", ""),
                "threshold_locked": (
                    str(own_data.get("data_max_delay_allowed_locked", "false"))
                    .strip()
                    .lower()
                    in ("true", "1")
                ),
                "allow_adaptive_delay": own_data.get("allow_adaptive_delay", ""),
            },
            "peers": peers,
            "peer_count": len(peers),
            "peer_delay_median_sec": peer_delay_median,
        }

    except Exception as e:
        return {"error": f"Failed to query peer entities: {str(e)}"}


@registry.tool(name="get_entity_variable_delay_schedule", tags=["lifecycle_read"])
def get_entity_variable_delay_schedule(
    tenant_id: str,
    component: str,
    object_id: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Get the current variable delay schedule configuration for an entity (if any).

    Returns the configured time slots with their day/hour definitions and delay thresholds.
    If the entity has variable_delay_policy='static', returns a message indicating no schedule.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm" or "dhm"
        object_id: The entity's _key hash in KV Store

    Use this before recommending or creating a variable delay schedule to understand
    what's already configured and whether it needs to be updated.
    """
    service = _get_trackme_service(ctx)

    result = _call_trackme_api(
        service,
        "trackme/v2/splk_variable_delay/get",
        body={
            "tenant_id": tenant_id,
            "component": component,
            "object_id": object_id,
        },
    )

    err = _api_error(result)
    if err is not None:
        # Distinguish a transport / HTTP failure from a legitimate
        # "no variable delay configured" response. The pre-PR-#1824 code
        # collapsed both into the misleading "uses static thresholds"
        # message, which could drive the advisor toward the wrong
        # remediation when the agent was actually facing an API outage
        # (CodeRabbit PR #1824 finding).
        #
        # ``_call_trackme_api`` populates ``http_status`` ONLY on HTTP
        # failures. REST-level "no record found" responses from the
        # endpoint flow through with an ``error`` field but no
        # ``http_status``. Use that to discriminate.
        http_status = (
            result.get("http_status") if isinstance(result, dict) else None
        )
        if isinstance(http_status, int) and http_status >= 400:
            # Real API failure — surface to the LLM verbatim instead
            # of pretending the entity is on static thresholds.
            return {
                "has_variable_delay": False,
                "error": err,
                "http_status": http_status,
                "api_response": result,
            }
        # REST-level no-record / no-config response — legitimate
        # fallback: the entity is on static thresholds.
        return {
            "has_variable_delay": False,
            "message": "No variable delay configuration found (entity uses static thresholds).",
            "api_response": result,
        }

    return {
        "has_variable_delay": True,
        "variable_delay_config": result,
    }


@registry.tool(name="get_entity_adaptive_delay_history", tags=["lifecycle_read"])
def get_entity_adaptive_delay_history(
    tenant_id: str,
    component: str,
    object_id: str,
    earliest: str = "-30d",
    latest: str = "now",
    ctx: ToolContext = None,
) -> dict:
    """
    Get the history of adaptive delay changes for an entity from the audit index.

    Returns timestamped records of when TrackMe's adaptive delay feature automatically
    adjusted the delay threshold, and by how much.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm" or "dhm"
        object_id: The entity's _key hash in KV Store
        earliest: Start time (default: "-30d")
        latest: End time (default: "now")

    Use this to detect if adaptive delay is frequently overriding manual threshold settings.
    High change frequency indicates the user's manual tuning is being overwritten.
    """
    service = _get_trackme_service(ctx)
    audit_idx = _get_audit_index(service, tenant_id)

    adaptive_changes = []
    try:
        search_query = (
            f'search index={audit_idx}'
            f' tenant_id="{tenant_id}"'
            f' object_id="{object_id}"'
            f' (change_type="adaptive_delay" OR update_comment="*adaptive*" OR update_comment="*auto*")'
            f' | sort -_time'
            f' | fields _time, change_type, new_data_max_delay_allowed, previous_data_max_delay_allowed, update_comment'
            f' | head 100'
        )
        search_params = {
            "earliest_time": earliest,
            "latest_time": latest,
            "output_mode": "json",
            "count": 0,
        }
        results_reader = run_splunk_search(service, search_query, search_params, max_retries=3)
        for result in results_reader:
            if isinstance(result, dict):
                adaptive_changes.append({
                    "_time": result.get("_time", ""),
                    "change_type": result.get("change_type", ""),
                    "new_delay": result.get("new_data_max_delay_allowed", ""),
                    "prev_delay": result.get("previous_data_max_delay_allowed", ""),
                    "comment": result.get("update_comment", ""),
                })
    except Exception as e:
        logger.warning(f"Could not fetch adaptive delay history: {e}")

    return {
        "object_id": object_id,
        "earliest": earliest,
        "latest": latest,
        "total_adaptive_changes": len(adaptive_changes),
        "adaptive_changes": adaptive_changes,
        "adaptive_delay_very_active": len(adaptive_changes) > 10,
    }


# ===========================================================================
# Data Sampling read tools (DSM only) — Phase 1 of issue #1901
# ===========================================================================
#
# Data Sampling is a DSM-only feature that samples events at configurable
# intervals, fits regex-based format models, and flags anomalies when match
# percentage drops below threshold. When a sampling anomaly fires for a
# given DSM entity, the decision maker adds
# ``impact_score_dsm_data_sampling_anomaly`` (default 36) to the entity's
# total score and ``data_sampling_anomaly`` to its anomaly_reasons.
#
# Pre-Phase-1, the advisor had no way to read this state — the describe
# endpoint surfaces only ``data_sample_lastrun`` (one timestamp). Without
# the tools below, an entity that's RED partly because of a sampling
# anomaly gets misdiagnosed (the agent reasons about delay/lag thresholds
# and misses the actual root cause).
#
# Two tools land in Phase 1 (inspect-mode only):
#
#   * ``get_entity_data_sampling_state`` — per-entity rich state from the
#     ``kv_trackme_dsm_data_sampling_tenant_<tid>`` collection. Returns the
#     colour, anomaly reason, status message, matched model summary,
#     multiformat detection flag, current and previous detected formats.
#     The agent SHOULD call this whenever ``anomaly_reasons`` contains
#     ``data_sampling_anomaly`` to reason about the actual root cause.
#
#   * ``get_data_sampling_models`` — list of OOTB rules and per-tenant
#     custom rules. Use BEFORE proposing a custom-model add (Phase 2) so
#     the agent sees what already exists and doesn't propose duplicates.
#
# Write tools (add / update / delete custom model) and the wizard-time
# generate-model mode land in Phases 2 and 3 — see issue #1901 for the
# full rollout plan.
# ===========================================================================


@registry.tool(name="get_entity_data_sampling_state", tags=["lifecycle_read"])
def get_entity_data_sampling_state(
    tenant_id: str,
    object_name: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Read the data-sampling state for a single DSM entity.

    Returns the colour, anomaly state, matched model summary, multiformat
    detection flag, and current / previous detected formats from
    ``kv_trackme_dsm_data_sampling_tenant_<tenant_id>``. Use this whenever
    the entity's ``anomaly_reasons`` contains ``data_sampling_anomaly`` —
    without it the advisor reasons about delay/lag thresholds and misses
    the actual root cause (a content-format change in the source data).

    Data Sampling is DSM-only. For DHM / MHM / FLX / FQM / WLK entities
    this tool returns ``has_data_sampling_state: False`` with a note —
    those components have their own data-quality mechanisms (FQM and FLX
    in particular) and are out of scope here.

    Parameters:
        tenant_id: The tenant identifier
        object_name: The entity name (the ``object`` field, e.g.
            ``"siem-cloud-amer:aws:config"``). NOT the ``object_id`` SHA256
            hash — the data-sampling KV collection is keyed by the
            human-readable entity name.

    Returns:
        On success:
          {
            "has_data_sampling_state": True,
            "object": "<entity name>",
            "status_colour": "green" | "orange" | "red" | "blue" | ...,
            "anomaly_detected": <int 0|1>,
            "anomaly_reason": "<short reason string>",
            "status_message": "<human-readable status>",
            "matched_model_summary": "<comma-sep model names>",
            "multiformat_detected": <bool>,
            "current_detected_format": "<format identifier>",
            "current_detected_major_format": "<json|xml|csv|kv|raw|...>",
            "previous_detected_format": "<format identifier>",
            "events_count": <int>,
            "last_run_epoch": <int>,
            "last_iteration": <int>,
            "iteration_interval_seconds": <int>,
            "sampling_window_seconds": <int>,
            "pct_min_inclusive_match": <float 0..100>,
            "pct_max_exclusive_match": <float 0..100>,
          }

        When no record exists (e.g. non-DSM entity, or DSM entity that hasn't
        been sampled yet):
          {
            "has_data_sampling_state": False,
            "object": "<entity name>",
            "message": "<reason>",
          }
    """
    service = _get_trackme_service(ctx)

    collection_name = f"kv_trackme_dsm_data_sampling_tenant_{tenant_id}"
    try:
        coll = service.kvstore[collection_name]
        # The collection is keyed by ``object`` (entity name), NOT by
        # the SHA256 _key hash. A direct query_by_id would only work if
        # the agent had pre-resolved the hash; the human-readable name
        # is what the rest of the advisor's reasoning chain uses, so
        # accept it directly and lookup via JSON query.
        records = coll.data.query(query=json.dumps({"object": object_name}))
    except KeyError:
        # Collection doesn't exist — tenant doesn't have DSM enabled, or
        # the entity belongs to a different component family.
        return {
            "has_data_sampling_state": False,
            "object": object_name,
            "message": (
                f"No data-sampling collection for tenant {tenant_id!r} — "
                "the tenant likely doesn't have DSM enabled."
            ),
        }
    except Exception as e:
        return {
            "has_data_sampling_state": False,
            "object": object_name,
            "error": (
                f"Failed to read data-sampling state for object={object_name!r}: {e}"
            ),
        }

    # ``records`` can be empty, a list of one, or rarely a list of more than
    # one if collection state is corrupted. Take the first; if empty,
    # signal no state.
    if not records:
        return {
            "has_data_sampling_state": False,
            "object": object_name,
            "message": (
                "No data-sampling record found for this entity. "
                "Either the entity is not DSM, sampling has never run, or "
                "sampling is disabled for this entity / tenant."
            ),
        }

    rec = records[0] if isinstance(records, list) else records

    def _safe_int(v, default=0):
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    def _safe_float(v, default=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def _truthy_int(v):
        return _safe_int(v) == 1

    return {
        "has_data_sampling_state": True,
        "object": rec.get("object", object_name),
        "status_colour": rec.get("data_sample_status_colour", "unknown"),
        "anomaly_detected": _safe_int(rec.get("data_sample_anomaly_detected"), 0),
        "anomaly_reason": rec.get("data_sample_anomaly_reason", ""),
        "status_message": rec.get("data_sample_status_message", ""),
        "matched_model_summary": rec.get("data_sample_model_matched_summary", ""),
        "multiformat_detected": _truthy_int(rec.get("multiformat_detected", 0)),
        "current_detected_format": rec.get("current_detected_format", ""),
        "current_detected_major_format": rec.get("current_detected_major_format", ""),
        "previous_detected_format": rec.get("previous_detected_format", ""),
        "events_count": _safe_int(rec.get("events_count"), 0),
        "last_run_epoch": _safe_int(rec.get("data_sample_mtime"), 0),
        "last_iteration": _safe_int(rec.get("data_sample_iteration"), 0),
        "iteration_interval_seconds": _safe_int(
            rec.get("min_time_btw_iterations_seconds"), 0
        ),
        "sampling_window_seconds": _safe_int(
            rec.get("relative_time_window_seconds"), 0
        ),
        "pct_min_inclusive_match": _safe_float(
            rec.get("pct_min_major_inclusive_model_match"), 0.0
        ),
        "pct_max_exclusive_match": _safe_float(
            rec.get("pct_max_exclusive_model_match"), 0.0
        ),
    }


@registry.tool(name="get_data_sampling_models", tags=["lifecycle_read"])
def get_data_sampling_models(
    tenant_id: str,
    include_ootb: bool = True,
    include_custom: bool = True,
    ctx: ToolContext = None,
) -> dict:
    """
    List the data-sampling models known to TrackMe for the given tenant.

    Two categories:
      * ``ootb`` — built-in regex format models shipped with TrackMe (json,
        xml, csv, key=value, syslog, …). Always available.
      * ``custom`` — per-tenant operator-defined models in
        ``kv_trackme_dsm_data_sampling_custom_models_tenant_<tenant_id>``.
        These extend the OOTB set with site-specific patterns (e.g. a
        proprietary log format).

    Use this BEFORE proposing a custom-model addition (Phase 2 of issue
    #1901) so the agent doesn't propose a regex that's already covered.

    Data Sampling is DSM-only — the response carries the tenant_id verbatim
    so the LLM can confirm scope.

    Parameters:
        tenant_id: The tenant identifier.
        include_ootb: Include the built-in OOTB models. Default True.
        include_custom: Include the tenant's custom models. Default True.

    Returns:
        {
          "tenant_id": "<tid>",
          "ootb": [<model dict>, ...],      # empty if include_ootb=False
          "custom": [<model dict>, ...],    # empty if include_custom=False
          "ootb_count": <int>,
          "custom_count": <int>,
        }

        On error from either endpoint, the corresponding list is empty and
        an ``ootb_error`` / ``custom_error`` field carries the message.
    """
    service = _get_trackme_service(ctx)

    out = {
        "tenant_id": tenant_id,
        "ootb": [],
        "custom": [],
        "ootb_count": 0,
        "custom_count": 0,
    }

    if include_ootb:
        # OOTB rules are tenant-agnostic — GET endpoint, empty body.
        ootb_result = _call_trackme_api(
            service,
            "trackme/v2/splk_data_sampling/data_sampling_ootb_rules_show",
            method="get",
        )
        ootb_err = _api_error(ootb_result)
        if ootb_err is not None:
            out["ootb_error"] = ootb_err
        else:
            # Normalise to a flat list — the REST endpoint returns either a
            # dict-with-records-key or a bare list depending on Splunk version.
            # If the dict doesn't match any of the known wrapper keys, surface
            # an explicit error rather than silently reporting "0 models" —
            # the LLM would otherwise conclude "no models exist" when in
            # reality we got a response shape we don't recognise (e.g. a new
            # Splunk version wrapping the payload differently). CodeRabbit
            # finding on PR #1902.
            if isinstance(ootb_result, list):
                out["ootb"] = ootb_result
            elif isinstance(ootb_result, dict):
                matched = False
                for key in ("records", "rules", "results", "data"):
                    val = ootb_result.get(key)
                    if isinstance(val, list):
                        out["ootb"] = val
                        matched = True
                        break
                if not matched:
                    out["ootb_error"] = (
                        f"Unrecognised response shape from OOTB endpoint: "
                        f"keys={sorted(ootb_result.keys())}"
                    )
            out["ootb_count"] = len(out["ootb"])

    if include_custom:
        # Custom rules are per-tenant — POST with tenant_id body.
        custom_result = _call_trackme_api(
            service,
            "trackme/v2/splk_data_sampling/data_sampling_rules_show",
            body={"tenant_id": tenant_id},
        )
        custom_err = _api_error(custom_result)
        if custom_err is not None:
            out["custom_error"] = custom_err
        else:
            # Same dict-without-known-keys defence as the OOTB branch.
            if isinstance(custom_result, list):
                out["custom"] = custom_result
            elif isinstance(custom_result, dict):
                matched = False
                for key in ("records", "rules", "results", "data"):
                    val = custom_result.get(key)
                    if isinstance(val, list):
                        out["custom"] = val
                        matched = True
                        break
                if not matched:
                    out["custom_error"] = (
                        f"Unrecognised response shape from custom endpoint: "
                        f"keys={sorted(custom_result.keys())}"
                    )
            out["custom_count"] = len(out["custom"])

    return out


# ===========================================================================
# WRITE TOOLS (7-12)
# ===========================================================================


@registry.tool(name="update_entity_thresholds", tags=["lifecycle_write"])
def update_entity_thresholds(
    tenant_id: str,
    component: str,
    object_id: str,
    reason: str,
    data_max_delay_allowed: str = "",
    data_max_lag_allowed: str = "",
    ctx: ToolContext = None,
) -> dict:
    """
    Update the STATIC delay and/or latency thresholds for a DSM/DHM entity.

    This tool writes to ``data_max_delay_allowed`` and/or
    ``data_max_lag_allowed``. These two fields behave DIFFERENTLY depending
    on the entity's ``variable_delay_policy``:

    - ``data_max_lag_allowed`` is ALWAYS the active lag threshold,
      regardless of policy. Use this tool for lag in every case.
    - ``data_max_delay_allowed`` is ONLY the active delay threshold when
      ``variable_delay_policy = "static"``. When the policy is
      ``"variable"``, slot-based thresholds apply and
      ``data_max_delay_allowed`` is INERT — writing to it succeeds at the
      API level but has no effect on the entity's actual alerting
      threshold.

    The tool enforces this at runtime: a call with
    ``data_max_delay_allowed`` on an entity whose policy is ``variable``
    is REJECTED with a structured error and a ``redirect_tool`` pointing
    you to ``update_entity_variable_delay``. To change the delay
    threshold on a variable-policy entity you MUST use that tool
    instead. If you ALSO need to change the lag threshold on the same
    entity, split into two calls: ``update_entity_variable_delay`` for
    the slot, then this tool again with ``data_max_lag_allowed`` only
    (leave ``data_max_delay_allowed`` empty).

    Calls the TrackMe update_lag_policy endpoint to set new threshold
    values. At least one of ``data_max_delay_allowed`` or
    ``data_max_lag_allowed`` must be provided.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm" or "dhm"
        object_id: The entity's _key hash in KV Store
        reason: Your explanation for why this change is appropriate
        data_max_delay_allowed: New delay threshold (e.g., "3600", "1h", "1d")
            Specify in seconds (integer string) or with unit suffix (m/h/d/w).
            NEVER tighten — only loosen to match observed p95 + buffer.
            Will be REJECTED if ``variable_delay_policy="variable"``.
        data_max_lag_allowed: New lag threshold in same format (optional)

    IMPORTANT: Only loosen thresholds based on observed historical data.
    Tightening thresholds (setting smaller values than current) is not allowed.
    """
    service = _get_trackme_service(ctx)

    if not data_max_delay_allowed and not data_max_lag_allowed:
        return {"success": False, "error": "At least one of data_max_delay_allowed or data_max_lag_allowed must be provided"}

    # Guard: when ``data_max_delay_allowed`` is being set, verify the
    # entity uses ``variable_delay_policy="static"``.  Entities with
    # policy=variable use slot-based thresholds; the static field is
    # inert in that regime and writing to it would succeed at the
    # underlying ``update_lag_policy`` endpoint while having zero effect
    # on the active delay threshold.  This caught a real demo failure
    # on Claude Haiku: the LLM conflated the two tools, called this one
    # with ``data_max_delay_allowed`` on a variable-policy entity, the
    # call returned success, the audit log recorded the write, and the
    # entity stayed RED because the active slot was unchanged.  Refuse
    # the call with a structured error pointing the LLM at the right
    # tool — smaller models reliably self-correct on next step when
    # given a structured ``redirect_tool`` hint.  ``data_max_lag_allowed``
    # is independent of the delay policy (lag is always static) so we
    # do NOT gate it; a call passing only lag proceeds normally even on
    # variable-policy entities.
    if data_max_delay_allowed:
        object_category = COMPONENT_TO_OBJECT_CATEGORY.get(component, f"splk-{component}")
        try:
            describe_resp = _call_trackme_api(
                service,
                "trackme/v2/describe/entity",
                body={
                    "tenant_id": tenant_id,
                    "object_category": object_category,
                    "object_id": object_id,
                },
            )
            policy = (
                (describe_resp or {})
                .get("entity_description", {})
                .get("configuration", {})
                .get("variable_delay_policy", "static")
            )
        except Exception as guard_exc:
            # Fail-open: if the describe call errors (transient network
            # blip, RBAC oddity, etc.) we proceed rather than block
            # legitimate writes.  Log so the failure mode is visible.
            logger.warning(
                f"update_entity_thresholds: policy guard pre-check failed "
                f"for tenant_id={tenant_id} object_id={object_id}: "
                f"{guard_exc!r} — proceeding without policy verification"
            )
            policy = "static"

        if str(policy).strip().lower() == "variable":
            logger.warning(
                f"update_entity_thresholds: rejected call with "
                f"data_max_delay_allowed={data_max_delay_allowed!r} on "
                f"entity {object_id} (tenant_id={tenant_id}) because "
                f"variable_delay_policy=variable — redirecting LLM to "
                f"update_entity_variable_delay"
            )
            return {
                "success": False,
                "error": (
                    "Entity uses variable_delay_policy=variable; the "
                    "static data_max_delay_allowed field is inert when "
                    "slot-based thresholds are active. Writing to it "
                    "would succeed at the API level but have no effect "
                    "on the entity's actual delay alerting threshold. "
                    "Use the update_entity_variable_delay tool instead "
                    "to modify the active slot (or all slots) for this "
                    "entity. If you ALSO need to update "
                    "data_max_lag_allowed (which IS independent of the "
                    "slot policy), call this tool again with "
                    "data_max_lag_allowed alone (leave "
                    "data_max_delay_allowed empty)."
                ),
                "redirect_tool": "update_entity_variable_delay",
                "entity_variable_delay_policy": "variable",
                "object_id": object_id,
            }

    comp_prefix = "ds" if component == "dsm" else "dh"
    endpoint = f"trackme/v2/splk_{component}/write/{comp_prefix}_update_lag_policy"

    body = {
        "tenant_id": tenant_id,
        "keys_list": object_id,
        "update_comment": f"[AI Feed Lifecycle Advisor] {reason}",
    }
    if data_max_delay_allowed:
        body["data_max_delay_allowed"] = data_max_delay_allowed
    if data_max_lag_allowed:
        body["data_max_lag_allowed"] = data_max_lag_allowed

    result = _call_trackme_api(service, endpoint, body=body)

    return {
        "success": not _api_error(result),
        "object_id": object_id,
        "data_max_delay_allowed": data_max_delay_allowed,
        "data_max_lag_allowed": data_max_lag_allowed,
        "reason": reason,
        "response": result,
    }


@registry.tool(name="update_entity_monitoring_state", tags=["lifecycle_write"])
def update_entity_monitoring_state(
    tenant_id: str,
    component: str,
    object_id: str,
    monitored_state: str,
    reason: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Enable or disable monitoring for a DSM/DHM entity.

    Calls the TrackMe monitoring endpoint to change the entity's monitored_state.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm" or "dhm"
        object_id: The entity's _key hash in KV Store
        monitored_state: "enabled" or "disabled"
        reason: Your explanation for why this change is appropriate
            REQUIRED: You MUST include the data evidence, e.g.:
            "No data received for 14 consecutive days (last seen: 2026-03-01)."

    IMPORTANT: Only disable an entity when you have clear evidence of inactivity
    (e.g., 7+ days of no data). Always document the evidence in the reason field.
    """
    service = _get_trackme_service(ctx)

    if monitored_state not in ("enabled", "disabled"):
        return {"success": False, "error": f"Invalid monitored_state '{monitored_state}'. Must be 'enabled' or 'disabled'"}

    # Tool-level guard: only applies in automated (scheduled) runs.
    # Interactive users are not subject to the tenant decommission policy.
    # The flag is the unified ``ai_components_advisor_allow_decommission``
    # (replaces the per-advisor ``ai_feed_lifecycle_allow_decommission``).
    if monitored_state == "disabled" and os.environ.get("TRACKME_AI_AUTOMATED") == "1":
        _allow_decommission = False
        try:
            _vt_records = service.kvstore["kv_trackme_virtual_tenants"].data.query(
                query=json.dumps({"tenant_id": tenant_id})
            )
            if _vt_records:
                _vt_account = json.loads(_vt_records[0].get("vtenant_account", "{}"))
                _allow_decommission = _vt_account.get("ai_components_advisor_allow_decommission", "0") == "1"
        except Exception:
            _allow_decommission = False  # fail safe: deny on lookup failure

        if not _allow_decommission:
            return {
                "success": False,
                "error": (
                    "Blocked by tenant policy: disabling entity monitoring is not permitted in "
                    "automated mode. Set ai_components_advisor_allow_decommission=1 in the tenant "
                    "AI Settings to enable automated decommissioning, or run manually. "
                    "Record this recommendation in your final response instead."
                ),
            }

    comp_prefix = "ds" if component == "dsm" else "dh"
    endpoint = f"trackme/v2/splk_{component}/write/{comp_prefix}_monitoring"

    result = _call_trackme_api(service, endpoint, body={
        "tenant_id": tenant_id,
        "object_id": object_id,
        "monitored_state": monitored_state,
        "update_comment": f"[AI Feed Lifecycle Advisor] {reason}",
    })

    return {
        "success": not _api_error(result),
        "object_id": object_id,
        "monitored_state": monitored_state,
        "reason": reason,
        "response": result,
    }


@registry.tool(name="update_entity_adaptive_delay", tags=["lifecycle_write"])
def update_entity_adaptive_delay(
    tenant_id: str,
    component: str,
    object_id: str,
    allow_adaptive_delay: str,
    reason: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Lock or unlock a DSM/DHM entity's delay/latency thresholds.

    The threshold lock is the single, authoritative control for how TrackMe
    manages an entity's thresholds. When LOCKED, TrackMe will NOT automatically
    adjust them (adaptive delay AND lagging classes are bypassed) and a reconcile
    routine restores the operator's values if anything changes them. Use this when
    an entity has manually-tuned thresholds that should not be overridden.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm" or "dhm"
        object_id: The entity's _key hash in KV Store
        allow_adaptive_delay: "false" to LOCK the thresholds (stop auto-adjustment),
            "true" to UNLOCK (let TrackMe auto-manage them). The parameter name is
            kept for backwards compatibility; it maps directly to the lock.
        reason: Your explanation for this change

    NOTE: Setting allow_adaptive_delay to 'false' (i.e. LOCKING) is the typical
    recommendation when automation has been frequently overriding manual threshold
    configurations.
    """
    service = _get_trackme_service(ctx)

    if allow_adaptive_delay not in ("true", "false"):
        return {"success": False, "error": f"Invalid allow_adaptive_delay '{allow_adaptive_delay}'. Must be 'true' or 'false'"}

    comp_prefix = "ds" if component == "dsm" else "dh"
    endpoint = f"trackme/v2/splk_{component}/write/{comp_prefix}_update_lag_policy"

    # Unified lock: allow_adaptive_delay='false' => LOCK the thresholds. We send
    # lock_threshold (the authoritative control); the backend orchestrates the
    # legacy allow_adaptive_delay / lagging-class flags from it, and records the
    # intent ledger so reconcile protects the values.
    lock_threshold = "true" if allow_adaptive_delay == "false" else "false"

    result = _call_trackme_api(service, endpoint, body={
        "tenant_id": tenant_id,
        "keys_list": object_id,
        "lock_threshold": lock_threshold,
        "update_comment": f"[AI Feed Lifecycle Advisor] {reason}",
    })

    return {
        "success": not _api_error(result),
        "object_id": object_id,
        "allow_adaptive_delay": allow_adaptive_delay,
        "lock_threshold": lock_threshold,
        "reason": reason,
        "response": result,
    }


@registry.tool(name="update_entity_variable_delay", tags=["lifecycle_write"])
def update_entity_variable_delay(
    tenant_id: str,
    component: str,
    object_id: str,
    variable_delay_default: str,
    variable_delay_slots: str,
    reason: str,
    variable_delay_enabled: str = "true",
    ctx: ToolContext = None,
) -> dict:
    """
    Create or update the variable delay schedule for a DSM/DHM entity.

    This is the ONLY tool that affects the active delay threshold when an
    entity uses ``variable_delay_policy="variable"``. The static
    ``data_max_delay_allowed`` field is INERT under variable policy —
    calling ``update_entity_thresholds`` to modify it will be rejected by
    that tool's runtime guard with a ``redirect_tool`` hint pointing
    here. Use this tool to:

    - Switch a ``static``-policy entity to ``variable`` policy
      (create slot config).
    - Adjust existing slot thresholds for an entity already on
      ``variable`` policy.

    If the entity also has a ``lag_threshold_breached`` /
    ``latency_threshold_breached`` anomaly, that is a SEPARATE concern:
    lag thresholds are always static. Make a second call to
    ``update_entity_thresholds`` with ``data_max_lag_allowed`` only.

    Variable delay allows different delay thresholds for different times of day/week —
    e.g., higher thresholds on weekends or at night when data arrives more slowly.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm" or "dhm"
        object_id: The entity's _key hash in KV Store
        variable_delay_default: Fallback threshold in seconds when no slot matches (e.g., "3600")
        variable_delay_slots: JSON string defining time slots. Format:
            '{"slots": [
                {"slot_name": "business_hours", "days": [0,1,2,3,4], "hours": [8,9,10,11,12,13,14,15,16,17], "max_delay_allowed": 3600},
                {"slot_name": "nights_and_weekends", "days": [5,6], "hours": [0,1,2,3,4,5,6,7,18,19,20,21,22,23], "max_delay_allowed": 86400}
            ]}'
            Days: 0=Monday, 1=Tuesday, ..., 5=Saturday, 6=Sunday
            Hours: 0-23 (UTC)
        reason: Your explanation for why this schedule is appropriate
        variable_delay_enabled: "true" (default) to activate the schedule

    After setting variable delay, TrackMe automatically sets variable_delay_policy='variable'
    and allow_adaptive_delay='false' on the entity.
    """
    service = _get_trackme_service(ctx)

    # Validate variable_delay_slots is valid JSON
    try:
        slots_parsed = json.loads(variable_delay_slots)
        if "slots" not in slots_parsed:
            return {"success": False, "error": "variable_delay_slots must contain a 'slots' key"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON in variable_delay_slots: {e}"}

    result = _call_trackme_api(
        service,
        "trackme/v2/splk_variable_delay/write/set",
        body={
            "tenant_id": tenant_id,
            "component": component,
            "object_id": object_id,
            "variable_delay_enabled": variable_delay_enabled,
            "variable_delay_mode": "manual",
            "variable_delay_default": variable_delay_default,
            "variable_delay_slots": variable_delay_slots,
            "update_comment": f"[AI Feed Lifecycle Advisor] {reason}",
        },
    )

    return {
        "success": not _api_error(result),
        "object_id": object_id,
        "variable_delay_default": variable_delay_default,
        "slots_count": len(slots_parsed.get("slots", [])),
        "reason": reason,
        "response": result,
    }


@registry.tool(name="update_entity_priority_and_tags", tags=["lifecycle_write"])
def update_entity_priority_and_tags(
    tenant_id: str,
    component: str,
    object_id: str,
    reason: str,
    priority: str = "",
    tags: str = "",
    ctx: ToolContext = None,
) -> dict:
    """
    Update the priority and/or manual tags for a DSM/DHM entity.

    At least one of priority or tags must be provided.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm" or "dhm"
        object_id: The entity's _key hash in KV Store
        reason: Your explanation for the change
        priority: New priority level: "critical", "high", "medium", "low", or "pending"
            Leave empty to keep current priority.
        tags: Comma-separated tags to set (e.g., "lifecycle:stale,reviewed:2026-03")
            Leave empty to keep current tags.

    Use priority adjustment when an entity's monitoring criticality doesn't match
    its actual data importance.
    """
    service = _get_trackme_service(ctx)

    valid_priorities = {"critical", "high", "medium", "low", "pending", ""}
    if priority and priority not in valid_priorities:
        return {"success": False, "error": f"Invalid priority '{priority}'. Must be one of: critical, high, medium, low, pending"}

    comp_prefix = "ds" if component == "dsm" else "dh"
    results = {}

    if priority:
        priority_endpoint = f"trackme/v2/splk_{component}/write/{comp_prefix}_update_priority"
        priority_result = _call_trackme_api(service, priority_endpoint, body={
            "tenant_id": tenant_id,
            "keys_list": object_id,
            "priority": priority,
            "update_comment": f"[AI Feed Lifecycle Advisor] {reason}",
        })
        results["priority_update"] = priority_result

    if tags:
        tags_endpoint = f"trackme/v2/splk_{component}/write/{comp_prefix}_update_manual_tags"
        tags_result = _call_trackme_api(service, tags_endpoint, body={
            "tenant_id": tenant_id,
            "keys_list": object_id,
            "tags_manual": tags,
            "update_comment": f"[AI Feed Lifecycle Advisor] {reason}",
        })
        results["tags_update"] = tags_result

    if not results:
        return {"success": False, "error": "At least one of priority or tags must be provided"}

    has_error = any(r.get("error") for r in results.values())
    return {
        "success": not has_error,
        "object_id": object_id,
        "priority": priority,
        "tags": tags,
        "reason": reason,
        "results": results,
    }


@registry.tool(name="update_entity_impact_score_weights", tags=["lifecycle_write"])
def update_entity_impact_score_weights(
    tenant_id: str,
    component: str,
    object_id: str,
    reason: str,
    delay_weight: int = -1,
    latency_weight: int = -1,
    ctx: ToolContext = None,
) -> dict:
    """
    Adjust the per-entity impact score weights for delay and/or latency breaches.

    Impact score weights control how much a delay or latency threshold breach
    contributes to the entity's total score (0-100). The entity goes RED when
    total_score >= 100. Reducing a weight lowers the impact of that specific
    threshold breach on the overall alert state.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm" or "dhm"
        object_id: The entity's _key hash in KV Store
        reason: Your explanation for the weight adjustment
        delay_weight: New delay impact score weight (0-100). Use -1 to keep current.
            0 = disable delay score contribution, 100 = maximum contribution.
        latency_weight: New latency impact score weight (0-100). Use -1 to keep current.

    Use this to fine-tune alert sensitivity without changing the threshold values.
    For example, reducing delay_weight from 100 to 50 means the entity needs
    both delay AND latency to breach to reach RED state.

    NOTE: At least one of delay_weight or latency_weight must be >= 0.
    """
    service = _get_trackme_service(ctx)

    weights = {}
    if delay_weight >= 0:
        if not (0 <= delay_weight <= 100):
            return {"success": False, "error": f"delay_weight must be 0-100, got {delay_weight}"}
        weights["delay"] = delay_weight
    if latency_weight >= 0:
        if not (0 <= latency_weight <= 100):
            return {"success": False, "error": f"latency_weight must be 0-100, got {latency_weight}"}
        weights["latency"] = latency_weight

    if not weights:
        return {"success": False, "error": "At least one of delay_weight or latency_weight must be >= 0"}

    comp_prefix = "ds" if component == "dsm" else "dh"
    endpoint = f"trackme/v2/splk_{component}/write/{comp_prefix}_update_lag_policy"

    result = _call_trackme_api(service, endpoint, body={
        "tenant_id": tenant_id,
        "keys_list": object_id,
        "impact_score_weights": json.dumps(weights),
        "update_comment": f"[AI Feed Lifecycle Advisor] {reason}",
    })

    return {
        "success": not _api_error(result),
        "object_id": object_id,
        "impact_score_weights": weights,
        "reason": reason,
        "response": result,
    }


# ===========================================================================
# LAGGING CLASS TOOLS (DSM / DHM)
#
# Lagging classes are tenant-level rule policies that override entity-level
# delay (and optionally lag) thresholds when their match pattern hits an
# entity. The match runs per-cycle inside the per-tenant decision maker;
# every entity record carries the resulting assignment under
# ``lagging_class_assignment`` (matched flag, name, level, match_mode,
# delay_mode, key) so the advisor can see precedence at a glance — see
# ``get_entity_lifecycle_context`` and the LAGGING CLASSES section of the
# Feed Lifecycle Advisor system prompt for the full precedence chain.
#
# These tools wrap the existing ``/splk_lagging_classes/*`` REST endpoints
# in the shape the agent SDK consumes: every required option of the REST
# contract is a named keyword argument with type-checked validation, so the
# LLM can call them safely without re-deriving the endpoint schema from
# the system prompt.
#
# All tools here are scoped to ``events`` lagging classes (DSM / DHM).
# MHM ``metrics`` lagging classes exist on the same endpoints but are out
# of scope for the Feed Lifecycle Advisor (MHM is owned by the Component
# Health Advisor).
# ===========================================================================


@registry.tool(name="get_lagging_classes", tags=["lifecycle_read"])
def get_lagging_classes(
    tenant_id: str,
    component: str,
    ctx: ToolContext = None,
) -> dict:
    """
    List every lagging class defined for the given tenant + component.

    Returns the full set of class records (name, level, match_mode,
    delay_mode, static value_delay OR variable_delay_default+slots,
    optional value_lag, comment, _key). Use this BEFORE recommending
    or applying any threshold remediation on an entity that has
    ``lagging_class_assignment.matched=true`` — without seeing the
    class definition you can't reason about whether to update the
    class, flip the entity's override, or live with the precedence.

    Parameters:
        tenant_id: The tenant identifier
        component: "dsm" or "dhm" (events scope). MHM is out of scope.

    Returns:
        {"lagging_classes": [...], "count": N} on success
        {"lagging_classes": [], "count": 0, "error": ...} on failure
    """
    if component not in ("dsm", "dhm"):
        return {
            "lagging_classes": [],
            "count": 0,
            "error": f'invalid component="{component}" — must be "dsm" or "dhm"',
        }

    service = _get_trackme_service(ctx)
    result = _call_trackme_api(
        service,
        "trackme/v2/splk_lagging_classes/lagging_classes_show",
        body={
            "tenant_id": tenant_id,
            "lagging_class_type": "events",
            "component": component,
        },
    )

    # Error-result detection MUST guard against the response being a list
    # before calling ``.get("error")`` — the lagging_classes_show endpoint
    # returns a list (often empty) when classes exist OR when none are
    # defined, and an unconditional ``result.get("error")`` raises
    # ``AttributeError: 'list' object has no attribute 'get'`` on tenants
    # that haven't configured any lagging classes yet (the production
    # symptom reported on PR #1812's runtime, fixed in PR #1823).
    #
    # PR #1824 routes the check through the centralised ``_api_error()``
    # helper (defined in trackme_ai_agent_tools.py) so every tool in
    # every file goes through the same defensive guard. The tenant_id /
    # component fields are carried into the error return for parity
    # with the success return shape (CodeRabbit PR #1823 consistency
    # note) — gives the LLM the full context regardless of which path
    # the tool took.
    if _api_error(result) is not None:
        return {
            "lagging_classes": [],
            "count": 0,
            "tenant_id": tenant_id,
            "component": component,
            "error": result.get("error"),
            "api_response": result,
        }

    # The REST endpoint returns the records under varying shapes
    # depending on whether records exist; normalise to a flat list.
    records = []
    if isinstance(result, list):
        records = result
    elif isinstance(result, dict):
        # Common shapes: {"records": [...]} or just the list under
        # a top-level key.
        for key in ("records", "lagging_classes", "results"):
            if isinstance(result.get(key), list):
                records = result[key]
                break
        # Otherwise: maybe the dict IS the single record (unlikely
        # but defensive).
        if not records and "_key" in result:
            records = [result]

    return {
        "lagging_classes": records,
        "count": len(records),
        "tenant_id": tenant_id,
        "component": component,
    }


def _validate_lagging_class_write_args(
    component: str,
    level: str,
    match_mode: str,
    delay_mode: str,
    value_delay: str,
    variable_delay_default: str,
    variable_delay_slots,
) -> dict | None:
    """Shared validation for create_lagging_class / update_lagging_class.

    Returns None on success, or a dict ``{"success": False, "error": ...}``
    structured-error suitable for direct return from a tool when any
    argument violates the REST endpoint's contract. Mirrors the checks
    the REST handler performs server-side so the advisor sees a
    consistent error shape regardless of which layer rejects.
    """
    if component not in ("dsm", "dhm"):
        return {
            "success": False,
            "error": f'invalid component="{component}" — must be "dsm" or "dhm"',
        }
    if level not in ("sourcetype", "index", "priority"):
        return {
            "success": False,
            "error": f'invalid level="{level}" — must be "sourcetype", "index", or "priority"',
        }
    if match_mode not in ("exact", "wildcard", "regex"):
        return {
            "success": False,
            "error": f'invalid match_mode="{match_mode}" — must be "exact", "wildcard", or "regex"',
        }
    if delay_mode not in ("static", "variable"):
        return {
            "success": False,
            "error": f'invalid delay_mode="{delay_mode}" — must be "static" or "variable"',
        }
    if delay_mode == "static":
        try:
            int(value_delay)
        except (TypeError, ValueError):
            return {
                "success": False,
                "error": (
                    "value_delay is required and must be an integer (seconds) "
                    'when delay_mode="static"'
                ),
            }
    else:  # variable
        try:
            int(variable_delay_default)
        except (TypeError, ValueError):
            return {
                "success": False,
                "error": (
                    "variable_delay_default is required and must be an integer "
                    '(seconds) when delay_mode="variable"'
                ),
            }
        if not variable_delay_slots:
            return {
                "success": False,
                "error": (
                    "variable_delay_slots is required when delay_mode=\"variable\"; "
                    "pass the slot configuration as a JSON object or pre-serialised "
                    "JSON string matching the {\"slots\": [...]} shape used by "
                    "update_entity_variable_delay"
                ),
            }
    return None


@registry.tool(name="create_lagging_class", tags=["lifecycle_write"])
def create_lagging_class(
    tenant_id: str,
    component: str,
    name: str,
    level: str,
    match_mode: str,
    reason: str,
    delay_mode: str = "static",
    value_delay: str = "",
    variable_delay_default: str = "",
    variable_delay_slots: str = "",
    value_lag: str = "",
    comment: str = "",
    ctx: ToolContext = None,
) -> dict:
    """
    Create a new lagging class for ``dsm`` or ``dhm``.

    A lagging class is a rule policy that overrides entity-level
    delay thresholds for every entity whose ``level`` value matches
    its ``name`` pattern under the given ``match_mode``. Use this when
    multiple entities share the same operational behaviour and you
    want a single tunable threshold for them all (e.g. all
    ``priority="critical"`` entities should share a 9000s
    business-hours threshold).

    Parameters:
        tenant_id: The tenant identifier.
        component: "dsm" or "dhm".
        name: The pattern to match against ``level``. For ``match_mode="exact"``
            this is the literal value (e.g. ``"critical"`` for level=priority);
            for ``"wildcard"`` use ``*`` glob (e.g. ``"linux:*"``); for
            ``"regex"`` use a Python regex (validated server-side at create
            time — invalid patterns are rejected).
        level: Which entity field this class matches against:
            ``"sourcetype"`` | ``"index"`` | ``"priority"``.
        match_mode: ``"exact"`` | ``"wildcard"`` | ``"regex"``.
        reason: Operator-facing rationale for creating this class. Lands
            in the audit log as ``[AI Feed Lifecycle Advisor] <reason>``.
        delay_mode: ``"static"`` (default) — single ``value_delay`` applies
            24/7; or ``"variable"`` — time-slot schedule via
            ``variable_delay_default`` + ``variable_delay_slots``.
        value_delay: Delay threshold in seconds. Required when
            ``delay_mode="static"``.
        variable_delay_default: Fallback delay (seconds) for slots not
            otherwise covered. Required when ``delay_mode="variable"``.
        variable_delay_slots: Slot schedule as a JSON object or
            pre-serialised JSON string. Same shape used by
            ``update_entity_variable_delay`` — ``{"slots": [{slot_name,
            days, hours, max_delay_allowed}, ...]}``. Required when
            ``delay_mode="variable"``.
        value_lag: OPTIONAL lag threshold in seconds. When set, the class
            also overrides the entity-level ``data_max_lag_allowed``. Leave
            empty to NOT override lag (delay-only class).
        comment: OPTIONAL free-text comment stored on the class record
            (visible in the lagging-classes management UI).

    IMPORTANT:
    - A class match SILENTLY OVERRIDES every targeted entity's delay
      threshold unless that entity's threshold is LOCKED (the locked
      entity's own pinned values win over the class; locking is what sets
      the underlying ``data_override_lagging_class`` flag). Before creating
      a class, call ``get_lagging_classes`` first to check there's no
      existing class that would conflict.
    - The class match is computed by the per-tenant decision maker on
      its next cycle (~5 min). Newly-matched entities won't reflect the
      override until that cycle runs.
    """
    err = _validate_lagging_class_write_args(
        component, level, match_mode, delay_mode, value_delay,
        variable_delay_default, variable_delay_slots,
    )
    if err is not None:
        return err

    if value_lag:
        try:
            int(value_lag)
        except (TypeError, ValueError):
            return {
                "success": False,
                "error": "value_lag must be an integer (seconds) when provided",
            }

    service = _get_trackme_service(ctx)

    body = {
        "tenant_id": tenant_id,
        "component": component,
        "name": name,
        "level": level,
        "match_mode": match_mode,
        "delay_mode": delay_mode,
        "update_comment": f"[AI Feed Lifecycle Advisor] {reason}",
    }
    if delay_mode == "static":
        body["value_delay"] = str(value_delay)
    else:
        body["variable_delay_default"] = str(variable_delay_default)
        # The REST endpoint accepts the slots as either a JSON string or
        # a dict — normalise to a JSON string so the wire payload is
        # consistent with what the UI sends.
        if isinstance(variable_delay_slots, (dict, list)):
            body["variable_delay_slots"] = json.dumps(variable_delay_slots)
        else:
            body["variable_delay_slots"] = str(variable_delay_slots)
    if value_lag:
        body["value_lag"] = str(value_lag)
    if comment:
        body["comment"] = comment

    result = _call_trackme_api(
        service,
        "trackme/v2/splk_lagging_classes/write/lagging_classes_add",
        body=body,
    )

    return {
        "success": not _api_error(result),
        "tenant_id": tenant_id,
        "component": component,
        "name": name,
        "level": level,
        "match_mode": match_mode,
        "delay_mode": delay_mode,
        "reason": reason,
        "api_response": result,
    }


@registry.tool(name="update_lagging_class", tags=["lifecycle_write"])
def update_lagging_class(
    tenant_id: str,
    component: str,
    lagging_class_key: str,
    reason: str,
    name: str = "",
    level: str = "",
    match_mode: str = "",
    delay_mode: str = "",
    value_delay: str = "",
    variable_delay_default: str = "",
    variable_delay_slots: str = "",
    value_lag: str = "",
    comment: str = "",
    ctx: ToolContext = None,
) -> dict:
    """
    Update an existing lagging class in place.

    Use this when an entity is RED because a lagging class threshold
    is too tight (the class delay/lag is below the observed p95).
    Loosening the class fixes ALL entities matched by it in one
    write, instead of opting each entity out individually via
    ``set_entity_lagging_class_override``.

    Parameters:
        tenant_id: The tenant identifier.
        component: "dsm" or "dhm".
        lagging_class_key: The class's ``_key`` (SHA256). Get it from
            ``get_lagging_classes`` or from
            ``lagging_class_assignment.key`` on the entity context.
        reason: Operator-facing rationale. Lands in audit log as
            ``[AI Feed Lifecycle Advisor] <reason>``.

    All other parameters are OPTIONAL — pass only the fields you want
    to change. Field semantics match ``create_lagging_class``. If you
    change ``delay_mode``, you MUST also pass the fields the new mode
    requires (e.g. switching ``static`` → ``variable`` needs both
    ``variable_delay_default`` and ``variable_delay_slots``).

    IMPORTANT:
    - The class's match takes effect on the next decision-maker cycle
      (~5 min); existing matched entities will see the new threshold
      then.
    """
    if not lagging_class_key:
        return {
            "success": False,
            "error": "lagging_class_key is required — obtain it from get_lagging_classes",
        }
    if component not in ("dsm", "dhm"):
        return {
            "success": False,
            "error": f'invalid component="{component}" — must be "dsm" or "dhm"',
        }

    # Build the partial record. The update endpoint accepts a
    # records_list of dicts each carrying _key + the fields to mutate.
    record: dict = {"_key": lagging_class_key}
    if name:
        record["name"] = name
    if level:
        if level not in ("sourcetype", "index", "priority"):
            return {
                "success": False,
                "error": f'invalid level="{level}" — must be "sourcetype", "index", or "priority"',
            }
        record["level"] = level
    if match_mode:
        if match_mode not in ("exact", "wildcard", "regex"):
            return {
                "success": False,
                "error": (
                    f'invalid match_mode="{match_mode}" — must be "exact", "wildcard", '
                    'or "regex"'
                ),
            }
        record["match_mode"] = match_mode
    if delay_mode:
        if delay_mode not in ("static", "variable"):
            return {
                "success": False,
                "error": f'invalid delay_mode="{delay_mode}" — must be "static" or "variable"',
            }
        record["delay_mode"] = delay_mode
    if value_delay:
        try:
            int(value_delay)
        except (TypeError, ValueError):
            return {
                "success": False,
                "error": "value_delay must be an integer (seconds) when provided",
            }
        record["value_delay"] = str(value_delay)
    if variable_delay_default:
        try:
            int(variable_delay_default)
        except (TypeError, ValueError):
            return {
                "success": False,
                "error": "variable_delay_default must be an integer (seconds) when provided",
            }
        record["variable_delay_default"] = str(variable_delay_default)
    if variable_delay_slots:
        if isinstance(variable_delay_slots, (dict, list)):
            record["variable_delay_slots"] = json.dumps(variable_delay_slots)
        else:
            record["variable_delay_slots"] = str(variable_delay_slots)
    if value_lag:
        try:
            int(value_lag)
        except (TypeError, ValueError):
            return {
                "success": False,
                "error": "value_lag must be an integer (seconds) when provided",
            }
        record["value_lag"] = str(value_lag)
    if comment:
        record["comment"] = comment

    if len(record) == 1:  # only _key, nothing to update
        return {
            "success": False,
            "error": (
                "no fields to update — pass at least one of name, level, "
                "match_mode, delay_mode, value_delay, variable_delay_default, "
                "variable_delay_slots, value_lag, or comment"
            ),
        }

    service = _get_trackme_service(ctx)
    result = _call_trackme_api(
        service,
        "trackme/v2/splk_lagging_classes/write/lagging_classes_update",
        body={
            "tenant_id": tenant_id,
            "lagging_class_type": "events",
            "component": component,
            "records_list": json.dumps([record]),
            "update_comment": f"[AI Feed Lifecycle Advisor] {reason}",
        },
    )

    return {
        "success": not _api_error(result),
        "tenant_id": tenant_id,
        "component": component,
        "lagging_class_key": lagging_class_key,
        "updated_fields": [k for k in record if k != "_key"],
        "reason": reason,
        "api_response": result,
    }


@registry.tool(name="delete_lagging_class", tags=["lifecycle_write"])
def delete_lagging_class(
    tenant_id: str,
    component: str,
    lagging_class_key: str,
    reason: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Delete a lagging class.

    DESTRUCTIVE. Every entity previously matched by this class will
    fall back to its entity-level thresholds on the next decision-
    maker cycle (~5 min). If those entity-level thresholds are
    appropriate, this is fine — but if the class was the ONLY thing
    keeping those entities GREEN, expect a wave of RED state changes.

    Use ``update_lagging_class`` to loosen the threshold instead when
    the class itself is too tight. Use this tool only when the class
    is genuinely obsolete (e.g. a deprecated sourcetype pattern with
    zero current matches, or a class superseded by a different
    matching strategy).

    Parameters:
        tenant_id: The tenant identifier.
        component: "dsm" or "dhm".
        lagging_class_key: The class's ``_key`` from
            ``get_lagging_classes``.
        reason: Operator-facing rationale. Lands in the audit log as
            ``[AI Feed Lifecycle Advisor] <reason>``.

    IMPORTANT:
    - Before deleting, call ``get_lagging_classes`` and confirm which
      class you're targeting by name + level + match_mode.
    - Consider whether existing matched entities will be left
      stranded with inappropriate thresholds.
    """
    if not lagging_class_key:
        return {
            "success": False,
            "error": "lagging_class_key is required — obtain it from get_lagging_classes",
        }
    if component not in ("dsm", "dhm"):
        return {
            "success": False,
            "error": f'invalid component="{component}" — must be "dsm" or "dhm"',
        }

    service = _get_trackme_service(ctx)
    result = _call_trackme_api(
        service,
        "trackme/v2/splk_lagging_classes/write/lagging_classes_del",
        body={
            "tenant_id": tenant_id,
            "lagging_class_type": "events",
            "component": component,
            "records_list": json.dumps([lagging_class_key]),
            "update_comment": f"[AI Feed Lifecycle Advisor] {reason}",
        },
    )

    return {
        "success": not _api_error(result),
        "tenant_id": tenant_id,
        "component": component,
        "lagging_class_key": lagging_class_key,
        "reason": reason,
        "api_response": result,
    }


@registry.tool(name="set_entity_lagging_class_override", tags=["lifecycle_write"])
def set_entity_lagging_class_override(
    tenant_id: str,
    component: str,
    object_id: str,
    override: bool,
    reason: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Lock or unlock an entity's delay/latency thresholds (unified threshold lock).

    When ``override=True``, the entity is **LOCKED**: its own thresholds win, the
    matched lagging class is bypassed AND adaptive auto-management is disabled, and
    a reconcile routine restores the values if anything changes them. Use this when
    the entity needs manually-pinned thresholds that differ from its peers and must
    not be auto-adjusted.

    When ``override=False``, the entity is **UNLOCKED** and returns to the normal
    auto-managed path (lagging classes / adaptive delay — the tenant default for
    newly-created entities).

    NOTE: ``override`` maps directly to the threshold lock (``lock_threshold``); the
    parameter name is kept for backwards compatibility. This is BROADER than a
    class-only change — locking also disables adaptive delay.

    Parameters:
        tenant_id: The tenant identifier.
        component: "dsm" or "dhm".
        object_id: The entity's _key.
        override: ``True`` to LOCK the entity (pin its thresholds, no auto-adjust);
            ``False`` to UNLOCK (return to the auto-managed path).
        reason: Operator-facing rationale. Lands in audit log as
            ``[AI Feed Lifecycle Advisor] <reason>``.

    DECISION GUIDE — when to use this vs ``update_lagging_class``:
    - Use ``update_lagging_class`` when the class threshold is wrong
      for EVERY matched entity (typical case — same operational
      regime).
    - Use this tool only for the SPECIFIC entity that needs to differ
      from its peers (rare; usually a temporary divergence). Document
      the divergence in ``reason``.
    """
    if component not in ("dsm", "dhm"):
        return {
            "success": False,
            "error": f'invalid component="{component}" — must be "dsm" or "dhm"',
        }

    service = _get_trackme_service(ctx)

    # Unified lock: "entity thresholds win over the class" (override=True) maps to
    # LOCKING the entity; "defer to the class" (override=False) maps to UNLOCKING
    # (auto-managed). Send lock_threshold (the authoritative control); the backend
    # orchestrates the legacy override / adaptive flags and records the intent
    # ledger so reconcile protects the values. Same update_lag_policy endpoint.
    comp_prefix = "ds" if component == "dsm" else "dh"
    endpoint = f"trackme/v2/splk_{component}/write/{comp_prefix}_update_lag_policy"

    lock_threshold = "true" if override else "false"

    result = _call_trackme_api(
        service,
        endpoint,
        body={
            "tenant_id": tenant_id,
            "keys_list": object_id,
            "lock_threshold": lock_threshold,
            "update_comment": f"[AI Feed Lifecycle Advisor] {reason}",
        },
    )

    return {
        "success": not _api_error(result),
        "tenant_id": tenant_id,
        "component": component,
        "object_id": object_id,
        "lock_threshold": lock_threshold,
        "reason": reason,
        "api_response": result,
    }


# ===========================================================================
# Data Sampling write tools (DSM only) — Phase 2 of issue #1901
# ===========================================================================
#
# These tools let the advisor mutate the per-tenant custom data-sampling
# model collection (``kv_trackme_dsm_data_sampling_custom_models_tenant_<tid>``)
# via the existing power-scope REST handlers. They are the act-mode
# counterpart to the Phase 1 readers (``get_entity_data_sampling_state`` /
# ``get_data_sampling_models``).
#
# Discipline (mirrors the lagging-class write-tool pattern, see system
# prompt § DATA SAMPLING WRITE-TOOL DISCIPLINE):
#
#   * BEFORE proposing an add: call ``get_data_sampling_models`` to enumerate
#     OOTB + existing custom models. If the proposed pattern is already
#     covered by an OOTB or custom entry, recommend re-using it instead.
#   * BEFORE proposing an update: call ``get_data_sampling_models`` to see
#     the current record (including its ``_key``). The tool API takes
#     ``model_name`` for convenience; the underlying REST endpoint resolves
#     it to a ``_key`` server-side.
#   * BEFORE proposing a delete: confirm the model is custom (OOTB models
#     can't be deleted via this endpoint). Also confirm no entity currently
#     relies on this model as its sole matcher — surface that as a
#     recommendation rather than blocking, since the act-decision is the
#     operator's.
#   * NEVER add or update a model just to silence an active alert without
#     surfacing the root-cause analysis in ``reason``. Audit trail clarity
#     matters; the same lesson as the lagging-class discipline.
#   * ``reason`` is mandatory on every write — it lands in the audit log
#     (``update_comment`` field on the REST endpoint) so operators can see
#     why the advisor changed things.
# ===========================================================================


@registry.tool(name="add_data_sampling_model", tags=["lifecycle_write"])
def add_data_sampling_model(
    tenant_id: str,
    model_name: str,
    model_regex: str,
    model_type: str,
    reason: str,
    sourcetype_scope: str = "*",
    ctx: ToolContext = None,
) -> dict:
    """
    Add a new custom data-sampling model for the given tenant (DSM only).

    Custom models extend the OOTB built-in format models with site-specific
    patterns (e.g. a proprietary log format that none of the OOTB regexes
    cover). Once added, the next data-sampling iteration will fit the new
    model against sampled events and surface it under
    ``matched_model_summary`` in the entity's data-sampling state.

    The advisor SHOULD call ``get_data_sampling_models`` first to check
    whether the proposed pattern is already covered by an OOTB or custom
    entry — duplicate models clutter the audit trail without adding value.

    Parameters:
        tenant_id: The tenant identifier (DSM-enabled tenant only).
        model_name: Human-readable name for the new model. Must be unique
            within the tenant. Example: ``"netscreen_firewall"``.
        model_regex: The regular expression the model uses to fit sampled
            events. Special characters must be escaped according to Python
            re-module conventions (e.g. ``r":\\sNetScreen\\sdevice_id="``).
        model_type: Match semantics — one of:
            * ``"inclusive"`` — events MUST match this regex to count as
              "well-formed" for this sourcetype.
            * ``"exclusive"`` — events MUST NOT match this regex (a match
              indicates malformed / unexpected content).
        reason: REQUIRED. Your explanation for why this model is being
            added. Lands in the audit log via the underlying endpoint's
            ``update_comment`` field — operators read this to understand
            why the advisor acted. Example: ``"Coverage gap detected for
            netscreen:firewall sourcetype — no OOTB match"``.
        sourcetype_scope: Optional. Comma-separated sourcetype names this
            model applies to. Defaults to ``"*"`` (match all sourcetypes).
            Wildcards and spaces are NOT supported per the REST endpoint
            contract — use an exact match list (e.g.
            ``"netscreen:firewall,netscreen:vpn"``).

    Returns:
        {
          "success": True | False,
          "tenant_id": "<tid>",
          "model_name": "<name>",
          "model_type": "<type>",
          "sourcetype_scope": "<scope>",
          "reason": "<reason>",
          "api_response": <raw REST response>,
        }

        On REST error, ``success`` is False and ``error`` carries the
        message returned by the endpoint.
    """
    service = _get_trackme_service(ctx)

    # Argument validation — surface obvious mistakes before the REST call.
    valid_types = {"inclusive", "exclusive"}
    if model_type not in valid_types:
        return {
            "success": False,
            "error": (
                f"Invalid model_type {model_type!r} — must be one of "
                f"{sorted(valid_types)}"
            ),
            "tenant_id": tenant_id,
            "model_name": model_name,
            "reason": reason,
        }
    if not model_name:
        return {
            "success": False,
            "error": "model_name is required and must not be empty",
            "tenant_id": tenant_id,
            "reason": reason,
        }
    if not model_regex:
        return {
            "success": False,
            "error": "model_regex is required and must not be empty",
            "tenant_id": tenant_id,
            "model_name": model_name,
            "reason": reason,
        }
    if not _is_meaningful_reason(reason):
        return {
            "success": False,
            "error": _MEANINGFUL_REASON_ERROR,
            "tenant_id": tenant_id,
            "model_name": model_name,
        }

    body = {
        "tenant_id": tenant_id,
        "model_name": model_name,
        "model_regex": model_regex,
        "model_type": model_type,
        "sourcetype_scope": sourcetype_scope,
        "update_comment": f"[AI Feed Lifecycle Advisor] {reason}",
    }
    result = _call_trackme_api(
        service,
        "trackme/v2/splk_data_sampling/write/data_sampling_models_add",
        body=body,
    )
    err = _api_error(result)
    if err is not None:
        return {
            "success": False,
            "error": err,
            "tenant_id": tenant_id,
            "model_name": model_name,
            "reason": reason,
            "api_response": result,
        }
    return {
        "success": True,
        "tenant_id": tenant_id,
        "model_name": model_name,
        "model_type": model_type,
        "sourcetype_scope": sourcetype_scope,
        "reason": reason,
        "api_response": result,
    }


@registry.tool(name="update_data_sampling_model", tags=["lifecycle_write"])
def update_data_sampling_model(
    tenant_id: str,
    model_record: dict,
    reason: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Update an existing custom data-sampling model for the given tenant.

    The underlying REST endpoint operates on full records (the same shape
    returned by ``get_data_sampling_models``). The advisor MUST call
    ``get_data_sampling_models`` first to fetch the current record, mutate
    only the fields that need to change (``model_regex``, ``model_type``,
    ``sourcetype_scope``), and pass the resulting dict here as
    ``model_record``. The ``_key`` field on the record identifies which
    model to update.

    Updates apply to CUSTOM models only. OOTB models live outside the
    custom-models collection and can't be modified through this endpoint
    — proposing a change there should surface as a recommendation to add
    a new custom model that supersedes the OOTB behaviour for the tenant.

    Parameters:
        tenant_id: The tenant identifier.
        model_record: The full record dict with mutated fields. Must
            include the ``_key`` from the existing record (returned by
            ``get_data_sampling_models``). Other expected fields:
            ``model_name``, ``model_regex``, ``model_type``,
            ``sourcetype_scope``.
        reason: REQUIRED. Your explanation for why this model is being
            updated. Lands in the audit log via ``update_comment``.

    Returns:
        {
          "success": True | False,
          "tenant_id": "<tid>",
          "model_key": "<_key>",
          "model_name": "<name>",
          "reason": "<reason>",
          "api_response": <raw REST response>,
        }
    """
    service = _get_trackme_service(ctx)

    if not isinstance(model_record, dict):
        return {
            "success": False,
            "error": (
                "model_record must be a dict — call get_data_sampling_models "
                "to fetch the current record shape and mutate only the fields "
                "you need to change"
            ),
            "tenant_id": tenant_id,
            "reason": reason,
        }
    if not model_record.get("_key"):
        return {
            "success": False,
            "error": (
                "model_record must include a non-empty '_key' field — the "
                "REST endpoint uses it to identify which model to update"
            ),
            "tenant_id": tenant_id,
            "reason": reason,
        }
    if not _is_meaningful_reason(reason):
        return {
            "success": False,
            "error": _MEANINGFUL_REASON_ERROR,
            "tenant_id": tenant_id,
            "model_key": model_record.get("_key"),
        }

    body = {
        "tenant_id": tenant_id,
        # The endpoint takes ``records_list`` — a list (or list-like JSON)
        # of full records. We pass a single-element list to mutate one
        # model at a time; the agent's reasoning chain is clearer when
        # each call targets one record.
        "records_list": [model_record],
        "update_comment": f"[AI Feed Lifecycle Advisor] {reason}",
    }
    result = _call_trackme_api(
        service,
        "trackme/v2/splk_data_sampling/write/data_sampling_models_update",
        body=body,
    )
    err = _api_error(result)
    if err is not None:
        return {
            "success": False,
            "error": err,
            "tenant_id": tenant_id,
            "model_key": model_record.get("_key"),
            "model_name": model_record.get("model_name", ""),
            "reason": reason,
            "api_response": result,
        }
    return {
        "success": True,
        "tenant_id": tenant_id,
        "model_key": model_record.get("_key"),
        "model_name": model_record.get("model_name", ""),
        "reason": reason,
        "api_response": result,
    }


@registry.tool(name="delete_data_sampling_model", tags=["lifecycle_write"])
def delete_data_sampling_model(
    tenant_id: str,
    model_name: str,
    reason: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Delete a custom data-sampling model from the given tenant.

    Removes the named custom model from
    ``kv_trackme_dsm_data_sampling_custom_models_tenant_<tenant_id>``.
    Subsequent sampling iterations will no longer fit this model against
    sampled events, which may produce new ``data_sampling_anomaly`` reports
    for entities that depended on this model — the advisor SHOULD confirm
    via ``get_entity_data_sampling_state`` calls that the model isn't the
    sole matcher for any active entity before recommending its removal.

    Deletes apply to CUSTOM models only. OOTB models can't be removed via
    this endpoint (and shouldn't be — they're part of the TrackMe baseline).

    Parameters:
        tenant_id: The tenant identifier.
        model_name: The name of the custom model to delete (as returned by
            ``get_data_sampling_models`` under the ``custom`` list).
        reason: REQUIRED. Your explanation for why this model is being
            removed. Lands in the audit log via ``update_comment``.

    Returns:
        {
          "success": True | False,
          "tenant_id": "<tid>",
          "model_name": "<name>",
          "reason": "<reason>",
          "api_response": <raw REST response>,
        }
    """
    service = _get_trackme_service(ctx)

    if not model_name:
        return {
            "success": False,
            "error": "model_name is required and must not be empty",
            "tenant_id": tenant_id,
            "reason": reason,
        }
    if not _is_meaningful_reason(reason):
        return {
            "success": False,
            "error": _MEANINGFUL_REASON_ERROR,
            "tenant_id": tenant_id,
            "model_name": model_name,
        }

    body = {
        "tenant_id": tenant_id,
        # The endpoint accepts a comma-separated list OR a list — pass a
        # single name for the agent's one-model-at-a-time discipline.
        "models_list": model_name,
        "update_comment": f"[AI Feed Lifecycle Advisor] {reason}",
    }
    result = _call_trackme_api(
        service,
        "trackme/v2/splk_data_sampling/write/data_sampling_models_del",
        body=body,
    )
    err = _api_error(result)
    if err is not None:
        return {
            "success": False,
            "error": err,
            "tenant_id": tenant_id,
            "model_name": model_name,
            "reason": reason,
            "api_response": result,
        }
    return {
        "success": True,
        "tenant_id": tenant_id,
        "model_name": model_name,
        "reason": reason,
        "api_response": result,
    }


# ---------------------------------------------------------------------------
# Entry point: run as MCP tool server when executed directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    registry.run()
