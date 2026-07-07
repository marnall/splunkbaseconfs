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
    "trackme.rest.splk_fqm_power", "trackme_rest_api_splk_fqm_power.log"
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
    persistent_fields_fqm,
)

# import trackme libs bulk edit
from trackme_libs_bulk_edit import post_bulk_edit, generic_batch_update
from trackme_libs_shadow import delete_shadow_records

# import batched KV upsert helper (used to bulk-seed tracker-discovered records)
from trackme_libs_kvstore_batch import batch_update_worker

# import trackme libs utils
from trackme_libs_utils import interpret_boolean, strict_interpret_boolean

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkFqmTrackingWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkFqmTrackingWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_fqm(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_fqm/write",
            "resource_group_desc": "Endpoints specific to the splk-fqm TrackMe component (Splunk Flex objects tracking, power operations)",
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
    def post_fqm_bulk_edit(self, request_info, **kwargs):
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
            component_name="fqm",
            persistent_fields=persistent_fields_fqm,
            collection_name_suffix="fqm",
            endpoint_suffix="fqm",
            function_name="fqm_bulk_edit",
            **kwargs,
        )

        return {
            "payload": response,
            "status": http_status,
        }

    # Update priority by object name
    def post_fqm_update_priority(self, request_info, **kwargs):

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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/write/fqm_update_priority\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'priority': 'high', 'object_list': 'Okta:Splunk_TA_okta_identity_cloud:okta_logs'}\"",
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
        collection_name = f"kv_trackme_fqm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "fqm",
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
            persistent_fields=persistent_fields_fqm,
            component="fqm",
            update_comment=update_comment,
            audit_context="update priority",
            audit_message="Priority was updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Enable/Disable monitoring by object name
    def post_fqm_monitoring(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/write/fqm_monitoring\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'action': 'disable', 'object_list': 'Okta:Splunk_TA_okta_identity_cloud:okta_logs'}\"",
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
        collection_name = f"kv_trackme_fqm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "fqm",
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
            persistent_fields=persistent_fields_fqm,
            component="fqm",
            update_comment=update_comment,
            audit_context="update monitoring",
            audit_message="Monitoring state was updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Remove entities
    def post_fqm_delete(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/write/fqm_delete\" mode=\"post\" body=\"{'tenant_id':'mytenant', 'deletion_type': 'temporary', 'object_list':'Okta:Splunk_TA_okta_identity_cloud:okta_logs'}\"",
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
        collection_name = f"kv_trackme_fqm_tenant_{tenant_id}"
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
            f"kv_trackme_fqm_outliers_entity_rules_tenant_{tenant_id}"
        )
        collection_entity_rules = service.kvstore[collection_outliers_entity_rules_name]

        # data rules collection
        collection_outliers_entity_data_name = (
            f"kv_trackme_fqm_outliers_entity_data_tenant_{tenant_id}"
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
                                    {"object": obj, "object_category": "splk-fqm"}
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
                                    "object_category": "splk-fqm",
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
                        "object_category": "splk-fqm",
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
                    delete_shadow_records(service_system, tenant_id, "fqm", deleted_keys, shadow_enabled=shadow_enabled)
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
                "fqm",
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
    def post_fqm_update_wdays(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/write/fqm_update_wdays\" mode=\"post\" body=\"{'tenant_id':'mytenant','object_list':'netscreen:netscreen:firewall','monitoring_wdays':'manual:1,2,3,4,5'}\"",
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
        collection_name = f"kv_trackme_fqm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "fqm",
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
            persistent_fields=persistent_fields_fqm,
            component="fqm",
            update_comment=update_comment,
            audit_context="update week days monitoring",
            audit_message="Week days monitoring was updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Update monitoring hours ranges by object name
    def post_fqm_update_hours_ranges(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/write/fqm_update_hours_ranges\" mode=\"post\" body=\"{'tenant_id':'mytenant', 'object_list':'netscreen:netscreen:firewall', 'monitoring_hours_ranges':'manual:8,9,10,11,12,13,14,15,16,17'}\"",
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
        collection_name = f"kv_trackme_fqm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "fqm",
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
            persistent_fields=persistent_fields_fqm,
            component="fqm",
            update_comment=update_comment,
            audit_context="update hours ranges monitoring",
            audit_message="Monitoring hours ranges were updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Update monitoring time policy and rules by object name
    def post_fqm_update_monitoring_time(self, request_info, **kwargs):
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
                "describe": "This endpoint configures the monitoring time policy and rules for an existing fields quality monitoring entity, it requires a POST call with the following information:",
                "resource_desc": "Update monitoring time policy/rules for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/write/fqm_update_monitoring_time\" mode=\"post\" body=\"{'tenant_id':'mytenant','object_list':'index:sourcetype:fieldname','monitoring_time_policy':'business_days_08h_20h'}\"",
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
        collection_name = f"kv_trackme_fqm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "fqm",
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
            persistent_fields=persistent_fields_fqm,
            component="fqm",
            update_comment=update_comment,
            audit_context="update monitoring time policy/rules",
            audit_message="Monitoring time policy/rules were updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Update list of manual tags
    def post_fqm_update_manual_tags(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/write/fqm_update_manual_tags\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'tags_manual': 'mytag1,maytag2,mytag3', 'object_list': 'netscreen:netscreen:firewall,wineventlog:WinEventLog'}\"",
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
        collection_name = f"kv_trackme_fqm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Tags policies collection
        collection_tags_policies_name = f"kv_trackme_fqm_tags_tenant_{tenant_id}"
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
                    "splk-fqm",
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
                "fqm",
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
    def post_fqm_update_sla_class(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/write/fqm_update_sla_class\" mode=\"post\" body=\"{'tenant_id':'mytenant','object_list':'netscreen:netscreen:firewall','sla_class':'gold'}\"",
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
        collection_name = f"kv_trackme_fqm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "fqm",
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
            persistent_fields=persistent_fields_fqm,
            component="fqm",
            update_comment=update_comment,
            audit_context="update SLA class",
            audit_message="SLA class was updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Add new policy
    def post_fqm_thresholds_add(self, request_info, **kwargs):

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

                    # Create threshold object
                    threshold_record = {
                        "metric_name": metric_name,
                        "value": value,
                        "operator": operator,
                        "condition_true": condition_true,
                        "mtime": time.time(),
                        "comment": comment,
                        "score": score,
                    }

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
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_fqm/write/fqm_thresholds_add\" body=\"{'tenant_id': 'mytenant', 'keys_list': 'object1,object2', 'metric_name': 'error_count', 'value': 1000, 'operator': '>', 'condition_true': 1, 'comment': 'Alert on high error count'}\"",
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
        collection_name = f"kv_trackme_fqm_thresholds_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Pre-load existing thresholds for this metric_name in a single query, then
        # index by object_id. Replaces a per-record query/insert loop that scaled
        # linearly with the entity count and dominated the FQM tracker
        # first-execution time at large scale. If this query fails we must NOT
        # fall back to an empty set (that would treat every entity as new and
        # create duplicate KV rows with fresh sha256 _keys alongside the existing
        # ones); abort with 500 so the caller can retry.
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

        records_to_upsert = []
        planned_insert_count = 0
        planned_update_count = 0
        score_provided = "score" in resp_dict
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
                task_name="fqm_thresholds_seed",
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

        # The "planned_*" counters reflect what the merge loop classified before
        # the batch_save call; "written" and "failed" come from the
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
                "splk-fqm",
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
            f'fqm_thresholds_seed planned_insert_count={planned_insert_count}, planned_update_count={planned_update_count}, '
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
    def post_fqm_thresholds_del(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_fqm/write/fqm_thresholds_del\" body=\"{'tenant_id': 'mytenant', 'keys_list': 'key1,key2'}\"",
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
        collection_name = f"kv_trackme_fqm_thresholds_tenant_{tenant_id}"
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
                        "splk-fqm",
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
                        "splk-fqm",
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
    def post_fqm_thresholds_update(self, request_info, **kwargs):
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
                "describe": "This endpoint updates multiple thresholds for fqm objects, it requires a POST call with the following information:",
                "resource_desc": "Update multiple thresholds",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/write/fqm_thresholds_update\" mode=\"post\" body=\"{'tenant_id':'mytenant','records_list':[{'key':'key1','metric_name':'error_count','value':1000,'operator':'>','condition_true':'1','comment':'Alert on high error count'}]}\"",
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
        collection_name = f"kv_trackme_fqm_thresholds_tenant_{tenant_id}"
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

                if (
                    current_record["value"] != record["value"]
                    or current_record["operator"] != record["operator"]
                    or current_record["condition_true"] != record["condition_true"]
                    or current_record.get("comment", "") != record.get("comment", "")
                    or current_score != record_score
                ):
                    # Ensure score is included in the record
                    record["score"] = record_score
                    # Preserve fields that might not be in the update record
                    if "metric_name" not in record:
                        record["metric_name"] = current_record.get("metric_name")
                    if "object_id" not in record:
                        record["object_id"] = current_record.get("object_id")
                    record["mtime"] = time.time()

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
                            "splk-fqm",
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
                        "splk-fqm",
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
    def post_fqm_thresholds_update_bulk(self, request_info, **kwargs):
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
                "describe": "This endpoint bulk updates thresholds for fqm objects, it requires a POST call with the following information:",
                "resource_desc": "Bulk update multiple thresholds",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/write/fqm_thresholds_update_bulk\" mode=\"post\" body=\"{'tenant_id':'mytenant','component':'fqm','keys_list':['key1','key2'],'record_changes':{'kpi_metric_name':'error_count','kpi_metric_value':1000,'operator':'>','condition_true':'1'},'update_comment':'Bulk update thresholds'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "Component identifier (e.g., 'fqm')",
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
            logger.info(f'endpoint fqm_thresholds_update_bulk, processed_count="{processed_count}", success_count="{success_count}", nothing to be done, returning 200')
        elif processed_count == success_count:
            logger.info(f'endpoint fqm_thresholds_update_bulk, processed_count="{processed_count}", success_count="{success_count}", thresholds records updated successfully, returning 200')
            return {"payload": req_summary, "status": 200}
        else:
            logger.info(f'endpoint fqm_thresholds_update_bulk, processed_count="{processed_count}", success_count="{success_count}", returning 500')
            return {"payload": req_summary, "status": 500}

    # Update a data dictionary definition
    def post_fqm_update_data_dictionary(self, request_info, **kwargs):
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
                    if not tenant_id or len(tenant_id) == 0:
                        return {
                            "payload": "tenant_id is required, please provide a valid tenant_id",
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": "tenant_id is required, please provide a valid tenant_id",
                        "status": 500,
                    }

                try:
                    dictionary_name = resp_dict["dictionary_name"]
                    if not dictionary_name or len(dictionary_name) == 0:
                        return {
                            "payload": "dictionary_name is required, please provide a valid dictionary_name",
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": "dictionary_name is required, please provide a valid dictionary_name",
                        "status": 500,
                    }

                try:
                    action = resp_dict["action"]
                    if not action or len(action) == 0 or action not in ["update_fields", "add_field", "delete_fields"]:
                        return {
                            "payload": "action is required, please provide a valid action",
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": "action is required, please provide a valid action",
                        "status": 500,
                    }

                try:
                    fields_list = resp_dict["fields_list"]
                    if not fields_list or len(fields_list) == 0:
                        return {
                            "payload": "fields_list is required, please provide a valid fields_list",
                            "status": 500,
                        }
                    if isinstance(fields_list, str):
                        fields_list = json.loads(fields_list)
                except Exception as e:
                    return {
                        "payload": "fields_list is required, please provide a valid fields_list",
                        "status": 500,
                    }

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint updates data dictionary fields, it requires a POST call with the following information:",
                "resource_desc": "Update data dictionary fields",
                "resource_spl_example": '| trackme mode=post url=/services/trackme/v2/splk_fqm/write/fqm_update_data_dictionary body="'
                + "{'tenant_id': 'test001', 'dictionary_name': 'WinEventLog', 'fields_list': '[{'field_name':'action','allow_unknown':true,'allow_empty_or_missing':false,'regex':'^(success|failure|allowed|blocked|deferred)$'}]'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "dictionary_name": "The name of the data dictionary to update",
                        "action": "The action to perform: update_fields, add_field, delete_fields",
                        "fields_list": "JSON array of field definitions to update/add/delete",
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
        collection_name = f"kv_trackme_fqm_data_dictionary_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Define the KV query to find the dictionary by name
        query_string = {"name": dictionary_name}

        # Get the current dictionary record
        try:
            kvrecords = collection.data.query(query=json.dumps(query_string))
            if not kvrecords:
                return {
                    "payload": f"dictionary_name={dictionary_name} not found in tenant {tenant_id}",
                    "status": 404,
                }

            dictionary_kvrecord = kvrecords[0]
            dictionary_kvrecord_key = dictionary_kvrecord.get("_key")

        except Exception as e:
            return {
                "payload": f"Failed to retrieve dictionary {dictionary_name}: {str(e)}",
                "status": 500,
            }

        # Get the current json_dict from the record
        try:
            current_json_dict_str = dictionary_kvrecord.get("json_dict")
            if not current_json_dict_str:
                return {
                    "payload": f"dictionary {dictionary_name} has no json_dict field",
                    "status": 500,
                }
            current_json_dict = json.loads(current_json_dict_str)
        except Exception as e:
            return {
                "payload": f"Failed to parse json_dict for dictionary {dictionary_name}: {str(e)}",
                "status": 500,
            }

        logger.debug(f'fields_list="{json.dumps(fields_list, indent=0)}"')
        logger.debug(f'current_json_dict="{json.dumps(current_json_dict, indent=0)}"')

        processed_count = 0
        success_count = 0
        failures_count = 0
        affected_fields = []
        failed_fields = []
        action_performed = action

        if action == "update_fields":
            for field_item in fields_list:
                processed_count += 1
                try:
                    field_name = field_item.get("field_name")
                    if not field_name:
                        raise ValueError("field_name is required for each field item")
                    if field_name not in current_json_dict:
                        raise ValueError(f"Field '{field_name}' does not exist in the current dictionary")
                    current_field = current_json_dict[field_name]
                    regex = field_item.get("regex", current_field.get("regex", ".*"))
                    if not regex or len(regex) == 0:
                        regex = ".*"
                    updated_field = {
                        "name": field_name,
                        "regex": regex,
                        "allow_unknown": strict_interpret_boolean(field_item.get("allow_unknown", current_field.get("allow_unknown", False))),
                        "allow_empty_or_missing": strict_interpret_boolean(field_item.get("allow_empty_or_missing", current_field.get("allow_empty_or_missing", False))),
                    }
                    current_json_dict[field_name] = updated_field
                    success_count += 1
                    affected_fields.append(field_name)
                    logger.info(f"Successfully updated field '{field_name}' in dictionary '{dictionary_name}'")
                except Exception as e:
                    failures_count += 1
                    failed_fields.append({"field": field_item.get("field_name", "<unknown>"), "error": str(e)})
                    logger.error(f"Failed to update field in dictionary '{dictionary_name}': {str(e)}")
                    continue
        elif action == "add_field":
            for field_item in fields_list:
                processed_count += 1
                try:
                    field_name = field_item.get("field_name")
                    if not field_name:
                        raise ValueError("field_name is required for each field item")
                    if field_name in current_json_dict:
                        raise ValueError(f"Field '{field_name}' already exists in the current dictionary")
                    regex = field_item.get("regex", ".*")
                    if not regex or len(regex) == 0:
                        regex = ".*"
                    # Add the new field
                    new_field = {
                        "name": field_name,
                        "regex": regex,
                        "allow_unknown": strict_interpret_boolean(field_item.get("allow_unknown", False)),
                        "allow_empty_or_missing": strict_interpret_boolean(field_item.get("allow_empty_or_missing", False)),
                    }
                    current_json_dict[field_name] = new_field
                    success_count += 1
                    affected_fields.append(field_name)
                    logger.info(f"Successfully added field '{field_name}' to dictionary '{dictionary_name}'")
                except Exception as e:
                    failures_count += 1
                    failed_fields.append({"field": field_item.get("field_name", "<unknown>"), "error": str(e)})
                    logger.error(f"Failed to add field to dictionary '{dictionary_name}': {str(e)}")
                    continue
        elif action == "delete_fields":
            for field_item in fields_list:
                processed_count += 1
                try:
                    # Accept either a dict with field_name or a string
                    if isinstance(field_item, dict):
                        field_name = field_item.get("field_name")
                    else:
                        field_name = field_item
                    if not field_name:
                        raise ValueError("field_name is required for each field item")
                    if field_name not in current_json_dict:
                        raise ValueError(f"Field '{field_name}' does not exist in the current dictionary")
                    del current_json_dict[field_name]
                    success_count += 1
                    affected_fields.append(field_name)
                    logger.info(f"Successfully deleted field '{field_name}' from dictionary '{dictionary_name}'")
                except Exception as e:
                    failures_count += 1
                    failed_fields.append({"field": field_item if isinstance(field_item, str) else field_item.get("field_name", "<unknown>"), "error": str(e)})
                    logger.error(f"Failed to delete field from dictionary '{dictionary_name}': {str(e)}")
                    continue
        else:
            return {
                "payload": f"Invalid action: {action}",
                "status": 500,
            }

        # Update the KVstore record with the modified json_dict
        if success_count > 0:
            try:
                collection.data.update(
                    str(dictionary_kvrecord_key),
                    json.dumps({
                        "name": dictionary_name,
                        "json_dict": json.dumps(current_json_dict, indent=2),
                        "mtime": time.time(),
                    })
                )
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    request_info.user,
                    "success",
                    f"{action_performed} data dictionary",
                    dictionary_name,
                    "splk-fqm",
                    json.dumps({"affected_fields": affected_fields, "fields_list": fields_list, "action": action_performed}, indent=1),
                    f"Successfully performed {action_performed} on {success_count} fields in dictionary '{dictionary_name}'",
                    str(update_comment),
                )
                logger.info(f"Successfully performed {action_performed} on dictionary '{dictionary_name}' with {success_count} fields")
            except Exception as e:
                return {
                    "payload": f"Failed to update dictionary record in KVstore: {str(e)}",
                    "status": 500,
                }

        # call trackme_register_tenant_component_summary
        thread = threading.Thread(
            target=self.register_component_summary_async,
            args=(
                request_info.session_key,
                request_info.server_rest_uri,
                tenant_id,
                "splk-fqm",
            ),
        )
        thread.start()

        req_summary = {
            "process_count": processed_count,
            "success_count": success_count,
            "failures_count": failures_count,
            "affected_fields": affected_fields,
            "failed_fields": failed_fields,
            "dictionary_name": dictionary_name,
            "tenant_id": tenant_id,
            "action": action_performed,
        }

        if processed_count > 0 and failures_count == 0:
            return {"payload": req_summary, "status": 200}
        elif success_count > 0:
            return {"payload": req_summary, "status": 207}  # Partial success
        else:
            return {"payload": req_summary, "status": 500}

    # Delete a data dictionary
    def post_fqm_delete_data_dictionary(self, request_info, **kwargs):
        # Declare
        describe = False
        tenant_id = None
        dictionary_name = None

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
                    if not tenant_id or len(tenant_id) == 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "message": "tenant_id is required, please provide a valid tenant_id",
                                "failures_count": 1,
                                "dictionary_name": dictionary_name,
                                "error": "tenant_id is required, please provide a valid tenant_id",
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "message": "tenant_id is required, please provide a valid tenant_id",
                            "failures_count": 1,
                            "dictionary_name": dictionary_name,
                            "error": "tenant_id is required, please provide a valid tenant_id",
                        },
                        "status": 500,
                    }

                try:
                    dictionary_name = resp_dict["dictionary_name"]
                    if not dictionary_name or len(dictionary_name) == 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "message": "dictionary_name is required, please provide a valid dictionary_name",
                                "failures_count": 1,
                                "dictionary_name": dictionary_name,
                                "error": "dictionary_name is required, please provide a valid dictionary_name",
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "message": "dictionary_name is required, please provide a valid dictionary_name",
                            "failures_count": 1,
                            "dictionary_name": dictionary_name,
                            "error": "dictionary_name is required, please provide a valid dictionary_name",
                        },
                        "status": 500,
                    }

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes a data dictionary, it requires a POST call with the following information:",
                "resource_desc": "Delete a data dictionary",
                "resource_spl_example": '| trackme mode=post url=/services/trackme/v2/splk_fqm/write/fqm_delete_data_dictionary body="'
                + "{'tenant_id': 'test001', 'dictionary_name': 'WinEventLog'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "dictionary_name": "The name of the data dictionary to update",
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

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % request_info.system_authtoken,
            "Content-Type": "application/json",
        }

        # Data collection
        collection_name = f"kv_trackme_fqm_data_dictionary_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Define the KV query to find the dictionary by name
        query_string = {"name": dictionary_name}

        # Get the current dictionary record
        try:
            kvrecords = collection.data.query(query=json.dumps(query_string))
            if not kvrecords:
                return {
                    "payload": {
                        "action": "failure",
                        "message": f"dictionary_name={dictionary_name} not found in tenant {tenant_id}",
                        "failures_count": 1,
                        "dictionary_name": dictionary_name,
                        "error": f"dictionary_name={dictionary_name} not found in tenant {tenant_id}",
                    },
                    "status": 404,
                }

            dictionary_kvrecord = kvrecords[0]
            dictionary_kvrecord_key = dictionary_kvrecord.get("_key")

        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "message": f"Failed to retrieve dictionary {dictionary_name}: {str(e)}",
                    "failures_count": 1,
                    "dictionary_name": dictionary_name,
                    "error": str(e),
                },
                "status": 500,
            }

        # Get the current json_dict from the record
        try:
            current_json_dict_str = dictionary_kvrecord.get("json_dict")
            if not current_json_dict_str:
                return {
                    "payload": {
                        "action": "failure",
                        "message": f"dictionary {dictionary_name} has no json_dict field",
                        "failures_count": 1,
                        "dictionary_name": dictionary_name,
                        "error": f"dictionary {dictionary_name} has no json_dict field",
                    },
                    "status": 500,
                }
            current_json_dict = json.loads(current_json_dict_str)
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "message": f"Failed to parse json_dict for dictionary {dictionary_name}: {str(e)}",
                    "failures_count": 1,
                    "dictionary_name": dictionary_name,
                    "error": str(e),
                },
                "status": 500,
            }

        # do a request call to verify if the dictionary is used in any tracker, if so raise an error
        # target
        endpoint_url = f"{request_info.server_rest_uri}/services/trackme/v2/splk_fqm/fqm_dictionaries_by_trackers"

        try:
            response = requests.post(
                endpoint_url,
                headers=header,
                data=json.dumps({"tenant_id": tenant_id, "dictionary_name": dictionary_name}),
                verify=False,
                timeout=600,
            )
            response.raise_for_status()
            response_json = response.json()
            trackers_list = response_json[dictionary_name].get("trackers", [])

            if len(trackers_list) > 0:
                return {
                    "payload": {
                        "action": "failure",
                        "message": f"Dictionary {dictionary_name} cannot be deleted because it is used in the following trackers: {trackers_list}",
                        "failures_count": 1,
                        "dictionary_name": dictionary_name,
                        "error": f"Dictionary {dictionary_name} cannot be deleted because it is used in the following trackers: {trackers_list}",
                    },
                    "status": 500,
                }

        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "message": f"Failed to check if dictionary {dictionary_name} is used in any tracker: {str(e)}",
                    "failures_count": 1,
                    "dictionary_name": dictionary_name,
                    "error": str(e),
                },
                "status": 500,
            }

        # attempt to delete the dictionary
        try:
            collection.data.delete(json.dumps({"_key": dictionary_kvrecord_key}))
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user,
                "success",
                f"delete data dictionary",
                dictionary_name,
                "splk-fqm",
                json.dumps(current_json_dict, indent=2),
                f"Successfully deleted dictionary '{dictionary_name}'",
                str(update_comment),
            )
            logger.info(f"Successfully deleted dictionary '{dictionary_name} by user={request_info.user}")
            return {
                "payload": {
                    "action": "success",
                    "message": f"Dictionary {dictionary_name} deleted successfully",
                    "failures_count": 0,
                    "dictionary_name": dictionary_name,
                },
                "status": 200,
            }
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "message": f"Failed to delete dictionary {dictionary_name}: {str(e)}",
                    "failures_count": 1,
                    "dictionary_name": dictionary_name,
                    "error": str(e),
                },
                "status": 500,
            }

    # Import a data dictionary
    def post_fqm_import_data_dictionary(self, request_info, **kwargs):
        # Declare
        describe = False
        tenant_id = None
        dictionary_name = None
        dictionary_json = None

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
                    if not tenant_id or len(tenant_id) == 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "message": "tenant_id is required, please provide a valid tenant_id",
                                "failures_count": 1,
                                "dictionary_name": dictionary_name,
                                "error": "tenant_id is required, please provide a valid tenant_id",
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "message": "tenant_id is required, please provide a valid tenant_id",
                            "failures_count": 1,
                            "dictionary_name": dictionary_name,
                            "error": "tenant_id is required, please provide a valid tenant_id",
                        },
                        "status": 500,
                    }

                try:
                    dictionary_name = resp_dict["dictionary_name"]
                    if not dictionary_name or len(dictionary_name) == 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "message": "dictionary_name is required, please provide a valid dictionary_name",
                                "failures_count": 1,
                                "dictionary_name": dictionary_name,
                                "error": "dictionary_name is required, please provide a valid dictionary_name",
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "message": "dictionary_name is required, please provide a valid dictionary_name",
                            "failures_count": 1,
                            "dictionary_name": dictionary_name,
                            "error": "dictionary_name is required, please provide a valid dictionary_name",
                        },
                        "status": 500,
                    }

                try:
                    dictionary_json = resp_dict["dictionary_json"]
                    if not dictionary_json or len(dictionary_json) == 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "message": "dictionary_json is required, please provide a valid dictionary_json",
                                "failures_count": 1,
                                "dictionary_name": dictionary_name,
                                "error": "dictionary_json is required, please provide a valid dictionary_json",
                            },
                            "status": 500,
                        }
                    # check if the dictionary_json is a valid json
                    if isinstance(dictionary_json, str):
                        try:
                            dictionary_json = json.loads(dictionary_json)
                        except Exception as e:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "message": "dictionary_json is not a valid json",
                                    "failures_count": 1,
                                    "dictionary_name": dictionary_name,
                                    "error": "dictionary_json is not a valid json",
                                },
                                "status": 500,
                            }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "message": "dictionary_json is required, please provide a valid dictionary_json",
                            "failures_count": 1,
                            "dictionary_name": dictionary_name,
                            "error": "dictionary_json is required, please provide a valid dictionary_json",
                        },
                        "status": 500,
                    }

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint imports a data dictionary, it requires a POST call with the following information:",
                "resource_desc": "Import a data dictionary",
                "resource_spl_example": '| trackme mode=post url=/services/trackme/v2/splk_fqm/write/fqm_import_data_dictionary body="'
                + "{'tenant_id': 'test001', 'dictionary_name': 'WinEventLog', 'dictionary_json': '{\"action\":{\"name\":\"action\",\"regex\":\"^(success|failure|allowed|blocked|deferred)$\",\"allow_unknown\":false,\"allow_empty_or_missing\":false}}'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "dictionary_name": "The name of the data dictionary to import",
                        "dictionary_json": "JSON object containing the dictionary structure",
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

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % request_info.system_authtoken,
            "Content-Type": "application/json",
        }

        # Data collection
        collection_name = f"kv_trackme_fqm_data_dictionary_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Define the KV query to find the dictionary by name
        query_string = {"name": dictionary_name}

        # Check if the dictionary already exists
        try:
            kvrecords = collection.data.query(query=json.dumps(query_string))
            if kvrecords:
                return {
                    "payload": {
                        "action": "failure",
                        "message": f"dictionary_name={dictionary_name} already exists in tenant {tenant_id}",
                        "failures_count": 1,
                        "dictionary_name": dictionary_name,
                        "error": f"dictionary_name={dictionary_name} already exists in tenant {tenant_id}",
                    },
                    "status": 409,
                }
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "message": f"Failed to check if dictionary {dictionary_name} exists: {str(e)}",
                    "failures_count": 1,
                    "dictionary_name": dictionary_name,
                    "error": str(e),
                },
                "status": 500,
            }

        # Create the new dictionary record
        try:
            new_record = {
                "name": dictionary_name,
                "json_dict": json.dumps(dictionary_json),
                "created_by": request_info.user,
                "created_time": int(time.time()),
                "updated_by": request_info.user,
                "updated_time": int(time.time()),
            }

            collection.data.insert(json.dumps(new_record))

            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user,
                "success",
                f"import data dictionary",
                dictionary_name,
                "splk-fqm",
                json.dumps(dictionary_json, indent=2),
                f"Successfully imported dictionary '{dictionary_name}'",
                str(update_comment),
            )
            logger.info(f"Successfully imported dictionary '{dictionary_name}' by user={request_info.user}")
            return {
                "payload": {
                    "action": "success",
                    "message": f"Dictionary {dictionary_name} imported successfully",
                    "failures_count": 0,
                    "dictionary_name": dictionary_name,
                },
                "status": 200,
            }
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "message": f"Failed to import dictionary {dictionary_name}: {str(e)}",
                    "failures_count": 1,
                    "dictionary_name": dictionary_name,
                    "error": str(e),
                },
                "status": 500,
            }

    # Create a new empty data dictionary
    def post_fqm_create_data_dictionary(self, request_info, **kwargs):
        # Declare
        describe = False
        tenant_id = None
        dictionary_name = None

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
                    if not tenant_id or len(tenant_id) == 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "message": "tenant_id is required, please provide a valid tenant_id",
                                "failures_count": 1,
                                "dictionary_name": dictionary_name,
                                "error": "tenant_id is required, please provide a valid tenant_id",
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "message": "tenant_id is required, please provide a valid tenant_id",
                            "failures_count": 1,
                            "dictionary_name": dictionary_name,
                            "error": "tenant_id is required, please provide a valid tenant_id",
                        },
                        "status": 500,
                    }

                try:
                    dictionary_name = resp_dict["dictionary_name"]
                    if not dictionary_name or len(dictionary_name) == 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "message": "dictionary_name is required, please provide a valid dictionary_name",
                                "failures_count": 1,
                                "dictionary_name": dictionary_name,
                                "error": "dictionary_name is required, please provide a valid dictionary_name",
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "message": "dictionary_name is required, please provide a valid dictionary_name",
                            "failures_count": 1,
                            "dictionary_name": dictionary_name,
                            "error": "dictionary_name is required, please provide a valid dictionary_name",
                        },
                        "status": 500,
                    }

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint creates a brand new empty data dictionary, it requires a POST call with the following information:",
                "resource_desc": "Create a new empty data dictionary",
                "resource_spl_example": '| trackme mode=post url=/services/trackme/v2/splk_fqm/write/fqm_create_data_dictionary body="'
                + "{'tenant_id': 'test001', 'dictionary_name': 'MyNewDictionary'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "dictionary_name": "The name of the data dictionary to create",
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
        collection_name = f"kv_trackme_fqm_data_dictionary_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Define the KV query to find the dictionary by name
        query_string = {"name": dictionary_name}

        # Check if the dictionary already exists
        try:
            kvrecords = collection.data.query(query=json.dumps(query_string))
            if kvrecords:
                return {
                    "payload": {
                        "action": "failure",
                        "message": f"dictionary_name={dictionary_name} already exists in tenant {tenant_id}",
                        "failures_count": 1,
                        "dictionary_name": dictionary_name,
                        "error": f"dictionary_name={dictionary_name} already exists in tenant {tenant_id}",
                    },
                    "status": 409,
                }
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "message": f"Failed to check if dictionary {dictionary_name} exists: {str(e)}",
                    "failures_count": 1,
                    "dictionary_name": dictionary_name,
                    "error": str(e),
                },
                "status": 500,
            }

        # Create the new empty dictionary record
        try:
            empty_dictionary = {}
            new_record = {
                "name": dictionary_name,
                "json_dict": json.dumps(empty_dictionary),
                "created_by": request_info.user,
                "created_time": int(time.time()),
                "updated_by": request_info.user,
                "updated_time": int(time.time()),
            }

            collection.data.insert(json.dumps(new_record))

            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user,
                "success",
                f"create data dictionary",
                dictionary_name,
                "splk-fqm",
                json.dumps(empty_dictionary, indent=2),
                f"Successfully created empty dictionary '{dictionary_name}'",
                str(update_comment),
            )
            logger.info(f"Successfully created empty dictionary '{dictionary_name}' by user={request_info.user}")
            return {
                "payload": {
                    "action": "success",
                    "message": f"Empty dictionary {dictionary_name} created successfully",
                    "failures_count": 0,
                    "dictionary_name": dictionary_name,
                },
                "status": 200,
            }
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "message": f"Failed to create dictionary {dictionary_name}: {str(e)}",
                    "failures_count": 1,
                    "dictionary_name": dictionary_name,
                    "error": str(e),
                },
                "status": 500,
            }
