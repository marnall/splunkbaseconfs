"""
TrackMe AI Agent Tools — FLX Threshold Advisor

Tool definitions for the Splunk Agent SDK, enabling the FLX Threshold Advisor
agent to inspect, analyze, and manage Flex Object entity threshold configurations.

Tools defined:
    READ (agent's "eyes"):
    1. get_flx_entity_context          — Full entity config, metrics, and threshold list
    2. get_flx_metric_history          — 30-day metric value history from summary index
    3. get_flx_threshold_breach_history — State transition and breach history
    4. get_flx_use_case_definition     — Use case definition from flx_library
    5. get_flx_peer_entity_thresholds  — Threshold calibration data from peer entities

    WRITE (agent's "hands"):
    6. add_flx_threshold               — Add a new dynamic threshold for a metric
    7. update_flx_threshold            — Recalibrate an existing threshold
    8. delete_flx_threshold            — Remove a misconfigured threshold
    9. set_flx_variable_threshold_slots — Configure time-slot based threshold variation
    10. update_flx_entity_state_priority — Update monitoring state or priority
"""

import json
import logging
import re
import sys
import os

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
    _get_metrics_index,
)

# Named logger — shares the singleton configured by the parent
# REST handler's setup_logger() call (root logger redirect there means
# `logging.<level>(...)` here would bleed across handlers).
logger = logging.getLogger("trackme.rest.ai.flx_threshold")


# ===========================================================================
# READ TOOLS (1-5)
# ===========================================================================


@registry.tool(tags=["flx_threshold_read"])
async def get_flx_entity_context(ctx: ToolContext, tenant_id: str, object_id: str) -> str:
    """
    Retrieve the full context of a FLX entity from the describe endpoint.

    Returns entity identity (tracker_name, group, flx_type, account), current
    metric values, all configured thresholds (including variable threshold slots),
    monitoring configuration, outlier model status, and current health state.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store

    Returns:
        JSON string with entity context including: tracker_name, flx_type, account,
        metrics (current values), thresholds (list of threshold records with variable
        slot configs), monitoring config, health state, anomaly reasons
    """
    service = _get_trackme_service(ctx)

    result = _call_trackme_api(
        service,
        "trackme/v2/describe/entity",
        body={
            "tenant_id": tenant_id,
            "object_category": "splk-flx",
            "object_id": object_id,
        },
        method="post",
    )

    if isinstance(result, dict) and result.get("error"):
        return json.dumps({
            "error": result.get("error"),
            "message": f"Failed to retrieve entity context for object_id={object_id} in tenant={tenant_id}",
        })

    if "entity_description" in result:
        desc = result["entity_description"]
        identity = desc.get("identity", {})
        config = desc.get("configuration", {})
        health = desc.get("health", {})
        thresholds = desc.get("thresholds", [])
        metrics = desc.get("metrics", {})

        entity_context = {
            "object_id": object_id,
            "object": identity.get("object", ""),
            "tenant_id": tenant_id,
            "tracker_name": identity.get("tracker_name", ""),
            "flx_type": identity.get("flx_type", ""),
            "account": identity.get("account", "local"),
            "group": identity.get("group", ""),
            "metrics": metrics,
            "thresholds": thresholds,
            "monitored_state": config.get("monitored_state", "unknown"),
            "priority": config.get("priority", "unknown"),
            "sla_class": config.get("sla_class", ""),
            "tags": config.get("tags_manual", ""),
            "current_state": health.get("object_state", "unknown"),
            "anomaly_reasons": health.get("anomaly_reasons", []),
            "is_outlier": health.get("isOutlier", 0),
            "outlier_readiness": health.get("outlier_readiness", False),
            "last_event_detected_time": identity.get("last_event_detected_time", ""),
            "last_ingest_time": identity.get("last_ingest_time", ""),
            "full_description": desc,
        }
        return json.dumps(entity_context)

    return json.dumps(result)


@registry.tool(tags=["flx_threshold_read"])
async def get_flx_metric_history(ctx: ToolContext, tenant_id: str, object_id: str) -> str:
    """
    Retrieve metric history for a FLX entity over the last 24 hours (detailed)
    and the last 7 days (aggregate), so the LLM can reason about whether the
    threshold values are calibrated against the metric's actual behaviour.

    Implementation
    --------------

    Runs two ``mstats`` searches against the tenant's metrics index (the
    same data path that drives the TrackMe UI charts and the stateful
    alert-action chart generator).

    1. **Query A — 24h + 7d aggregate stats** via two separate
       ``mstats`` searches merged in Python by ``metric_name``. One row
       per metric_name in the output, with 10 columns side-by-side
       (24h_latest_value / 24h_avg_value / 24h_max_value /
       24h_perc95_value / 24h_stdev_value, plus the same five for 7d).
       Lets the LLM spot drift between the latest 24h window and the
       weekly baseline at a glance. Splunk's ``appendcols`` was tried
       first but discarded: it does positional (row-number) matching,
       not key-based, so any difference in the two ``mstats`` row sets
       silently attached 7d stats to the wrong ``metric_name`` (PR
       #1530 cycle 1 finding).

    2. **Query B — per-metric 24h timeseries** at ``span=5m``, one search
       per metric_name discovered in Query A. Returns structured per-metric
       blocks so the LLM can spot plateaus, spikes, or ramps without having
       to demux interleaved rows itself.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash

    Returns:
        JSON string with:
        - ``aggregate_stats_24h_vs_7d``: array of {metric_name, 24h_*,
          7d_*} rows
        - ``timeseries_24h_per_metric``: dict mapping metric_name → list of
          {_time, value} buckets at 5-minute granularity

    Notes
    -----

    - FLX metrics are written to ``index=<metrics_idx>`` (per-tenant,
      defaults to ``trackme_metrics``) with ``object_category="splk-flx"``
      and ``metric_name="trackme.splk.flx.<short>"``. The internal
      ``trackme.splk.flx.status`` metric is filtered out.
    - The framework's ``earliest_time`` parameter passed to
      ``run_splunk_search`` is irrelevant here — the SPL itself sets the
      windows via ``earliest=-24h`` / ``earliest=-7d``.
    """
    service = _get_trackme_service(ctx)
    metrics_idx = _get_metrics_index(service, tenant_id)

    # Query A — 24h + 7d aggregate stats via TWO separate ``mstats``
    # searches merged in Python by metric_name.
    #
    # NB: a previous design used a single SPL with ``appendcols`` to
    # combine the two windows.  Splunk's ``appendcols`` does *positional*
    # (row-number) matching — not key-based — so if a metric exists in
    # one window but not the other (newly added or recently silenced
    # metric), or if the two ``mstats`` runs returned rows in different
    # orders, the 7d stats would be silently attached to the wrong
    # metric_name.  Bugbot caught this on PR #1530 cycle 1 (Medium).
    # Two queries + dict merge by ``metric_name`` is bulletproof and
    # costs at most a few hundred milliseconds extra.
    def _build_aggregate_spl(window):
        """Build an mstats aggregate over ``window`` (e.g. "24h", "7d").
        Column names are prefixed with the window for join-time clarity."""
        return (
            '| mstats '
            f'latest(_value) as {window}_latest_value, '
            f'avg(_value) as {window}_avg_value, '
            f'max(_value) as {window}_max_value, '
            f'perc95(_value) as {window}_perc95_value, '
            f'stdev(_value) as {window}_stdev_value '
            f'where index="{metrics_idx}" '
            'metric_name=trackme.splk.flx.* '
            'metric_name!=trackme.splk.flx.status '
            f'tenant_id="{tenant_id}" '
            'object_category="splk-flx" '
            f'object_id="{object_id}" '
            f'earliest=-{window} latest=now '
            'by index, object, metric_name'
        )

    search_params = {
        # SPL self-contains the windows; pick a small framework window so
        # job dispatch is cheap.
        "earliest_time": "-5m",
        "latest_time": "now",
        "output_mode": "json",
        "count": 0,
    }

    def _run_aggregate(window):
        rows = []
        try:
            for result in run_splunk_search(
                service,
                _build_aggregate_spl(window),
                search_params,
                max_retries=3,
            ):
                if isinstance(result, dict):
                    rows.append(result)
        except Exception as e:
            raise RuntimeError(f"{window} aggregate search failed: {str(e)}")
        return rows

    try:
        rows_24h = _run_aggregate("24h")
        rows_7d = _run_aggregate("7d")
    except RuntimeError as e:
        return json.dumps({
            "error": str(e),
            "suggestion": "Verify the tenant_id, object_id, and that the metrics index is reachable.",
            "metrics_index": metrics_idx,
        })

    # Merge the two windows by ``metric_name`` (the only field that
    # can join the rows safely — index and object are constants across
    # both queries anyway).  A metric present in one window but not the
    # other ends up with one half of the stats; the LLM sees the
    # asymmetry directly rather than wrong values.
    merged_by_metric = {}
    for row in rows_24h:
        mn = row.get("metric_name")
        if not mn:
            continue
        merged_by_metric.setdefault(mn, {
            "metric_name": mn,
            "index": row.get("index", ""),
            "object": row.get("object", ""),
        }).update({
            k: v for k, v in row.items()
            if k.startswith("24h_")
        })
    for row in rows_7d:
        mn = row.get("metric_name")
        if not mn:
            continue
        merged_by_metric.setdefault(mn, {
            "metric_name": mn,
            "index": row.get("index", ""),
            "object": row.get("object", ""),
        }).update({
            k: v for k, v in row.items()
            if k.startswith("7d_")
        })

    aggregate_rows = [merged_by_metric[mn] for mn in sorted(merged_by_metric.keys())]

    if not aggregate_rows:
        return json.dumps({
            "aggregate_stats_24h_vs_7d": [],
            "timeseries_24h_per_metric": {},
            "metrics_index": metrics_idx,
            "tenant_id": tenant_id,
            "object_id": object_id,
            "note": (
                "No metrics found for this entity in the last 7 days. The "
                "entity may be newly created, decommissioned, or the metrics "
                "collection path may be broken upstream."
            ),
        })

    # Discover the metric_name list from the merged aggregate so Query B
    # iterates one search per metric (clean per-metric grouping in the
    # response payload — easier for the LLM than demuxing interleaved
    # rows itself).
    metric_names = list(merged_by_metric.keys())

    timeseries_per_metric = {}
    for metric_name in metric_names:
        spl_timeseries = (
            '| mstats latest(_value) as value '
            f'where index="{metrics_idx}" '
            'metric_name=trackme.splk.flx.* '
            f'metric_name="{metric_name}" '
            f'tenant_id="{tenant_id}" '
            'object_category="splk-flx" '
            f'object_id="{object_id}" '
            'earliest=-24h latest=now '
            'by index, object, metric_name span=5m'
        )
        rows = []
        try:
            for result in run_splunk_search(service, spl_timeseries, search_params, max_retries=3):
                if isinstance(result, dict):
                    rows.append({
                        "_time": result.get("_time", ""),
                        "value": result.get("value", ""),
                    })
        except Exception as e:
            # Non-fatal — record the per-metric error and continue with
            # the others.  The LLM still gets aggregate stats + whatever
            # timeseries did succeed.
            timeseries_per_metric[metric_name] = {
                "error": f"Timeseries search failed: {str(e)}",
            }
            continue
        timeseries_per_metric[metric_name] = rows

    return json.dumps({
        "tenant_id": tenant_id,
        "object_id": object_id,
        "metrics_index": metrics_idx,
        "aggregate_stats_24h_vs_7d": aggregate_rows,
        "timeseries_24h_per_metric": timeseries_per_metric,
        "note": (
            "aggregate_stats_24h_vs_7d: one row per metric with 5 stats over "
            "the last 24h side-by-side with 5 stats over the last 7d. Use "
            "this to spot drift (e.g. 24h_perc95 much higher than 7d_avg). "
            "timeseries_24h_per_metric: 5-minute buckets per metric over the "
            "last 24h. Use this to spot plateaus / spikes / ramps."
        ),
    })


@registry.tool(tags=["flx_threshold_read"])
async def get_flx_threshold_breach_history(ctx: ToolContext, tenant_id: str, object_id: str, days: int = 30) -> str:
    """
    Retrieve state transition and threshold breach history for a FLX entity.

    Shows when the entity entered RED/ORANGE states, frequency of state changes,
    and (where available) which threshold breaches triggered the state change.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash
        days: Number of days of history (default: 30)

    Returns:
        JSON string with: state_transitions (list of flip events with timestamp,
        from_state, to_state), breach_count_by_state, anomaly_reason_history,
        and total_red_orange_periods
    """
    service = _get_trackme_service(ctx)

    capped_days = min(max(1, days), 90)
    summary_idx = _get_summary_index(service, tenant_id)
    audit_idx = _get_audit_index(service, tenant_id)

    # Summary index query for state overview by day-of-week
    spl_summary = (
        f'search index={summary_idx} sourcetype="trackme:flx:*" '
        f'tenant_id="{tenant_id}" object_id="{object_id}" earliest=-{capped_days}d@d '
        f'| eval day_of_week=strftime(_time, "%A") '
        f'| stats '
        f'count(eval(object_state="red")) as red_count, '
        f'count(eval(object_state="orange")) as orange_count, '
        f'values(anomaly_reason) as anomaly_reasons '
        f'by day_of_week '
        f'| sort day_of_week'
    )

    # Audit index query for state transitions
    spl_transitions = (
        f'search index={audit_idx} '
        f'tenant_id="{tenant_id}" '
        f'object_id="{object_id}" '
        f'change_type="state change" '
        f'| sort _time '
        f'| fields _time, previous_state, new_state, anomaly_reason '
        f'| head 100'
    )

    search_params = {
        "earliest_time": f"-{capped_days}d@d",
        "latest_time": "now",
        "output_mode": "json",
        "count": 0,
    }

    summary_data = []
    transitions = []
    total_reds = 0
    total_oranges = 0

    try:
        reader = run_splunk_search(service, spl_summary, search_params, max_retries=3)
        for result in reader:
            if isinstance(result, dict):
                try:
                    red_c = int(float(result.get("red_count", 0) or 0))
                    orange_c = int(float(result.get("orange_count", 0) or 0))
                    total_reds += red_c
                    total_oranges += orange_c
                    summary_data.append({
                        "day_of_week": result.get("day_of_week", ""),
                        "red_count": red_c,
                        "orange_count": orange_c,
                        "anomaly_reasons": result.get("anomaly_reasons", []),
                    })
                except (ValueError, TypeError):
                    continue
    except Exception as e:
        logger.warning(f"FLX breach history summary search failed: {e}")

    try:
        reader = run_splunk_search(service, spl_transitions, search_params, max_retries=3)
        for result in reader:
            if isinstance(result, dict):
                transitions.append({
                    "_time": result.get("_time", ""),
                    "from": result.get("previous_state", ""),
                    "to": result.get("new_state", ""),
                    "reason": result.get("anomaly_reason", ""),
                })
    except Exception as e:
        logger.warning(f"FLX breach history transitions search failed: {e}")

    return json.dumps({
        "tenant_id": tenant_id,
        "object_id": object_id,
        "days_queried": capped_days,
        "total_red_events": total_reds,
        "total_orange_events": total_oranges,
        "total_state_transitions": len(transitions),
        "breach_summary_by_day": summary_data,
        "recent_state_transitions": transitions[-50:],
    })


@registry.tool(tags=["flx_threshold_read"])
async def get_flx_use_case_definition(ctx: ToolContext, tracker_name: str) -> str:
    """
    Retrieve the use case definition for a FLX entity's tracker.

    For standard use cases (tracker_name matching a library entry), returns the
    full use case specification including search definition, expected metrics,
    vendor, category, and scheduling. For custom trackers, returns available
    hybrid tracker configuration.

    Args:
        tracker_name: The entity's tracker_name field value (normalized, without
                      'trackme_flx_hybrid_' prefix or '_tracker_tenant_X' suffix)

    Returns:
        JSON string with use case definition fields: uc_ref, uc_vendor, uc_description,
        uc_category, uc_metrics, uc_search, uc_cron, uc_earliest, uc_latest.
        If no standard definition found, returns custom tracker info or "unknown" status.
    """
    # Normalize tracker_name: remove prefix/suffix patterns
    normalized = tracker_name
    for prefix in ["trackme_flx_hybrid_", "trackme_flx_"]:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    # Remove tenant suffix pattern
    normalized = re.sub(r"_tracker_tenant_\w+$", "", normalized)

    # Security: reject path traversal sequences before building any file path
    if ".." in normalized or "/" in normalized or os.sep in normalized:
        return json.dumps({
            "found": False,
            "source": "unknown",
            "normalized_name": normalized,
            "error": "tracker_name contains invalid path characters",
            "definition": None,
        })

    lib_dir = os.path.join(os.path.dirname(__file__), "..", "lib", "flx_library")
    lib_dir_real = os.path.realpath(lib_dir)

    try:
        uc_file = os.path.join(lib_dir, f"{normalized}.json")
        # Second containment check via realpath (handles any residual traversal)
        if not os.path.realpath(uc_file).startswith(lib_dir_real + os.sep):
            return json.dumps({
                "found": False,
                "source": "unknown",
                "normalized_name": normalized,
                "error": "tracker_name resolves outside the use case library",
                "definition": None,
            })
        if os.path.isfile(uc_file):
            with open(uc_file, "r") as f:
                uc_def = json.load(f)
            return json.dumps({
                "found": True,
                "source": "standard_library",
                "normalized_name": normalized,
                "definition": uc_def,
            })
        else:
            # Return list of available standard UCs for context
            available = []
            if os.path.isdir(lib_dir):
                available = sorted([f.replace(".json", "") for f in os.listdir(lib_dir) if f.endswith(".json")])
            return json.dumps({
                "found": False,
                "source": "custom_tracker",
                "normalized_name": normalized,
                "original_tracker_name": tracker_name,
                "message": (
                    f"No standard library entry found for tracker '{normalized}'. "
                    "This is a custom tracker — analyze based on the entity's current metrics "
                    "and existing threshold configuration from get_flx_entity_context."
                ),
                "available_standard_trackers": available,
            })
    except Exception as e:
        return json.dumps({
            "error": f"Failed to read use case library: {str(e)}",
            "normalized_name": normalized,
            "original_tracker_name": tracker_name,
        })


@registry.tool(tags=["flx_threshold_read"])
async def get_flx_peer_entity_thresholds(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    tracker_name: str,
) -> str:
    """
    Retrieve threshold configurations from peer FLX entities sharing the same tracker.

    Finds other enabled entities in the same tenant with the same tracker_name
    and returns their threshold configurations. This provides calibration reference
    data — if peers have similar thresholds at value X for metric M, it suggests
    that's a reasonable calibration for the current entity too.

    Args:
        tenant_id: The tenant identifier
        object_id: The current entity's _key (to exclude from results)
        tracker_name: The tracker_name to search for among peers

    Returns:
        JSON string with: peer_count, peer_thresholds (list of {peer_object, metric_name,
        value, operator, condition_true, score, has_variable_threshold}),
        metric_calibration_summary (per-metric stats across peers)
    """
    service = _get_trackme_service(ctx)

    # First get peer object_ids with same tracker_name
    spl_peers = (
        f'| inputlookup kv_trackme_flx_tenant_{tenant_id} '
        f'| search tracker_name="{tracker_name}" monitored_state="enabled" '
        f'| where _key!="{object_id}" '
        f'| fields _key, object '
        f'| rename _key as peer_object_id '
        f'| head 20'
    )

    search_params = {
        "earliest_time": "-5m",
        "latest_time": "now",
        "output_mode": "json",
        "count": 0,
    }

    peers = []
    try:
        reader = run_splunk_search(service, spl_peers, search_params, max_retries=3)
        for result in reader:
            if isinstance(result, dict):
                peers.append({
                    "peer_object_id": result.get("peer_object_id", ""),
                    "object": result.get("object", ""),
                })
    except Exception as e:
        return json.dumps({"error": f"Failed to query peer entities: {str(e)}"})

    if not peers:
        return json.dumps({
            "peer_count": 0,
            "message": f"No peer entities found with tracker_name='{tracker_name}' in tenant='{tenant_id}'",
            "peer_thresholds": [],
            "metric_calibration_summary": {},
        })

    peer_ids = [p["peer_object_id"] for p in peers if p["peer_object_id"]]
    peer_id_map = {p["peer_object_id"]: p["object"] for p in peers}

    if not peer_ids:
        return json.dumps({
            "peer_count": 0,
            "message": "No valid peer object IDs found",
            "peer_thresholds": [],
            "metric_calibration_summary": {},
        })

    peer_ids_quoted = " ".join(f'"{pid}"' for pid in peer_ids)
    spl_thresholds = (
        f'| inputlookup kv_trackme_flx_thresholds_tenant_{tenant_id} '
        f'| search object_id IN ({peer_ids_quoted}) '
        f'| table object_id, metric_name, value, operator, condition_true, score, variable_threshold_enabled'
    )

    peer_thresholds = []
    metric_values_by_name: dict = {}

    try:
        reader = run_splunk_search(service, spl_thresholds, search_params, max_retries=3)
        for result in reader:
            if isinstance(result, dict):
                metric_name = result.get("metric_name", "")
                peer_obj_id = result.get("object_id", "")
                entry = {
                    "peer_object": peer_id_map.get(peer_obj_id, peer_obj_id),
                    "peer_object_id": peer_obj_id,
                    "metric_name": metric_name,
                    "value": result.get("value", ""),
                    "operator": result.get("operator", ""),
                    "condition_true": result.get("condition_true", ""),
                    "score": result.get("score", ""),
                    "has_variable_threshold": result.get("variable_threshold_enabled", "false"),
                }
                peer_thresholds.append(entry)

                # Aggregate values per metric for calibration summary
                try:
                    val = float(result.get("value", 0) or 0)
                    if metric_name not in metric_values_by_name:
                        metric_values_by_name[metric_name] = []
                    metric_values_by_name[metric_name].append(val)
                except (ValueError, TypeError):
                    pass
    except Exception as e:
        logger.warning(f"FLX peer thresholds search failed: {e}")

    # Build per-metric calibration summary
    metric_calibration_summary = {}
    for metric_name, values in metric_values_by_name.items():
        if values:
            sv = sorted(values)
            n = len(sv)
            median = (sv[(n - 1) // 2] + sv[n // 2]) / 2
            metric_calibration_summary[metric_name] = {
                "peer_count": n,
                "min": sv[0],
                "max": sv[-1],
                "median": round(median, 4),
                "mean": round(sum(sv) / n, 4),
            }

    return json.dumps({
        "tenant_id": tenant_id,
        "tracker_name": tracker_name,
        "peer_count": len(peers),
        "peers": [{"object": p["object"], "object_id": p["peer_object_id"]} for p in peers],
        "peer_thresholds": peer_thresholds,
        "metric_calibration_summary": metric_calibration_summary,
    })


# ===========================================================================
# WRITE TOOLS (6-10)
# ===========================================================================


@registry.tool(tags=["flx_threshold_write"])
async def add_flx_threshold(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    metric_name: str,
    value: float,
    operator: str,
    condition_true: bool,
    score: int = 100,
    comment: str = "",
) -> str:
    """
    Add a new dynamic threshold to a FLX entity for a specific metric.

    TrackMe threshold semantics (the four-field alert-fire formula):

        match = op_func(metric_value, threshold_value)
        Alert fires if: (condition_true AND NOT match) OR (NOT condition_true AND match)

    ``condition_true=True`` means **"this is the HEALTHY condition I expect to
    hold — alert me when it breaks."**  It does NOT mean "alert when the
    operator evaluates to true."

    Inverse-style is the most common pattern.  Worked example:

        operator='<', value=90, condition_true=True

      - Healthy expectation: metric < 90 (i.e. memory below 90% is GOOD)
      - match = (metric_value < 90)
      - Alert fires when: condition_true=True AND NOT match
                       = healthy expectation is broken
                       = metric_value >= 90
      - This is a HIGH-memory alert, NOT a low-memory alert.

    Four common correct patterns.

    **Inverse-style** (``condition_true=True``, idiomatic TrackMe —
    operator names the HEALTHY condition; alert when violated):

      | Intent                                  | operator | condition_true | Alert when    |
      |-----------------------------------------|----------|----------------|---------------|
      | Expect metric BELOW X; alert when HIGH  | '<'      | True           | metric >= X   |
      | Expect metric ABOVE X; alert when LOW   | '>'      | True           | metric <= X   |
      | Expect zero; alert on ANY non-zero      | '=='     | True, value=0  | metric != 0   |

    **Direct-style** (``condition_true=False``, rare — operator names
    the ALERT condition directly; alert fires when match is TRUE):

      | Intent                                      | operator | condition_true | Alert when    |
      |---------------------------------------------|----------|----------------|---------------|
      | Alert when metric matches a specific value  | '=='     | False          | metric == X   |
      | Alert when metric exceeds X (strict-direct) | '>'      | False          | metric > X    |

    Note the symmetry: with ``condition_true=False`` the operator IS the
    alert direction, the opposite of the inverse-style.  E.g.
    ``operator='>', condition_true=False, value=100`` means "alert when
    metric > 100" (the operator directly describes the alert condition).

    Prefer inverse-style for continuous metrics — it's easier to reason
    about, harder to misread, and matches every default in the TrackMe
    use-case library.  Reserve direct-style for enum-like metrics where
    a specific value IS the alert condition (e.g. a status code where
    ``2`` means "critical").

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash (keys_list will be [object_id])
        metric_name: The exact metric name from the entity's metrics JSON
        value: Threshold numeric value
        operator: Comparison operator: '<', '>', '<=', '>=', '==', '!='
        condition_true: True = the operator+value pair describes the HEALTHY
                        expectation (alert fires when it's violated). False =
                        the operator+value pair describes the ALERT condition
                        directly (alert fires when it matches).
        score: Impact score 0-100 (default 100 = critical)
        comment: Optional description of why this threshold exists

    Returns:
        JSON string confirming threshold was added with the new threshold _key
    """
    service = _get_trackme_service(ctx)

    valid_operators = ("<", ">", "<=", ">=", "==", "!=")
    if operator not in valid_operators:
        return json.dumps({
            "error": f"Invalid operator '{operator}'. Must be one of: {valid_operators}"
        })

    body = {
        "tenant_id": tenant_id,
        "keys_list": [object_id],
        "metric_name": metric_name,
        "value": value,
        "operator": operator,
        "condition_true": condition_true,
        "score": score,
        "comment": comment,
    }
    result = _call_trackme_api(service, "trackme/v2/splk_flx/flx_thresholds_add", body)
    return json.dumps(result)


@registry.tool(tags=["flx_threshold_write"])
async def update_flx_threshold(
    ctx: ToolContext,
    tenant_id: str,
    threshold_key: str,
    metric_name: str,
    value: float,
    operator: str,
    condition_true: bool,
    score: int = 100,
    comment: str = "",
) -> str:
    """
    Update an existing FLX threshold's value, operator, or score.

    Use this to recalibrate a threshold that is too tight or too loose based
    on observed metric history.  Requires the threshold _key from
    ``get_flx_entity_context``.

    TrackMe threshold semantics — read ``add_flx_threshold``'s docstring for
    the full alert-fire formula and the four canonical patterns.  Summary:

        match = op_func(metric_value, threshold_value)
        Alert fires if: (condition_true AND NOT match) OR (NOT condition_true AND match)

    ``condition_true=True`` means "this is the HEALTHY expectation; alert me
    when it breaks."  ``operator='<', value=90, condition_true=True`` is a
    HIGH-memory alert (fires when memory >= 90), NOT a low-memory alert.

    Before flipping ``operator`` or ``condition_true``, apply the mandatory
    pre-flip checklist from the system prompt: restate the current healthy
    condition in plain English, prove it is logically inverted, then spell
    out what the proposed new pair would mean.  Most "operator is wrong"
    intuitions are wrong themselves — usually only the threshold *value*
    needs tuning.

    Args:
        tenant_id: The tenant identifier
        threshold_key: The threshold record _key (from thresholds list in entity context)
        metric_name: The metric name (required even for updates)
        value: New threshold value
        operator: New comparison operator: '<', '>', '<=', '>=', '==', '!='
        condition_true: True if the new operator+value pair describes the
                        HEALTHY expectation (alert fires when violated).
                        False if the pair describes the ALERT condition
                        directly.  See ``add_flx_threshold`` docstring for
                        the four canonical patterns.
        score: New impact score
        comment: Updated description

    Returns:
        JSON string confirming the threshold was updated
    """
    service = _get_trackme_service(ctx)

    valid_operators = ("<", ">", "<=", ">=", "==", "!=")
    if operator not in valid_operators:
        return json.dumps({
            "error": f"Invalid operator '{operator}'. Must be one of: {valid_operators}"
        })

    body = {
        "tenant_id": tenant_id,
        "records_list": [{
            "_key": threshold_key,
            "metric_name": metric_name,
            "value": value,
            "operator": operator,
            "condition_true": condition_true,
            "score": score,
            "comment": comment,
        }],
    }
    result = _call_trackme_api(service, "trackme/v2/splk_flx/flx_thresholds_update", body)
    return json.dumps(result)


@registry.tool(tags=["flx_threshold_write"])
async def delete_flx_threshold(
    ctx: ToolContext,
    tenant_id: str,
    threshold_key: str,
    reason: str,
) -> str:
    """
    Delete a FLX threshold that is causing false positives or is no longer relevant.

    IMPORTANT: Only delete thresholds when there is clear evidence they are
    misconfigured or causing more harm than benefit. Always record the reason.
    Do not delete the last threshold on an entity without adding a replacement.

    Args:
        tenant_id: The tenant identifier
        threshold_key: The threshold record _key to delete
        reason: Explanation of why this threshold is being removed (required)

    Returns:
        JSON string confirming deletion
    """
    service = _get_trackme_service(ctx)

    if not reason or not reason.strip():
        return json.dumps({
            "error": "reason is required and must not be empty when deleting a threshold."
        })

    body = {
        "tenant_id": tenant_id,
        "keys_list": [threshold_key],
    }
    result = _call_trackme_api(service, "trackme/v2/splk_flx/flx_thresholds_del", body)
    if isinstance(result, dict) and result.get("error"):
        return json.dumps({
            "deleted": False,
            "threshold_key": threshold_key,
            "error": result.get("error"),
            "api_response": result,
        })
    return json.dumps({
        "deleted": True,
        "threshold_key": threshold_key,
        "reason": reason,
        "api_response": result,
    })


@registry.tool(tags=["flx_threshold_write"])
async def set_flx_variable_threshold_slots(
    ctx: ToolContext,
    tenant_id: str,
    threshold_key: str,
    metric_name: str,
    variable_threshold_default: float,
    variable_threshold_slots: str,
) -> str:
    """
    Configure variable (time-slot based) threshold values on an existing threshold.

    Enables time-based threshold variation so different values apply at different
    times of day or days of week. For example, higher thresholds during business
    hours when traffic is expected to be high, lower thresholds at night.

    The slots JSON must follow this format:
    {"slots": [{"slot_name": "business_hours", "days": [0,1,2,3,4], "hours": [8,9,...,17], "value": 100}, ...]}

    Days: 0=Monday through 6=Sunday. Hours: 0-23 in UTC.

    Args:
        tenant_id: The tenant identifier
        threshold_key: The existing threshold _key to add variable slots to
        metric_name: The metric name (required for the update API)
        variable_threshold_default: Fallback value when no slot matches
        variable_threshold_slots: JSON string with the slots configuration

    Returns:
        JSON string confirming the variable threshold configuration was applied
    """
    service = _get_trackme_service(ctx)

    # Parse slots to validate JSON
    try:
        slots_parsed = json.loads(variable_threshold_slots)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid variable_threshold_slots JSON: {e}"})

    if "slots" not in slots_parsed:
        return json.dumps({
            "error": "variable_threshold_slots must contain a 'slots' key with a list of slot objects."
        })

    body = {
        "tenant_id": tenant_id,
        "records_list": [{
            "_key": threshold_key,
            "metric_name": metric_name,
            "variable_threshold_enabled": "true",
            "variable_threshold_default": variable_threshold_default,
            "variable_threshold_slots": json.dumps(slots_parsed),
        }],
    }
    result = _call_trackme_api(service, "trackme/v2/splk_flx/flx_thresholds_update", body)
    return json.dumps(result)


@registry.tool(tags=["flx_threshold_write"])
async def update_flx_entity_state_priority(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    reason: str,
    monitored_state: str = None,
    priority: str = None,
) -> str:
    """
    Update a FLX entity's monitoring state or priority level.

    Use monitored_state='disabled' for stale/decommissioned entities that
    are causing false alerts. Only disable if the entity has had no metric
    updates in 14+ days.

    Use priority to escalate critical entities or downgrade low-importance ones.
    Priority levels: critical, high, medium, low, pending

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash
        reason: Your explanation for this change — REQUIRED. Include the
            evidence, e.g. "No metric updates for 18 days (last seen: 2026-03-01)."
        monitored_state: Optional new state: 'enabled' or 'disabled'
        priority: Optional new priority: critical | high | medium | low | pending

    Returns:
        JSON string confirming the changes applied
    """
    service = _get_trackme_service(ctx)

    body = {"tenant_id": tenant_id, "keys_list": [object_id], "update_comment": reason or "AI FLX Threshold Advisor"}
    changes_applied = []

    if monitored_state is not None:
        if monitored_state not in ("enabled", "disabled"):
            return json.dumps({
                "error": f"Invalid monitored_state '{monitored_state}'. Must be 'enabled' or 'disabled'."
            })

        # Tool-level guard: only applies in automated (scheduled) runs.
        # Interactive users are not subject to the tenant decommission policy —
        # they have explicitly chosen to run the advisor and can disable entities.
        if monitored_state == "disabled" and os.environ.get("TRACKME_AI_AUTOMATED") == "1":
            # The flag is the unified ai_components_advisor_allow_decommission
            # (replaces the per-advisor ai_flxthreshold_allow_decommission).
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
                return json.dumps({
                    "error": (
                        "Blocked by tenant policy: disabling entity monitoring is not permitted in "
                        "automated mode. Set ai_components_advisor_allow_decommission=1 in the tenant "
                        "AI Settings to enable automated decommissioning, or run manually. "
                        "Record this recommendation in your final response instead."
                    ),
                })


        body["monitored_state"] = monitored_state
        changes_applied.append(f"monitored_state={monitored_state}")

    if priority is not None:
        valid_priorities = ("critical", "high", "medium", "low", "pending")
        if priority not in valid_priorities:
            return json.dumps({
                "error": f"Invalid priority '{priority}'. Must be one of: {valid_priorities}"
            })
        body["priority"] = priority
        changes_applied.append(f"priority={priority}")

    if not changes_applied:
        return json.dumps({
            "error": "No changes specified. Provide monitored_state and/or priority."
        })

    result = _call_trackme_api(service, "trackme/v2/splk_flx/flx_bulk_edit", body)
    return json.dumps({"changes_applied": changes_applied, "api_response": result})


# ---------------------------------------------------------------------------
# Entry point: run as MCP tool server when executed directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    registry.run()
