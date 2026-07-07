#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_fqm.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Built-in libraries
import json
import os
import sys
import re
import time
import requests
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
    "trackme.rest.splk_fqm_user", "trackme_rest_api_splk_fqm_user.log"
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import extract_keys_list, run_splunk_search, trackme_getloglevel, trackme_idx_for_tenant, trackme_parse_describe_flag

# import TrackMe splk-fqm libs
from trackme_libs_splk_fqm import splk_fqm_return_searches

# import trackme libs utils
from trackme_libs_utils import decode_unicode

# import trackme decision maker
from trackme_libs_decisionmaker import convert_epoch_to_datetime

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkFqmTrackingRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkFqmTrackingRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_fqm(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_fqm",
            "resource_group_desc": "Endpoints specific to the splk-fqm TrackMe component (Splunk Flex objects tracking, read-only operations).",
        }

        return {"payload": response, "status": 200}

    # get dictionaries
    def post_fqm_get_dictionaries(self, request_info, **kwargs):
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
        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns every Field Quality Monitoring (FQM) data dictionary defined for the given tenant. Data dictionaries describe the expected field model — the union of fields each entity in the tenant should surface — and are referenced by FQM trackers when computing per-field quality scores. It requires a POST call with the following information:",
                "resource_desc": "Return every FQM data dictionary defined for a given tenant",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/fqm_get_dictionaries\" mode=\"post\" body=\"{'tenant_id': 'mytenant'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
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
        
        # Data collection
        collection_name = f"kv_trackme_fqm_data_dictionary_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]
        
        # Define the KV query
        query_string = {}

        # init dictionaries list
        dictionaries_list = []

        # Get the current records
        records = collection.data.query(query=json.dumps(query_string))

        # loop and proceed
        for record in records:
            dictionaries_list.append(record)

        # Return the records
        return {"payload": {"dictionaries": dictionaries_list}, "status": 200}

    # get the component table
    def post_fqm_get_table(self, request_info, **kwargs):
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
                "describe": "This endpoint retrieves the component table. It requires a POST call with the following options:",
                "resource_desc": "Get the entity table",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/fqm_get_table\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'key_id': '*', 'object': '*'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "key_id": "(Optional) The key ID. Do not specify this to match all entities",
                        "object": "(Optional) The entity name. Do not specify this to match all entities",
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
            "component": "fqm",
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

    # get all records
    def post_fqm_tracker_show(self, request_info, **kwargs):
        """
        | trackme mode=post url="/services/trackme/v2/splk_fqm/fqm_tracker_show" body="{'tenant_id': 'mytenant'}"
        """

        # Declare
        tenant_id = None
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

                # show_search, defaults to False
                show_search = resp_dict.get("show_search", False)
                if show_search in ("true", "True"):
                    show_search = True
                else:
                    show_search = False

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves all records for the hybrid tracker collection. It requires a POST call with the following information:",
                "resource_desc": "Get hybrid trackers",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_fqm/fqm_tracker_show\" body=\"{'tenant_id': 'mytenant'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "show_search": "Show the search definition for the tracker, in large environments and/or with many trackers this can cause UI performance issues. Defaults to False.",
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

        # Declare
        trackers_list = []
        seen_tracker_ids = set()  # Track seen tracker_ids for deduplication

        try:
            # Data collection
            collection_name = "kv_trackme_fqm_hybrid_trackers_tenant_" + str(tenant_id)
            collection = service.kvstore[collection_name]

            for entity in collection.data.query():
                tracker_id = entity.get("tracker_id")
                
                # Skip if we've already seen this tracker_id
                if tracker_id in seen_tracker_ids:
                    continue
                
                # Add tracker_id to seen set
                seen_tracker_ids.add(tracker_id)
                tracker_name = entity.get("tracker_name")
                knowledge_objects = entity.get("knowledge_objects")
                # try to load as a json
                try:
                    knowledge_objects = json.loads(knowledge_objects)
                except Exception as e:
                    knowledge_objects = {}

                # get the live definition
                ko_json = {}
                ko_json["reports"] = []
                ko_json["properties"] = {}

                if knowledge_objects:
                    reports_list = knowledge_objects.get("reports", [])
                    ko_json["reports"] = reports_list
                    for report_name in reports_list:

                        # _tracker only
                        if "_tracker" in report_name:
                            try:
                                savedsearch = service.saved_searches[report_name]
                                search_cron_schedule = savedsearch.content[
                                    "cron_schedule"
                                ]
                                search_earliest = savedsearch.content[
                                    "dispatch.earliest_time"
                                ]
                                search_latest = savedsearch.content[
                                    "dispatch.latest_time"
                                ]
                                ko_json["properties"][
                                    "cron_schedule"
                                ] = search_cron_schedule
                                ko_json["properties"]["earliest"] = search_earliest
                                ko_json["properties"]["latest"] = search_latest
                            except Exception as e:
                                logger.error(
                                    f'failed to get the savedsearch definition for the report="{report_name}", exception="{str(e)}"'
                                )

                        # _wrapper only (show search)
                        if show_search:
                            if "_wrapper" in report_name:
                                try:
                                    savedsearch = service.saved_searches[report_name]
                                    savedsearch_definition = savedsearch.content[
                                        "search"
                                    ]
                                    ko_json["properties"][
                                        "search"
                                    ] = savedsearch_definition
                                except Exception as e:
                                    logger.error(
                                        f'failed to get the savedsearch definition for the report="{report_name}", exception="{str(e)}"'
                                    )

                # add to the list
                trackers_list.append(
                    {
                        "tracker_id": tracker_id,
                        "tracker_name": tracker_name,
                        "knowledge_objects": ko_json,
                    }
                )

            return {"payload": trackers_list, "status": 200}

        except Exception as e:
            error_msg = f'An exception was encountered="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"response": error_msg}, "status": 500}

    # Get entity info
    def post_fqm_entity_info(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_fqm/fqm_entity_info" mode="post" body="{'tenant_id': 'mytenant', 'object': 'Okta:Splunk_TA_okta_identity_cloud:okta_logs'}"
        """

        # init
        object_id = None
        object_value = None
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
                "describe": "This endpoint returns various information related to the entity, it requires a POST call with the following information:",
                "resource_desc": "Return the entity main information, these normalized information are used to build dynamically the various queries through the user interfaces",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/fqm_entity_info\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'object': 'remote|account:lab|firewall.pan.amer.design.node1'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object": "The entity identifier, you can specify the object or the object_id, but not both",
                        "object_id": "The entity key identifier, you can specify the object or the object_id, but not both",
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
        collection_name = "kv_trackme_fqm_tenant_" + str(tenant_id)
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
                # entity_info
                entity_info = {}

                # get fqm_type
                fqm_type = kvrecord.get("fqm_type", "field")

                # get tenant metric index
                tenant_indexes = trackme_idx_for_tenant(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                )
                tenant_trackme_metric_idx = tenant_indexes.get("trackme_metric_idx", "trackme_metrics")

                # get entity searches
                entity_searches = splk_fqm_return_searches(tenant_id, fqm_type, kvrecord, tenant_trackme_metric_idx=tenant_trackme_metric_idx)

                # log debug
                logger.debug(
                    f'function splk_fqm_return_searches, entity_searches="{json.dumps(entity_searches, indent=2)}"'
                )

                # add
                entity_info["splk_fqm_mctalog_search"] = entity_searches.get(
                    "splk_fqm_mctalog_search"
                )
                entity_info["splk_fqm_mctalog_search_litsearch"] = entity_searches.get(
                    "splk_fqm_mctalog_search_litsearch"
                )
                entity_info["splk_fqm_metrics_report"] = entity_searches.get(
                    "splk_fqm_metrics_report"
                )
                entity_info["splk_fqm_metrics_report_litsearch"] = entity_searches.get(
                    "splk_fqm_metrics_report_litsearch"
                )
                entity_info["splk_fqm_mpreview"] = entity_searches.get(
                    "splk_fqm_mpreview"
                )
                entity_info["splk_fqm_mpreview_litsearch"] = entity_searches.get(
                    "splk_fqm_mpreview_litsearch"
                )
                entity_info["splk_fqm_metrics_populate_search"] = entity_searches.get(
                    "splk_fqm_metrics_populate_search"
                )
                entity_info["splk_fqm_chart_values_search"] = entity_searches.get(
                    "splk_fqm_chart_values_search"
                )
                entity_info["splk_fqm_chart_description_search"] = entity_searches.get(
                    "splk_fqm_chart_description_search"
                )
                entity_info["splk_fqm_chart_status_search"] = entity_searches.get(
                    "splk_fqm_chart_status_search"
                )
                entity_info["splk_fqm_table_summary_search"] = entity_searches.get(
                    "splk_fqm_table_summary_search"
                )
                entity_info["splk_fqm_table_summary_formated_search"] = entity_searches.get(
                    "splk_fqm_table_summary_formated_search"
                )
                entity_info["splk_fqm_metrics_success_overtime"] = entity_searches.get(
                    "splk_fqm_metrics_success_overtime"
                )
                entity_info["splk_fqm_search_sample_events"] = entity_searches.get(
                    "splk_fqm_search_sample_events"
                )
                entity_info["splk_fqm_search_sample_events_raw"] = entity_searches.get(
                    "splk_fqm_search_sample_events_raw"
                )
                entity_info["splk_fqm_search_sample_not_matching_regex_events"] = entity_searches.get(
                    "splk_fqm_search_sample_not_matching_regex_events"
                )
                entity_info["splk_fqm_search_sample_not_matching_regex_events_raw"] = entity_searches.get(
                    "splk_fqm_search_sample_not_matching_regex_events_raw"
                )

                # add object and key
                entity_info["object"] = object_value
                entity_info["key"] = key
                entity_info["fqm_type"] = fqm_type

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

    # get thresholds
    def post_fqm_get_thresholds(self, request_info, **kwargs):
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

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves thresholds for a given list of entities, it requires a POST call with the following information:",
                "resource_desc": "Retrieve thresholds for a given list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/fqm_get_thresholds\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'object_list': 'entity1,entity2'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_list": "List of object entities, provided as a comma separated list of fields, you can provide object_list or keys_list",
                        "keys_list": "List of key entities, provided as a comma separated list of fields, you can provide object_list or keys_list",
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
        collection_name = "kv_trackme_fqm_thresholds_tenant_" + str(tenant_id)
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
                kvrecords = collection.data.query(query=json.dumps({"object_id": key}))
                for kvrecord in kvrecords:

                    mtime = kvrecord.get("mtime")
                    if mtime:
                        mtime = convert_epoch_to_datetime(mtime)
                    else:
                        mtime = "N/A"

                    # Get score, default to 100 if not present (for backward compatibility)
                    score = kvrecord.get("score")
                    if score is None:
                        score = 100
                    else:
                        try:
                            score = int(score)
                        except (TypeError, ValueError):
                            score = 100
                    
                    return_records.append(
                        {
                            "_key": kvrecord.get("_key"),
                            "object_id": kvrecord.get("object_id"),
                            "metric_name": kvrecord.get("metric_name"),
                            "value": kvrecord.get("value"),
                            "operator": kvrecord.get("operator"),
                            "condition_true": kvrecord.get("condition_true"),
                            "mtime": mtime,
                            "comment": kvrecord.get("comment"),
                            "score": score,
                        }
                    )
            except:
                pass

        # render
        return {"payload": return_records, "status": 200}

    # Return the basis data dictionary for a given datamodel
    def post_fqm_return_data_dictionary(self, request_info, **kwargs):
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

                # from_name (string) - load the dictionary from an existing dictionary stored in the KVstore collection
                try:
                    from_name = resp_dict["from_name"]
                except Exception as e:
                    from_name = None

                # tenant_id (string) - the tenant id is required if from_name is specified
                tenant_id = None
                if from_name:
                    try:
                        tenant_id = resp_dict["tenant_id"]
                    except Exception as e:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'Invalid option for tenant_id="{tenant_id}", the tenant id is required if from_name is specified',
                            },
                            "status": 500,
                        }

                # datamodel (string, must not be empty unless from_name is specified)
                datamodel = None
                if not from_name:
                    try:
                        datamodel = resp_dict["datamodel"]
                        if not datamodel or len(datamodel) == 0:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'Invalid option for datamodel="{datamodel}", the name of the datamodel is required unless from_name is specified, example: "Authentication"',
                                },
                                "status": 500,
                            }
                    except Exception as e:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'Invalid option for datamodel="{datamodel}", the name of the datamodel is required unless from_name is specified, example: "Authentication"',
                            },
                            "status": 500,
                        }

                # recommended_fields (True/False, unused if from_name is specified)
                recommended_fields = False
                if not from_name:
                    try:
                        recommended_fields = resp_dict["recommended_fields"]
                        if not isinstance(recommended_fields, bool):
                            if recommended_fields not in ("true", "True", "false", "False"):
                                return {
                                    "payload": {
                                        "action": "failure",
                                        "response": f'Invalid option for recommended_fields="{recommended_fields}", valid choices are: true | false',
                                    },
                                    "status": 500,
                                }
                            if recommended_fields in ("true", "True"):
                                recommended_fields = True
                            elif recommended_fields in ("false", "False"):
                                recommended_fields = False
                    except Exception as e:
                        recommended_fields = False

                # allow_unknown (True/False, unused if from_name is specified)
                allow_unknown = False
                if not from_name:
                    try:
                        allow_unknown = resp_dict["allow_unknown"]
                        if not isinstance(allow_unknown, bool):
                            if allow_unknown not in ("true", "True", "false", "False"):
                                return {
                                    "payload": {
                                        "action": "failure",
                                        "response": f'Invalid option for allow_unknown="{allow_unknown}", valid choices are: true | false',
                                    },
                                    "status": 500,
                                }
                            if allow_unknown in ("true", "True"):
                                allow_unknown = True
                            elif allow_unknown in ("false", "False"):
                                allow_unknown = False
                    except Exception as e:
                        allow_unknown = False

                # allow_empty_or_missing (True/False, unused if from_name is specified)
                allow_empty_or_missing = False
                if not from_name:
                    try:
                        allow_empty_or_missing = resp_dict["allow_empty_or_missing"]
                        if not isinstance(allow_empty_or_missing, bool):
                            if allow_empty_or_missing not in ("true", "True", "false", "False"):
                                return {
                                    "payload": {
                                        "action": "failure",
                                        "response": f'Invalid option for allow_empty_or_missing="{allow_empty_or_missing}", valid choices are: true | false',
                                    },
                                    "status": 500,
                                }
                            if allow_empty_or_missing in ("true", "True"):
                                allow_empty_or_missing = True
                            elif allow_empty_or_missing in ("false", "False"):
                                allow_empty_or_missing = False
                    except Exception as e:
                        allow_empty_or_missing = False

                # output_mode (json/array, defaults to json)
                output_mode = "json"
                try:
                    output_mode = resp_dict["output_mode"]
                    if output_mode not in ("json", "array"):
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'Invalid option for output_mode="{output_mode}", valid choices are: json | array',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    output_mode = "json"

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns the basis data dictionary for a given datamodel, it requires a POST call with the following information:",
                "resource_desc": "Return the basis data dictionary for a given datamodel",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/fqm_return_data_dictionary\" mode=post body=\"{'datamodel': 'Authentication', 'recommended_fields': True, 'allow_unknown': False, 'allow_empty_or_missing': False}\"}",
                "options": [
                    {
                        "from_name": "Optional, the name of the dictionary to be used, if not specified a new dictionary will be generated.",
                        "tenant_id": "The tenant id is required if from_name is specified",
                        "datamodel": "The datamodel to be used for the simulation, this value will be used to generate the recommended fields. (unused if from_name is specified)",
                        "recommended_fields": "Optional, if true only recommended fields will be returned, if false all fields will be returned. (unused if from_name is specified)",
                        "allow_unknown": "Optional, if true unknown field values will be allowed, if false unknown field values will be considered as failures. (unused if from_name is specified)",
                        "allow_empty_or_missing": "Optional, if true empty or missing field values will be allowed, if false empty or missing field values will be considered as failures. (unused if from_name is specified)",
                        "output_mode": "Optional, the output format for the dictionary, valid options are: json | array (defaults to json)",
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

        # run the search and returns the data dictionary
        if from_name:
            search = f"| inputlookup trackme_fqm_data_dictionary_tenant_{tenant_id} where name=\"{from_name}\" | head 1 | table json_dict"
        else:
            search = f"| trackmefieldsqualitygendict datamodel={datamodel} show_only_recommended_fields={recommended_fields} allow_unknown={allow_unknown} allow_empty_or_missing={allow_empty_or_missing}"

        json_dict = None

        kwargs = {
            "earliest_time": "-5m",
            "latest_time": "now",
            "search_mode": "normal",
            "preview": False,
            "time_format": "%s",
            "output_mode": "json",
            "count": 0,
        }

        # run search
        try:
            reader = run_splunk_search(
                service,
                search,
                kwargs,
                24,
                5,
            )

            for item in reader:
                if isinstance(item, dict):
                    json_dict = item.get("json_dict")
                break

            if json_dict:
                # Handle output_mode
                if output_mode == "array":
                    try:
                        # Parse the JSON string to get the dictionary
                        if isinstance(json_dict, str):
                            dict_data = json.loads(json_dict)
                        else:
                            dict_data = json_dict
                        
                        # Convert dictionary to array format with required keys
                        array_result = []
                        for field_name, field_config in dict_data.items():
                            field_entry = {
                                "field_name": field_name,
                                "allow_unknown": field_config.get("allow_unknown"),
                                "allow_empty_or_missing": field_config.get("allow_empty_or_missing"),
                                "regex": field_config.get("regex")
                            }
                            array_result.append(field_entry)
                        
                        return {"payload": array_result, "status": 200}
                    except Exception as e:
                        return {"payload": {"action": "failure", "response": f"Failed to convert dictionary to array format: {str(e)}"}, "status": 500}
                else:
                    # Default JSON mode - return as is
                    return {"payload": json_dict, "status": 200}
            else:
                if from_name:
                    return {"payload": {"action": "failure", "response": f"No data dictionary found for from_name={from_name}"}, "status": 500}
                else:
                    return {"payload": {"action": "failure", "response": f"No data dictionary found for datamodel={datamodel}"}, "status": 500}

        except Exception as e:
            return {"payload": {"action": "failure", "response": str(e)}, "status": 500}

    # Return a recommended regex expression for a given field name
    def post_fqm_return_regex_expression(self, request_info, **kwargs):
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

                # field_name (string) - the field name to return the regex expression for
                field_name = None
                try:
                    field_name = resp_dict["field_name"]
                    # must not be empty
                    if not field_name or len(field_name) == 0:
                        return {
                            "payload": {"action": "failure", "response": f"Invalid option for field_name={field_name}, the field name is required"}, "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": f"Invalid option for field_name={field_name}, the field name is required"}, "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns a recommended regex expression for a given field name, it requires a POST call with the following information:",
                "resource_desc": "Return a recommended regex expression for a given field name",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/fqm_return_regex_expression\" mode=post body=\"{'field_name': 'action'}\"",
                "options": [
                    {
                        "field_name": "The field name to return the regex expression for",
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

        # run the search and returns the recommended regex expression
        search = f'| inputlookup trackme_cim_regex_v2 | where datamodel="*" | where field=\"{field_name}\" | table validation_regex'
        recommended_regex = None

        kwargs = {
            "earliest_time": "-5m",
            "latest_time": "now",
            "search_mode": "normal",
            "preview": False,
            "time_format": "%s",
            "output_mode": "json",
            "count": 0,
        }

        # run search
        try:
            reader = run_splunk_search(
                service,
                search,
                kwargs,
                24,
                5,
            )

            for item in reader:
                if isinstance(item, dict):
                    recommended_regex = item.get("validation_regex")
                break

            if recommended_regex:
                return {"payload": {"field_name": field_name, "regex": recommended_regex}, "status": 200}
            else:
                return {"payload": {"field_name": field_name, "regex": ".*"}, "status": 200}

        except Exception as e:
            return {"payload": {"action": "failure", "response": str(e)}, "status": 500}


    # Return dictionaries (list of dictionaries and trackers using them)
    def post_fqm_dictionaries_by_trackers(self, request_info, **kwargs):

        # Declare
        tenant_id = None
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

                # dictionary_name, optional (filter by dictionary name)
                dictionary_name = None
                try:
                    dictionary_name = resp_dict["dictionary_name"]
                    # must not be empty
                    if not dictionary_name or len(dictionary_name) == 0:
                        dictionary_name = None
                except Exception as e:
                    pass

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves all records for the hybrid tracker collection. It requires a POST call with the following information:",
                "resource_desc": "Get hybrid trackers",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_fqm/fqm_dictionaries_by_trackers\" body=\"{'tenant_id': 'mytenant', 'dictionary_name': 'mydictionary'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "dictionary_name": "Optional, filter by dictionary name",
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

        #
        # Get dictionaries
        #

        # Data collection
        dictionaries_collection_name = f"kv_trackme_fqm_data_dictionary_tenant_{tenant_id}"
        dictionaries_collection = service.kvstore[dictionaries_collection_name]
        
        # Define the KV query
        query_string = {}

        # init dictionaries dict
        dictionaries_dict = {}

        # Get the current records
        records = dictionaries_collection.data.query(query=json.dumps(query_string))

        # loop and proceed
        for record in records:
            dictionaries_dict[record["name"]] = {"trackers": []}
        logger.debug(f'tenant_id="{tenant_id}", dictionaries_dict="{json.dumps(dictionaries_dict, indent=2)}"')

        #
        # Get and inspect trackers
        #

        try:
            # Data collection
            collection_name = "kv_trackme_fqm_hybrid_trackers_tenant_" + str(tenant_id)
            collection = service.kvstore[collection_name]

            for entity in collection.data.query():
                tracker_name = entity.get("tracker_name")
                knowledge_objects = entity.get("knowledge_objects")
                # try to load as a json
                try:
                    knowledge_objects = json.loads(knowledge_objects)
                except Exception as e:
                    knowledge_objects = {}

                # get the live definition
                ko_json = {}
                ko_json["reports"] = []
                ko_json["properties"] = {}

                if knowledge_objects:
                    reports_list = knowledge_objects.get("reports", [])
                    ko_json["reports"] = reports_list
                    for report_name in reports_list:

                        # we only care about trackme_fqm_collect_*_wrapper_*
                        if "_wrapper" in report_name:
                            try:
                                savedsearch = service.saved_searches[report_name]
                                savedsearch_definition = savedsearch.content[
                                    "search"
                                ]

                                # check using a regular expression if we find the dictionary name in the search as:
                                # | inputlookup trackme_fqm_data_dictionary_tenant_{tenant_id} where name="<dictionary_name>" or name=<dictionary_name>
                                match = re.search(r'\| inputlookup trackme_fqm_data_dictionary_tenant_[^ ]+ where name=(?:"([^"]+)"|([^\s]+))', savedsearch_definition)
                                if match:
                                    matched_dictionary_name = match.group(1) or match.group(2)
                                    dictionaries_dict[matched_dictionary_name]["trackers"].append(tracker_name)

                            except Exception as e:
                                logger.error(
                                    f'failed to get the savedsearch definition for the report="{report_name}", exception="{str(e)}"'
                                )

            # if filtering by dictionary name, only the list of trackers associated to it
            # otherwise, return the whole dictionaries_dict
            logger.debug(f'tenant_id="{tenant_id}", dictionary_name="{dictionary_name}"')
            if dictionary_name:
                dictionaries_dict = {k: v for k, v in dictionaries_dict.items() if k == dictionary_name}

            # return
            return {"payload": dictionaries_dict, "status": 200}

        except Exception as e:
            error_msg = f'An exception was encountered="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"response": error_msg}, "status": 500}

    # Return dictionaries (list of dictionaries and sources using them)
    def post_fqm_dictionaries_by_sources(self, request_info, **kwargs):

        # Declare
        tenant_id = None
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

                # dictionary_name, optional (filter by dictionary name)
                dictionary_name = None
                try:
                    dictionary_name = resp_dict["dictionary_name"]
                    # must not be empty
                    if not dictionary_name or len(dictionary_name) == 0:
                        dictionary_name = None
                except Exception as e:
                    pass

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves all records for the hybrid tracker collection and extracts sources from the collect commands. It requires a POST call with the following information:",
                "resource_desc": "Get sources by dictionaries",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_fqm/fqm_dictionaries_by_sources\" body=\"{'tenant_id': 'mytenant', 'dictionary_name': 'mydictionary'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "dictionary_name": "Optional, filter by dictionary name",
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

        #
        # Get dictionaries
        #

        # Data collection
        dictionaries_collection_name = f"kv_trackme_fqm_data_dictionary_tenant_{tenant_id}"
        dictionaries_collection = service.kvstore[dictionaries_collection_name]
        
        # Define the KV query
        query_string = {}

        # init dictionaries dict
        dictionaries_dict = {}

        # Get the current records
        records = dictionaries_collection.data.query(query=json.dumps(query_string))

        # loop and proceed
        for record in records:
            dictionaries_dict[record["name"]] = {"sources": []}
        logger.debug(f'tenant_id="{tenant_id}", dictionaries_dict="{json.dumps(dictionaries_dict, indent=2)}"')

        #
        # Get and inspect trackers
        #

        try:
            # Data collection
            collection_name = "kv_trackme_fqm_hybrid_trackers_tenant_" + str(tenant_id)
            collection = service.kvstore[collection_name]

            for entity in collection.data.query():
                tracker_name = entity.get("tracker_name")
                knowledge_objects = entity.get("knowledge_objects")
                # try to load as a json
                try:
                    knowledge_objects = json.loads(knowledge_objects)
                except Exception as e:
                    knowledge_objects = {}

                # get the live definition
                ko_json = {}
                ko_json["reports"] = []
                ko_json["properties"] = {}

                if knowledge_objects:
                    reports_list = knowledge_objects.get("reports", [])
                    ko_json["reports"] = reports_list
                    for report_name in reports_list:

                        # we only care about trackme_fqm_collect_*_wrapper_*
                        if "_wrapper" in report_name:
                            try:
                                savedsearch = service.saved_searches[report_name]
                                savedsearch_definition = savedsearch.content[
                                    "search"
                                ]

                                # check using a regular expression if we find the dictionary name in the search as:
                                # | inputlookup trackme_fqm_data_dictionary_tenant_{tenant_id} where name="<dictionary_name>" or name=<dictionary_name>
                                match = re.search(r'\| inputlookup trackme_fqm_data_dictionary_tenant_[^ ]+ where name=(?:"([^"]+)"|([^\s]+))', savedsearch_definition)
                                if match:
                                    matched_dictionary_name = match.group(1) or match.group(2)
                                    
                                    # Extract source from collect command
                                    # Look for pattern: | collect index=summary sourcetype=trackme:fields_quality source="trackme:quality:authentication-wineventlog_cf927"
                                    source_match = re.search(r'\| collect[^|]*source=(?:"([^"]+)"|([^\s]+))', savedsearch_definition)
                                    if source_match:
                                        source_value = source_match.group(1) or source_match.group(2)
                                        if source_value not in dictionaries_dict[matched_dictionary_name]["sources"]:
                                            dictionaries_dict[matched_dictionary_name]["sources"].append(source_value)

                            except Exception as e:
                                logger.error(
                                    f'failed to get the savedsearch definition for the report="{report_name}", exception="{str(e)}"'
                                )

            # if filtering by dictionary name, only the list of sources associated to it
            # otherwise, return the whole dictionaries_dict
            logger.debug(f'tenant_id="{tenant_id}", dictionary_name="{dictionary_name}"')
            if dictionary_name:
                dictionaries_dict = {k: v for k, v in dictionaries_dict.items() if k == dictionary_name}

            # return
            return {"payload": dictionaries_dict, "status": 200}

        except Exception as e:
            error_msg = f'An exception was encountered="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"response": error_msg}, "status": 500}
