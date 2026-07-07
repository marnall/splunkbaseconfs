#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_hybrid_trackers.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Built-in libraries
import hashlib
import json
import os
import sys
import time
from collections import OrderedDict

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_hybrid_trackers_admin",
    "trackme_rest_api_splk_hybrid_trackers_admin.log",
)


# import rest handler
import trackme_rest_handler

# import TrackMe libs
from trackme_libs import (
    run_splunk_search,
    trackme_audit_event,
    trackme_create_macro,
    trackme_create_report,
    trackme_delete_macro,
    trackme_delete_tenant_object_summary,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_reqinfo,
    trackme_send_to_tcm,
)

# TrackMe splk-feeds libs
from trackme_libs_splk_feeds import (
    splk_dsm_hybrid_tracker_simulation_return_searches,
    _build_dhm_extras_eval_fragments,
    generate_lookups_report_search,
)

# import trackme licensing libs
from trackme_libs_licensing import trackme_check_license
from trackme_libs_utils import sanitize_spl_input, sanitize_spl_quoted_arg

# import trackme libs croniter
from trackme_libs_croniter import validate_cron_schedule

# import Splunk libs
import splunklib.client as client


# Reserved field names that may not appear in breakby_extra_fields for DHM.
# Two sets are merged here:
#
#   1. Operator-facing collisions — names that would either double-count
#      in the SPL split-by or shadow existing knobs. The implicit DHM
#      dimensions (index, sourcetype), the entity identifier slot (host),
#      the optional splunk_server dimension already controlled by
#      dhm_tstats_root_breakby_include_splunk_server, and the time
#      dimension.
#
#   2. Pipeline-internal column names that the read-path silently strips
#      when building the overview SPL — see
#      trackme_rest_handler_splk_dhm_user.py:322-326. Without rejecting
#      these at the front door, a REST caller bypassing the wizard
#      could POST e.g. breakby_extra_fields=["idx"]; the entity would
#      accept it and the metrics pipeline would group by it (yielding
#      a NULL-valued dimension on every event), but the overview
#      per-extras donut would never render because the read-path
#      drops it. Keep the two lists in lock-step — both reserved, both
#      rejected at the front door.
_DHM_RESERVED_EXTRA_FIELDS = frozenset([
    # operator-facing collisions
    "host", "index", "sourcetype", "splunk_server", "_time",
    # pipeline-internal column names — must mirror the strip list in
    # trackme_rest_handler_splk_dhm_user.py:322-326
    "object", "object_id", "idx", "st", "alias", "tenant_id",
    "object_category",
])
# Static cap on the number of extra metadata dimensions per tracker. Each
# extra dimension multiplies the per-host combo cardinality, and the
# pipeline enforces a hard 100-combos-per-host cap downstream — five
# dimensions is already an aggressive cardinality budget for that ceiling.
_DHM_EXTRA_FIELDS_MAX = 5
# Allowed character set for extras field names. We splice the field name
# unquoted into the SPL `stats by <field>` clause downstream (both in the
# pie root search and in per-extra donut post-processors), so the name
# must be a valid Splunk field identifier. Splunk field names can contain
# dots for nested-field style (e.g. `vendor.product`); anything outside
# this allowlist is either an SPL injection vector or a name Splunk can't
# query anyway. Defending here keeps the bad input out of every consumer
# (pie root search, metrics emission, donut wiring) at the front door.
import re as _re
_DHM_EXTRA_FIELD_PATTERN = _re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def _normalize_breakby_extra_fields(raw, breakby_field, is_merged):
    """Validate, dedupe and normalize breakby_extra_fields submitted to the
    DHM hybrid-tracker simulation / create endpoints.

    Returns (normalized_list, error_message_or_None). Empty/None input is
    valid and yields ([], None). On any validation failure the function
    returns (None, message) so the caller can short-circuit with a 400.
    """
    if raw is None or raw == "":
        return [], None
    # accept a CSV string for convenience (the wizard sends a JSON array,
    # but the REST endpoint should accept either form for power users)
    if isinstance(raw, str):
        raw = [x for x in raw.split(",")]
    if not isinstance(raw, (list, tuple)):
        return None, "breakby_extra_fields must be a JSON array of field names (or a comma-separated string)"
    # Mode-compatibility short-circuits — surface these before the
    # per-item loop so a reserved-name or invalid-name complaint can't
    # mask the more actionable "wrong mode" diagnosis. Both Merged and
    # Standard modes are incompatible with extras by design.
    #
    # `breakby_field is None` here means the caller passed None, "none",
    # or "merged" upstream — the call-site filter collapses those three
    # to None and passes `is_merged` separately. So:
    #   - is_merged True            → Merged mode → reject
    #   - is_merged False AND       → Standard mode → reject (this is
    #     breakby_field is None        the gap bugbot flagged on PR #1575:
    #                                  the wizard's UI gate prevents this
    #                                  case but a raw REST API caller
    #                                  bypassing the wizard could submit
    #                                  Standard + extras and have it
    #                                  silently accepted prior to this
    #                                  guard)
    #   - is_merged False AND       → Custom mode (or Standard-with-host;
    #     breakby_field is not None    ambiguous at the wire level so we
    #                                  accept it as Custom-with-host —
    #                                  the wizard never sends extras
    #                                  outside Custom anyway)
    has_any_value = any(
        (item is not None and str(item).strip() != "") for item in raw
    )
    if has_any_value:
        if is_merged:
            return None, (
                "breakby_extra_fields cannot be combined with merged mode "
                "(merged mode collapses the per-sourcetype dimension; extras would defeat that)"
            )
        if breakby_field is None:
            return None, (
                "breakby_extra_fields require Custom mode. Pass a breakby_field "
                "value to opt in (you may use 'host' if you only want extras "
                "without changing the host identifier). Submitting extras with "
                "breakby_field=None or 'none' (Standard mode) is rejected because "
                "the documented contract scopes extras to Custom mode."
            )
    normalized = []
    seen = set()
    for item in raw:
        if item is None:
            continue
        name = str(item).strip()
        if not name:
            continue
        if name in seen:
            continue
        if name in _DHM_RESERVED_EXTRA_FIELDS:
            return None, (
                f'breakby_extra_fields: "{name}" is reserved and cannot be used as an extra dimension '
                f'(reserved: {sorted(_DHM_RESERVED_EXTRA_FIELDS)})'
            )
        if breakby_field and name == breakby_field:
            return None, (
                f'breakby_extra_fields: "{name}" is already the host identifier '
                f'(breakby_field), it cannot also be an extra dimension'
            )
        if not _DHM_EXTRA_FIELD_PATTERN.match(name):
            return None, (
                f'breakby_extra_fields: "{name}" is not a valid field name. '
                "Names must start with a letter or underscore and contain only "
                "letters, digits, underscores, or dots."
            )
        normalized.append(name)
        seen.add(name)
    if not normalized:
        return [], None
    # NOTE: the merged + extras incompatibility is caught up-front above
    # so a reserved-name or invalid-name error doesn't mask the more
    # actionable configuration mismatch.
    if len(normalized) > _DHM_EXTRA_FIELDS_MAX:
        return None, (
            f"breakby_extra_fields: at most {_DHM_EXTRA_FIELDS_MAX} extra dimensions are allowed "
            f"(received {len(normalized)})"
        )
    return normalized, None


class TrackMeHandlerSplkHybridTrackerAdmin_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkHybridTrackerAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_hybrid_trackers(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_hybrid_trackers/admin",
            "resource_group_desc": "Endpoints related to the manage of Hybrid trackers for splk-feeds components (admin operations)",
        }

        return {"payload": response, "status": 200}

    # Return and execute simulation searches
    def post_hybrid_tracker_simulation(self, request_info, **kwargs):
        """
        | trackme url=\"/services/trackme/v2/splk_hybrid_trackers/admin/hybrid_tracker_simulation\" mode=\"post\" body=\"{'component': 'dsm', 'account': 'local', 'search_mode': 'tstats', 'earliest_time': '-4h', 'latest_time': '+4h', 'search_constraint': 'splunk_server=* sourcetype!=stash sourcetype!=*too_small sourcetype!=modular_alerts:trackme* sourcetype!=trackme:*', 'breakby_field': 'none'}\"
        """

        # init
        simulation_info = None
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    run_simulation = resp_dict["run_simulation"]
                except Exception as e:
                    if run_simulation in ("true", "false"):
                        if run_simulation == "true":
                            run_simulation = True
                        elif run_simulation == "false":
                            run_simulation = False
                    else:
                        msg = f'Invalid option for run_simulation="{run_simulation}", valid choices are: true | false'
                        logger.error(msg)
                        return {
                            "payload": {
                                "action": "failure",
                                "response": msg,
                            },
                            "status": 500,
                        }
                # component
                component = resp_dict["component"]
                if not component in ("dsm", "dhm", "mhm"):
                    return {
                        "payload": {
                            "response": f'Invalid component="{component}", valid options are: dsm|dhm|mhm'
                        },
                        "status": 500,
                    }
                account = resp_dict["account"]
                search_mode = resp_dict["search_mode"]
                if not search_mode in ("tstats", "raw", "mstats", "lookups"):
                    return {
                        "payload": {
                            "response": f'Invalid search_mode="{search_mode}", valid options are: tstats|raw|mstats|lookups'
                        },
                        "status": 500,
                    }
                # In lookups mode the wizard does not send a root constraint
                # or time-range pickers — set permissive defaults so the rest
                # of the simulation flow does not NPE on these.
                if search_mode == "lookups":
                    search_constraint = resp_dict.get("search_constraint", "") or ""
                    earliest_time = resp_dict.get("earliest_time", "-5m") or "-5m"
                    latest_time = resp_dict.get("latest_time", "now") or "now"
                else:
                    search_constraint = resp_dict["search_constraint"]
                    earliest_time = resp_dict["earliest_time"]
                    latest_time = resp_dict["latest_time"]

                # this is optional
                try:
                    index_earliest_time = resp_dict["index_earliest_time"]
                except Exception as e:
                    index_earliest_time = None

                try:
                    index_latest_time = resp_dict["index_latest_time"]
                except Exception as e:
                    index_latest_time = None

                # In lookups mode the wizard does not send a break-by field
                # (one entity per lookup), so this key is absent. Default to
                # "none" — the same sentinel tstats/raw use for "no custom
                # break-by" — and skip the KeyError. The downstream lookups
                # short-circuit ignores the value anyway.
                breakby_field = resp_dict.get("breakby_field", "none") or "none"

                try:
                    breakby_field_include_sourcetype = resp_dict[
                        "breakby_field_include_sourcetype"
                    ]

                    # if a string, convert to bool
                    if isinstance(breakby_field_include_sourcetype, str):
                        if breakby_field_include_sourcetype.lower() in (
                            "true",
                            "false",
                        ):
                            if breakby_field_include_sourcetype.lower() == "true":
                                breakby_field_include_sourcetype = True
                            elif breakby_field_include_sourcetype.lower() == "false":
                                breakby_field_include_sourcetype = False

                    elif isinstance(breakby_field_include_sourcetype, int):
                        if breakby_field_include_sourcetype in (0, 1):
                            breakby_field_include_sourcetype = bool(
                                breakby_field_include_sourcetype
                            )

                    else:
                        error_msg = f"breakby_field_include_sourcetype value is invalid, valid options are: 0 (False), 1 (True)"
                        logger.error(error_msg)
                        return {
                            "payload": {
                                "action": "failure",
                                "response": str(e),
                            },
                            "status": 500,
                        }

                except Exception as e:
                    breakby_field_include_sourcetype = True

                # Optional, breakby_extra_fields (splk-dhm only): extra per-host
                # metadata dimensions appended to the combo grain on top of
                # (index, sourcetype). Single host identifier stays in
                # breakby_field; extras are a structurally separate list.
                breakby_extra_fields = resp_dict.get("breakby_extra_fields", [])
                if component == "dhm":
                    normalized_extras, extras_err = _normalize_breakby_extra_fields(
                        breakby_extra_fields,
                        breakby_field if breakby_field not in (None, "none", "merged") else None,
                        breakby_field == "merged",
                    )
                    if extras_err is not None:
                        logger.error(extras_err)
                        return {
                            "payload": {
                                "action": "failure",
                                "response": extras_err,
                            },
                            "status": 400,
                        }
                    breakby_extra_fields = normalized_extras
                else:
                    breakby_extra_fields = []

                # cron_schedule is optional
                try:
                    cron_schedule = resp_dict["cron_schedule"]
                except Exception as e:
                    cron_schedule = None

                # verify the cron schedule validity, if submitted
                if cron_schedule:
                    try:
                        validate_cron_schedule(cron_schedule)
                    except Exception as e:
                        logger.error(str(e))
                        return {
                            "payload": {
                                "action": "failure",
                                "response": str(e),
                            },
                            "status": 500,
                        }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns and executes simulation searches, it requires a POST call with the following information:",
                "resource_desc": "Return and execute hybrid tracker search for simulation purposes",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_hybrid_trackers/admin/hybrid_tracker_simulation\" mode=\"post\" body=\"{'component': 'dsm', 'account': 'local', 'search_mode': 'tstats', 'earliest_time': '-4h', 'latest_time': '+4h', 'search_constraint': 'splunk_server=* sourcetype!=stash sourcetype!=*too_small sourcetype!=modular_alerts:trackme* sourcetype!=trackme:*', 'breakby_field': 'none'\"}",
                "options": [
                    {
                        "run_simulation": "Optional, Execute the simulation search or simply return the search syntax and other information, valid options are: true | false (default to true)",
                        "component": "The component, valid options are: dsm | dhm | mhm",
                        "account": "Splunk deployment, either local or a configured remote account",
                        "search_mode": "Splunk search mode, valid options are: tstats | raw | mstats",
                        "search_constraint": "REQUIRED. Splunk root search constraint. When using tstats mode, all referenced fields must be indexed time fields",
                        "breakby_field": "Optional: additional break by logic, for instance to use a custom indexed key, refer to none if unused. For splk-dsm and splk-dhm, the special value 'merged' switches the tracker to merged mode (sourcetype collapsed to '@all' — entity per index for splk-dsm, entity per host with sourcetype='@all' for splk-dhm).",
                        "breakby_field_include_sourcetype": "Optional (for splk-dsm only): When using a custom break by for splk-dsm, you can optionally decide not to consider the sourcetype, in this case the entity will match any sourcetype associated with the metadata. Defaults to 1 (for True), can be set to 0 for False and 1 for True",
                        "breakby_extra_fields": "Optional (for splk-dhm only): JSON array of additional per-host metadata dimensions appended to the combo grain on top of (index, sourcetype) — e.g. ['source']. The host identifier stays in breakby_field; this list is structurally separate. Up to 5 entries; reserved names (host, index, sourcetype, splunk_server, _time) and the breakby_field value are rejected. Not allowed with merged mode.",
                        "earliest_time": "The earliest time quantifier",
                        "latest_time": "The latest time quantifier",
                        "index_earliest_time": "The indexed earliest time quantifier",
                        "index_latest_time": "The indexed latest time quantifier",
                        "cron_schedule": "Optional, if submitted in the context of the simulation, the cron schedule validity will be verified",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # proceed

        try:
            # ------------------------------------------------------------
            # Lookups mode short-circuit
            #
            # In lookups mode the tracker has no Splunk search constraint,
            # break-by or time-range pickers. The SPL is fully determined by
            # the four lookups-specific params plus the chosen account. We
            # build the simulation search via the same helper used by the
            # create flow and return it immediately, bypassing the
            # tstats/raw/mstats simulation pipeline below.
            # ------------------------------------------------------------
            if search_mode == "lookups":
                # Lookups mode is implemented exclusively for splk-dsm: the
                # downstream macro hardcodes the DSM abstract macro and
                # writes to the DSM tenant collection. Reject any attempt
                # to use it for dhm/mhm at the boundary so the caller sees
                # a clear error instead of silent miswrites.
                if component != "dsm":
                    return {
                        "payload": {
                            "response": (
                                f'search_mode="lookups" is only supported for '
                                f'component="dsm" (got component="{component}")'
                            )
                        },
                        "status": 400,
                    }
                # The simulation endpoint's tstats/raw/mstats flow does not
                # need tenant_id (it builds a stateless preview), but our
                # lookups branch interpolates it into the generative command
                # arg and the preview SPL. Require it explicitly here so a
                # missing value 400s with a clear message instead of
                # producing `tenant_id=""` SPL.
                lookups_tenant_id = resp_dict.get("tenant_id")
                lookups_tenant_id = sanitize_spl_quoted_arg(lookups_tenant_id)
                # Check emptiness AFTER sanitisation: an input made
                # entirely of stripped chars (e.g. `"$$$"`) would pass a
                # naive truthiness check on the raw value but reach the
                # generated SPL as `tenant_id=""`.
                if not lookups_tenant_id:
                    return {
                        "payload": {
                            "response": (
                                'tenant_id is required when '
                                'search_mode="lookups" and must contain at '
                                'least one character after sanitisation'
                            )
                        },
                        "status": 400,
                    }
                # All three lookups inputs land inside double-quoted SPL
                # strings via the generative command and the preview search,
                # so strip SPL-injection vectors at the validator boundary.
                lookups_app_namespace = sanitize_spl_quoted_arg(
                    resp_dict.get("lookups_app_namespace") or "-"
                )
                lookups_name_pattern = sanitize_spl_quoted_arg(
                    resp_dict.get("lookups_name_pattern") or ".*"
                )
                lookups_type = sanitize_spl_quoted_arg(
                    resp_dict.get("lookups_type") or "csv"
                )
                # Operator-supplied candidate field list for the KVstore
                # mtime probe — commas survive sanitize_spl_quoted_arg so
                # the comma-list form is preserved. Falls back to the same
                # default the TA command's Option declares so the entity
                # behaviour is stable when the wizard omits the field.
                lookups_kvstore_time_fields = sanitize_spl_quoted_arg(
                    resp_dict.get("lookups_kvstore_time_fields")
                    or "_time, mtime, updated_at, modified, timestamp, last_modified"
                )
                # Whitelist enforcement: the helper accepts only these three
                # values, the wizard only ever sends one of them.
                if lookups_type not in ("csv", "kvstore", "both"):
                    return {
                        "payload": {
                            "response": (
                                f'Invalid lookups_type="{lookups_type}", valid '
                                f'options are: csv|kvstore|both'
                            )
                        },
                        "status": 400,
                    }
                try:
                    data_max_delay_allowed = int(
                        resp_dict.get("data_max_delay_allowed", 86400)
                    )
                except (TypeError, ValueError):
                    data_max_delay_allowed = 86400
                # Reject non-positive thresholds. The frontend constrains
                # the input to > 0 but a direct API caller could send 0
                # (or a negative), which would create a tracker where
                # `now() - data_last_time_seen > 0` is always true and
                # every lookup is immediately stale.
                if data_max_delay_allowed <= 0:
                    data_max_delay_allowed = 86400

                tracker_simulation_search = generate_lookups_report_search(
                    tenant_id=lookups_tenant_id,
                    account=account,
                    app_namespace=lookups_app_namespace,
                    name_pattern=lookups_name_pattern,
                    lookup_type=lookups_type,
                    kvstore_time_fields=lookups_kvstore_time_fields,
                    data_max_delay_allowed=data_max_delay_allowed,
                )

                response = {
                    "run_simulation": run_simulation,
                    "component": component,
                    "account": account,
                    "search_mode": search_mode,
                    "tenant_id": lookups_tenant_id,
                    "lookups_app_namespace": lookups_app_namespace,
                    "lookups_name_pattern": lookups_name_pattern,
                    "lookups_type": lookups_type,
                    "lookups_kvstore_time_fields": lookups_kvstore_time_fields,
                    "data_max_delay_allowed": data_max_delay_allowed,
                    "tracker_simulation_search": tracker_simulation_search,
                }

                # Optionally execute a bounded preview of the discovery.
                # Returns up to 100 entities with their discovery metadata so
                # the wizard's Simulation Results table is informative rather
                # than just a count. Each row carries `dcount_entities` —
                # the TRUE total of matched lookups (i.e. the count over
                # the FULL discovery stream — `eventstats count` runs
                # BEFORE `head 100` precisely so the wizard's "Found N
                # lookups" headline reflects the real filter scope, not
                # the capped preview size). The wizard derives the
                # "showing first 100 of N" hint locally by comparing
                # dcount_entities against the row count it received.
                # …plus the trimmed set of fields most useful to inspect
                # before creating the tracker: object, app_namespace,
                # lookup_type, lookup_path, data_eventcount,
                # data_last_time_seen, mtime_source.
                if run_simulation:
                    preview_search = (
                        f'| trackmelookupsmonitor tenant_id="{lookups_tenant_id}" '
                        f'app_namespace="{lookups_app_namespace}" '
                        f'name_pattern="{lookups_name_pattern}" '
                        f'lookup_type="{lookups_type}" '
                        f'kvstore_time_fields="{lookups_kvstore_time_fields}" '
                        # Count the full discovery stream BEFORE capping
                        # it, otherwise dcount_entities saturates at 100
                        # and the wizard silently lies about the filter
                        # scope.
                        '| eventstats count as dcount_entities '
                        '| head 100 '
                        # `| table` is intentional rather than `| fields`
                        # so the underscore-prefixed Splunk internals
                        # (`_raw`, `_time`) the command stamps on each
                        # row for the events view are NOT carried into
                        # the wizard's simulation table — they appear as
                        # noisy columns there.
                        '| table object, app_namespace, lookup_type, '
                        'lookup_path, data_eventcount, data_last_time_seen, '
                        'mtime_source, dcount_entities'
                    )
                    if account and account != "local":
                        # `account` lands inside a quoted SPL arg in the
                        # splunkremotesearch wrapper, so apply the same
                        # sanitiser the lookups inputs already use.
                        safe_account = sanitize_spl_quoted_arg(account)
                        # Escape BACKSLASHES FIRST, then double-quotes —
                        # otherwise a regex name_pattern carrying `\d`,
                        # `\w`, `\.` etc. survives the sanitiser (which
                        # only strips trailing backslashes) but gets
                        # mangled when nested inside `search="..."` of
                        # `splunkremotesearch`, because the remote SH's
                        # SPL parser interprets the bare `\` as an
                        # escape sequence and silently drops it.
                        # Same pattern already used at
                        # trackme_libs_splk_feeds.py:1448.
                        preview_escaped = preview_search.replace(
                            "\\", "\\\\"
                        ).replace('"', '\\"')
                        preview_search = (
                            f'| splunkremotesearch account="{safe_account}" '
                            f'search="{preview_escaped}" '
                            f'tenant_id="{lookups_tenant_id}"'
                        )
                    kwargs_search = {
                        "app": "trackme",
                        "earliest_time": "-5m",
                        "latest_time": "now",
                        "output_mode": "json",
                        "count": 0,
                    }
                    query_results = []
                    try:
                        reader = run_splunk_search(
                            service,
                            preview_search,
                            kwargs_search,
                            24,
                            5,
                        )
                        for item in reader:
                            if isinstance(item, dict):
                                query_results.append(item)
                    except Exception as e:
                        msg = (
                            "An exception was encountered while running the "
                            f'lookups simulation, exception="{str(e)}"'
                        )
                        logger.error(msg)
                        return {
                            "payload": {"action": "failure", "response": msg},
                            "status": 500,
                        }
                    # Return the full preview as a list so the wizard can
                    # render a per-lookup table; fall back to a single
                    # zero-count dict when nothing matched the filter.
                    response["results"] = (
                        query_results if query_results else [{"dcount_entities": 0}]
                    )

                return {"payload": response, "status": 200}

            # init
            response = {
                "run_simulation": run_simulation,
                "component": component,
                "account": account,
                "search_mode": search_mode,
                "search_constraint": search_constraint,
                "earliest_time": earliest_time,
                "latest_time": latest_time,
                "index_earliest_time": index_earliest_time,
                "index_latest_time": index_latest_time,
                "breakby_field": breakby_field,
                "breakby_extra_fields": breakby_extra_fields,
            }

            # retrieve from lib
            simulation_info = splk_dsm_hybrid_tracker_simulation_return_searches(
                {
                    "component": component,
                    "account": account,
                    "search_mode": search_mode,
                    "search_constraint": search_constraint,
                    "earliest_time": earliest_time,
                    "latest_time": latest_time,
                    "index_earliest_time": index_earliest_time,
                    "index_latest_time": index_latest_time,
                    "breakby_field": breakby_field,
                    "breakby_field_include_sourcetype": breakby_field_include_sourcetype,
                    "breakby_extra_fields": breakby_extra_fields,
                }
            )

            # get new_tenant_simulation_search
            tracker_simulation_search = simulation_info.get("tracker_simulation_search")
            # add to response
            response["tracker_simulation_search"] = tracker_simulation_search

            # attempt its execution
            kwargs_search = {
                "app": "trackme",
                "earliest_time": earliest_time,
                "latest_time": latest_time,
                "output_mode": "json",
                "count": 0,
            }
            query_results = []
            results_count = 0

            if run_simulation:
                try:
                    # spawn the search and get the results
                    reader = run_splunk_search(
                        service,
                        tracker_simulation_search,
                        kwargs_search,
                        24,
                        5,
                    )

                    for item in reader:
                        if isinstance(item, dict):
                            query_results.append(item)
                            results_count += 1

                except Exception as e:
                    # render response
                    msg = f'An exception was encountered while attempting to run the hybrid tracker simulation, exception="{str(e)}"'
                    logger.error(msg)
                    return {
                        "payload": {
                            "action": "failure",
                            "response": msg,
                        },
                        "status": 500,
                    }

            # Add the search results to the response (the first result only)
            if results_count > 0:
                response["results"] = query_results[0]
            else:
                response["results"] = {
                    "dcount_entities": 0,
                }

            # render response
            return {"payload": response, "status": 200}

        except Exception as e:
            # render response
            msg = f'An exception was encountered while processing hybrid tracker simulation, exception="{str(e)}"'
            logger.error(msg)
            return {
                "payload": {
                    "action": "failure",
                    "response": msg,
                },
                "status": 500,
            }

    # Create an hybrid tracker
    def post_hybrid_tracker_create(self, request_info, **kwargs):
        """
        | trackme mode=post url="/services/trackme/v2/splk_hybrid_trackers/admin/hybrid_tracker_create" body="{'tenant_id': 'mytenant', 'component': 'dsm', 'tracker_name': 'test:001', 'account': 'local', 'search_mode': 'tstats', 'root_constraint': 'index=net* OR index=fire* region=*', 'breakby_field': 'region', 'earliest_time': '-4h', 'latest_time': '+4h', 'index_earliest_time': '-4h', 'index_latest_time': '+4h'}"
        """

        # args
        account = None
        tenant_id = None
        component = None
        tracker_name = None
        tracker_type = None
        search_mode = None
        root_constraint = None
        cron_schedule = None
        breakby_field = None
        owner = None
        earliest_time = None
        latest_time = None
        index_earliest_time = None
        index_latest_time = None
        burn_test = None
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

            # gets args
            if not describe:
                #
                # mandatory args
                #

                # tenant
                tenant_id = resp_dict["tenant_id"]

                # component
                component = resp_dict["component"]
                if not component in ("dsm", "dhm", "mhm"):
                    return {
                        "payload": {
                            "response": f'Invalid component="{component}", valid options are: dsm|dhm|mhm'
                        },
                        "status": 500,
                    }

                # tracker name (replace and truncate to 40 chars)
                tracker_name = (
                    resp_dict["tracker_name"]
                    .lower()
                    .replace(" ", "-")
                    .replace(":", "-")[:40]
                )

                # remote account
                account = resp_dict["account"]

                # set tracker_type
                if account != "local":
                    tracker_type = "remote"
                else:
                    tracker_type = "local"

                # search_mode: accepted values are: tstats,raw,mstats,lookups
                search_mode = resp_dict["search_mode"]
                if not search_mode in ("tstats", "raw", "mstats", "lookups"):
                    search_mode = "tstats"

                # the root constraint of the tracker — not used in lookups
                # mode (the trackmelookupsmonitor command enumerates lookups
                # via REST and does not need a Splunk search constraint), so
                # default to an empty string when omitted by the wizard.
                if search_mode == "lookups":
                    root_constraint = sanitize_spl_input(
                        resp_dict.get("root_constraint", "") or ""
                    )
                else:
                    root_constraint = sanitize_spl_input(resp_dict["root_constraint"])

                #
                # optional args
                #

                try:
                    cron_schedule = resp_dict["cron_schedule"]
                except Exception as e:
                    cron_schedule = "*/5 * * * *"

                # verify the cron schedule validity, if submitted
                if cron_schedule:
                    try:
                        validate_cron_schedule(cron_schedule)
                    except Exception as e:
                        logger.error(str(e))
                        return {
                            "payload": {
                                "action": "failure",
                                "response": str(e),
                            },
                            "status": 500,
                        }

                try:
                    owner = resp_dict["owner"]
                except Exception as e:
                    owner = None

                # Update comment is optional and used for audit changes
                try:
                    update_comment = resp_dict["update_comment"]
                except Exception as e:
                    update_comment = "API update"

                # earliest_time and latest_time for the tracker, if not specified, defaults to -4h / +4h for dsm|dhm and -5m/+5m for mhm
                try:
                    earliest_time = resp_dict["earliest_time"]
                except Exception as e:
                    if component in ("dsm", "dhm"):
                        earliest_time = "-4h"
                    elif component in ("mhm"):
                        earliest_time = "-5m"

                try:
                    latest_time = resp_dict["latest_time"]
                except Exception as e:
                    if component in ("dsm", "dhm"):
                        latest_time = "+4h"
                    elif component in ("mhm"):
                        latest_time = "+5m"

                # index_earliest_time and index_latest_time for the tracker, if not specified, defaults to -4h / +4h (these are only relevant for dsm|dhm)
                try:
                    index_earliest_time = resp_dict["index_earliest_time"]
                except Exception as e:
                    index_earliest_time = "-4h"

                try:
                    index_latest_time = resp_dict["index_latest_time"]
                except Exception as e:
                    index_latest_time = "+4h"

                # Optional, tstats root break by sequence for splk-dsm
                try:
                    breakby_field = resp_dict["breakby_field"]
                except Exception as e:
                    breakby_field = None
                # accept none as a way to deactivate the option
                if breakby_field == "none":
                    breakby_field = None

                try:
                    breakby_field_include_sourcetype = resp_dict[
                        "breakby_field_include_sourcetype"
                    ]

                    # if a string, convert to bool
                    if isinstance(breakby_field_include_sourcetype, str):
                        if breakby_field_include_sourcetype.lower() in (
                            "true",
                            "false",
                        ):
                            if breakby_field_include_sourcetype.lower() == "true":
                                breakby_field_include_sourcetype = True
                            elif breakby_field_include_sourcetype.lower() == "false":
                                breakby_field_include_sourcetype = False

                    elif isinstance(breakby_field_include_sourcetype, int):
                        if breakby_field_include_sourcetype in (0, 1):
                            breakby_field_include_sourcetype = bool(
                                breakby_field_include_sourcetype
                            )

                    else:
                        error_msg = f"breakby_field_include_sourcetype value is invalid, valid options are: 0 (False), 1 (True)"
                        logger.error(error_msg)
                        return {
                            "payload": {
                                "action": "failure",
                                "response": str(e),
                            },
                            "status": 500,
                        }

                except Exception as e:
                    breakby_field_include_sourcetype = True

                # Optional, breakby_extra_fields (splk-dhm only): extra per-host
                # metadata dimensions appended to the combo grain on top of
                # (index, sourcetype). The single host identifier stays in
                # breakby_field; extras are a structurally separate list.
                breakby_extra_fields = resp_dict.get("breakby_extra_fields", [])
                if component == "dhm":
                    normalized_extras, extras_err = _normalize_breakby_extra_fields(
                        breakby_extra_fields,
                        breakby_field if breakby_field not in (None, "none", "merged") else None,
                        breakby_field == "merged",
                    )
                    if extras_err is not None:
                        logger.error(extras_err)
                        return {
                            "payload": {
                                "action": "failure",
                                "response": extras_err,
                            },
                            "status": 400,
                        }
                    breakby_extra_fields = normalized_extras
                else:
                    breakby_extra_fields = []

                # Optional, dsm_tstats_root_time_span
                try:
                    dsm_tstats_root_time_span = resp_dict["dsm_tstats_root_time_span"]
                except Exception as e:
                    dsm_tstats_root_time_span = "30s"

                # Optional, dsm_tstats_root_breakby_include_splunk_server
                try:
                    dsm_tstats_root_breakby_include_splunk_server = resp_dict[
                        "dsm_tstats_root_breakby_include_splunk_server"
                    ]
                    if dsm_tstats_root_breakby_include_splunk_server == "True":
                        dsm_tstats_root_breakby_include_splunk_server = True
                    elif dsm_tstats_root_breakby_include_splunk_server == "False":
                        dsm_tstats_root_breakby_include_splunk_server = False
                    else:
                        dsm_tstats_root_breakby_include_splunk_server = True
                except Exception as e:
                    dsm_tstats_root_breakby_include_splunk_server = False

                # Optional, dsm_tstats_root_breakby_include_host
                try:
                    dsm_tstats_root_breakby_include_host = resp_dict[
                        "dsm_tstats_root_breakby_include_host"
                    ]
                    if dsm_tstats_root_breakby_include_host == "True":
                        dsm_tstats_root_breakby_include_host = True
                    elif dsm_tstats_root_breakby_include_host == "False":
                        dsm_tstats_root_breakby_include_host = False
                    else:
                        dsm_tstats_root_breakby_include_host = True
                except Exception as e:
                    dsm_tstats_root_breakby_include_host = False

                # Optional, dhm_tstats_root_time_span
                try:
                    dhm_tstats_root_time_span = resp_dict["dhm_tstats_root_time_span"]
                except Exception as e:
                    dhm_tstats_root_time_span = "1m"

                # Optional, dhm_tstats_root_breakby_include_splunk_server
                try:
                    dhm_tstats_root_breakby_include_splunk_server = resp_dict[
                        "dhm_tstats_root_breakby_include_splunk_server"
                    ]
                    if dhm_tstats_root_breakby_include_splunk_server == "True":
                        dhm_tstats_root_breakby_include_splunk_server = True
                    elif dhm_tstats_root_breakby_include_splunk_server == "False":
                        dhm_tstats_root_breakby_include_splunk_server = False
                    else:
                        dhm_tstats_root_breakby_include_splunk_server = True
                except Exception as e:
                    dhm_tstats_root_breakby_include_splunk_server = False

                # Optional: burn_test, temporary create the abstract, perform a burn test, report the run time performance, delete and report
                try:
                    burn_test = resp_dict["burn_test"]
                    if burn_test == "True":
                        burn_test = True
                    elif burn_test == "False":
                        burn_test = False
                except Exception as e:
                    burn_test = False

                # Optional: burn_test_runsearch, if burn_test True, execute the search or just render the search that would be executed
                try:
                    burn_test_runsearch = resp_dict["burn_test_runsearch"]
                    if burn_test_runsearch == "True":
                        burn_test_runsearch = True
                    elif burn_test_runsearch == "False":
                        burn_test_runsearch = False
                except Exception as e:
                    burn_test_runsearch = True

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows creating a custom remote hybrid tracker for data sources, it requires a POST call with the following information:",
                "resource_desc": "Create a new Hybrid tracker",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_hybrid_trackers/admin/hybrid_tracker_create\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'tracker_name': 'test:001', 'account': 'local', 'search_mode': 'tstats', 'root_constraint': 'index=net* OR index=fire* region=*', 'breakby_field': 'region', 'earliest_time': '-4h', 'latest_time': '+4h', 'index_earliest_time': '-4h', 'index_latest_time': '+4h'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component, valid options are: dsm | dhm | mhm",
                        "tracker_name": "name of the hybrid tracker report",
                        "account": "name of remote Splunk deployment account as configured in TrackMe",
                        "search_mode": "the search mode for the tracker, can be tstats or raw",
                        "root_constraint": "the tracker report root search constraint, to define search filters scoping the data set",
                        "breakby_field": "Optional, the break by key field(s), used to discover and maintain the entities via this tracker. splk-dsm supports multiple fields provided as a comma separated list of fields. splk-dhm accepts a single host identifier field (additional per-host dimensions go in breakby_extra_fields). For splk-dsm and splk-dhm, the special value 'merged' switches the tracker to merged mode (sourcetype collapsed to '@all' — entity per index for splk-dsm, entity per host with sourcetype='@all' for splk-dhm).",
                        "breakby_field_include_sourcetype": "Optional (for splk-dsm only): When using a custom break by for splk-dsm, you can optionally decide not to consider the sourcetype, in this case the entity will match any sourcetype associated with the metadata. Defaults to 1 (for True), can be set to 0 for False and 1 for True",
                        "breakby_extra_fields": "Optional (for splk-dhm only): JSON array of additional per-host metadata dimensions appended to the combo grain on top of (index, sourcetype) — e.g. ['source']. The host identifier stays in breakby_field; this list is structurally separate. Up to 5 entries; reserved names (host, index, sourcetype, splunk_server, _time) and the breakby_field value are rejected. Not allowed with merged mode.",
                        "dsm_tstats_root_time_span": "Optional, for splk-dsm in tstats mode, define the span value at the tstats root level, defaults to 30s which is suitable for most use cases, higher time value means less accuracy for the calculation of latency but reduced computing costs. Use 'none' to drop the time bucketing entirely (best performance, but per-bucket latency calculations are not accurate — entities are still discovered and a single latest snapshot is captured per run).",
                        "dsm_tstats_root_breakby_include_splunk_server": "Optional, for splk-dsm in tstats mode, include or exclude splunk_server in the root break by sequence, improves accuracy for latency calculation at the price of potentially more computing costs, valid optooms are: True|False, defaults to True",
                        "dhm_tstats_root_time_span": "Optional, for splk-dhm in tstats mode, define the span value at the tstats root level, defaults to 1m which is suitable for most use cases, higher time value means less accuracy for the calculation of latency but reduced computing costs. Use 'none' to drop the time bucketing entirely (best performance, but per-bucket latency calculations are not accurate — entities are still discovered and a single latest snapshot is captured per run).",
                        "dhm_tstats_root_breakby_include_splunk_server": "Optional, for splk-dhm in tstats mode, include or exclude splunk_server in the root break by sequence, improves accuracy for latency calculation at the price of potentially more computing costs, valid optooms are: True|False, defaults to True",
                        "dsm_tstats_root_breakby_include_host": "Optional, for splk-dsm in tstats mode, include or exclude host in the root break by sequence, improves accuracy for latency calculation at the price of potentially more computing costs, valid optooms are: True|False, defaults to True",
                        "owner": "Optional, the Splunk user owning the objects to be created, defaults to the owner set for the tenant",
                        "cron_schedule": "Optional, the cron schedule, defaults to every 5 minutes",
                        "earliest_time": "Optional, the earliest time value for the tracker, defaults to -4h for dsm|dhm and -5m for mhm",
                        "latest_time": "Optional, the latest time value for the tracker, defaults to +4h for dsm|dhm and +5m for mhm",
                        "index_earliest_time": "Optional, the indexed earliest time value for the tracker, defaults to -4h (applies to dsm|dhm)",
                        "index_latest_time": "Optional, the indexed latest time value for the tracker, defaults to +4h (applies to dsm|dhm)",
                        "burn_test": "Optional, create the abstract report, run a performance test, delete the report and report the performance results, valid options are: True | False (default: False)",
                        "burn_test_runsearch": "Optional, if burn_test True, execute the search effectively or only render the search that will be executed, valid options are: True | False (default: True)",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # run creation
        else:
            # Get splunkd port
            splunkd_port = request_info.server_rest_port

            # Get service
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=splunkd_port,
                token=request_info.system_authtoken,
                timeout=600,
            )

            # set loglevel
            loglevel = trackme_getloglevel(
                request_info.system_authtoken, request_info.server_rest_port
            )
            logger.setLevel(loglevel)

            # get TrackMe conf
            trackme_conf = trackme_reqinfo(
                request_info.system_authtoken, request_info.server_rest_uri
            )
            logger.debug(f'trackme_conf="{json.dumps(trackme_conf, indent=2)}"')

            # TrackMe sharing level
            trackme_default_sharing = trackme_conf["trackme_conf"]["trackme_general"][
                "trackme_default_sharing"
            ]

            # Retrieve the virtual tenant record to access acl
            collection_vtenants_name = "kv_trackme_virtual_tenants"
            collection_vtenants = service.kvstore[collection_vtenants_name]

            # Define the KV query search string
            query_string = {
                "tenant_id": tenant_id,
            }

            # Get the tenant
            try:
                vtenant_record = collection_vtenants.data.query(
                    query=json.dumps(query_string)
                )[0]
                vtenant_key = vtenant_record.get("_key")

            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", failed to retrieve the tenant record, exception="{str(e)}"'
                )
                return {
                    "payload": f'tenant_id="{tenant_id}", failed to retrieve the tenant record, exception="{str(e)}"',
                    "status": 500,
                }

            # verify the owner
            if not owner:
                owner = vtenant_record.get("tenant_owner")

            # manage some enforcements
            if component == "mhm" and not search_mode == "mstats":
                search_mode = "mstats"

            # check license state
            try:
                check_license = trackme_check_license(
                    request_info.server_rest_uri,
                    request_info.session_key,
                    request_info.system_authtoken,
                )
                license_is_valid = check_license.get("license_is_valid")
                license_subscription_class = check_license.get(
                    "license_subscription_class"
                )
                license_read_only = check_license.get("license_read_only", False)
                license_active_hybrid_trackers = None
                if component == "dsm":
                    license_active_hybrid_trackers = int(
                        check_license.get("license_active_splk_dsm_hybrid_trackers")
                    )
                elif component == "dhm":
                    license_active_hybrid_trackers = int(
                        check_license.get("license_active_splk_dhm_hybrid_trackers")
                    )
                elif component == "mhm":
                    license_active_hybrid_trackers = int(
                        check_license.get("license_active_splk_mhm_hybrid_trackers")
                    )
                license_active_hybrid_trackers_total = int(
                    check_license.get("license_active_hybrid_trackers")
                )
                logger.debug(
                    f'function check_license called, response="{json.dumps(check_license, indent=2)}"'
                )

            except Exception as e:
                license_is_valid = 0
                license_active_hybrid_trackers = 2
                license_active_hybrid_trackers_total = license_active_hybrid_trackers
                license_subscription_class = "free"
                license_read_only = False
                logger.error(f'function check_license exception="{str(e)}"')

            if license_read_only:
                audit_record = {
                    "action": "failure",
                    "change_type": "add new hybrid tracker",
                    "tenant_id": str(tenant_id),
                    "result": "I'm afraid I can't do that, this instance is currently in read-only mode and cannot create new trackers.",
                }

                logger.error(str(audit_record))
                return {"payload": audit_record, "status": 402}

            if license_active_hybrid_trackers >= 2 and license_is_valid != 1:
                # Licensing restrictions reached
                audit_record = {
                    "action": "failure",
                    "change_type": "add new hybrid tracker",
                    "tenant_id": str(tenant_id),
                    "result": f"I'm afraid I can't do that, this instance is running in Free limited mode edition which is limited to two active hybrid trackers per component, there are {license_active_hybrid_trackers} active trackers currently for this component",
                }

                logger.error(str(audit_record))
                return {"payload": audit_record, "status": 402}

            elif (
                license_active_hybrid_trackers_total >= 8
                and license_subscription_class == "foundation"
            ):
                # Licensing restrictions reached
                audit_record = {
                    "action": "failure",
                    "change_type": "add new hybrid tracker",
                    "tenant_id": str(tenant_id),
                    "result": f"I'm afraid I can't do that, this instance is running in Foundation edition which is limited to 8 active hybrid trackers in total, there are {license_active_hybrid_trackers_total} active trackers currently for the whole deployment",
                }

                logger.error(str(audit_record))
                return {"payload": audit_record, "status": 402}

            elif (
                license_active_hybrid_trackers_total >= 6
                and license_subscription_class == "free_extended"
            ):
                # Licensing restrictions reached
                audit_record = {
                    "action": "failure",
                    "change_type": "add new hybrid tracker",
                    "tenant_id": str(tenant_id),
                    "result": f"I'm afraid I can't do that, this instance is running in Free extended mode edition which is limited to 6 active hybrid trackers in total, there are {license_active_hybrid_trackers_total} active trackers currently for the whole deployment",
                }

                logger.error(str(audit_record))
                return {"payload": audit_record, "status": 402}

            elif (
                license_active_hybrid_trackers_total >= 16
                and license_subscription_class == "enterprise"
            ):
                # Licensing restrictions reached
                audit_record = {
                    "action": "failure",
                    "change_type": "add new hybrid tracker",
                    "tenant_id": str(tenant_id),
                    "result": f"I'm afraid I can't do that, this instance is running in Enterprise mode edition which is limited to 16 active hybrid trackers in total, there are {license_active_hybrid_trackers_total} active trackers currently for the whole deployment",
                }

                logger.error(str(audit_record))
                return {"payload": audit_record, "status": 402}

            # check if TCM is enabled in receiver mode
            enable_conf_manager_receiver = int(
                trackme_conf["trackme_conf"]["trackme_general"][
                    "enable_conf_manager_receiver"
                ]
            )

            if enable_conf_manager_receiver == 1:
                try:
                    tcm_response = trackme_send_to_tcm(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        resp_dict,
                        "post",
                        "/services/trackme/v2/splk_hybrid_trackers/admin/hybrid_tracker_create",
                    )
                    logger.info(f"trackme_send_to_tcm was successfully executed")
                except Exception as e:
                    logger.error(
                        f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                    )

            # ------------------------------------------------------------
            # Lookups mode: short-circuit
            #
            # Lookups trackers don't need a root-constraint macro, abstract
            # report or wrapper report. The scheduled saved search runs the
            # `| trackmelookupsmonitor` generative command (shipped by the
            # TA-trackme-lookupmonitor add-on) directly and pipes the rows
            # through `trackme_lookups_dedicated_tracker` for persistence.
            # We build a single scheduled saved search, register it in the
            # tenant + hybrid collections, and return an audit record.
            # ------------------------------------------------------------
            if search_mode == "lookups":
                # Lookups mode is implemented exclusively for splk-dsm: the
                # downstream macro hardcodes the DSM abstract macro and
                # writes to tenant_dsm_hybrid_objects + the per-tenant DSM
                # hybrid collection. Reject other components at the
                # boundary so the caller sees a clear error instead of
                # silent miswrites.
                if component != "dsm":
                    return {
                        "payload": {
                            "response": (
                                f'search_mode="lookups" is only supported for '
                                f'component="dsm" (got component="{component}")'
                            )
                        },
                        "status": 400,
                    }
                # All three lookups inputs land inside double-quoted SPL
                # strings in the generated saved search; strip SPL-injection
                # vectors at the validator boundary.
                lookups_app_namespace = sanitize_spl_quoted_arg(
                    resp_dict.get("lookups_app_namespace") or "-"
                )
                lookups_name_pattern = sanitize_spl_quoted_arg(
                    resp_dict.get("lookups_name_pattern") or ".*"
                )
                lookups_type = sanitize_spl_quoted_arg(
                    resp_dict.get("lookups_type") or "csv"
                )
                # Operator-supplied candidate field list for the KVstore
                # mtime probe. Commas survive sanitize_spl_quoted_arg so
                # the comma-list form is preserved. Falls back to the
                # same default the TA command's Option declares.
                lookups_kvstore_time_fields = sanitize_spl_quoted_arg(
                    resp_dict.get("lookups_kvstore_time_fields")
                    or "_time, mtime, updated_at, modified, timestamp, last_modified"
                )
                if lookups_type not in ("csv", "kvstore", "both"):
                    return {
                        "payload": {
                            "response": (
                                f'Invalid lookups_type="{lookups_type}", valid '
                                f'options are: csv|kvstore|both'
                            )
                        },
                        "status": 400,
                    }
                try:
                    data_max_delay_allowed = int(
                        resp_dict.get("data_max_delay_allowed", 86400)
                    )
                except (TypeError, ValueError):
                    data_max_delay_allowed = 86400
                # Reject non-positive thresholds. The frontend constrains
                # the input to > 0 but a direct API caller could send 0
                # (or a negative), which would create a tracker where
                # `now() - data_last_time_seen > 0` is always true and
                # every lookup is immediately stale.
                if data_max_delay_allowed <= 0:
                    data_max_delay_allowed = 86400

                # Two-tier saved-search layout — same shape as tstats/raw
                # but without the abstract/root_constraint_macro layer
                # (lookups has no constraint macro to indirect through):
                #
                #   <wrapper>: contains the actual search logic
                #              (| trackmelookupsmonitor ... |
                #               `trackme_lookups_dedicated_tracker(...)`).
                #              NOT scheduled.
                #
                #   <tracker>: scheduled with the user-supplied cron.
                #              Runs `| trackmetrackerexecutor ...
                #              report="<wrapper>" alert_no_results=True`
                #              so the standard TrackMe executor backend
                #              tracks the run health (failures, no-results
                #              conditions, runtime metrics) — same as
                #              every other hybrid tracker.
                wrapper_report_search = generate_lookups_report_search(
                    tenant_id=tenant_id,
                    account=account,
                    app_namespace=lookups_app_namespace,
                    name_pattern=lookups_name_pattern,
                    lookup_type=lookups_type,
                    kvstore_time_fields=lookups_kvstore_time_fields,
                    data_max_delay_allowed=data_max_delay_allowed,
                )

                wrapper_report_name = (
                    "trackme_"
                    + str(component)
                    + "_hybrid_"
                    + str(tracker_name)
                    + "_wrapper"
                    + "_tenant_"
                    + str(tenant_id)
                )
                tracker_report_name = (
                    "trackme_"
                    + str(component)
                    + "_hybrid_"
                    + str(tracker_name)
                    + "_tracker"
                    + "_tenant_"
                    + str(tenant_id)
                )
                tracker_report_search = (
                    f'| trackmetrackerexecutor tenant_id="{tenant_id}" '
                    f'component="splk-{component}" '
                    f'report="{wrapper_report_name}" '
                    f'alert_no_results=True'
                )

                logger.debug(
                    f'tenant_id="{tenant_id}", lookups tracker creation, '
                    f'wrapper_report_name="{wrapper_report_name}", '
                    f'tracker_report_name="{tracker_report_name}", '
                    f'wrapper_report_search="{wrapper_report_search}", '
                    f'tracker_report_search="{tracker_report_search}"'
                )

                # ----------------------------------------------------------
                # Burn test for lookups mode
                #
                # The tstats/raw burn test creates a temporary abstract
                # report, executes it once, and deletes it. For lookups we
                # do not want to materialise the persistent saved search
                # (the user has not yet clicked "Create" — the burn test
                # is a benchmark run from Step 6) and we definitely don't
                # want to fire the persistence pipeline (writes to the
                # DSM KVstore). Instead we time the discovery itself —
                # the dominant cost of any lookups tracker — by running
                # `| trackmelookupsmonitor ... | stats count`.
                # ----------------------------------------------------------
                if burn_test:
                    # Sanitise both `tenant_id` and `account` before
                    # interpolating into the benchmark SPL — they land
                    # inside double-quoted args via the trackmelookups-
                    # monitor command and the splunkremotesearch wrapper,
                    # so they get the same treatment as the three
                    # user-controlled lookups inputs.
                    safe_tenant_id = sanitize_spl_quoted_arg(tenant_id)
                    benchmark_core = (
                        f'| trackmelookupsmonitor tenant_id="{safe_tenant_id}" '
                        f'app_namespace="{lookups_app_namespace}" '
                        f'name_pattern="{lookups_name_pattern}" '
                        f'lookup_type="{lookups_type}" '
                        f'kvstore_time_fields="{lookups_kvstore_time_fields}"'
                    )
                    if account and account != "local":
                        safe_account = sanitize_spl_quoted_arg(account)
                        # Escape backslashes first, then double-quotes
                        # — see the equivalent block in the simulation
                        # branch (~line 612) for the rationale (regex
                        # name patterns with `\d`, `\w`, `\.` get
                        # mangled otherwise when nested inside
                        # splunkremotesearch's `search="..."` arg).
                        bench_escaped = benchmark_core.replace(
                            "\\", "\\\\"
                        ).replace('"', '\\"')
                        benchmark_search = (
                            f'| splunkremotesearch account="{safe_account}" '
                            f'search="{bench_escaped}" '
                            f'tenant_id="{safe_tenant_id}" '
                            f'| stats count as dcount_entities'
                        )
                    else:
                        benchmark_search = (
                            f'{benchmark_core} | stats count as dcount_entities'
                        )

                    if not burn_test_runsearch:
                        # Return the SPL for display only; no execution.
                        burn_test_results_record = {
                            "tenant_id": tenant_id,
                            "search": benchmark_search,
                            "root_constraint_macro": None,
                            "burn_test_success": True,
                            "earliest_time": "-5m",
                            "latest_time": "now",
                            "search_mode": "lookups",
                        }
                        logger.info(
                            f'tenant_id="{tenant_id}", lookups burn test '
                            f'(render only): {json.dumps(burn_test_results_record, indent=2)}'
                        )
                        return {"payload": burn_test_results_record, "status": 200}

                    burn_test_kwargs = {
                        "earliest_time": "-5m",
                        "latest_time": "now",
                        "search_mode": "normal",
                        "preview": False,
                        "time_format": "%s",
                        "output_mode": "json",
                        "count": 0,
                    }
                    burn_test_start_time = time.time()
                    burn_test_results_counter = 0
                    try:
                        reader = run_splunk_search(
                            service,
                            benchmark_search,
                            burn_test_kwargs,
                            24,
                            5,
                        )
                        for item in reader:
                            if isinstance(item, dict):
                                burn_test_results_counter += 1
                        burn_test_results_record = {
                            "tenant_id": tenant_id,
                            "run_time": round(time.time() - burn_test_start_time, 3),
                            "results_count": burn_test_results_counter,
                            "search": benchmark_search,
                            "burn_test_success": True,
                            "earliest_time": "-5m",
                            "latest_time": "now",
                            "search_mode": "lookups",
                        }
                        logger.info(
                            f'tenant_id="{tenant_id}", lookups burn test '
                            f'results: {json.dumps(burn_test_results_record, indent=2)}'
                        )
                        return {"payload": burn_test_results_record, "status": 200}
                    except Exception as e:
                        burn_test_results_record = {
                            "tenant_id": tenant_id,
                            "run_time": round(time.time() - burn_test_start_time, 3),
                            "results_count": burn_test_results_counter,
                            "search": benchmark_search,
                            "burn_test_success": False,
                            "earliest_time": "-5m",
                            "latest_time": "now",
                            "search_mode": "lookups",
                            "exception": f'search failed with exception="{str(e)}"',
                        }
                        logger.error(json.dumps(burn_test_results_record, indent=2))
                        return {"payload": burn_test_results_record, "status": 200}

                # ----------------------------------------------------------
                # Step 1 — create the wrapper saved search (NOT scheduled).
                # This is the search logic: it actually runs
                # `| trackmelookupsmonitor ...` and persists into the DSM
                # KVstore via `trackme_lookups_dedicated_tracker(...)`.
                # The tracker (created in step 2) invokes it via
                # `| trackmetrackerexecutor`, the same two-tier pattern
                # used by tstats/raw hybrid trackers.
                # ----------------------------------------------------------
                wrapper_report_properties = {
                    "description": "TrackMe DSM lookups monitor hybrid wrapper",
                    "is_scheduled": False,
                    "dispatch.earliest_time": "-5m",
                    "dispatch.latest_time": "now",
                }
                report_acl = {
                    "owner": owner,
                    "sharing": trackme_default_sharing,
                    "perms.write": vtenant_record.get("tenant_roles_admin"),
                    "perms.read": (
                        f"{vtenant_record.get('tenant_roles_user')},"
                        f"{vtenant_record.get('tenant_roles_power')}"
                    ),
                }
                wrapper_create_report = trackme_create_report(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    wrapper_report_name,
                    wrapper_report_search,
                    wrapper_report_properties,
                    report_acl,
                )

                # Splunkd API needs a couple of seconds to refresh while KOs are created.
                max_failures_count = 24
                sleep_time = 5
                wrapper_creation_success = False
                current_failures_count = 0
                while (
                    current_failures_count < max_failures_count
                    and not wrapper_creation_success
                ):
                    try:
                        service.saved_searches[wrapper_report_name]
                        logger.info(
                            f'action="success", lookups hybrid wrapper was successfully created, report_name="{wrapper_report_name}"'
                        )
                        wrapper_creation_success = True
                        break
                    except Exception as e:
                        logger.warning(
                            f'temporary failure, the wrapper is not yet available, will sleep and re-attempt, report_name="{wrapper_report_name}"'
                        )
                        time.sleep(sleep_time)
                        current_failures_count += 1
                        if current_failures_count >= max_failures_count:
                            logger.error(
                                f'max attempt reached, failure to create wrapper report_name="{wrapper_report_name}" with exception="{str(e)}"'
                            )
                            break
                time.sleep(2)

                if not wrapper_creation_success:
                    failure_record = {
                        "action": "failure",
                        "search_mode": "lookups",
                        "tenant_id": str(tenant_id),
                        "tracker_name": str(tracker_name),
                        "wrapper_report": wrapper_create_report.get("report_name"),
                        "tracker_report": None,
                        "response": (
                            f"saved search {wrapper_report_name} could not be verified "
                            f"as created after {max_failures_count} attempts; "
                            f"no tracker was registered"
                        ),
                    }
                    logger.error(json.dumps(failure_record, indent=2))
                    return {"payload": failure_record, "status": 500}

                # ----------------------------------------------------------
                # Step 2 — create the tracker saved search (SCHEDULED).
                # It contains only the `| trackmetrackerexecutor ... `
                # call referencing the wrapper; the executor backend
                # runs the wrapper and tracks the run health (failure
                # detection, no-results alerting, runtime metrics) so the
                # lookups tracker behaves like every other hybrid tracker.
                # ----------------------------------------------------------
                tracker_report_properties = {
                    "description": "TrackMe DSM lookups monitor hybrid tracker",
                    "is_scheduled": True,
                    "schedule_window": "5",
                    "cron_schedule": cron_schedule,
                    "dispatch.earliest_time": "-5m",
                    "dispatch.latest_time": "now",
                }
                tracker_create_report = trackme_create_report(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    tracker_report_name,
                    tracker_report_search,
                    tracker_report_properties,
                    report_acl,
                )

                tracker_creation_success = False
                current_failures_count = 0
                while (
                    current_failures_count < max_failures_count
                    and not tracker_creation_success
                ):
                    try:
                        service.saved_searches[tracker_report_name]
                        logger.info(
                            f'action="success", lookups hybrid tracker was successfully created, report_name="{tracker_report_name}"'
                        )
                        tracker_creation_success = True
                        break
                    except Exception as e:
                        logger.warning(
                            f'temporary failure, the tracker is not yet available, will sleep and re-attempt, report_name="{tracker_report_name}"'
                        )
                        time.sleep(sleep_time)
                        current_failures_count += 1
                        if current_failures_count >= max_failures_count:
                            logger.error(
                                f'max attempt reached, failure to create tracker report_name="{tracker_report_name}" with exception="{str(e)}"'
                            )
                            break
                time.sleep(2)

                # If the tracker never materialised, bail out and surface
                # the failure to the caller. Note: the wrapper saved
                # search has already been created at this point — it is
                # left in place (registry entries below are skipped on
                # this failure path) so an operator can inspect/clean up
                # rather than us silently masking a partial creation.
                if not tracker_creation_success:
                    failure_record = {
                        "action": "failure",
                        "search_mode": "lookups",
                        "tenant_id": str(tenant_id),
                        "tracker_name": str(tracker_name),
                        "wrapper_report": wrapper_create_report.get("report_name"),
                        "tracker_report": tracker_create_report.get("report_name"),
                        "response": (
                            f"saved search {tracker_report_name} could not be verified "
                            f"as created after {max_failures_count} attempts; "
                            f"no tracker was registered"
                        ),
                    }
                    logger.error(json.dumps(failure_record, indent=2))
                    return {"payload": failure_record, "status": 500}

                # Build the audit record. Lookups mode has no abstract /
                # root-constraint macro, so those fields are explicitly
                # null in the audit trail; wrapper + tracker are both
                # recorded so the registry mirrors the two-tier shape
                # used by tstats/raw trackers.
                audit_record = {
                    "account": str(account),
                    "abstract_report": None,
                    "wrapper_report": wrapper_create_report.get("report_name"),
                    "tracker_report": tracker_create_report.get("report_name"),
                    "root_constraint_macro": None,
                    "root_constraint": None,
                    "tracker_name": str(tracker_name),
                    "breakby_field": None,
                    "search_mode": "lookups",
                    "lookups_app_namespace": lookups_app_namespace,
                    "lookups_name_pattern": lookups_name_pattern,
                    "lookups_type": lookups_type,
                    "lookups_kvstore_time_fields": lookups_kvstore_time_fields,
                    "data_max_delay_allowed": data_max_delay_allowed,
                    "cron_schedule": tracker_create_report.get("cron_schedule"),
                    "action": "success",
                }

                # Register the new tracker in the vtenant record.
                try:
                    tenant_hybrid_objects = vtenant_record.get(
                        "tenant_dsm_hybrid_objects"
                    )
                except Exception as e:
                    tenant_hybrid_objects = None

                wrapper_report_name_str = wrapper_create_report.get("report_name")
                tracker_report_name_str = tracker_create_report.get("report_name")
                if tenant_hybrid_objects and tenant_hybrid_objects != "None":
                    vtenant_dict = json.loads(tenant_hybrid_objects)
                    reports = vtenant_dict.get("reports", [])
                    macros = vtenant_dict.get("macros", [])
                    reports.append(str(wrapper_report_name_str))
                    reports.append(str(tracker_report_name_str))
                    vtenant_dict = {"reports": reports, "macros": macros}
                else:
                    vtenant_dict = {
                        "reports": [
                            str(wrapper_report_name_str),
                            str(tracker_report_name_str),
                        ],
                        "macros": [],
                    }

                try:
                    vtenant_record["tenant_dsm_hybrid_objects"] = json.dumps(
                        vtenant_dict, indent=1
                    )
                    collection_vtenants.data.update(
                        str(vtenant_key), json.dumps(vtenant_record)
                    )
                except Exception as e:
                    logger.error(
                        f'failure while trying to update the vtenant KVstore record, exception="{str(e)}"'
                    )
                    return {
                        "payload": "Warn: exception encountered: " + str(e)
                    }

                # Register the new hybrid tracker in the hybrid collection.
                collection_hybrid_name = (
                    "kv_trackme_"
                    + str(component)
                    + "_hybrid_trackers_tenant_"
                    + str(tenant_id)
                )
                collection_hybrid = service.kvstore[collection_hybrid_name]
                hybrid_dict = {
                    "reports": [
                        str(wrapper_report_name_str),
                        str(tracker_report_name_str),
                    ],
                    "macros": [],
                    "properties": [
                        {
                            "tracker_name": str(tracker_name),
                            "search_mode": "lookups",
                            "lookups_app_namespace": lookups_app_namespace,
                            "lookups_name_pattern": lookups_name_pattern,
                            "lookups_type": lookups_type,
                            "lookups_kvstore_time_fields": lookups_kvstore_time_fields,
                            "data_max_delay_allowed": data_max_delay_allowed,
                            "cron_schedule": tracker_create_report.get(
                                "cron_schedule"
                            ),
                        }
                    ],
                }
                try:
                    collection_hybrid.data.insert(
                        json.dumps(
                            {
                                "_key": hashlib.sha256(
                                    tracker_name.encode("utf-8")
                                ).hexdigest(),
                                "tracker_name": tracker_name,
                                "knowledge_objects": json.dumps(
                                    hybrid_dict, indent=1
                                ),
                            }
                        )
                    )
                except Exception as e:
                    logger.error(
                        f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", failure while trying to insert the hybrid KVstore record, exception="{str(e)}"'
                    )

                # Audit event.
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        "add hybrid tracker",
                        "trackme_" + str(component) + "_hybrid_" + str(tracker_name),
                        "hybrid_tracker",
                        str(audit_record),
                        "The lookups hybrid tracker was created successfully",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                logger.info(json.dumps(audit_record, indent=2))
                return {"payload": audit_record, "status": 200}

            #
            # step 1: break by statement
            #

            if component == "dsm":
                # "none" tstats root time span — drop _time and span= from the
                # root tstats by-clause and inject `eval _time=now()` so the
                # rest of the pipeline still has a single (synthetic) time
                # bucket. Trades per-bucket latency accuracy for cheaper root
                # tstats execution. The injected eval has no quoted strings,
                # so the same fragment works for both local and remote
                # (splunkremotesearch) variants.
                dsm_is_no_span = str(dsm_tstats_root_time_span).lower() == "none"
                dsm_no_span_eval = (
                    '\n``` no tstats time span ```\n| eval _time=now()'
                    if dsm_is_no_span
                    else ""
                )

                breakby_field_list = ["index", "sourcetype", "splunk_server", "host"]
                custom_breakby_field_list = []
                if breakby_field and breakby_field != "merged":

                    # sourcetype to any with a custom breakby
                    if not breakby_field_include_sourcetype:

                        # turn into a list
                        custom_breakby_field_list = breakby_field.split(",")

                        # remove sourcetype from breakby_field_list
                        if "sourcetype" in custom_breakby_field_list:
                            breakby_field_list.remove("sourcetype")

                    # otherwise
                    else:
                        # turn into a list
                        custom_breakby_field_list = breakby_field.split(",")

                    for field in custom_breakby_field_list:
                        if not field in breakby_field_list:
                            breakby_field_list.append(field)

                # translates into a csv list while handling few more options
                trackme_root_splitby = []
                for field in breakby_field_list:
                    if field in ("index", "sourcetype"):
                        trackme_root_splitby.append(field)
                    elif field == "splunk_server":
                        if dsm_tstats_root_breakby_include_splunk_server:
                            trackme_root_splitby.append(field)
                    elif field == "host":
                        # if host is part of the custom break by fields, then including host is mandatory
                        if (
                            not dsm_tstats_root_breakby_include_host
                            and "host" in custom_breakby_field_list
                        ):
                            dsm_tstats_root_breakby_include_host = True
                            trackme_root_splitby.append(field)
                        elif dsm_tstats_root_breakby_include_host:
                            trackme_root_splitby.append(field)
                    else:
                        trackme_root_splitby.append(field)

                # return as csv list
                trackme_root_splitby = ",".join(trackme_root_splitby)

                # aggreg split by (required for tstats searches)
                trackme_aggreg_splitby_list = ["index", "sourcetype"]
                if breakby_field and breakby_field != "merged":

                    # sourcetype to any with a custom breakby
                    if not breakby_field_include_sourcetype:

                        # turn into a list
                        custom_breakby_field_list = breakby_field.split(",")

                        # remove sourcetype from custom_breakby_field_list
                        if "sourcetype" in custom_breakby_field_list:
                            custom_breakby_field_list.remove("sourcetype")

                    # otherwise
                    else:
                        # turn into a list
                        custom_breakby_field_list = breakby_field.split(",")

                    for field in custom_breakby_field_list:
                        if not field in trackme_aggreg_splitby_list:
                            trackme_aggreg_splitby_list.append(field)

                # translates into a csv list
                trackme_aggreg_splitby = ",".join(trackme_aggreg_splitby_list)

            elif component == "dhm":
                # merged mode: drop sourcetype from the tstats root split-by and treat
                # sourcetype as "@all" downstream. Entity is still keyed by host
                # (DHM is host-centric); only the per-sourcetype dimension is collapsed.
                dhm_is_merged = breakby_field == "merged"
                # SPL fragment that collapses sourcetype to "@all" in merged mode,
                # injected between the tstats root and the bucket span step.
                dhm_merged_sourcetype_eval_local = (
                    '\n``` merged mode ```\n| eval sourcetype="@all"' if dhm_is_merged else ""
                )
                # Same fragment but for remote (splunkremotesearch) — quotes are
                # escaped because the string is embedded inside a `search="..."`.
                dhm_merged_sourcetype_eval_remote = (
                    '\n``` merged mode ```\n| eval sourcetype=\\"@all\\"' if dhm_is_merged else ""
                )

                # "none" tstats root time span — drop _time and span= from the
                # root tstats by-clause and inject `eval _time=now()` so the
                # rest of the pipeline still has a single (synthetic) time
                # bucket. Trades per-bucket latency accuracy for cheaper root
                # tstats execution. The injected eval has no quoted strings,
                # so the same fragment works for both local and remote
                # (splunkremotesearch) variants.
                dhm_is_no_span = str(dhm_tstats_root_time_span).lower() == "none"
                dhm_no_span_eval = (
                    '\n``` no tstats time span ```\n| eval _time=now()'
                    if dhm_is_no_span
                    else ""
                )

                # Effective extras: empty if merged (mutually exclusive by design).
                # breakby_extra_fields has already been normalized at the
                # request-parsing step (reserved names, dedup, cap, type check).
                dhm_effective_extras = (
                    [] if dhm_is_merged else list(breakby_extra_fields or [])
                )

                breakby_field_list = ["index", "sourcetype", "splunk_server"]
                if breakby_field and not dhm_is_merged:
                    # breakby_field is a single host identifier field — no CSV split.
                    if breakby_field not in breakby_field_list:
                        breakby_field_list.append(breakby_field)
                    # set meta
                    trackme_dhm_host_meta = str(breakby_field)
                else:
                    breakby_field_list.append("host")
                    # set meta (entity keyed by host in both standard and merged modes)
                    trackme_dhm_host_meta = "host"

                # Append extras after the host identifier — they enter both
                # the root tstats split-by and the aggreg split-by, extending
                # the per-host combo grain.
                for f in dhm_effective_extras:
                    if f not in breakby_field_list:
                        breakby_field_list.append(f)

                # translates into a csv list while handling few more options
                trackme_root_splitby = []
                for field in breakby_field_list:
                    if field == "index":
                        trackme_root_splitby.append(field)
                    elif field == "sourcetype":
                        # In merged mode, drop sourcetype from the tstats root split-by;
                        # `eval sourcetype="@all"` is injected after the root tstats below.
                        if not dhm_is_merged:
                            trackme_root_splitby.append(field)
                    elif field == "splunk_server":
                        if dhm_tstats_root_breakby_include_splunk_server:
                            trackme_root_splitby.append(field)
                    else:
                        trackme_root_splitby.append(field)

                # return as csv list
                trackme_root_splitby = ",".join(trackme_root_splitby)

                # aggreg split by (required for tstats searches)
                # In merged mode, sourcetype is kept here because it is set to "@all"
                # immediately after the root tstats so the aggregation rolls up per index.
                trackme_aggreg_splitby_list = ["index", "sourcetype"]
                if breakby_field and not dhm_is_merged:
                    if breakby_field not in trackme_aggreg_splitby_list:
                        trackme_aggreg_splitby_list.append(breakby_field)
                else:
                    trackme_aggreg_splitby_list.append("host")

                for f in dhm_effective_extras:
                    if f not in trackme_aggreg_splitby_list:
                        trackme_aggreg_splitby_list.append(f)

                # translates into a csv list
                trackme_aggreg_splitby = ",".join(trackme_aggreg_splitby_list)

                # SPL fragment that builds _trackme_combo_extras_str — picked
                # up by the trackme_dhm_tracker_abstract macro to extend
                # combo_id beyond (index, sourcetype). Shared helper in
                # trackme_libs_splk_feeds keeps the encoding contract
                # identical to generate_dhm_report_search — see the
                # helper's docstring for the encoding rules. Empty
                # extras → empty fragments → byte-identical SPL to
                # pre-extras trackers.
                dhm_extras_eval_local, dhm_extras_eval_remote = (
                    _build_dhm_extras_eval_fragments(dhm_effective_extras)
                )

            elif component == "mhm":
                breakby_field_list = ["metric_name", "index"]
                if breakby_field:
                    custom_breakby_field_list = breakby_field.split(",")
                    for field in custom_breakby_field_list:
                        if not field in breakby_field_list:
                            breakby_field_list.append(field)
                    # set meta
                    trackme_mhm_host_meta = str(breakby_field)
                else:
                    breakby_field_list.append("host")
                    # set meta
                    trackme_mhm_host_meta = "host"

                # translates into a csv list
                trackme_root_splitby = ",".join(breakby_field_list)

            #
            # step 2: define the intermediate aggreg search string
            #

            if component == "dsm":
                if tracker_type == "local":
                    if breakby_field:
                        if breakby_field == "merged":
                            # remove sourcetype
                            trackme_aggreg_splitby_list = []
                            trackme_aggreg_splitby_list = trackme_aggreg_splitby.split(
                                ","
                            )
                            if "sourcetype" in trackme_aggreg_splitby_list:
                                trackme_aggreg_splitby_list.remove("sourcetype")
                            trackme_aggreg_splitby = ",".join(
                                trackme_aggreg_splitby_list
                            )

                            # set object definition
                            object_definition = ' | eval object=data_index . ":@all"'

                            if search_mode in "tstats":
                                search_string_aggreg = (
                                    "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                    + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                    + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                    + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                    + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                    + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                    + str(trackme_aggreg_splitby)
                                    + "\n| eval dcount_host=round(global_dcount_host, 0)"
                                    + "\n| eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                                    + '\n| rename index as data_index | eval data_sourcetype="all"'
                                    + object_definition
                                )

                            elif search_mode in "raw":
                                search_string_aggreg = (
                                    "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                    + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                    + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                    + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                    + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                    + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                    + str(trackme_aggreg_splitby)
                                    + "\n"
                                    + " | eval dcount_host=round(global_dcount_host, 0)\n"
                                    + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)\n"
                                    + " | rename index as data_index\n"
                                    + object_definition
                                )

                        else:

                            # support multiple fields
                            break_by_field = breakby_field.split(",")

                            # if sourcetype to any, remove sourcetype (sourcetype=* or sourcetype="*") from the list
                            if not breakby_field_include_sourcetype:
                                for field in break_by_field:
                                    if "sourcetype" in field:
                                        break_by_field.remove(field)

                            #
                            # tstats mode
                            #

                            if search_mode in "tstats":

                                if len(break_by_field) == 1:

                                    # sourcetype to any with a custom breakby
                                    if not breakby_field_include_sourcetype:
                                        object_definition = (
                                            ' | eval object=data_index . ":" . "any" . "|key:" . "'
                                            + str(breakby_field)
                                            + '" . "|" . '
                                            + str(breakby_field)
                                        )

                                    # otherwise
                                    else:
                                        object_definition = (
                                            ' | eval object=data_index . ":" . data_sourcetype . "|key:" . "'
                                            + str(breakby_field)
                                            + '" . "|" . '
                                            + str(breakby_field)
                                        )

                                else:

                                    # sourcetype to any with a custom breakby
                                    if not breakby_field_include_sourcetype:
                                        object_definition = (
                                            ' | eval object=data_index . ":" . "any" . "|key:" . "'
                                            + str(breakby_field).replace(",", ";")
                                            + '" . "|"'
                                        )

                                    # otherwise
                                    else:
                                        object_definition = (
                                            ' | eval object=data_index . ":" . data_sourcetype . "|key:" . "'
                                            + str(breakby_field).replace(",", ";")
                                            + '" . "|"'
                                        )

                                    append_count = 0
                                    for subbreak_by_field in break_by_field:
                                        if append_count == 0:
                                            object_definition = (
                                                object_definition
                                                + " . "
                                                + subbreak_by_field
                                            )
                                        else:
                                            object_definition = (
                                                object_definition
                                                + " . "
                                                + '";"'
                                                + " . "
                                                + subbreak_by_field
                                            )
                                        append_count += 1

                                # if sourcetype to any
                                if not breakby_field_include_sourcetype:
                                    search_string_aggreg = (
                                        "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                        + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                        + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                        + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                        + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                        + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                        + str(trackme_aggreg_splitby)
                                        + "\n| eval dcount_host=round(global_dcount_host, 0)"
                                        + "\n| eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                                        + '\n| rename index as data_index | eval data_sourcetype="any"'
                                        + object_definition
                                    )

                                else:
                                    search_string_aggreg = (
                                        "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                        + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                        + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                        + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                        + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                        + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                        + str(trackme_aggreg_splitby)
                                        + "\n| eval dcount_host=round(global_dcount_host, 0)"
                                        + "\n| eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                                        + "\n| rename index as data_index, sourcetype as data_sourcetype"
                                        + object_definition
                                    )

                            #
                            # raw mode
                            #

                            elif search_mode in "raw":

                                if len(break_by_field) == 1:

                                    # sourcetype to any with a custom breakby
                                    if not breakby_field_include_sourcetype:
                                        object_definition = (
                                            ' | eval object=data_index . ":" . "any" . "|rawkey:" . "'
                                            + str(breakby_field)
                                            + '" . "|" . '
                                            + str(breakby_field)
                                        )

                                    # otherwise
                                    object_definition = (
                                        ' | eval object=data_index . ":" . data_sourcetype . "|rawkey:" . "'
                                        + str(breakby_field)
                                        + '" . "|" . '
                                        + str(breakby_field)
                                    )

                                else:

                                    # sourcetype to any with a custom breakby
                                    if not breakby_field_include_sourcetype:
                                        object_definition = (
                                            ' | eval object=data_index . ":" . "any" . "|rawkey:" . "'
                                            + str(breakby_field).replace(",", ";")
                                            + '" . "|"'
                                        )

                                        # otherwise
                                        object_definition = (
                                            ' | eval object=data_index . ":" . data_sourcetype . "|rawkey:" . "'
                                            + str(breakby_field).replace(",", ";")
                                            + '" . "|"'
                                        )

                                    append_count = 0
                                    for subbreak_by_field in break_by_field:
                                        if append_count == 0:
                                            object_definition = (
                                                object_definition
                                                + " . "
                                                + subbreak_by_field
                                            )
                                        else:
                                            object_definition = (
                                                object_definition
                                                + " . "
                                                + '";"'
                                                + " . "
                                                + subbreak_by_field
                                            )
                                        append_count += 1

                                # if sourcetype to any
                                if not breakby_field_include_sourcetype:
                                    search_string_aggreg = (
                                        "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                        + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                        + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                        + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                        + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                        + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                        + str(trackme_aggreg_splitby)
                                        + "\n"
                                        + " | eval dcount_host=round(global_dcount_host, 0)\n"
                                        + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)\n"
                                        + ' | rename index as data_index | eval data_sourcetype="any"\n'
                                        + object_definition
                                    )

                                # otherwise
                                else:
                                    search_string_aggreg = (
                                        "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                        + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                        + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                        + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                        + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                        + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                        + str(trackme_aggreg_splitby)
                                        + "\n"
                                        + " | eval dcount_host=round(global_dcount_host, 0)\n"
                                        + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)\n"
                                        + " | rename index as data_index, sourcetype as data_sourcetype\n"
                                        + object_definition
                                    )
                    else:
                        if search_mode in "tstats":
                            search_string_aggreg = (
                                "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                + str(trackme_aggreg_splitby)
                                + " | eval dcount_host=round(global_dcount_host, 0)\n"
                                + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                                + " | rename index as data_index, sourcetype as data_sourcetype"
                                + ' | eval object=data_index . ":" . data_sourcetype'
                            )

                        elif search_mode in "raw":
                            search_string_aggreg = (
                                "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                + str(trackme_aggreg_splitby)
                                + " | eval dcount_host=round(global_dcount_host, 0)\n"
                                + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                                + " | rename index as data_index, sourcetype as data_sourcetype"
                                + ' | eval object=data_index . ":" . data_sourcetype'
                            )

                elif tracker_type == "remote":
                    if breakby_field:
                        if breakby_field == "merged":
                            # remove sourcetype
                            trackme_aggreg_splitby_list = []
                            trackme_aggreg_splitby_list = trackme_aggreg_splitby.split(
                                ","
                            )
                            if "sourcetype" in trackme_aggreg_splitby_list:
                                trackme_aggreg_splitby_list.remove("sourcetype")
                            trackme_aggreg_splitby = ",".join(
                                trackme_aggreg_splitby_list
                            )

                            object_definition = (
                                ' | eval object=\\"remote|account:'
                                + str(account.replace('"', ""))
                                + '|\\" . data_index . \\":@all\\"'
                            )

                            if search_mode in "tstats":
                                search_string_aggreg = (
                                    "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                    + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                    + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                    + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                    + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                    + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                    + str(trackme_aggreg_splitby)
                                    + " | eval dcount_host=round(global_dcount_host, 0)\n"
                                    + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                                    + ' | rename index as data_index | eval data_sourcetype=\\"all\\"'
                                    + object_definition
                                )

                            elif search_mode in "raw":
                                search_string_aggreg = (
                                    "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                    + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                    + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                    + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                    + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                    + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                    + str(trackme_aggreg_splitby)
                                    + " | eval dcount_host=round(global_dcount_host, 0)\n"
                                    + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                                    + ' | rename index as data_index | eval data_sourcetype=\\"all\\"'
                                    + object_definition
                                )

                        else:

                            # support multiple fields
                            break_by_field = breakby_field.split(",")

                            # if sourcetype to any, remove sourcetype (sourcetype=* or sourcetype="*") from the list
                            if not breakby_field_include_sourcetype:
                                for field in break_by_field:
                                    if "sourcetype" in field:
                                        break_by_field.remove(field)

                            #
                            # tstats mode
                            #

                            if search_mode in "tstats":

                                if len(break_by_field) == 1:

                                    # sourcetype to any with a custom breakby
                                    if not breakby_field_include_sourcetype:
                                        object_definition = (
                                            ' | eval object=\\"remote|account:'
                                            + str(account.replace('"', ""))
                                            + '|\\" . data_index . \\":\\" . \\"any\\" . \\"|key:\\" . \\"'
                                            + str(breakby_field)
                                            + '\\" . \\"|\\" . '
                                            + str(breakby_field)
                                        )

                                    else:
                                        object_definition = (
                                            ' | eval object=\\"remote|account:'
                                            + str(account.replace('"', ""))
                                            + '|\\" . data_index . \\":\\" . data_sourcetype . \\"|key:\\" . \\"'
                                            + str(breakby_field)
                                            + '\\" . \\"|\\" . '
                                            + str(breakby_field)
                                        )

                                else:

                                    # sourcetype to any with a custom breakby
                                    if not breakby_field_include_sourcetype:
                                        object_definition = (
                                            ' | eval object=\\"remote|account:'
                                            + str(account.replace('"', ""))
                                            + '|\\" . data_index . \\":\\" . \\"any\\" . \\"|key:\\" . \\"'
                                            + str(breakby_field).replace(",", ";")
                                            + '\\" . \\"|\\"'
                                        )

                                    else:
                                        object_definition = (
                                            ' | eval object=\\"remote|account:'
                                            + str(account.replace('"', ""))
                                            + '|\\" . data_index . \\":\\" . data_sourcetype . \\"|key:\\" . \\"'
                                            + str(breakby_field).replace(",", ";")
                                            + '\\" . \\"|\\"'
                                        )

                                    append_count = 0
                                    for subbreak_by_field in break_by_field:
                                        if append_count == 0:
                                            object_definition = (
                                                object_definition
                                                + " . "
                                                + subbreak_by_field
                                            )
                                        else:
                                            object_definition = (
                                                object_definition
                                                + " . "
                                                + '\\";\\"'
                                                + " . "
                                                + subbreak_by_field
                                            )
                                        append_count += 1

                                # if sourcetype to any
                                if not breakby_field_include_sourcetype:
                                    search_string_aggreg = (
                                        "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                        + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                        + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                        + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                        + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                        + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                        + str(trackme_aggreg_splitby)
                                        + " | eval dcount_host=round(global_dcount_host, 0)\n"
                                        + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                                        + ' | rename index as data_index | eval data_sourcetype=\\"any\\"'
                                        + object_definition
                                    )

                                # otherwise
                                else:
                                    search_string_aggreg = (
                                        "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                        + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                        + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                        + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                        + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                        + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                        + str(trackme_aggreg_splitby)
                                        + " | eval dcount_host=round(global_dcount_host, 0)\n"
                                        + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                                        + " | rename index as data_index, sourcetype as data_sourcetype"
                                        + object_definition
                                    )

                            #
                            # raw mode
                            #

                            elif search_mode in "raw":

                                if len(break_by_field) == 1:

                                    # sourcetype to any with a custom breakby
                                    if not breakby_field_include_sourcetype:
                                        object_definition = (
                                            ' | eval object=\\"remoteraw|account:'
                                            + str(account.replace('"', ""))
                                            + '|\\" . data_index . \\":\\" . \\"any\\" . \\"|rawkey:\\" . \\"'
                                            + str(breakby_field)
                                            + '\\" . \\"|\\" . '
                                            + str(breakby_field)
                                        )

                                    # otherwise
                                    else:
                                        object_definition = (
                                            ' | eval object=\\"remoteraw|account:'
                                            + str(account.replace('"', ""))
                                            + '|\\" . data_index . \\":\\" . data_sourcetype . \\"|rawkey:\\" . \\"'
                                            + str(breakby_field)
                                            + '\\" . \\"|\\" . '
                                            + str(breakby_field)
                                        )

                                else:

                                    # sourcetype to any with a custom breakby
                                    if not breakby_field_include_sourcetype:
                                        object_definition = (
                                            ' | eval object=\\"remoteraw|account:'
                                            + str(account.replace('"', ""))
                                            + '|\\" . data_index . \\":\\" . \\"any\\" . \\"|rawkey:\\" . \\"'
                                            + str(breakby_field).replace(",", ";")
                                            + '\\" . \\"|\\"'
                                        )

                                    # otherwise
                                    else:
                                        object_definition = (
                                            ' | eval object=\\"remoteraw|account:'
                                            + str(account.replace('"', ""))
                                            + '|\\" . data_index . \\":\\" . data_sourcetype . \\"|rawkey:\\" . \\"'
                                            + str(breakby_field).replace(",", ";")
                                            + '\\" . \\"|\\"'
                                        )

                                    append_count = 0
                                    for subbreak_by_field in break_by_field:
                                        if append_count == 0:
                                            object_definition = (
                                                object_definition
                                                + " . "
                                                + subbreak_by_field
                                            )
                                        else:
                                            object_definition = (
                                                object_definition
                                                + " . "
                                                + '\\";\\"'
                                                + " . "
                                                + subbreak_by_field
                                            )
                                        append_count += 1

                                # if sourcetype to any
                                if not breakby_field_include_sourcetype:
                                    search_string_aggreg = (
                                        "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                        + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                        + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                        + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                        + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                        + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                        + str(trackme_aggreg_splitby)
                                        + " | eval dcount_host=round(global_dcount_host, 0)\n"
                                        + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                                        + ' | rename index as data_index | eval data_sourcetype=\\"any\\"'
                                        + object_definition
                                    )

                                # otherwise
                                else:
                                    search_string_aggreg = (
                                        "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                        + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                        + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                        + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                        + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                        + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                        + str(trackme_aggreg_splitby)
                                        + " | eval dcount_host=round(global_dcount_host, 0)\n"
                                        + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                                        + " | rename index as data_index, sourcetype as data_sourcetype"
                                        + object_definition
                                    )

                    else:
                        if search_mode in "tstats":
                            search_string_aggreg = (
                                "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                + " max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                + str(trackme_aggreg_splitby)
                                + " | eval dcount_host=round(global_dcount_host, 0)\n"
                                + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                                + " | rename index as data_index, sourcetype as data_sourcetype"
                                + ' | eval object=\\"remote|account:'
                                + str(account.replace('"', ""))
                                + '|\\" . data_index . \\":\\" . data_sourcetype'
                            )

                        elif search_mode in "raw":
                            search_string_aggreg = (
                                "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                                + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                                + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                                + " max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                                + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                                + "sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by "
                                + str(trackme_aggreg_splitby)
                                + " | eval dcount_host=round(global_dcount_host, 0)\n"
                                + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                                + " | rename index as data_index, sourcetype as data_sourcetype"
                                + ' | eval object=\\"remoteraw|account:'
                                + str(account.replace('"', ""))
                                + '|\\" . data_index . \\":\\" . data_sourcetype'
                            )

            elif component == "dhm":
                if tracker_type == "local":
                    search_string_aggreg = (
                        "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                        + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                        + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                        + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                        + "sum(data_eventcount) as data_eventcount by "
                        + str(trackme_aggreg_splitby)
                        + "\n"
                        + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)\n"
                        + " | eval alias="
                        + str(trackme_dhm_host_meta)
                        + ' | eval host="key:'
                        + str(trackme_dhm_host_meta)
                        + '|" . '
                        + str(trackme_dhm_host_meta)
                    )

                elif tracker_type == "remote":
                    if search_mode in "tstats":
                        search_string_aggreg = (
                            "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                            + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                            + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                            + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                            + "sum(data_eventcount) as data_eventcount by "
                            + str(trackme_aggreg_splitby)
                            + "\n"
                            + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)\n"
                            + " | eval alias="
                            + str(trackme_dhm_host_meta)
                            + ' | eval host=\\"remote|account:'
                            + str(account.replace('"', ""))
                            + "|key:"
                            + str(trackme_dhm_host_meta)
                            + '|\\" . '
                            + str(trackme_dhm_host_meta)
                        )

                    elif search_mode in "raw":
                        search_string_aggreg = (
                            "stats sum(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                            + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                            + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                            + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                            + "sum(data_eventcount) as data_eventcount by "
                            + str(trackme_aggreg_splitby)
                            + "\n"
                            + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)\n"
                            + " | eval alias="
                            + str(trackme_dhm_host_meta)
                            + ' | eval host=\\"remoteraw|account:'
                            + str(account.replace('"', ""))
                            + "|key:"
                            + str(trackme_dhm_host_meta)
                            + '|\\" . '
                            + str(trackme_dhm_host_meta)
                        )

            elif component == "mhm":
                if tracker_type == "local":
                    search_string_aggreg = (
                        "stats max(_time) as _time by metric_name, index, "
                        + str(trackme_mhm_host_meta)
                        + " | eval alias="
                        + str(trackme_mhm_host_meta)
                        + ' | eval host="key:'
                        + str(trackme_mhm_host_meta)
                        + '|" . '
                        + str(trackme_mhm_host_meta)
                    )

                elif tracker_type == "remote":
                    search_string_aggreg = (
                        "stats max(_time) as _time by metric_name, index, "
                        + str(trackme_mhm_host_meta)
                        + " | eval alias="
                        + str(trackme_mhm_host_meta)
                        + ' | eval host=\\"remote|account:'
                        + str(account.replace('"', ""))
                        + "|key:"
                        + str(trackme_mhm_host_meta)
                        + '|\\" . '
                        + str(trackme_mhm_host_meta)
                    )

            #
            # step 3: create the hybrid root constraint macro
            #

            root_constraint_macro = "trackme_%s_hybrid_root_constraint_%s_tenant_%s" % (
                component,
                tracker_name,
                tenant_id,
            )
            macro_acl = {
                "owner": owner,
                "sharing": trackme_default_sharing,
                "perms.write": vtenant_record.get("tenant_roles_admin"),
                "perms.read": f"{vtenant_record.get('tenant_roles_user')},{vtenant_record.get('tenant_roles_power')}",
            }
            macro_result = trackme_create_macro(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                root_constraint_macro,
                root_constraint,
                owner,
                macro_acl,
            )

            #
            # step 4: create the abstract report
            #

            if component == "dsm":
                # if break by merged, remove the sourcetype
                if breakby_field and breakby_field == "merged":
                    trackme_aggreg_splitby = trackme_aggreg_splitby.split(",")
                    if "sourcetype" in trackme_aggreg_splitby:
                        trackme_aggreg_splitby.remove("sourcetype")
                    trackme_aggreg_splitby = ",".join(trackme_aggreg_splitby)

                if tracker_type == "local":
                    report_name = (
                        "trackme_dsm_hybrid_abstract_"
                        + str(tracker_name)
                        + "_tenant_"
                        + str(tenant_id)
                    )
                    if search_mode in "tstats":
                        if dsm_tstats_root_breakby_include_host:
                            report_search = (
                                "| tstats max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                                + "count as data_eventcount where `"
                                + str(root_constraint_macro)
                                + "`"
                                + ' _index_earliest="'
                                + index_earliest_time
                                + '" _index_latest="'
                                + index_latest_time
                                + '"'
                                + (
                                    " by " + str(trackme_root_splitby)
                                    if dsm_is_no_span
                                    else (
                                        " by _time,"
                                        + str(trackme_root_splitby)
                                        + " span="
                                        + str(dsm_tstats_root_time_span)
                                    )
                                )
                                + "\n| eval data_last_ingestion_lag_seen=data_last_ingest-data_last_time_seen"
                                + dsm_no_span_eval
                                + "\n``` intermediate calculation ```"
                                + "\n| bucket _time span=1m"
                                + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, max(data_last_time_seen) as data_last_time_seen, sum(data_eventcount) as data_eventcount, dc(host) as dcount_host by _time,"
                                + str(trackme_aggreg_splitby)
                                + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen, max(dcount_host) as global_dcount_host by "
                                + str(trackme_aggreg_splitby)
                                + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                                + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                                + str(trackme_aggreg_splitby)
                                + "\n| "
                                + str(search_string_aggreg)
                                + "\n``` tenant_id ```"
                                + '\n| eval tenant_id="'
                                + str(tenant_id)
                                + '"'
                                + "\n``` call the abstract macro ```"
                                + "\n`trackme_dsm_tracker_abstract("
                                + str(tenant_id)
                                + ", tstats)`"
                            )

                        else:
                            report_search = (
                                "| tstats max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                                + "count as data_eventcount, dc(host) as host where `"
                                + str(root_constraint_macro)
                                + "`"
                                + ' _index_earliest="'
                                + index_earliest_time
                                + '" _index_latest="'
                                + index_latest_time
                                + '"'
                                + (
                                    " by " + str(trackme_root_splitby)
                                    if dsm_is_no_span
                                    else (
                                        " by _time,"
                                        + str(trackme_root_splitby)
                                        + " span="
                                        + str(dsm_tstats_root_time_span)
                                    )
                                )
                                + "\n| eval data_last_ingestion_lag_seen=data_last_ingest-data_last_time_seen"
                                + dsm_no_span_eval
                                + "\n``` intermediate calculation ```"
                                + "\n| bucket _time span=1m"
                                + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, max(data_last_time_seen) as data_last_time_seen, sum(data_eventcount) as data_eventcount, max(host) as dcount_host by _time,"
                                + str(trackme_aggreg_splitby)
                                + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen, max(dcount_host) as global_dcount_host by "
                                + str(trackme_aggreg_splitby)
                                + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                                + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                                + str(trackme_aggreg_splitby)
                                + "\n| "
                                + str(search_string_aggreg)
                                + "\n``` tenant_id ```"
                                + '\n| eval tenant_id="'
                                + str(tenant_id)
                                + '"'
                                + "\n``` call the abstract macro ```"
                                + "\n`trackme_dsm_tracker_abstract("
                                + str(tenant_id)
                                + ", tstats)`"
                            )

                    elif search_mode in "raw":
                        report_search = (
                            "`"
                            + str(root_constraint_macro)
                            + '` _index_earliest="'
                            + index_earliest_time
                            + '" _index_latest="'
                            + index_latest_time
                            + '"'
                            + "\n| eval data_last_ingestion_lag_seen=(_indextime-_time)"
                            + "\n``` intermediate calculation ```"
                            + "\n| bucket _time span=1m"
                            + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                            + "count as data_eventcount, dc(host) as dcount_host by _time,"
                            + str(trackme_aggreg_splitby)
                            + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen by "
                            + str(trackme_aggreg_splitby)
                            + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                            + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                            + str(trackme_aggreg_splitby)
                            + "\n| "
                            + str(search_string_aggreg)
                            + "\n``` tenant_id ```"
                            + '\n| eval tenant_id="'
                            + str(tenant_id)
                            + '"'
                            + "\n``` call the abstract macro ```"
                            + "\n`trackme_dsm_tracker_abstract("
                            + str(tenant_id)
                            + ", raw)`"
                        )

                elif tracker_type == "remote":
                    report_name = (
                        "trackme_dsm_hybrid_abstract_"
                        + str(tracker_name)
                        + "_tenant_"
                        + str(tenant_id)
                    )
                    if search_mode in "tstats":
                        if dsm_tstats_root_breakby_include_host:
                            report_search = (
                                '| splunkremotesearch account="'
                                + str(account)
                                + '"'
                                + ' search="'
                                + "| tstats max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                                + "count as data_eventcount where "
                                + str(root_constraint.replace('"', '\\"'))
                                + ' _index_earliest="'
                                + index_earliest_time
                                + '" _index_latest="'
                                + index_latest_time
                                + '"'
                                + (
                                    " by " + str(trackme_root_splitby)
                                    if dsm_is_no_span
                                    else (
                                        " by _time,"
                                        + str(trackme_root_splitby)
                                        + " span="
                                        + str(dsm_tstats_root_time_span)
                                    )
                                )
                                + "\n| eval data_last_ingestion_lag_seen=data_last_ingest-data_last_time_seen"
                                + dsm_no_span_eval
                                + "\n``` intermediate calculation ```"
                                + "\n| bucket _time span=1m"
                                + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, max(data_last_time_seen) as data_last_time_seen, sum(data_eventcount) as data_eventcount, dc(host) as dcount_host by _time,"
                                + str(trackme_aggreg_splitby)
                                + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen, max(dcount_host) as global_dcount_host by "
                                + str(trackme_aggreg_splitby)
                                + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                                + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                                + str(trackme_aggreg_splitby)
                                + "\n| "
                                + str(search_string_aggreg)
                                + '" earliest="'
                                + str(earliest_time)
                                + '" '
                                + 'latest="'
                                + str(latest_time)
                                + '" register_component="True" tenant_id="'
                                + str(tenant_id)
                                + '" component="splk-dsm" report="'
                                + "trackme_dsm_hybrid_"
                                + str(tracker_name)
                                + "_wrapper"
                                + "_tenant_"
                                + str(tenant_id)
                                + '"'
                                + "\n``` set tenant_id ```\n"
                                + '\n| eval tenant_id="'
                                + str(tenant_id)
                                + '"'
                                + "\n``` call the abstract macro ```"
                                + "\n`trackme_dsm_tracker_abstract("
                                + str(tenant_id)
                                + ", tstats)`"
                            )

                        else:
                            report_search = (
                                '| splunkremotesearch account="'
                                + str(account)
                                + '"'
                                + ' search="'
                                + "| tstats max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                                + "count as data_eventcount, dc(host) as host where "
                                + str(root_constraint.replace('"', '\\"'))
                                + ' _index_earliest="'
                                + index_earliest_time
                                + '" _index_latest="'
                                + index_latest_time
                                + '"'
                                + (
                                    " by " + str(trackme_root_splitby)
                                    if dsm_is_no_span
                                    else (
                                        " by _time,"
                                        + str(trackme_root_splitby)
                                        + " span="
                                        + str(dsm_tstats_root_time_span)
                                    )
                                )
                                + "\n| eval data_last_ingestion_lag_seen=data_last_ingest-data_last_time_seen"
                                + dsm_no_span_eval
                                + "\n``` intermediate calculation ```"
                                + "\n| bucket _time span=1m"
                                + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, max(data_last_time_seen) as data_last_time_seen, sum(data_eventcount) as data_eventcount, max(host) as dcount_host by _time,"
                                + str(trackme_aggreg_splitby)
                                + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen, max(dcount_host) as global_dcount_host by "
                                + str(trackme_aggreg_splitby)
                                + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                                + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                                + str(trackme_aggreg_splitby)
                                + "\n| "
                                + str(search_string_aggreg)
                                + '" earliest="'
                                + str(earliest_time)
                                + '" '
                                + 'latest="'
                                + str(latest_time)
                                + '" register_component="True" tenant_id="'
                                + str(tenant_id)
                                + '" component="splk-dsm" report="'
                                + "trackme_dsm_hybrid_"
                                + str(tracker_name)
                                + "_wrapper"
                                + "_tenant_"
                                + str(tenant_id)
                                + '"'
                                + "\n``` set tenant_id ```\n"
                                + '\n| eval tenant_id="'
                                + str(tenant_id)
                                + '"'
                                + "\n``` call the abstract macro ```"
                                + "\n`trackme_dsm_tracker_abstract("
                                + str(tenant_id)
                                + ", tstats)`"
                            )

                    elif search_mode in "raw":
                        report_search = (
                            '| splunkremotesearch account="'
                            + str(account)
                            + '"'
                            + ' search="'
                            + "search "
                            + str(root_constraint.replace('"', '\\"'))
                            + ' _index_earliest="'
                            + index_earliest_time
                            + '" _index_latest="'
                            + index_latest_time
                            + '"'
                            + "\n| eval data_last_ingestion_lag_seen=(_indextime-_time)"
                            + "\n``` intermediate calculation ```"
                            + "\n| bucket _time span=1m"
                            + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                            + "count as data_eventcount, dc(host) as dcount_host by _time,"
                            + str(trackme_aggreg_splitby)
                            + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen by "
                            + str(trackme_aggreg_splitby)
                            + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                            + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                            + str(trackme_aggreg_splitby)
                            + "\n| "
                            + str(search_string_aggreg)
                            + '" earliest="'
                            + str(earliest_time)
                            + '" '
                            + 'latest="'
                            + str(latest_time)
                            + '" register_component="True" tenant_id="'
                            + str(tenant_id)
                            + '" component="splk-dsm" report="'
                            + "trackme_dsm_hybrid_"
                            + str(tracker_name)
                            + "_wrapper"
                            + "_tenant_"
                            + str(tenant_id)
                            + '"'
                            + "\n``` tenant_id ```"
                            + '\n| eval tenant_id="'
                            + str(tenant_id)
                            + '"'
                            + "\n``` call the abstract macro ```"
                            + "\n`trackme_dsm_tracker_abstract("
                            + str(tenant_id)
                            + ", raw)`"
                        )

            elif component == "dhm":
                if tracker_type == "local":
                    report_name = (
                        "trackme_dhm_hybrid_abstract_"
                        + str(tracker_name)
                        + "_tenant_"
                        + str(tenant_id)
                    )
                    if search_mode in "tstats":
                        report_search = (
                            "| tstats max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                            + 'count as data_eventcount, dc(host) as dcount_host where (host=* host!="") `'
                            + str(root_constraint_macro)
                            + "`"
                            + ' _index_earliest="'
                            + index_earliest_time
                            + '" _index_latest="'
                            + index_latest_time
                            + '"'
                            + (
                                " by " + str(trackme_root_splitby)
                                if dhm_is_no_span
                                else (
                                    " by _time,"
                                    + str(trackme_root_splitby)
                                    + " span="
                                    + str(dhm_tstats_root_time_span)
                                )
                            )
                            + "\n| eval data_last_ingestion_lag_seen=data_last_ingest-data_last_time_seen"
                            + dhm_merged_sourcetype_eval_local
                            + dhm_no_span_eval
                            + "\n``` intermediate calculation ```"
                            + "\n| bucket _time span=1m"
                            + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, max(data_last_time_seen) as data_last_time_seen, sum(data_eventcount) as data_eventcount by _time,"
                            + str(trackme_aggreg_splitby)
                            + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen, max(dcount_host) as global_dcount_host by "
                            + str(trackme_aggreg_splitby)
                            + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                            + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                            + str(trackme_aggreg_splitby)
                            + "\n| "
                            + str(search_string_aggreg)
                            + dhm_extras_eval_local
                            + "\n``` tenant_id ```"
                            + '\n| eval tenant_id="'
                            + str(tenant_id)
                            + '"'
                            + "\n``` call the abstract macro ```"
                            + "\n| `trackme_dhm_tracker_abstract("
                            + str(tenant_id)
                            + ", tstats)`"
                        )

                    elif search_mode in "raw":
                        report_search = (
                            "`"
                            + str(root_constraint_macro)
                            + '` (host=* host!="")'
                            + ' _index_earliest="'
                            + index_earliest_time
                            + '" _index_latest="'
                            + index_latest_time
                            + '"'
                            + "\n| eval data_last_ingestion_lag_seen=(_indextime-_time)"
                            + dhm_merged_sourcetype_eval_local
                            + "\n``` intermediate calculation ```"
                            + "\n| bucket _time span=1m"
                            + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                            + "count as data_eventcount by _time,"
                            + str(trackme_aggreg_splitby)
                            + "\n| eval spantime=data_last_ingest | eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m by spantime,"
                            + str(trackme_aggreg_splitby)
                            + "\n| "
                            + str(search_string_aggreg)
                            + dhm_extras_eval_local
                            + "\n``` tenant_id ```\n"
                            + '\n| eval tenant_id="'
                            + str(tenant_id)
                            + '"'
                            + "\n``` call the abstract macro ```"
                            + "\n| `trackme_dhm_tracker_abstract("
                            + str(tenant_id)
                            + ", raw)`"
                        )

                elif tracker_type == "remote":
                    report_name = (
                        "trackme_dhm_hybrid_abstract_"
                        + str(tracker_name)
                        + "_tenant_"
                        + str(tenant_id)
                    )
                    if search_mode in "tstats":
                        report_search = (
                            '| splunkremotesearch account="'
                            + str(account)
                            + '"'
                            + ' search="'
                            + "| tstats max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                            + 'count as data_eventcount where (host=* host!=\\"\\") '
                            + str(root_constraint.replace('"', '\\"'))
                            + ' _index_earliest="'
                            + index_earliest_time
                            + '" _index_latest="'
                            + index_latest_time
                            + '"'
                            + (
                                " by " + str(trackme_root_splitby)
                                if dhm_is_no_span
                                else (
                                    " by _time,"
                                    + str(trackme_root_splitby)
                                    + " span="
                                    + str(dhm_tstats_root_time_span)
                                )
                            )
                            + "\n| eval data_last_ingestion_lag_seen=data_last_ingest-data_last_time_seen"
                            + dhm_merged_sourcetype_eval_remote
                            + dhm_no_span_eval
                            + "\n``` intermediate calculation ```"
                            + "\n| bucket _time span=1m"
                            + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, max(data_last_time_seen) as data_last_time_seen, sum(data_eventcount) as data_eventcount by _time,"
                            + str(trackme_aggreg_splitby)
                            + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen, max(dcount_host) as global_dcount_host by "
                            + str(trackme_aggreg_splitby)
                            + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                            + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                            + str(trackme_aggreg_splitby)
                            + "\n| "
                            + str(search_string_aggreg)
                            + dhm_extras_eval_remote
                            + '" earliest="'
                            + str(earliest_time)
                            + '" '
                            + 'latest="'
                            + str(latest_time)
                            + '" register_component="True" tenant_id="'
                            + str(tenant_id)
                            + '" component="splk-dhm" report="'
                            + "trackme_dhm_hybrid_"
                            + str(tracker_name)
                            + "_wrapper"
                            + "_tenant_"
                            + str(tenant_id)
                            + '"'
                            + "\n``` set tenant_id ```"
                            + '\n| eval tenant_id="'
                            + str(tenant_id)
                            + '"'
                            + "\n``` call the abstract macro ```"
                            + "\n| `trackme_dhm_tracker_abstract("
                            + str(tenant_id)
                            + ", tstats)`"
                        )

                    elif search_mode in "raw":
                        report_search = (
                            '| splunkremotesearch account="'
                            + str(account)
                            + '"'
                            + ' search="'
                            + 'search (host=* host!=\\"\\") '
                            + str(root_constraint.replace('"', '\\"'))
                            + ' _index_earliest="'
                            + index_earliest_time
                            + '" _index_latest="'
                            + index_latest_time
                            + '"'
                            + "\n| eval data_last_ingestion_lag_seen=(_indextime-_time)"
                            + dhm_merged_sourcetype_eval_remote
                            + "\n``` intermediate calculation ```"
                            + "\n| bucket _time span=1m"
                            + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                            + "count as data_eventcount, dc(host) as dcount_host by _time,"
                            + str(trackme_aggreg_splitby)
                            + "\n| eval spantime=data_last_ingest | eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m by spantime,"
                            + str(trackme_aggreg_splitby)
                            + "\n| "
                            + str(search_string_aggreg)
                            + dhm_extras_eval_remote
                            + '" earliest="'
                            + str(earliest_time)
                            + '" '
                            + 'latest="'
                            + str(latest_time)
                            + '" register_component="True" tenant_id="'
                            + str(tenant_id)
                            + '" component="splk-dhm" report="'
                            + "trackme_dhm_hybrid_"
                            + str(tracker_name)
                            + "_wrapper"
                            + "_tenant_"
                            + str(tenant_id)
                            + '"'
                            + "\n``` tenant_id ```"
                            + '\n| eval tenant_id="'
                            + str(tenant_id)
                            + '"'
                            + "\n``` call the abstract macro ```"
                            + "\n| `trackme_dhm_tracker_abstract("
                            + str(tenant_id)
                            + ", raw)`"
                        )

            elif component == "mhm":
                if tracker_type == "local":
                    report_name = (
                        "trackme_mhm_hybrid_abstract_"
                        + str(tracker_name)
                        + "_tenant_"
                        + str(tenant_id)
                    )
                    report_search = (
                        "| mstats latest(_value) as value where `"
                        + str(root_constraint_macro)
                        + "` by metric_name, index, "
                        + str(trackme_mhm_host_meta)
                        + " span=1m"
                        + "| "
                        + str(search_string_aggreg)
                        + "\n"
                        + "``` call the abstract macro ```"
                        + "| `trackme_mhm_tracker_abstract("
                        + str(tenant_id)
                        + ', host, "*")`'
                    )

                elif tracker_type == "remote":
                    report_name = (
                        "trackme_mhm_hybrid_abstract_"
                        + str(tracker_name)
                        + "_tenant_"
                        + str(tenant_id)
                    )
                    report_search = (
                        '| splunkremotesearch account="'
                        + str(account)
                        + '"'
                        + ' search="'
                        + "| mstats latest(_value) as value where "
                        + str(root_constraint.replace('"', '\\"'))
                        + " by metric_name, index, "
                        + str(trackme_mhm_host_meta)
                        + " span=1m"
                        + "| "
                        + str(search_string_aggreg)
                        + '" earliest="'
                        + str(earliest_time)
                        + '" '
                        + 'latest="'
                        + str(latest_time)
                        + '" register_component="True" tenant_id="'
                        + str(tenant_id)
                        + '" component="splk-mhm" report="'
                        + "trackme_mhm_hybrid_"
                        + str(tracker_name)
                        + "_wrapper"
                        + "_tenant_"
                        + str(tenant_id)
                        + '"\n'
                        + "``` call the abstract macro ```"
                        + "| `trackme_mhm_tracker_abstract("
                        + str(tenant_id)
                        + ', host, "*")`'
                    )

            # log debug
            logger.debug(
                f'tenant_id="{tenant_id}", hybrid tracker creation, report_search="{report_search}"'
            )

            # create the report, unless in burn test
            if not burn_test:
                # create a new report
                report_properties = {
                    "description": "TrackMe abstract hybrid root tracker",
                    "dispatch.earliest_time": str(earliest_time),
                    "dispatch.latest_time": str(latest_time),
                    "is_scheduled": False,
                }
                report_acl = {
                    "owner": owner,
                    "sharing": trackme_default_sharing,
                    "perms.write": vtenant_record.get("tenant_roles_admin"),
                    "perms.read": f"{vtenant_record.get('tenant_roles_user')},{vtenant_record.get('tenant_roles_power')}",
                }
                abstract_create_report = trackme_create_report(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    report_name,
                    report_search,
                    report_properties,
                    report_acl,
                )

                #
                # Splunkd API needs a couple of seconds to refresh while KOs are created
                #

                # set max failed re-attempt
                max_failures_count = 24
                sleep_time = 5
                creation_success = False
                current_failures_count = 0

                while (
                    current_failures_count < max_failures_count and not creation_success
                ):
                    try:
                        newtracker = service.saved_searches[report_name]
                        logger.info(
                            f'action="success", hybrid tracker was successfully created, report_name="{report_name}"'
                        )
                        creation_success = True
                        break

                    except Exception as e:
                        # We except this sentence in the exception if the API is not ready yet
                        logger.warning(
                            f'temporary failure, the report is not yet available, will sleep and re-attempt, report report_name="{report_name}"'
                        )
                        time.sleep(sleep_time)
                        current_failures_count += 1

                        if current_failures_count >= max_failures_count:
                            logger.error(
                                f'max attempt reached, failure to create report report_name="{report_name}" with exception="{str(e)}"'
                            )
                            break

                # sleep 2 sec as an additional safety
                time.sleep(2)

            #
            # burn test: execute the abstract report, delete and report the run time performance
            #

            if burn_test:
                logger.info(
                    f'tenant_id="{tenant_id}", burn test was requested, starting burn test search now'
                )

                # Define the query
                if search_mode == "raw" and tracker_type == "local":
                    burn_test_search = "search %s" % (report_search)
                else:
                    burn_test_search = report_search

                if not burn_test_runsearch:
                    # replacement of the macro root
                    burn_test_replace_string = "`%s`" % (root_constraint_macro)

                    # return
                    burn_test_results_record = {
                        "tenant_id": tenant_id,
                        "search": burn_test_search.replace(
                            burn_test_replace_string, root_constraint
                        ),
                        "root_constraint_macro": root_constraint.replace(
                            burn_test_replace_string, root_constraint
                        ),
                        "burn_test_success": True,
                        "earliest_time": earliest_time,
                        "latest_time": latest_time,
                    }

                    # remove macro
                    try:
                        action = trackme_delete_macro(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            root_constraint_macro,
                        )
                        logger.info(
                            f'tenant_id="{tenant_id}", burn test, macro="{root_constraint_macro}", action="success", the macro was successfully removed.'
                        )
                    except Exception as e:
                        logger.error(
                            f'tenant_id="{tenant_id}", burn test, macro="{root_constraint_macro}", failed to remove the macro, macro_name="{root_constraint_macro}", exception="{str(e)}"'
                        )

                    logger.info(
                        f'tenant_id="{tenant_id}", burn test, results="{json.dumps(burn_test_results_record, indent=2)}"'
                    )
                    return {"payload": burn_test_results_record, "status": 200}

                else:
                    # kwargs
                    burn_test_kwargs = {
                        "earliest_time": earliest_time,
                        "latest_time": latest_time,
                        "search_mode": "normal",
                        "preview": False,
                        "time_format": "%s",
                        "output_mode": "json",
                        "count": 0,
                    }

                    burn_test_start_time = time.time()

                    # results counter
                    burn_test_results_counter = 0

                    # run search
                    try:
                        reader = run_splunk_search(
                            service,
                            burn_test_search,
                            burn_test_kwargs,
                            24,
                            5,
                        )

                        for item in reader:
                            if isinstance(item, dict):
                                # increment
                                burn_test_results_counter += 1

                        # remove macro
                        try:
                            action = trackme_delete_macro(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                tenant_id,
                                root_constraint_macro,
                            )
                            logger.info(
                                f'tenant_id="{tenant_id}", burn test, macro="{root_constraint_macro}", action="success", the macro was successfully removed.'
                            )
                        except Exception as e:
                            logger.error(
                                f'tenant_id="{tenant_id}", burn test, macro="{root_constraint_macro}", failed to remove the macro, macro_name="{root_constraint_macro}", exception="{str(e)}"'
                            )

                        # return
                        burn_test_results_record = {
                            "tenant_id": tenant_id,
                            "run_time": round((time.time() - burn_test_start_time), 3),
                            "results_count": burn_test_results_counter,
                            "search": burn_test_search.replace("\n", " "),
                            "burn_test_success": True,
                            "earliest_time": earliest_time,
                            "latest_time": latest_time,
                        }

                        logger.info(
                            f'tenant_id="{tenant_id}", burn test, results="{json.dumps(burn_test_results_record, indent=2)}"'
                        )
                        return {"payload": burn_test_results_record, "status": 200}

                    except Exception as e:
                        # return
                        burn_test_results_record = {
                            "tenant_id": tenant_id,
                            "run_time": round((time.time() - burn_test_start_time), 3),
                            "results_count": burn_test_results_counter,
                            "search": burn_test_search.replace("\n", " "),
                            "burn_test_success": False,
                            "earliest_time": earliest_time,
                            "latest_time": latest_time,
                            "exception": f'search failed with exception="{str(e)}"',
                        }

                        # remove macro
                        try:
                            action = trackme_delete_macro(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                tenant_id,
                                root_constraint_macro,
                            )
                            logger.info(
                                f'tenant_id="{tenant_id}", burn test, macro="{root_constraint_macro}", action="success", the macro was successfully removed.'
                            )
                        except Exception as e:
                            logger.error(
                                f'tenant_id="{tenant_id}", burn test, macro="{root_constraint_macro}", failed to remove the macro, macro_name="{root_constraint_macro}", exception="{str(e)}"'
                            )

                        logger.error(json.dumps(burn_test_results_record, indent=2))
                        return {
                            "payload": burn_test_results_record,
                            "status": 200,
                        }

            #
            # step 4: create the wrapper
            #

            if component == "dsm":
                report_name = (
                    "trackme_dsm_hybrid_"
                    + str(tracker_name)
                    + "_wrapper"
                    + "_tenant_"
                    + str(tenant_id)
                )
                report_search = (
                    '| savedsearch "'
                    + "trackme_dsm_hybrid_abstract_"
                    + str(tracker_name)
                    + "_tenant_"
                    + str(tenant_id)
                    + '"\n'
                    + "\n``` collects latest collection state into the summary index ```"
                    + '\n| `trackme_collect_state("current_state_tracking:splk-dsm:'
                    + str(tenant_id)
                    + '", "object", "'
                    + str(tenant_id)
                    + '")`\n'
                    + "\n``` output flipping change status if changes ```"
                    + '\n| trackmesplkgetflipping tenant_id="'
                    + str(tenant_id)
                    + '" object_category="splk-dsm"'
                    + "\n```Generate splk outliers rules```"
                    + "\n| `set_splk_outliers_rules("
                    + str(tenant_id)
                    + ", "
                    + "dsm"
                    + ")`"
                    + "\n| `trackme_outputlookup(trackme_dsm_tenant_"
                    + str(tenant_id)
                    + ", key)`"
                    + '\n| where splk_dsm_is_online="true"'
                    + '\n| `trackme_mcollect(object, splk-dsm, "metric_name:trackme.splk.feeds.avg_eventcount_5m=avg_eventcount_5m, '
                    + "metric_name:trackme.splk.feeds.latest_eventcount_5m=latest_eventcount_5m, metric_name:trackme.splk.feeds.perc95_eventcount_5m=perc95_eventcount_5m, "
                    + "metric_name:trackme.splk.feeds.stdev_eventcount_5m=stdev_eventcount_5m, metric_name:trackme.splk.feeds.avg_latency_5m=avg_latency_5m, "
                    + "metric_name:trackme.splk.feeds.latest_latency_5m=latest_latency_5m, metric_name:trackme.splk.feeds.perc95_latency_5m=perc95_latency_5m, "
                    + "metric_name:trackme.splk.feeds.avg_dcount_host_5m=avg_dcount_host_5m, metric_name:trackme.splk.feeds.latest_dcount_host_5m=latest_dcount_host_5m, "
                    + "metric_name:trackme.splk.feeds.perc95_dcount_host_5m=perc95_dcount_host_5m, metric_name:trackme.splk.feeds.stdev_dcount_host_5m=stdev_dcount_host_5m, "
                    + "metric_name:trackme.splk.feeds.global_dcount_host=global_dcount_host, "
                    + "metric_name:trackme.splk.feeds.stdev_latency_5m=stdev_latency_5m, metric_name:trackme.splk.feeds.eventcount_4h=data_eventcount, "
                    + "metric_name:trackme.splk.feeds.hostcount_4h=dcount_host, metric_name:trackme.splk.feeds.lag_event_sec=data_last_lag_seen, "
                    + 'metric_name:trackme.splk.feeds.lag_ingestion_sec=data_last_ingestion_lag_seen", "tenant_id, object_category, object", "'
                    + str(tenant_id)
                    + '")`'
                    + "\n| stats count as report_entities_count, values(object) as report_objects_list by tenant_id"
                    + "\n| `register_tenant_component_summary("
                    + str(tenant_id)
                    + ", dsm)`"
                )

            elif component == "dhm":
                report_name = (
                    "trackme_dhm_hybrid_"
                    + str(tracker_name)
                    + "_wrapper"
                    + "_tenant_"
                    + str(tenant_id)
                )
                report_search = (
                    '| savedsearch "'
                    + "trackme_dhm_hybrid_abstract_"
                    + str(tracker_name)
                    + "_tenant_"
                    + str(tenant_id)
                    + '"'
                    + "\n``` collects latest collection state into the summary index ```"
                    + '\n| `trackme_collect_state("current_state_tracking:splk-dhm:'
                    + str(tenant_id)
                    + '", "object", "'
                    + str(tenant_id)
                    + '")`'
                    + "\n``` output flipping change status if changes ```"
                    '\n| trackmesplkgetflipping tenant_id="'
                    + str(tenant_id)
                    + '" object_category="splk-dhm"'
                    + "\n```Generate splk outliers rules```"
                    + "\n| `set_splk_outliers_rules("
                    + str(tenant_id)
                    + ", dhm)`"
                    + "\n| `trackme_outputlookup_preloaded(trackme_dhm_tenant_"
                    + str(tenant_id)
                    + ", key, "
                    + str(tenant_id)
                    + ")`"
                    + '\n| where splk_dhm_is_online="true"'
                    + '\n| `trackme_mcollect(object, splk-dhm, "metric_name:trackme.splk.feeds.avg_eventcount_5m=avg_eventcount_5m, '
                    + "metric_name:trackme.splk.feeds.latest_eventcount_5m=latest_eventcount_5m, metric_name:trackme.splk.feeds.perc95_eventcount_5m=perc95_eventcount_5m, "
                    + "metric_name:trackme.splk.feeds.stdev_eventcount_5m=stdev_eventcount_5m, metric_name:trackme.splk.feeds.avg_latency_5m=avg_latency_5m, "
                    + "metric_name:trackme.splk.feeds.latest_latency_5m=latest_latency_5m, metric_name:trackme.splk.feeds.perc95_latency_5m=perc95_latency_5m, "
                    + "metric_name:trackme.splk.feeds.stdev_latency_5m=stdev_latency_5m, metric_name:trackme.splk.feeds.eventcount_4h=data_eventcount, "
                    + 'metric_name:trackme.splk.feeds.lag_event_sec=data_last_lag_seen, metric_name:trackme.splk.feeds.lag_ingestion_sec=data_last_ingestion_lag_seen", "tenant_id, object_category, object", "'
                    + str(tenant_id)
                    + '")`'
                    + "\n| stats count as report_entities_count, values(object) as report_objects_list by tenant_id"
                    + "\n| `register_tenant_component_summary("
                    + str(tenant_id)
                    + ', dhm, "data_index,data_sourcetype")`'
                )

            elif component == "mhm":
                report_name = (
                    "trackme_mhm_hybrid_"
                    + str(tracker_name)
                    + "_wrapper"
                    + "_tenant_"
                    + str(tenant_id)
                )
                report_search = (
                    '| savedsearch "'
                    + "trackme_mhm_hybrid_abstract_"
                    + str(tracker_name)
                    + "_tenant_"
                    + str(tenant_id)
                    + '"\n'
                    + "\n``` collects latest collection state into the summary index ```"
                    + '\n| `trackme_collect_state("current_state_tracking:splk-mhm:'
                    + str(tenant_id)
                    + '", "object", "'
                    + str(tenant_id)
                    + '")`'
                    + "\n``` output flipping change status if changes ```"
                    + '\n| trackmesplkgetflipping tenant_id="'
                    + str(tenant_id)
                    + '" object_category="splk-mhm"'
                    + "\n| search NOT [ | inputlookup trackme_common_audit_changes_tenant_"
                    + str(tenant_id)
                    + ' | where action="success" AND '
                    + '\nchange_type="delete permanent" AND object_category="object" | eval _time=time/1000 | where _time>relative_time(now(), "-7d")'
                    + "\n| table object | dedup object | sort limit=0 object | rename object as object ]"
                    + '\n| eval tenant_id="'
                    + str(tenant_id)
                    + '"'
                    + "\n| `trackme_outputlookup(trackme_mhm_tenant_"
                    + str(tenant_id)
                    + ", key, "
                    + str(tenant_id)
                    + ")`"
                    + "\n| stats count as report_entities_count, values(object) as report_objects_list by tenant_id"
                    + "\n| `register_tenant_component_summary("
                    + str(tenant_id)
                    + ', mhm, "metric_index,metric_category")`'
                )

            # create a new report
            report_properties = {
                "description": "TrackMe hybrid wrapper",
                "dispatch.earliest_time": str(earliest_time),
                "dispatch.latest_time": str(latest_time),
                "is_scheduled": False,
            }
            report_acl = {
                "owner": owner,
                "sharing": trackme_default_sharing,
                "perms.write": vtenant_record.get("tenant_roles_admin"),
                "perms.read": f"{vtenant_record.get('tenant_roles_user')},{vtenant_record.get('tenant_roles_power')}",
            }
            wrapper_create_report = trackme_create_report(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                report_name,
                report_search,
                report_properties,
                report_acl,
            )

            #
            # Splunkd API needs a couple of seconds to refresh while KOs are created
            #

            # set max failed re-attempt
            max_failures_count = 24
            sleep_time = 5
            creation_success = False
            current_failures_count = 0

            while current_failures_count < max_failures_count and not creation_success:
                try:
                    newtracker = service.saved_searches[report_name]
                    logger.info(
                        f'action="success", hybrid tracker was successfully created, report_name="{report_name}"'
                    )
                    creation_success = True
                    break

                except Exception as e:
                    # We except this sentence in the exception if the API is not ready yet
                    logger.warning(
                        f'temporary failure, the report is not yet available, will sleep and re-attempt, report report_name="{report_name}"'
                    )
                    time.sleep(sleep_time)
                    current_failures_count += 1

                    if current_failures_count >= max_failures_count:
                        logger.error(
                            f'max attempt reached, failure to create report report_name="{report_name}" with exception="{str(e)}"'
                        )
                        break

            # sleep 2 sec as an additional safety
            time.sleep(2)

            #
            # step 5: create the tracker
            #

            report_name = (
                "trackme_"
                + str(component)
                + "_hybrid_"
                + str(tracker_name)
                + "_tracker"
                + "_tenant_"
                + str(tenant_id)
            )
            report_search = (
                '| trackmetrackerexecutor tenant_id="'
                + str(tenant_id)
                + '" component="splk-'
                + str(component)
                + '" report="'
                + "trackme_"
                + str(component)
                + "_hybrid_"
                + str(tracker_name)
                + "_wrapper"
                + "_tenant_"
                + str(tenant_id)
                + '"'
                + " alert_no_results=True"
            )

            # create a new report
            report_properties = {
                "description": "TrackMe hybrid tracker",
                "is_scheduled": True,
                "schedule_window": "5",
                "cron_schedule": cron_schedule,
                "dispatch.earliest_time": str(earliest_time),
                "dispatch.latest_time": str(latest_time),
            }
            report_acl = {
                "owner": owner,
                "sharing": trackme_default_sharing,
                "perms.write": vtenant_record.get("tenant_roles_admin"),
                "perms.read": f"{vtenant_record.get('tenant_roles_user')},{vtenant_record.get('tenant_roles_power')}",
            }
            tracker_create_report = trackme_create_report(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                report_name,
                report_search,
                report_properties,
                report_acl,
            )

            #
            # Splunkd API needs a couple of seconds to refresh while KOs are created
            #

            # set max failed re-attempt
            max_failures_count = 24
            sleep_time = 5
            creation_success = False
            current_failures_count = 0

            while current_failures_count < max_failures_count and not creation_success:
                try:
                    newtracker = service.saved_searches[report_name]
                    logger.info(
                        f'action="success", hybrid tracker was successfully created, report_name="{report_name}"'
                    )
                    creation_success = True
                    break

                except Exception as e:
                    # We except this sentence in the exception if the API is not ready yet
                    logger.warning(
                        f'temporary failure, the report is not yet available, will sleep and re-attempt, report report_name="{report_name}"'
                    )
                    time.sleep(sleep_time)
                    current_failures_count += 1

                    if current_failures_count >= max_failures_count:
                        logger.error(
                            f'max attempt reached, failure to create report report_name="{report_name}" with exception="{str(e)}"'
                        )
                        break

            # sleep 2 sec as an additional safety
            time.sleep(2)

        #
        # END
        #

        # re-transform as a string
        if not breakby_field:
            breakby_field = "none"

        audit_record = {
            "account": str(account),
            "abstract_report": abstract_create_report.get("report_name"),
            "wrapper_report": wrapper_create_report.get("report_name"),
            "tracker_report": tracker_create_report.get("report_name"),
            "root_constraint_macro": str(root_constraint_macro),
            "root_constraint": str(root_constraint),
            "tracker_name": str(tracker_name),
            "breakby_field": str(breakby_field),
            "search_mode": str(search_mode),
            "earliest": str(earliest_time),
            "latest": str(latest_time),
            "cron_schedule": tracker_create_report.get("cron_schedule"),
            "action": "success",
        }

        # this applies to dsm|dhm only
        if component in ("dsm", "dhm"):
            audit_record["index_earliest"] = str(index_earliest_time)
            audit_record["index_latest"] = str(index_latest_time)

        # extras (splk-dhm only) — record on the audit trail when non-empty so
        # the tracker creation entry self-describes the configured grain.
        if component == "dhm" and breakby_extra_fields:
            audit_record["breakby_extra_fields"] = list(breakby_extra_fields)

        # Register the new components in the vtenant collection
        collection_vtenants_name = "kv_trackme_virtual_tenants"
        collection_vtenants = service.kvstore[collection_vtenants_name]

        # Define the KV query search string
        query_string = {
            "tenant_id": tenant_id,
        }

        # Get the tenant
        try:
            vtenant_record = collection_vtenants.data.query(
                query=json.dumps(query_string)
            )[0]
            vtenant_key = vtenant_record.get("_key")

        except Exception as e:
            vtenant_key = None

        # We can only proceed with a valid tenant record
        if vtenant_key:
            # Try to get the current definition
            try:
                if component == "dsm":
                    tenant_hybrid_objects = vtenant_record.get(
                        "tenant_dsm_hybrid_objects"
                    )
                elif component == "dhm":
                    tenant_hybrid_objects = vtenant_record.get(
                        "tenant_dhm_hybrid_objects"
                    )
                elif component == "mhm":
                    tenant_hybrid_objects = vtenant_record.get(
                        "tenant_mhm_hybrid_objects"
                    )

                # logger.debug
                logger.debug(f'tenant_hybrid_objects="{tenant_hybrid_objects}"')
            except Exception as e:
                tenant_hybrid_objects = None

            # add to existing dict
            if tenant_hybrid_objects and tenant_hybrid_objects != "None":
                vtenant_dict = json.loads(tenant_hybrid_objects)
                logger.info(f'vtenant_dict="{json.dumps(vtenant_dict, indent=1)}"')

                report1 = abstract_create_report.get("report_name")
                report2 = wrapper_create_report.get("report_name")
                report3 = tracker_create_report.get("report_name")
                macro1 = str(root_constraint_macro)

                try:
                    reports = vtenant_dict["reports"]
                except Exception as e:
                    reports = []

                try:
                    macros = vtenant_dict["macros"]
                except Exception as e:
                    macros = []

                reports.append(str(report1))
                reports.append(str(report2))
                reports.append(str(report3))
                macros.append(str(macro1))

                vtenant_dict = dict(
                    [
                        ("reports", reports),
                        ("macros", macros),
                    ]
                )

            # empty dict
            else:
                report1 = abstract_create_report.get("report_name")
                report2 = wrapper_create_report.get("report_name")
                report3 = tracker_create_report.get("report_name")
                macro1 = str(root_constraint_macro)

                reports = []
                reports.append(str(report1))
                reports.append(str(report2))
                reports.append(str(report3))

                macros = []
                macros.append(macro1)

                vtenant_dict = dict(
                    [
                        ("reports", reports),
                        ("macros", macros),
                    ]
                )

            try:
                if component == "dsm":
                    vtenant_record["tenant_dsm_hybrid_objects"] = json.dumps(
                        vtenant_dict, indent=1
                    )
                    collection_vtenants.data.update(
                        str(vtenant_key), json.dumps(vtenant_record)
                    )

                elif component == "dhm":
                    vtenant_record["tenant_dhm_hybrid_objects"] = json.dumps(
                        vtenant_dict, indent=1
                    )
                    collection_vtenants.data.update(
                        str(vtenant_key), json.dumps(vtenant_record)
                    )

                elif component == "mhm":
                    vtenant_record["tenant_mhm_hybrid_objects"] = json.dumps(
                        vtenant_dict, indent=1
                    )
                    collection_vtenants.data.update(
                        str(vtenant_key), json.dumps(vtenant_record)
                    )

            except Exception as e:
                logger.error(
                    f'failure while trying to update the vtenant KVstore record, exception="{str(e)}"'
                )
                return {
                    "payload": "Warn: exception encountered: "
                    + str(e)  # Payload of the request.
                }

            # Record the new hybrid component in the hybrid collection
            collection_hybrid_name = (
                "kv_trackme_"
                + str(component)
                + "_hybrid_trackers_tenant_"
                + str(tenant_id)
            )
            collection_hybrid = service.kvstore[collection_hybrid_name]

            reports = []
            reports.append(str(report1))
            reports.append(str(report2))
            reports.append(str(report3))

            macros = []
            macros.append(str(macro1))

            properties = []
            properties_dict = {
                "root_constraint_macro": str(root_constraint_macro),
                "root_constraint": str(root_constraint),
                "tracker_name": str(tracker_name),
                "breakby_field": str(breakby_field),
                "search_mode": str(search_mode),
                "earliest": str(earliest_time),
                "latest": str(latest_time),
                "cron_schedule": tracker_create_report.get("cron_schedule"),
            }

            # this only applied to dsm|dhm
            if component in ("dsm", "dhm"):
                properties_dict["index_earliest"] = index_earliest_time
                properties_dict["index_latest"] = index_latest_time

            # extras (splk-dhm only) — persist alongside breakby_field so
            # GET handlers and tracker-edit flows can surface them. Omitted
            # when empty to keep the registry entry byte-identical for
            # trackers that don't opt in.
            if component == "dhm" and breakby_extra_fields:
                properties_dict["breakby_extra_fields"] = list(breakby_extra_fields)

            properties.append(properties_dict)

            hybrid_dict = dict(
                [
                    ("reports", reports),
                    ("macros", macros),
                    ("properties", properties),
                ]
            )

            try:
                collection_hybrid.data.insert(
                    json.dumps(
                        {
                            "_key": hashlib.sha256(
                                tracker_name.encode("utf-8")
                            ).hexdigest(),
                            "tracker_name": tracker_name,
                            "knowledge_objects": json.dumps(hybrid_dict, indent=1),
                        }
                    )
                )
            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", failure while trying to insert the hybrid KVstore record, exception="{str(e)}"'
                )

        # Record an audit change
        try:
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user,
                "success",
                "add hybrid tracker",
                "trackme_" + str(component) + "_hybrid_" + str(tracker_name),
                "hybrid_tracker",
                str(audit_record),
                "The hybrid tracker was created successfully",
                str(update_comment),
            )
        except Exception as e:
            logger.error(f'failed to generate an audit event with exception="{str(e)}"')

        # final return
        logger.info(json.dumps(audit_record, indent=2))
        return {"payload": audit_record, "status": 200}

    # Remove an hybrid tracker and associated objects
    def post_hybrid_tracker_delete(self, request_info, **kwargs):
        """
        | trackme mode=post url="/services/trackme/v2/splk_hybrid_trackers/admin/hybrid_tracker_delete" body="{'tenant_id': 'mytenant', 'component': 'dsm', 'hybrid_trackers_list': 'test:001,test:002'}"
        """

        # By tracker_name
        tenant_id = None
        component = None
        hybrid_trackers_list = None
        query_string = None

        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]
                hybrid_trackers_list = resp_dict["hybrid_trackers_list"]
                # Handle as a CSV list of keys, it not already a list
                if not isinstance(hybrid_trackers_list, list):
                    hybrid_trackers_list = [x.strip() for x in hybrid_trackers_list.split(",") if x.strip()]
                else:
                    # Filter out empty strings from existing list
                    hybrid_trackers_list = [x.strip() if isinstance(x, str) else x for x in hybrid_trackers_list if (x.strip() if isinstance(x, str) else bool(x))]
                # get component
                component = resp_dict["component"]
                if not component in ("dsm", "dhm", "mhm"):
                    return {
                        "payload": {
                            "response": f'Invalid component="{component}", valid options are: dsm|dhm|mhm'
                        },
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint performs the deletion of an hybrid tracker and associated objects, it requires a POST call with the following information:",
                "resource_desc": "Delete an hybrid tracker and associated objects",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_hybrid_trackers/admin/hybrid_tracker_delete\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'hybrid_trackers_list': 'test:001,test:002'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component, valid options are: dsm | dhm | mhm",
                        "hybrid_trackers_list": "comma separated list of hybrid entities to be deleted, for each submitted entity, all related objects will be purged",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # records summary
        records = []

        # Loop through the list of entities to be handled
        for hybrid_tracker in hybrid_trackers_list:
            # this operation will be considered to be successful only no failures were encountered
            # any failure encountered will be added to the record summary for that entity
            sub_failures_count = 0

            # Define the KV query
            query_string = {
                "tracker_name": hybrid_tracker,
            }

            # Get splunkd port
            splunkd_port = request_info.server_rest_port

            # Get service
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=splunkd_port,
                token=request_info.system_authtoken,
                timeout=600,
            )

            # set loglevel
            loglevel = trackme_getloglevel(
                request_info.system_authtoken, request_info.server_rest_port
            )
            logger.setLevel(loglevel)

            # get TrackMe conf
            trackme_conf = trackme_reqinfo(
                request_info.system_authtoken, request_info.server_rest_uri
            )
            logger.debug(f'trackme_conf="{json.dumps(trackme_conf, indent=2)}"')

            try:
                # Data collection
                collection_name = (
                    "kv_trackme_"
                    + str(component)
                    + "_hybrid_trackers_tenant_"
                    + str(tenant_id)
                )
                collection = service.kvstore[collection_name]

                # Get the current record
                # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

                try:
                    hybrid_record = collection.data.query(
                        query=json.dumps(query_string)
                    )
                    key = hybrid_record[0].get("_key")

                except Exception as e:
                    key = None

                # Render result
                if key:
                    # check if TCM is enabled in receiver mode
                    enable_conf_manager_receiver = int(
                        trackme_conf["trackme_conf"]["trackme_general"][
                            "enable_conf_manager_receiver"
                        ]
                    )

                    if enable_conf_manager_receiver == 1:
                        try:
                            tcm_response = trackme_send_to_tcm(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                resp_dict,
                                "post",
                                "/services/trackme/v2/splk_hybrid_trackers/admin/hybrid_tracker_delete",
                            )
                            logger.info(
                                f"trackme_send_to_tcm was successfully executed"
                            )
                        except Exception as e:
                            logger.error(
                                f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                            )

                    # load the knowledge object dict
                    tenant_hybrid_objects = json.loads(
                        hybrid_record[0].get("knowledge_objects")
                    )
                    logger.debug(
                        f'tenant_hybrid_objects="{json.dumps(tenant_hybrid_objects, indent=1)}"'
                    )

                    # Step 1: delete knowledge objects
                    try:
                        reports_list = tenant_hybrid_objects["reports"]
                    except Exception as e:
                        reports_list = []
                    logger.debug(f'reports_list="{reports_list}"')

                    try:
                        macros_list = tenant_hybrid_objects["macros"]
                    except Exception as e:
                        macros_list = []
                    logger.debug(f'macros_list="{macros_list}"')

                    # Delete all reports
                    for report_name in reports_list:
                        logger.info(
                            f'tenant_id="{tenant_id}", attempting removal of report="{report_name}"'
                        )
                        try:
                            service.saved_searches.delete(str(report_name))
                            logger.info(
                                f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", action="success", the report was successfully removed, report_name="{report_name}"'
                            )
                        except Exception as e:
                            logger.error(
                                f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", failed to remove the report, report_name="{report_name}", exception="{str(e)}"'
                            )

                            sub_failures_count += 1
                            result = {
                                "hybrid_tracker": hybrid_tracker,
                                "action": "delete",
                                "result": "failure",
                                "exception": f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", failed to remove the report, report_name="{report_name}", exception="{str(e)}"',
                            }
                            records.append(result)

                    # Delete all macros
                    for macro_name in macros_list:
                        logger.info(
                            f'tenant_id="{tenant_id}", attempting removal of macro="{macro_name}"'
                        )
                        try:
                            action = trackme_delete_macro(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                tenant_id,
                                macro_name,
                            )
                            logger.info(
                                f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", action="success", the macro was successfully removed, macro_name="{macro_name}"'
                            )
                        except Exception as e:
                            logger.error(
                                f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", failed to remove the macro, macro_name="{macro_name}", exception="{str(e)}"'
                            )

                            sub_failures_count += 1
                            result = {
                                "hybrid_tracker": hybrid_tracker,
                                "action": "delete",
                                "result": "failure",
                                "exception": f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", failed to remove the macro, macro_name="{macro_name}", exception="{str(e)}"',
                            }
                            records.append(result)

                    # Step 2: delete the KVstore record

                    # Remove the record
                    try:
                        collection.data.delete(json.dumps({"_key": key}))

                    except Exception as e:
                        logger.error(
                            f'tenant_id="{tenant_id}", tracker_name="{hybrid_tracker}", exception encountered while attempting to delete the KVstore record, exception="{str(e)}"'
                        )
                        sub_failures_count += 1
                        result = {
                            "tracker_name": hybrid_tracker,
                            "action": "delete",
                            "result": "failure",
                            "exception": f'tenant_id="{tenant_id}", tracker_name="{hybrid_tracker}", exception encountered while attempting to delete the KVstore record, exception="{str(e)}"',
                        }
                        records.append(result)

                    # Step 2.5: Cleanup sourcetype cap alerts for this tracker's collection
                    if component == "dsm":
                        try:
                            cap_collection_name = f"trackme_{component}_tenant_{tenant_id}"
                            cap_alert_collection = service.kvstore["kv_trackme_sourcetype_cap_alerts"]
                            cap_alert_records = cap_alert_collection.data.query()
                            for cap_alert in cap_alert_records:
                                if (
                                    cap_alert.get("tenant_id") == str(tenant_id)
                                    and cap_alert.get("collection_name") == cap_collection_name
                                ):
                                    try:
                                        cap_alert_collection.data.delete(json.dumps({"_key": cap_alert.get("_key")}))
                                        logger.info(
                                            f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", '
                                            f'deleted sourcetype cap alert for index="{cap_alert.get("data_index")}"'
                                        )
                                    except Exception:
                                        pass
                        except Exception as e:
                            logger.warning(
                                f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", '
                                f'failed to cleanup sourcetype cap alerts: {e}'
                            )

                    # Step 3: delete the hybrid knowledge from the tenant

                    # Register the new components in the vtenant collection
                    collection_vtenants_name = "kv_trackme_virtual_tenants"
                    collection_vtenants = service.kvstore[collection_vtenants_name]

                    # Define the KV query search string
                    query_string = {
                        "tenant_id": tenant_id,
                    }

                    # Get the tenant
                    try:
                        vtenant_record = collection_vtenants.data.query(
                            query=json.dumps(query_string)
                        )[0]
                        vtenant_key = vtenant_record.get("_key")

                    except Exception as e:
                        vtenant_key = None

                    # We can only proceed with a valid tenant record
                    if vtenant_key:
                        # Try to get the current definition
                        try:
                            tenant_hybrid_objects = vtenant_record.get(
                                "tenant_" + str(component) + "_hybrid_objects"
                            )
                            # logger.debug
                            logger.debug(
                                f'tenant_hybrid_objects="{tenant_hybrid_objects}"'
                            )
                        except Exception as e:
                            tenant_hybrid_objects = None

                        # remove from the dict
                        if tenant_hybrid_objects and tenant_hybrid_objects != "None":
                            vtenant_dict = json.loads(tenant_hybrid_objects)
                            logger.debug(
                                f'vtenant_dict="{json.dumps(vtenant_dict, indent=1)}"'
                            )

                            report1 = (
                                "trackme_"
                                + str(component)
                                + "_hybrid_abstract_"
                                + str(hybrid_tracker)
                                + "_tenant_"
                                + str(tenant_id)
                            )
                            report2 = (
                                "trackme_"
                                + str(component)
                                + "_hybrid_"
                                + str(hybrid_tracker)
                                + "_wrapper"
                                + "_tenant_"
                                + str(tenant_id)
                            )
                            report3 = (
                                "trackme_"
                                + str(component)
                                + "_hybrid_"
                                + str(hybrid_tracker)
                                + "_tracker"
                                + "_tenant_"
                                + str(tenant_id)
                            )

                            reports = vtenant_dict["reports"]
                            for report_to_remove in [str(report1), str(report2), str(report3)]:
                                try:
                                    reports.remove(report_to_remove)
                                except ValueError:
                                    logger.warning(
                                        f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", report="{report_to_remove}" not found in tenant_{component}_hybrid_objects, skipping removal'
                                    )

                            # macros were added in a later version
                            macro1 = (
                                "trackme_%s_hybrid_root_constraint_%s_tenant_%s"
                                % (component, hybrid_tracker, tenant_id)
                            )

                            try:
                                macros = vtenant_dict["macros"]
                                try:
                                    macros.remove(str(macro1))
                                except ValueError:
                                    logger.warning(
                                        f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", macro="{macro1}" not found in tenant_{component}_hybrid_objects, skipping removal'
                                    )

                            except Exception as e:
                                macros = []

                            vtenant_dict = dict(
                                [
                                    ("reports", reports),
                                    ("macros", macros),
                                ]
                            )

                            # Update the KVstore
                            try:
                                if component == "dsm":
                                    vtenant_record["tenant_dsm_hybrid_objects"] = (
                                        json.dumps(vtenant_dict, indent=2)
                                    )
                                    collection_vtenants.data.update(
                                        str(vtenant_key), json.dumps(vtenant_record)
                                    )

                                elif component == "dhm":
                                    vtenant_record["tenant_dhm_hybrid_objects"] = (
                                        json.dumps(vtenant_dict, indent=2)
                                    )
                                    collection_vtenants.data.update(
                                        str(vtenant_key), json.dumps(vtenant_record)
                                    )

                                elif component == "mhm":
                                    vtenant_record["tenant_mhm_hybrid_objects"] = (
                                        json.dumps(vtenant_dict, indent=2)
                                    )
                                    collection_vtenants.data.update(
                                        str(vtenant_key), json.dumps(vtenant_record)
                                    )

                            except Exception as e:
                                logger.error(
                                    f'failure while trying to update the vtenant KVstore record, exception="{str(e)}"'
                                )
                                return {
                                    "payload": "Warn: exception encountered: "
                                    + str(e)  # Payload of the request.
                                }

                    # Step 4: purge the register summary object
                    try:
                        delete_register_summary = trackme_delete_tenant_object_summary(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            "splk-" + str(component),
                            "trackme_"
                            + str(component)
                            + "_hybrid_"
                            + str(hybrid_tracker)
                            + "_wrapper"
                            + "_tenant_"
                            + str(tenant_id),
                        )
                    except Exception as e:
                        logger.error(
                            f'exception encountered while calling function trackme_delete_tenant_object_summary, exception="{str(e)}"'
                        )

                    # Record an audit change
                    try:
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "success",
                            "remove hybrid tracker",
                            str(hybrid_tracker),
                            "hybrid_tracker",
                            str(json.dumps(hybrid_record, indent=2)),
                            "The Hybrid tracker and its associated objects were successfully deleted",
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                    logger.info(
                        f'tenant_id="{tenant_id}", tracker_name="{hybrid_tracker}", The hybrid tracker and its associated objects were successfully deleted'
                    )

                    # Handle the sub operation results
                    if sub_failures_count == 0:
                        # increment counter
                        processed_count += 1
                        succcess_count += 1
                        failures_count += 0

                        # append for summary
                        result = {
                            "tracker_name": hybrid_tracker,
                            "action": "delete",
                            "result": "success",
                            "message": f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", The hybrid tracker and its associated objects were successfully deleted',
                        }
                        records.append(result)

                else:
                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    logger.error(
                        f'tenant_id="{tenant_id}", tracker_name="{hybrid_tracker}", the resource was not found or the request is incorrect'
                    )

                    # append for summary
                    result = {
                        "tracker_name": hybrid_tracker,
                        "action": "delete",
                        "result": "failure",
                        "exception": "HTTP 404 NOT FOUND",
                    }
                    records.append(result)

            # raise any exception
            except Exception as e:
                # increment counter
                processed_count += 1
                succcess_count += 0
                failures_count += 1

                logger.error(
                    f'tenant_id="{tenant_id}", exception encountered, exception="{str(e)}"'
                )

                # append for summary
                result = {
                    "tracker_name": hybrid_tracker,
                    "action": "delete",
                    "result": "failure",
                    "exception": str(e),
                }

                records.append(result)

        # render HTTP status and summary

        req_summary = {
            "process_count": processed_count,
            "success_count": succcess_count,
            "failures_count": failures_count,
            "records": records,
        }

        if processed_count > 0 and processed_count == succcess_count:
            return {"payload": req_summary, "status": 200}

        else:
            return {"payload": req_summary, "status": 500}
