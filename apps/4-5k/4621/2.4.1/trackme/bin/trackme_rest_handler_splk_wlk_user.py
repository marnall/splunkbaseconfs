#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_wlk_user.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import os
import sys
import json
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
    "trackme.rest.splk_wlk_user",
    "trackme_rest_api_splk_wlk_user.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import extract_keys_list, trackme_getloglevel, trackme_idx_for_tenant, trackme_parse_describe_flag

# TrackMe splk-wlk libs
from trackme_libs_splk_wlk import splk_wlk_return_searches

# import trackme libs decisionmaker
from trackme_libs_decisionmaker import convert_epoch_to_datetime

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkWlkRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkWlkRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_wlk(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_wlk",
            "resource_group_desc": "Endpoints specific to the splk-wlk TrackMe component (Splunk Workload, read only operations)",
        }

        return {"payload": response, "status": 200}

    # get the component table
    def post_wlk_get_table(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_wlk/wlk_get_table\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'key_id': '*', 'object': '*'}\"",
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
            "component": "wlk",
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
    def post_wlk_tracker_show(self, request_info, **kwargs):
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
                "describe": "This endpoint retrieves all records for the hybrid tracker collection, it requires a POST call with the following information:",
                "resource_desc": "Get Hybrid trackers",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_wlk/wlk_tracker_show\" body=\"{'tenant_id': 'mytenant'}\"",
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
        seen_tracker_names = set()  # Track seen tracker_names for deduplication

        try:
            # Data collection
            collection_name = "kv_trackme_wlk_hybrid_trackers_tenant_" + str(tenant_id)
            collection = service.kvstore[collection_name]

            for entity in collection.data.query():
                tracker_name = entity.get("tracker_name")
                
                # Skip if we've already seen this tracker_name
                if tracker_name in seen_tracker_names:
                    continue
                
                # Add tracker_name to seen set
                seen_tracker_names.add(tracker_name)
                knowledge_objects = entity.get("knowledge_objects")
                # try to load as a json
                try:
                    knowledge_objects = json.loads(knowledge_objects)
                except Exception as e:
                    knowledge_objects = {}

                # get the live definition
                ko_json = {}
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
    def post_wlk_entity_info(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_wlk/wlk_entity_info" mode="post" body="{'tenant_id': 'mytenant', 'object': 'Okta:Splunk_TA_okta_identity_cloud:okta_logs'}"
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_wlk/wlk_entity_info\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'object': 'remote|account:lab|firewall.pan.amer.design.node1'}\"",
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
        collection_name = "kv_trackme_wlk_tenant_" + str(tenant_id)
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

                # get tenant metric index
                tenant_indexes = trackme_idx_for_tenant(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                )
                tenant_trackme_metric_idx = tenant_indexes.get("trackme_metric_idx", "trackme_metrics")

                # get entity searches
                entity_searches = splk_wlk_return_searches(tenant_id, kvrecord, tenant_trackme_metric_idx=tenant_trackme_metric_idx)

                # log debug
                logger.debug(
                    f'function splk_wlk_return_searches, entity_searches="{json.dumps(entity_searches, indent=2)}"'
                )

                # add
                entity_info["splk_wlk_mctalog_search"] = entity_searches.get(
                    "splk_wlk_mctalog_search"
                )
                entity_info["splk_wlk_mctalog_search_litsearch"] = entity_searches.get(
                    "splk_wlk_mctalog_search_litsearch"
                )
                entity_info["splk_wlk_metrics_report"] = entity_searches.get(
                    "splk_wlk_metrics_report"
                )
                entity_info["splk_wlk_metrics_report_litsearch"] = entity_searches.get(
                    "splk_wlk_metrics_report_litsearch"
                )
                entity_info["splk_wlk_mpreview"] = entity_searches.get(
                    "splk_wlk_mpreview"
                )
                entity_info["splk_wlk_mpreview_litsearch"] = entity_searches.get(
                    "splk_wlk_mpreview_litsearch"
                )
                entity_info["splk_wlk_metrics_populate_search"] = entity_searches.get(
                    "splk_wlk_metrics_populate_search"
                )
                entity_info["splk_wlk_scheduler_skipping_search"] = entity_searches.get(
                    "splk_wlk_scheduler_skipping_search"
                )
                entity_info["splk_wlk_scheduler_errors_search"] = entity_searches.get(
                    "splk_wlk_scheduler_errors_search"
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

    # Get entity metadata versioning
    def post_wlk_entity_metadata(self, request_info, **kwargs):
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
                tenant_id = resp_dict["tenant_id"]
                try:
                    object_value = resp_dict["object"]
                except Exception as e:
                    object_value = None
                try:
                    object_id = resp_dict["object_id"]
                except Exception as e:
                    object_id = None
                
                # object or object_id must be provided, but not both
                if object_value and object_id:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "only object or object_id can be specified, not both",
                        },
                        "status": 500,
                    }
                if not object_value and not object_id:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "either object or object_id must be specified",
                        },
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns the versioning metadata information for a given entity, it requires a POST call with the following information:",
                "resource_desc": "Return the entity versioning metadata, active entities are automatically inspected and their metadata information are versioned over time",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_wlk/wlk_entity_metadata\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'object': 'search:admin:myreport'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object": "The entity identifier, you can specify the object or the object_id, but not both",
                        "object_id": "The entity key identifier (_key in KVstore), you can specify the object or the object_id, but not both",
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
        collection_name = "kv_trackme_wlk_versioning_tenant_" + str(tenant_id)
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
            
            # If we searched by object_id, get the object value for error messages
            if not object_value:
                object_value = kvrecord.get("object")

            # get the dict
            json_dict = json.loads(kvrecord.get("version_dict"))

            # Sort the dictionary by the "time_inspected_epoch" value in descending order
            sorted_json_dict = {
                k: v
                for k, v in sorted(
                    json_dict.items(),
                    key=lambda item: item[1]["time_inspected_epoch"],
                    reverse=True,
                )
            }

        except Exception as e:
            key = None
            identifier = object_id if object_id else object_value
            return {
                "payload": {
                    "response": f'The entity with identifier="{identifier}" was not found, this might be expected in some cases (acceleration searches, etc)',
                },
                "status": 404,
            }

        # proceed
        if key:
            # init
            response = {}

            try:
                # render response
                return {"payload": sorted_json_dict, "status": 200}

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

    # Get apps enablement
    def post_wlk_apps_enablement(self, request_info, **kwargs):
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

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns the list of apps and their enablement status, it requires a POST call with the following information:",
                "resource_desc": "Return apps enablement status, a disabled application name is not considered in the UI and for alerting purposes",
                "resource_spl_example": '| trackme url="/services/trackme/v2/splk_wlk/wlk_apps_enablement" mode="post" body="{\'tenant_id\': \'mytenant\'}"',
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
            token=request_info.session_key,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Data collection
        collection_name = "kv_trackme_wlk_apps_enablement_tenant_" + str(tenant_id)
        collection = service.kvstore[collection_name]

        # Get the current record
        # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

        try:
            kvrecords = collection.data.query()
        except Exception as e:
            kvrecords = []

        # Sort the kvrecords alphabetically by the value of "app"
        kvrecords_sorted = sorted(kvrecords, key=lambda x: x["app"])

        # return
        return {"payload": kvrecords_sorted, "status": 200}

    # get thresholds for a list of entities
    def post_wlk_get_thresholds(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_wlk/wlk_get_thresholds\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'object_list': 'entity1,entity2'}\"",
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
        collection_name = "kv_trackme_wlk_thresholds_tenant_" + str(tenant_id)
        collection = service.kvstore[collection_name]

        # loop and proceed
        return_records = []

        if object_list:
            # For WLK, object_list values are treated as object_id lookups
            keys_list = list(object_list)

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
            except Exception as e:
                logger.error(
                    f'failed to retrieve threshold records for object_id="{key}", exception="{str(e)}"'
                )

        # render
        return {"payload": return_records, "status": 200}
