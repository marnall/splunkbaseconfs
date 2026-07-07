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

logger = setup_logger("trackme.rest.ack_power", "trackme_rest_api_ack_power.log")


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


class TrackMeHandlerAckWriteOps_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerAckWriteOps_v2, self).__init__(command_line, command_arg, logger)

    def get_resource_group_desc_ack(self, request_info, **kwargs):
        response = {
            "resource_group_name": "ack",
            "resource_group_desc": "Acknowledgments allow silencing an entity alert for a given period of time automatically (write operations)",
        }

        return {"payload": response, "status": 200}

    def post_ack_manage(self, request_info, **kwargs):

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

                # the action, if not specified, show will be the default
                action = resp_dict.get("action", "show")
                if action not in ("show", "enable", "disable"):
                    # log error and return
                    error_msg = f'tenant_id="{tenant_id}", action="{action}", action is incorrect, valid options are show | enable | disable'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

                # object_list
                object_list = resp_dict.get("object_list", None)
                object_value_list = []

                # for action = show, if not set, will be defined to *
                # for action = enable/disable, if not set, will return an error

                if object_list is None:
                    if action == "show":
                        object_list = "*"
                    else:
                        error_msg = f'tenant_id="{tenant_id}", action="{action}", object_list is required'
                        logger.error(error_msg)
                        return {
                            "payload": {"action": "failure", "result": error_msg},
                            "status": 500,
                        }

                else:
                    # turn as a list
                    object_value_list = object_list.split(",")

                # object_category
                object_category_value = resp_dict["object_category"]

                # ack_period
                ack_period = resp_dict.get("ack_period", 86400)
                try:
                    ack_period = int(ack_period)
                except Exception as e:
                    # log error format and return error
                    error_msg = f'tenant_id="{tenant_id}", ack_period="{ack_period}", ack_period period is incorrect, an integer is expected, exception="{str(e)}"'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

                # ack_type is optional, if not set, will be defined to unsticky
                ack_type = resp_dict.get("ack_type", "unsticky")
                if not ack_type in ("sticky", "unsticky"):
                    # log error format and return error
                    error_msg = f'tenant_id="{tenant_id}", ack_type="{ack_type}", ack_type is incorrect, valid options are sticky | unsticky'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

                # ack_comment
                ack_comment = resp_dict.get("ack_comment", None)

                # anomaly_reason is optional, if not set, will be defined to N/A
                anomaly_reason = resp_dict.get("anomaly_reason", "N/A")

                # ack_source is optional, if not set, will be defined to user_ack
                ack_source = resp_dict.get("ack_source", "user_ack")

                if not ack_source in ("auto_ack", "user_ack"):
                    # log error format and return error
                    error_msg = f'tenant_id="{tenant_id}", ack_source="{ack_source}", ack_source is incorrect, valid options are auto_ack | user_ack'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint will enable/disable an acknowledgment for one or more entities, it requires a POST call with the following information:",
                "resource_desc": "Show/Enable/Disable/Update acknowledgement for a comma separated list of entities",
                "resource_spl_example": '| trackme url="/services/trackme/v2/ack/write/ack_manage" mode="post" body="{\'tenant_id\': \'mytenant\', '
                + "'action': 'enable', 'object_category': 'splk-dsm', 'object_list': 'netscreen:netscreen:firewall', 'ack_period': 86400, 'ack_comment': 'Under review'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "action": "The action to be performed, valid options are: enable | disable | show.",
                        "object_category": "the object category (splk-dsm, splk-dhm, splk-mhm, splk-flx, splk-wlk, splk-fqm)",
                        "object_list": "List of entities, in a comma separated format. If action=show and not set, will be defined to * to retrieve all Ack records, mandatory for action=enable/disable",
                        "ack_period": "Required if action=enable, the period for the acknowledgment in seconds",
                        "ack_type": "The type of Ack, valid options are sticky | unsticky, defaults to unsticky if not specified. Unsticky Ack are purged automatically when the entity goes back to a green state, while sticky Ack are purged only when the expiration is reached.",
                        "ack_comment": "Relevant if action=enable but optional, the acknowledgment comment to be added to the records",
                        "ack_source": "OPTIONAL: the source of the ack, if unset will be defined to: user_ack. Valid options are: auto_ack, user_ack",
                        "anomaly_reason": "OPTIONAL: the reason for the anomaly, if unset will be defined to: N/A",
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

        # ack_comment
        if ack_comment is None:
            ack_comment = update_comment

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # records summary
        records_summary = []

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

        # Component mapping
        component_mapping = {
            "splk-dsm": "dsm",
            "splk-dhm": "dhm",
            "splk-mhm": "mhm",
            "splk-flx": "flx",
            "splk-fqm": "fqm",
            "splk-wlk": "wlk",
        }

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
        if action == "show" and object_list == "*":
            return {
                "payload": {
                    "process_count": len(collection_records_list),
                    "records": collection_records_list,
                },
                "status": 200,
            }

        else:
            # action show
            if action == "show":
                for object_value in object_value_list:
                    if object_value in collection_records_objects:
                        # increment counter
                        processed_count += 1
                        succcess_count += 1
                        failures_count += 0

                        records_summary.append(
                            collection_records_objects_dict[object_value]
                        )

                    else:
                        # increment counter
                        processed_count += 1
                        succcess_count += 0
                        failures_count += 1

                        result = {
                            "object": object_value,
                            "action": "show",
                            "result": "failure",
                            "exception": f'tenant_id="{tenant_id}", the entity="{object_value}" could not be found in this tenant',
                        }
                        records_summary.append(result)

            # action enable
            elif action == "enable" or action == "disable":
                if action == "enable":
                    ack_state = "active"
                    ack_expiration = time.time() + ack_period
                else:
                    ack_state = "inactive"
                    ack_expiration = 0
                    ack_type = "N/A"

                for object_value in object_value_list:

                    ack_record = {
                        "object": object_value,
                        "object_category": object_category_value,
                        "anomaly_reason": anomaly_reason,
                        "ack_source": ack_source,
                        "ack_expiration": ack_expiration,
                        "ack_state": ack_state,
                        "ack_mtime": time.time(),
                        "ack_type": ack_type,
                        "ack_comment": ack_comment,
                    }

                    # only for enable, on a per object and if anomaly_reason is not set
                    if action == "enable":
                        # if action is enable, and anomaly_reason is not set, attempt to connect to the data KV and retrieve the actual anomaly_reason
                        if anomaly_reason == "N/A":

                            try:
                                collection_data_name = f"kv_trackme_{component_mapping.get(object_category_value, None)}_tenant_{tenant_id}"
                                collection_data = service.kvstore[collection_data_name]
                                data_kvrecord = collection_data.data.query(
                                    query=json.dumps({"object": object_value})
                                )[0]
                                ack_record["anomaly_reason"] = data_kvrecord.get(
                                    "anomaly_reason", "N/A"
                                )

                            except Exception as e:
                                error_msg = f'tenant_id="{tenant_id}", while attempting to retrieve the anomaly_reason in the data KVstore {collection_data_name} an exception was encountered, exception="{str(e)}"'
                                logger.error(error_msg)

                    try:
                        if object_value in collection_records_objects:
                            # Update the record
                            collection.data.update(
                                collection_records_objects_dict[object_value]["_key"],
                                json.dumps(ack_record),
                            )
                        else:
                            collection.data.insert(json.dumps(ack_record))

                        # increment counter
                        processed_count += 1
                        succcess_count += 1
                        failures_count += 0

                        result = {
                            "object": object_value,
                            "action": action,
                            "result": "success",
                            "ack_record": ack_record,
                        }
                        records_summary.append(result)

                        # set audit message depending on the action (enable / disable)
                        if action == "enable":
                            audit_msg = "The Ack was enabled successfully"
                        elif action == "disable":
                            audit_msg = "The Ack was disabled successfully"

                        # audit
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "success",
                            f"{action} ack",
                            str(object_value),
                            str(object_category_value),
                            ack_record,
                            audit_msg,
                            str(update_comment),
                        )

                    except Exception as e:
                        # increment counter
                        processed_count += 1
                        succcess_count += 0
                        failures_count += 1

                        result = {
                            "object": object_value,
                            "action": "enable",
                            "result": "failure",
                            "exception": f'tenant_id="{tenant_id}", the entity="{object_value}" could not be updated, exception="{str(e)}"',
                        }
                        records_summary.append(result)

                        # set audit message depending on the action (enable / disable)
                        if action == "enable":
                            audit_msg = (
                                f"The Ack could not be enabled, exception={str(e)}"
                            )
                        elif action == "disable":
                            audit_msg = (
                                f"The Ack could not be disabled, exception={str(e)}"
                            )

                        # audit
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "failure",
                            f"{action} ack",
                            str(object_value),
                            str(object_category_value),
                            ack_record,
                            audit_msg,
                            str(update_comment),
                        )

            # render HTTP status and summary
            req_summary = {
                "process_count": processed_count,
                "success_count": succcess_count,
                "failures_count": failures_count,
                "records": records_summary,
            }

            if processed_count > 0 and processed_count == succcess_count:
                http_status = 200
            else:
                http_status = 500

            return {"payload": req_summary, "status": http_status}
