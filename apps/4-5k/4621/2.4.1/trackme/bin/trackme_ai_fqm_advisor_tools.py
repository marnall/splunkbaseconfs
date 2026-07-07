"""
TrackMe AI Agent Tools — FQM Advisor

Tool definitions for the Splunk Agent SDK, enabling the FQM (Field Quality
Monitoring) Advisor agent to inspect, analyze, and manage FQM tracker
entities, field quality thresholds, and data dictionary configurations.

Tools defined:
    READ (agent's "eyes"):
    1. get_fqm_entity_context            — Full entity config, metrics, thresholds,
                                            tenant-level default thresholds, linked
                                            dictionary name, CIM datamodel
    2. get_fqm_dictionary                — Read a full data dictionary and list
                                            trackers using it
    3. get_fqm_field_dictionary_entry    — Read a single field entry (regex,
                                            allow_unknown, allow_empty_or_missing)
    4. get_fqm_quality_history           — percent_success / percent_coverage stats
                                            broken down by day-of-week and
                                            hour-of-day, plus trend direction
    5. get_fqm_sampled_failures          — Inspect collect-job sampled failure
                                            events classified by type
    6. get_fqm_collect_job_context       — Collect + monitor saved search health
                                            and scheduler error counts
    7. get_fqm_peer_entity_thresholds    — Threshold calibration data from peer
                                            FQM entities on the same tracker
    8. get_fqm_datamodel_context         — CIM datamodel required/recommended
                                            fields and dictionary delta

    READ (regex experimentation — read-only):
    9. test_fqm_regex                    — Test a candidate regex against sampled
                                            field values, reporting match rate
                                            and up to 10 match/mismatch samples

    WRITE (agent's "hands"):
    10. add_fqm_threshold                — Add a new dynamic threshold
    11. update_fqm_threshold             — Recalibrate an existing threshold
    12. delete_fqm_threshold             — Remove a misconfigured threshold
    13. update_fqm_field_dictionary_entry — Update a single field in a dictionary
    14. update_fqm_dictionary_bulk       — Bulk update/add/delete fields in a
                                            dictionary (automated-mode safety cap)
    15. update_fqm_entity_state_priority — Update monitoring state or priority
                                            (automated decommission guarded by
                                            TRACKME_AI_COMPONENTS_ALLOW_DECOMMISSION)
"""

import json
import logging
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.ai.registry import ToolContext

from trackme_libs import run_splunk_search

# Share the single MCP registry with the other advisor tool modules so that
# all tools are served through the same tools.py MCP entry point. tools.py
# imports this module to trigger registration on the shared registry.
from trackme_ai_agent_tools import (
    registry,
    _get_trackme_service,
    _call_trackme_api,
    _api_error,
    _get_metrics_index,
)

# Named logger — shares the singleton configured by the parent
# REST handler's setup_logger() call (root logger redirect there means
# `logging.<level>(...)` here would bleed across handlers).
logger = logging.getLogger("trackme.rest.ai.fqm_advisor")


# ---------------------------------------------------------------------------
# Internal helpers (not exposed as tools)
# ---------------------------------------------------------------------------


def _build_fqm_metadata_search_constraint(fields_quality_summary) -> str:
    """
    Build the SPL metadata constraint string used to filter collect-job events
    for an FQM entity.

    Replicates the logic from package/lib/trackme_libs_splk_fqm.py: iterates the
    entity's ``fields_quality_summary`` (parsed JSON) for keys starting with
    ``metadata.`` and emits ``"<key>"="<value>"`` clauses joined by spaces.
    Returns ``"*"`` if no metadata keys are present — keeping behavior aligned
    with the UI-side constraint building.
    """
    metadata_constraint = "*"
    if not fields_quality_summary:
        return metadata_constraint
    try:
        if isinstance(fields_quality_summary, str):
            fqs = json.loads(fields_quality_summary)
        else:
            fqs = fields_quality_summary
        parts = []
        if isinstance(fqs, dict):
            for key, value in fqs.items():
                if isinstance(key, str) and key.startswith("metadata."):
                    parts.append(f'"{key}"="{value}"')
        if parts:
            metadata_constraint = " ".join(parts)
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        logger.warning(
            f"_build_fqm_metadata_search_constraint: failed to parse fields_quality_summary: {e}"
        )
    return metadata_constraint


def _lookup_fqm_entity_record(service, tenant_id: str, object_id: str) -> dict:
    """
    Look up a single FQM entity record directly from KV Store.

    Returns the raw record dict (with all schema fields) or ``{}`` on failure.
    Does NOT raise.
    """
    try:
        kv_name = f"kv_trackme_fqm_tenant_{tenant_id}"
        records = service.kvstore[kv_name].data.query(
            query=json.dumps({"_key": object_id})
        )
        if records:
            return dict(records[0])
    except Exception as e:
        logger.warning(
            f"_lookup_fqm_entity_record failed for tenant={tenant_id} object_id={object_id}: {e}"
        )
    return {}


def _read_fqm_dictionary_record(service, tenant_id: str, dictionary_name: str) -> dict:
    """
    Read a single FQM data dictionary record by name.

    Returns the raw KV record dict or ``{}`` if not found.
    """
    try:
        kv_name = f"kv_trackme_fqm_data_dictionary_tenant_{tenant_id}"
        records = service.kvstore[kv_name].data.query(
            query=json.dumps({"name": dictionary_name})
        )
        if records:
            return dict(records[0])
    except Exception as e:
        logger.warning(
            f"_read_fqm_dictionary_record failed for tenant={tenant_id} name={dictionary_name}: {e}"
        )
    return {}


def _parse_dictionary_fields(record: dict) -> list:
    """
    Parse the ``json_dict`` JSON string inside a dictionary KV record into a
    list of field entries ``[{name, regex, allow_unknown, allow_empty_or_missing}, ...]``.
    Returns an empty list on failure.
    """
    if not record:
        return []
    raw = record.get("json_dict", "")
    if not raw:
        return []
    try:
        if isinstance(raw, (list, dict)):
            parsed = raw
        else:
            parsed = json.loads(raw)
        if isinstance(parsed, dict):
            # Some dictionary shapes may wrap the list under a key
            for key in ("fields", "json_dict", "items"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
        if not isinstance(parsed, list):
            return []
        normalized = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            normalized.append({
                "name": item.get("name", item.get("field_name", "")),
                "regex": item.get("regex", ""),
                "allow_unknown": item.get("allow_unknown", ""),
                "allow_empty_or_missing": item.get("allow_empty_or_missing", ""),
            })
        return normalized
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"_parse_dictionary_fields parse error: {e}")
        return []


def _truncate_value(value, limit: int = 500) -> str:
    """Clip stringified value to ``limit`` chars for safety."""
    try:
        s = str(value) if value is not None else ""
    except Exception:
        s = ""
    if len(s) > limit:
        return s[:limit] + "...[truncated]"
    return s


# ===========================================================================
# READ TOOLS (1-8) + REGEX TEST (9)
# ===========================================================================


@registry.tool(tags=["fqm_advisor_read"])
async def get_fqm_entity_context(ctx: ToolContext, tenant_id: str, object_id: str) -> str:
    """
    Retrieve the full context of a FQM (Field Quality Monitoring) entity.

    Gathers entity identity (object, fieldname, fqm_type, tracker_name,
    tracker_index, dictionary_name), current quality metrics
    (percent_success, percent_coverage, metrics), all configured entity-specific
    thresholds AND tenant-level default thresholds, monitoring state,
    fields_quality_summary (JSON string with metadata.* breakdown fields), and
    the associated CIM datamodel (if any).

    The dictionary_name is inferred from the tracker configuration. If a
    dictionary cannot be determined, the field is returned as null.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store

    Returns:
        JSON string with keys: object_id, object, fieldname, fqm_type,
        tracker_name, tracker_index, collect_job_source, dictionary_name,
        percent_success, percent_coverage, metrics, thresholds,
        tenant_default_thresholds, monitored_state, priority, current_state,
        anomaly_reason, last_ingest_time, fields_quality_summary, cim_datamodel.
    """
    service = _get_trackme_service(ctx)

    result = _call_trackme_api(
        service,
        "trackme/v2/describe/entity",
        body={
            "tenant_id": tenant_id,
            "object_category": "splk-fqm",
            "object_id": object_id,
        },
        method="post",
    )

    if isinstance(result, dict) and result.get("error"):
        return json.dumps({
            "error": result.get("error"),
            "message": f"Failed to retrieve FQM entity context for object_id={object_id} in tenant={tenant_id}",
        })

    entity_context = {"object_id": object_id, "tenant_id": tenant_id}
    desc = {}
    identity = {}
    config = {}
    health = {}

    if isinstance(result, dict) and "entity_description" in result:
        desc = result["entity_description"]
        identity = desc.get("identity", {}) if isinstance(desc, dict) else {}
        config = desc.get("configuration", {}) if isinstance(desc, dict) else {}
        health = desc.get("health", {}) if isinstance(desc, dict) else {}

    # Also pull the raw KV record for fields that may not be surfaced through
    # /describe/entity (tracker_index, fields_quality_summary, fqm_type, dictionary_name).
    kv_record = _lookup_fqm_entity_record(service, tenant_id, object_id)

    tracker_name = identity.get("tracker_name") or kv_record.get("tracker_name", "")
    tracker_index = identity.get("tracker_index") or kv_record.get("tracker_index", "")
    fieldname = identity.get("fieldname") or kv_record.get("fieldname", "")
    fqm_type = identity.get("fqm_type") or kv_record.get("fqm_type", "")
    fields_quality_summary_raw = (
        identity.get("fields_quality_summary")
        or kv_record.get("fields_quality_summary", "")
    )

    # Extract cim_datamodel from fields_quality_summary metadata.datamodel if present
    cim_datamodel = None
    try:
        if isinstance(fields_quality_summary_raw, str) and fields_quality_summary_raw:
            fqs_parsed = json.loads(fields_quality_summary_raw)
        elif isinstance(fields_quality_summary_raw, dict):
            fqs_parsed = fields_quality_summary_raw
        else:
            fqs_parsed = {}
        if isinstance(fqs_parsed, dict):
            dm = fqs_parsed.get("metadata.datamodel")
            if dm:
                cim_datamodel = dm
    except (json.JSONDecodeError, TypeError):
        pass

    # dictionary_name: attempt to read from the KV record; not all entity records
    # carry this field directly — when absent we leave it null and the agent can
    # still call get_fqm_dictionary by name.
    dictionary_name = (
        kv_record.get("dictionary_name")
        or kv_record.get("fqm_dictionary_name")
        or identity.get("dictionary_name")
        or ""
    )

    # Fetch entity-specific thresholds and tenant-level defaults from KV Store
    entity_thresholds = []
    default_thresholds = []
    try:
        kv_name = f"kv_trackme_fqm_thresholds_tenant_{tenant_id}"
        records = service.kvstore[kv_name].data.query(
            query=json.dumps({"object_id": object_id})
        )
        entity_thresholds = [dict(r) for r in records] if records else []

        default_records = service.kvstore[kv_name].data.query(
            query=json.dumps({"object_id": "default"})
        )
        default_thresholds = [dict(r) for r in default_records] if default_records else []
    except Exception as e:
        logger.warning(f"FQM threshold KV query failed for {object_id}: {e}")

    collect_job_source = f"trackme:quality:{tracker_name}" if tracker_name else ""

    # Helper: prefer primary dict's value even when it is falsy-but-valid
    # (0, 0.0, {}, []).  Using ``a.get(k) or b.get(k)`` silently substitutes
    # the fallback when the primary value is a legitimate 0 / 0.0 / {},
    # which for quality metrics is exactly the state where the advisor is
    # most needed (percent_success == 0).  Only fall back when the primary
    # dict lacks the key or has it set to None.
    def _prefer_primary(primary, fallback, key, default):
        if key in primary and primary[key] is not None:
            return primary[key]
        return fallback.get(key, default)

    entity_context.update({
        "object": identity.get("object") or kv_record.get("object", ""),
        "fieldname": fieldname,
        "fqm_type": fqm_type,
        "tracker_name": tracker_name,
        "tracker_index": tracker_index,
        "collect_job_source": collect_job_source,
        "dictionary_name": dictionary_name or None,
        "percent_success": _prefer_primary(health, kv_record, "percent_success", ""),
        "percent_coverage": _prefer_primary(health, kv_record, "percent_coverage", ""),
        "metrics": _prefer_primary(health, kv_record, "metrics", {}),
        "thresholds": entity_thresholds,
        "tenant_default_thresholds": default_thresholds,
        "monitored_state": config.get("monitored_state") or kv_record.get("monitored_state", "unknown"),
        "priority": config.get("priority") or kv_record.get("priority", "unknown"),
        "current_state": health.get("object_state") or kv_record.get("object_state", "unknown"),
        "anomaly_reason": health.get("anomaly_reason") or kv_record.get("anomaly_reason", ""),
        "last_ingest_time": identity.get("last_ingest_time") or kv_record.get("last_ingest_time", ""),
        "fields_quality_summary": fields_quality_summary_raw,
        "cim_datamodel": cim_datamodel,
        "note": (
            "tenant_default_thresholds (object_id='default') are fallback thresholds applied "
            "when no entity-specific threshold matches. Entity-specific thresholds take precedence. "
            "If dictionary_name is null, use the tracker's data dictionary configuration via "
            "get_fqm_dictionary by passing the expected name."
        ),
    })
    return json.dumps(entity_context, default=str)


@registry.tool(tags=["fqm_advisor_read"])
async def get_fqm_dictionary(ctx: ToolContext, tenant_id: str, dictionary_name: str) -> str:
    """
    Retrieve a FQM data dictionary and the list of trackers that currently use it.

    The data dictionary defines per-field regex validation and whether unknown
    or empty values are tolerated. Multiple trackers can share a dictionary, so
    an edit to any field propagates to all of them — review trackers_using_this_dictionary
    carefully before using any of the dictionary-write tools.

    Args:
        tenant_id: The tenant identifier
        dictionary_name: The dictionary ``name`` field (unique per tenant)

    Returns:
        JSON string with keys: dictionary_name, mtime, fields
        (list of {name, regex, allow_unknown, allow_empty_or_missing}),
        trackers_using_this_dictionary (list).
    """
    service = _get_trackme_service(ctx)

    record = _read_fqm_dictionary_record(service, tenant_id, dictionary_name)
    if not record:
        return json.dumps({
            "error": f"Dictionary '{dictionary_name}' not found in tenant '{tenant_id}'",
            "dictionary_name": dictionary_name,
            "fields": [],
            "trackers_using_this_dictionary": [],
        })

    fields = _parse_dictionary_fields(record)

    # Ask the TrackMe API which trackers use this dictionary.
    trackers_using = []
    try:
        resp = _call_trackme_api(
            service,
            "trackme/v2/splk_fqm/fqm_dictionaries_by_trackers",
            body={"tenant_id": tenant_id, "dictionary_name": dictionary_name},
            method="post",
        )
        if isinstance(resp, dict):
            # The response shape can be {"payload": {...}}, a top-level dict keyed by
            # dictionary name, or a list — be defensive and flatten any shape to a
            # list of tracker identifiers.
            candidate = resp.get("payload", resp)
            if isinstance(candidate, dict):
                # look for this dictionary's entry
                entry = candidate.get(dictionary_name, candidate)
                if isinstance(entry, dict):
                    # common patterns: { trackers: [...] } or { tracker_name: {...}, ...}
                    if "trackers" in entry and isinstance(entry["trackers"], list):
                        trackers_using = entry["trackers"]
                    else:
                        trackers_using = list(entry.keys())
                elif isinstance(entry, list):
                    trackers_using = entry
            elif isinstance(candidate, list):
                trackers_using = candidate
    except Exception as e:
        logger.warning(
            f"get_fqm_dictionary: failed to query trackers for {dictionary_name}: {e}"
        )

    return json.dumps({
        "dictionary_name": dictionary_name,
        "mtime": record.get("mtime", ""),
        "fields": fields,
        "trackers_using_this_dictionary": trackers_using,
    }, default=str)


@registry.tool(tags=["fqm_advisor_read"])
async def get_fqm_field_dictionary_entry(
    ctx: ToolContext,
    tenant_id: str,
    dictionary_name: str,
    field_name: str,
) -> str:
    """
    Retrieve a single field's entry from a FQM data dictionary.

    Use this when the agent already knows the field name and only needs its
    validation config (regex, allow_unknown, allow_empty_or_missing) rather than
    the full dictionary. The response also indicates how many trackers share
    this dictionary, so the agent can assess blast radius before editing.

    Args:
        tenant_id: The tenant identifier
        dictionary_name: The dictionary ``name`` field
        field_name: The target field name inside the dictionary

    Returns:
        JSON string with keys: field_name, regex, allow_unknown,
        allow_empty_or_missing, dictionary_name, shared_with_n_trackers.
        If not found: {error, dictionary_name, field_name}.
    """
    service = _get_trackme_service(ctx)

    record = _read_fqm_dictionary_record(service, tenant_id, dictionary_name)
    if not record:
        return json.dumps({
            "error": "Dictionary not found",
            "dictionary_name": dictionary_name,
            "field_name": field_name,
        })

    fields = _parse_dictionary_fields(record)
    match = next((f for f in fields if f.get("name") == field_name), None)

    # Determine shared_with_n_trackers via the same endpoint used by get_fqm_dictionary.
    shared_n = 0
    try:
        resp = _call_trackme_api(
            service,
            "trackme/v2/splk_fqm/fqm_dictionaries_by_trackers",
            body={"tenant_id": tenant_id, "dictionary_name": dictionary_name},
            method="post",
        )
        if isinstance(resp, dict):
            candidate = resp.get("payload", resp)
            if isinstance(candidate, dict):
                entry = candidate.get(dictionary_name, candidate)
                if isinstance(entry, dict):
                    if "trackers" in entry and isinstance(entry["trackers"], list):
                        shared_n = len(entry["trackers"])
                    else:
                        shared_n = len(entry.keys())
                elif isinstance(entry, list):
                    shared_n = len(entry)
            elif isinstance(candidate, list):
                shared_n = len(candidate)
    except Exception as e:
        logger.warning(
            f"get_fqm_field_dictionary_entry: failed to count trackers for {dictionary_name}: {e}"
        )

    if not match:
        return json.dumps({
            "error": "Field not found",
            "dictionary_name": dictionary_name,
            "field_name": field_name,
            "available_fields": [f.get("name", "") for f in fields],
            "shared_with_n_trackers": shared_n,
        })

    return json.dumps({
        "field_name": field_name,
        "regex": match.get("regex", ""),
        "allow_unknown": match.get("allow_unknown", ""),
        "allow_empty_or_missing": match.get("allow_empty_or_missing", ""),
        "dictionary_name": dictionary_name,
        "shared_with_n_trackers": shared_n,
    }, default=str)


@registry.tool(tags=["fqm_advisor_read"])
async def get_fqm_quality_history(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
) -> str:
    """
    Retrieve FQM entity quality-metric history over the last 24 hours
    (detailed) and the last 7 days (aggregate), so the LLM can reason about
    whether the threshold values are calibrated against the metric's actual
    behaviour.

    Implementation
    --------------

    Runs two ``mstats`` searches against the tenant's metrics index
    (``trackme.splk.fqm.fields_quality.*`` family — the same data path that
    drives the TrackMe UI charts and the stateful alert-action chart
    generator).

    1. **Query A — 24h + 7d aggregate stats** via two separate
       ``mstats`` searches merged in Python by ``metric_name``. One row
       per FQM quality metric in the output, with 10 columns side-by-side
       (24h_latest_value / 24h_avg_value / 24h_max_value /
       24h_perc95_value / 24h_stdev_value, plus the same five for 7d).
       Lets the LLM spot drift at a glance. Splunk's ``appendcols`` was
       tried first but discarded: it does positional (row-number)
       matching, not key-based, so any difference in the two ``mstats``
       row sets silently attached 7d stats to the wrong ``metric_name``
       (PR #1530 cycle 1 finding).

    2. **Query B — per-metric 24h timeseries** at ``span=5m``, one search
       per metric_name discovered in Query A. Returns structured per-metric
       blocks so the LLM can spot plateaus, spikes, or ramps without having
       to demux interleaved rows itself.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store

    Returns:
        JSON string with:
        - ``aggregate_stats_24h_vs_7d``: array of {metric_name, 24h_*,
          7d_*} rows
        - ``timeseries_24h_per_metric``: dict mapping metric_name → list of
          {_time, value} buckets at 5-minute granularity

    Notes
    -----

    - FQM quality metrics are written to ``index=<metrics_idx>``
      (per-tenant, defaults to ``trackme_metrics``) with
      ``object_category="splk-fqm"`` and
      ``metric_name="trackme.splk.fqm.fields_quality.<short>"``.
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
    # (row-number) matching — not key-based — so a metric present in
    # only one window or different row ordering between the two
    # ``mstats`` runs would silently attach 7d stats to the wrong
    # metric_name.  Bugbot caught this on PR #1530 cycle 1 (Medium).
    # Two queries + dict merge by ``metric_name`` is bulletproof.
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
            'metric_name=trackme.splk.fqm.fields_quality.* '
            f'tenant_id="{tenant_id}" '
            'object_category="splk-fqm" '
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

    # Merge the two windows by ``metric_name`` (the only field that can
    # join the rows safely).  A metric present in one window but not the
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
                "No FQM quality metrics found for this entity in the last "
                "7 days. The entity may be newly created, the collect job "
                "may be silent (check Layer 1 via get_fqm_collect_job_context), "
                "or the metrics collection path may be broken upstream."
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
            'metric_name=trackme.splk.fqm.fields_quality.* '
            f'metric_name="{metric_name}" '
            f'tenant_id="{tenant_id}" '
            'object_category="splk-fqm" '
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
            "aggregate_stats_24h_vs_7d: one row per FQM quality metric (e.g. "
            "percent_success, percent_coverage) with 5 stats over the last "
            "24h side-by-side with 5 stats over the last 7d. Use this to "
            "spot drift (e.g. 24h_perc95 much lower than 7d_avg). "
            "timeseries_24h_per_metric: 5-minute buckets per metric over the "
            "last 24h. Use this to spot quality degradation timing / patterns."
        ),
    }, default=str)


@registry.tool(tags=["fqm_advisor_read"])
async def get_fqm_sampled_failures(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    limit: int = 50,
) -> str:
    """
    Inspect collect-job sampled failure events for an FQM entity.

    Queries the tracker's raw collect-job events in its tracker_index, filters
    by the entity's fieldname and ``status=failure``, and classifies each
    failure as is_missing / is_empty / is_unknown / regex_failure. This is the
    agent's direct window into *why* the field is failing quality checks —
    e.g. if 90% of failures are ``is_empty``, a regex tweak won't help; if
    most are ``regex_failure``, the regex is too strict for real-world values.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store
        limit: Maximum number of sampled failure events to return (default 50)

    Returns:
        JSON string with keys: field_name, total_failures_sampled,
        by_classification (counts for is_missing, is_empty, is_unknown,
        regex_failure), sample_events (list of {value, is_missing, is_empty,
        is_unknown, regex_failure, _time}; values truncated to 500 chars).
    """
    service = _get_trackme_service(ctx)

    kv_record = _lookup_fqm_entity_record(service, tenant_id, object_id)
    if not kv_record:
        return json.dumps({
            "error": f"FQM entity not found for object_id={object_id} in tenant={tenant_id}",
            "field_name": "",
            "total_failures_sampled": 0,
            "by_classification": {"is_missing": 0, "is_empty": 0, "is_unknown": 0, "regex_failure": 0},
            "sample_events": [],
        })

    fieldname = kv_record.get("fieldname", "")
    tracker_name = kv_record.get("tracker_name", "")
    tracker_index = kv_record.get("tracker_index", "")
    metadata_constraint = _build_fqm_metadata_search_constraint(
        kv_record.get("fields_quality_summary", "")
    )

    if not (fieldname and tracker_name and tracker_index):
        return json.dumps({
            "error": "Entity record missing fieldname/tracker_name/tracker_index",
            "field_name": fieldname,
            "total_failures_sampled": 0,
            "by_classification": {"is_missing": 0, "is_empty": 0, "is_unknown": 0, "regex_failure": 0},
            "sample_events": [],
        })

    capped_limit = min(max(1, int(limit or 50)), 500)

    spl = (
        f'search index={tracker_index} sourcetype=trackme:fields_quality '
        f'source="trackme:quality:{tracker_name}" {metadata_constraint} '
        f'| trackmefieldsqualityextract '
        f'| where fieldname="{fieldname}" AND status="failure" '
        f'| table _time, value, is_missing, is_empty, is_unknown, regex_failure '
        f'| head {capped_limit}'
    )

    search_params = {
        "earliest_time": "-7d@d",
        "latest_time": "now",
        "output_mode": "json",
        "count": 0,
    }

    sample_events = []
    counts = {"is_missing": 0, "is_empty": 0, "is_unknown": 0, "regex_failure": 0}

    def _truthy(v):
        try:
            if v is None:
                return False
            if isinstance(v, bool):
                return v
            s = str(v).strip().lower()
            return s in ("1", "true", "yes", "y")
        except Exception:
            return False

    try:
        reader = run_splunk_search(service, spl, search_params, max_retries=3)
        for result in reader:
            if not isinstance(result, dict):
                continue
            is_missing = _truthy(result.get("is_missing"))
            is_empty = _truthy(result.get("is_empty"))
            is_unknown = _truthy(result.get("is_unknown"))
            regex_failure = _truthy(result.get("regex_failure"))
            if is_missing:
                counts["is_missing"] += 1
            if is_empty:
                counts["is_empty"] += 1
            if is_unknown:
                counts["is_unknown"] += 1
            if regex_failure:
                counts["regex_failure"] += 1

            sample_events.append({
                "_time": result.get("_time", ""),
                "value": _truncate_value(result.get("value", "")),
                "is_missing": is_missing,
                "is_empty": is_empty,
                "is_unknown": is_unknown,
                "regex_failure": regex_failure,
            })
    except Exception as e:
        return json.dumps({
            "error": f"Sampled failures search failed: {str(e)}",
            "field_name": fieldname,
            "total_failures_sampled": 0,
            "by_classification": counts,
            "sample_events": [],
        })

    return json.dumps({
        "tenant_id": tenant_id,
        "object_id": object_id,
        "field_name": fieldname,
        "tracker_name": tracker_name,
        "total_failures_sampled": len(sample_events),
        "by_classification": counts,
        "sample_events": sample_events,
    }, default=str)


@registry.tool(tags=["fqm_advisor_read"])
async def get_fqm_collect_job_context(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
) -> str:
    """
    Report on the health of the FQM tracker's collect-job and monitor saved
    searches, plus recent scheduler error counts.

    Looks up the entity's ``tracker_name`` and queries Splunk's saved_searches
    endpoint for two saved searches:
      - ``<tracker_name>_wrapper*``  (the collect phase — samples raw data)
      - ``<tracker_name>_tracker*``  (the monitor phase — updates entity state)

    Computes ``hours_since_last_success`` as the max across both. Also counts
    scheduler errors in the last 7 days via an ``index=_internal`` query, which
    may be ACL-restricted — on failure the tool returns
    ``scheduler_errors_7d=null, scheduler_errors_7d_query_failed=true`` instead
    of raising.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store

    Returns:
        JSON string with keys: tracker_name, collect_saved_search
        (name, is_scheduled, cron_schedule, last_success_time, is_healthy),
        monitor_saved_search (same shape), hours_since_last_success,
        is_healthy (combined), scheduler_errors_7d, scheduler_errors_7d_query_failed.
    """
    service = _get_trackme_service(ctx)

    kv_record = _lookup_fqm_entity_record(service, tenant_id, object_id)
    if not kv_record:
        return json.dumps({
            "error": f"FQM entity not found for object_id={object_id}",
            "tracker_name": "",
        })

    tracker_name = kv_record.get("tracker_name", "")
    if not tracker_name:
        return json.dumps({
            "error": "Entity record missing tracker_name",
            "tracker_name": "",
        })

    def _lookup_saved_search(prefix: str) -> dict:
        """Find first saved search whose name starts with prefix; summarize it."""
        info = {
            "name": None,
            "is_scheduled": None,
            "cron_schedule": None,
            "last_success_time": None,
            "is_healthy": None,
        }
        try:
            for ss in service.saved_searches:
                try:
                    if ss.name and ss.name.startswith(prefix):
                        info["name"] = ss.name
                        content = ss.content or {}
                        is_scheduled = content.get("is_scheduled", "0")
                        info["is_scheduled"] = str(is_scheduled) in ("1", "true", "True")
                        info["cron_schedule"] = content.get("cron_schedule", "") or None
                        # next_scheduled_time / last_success indicators are not
                        # always present — attempt multiple field names.
                        last_ok = (
                            content.get("last_success_time")
                            or content.get("dispatch.latest_time")
                            or None
                        )
                        info["last_success_time"] = last_ok
                        # A saved search is considered healthy if scheduled and has run.
                        info["is_healthy"] = bool(info["is_scheduled"]) and bool(last_ok)
                        break
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"_lookup_saved_search failed for prefix={prefix}: {e}")
        return info

    collect_ss = _lookup_saved_search(f"{tracker_name}_wrapper")
    monitor_ss = _lookup_saved_search(f"{tracker_name}_tracker")

    # hours_since_last_success: max of the two (max means "oldest", i.e. worst)
    # Since last_success_time format is unpredictable, we leave this as null
    # when we can't parse a usable timestamp and let the agent interpret.
    hours_since_last_success = None

    overall_is_healthy = bool(collect_ss.get("is_healthy")) and bool(monitor_ss.get("is_healthy"))

    # Scheduler errors in last 7 days — optional; may be ACL-restricted.
    scheduler_errors_7d = None
    scheduler_errors_7d_query_failed = False
    try:
        spl = (
            f'search index=_internal source=*scheduler.log* '
            f'savedsearch_name="{tracker_name}_*" log_level=ERROR earliest=-7d@d latest=now '
            f'| stats count'
        )
        search_params = {
            "earliest_time": "-7d@d",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }
        reader = run_splunk_search(service, spl, search_params, max_retries=2)
        for r in reader:
            if isinstance(r, dict) and "count" in r:
                try:
                    scheduler_errors_7d = int(float(r.get("count", 0) or 0))
                except (ValueError, TypeError):
                    scheduler_errors_7d = None
                break
        if scheduler_errors_7d is None:
            scheduler_errors_7d = 0
    except Exception as e:
        logger.warning(f"Scheduler error count query failed (ACL restricted?): {e}")
        scheduler_errors_7d = None
        scheduler_errors_7d_query_failed = True

    return json.dumps({
        "tenant_id": tenant_id,
        "object_id": object_id,
        "tracker_name": tracker_name,
        "collect_saved_search": collect_ss,
        "monitor_saved_search": monitor_ss,
        "hours_since_last_success": hours_since_last_success,
        "is_healthy": overall_is_healthy,
        "scheduler_errors_7d": scheduler_errors_7d,
        "scheduler_errors_7d_query_failed": scheduler_errors_7d_query_failed,
    }, default=str)


@registry.tool(tags=["fqm_advisor_read"])
async def get_fqm_peer_entity_thresholds(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
) -> str:
    """
    Retrieve threshold configurations from peer FQM entities sharing the same tracker.

    Looks up the tracker_name for the current entity, then finds all other FQM
    entities monitored by the same tracker that have configured thresholds.
    Entities sharing a tracker are typically monitoring the same CIM data model
    field across multiple sources, making them the most relevant calibration
    peers.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash (excluded from peer results)

    Returns:
        JSON string with keys: peer_count, tracker_name, peer_thresholds
        (list of {peer_object, metric_name, value, operator, condition_true,
        score}), metric_calibration_summary (per-metric stats across peers).
    """
    service = _get_trackme_service(ctx)

    # Look up tracker_name + fieldname for this entity
    entity_tracker = ""
    entity_object = ""
    entity_fieldname = ""
    try:
        kv_name = f"kv_trackme_fqm_tenant_{tenant_id}"
        records = service.kvstore[kv_name].data.query(
            query=json.dumps({"_key": object_id})
        )
        if records:
            entity_tracker = records[0].get("tracker_name", "")
            entity_object = records[0].get("object", "")
            entity_fieldname = records[0].get("fieldname", "")
    except Exception as e:
        return json.dumps({"error": f"Failed to look up entity tracker_name: {str(e)}"})

    if not entity_tracker:
        return json.dumps({
            "peer_count": 0,
            "message": f"Could not determine tracker_name for object_id={object_id} — cannot find peers.",
            "peer_thresholds": [],
            "metric_calibration_summary": {},
        })

    search_params = {
        "earliest_time": "-5m",
        "latest_time": "now",
        "output_mode": "json",
        "count": 0,
    }

    spl_peers = (
        f'| inputlookup kv_trackme_fqm_tenant_{tenant_id} '
        f'| search tracker_name="{entity_tracker}" monitored_state="enabled" '
        f'| where _key!="{object_id}" '
        f'| fields _key, object, fieldname '
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
                    "fieldname": result.get("fieldname", ""),
                })
    except Exception as e:
        return json.dumps({"error": f"Failed to query peer FQM entities: {str(e)}"})

    if not peers:
        return json.dumps({
            "peer_count": 0,
            "tracker_name": entity_tracker,
            "current_fieldname": entity_fieldname,
            "current_object": entity_object,
            "message": f"No peer FQM entities found with tracker_name='{entity_tracker}' in tenant='{tenant_id}'",
            "peer_thresholds": [],
            "metric_calibration_summary": {},
        })

    peer_ids = [p["peer_object_id"] for p in peers if p["peer_object_id"]]
    peer_id_map = {p["peer_object_id"]: p["object"] for p in peers}

    if not peer_ids:
        return json.dumps({
            "peer_count": 0,
            "tracker_name": entity_tracker,
            "message": "No valid peer object IDs found",
            "peer_thresholds": [],
            "metric_calibration_summary": {},
        })

    peer_ids_quoted = " ".join(f'"{pid}"' for pid in peer_ids)
    spl_thresholds = (
        f'| inputlookup kv_trackme_fqm_thresholds_tenant_{tenant_id} '
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
        logger.warning(f"FQM peer thresholds search failed: {e}")

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
        "tracker_name": entity_tracker,
        "current_object": entity_object,
        "current_fieldname": entity_fieldname,
        "peer_count": len(peers),
        "peers": [
            {"object": p["object"], "object_id": p["peer_object_id"], "fieldname": p.get("fieldname", "")}
            for p in peers
        ],
        "peer_thresholds": peer_thresholds,
        "metric_calibration_summary": metric_calibration_summary,
    }, default=str)


@registry.tool(tags=["fqm_advisor_read"])
async def get_fqm_datamodel_context(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
) -> str:
    """
    Retrieve the CIM datamodel context for a FQM entity and diff it against
    the currently configured data dictionary.

    If the entity is not CIM-based (no ``metadata.datamodel`` key in
    ``fields_quality_summary``), returns ``{applicable: false, reason: ...}``.
    Otherwise runs ``| trackmefieldsqualitygendict datamodel=<dm>
    show_only_recommended_fields=false`` to fetch required vs recommended CIM
    fields, then compares them to the configured dictionary fields and returns
    which required fields are missing from the dictionary and which dictionary
    fields are not in the CIM model.

    Never raises — any failure returns ``{applicable: false, error: ...}``.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store

    Returns:
        JSON string. On success (CIM applicable): ``{applicable: true,
        datamodel, required_fields, recommended_fields,
        current_dictionary_delta: {missing_from_dictionary, extra_in_dictionary}}``.
        Otherwise: ``{applicable: false, reason|error: "..."}``.
    """
    try:
        service = _get_trackme_service(ctx)

        kv_record = _lookup_fqm_entity_record(service, tenant_id, object_id)
        if not kv_record:
            return json.dumps({
                "applicable": False,
                "error": f"FQM entity not found for object_id={object_id}",
            })

        fqs_raw = kv_record.get("fields_quality_summary", "")
        datamodel = None
        try:
            if isinstance(fqs_raw, str) and fqs_raw:
                fqs = json.loads(fqs_raw)
            elif isinstance(fqs_raw, dict):
                fqs = fqs_raw
            else:
                fqs = {}
            datamodel = fqs.get("metadata.datamodel") if isinstance(fqs, dict) else None
        except (json.JSONDecodeError, TypeError):
            datamodel = None

        if not datamodel:
            return json.dumps({
                "applicable": False,
                "reason": "entity is not CIM-based",
            })

        # Run the gendict command to enumerate CIM fields
        spl = (
            f'| trackmefieldsqualitygendict datamodel="{datamodel}" '
            f'show_only_recommended_fields=false'
        )
        search_params = {
            "earliest_time": "-5m",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }
        required_fields = []
        recommended_fields = []
        try:
            reader = run_splunk_search(service, spl, search_params, max_retries=2)
            for result in reader:
                if not isinstance(result, dict):
                    continue
                fname = result.get("name", result.get("field_name", ""))
                if not fname:
                    continue
                is_recommended = str(result.get("is_recommended", "")).strip().lower() in ("1", "true", "yes")
                is_required = str(result.get("is_required", "")).strip().lower() in ("1", "true", "yes")
                if is_required:
                    required_fields.append(fname)
                if is_recommended:
                    recommended_fields.append(fname)
            # Fallback: if neither flag was populated, treat all as recommended
            if not required_fields and not recommended_fields:
                # Re-scan to grab every name field at least
                pass
        except Exception as e:
            return json.dumps({
                "applicable": False,
                "error": f"trackmefieldsqualitygendict search failed: {str(e)}",
                "datamodel": datamodel,
            })

        # Resolve the entity's dictionary and diff field sets
        dict_name = (
            kv_record.get("dictionary_name")
            or kv_record.get("fqm_dictionary_name")
            or ""
        )
        dict_fields = []
        if dict_name:
            rec = _read_fqm_dictionary_record(service, tenant_id, dict_name)
            dict_fields = [f.get("name", "") for f in _parse_dictionary_fields(rec) if f.get("name")]

        required_set = set(required_fields)
        recommended_set = set(recommended_fields)
        dict_set = set(dict_fields)

        missing_from_dictionary = sorted(required_set - dict_set)
        extra_in_dictionary = sorted(dict_set - (required_set | recommended_set))

        return json.dumps({
            "applicable": True,
            "datamodel": datamodel,
            "dictionary_name": dict_name or None,
            "required_fields": sorted(required_set),
            "recommended_fields": sorted(recommended_set),
            "current_dictionary_delta": {
                "missing_from_dictionary": missing_from_dictionary,
                "extra_in_dictionary": extra_in_dictionary,
            },
        }, default=str)
    except Exception as e:
        # Defensive: this tool must never raise
        logger.error(f"get_fqm_datamodel_context unexpected failure: {e}")
        return json.dumps({
            "applicable": False,
            "error": f"Unexpected failure: {str(e)}",
        })


@registry.tool(tags=["fqm_advisor_read"])
async def test_fqm_regex(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    candidate_regex: str,
    sample_size: int = 100,
) -> str:
    """
    Test a candidate regex pattern against real sampled values for an FQM entity's field.

    This is the FQM Advisor's core experimentation tool: before proposing a
    regex change via update_fqm_field_dictionary_entry, the agent should call
    this tool to verify the new pattern matches the bulk of real field values
    and identify edge cases. Returns the match rate and up to 10 match and 10
    mismatch samples so the agent can explain the tradeoff concretely.

    The tool:
      1. Validates the regex via ``re.compile`` — returns ``compile_error`` on failure.
      2. Queries sampled field values (ALL statuses, not just failures) using the
         entity's tracker_index + tracker_name + metadata constraint.
      3. Classifies each sampled value against the candidate regex in Python.

    Never raises — always returns structured JSON.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash in KV Store
        candidate_regex: The regex to test (must be a valid Python regex)
        sample_size: Max number of sample values to pull (default 100, max 1000)

    Returns:
        JSON string with keys: candidate_regex, sample_size (actual count
        retrieved), match_count, mismatch_count, match_rate_pct (one decimal),
        sample_matches (up to 10 matching values, truncated to 500 chars),
        sample_mismatches (up to 10 non-matching values), compile_error
        (null or error string).
    """
    try:
        # 1. Validate regex
        try:
            compiled = re.compile(candidate_regex)
        except re.error as e:
            return json.dumps({
                "candidate_regex": candidate_regex,
                "sample_size": 0,
                "match_count": 0,
                "mismatch_count": 0,
                "match_rate_pct": 0.0,
                "sample_matches": [],
                "sample_mismatches": [],
                "compile_error": str(e),
            })

        service = _get_trackme_service(ctx)
        kv_record = _lookup_fqm_entity_record(service, tenant_id, object_id)
        if not kv_record:
            return json.dumps({
                "candidate_regex": candidate_regex,
                "sample_size": 0,
                "match_count": 0,
                "mismatch_count": 0,
                "match_rate_pct": 0.0,
                "sample_matches": [],
                "sample_mismatches": [],
                "compile_error": None,
                "error": f"FQM entity not found for object_id={object_id}",
            })

        fieldname = kv_record.get("fieldname", "")
        tracker_name = kv_record.get("tracker_name", "")
        tracker_index = kv_record.get("tracker_index", "")
        metadata_constraint = _build_fqm_metadata_search_constraint(
            kv_record.get("fields_quality_summary", "")
        )

        if not (fieldname and tracker_name and tracker_index):
            return json.dumps({
                "candidate_regex": candidate_regex,
                "sample_size": 0,
                "match_count": 0,
                "mismatch_count": 0,
                "match_rate_pct": 0.0,
                "sample_matches": [],
                "sample_mismatches": [],
                "compile_error": None,
                "error": "Entity record missing fieldname/tracker_name/tracker_index",
            })

        capped_size = min(max(1, int(sample_size or 100)), 1000)

        spl = (
            f'search index={tracker_index} sourcetype=trackme:fields_quality '
            f'source="trackme:quality:{tracker_name}" {metadata_constraint} '
            f'| trackmefieldsqualityextract '
            f'| where fieldname="{fieldname}" '
            f'| table value '
            f'| head {capped_size}'
        )

        search_params = {
            "earliest_time": "-7d@d",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }

        # Keep the *raw* values for regex matching — production FQM validation
        # runs ``re.match`` against the full, unmodified field value.  If we
        # truncate here we'd be classifying against an artificial string
        # (potentially ending in our own ``"...[truncated]"`` marker), which
        # changes the regex verdict for any value >500 chars.  Truncation is
        # a *display* concern for the sample_matches / sample_mismatches
        # returned in the response, NOT a matching concern.
        sample_values = []
        try:
            reader = run_splunk_search(service, spl, search_params, max_retries=2)
            for result in reader:
                if isinstance(result, dict):
                    v = result.get("value", "")
                    sample_values.append(v)
        except Exception as e:
            return json.dumps({
                "candidate_regex": candidate_regex,
                "sample_size": 0,
                "match_count": 0,
                "mismatch_count": 0,
                "match_rate_pct": 0.0,
                "sample_matches": [],
                "sample_mismatches": [],
                "compile_error": None,
                "error": f"Sample value search failed: {str(e)}",
            })

        match_count = 0
        mismatch_count = 0
        sample_matches = []
        sample_mismatches = []

        for value in sample_values:
            try:
                # Use ``match`` to mirror production FQM validation exactly.
                # ``trackmefieldsquality.py`` classifies a value as a regex
                # failure via ``not re.match(regex_pattern, str(item))`` — so
                # the regex is anchored at the *start* of the value only, not
                # at the end.  Using ``search`` (anywhere) would over-report;
                # using ``fullmatch`` (both ends) would under-report and lead
                # the agent to commit an unnecessarily permissive regex.
                # ``re.match`` is the exact production semantic.
                #
                # We match against the raw value but only store the
                # *truncated* form in the response samples, so oversized
                # values don't blow the tool output size without affecting
                # classification.
                if compiled.match(value):
                    match_count += 1
                    if len(sample_matches) < 10:
                        sample_matches.append(_truncate_value(value))
                else:
                    mismatch_count += 1
                    if len(sample_mismatches) < 10:
                        sample_mismatches.append(_truncate_value(value))
            except Exception:
                mismatch_count += 1
                if len(sample_mismatches) < 10:
                    sample_mismatches.append(_truncate_value(value))

        total = match_count + mismatch_count
        rate = round((match_count / total) * 100, 1) if total > 0 else 0.0

        return json.dumps({
            "candidate_regex": candidate_regex,
            "sample_size": len(sample_values),
            "match_count": match_count,
            "mismatch_count": mismatch_count,
            "match_rate_pct": rate,
            "sample_matches": sample_matches,
            "sample_mismatches": sample_mismatches,
            "compile_error": None,
        }, default=str)
    except Exception as e:
        logger.error(f"test_fqm_regex unexpected failure: {e}")
        return json.dumps({
            "candidate_regex": candidate_regex,
            "sample_size": 0,
            "match_count": 0,
            "mismatch_count": 0,
            "match_rate_pct": 0.0,
            "sample_matches": [],
            "sample_mismatches": [],
            "compile_error": None,
            "error": f"Unexpected failure: {str(e)}",
        })


# ===========================================================================
# WRITE TOOLS (10-15)
# ===========================================================================


@registry.tool(tags=["fqm_advisor_write"])
async def add_fqm_threshold(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    metric_name: str,
    operator: str,
    value: float,
    condition_true: bool,
    score: int,
    comment: str,
    reason: str,
) -> str:
    """
    Add a new dynamic threshold to a FQM entity for a specific field quality metric.

    Creates a threshold rule that fires when the metric meets the condition.
    FQM metrics are stored in the entity's metrics JSON dict. Key metrics:
      - percent_success:  % of events where required fields parse correctly
      - percent_coverage: % of events containing the monitored fields

    Example: metric_name='percent_success', operator='<', value=95.0,
    condition_true=True alerts when success rate drops below 95%.

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash
        metric_name: The FQM metric name (e.g. 'percent_success', 'percent_coverage')
        operator: '<', '>', '<=', '>=', '==', '!='
        value: Threshold numeric value
        condition_true: True = alert when condition matches; False = inverse
        score: Impact score 0-100 (100 = critical)
        comment: Short description of the threshold's purpose
        reason: Agent's rationale — REQUIRED. Appended to comment if not already there.

    Returns:
        JSON string with API response including the new threshold _key.
    """
    service = _get_trackme_service(ctx)

    valid_operators = ("<", ">", "<=", ">=", "==", "!=")
    if operator not in valid_operators:
        return json.dumps({
            "error": f"Invalid operator '{operator}'. Must be one of: {valid_operators}"
        })

    if not reason or not reason.strip():
        return json.dumps({
            "error": "reason is required and must not be empty when adding a threshold."
        })

    full_comment = comment or ""
    if reason and reason not in full_comment:
        full_comment = f"{full_comment} | reason: {reason}" if full_comment else f"reason: {reason}"

    body = {
        "tenant_id": tenant_id,
        "keys_list": [object_id],
        "metric_name": metric_name,
        "value": value,
        "operator": operator,
        "condition_true": condition_true,
        "score": score,
        "comment": full_comment,
    }
    result = _call_trackme_api(service, "trackme/v2/splk_fqm/write/fqm_thresholds_add", body)
    return json.dumps({
        "success": not (isinstance(result, dict) and result.get("error")),
        "metric_name": metric_name,
        "reason": reason,
        "api_response": result,
    }, default=str)


@registry.tool(tags=["fqm_advisor_write"])
async def update_fqm_threshold(
    ctx: ToolContext,
    tenant_id: str,
    threshold_key: str,
    metric_name: str,
    operator: str,
    value: float,
    condition_true: bool,
    score: int,
    comment: str,
    reason: str,
) -> str:
    """
    Update an existing FQM threshold's value, operator, or score.

    Use this to recalibrate a threshold that is firing too often (too tight)
    or missing real quality regressions (too loose). Requires the threshold
    _key from ``get_fqm_entity_context``.

    Args:
        tenant_id: The tenant identifier
        threshold_key: The threshold record _key to update
        metric_name: The FQM metric name (required for the update API)
        operator: New comparison operator
        value: New threshold value
        condition_true: New condition direction
        score: New impact score
        comment: Updated description
        reason: Agent's rationale — REQUIRED. Appended to comment.

    Returns:
        JSON string confirming the update.
    """
    service = _get_trackme_service(ctx)

    valid_operators = ("<", ">", "<=", ">=", "==", "!=")
    if operator not in valid_operators:
        return json.dumps({
            "error": f"Invalid operator '{operator}'. Must be one of: {valid_operators}"
        })

    if not reason or not reason.strip():
        return json.dumps({
            "error": "reason is required and must not be empty when updating a threshold."
        })

    full_comment = comment or ""
    if reason and reason not in full_comment:
        full_comment = f"{full_comment} | reason: {reason}" if full_comment else f"reason: {reason}"

    body = {
        "tenant_id": tenant_id,
        "threshold_key": threshold_key,
        "metric_name": metric_name,
        "value": value,
        "operator": operator,
        "condition_true": condition_true,
        "score": score,
        "comment": full_comment,
    }
    result = _call_trackme_api(service, "trackme/v2/splk_fqm/write/fqm_thresholds_update", body)
    return json.dumps({
        "success": not (isinstance(result, dict) and result.get("error")),
        "threshold_key": threshold_key,
        "metric_name": metric_name,
        "reason": reason,
        "api_response": result,
    }, default=str)


@registry.tool(tags=["fqm_advisor_write"])
async def delete_fqm_threshold(
    ctx: ToolContext,
    tenant_id: str,
    threshold_key: str,
    reason: str,
) -> str:
    """
    Delete a FQM threshold that is misconfigured or superseded.

    IMPORTANT: Only delete thresholds when there is clear evidence they are
    causing false positives or have been replaced by a corrected configuration.
    The ``reason`` argument is REQUIRED and validated server-side; this tool
    additionally validates non-empty locally.

    Args:
        tenant_id: The tenant identifier
        threshold_key: The threshold record _key to delete
        reason: Explanation of why this threshold is being removed — REQUIRED.

    Returns:
        JSON string confirming deletion.
    """
    service = _get_trackme_service(ctx)

    if not reason or not reason.strip():
        return json.dumps({
            "success": False,
            "error": "reason is required for delete",
        })

    body = {
        "tenant_id": tenant_id,
        "threshold_key": threshold_key,
        "update_comment": reason,
    }
    result = _call_trackme_api(service, "trackme/v2/splk_fqm/write/fqm_thresholds_del", body)
    if isinstance(result, dict) and result.get("error"):
        return json.dumps({
            "success": False,
            "deleted": False,
            "threshold_key": threshold_key,
            "reason": reason,
            "error": result.get("error"),
            "api_response": result,
        })
    return json.dumps({
        "success": True,
        "deleted": True,
        "threshold_key": threshold_key,
        "reason": reason,
        "api_response": result,
    }, default=str)


@registry.tool(tags=["fqm_advisor_write"])
async def update_fqm_field_dictionary_entry(
    ctx: ToolContext,
    tenant_id: str,
    dictionary_name: str,
    field_name: str,
    regex: str,
    allow_unknown: str,
    allow_empty_or_missing: str,
    reason: str,
) -> str:
    """
    Update a single field's validation config in a FQM data dictionary.

    Edits the regex / allow_unknown / allow_empty_or_missing flags for
    ``field_name`` within ``dictionary_name``. This change propagates to EVERY
    tracker that uses this dictionary — always call ``get_fqm_dictionary``
    first to confirm blast radius.

    ``allow_unknown`` and ``allow_empty_or_missing`` must be the strings
    ``"true"`` or ``"false"`` (Splunk convention, not Python booleans).

    Args:
        tenant_id: The tenant identifier
        dictionary_name: The dictionary ``name`` field
        field_name: The target field name inside the dictionary
        regex: New regex pattern (should be tested via test_fqm_regex first)
        allow_unknown: "true" | "false"
        allow_empty_or_missing: "true" | "false"
        reason: Agent's rationale — REQUIRED.

    Returns:
        JSON string with keys: success, field_name, dictionary_name, reason, api_response.
    """
    service = _get_trackme_service(ctx)

    if not reason or not reason.strip():
        return json.dumps({
            "success": False,
            "error": "reason is required and must not be empty when updating a dictionary field.",
        })

    if allow_unknown not in ("true", "false") or allow_empty_or_missing not in ("true", "false"):
        return json.dumps({
            "success": False,
            "error": "allow_unknown and allow_empty_or_missing must be the strings 'true' or 'false'.",
        })

    body = {
        "tenant_id": tenant_id,
        "dictionary_name": dictionary_name,
        "action": "update_fields",
        "fields_list": [{
            "field_name": field_name,
            "regex": regex,
            "allow_unknown": allow_unknown,
            "allow_empty_or_missing": allow_empty_or_missing,
        }],
        "update_comment": reason,
    }
    result = _call_trackme_api(service, "trackme/v2/splk_fqm/write/fqm_update_data_dictionary", body)
    return json.dumps({
        "success": not (isinstance(result, dict) and result.get("error")),
        "field_name": field_name,
        "dictionary_name": dictionary_name,
        "reason": reason,
        "api_response": result,
    }, default=str)


@registry.tool(tags=["fqm_advisor_write"])
async def update_fqm_dictionary_bulk(
    ctx: ToolContext,
    tenant_id: str,
    dictionary_name: str,
    action: str,
    fields_list_json: str,
    reason: str,
) -> str:
    """
    Bulk update / add / delete multiple fields in a FQM data dictionary.

    Use for atomic dictionary changes touching multiple fields. In automated
    mode (``TRACKME_AI_AUTOMATED=1``) the tool enforces a safety cap of 5
    fields per call; interactive runs can pass more. Deletes require a non-empty
    ``reason``.

    Args:
        tenant_id: The tenant identifier
        dictionary_name: The dictionary ``name`` field
        action: one of ``"update_fields"``, ``"add_field"``, ``"delete_fields"``
        fields_list_json: JSON string encoding a list of field objects. Each
            field object must match the endpoint spec for the given action:
              - update_fields: {"field_name", "regex", "allow_unknown", "allow_empty_or_missing"}
              - add_field:     same as update_fields
              - delete_fields: [{"field_name": "..."}, ...]
        reason: Agent's rationale. REQUIRED for ``delete_fields`` action.

    Returns:
        JSON string: {success, dictionary_name, action, fields_count, reason, api_response}.
    """
    service = _get_trackme_service(ctx)

    allowed_actions = {"update_fields", "add_field", "delete_fields"}
    if action not in allowed_actions:
        return json.dumps({
            "success": False,
            "error": f"Invalid action '{action}'. Must be one of: {sorted(allowed_actions)}",
        })

    # Validate fields_list_json
    try:
        fields_list = json.loads(fields_list_json)
    except (TypeError, json.JSONDecodeError) as e:
        return json.dumps({
            "success": False,
            "error": f"fields_list_json is not valid JSON: {e}",
        })

    if not isinstance(fields_list, list):
        return json.dumps({
            "success": False,
            "error": "fields_list_json must decode to a JSON list.",
        })

    if len(fields_list) == 0:
        return json.dumps({
            "success": False,
            "error": "fields_list must contain at least one field.",
        })

    # Automated-mode safety cap
    if os.environ.get("TRACKME_AI_AUTOMATED") == "1" and len(fields_list) > 5:
        return json.dumps({
            "success": False,
            "error": (
                f"Automated-mode safety cap exceeded: {len(fields_list)} fields requested, "
                "max 5 per call. Safety rail — interactive mode can override."
            ),
        })

    # Deletes require a reason
    if action == "delete_fields" and (not reason or not reason.strip()):
        return json.dumps({
            "success": False,
            "error": "reason is required and must not be empty for delete_fields.",
        })

    body = {
        "tenant_id": tenant_id,
        "dictionary_name": dictionary_name,
        "action": action,
        "fields_list": fields_list,
        "update_comment": reason or "",
    }
    result = _call_trackme_api(service, "trackme/v2/splk_fqm/write/fqm_update_data_dictionary", body)
    return json.dumps({
        "success": not (isinstance(result, dict) and result.get("error")),
        "dictionary_name": dictionary_name,
        "action": action,
        "fields_count": len(fields_list),
        "reason": reason,
        "api_response": result,
    }, default=str)


@registry.tool(tags=["fqm_advisor_write"])
async def update_fqm_entity_state_priority(
    ctx: ToolContext,
    tenant_id: str,
    object_id: str,
    reason: str,
    monitored_state: str = None,
    priority: str = None,
) -> str:
    """
    Update a FQM entity's monitoring state or priority level.

    Use ``monitored_state='disabled'`` for FQM trackers covering data models or
    fields that are no longer in use, or whose underlying data source has been
    retired. Only disable if there is clear evidence the tracker has produced
    no quality data in 14+ days.

    Use ``priority`` to escalate CIM compliance monitoring for critical data
    models (e.g. Authentication, Endpoint) or downgrade less critical ones.

    Priority levels: critical, high, medium, low, pending.

    Automated decommission guard: in automated mode
    (``TRACKME_AI_AUTOMATED=1``), setting ``monitored_state='disabled'``
    requires the env var ``TRACKME_AI_COMPONENTS_ALLOW_DECOMMISSION=1``.
    This unified env var is shared across the four component advisors
    (Feed Lifecycle, FLX Threshold, FQM, Component Health) — it replaces
    the old per-advisor ``TRACKME_AI_FQM_ALLOW_DECOMMISSION``.  It is
    propagated by ``_run_fqm_advisor_agent`` from the tenant's
    ``ai_components_advisor_allow_decommission`` config, so interactive
    runs effectively bypass this guard (they leave the env var at ``"0"``
    but also set ``TRACKME_AI_AUTOMATED=0``, so the guard never fires).

    Args:
        tenant_id: The tenant identifier
        object_id: The entity _key hash
        reason: Your explanation for this change — REQUIRED. Include evidence,
            e.g. "FQM tracker has produced no quality data in 21 days."
        monitored_state: Optional new state: 'enabled' or 'disabled'
        priority: Optional new priority: critical | high | medium | low | pending

    Returns:
        JSON string confirming the changes applied.
    """
    service = _get_trackme_service(ctx)

    if not reason or not reason.strip():
        return json.dumps({
            "success": False,
            "error": "reason is required and must not be empty.",
        })

    changes_applied = []
    body = {
        "tenant_id": tenant_id,
        "keys_list": [object_id],
        "update_comment": reason,
    }

    if monitored_state is not None:
        if monitored_state not in ("enabled", "disabled"):
            return json.dumps({
                "success": False,
                "error": f"Invalid monitored_state '{monitored_state}'. Must be 'enabled' or 'disabled'.",
            })

        # Automated decommission guard — unified env var across the four
        # component advisors (Feed Lifecycle / FLX Threshold / FQM /
        # Component Health).
        if monitored_state == "disabled" and os.environ.get("TRACKME_AI_AUTOMATED") == "1":
            if os.environ.get("TRACKME_AI_COMPONENTS_ALLOW_DECOMMISSION", "0") != "1":
                return json.dumps({
                    "success": False,
                    "error": (
                        "decommissioning blocked by tenant policy "
                        "(ai_components_advisor_allow_decommission=0)"
                    ),
                })

        body["monitored_state"] = monitored_state
        changes_applied.append(f"monitored_state={monitored_state}")

    if priority is not None:
        valid_priorities = ("critical", "high", "medium", "low", "pending")
        if priority not in valid_priorities:
            return json.dumps({
                "success": False,
                "error": f"Invalid priority '{priority}'. Must be one of: {valid_priorities}",
            })
        body["priority"] = priority
        changes_applied.append(f"priority={priority}")

    if not changes_applied:
        return json.dumps({
            "success": False,
            "error": "No changes specified. Provide monitored_state and/or priority.",
        })

    result = _call_trackme_api(service, "trackme/v2/splk_fqm/write/fqm_bulk_edit", body)
    return json.dumps({
        "success": not (isinstance(result, dict) and result.get("error")),
        "changes_applied": changes_applied,
        "reason": reason,
        "api_response": result,
    }, default=str)


# ---------------------------------------------------------------------------
# Entry point: run as MCP tool server when executed directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    registry.run()
