#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_variable_delay.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import os, sys
import json
import time

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_variable_delay_user",
    "trackme_rest_api_splk_variable_delay_user.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    run_splunk_search,
    trackme_getloglevel,
    trackme_idx_for_tenant,
    trackme_parse_describe_flag,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# import Splunk libs
import splunklib.client as client

# import shared pure helpers (#1717: moved out of the
# trackmesplkvariabledelay custom command so that importing them no
# longer drags that command's module-load code — which rebinds the root
# logger to trackme_variable_delay.log — into the caller's process. The
# Health Tracker's API-catalog warmup imports every REST handler at
# top level, so an `import trackmesplkvariabledelay` here would route
# every subsequent schema-upgrade log line into the wrong log file).
from trackme_libs_variable_delay import (
    aggregate_slots,
    compute_threshold,
    recompute_existing_slot_thresholds,
)


class TrackMeHandlerSplkVariableDelayRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkVariableDelayRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_variable_delay(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_variable_delay",
            "resource_group_desc": "Endpoints for managing variable delay threshold configurations. Variable delay allows time-aware delay thresholds that change based on day-of-week and hour-of-day, providing tighter monitoring during active periods and relaxed thresholds during known quiet periods.",
        }

        return {"payload": response, "status": 200}

    # Get variable delay config for an entity
    def post_get(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_variable_delay/get" mode="post" body="{'tenant_id': 'mytenant', 'component': 'dsm', 'object': 'myobject'}"
        """

        # init
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
                component = resp_dict["component"]
                object_id = resp_dict.get("object_id")
                object_value = resp_dict.get("object")
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves the variable delay configuration for an entity, it requires a POST call with the following information:",
                "resource_desc": "Get variable delay threshold configuration for an entity",
                "resource_spl_example": '| trackme url="/services/trackme/v2/splk_variable_delay/get" mode="post" body=\'{"tenant_id": "mytenant", "component": "dsm", "object": "myobject"}\'',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "MANDATORY, component type: dsm or dhm",
                        "object": "CONDITIONAL, the entity name (either object or object_id is required)",
                        "object_id": "CONDITIONAL, the entity KVstore key (preferred over object for robustness)",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # set log level
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Splunk SDK service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.session_key,
            timeout=600,
        )

        # validate component
        if component not in ("dsm", "dhm", "splk-dsm", "splk-dhm"):
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Invalid component "{component}", must be "dsm", "dhm", "splk-dsm", or "splk-dhm"',
                },
                "status": 400,
            }

        # normalize component
        comp = component.replace("splk-", "")

        # validate that at least one entity identifier is provided
        if not object_id and not object_value:
            return {
                "payload": {
                    "action": "failure",
                    "response": "Either object_id or object is required",
                },
                "status": 400,
            }

        # get entity _key from main collection first
        main_collection_name = f"kv_trackme_{comp}_tenant_{tenant_id}"
        try:
            main_collection = service.kvstore[main_collection_name]
            if object_id:
                main_query = {"_key": object_id}
            else:
                main_query = {"object": object_value}
            main_records = main_collection.data.query(
                query=json.dumps(main_query)
            )
            if not main_records or len(main_records) == 0:
                identifier = object_id or object_value
                return {
                    "payload": {
                        "action": "success",
                        "response": f"Entity '{identifier}' not found. Entity uses static delay threshold.",
                        "variable_delay_enabled": "false",
                    },
                    "status": 200,
                }
            main_record = main_records[0]
            entity_key = main_record.get("_key")
            if not object_value:
                object_value = main_record.get("object", "")
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"Failed to lookup entity in main collection: {str(e)}",
                },
                "status": 500,
            }

        # get variable delay collection
        collection_name = f"kv_trackme_{comp}_variable_delay_tenant_{tenant_id}"
        try:
            collection = service.kvstore[collection_name]
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"Variable delay collection not found: {collection_name}",
                    "exception": str(e),
                },
                "status": 404,
            }

        # query for the entity by _key
        try:
            records = collection.data.query(query=json.dumps({"_key": entity_key}))
            if records and len(records) > 0:
                record = records[0]
                return {"payload": record, "status": 200}
            else:
                return {
                    "payload": {
                        "action": "success",
                        "response": f"No variable delay configuration found for entity {object_value}. Entity uses static delay threshold.",
                        "variable_delay_enabled": "false",
                    },
                    "status": 200,
                }
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"Error querying variable delay collection",
                    "exception": str(e),
                },
                "status": 500,
            }

    # Get all variable delay configs for a tenant/component
    def post_get_all(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_variable_delay/get_all" mode="post" body="{'tenant_id': 'mytenant', 'component': 'dsm'}"
        """

        # init
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
                component = resp_dict["component"]
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves all variable delay configurations for a tenant and component, it requires a POST call with the following information:",
                "resource_desc": "Get all variable delay threshold configurations for a tenant/component",
                "resource_spl_example": '| trackme url="/services/trackme/v2/splk_variable_delay/get_all" mode="post" body=\'{"tenant_id": "mytenant", "component": "dsm"}\'',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "MANDATORY, component type: dsm or dhm",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # set log level
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Splunk SDK service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.session_key,
            timeout=600,
        )

        # validate component
        if component not in ("dsm", "dhm", "splk-dsm", "splk-dhm"):
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Invalid component "{component}", must be "dsm", "dhm", "splk-dsm", or "splk-dhm"',
                },
                "status": 400,
            }

        # normalize component
        comp = component.replace("splk-", "")

        # get variable delay collection
        collection_name = f"kv_trackme_{comp}_variable_delay_tenant_{tenant_id}"
        try:
            collection = service.kvstore[collection_name]
            records = collection.data.query()
            return {
                "payload": {
                    "action": "success",
                    "count": len(records),
                    "records": records,
                },
                "status": 200,
            }
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"Error querying variable delay collection",
                    "exception": str(e),
                },
                "status": 500,
            }

    # Compute variable delay thresholds from historical metrics (dry-run)
    def post_compute(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_variable_delay/compute" mode="post" body="{'tenant_id': 'mytenant', 'component': 'splk-dsm', 'object': 'myobject', 'method': 'perc95', 'lookback': '-30d'}"
        """

        # init
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        # defaults so the variables exist on every code path below
        strategy = "generate"
        existing_slots = []

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]
                component = resp_dict["component"]
                object_id = resp_dict.get("object_id")
                object_value = resp_dict.get("object")
                method = resp_dict.get("method", "perc95")
                lookback = resp_dict.get("lookback", "-30d")
                min_samples = int(resp_dict.get("min_samples", "10"))
                max_threshold_sec = int(resp_dict.get("max_threshold_sec", "604800"))
                strategy = str(resp_dict.get("strategy", "generate")).lower()
                # existing_slots accepted as either a JSON list of slot dicts
                # or the wrapped {"slots": [...]} shape that the modal stores
                # in variable_delay_slots. Parse strings opportunistically so
                # callers can pass the raw KV value through unchanged.
                raw_existing = resp_dict.get("existing_slots")
                if isinstance(raw_existing, str):
                    try:
                        raw_existing = json.loads(raw_existing)
                    except (ValueError, TypeError):
                        raw_existing = None
                if isinstance(raw_existing, dict):
                    raw_existing = raw_existing.get("slots")
                if isinstance(raw_existing, list):
                    existing_slots = raw_existing
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint computes proposed variable delay thresholds from historical metrics data (dry-run, does not save). It requires a POST call with the following information:",
                "resource_desc": "Compute proposed variable delay thresholds from historical data",
                "resource_spl_example": '| trackme url="/services/trackme/v2/splk_variable_delay/compute" mode="post" body=\'{"tenant_id": "mytenant", "component": "splk-dsm", "object": "myobject", "method": "perc95", "lookback": "-30d", "strategy": "honour", "existing_slots": [{"slot_name": "business_hours", "days": [0,1,2,3,4], "hours": [8,9,10,11,12,13,14,15,16,17], "max_delay_allowed": 3600}]}\'',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "MANDATORY, component type: splk-dsm or splk-dhm",
                        "object": "CONDITIONAL, the entity name (either object or object_id is required)",
                        "object_id": "CONDITIONAL, the entity KVstore key (preferred over object for robustness)",
                        "method": "OPTIONAL, statistical method: perc95 (default) or perc99",
                        "lookback": "OPTIONAL, lookback period for metrics: e.g. -30d (default: -30d)",
                        "min_samples": "OPTIONAL, minimum metric samples per hour/day (default: 10)",
                        "max_threshold_sec": "OPTIONAL, safety cap in seconds (default: 604800 = 7 days)",
                        "strategy": 'OPTIONAL, "generate" (default) regenerates slots from scratch; "honour" keeps existing slot layout and only refreshes max_delay_allowed per slot. Requires existing_slots.',
                        "existing_slots": 'CONDITIONAL (required when strategy="honour"), the current slot list as either a JSON list or {"slots": [...]} object',
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # validate strategy / existing_slots pairing
        if strategy not in ("generate", "honour"):
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Invalid strategy "{strategy}", must be "generate" or "honour"',
                },
                "status": 400,
            }
        if strategy == "honour" and not existing_slots:
            return {
                "payload": {
                    "action": "failure",
                    "response": 'strategy="honour" requires existing_slots in the payload',
                },
                "status": 400,
            }

        # set log level
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # validate component
        if component not in ("dsm", "dhm", "splk-dsm", "splk-dhm"):
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Invalid component "{component}", must be "dsm", "dhm", "splk-dsm", or "splk-dhm"',
                },
                "status": 400,
            }

        # normalize component
        comp = component.replace("splk-", "")
        object_category = f"splk-{comp}"

        # validate that at least one entity identifier is provided
        if not object_id and not object_value:
            return {
                "payload": {
                    "action": "failure",
                    "response": "Either object_id or object is required",
                },
                "status": 400,
            }

        # create service connection (needed for KVstore lookups and search execution)
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.session_key,
            timeout=600,
        )

        # if object_id is provided but not object, resolve object name from main collection
        if object_id and not object_value:
            try:
                main_collection_name = f"kv_trackme_{comp}_tenant_{tenant_id}"
                main_collection = service.kvstore[main_collection_name]
                main_records = main_collection.data.query(
                    query=json.dumps({"_key": object_id})
                )
                if main_records and len(main_records) > 0:
                    object_value = main_records[0].get("object", "")
                else:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f"Entity with object_id '{object_id}' not found",
                        },
                        "status": 404,
                    }
            except Exception as e:
                return {
                    "payload": {
                        "action": "failure",
                        "response": f"Failed to resolve object name from object_id: {str(e)}",
                    },
                    "status": 500,
                }

        # validate method
        if method not in ("perc95", "perc99"):
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Invalid method "{method}", must be "perc95" or "perc99"',
                },
                "status": 400,
            }

        stat_func = "perc95" if method == "perc95" else "perc99"

        # Build mstats query
        search_query = remove_leading_spaces(
            f"""
            | mstats latest(trackme.splk.feeds.lag_event_sec) as lag_event_sec
              where `trackme_metrics_idx({tenant_id})`
              tenant_id="{tenant_id}"
              object_category="{object_category}"
              object="{object_value}"
              earliest="{lookback}" latest="now"
              by object span=5m
            | eval day_of_week=tonumber(strftime(_time, "%w"))
            | eval day_of_week=if(day_of_week==0, 6, day_of_week-1)
            | eval hour_of_day=tonumber(strftime(_time, "%H"))
            | stats {stat_func}(lag_event_sec) as stat_delay,
                    avg(lag_event_sec) as avg_delay,
                    count as sample_count
              by object, day_of_week, hour_of_day
            | where sample_count >= {min_samples}
            """
        )

        kwargs_search = {
            "earliest_time": lookback,
            "latest_time": "now",
            "output_mode": "json",
            # count=0 returns all rows. The stats produces up to 7*24 = 168
            # rows (day_of_week x hour_of_day); the Splunk default of 100
            # would silently truncate and yield incomplete hourly thresholds.
            "count": 0,
        }

        try:
            search_results_reader = run_splunk_search(
                service,
                search_query,
                kwargs_search,
                24,
                5,
            )
            # Materialize the lazy JSONResultsReader into a list inside the
            # try/except so that JSON parse errors (e.g. empty response) are
            # caught here rather than bubbling up as an unhandled HTTP 500.
            search_results = [
                r for r in search_results_reader if isinstance(r, dict)
            ]
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": "Failed to run metrics search",
                    "exception": str(e),
                },
                "status": 500,
            }

        if not search_results:
            return {
                "payload": {
                    "action": "success",
                    "response": "No historical metrics data found for this entity in the specified lookback period",
                    "proposed_slots": None,
                    "sample_count": 0,
                },
                "status": 200,
            }

        # Compute per-hour thresholds from the metrics
        hourly_thresholds = {}
        total_samples = 0
        for result in search_results:
            try:
                day = int(float(result.get("day_of_week", 0)))
                hour = int(float(result.get("hour_of_day", 0)))
                stat_delay = float(result.get("stat_delay", 0))
                sample_count = int(float(result.get("sample_count", 0)))
            except (ValueError, TypeError):
                continue

            threshold = compute_threshold(stat_delay)
            # Apply safety cap
            if threshold > max_threshold_sec:
                threshold = max_threshold_sec
            hourly_thresholds[(day, hour)] = threshold
            total_samples += sample_count

        if not hourly_thresholds:
            return {
                "payload": {
                    "action": "success",
                    "response": "No valid hourly thresholds could be computed from the available data",
                    "proposed_slots": None,
                    "sample_count": 0,
                },
                "status": 200,
            }

        # Aggregate into slots
        if strategy == "honour":
            proposed_slots_list, proposed_default = recompute_existing_slot_thresholds(
                existing_slots, hourly_thresholds, max_threshold_sec
            )
        else:
            proposed_slots_list = aggregate_slots(hourly_thresholds)
            proposed_default = max(hourly_thresholds.values())
            if proposed_default > max_threshold_sec:
                proposed_default = max_threshold_sec

        proposed_slots_config = {"slots": proposed_slots_list}

        return {
            "payload": {
                "action": "success",
                "proposed_slots": proposed_slots_config,
                "proposed_default": int(proposed_default),
                "method": method,
                "lookback": lookback,
                "strategy": strategy,
                "sample_count": total_samples,
                "hourly_coverage": len(hourly_thresholds),
                "slot_count": len(proposed_slots_list),
            },
            "status": 200,
        }

    # ------------------------------------------------------------------
    # POST /templates_list — list custom variable delay slot templates
    #
    # Returns the RAW per-tenant custom template records for a given
    # component. The frontend is responsible for merging these with the
    # hardcoded factory defaults (from slotTemplates.ts), following the
    # override-by-template_id model documented in issue #1056. Any
    # trackme_user role can read — the templates are used to render the
    # Quick templates buttons in the variable delay slot editor, which
    # every user configuring variable delay needs access to.
    # ------------------------------------------------------------------
    def post_templates_list(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_variable_delay/templates_list" mode="post" body='{"tenant_id": "mytenant", "component": "dsm"}'
        """

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": (
                    "List per-tenant custom variable delay slot templates for a given "
                    "component. Returns the raw KVstore records; the frontend merges "
                    "them with the factory defaults from slotTemplates.ts using the "
                    "override-by-template_id model. Used by the variable delay slot "
                    "editor and by the 'Manage: Variable delay templates' admin modal."
                ),
                "resource_desc": "List custom variable delay templates for a tenant + component",
                "resource_spl_example": (
                    '| trackme url="/services/trackme/v2/splk_variable_delay/templates_list" '
                    'mode="post" body=\'{"tenant_id":"mytenant","component":"dsm"}\''
                ),
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "MANDATORY — 'dsm' or 'dhm' (also accepts 'splk-dsm'/'splk-dhm')",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        tenant_id = resp_dict.get("tenant_id")
        raw_component = resp_dict.get("component", "")
        if not tenant_id:
            return {"payload": {"action": "failure", "response": "tenant_id is required"}, "status": 400}

        if not isinstance(raw_component, str):
            return {"payload": {"action": "failure", "response": "component must be a string"}, "status": 400}
        # Lowercase BEFORE stripping the "splk-" prefix: the replace is
        # case-sensitive, so uppercase/mixed-case inputs like "SPLK-DSM"
        # would have bypassed the replace with the previous order and
        # then .lower() would have produced "splk-dsm", failing the
        # component check. See bugbot R2 on #1058.
        component = raw_component.strip().lower().replace("splk-", "")
        if component not in ("dsm", "dhm"):
            return {
                "payload": {
                    "action": "failure",
                    "response": "component must be one of ('dsm', 'dhm')",
                },
                "status": 400,
            }

        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.session_key,
            timeout=600,
        )

        collection_name = f"kv_trackme_common_variable_delay_templates_tenant_{tenant_id}"
        try:
            collection = service.kvstore[collection_name]
        except Exception as e:
            # Graceful degradation — a tenant that predates this feature or
            # has a broken collection should still render the factory
            # defaults client-side, not crash the editor.
            logger.warning(
                f'post_templates_list: collection not found, tenant_id="{tenant_id}", '
                f'collection="{collection_name}", exception="{str(e)}"'
            )
            return {
                "payload": {
                    "action": "success",
                    "response": "No custom templates collection — using factory defaults",
                    "templates": [],
                },
                "status": 200,
            }

        try:
            records = collection.data.query(query=json.dumps({"component": component}))
        except Exception as e:
            logger.error(
                f'post_templates_list: query failed, tenant_id="{tenant_id}", '
                f'component="{component}", exception="{str(e)}"'
            )
            return {
                "payload": {
                    "action": "failure",
                    "response": "Failed to query custom templates",
                    "exception": str(e),
                },
                "status": 500,
            }

        # Sort client-readable order: sort_order ascending, then ctime
        def _sort_key(rec):
            try:
                so = int(rec.get("sort_order", 100))
            except (TypeError, ValueError):
                so = 100
            try:
                ct = float(rec.get("ctime", 0))
            except (TypeError, ValueError):
                ct = 0
            return (so, ct)

        records_sorted = sorted(records or [], key=_sort_key)

        return {
            "payload": {
                "action": "success",
                "templates": records_sorted,
            },
            "status": 200,
        }
