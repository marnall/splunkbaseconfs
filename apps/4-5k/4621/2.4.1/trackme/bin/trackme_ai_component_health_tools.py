"""
TrackMe AI Agent Tools — Component Health Advisor

Tool definitions for the Splunk Agent SDK, enabling the Component Health Advisor
agent to inspect, analyze, and manage WLK and MHM entity configurations.
(FQM has its own dedicated advisor — see trackme_ai_fqm_advisor_tools.py.)

Tools defined:

    WLK READ (WorkLoad Knowledge):
    1. get_wlk_entity_context          — Full entity config, thresholds, execution metrics
    2. get_wlk_execution_history       — Per-day-of-week skip/error statistics from summary index
    3. get_wlk_execution_errors        — Raw scheduler ERROR log entries (root-cause diagnosis)
    4. get_wlk_breach_history          — State transition history from audit index
    5. get_wlk_peer_thresholds         — Threshold calibration data from same-app peer entities

    WLK WRITE:
    6. add_wlk_threshold               — Add a new dynamic threshold for a WLK metric
    7. update_wlk_threshold            — Recalibrate an existing WLK threshold
    8. delete_wlk_threshold            — Remove a misconfigured WLK threshold
    9. update_wlk_entity_state_priority — Update monitoring state or priority (with decommission guard)

    MHM READ (Metric Host Monitoring):
    10. get_mhm_entity_context         — Full entity config, metric lag info, per-category status
    11. get_mhm_metric_lag_history     — Per-day-of-week lag statistics from summary index
    12. get_mhm_breach_history         — State transition history from audit index
    13. get_mhm_lagging_classes        — All lagging class definitions for a tenant

    MHM WRITE:
    14. update_mhm_metric_max_lag      — Update the lag threshold for a metric host
    15. update_mhm_entity_state_priority — Update monitoring state or priority (with decommission guard)
"""

import json
import logging
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
)

# Named logger — shares the singleton configured by the parent
# REST handler's setup_logger() call (root logger redirect there means
# `logging.<level>(...)` here would bleed across handlers).
logger = logging.getLogger("trackme.rest.ai.component_health")


# ===========================================================================
# WLK READ TOOLS (1-4)
# ===========================================================================


@registry.tool(tags=["wlk_read"])
async def get_wlk_entity_context(ctx: ToolContext, tenant_id: str, object_id: str) -> str:
    """
    Retrieve the full context of a WLK (WorkLoad Knowledge) entity.

    Calls the TrackMe describe endpoint to gather entity identity, execution metrics,
    and monitoring configuration. Also fetches all configured dynamic thresholds from
    the KV Store for this entity (including tenant-level default thresholds).

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store (savedsearch name hash)

    Returns:
        JSON string with entity context including: savedsearch_name, app,
        monitored_state, priority, object_state, anomaly_reason,
        skipped_pct_last_24h, count_errors_last_24h, execution metrics,
        and all configured thresholds for this entity (including any
        object_id=="default" tenant-level defaults).
    """
    service = _get_trackme_service(ctx)

    result = _call_trackme_api(
        service,
        "trackme/v2/describe/entity",
        body={
            "tenant_id": tenant_id,
            "object_category": "splk-wlk",
            "object_id": object_id,
        },
        method="post",
    )

    if isinstance(result, dict) and result.get("error"):
        return json.dumps({
            "error": result.get("error"),
            "message": f"Failed to retrieve WLK entity context for object_id={object_id} in tenant={tenant_id}",
        })

    entity_context = {}

    if "entity_description" in result:
        desc = result["entity_description"]
        identity = desc.get("identity", {})
        config = desc.get("configuration", {})
        health = desc.get("health", {})

        entity_context = {
            "object_id": object_id,
            "object": identity.get("object", ""),
            "savedsearch_name": identity.get("savedsearch_name", identity.get("object", "")),
            "app": identity.get("app", ""),
            "tenant_id": tenant_id,
            "monitored_state": config.get("monitored_state", "unknown"),
            "priority": config.get("priority", "unknown"),
            "sla_class": config.get("sla_class", ""),
            "tags": config.get("tags_manual", ""),
            "current_state": health.get("object_state", "unknown"),
            "anomaly_reason": health.get("anomaly_reason", ""),
            "anomaly_reasons": health.get("anomaly_reasons", []),
            "skipped_pct_last_24h": health.get("skipped_pct_last_24h", ""),
            "count_errors_last_24h": health.get("count_errors_last_24h", ""),
            "full_description": desc,
        }
    else:
        entity_context = result

    # Fetch entity-specific thresholds from KV Store
    entity_thresholds = []
    default_thresholds = []
    try:
        kv_name = f"kv_trackme_wlk_thresholds_tenant_{tenant_id}"
        records = service.kvstore[kv_name].data.query(
            query=json.dumps({"object_id": object_id})
        )
        entity_thresholds = list(records) if records else []

        # Also fetch tenant-level defaults (object_id == "default")
        default_records = service.kvstore[kv_name].data.query(
            query=json.dumps({"object_id": "default"})
        )
        default_thresholds = list(default_records) if default_records else []
    except Exception as e:
        logger.warning(f"WLK threshold KV query failed for {object_id}: {e}")

    entity_context["thresholds"] = entity_thresholds
    entity_context["tenant_default_thresholds"] = default_thresholds
    entity_context["note"] = (
        "tenant_default_thresholds are fallback thresholds (object_id='default') applied "
        "when no entity-specific threshold matches. Entity-specific thresholds take precedence."
    )

    return json.dumps(entity_context)


@registry.tool(tags=["wlk_read"])
async def get_wlk_execution_history(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    days: int = 30,
) -> str:
    """
    Retrieve execution history statistics for a WLK entity, broken down by day of week.

    Queries the TrackMe summary index for historical WLK snapshots and computes
    per-day-of-week aggregates: average and maximum skip percentage and error counts.
    High skip percentages on specific days indicate scheduling conflicts or resource
    contention patterns that can guide threshold calibration.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store
        days: Number of days of history to retrieve (default: 30, max: 90)

    Returns:
        JSON string with execution statistics per day-of-week:
        avg_skip_pct, max_skip_pct, avg_errors, max_errors, and states_seen.
    """
    service = _get_trackme_service(ctx)

    capped_days = min(max(1, days), 90)
    summary_idx = _get_summary_index(service, tenant_id)

    spl = (
        f'search index={summary_idx} sourcetype="trackme:wlk:*" '
        f'tenant_id="{tenant_id}" object_id="{object_id}" '
        f'earliest=-{capped_days}d@d latest=now '
        f'| eval day_of_week=strftime(_time, "%A") '
        f'| stats '
        f'avg(skipped_pct_last_24h) as avg_skip_pct, '
        f'max(skipped_pct_last_24h) as max_skip_pct, '
        f'avg(count_errors_last_24h) as avg_errors, '
        f'max(count_errors_last_24h) as max_errors, '
        f'values(object_state) as states_seen '
        f'by day_of_week '
        f'| sort day_of_week'
    )

    search_params = {
        "earliest_time": f"-{capped_days}d@d",
        "latest_time": "now",
        "output_mode": "json",
        "count": 0,
    }

    results = []
    try:
        reader = run_splunk_search(service, spl, search_params, max_retries=3)
        for result in reader:
            if isinstance(result, dict):
                try:
                    results.append({
                        "day_of_week": result.get("date_wday", ""),
                        "avg_skip_pct": round(float(result.get("avg_skip_pct", 0) or 0), 2),
                        "max_skip_pct": round(float(result.get("max_skip_pct", 0) or 0), 2),
                        "avg_errors": round(float(result.get("avg_errors", 0) or 0), 2),
                        "max_errors": round(float(result.get("max_errors", 0) or 0), 2),
                        "states_seen": result.get("states_seen", []),
                    })
                except (ValueError, TypeError):
                    continue
    except Exception as e:
        return json.dumps({
            "error": f"Search failed: {str(e)}",
            "suggestion": "Verify the tenant_id and object_id are correct.",
        })

    if not results:
        return json.dumps({
            "error": f"No WLK execution history found for object_id={object_id} in the last {capped_days} days",
            "suggestion": "Entity may be new, inactive, or the summary index may not contain WLK data.",
        })

    return json.dumps({
        "tenant_id": tenant_id,
        "object_id": object_id,
        "days_queried": capped_days,
        "execution_history_by_day": results,
        "note": (
            "avg_skip_pct and max_skip_pct are the percentage of scheduled runs skipped "
            "in each 24h window. High values indicate scheduling pressure or resource contention. "
            "Use this to calibrate skipped_pct_last_24h thresholds."
        ),
    })


@registry.tool(tags=["wlk_read"])
async def get_wlk_execution_errors(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    earliest: str = "-7d",
    latest: str = "now",
    max_errors: int = 20,
) -> str:
    """
    Retrieve recent scheduler ERROR log entries for the WLK entity's saved
    search — the diagnostic tool for root-cause analysis of execution errors.

    Where ``get_wlk_execution_history`` reports aggregated COUNTS
    (avg_errors / max_errors per day-of-week), this tool returns the actual
    error MESSAGES from Splunk's ``index=_internal sourcetype=scheduler``
    logs. The messages tell you exactly what's wrong — a missing or
    misnamed lookup, a malformed SPL fragment, an unauthorised index
    reference, a typo in a macro — so the advisor can pinpoint the fix
    rather than guess from the entity name.

    Reuses the well-established WLK execution-errors investigation SPL
    pattern so that the AI advisor can reach the same conclusions a
    human operator would by inspecting the scheduler logs directly.

    Args:
        tenant_id: The tenant identifier
        object_id: The WLK entity _key hash in KV Store
        earliest: SPL earliest_time (default: -7d, max useful ~30d)
        latest: SPL latest_time (default: now)
        max_errors: Maximum error log entries to return (default: 20, cap 100)

    Returns:
        JSON string with:
          - error_count: number of entries returned (after head limit)
          - unique_error_messages: deduplicated list of
            ``{"message": ..., "occurrences": N}`` sorted by occurrence
            count desc — chronic errors repeat the same message many
            times, so the highest-count entry is almost always the
            actionable root cause
          - errors: list of ``{_time, host, app, savedsearch_name, errmsg}``
            (raw entries, latest first)
          - savedsearch_name / app / owner: parsed from the entity identity
          - account: ``"local"`` or the remote account name — when
            non-local the search was dispatched via ``| splunkremotesearch``
            against the remote SH (errors of WLK entities backed by a
            remote account are not visible in the local ``_internal``
            index, hence the cross-SH dispatch).
          - query_period: the earliest / latest window used
          - search_dispatch: ``"local"`` or ``"remote"`` for clarity
          - note: usage guidance

    When to call this tool:
      - ``count_errors_last_24h > 0`` in the entity context, OR
      - ``execution_errors_detected`` appears in ``anomaly_reasons``, OR
      - Any recommendation involves an SPL / lookup / macro / permission
        correction (cite the actual error message in your reasoning).

    Diagnostic guidance for the advisor:
      - "Error in 'lookup' command: Could not construct lookup '<name>'":
        the SPL references a lookup that does not exist. Recommendation
        is to correct the lookup reference in the saved search SPL —
        NOT a threshold change.
      - "Search not executed: Unknown sid": the search was cancelled or
        the scheduler restarted. Transient; threshold tuning may be
        appropriate.
      - "permission denied" / "user does not have permissions": RBAC
        issue. Recommend reviewing the search owner's role assignments.
      - Empty errors list: no scheduler errors in window. If the entity
        is still RED with ``execution_errors_detected``, the breach is
        older than ``earliest`` — widen the window.
    """
    service = _get_trackme_service(ctx)

    # Resolve the entity's saved search name + app via the describe
    # endpoint.  This is also the tool's mandatory existence-check —
    # without it the SPL filter would silently return zero results on a
    # mistyped object_id.
    describe_resp = _call_trackme_api(
        service,
        "trackme/v2/describe/entity",
        body={
            "tenant_id": tenant_id,
            "object_category": "splk-wlk",
            "object_id": object_id,
        },
        method="post",
    )

    if isinstance(describe_resp, dict) and describe_resp.get("error"):
        return json.dumps({
            "error": describe_resp.get("error"),
            "message": f"Failed to resolve WLK entity for object_id={object_id} in tenant={tenant_id}",
            "errors": [],
        })

    desc = (describe_resp or {}).get("entity_description", {}) if isinstance(describe_resp, dict) else {}
    identity = desc.get("identity", {})
    entity_info = desc.get("entity_info", {}) or {}
    object_name = identity.get("object", "")
    # Prefer the describe endpoint's explicit ``savedsearch_name``;
    # fall back to parsing ``object`` (format ``app:owner:savedsearch_name``,
    # splitting on the first two colons so saved-search names that contain
    # colons survive).  The describe payload exposes ``savedsearch_name``
    # / ``app`` / ``user`` under ``entity_info`` (see
    # ``trackme_libs_describe._build_wlk_entity_info``); ``identity`` carries
    # the human-readable ``object`` identifier.
    savedsearch_name = (
        entity_info.get("savedsearch_name")
        or identity.get("savedsearch_name")
        or ""
    )
    app = entity_info.get("app") or identity.get("app") or ""
    owner = (
        entity_info.get("owner")
        or entity_info.get("user")
        or identity.get("user")
        or identity.get("owner")
        or ""
    )
    if not savedsearch_name and object_name:
        parts = object_name.split(":", 2)
        if len(parts) == 3:
            app, owner, savedsearch_name = parts[0], parts[1], parts[2]
        else:
            savedsearch_name = object_name

    if not savedsearch_name:
        return json.dumps({
            "error": "Could not determine savedsearch_name for this entity",
            "object_id": object_id,
            "object": object_name,
            "errors": [],
        })

    # Account routing — the critical bit for WLK on remote SHs.
    # WLK entities backed by a remote account live in a DIFFERENT
    # Splunk's ``index=_internal``.  The scheduler logs we need
    # therefore can't be reached with a plain ``search index=_internal``
    # on this SH — we have to dispatch through ``splunkremotesearch``,
    # the same way the WLK investigation SPL routes through
    # ``splk_wlk_return_searches`` (see ``trackme_libs_splk_wlk.py``).
    # Without this every WLK entity whose ``account != "local"`` would
    # silently return zero errors and the advisor would conclude
    # (wrongly) that the search has no scheduler issues.
    #
    # The describe endpoint surfaces the entity's account under
    # ``entity_info.account`` (default ``"local"``).  Empty / missing /
    # ``"local"`` → execute locally; anything else → remote dispatch.
    account = (entity_info.get("account") or "local").strip() or "local"
    is_remote = account != "local"

    # Cap the head limit to protect against runaway responses.  Twenty
    # is a reasonable default; one hundred is plenty for an advisor to
    # deduplicate and pick a representative.
    capped_max = min(max(1, int(max_errors)), 100)

    # SPL — the canonical WLK execution-errors investigation shape.
    # Deliberately scoped by ``savedsearch_name`` only (not by app):
    # the rex+savedsearch_name match is the authoritative join.  The
    # scheduler's ``savedsearch_id`` field has the format
    # ``user;app;savedsearch_name``; ``rex`` extracts the name portion
    # when only the id is logged.  We deliberately ALSO escape any
    # double-quotes in the saved-search name so the generated SPL stays
    # syntactically valid for searches whose names contain quotes.
    safe_name = savedsearch_name.replace('\\', '\\\\').replace('"', '\\"')

    inner_spl = (
        f'search index=_internal sourcetype=scheduler host=* splunk_server=* '
        f'| rex field=savedsearch_id "^(?<user_alt>[^\\;]*)\\;(?<app_alt>[^\\;]*)\\;(?<savedsearch_name_alt>.*)" '
        f'| eval app=coalesce(app, app_alt), savedsearch_name=coalesce(savedsearch_name, savedsearch_name_alt) '
        f'| search savedsearch_name="{safe_name}" '
        f'| eval errmsg=case(len(errmsg)>0, errmsg, match(log_level, "(?i)error") AND len(message)>0, message) '
        f'| eval status=case((status="success" OR status="completed"),"completed",(status="skipped"),"skipped",(status="continued"),"deferred",len(errmsg)>0 OR status="delegated_remote_error","error") '
        f'| where status="error" '
        f'| sort - _time '
        f'| head {capped_max} '
        f'| table _time, host, app, savedsearch_name, errmsg, message'
    )

    if is_remote:
        # Wrap for remote dispatch — matches
        # ``splk_wlk_return_searches`` lines 273-280: escape inner
        # quotes, then embed inside the splunkremotesearch ``search=``
        # parameter.  Also pass ``earliest`` / ``latest`` explicitly to
        # the remote command so the remote SH applies the same window
        # (the local job's time bounds don't propagate through
        # splunkremotesearch on every code path).
        escaped_inner = inner_spl.replace('"', '\\"')
        # Escape any quotes that may legitimately appear in the account
        # name (very rare but defence in depth — Splunk account names
        # are typically alphanumeric).
        safe_account = account.replace('"', '\\"')
        safe_earliest = str(earliest).replace('"', '\\"')
        safe_latest = str(latest).replace('"', '\\"')
        spl = (
            f'| splunkremotesearch '
            f'account="{safe_account}" '
            f'search="{escaped_inner}" '
            f'earliest="{safe_earliest}" '
            f'latest="{safe_latest}"'
        )
    else:
        spl = inner_spl

    search_params = {
        "earliest_time": earliest,
        "latest_time": latest,
        "output_mode": "json",
        "count": 0,
    }

    errors_list = []
    unique_messages = {}
    try:
        reader = run_splunk_search(service, spl, search_params, max_retries=3)
        for result in reader:
            if not isinstance(result, dict):
                continue
            errmsg = (result.get("errmsg") or result.get("message") or "").strip()
            entry = {
                "_time": result.get("_time", ""),
                "host": result.get("host", ""),
                "app": result.get("app", ""),
                "savedsearch_name": result.get("savedsearch_name", ""),
                "errmsg": errmsg,
            }
            errors_list.append(entry)
            if errmsg:
                unique_messages[errmsg] = unique_messages.get(errmsg, 0) + 1
    except Exception as e:
        return json.dumps({
            "error": f"Search failed: {str(e)}",
            "suggestion": (
                "Verify the tenant_id and object_id are correct. The search "
                "queries index=_internal which requires elevated capabilities. "
                "For remote accounts, also verify the remote account is "
                "reachable and the bearer token is valid (test via "
                "POST /trackme/v2/configuration/test_remote_account)."
            ),
            "object_id": object_id,
            "savedsearch_name": savedsearch_name,
            "account": account,
            "search_dispatch": "remote" if is_remote else "local",
            "errors": [],
        })

    earliest_observed = errors_list[-1]["_time"] if errors_list else ""
    latest_observed = errors_list[0]["_time"] if errors_list else ""

    return json.dumps({
        "error_count": len(errors_list),
        "earliest_observed": earliest_observed,
        "latest_observed": latest_observed,
        "unique_error_messages": [
            {"message": msg, "occurrences": count}
            for msg, count in sorted(unique_messages.items(), key=lambda x: -x[1])
        ],
        "errors": errors_list,
        "tenant_id": tenant_id,
        "object_id": object_id,
        "savedsearch_name": savedsearch_name,
        "app": app,
        "owner": owner,
        "account": account,
        "search_dispatch": "remote" if is_remote else "local",
        "query_period": {"earliest": earliest, "latest": latest, "max_errors": capped_max},
        "note": (
            "unique_error_messages is the actionable view — chronic scheduler "
            "errors repeat the same message every cycle, so the highest-count "
            "entry is almost always the root cause. When the message points "
            "to broken SPL (missing lookup, malformed command, RBAC denial), "
            "the correct remediation is fixing the saved search definition — "
            "NOT a threshold change. Quote the actual error verbatim in your "
            "reasoning so the operator can map directly to the SPL line that "
            "needs fixing."
        ),
    })


@registry.tool(tags=["wlk_read"])
async def get_wlk_breach_history(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    days: int = 30,
) -> str:
    """
    Retrieve state transition and threshold breach history for a WLK entity.

    Queries the audit index for state change events, showing when the entity
    entered RED/ORANGE states and what anomaly reasons were recorded. This helps
    identify whether threshold breaches are persistent or transient, and whether
    skip/error spikes correlate with specific days or time periods.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store
        days: Number of days of history to retrieve (default: 30, max: 90)

    Returns:
        JSON string with: total_state_transitions, total_reds, total_oranges,
        recent_state_transitions (list of flip events with timestamp, from/to
        state, and anomaly_reason), and breach_count_by_state.
    """
    service = _get_trackme_service(ctx)

    capped_days = min(max(1, days), 90)
    audit_idx = _get_audit_index(service, tenant_id)

    spl = (
        f'search index={audit_idx} '
        f'tenant_id="{tenant_id}" '
        f'object_id="{object_id}" '
        f'change_type="state change" '
        f'earliest=-{capped_days}d@d latest=now '
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

    transitions = []
    total_reds = 0
    total_oranges = 0

    try:
        reader = run_splunk_search(service, spl, search_params, max_retries=3)
        for result in reader:
            if isinstance(result, dict):
                new_state = result.get("new_state", "")
                if new_state in ("red", "RED"):
                    total_reds += 1
                elif new_state in ("orange", "ORANGE"):
                    total_oranges += 1
                transitions.append({
                    "_time": result.get("_time", ""),
                    "from": result.get("previous_state", ""),
                    "to": new_state,
                    "reason": result.get("anomaly_reason", ""),
                })
    except Exception as e:
        logger.warning(f"WLK breach history search failed for {object_id}: {e}")

    return json.dumps({
        "tenant_id": tenant_id,
        "object_id": object_id,
        "days_queried": capped_days,
        "total_state_transitions": len(transitions),
        "total_reds": total_reds,
        "total_oranges": total_oranges,
        "recent_state_transitions": transitions[-50:],
    })


@registry.tool(tags=["wlk_read"])
async def get_wlk_peer_thresholds(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
) -> str:
    """
    Retrieve threshold configurations from WLK peer entities in the same Splunk app.

    Looks up the app field for the current entity, then finds all other WLK entities
    in the same app that have configured thresholds. This provides calibration reference
    data — if peers monitoring similar scheduled searches in the same app have thresholds
    at value X for metric M, it suggests a reasonable baseline for the current entity.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash (excluded from peer results)

    Returns:
        JSON string with: peer_count, peer_thresholds (list of {peer_object,
        metric_name, value, operator, condition_true, score}),
        and metric_calibration_summary (per-metric stats across peers).
    """
    service = _get_trackme_service(ctx)

    # Look up the app for this entity
    entity_app = ""
    try:
        kv_name = f"kv_trackme_wlk_tenant_{tenant_id}"
        records = service.kvstore[kv_name].data.query(
            query=json.dumps({"_key": object_id})
        )
        if records:
            entity_app = records[0].get("app", "")
    except Exception as e:
        return json.dumps({"error": f"Failed to look up entity app: {str(e)}"})

    if not entity_app:
        return json.dumps({
            "peer_count": 0,
            "message": f"Could not determine app for object_id={object_id} — cannot find peers.",
            "peer_thresholds": [],
            "metric_calibration_summary": {},
        })

    # Find peer entities in the same app
    search_params = {
        "earliest_time": "-5m",
        "latest_time": "now",
        "output_mode": "json",
        "count": 0,
    }

    spl_peers = (
        f'| inputlookup kv_trackme_wlk_tenant_{tenant_id} '
        f'| search app="{entity_app}" monitored_state="enabled" '
        f'| where _key!="{object_id}" '
        f'| fields _key, object '
        f'| rename _key as peer_object_id '
        f'| head 20'
    )

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
        return json.dumps({"error": f"Failed to query peer WLK entities: {str(e)}"})

    if not peers:
        return json.dumps({
            "peer_count": 0,
            "message": f"No peer WLK entities found in app='{entity_app}' for tenant='{tenant_id}'",
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
        f'| inputlookup kv_trackme_wlk_thresholds_tenant_{tenant_id} '
        f'| search object_id IN ({peer_ids_quoted}) '
        f'| table object_id, metric_name, value, operator, condition_true, score'
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
                }
                peer_thresholds.append(entry)

                try:
                    val = float(result.get("value", 0) or 0)
                    if metric_name not in metric_values_by_name:
                        metric_values_by_name[metric_name] = []
                    metric_values_by_name[metric_name].append(val)
                except (ValueError, TypeError):
                    pass
    except Exception as e:
        logger.warning(f"WLK peer thresholds search failed: {e}")

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
        "entity_app": entity_app,
        "peer_count": len(peers),
        "peers": [{"object": p["object"], "object_id": p["peer_object_id"]} for p in peers],
        "peer_thresholds": peer_thresholds,
        "metric_calibration_summary": metric_calibration_summary,
    })


# ===========================================================================
# WLK WRITE TOOLS (5-8)
# ===========================================================================


@registry.tool(tags=["wlk_write"])
async def add_wlk_threshold(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    metric_name: str,
    value: float,
    operator: str,
    condition_true: bool,
    score: int = 100,
    comment: str = "AI Component Health Advisor",
) -> str:
    """
    Add a new dynamic threshold to a WLK entity for a specific execution metric.

    Creates a threshold rule that fires when the metric meets the condition.
    WLK metrics operate on top-level record fields such as skipped_pct_last_24h
    (percentage of skipped runs) and count_errors_last_24h (error count).

    Example: metric_name='skipped_pct_last_24h', operator='>', value=20.0,
    condition_true=True means "alert when skip percentage exceeds 20%".

    To set a tenant-level default threshold (applies to all entities without
    specific thresholds), pass object_id='default'.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash, or "default" for a tenant-level default
        metric_name: The WLK metric field name (e.g., skipped_pct_last_24h,
            count_errors_last_24h)
        value: Threshold numeric value
        operator: Comparison operator: '<', '>', '<=', '>=', '==', '!='
        condition_true: True = alert when condition matches; False = alert when it doesn't
        score: Impact score 0-100 (default 100 = critical)
        comment: Description of why this threshold exists

    Returns:
        JSON string confirming threshold was added
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
    result = _call_trackme_api(service, "trackme/v2/splk_wlk/write/wlk_thresholds_add", body)
    return json.dumps(result)


@registry.tool(tags=["wlk_write"])
async def update_wlk_threshold(
    ctx: ToolContext,
    tenant_id: str,
    threshold_key: str,
    metric_name: str,
    value: float,
    operator: str,
    condition_true: bool,
    score: int = 100,
    comment: str = "AI Component Health Advisor",
) -> str:
    """
    Update an existing WLK threshold's value, operator, or score.

    Use this to recalibrate a threshold that is generating too many false positives
    (too tight) or missing real issues (too loose). Requires the threshold _key
    from get_wlk_entity_context.

    Args:
        tenant_id: The tenant identifier
        threshold_key: The threshold record _key (from thresholds list in entity context)
        metric_name: The WLK metric field name (required even for updates)
        value: New threshold value
        operator: New comparison operator: '<', '>', '<=', '>=', '==', '!='
        condition_true: New condition direction
        score: New impact score (0-100)
        comment: Updated description of this threshold's purpose

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
        "threshold_key": threshold_key,
        "metric_name": metric_name,
        "value": value,
        "operator": operator,
        "condition_true": condition_true,
        "score": score,
        "comment": comment,
    }
    result = _call_trackme_api(service, "trackme/v2/splk_wlk/write/wlk_thresholds_update", body)
    return json.dumps(result)


@registry.tool(tags=["wlk_write"])
async def delete_wlk_threshold(
    ctx: ToolContext,
    tenant_id: str,
    threshold_key: str,
    reason: str,
) -> str:
    """
    Delete a WLK threshold that is misconfigured or no longer relevant.

    IMPORTANT: Only delete thresholds when there is clear evidence they are
    causing false positives or have been superseded by a corrected replacement.
    Always record the reason. Do not delete the last threshold without adding
    a replacement first.

    In automated mode (TRACKME_AI_AUTOMATED=1), decommissioning an entity via
    monitored_state=disabled is gated by the tenant policy flag
    ai_components_advisor_allow_decommission. Threshold deletion itself is not gated.

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
        "threshold_key": threshold_key,
        "update_comment": reason,
    }
    result = _call_trackme_api(service, "trackme/v2/splk_wlk/write/wlk_thresholds_del", body)
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


@registry.tool(tags=["wlk_write"])
async def update_wlk_entity_state_priority(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    reason: str,
    monitored_state: str = None,
    priority: str = None,
) -> str:
    """
    Update a WLK entity's monitoring state or priority level.

    Use monitored_state='disabled' for decommissioned scheduled searches that
    no longer exist in Splunk or have been permanently retired. Only disable
    if there is clear evidence the search has not run in 14+ days.

    Use priority to escalate business-critical scheduled searches (e.g., SLA
    reports, data ingestion jobs) or downgrade low-importance ones.

    In automated mode (TRACKME_AI_AUTOMATED=1), setting monitored_state='disabled'
    requires the tenant policy flag ai_components_advisor_allow_decommission=1.

    Priority levels: critical, high, medium, low, pending

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store
        reason: Your explanation for this change — REQUIRED. Include evidence,
            e.g. "Scheduled search has not executed in 18 days (last seen: 2026-03-01)."
        monitored_state: Optional new state: 'enabled' or 'disabled'
        priority: Optional new priority: critical | high | medium | low | pending

    Returns:
        JSON string confirming the changes applied
    """
    service = _get_trackme_service(ctx)

    changes_applied = []
    body = {
        "tenant_id": tenant_id,
        "keys_list": [object_id],
        "update_comment": reason or "AI Component Health Advisor",
    }

    if monitored_state is not None:
        if monitored_state not in ("enabled", "disabled"):
            return json.dumps({
                "error": f"Invalid monitored_state '{monitored_state}'. Must be 'enabled' or 'disabled'."
            })

        # Tool-level guard: only applies in automated (scheduled) runs.
        # Interactive users are not subject to the tenant decommission policy —
        # they have explicitly chosen to run the advisor and can disable entities.
        if monitored_state == "disabled" and os.environ.get("TRACKME_AI_AUTOMATED") == "1":
            _allow_decommission = False
            try:
                _vt_records = service.kvstore["kv_trackme_virtual_tenants"].data.query(
                    query=json.dumps({"tenant_id": tenant_id})
                )
                if _vt_records:
                    _vt_account = json.loads(_vt_records[0].get("vtenant_account", "{}"))
                    # Unified ai_components_advisor_allow_decommission flag
                    # (replaces the per-advisor ai_wlkadvisor_allow_decommission).
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

    result = _call_trackme_api(service, "trackme/v2/splk_wlk/write/wlk_bulk_edit", body)
    return json.dumps({"changes_applied": changes_applied, "api_response": result})


# ===========================================================================
# MHM READ TOOLS (17-20)
# ===========================================================================


@registry.tool(tags=["mhm_read"])
async def get_mhm_entity_context(ctx: ToolContext, tenant_id: str, object_id: str) -> str:
    """
    Retrieve the full context of a MHM (Metric Host Monitoring) entity.

    Calls the TrackMe describe endpoint to gather entity identity, metric lag
    configuration, per-category metric status, and monitoring state. MHM monitors
    hosts sending metric data to Splunk and tracks lag (age of most recent metric
    event) per metric category.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store (typically the hostname)

    Returns:
        JSON string with entity context including: object (hostname),
        metric_index, metric_max_lag_allowed (global lag threshold in seconds),
        metric_last_lag_seen (current measured lag), metric_details (JSON with
        per-category status and individual lag values), monitored_state,
        priority, and current object_state.
    """
    service = _get_trackme_service(ctx)

    result = _call_trackme_api(
        service,
        "trackme/v2/describe/entity",
        body={
            "tenant_id": tenant_id,
            "object_category": "splk-mhm",
            "object_id": object_id,
        },
        method="post",
    )

    if isinstance(result, dict) and result.get("error"):
        return json.dumps({
            "error": result.get("error"),
            "message": f"Failed to retrieve MHM entity context for object_id={object_id} in tenant={tenant_id}",
        })

    entity_context = {}

    if "entity_description" in result:
        desc = result["entity_description"]
        identity = desc.get("identity", {})
        config = desc.get("configuration", {})
        health = desc.get("health", {})

        entity_context = {
            "object_id": object_id,
            "object": identity.get("object", ""),
            "metric_index": identity.get("metric_index", ""),
            "tenant_id": tenant_id,
            "monitored_state": config.get("monitored_state", "unknown"),
            "priority": config.get("priority", "unknown"),
            "sla_class": config.get("sla_class", ""),
            "tags": config.get("tags_manual", ""),
            "metric_max_lag_allowed": config.get("metric_max_lag_allowed", ""),
            "current_state": health.get("object_state", "unknown"),
            "anomaly_reason": health.get("anomaly_reason", ""),
            "anomaly_reasons": health.get("anomaly_reasons", []),
            "metric_last_lag_seen": health.get("metric_last_lag_seen", ""),
            "metric_details": health.get("metric_details", ""),
            "full_description": desc,
        }
    else:
        entity_context = result

    return json.dumps(entity_context)


@registry.tool(tags=["mhm_read"])
async def get_mhm_metric_lag_history(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    days: int = 30,
) -> str:
    """
    Retrieve metric lag history statistics for a MHM entity, broken down by day of week.

    Queries the TrackMe summary index for historical MHM snapshots and computes per-day-of-week
    aggregates: average and maximum metric_last_lag_seen values. High lag values on specific
    days indicate batch metric collection, network issues, or infrastructure maintenance windows
    that should be accounted for in the lag threshold (metric_max_lag_allowed).

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store
        days: Number of days of history to retrieve (default: 30, max: 90)

    Returns:
        JSON string with lag statistics per day-of-week:
        avg_lag (seconds), max_lag (seconds), and states_seen.
    """
    service = _get_trackme_service(ctx)

    capped_days = min(max(1, days), 90)
    summary_idx = _get_summary_index(service, tenant_id)

    spl = (
        f'search index={summary_idx} sourcetype="trackme:mhm:*" '
        f'tenant_id="{tenant_id}" object_id="{object_id}" '
        f'earliest=-{capped_days}d@d latest=now '
        f'| eval day_of_week=strftime(_time, "%A") '
        f'| stats '
        f'avg(metric_last_lag_seen) as avg_lag, '
        f'max(metric_last_lag_seen) as max_lag, '
        f'values(object_state) as states_seen '
        f'by day_of_week '
        f'| sort day_of_week'
    )

    search_params = {
        "earliest_time": f"-{capped_days}d@d",
        "latest_time": "now",
        "output_mode": "json",
        "count": 0,
    }

    results = []
    try:
        reader = run_splunk_search(service, spl, search_params, max_retries=3)
        for result in reader:
            if isinstance(result, dict):
                try:
                    results.append({
                        "day_of_week": result.get("date_wday", ""),
                        "avg_lag_sec": round(float(result.get("avg_lag", 0) or 0), 0),
                        "max_lag_sec": round(float(result.get("max_lag", 0) or 0), 0),
                        "states_seen": result.get("states_seen", []),
                    })
                except (ValueError, TypeError):
                    continue
    except Exception as e:
        return json.dumps({
            "error": f"Search failed: {str(e)}",
            "suggestion": "Verify the tenant_id and object_id are correct.",
        })

    if not results:
        return json.dumps({
            "error": f"No MHM lag history found for object_id={object_id} in the last {capped_days} days",
            "suggestion": "Entity may be new, inactive, or the summary index may not contain MHM data.",
        })

    # Compute overall max and p95 across all days
    all_max_lags = [r["max_lag_sec"] for r in results if r["max_lag_sec"] > 0]
    p95_lag = None
    if all_max_lags:
        sv = sorted(all_max_lags)
        n = len(sv)
        p95_lag = sv[min(int(n * 0.95), n - 1)]

    return json.dumps({
        "tenant_id": tenant_id,
        "object_id": object_id,
        "days_queried": capped_days,
        "lag_history_by_day": results,
        "overall_max_lag_sec": max(all_max_lags) if all_max_lags else 0,
        "p95_max_lag_sec": p95_lag,
        "note": (
            "avg_lag_sec and max_lag_sec are the metric event lag in seconds (age of newest metric). "
            "The recommended metric_max_lag_allowed is p95_max_lag_sec * 1.2 to provide a safety margin. "
            "Weekends often show higher lag for batch-collected metrics."
        ),
    })


@registry.tool(tags=["mhm_read"])
async def get_mhm_breach_history(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    days: int = 30,
) -> str:
    """
    Retrieve state transition and lag breach history for a MHM entity.

    Queries the audit index for state change events, showing when the entity
    entered RED/ORANGE states and what anomaly reasons were recorded. Frequent
    breaches on the same days of week indicate predictable lag spikes (e.g., weekend
    batch jobs) that should be handled with a higher lag threshold rather than
    repeated false alerts.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store
        days: Number of days of history to retrieve (default: 30, max: 90)

    Returns:
        JSON string with: total_state_transitions, total_reds, total_oranges,
        and recent_state_transitions (list of events with timestamp,
        from/to state, and anomaly_reason).
    """
    service = _get_trackme_service(ctx)

    capped_days = min(max(1, days), 90)
    audit_idx = _get_audit_index(service, tenant_id)

    spl = (
        f'search index={audit_idx} '
        f'tenant_id="{tenant_id}" '
        f'object_id="{object_id}" '
        f'change_type="state change" '
        f'earliest=-{capped_days}d@d latest=now '
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

    transitions = []
    total_reds = 0
    total_oranges = 0

    try:
        reader = run_splunk_search(service, spl, search_params, max_retries=3)
        for result in reader:
            if isinstance(result, dict):
                new_state = result.get("new_state", "")
                if new_state in ("red", "RED"):
                    total_reds += 1
                elif new_state in ("orange", "ORANGE"):
                    total_oranges += 1
                transitions.append({
                    "_time": result.get("_time", ""),
                    "from": result.get("previous_state", ""),
                    "to": new_state,
                    "reason": result.get("anomaly_reason", ""),
                })
    except Exception as e:
        logger.warning(f"MHM breach history search failed for {object_id}: {e}")

    return json.dumps({
        "tenant_id": tenant_id,
        "object_id": object_id,
        "days_queried": capped_days,
        "total_state_transitions": len(transitions),
        "total_reds": total_reds,
        "total_oranges": total_oranges,
        "recent_state_transitions": transitions[-50:],
    })


@registry.tool(tags=["mhm_read"])
async def get_mhm_lagging_classes(ctx: ToolContext, tenant_id: str) -> str:
    """
    Retrieve all lagging class definitions for a tenant's MHM component.

    Lagging classes define named metric-category-to-lag-threshold mappings that
    can be assigned to metric hosts. They allow different lag thresholds for
    different metric categories (e.g., CPU metrics may be collected more frequently
    than disk metrics, requiring a tighter lag threshold).

    Args:
        tenant_id: The tenant identifier

    Returns:
        JSON string with all lagging class records: each containing class_name,
        metric_category (filter pattern), metric_max_lag_allowed (seconds),
        and any additional configuration fields.
    """
    service = _get_trackme_service(ctx)

    lagging_classes = []
    try:
        kv_name = f"kv_trackme_mhm_lagging_classes_tenant_{tenant_id}"
        records = service.kvstore[kv_name].data.query()
        lagging_classes = list(records) if records else []
    except Exception as e:
        return json.dumps({
            "error": f"Failed to query MHM lagging classes: {str(e)}",
            "tenant_id": tenant_id,
        })

    return json.dumps({
        "tenant_id": tenant_id,
        "lagging_class_count": len(lagging_classes),
        "lagging_classes": lagging_classes,
        "note": (
            "Lagging classes define per-category lag thresholds. A metric host with a "
            "lagging class assigned uses those per-category thresholds instead of the "
            "global metric_max_lag_allowed. If no lagging class is assigned, the entity's "
            "metric_max_lag_allowed field is used as a single threshold for all categories."
        ),
    })


# ===========================================================================
# MHM WRITE TOOLS (21-22)
# ===========================================================================


@registry.tool(tags=["mhm_write"])
async def update_mhm_metric_max_lag(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    metric_max_lag_allowed: int,
    reason: str,
) -> str:
    """
    Update the global metric lag threshold for a MHM entity.

    Sets metric_max_lag_allowed (in seconds) — the maximum acceptable age of the
    most recent metric event before the entity is considered lagging. Use this to
    accommodate hosts with known collection intervals that exceed the current threshold
    (e.g., a host with 15-minute metric collection intervals requires a threshold
    of at least 900 seconds, plus a buffer for collection jitter).

    Recommended approach: Use get_mhm_metric_lag_history to find the p95 max lag,
    then set metric_max_lag_allowed to p95 * 1.2 as a safety margin.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store (object_list will be [object_id])
        metric_max_lag_allowed: New lag threshold in seconds (must be a positive integer)
        reason: Your explanation for this change — REQUIRED. Include the evidence,
            e.g. "p95 max lag is 720s (30-day history); setting threshold to 900s."

    Returns:
        JSON string confirming the lag threshold was updated
    """
    service = _get_trackme_service(ctx)

    if metric_max_lag_allowed <= 0:
        return json.dumps({
            "error": f"metric_max_lag_allowed must be a positive integer, got {metric_max_lag_allowed}"
        })

    if not reason or not reason.strip():
        return json.dumps({
            "error": "reason is required and must not be empty."
        })

    body = {
        "tenant_id": tenant_id,
        "object_list": [object_id],
        "metric_max_lag_allowed": str(metric_max_lag_allowed),
        "update_comment": reason,
    }
    result = _call_trackme_api(service, "trackme/v2/splk_mhm/write/mh_bulk_edit", body)
    return json.dumps({
        "object_id": object_id,
        "metric_max_lag_allowed": metric_max_lag_allowed,
        "reason": reason,
        "api_response": result,
    })


@registry.tool(tags=["mhm_write"])
async def update_mhm_entity_state_priority(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    reason: str,
    monitored_state: str = None,
    priority: str = None,
) -> str:
    """
    Update a MHM entity's monitoring state or priority level.

    Use monitored_state='disabled' for decommissioned hosts that no longer send
    metric data to Splunk. Only disable if there is clear evidence the host has
    not reported metrics in 14+ days.

    Use priority to escalate monitoring for critical infrastructure hosts (e.g.,
    core network devices, production compute nodes) or downgrade lab/test hosts.

    In automated mode (TRACKME_AI_AUTOMATED=1), setting monitored_state='disabled'
    requires the tenant policy flag ai_components_advisor_allow_decommission=1.

    Priority levels: critical, high, medium, low, pending

    MHM uses separate API endpoints for monitoring state and priority changes.
    Both operations are performed if both parameters are provided.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store (object_list will be [object_id])
        reason: Your explanation for this change — REQUIRED. Include evidence,
            e.g. "Host has not sent metric data for 19 days (last seen: 2026-03-01)."
        monitored_state: Optional new state: 'enabled' or 'disabled'
        priority: Optional new priority: critical | high | medium | low | pending

    Returns:
        JSON string confirming the changes applied, with separate API responses
        for monitoring state and priority if both were changed.
    """
    service = _get_trackme_service(ctx)

    if not reason or not reason.strip():
        return json.dumps({
            "error": "reason is required and must not be empty."
        })

    changes_applied = []
    api_responses = {}

    if monitored_state is not None:
        if monitored_state not in ("enabled", "disabled"):
            return json.dumps({
                "error": f"Invalid monitored_state '{monitored_state}'. Must be 'enabled' or 'disabled'."
            })

        # Tool-level guard: only applies in automated (scheduled) runs.
        if monitored_state == "disabled" and os.environ.get("TRACKME_AI_AUTOMATED") == "1":
            _allow_decommission = False
            try:
                _vt_records = service.kvstore["kv_trackme_virtual_tenants"].data.query(
                    query=json.dumps({"tenant_id": tenant_id})
                )
                if _vt_records:
                    _vt_account = json.loads(_vt_records[0].get("vtenant_account", "{}"))
                    # Unified ai_components_advisor_allow_decommission flag
                    # (replaces the per-advisor ai_mhmadvisor_allow_decommission).
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

        monitoring_result = _call_trackme_api(
            service,
            "trackme/v2/splk_mhm/write/mh_monitoring",
            {
                "tenant_id": tenant_id,
                "object_list": [object_id],
                "monitored_state": monitored_state,
                "update_comment": reason,
            },
        )
        changes_applied.append(f"monitored_state={monitored_state}")
        api_responses["monitoring_state"] = monitoring_result

    if priority is not None:
        valid_priorities = ("critical", "high", "medium", "low", "pending")
        if priority not in valid_priorities:
            return json.dumps({
                "error": f"Invalid priority '{priority}'. Must be one of: {valid_priorities}"
            })

        priority_result = _call_trackme_api(
            service,
            "trackme/v2/splk_mhm/write/mh_update_priority",
            {
                "tenant_id": tenant_id,
                "object_list": [object_id],
                "priority": priority,
                "update_comment": reason,
            },
        )
        changes_applied.append(f"priority={priority}")
        api_responses["priority"] = priority_result

    if not changes_applied:
        return json.dumps({
            "error": "No changes specified. Provide monitored_state and/or priority."
        })

    return json.dumps({
        "changes_applied": changes_applied,
        "api_responses": api_responses,
    })


# ---------------------------------------------------------------------------
# Entry point: run as MCP tool server when executed directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    registry.run()
