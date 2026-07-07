#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_flx.py"
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
import hashlib
import uuid
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
    "trackme.rest.splk_flx_power", "trackme_rest_api_splk_flx_power.log"
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
    persistent_fields_flx,
)

# import trackme libs bulk edit
from trackme_libs_bulk_edit import post_bulk_edit, generic_batch_update
from trackme_libs_shadow import delete_shadow_records

# import batched KV upsert helper (used to bulk-seed tracker-discovered records)
from trackme_libs_kvstore_batch import batch_update_worker

# import trackme libs utils
from trackme_libs_utils import interpret_boolean

# import trackme libs splk flx
from trackme_libs_splk_flx import normalize_flx_tracker_name

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkFlxTrackingWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkFlxTrackingWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_flx(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_flx/write",
            "resource_group_desc": "Endpoints specific to the splk-flx TrackMe component (Splunk Flex objects tracking, power operations)",
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
    def post_flx_bulk_edit(self, request_info, **kwargs):
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
            component_name="flx",
            persistent_fields=persistent_fields_flx,
            collection_name_suffix="flx",
            endpoint_suffix="flx",
            function_name="flx_bulk_edit",
            **kwargs,
        )

        return {
            "payload": response,
            "status": http_status,
        }

    # Update priority by object name
    def post_flx_update_priority(self, request_info, **kwargs):

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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/write/flx_update_priority\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'priority': 'high', 'object_list': 'Okta:Splunk_TA_okta_identity_cloud:okta_logs'}\"",
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
        collection_name = f"kv_trackme_flx_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "flx",
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
            persistent_fields=persistent_fields_flx,
            component="flx",
            update_comment=update_comment,
            audit_context="update priority",
            audit_message="Priority was updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Enable/Disable monitoring by object name
    def post_flx_monitoring(self, request_info, **kwargs):
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
                        "payload": f"Invalid option for action, valid options are: enable | disable",
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/write/flx_monitoring\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'action': 'disable', 'object_list': 'Okta:Splunk_TA_okta_identity_cloud:okta_logs'}\"",
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
        collection_name = f"kv_trackme_flx_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "flx",
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
            persistent_fields=persistent_fields_flx,
            component="flx",
            update_comment=update_comment,
            audit_context="update monitoring",
            audit_message="Monitoring state was updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Remove entities
    def post_flx_delete(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/write/flx_delete\" mode=\"post\" body=\"{'tenant_id':'mytenant', 'deletion_type': 'temporary', 'object_list':'Okta:Splunk_TA_okta_identity_cloud:okta_logs'}\"",
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
        collection_name = f"kv_trackme_flx_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Permanently deleted objects
        collection_perm_deleted_name = (
            f"kv_trackme_common_permanently_deleted_objects_tenant_{tenant_id}"
        )
        collection_perm_deleted = service.kvstore[collection_perm_deleted_name]

        #
        # Outliers collections
        #

        # entity rules collection
        collection_outliers_entity_rules_name = (
            f"kv_trackme_flx_outliers_entity_rules_tenant_{tenant_id}"
        )
        collection_entity_rules = service.kvstore[collection_outliers_entity_rules_name]

        # data rules collection
        collection_outliers_entity_data_name = (
            f"kv_trackme_flx_outliers_entity_data_tenant_{tenant_id}"
        )
        collection_outliers_entity_data = service.kvstore[
            collection_outliers_entity_data_name
        ]

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
                            "message": f'tenant_id="{tenant_id}", The object was successfully deleted',
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
                                "message": f'tenant_id="{tenant_id}", The object was successfully deleted',
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
                                    {"object": obj, "object_category": "splk-flx"}
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
                                    "object_category": "splk-flx",
                                }
                            )
                        )
                    except Exception as e:
                        logger.error(
                            f'tenant_id="{tenant_id}", failed to register a new permanently deleted object, object="{obj}", exception="{str(e)}"'
                        )

        # Batch delete outliers records (chunked, only for successfully deleted) - there might be nothing to delete
        for i in range(0, len(deleted_objects), BATCH_CHUNK_SIZE):
            chunk_objects = deleted_objects[i : i + BATCH_CHUNK_SIZE]
            try:
                collection_entity_rules.data.delete(
                    json.dumps({"$or": [{"object": obj} for obj in chunk_objects]})
                )
            except Exception:
                pass

            try:
                collection_outliers_entity_data.data.delete(
                    json.dumps({"$or": [{"object": obj} for obj in chunk_objects]})
                )
            except Exception:
                pass

        # Batch audit events in a single REST call (only for successfully deleted)
        if deleted_records:
            audit_events = []
            for record in deleted_records:
                audit_events.append(
                    {
                        "action": "success",
                        "change_type": f"delete {deletion_type}",
                        "object": str(record.get("object")),
                        "object_category": "splk-flx",
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
                    delete_shadow_records(service_system, tenant_id, "flx", deleted_keys, shadow_enabled=shadow_enabled)
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
                "flx",
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

    # Update monitoring week days by object name
    def post_flx_update_wdays(self, request_info, **kwargs):
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

                # Week days monitoring can be:
                # manual:all_days / manual:monday-to-friday / manual:monday-to-saturday / [ 0, 1, 2, 3, 4, 5, 6 ] where Sunday is 0
                monitoring_wdays = resp_dict["monitoring_wdays"]

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint configures the week days monitoring rule for an existing data source, it requires a POST call with the following information:",
                "resource_desc": "Update week days monitoring for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/write/flx_update_wdays\" mode=\"post\" body=\"{'tenant_id':'mytenant','object_list':'netscreen:netscreen:firewall','monitoring_wdays':'manual:1,2,3,4,5'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_list": "REQUIRED (with keys_list as alternative). Comma-separated list of entity object names. Either object_list or keys_list must be provided",
                        "keys_list": "REQUIRED (with object_list as alternative). Comma-separated list of entity KV record _keys. Either object_list or keys_list must be provided",
                        "monitoring_wdays": "the week days rule, valid options are manual:all_days / manual:monday-to-friday / manual:monday-to-saturday / [ 0, 1, 2, 3, 4, 5, 6 ] where Sunday is 0",
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
        collection_name = f"kv_trackme_flx_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "flx",
            "object_list": object_list,
            "keys_list": keys_list,
        }

        # Prepare the update fields
        update_fields = {"monitoring_wdays": monitoring_wdays}

        # Call the generic update function
        response, status_code = generic_batch_update(
            self,
            request_info,
            update_request_info=update_request_info,
            collection=collection,
            update_fields=update_fields,
            persistent_fields=persistent_fields_flx,
            component="flx",
            update_comment=update_comment,
            audit_context="update week days monitoring",
            audit_message="Week days monitoring was updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Update monitoring hours ranges by object name
    def post_flx_update_hours_ranges(self, request_info, **kwargs):
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

                monitoring_hours_ranges = resp_dict["monitoring_hours_ranges"]

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint configures the week days monitoring rule for an existing data source, it requires a POST call with the following information:",
                "resource_desc": "Update hours of monitoring for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/write/flx_update_hours_ranges\" mode=\"post\" body=\"{'tenant_id':'mytenant', 'object_list':'netscreen:netscreen:firewall', 'monitoring_hours_ranges':'manual:8,9,10,11,12,13,14,15,16,17'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_list": "REQUIRED (with keys_list as alternative). Comma-separated list of entity object names. Either object_list or keys_list must be provided",
                        "keys_list": "REQUIRED (with object_list as alternative). Comma-separated list of entity KV record _keys. Either object_list or keys_list must be provided",
                        "monitoring_hours_ranges": "the hours ranges rule, valid options are manual:all_ranges / manual:08h-to-20h / [ 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 ] where 00h00 to 01h59 is 0",
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
        collection_name = f"kv_trackme_flx_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "flx",
            "object_list": object_list,
            "keys_list": keys_list,
        }

        # Prepare the update fields
        update_fields = {"monitoring_hours_ranges": monitoring_hours_ranges}

        # Call the generic update function
        response, status_code = generic_batch_update(
            self,
            request_info,
            update_request_info=update_request_info,
            collection=collection,
            update_fields=update_fields,
            persistent_fields=persistent_fields_flx,
            component="flx",
            update_comment=update_comment,
            audit_context="update hours ranges monitoring",
            audit_message="Monitoring hours ranges were updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Update monitoring time policy and rules by object name
    def post_flx_update_monitoring_time(self, request_info, **kwargs):
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
                "describe": "This endpoint configures the monitoring time policy and rules for an existing flex object, it requires a POST call with the following information:",
                "resource_desc": "Update monitoring time policy/rules for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/write/flx_update_monitoring_time\" mode=\"post\" body=\"{'tenant_id':'mytenant','object_list':'group:subgroup:object','monitoring_time_policy':'business_days_08h_20h'}\"",
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
        collection_name = f"kv_trackme_flx_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "flx",
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
            persistent_fields=persistent_fields_flx,
            component="flx",
            update_comment=update_comment,
            audit_context="update monitoring time policy/rules",
            audit_message="Monitoring time policy/rules were updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Update list of manual tags
    def post_flx_update_manual_tags(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/write/flx_update_manual_tags\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'tags_manual': 'mytag1,maytag2,mytag3', 'object_list': 'netscreen:netscreen:firewall,wineventlog:WinEventLog'}\"",
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
        collection_name = f"kv_trackme_flx_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Tags policies collection
        collection_tags_policies_name = f"kv_trackme_flx_tags_tenant_{tenant_id}"
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
                    "splk-flx",
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
                "flx",
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

    # Update SLA class
    def post_flx_update_sla_class(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/write/flx_update_sla_class\" mode=\"post\" body=\"{'tenant_id':'mytenant','object_list':'netscreen:netscreen:firewall','sla_class':'gold'}\"",
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
        collection_name = f"kv_trackme_flx_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "flx",
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
            persistent_fields=persistent_fields_flx,
            component="flx",
            update_comment=update_comment,
            audit_context="update SLA class",
            audit_message="SLA class was updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Add new policy
    def post_flx_thresholds_add(self, request_info, **kwargs):

        # Declare
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
                            "response": "The tenant_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                # handle keys_list
                keys_list = extract_keys_list(resp_dict)
                if keys_list:
                    if not isinstance(keys_list, list):
                        keys_list = keys_list.split(",")
                    # Deduplicate while preserving order. Without this, a caller
                    # that passes duplicate object_ids would cause the WLK
                    # handler (which uses a randomly-salted _key) to insert
                    # multiple KV rows for the same logical entity, violating
                    # the (object_id, metric_name, value) invariant.
                    # FLX/FQM use a deterministic record-hash _key so duplicates
                    # already collide on upsert, but dedup makes the contract
                    # explicit and defends against subtle differences in the
                    # record payload.
                    keys_list = list(dict.fromkeys(keys_list))
                else:
                    return {
                        "payload": {"error": "keys_list is required"},
                        "status": 500,
                    }

                # Validate threshold fields
                try:
                    metric_name = resp_dict["metric_name"]
                    value = resp_dict["value"]
                    operator = resp_dict["operator"]
                    condition_true = resp_dict["condition_true"]
                    comment = resp_dict.get("comment", "")
                    # Score is optional, default to 100 if not provided
                    score = resp_dict.get("score", 100)

                    # Validate value is not null or empty, we can accept both numerical values or string referencing a field in the metrics_record
                    if value is None or value == "":
                        return {
                            "payload": {
                                "error": "value must be a numeric value (integer or float)"
                            },
                            "status": 500,
                        }

                    try:
                        # Try to convert to float first
                        value = float(value)
                        # If it's a whole number, convert to int
                        if value.is_integer():
                            value = int(value)
                    except (ValueError, TypeError):
                        return {
                            "payload": {
                                "error": "value must be a numeric value (integer or float)"
                            },
                            "status": 500,
                        }

                    # Validate operator
                    if operator not in ["<", ">", "<=", ">=", "==", "!="]:
                        return {
                            "payload": {
                                "error": "operator must be one of: <, >, <=, >=, ==, !="
                            },
                            "status": 500,
                        }

                    # Validate condition_true (accept 0 or False, 1 or True)
                    try:
                        condition_true = interpret_boolean(condition_true)
                    except ValueError as e:
                        return {
                            "payload": {"error": str(e)},
                            "status": 500,
                        }

                    # Validate score (must be integer between 0 and 100, default 100)
                    try:
                        score = int(score)
                        if score < 0 or score > 100:
                            return {
                                "payload": {
                                    "error": "score must be an integer between 0 and 100"
                                },
                                "status": 500,
                            }
                    except (ValueError, TypeError):
                        return {
                            "payload": {
                                "error": "score must be an integer between 0 and 100"
                            },
                            "status": 500,
                        }

                    # Variable threshold fields (optional)
                    variable_threshold_enabled = str(resp_dict.get("variable_threshold_enabled", "false")).lower()
                    variable_threshold_default = resp_dict.get("variable_threshold_default", None)
                    variable_threshold_slots = resp_dict.get("variable_threshold_slots", None)

                    # Coerce variable_threshold_default to numeric (float) if provided
                    if variable_threshold_default is not None:
                        try:
                            variable_threshold_default = float(variable_threshold_default)
                        except (ValueError, TypeError):
                            variable_threshold_default = None

                    # Normalize slots to JSON string unconditionally (matches update path)
                    if variable_threshold_slots is not None and isinstance(variable_threshold_slots, (dict, list)):
                        variable_threshold_slots = json.dumps(variable_threshold_slots)

                    # Validate variable threshold slots — required when enabling
                    if variable_threshold_enabled == "true":
                        if variable_threshold_slots is None:
                            return {
                                "payload": {
                                    "error": "variable_threshold_slots is required when variable_threshold_enabled is true"
                                },
                                "status": 400,
                            }
                        try:
                            if isinstance(variable_threshold_slots, str):
                                slots_config = json.loads(variable_threshold_slots)
                            else:
                                slots_config = variable_threshold_slots
                            from trackme_libs_decisionmaker import validate_variable_threshold_slots
                            slot_errors = validate_variable_threshold_slots(slots_config)
                            if slot_errors:
                                return {
                                    "payload": {
                                        "error": f"Invalid variable_threshold_slots: {'; '.join(slot_errors)}"
                                    },
                                    "status": 500,
                                }
                            # Store as JSON string
                            variable_threshold_slots = json.dumps(slots_config)
                        except (json.JSONDecodeError, TypeError) as e:
                            return {
                                "payload": {
                                    "error": f"variable_threshold_slots must be valid JSON: {str(e)}"
                                },
                                "status": 500,
                            }

                    # Create threshold object
                    threshold_record = {
                        "metric_name": metric_name,
                        "value": value,
                        "operator": operator,
                        "condition_true": condition_true,
                        "mtime": time.time(),
                        "comment": comment,
                        "score": score,
                        "variable_threshold_enabled": variable_threshold_enabled,
                    }

                    # Add variable threshold fields if provided
                    if variable_threshold_default is not None:
                        threshold_record["variable_threshold_default"] = variable_threshold_default
                    if variable_threshold_slots is not None:
                        threshold_record["variable_threshold_slots"] = variable_threshold_slots

                except KeyError as e:
                    return {
                        "payload": {"error": f"Missing required field: {str(e)}"},
                        "status": 500,
                    }
                except Exception as e:
                    return {
                        "payload": {"error": f"Invalid threshold data: {str(e)}"},
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint creates a new threshold or updates an existing threshold for a given object, it requires a POST call with the following data:",
                "resource_desc": "Add or update a threshold",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_flx/write/flx_thresholds_add\" body=\"{'tenant_id': 'mytenant', 'keys_list': 'object1,object2', 'metric_name': 'error_count', 'value': 1000, 'operator': '>', 'condition_true': 1, 'comment': 'Alert on high error count'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "keys_list": "(required) Comma separated list of object keys to apply the threshold to",
                        "metric_name": "(required) Name of the metric to set threshold for",
                        "value": "(required) Numeric threshold value",
                        "operator": "(required) Comparison operator (<, >, <=, >=, ==, !=)",
                        "condition_true": "(required) Condition to be met (0 or 1 or True or False)",
                        "comment": "(optional) Description of the threshold",
                        "score": "(optional) Score value (0-100) to assign when threshold is breached, defaults to 100 if not provided",
                        "update_comment": "(optional) Comment for the update, comments are added to the audit record, if unset will be defined to: API update",
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
        collection_name = f"kv_trackme_flx_thresholds_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Pre-load existing thresholds for this metric_name in a single query, then
        # index by object_id to decide insert vs update for each input key in O(1).
        # Replaces the previous per-record query/insert loop which scaled linearly
        # with the entity count and dominated the FLX tracker first-execution time
        # at large scale. If this query fails we must NOT fall back to an empty
        # set (that would treat every entity as new and create duplicate KV rows
        # with fresh sha256 _keys alongside the existing ones); abort with 500
        # so the caller can retry.
        try:
            existing_records = collection.data.query(
                query=json.dumps({"metric_name": metric_name})
            )
        except Exception as e:
            logger.error(
                f'tenant_id="{tenant_id}", metric_name="{metric_name}", failed to pre-load existing thresholds, aborting bulk seed to avoid duplicate inserts, exception="{str(e)}"'
            )
            return {
                "payload": {
                    "error": (
                        f"Failed to pre-load existing thresholds for metric_name='{metric_name}'; "
                        f"refusing to proceed to avoid duplicate KV records. Underlying error: {str(e)}"
                    ),
                    "tenant_id": tenant_id,
                    "metric_name": metric_name,
                },
                "status": 500,
            }

        existing_by_object_id = {}
        for r in existing_records:
            obj_id = r.get("object_id")
            if obj_id is not None:
                existing_by_object_id[obj_id] = r

        # Build the list of records to upsert. _key reused from the existing record
        # on update; freshly hashed for inserts. Score preservation matches the
        # previous per-record behaviour exactly. Variable-threshold fields are
        # preserved from the existing record on update unless the request
        # explicitly supplied them - matches the single-entity update endpoint
        # contract and prevents tracker re-seeds from silently wiping
        # UI-customised per-entity variable thresholds (the parse hot path
        # never sends variable_threshold_* keys, so without this preservation
        # `threshold_record` would carry the default `enabled="false"` and
        # batch_save would overwrite any customised configuration).
        records_to_upsert = []
        planned_insert_count = 0
        planned_update_count = 0
        score_provided = "score" in resp_dict
        variable_threshold_enabled_provided = "variable_threshold_enabled" in resp_dict
        variable_threshold_default_provided = "variable_threshold_default" in resp_dict
        variable_threshold_slots_provided = "variable_threshold_slots" in resp_dict
        for object_id in keys_list:
            iter_record = dict(threshold_record)
            iter_record["object_id"] = object_id
            existing = existing_by_object_id.get(object_id)
            if existing:
                iter_record["_key"] = existing.get("_key")
                if not score_provided:
                    existing_score = existing.get("score")
                    if existing_score is not None:
                        try:
                            iter_record["score"] = int(existing_score)
                        except (TypeError, ValueError):
                            iter_record["score"] = 100
                if not variable_threshold_enabled_provided:
                    existing_var_enabled = existing.get("variable_threshold_enabled")
                    if existing_var_enabled is not None:
                        iter_record["variable_threshold_enabled"] = str(existing_var_enabled).lower()
                if not variable_threshold_default_provided:
                    existing_var_default = existing.get("variable_threshold_default")
                    if existing_var_default is not None:
                        iter_record["variable_threshold_default"] = existing_var_default
                    else:
                        iter_record.pop("variable_threshold_default", None)
                if not variable_threshold_slots_provided:
                    existing_var_slots = existing.get("variable_threshold_slots")
                    if existing_var_slots is not None:
                        iter_record["variable_threshold_slots"] = existing_var_slots
                    else:
                        iter_record.pop("variable_threshold_slots", None)
                planned_update_count += 1
            else:
                iter_record["_key"] = hashlib.sha256(
                    json.dumps(iter_record, sort_keys=True).encode("utf-8")
                ).hexdigest()
                planned_insert_count += 1
            records_to_upsert.append(iter_record)

        processed_count = len(keys_list)
        task_instance_id = str(uuid.uuid4())
        try:
            batch_result = batch_update_worker(
                collection_name,
                collection,
                records_to_upsert,
                request_info.user,
                task_instance_id,
                task_name="flx_thresholds_seed",
                max_multi_thread_workers=8,
            )
            successful_updates = batch_result.get("successful_updates", 0)
            failed_updates = batch_result.get("failed_updates", 0)
        except Exception as e:
            logger.error(
                f'tenant_id="{tenant_id}", metric_name="{metric_name}", batch threshold upsert failed, exception="{str(e)}"'
            )
            successful_updates = 0
            failed_updates = processed_count

        # Aggregated audit event - one per (metric_name) call instead of one per
        # entity. The "planned_*" counters reflect what the merge loop classified
        # before the batch_save call; "written" and "failed" come from the
        # batch_update_worker outcome so a partial chunk failure does not get
        # double-counted as a successful insert+update.
        sample_object_ids = keys_list[:10]
        audit_status = "success" if failed_updates == 0 else "failure"
        try:
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user,
                audit_status,
                "add threshold (bulk)",
                f"metric_name={metric_name}",
                "splk-flx",
                {
                    "metric_name": metric_name,
                    "value": value,
                    "operator": operator,
                    "condition_true": condition_true,
                    "planned_insert_count": planned_insert_count,
                    "planned_update_count": planned_update_count,
                    "written_count": successful_updates,
                    "failed_count": failed_updates,
                    "sample_object_ids": sample_object_ids,
                },
                f"Bulk threshold seed: planned {planned_insert_count} insert(s) + {planned_update_count} update(s); {successful_updates} written, {failed_updates} failed",
                str(update_comment),
            )
        except Exception as e:
            logger.error(
                f'failed to generate an audit event with exception="{str(e)}"'
            )

        logger.info(
            f'tenant_id="{tenant_id}", metric_name="{metric_name}", task_instance_id={task_instance_id}, '
            f'flx_thresholds_seed planned_insert_count={planned_insert_count}, planned_update_count={planned_update_count}, '
            f'written_count={successful_updates}, failed_count={failed_updates}, total_object_ids={len(keys_list)}, full_object_ids={json.dumps(keys_list)}'
        )

        summary_records = [
            {
                "action": "bulk_upsert",
                "result": audit_status,
                "metric_name": metric_name,
                "planned_insert_count": planned_insert_count,
                "planned_update_count": planned_update_count,
                "written_count": successful_updates,
                "failed_count": failed_updates,
                "sample_object_ids": sample_object_ids,
            }
        ]

        req_summary = {
            "process_count": processed_count,
            "success_count": successful_updates,
            "failures_count": failed_updates,
            "records": summary_records,
        }

        # Return 500 only when there are actual failures; a no-op add
        # (no records processed) is not an error.
        if failed_updates > 0:
            return {"payload": req_summary, "status": 500}
        else:
            return {"payload": req_summary, "status": 200}

    # Delete records from the collection
    def post_flx_thresholds_del(self, request_info, **kwargs):
        # Declare
        tenant_id = None
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
                            "response": "The tenant_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    keys_list = extract_keys_list(resp_dict)
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The keys_list is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                # if keys_list is a string, turn into a list
                if isinstance(keys_list, str):
                    keys_list = keys_list.split(",")

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes thresholds, it requires a POST call with the following information:",
                "resource_desc": "Delete one or more thresholds",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_flx/write/flx_thresholds_del\" body=\"{'tenant_id': 'mytenant', 'keys_list': 'key1,key2'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "keys_list": "(required) Comma separated list of threshold keys to delete",
                        "update_comment": "(optional) Comment for the update, comments are added to the audit record, if unset will be defined to: API update",
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

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # Data collection
        collection_name = f"kv_trackme_flx_thresholds_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # records summary
        records = []

        # loop
        for key in keys_list:
            try:
                # Get the current record
                record = collection.data.query_by_id(key)

                # Get the object_id before deleting the record
                object_id = record.get("object_id")

                # Remove the record
                collection.data.delete(json.dumps({"_key": key}))

                # increment counter
                processed_count += 1
                succcess_count += 1

                # audit record
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        "delete threshold",
                        object_id,
                        "splk-flx",
                        record,
                        "The threshold was deleted successfully",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                result = {
                    "action": "delete",
                    "result": "success",
                    "record": record,
                }

                records.append(result)

                logger.info(json.dumps(result, indent=0))

            except Exception as e:
                # increment counter
                processed_count += 1
                succcess_count += 0
                failures_count += 1

                # audit record
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "failure",
                        "delete threshold",
                        object_id,
                        "splk-flx",
                        None,
                        str(e),
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                result = {
                    "action": "delete",
                    "result": "failure",
                    "record": key,
                    "exception": str(e),
                }

                # append to records
                records.append(result)

                # log
                logger.error(json.dumps(result, indent=0))

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

    # Update records
    def post_flx_thresholds_update(self, request_info, **kwargs):
        # Declare
        tenant_id = None
        describe = False
        records_list = None

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
                            "response": "The tenant_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    records_list = resp_dict["records_list"]
                    if not isinstance(records_list, list):
                        return {
                            "payload": {
                                "error": f"records_list must be a list of records, received: {type(records_list)}, content: {records_list}"
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The records_list list is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint updates multiple thresholds for flx objects, it requires a POST call with the following information:",
                "resource_desc": "Update multiple thresholds",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/write/flx_thresholds_update\" mode=\"post\" body=\"{'tenant_id':'mytenant','records_list':[{'key':'key1','metric_name':'error_count','value':1000,'operator':'>','condition_true':'1','comment':'Alert on high error count'}]}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "threshold_records": "List of threshold records to update. Each record must contain:",
                        "records_list": {
                            "_key": "The key of the threshold to update",
                            "object_id": "The object id of the threshold to update",
                            "metric_name": "The name of the metric to set threshold for",
                            "value": "The threshold value (numeric)",
                            "operator": "The comparison operator (<, >, <=, >=, ==, !=)",
                            "condition_true": "The condition to be met (0 or 1 or True or False)",
                            "score": "(optional) The score (0-100) assigned when this threshold is breached. Default is 100.",
                            "comment": "(optional) A comment describing the threshold",
                        },
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

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # Data collection
        collection_name = f"kv_trackme_flx_thresholds_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # records summary
        records = []

        # loop through validated records
        for record in records_list:
            key = None
            current_record = None
            try:
                key = record.get("_key")
                if not key:
                    raise KeyError("'_key' field is required in record")
                # Get the current record
                current_record = collection.data.query_by_id(key)

                # if value or operator are different, update the record and uptime the mtime
                # Get score from current_record, default to 100 if not present
                current_score = current_record.get("score")
                if current_score is None:
                    current_score = 100
                else:
                    try:
                        current_score = int(current_score)
                    except (TypeError, ValueError):
                        current_score = 100

                # Get score from record, preserve existing score if not provided
                record_score = record.get("score")
                if record_score is None:
                    # If score not provided, use the current score to preserve existing value
                    record_score = current_score
                else:
                    try:
                        record_score = int(record_score)
                        if record_score < 0 or record_score > 100:
                            return {
                                "payload": {
                                    "error": "score must be an integer between 0 and 100"
                                },
                                "status": 500,
                            }
                    except (TypeError, ValueError):
                        # If invalid, fall back to current score
                        record_score = current_score

                # Handle variable threshold fields - preserve from current record if not provided
                record_variable_enabled = str(record.get("variable_threshold_enabled", current_record.get("variable_threshold_enabled", "false"))).lower()
                record_variable_default = record.get("variable_threshold_default", current_record.get("variable_threshold_default"))
                record_variable_slots = record.get("variable_threshold_slots", current_record.get("variable_threshold_slots"))

                # Coerce variable_threshold_default to numeric (float) if provided
                if record_variable_default is not None:
                    try:
                        record_variable_default = float(record_variable_default)
                    except (ValueError, TypeError):
                        record_variable_default = None

                # Normalize slots to JSON string unconditionally (matches bulk update path)
                if record_variable_slots is not None and isinstance(record_variable_slots, (dict, list)):
                    record_variable_slots = json.dumps(record_variable_slots)

                # Validate variable threshold slots — required when enabling
                if record_variable_enabled == "true":
                    if record_variable_slots is None:
                        return {
                            "payload": {
                                "error": "variable_threshold_slots is required when variable_threshold_enabled is true"
                            },
                            "status": 400,
                        }
                    try:
                        if isinstance(record_variable_slots, str):
                            slots_config = json.loads(record_variable_slots)
                        else:
                            slots_config = record_variable_slots
                        from trackme_libs_decisionmaker import validate_variable_threshold_slots
                        slot_errors = validate_variable_threshold_slots(slots_config)
                        if slot_errors:
                            return {
                                "payload": {
                                    "error": f"Invalid variable_threshold_slots: {'; '.join(slot_errors)}"
                                },
                                "status": 500,
                            }
                        record_variable_slots = json.dumps(slots_config)
                    except (json.JSONDecodeError, TypeError) as e:
                        return {
                            "payload": {
                                "error": f"variable_threshold_slots must be valid JSON: {str(e)}"
                            },
                            "status": 500,
                        }

                if (
                    current_record["value"] != record["value"]
                    or current_record["operator"] != record["operator"]
                    or current_record["condition_true"] != record["condition_true"]
                    or current_record.get("comment", "") != record.get("comment", "")
                    or current_score != record_score
                    or current_record.get("variable_threshold_enabled", "false") != record_variable_enabled
                    or current_record.get("variable_threshold_default") != record_variable_default
                    or current_record.get("variable_threshold_slots") != record_variable_slots
                ):
                    # Ensure score is included in the record
                    record["score"] = record_score
                    # Preserve fields that might not be in the update record
                    if "metric_name" not in record:
                        record["metric_name"] = current_record.get("metric_name")
                    if "object_id" not in record:
                        record["object_id"] = current_record.get("object_id")
                    record["mtime"] = time.time()

                    # Set variable threshold fields
                    record["variable_threshold_enabled"] = record_variable_enabled
                    if record_variable_default is not None:
                        record["variable_threshold_default"] = record_variable_default
                    elif "variable_threshold_default" in record:
                        del record["variable_threshold_default"]
                    if record_variable_slots is not None:
                        record["variable_threshold_slots"] = record_variable_slots
                    elif "variable_threshold_slots" in record:
                        del record["variable_threshold_slots"]

                    # in record, convert condition_true to integer (from False/True to 0/1)
                    try:
                        record["condition_true"] = interpret_boolean(
                            record["condition_true"]
                        )
                    except ValueError as e:
                        logger.error(f"Invalid condition_true value: {str(e)}")
                        raise

                    # Update the record
                    collection.data.update(
                        str(key),
                        json.dumps(record),
                    )

                    # increment counter
                    processed_count += 1
                    succcess_count += 1

                    # audit record
                    try:
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "success",
                            "update threshold",
                            current_record.get("object_id"),
                            "splk-flx",
                            current_record,
                            "The threshold was updated successfully",
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                    result = {
                        "action": "update",
                        "result": "success",
                        "record": current_record,
                    }

                    records.append(result)

                    logger.info(json.dumps(result, indent=0))

            except Exception as e:
                # increment counter
                processed_count += 1
                succcess_count += 0
                failures_count += 1

                # audit record
                try:
                    object_id = current_record.get("object_id") if current_record else record.get("object_id")
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "failure",
                        "update threshold",
                        object_id,
                        "splk-flx",
                        None,
                        str(e),
                        str(update_comment),
                    )
                except Exception as audit_e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(audit_e)}"'
                    )

                result = {
                    "action": "update",
                    "result": "failure",
                    "record": key if key else record,
                    "exception": str(e),
                }

                # append to records
                records.append(result)

                # log
                logger.error(json.dumps(result, indent=0))

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

    # Bulk update thresholds
    def post_flx_thresholds_update_bulk(self, request_info, **kwargs):
        # Declare
        tenant_id = None
        component = None
        keys_list = None
        record_changes = None
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
                            "response": "The tenant_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }
                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The component is required",
                            "status": 400,
                        },
                        "status": 400,
                    }
                try:
                    keys_list = extract_keys_list(resp_dict)

                    # if is a string, convert to list from comma separated string
                    if isinstance(keys_list, str):
                        keys_list = keys_list.split(",")

                    # must not be empty
                    if not keys_list or len(keys_list) == 0:
                        return {
                            "payload": {
                                "error": f"keys_list must be a list of keyids, provided as a native list or a comma separated string, received: {type(keys_list)}, content: {keys_list}"
                            },
                            "status": 500,
                        }

                except Exception as e:
                    return {
                        "payload": {
                            "response": "The keys_list list is required",
                            "status": 400,
                        },
                        "status": 400,
                    }
                try:
                    record_changes = resp_dict["record_changes"]
                    if not isinstance(record_changes, dict):
                        return {
                            "payload": {
                                "error": f"record_changes must be a dictionary, received: {type(record_changes)}, content: {record_changes}"
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The record_changes dictionary is required",
                            "status": 400,
                        },
                        "status": 400,
                    }
        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint bulk updates thresholds for flx objects, it requires a POST call with the following information:",
                "resource_desc": "Bulk update multiple thresholds",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/write/flx_thresholds_update_bulk\" mode=\"post\" body=\"{'tenant_id':'mytenant','component':'flx','keys_list':['key1','key2'],'record_changes':{'kpi_metric_name':'error_count','kpi_metric_value':1000,'operator':'>','condition_true':'1'},'update_comment':'Bulk update thresholds'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "Component identifier (e.g., 'flx')",
                        "keys_list": "List of keyids to update",
                        "record_changes": {
                            "kpi_metric_name": "The name of the metric to set threshold for",
                            "kpi_metric_value": "The threshold value (numeric)",
                            "operator": "The comparison operator (<, >, <=, >=, ==, !=)",
                            "condition_true": "The condition to be met (0 or 1 or True or False)",
                        },
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

        # counters
        processed_count = 0
        success_count = 0
        failures_count = 0

        # Data collection
        collection_name = f"kv_trackme_{component}_thresholds_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # records summary
        records = []

        # loop through keys_list
        for keyid in keys_list:
            logger.debug(f'keyid="{keyid}", searching for records in collection {collection_name}')

            try:
                # Get records in the KVstore that match this object_id (we get a list)
                kvrecords = collection.data.query(query=json.dumps({"object_id": keyid}))
                logger.debug(f'object_id="{keyid}" kvrecords="{json.dumps(kvrecords, indent=2)}"')

            except Exception as e:
                logger.error(f"Failed to retrieve records for object_id {keyid}: {str(e)}")
                return {
                    "payload": f"Failed to retrieve records from the KVstore collection {collection_name} for object_id {keyid}: {str(e)}",
                    "status": 500,
                }

            # if not kvrecords, continue, nothing to do.
            if not kvrecords:
                logger.info(f'object_id="{keyid}", no records found, nothing to do.')
                continue

            # loop through the records
            for kvrecord in kvrecords:

                logger.info(f'object_id="{keyid}", processing kvrecord="{json.dumps(kvrecord, indent=2)}"')

                original_record = kvrecord.copy()

                # check if the kpi metric name matches, otherwise skip record
                if kvrecord.get("metric_name") != record_changes["kpi_metric_name"]:
                    continue

                # Check if any of the record_changes fields are different
                needs_update = False
                updated_record = kvrecord.copy()

                # Update kpi_metric_value if provided and different
                if "kpi_metric_value" in record_changes and kvrecord.get("value") != record_changes["kpi_metric_value"]:
                    updated_record["value"] = record_changes["kpi_metric_value"]
                    needs_update = True

                # Update operator if provided and different
                if "operator" in record_changes and kvrecord.get("operator") != record_changes["operator"]:
                    updated_record["operator"] = record_changes["operator"]
                    needs_update = True

                # Update condition_true if provided and different
                if "condition_true" in record_changes:
                    new_condition_true = interpret_boolean(record_changes["condition_true"])
                    if interpret_boolean(kvrecord.get("condition_true")) != new_condition_true:
                        updated_record["condition_true"] = new_condition_true
                        needs_update = True

                # Update variable threshold fields if provided
                if "variable_threshold_enabled" in record_changes:
                    normalized_enabled = str(record_changes["variable_threshold_enabled"]).lower()
                    # When enabling, require that slots are available (either in this request or existing)
                    if normalized_enabled == "true":
                        has_new_slots = "variable_threshold_slots" in record_changes and record_changes.get("variable_threshold_slots") is not None
                        has_existing_slots = kvrecord.get("variable_threshold_slots") is not None
                        if not has_new_slots and not has_existing_slots:
                            logger.warning(f'object_id="{keyid}", cannot enable variable threshold without slots, skipping')
                            continue
                    if kvrecord.get("variable_threshold_enabled", "false") != normalized_enabled:
                        updated_record["variable_threshold_enabled"] = normalized_enabled
                        needs_update = True

                if "variable_threshold_default" in record_changes:
                    new_default = record_changes["variable_threshold_default"]
                    # Coerce to numeric (float) if provided
                    if new_default is not None:
                        try:
                            new_default = float(new_default)
                        except (ValueError, TypeError):
                            new_default = None
                    if new_default is not None:
                        if kvrecord.get("variable_threshold_default") != new_default:
                            updated_record["variable_threshold_default"] = new_default
                            needs_update = True
                    elif kvrecord.get("variable_threshold_default") is not None:
                        # Clear stale value when coercion fails (e.g. "" during disable)
                        updated_record["variable_threshold_default"] = None
                        needs_update = True

                if "variable_threshold_slots" in record_changes:
                    new_slots = record_changes["variable_threshold_slots"]
                    if new_slots is not None:
                        # Normalize to JSON string if provided as dict/list
                        if isinstance(new_slots, (dict, list)):
                            new_slots = json.dumps(new_slots)
                        # Validate slot configuration before storing
                        try:
                            slots_to_validate = json.loads(new_slots) if isinstance(new_slots, str) else new_slots
                            from trackme_libs_decisionmaker import validate_variable_threshold_slots
                            slot_errors = validate_variable_threshold_slots(slots_to_validate)
                            if slot_errors:
                                logger.warning(f'object_id="{keyid}", invalid variable_threshold_slots in bulk update: {"; ".join(slot_errors)}, skipping slot update')
                            else:
                                if kvrecord.get("variable_threshold_slots") != new_slots:
                                    updated_record["variable_threshold_slots"] = new_slots
                                    needs_update = True
                        except Exception as e:
                            logger.warning(f'object_id="{keyid}", failed to validate variable_threshold_slots: {str(e)}, skipping slot update')
                    elif kvrecord.get("variable_threshold_slots") is not None:
                        # Clear stale slots when new_slots is None (e.g. during disable)
                        updated_record["variable_threshold_slots"] = None
                        needs_update = True

                # Only update if there are changes
                if not needs_update:
                    logger.info(f'object_id="{keyid}", no update is required, original_record="{json.dumps(original_record, indent=2)}"')
                    continue

                if needs_update:
                    updated_record["mtime"] = time.time()

                    # Try updating the record
                    try:

                        logger.info(f'object_id="{keyid}", update is required, original_record="{json.dumps(original_record, indent=0)}", updated_record="{json.dumps(updated_record, indent=2)}"')

                        # Update the record
                        collection.data.update(
                            updated_record.get("_key"),
                            json.dumps(updated_record),
                        )
                        # increment counter
                        processed_count += 1
                        success_count += 1
                        # audit record
                        try:
                            trackme_audit_event(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                tenant_id,
                                request_info.user,
                                "success",
                                "bulk update threshold",
                                kvrecord.get("object_id"),
                                f"splk-{component}",
                                kvrecord,
                                "The threshold was bulk updated successfully",
                                str(update_comment),
                            )
                        except Exception as e:
                            logger.error(
                                f'failed to generate an audit event with exception="{str(e)}"'
                            )
                        result = {
                            "action": "bulk_update",
                            "result": "success",
                            "keyid": keyid,
                            "object_id": kvrecord.get("object_id"),
                            "changes": record_changes,
                        }
                        records.append(result)
                        logger.info(json.dumps(result, indent=0))

                    except Exception as e:
                        # increment counter
                        processed_count += 1
                        failures_count += 1
                        # audit record
                        try:
                            trackme_audit_event(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                tenant_id,
                                request_info.user,
                                "failure",
                                "bulk update threshold",
                                keyid,
                                f"splk-{component}",
                                None,
                                str(e),
                                str(update_comment),
                            )
                        except Exception as e:
                            logger.error(
                                f'failed to generate an audit event with exception="{str(e)}"'
                            )
                        result = {
                            "action": "bulk_update",
                            "result": "failure",
                            "keyid": keyid,
                            "exception": str(e),
                        }
                        # append to records
                        records.append(result)
                        # log
                        logger.error(json.dumps(result, indent=0))

                else:
                    # No changes needed
                    processed_count += 1
                    success_count += 1
                    result = {
                        "action": "bulk_update",
                        "result": "no_changes_needed",
                        "keyid": keyid,
                        "object_id": kvrecord.get("object_id"),
                        "changes": record_changes,
                    }
                    records.append(result)
                    logger.info(json.dumps(result, indent=0))

        # render HTTP status and summary
        req_summary = {
            "process_count": processed_count,
            "success_count": success_count,
            "failures_count": failures_count,
            "records": records,
        }
        if processed_count == 0: # nothing to be done, return 200
            logger.info(f'endpoint flx_thresholds_update_bulk, processed_count="{processed_count}", success_count="{success_count}", nothing to be done, returning 200')
        elif processed_count == success_count:
            logger.info(f'endpoint flx_thresholds_update_bulk, processed_count="{processed_count}", success_count="{success_count}", thresholds records updated successfully, returning 200')
            return {"payload": req_summary, "status": 200}
        else:
            logger.info(f'endpoint flx_thresholds_update_bulk, processed_count="{processed_count}", success_count="{success_count}", returning 500')
            return {"payload": req_summary, "status": 500}

    # Update drilldown search definitions for Flex Objects
    def post_flx_update_drilldown_searches(self, request_info, **kwargs):
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
                            "response": "The tenant_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    drilldown_records = resp_dict["drilldown_records"]
                    if not isinstance(drilldown_records, list):
                        # try loading as a json string, if failed return
                        try:
                            drilldown_records = json.loads(drilldown_records)
                        except Exception as e:
                            return {
                                "payload": {
                                    "error": "drilldown_records must be a list of records or a JSON string containing a list of records"
                                },
                                "status": 500,
                            }
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The drilldown_records list is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint defines or updates drilldown search definitions for Flex Objects, it requires a POST call with the following information:",
                "resource_desc": "Define or update drilldown search definitions for Flex Objects",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/write/flx_update_drilldown_searches\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'drilldown_records': [{'tracker_name': 'mytracker', 'drilldown_search': 'index=main | search source=*', 'drilldown_search_earliest': '-24h', 'drilldown_search_latest': 'now'}]}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "drilldown_records": "List of drilldown search records. Each record must contain:",
                        "drilldown_records_fields": {
                            "tracker_name": "The name of the associated tracker",
                            "drilldown_search": "The drilldown search definition",
                            "drilldown_search_earliest": "The drilldown search earliest time",
                            "drilldown_search_latest": "The drilldown search latest time",
                        },
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

        # records summary
        records = []

        # Data collection
        collection_name = f"kv_trackme_flx_drilldown_searches_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Pre-validate all incoming drilldown_records once, collect the valid
        # candidates and the validation failures separately. Replaces a per-record
        # query/insert/update loop that scaled linearly with the tracker count.
        # `valid_candidates_by_tracker` is keyed by tracker_name so duplicate
        # entries in `drilldown_records` collapse to a single record (last-write
        # wins, matches REST upsert semantics). Without this, duplicates would
        # each get a distinct `_key` (the hash includes per-candidate `mtime`)
        # and `batch_save` would write multiple rows for one tracker, breaking
        # the one-row-per-tracker invariant.
        valid_candidates_by_tracker = {}
        validation_failures = []
        for drilldown_record in drilldown_records:
            try:
                tracker_name = normalize_flx_tracker_name(
                    tenant_id, drilldown_record.get("tracker_name")
                )
                drilldown_search = drilldown_record.get("drilldown_search")
                drilldown_search_earliest = drilldown_record.get("drilldown_search_earliest")
                drilldown_search_latest = drilldown_record.get("drilldown_search_latest")

                if not tracker_name:
                    raise ValueError("tracker_name is required")
                if not drilldown_search:
                    raise ValueError("drilldown_search is required")
                if not drilldown_search_earliest:
                    raise ValueError("drilldown_search_earliest is required")
                if not drilldown_search_latest:
                    raise ValueError("drilldown_search_latest is required")

                valid_candidates_by_tracker[tracker_name] = {
                    "tracker_name": tracker_name,
                    "drilldown_search": drilldown_search,
                    "drilldown_search_earliest": drilldown_search_earliest,
                    "drilldown_search_latest": drilldown_search_latest,
                    "mtime": time.time(),
                }
            except Exception as e:
                validation_failures.append(
                    {
                        "tracker_name": drilldown_record.get("tracker_name", "unknown"),
                        "action": "error",
                        "result": "failure",
                        "exception": f"Failed to process drilldown record: {str(e)}",
                    }
                )
                logger.error(f"Failed to process drilldown record: {str(e)}")

        # Pre-load existing drilldown records for the candidate tracker_names in
        # a single broad query (the drilldown collection has at most one row per
        # tracker, so this is bounded and cheap). If this query fails we must
        # NOT fall back to an empty dict (that would treat every tracker as new
        # and create duplicate rows alongside the existing one-per-tracker rows,
        # breaking the invariant); abort with 500 so the caller can retry.
        existing_by_tracker_name = {}
        if valid_candidates_by_tracker:
            try:
                existing_records = collection.data.query(query=json.dumps({}))
            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", failed to pre-load existing drilldown records, aborting bulk seed to avoid duplicate inserts, exception="{str(e)}"'
                )
                return {
                    "payload": {
                        "error": (
                            f"Failed to pre-load existing drilldown records for tenant_id='{tenant_id}'; "
                            f"refusing to proceed to avoid duplicate KV records. Underlying error: {str(e)}"
                        ),
                        "tenant_id": tenant_id,
                    },
                    "status": 500,
                }
            for r in existing_records:
                t = r.get("tracker_name")
                if t is not None:
                    existing_by_tracker_name[t] = r

        # Build the upsert list. _key reused for updates, freshly hashed otherwise.
        records_to_upsert = []
        inserted_count = 0
        updated_count = 0
        for candidate in valid_candidates_by_tracker.values():
            existing = existing_by_tracker_name.get(candidate["tracker_name"])
            if existing:
                candidate["_key"] = existing.get("_key")
                updated_count += 1
            else:
                candidate["_key"] = hashlib.sha256(
                    json.dumps(candidate, sort_keys=True).encode("utf-8")
                ).hexdigest()
                inserted_count += 1
            records_to_upsert.append(candidate)

        task_instance_id = str(uuid.uuid4())
        successful_updates = 0
        failed_updates = 0
        if records_to_upsert:
            try:
                batch_result = batch_update_worker(
                    collection_name,
                    collection,
                    records_to_upsert,
                    request_info.user,
                    task_instance_id,
                    task_name="flx_drilldown_seed",
                    max_multi_thread_workers=8,
                )
                successful_updates = batch_result.get("successful_updates", 0)
                failed_updates = batch_result.get("failed_updates", 0)
            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", batch drilldown upsert failed, exception="{str(e)}"'
                )
                failed_updates = len(records_to_upsert)

        # Aggregated audit event for the bulk-seed path. Single-tracker edits via
        # other endpoints retain per-record audit.
        sample_tracker_names = [c["tracker_name"] for c in records_to_upsert[:10]]
        total_failures = failed_updates + len(validation_failures)
        audit_status = "success" if total_failures == 0 else "failure"
        if records_to_upsert or validation_failures:
            try:
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    request_info.user,
                    audit_status,
                    "update drilldown searches (bulk)",
                    f"trackers={len(records_to_upsert)}",
                    "splk-flx",
                    {
                        "inserted_count": inserted_count,
                        "updated_count": updated_count,
                        "failed_updates": failed_updates,
                        "validation_failures": len(validation_failures),
                        "sample_tracker_names": sample_tracker_names,
                    },
                    f"Bulk drilldown seed: {inserted_count} inserted, {updated_count} updated, {total_failures} failed",
                    str(update_comment),
                )
            except Exception as e:
                logger.error(
                    f'failed to generate an audit event with exception="{str(e)}"'
                )

        logger.info(
            f'tenant_id="{tenant_id}", task_instance_id={task_instance_id}, '
            f'flx_drilldown_seed inserted_count={inserted_count}, updated_count={updated_count}, '
            f'failed_updates={failed_updates}, validation_failures={len(validation_failures)}, '
            f'full_tracker_names={json.dumps([c["tracker_name"] for c in records_to_upsert])}'
        )

        if records_to_upsert:
            records.append(
                {
                    "action": "bulk_upsert",
                    "result": audit_status,
                    "inserted_count": inserted_count,
                    "updated_count": updated_count,
                    "failed_updates": failed_updates,
                    "sample_tracker_names": sample_tracker_names,
                }
            )
        records.extend(validation_failures)

        # call trackme_register_tenant_component_summary
        thread = threading.Thread(
            target=self.register_component_summary_async,
            args=(
                request_info.session_key,
                request_info.server_rest_uri,
                tenant_id,
                "flx",
            ),
        )
        thread.start()

        processed_count = len(records_to_upsert) + len(validation_failures)
        success_count = successful_updates

        req_summary = {
            "process_count": processed_count,
            "success_count": success_count,
            "failures_count": total_failures,
            "records": records,
        }

        if processed_count > 0 and total_failures == 0:
            return {"payload": req_summary, "status": 200}
        else:
            return {"payload": req_summary, "status": 500}

    # Delete drilldown search definitions for Flex Objects
    def post_flx_delete_drilldown_searches(self, request_info, **kwargs):
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
                            "response": "The tenant_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    keys_list = extract_keys_list(resp_dict)
                    if isinstance(keys_list, str):
                        keys_list = keys_list.split(",")
                    elif not isinstance(keys_list, list):
                        return {
                            "payload": {
                                "error": "keys_list must be a list or comma-separated string"
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The keys_list is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes drilldown search definitions for Flex Objects, it requires a POST call with the following information:",
                "resource_desc": "Delete drilldown search definitions for Flex Objects",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/write/flx_delete_drilldown_searches\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'keys_list': 'key1,key2,key3'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "keys_list": "Comma-separated list of record keys (_key) to delete from the drilldown searches collection",
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

        # counters
        processed_count = 0
        success_count = 0
        failures_count = 0

        # records summary
        records = []

        # Data collection
        collection_name = f"kv_trackme_flx_drilldown_searches_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Process each key to delete
        for key in keys_list:
            try:
                # Get the current record before deleting to get tracker_name for audit
                try:
                    record = collection.data.query_by_id(key)
                    tracker_name = record.get("tracker_name", "unknown")
                except Exception as e:
                    # Record doesn't exist, skip it
                    logger.warning(f'Record with key="{key}" not found, skipping deletion')
                    continue

                # Delete the record
                collection.data.delete(json.dumps({"_key": key}))

                # Record an audit change
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        "delete drilldown search",
                        tracker_name,
                        "splk-flx",
                        record,
                        "Drilldown search was deleted successfully",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                # increment counters
                processed_count += 1
                success_count += 1

                # append for summary
                result = {
                    "key": key,
                    "tracker_name": tracker_name,
                    "action": "delete",
                    "result": "success",
                    "message": "Drilldown search was deleted successfully",
                }
                records.append(result)
                logger.info(f'Deleted drilldown search for tracker="{tracker_name}" with key="{key}"')

            except Exception as e:
                # increment counters
                processed_count += 1
                failures_count += 1

                result = {
                    "key": key,
                    "action": "delete",
                    "result": "failure",
                    "exception": f'Failed to delete drilldown search: {str(e)}',
                }
                records.append(result)
                logger.error(f'Failed to delete drilldown search with key="{key}": {str(e)}')

        # call trackme_register_tenant_component_summary
        thread = threading.Thread(
            target=self.register_component_summary_async,
            args=(
                request_info.session_key,
                request_info.server_rest_uri,
                tenant_id,
                "flx",
            ),
        )
        thread.start()

        # render HTTP status and summary
        req_summary = {
            "process_count": processed_count,
            "success_count": success_count,
            "failures_count": failures_count,
            "records": records,
        }

        if processed_count > 0 and processed_count == success_count:
            return {"payload": req_summary, "status": 200}
        else:
            return {"payload": req_summary, "status": 500}

    # Update default metric definitions for Flex Objects
    def post_flx_update_default_metrics(self, request_info, **kwargs):
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
                            "response": "The tenant_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    default_metric_records = resp_dict["default_metric_records"]
                    if not isinstance(default_metric_records, list):
                        # try loading as a json string, if failed return
                        try:
                            default_metric_records = json.loads(default_metric_records)
                        except Exception as e:
                            return {
                                "payload": {
                                    "error": "default_metric_records must be a list of records or a JSON string containing a list of records"
                                },
                                "status": 500,
                            }
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The default_metric_records list is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint defines or updates default metric definitions for Flex Objects, it requires a POST call with the following information:",
                "resource_desc": "Define or update default metric definitions for Flex Objects",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/write/flx_update_default_metrics\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'default_metric_records': [{'tracker_name': 'mytracker', 'metric_name': 'cpu_usage'}]}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "default_metric_records": "List of default metric records. Each record must contain:",
                        "default_metric_records_fields": {
                            "tracker_name": "The name of the associated tracker",
                            "metric_name": "The name of the default metric (string) or array of metric names. Multiple records with the same tracker_name will be grouped together, replacing all existing metrics for that tracker.",
                        },
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

        # counters
        processed_count = 0
        success_count = 0
        failures_count = 0

        # records summary
        records = []

        # Data collection
        collection_name = f"kv_trackme_flx_default_metric_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Group records by tracker_name to support multiple metrics per tracker
        # Structure: {tracker_name: [metric_name1, metric_name2, ...]}
        tracker_metrics_map = {}
        for default_metric_record in default_metric_records:
            try:
                tracker_name = normalize_flx_tracker_name(tenant_id, default_metric_record.get("tracker_name"))
                metric_name = default_metric_record.get("metric_name")

                if not tracker_name:
                    raise ValueError("tracker_name is required")
                if not metric_name:
                    raise ValueError("metric_name is required")

                # Handle both string and array formats for backward compatibility
                if isinstance(metric_name, list):
                    metric_names = metric_name
                elif isinstance(metric_name, str):
                    metric_names = [metric_name]
                else:
                    raise ValueError("metric_name must be a string or array of strings")

                # Filter out falsy values and validate we have at least one valid metric
                valid_metrics = [m for m in metric_names if m and isinstance(m, str) and m.strip()]

                if not valid_metrics:
                    raise ValueError(f"metric_name must contain at least one non-empty string value, got: {metric_name}")

                # Group metrics by tracker
                if tracker_name not in tracker_metrics_map:
                    tracker_metrics_map[tracker_name] = []

                # Add all valid metrics for this tracker (avoid duplicates)
                for m in valid_metrics:
                    if m not in tracker_metrics_map[tracker_name]:
                        tracker_metrics_map[tracker_name].append(m)

            except Exception as e:
                # increment counters
                processed_count += 1
                failures_count += 1

                result = {
                    "tracker_name": default_metric_record.get("tracker_name", "unknown"),
                    "action": "error",
                    "result": "failure",
                    "exception": f'Failed to process default metric record: {str(e)}',
                }
                records.append(result)
                logger.error(f'Failed to process default metric record: {str(e)}')

        # Process each tracker with its metrics. Per-tracker isolation is preserved
        # (the existing delete-then-insert contract): a failure in one tracker's
        # records does not affect other trackers. The per-record loops are
        # replaced by a single batched delete + a single batched insert per tracker,
        # which scales the on-demand seed of new trackers from the parse path.
        for tracker_name, metric_names in tracker_metrics_map.items():
            try:
                # Safety check: skip trackers with empty metric lists to prevent silent deletion
                if not metric_names or len(metric_names) == 0:
                    logger.warning(f'Skipping tracker "{tracker_name}" with empty metric list to prevent data loss')
                    continue

                # Find all existing records for this tracker (single query). We
                # keep their _keys around for the post-insert delete; the records
                # themselves stay in KV until that delete fires - if anything
                # below fails before we get there, the previous state is
                # preserved.
                existing_records = collection.data.query(
                    query=json.dumps({"tracker_name": tracker_name})
                )
                existing_keys = [
                    r.get("_key") for r in existing_records if r.get("_key")
                ]
                existing_count = len(existing_keys)

                # Build the new records to insert (one per metric) with random
                # SHA256 _keys (matches the prior, mtime-seeded scheme). These
                # are distinct from any existing _key so insert-then-delete
                # produces a brief duplicate-rows window for the tracker, NOT
                # a key collision.
                new_records = []
                for metric_name in metric_names:
                    record_data = {
                        "tracker_name": tracker_name,
                        "metric_name": metric_name,
                        "mtime": time.time(),
                    }
                    record_data["_key"] = hashlib.sha256(
                        json.dumps(record_data, sort_keys=True).encode("utf-8")
                    ).hexdigest()
                    new_records.append(record_data)

                # --------------------------------------------------------------
                # Insert FIRST. The previous flow deleted all existing rows
                # before calling batch_update_worker, so a KV-store timeout
                # mid-insert (the worker retries each chunk 3 times, then
                # gives up) would leave the tracker with zero metrics and no
                # rollback path. Insert-then-delete preserves the existing
                # state on any insert failure - the caller can retry and the
                # next call self-heals (it sees the old rows, treats them as
                # `existing_keys`, and re-applies insert-then-delete on top).
                # --------------------------------------------------------------
                inserted_count = 0
                failed_insert_count = 0
                if new_records:
                    try:
                        batch_result = batch_update_worker(
                            collection_name,
                            collection,
                            new_records,
                            request_info.user,
                            str(uuid.uuid4()),
                            task_name="flx_default_metrics_seed",
                            max_multi_thread_workers=8,
                        )
                        inserted_count = batch_result.get("successful_updates", 0)
                        failed_insert_count = batch_result.get("failed_updates", 0)
                    except Exception as e:
                        logger.error(
                            f'Failed batched insert for tracker="{tracker_name}": {str(e)}'
                        )
                        failed_insert_count = len(new_records)

                # Insert failure path: abort this tracker without deleting the
                # existing rows. The collection state for this tracker either
                # stays exactly as it was (zero new records landed) or holds
                # both the old rows AND a partial set of new rows (some chunks
                # succeeded before the failure). Either way, no data loss -
                # the next call re-queries `existing_keys` and re-runs
                # insert-then-delete on top of the partial state.
                if failed_insert_count > 0:
                    error_msg = (
                        f'Insert failure for tracker="{tracker_name}": '
                        f'inserted_count={inserted_count}, failed_insert_count={failed_insert_count} '
                        f'of {len(metric_names)} metric(s). Existing {existing_count} record(s) preserved; '
                        f'no delete performed. Caller should retry.'
                    )
                    logger.error(error_msg)
                    processed_count += 1
                    failures_count += failed_insert_count
                    records.append(
                        {
                            "tracker_name": tracker_name,
                            "action": "error",
                            "result": "failure",
                            "inserted_count": inserted_count,
                            "failed_insert_count": failed_insert_count,
                            "existing_count": existing_count,
                            "exception": (
                                f'Insert failure: {failed_insert_count} of {len(metric_names)} metric(s) failed; '
                                f'existing {existing_count} record(s) preserved (no data loss). '
                                f'Retry will reconcile state.'
                            ),
                        }
                    )
                    continue

                # Insert fully succeeded. Now safe to delete the old rows.
                # The duplicate-rows window for this tracker (old + new) is
                # open from here until the delete returns. If the delete fails
                # we treat the request as successful (the new rows are
                # in place) but log a warning - the leaked old rows are
                # recoverable on the next call (which will pick them up as
                # `existing_keys` and clean them up via the same flow).
                deleted_count = 0
                deleted_keys = []
                if existing_keys:
                    try:
                        collection.data.delete(
                            json.dumps({"_key": {"$in": existing_keys}})
                        )
                        deleted_count = len(existing_keys)
                        deleted_keys = list(existing_keys)
                    except Exception as e:
                        logger.warning(
                            f'Post-insert batched $in delete failed for tracker="{tracker_name}", '
                            f'falling back to per-record delete (any remaining old rows leak '
                            f'temporarily and self-heal on the next call), exception="{str(e)}"'
                        )
                        for record_key in existing_keys:
                            try:
                                collection.data.delete(json.dumps({"_key": record_key}))
                                deleted_count += 1
                                deleted_keys.append(record_key)
                            except Exception as e_inner:
                                logger.warning(
                                    f'Failed to delete existing record for tracker="{tracker_name}": {str(e_inner)}'
                                )

                # Success path. inserted_count > 0 is implied here (we already
                # bailed out above on any insert failure). The action label
                # remains "update" when we actually deleted existing rows,
                # "insert" otherwise - matches the previous response contract.
                processed_count += 1
                success_count += 1
                action = "update" if deleted_count > 0 else "insert"
                result_label = "success"
                result_message = f'Default metrics ({inserted_count} metric(s)) were {action}d successfully'
                audit_status = "success"

                logger.info(
                    f'Updated default metrics for tracker="{tracker_name}": '
                    f'inserted_count={inserted_count}, deleted_count={deleted_count}, '
                    f'existing_count={existing_count}, leaked_old_count={existing_count - deleted_count} '
                    f'(insert-first ordering; leaked_old_count self-heals on next call)'
                )

                # Aggregated audit event per tracker (replaces N per-metric events).
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        audit_status,
                        f"{action} default metrics (bulk)",
                        tracker_name,
                        "splk-flx",
                        {
                            "tracker_name": tracker_name,
                            "metric_names": metric_names,
                            "existing_count": existing_count,
                            "inserted_count": inserted_count,
                            "deleted_count": deleted_count,
                            "failed_insert_count": failed_insert_count,
                        },
                        result_message,
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                records.append(
                    {
                        "tracker_name": tracker_name,
                        "metric_name": ", ".join(metric_names),
                        "action": action,
                        "result": result_label,
                        "inserted_count": inserted_count,
                        "deleted_count": deleted_count,
                        "existing_count": existing_count,
                        "message": result_message,
                    }
                )

            except Exception as e:
                processed_count += 1
                failures_count += 1
                records.append(
                    {
                        "tracker_name": tracker_name,
                        "action": "error",
                        "result": "failure",
                        "exception": f'Failed to process tracker: {str(e)}',
                    }
                )
                logger.error(f'Failed to process tracker "{tracker_name}": {str(e)}')

        # call trackme_register_tenant_component_summary
        thread = threading.Thread(
            target=self.register_component_summary_async,
            args=(
                request_info.session_key,
                request_info.server_rest_uri,
                tenant_id,
                "flx",
            ),
        )
        thread.start()

        # render HTTP status and summary
        req_summary = {
            "process_count": processed_count,
            "success_count": success_count,
            "failures_count": failures_count,
            "records": records,
        }

        if processed_count > 0 and processed_count == success_count:
            return {"payload": req_summary, "status": 200}
        else:
            return {"payload": req_summary, "status": 500}

    # Delete default metric definitions for Flex Objects
    def post_flx_delete_default_metrics(self, request_info, **kwargs):
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
                            "response": "The tenant_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    keys_list = extract_keys_list(resp_dict)
                    if isinstance(keys_list, str):
                        keys_list = keys_list.split(",")
                    elif not isinstance(keys_list, list):
                        return {
                            "payload": {
                                "error": "keys_list must be a list or comma-separated string"
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The keys_list is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes default metric definitions for Flex Objects, it requires a POST call with the following information:",
                "resource_desc": "Delete default metric definitions for Flex Objects",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/write/flx_delete_default_metrics\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'keys_list': 'key1,key2'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "keys_list": "List of keys to delete, provided as a comma separated list of keys",
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

        # counters
        processed_count = 0
        success_count = 0
        failures_count = 0

        # records summary
        records = []

        # Data collection
        collection_name = f"kv_trackme_flx_default_metric_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Process each key for deletion
        for key in keys_list:
            try:
                # Get the record before deletion for audit purposes
                try:
                    existing_record = collection.data.query_by_id(key)
                    tracker_name = existing_record.get("tracker_name", "unknown")
                except Exception as e:
                    tracker_name = "unknown"

                # Delete the record
                collection.data.delete(json.dumps({"_key": key}))

                # Record an audit change
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        "delete default metric",
                        tracker_name,
                        "splk-flx",
                        {"_key": key, "tracker_name": tracker_name},
                        "Default metric was deleted successfully",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                # increment counters
                processed_count += 1
                success_count += 1

                # append for summary
                result = {
                    "key": key,
                    "tracker_name": tracker_name,
                    "action": "delete",
                    "result": "success",
                    "message": "Default metric was deleted successfully",
                }
                records.append(result)
                logger.info(f'Deleted default metric for tracker="{tracker_name}" with key="{key}"')

            except Exception as e:
                # increment counters
                processed_count += 1
                failures_count += 1

                result = {
                    "key": key,
                    "action": "delete",
                    "result": "failure",
                    "exception": f'Failed to delete default metric: {str(e)}',
                }
                records.append(result)
                logger.error(f'Failed to delete default metric with key="{key}": {str(e)}')

        # call trackme_register_tenant_component_summary
        thread = threading.Thread(
            target=self.register_component_summary_async,
            args=(
                request_info.session_key,
                request_info.server_rest_uri,
                tenant_id,
                "flx",
            ),
        )
        thread.start()

        # render HTTP status and summary
        req_summary = {
            "process_count": processed_count,
            "success_count": success_count,
            "failures_count": failures_count,
            "records": records,
        }

        if processed_count > 0 and processed_count == success_count:
            return {"payload": req_summary, "status": 200}
        else:
            return {"payload": req_summary, "status": 500}
