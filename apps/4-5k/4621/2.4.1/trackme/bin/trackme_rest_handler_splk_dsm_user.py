#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_dsm.py"
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
import requests

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_dsm_user", "trackme_rest_api_splk_dsm_user.log"
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import extract_keys_list, trackme_getloglevel, trackme_idx_for_tenant, trackme_parse_describe_flag, trackme_reqinfo

# TrackMe splk-feeds libs
from trackme_libs_splk_feeds import (
    splk_dsm_return_entity_info,
    splk_dsm_return_elastic_info,
    splk_dsm_return_searches,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkDsmRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkDsmRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_dsm(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_dsm",
            "resource_group_desc": "Endpoints specific to the splk-dsm TrackMe component (Splunk Data Sources monitoring, read-only operations).",
        }

        return {"payload": response, "status": 200}

    # Get entity info
    def post_ds_entity_info(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_dsm/ds_entity_info" mode="post" body="{'tenant_id': 'mytenant', 'object': 'netscreen:netscreen:firewall'}"
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/ds_entity_info\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'object': 'netscreen:netscreen:firewall'}\"",
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
        collection_name = "kv_trackme_dsm_tenant_" + str(tenant_id)
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

            # ensure object_id is set and use it as the convention
            object_id = key

            # init
            response = {}

            try:
                # Get entity info
                elastic_info = splk_dsm_return_elastic_info(
                    request_info.session_key,
                    request_info.server_rest_port,
                    tenant_id,
                    object_value,
                )
                entity_info = splk_dsm_return_entity_info(kvrecord)

                # add object_id to entity_info
                entity_info["object_id"] = object_id

                # Check if is an Elastic Source
                is_elastic = elastic_info.get("is_elastic")
                if is_elastic == 1:
                    response["elastic_info"] = elastic_info
                else:
                    response["entity_info"] = entity_info

                # log debug
                logger.debug(
                    f'function splk_dsm_return_elastic_info, elastic_info="{json.dumps(elastic_info, indent=2)}"'
                )
                logger.debug(
                    f'function splk_dsm_return_entity_info, entity_info="{json.dumps(entity_info, indent=2)}"'
                )

                # Get entity account and search_mode
                account = None
                search_mode = None

                if is_elastic == 1:
                    account = elastic_info.get("account")
                    search_mode = elastic_info.get("search_mode")

                else:
                    account = entity_info.get("account")
                    search_mode = entity_info.get("search_mode")

                # if is elastic, update the elastic info to the entity info dict
                if is_elastic == 1:
                    entity_info["account"] = account
                    entity_info["search_mode"] = search_mode
                    entity_info["is_elastic"] = 1
                    entity_info["search_constraint"] = elastic_info.get(
                        "search_constraint"
                    )
                    entity_info["elastic_search_mode"] = elastic_info.get(
                        "elastic_search_mode"
                    )
                    entity_info.pop("breakby_key", None)
                    entity_info.pop("breakby_value", None)
                    entity_info.pop("breakby_statement", None)

                else:
                    entity_info["is_elastic"] = 0
                    entity_info["index"] = kvrecord.get("data_index")

                    # entity sourcetype
                    entity_sourcetype = kvrecord.get("data_sourcetype", "any")

                    # if entity_sourcetype is all/any, set to * and handle merged mode
                    if entity_sourcetype in ("all", "any", ""):
                        entity_info["sourcetype"] = "*"
                        entity_sourcetype = "*"

                        # set the key only for merged mode
                        if entity_info["breakby_key"] == "none":
                            entity_info["breakby_key"] = "merged"

                    else:
                        entity_info["sourcetype"] = entity_sourcetype

                    # set the search constraint
                    if (
                        entity_info["breakby_key"] != "none"
                        and entity_info["breakby_key"] != "merged"
                    ):

                        # support multiple fields

                        # first, convert into lists
                        break_by_field = entity_info["breakby_key"].split(";")
                        break_by_value = entity_info["breakby_value"].split(";")

                        # init a dict and counter
                        break_by_dict = {}
                        break_by_ordercount = 0

                        # if we have multiple fields, create a dict of keys/values
                        if len(break_by_field) > 1:

                            for subbreak_by_field in break_by_field:
                                break_by_dict[subbreak_by_field] = break_by_value[
                                    break_by_ordercount
                                ]
                                break_by_ordercount += 1

                            # init the search definition
                            search_definition = f'index="{kvrecord.get("data_index")}" sourcetype="{entity_sourcetype}"'

                            # loop through the keys and the key/value pair
                            for subbreak_by_field in break_by_field:
                                search_definition = f'{search_definition} {subbreak_by_field}="{break_by_dict[subbreak_by_field]}"'

                            # finally, to the response
                            entity_info["search_constraint"] = search_definition

                        # single break by field
                        else:
                            entity_info["search_constraint"] = (
                                f'index="{kvrecord.get("data_index")}" sourcetype="{entity_sourcetype}" {entity_info["breakby_key"]}="{entity_info["breakby_value"]}"'
                            )

                    else:

                        entity_info["search_constraint"] = (
                            f'index="{kvrecord.get("data_index")}" sourcetype="{entity_sourcetype}"'
                        )

                # log debug
                logger.debug(
                    f'function post_ds_entity_info, entity_info="{json.dumps(entity_info, indent=2)}"'
                )

                # Resolve metric index for this tenant
                tenant_indexes = trackme_idx_for_tenant(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                )
                tenant_trackme_metric_idx = tenant_indexes.get("trackme_metric_idx", "trackme_metrics")

                # get entity searches
                entity_searches = splk_dsm_return_searches(
                    tenant_id, object_value, entity_info, tenant_trackme_metric_idx=tenant_trackme_metric_idx
                )

                # log debug
                logger.debug(
                    f'function splk_dsm_return_searches, entity_searches="{json.dumps(entity_searches, indent=2)}"'
                )

                # add
                entity_info["splk_dsm_overview_root_search"] = entity_searches.get(
                    "splk_dsm_overview_root_search"
                )

                # single stats: manage both splunk query and trackme metric based query
                entity_info["splk_dsm_overview_splunk_single_stats"] = (
                    entity_searches.get("splk_dsm_overview_single_stats")
                )
                entity_info["splk_dsm_overview_trackme_single_stats"] = (
                    remove_leading_spaces(
                        f"""\
                        | mstats avg(trackme.splk.feeds.avg_latency_5m) as avg_latency, avg(trackme.splk.feeds.perc95_latency_5m) as perc95_latency where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-dsm" object="{object_value}"
                        | appendcols [ | inputlookup trackme_dsm_tenant_{tenant_id} where object="{object_value}" | eval event_delay=now()-data_last_time_seen | table event_delay ]
                        """
                    )
                )

                # timechart overview: manage both splunk query and trackme metric based query
                entity_info["splk_dsm_overview_splunk_timechart"] = entity_searches.get(
                    "splk_dsm_overview_timechart"
                )
                entity_info["splk_dsm_overview_trackme_timechart"] = (
                    remove_leading_spaces(
                        f"""\
                        | mstats avg(trackme.splk.feeds.lag_event_sec) as lag_event_sec, avg(trackme.splk.feeds.latest_eventcount_5m) as latest_eventcount_5m, avg(trackme.splk.feeds.latest_dcount_host_5m) as latest_dcount_host_5m, avg(trackme.splk.feeds.avg_latency_5m) as avg_latency_5m where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-dsm" object="{object_value}" by object span=5m
                        | timechart `auto_span` avg(avg_latency_5m) as avg_latency_5m, sum(latest_eventcount_5m) as latest_eventcount_5m, avg(latest_dcount_host_5m) as latest_dcount_host_5m, avg(lag_event_sec) as lag_event_sec
                        """
                    )
                )

                # add
                entity_info["splk_dsm_raw_search"] = entity_searches.get(
                    "splk_dsm_raw_search"
                )
                entity_info["splk_dsm_sampling_search"] = entity_searches.get(
                    "splk_dsm_sampling_search"
                )
                entity_info["splk_dsm_metrics_populate_search"] = entity_searches.get(
                    "splk_dsm_metrics_populate_search"
                )

                # add object and key
                entity_info["object"] = object_value
                entity_info["key"] = key

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
    def post_dsm_get_table(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/dsm_get_table\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'key_id': '*', 'object': '*'}\"",
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
            "component": "dsm",
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

    # get sampling obfuscation mode for a given tenant
    def post_ds_get_dsm_sampling_obfuscation_mode(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_dsm/ds_get_dsm_sampling_obfuscation_mode" mode="post" body="{'tenant_id':'mytenant'}"
        """

        describe = False
        tenant_id = None

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]
        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrieves the tenant sampling obfuscation mode,, it requires a POST call with the following options:",
                "resource_desc": "Get the data sampling obfuscation mode for a given entity",
                "resource_spl_example": '| trackme url="/services/trackme/v2/splk_dsm/ds_get_dsm_sampling_obfuscation_mode" mode="post" body="{\'tenant_id\':\'mytenant\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % request_info.session_key,
            "Content-Type": "application/json",
        }

        # target
        record_url = "%s/services/trackme/v2/vtenants/vtenants_accounts" % (
            request_info.server_rest_uri
        )

        try:
            response = requests.post(
                record_url,
                headers=header,
                data=json.dumps({"tenant_id": tenant_id}),
                verify=False,
                timeout=600,
            )
            if response.status_code == 200:
                response_json = response.json()
                logger.info(f'response_json="{response_json}"')
                data_sampling_obfuscation = int(
                    response_json.get("data_sampling_obfuscation")
                )
                logger.info(f'data_sampling_obfuscation="{data_sampling_obfuscation}"')
            else:
                data_sampling_obfuscation = 1
        except Exception as e:
            return {
                "payload": {
                    "response": "An exception was encountered",
                    "exception": str(e),
                },
                "status": 500,
            }

        # return
        if data_sampling_obfuscation == 0:
            return {
                "payload": {
                    "mode": "disabled",
                },
                "status": 200,
            }

        elif data_sampling_obfuscation == 1:
            return {
                "payload": {
                    "mode": "enabled",
                },
                "status": 200,
            }

        else:
            return {
                "payload": {
                    "response": "unable to retrieve the obfuscation mode, consults the logs for more information",
                },
                "status": 500,
            }

    # get sampling summary for a given entity
    def post_ds_get_dsm_sampling(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_dsm/ds_get_dsm_sampling" mode="post" body="{'tenant_id':'mytenant', 'object': 'netscreen:netscreen:firewall'}"
        """

        describe = False
        tenant_id = None
        object = None

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]
                object = resp_dict["object"]
        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrievs the component table, it requires a POST call with the following options:",
                "resource_desc": "Get the data sampling summary for a given entity",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/ds_get_dsm_sampling\" mode=\"post\" body=\"{'tenant_id':'mytenant', 'object': 'netscreen:netscreen:firewall'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object": "the entity identifier",
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

        # Data collections

        # component
        collection_name = "kv_trackme_dsm_tenant_" + str(tenant_id)
        collection = service.kvstore[collection_name]

        # sampling
        collection_sampling_name = "kv_trackme_dsm_data_sampling_tenant_" + str(
            tenant_id
        )
        collection_sampling = service.kvstore[collection_sampling_name]

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Get request info and set logger.level
        reqinfo = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )

        # try to get the KVrecord

        # check if we have a KVrecord already for this object
        query_string = {
            "$and": [
                {
                    "object": object,
                }
            ]
        }

        # record from the component
        try:
            # try get to get the key
            kvrecord = collection.data.query(query=(json.dumps(query_string)))[0]
            key = kvrecord.get("_key")
        except Exception as e:
            kvrecord = {}
            key = None

        # record from sampling
        try:
            # try get to get the key
            kvrecord_sampling = collection_sampling.data.query(
                query=(json.dumps(query_string))
            )[0]
            key_sampling = kvrecord_sampling.get("_key")
        except Exception as e:
            kvrecord_sampling = {}
            key_sampling = None

        # set the feature conditionally
        feature = ""
        if kvrecord_sampling:
            if kvrecord_sampling.get("data_sample_feature") == "enabled":
                feature = "🟢"
            elif kvrecord_sampling.get("data_sample_feature") == "disabled":
                feature = "🔴"
            elif kvrecord_sampling.get("data_sample_feature") == "disabled_auto":
                feature = "🟠"
            else:
                feature = "🟠"
        else:
            feature = "🟠"

        # set the state conditionally
        state = "⚫"

        #
        # system wide settings for data sampling
        #

        # Minimum time in seconds between two iterations of sampling per entity
        splk_data_sampling_min_time_btw_iterations_seconds = int(
            reqinfo["trackme_conf"]["splk_data_sampling"][
                "splk_data_sampling_min_time_btw_iterations_seconds"
            ]
        )

        # Min inclusive model matched percentage (float)
        splk_data_sampling_pct_min_major_inclusive_model_match = float(
            reqinfo["trackme_conf"]["splk_data_sampling"][
                "splk_data_sampling_pct_min_major_inclusive_model_match"
            ]
        )

        # Max exclusive model matched percentage (float)
        splk_data_sampling_pct_max_exclusive_model_match = float(
            reqinfo["trackme_conf"]["splk_data_sampling"][
                "splk_data_sampling_pct_max_exclusive_model_match"
            ]
        )

        # number of records to be sampled per entity
        splk_data_sampling_no_records_per_entity = int(
            reqinfo["trackme_conf"]["splk_data_sampling"][
                "splk_data_sampling_no_records_per_entity"
            ]
        )

        # The relative time window size in seconds
        splk_data_sampling_relative_time_window_seconds = int(
            reqinfo["trackme_conf"]["splk_data_sampling"][
                "splk_data_sampling_relative_time_window_seconds"
            ]
        )

        # if disabled
        if kvrecord_sampling.get("data_sample_feature") == "disabled":
            return {
                "payload": [
                    {
                        "anomaly_reason": "N/A",
                        "current_detected_format": ["N/A"],
                        "current_detected_major_format": "N/A",
                        "data_sample_anomaly_detected": "N/A",
                        "data_sample_feature": "disabled",
                        "data_sample_mtime": "N/A",
                        "data_sample_model_matched_summary": {},
                        "data_sample_status_colour": "N/A",
                        "data_sample_status_message": {
                            "state": "disabled",
                            "desc": "Data Sampling is currently disabled for this entity, it will not be processed",
                        },
                        "direction": "N/A",
                        "feature": feature,
                        "state": state,
                        "_key": kvrecord_sampling.get("_key", "N/A"),
                        "mtime": time.time(),
                        "multiformat": "N/A",
                        "object": kvrecord_sampling.get("object", "N/A"),
                        "previous_detected_format": ["N/A"],
                        "previous_detected_major_format": "N/A",
                        "min_time_btw_iterations_seconds": splk_data_sampling_min_time_btw_iterations_seconds,
                        "pct_min_major_inclusive_model_match": splk_data_sampling_pct_min_major_inclusive_model_match,
                        "pct_max_exclusive_model_match": splk_data_sampling_pct_max_exclusive_model_match,
                        "max_events_per_sampling_iteration": splk_data_sampling_no_records_per_entity,
                        "relative_time_window_seconds": splk_data_sampling_relative_time_window_seconds,
                    }
                ],
                "status": 200,
            }

        # if not ready yet
        elif not key_sampling:
            return {
                "payload": [
                    {
                        "anomaly_reason": "pending",
                        "current_detected_format": ["pending"],
                        "current_detected_major_format": "pending",
                        "data_sample_anomaly_detected": 0,
                        "data_sample_feature": "pending",
                        "data_sample_mtime": "pending",
                        "data_sample_model_matched_summary": {},
                        "data_sample_status_colour": "yellow",
                        "data_sample_status_message": {
                            "state": "pending",
                            "desc": "Data Sampling is pending and has not been performed yet for this entity",
                        },
                        "direction": "none",
                        "feature": "🟠",
                        "state": state,
                        "_key": key,
                        "mtime": "pending",
                        "multiformat": "false",
                        "object": object,
                        "previous_detected_format": ["pending"],
                        "previous_detected_major_format": "pending",
                        "min_time_btw_iterations_seconds": splk_data_sampling_min_time_btw_iterations_seconds,
                        "pct_min_major_inclusive_model_match": splk_data_sampling_pct_min_major_inclusive_model_match,
                        "pct_max_exclusive_model_match": splk_data_sampling_pct_max_exclusive_model_match,
                        "max_events_per_sampling_iteration": splk_data_sampling_no_records_per_entity,
                        "relative_time_window_seconds": splk_data_sampling_relative_time_window_seconds,
                    }
                ],
                "status": 200,
            }

        # otherwise
        else:

            # load list
            current_detected_format = kvrecord_sampling.get(
                "current_detected_format", ["N/A"]
            )

            # load list
            previous_detected_format = kvrecord_sampling.get(
                "previous_detected_format", ["N/A"]
            )

            # convert mtime
            try:
                mtime = time.strftime(
                    "%c",
                    time.localtime(float(kvrecord_sampling.get("data_sample_mtime"))),
                )
            except Exception as e:
                mtime = kvrecord_sampling.get("data_sample_mtime")

            # data_sample_anomaly_detected
            try:
                data_sample_anomaly_detected = kvrecord_sampling.get(
                    "data_sample_anomaly_detected"
                )
            except Exception as e:
                data_sample_anomaly_detected = 0

            # define state
            if data_sample_anomaly_detected == 0:
                state = "🟢"
            elif data_sample_anomaly_detected == 1:
                state = "🔴"
            elif data_sample_anomaly_detected == 2:
                state = "🟠"

            # get data_sample_model_matched_summary
            try:
                data_sample_model_matched_summary = kvrecord_sampling.get(
                    "data_sample_model_matched_summary"
                )
            except Exception as e:
                data_sample_model_matched_summary = {}

            # get data_sample_status_message
            try:
                data_sample_status_message = kvrecord_sampling.get(
                    "data_sample_status_message"
                )
            except Exception as e:
                data_sample_status_message = {}

            return {
                "payload": [
                    {
                        "anomaly_reason": kvrecord_sampling.get(
                            "data_sample_anomaly_reason"
                        ),
                        "current_detected_format": current_detected_format,
                        "current_detected_major_format": kvrecord_sampling.get(
                            "current_detected_major_format"
                        ),
                        "data_sample_anomaly_detected": kvrecord_sampling.get(
                            "data_sample_anomaly_detected"
                        ),
                        "data_sample_feature": kvrecord_sampling.get(
                            "data_sample_feature"
                        ),
                        "data_sample_mtime": kvrecord_sampling.get("data_sample_mtime"),
                        "data_sample_model_matched_summary": data_sample_model_matched_summary,
                        "data_sample_status_colour": kvrecord_sampling.get(
                            "data_sample_status_colour"
                        ),
                        "data_sample_status_message": data_sample_status_message,
                        "direction": "⬅",
                        "feature": feature,
                        "state": state,
                        "_key": kvrecord_sampling.get("_key"),
                        "mtime": mtime,
                        "multiformat": kvrecord_sampling.get("multiformat_detected"),
                        "object": kvrecord_sampling.get("object"),
                        "previous_detected_format": previous_detected_format,
                        "previous_detected_major_format": kvrecord_sampling.get(
                            "previous_detected_major_format"
                        ),
                        "min_time_btw_iterations_seconds": kvrecord_sampling.get(
                            "min_time_btw_iterations_seconds"
                        ),
                        "pct_min_major_inclusive_model_match": kvrecord_sampling.get(
                            "pct_min_major_inclusive_model_match"
                        ),
                        "pct_max_exclusive_model_match": kvrecord_sampling.get(
                            "pct_max_exclusive_model_match"
                        ),
                        "max_events_per_sampling_iteration": kvrecord_sampling.get(
                            "max_events_per_sampling_iteration"
                        ),
                        "relative_time_window_seconds": kvrecord_sampling.get(
                            "relative_time_window_seconds"
                        ),
                    }
                ],
                "status": 200,
            }

    # get manual tags
    def post_ds_get_manual_tags(self, request_info, **kwargs):
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
                "describe": "This endpoint returns the current manual_tags assigned to one or more DSM entities. It requires a POST call with tenant_id, action, and either object_list or keys_list to identify the target entities. The response is a list of {keyid, object, manual_tags} records, one per resolved entity.",
                "resource_desc": "Return the current manual_tags assigned to a list of DSM entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/ds_get_manual_tags\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'action': 'enable', 'object_list': 'netscreen:netscreen:firewall,wineventlog:WinEventLog'}\"",
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
        collection_name = "kv_trackme_dsm_tenant_" + str(tenant_id)
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
                manual_tags = kvrecord.get("manual_tags", [])
                # if manual_tags is defined, turn as a list from CSV
                if manual_tags:
                    manual_tags = manual_tags.split(",")
                return_records.append(
                    {
                        "keyid": key,
                        "object": kvrecord.get("object"),
                        "manual_tags": manual_tags,
                    }
                )
            except:
                pass

        # render
        return {"payload": return_records, "status": 200}
