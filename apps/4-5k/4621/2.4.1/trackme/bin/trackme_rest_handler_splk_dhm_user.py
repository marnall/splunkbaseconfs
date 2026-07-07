#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_dhm.py"
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
import re
import requests

splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_dhm_user", "trackme_rest_api_splk_dhm_user.log"
)


import trackme_rest_handler

# import trackme libs
from trackme_libs import extract_keys_list, trackme_getloglevel, trackme_idx_for_tenant, trackme_parse_describe_flag

# TrackMe splk-feeds libs
from trackme_libs_splk_feeds import (
    splk_dhm_return_entity_info,
    splk_dhm_return_searches,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# Splunk libs
import splunklib.client as client


# Read-path allowlist for breakby_extra_fields names — must match the
# canonical pattern enforced by _normalize_breakby_extra_fields in
# trackme_rest_handler_splk_hybrid_trackers_admin.py at tracker-creation
# time. Duplicated intentionally (not imported from the admin handler)
# to keep this user-tier handler free of admin-handler dependencies.
# A legitimate extras-aware tracker passes this regex by construction;
# the check is purely defense-in-depth against directly-edited KV
# records ending up spliced into the SPL `mstats ... by` clause.
_DHM_EXTRA_FIELD_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


class TrackMeHandlerSplkDhmRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkDhmRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_dhm(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_dhm",
            "resource_group_desc": "Endpoints specific to the splk-dhm TrackMe component (Splunk Data Hosts monitoring, read-only operations).",
        }

        return {"payload": response, "status": 200}

    # Get entity info
    def post_dh_entity_info(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_dhm/dh_entity_info" mode="post" body="{'tenant_id': 'mytenant', 'object': 'remote|account:lab|firewall.pan.amer.design.node1'}"
        """

        # init
        object_value = None
        object_id = None
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
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "the tenant_id is required",
                        },
                        "status": 500,
                    }
                # object or object_id must be provided, but not both
                try:
                    object_value = resp_dict["object"]
                except Exception as e:
                    object_value = None
                try:
                    object_id = resp_dict["object_id"]
                except Exception as e:
                    object_id = None
                if object_value and object_id:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "only object or object_id can be specified, not both",
                        },
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns various information related to the entity. It requires a POST call with the following information:",
                "resource_desc": "Return the entity's main information. These normalized details are used to build queries dynamically through the user interfaces.",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dhm/dh_entity_info\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'object': 'remote|account:lab|firewall.pan.amer.design.node1'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object": "The entity identifier. You can specify either the object or the object_id, but not both",
                        "object_id": "The entity key identifier. You can specify either the object or the object_id, but not both",
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
            token=request_info.session_key,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Data collection
        collection_name = "kv_trackme_dhm_tenant_" + str(tenant_id)
        collection = service.kvstore[collection_name]

        # Define the KV query
        query_string = {}

        if object_value:
            query_string["object"] = object_value
        elif object_id:
            query_string["_key"] = object_id

        # Get the current record
        # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

        try:
            kvrecord = collection.data.query(query=json.dumps(query_string))[0]
            key = kvrecord.get("_key")
            if not object_value:
                object_value = kvrecord.get("object")

        except Exception as e:
            key = None

            if not object_value:
                return {
                    "payload": {
                        "action": "failure",
                        "response": f'the entity with identifier="{object_id}" was not found',
                    },
                    "status": 404,
                }

            else:
                return {
                    "payload": {
                        "action": "failure",
                        "response": f'the entity with identifier="{object_value}" was not found',
                    },
                    "status": 404,
                }

        # proceed
        if key:
            # init
            response = {}

            try:
                # Get entity info
                entity_info = splk_dhm_return_entity_info(kvrecord)

                # Add
                response["entity_info"] = entity_info

                # log debug
                logger.debug(
                    f'function splk_dhm_return_entity_info, entity_info="{json.dumps(entity_info, indent=2)}"'
                )

                # Add to dict
                entity_info["index"] = kvrecord.get("data_index")
                entity_info["sourcetype"] = kvrecord.get("data_sourcetype")
                # set the search constraint
                # In merged mode, data_sourcetype is the "@all" sentinel rather
                # than a real sourcetype — drop the sourcetype clause so the
                # search matches every sourcetype the host actually produces.
                data_sourcetype_raw = kvrecord.get("data_sourcetype", "")
                sourcetype_clause = (
                    "" if data_sourcetype_raw == "@all"
                    else f" sourcetype IN ({data_sourcetype_raw})"
                )
                if entity_info["breakby_key"] != "none":
                    entity_info["search_constraint"] = (
                        f'index IN ({kvrecord.get("data_index")}){sourcetype_clause} {entity_info["breakby_key"]}="{entity_info["breakby_value"]}"'
                    )
                else:
                    entity_info["search_constraint"] = (
                        f'index IN ({kvrecord.get("data_index")}){sourcetype_clause} host="{str(object_value)}"'
                    )

                # Resolve metric index for this tenant
                tenant_indexes = trackme_idx_for_tenant(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                )
                tenant_trackme_metric_idx = tenant_indexes.get("trackme_metric_idx", "trackme_metrics")

                # get entity searches
                entity_searches = splk_dhm_return_searches(
                    tenant_id, object_value, entity_info, tenant_trackme_metric_idx=tenant_trackme_metric_idx
                )

                # log debug
                logger.debug(
                    f'function splk_dhm_return_searches, entity_searches="{json.dumps(entity_searches, indent=2)}"'
                )

                # add
                entity_info["splk_dhm_raw_search"] = entity_searches.get(
                    "splk_dhm_raw_search"
                )
                entity_info["splk_dhm_metrics_populate_search"] = entity_searches.get(
                    "splk_dhm_metrics_populate_search"
                )

                # single stats: manage both splunk query and trackme metric based query
                entity_info["splk_dhm_overview_splunk_single_stats"] = (
                    entity_searches.get("splk_dhm_overview_root_search")
                )
                entity_info["splk_dhm_overview_trackme_single_stats"] = (
                    remove_leading_spaces(
                        f"""\
                            | mstats avg(trackme.splk.feeds.avg_latency_5m) as avg_latency, avg(trackme.splk.feeds.perc95_latency_5m) as perc95_latency where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-dhm" object="{object_value}"
                            | appendcols [ | inputlookup trackme_dhm_tenant_{tenant_id} where object="{object_value}" | eval event_delay=now()-data_last_time_seen | table event_delay ]
                        """
                    )
                )

                # Detect the entity's extras dimensions (breakby_extra_fields
                # propagated through the pipeline). We collect the union of
                # `extras` keys across all combos in splk_dhm_st_summary so
                # the pie root search groups by every dimension the entity
                # actually emits metrics for. Empty / absent for legacy
                # non-extras trackers — root search stays byte-identical.
                dhm_extras_fields = []
                try:
                    raw_summary_str = kvrecord.get("splk_dhm_st_summary") or "{}"
                    raw_summary_obj = (
                        json.loads(raw_summary_str)
                        if isinstance(raw_summary_str, str)
                        else raw_summary_str
                    )
                    if isinstance(raw_summary_obj, dict):
                        # Preserve first-seen order across combos for stable
                        # field ordering in the SPL `by` clause.
                        seen_extras = set()
                        for combo_entry in raw_summary_obj.values():
                            if not isinstance(combo_entry, dict):
                                continue
                            extras_inner = combo_entry.get("extras")
                            if isinstance(extras_inner, dict):
                                for ek in extras_inner.keys():
                                    if ek and ek not in seen_extras:
                                        seen_extras.add(ek)
                                        dhm_extras_fields.append(str(ek))
                except (ValueError, TypeError, AttributeError):
                    dhm_extras_fields = []
                # Filter out anything that would shadow the existing dims —
                # `idx`/`st` are emitted by the metrics generator under those
                # exact names, and `object`/`object_id` are reserved entity
                # identifiers. The REST validator already rejects these on
                # tracker creation, but defensive here too.
                dhm_extras_fields = [
                    f for f in dhm_extras_fields
                    if f not in ("object", "object_id", "idx", "st", "alias", "tenant_id", "object_category")
                ]
                # Defense-in-depth: re-apply the canonical field-name
                # allowlist before splicing into the SPL `by` clause.
                # _normalize_breakby_extra_fields rejects names that
                # don't match this regex at tracker-creation time, but
                # the KV record could in theory be edited directly
                # (REST API or kvstore CLI) to inject characters that
                # break out of the `by` clause. Anything that fails the
                # regex is silently dropped — a legitimate tracker
                # never produces such names, so this is a no-op for
                # every valid extras-aware tracker.
                dhm_extras_fields = [
                    f for f in dhm_extras_fields
                    if _DHM_EXTRA_FIELD_PATTERN.match(f)
                ]
                # Embed extras into the metrics `by` clause so the per-extras
                # donut (and any future extras-aware analytics) can stack on
                # the same root query.
                dhm_extras_by_suffix = (
                    (", " + ", ".join(dhm_extras_fields)) if dhm_extras_fields else ""
                )

                # add both options for trackme and splunk
                entity_info["splk_dhm_overview_splunk_pie_root_search"] = (
                    entity_searches.get("splk_dhm_overview_pie_root_search")
                )
                entity_info["splk_dhm_overview_trackme_pie_root_search"] = (
                    f'| mstats latest(trackme.splk_dhm.last_eventcount) as count where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-dhm" object_id="{key}" by object, idx, st{dhm_extras_by_suffix} | rename idx as index, st as sourcetype | where [ | inputlookup trackme_dhm_tenant_{tenant_id} where _key="{key}" | table data_index, data_sourcetype | eval data_index=split(data_index, ","), data_sourcetype=split(data_sourcetype, ",") | rename data_index as index, data_sourcetype as sourcetype | where isnotnull(index) and isnotnull(sourcetype) | append [ | makeresults | eval index="none", sourcetype="none" | fields - _time ] | head 1 | format | return $search ]'
                )
                # Surface the resolved extras-field list back to the
                # frontend so the overview tab knows which per-extras
                # donuts to render without re-parsing splk_dhm_st_summary.
                # Omit the key entirely on pre-extras (non-extras-aware)
                # trackers — matches the omit-when-empty pattern used by
                # `summary_extras` (component_user.py), `extras_dimensions`
                # (trackme_libs_describe.py), and `breakby_extra_fields`
                # (admin handler). Preserves the byte-identical
                # entity_info shape for legacy DHM entities so consumers
                # that key-presence-check don't get a false signal.
                # OverviewTabDhm.tsx handles `undefined` via its
                # Array.isArray fallback to `[]`.
                if dhm_extras_fields:
                    entity_info["splk_dhm_overview_extras_fields"] = list(dhm_extras_fields)

                # timechart view
                entity_info["splk_dhm_overview_splunk_timechart"] = entity_searches.get(
                    "splk_dhm_overview_timechart"
                )
                entity_info["splk_dhm_overview_trackme_timechart"] = (
                    remove_leading_spaces(
                        f"""\
                            | mstats avg(trackme.splk.feeds.lag_event_sec) as lag_event_sec, avg(trackme.splk.feeds.latest_eventcount_5m) as latest_eventcount_5m, avg(trackme.splk.feeds.avg_latency_5m) as avg_latency_5m where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-dhm" object="{object_value}" by object span=5m
                            | timechart `auto_span` avg(avg_latency_5m) as avg_latency_5m, sum(latest_eventcount_5m) as latest_eventcount_5m, avg(lag_event_sec) as lag_event_sec
                        """
                    )
                )

                # add object and key
                entity_info["object"] = object_value
                entity_info["key"] = key

                #
                # Handle problematic backslashes in search_constraint: replace single backslashes by double backslashes
                #

                # for key pairs in entity_info, replace single backslashes by double backslashes
                for key, value in entity_info.items():
                    if isinstance(value, str):
                        entity_info[key] = value.replace("\\", "\\\\")

                # render response
                return {"payload": entity_info, "status": 200}

            except Exception as e:
                # render response
                msg = f'An exception was encountered while processing entity get info, exception="{str(e)}"'
                logger.error(msg)
                return {
                    "payload": {
                        "action": "failure",
                        "response": msg,
                    },
                    "status": 500,
                }

    # get the component table
    def post_dhm_get_table(self, request_info, **kwargs):
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
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "the tenant_id is required",
                        },
                        "status": 500,
                    }

                try:
                    key_id = resp_dict["key_id"]
                    if key_id == "*":
                        key_id = None
                except Exception as e:
                    key_id = None

                try:
                    object = resp_dict["object"]
                    if object == "*":
                        object = None
                except Exception as e:
                    object = None

                # only key_id or object can be specified
                if key_id and object:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "only key_id or object can be specified, not both",
                        },
                        "status": 500,
                    }

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrievs the component table, it requires a POST call with the following options:",
                "resource_desc": "Get the entity table",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dhm/dhm_get_table\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'key_id': '*', 'object': '*'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "key_id": "(optional) key id, do not specify this to match all entities",
                        "object": "(optional) entity name, do not specify this to match all entities",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # url
        url = f"{request_info.server_rest_uri}/services/trackme/v2/component/load_component_data"

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": f"Splunk {request_info.system_authtoken}",
            "Content-Type": "application/json",
        }

        params = {
            "tenant_id": tenant_id,
            "component": "dhm",
            "page": 1,
            "size": 0,
        }

        if key_id:
            params["filter_key"] = key_id
        elif object:
            params["object_key"] = object

        data_records = []

        # Proceed
        try:
            response = requests.get(
                url,
                headers=header,
                params=params,
                verify=False,
                timeout=600,
            )

            if response.status_code not in (200, 201, 204):
                msg = f'get component has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                return {"payload": msg, "status": 500}

            else:
                response_json = response.json()
                data = response_json.get("data", [])

                # add the data to the data_records
                for record in data:
                    data_records.append(record)

                # return
                return {"payload": data_records, "status": 200}

        except Exception as e:
            msg = f'get component has failed, exception="{str(e)}"'
            logger.error(msg)
            return {"payload": msg, "status": 500}

    # get per hosts blocklists
    def post_dh_get_host_blocklists(self, request_info, **kwargs):
        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]

                # handle object_list / keys_list
                object_list = resp_dict.get("object_list", None)
                if object_list:
                    if not isinstance(object_list, list):
                        object_list = object_list.split(",")

                keys_list = extract_keys_list(resp_dict)
                if keys_list:
                    if not isinstance(keys_list, list):
                        keys_list = keys_list.split(",")

                if not object_list and not keys_list:
                    return {
                        "payload": {
                            "error": "either object_list or keys_list must be provided"
                        },
                        "status": 500,
                    }

                action = resp_dict["action"]
                if not action in ("enable", "disable"):
                    return {
                        "payload": "Invalid option for action, valid options are: enable | disable",
                        "status": 500,
                    }
                else:
                    if action == "enable":
                        action_value = "enabled"
                    elif action == "disable":
                        action_value = "disabled"

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns the current per-host data blocklist definitions assigned to one or more DHM entities. It requires a POST call with tenant_id, action, and either object_list or keys_list to identify the target entities. The response is a list of {keyid, object, host_blocklists} records, one per resolved entity.",
                "resource_desc": "Return the current per-host data blocklist definitions for a list of DHM entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dhm/dh_get_host_blocklists\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'action': 'enable', 'object_list': 'key:host|linux-srv-eu1'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "action": "REQUIRED. Must be one of: enable | disable. Reserved by the existing endpoint contract; the response payload is identical regardless of the value supplied",
                        "object_list": "REQUIRED (with keys_list as alternative). Comma-separated list of entity object names. Either object_list or keys_list must be provided",
                        "keys_list": "REQUIRED (with object_list as alternative). Comma-separated list of entity KV record _keys. Either object_list or keys_list must be provided",
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
            token=request_info.session_key,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Data collection
        collection_name = f"kv_trackme_dhm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # loop and proceed
        return_records = []

        if object_list:
            keys_list = []
            for object in object_list:
                try:
                    kvrecord = collection.data.query(
                        query=json.dumps({"object": object})
                    )[0]
                    key = kvrecord.get("_key")
                    keys_list.append(key)
                except Exception as e:
                    key = None

        for key in keys_list:
            try:
                kvrecord = collection.data.query(query=json.dumps({"_key": key}))[0]
                host_idx_blocklists = kvrecord.get("host_idx_blocklists", [])
                host_st_blocklists = kvrecord.get("host_st_blocklists", [])

                # turn as lists from CSV if defined and not already
                if host_idx_blocklists:
                    if not isinstance(host_idx_blocklists, list):
                        host_idx_blocklists = host_idx_blocklists.split(",")

                if host_st_blocklists:
                    if not isinstance(host_st_blocklists, list):
                        host_st_blocklists = host_st_blocklists.split(",")

                return_records.append(
                    {
                        "keyid": key,
                        "object": kvrecord.get("object"),
                        "host_idx_blocklists": host_idx_blocklists,
                        "host_st_blocklists": host_st_blocklists,
                    }
                )
            except:
                pass

        # render
        return {"payload": return_records, "status": 200}
