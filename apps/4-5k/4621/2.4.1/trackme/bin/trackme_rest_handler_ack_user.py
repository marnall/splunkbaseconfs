#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_ack.py"
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
import time

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger("trackme.rest.ack_user", "trackme_rest_api_ack_user.log")


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    trackme_audit_event,
    trackme_getloglevel,
    trackme_parse_describe_flag,
)

from trackme_libs_ack import (
    get_all_ack_records_from_kvcollection,
    convert_epoch_to_datetime,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerAckReadOps_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerAckReadOps_v2, self).__init__(command_line, command_arg, logger)

    def get_resource_group_desc_ack(self, request_info, **kwargs):
        response = {
            "resource_group_name": "ack",
            "resource_group_desc": "Acknowledgments allow silencing an entity alert for a given period of time automatically (read-only operations)",
        }

        return {"payload": response, "status": 200}


    def post_get_ack_for_object(self, request_info, **kwargs):

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
                # tenant_id is required
                tenant_id = resp_dict.get("tenant_id", None)
                if tenant_id is None:
                    error_msg = f'tenant_id="{tenant_id}", tenant_id is required'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

                # object_list
                object_list = resp_dict.get("object_list", None)
                object_value_list = []

                if object_list is None:
                    object_list = "*"

                else:
                    # turn as a list
                    object_value_list = object_list.split(",")

                # object_category
                object_category_value = resp_dict["object_category"]

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves the Ack record for one or more objects. It requires a POST call with the following information:",
                "resource_desc": "Get acknowledgement for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/ack/get_ack_for_object\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'object_category': 'splk-dsm', 'object_list': 'netscreen:netscreen:firewall'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_category": "the object category (splk-dsm, splk-dhm, splk-mhm, splk-flx, splk-wlk, splk-fqm)",
                        "object_list": "List of entities, in a comma separated format. Use * to retrieve all objects, defaults to * if not specified",
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

        collection_name = f"kv_trackme_common_alerts_ack_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # get the whole collection
        try:
            (
                collection_records_list,
                collection_records_keys,
                collection_records_objects,
                collection_records_objects_dict,
                collection_records_keys_dict,
            ) = get_all_ack_records_from_kvcollection(
                collection_name, collection, object_category_value
            )

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failed to retrieve KVstore collection records using function get_all_records_from_kvcollection, exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {"action": "failure", "result": error_msg},
                "status": 500,
            }

        # if action is show and object_list is *, return all records
        filtered_records = []

        if object_list == "*":
            for record in collection_records_list:
                # convert ack_mtime to ack_mtime_datetime
                ack_mtime_datetime = convert_epoch_to_datetime(record.get("ack_mtime"))
                record["ack_mtime_datetime"] = ack_mtime_datetime

                # convert ack_expiration to ack_expiration_datetime
                ack_expiration_datetime = convert_epoch_to_datetime(
                    record.get("ack_expiration")
                )
                record["ack_expiration_datetime"] = ack_expiration_datetime

                # create a new field called ack_is_enabled which is a boolean 0/1 depending on if the ack_state is active or inactive
                if record.get("ack_state") == "active":
                    record["ack_is_enabled"] = 1
                else:
                    record["ack_is_enabled"] = 0

                # field anomaly_reason is optional, if not set, will be defined to N/A, if set it is a comma separated string to be turned into a list
                anomaly_reason = record.get("anomaly_reason", None)
                if not anomaly_reason:
                    record["anomaly_reason"] = "N/A"
                else:
                    if not isinstance(anomaly_reason, list):
                        record["anomaly_reason"] = anomaly_reason.split(",")

                # field ack_source is optional, if not set, will be defined to user_ack
                ack_source = record.get("ack_source", "user_ack")
                record["ack_source"] = ack_source

                filtered_records.append(record)

            return {
                "payload": filtered_records,
                "status": 200,
            }

        else:
            filtered_records = []
            for object_value in object_value_list:
                if object_value in collection_records_objects:
                    record = collection_records_objects_dict[object_value]

                    # convert ack_mtime to ack_mtime_datetime
                    ack_mtime_datetime = convert_epoch_to_datetime(
                        record.get("ack_mtime")
                    )
                    record["ack_mtime_datetime"] = ack_mtime_datetime

                    # convert ack_expiration to ack_expiration_datetime
                    if record.get("ack_expiration") != 0:
                        ack_expiration_datetime = convert_epoch_to_datetime(
                            record.get("ack_expiration")
                        )
                    else:
                        ack_expiration_datetime = "N/A"
                    record["ack_expiration_datetime"] = ack_expiration_datetime

                    # create a new field called ack_is_enabled which is a boolean 0/1 depending on if the ack_state is active or inactive
                    if record.get("ack_state") == "active":
                        record["ack_is_enabled"] = 1
                    else:
                        record["ack_is_enabled"] = 0

                    # field anomaly_reason is optional, if not set, will be defined to N/A, if set it is a comma separated string to be turned into a list
                    anomaly_reason = record.get("anomaly_reason", None)
                    if not anomaly_reason:
                        record["anomaly_reason"] = "N/A"
                    else:
                        if not isinstance(anomaly_reason, list):
                            record["anomaly_reason"] = anomaly_reason.split(",")

                    # field ack_source is optional, if not set, will be defined to user_ack
                    ack_source = record.get("ack_source", "user_ack")
                    record["ack_source"] = ack_source

                    filtered_records.append(record)

            return {
                "payload": filtered_records,
                "status": 200,
            }
