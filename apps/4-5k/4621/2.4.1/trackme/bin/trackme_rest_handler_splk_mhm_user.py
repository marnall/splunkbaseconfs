#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_mhm.py"
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
    "trackme.rest.splk_mhm_user",
    "trackme_rest_api_splk_mhm_user.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_getloglevel, trackme_parse_describe_flag

# TrackMe splk-feeds libs
from trackme_libs_splk_feeds import (
    splk_mhm_return_entity_info,
    splk_mhm_return_searches,
)

# Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkMhmRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkMhmRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_mhm(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_mhm",
            "resource_group_desc": "Endpoints specific to the splk-mhm TrackMe component (Splunk Metric Hosts monitoring, read-only operations).",
        }

        return {"payload": response, "status": 200}

    # Get entity info
    def post_mh_entity_info(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_mhm/mh_entity_info" mode="post" body="{'tenant_id': 'mytenant', 'object': 'key:env|splunk'}"
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_mhm/mh_entity_info\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'object': 'remote|account:lab|firewall.pan.amer.design.node1'}\"",
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
        collection_name = "kv_trackme_mhm_tenant_" + str(tenant_id)
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
                entity_info = splk_mhm_return_entity_info(kvrecord)

                # Add
                response["entity_info"] = entity_info

                # log debug
                logger.debug(
                    f'function splk_mhm_return_entity_info, entity_info="{json.dumps(entity_info, indent=2)}"'
                )

                # Add to dict
                entity_info["index"] = kvrecord.get("metric_index")
                entity_info["metric_category"] = kvrecord.get("metric_category")

                # set the search constraint
                if entity_info["breakby_key"] != "none":
                    entity_info["search_constraint"] = (
                        "index IN ("
                        + kvrecord.get("metric_index")
                        + ") "
                        + entity_info["breakby_key"]
                        + "="
                        + '"'
                        + entity_info["breakby_value"]
                        + '"'
                    )
                else:
                    entity_info["search_constraint"] = (
                        "index IN ("
                        + kvrecord.get("metric_index")
                        + ") "
                        + 'host="'
                        + str(object_value)
                        + '"'
                    )

                # get entity searches
                entity_searches = splk_mhm_return_searches(
                    tenant_id, object_value, entity_info
                )

                # log debug
                logger.debug(
                    f'function splk_mhm_return_searches, entity_searches="{json.dumps(entity_searches, indent=2)}"'
                )

                # add
                entity_info["splk_mhm_mctalog_search"] = entity_searches.get(
                    "splk_mhm_mctalog_search"
                )
                entity_info["splk_mhm_mctalog_search_litsearch"] = entity_searches.get(
                    "splk_mhm_mctalog_search_litsearch"
                )
                entity_info["splk_mhn_metrics_report"] = entity_searches.get(
                    "splk_mhn_metrics_report"
                )
                entity_info["splk_mhn_metrics_report_litsearch"] = entity_searches.get(
                    "splk_mhn_metrics_report_litsearch"
                )
                entity_info["splk_mhn_mpreview"] = entity_searches.get(
                    "splk_mhn_mpreview"
                )
                entity_info["splk_mhn_mpreview_litsearch"] = entity_searches.get(
                    "splk_mhn_mpreview_litsearch"
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
    def post_mhm_get_table(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_mhm/mhm_get_table\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'key_id': '*', 'object': '*'}\"",
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
            "component": "mhm",
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
