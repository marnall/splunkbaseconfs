#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_disruption_user.py"
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
import requests

splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_disruption_user", "trackme_rest_api_splk_disruption_user.log"
)

import trackme_rest_handler

# import trackme libs
from trackme_libs import extract_keys_list, trackme_getloglevel, trackme_parse_describe_flag

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkDisruptionRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkDisruptionRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_disruption(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_disruption",
            "resource_group_desc": "Endpoints specific to the splk-disruption TrackMe component (Disruption tracking, read-only operations).",
        }

        return {"payload": response, "status": 200}

    # Get disruption records
    def post_disruption_records(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_disruption/disruption_records" mode="post" body="{'tenant_id': 'mytenant', 'keys_list': ['key1', 'key2']}"
        """

        # init
        keys_list = None
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

                # handle keys_list
                keys_list = extract_keys_list(resp_dict)
                if keys_list:
                    if not isinstance(keys_list, list):
                        keys_list = keys_list.split(",")

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns disruption records. It requires a POST call with the following information:",
                "resource_desc": "Return disruption records, optionally filtered by a list of keys.",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_disruption/disruption_records\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'keys_list': ['key1', 'key2']}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "keys_list": "Optional list of keys to filter the records. If not provided, all records will be returned.",
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
        collection_name = "kv_trackme_common_disruption_queue_tenant_" + str(tenant_id)
        collection = service.kvstore[collection_name]

        # Define the KV query
        query_string = {}

        if keys_list:
            query_string["_key"] = {"$in": keys_list}

        # Get the records
        try:
            kvrecords = collection.data.query(query=json.dumps(query_string))
            response = {
                "action": "success",
                "response": "success",
                "records": kvrecords,
            }
            return {"payload": response, "status": 200}

        except Exception as e:
            logger.error(f"Error querying disruption records: {str(e)}")
            return {
                "payload": {
                    "action": "failure",
                    "response": f"Error querying disruption records: {str(e)}",
                },
                "status": 500,
            }
