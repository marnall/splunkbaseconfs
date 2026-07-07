#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_deleted_entities_power.py"
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
import threading

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_deleted_entities_power",
    "trackme_rest_api_splk_deleted_entities_power.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    extract_keys_list,
    trackme_audit_event,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_register_tenant_component_summary,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkDeletedEntitiesPower_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkDeletedEntitiesPower_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_deleted_entities(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_deleted_entities/write",
            "resource_group_desc": "Endpoints related to the management of deleted entities",
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

    # Remove object entities
    def post_remove_perm_deleted_entities(self, request_info, **kwargs):
        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                # get tenant_id
                tenant_id = resp_dict["tenant_id"]

                # get the component
                component = resp_dict.get("component", None)
                if not component:
                    return {
                        "payload": {
                            "error": "component must be provided, valid options are: dsm/dhm/mhm/wlk/flx/fqm"
                        },
                        "status": 500,
                    }
                elif component not in ("dsm", "dhm", "mhm", "wlk", "flx", "fqm"):
                    return {
                        "payload": {
                            "error": "Invalid option for component, valid options are: dsm/dhm/mhm/wlk/flx/fqm"
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
                "describe": "This endpoints allows removing permanently deleted entities records, it requires a POST call with the following information:",
                "resource_desc": "Delete permanently deleted entities records for a tenant/component",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_deleted_entities/write/remove_perm_deleted_entities\" mode=\"post\" body=\"{'tenant_id':'mytenant', 'component': 'dsm', 'object_list':'netscreen:netscreen:firewall,wineventlog:WinEventLog'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "Component identifier, valid options are: dsm/dhm/mhm/wlk/flx/fqm",
                        "object_list": "REQUIRED (with keys_list as alternative). Comma-separated list of entity object names. Either object_list or keys_list must be provided",
                        "keys_list": "REQUIRED (with object_list as alternative). Comma-separated list of entity KV record _keys. Either object_list or keys_list must be provided",
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

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # records summary
        records = []

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
        collection_name = (
            f"kv_trackme_common_permanently_deleted_objects_tenant_{tenant_id}"
        )
        collection = service.kvstore[collection_name]

        # loop and proceed
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
                # Remove the record
                kvrecord = collection.data.query(query=json.dumps({"_key": key}))[0]
                object = kvrecord.get("object")
                collection.data.delete(json.dumps({"_key": key}))

                # Record an audit change
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    request_info.user,
                    "success",
                    "remove permanently deleted entities ",
                    str(object),
                    "splk-deleted-entities",
                    str(json.dumps(kvrecord, indent=1)),
                    "Entity was deleted successfully",
                    str(update_comment),
                )

                # increment counter
                processed_count += 1
                succcess_count += 1
                failures_count += 0

                # append for summary
                result = {
                    "object": object,
                    "action": "delete",
                    "result": "success",
                    "message": f'tenant_id="{tenant_id}", The object was successfully deleted',
                }
                records.append(result)

            except Exception as e:
                # increment counter
                processed_count += 1
                succcess_count += 0
                failures_count += 1

                result = {
                    "object": object,
                    "action": "delete",
                    "result": "failure",
                    "exception": f'tenant_id="{tenant_id}", failed to remove the entity, object="{object}", exception="{str(e)}"',
                }
                records.append(result)

        # call trackme_register_tenant_component_summary
        thread = threading.Thread(
            target=self.register_component_summary_async,
            args=(
                request_info.session_key,
                request_info.server_rest_uri,
                tenant_id,
                component,
            ),
        )
        thread.start()

        # render HTTP status and summary

        req_summary = {
            "process_count": processed_count,
            "success_count": succcess_count,
            "failures_count": failures_count,
            "records": records,
        }

        if processed_count > 0 and processed_count == succcess_count:
            return {"payload": req_summary, "status": 200}

        else:
            return {"payload": req_summary, "status": 500}
