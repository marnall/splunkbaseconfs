"""
TrackMe AI Agent Tools — ML Outlier Advisor

Tool definitions for the Splunk Agent SDK, enabling the ML Outlier Advisor
agent to inspect, analyze, and manage ML outlier detection models.

Uses the official Splunk Python SDK (splunklib.ai). splunk-sdk>=3.0.0
(pinned in package/lib/requirements.txt) bundles the AI module on PyPI,
so ucc-gen installs it directly into lib/splunklib/ at build time.

Tools defined:
    READ (agent's "eyes"):
    1. get_entity_outlier_context — Full entity description via /describe/entity
       (includes identity, health, score breakdown, ML model configs, detection
       state with boundary values, confidence, and investigation searches)
    2. get_entity_metric_history — Raw time series data (mstats search)
    3. get_model_training_details — Per-group fitted distributions, boundaries,
       fit quality (Wasserstein distance) from native ML KV Store
    4. get_outlier_score_history — Scoring timeline (mstats search)
    5. get_entity_alert_history — State transitions (describe + audit search)
    6. get_model_render_history — Full training window render with boundaries
       (trackmesplkoutliersrender — metric values + upper/lower bounds + outlier flags)
    7. simulate_model_with_time_factor — Empirically verify a proposed
       time_factor change before recommending it (runs simulation-mode
       training, compares fit quality, returns improves/neutral/worsens)

    WRITE (agent's "hands"):
    8. add_period_exclusion — Exclude anomaly window from training
    9. trigger_model_retrain — Retrain model (live or simulation)
    10. set_false_positive — Neutralize current outlier scoring
    11. update_model_rules — Tune any model parameter (18+ fields)
    12. manage_outlier_detection — Enable/disable/reset/monitor
"""

import json
import logging
import sys
import os
import time

# Add the app's lib directory to the path for TrackMe shared libraries
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.ai.registry import ToolRegistry, ToolContext

# Import TrackMe shared libraries
from trackme_libs import run_splunk_search

# Named logger — shares the singleton configured by the parent
# REST handler's setup_logger() call (root logger redirect there means
# `logging.<level>(...)` here would bleed across handlers).
logger = logging.getLogger("trackme.rest.ai.ml_advisor")

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

registry = ToolRegistry()

# ---------------------------------------------------------------------------
# Helper: component short name mapping
# ---------------------------------------------------------------------------

COMPONENT_TO_OBJECT_CATEGORY = {
    "dsm": "splk-dsm",
    "dhm": "splk-dhm",
    "mhm": "splk-mhm",
    "flx": "splk-flx",
    "fqm": "splk-fqm",
    "wlk": "splk-wlk",
}


def _get_trackme_service(ctx: ToolContext):
    """
    Get a Splunk service connected with the correct app context for TrackMe.

    The SDK's SerializedService.connect() creates a service without app/owner
    context, which means KV Store lookups and REST calls silently target the
    wrong namespace.  We re-connect with app="trackme", owner="nobody".
    """
    base_service = ctx.service
    import splunklib.client as client
    return client.connect(
        scheme=base_service.scheme,
        host=base_service.host,
        port=base_service.port,
        token=base_service.token,
        app="trackme",
        owner="nobody",
        timeout=120,
    )


def _call_trackme_api(service, endpoint, body=None, method="post"):
    """
    Call a TrackMe REST API endpoint via splunklib service.

    TrackMe REST handlers expect POST data as raw JSON with Content-Type:
    application/json.  The handler reads the body from:
        resp_dict = json.loads(str(request_info.raw_args["payload"]))
    where "payload" is Splunk's raw body field from PersistentServerConnectionApplication.

    We use the requests library with JSON content type (same approach as TrackMe's
    own ``trackme`` custom command) instead of splunklib service.post because
    service.post always sends form-encoded data, which Splunk puts into
    args["form"] instead of args["payload"].

    Args:
        service: Splunk service connection (with app="trackme")
        endpoint: REST path WITHOUT the /services prefix (e.g., "trackme/v2/describe/entity")
        body: Dict payload for POST requests
        method: "get" or "post"

    Returns:
        Parsed JSON response as dict
    """
    import requests as req_lib
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Build the full URL from the service connection
    base_url = f"{service.scheme}://{service.host}:{service.port}"
    url = f"{base_url}/services/{endpoint}"
    token = service.token
    auth_value = token if token.startswith("Splunk ") else f"Splunk {token}"
    headers = {
        "Authorization": auth_value,
    }

    try:
        if method.lower() == "post":
            headers["Content-Type"] = "application/json"
            response = req_lib.post(
                url,
                headers=headers,
                data=json.dumps(body) if body else "{}",
                verify=False,
                timeout=120,
            )
        else:
            response = req_lib.get(
                url,
                headers=headers,
                params={"output_mode": "json"},
                verify=False,
                timeout=120,
            )

        response.raise_for_status()
        return response.json()

    except req_lib.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else None
        error_body = e.response.text if e.response is not None else None
        error_detail = str(e)

        logger.error(
            f"TrackMe API call failed: endpoint={endpoint}, "
            f"http_status={status_code}, error={error_detail}, "
            f"body={error_body}"
        )
        # Include the response body so callers (and downstream LLM tools) can
        # read the handler's rejection message rather than the bare HTTP status.
        return {
            "error": error_detail,
            "http_status": status_code,
            "endpoint": endpoint,
            "response_body": error_body,
        }
    except Exception as e:
        logger.error(
            f"TrackMe API call failed: endpoint={endpoint}, error={e}"
        )
        return {"error": str(e), "endpoint": endpoint}


def _api_error(result):
    """Return the error string when ``_call_trackme_api`` reported a
    failure, or ``None`` when the call succeeded.

    Centralised replacement for the unguarded ``result.get("error")``
    pattern that previously crashed when a REST endpoint returned a
    list payload (e.g. ``lagging_classes_show`` returns ``[]`` for
    tenants with no classes configured — see PR #1823 root-cause).
    The crash signature was
    ``AttributeError: 'list' object has no attribute 'get'``.

    Behaviour:
      * Dict with an ``"error"`` key → returns the value of that key
        verbatim (including the empty string if the API returned
        ``{"error": ""}`` — see contract note below).
      * Dict without an ``"error"`` key → returns ``None``.
      * Any non-dict shape (list, primitive, ``None``) → returns
        ``None``. The API call succeeded with whatever payload the
        endpoint returned.

    CONTRACT — ``None`` is the sentinel for "no API error":

        ``if _api_error(result) is None:``  # SUCCESS
        ``if _api_error(result) is not None:``  # ERROR

    Callers using the convenience ``if not _api_error(result):`` /
    ``not _api_error(result)`` truthy-checks are safe in practice
    because ``_call_trackme_api`` itself never produces an
    ``{"error": ""}`` shape — its HTTP-error branch always
    populates ``error`` with a non-empty message, and its general-
    exception branch uses ``str(e)`` which is also non-empty. But
    the contract here is None-vs-not-None, not falsy-vs-truthy:
    don't lean on the convenience if you can't guarantee the input
    shape upstream.

    Use this in every tool that needs to determine whether the API
    call succeeded, instead of calling ``result.get("error")``
    directly. The helper makes the read-vs-write tool fragility
    structurally impossible: every tool routes its error detection
    through the same defensive guard.
    """
    if isinstance(result, dict):
        return result.get("error")
    return None


def _get_metrics_index(service, tenant_id: str) -> str:
    """
    Get the metrics index name for a tenant.
    Falls back to 'trackme_metrics' if lookup fails.
    """
    try:
        search_query = (
            f'| trackmegetconf tenant_id="{tenant_id}" stanza="index_settings"'
            f' | fields trackme_metric_idx'
        )
        search_params = {
            "earliest_time": "-5m",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }
        results_reader = run_splunk_search(service, search_query, search_params, max_retries=3)
        for result in results_reader:
            if isinstance(result, dict):
                return result.get("trackme_metric_idx", "trackme_metrics")
    except Exception:
        pass
    return "trackme_metrics"


def _get_summary_index(service, tenant_id: str) -> str:
    """Get the summary index name for a tenant. Falls back to 'trackme_summary'."""
    try:
        search_query = (
            f'| trackmegetconf tenant_id="{tenant_id}" stanza="index_settings"'
            f' | fields trackme_summary_idx'
        )
        search_params = {"earliest_time": "-5m", "latest_time": "now", "output_mode": "json", "count": 0}
        results_reader = run_splunk_search(service, search_query, search_params, max_retries=3)
        for result in results_reader:
            if isinstance(result, dict):
                return result.get("trackme_summary_idx", "trackme_summary")
    except Exception:
        pass
    return "trackme_summary"


def _get_audit_index(service, tenant_id: str) -> str:
    """Get the audit index name for a tenant. Falls back to 'trackme_audit'."""
    try:
        search_query = (
            f'| trackmegetconf tenant_id="{tenant_id}" stanza="index_settings"'
            f' | fields trackme_audit_idx'
        )
        search_params = {"earliest_time": "-5m", "latest_time": "now", "output_mode": "json", "count": 0}
        results_reader = run_splunk_search(service, search_query, search_params, max_retries=3)
        for result in results_reader:
            if isinstance(result, dict):
                return result.get("trackme_audit_idx", "trackme_audit")
    except Exception:
        pass
    return "trackme_audit"


def _parse_json_field(value, default=None):
    """Safely parse a JSON string field, returning default on failure."""
    if default is None:
        default = {}
    if isinstance(value, dict) or isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return default
    return default


# ===========================================================================
# READ TOOLS (1-5)
# ===========================================================================


@registry.tool(name="get_entity_outlier_context", tags=["ml_read"])
def get_entity_outlier_context(
    tenant_id: str,
    component: str,
    object_id: str,
    ctx: ToolContext,
) -> dict:
    """
    Get the full entity description including ML outlier context via the
    TrackMe describe endpoint.

    Returns comprehensive entity data: identity (name, alias, priority, SLA),
    health (state, score breakdown, anomaly reasons, ACK status),
    outlier models (algorithm, time_factor, thresholds, period_exclusions,
    detection state, per-model anomaly details with boundary values),
    configuration, and investigation searches.

    Parameters:
        tenant_id: The tenant identifier (e.g., "demo-outliers")
        component: The component type: "dsm", "dhm", "flx", "fqm", or "wlk"
        object_id: The entity's _key hash in KV Store

    Use this as the FIRST tool to understand an entity's full situation.
    The response contains everything needed for initial assessment:
    - identity.object = entity name (use for metric queries)
    - health.score = impact score breakdown
    - outliers.models = all ML model configs with current detection state
    - outliers.detection.models_summary = per-model anomaly details
    - investigation.context_searches = ready-made SPL for scoring/flipping
    """
    service = _get_trackme_service(ctx)
    object_category = COMPONENT_TO_OBJECT_CATEGORY.get(component, f"splk-{component}")

    result = _call_trackme_api(service, "trackme/v2/describe/entity", body={
        "tenant_id": tenant_id,
        "object_category": object_category,
        "object_id": object_id,
    })

    # The describe endpoint wraps its response in an "entity_description" key
    if "entity_description" in result:
        return result["entity_description"]

    return result


@registry.tool(name="get_entity_metric_history", tags=["ml_read"])
def get_entity_metric_history(
    tenant_id: str,
    component: str,
    object_id: str,
    model_id: str,
    object_name: str = "",
    kpi_metric: str = "",
    method_calculation: str = "",
    earliest: str = "-7d",
    latest: str = "now",
    span: str = "1h",
    ctx: ToolContext = None,
) -> dict:
    """
    Query the metric time series for an entity's ML model.

    Returns timestamped metric values that the ML model monitors. Use this to:
    - Understand the entity's normal behavior pattern (daily cycles, weekly patterns)
    - Identify anomaly windows (sudden drops or spikes)
    - Determine appropriate period exclusions by seeing exactly when anomalies occurred

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm", "dhm", "flx", "fqm", or "wlk"
        object_id: The entity's _key hash in KV Store
        model_id: The ML model identifier (from get_entity_outlier_context)
        object_name: The entity name (from get_entity_outlier_context identity.object).
            If not provided, will be looked up via the describe endpoint.
        kpi_metric: The metric name (from get_entity_outlier_context
            outliers.models.{model_id}.kpi_metric). If not provided, looked up
            via describe endpoint.
        method_calculation: Aggregation method (from get_entity_outlier_context
            outliers.models.{model_id}.method_calculation, e.g. "avg").
            If not provided, looked up via describe endpoint.
        earliest: Start time in Splunk relative format (default: "-7d")
        latest: End time in Splunk relative format (default: "now")
        span: Aggregation span — use "1h" for overview, "10m" for detailed windows

    The returned time_series contains {_time, value} pairs. The statistics
    section provides mean, std, min, max, p05, p95 for quick assessment.

    TIP: Pass object_name, kpi_metric, and method_calculation from a prior
    get_entity_outlier_context call to avoid a redundant describe API call.
    """
    service = _get_trackme_service(ctx)
    object_category = COMPONENT_TO_OBJECT_CATEGORY.get(component, f"splk-{component}")

    # Only call describe endpoint if we're missing required fields
    if not object_name or not kpi_metric:
        describe = _call_trackme_api(service, "trackme/v2/describe/entity", body={
            "tenant_id": tenant_id,
            "object_category": object_category,
            "object_id": object_id,
        })
        entity_desc = describe.get("entity_description", describe)

        if not object_name:
            object_name = entity_desc.get("identity", {}).get("object", "")
            if not object_name:
                return {"error": f"Could not resolve entity name for {object_id}"}

        if not kpi_metric:
            models = entity_desc.get("outliers", {}).get("models", {})
            model_def = models.get(model_id, {})
            kpi_metric = model_def.get("kpi_metric", "")
            if not method_calculation:
                method_calculation = model_def.get("method_calculation", "avg")

    if not method_calculation:
        method_calculation = "avg"

    if not kpi_metric:
        return {"error": f"Model {model_id} not found — kpi_metric could not be resolved"}

    # Get the metrics index for this tenant
    metrics_idx = _get_metrics_index(service, tenant_id)

    # Build the mstats query — KPI metrics use the entity name ('object' dimension)
    search_query = (
        f'| mstats {method_calculation}(trackme.{kpi_metric}) as metric_value'
        f' where index="{metrics_idx}"'
        f' tenant_id="{tenant_id}"'
        f' object_category="{object_category}"'
        f' object="{object_name}"'
        f' by object span={span}'
        f' | stats {method_calculation}(metric_value) as value by _time'
        f' | sort _time'
    )

    search_params = {
        "earliest_time": earliest,
        "latest_time": latest,
        "output_mode": "json",
        "count": 0,
    }

    time_series = []
    try:
        results_reader = run_splunk_search(service, search_query, search_params, max_retries=3)
        for result in results_reader:
            if isinstance(result, dict):
                try:
                    time_series.append({
                        "_time": result.get("_time", ""),
                        "value": float(result.get("value", 0)),
                    })
                except (ValueError, TypeError):
                    pass
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}

    # Calculate basic statistics
    values = [dp["value"] for dp in time_series]
    stats = {}
    if values:
        sorted_values = sorted(values)
        n = len(sorted_values)
        mean = sum(values) / n
        stats = {
            "mean": round(mean, 2),
            "std": round((sum((v - mean) ** 2 for v in values) / n) ** 0.5, 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "p05": round(sorted_values[int(n * 0.05)], 2),
            "p95": round(sorted_values[int(n * 0.95)], 2),
        }

    return {
        "model_id": model_id,
        "kpi_metric": kpi_metric,
        "method_calculation": method_calculation,
        "earliest": earliest,
        "latest": latest,
        "span": span,
        "data_points": len(time_series),
        "time_series": time_series,
        "statistics": stats,
    }


@registry.tool(name="get_model_training_details", tags=["ml_read"])
def get_model_training_details(
    tenant_id: str,
    model_id: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Read the trained ML model's internal parameters and fit quality from
    the native ML models KV Store collection.

    Returns per-group distribution type, fit quality (Wasserstein distance),
    data point counts, and computed boundaries. Use this to:
    - Assess if the model has enough training data per group (min 10 required)
    - Check which distribution was auto-selected (gaussian_kde, norm, beta, expon)
      and its fit quality (lower Wasserstein distance = better fit)
    - Identify groups with poor fit (high Wasserstein distance > 1.5)
    - Understand boundary values per time segment (when time_factor is used)
    - See the actual training data points used per group

    Parameters:
        tenant_id: The tenant identifier
        model_id: The ML model identifier (from get_entity_outlier_context
                  outliers.models keys, e.g. "model_195004764423343")

    Groups represent time segments based on time_factor:
    - time_factor="%H": groups "000"-"623" (day_of_week + hour, 168 groups)
    - time_factor="none": single "__default__" group
    Each group has its own fitted distribution and boundaries.
    """
    service = _get_trackme_service(ctx)

    # Read from the native ML models KV Store collection.
    # This is the only tool that uses direct KV Store access because:
    # 1. No REST endpoint exposes the model_json training internals
    # 2. The data is a goldmine: per-group distributions, Wasserstein distances,
    #    raw training data points, and computed boundaries
    # 3. KV Store reads are fast and the _get_trackme_service() helper
    #    ensures proper app="trackme" context
    ml_collection_name = f"kv_trackme_native_ml_models_tenant_{tenant_id}"

    try:
        ml_collection = service.kvstore[ml_collection_name]
        ml_records = ml_collection.data.query(
            query=json.dumps({"_key": model_id})
        )
    except Exception as e:
        return {"error": f"Failed to query ML models collection: {str(e)}"}

    if not ml_records:
        return {"error": f"No trained model found with id {model_id}"}

    model_data = ml_records[0]

    # Parse the model_data JSON (stored as string in KV Store)
    model_json_raw = model_data.get("model_data", "{}")
    model_json = _parse_json_field(model_json_raw)

    # Extract group details with summary statistics
    groups_raw = model_json.get("groups", {})
    groups = {}
    fitted_count = 0
    insufficient_count = 0
    total_distance = 0
    worst_group = {"group": None, "distance_score": 0}

    for group_key, group_data in groups_raw.items():
        if not isinstance(group_data, dict):
            continue

        status = group_data.get("status", "unknown")
        count = group_data.get("count", 0)
        distance = group_data.get("distance_score", 0)
        selected_type = group_data.get("selected_type", "")
        distribution = group_data.get("distribution", {})

        groups[group_key] = {
            "status": status,
            "count": count,
            "selected_type": selected_type,
            "distance_score": round(float(distance), 4) if distance else 0,
            "lower_bound": group_data.get("lower_bound"),
            "upper_bound": group_data.get("upper_bound"),
            "distribution_mean": distribution.get("mean"),
            "distribution_std": distribution.get("std"),
        }

        if status == "fitted":
            fitted_count += 1
            total_distance += float(distance) if distance else 0
            if float(distance or 0) > worst_group["distance_score"]:
                worst_group = {
                    "group": group_key,
                    "distance_score": round(float(distance), 4),
                }
        elif status == "insufficient_data":
            insufficient_count += 1

    total_groups = len(groups)
    avg_distance = round(total_distance / fitted_count, 4) if fitted_count > 0 else 0

    return {
        "model_id": model_id,
        "feature_name": model_json.get("feature_name", ""),
        "group_fields": model_json.get("group_fields", []),
        "dist_type": model_json.get("dist_type", ""),
        "exclude_dist": model_json.get("exclude_dist", []),
        "fitted_at": model_json.get("fitted_at"),
        "lower_threshold": model_json.get("lower_threshold"),
        "upper_threshold": model_json.get("upper_threshold"),
        "groups": groups,
        "summary": {
            "total_groups": total_groups,
            "fitted_groups": fitted_count,
            "insufficient_data_groups": insufficient_count,
            "avg_distance_score": avg_distance,
            "worst_group": worst_group if worst_group["group"] else None,
        },
    }


@registry.tool(name="get_outlier_score_history", tags=["ml_read"])
def get_outlier_score_history(
    tenant_id: str,
    component: str,
    object_id: str,
    earliest: str = "-7d",
    latest: str = "now",
    ctx: ToolContext = None,
) -> dict:
    """
    Get the outlier scoring history for an entity.

    Returns timestamped score events showing when outlier scores were generated
    (positive = anomaly detected) and when false positives were marked (negative).
    Also computes anomaly windows with start/end times and duration.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm", "dhm", "flx", "fqm", or "wlk"
        object_id: The entity's _key hash in KV Store (scoring metrics use object_id
            as a dimension with the _key hash value)
        earliest: Start time in Splunk relative format (default: "-7d")
        latest: End time in Splunk relative format (default: "now")

    Use this to understand the timeline of anomaly detections and correlate
    with metric patterns from get_entity_metric_history.
    """
    service = _get_trackme_service(ctx)
    metrics_idx = _get_metrics_index(service, tenant_id)

    # Query outlier score events via mstats (requires search — no REST endpoint
    # exposes historical scoring time-series)
    search_query = (
        f'| mstats sum(trackme.scoring.score) as score'
        f' where index="{metrics_idx}"'
        f' tenant_id="{tenant_id}"'
        f' object_id="{object_id}"'
        f' (score_source="lowerbound_outlier*"'
        f'  OR score_source="upperbound_outlier*"'
        f'  OR score_source="false_positive_outlier")'
        f' by score_source, _time span=10m'
        f' | sort _time'
    )

    search_params = {
        "earliest_time": earliest,
        "latest_time": latest,
        "output_mode": "json",
        "count": 0,
    }

    score_events = []
    false_positive_events = []
    total_current_score = 0

    try:
        results_reader = run_splunk_search(service, search_query, search_params, max_retries=3)
        for result in results_reader:
            if isinstance(result, dict):
                try:
                    score = float(result.get("score", 0))
                    source = result.get("score_source", "")
                    event = {
                        "_time": result.get("_time", ""),
                        "score_source": source,
                        "score": score,
                    }
                    if "false_positive" in source:
                        false_positive_events.append(event)
                    else:
                        score_events.append(event)
                    total_current_score += score
                except (ValueError, TypeError):
                    pass
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}

    # Detect anomaly windows (consecutive score events from the same source)
    anomaly_windows = []
    if score_events:
        current_window = None
        for event in score_events:
            source = event["score_source"]
            if current_window is None or current_window["score_source"] != source:
                if current_window:
                    anomaly_windows.append(current_window)
                current_window = {
                    "start": event["_time"],
                    "end": event["_time"],
                    "score_source": source,
                    "total_score_contribution": event["score"],
                    "event_count": 1,
                }
            else:
                current_window["end"] = event["_time"]
                current_window["total_score_contribution"] += event["score"]
                current_window["event_count"] += 1
        if current_window:
            anomaly_windows.append(current_window)

    return {
        "object_id": object_id,
        "earliest": earliest,
        "latest": latest,
        "total_current_score": round(total_current_score, 2),
        "score_events_count": len(score_events),
        "score_events": score_events[-50:],  # Last 50 events to keep response manageable
        "false_positive_events": false_positive_events,
        "anomaly_windows": anomaly_windows,
    }


@registry.tool(name="get_entity_alert_history", tags=["ml_read"])
def get_entity_alert_history(
    tenant_id: str,
    component: str,
    object_id: str,
    earliest: str = "-30d",
    latest: str = "now",
    ctx: ToolContext = None,
) -> dict:
    """
    Get the alert and state transition history for an entity.

    Uses the describe endpoint for current state/ACK status, then queries
    the audit index for historical state transitions.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm", "dhm", "flx", "fqm", or "wlk"
        object_id: The entity's _key hash in KV Store
        earliest: Start time for history lookback (default: "-30d")
        latest: End time (default: "now")

    Use this to correlate anomaly periods with actual alert activity,
    check if incidents were acknowledged, and find recurring patterns.
    """
    service = _get_trackme_service(ctx)
    object_category = COMPONENT_TO_OBJECT_CATEGORY.get(component, f"splk-{component}")

    # 1. Get current state, ACK, and alert info from the describe endpoint
    describe = _call_trackme_api(service, "trackme/v2/describe/entity", body={
        "tenant_id": tenant_id,
        "object_category": object_category,
        "object_id": object_id,
    })

    entity_desc = describe.get("entity_description", describe)
    health = entity_desc.get("health", {})

    current_state = health.get("object_state", "unknown")
    ack_state = health.get("ack_state", {})
    stateful_alert = {
        "current_state": current_state,
        "anomaly_reasons": health.get("anomaly_reasons", []),
        "score": health.get("score", {}),
        "latest_flip_state": health.get("latest_flip_state"),
        "latest_flip_time": health.get("latest_flip_time"),
        "is_acknowledged": ack_state.get("is_acked", False),
        "ack_expiration": ack_state.get("ack_expiration"),
    }

    # 2. Query audit index for state transitions (requires search — no REST
    # endpoint provides per-entity transition history)
    state_transitions = []
    try:
        search_query = (
            f'search index=trackme_audit'
            f' tenant_id="{tenant_id}"'
            f' object_id="{object_id}"'
            f' change_type="state change"'
            f' | sort _time'
            f' | fields _time, previous_state, new_state, anomaly_reason'
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
                state_transitions.append({
                    "_time": result.get("_time", ""),
                    "from": result.get("previous_state", ""),
                    "to": result.get("new_state", ""),
                    "reason": result.get("anomaly_reason", ""),
                })
    except Exception as e:
        logger.warning(f"Could not fetch state transitions: {e}")

    return {
        "object_id": object_id,
        "current_state": current_state,
        "stateful_alert": stateful_alert,
        "state_transitions": state_transitions,
    }


@registry.tool(name="get_model_render_history", tags=["ml_read"])
def get_model_render_history(
    tenant_id: str,
    component: str,
    object_id: str,
    model_id: str,
    earliest: str = "-90d",
    latest: str = "now",
    ctx: ToolContext = None,
) -> dict:
    """
    Render the full ML model time series with trained boundaries over the training window.

    Returns the complete picture: actual metric values overlaid with the model's
    learned upper/lower boundaries and outlier flags for each data point. This is
    essential for understanding the model's behaviour over its full training period
    and identifying patterns like:
    - Behaviour changes (sustained shift to a new baseline)
    - Gradual drift (slow trend over weeks)
    - Seasonal patterns the model has learned
    - Whether the current anomaly is part of a broader trend

    IMPORTANT: Always call this tool when analyzing an anomaly — it provides the
    full training window context that get_entity_metric_history (7-day view) cannot.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm", "dhm", "flx", "fqm", or "wlk"
        object_id: The entity's _key hash in KV Store
        model_id: The ML model identifier (from get_entity_outlier_context)
        earliest: Start time (default: "-90d" to cover the full training window)
        latest: End time (default: "now")

    Returns daily_summary (one row per day with avg/min/max metric values, avg boundaries,
    and outlier counts) plus overall statistics. The daily aggregation dramatically reduces
    token usage (~90 rows for 90 days vs ~2,160 hourly rows) while preserving the signal
    needed to detect behaviour changes, gradual drift, and anomaly windows.
    """
    service = _get_trackme_service(ctx)

    # Build the render search — uses trackmesplkoutliersrender to overlay trained
    # boundaries on metric data, then aggregates to daily summaries via Splunk SPL
    # to keep token usage manageable over the full training window.
    search_query = (
        f'| trackmesplkoutliersrender tenant_id="{tenant_id}" component="{component}"'
        f' object_id="{object_id}" model_id="{model_id}"'
        f' | eval day=strftime(_time, "%Y-%m-%d")'
        f' | stats avg(kpi_metric_value) as avg_value'
        f' min(kpi_metric_value) as min_value'
        f' max(kpi_metric_value) as max_value'
        f' avg(LowerBound) as avg_lower_bound'
        f' avg(UpperBound) as avg_upper_bound'
        f' sum(isOutlier) as outlier_count'
        f' sum(isLowerBoundOutlier) as lower_outlier_count'
        f' sum(isUpperBoundOutlier) as upper_outlier_count'
        f' count as data_points'
        f' by day'
        f' | sort day'
    )

    search_params = {
        "earliest_time": earliest,
        "latest_time": latest,
        "output_mode": "json",
        "count": 0,
    }

    daily_summary = []
    try:
        results_reader = run_splunk_search(service, search_query, search_params, max_retries=3)
        for result in results_reader:
            if isinstance(result, dict):
                try:
                    daily_summary.append({
                        "day": result.get("day", ""),
                        "avg_value": round(float(result.get("avg_value", 0)), 2),
                        "min_value": round(float(result.get("min_value", 0)), 2),
                        "max_value": round(float(result.get("max_value", 0)), 2),
                        "avg_lower_bound": round(float(result.get("avg_lower_bound", 0)), 2),
                        "avg_upper_bound": round(float(result.get("avg_upper_bound", 0)), 2),
                        "outlier_count": int(float(result.get("outlier_count", 0))),
                        "lower_outlier_count": int(float(result.get("lower_outlier_count", 0))),
                        "upper_outlier_count": int(float(result.get("upper_outlier_count", 0))),
                        "data_points": int(float(result.get("data_points", 0))),
                    })
                except (ValueError, TypeError):
                    continue

    except Exception as e:
        logger.error(f"Model render search failed: {e}")
        return {"error": f"Failed to render model history: {str(e)}"}

    if not daily_summary:
        return {
            "message": "No render data returned — the model may not have been trained yet or the time range is empty.",
            "daily_summary": [],
            "summary": {},
        }

    # Compute overall statistics
    total_points = sum(d["data_points"] for d in daily_summary)
    total_outliers = sum(d["outlier_count"] for d in daily_summary)
    lower_outliers = sum(d["lower_outlier_count"] for d in daily_summary)
    upper_outliers = sum(d["upper_outlier_count"] for d in daily_summary)
    all_avg_values = [d["avg_value"] for d in daily_summary]

    summary = {
        "total_days": len(daily_summary),
        "total_data_points": total_points,
        "total_outliers": total_outliers,
        "lower_bound_outliers": lower_outliers,
        "upper_bound_outliers": upper_outliers,
        "outlier_percentage": round(total_outliers / total_points * 100, 2) if total_points else 0,
    }
    if all_avg_values:
        summary["metric_daily_avg_min"] = min(all_avg_values)
        summary["metric_daily_avg_max"] = max(all_avg_values)
        summary["metric_daily_avg_mean"] = round(sum(all_avg_values) / len(all_avg_values), 2)

    return {
        "model_id": model_id,
        "earliest": earliest,
        "latest": latest,
        "daily_summary": daily_summary,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Helpers for simulate_model_with_time_factor
# ---------------------------------------------------------------------------


# Closed enum of time_factor candidates the agent may propose. We do NOT let
# the LLM invent novel time_factor values — restructuring the model's group
# schema with an unverified factor is the precise risk the SUGGESTION-ONLY
# rule exists to prevent. Operators may still propose anything via the UI;
# this constraint applies only to the agent's automated path.
_ALLOWED_PROPOSED_TIME_FACTORS = {"%H", "%w%H", "%m%w%H"}


def _summarise_model_groups(model_json: dict) -> dict:
    """Extract fit-quality summary statistics from a model_json carrying a
    ``groups`` sub-dict (the per-time-segment fitted distributions).

    Mirrors the same aggregation logic ``get_model_training_details`` uses,
    but returns ONLY the summary fields needed for comparison — per-group
    details are dropped to keep the verdict payload small.
    """
    groups = model_json.get("groups", {}) if isinstance(model_json, dict) else {}
    fitted_count = 0
    insufficient_count = 0
    total_distance = 0.0

    for group_data in groups.values():
        if not isinstance(group_data, dict):
            continue
        status = group_data.get("status", "")
        distance_raw = group_data.get("distance_score")
        try:
            distance = float(distance_raw) if distance_raw not in (None, "") else 0.0
        except (TypeError, ValueError):
            distance = 0.0
        if status == "fitted":
            fitted_count += 1
            total_distance += distance
        elif status == "insufficient_data":
            insufficient_count += 1

    total_groups = len(groups)
    avg_distance = (
        round(total_distance / fitted_count, 4) if fitted_count > 0 else 0.0
    )
    return {
        "total_groups": total_groups,
        "fitted_groups": fitted_count,
        "insufficient_data_groups": insufficient_count,
        "avg_distance_score": avg_distance,
    }


def _get_current_model_fit(service, tenant_id: str, model_id: str) -> dict:
    """Read the currently deployed model's fit-quality summary from the
    native ML models KV collection. Returns ``{"error": ...}`` on failure
    (callers translate that to ``success: false``)."""
    ml_collection_name = f"kv_trackme_native_ml_models_tenant_{tenant_id}"
    try:
        ml_collection = service.kvstore[ml_collection_name]
        ml_records = ml_collection.data.query(
            query=json.dumps({"_key": model_id})
        )
    except Exception as e:
        return {"error": f"Failed to query ML models collection: {e}"}
    if not ml_records:
        return {"error": f"No trained model found with id {model_id}"}
    model_json = _parse_json_field(ml_records[0].get("model_data", "{}"))
    return _summarise_model_groups(model_json)


def _find_groups_dict(obj):
    """Walk a nested dict/list looking for the first sub-dict that contains
    a ``groups`` key whose value is itself a dict. The simulation endpoint's
    response wraps the new model_json under one of several keys depending on
    the entity component — this helper hides that variation from the tool's
    main flow so the response-shape changes upstream don't immediately break
    the verdict logic."""
    if isinstance(obj, dict):
        if isinstance(obj.get("groups"), dict):
            return obj
        for v in obj.values():
            found = _find_groups_dict(v)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_groups_dict(item)
            if found is not None:
                return found
    return None


def _compare_fit_quality(current: dict, proposed: dict) -> dict:
    """Decide ``verdict`` (``improves`` / ``neutral`` / ``worsens``) and
    write a one-line ``rationale`` citing the numbers that drove the call.

    Heuristics (closed and explicit so the agent's reasoning is auditable):
      - WORSENS if <50% of proposed groups fit (over-segmentation: the new
        time_factor split the data so finely that most groups don't have
        enough points). The agent must not recommend a configuration that
        leaves the model partly unfit.
      - WORSENS if avg distance degrades by >=10%.
      - IMPROVES if avg distance improves by >=10% AND >=80% of proposed
        groups fit (the win is real and broad).
      - NEUTRAL otherwise — the agent should keep the current configuration.
    """
    cur_avg = float(current.get("avg_distance_score") or 0.0)
    prop_avg = float(proposed.get("avg_distance_score") or 0.0)
    cur_fitted = int(current.get("fitted_groups") or 0)
    prop_fitted = int(proposed.get("fitted_groups") or 0)
    cur_total = int(current.get("total_groups") or 0)
    prop_total = int(proposed.get("total_groups") or 0)

    prop_fit_ratio = prop_fitted / prop_total if prop_total > 0 else 0.0

    if prop_total > 0 and prop_fit_ratio < 0.5:
        return {
            "verdict": "worsens",
            "rationale": (
                f"Proposed time_factor produces {prop_fitted}/{prop_total} "
                f"fitted groups ({round(prop_fit_ratio * 100, 1)}%) — over-"
                f"segmentation means most groups lack the minimum 10 data "
                f"points to fit. Keep the current configuration."
            ),
        }

    if cur_avg > 0 and prop_avg > 0:
        # +ve improvement_pct = avg distance went DOWN (tighter fit).
        improvement_pct = ((cur_avg - prop_avg) / cur_avg) * 100
        if improvement_pct >= 10 and prop_fit_ratio >= 0.8:
            return {
                "verdict": "improves",
                "rationale": (
                    f"Proposed time_factor reduces avg Wasserstein distance "
                    f"from {cur_avg} to {prop_avg} "
                    f"({round(improvement_pct, 1)}% improvement) and "
                    f"{prop_fitted}/{prop_total} groups fit "
                    f"({round(prop_fit_ratio * 100, 1)}%). The change is "
                    f"empirically justified."
                ),
            }
        if improvement_pct <= -10:
            return {
                "verdict": "worsens",
                "rationale": (
                    f"Proposed time_factor increases avg Wasserstein distance "
                    f"from {cur_avg} to {prop_avg} "
                    f"({round(-improvement_pct, 1)}% degradation). Keep "
                    f"the current configuration."
                ),
            }

    return {
        "verdict": "neutral",
        "rationale": (
            f"Proposed time_factor produces comparable fit quality "
            f"(current avg={cur_avg}, proposed avg={prop_avg}; current "
            f"fitted={cur_fitted}/{cur_total}, proposed "
            f"fitted={prop_fitted}/{prop_total}). No empirical evidence "
            f"the change would improve detection sensitivity — keep current."
        ),
    }


def _find_model_def_in_entities_outliers(entities_outliers, model_id: str):
    """Locate a specific model's definition dict inside the polymorphic
    ``entities_outliers`` payload stored on the outlier rules KV record.

    The shape varies by component and tenant age. Known forms include:
        {"<kpi_metric>": {<model_def with model_id>}}
        {"<kpi_metric>": {"<model_id>": <model_def>}}
        {"<kpi_metric>": {"models": {"<model_id>": <model_def>}}}

    The helper does a depth-first walk for any dict carrying
    ``model_id == <target>`` and returns it, or ``None`` if not found.
    Defensive against partial / malformed records.
    """
    def _walk(obj):
        if isinstance(obj, dict):
            if obj.get("model_id") == model_id:
                return obj
            for v in obj.values():
                found = _walk(v)
                if found is not None:
                    return found
        elif isinstance(obj, list):
            for item in obj:
                found = _walk(item)
                if found is not None:
                    return found
        return None
    return _walk(entities_outliers)


@registry.tool(name="simulate_model_with_time_factor", tags=["ml_read"])
def simulate_model_with_time_factor(
    tenant_id: str,
    component: str,
    object_id: str,
    model_id: str,
    proposed_time_factor: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Verify a proposed ``time_factor`` change empirically BEFORE recommending
    it. Runs a SIMULATION-MODE training pass on the entity with the new
    time_factor and compares the resulting fit quality (avg Wasserstein
    distance, fitted group ratio) against the currently deployed model.

    Use this exclusively as evidence-gathering for the TIME-FACTOR
    SEASONALITY MISMATCH rule. The system prompt restricts the agent to
    AT MOST ONE simulation call per advisor run, and ONLY when
    ``get_model_render_history`` shows a clear weekday/weekend variance
    pattern that suggests the current time_factor is too coarse.

    Parameters:
        tenant_id: The tenant identifier.
        component: The component type: "dsm", "dhm", "flx", "fqm", or "wlk".
        object_id: The entity's _key hash in KV Store.
        model_id: The ML model identifier (read from
            ``get_entity_outlier_context`` → ``outliers.models``).
        proposed_time_factor: Candidate time_factor — MUST be one of
            ``"%H"``, ``"%w%H"``, ``"%m%w%H"``. Other values are rejected
            (closed enum prevents the LLM from inventing novel factors that
            could over-segment the data).

    Returns:
        A dict with:
        - ``success``: bool — whether the simulation completed.
        - ``current_time_factor`` / ``proposed_time_factor``: the values
          compared.
        - ``current`` / ``proposed``: ``{avg_distance_score, fitted_groups,
          total_groups, insufficient_data_groups}`` for each model.
        - ``delta``: ``{avg_distance_score_delta, fitted_groups_delta}`` —
          the numbers the agent should cite in its recommendation's
          ``details.evidence`` field.
        - ``verdict``: ``"improves"`` / ``"neutral"`` / ``"worsens"``. Emit
          the ``config_change`` recommendation ONLY when the verdict is
          ``improves``.
        - ``rationale``: human-readable explanation of the verdict.

    HEAVINESS WARNING — server-side training is expensive (typically
    30-90s for a single entity). Do not call this tool speculatively;
    only after the variance pattern in ``get_model_render_history`` makes
    a strong case for a finer time_factor.

    SAFETY — the simulation endpoint runs in ``mode=simulation`` which
    does NOT mutate the deployed model. This tool is tagged ``ml_read``
    so it is available in inspect mode only and never as part of an act-
    mode write sequence.
    """
    # ---- Step 1: validate proposed_time_factor against the closed enum ----
    if proposed_time_factor not in _ALLOWED_PROPOSED_TIME_FACTORS:
        return {
            "success": False,
            "error": (
                f"proposed_time_factor must be one of "
                f"{sorted(_ALLOWED_PROPOSED_TIME_FACTORS)}; "
                f"got {proposed_time_factor!r}."
            ),
        }

    service = _get_trackme_service(ctx)

    # ---- Step 2: read the entity's outlier rules from KV ----
    # Mirrors the lookup path used by the simulation REST endpoint itself
    # (see ``post_outliers_train_entity_model`` in
    # ``trackme_rest_handler_splk_outliers_engine_power.py``).
    rules_collection_name = (
        f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
    )
    try:
        rules_collection = service.kvstore[rules_collection_name]
        rules_record = rules_collection.data.query_by_id(object_id)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to read outliers rules for object_id={object_id}: {e}",
        }
    if not rules_record:
        return {
            "success": False,
            "error": (
                f"No outliers rules record found for tenant_id={tenant_id}, "
                f"component={component}, object_id={object_id}."
            ),
        }

    # ---- Step 3: locate the specific model_def inside entities_outliers ----
    entities_outliers = _parse_json_field(
        rules_record.get("entities_outliers", "{}"), default={}
    )
    target_model_def = _find_model_def_in_entities_outliers(
        entities_outliers, model_id
    )
    if not target_model_def:
        return {
            "success": False,
            "error": (
                f"model_id={model_id!r} not found in entities_outliers for "
                f"this entity. Verify the model_id via get_entity_outlier_context."
            ),
        }

    current_time_factor = target_model_def.get("time_factor", "")
    if current_time_factor == proposed_time_factor:
        return {
            "success": True,
            "model_id": model_id,
            "current_time_factor": current_time_factor,
            "proposed_time_factor": proposed_time_factor,
            "verdict": "neutral",
            "rationale": (
                f"Proposed time_factor equals the current time_factor "
                f"({current_time_factor!r}) — no simulation needed."
            ),
        }

    # ---- Step 4: snapshot the current model's fit quality ----
    current_fit = _get_current_model_fit(service, tenant_id, model_id)
    if "error" in current_fit:
        return {
            "success": False,
            "error": f"Failed to read current model fit: {current_fit['error']}",
        }

    # ---- Step 5: build the proposed model_json_def (clone + override) ----
    # Shallow clone is fine — we mutate only the top-level time_factor.
    proposed_model_def = dict(target_model_def)
    proposed_model_def["time_factor"] = proposed_time_factor

    # ---- Step 6: invoke the simulation endpoint ----
    entity_outlier_label = (
        rules_record.get("object") or rules_record.get("object_id") or object_id
    )
    simulation_response = _call_trackme_api(
        service,
        "trackme/v2/splk_outliers_engine/write/outliers_train_entity_model",
        body={
            "tenant_id": tenant_id,
            "component": component,
            "object_id": object_id,
            "mode": "simulation",
            "entity_outlier": entity_outlier_label,
            "entity_outlier_dict": target_model_def,
            "model_json_def": proposed_model_def,
        },
    )
    if "error" in simulation_response:
        return {
            "success": False,
            "error": f"Simulation endpoint failed: {simulation_response.get('error')}",
            "http_status": simulation_response.get("http_status"),
            "response_body": simulation_response.get("response_body"),
        }

    # ---- Step 7: extract the simulated model's fit quality ----
    proposed_groups_owner = _find_groups_dict(simulation_response)
    if not proposed_groups_owner:
        return {
            "success": False,
            "error": (
                "Simulation completed but the response did not carry a "
                "recognisable 'groups' fit structure. Cannot compare."
            ),
            "raw_response_keys": list(simulation_response.keys())
            if isinstance(simulation_response, dict) else [],
        }
    proposed_fit = _summarise_model_groups(proposed_groups_owner)

    # ---- Step 8: render the verdict ----
    verdict_info = _compare_fit_quality(current_fit, proposed_fit)

    return {
        "success": True,
        "model_id": model_id,
        "current_time_factor": current_time_factor,
        "proposed_time_factor": proposed_time_factor,
        "current": current_fit,
        "proposed": proposed_fit,
        "delta": {
            "avg_distance_score_delta": round(
                proposed_fit["avg_distance_score"]
                - current_fit["avg_distance_score"],
                4,
            ),
            "fitted_groups_delta": (
                proposed_fit["fitted_groups"] - current_fit["fitted_groups"]
            ),
        },
        "verdict": verdict_info["verdict"],
        "rationale": verdict_info["rationale"],
    }


# ===========================================================================
# WRITE TOOLS (7-11)
# ===========================================================================


@registry.tool(name="add_period_exclusion", tags=["ml_write"])
def add_period_exclusion(
    tenant_id: str,
    component: str,
    object_id: str,
    model_id: str,
    earliest: str,
    latest: str,
    reason: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Add a period exclusion to an ML model's training configuration.

    This excludes a specific time window from future model training, preventing
    anomalous data from polluting the model's learned boundaries. The next
    training cycle will skip data points within [earliest, latest].

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm", "dhm", "flx", "fqm", or "wlk"
        object_id: The entity's unique identifier
        model_id: The ML model identifier (use "all" to apply to all models)
        earliest: Start of exclusion window. STRONGLY PREFER an ISO date string
            like "2026-01-29" or "2026-01-29T00:00" — these are unambiguous and
            cannot drift. Epoch seconds and relative tokens ("-30d", "-90d")
            are accepted but discouraged: constructing 10-digit epochs from a
            date is arithmetic LLMs get wrong silently, and the resulting bad
            window will be rejected by the API or dropped by the trainer.
        latest: End of exclusion window. Same format rules as ``earliest``.
        reason: Your explanation for why this window should be excluded.

    IMPORTANT — value formats and validation:
        - The exclusion's ``latest`` MUST fall inside the model's training
          window (e.g. -30d). The API endpoint validates this and returns
          HTTP 400 with a clear message if the window is too old; in that
          case, fix the dates and retry — do not assume success.
        - ``earliest`` must be in the past and strictly before ``latest``.
        - ALWAYS use the current-time anchor in your initial context to
          pick valid dates — do not infer the year from training-data priors.

    Only use this when you have identified a genuine anomaly window that
    should NOT influence the model's understanding of "normal" behavior.
    """
    service = _get_trackme_service(ctx)

    result = _call_trackme_api(
        service,
        "trackme/v2/splk_outliers_engine/write/outliers_manage_model_period_exclusion",
        body={
            "tenant_id": tenant_id,
            "component": component,
            "object_id": object_id,
            "model_id": model_id,
            "action": "add",
            "earliest": str(earliest),
            "latest": str(latest),
            "update_comment": f"[AI Agent] {reason}",
        },
    )

    # Surface API-side validation failures as a non-success result, with the
    # rejection message lifted to the top level so the LLM can read it and
    # retry with corrected dates instead of treating a 4xx as a silent success.
    api_error = isinstance(result, dict) and bool(result.get("error"))
    out = {
        "success": not api_error,
        "model_id": model_id,
        "earliest": earliest,
        "latest": latest,
        "reason": reason,
        "response": result,
    }
    if api_error:
        out["error"] = result.get("error")
        out["http_status"] = result.get("http_status")
        # Lift the server's rejection text so the LLM reads it directly.
        out["error_message"] = result.get("response_body")
    return out


@registry.tool(name="trigger_model_retrain", tags=["ml_write"])
def trigger_model_retrain(
    tenant_id: str,
    component: str,
    object_id: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Trigger a live retrain of ML outlier models for an entity.

    Models are retrained and persisted, immediately updating the boundaries
    used for outlier detection. This is always a live operation.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm", "dhm", "flx", "fqm", or "wlk"
        object_id: The entity's unique identifier

    Best practice: after adding period exclusions, retrain to immediately update
    boundaries with clean data. Use get_model_training_details to review current
    model state before retraining.

    Note: Training runs asynchronously — this call returns immediately.
    Use get_model_training_details afterwards to check the new boundaries.
    """
    service = _get_trackme_service(ctx)

    result = _call_trackme_api(
        service,
        "trackme/v2/splk_outliers_engine/write/outliers_train_models",
        body={
            "tenant_id": tenant_id,
            "component": component,
            "object_id_list": object_id,
        },
    )

    return {
        "success": not _api_error(result),
        "object_id": object_id,
        "response": result,
    }


@registry.tool(name="set_false_positive", tags=["ml_write"])
def set_false_positive(
    tenant_id: str,
    component: str,
    object_id: str,
    reason: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Mark current outlier detections as false positive for an entity.

    This generates a negative score event that cancels the current outlier
    impact score, effectively returning the entity to a non-alerted state.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm", "dhm", "flx", "fqm", or "wlk"
        object_id: The entity's unique identifier
        reason: Your explanation for why this is a false positive

    NOTE: This is a temporary measure — if the outlier condition persists at the
    next evaluation cycle, a new positive score will be generated. For persistent
    issues, use add_period_exclusion + trigger_model_retrain instead.
    """
    service = _get_trackme_service(ctx)

    result = _call_trackme_api(
        service,
        "trackme/v2/splk_outliers_engine/write/outliers_set_false_positive",
        body={
            "tenant_id": tenant_id,
            "component": component,
            "object_id": object_id,
            "update_comment": f"[AI Agent] {reason}",
        },
    )

    return {
        "success": not _api_error(result),
        "object_id": object_id,
        "reason": reason,
        "response": result,
    }


@registry.tool(name="update_model_rules", tags=["ml_write"])
def update_model_rules(
    tenant_id: str,
    component: str,
    object_id: str,
    model_id: str,
    updates: dict,
    reason: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Update configuration parameters of an ML outlier model.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm", "dhm", "flx", "fqm", or "wlk"
        object_id: The entity's unique identifier
        model_id: The ML model identifier
        updates: Dict of field names to new values (see below)
        reason: Your explanation for why these changes are appropriate

    Updatable fields in 'updates':
        TIME & TRAINING:
        - time_factor: "%H" (hourly), "%w%H" (weekday+hour), "%H%M", "%w", "none"
        - period_calculation: "-30d", "-60d", "-12h", etc.
        - period_calculation_latest: "now" or "-Nd"
        - kpi_span: "10m", "1h", "5m", etc.
        - method_calculation: "avg", "sum", "min", "max", "stdev", "perc95", "latest"
        - kpi_metric: metric field name

        DENSITY THRESHOLDS:
        - density_lowerthreshold: float (e.g., 0.005 = 0.5% tail)
        - density_upperthreshold: float

        STATIC THRESHOLDS (override density, set to 0 to disable/clear):
        - static_lower_threshold: float (0 = disabled, use ML boundary)
        - static_upper_threshold: float (0 = disabled, use ML boundary)

        DEVIATION GUARDS:
        - perc_min_lowerbound_deviation: float (min % below boundary)
        - perc_min_upperbound_deviation: float
        - min_value_for_lowerbound_breached: float (absolute floor)
        - min_value_for_upperbound_breached: float

        ALERTING:
        - alert_lower_breached: 0 or 1
        - alert_upper_breached: 0 or 1
        - score: 0-100 (impact score weight)
        - auto_correct: 0 or 1
        - is_disabled: 0 or 1

    To clear a static threshold, set its value to 0 (e.g., {"static_upper_threshold": 0}).
    After updating, consider running trigger_model_retrain to apply the changes.
    """
    service = _get_trackme_service(ctx)

    # Tool-level guard: reject empty / non-dict ``updates`` outright.
    #
    # Real-world failure mode (May 2026 incident): the LLM expressed the
    # intended change perfectly in ``reason`` prose ("Update time_factor
    # to %w%H to account for weekly seasonality") but emitted ``updates={}``
    # as the structured arg. Without this guard the tool would happily
    # overlay nothing on top of ``current_config``, send the same record
    # back to the backend, get a 200, and report ``success: true``. The
    # agent would then re-read the model via ``get_entity_outlier_context``,
    # see the field unchanged, and retry indefinitely (15+ identical
    # tool calls observed in production until the user cancelled). Both
    # Sonnet and Gemini fumbled the structured arg under high reasoning
    # load — this is not a model-quality issue, it's a structured-output
    # robustness issue, and the right place to defend is here in the tool.
    #
    # Make the no-op LOUD: return ``success: false`` with explicit
    # guidance so the next agent turn can correct itself.
    if not isinstance(updates, dict) or len(updates) == 0:
        return {
            "success": False,
            "error": (
                "Empty `updates` argument. The `reason` field describes intent "
                "in prose but does not change anything — you must populate the "
                "`updates` dict with the field name(s) you want to change, e.g. "
                "`{\"time_factor\": \"%w%H\"}`. Do NOT retry this call without "
                "filling the `updates` arg."
            ),
            "model_id": model_id,
            "updates_applied": updates,
            "reason": reason,
        }

    # Tool-level guard: block model disable via is_disabled=1 in automated mode.
    if str(updates.get("is_disabled", "0")) == "1" and os.environ.get("TRACKME_AI_ALLOW_MODEL_DISABLE", "1") == "0":
        return {
            "success": False,
            "error": (
                "Blocked by tenant policy: setting is_disabled=1 on an ML model is not permitted "
                "in automated mode. Set ai_mladvisor_allow_model_disable=1 in the tenant "
                "AI Settings to enable automated model disablement, or run manually. "
                "Record this recommendation in your final response instead."
            ),
        }

    # The backend endpoint overwrites ALL model fields from the submitted rule.
    # To avoid wiping unmodified fields, we must fetch the current model config
    # first and merge the agent's updates on top.
    # Must match the backend's fields_list in post_outliers_update_models exactly
    # to avoid wiping fields not included in the submitted rule.
    UPDATABLE_FIELDS = [
        "score", "kpi_metric", "kpi_span", "method_calculation",
        "period_calculation", "period_calculation_latest", "time_factor",
        "density_lowerthreshold", "density_upperthreshold",
        "alert_lower_breached", "alert_upper_breached", "auto_correct",
        "perc_min_lowerbound_deviation", "perc_min_upperbound_deviation",
        "min_value_for_lowerbound_breached", "min_value_for_upperbound_breached",
        "static_lower_threshold", "static_upper_threshold",
        "algorithm", "boundaries_extraction_macro",
        "fit_extra_parameters", "apply_extra_parameters", "is_disabled",
        "ai_mladvisor_disabled",
    ]

    # Fetch current model config from the outliers summary endpoint.
    # Response format is a list of single-key dicts:
    # [{"model_id_1": {"rules": [...], "data": [...]}}, {"model_id_2": {...}}]
    # The rules array contains the model config fields we need to preserve.
    current_config = {}
    try:
        summary = _call_trackme_api(
            service,
            "trackme/v2/splk_outliers_engine/outliers_get_summary",
            body={
                "tenant_id": tenant_id,
                "component": component,
                "object_id": object_id,
            },
        )
        # Navigate the response structure to find this model's rules
        payload = summary if isinstance(summary, list) else summary.get("payload", summary)
        if isinstance(payload, list):
            for entry in payload:
                if isinstance(entry, dict) and model_id in entry:
                    model_data = entry[model_id]
                    # Extract config fields from the first rule in the rules array
                    rules = model_data.get("rules", []) if isinstance(model_data, dict) else []
                    if rules and isinstance(rules[0], dict):
                        current_config = rules[0]
                    break
    except Exception as e:
        logger.warning(f"Could not fetch current model config for merge: {e}")

    # Guard: if we couldn't retrieve the current config, refuse to proceed
    # to avoid sending a partial update that would wipe all unspecified fields.
    if not current_config:
        error_msg = (
            f"Cannot update model {model_id}: failed to retrieve current model configuration. "
            "Update aborted to prevent data loss from partial overwrites."
        )
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    # Build the complete rule: start from current config, overlay agent's updates
    rule_update = {"model_id": model_id}
    for field in UPDATABLE_FIELDS:
        if field in current_config:
            rule_update[field] = current_config[field]

    # Normalise the agent's updates the same way the backend will (None →
    # 0 for static thresholds) so the no-op comparison below is faithful.
    normalised_updates = {}
    for key, value in updates.items():
        if value is None and key in ("static_lower_threshold", "static_upper_threshold"):
            normalised_updates[key] = 0
        else:
            normalised_updates[key] = value

    # Tool-level guard (no-op detection): reject calls where every supplied
    # update already matches ``current_config``. Same root cause as the
    # empty-updates path — the LLM thinks it's making a change but the
    # values it supplied are identical to what's stored — and same
    # recovery: raise loud, don't silently succeed and let the agent loop.
    # Compare via str() to absorb the int/float/bool round-trip through
    # Splunk KV (everything resurfaces as a string).
    unchanged_fields = []
    changed_fields = []
    for key, new_value in normalised_updates.items():
        current_value = current_config.get(key)
        if str(new_value) == str(current_value):
            unchanged_fields.append({"field": key, "value": current_value})
        else:
            changed_fields.append(
                {"field": key, "from": current_value, "to": new_value}
            )

    if not changed_fields:
        return {
            "success": False,
            "error": (
                f"No-op update on model {model_id}: every field in `updates` "
                f"already matches the current model config. Either this change "
                f"was already applied in a prior turn, or the values you "
                f"supplied are identical to what is stored. DO NOT RETRY this "
                f"call with the same arguments — it will keep no-op'ing. If "
                f"the model still looks wrong to you, re-read it via "
                f"`get_entity_outlier_context` and propose a DIFFERENT change."
            ),
            "model_id": model_id,
            "updates_applied": updates,
            "unchanged_fields": unchanged_fields,
        }

    # Apply the (now-validated) updates on top
    for key, value in normalised_updates.items():
        rule_update[key] = value

    result = _call_trackme_api(
        service,
        "trackme/v2/splk_outliers_engine/write/outliers_update_models",
        body={
            "tenant_id": tenant_id,
            "component": component,
            "object_id": object_id,
            "outliers_rules": [rule_update],
            "update_comment": f"[AI Agent] {reason}",
        },
    )

    # Layer 1 belt & braces: even if the local pre-write diff said the
    # call would change something, ask the backend if anything actually
    # moved on disk. The handler returns ``any_changes_applied`` (and
    # per-model ``per_model_diffs.<model_id>.changed_fields``) as Layer 2
    # of this fix. If the local check passed but the backend reports no
    # change, flip success to False with a loud message — this catches
    # type-coercion edge cases (booleans, int/float string round-trips)
    # the local str()-comparison can miss.
    #
    # Unwrap pattern: Splunk's ``PersistentServerConnectionApplication``
    # delivers the handler's ``payload`` value as the HTTP response
    # body, so most TrackMe handlers' result records appear at the top
    # level of ``result``. A few legacy paths still nest under a
    # ``payload`` key. Mirror the established fallback pattern used by
    # ``outliers_get_summary`` above (``summary.get("payload", summary)``)
    # so we transparently handle both shapes — bugbot caught a regression
    # on PR #1481 cycle 1 where the fallback was ``{}`` and rendered
    # this whole cross-check dead code.
    backend_payload = (
        result.get("payload", result) if isinstance(result, dict) else {}
    )
    backend_any_changes = backend_payload.get("any_changes_applied")
    backend_per_model = backend_payload.get("per_model_diffs", {}) or {}
    backend_changed = backend_per_model.get(model_id, {}).get("changed_fields", {})

    success = not _api_error(result)
    if success and backend_any_changes is False:
        return {
            "success": False,
            "error": (
                f"Backend reported no fields changed on disk for model "
                f"{model_id}, despite the tool sending a non-trivial update. "
                f"This usually means a type-coercion mismatch (e.g. boolean "
                f"vs int) or that another caller wrote the same values "
                f"between read and write. DO NOT RETRY identical arguments. "
                f"Re-read the model via `get_entity_outlier_context` and "
                f"verify the field types match what the model expects."
            ),
            "model_id": model_id,
            "updates_applied": updates,
            "changed_fields_local": changed_fields,
            "changed_fields_backend": backend_changed,
            "response": result,
        }

    # Bubble up both the tool's pre-write diff and the backend's
    # authoritative post-write diff so the agent can self-validate.
    # When both are present and disagree, the backend version is the
    # source of truth (it reflects what's actually on disk).
    return {
        "success": success,
        "model_id": model_id,
        "updates_applied": updates,
        "reason": reason,
        "response": result,
        "changed_fields": changed_fields,
        "unchanged_fields": unchanged_fields,
        "backend_changed_fields": backend_changed,
        "backend_any_changes_applied": backend_any_changes,
    }


@registry.tool(name="manage_outlier_detection", tags=["ml_write"])
def manage_outlier_detection(
    tenant_id: str,
    component: str,
    object_id: str,
    action: str,
    reason: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Manage outlier detection state for an entity.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm", "dhm", "flx", "fqm", or "wlk"
        object_id: The entity's unique identifier
        action: One of:
            - "enable" — Enable outlier detection (sets is_disabled=0 on all models)
            - "disable" — Disable outlier detection (sets is_disabled=1)
            - "reset_status" — Clear current detection state (useful after model changes)
            - "run_monitor" — Re-evaluate entity against current boundaries (async)
        reason: Your explanation for this action

    Use reset_status after making significant model configuration changes
    to clear stale detection state. Use run_monitor to force immediate
    re-evaluation instead of waiting for the next scheduled cycle.
    """
    service = _get_trackme_service(ctx)

    # Map actions to the bulk action endpoint values
    valid_actions = {"enable", "disable", "reset_status", "run_monitor"}
    if action not in valid_actions:
        return {"success": False, "error": f"Invalid action: {action}. Must be one of: {valid_actions}"}

    # Tool-level guard: block model disable in automated mode unless tenant explicitly allows it.
    if action == "disable" and os.environ.get("TRACKME_AI_ALLOW_MODEL_DISABLE", "1") == "0":
        return {
            "success": False,
            "error": (
                "Blocked by tenant policy: disabling outlier detection is not permitted in "
                "automated mode. Set ai_mladvisor_allow_model_disable=1 in the tenant "
                "AI Settings to enable automated model disablement, or run manually. "
                "Record this recommendation in your final response instead."
            ),
        }

    # Map run_monitor to the API's expected action name
    api_action = "mlmonitor" if action == "run_monitor" else action

    result = _call_trackme_api(
        service,
        "trackme/v2/splk_outliers_engine/write/outliers_bulk_action",
        body={
            "tenant_id": tenant_id,
            "component": component,
            "keys_list": object_id,
            "action": api_action,
            "update_comment": f"[AI Agent] {reason}",
        },
    )

    return {
        "success": not _api_error(result),
        "object_id": object_id,
        "action": action,
        "reason": reason,
        "response": result,
    }


# ===========================================================================
# COMMON ENTITY-METADATA TOOLS
# ===========================================================================
#
# Tools below are shared across all FIVE specialised advisors (ML, Feed
# Lifecycle, FQM, FLX Threshold, Component Health). They are tagged with
# ``entity_metadata_write`` rather than the per-advisor ``<advisor>_write``
# tag so each advisor opts in by adding the tag to its ``allowed_tags``
# list (see ``_run_*_agent`` in each advisor lib). The Concierge Advisor
# stays out by design — it has no static write tools, mutations flow
# through ``propose_action`` → consent card → user-clicked REST endpoint.
#
# Each tool here wraps a TrackMe REST endpoint that already exists for
# all 6 components. The tool layer adds:
#  - LLM-friendly arguments (e.g. label *names* rather than KV ``_key``s)
#  - Mode multiplexing where the underlying API splits the operation
#    across multiple endpoints (e.g. labels: assign + remove are two
#    REST verbs, one tool with a ``mode`` parameter)
#
# Reason / audit-trail propagation, per tool family:
#  - **Notes (create)**: the agent's ``reason`` is prepended to the
#    note body itself as ``[AI Agent] <reason>: <note content>`` —
#    notes ARE the audit content, so this puts the reason in the
#    permanent record where humans / future audits read it.
#  - **Notes (delete)** and **Labels (all modes)**: the underlying
#    REST endpoints (``post_delete_note``, ``post_assign_labels``)
#    do not currently read an ``update_comment`` body field, so the
#    reason is captured in the agent's tool-response dict + the
#    SDK's reasoning trace + the audit-event ``user`` field, but
#    does not appear in the audit-event's ``update_comment``
#    column.  We pass ``update_comment`` in the body anyway for
#    forward compatibility — when the endpoints add support, this
#    tool benefits with no further change.  Tracked as a follow-up
#    backend enhancement (separate PR).
#
# See ``ai-context/policies/labels.md`` and ``ai-context/policies/notes.md``
# for the underlying feature documentation.


@registry.tool(name="manage_entity_labels", tags=["entity_metadata_write"])
def manage_entity_labels(
    tenant_id: str,
    component: str,
    object_id: str,
    mode: str,
    reason: str,
    # NOTE: ``list[str]`` (parameterised), NOT bare ``list``.  Bare
    # ``list`` produces a JSON schema of ``{"type": "array"}`` with no
    # ``items`` field; Anthropic / OpenAI / Mistral accept that, but
    # Google Gemini's strict JSONSchema validator rejects the entire
    # tool-list registration with HTTP 400:
    #
    #   GenerateContentRequest.tools[0].function_declarations[N]
    #   .parameters.properties[label_names].items: missing field
    #
    # which kills the whole agent run before any prompt is even sent.
    # ``list[str]`` gives the SDK enough info to emit
    # ``{"type": "array", "items": {"type": "string"}}``, which all
    # providers including Gemini accept.  Caught in a live demo on
    # gemini-pro-latest; reproducible on every Gemini model.
    label_names: list[str] = None,
    ctx: ToolContext = None,
) -> dict:
    """
    Assign / remove labels (curated coloured chips from the tenant's label
    catalog) on an entity.

    LABELS ARE NOT TAGS. Labels are a structured, catalog-backed feature
    with deliberate visual semantics — coloured chips picked from a curated
    per-tenant catalog (e.g. "blocked" / "under-review" / "in-progress" /
    "resolved" / "decommissioned" — 8 default labels seeded on tenant
    creation). Tags are a separate feature: free-form strings on a different
    KV path. Use this tool when the user mentions "label" / "lifecycle
    badge" / "coloured chip"; use the tags tool (when available) for
    free-form metadata.

    See ``ai-context/policies/labels.md`` for the full feature description
    and the side-by-side labels-vs-tags comparison.

    Parameters:
        tenant_id: The tenant identifier.
        component: The component type ("dsm", "dhm", "mhm", "flx", "fqm", "wlk").
        object_id: The entity's unique identifier (KV ``_key``).
        mode: One of:
            "set"    — replace the entity's current label set with ``label_names``.
            "add"    — add ``label_names`` to existing labels (idempotent — duplicates removed).
            "remove" — remove ``label_names`` from existing labels (idempotent).
            "clear"  — remove all labels from the entity (``label_names`` ignored).
        reason: Free-text rationale (audit trail; rendered in the per-entity
            Audit changes tab).
        label_names: List of label *names* (case-insensitive) — resolved
            against the tenant's label catalog. Required for "set" / "add" /
            "remove"; ignored for "clear".

    Returns:
        On success: ``{"success": True, "mode": str,
        "intended_label_names": list, "current_label_names_after": list,
        "reason": str, "response": <REST response>}``.

        On failure: ``current_label_names_after`` is OMITTED so an LLM
        cannot mistake the intended set for the actual on-disk state.
        ``intended_label_names`` is always present (records what the
        tool tried to apply); the LLM should rely on the ``success``
        flag plus ``response.error`` to reason about whether the
        change actually landed.

    Errors:
        - ``mode="set"|"add"|"remove"`` with empty ``label_names``.
        - Any name in ``label_names`` not present in the tenant's catalog
          (the tool does NOT auto-create labels — define them first via the
          ``/trackme/v2/labels/write/create_label`` admin endpoint, or via
          the LabelsManageModal in the UI).
        - Underlying REST failure (e.g. permissions, KV unavailable).
    """
    service = _get_trackme_service(ctx)

    valid_modes = ("set", "add", "remove", "clear")
    if mode not in valid_modes:
        return {
            "success": False,
            "error": (
                f"Invalid mode {mode!r}. Must be one of {valid_modes}. "
                f'"set" replaces the full label set, "add" / "remove" '
                f'are idempotent, "clear" removes all labels.'
            ),
            "mode": mode,
        }

    label_names = label_names or []
    if mode != "clear" and not label_names:
        return {
            "success": False,
            "error": (
                f"label_names is required for mode={mode!r} and must be "
                f"a non-empty list. Use mode='clear' to remove all labels."
            ),
            "mode": mode,
        }

    # 1. Read the tenant's label catalog (name → _key resolution).
    #
    # SHORT-CIRCUIT for ``mode="clear"``: clearing labels writes
    # ``label_ids=[]`` and never needs name resolution or catalog
    # validation, so a transient catalog-endpoint failure must NOT
    # break the clear path.  Bugbot caught this on PR #1495 cycle 2.
    catalog = []
    name_to_key = {}
    if mode != "clear":
        catalog_result = _call_trackme_api(
            service,
            "trackme/v2/labels/get_labels",
            body={"tenant_id": tenant_id},
        )
        # ``_call_trackme_api`` returns either:
        #   - The endpoint's JSON body on success.  For the ``get_labels``
        #     read endpoint Splunk's persistent-connection framework
        #     extracts the handler's ``payload`` field as the HTTP body,
        #     so the wire response is the LIST directly (not the
        #     ``{"payload": [...]}`` wrapper observed inside the handler
        #     source).  Calling ``.get(...)`` on that list raises
        #     ``'list' object has no attribute 'get'`` — production
        #     repro on entity ``siem-...:aws:config`` 2026-05-09.
        #   - On HTTP error: ``{"error": ..., "http_status": ...}`` —
        #     always a dict.
        # Guard the error check with ``isinstance(..., dict)`` so the
        # success path (list payload) falls through cleanly.
        if isinstance(catalog_result, dict) and catalog_result.get("error"):
            return {
                "success": False,
                "error": (
                    f"Failed to read label catalog for tenant {tenant_id!r}: "
                    f"{catalog_result.get('error')}"
                ),
                "mode": mode,
                "response": catalog_result,
            }
        # The catalog endpoint returns ``{"payload": [...labels...]}`` or
        # the list directly depending on the response shape. Handle both,
        # mirroring the unwrap pattern used elsewhere in this module.
        catalog = (
            catalog_result.get("payload", catalog_result)
            if isinstance(catalog_result, dict)
            else catalog_result
        )
        if isinstance(catalog, dict):
            # Some response paths nest under another ``payload``.
            catalog = catalog.get("labels", catalog.get("payload", catalog))
        if not isinstance(catalog, list):
            catalog = []

        # Build a lowercase-name → _key index for case-insensitive resolution.
        name_to_key = {
            str(lbl.get("label_name", "")).strip().lower(): lbl.get("_key")
            for lbl in catalog
            if isinstance(lbl, dict) and lbl.get("_key")
        }

    if mode != "clear":
        unknown = [n for n in label_names if n.strip().lower() not in name_to_key]
        if unknown:
            available = sorted(
                lbl.get("label_name", "") for lbl in catalog
                if isinstance(lbl, dict) and lbl.get("label_name")
            )
            return {
                "success": False,
                "error": (
                    f"Label name(s) not in catalog: {unknown}. The tool "
                    f"does NOT auto-create labels. Either reuse an existing "
                    f"label or have an admin create it first via "
                    f"``/trackme/v2/labels/write/create_label`` or the "
                    f"LabelsManageModal UI. Available labels in this "
                    f"tenant: {available}"
                ),
                "mode": mode,
                "unknown_label_names": unknown,
                "available_label_names": available,
            }
        target_keys = [name_to_key[n.strip().lower()] for n in label_names]
    else:
        target_keys = []

    # 2. Read current assignments (only needed for add / remove modes).
    #
    # IMPORTANT: the ``post_get_labels_for_object`` REST handler resolves
    # ``label_ids`` from the assignment record into full label objects with
    # the schema ``{"label_id": <key>, "label_name": ..., ...}`` — the
    # identifier field is ``label_id``, NOT ``_key``.  Bugbot caught this
    # on PR #1495 cycle 1: extracting ``_key`` left ``current_keys``
    # always empty, which silently turned ``mode="add"`` into ``set``
    # (replacing all labels) and ``mode="remove"`` into a destructive
    # full clear (removing every label).  Index by ``label_id``.  Bare
    # string entries are still tolerated for forward compatibility.
    #
    # ABORT EARLY ON READ FAILURE.  Bugbot caught a related data-loss
    # path on PR #1495 cycle 3: if the ``get_labels_for_object`` call
    # returns an error and we silently fall through with
    # ``current_keys = []``, the same data-loss pattern reappears —
    # ``mode="add"`` becomes "set" (losing existing labels),
    # ``mode="remove"`` becomes a full clear.  We can NOT safely
    # compute the new label set without knowing the current state, so
    # any read failure here aborts the call with a loud error rather
    # than risking silent data loss.  ``mode="set"`` and ``mode="clear"``
    # don't need the current state and stay unaffected.
    current_keys = []
    if mode in ("add", "remove"):
        current_result = _call_trackme_api(
            service,
            "trackme/v2/labels/get_labels_for_object",
            body={
                "tenant_id": tenant_id,
                "component": component,
                "object_id": object_id,
            },
        )
        # Same shape contract as the catalog read above — the
        # ``get_labels_for_object`` handler returns the resolved list
        # in its ``payload`` field, which the persistent-connection
        # framework unwraps; ``_call_trackme_api`` therefore returns
        # the list directly on success.  Only HTTP errors come back as
        # an ``{"error": ...}`` dict.  Guard the error check
        # accordingly to avoid the ``'list' object has no attribute
        # 'get'`` crash that wiped out the pre-PR-#1495-cycle-3
        # data-loss safety check.
        if isinstance(current_result, dict) and current_result.get("error"):
            return {
                "success": False,
                "error": (
                    f"Failed to read current label assignments for "
                    f"object_id={object_id!r} (mode={mode!r}): "
                    f"{current_result.get('error')}. Aborting to "
                    f"prevent silent data loss — without knowing the "
                    f"current label set we cannot compute the correct "
                    f"new set for 'add' / 'remove' modes "
                    f"(would degrade to 'set' or 'clear' respectively). "
                    f"Retry the call once the labels read endpoint is "
                    f"reachable, or use mode='set' / mode='clear' if "
                    f"you intend to overwrite the full set."
                ),
                "mode": mode,
                "intended_label_names": label_names,
                "response": current_result,
            }
        payload = (
            current_result.get("payload", current_result)
            if isinstance(current_result, dict)
            else current_result
        )
        if isinstance(payload, dict):
            payload = payload.get("labels", payload.get("payload", []))
        if isinstance(payload, list):
            for entry in payload:
                if isinstance(entry, dict):
                    # Prefer ``label_id`` (the documented field on the
                    # resolved response); fall back to ``_key`` only
                    # for forward compat in case the response shape
                    # changes upstream.
                    key = entry.get("label_id") or entry.get("_key")
                    if key:
                        current_keys.append(key)
                elif isinstance(entry, str):
                    current_keys.append(entry)

    # 3. Compute the new label set per mode.
    if mode == "set" or mode == "clear":
        new_keys = list(dict.fromkeys(target_keys))  # dedupe, preserve order
    elif mode == "add":
        new_keys = list(dict.fromkeys(current_keys + target_keys))
    elif mode == "remove":
        target_set = set(target_keys)
        new_keys = [k for k in current_keys if k not in target_set]

    # 4. Write — assign_labels replaces the full set.
    write_result = _call_trackme_api(
        service,
        "trackme/v2/labels/write/assign_labels",
        body={
            "tenant_id": tenant_id,
            "component": component,
            "object_id": object_id,
            "label_ids": new_keys,
            # Forward-compat: ignored by current handler, picked up
            # automatically when ``post_assign_labels`` adds
            # ``update_comment`` support (see module-level comment on
            # reason-propagation strategy).
            "update_comment": f"[AI Agent] {reason}" if reason else "[AI Agent] labels updated",
        },
    )
    success = not _api_error(write_result)
    # Resolve the intended set back to names for the agent's
    # self-validation — so the LLM doesn't have to reverse-map _keys
    # when reading the response.
    key_to_name = {
        lbl.get("_key"): lbl.get("label_name", "")
        for lbl in catalog
        if isinstance(lbl, dict) and lbl.get("_key")
    }
    intended_names = [key_to_name.get(k, k) for k in new_keys]

    # Response semantics (Bugbot caught the original confusion on PR #1495
    # cycle 2): ``intended_label_names`` is what we asked the backend to
    # apply — populated regardless of success.  ``current_label_names_after``
    # is the post-write ground-truth — only present when the write
    # actually succeeded.  An LLM reading a ``success: False`` response
    # therefore has no ground-truth field to misread; it sees the intent
    # alongside the explicit failure flag.
    response_dict = {
        "success": success,
        "mode": mode,
        "intended_label_names": intended_names,
        "reason": reason,
        "response": write_result,
    }
    if success:
        response_dict["current_label_names_after"] = intended_names
    return response_dict


@registry.tool(name="manage_entity_note", tags=["entity_metadata_write"])
def manage_entity_note(
    tenant_id: str,
    component: str,
    object_id: str,
    mode: str,
    reason: str,
    note: str = "",
    note_id: str = "",
    ctx: ToolContext = None,
) -> dict:
    """
    Manage free-form Markdown notes attached to an entity. Notes are operator
    annotations that don't affect monitoring state — investigation context,
    runbook references, known workarounds, cross-team handoffs.

    Notes are DIFFERENT from labels and tags:
        - Notes are long-form Markdown text blocks.
        - Labels are coloured chips from a curated catalog.
        - Tags are flat free-form strings.

    See ``ai-context/policies/notes.md`` for the full feature description.

    Parameters:
        tenant_id: The tenant identifier.
        component: The component type ("dsm", "dhm", "mhm", "flx", "fqm", "wlk").
            Optional in the underlying REST API but recommended — when
            provided, the audit event is scoped under
            ``object_category=splk-<component>`` so the note appears in
            the per-entity Audit changes tab. The tool always passes it
            since the agent always knows the component.
        object_id: The entity's unique identifier (KV ``_key``).
        mode: One of:
            "create" — attach a new note. Requires ``note`` (Markdown body).
            "delete" — remove a note by ``note_id`` (KV ``_key`` from the
                       read endpoint ``/trackme/v2/notes/get_notes_for_object``).
        reason: Free-text rationale (audit trail; separate from the note
            content itself — ``reason`` describes WHY the note is being
            attached / removed; ``note`` is the content the operator wants
            recorded).
        note: Markdown body. Required for ``mode="create"``; ignored for
            ``mode="delete"``.
        note_id: KV ``_key`` of the existing note to delete. Required for
            ``mode="delete"``; ignored for ``mode="create"``.

    Returns:
        ``{"success": bool, "mode": str, "note_id": str, "response": <REST response>}``

    Note: notes are immutable in TrackMe — there is no update verb. To
    "edit" a note: delete the old one and create a new one. The audit
    trail records both events.

    The ``clone_note`` REST verb (copy text to multiple targets) is
    intentionally NOT exposed here — if the agent needs to attach the
    same context to multiple entities, it should make N independent
    create calls with this tool.
    """
    service = _get_trackme_service(ctx)

    valid_modes = ("create", "delete")
    if mode not in valid_modes:
        return {
            "success": False,
            "error": (
                f"Invalid mode {mode!r}. Must be one of {valid_modes}. "
                f'"create" attaches a new note, "delete" removes an '
                f"existing note by note_id."
            ),
            "mode": mode,
        }

    if mode == "create":
        if not note or not str(note).strip():
            return {
                "success": False,
                "error": (
                    "note is required for mode='create' and must be a "
                    "non-empty string. Notes support Markdown — use "
                    "headings, lists, links, code fences as appropriate."
                ),
                "mode": mode,
            }
        # Embed the agent's ``reason`` directly into the note body so
        # it lands in the permanent record.  Notes are the audit
        # content; this is where the "why" belongs.  Skip the prefix
        # when reason is empty (callers shouldn't, but be defensive).
        # See module-level comment on reason-propagation strategy.
        note_body = str(note).strip()
        if reason and str(reason).strip():
            note_body = f"[AI Agent] {str(reason).strip()}\n\n{note_body}"
        result = _call_trackme_api(
            service,
            "trackme/v2/notes/write/create_note",
            body={
                "tenant_id": tenant_id,
                "object_id": object_id,
                "component": component,
                "note": note_body,
                # Forward-compat: ignored by the current handler, picked
                # up automatically when ``post_create_note`` adds
                # ``update_comment`` support.
                "update_comment": f"[AI Agent] {reason}" if reason else "[AI Agent] note created",
            },
        )
        success = not _api_error(result)
        # The handler returns the created record's _key in the response
        # so the agent can reference it later (e.g. to delete after a
        # follow-up turn). Tolerate both wrapped and unwrapped shapes.
        payload = (
            result.get("payload", result) if isinstance(result, dict) else result
        )
        created_note_id = ""
        if isinstance(payload, dict):
            created_note_id = (
                payload.get("note", {}).get("_key", "")
                if isinstance(payload.get("note"), dict)
                else payload.get("_key", "")
            )
        return {
            "success": success,
            "mode": mode,
            "note_id": created_note_id,
            "reason": reason,
            "response": result,
        }

    # mode == "delete"
    if not note_id or not str(note_id).strip():
        return {
            "success": False,
            "error": (
                "note_id is required for mode='delete' (the KV _key of "
                "the note to remove — obtainable via the read endpoint "
                "``/trackme/v2/notes/get_notes_for_object``)."
            ),
            "mode": mode,
        }
    # IMPORTANT: the ``post_delete_note`` REST handler reads
    # ``resp_dict.get("note_key")``, NOT ``_key``.  Bugbot caught this
    # on PR #1495 cycle 1 — sending ``_key`` would fail every delete
    # with "note_key is required".  The tool keeps its public
    # ``note_id`` parameter name (LLM-friendly) and translates here.
    result = _call_trackme_api(
        service,
        "trackme/v2/notes/write/delete_note",
        body={
            "tenant_id": tenant_id,
            "object_id": object_id,
            "component": component,
            "note_key": str(note_id).strip(),
            # Forward-compat: ignored by current handler, picked up
            # automatically when ``post_delete_note`` adds
            # ``update_comment`` support.
            "update_comment": f"[AI Agent] {reason}" if reason else "[AI Agent] note deleted",
        },
    )
    return {
        "success": not _api_error(result),
        "mode": mode,
        "note_id": str(note_id).strip(),
        "reason": reason,
        "response": result,
    }


# ---------------------------------------------------------------------------
# Per-entity maintenance mode (read + write)
# ---------------------------------------------------------------------------


@registry.tool(name="get_entity_maintenance", tags=["maintenance_read"])
def get_entity_maintenance(
    tenant_id: str,
    component: str,
    object_id: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Read the current per-entity maintenance state for one entity.

    Per-entity maintenance mode forces an entity into BLUE (protected) state for
    a defined time window. While active, the entity is shielded from alerting
    regardless of its underlying health (green/orange/red). This tool reports
    whether a window exists and whether it is currently active.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm", "dhm", "mhm", "flx", "fqm", or "wlk"
        object_id: The entity's unique identifier (object_id / _key)

    Returns a dict with ``is_under_maintenance`` (active right now), the window
    epochs, and the comment, or ``is_under_maintenance=False`` when there is no
    record / the window is not currently active.
    """
    service = _get_trackme_service(ctx)
    result = _call_trackme_api(
        service,
        "trackme/v2/entity_maintenance/list_maintenance",
        body={"tenant_id": tenant_id, "keys_list": [object_id]},
    )
    if isinstance(result, dict) and result.get("error"):
        return {
            "success": False,
            "object_id": object_id,
            "error": result.get("error"),
            "response": result,
        }
    records = (result or {}).get("records", []) if isinstance(result, dict) else []
    record = records[0] if records else {}
    return {
        "success": True,
        "object_id": object_id,
        "is_under_maintenance": bool(record.get("is_active", False)),
        "maintenance_start_epoch": record.get("maintenance_start_epoch"),
        "maintenance_end_epoch": record.get("maintenance_end_epoch"),
        "maintenance_comment": record.get("maintenance_comment", ""),
    }


@registry.tool(name="set_entity_maintenance", tags=["maintenance_write"])
def set_entity_maintenance(
    tenant_id: str,
    component: str,
    object_id: str,
    duration_minutes: int,
    reason: str,
    ctx: ToolContext = None,
) -> dict:
    """
    Place an entity into maintenance mode (force BLUE) for a duration starting now.

    While the window is active, the decision maker forces the entity into BLUE
    (protected) state with TOP precedence over every other state and protection
    layer, and alerting is suppressed. The entity returns to normal monitoring
    automatically once the window expires.

    The window STARTS NOW and runs for ``duration_minutes``. The tool computes
    the epoch boundaries server-side — you only supply a duration, never raw
    epochs (constructing epochs is error-prone for language models).

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm", "dhm", "mhm", "flx", "fqm", or "wlk"
        object_id: The entity's unique identifier (object_id / _key)
        duration_minutes: How long the maintenance window lasts, in minutes
            (e.g. 240 for 4 hours). Must be a positive integer.
        reason: Why this entity is being put under maintenance (surfaced in the
            status message, UI, and audit trail).

    Use this when an entity should be intentionally shielded (planned upgrade,
    known data gap, a remediation you are about to perform) so it does not page.
    """
    try:
        duration_minutes = int(duration_minutes)
    except (TypeError, ValueError):
        return {
            "success": False,
            "object_id": object_id,
            "error": "duration_minutes must be a positive integer",
        }
    if duration_minutes <= 0:
        return {
            "success": False,
            "object_id": object_id,
            "error": "duration_minutes must be a positive integer",
        }

    now = time.time()
    start_epoch = now
    end_epoch = now + (duration_minutes * 60)

    service = _get_trackme_service(ctx)
    result = _call_trackme_api(
        service,
        "trackme/v2/entity_maintenance/write/set_maintenance",
        body={
            "tenant_id": tenant_id,
            "component": component,
            "keys_list": [object_id],
            "maintenance_start_epoch": start_epoch,
            "maintenance_end_epoch": end_epoch,
            "maintenance_comment": reason,
            "update_comment": f"[AI Agent] {reason}",
        },
    )
    api_error = isinstance(result, dict) and bool(result.get("error"))
    out = {
        "success": not api_error,
        "object_id": object_id,
        "duration_minutes": duration_minutes,
        "maintenance_start_epoch": start_epoch,
        "maintenance_end_epoch": end_epoch,
        "reason": reason,
        "response": result,
    }
    if api_error:
        out["error"] = result.get("error")
        out["http_status"] = result.get("http_status")
    return out


@registry.tool(name="clear_entity_maintenance", tags=["maintenance_write"])
def clear_entity_maintenance(
    tenant_id: str,
    component: str,
    object_id: str,
    reason: str = "",
    ctx: ToolContext = None,
) -> dict:
    """
    End an entity's maintenance window immediately.

    Deletes the maintenance record so the entity returns to its computed state
    (green/orange/red) on the next decision-maker cycle. Idempotent — clearing
    an entity that is not under maintenance succeeds with no effect.

    Parameters:
        tenant_id: The tenant identifier
        component: The component type: "dsm", "dhm", "mhm", "flx", "fqm", or "wlk"
        object_id: The entity's unique identifier (object_id / _key)
        reason: Optional explanation for the audit trail.
    """
    service = _get_trackme_service(ctx)
    result = _call_trackme_api(
        service,
        "trackme/v2/entity_maintenance/write/clear_maintenance",
        body={
            "tenant_id": tenant_id,
            "keys_list": [object_id],
            "update_comment": f"[AI Agent] {reason}" if reason else "[AI Agent] maintenance cleared",
        },
    )
    api_error = isinstance(result, dict) and bool(result.get("error"))
    out = {
        "success": not api_error,
        "object_id": object_id,
        "reason": reason,
        "response": result,
    }
    if api_error:
        out["error"] = result.get("error")
        out["http_status"] = result.get("http_status")
    return out


# ---------------------------------------------------------------------------
# Entry point: run as MCP tool server when executed directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    registry.run()
