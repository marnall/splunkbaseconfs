#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_disruption_power.py"
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
import threading

splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_disruption_power", "trackme_rest_api_splk_disruption_power.log"
)

import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    extract_keys_list,
    trackme_audit_event,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_register_tenant_component_summary,
    trackme_reqinfo,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# import trackme libs audit
from trackme_libs_audit import trackme_audits_callback

# Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkDisruptionWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkDisruptionWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_disruption(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_disruption/write",
            "resource_group_desc": "Endpoints specific to the splk-disruption TrackMe component (Disruption tracking, power operations).",
        }

        return {"payload": response, "status": 200}

    def register_component_summary_async(
        self, session_key, splunkd_uri, tenant_id, component
    ):
        try:
            summary_register_response = trackme_register_tenant_component_summary(
                session_key,
                splunkd_uri,
                tenant_id,
                component,
            )
            logger.debug(
                f'function="trackme_register_tenant_component_summary", response="{json.dumps(summary_register_response, indent=2)}"'
            )
        except Exception as e:
            logger.error(
                f'failed to register the component summary with exception="{str(e)}"'
            )

    # Update disruption min time
    def post_disruption_update_min_time(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_disruption/write/disruption_update_min_time" mode="post" body="{'tenant_id': 'mytenant', 'keys_list': ['key1', 'key2'], 'disruption_min_time_sec': 300}"
        """

        # init
        keys_list = None
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
                    component = resp_dict["component"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "the component is required",
                        },
                        "status": 500,
                    }
                if component not in ("dsm", "dhm", "mhm", "flx", "wlk", "fqm"):
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f"the component {component} is invalid, valid components are: dsm, dhm, mhm, flx, wlk, fqm",
                        },
                        "status": 400,
                    }

                # handle keys_list
                keys_list = extract_keys_list(resp_dict)
                if keys_list:
                    if not isinstance(keys_list, list):
                        keys_list = keys_list.split(",")
                else:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "the keys_list is required",
                        },
                        "status": 500,
                    }

                # handle disruption_min_time_sec
                try:
                    if "disruption_min_time_sec" not in resp_dict:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": "the disruption_min_time_sec parameter is required",
                            },
                            "status": 400,
                        }

                    disruption_min_time_sec = resp_dict["disruption_min_time_sec"]
                    try:
                        disruption_min_time_sec = int(disruption_min_time_sec)
                    except ValueError:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": "the disruption_min_time_sec must be a valid integer",
                            },
                            "status": 400,
                        }

                    if disruption_min_time_sec < 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": "the disruption_min_time_sec must be 0 (to disable) or a positive integer",
                            },
                            "status": 400,
                        }
                except (ValueError, TypeError):
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "the disruption_min_time_sec must be a valid integer",
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint updates the minimum disruption time for given records. It requires a POST call with the following information:",
                "resource_desc": "Update the minimum disruption time for given records. If a record does not exist, it will be created.",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_disruption/write/disruption_update_min_time\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'keys_list': ['key1', 'key2'], 'disruption_min_time_sec': 300}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component identifier",
                        "keys_list": "List of keys to update. Required.",
                        "disruption_min_time_sec": "Minimum disruption time in seconds. Required.",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Update comment is optional and used for audit changes
        update_comment = resp_dict.get("update_comment") or "API update"

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

        # Disruption collection
        collection_name = f"kv_trackme_common_disruption_queue_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Data collection
        collection_data_name = f"kv_trackme_{component}_tenant_{tenant_id}"
        collection_data = service.kvstore[collection_data_name]

        # Process each key
        updated_records = []
        created_records = []
        failed_records = []
        audit_dict = {}  # Dictionary to track changes for audit

        for key in keys_list:
            try:
                # Try to get existing record
                query = {"_key": key}
                existing_records = collection.data.query(query=json.dumps(query))

                if existing_records:
                    # Update existing record
                    record = existing_records[0]
                    old_value = record.get("disruption_min_time_sec")
                    record["disruption_min_time_sec"] = disruption_min_time_sec
                    record["mtime"] = time.time()
                    collection.data.update(key, record)
                    updated_records.append(key)

                    # Track changes for audit
                    if old_value != disruption_min_time_sec:
                        audit_dict[key] = [
                            {
                                "field": "disruption_min_time_sec",
                                "old_value": old_value,
                                "new_value": disruption_min_time_sec,
                            }
                        ]
                else:
                    # Create new record
                    new_record = {
                        "_key": key,
                        "object_state": "green",
                        "disruption_min_time_sec": disruption_min_time_sec,
                        "disruption_start_epoch": 0,
                        "mtime": time.time(),
                    }
                    collection.data.insert(new_record)
                    created_records.append(key)
                    # Track creation for audit
                    audit_dict[key] = []

            except Exception as e:
                logger.error(f"Error processing key {key}: {str(e)}")
                failed_records.append(key)

        # Generate audit events
        audits_events_list = []
        audit_status = "success" if not failed_records else "failure"
        audit_message = (
            "Entity was updated successfully"
            if not failed_records
            else "Entity update has failed"
        )

        # Audit for updated records
        for key in updated_records:
            if audit_dict.get(key):  # only generate audit if there were actual changes
                # Get the entity from the data collection
                query = {"_key": key}
                entity_record = collection_data.data.query(query=json.dumps(query))[0]
                audits_events_list.append(
                    {
                        "tenant_id": tenant_id,
                        "action": audit_status,
                        "user": request_info.user,
                        "change_type": "inline update",
                        "object_id": key,
                        "object": entity_record.get("object"),
                        "object_category": entity_record.get("object_category"),
                        "object_attrs": json.dumps(audit_dict.get(key)),
                        "result": f"{audit_status}: {audit_message}",
                        "comment": str(update_comment),
                    }
                )

        # Audit for created records
        for key in created_records:
            # Get the entity from the data collection
            query = {"_key": key}
            entity_record = collection_data.data.query(query=json.dumps(query))[0]
            # Create audit attributes for new record showing change from 0
            create_audit_attrs = [
                {
                    "field": "disruption_min_time_sec",
                    "old_value": 0,
                    "new_value": disruption_min_time_sec,
                }
            ]
            audits_events_list.append(
                {
                    "tenant_id": tenant_id,
                    "action": audit_status,
                    "user": request_info.user,
                    "change_type": "create",
                    "object_id": key,
                    "object": entity_record.get("object"),
                    "object_category": entity_record.get("object_category"),
                    "object_attrs": json.dumps(create_audit_attrs),
                    "result": f"{audit_status}: Record was created successfully",
                    "comment": str(update_comment),
                }
            )

        # Call trackme_audits_callback
        try:
            audit_response = trackme_audits_callback(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                json.dumps(audits_events_list),
            )
            logger.info(
                f'trackme_audits_callback was called successfully, tenant_id="{tenant_id}", audits_events="{audits_events_list}", audit_response="{audit_response}"'
            )
        except Exception as e:
            logger.error(
                f'Function trackme_audits_callback has failed, exception="{str(e)}"'
            )

        # Register component summary update
        try:
            thread = threading.Thread(
                target=self.register_component_summary_async,
                args=(
                    request_info.session_key,
                    request_info.server_rest_uri,
                    tenant_id,
                    entity_record.get("object_category"),
                ),
            )
            thread.start()
        except Exception as e:
            logger.error(f"Error starting component summary update thread: {str(e)}")

        # Return response
        response = {
            "action": "success",
            "response": "success",
            "updated_records": updated_records,
            "created_records": created_records,
            "failed_records": failed_records,
        }

        return {"payload": response, "status": 200}
