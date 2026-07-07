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
import time
import threading
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
    "trackme.rest.splk_mhm_power",
    "trackme_rest_api_splk_mhm_power.log",
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
    trackme_vtenant_account_from_service,
)

# import trackme libs get data
from trackme_libs_get_data import (
    batch_find_records_by_object,
    batch_find_records_by_key,
)

# import trackme libs persistent fields definition
from collections_data import (
    persistent_fields_mhm,
)

# import trackme libs bulk edit
from trackme_libs_bulk_edit import post_bulk_edit, generic_batch_update
from trackme_libs_shadow import delete_shadow_records

# Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkMhmWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkMhmWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_mhm(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_mhm/write",
            "resource_group_desc": "Endpoints specific to the splk-mhm TrackMe component (Splunk Metric Hosts monitoring, power operations)",
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

    # Bulk edit (to be used from the inline Tabulator)
    def post_mh_bulk_edit(self, request_info, **kwargs):
        """
        This function performs a bulk edit on given json data.
        :param request_info: Contains request related information
        :param kwargs: Other keyword arguments
        :return: Status and payload of the bulk edit operation
        """

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

        # call the bulkd edit function
        response, http_status = post_bulk_edit(
            self,
            log=logger,
            loglevel=loglevel,
            service=service,
            request_info=request_info,
            component_name="mhm",
            persistent_fields=persistent_fields_mhm,
            collection_name_suffix="mhm",
            endpoint_suffix="mhm",
            function_name="mh_bulk_edit",
            **kwargs,
        )

        return {
            "payload": response,
            "status": http_status,
        }

    # Reset metrics by object name
    def post_mh_reset(self, request_info, **kwargs):
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
                "describe": "This endpoint resets (removal of indexes and metrics knowledge) an existing metric host by the metric host name (object), it requires a POST call with the following information:",
                "resource_desc": "Reset sourcetypes knowledge for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_mhm/write/mh_reset\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'object_list': 'key:env|splunk'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
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
        collection_name = f"kv_trackme_mhm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "mhm",
            "object_list": object_list,
            "keys_list": keys_list,
        }

        # Prepare the update fields
        update_fields = {
            "metric_category": "",
            "metric_details": "{}",
            "metric_details_full": "{}",
            "metric_details_compact": "{}",
            "metric_details_minimal": "{}",
            "metric_index": "",
        }

        # Call the generic update function
        response, status_code = generic_batch_update(
            self,
            request_info,
            update_request_info=update_request_info,
            collection=collection,
            update_fields=update_fields,
            persistent_fields=persistent_fields_mhm,
            component="mhm",
            update_comment=update_comment,
            audit_context="Reset data",
            audit_message="Data was reset successfully",
        )

        return {"payload": response, "status": status_code}

    # Update priority by object name
    def post_mh_update_priority(self, request_info, **kwargs):
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

                priority = resp_dict["priority"]
                if priority not in ("low", "medium", "high", "critical", "pending"):
                    return {
                        "payload": f"Invalid option for priority with priority received: {priority}, valid options are: low | medium | high | critical | pending",
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint updates the priority definition for an existing metric host, it requires a POST call with the following information:",
                "resource_desc": "Update priority for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_mhm/write/mh_update_priority\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'priority': 'high', 'object_list': 'key:env|splunk'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_list": "REQUIRED (with keys_list as alternative). Comma-separated list of entity object names. Either object_list or keys_list must be provided",
                        "keys_list": "REQUIRED (with object_list as alternative). Comma-separated list of entity KV record _keys. Either object_list or keys_list must be provided",
                        "priority": "priority value, valid options are low / medium / high / critical / pending",
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
        collection_name = f"kv_trackme_mhm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "mhm",
            "object_list": object_list,
            "keys_list": keys_list,
        }

        # Prepare the update fields
        update_fields = {"priority": priority, "priority_updated": 1}

        # Call the generic update function
        response, status_code = generic_batch_update(
            self,
            request_info,
            update_request_info=update_request_info,
            collection=collection,
            update_fields=update_fields,
            persistent_fields=persistent_fields_mhm,
            component="mhm",
            update_comment=update_comment,
            audit_context="update priority",
            audit_message="Priority was updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Enable/Disable monitoring by object name
    def post_mh_monitoring(self, request_info, **kwargs):
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
                        "payload": f"Invalid option for action, valid options are: enable | disable {str(e)}",
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
                "describe": "This endpoint enables data monitoring for an existing data source by the entity name (object), it requires a POST call with the following information:",
                "resource_desc": "Enable/Disable monitoring for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_mhm/write/mh_monitoring\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'action': 'disable', 'object_list': 'key:env|splunk'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_list": "REQUIRED (with keys_list as alternative). Comma-separated list of entity object names. Either object_list or keys_list must be provided",
                        "keys_list": "REQUIRED (with object_list as alternative). Comma-separated list of entity KV record _keys. Either object_list or keys_list must be provided",
                        "action": "The action to be performed, valid options are: enable | disable",
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
        collection_name = f"kv_trackme_mhm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "mhm",
            "object_list": object_list,
            "keys_list": keys_list,
        }

        # Prepare the update fields
        update_fields = {"monitored_state": action_value}

        # Call the generic update function
        response, status_code = generic_batch_update(
            self,
            request_info,
            update_request_info=update_request_info,
            collection=collection,
            update_fields=update_fields,
            persistent_fields=persistent_fields_mhm,
            component="mhm",
            update_comment=update_comment,
            audit_context="update monitoring",
            audit_message="Monitoring state was updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Remove entities
    def post_mh_delete(self, request_info, **kwargs):
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

                deletion_type = resp_dict["deletion_type"]
                if deletion_type not in ("temporary", "permanent"):
                    return {
                        "payload": {
                            "error": "Invalid option for deletion_type, valid options are: tempoary | permanent"
                        },
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint performs a permanent or temporary deletion of entities, it requires a POST call with the following information:",
                "resource_desc": "Delete one or more entities, either temporarily or permanently",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_mhm/write/mh_delete\" mode=\"post\" body=\"{'tenant_id':'mytenant', 'deletion_type': 'temporary', 'object_list':'key:env|splunk'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_list": "REQUIRED (with keys_list as alternative). Comma-separated list of entity object names. Either object_list or keys_list must be provided",
                        "keys_list": "REQUIRED (with object_list as alternative). Comma-separated list of entity KV record _keys. Either object_list or keys_list must be provided",
                        "deletion_type": "The type of deletion, valid options are: temporary | permanent",
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
        collection_name = f"kv_trackme_mhm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Permanently deleted objects
        collection_perm_deleted_name = (
            f"kv_trackme_common_permanently_deleted_objects_tenant_{tenant_id}"
        )
        collection_perm_deleted = service.kvstore[collection_perm_deleted_name]

        # Convert comma-separated lists to Python lists if needed
        if isinstance(object_list, str):
            object_list = object_list.split(",")
        if isinstance(keys_list, str):
            keys_list = keys_list.split(",")

        # Determine query method based on input
        if object_list:
            kvrecords_dict, kvrecords = batch_find_records_by_object(
                collection, object_list
            )
        elif keys_list:
            kvrecords_dict, kvrecords = batch_find_records_by_key(collection, keys_list)
        else:
            return {
                "payload": {
                    "error": "either object_list or keys_list must be provided"
                },
                "status": 500,
            }

        # Extract all keys and object values for batched operations
        BATCH_CHUNK_SIZE = 250
        deleted_keys = []
        deleted_objects = []
        deleted_records = []

        # Batch delete main entities using $or queries (chunked, per-chunk error handling)
        for i in range(0, len(kvrecords), BATCH_CHUNK_SIZE):
            chunk = kvrecords[i : i + BATCH_CHUNK_SIZE]
            chunk_keys = [r.get("_key") for r in chunk]
            try:
                collection.data.delete(
                    json.dumps({"$or": [{"_key": k} for k in chunk_keys]})
                )
                # Entire chunk succeeded
                for kvrecord in chunk:
                    deleted_keys.append(kvrecord.get("_key"))
                    deleted_objects.append(kvrecord.get("object"))
                    deleted_records.append(kvrecord)
                    processed_count += 1
                    succcess_count += 1
                    records.append(
                        {
                            "object": kvrecord.get("object"),
                            "action": "delete",
                            "result": "success",
                            "message": f'tenant_id="{tenant_id}", The object "{kvrecord.get("object")}" was successfully deleted',
                        }
                    )
            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", batch chunk delete failed, falling back to per-entity deletion, exception="{str(e)}"'
                )
                # Fallback to per-entity deletion for this chunk only
                for kvrecord in chunk:
                    key = kvrecord.get("_key")
                    object_value = kvrecord.get("object")
                    try:
                        collection.data.delete(json.dumps({"_key": key}))
                        deleted_keys.append(key)
                        deleted_objects.append(object_value)
                        deleted_records.append(kvrecord)
                        processed_count += 1
                        succcess_count += 1
                        records.append(
                            {
                                "object": object_value,
                                "action": "delete",
                                "result": "success",
                                "message": f'tenant_id="{tenant_id}", The object "{object_value}" was successfully deleted',
                            }
                        )
                    except Exception as e2:
                        processed_count += 1
                        failures_count += 1
                        records.append(
                            {
                                "object": object_value,
                                "action": "delete",
                                "result": "failure",
                                "exception": f'tenant_id="{tenant_id}", failed to remove the entity, object="{object_value}", exception="{str(e2)}"',
                            }
                        )

        # Handle permanent deletion - batch register permanently deleted objects (only for successfully deleted)
        if deletion_type == "permanent" and deleted_objects:
            existing_objects = set()
            for i in range(0, len(deleted_objects), BATCH_CHUNK_SIZE):
                chunk_objects = deleted_objects[i : i + BATCH_CHUNK_SIZE]
                try:
                    existing_perm = collection_perm_deleted.data.query(
                        query=json.dumps(
                            {
                                "$or": [
                                    {"object": obj, "object_category": "splk-mhm"}
                                    for obj in chunk_objects
                                ]
                            }
                        )
                    )
                    existing_objects.update(r["object"] for r in existing_perm)
                except Exception:
                    pass

            for obj in deleted_objects:
                if obj not in existing_objects:
                    try:
                        collection_perm_deleted.data.insert(
                            json.dumps(
                                {
                                    "ctime": str(time.time()),
                                    "object": str(obj),
                                    "object_category": "splk-mhm",
                                }
                            )
                        )
                    except Exception as e:
                        logger.error(
                            f'tenant_id="{tenant_id}", failed to register a new permanently deleted object, object="{obj}", exception="{str(e)}"'
                        )

        # Batch audit events in a single REST call (only for successfully deleted)
        if deleted_records:
            audit_events = []
            for record in deleted_records:
                audit_events.append(
                    {
                        "action": "success",
                        "change_type": f"delete {deletion_type}",
                        "object": str(record.get("object")),
                        "object_category": "splk-mhm",
                        "object_attrs": str(json.dumps(record, indent=1)),
                        "user": request_info.user,
                        "result": "Entity was deleted successfully",
                        "comment": str(update_comment),
                    }
                )
            try:
                header = {
                    "Authorization": "Splunk %s" % request_info.system_authtoken,
                    "Content-Type": "application/json",
                }
                url = "%s/services/trackme/v2/audit/audit_events_v2" % request_info.server_rest_uri
                data = {"tenant_id": str(tenant_id), "audit_events": audit_events}
                response = requests.post(url, headers=header, data=json.dumps(data), verify=False, timeout=600)
                if not response.ok:
                    logger.error(
                        f'tenant_id="{tenant_id}", batch audit event failed, status_code={response.status_code}, response="{response.text}"'
                    )
            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", failed to generate audit events, exception="{str(e)}"'
                )

        # Remove deleted entities from shadow collection (non-blocking)
        if deleted_keys:
            # Retrieve shadow_enabled before entering thread closure
            try:
                vtenant_conf = trackme_vtenant_account_from_service(service, tenant_id)
                shadow_enabled = int(vtenant_conf.get("shadow_enabled", 0))
            except Exception:
                shadow_enabled = None

            def _delete_shadow():
                try:
                    service_system = client.connect(
                        token=request_info.system_authtoken,
                        owner="nobody",
                        app="trackme",
                        port=request_info.server_rest_port,
                        timeout=120,
                    )
                    delete_shadow_records(service_system, tenant_id, "mhm", deleted_keys, shadow_enabled=shadow_enabled)
                except Exception as e:
                    logger.error(
                        f'tenant_id="{tenant_id}", failed to delete shadow records, exception="{str(e)}"'
                    )
            shadow_thread = threading.Thread(target=_delete_shadow, daemon=True)
            shadow_thread.start()

        # call trackme_register_tenant_component_summary
        thread = threading.Thread(
            target=self.register_component_summary_async,
            args=(
                request_info.session_key,
                request_info.server_rest_uri,
                tenant_id,
                "mhm",
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

    # Update list of manual tags
    def post_mh_update_manual_tags(self, request_info, **kwargs):
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

                try:
                    tags_manual = resp_dict["tags_manual"]
                    # if is a list, deduplicate, make it lowercase, sort it and turn as a CSV string
                    if isinstance(tags_manual, list):
                        tags_manual = ",".join(
                            sorted(list(set([x.lower() for x in tags_manual])))
                        )
                    else:
                        # if is a string, split it, deduplicate, make it lowercase, sort it and turn as a CSV string
                        tags_manual = ",".join(
                            sorted(
                                list(set([x.lower() for x in tags_manual.split(",")]))
                            )
                        )

                except Exception as e:
                    return {
                        "payload": {
                            "error": "tags_manual must be provided as a comma separated list of tags"
                        },
                        "status": 500,
                    }

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint allows defining a comma separated list of manual tags, it requires a POST call with the following information:",
                "resource_desc": "Define a comma separated list of tags for one or more entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_mhm/write/mh_update_manual_tags\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'tags_manual': 'mytag1,maytag2,mytag3', 'object_list': 'netscreen:netscreen:firewall,wineventlog:WinEventLog'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_list": "REQUIRED (with keys_list as alternative). Comma-separated list of entity object names. Either object_list or keys_list must be provided",
                        "keys_list": "REQUIRED (with object_list as alternative). Comma-separated list of entity KV record _keys. Either object_list or keys_list must be provided",
                        "tags_manual": "A comma separated list of tags to be applied to the entities, to purge all manual tags, send an empty string",
                        "operation": "OPTIONAL: operation mode - 'replace' (default, replaces all manual tags), 'add' (adds tags to existing), 'remove' (removes specified tags)",
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
        collection_name = f"kv_trackme_mhm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Tags policies collection
        collection_tags_policies_name = f"kv_trackme_mhm_tags_tenant_{tenant_id}"
        collection_tags_policies = service.kvstore[collection_tags_policies_name]

        # Store original tags_manual input before loop to prevent mutation issues
        original_tags_manual = tags_manual
        # Get operation mode (default: "replace" for backward compatibility)
        operation = resp_dict.get("operation", "replace")

        # loop and proceed
        if object_list:
            keys_list = []
            for object_value in object_list:
                try:
                    kvrecord = collection.data.query(
                        query=json.dumps({"object": object_value})
                    )[0]
                    key = kvrecord.get("_key")
                    keys_list.append(key)
                except Exception as e:
                    key = None

        for key in keys_list:
            try:
                kvrecord = collection.data.query(query=json.dumps({"_key": key}))[0]

                # check if we have tags policies already
                try:
                    kvrecord_tags_policies = collection_tags_policies.data.query(
                        query=json.dumps({"_key": key})
                    )[0]
                except Exception as e:
                    kvrecord_tags_policies = None

                # check if we have tags_auto (list)
                try:
                    tags_auto = kvrecord_tags_policies.get("tags_auto", [])
                except Exception as e:
                    tags_auto = []

                # Update the record
                object_value = kvrecord.get("object")
                tags = kvrecord.get("tags", None)  # get current tags

                # if we have tags, the format is CSV, turn into a list
                if tags:
                    tags = tags.split(",")

                # Get existing tags_manual before updating
                existing_tags_manual = kvrecord.get("tags_manual", "")
                existing_tags_manual_list = existing_tags_manual.split(",") if existing_tags_manual else []
                # Filter out empty strings
                existing_tags_manual_list = [x for x in existing_tags_manual_list if x]

                # Process tags_manual based on operation using original input (not mutated)
                original_tags_manual_list = original_tags_manual.split(",") if original_tags_manual else []
                original_tags_manual_list = [x for x in original_tags_manual_list if x]  # Filter out empty strings

                if operation == "add":
                    # Merge: combine existing and new tags, deduplicate (lowercase before deduplication for case-insensitive matching)
                    all_tags = list(set([x.lower() for x in existing_tags_manual_list + original_tags_manual_list if x]))
                    tags_manual = ",".join(sorted(all_tags))
                elif operation == "remove":
                    # Remove: filter out tags to remove
                    original_tags_manual_list_lower = [x.lower() for x in original_tags_manual_list]
                    remaining_tags = [x for x in existing_tags_manual_list if x.lower() not in original_tags_manual_list_lower]
                    tags_manual = ",".join(sorted([x.lower() for x in remaining_tags if x]))
                else:  # "replace" (default)
                    # Replace: use new tags as-is (current behavior)
                    tags_manual = original_tags_manual  # Use original input

                # update the record with our manual tags
                kvrecord["tags_manual"] = tags_manual

                # make tags_manual_list (list from tags_manual CSV) for merging with tags_auto
                tags_manual_list = tags_manual.split(",") if tags_manual else []
                tags_manual_list = [x for x in tags_manual_list if x]  # Filter out empty strings

                # merged them all: define the tags field as the deduplicated, lowercase and sorted list of tags based on the tags_auto and tags_manual_list
                tags = ",".join(
                    sorted(
                        list(
                            set([x.lower() for x in tags_auto + tags_manual_list if x])
                        )
                    )
                )
                # update tags in the kvrecord now
                kvrecord["tags"] = tags
                kvrecord["mtime"] = time.time()
                collection.data.update(str(key), json.dumps(kvrecord))

                # Record an audit change
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    request_info.user,
                    "success",
                    "update manual tags",
                    str(object_value),
                    "splk-mhm",
                    {"tags_manual": tags_manual_list},
                    "Manual tags list was updated successfully",
                    str(update_comment),
                )

                # increment counter
                processed_count += 1
                succcess_count += 1
                failures_count += 0

                # append for summary
                result = {
                    "object": object_value,
                    "action": "update",
                    "result": "success",
                    "message": f'tenant_id="{tenant_id}", The object was successfully updated',
                }
                records.append(result)

            except Exception as e:
                # increment counter
                processed_count += 1
                succcess_count += 0
                failures_count += 1

                result = {
                    "object": object_value,
                    "action": "update",
                    "result": "failure",
                    "exception": f'tenant_id="{tenant_id}", failed to update the entity, object="{object_value}", exception="{str(e)}"',
                }
                records.append(result)

        # call trackme_register_tenant_component_summary
        thread = threading.Thread(
            target=self.register_component_summary_async,
            args=(
                request_info.session_key,
                request_info.server_rest_uri,
                tenant_id,
                "mhm",
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

    # Update monitoring time policy and rules by object name
    def post_mh_update_monitoring_time(self, request_info, **kwargs):
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

                # Get monitoring_time_policy (optional)
                monitoring_time_policy = resp_dict.get("monitoring_time_policy", None)
                
                # Get monitoring_time_rules (optional, takes precedence over policy)
                monitoring_time_rules = resp_dict.get("monitoring_time_rules", None)

                # Validate that at least one is provided
                if not monitoring_time_policy and not monitoring_time_rules:
                    return {
                        "payload": {
                            "error": "either monitoring_time_policy or monitoring_time_rules must be provided"
                        },
                        "status": 500,
                    }

                # Validate monitoring_time_rules format if provided
                if monitoring_time_rules is not None:
                    if isinstance(monitoring_time_rules, str):
                        try:
                            monitoring_time_rules = json.loads(monitoring_time_rules)
                        except Exception as e:
                            return {
                                "payload": {
                                    "error": f"monitoring_time_rules must be a valid JSON object, error: {str(e)}"
                                },
                                "status": 500,
                            }
                    
                    if not isinstance(monitoring_time_rules, dict):
                        return {
                            "payload": {
                                "error": "monitoring_time_rules must be a dictionary with week day keys (0-6) and hour lists as values"
                            },
                            "status": 500,
                        }
                    
                    # Validate each day entry
                    for day_key, hours_list in monitoring_time_rules.items():
                        try:
                            day_int = int(day_key)
                            if day_int < 0 or day_int > 6:
                                return {
                                    "payload": {
                                        "error": f"monitoring_time_rules: day key must be 0-6 (Sunday-Saturday), got {day_int}"
                                    },
                                    "status": 500,
                                }
                        except (ValueError, TypeError):
                            return {
                                "payload": {
                                    "error": f"monitoring_time_rules: day key must be an integer 0-6, got {day_key}"
                                },
                                "status": 500,
                            }
                        
                        if not isinstance(hours_list, list):
                            return {
                                "payload": {
                                    "error": f"monitoring_time_rules: hours for day {day_key} must be a list"
                                },
                                "status": 500,
                            }
                        
                        # Validate hours (0-23, with optional decimals like 0.5, 0.25)
                        for hour in hours_list:
                            try:
                                hour_float = float(hour)
                                if hour_float < 0 or hour_float >= 24:
                                    return {
                                        "payload": {
                                            "error": f"monitoring_time_rules: hours must be between 0-23.99, got {hour_float}"
                                        },
                                        "status": 500,
                                    }
                                # Check for valid decimal increments (0.25, 0.5, 0.75)
                                if hour_float != int(hour_float):
                                    decimal_part = hour_float - int(hour_float)
                                    if decimal_part not in [0.25, 0.5, 0.75]:
                                        return {
                                            "payload": {
                                                "error": f"monitoring_time_rules: decimal hours must be .25, .5, or .75, got {hour_float}"
                                            },
                                            "status": 500,
                                        }
                            except (ValueError, TypeError):
                                return {
                                    "payload": {
                                        "error": f"monitoring_time_rules: hour value must be numeric, got {hour}"
                                    },
                                    "status": 500,
                                }

                # Validate monitoring_time_policy format if provided
                if monitoring_time_policy is not None:
                    valid_policies = [
                        "all_time",
                        "business_days_all_hours",
                        "monday_saturday_all_hours",
                        "business_days_08h_20h",
                        "monday_saturday_08h_20h",
                    ]
                    
                    # Check if it's a string/list of predefined rules
                    if isinstance(monitoring_time_policy, str):
                        if monitoring_time_policy not in valid_policies:
                            # Try to parse as JSON (might be dictionary format)
                            try:
                                monitoring_time_policy = json.loads(monitoring_time_policy)
                            except Exception:
                                return {
                                    "payload": {
                                        "error": f"monitoring_time_policy must be one of {valid_policies} or a valid JSON dictionary"
                                    },
                                    "status": 500,
                                }
                    elif isinstance(monitoring_time_policy, list):
                        # Validate all items in list are valid policies
                        for policy in monitoring_time_policy:
                            if policy not in valid_policies:
                                return {
                                    "payload": {
                                        "error": f"monitoring_time_policy list contains invalid policy: {policy}, valid options are {valid_policies}"
                                    },
                                    "status": 500,
                                }
                    elif isinstance(monitoring_time_policy, dict):
                        # Dictionary format is allowed (same as monitoring_time_rules)
                        pass
                    else:
                        return {
                            "payload": {
                                "error": "monitoring_time_policy must be a string, list of strings, or dictionary"
                            },
                            "status": 500,
                        }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint configures the monitoring time policy and rules for an existing metric host, it requires a POST call with the following information:",
                "resource_desc": "Update monitoring time policy/rules for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_mhm/write/mh_update_monitoring_time\" mode=\"post\" body=\"{'tenant_id':'mytenant','object_list':'key:env|splunk','monitoring_time_policy':'business_days_08h_20h'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_list": "REQUIRED (with keys_list as alternative). Comma-separated list of entity object names. Either object_list or keys_list must be provided",
                        "keys_list": "REQUIRED (with object_list as alternative). Comma-separated list of entity KV record _keys. Either object_list or keys_list must be provided",
                        "monitoring_time_policy": "OPTIONAL: predefined policy name (all_time, business_days_all_hours, monday_saturday_all_hours, business_days_08h_20h, monday_saturday_08h_20h) or dictionary format like monitoring_time_rules",
                        "monitoring_time_rules": "OPTIONAL: dictionary with week day keys (0-6 for Sunday-Saturday) and hour lists as values, e.g. {0: [8,9,10], 1: [8,9,10]}. Hours can be 0-23 or decimals like 0.5 (00:30), 0.25 (00:15), 0.75 (00:45). Takes precedence over monitoring_time_policy if both provided.",
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
        collection_name = f"kv_trackme_mhm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "mhm",
            "object_list": object_list,
            "keys_list": keys_list,
        }

        # Prepare the update fields
        # monitoring_time_rules takes precedence over monitoring_time_policy
        update_fields = {}
        if monitoring_time_rules is not None:
            # Convert dict keys to strings if they're integers (for JSON serialization)
            if isinstance(monitoring_time_rules, dict):
                monitoring_time_rules = {str(k): v for k, v in monitoring_time_rules.items()}
            update_fields["monitoring_time_rules"] = json.dumps(monitoring_time_rules) if isinstance(monitoring_time_rules, dict) else monitoring_time_rules
        if monitoring_time_policy is not None:
            if isinstance(monitoring_time_policy, dict):
                monitoring_time_policy = {str(k): v for k, v in monitoring_time_policy.items()}
            update_fields["monitoring_time_policy"] = json.dumps(monitoring_time_policy) if isinstance(monitoring_time_policy, (dict, list)) else monitoring_time_policy

        # Call the generic update function
        response, status_code = generic_batch_update(
            self,
            request_info,
            update_request_info=update_request_info,
            collection=collection,
            update_fields=update_fields,
            persistent_fields=persistent_fields_mhm,
            component="mhm",
            update_comment=update_comment,
            audit_context="update monitoring time policy/rules",
            audit_message="Monitoring time policy/rules were updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Update SLA class
    def post_mh_update_sla_class(self, request_info, **kwargs):
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

                try:
                    sla_class = resp_dict["sla_class"]
                except Exception as e:
                    return {
                        "payload": {"error": "sla_class must be provided"},
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint updates the SLA class per entity, it requires a POST call with the following information:",
                "resource_desc": "Update SLA class for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_mhm/write/mh_update_sla_class\" mode=\"post\" body=\"{'tenant_id':'mytenant','object_list':'netscreen:netscreen:firewall','sla_class':'gold'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_list": "REQUIRED (with keys_list as alternative). Comma-separated list of entity object names. Either object_list or keys_list must be provided",
                        "keys_list": "REQUIRED (with object_list as alternative). Comma-separated list of entity KV record _keys. Either object_list or keys_list must be provided",
                        "sla_class": "(required) The SLA class to be applied to the entities",
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
        collection_name = f"kv_trackme_mhm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "mhm",
            "object_list": object_list,
            "keys_list": keys_list,
        }

        # Prepare the update fields
        update_fields = {
            "sla_class": sla_class,
        }

        # Call the generic update function
        response, status_code = generic_batch_update(
            self,
            request_info,
            update_request_info=update_request_info,
            collection=collection,
            update_fields=update_fields,
            persistent_fields=persistent_fields_mhm,
            component="mhm",
            update_comment=update_comment,
            audit_context="update SLA class",
            audit_message="SLA class was updated successfully",
        )

        return {"payload": response, "status": status_code}
