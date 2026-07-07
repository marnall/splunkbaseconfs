#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_variable_delay.py"
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
    "trackme.rest.splk_variable_delay_power",
    "trackme_rest_api_splk_variable_delay_power.log",
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
from trackme_libs_utils import validate_variable_delay_slots
from trackme_libs_get_data import batch_find_records_by_key, batch_find_records_by_object

# Threshold-lock ledger sync: when a locked entity's variable-delay slots are
# (re)written, refresh the intent-ledger snapshot so the reconcile safety net
# restores THESE slots, not a stale pre-edit copy.
from trackme_libs_threshold_intent import (
    apply_threshold_intent_on_manual_update,
    is_delay_threshold_locked,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkVariableDelayWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkVariableDelayWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_variable_delay(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_variable_delay",
            "resource_group_desc": "Endpoints for managing variable delay threshold configurations (write operations). Variable delay allows time-aware delay thresholds that change based on day-of-week and hour-of-day.",
        }

        return {"payload": response, "status": 200}

    # Set variable delay config for an entity
    def post_set(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_variable_delay/write/set" mode="post" body="{'tenant_id': 'mytenant', 'component': 'dsm', 'object': 'myobject', 'variable_delay_enabled': 'true', 'variable_delay_mode': 'manual', 'variable_delay_default': '3600', 'variable_delay_slots': '{...}'}"
        """

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
                component = resp_dict["component"]
                object_id = resp_dict.get("object_id")
                object_value = resp_dict.get("object")
                variable_delay_enabled = resp_dict.get(
                    "variable_delay_enabled", "true"
                )
                variable_delay_mode = resp_dict.get("variable_delay_mode", "manual")
                variable_delay_default = resp_dict.get("variable_delay_default", "3600")
                variable_delay_slots = resp_dict.get("variable_delay_slots", '{"slots": []}')
                variable_delay_auto_review_enabled = resp_dict.get(
                    "variable_delay_auto_review_enabled", "false"
                )
                variable_delay_auto_review_period = resp_dict.get(
                    "variable_delay_auto_review_period", "-30d"
                )
                variable_delay_auto_review_method = resp_dict.get(
                    "variable_delay_auto_review_method", "perc95"
                )
                update_comment = resp_dict.get("update_comment") or "API update"
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint creates or updates the variable delay configuration for an entity, it requires a POST call with the following information:",
                "resource_desc": "Create or update variable delay threshold configuration for an entity",
                "resource_spl_example": '| trackme url="/services/trackme/v2/splk_variable_delay/write/set" mode="post" body=\'{"tenant_id": "mytenant", "component": "dsm", "object": "myobject", "variable_delay_enabled": "true", "variable_delay_mode": "manual", "variable_delay_default": "3600", "variable_delay_slots": "{\\"slots\\": [{\\"slot_name\\": \\"business_hours\\", \\"days\\": [0,1,2,3,4], \\"hours\\": [8,9,10,11,12,13,14,15,16,17,18,19], \\"max_delay_allowed\\": 3600}]}"}\'',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "MANDATORY, component type: dsm or dhm",
                        "object": "CONDITIONAL, the entity name (either object or object_id is required)",
                        "object_id": "CONDITIONAL, the entity KVstore key (preferred over object for robustness)",
                        "variable_delay_enabled": "OPTIONAL, enable/disable variable delay: true or false (default: true)",
                        "variable_delay_mode": "OPTIONAL, how slots were defined: manual or auto (default: manual)",
                        "variable_delay_default": "OPTIONAL, fallback threshold in seconds when no slot matches (default: 3600)",
                        "variable_delay_slots": "MANDATORY, JSON-encoded slot definitions with days (0=Mon to 6=Sun), hours (0-23), and max_delay_allowed per slot. Slots are evaluated in order, first match wins.",
                        "variable_delay_auto_review_enabled": "OPTIONAL, enable periodic re-computation: true or false (default: false)",
                        "variable_delay_auto_review_period": "OPTIONAL, lookback period for auto-review: e.g. -30d (default: -30d)",
                        "variable_delay_auto_review_method": "OPTIONAL, statistical method for auto-review: perc95 or perc99 or density (default: perc95)",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # set log level
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Splunk SDK service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.session_key,
            timeout=600,
        )

        # validate component
        if component not in ("dsm", "dhm", "splk-dsm", "splk-dhm"):
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Invalid component "{component}", must be "dsm", "dhm", "splk-dsm", or "splk-dhm"',
                },
                "status": 400,
            }

        # normalize component
        comp = component.replace("splk-", "")

        # validate variable_delay_default
        try:
            variable_delay_default_int = int(variable_delay_default)
            if variable_delay_default_int < 60:
                return {
                    "payload": {
                        "action": "failure",
                        "response": "variable_delay_default must be >= 60 seconds",
                    },
                    "status": 400,
                }
        except (ValueError, TypeError):
            return {
                "payload": {
                    "action": "failure",
                    "response": "variable_delay_default must be a positive integer",
                },
                "status": 400,
            }

        # parse and validate slots
        if isinstance(variable_delay_slots, str):
            try:
                slots_config = json.loads(variable_delay_slots)
            except json.JSONDecodeError:
                return {
                    "payload": {
                        "action": "failure",
                        "response": "variable_delay_slots is not valid JSON",
                    },
                    "status": 400,
                }
        else:
            slots_config = variable_delay_slots

        validation_errors = validate_variable_delay_slots(slots_config, min_delay_seconds=60)
        if validation_errors:
            return {
                "payload": {
                    "action": "failure",
                    "response": "Slot validation errors",
                    "errors": validation_errors,
                },
                "status": 400,
            }

        # validate that at least one entity identifier is provided
        if not object_id and not object_value:
            return {
                "payload": {
                    "action": "failure",
                    "response": "Either object_id or object is required",
                },
                "status": 400,
            }

        # get entity _key from main collection FIRST (used as _key in variable delay collection)
        main_collection_name = f"kv_trackme_{comp}_tenant_{tenant_id}"
        try:
            main_collection = service.kvstore[main_collection_name]
            if object_id:
                main_query = {"_key": object_id}
            else:
                main_query = {"object": object_value}
            main_records = main_collection.data.query(
                query=json.dumps(main_query)
            )
            if not main_records or len(main_records) == 0:
                identifier = object_id or object_value
                return {
                    "payload": {
                        "action": "failure",
                        "response": f"Entity '{identifier}' not found in {main_collection_name}",
                    },
                    "status": 404,
                }
            main_record = main_records[0]
            entity_key = main_record.get("_key")
            # ensure we have the object name from the record
            if not object_value:
                object_value = main_record.get("object", "")
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"Failed to lookup entity in main collection: {str(e)}",
                },
                "status": 500,
            }

        # get variable delay collection
        collection_name = f"kv_trackme_{comp}_variable_delay_tenant_{tenant_id}"
        try:
            collection = service.kvstore[collection_name]
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"Variable delay collection not found: {collection_name}",
                    "exception": str(e),
                },
                "status": 404,
            }

        # check if record exists (lookup by entity _key)
        existing_record = None
        try:
            records = collection.data.query(query=json.dumps({"_key": entity_key}))
            if records and len(records) > 0:
                existing_record = records[0]
        except Exception:
            pass

        now_epoch = str(time.time())

        # build the variable delay record (always set _key to match entity's _key)
        variable_delay_record = {
            "_key": entity_key,
            "object": object_value,
            "object_category": f"splk-{comp}",
            "tenant_id": tenant_id,
            "variable_delay_enabled": variable_delay_enabled,
            "variable_delay_mode": variable_delay_mode,
            "variable_delay_default": str(variable_delay_default),
            "variable_delay_slots": json.dumps(slots_config)
            if isinstance(slots_config, dict)
            else variable_delay_slots,
            "variable_delay_auto_review_enabled": variable_delay_auto_review_enabled,
            "variable_delay_auto_review_period": variable_delay_auto_review_period,
            "variable_delay_auto_review_method": variable_delay_auto_review_method,
            "variable_delay_mtime": now_epoch,
            "variable_delay_updated_by": request_info.user,
        }

        if existing_record:
            # update existing
            variable_delay_record["variable_delay_ctime"] = existing_record.get(
                "variable_delay_ctime", now_epoch
            )
            variable_delay_record["variable_delay_last_auto_review"] = existing_record.get(
                "variable_delay_last_auto_review", ""
            )
            collection.data.update(str(entity_key), json.dumps(variable_delay_record))
        else:
            # insert new
            variable_delay_record["variable_delay_ctime"] = now_epoch
            variable_delay_record["variable_delay_last_auto_review"] = ""
            collection.data.insert(json.dumps(variable_delay_record))

        # update the main entity collection to set variable_delay_policy
        try:
            main_record["variable_delay_policy"] = "variable" if variable_delay_enabled == "true" else "static"
            # allow_adaptive_delay is an independent per-entity opt-in (default
            # "true") and is NOT coupled to the delay policy: since PR #1611 the
            # adaptive framework handles variable-delay entities too (the
            # honour-existing-slots path). Leave the operator's existing value
            # untouched here — flip it to "false" only via an explicit edit to
            # opt a specific entity out of adaptive delay.
            main_collection.data.update(
                str(entity_key), json.dumps(main_record)
            )
        except Exception as e:
            logger.warning(
                f"Failed to update main entity collection for variable_delay_policy: {str(e)}"
            )

        # Threshold-lock ledger sync. For a LOCKED variable-policy entity the
        # pinned delay configuration IS the slot schedule we just wrote — refresh
        # the intent-ledger snapshot (preserve path) so the reconcile safety net
        # restores these slots rather than a stale pre-edit copy. No-op for
        # unlocked entities (gated on the on-record lock flag → zero extra I/O).
        try:
            if comp in ("dsm", "dhm") and is_delay_threshold_locked(main_record):
                _, _intent_counts = apply_threshold_intent_on_manual_update(
                    service,
                    tenant_id,
                    comp,
                    main_collection,
                    [object_value],
                    None,
                    None,  # lock_threshold=None → preserve (refresh ledger only)
                    None,  # requested_delay → coalesce to live value
                    None,  # requested_lag → coalesce to live value
                    requested_by=request_info.user or "manual",
                    logger=logger,
                )
                if _intent_counts.get("preserve_refresh_failed"):
                    logger.warning(
                        f'threshold_intent slot-snapshot refresh failed after '
                        f'variable-delay set, tenant_id="{tenant_id}", '
                        f'component="{comp}", object="{object_value}" (reconcile '
                        f'may briefly restore the previous slots until the next edit)'
                    )
        except Exception as e:
            logger.warning(
                f'threshold_intent slot-snapshot refresh hook error (non-blocking), '
                f'tenant_id="{tenant_id}", component="{comp}", '
                f'object="{object_value}", exception="{str(e)}"'
            )

        # audit event
        trackme_audit_event(
            request_info.system_authtoken,
            request_info.server_rest_uri,
            tenant_id,
            request_info.user,
            "success",
            "set variable delay configuration",
            str(object_value),
            f"splk-{comp}",
            json.dumps(variable_delay_record, indent=1),
            "Variable delay configuration was set successfully",
            str(update_comment),
        )

        return {
            "payload": {
                "action": "success",
                "response": f"Variable delay configuration set for {object_value}",
                "record": variable_delay_record,
            },
            "status": 200,
        }

    # Enable variable delay for an entity
    def post_enable(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_variable_delay/write/enable" mode="post" body="{'tenant_id': 'mytenant', 'component': 'dsm', 'object': 'myobject'}"
        """

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
                component = resp_dict["component"]
                object_id = resp_dict.get("object_id")
                object_value = resp_dict.get("object")
                update_comment = resp_dict.get("update_comment") or "API update"
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint enables variable delay for an entity (sets variable_delay_enabled to true in the variable delay collection and variable_delay_policy to variable in the main collection), it requires a POST call with the following information:",
                "resource_desc": "Enable variable delay for an entity",
                "resource_spl_example": '| trackme url="/services/trackme/v2/splk_variable_delay/write/enable" mode="post" body=\'{"tenant_id": "mytenant", "component": "dsm", "object": "myobject"}\'',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "MANDATORY, component type: dsm or dhm",
                        "object": "CONDITIONAL, the entity name (either object or object_id is required)",
                        "object_id": "CONDITIONAL, the entity KVstore key (preferred over object for robustness)",
                        "update_comment": "OPTIONAL: a comment for the update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # set log level
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Splunk SDK service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.session_key,
            timeout=600,
        )

        # validate component
        if component not in ("dsm", "dhm", "splk-dsm", "splk-dhm"):
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Invalid component "{component}", must be "dsm", "dhm", "splk-dsm", or "splk-dhm"',
                },
                "status": 400,
            }

        # normalize component
        comp = component.replace("splk-", "")

        # validate that at least one entity identifier is provided
        if not object_id and not object_value:
            return {
                "payload": {
                    "action": "failure",
                    "response": "Either object_id or object is required",
                },
                "status": 400,
            }

        # get entity _key from main collection first
        main_collection_name = f"kv_trackme_{comp}_tenant_{tenant_id}"
        try:
            main_collection = service.kvstore[main_collection_name]
            if object_id:
                main_query = {"_key": object_id}
            else:
                main_query = {"object": object_value}
            main_records = main_collection.data.query(
                query=json.dumps(main_query)
            )
            if not main_records or len(main_records) == 0:
                identifier = object_id or object_value
                return {
                    "payload": {
                        "action": "failure",
                        "response": f"Entity '{identifier}' not found in {main_collection_name}",
                    },
                    "status": 404,
                }
            main_record = main_records[0]
            entity_key = main_record.get("_key")
            if not object_value:
                object_value = main_record.get("object", "")
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"Failed to lookup entity in main collection: {str(e)}",
                },
                "status": 500,
            }

        # update variable delay collection (lookup by entity _key)
        collection_name = f"kv_trackme_{comp}_variable_delay_tenant_{tenant_id}"
        try:
            collection = service.kvstore[collection_name]
            records = collection.data.query(query=json.dumps({"_key": entity_key}))
            if records and len(records) > 0:
                record = records[0]
                record["variable_delay_enabled"] = "true"
                record["variable_delay_mtime"] = str(time.time())
                record["variable_delay_updated_by"] = request_info.user
                collection.data.update(str(entity_key), json.dumps(record))
            else:
                return {
                    "payload": {
                        "action": "failure",
                        "response": f"No variable delay configuration found for {object_value}. Use set to create one first.",
                    },
                    "status": 404,
                }
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": "Error updating variable delay collection",
                    "exception": str(e),
                },
                "status": 500,
            }

        # update main entity collection
        try:
            # Set the delay policy only — allow_adaptive_delay is an independent
            # per-entity opt-in (default "true") that applies to variable-delay
            # entities too (PR #1611). Do not force it "false" on enable; preserve
            # the operator's value.
            main_record["variable_delay_policy"] = "variable"
            main_collection.data.update(
                str(entity_key), json.dumps(main_record)
            )
        except Exception as e:
            logger.warning(
                f"Failed to update main entity collection: {str(e)}"
            )

        # audit event
        trackme_audit_event(
            request_info.system_authtoken,
            request_info.server_rest_uri,
            tenant_id,
            request_info.user,
            "success",
            "enable variable delay",
            str(object_value),
            f"splk-{comp}",
            "N/A",
            "Variable delay was enabled successfully",
            str(update_comment),
        )

        return {
            "payload": {
                "action": "success",
                "response": f"Variable delay enabled for {object_value}",
            },
            "status": 200,
        }

    # Disable variable delay for an entity
    def post_disable(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_variable_delay/write/disable" mode="post" body="{'tenant_id': 'mytenant', 'component': 'dsm', 'object': 'myobject'}"
        """

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
                component = resp_dict["component"]
                object_id = resp_dict.get("object_id")
                object_value = resp_dict.get("object")
                update_comment = resp_dict.get("update_comment") or "API update"
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint disables variable delay for an entity (reverts to static delay threshold). The variable delay record is preserved for re-enablement. It requires a POST call with the following information:",
                "resource_desc": "Disable variable delay for an entity (revert to static threshold)",
                "resource_spl_example": '| trackme url="/services/trackme/v2/splk_variable_delay/write/disable" mode="post" body=\'{"tenant_id": "mytenant", "component": "dsm", "object": "myobject"}\'',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "MANDATORY, component type: dsm or dhm",
                        "object": "CONDITIONAL, the entity name (either object or object_id is required)",
                        "object_id": "CONDITIONAL, the entity KVstore key (preferred over object for robustness)",
                        "update_comment": "OPTIONAL: a comment for the update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # set log level
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Splunk SDK service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.session_key,
            timeout=600,
        )

        # validate component
        if component not in ("dsm", "dhm", "splk-dsm", "splk-dhm"):
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Invalid component "{component}", must be "dsm", "dhm", "splk-dsm", or "splk-dhm"',
                },
                "status": 400,
            }

        # normalize component
        comp = component.replace("splk-", "")

        # validate that at least one entity identifier is provided
        if not object_id and not object_value:
            return {
                "payload": {
                    "action": "failure",
                    "response": "Either object_id or object is required",
                },
                "status": 400,
            }

        # get entity _key from main collection first
        main_collection_name = f"kv_trackme_{comp}_tenant_{tenant_id}"
        try:
            main_collection = service.kvstore[main_collection_name]
            if object_id:
                main_query = {"_key": object_id}
            else:
                main_query = {"object": object_value}
            main_records = main_collection.data.query(
                query=json.dumps(main_query)
            )
            if not main_records or len(main_records) == 0:
                identifier = object_id or object_value
                return {
                    "payload": {
                        "action": "failure",
                        "response": f"Entity '{identifier}' not found in {main_collection_name}",
                    },
                    "status": 404,
                }
            main_record = main_records[0]
            entity_key = main_record.get("_key")
            if not object_value:
                object_value = main_record.get("object", "")
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"Failed to lookup entity in main collection: {str(e)}",
                },
                "status": 500,
            }

        # update variable delay collection (preserve record, set enabled=false, lookup by entity _key)
        collection_name = f"kv_trackme_{comp}_variable_delay_tenant_{tenant_id}"
        try:
            collection = service.kvstore[collection_name]
            records = collection.data.query(query=json.dumps({"_key": entity_key}))
            if records and len(records) > 0:
                record = records[0]
                record["variable_delay_enabled"] = "false"
                record["variable_delay_mtime"] = str(time.time())
                record["variable_delay_updated_by"] = request_info.user
                collection.data.update(str(entity_key), json.dumps(record))
        except Exception:
            pass

        # update main entity collection
        try:
            # Revert to the static policy only. Do NOT touch allow_adaptive_delay:
            # it is an independent per-entity opt-in (default "true"), so forcing
            # it here would silently clear an explicit opt-out when the entity
            # leaves variable-delay mode. Preserve the operator's stored value.
            main_record["variable_delay_policy"] = "static"
            main_collection.data.update(
                str(entity_key), json.dumps(main_record)
            )
        except Exception as e:
            logger.warning(
                f"Failed to update main entity collection: {str(e)}"
            )

        # audit event
        trackme_audit_event(
            request_info.system_authtoken,
            request_info.server_rest_uri,
            tenant_id,
            request_info.user,
            "success",
            "disable variable delay",
            str(object_value),
            f"splk-{comp}",
            "N/A",
            "Variable delay was disabled successfully, entity reverted to static delay threshold",
            str(update_comment),
        )

        return {
            "payload": {
                "action": "success",
                "response": f"Variable delay disabled for {object_value}, reverted to static threshold",
            },
            "status": 200,
        }

    # Bulk disable variable delay for multiple entities
    def post_bulk_disable(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_variable_delay/write/bulk_disable" mode="post" body="{'tenant_id': 'mytenant', 'component': 'dsm', 'keys_list': 'key1,key2'}"
        """

        describe = False

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]
                component = resp_dict["component"]

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

                update_comment = resp_dict.get("update_comment") or "API update"
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint disables variable delay for multiple entities in bulk (reverts to static delay threshold). It requires a POST call with the following information:",
                "resource_desc": "Bulk disable variable delay for multiple entities",
                "resource_spl_example": '| trackme url="/services/trackme/v2/splk_variable_delay/write/bulk_disable" mode="post" body=\'{"tenant_id": "mytenant", "component": "dsm", "keys_list": "key1,key2"}\'',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "MANDATORY, component type: dsm or dhm",
                        "object_list": "List of entity names, comma separated (provide object_list or keys_list)",
                        "keys_list": "List of entity keys, comma separated (provide object_list or keys_list)",
                        "update_comment": "OPTIONAL: a comment for the update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # set log level
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # validate component
        if component not in ("dsm", "dhm", "splk-dsm", "splk-dhm"):
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Invalid component "{component}", must be "dsm", "dhm", "splk-dsm", or "splk-dhm"',
                },
                "status": 400,
            }

        # normalize component
        comp = component.replace("splk-", "")

        # Splunk SDK service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.session_key,
            timeout=600,
        )

        # collections
        main_collection_name = f"kv_trackme_{comp}_tenant_{tenant_id}"
        main_collection = service.kvstore[main_collection_name]

        vardelay_collection_name = f"kv_trackme_{comp}_variable_delay_tenant_{tenant_id}"
        vardelay_collection = service.kvstore[vardelay_collection_name]

        # Resolve entities
        if object_list:
            kvrecords_dict, kvrecords = batch_find_records_by_object(
                main_collection, object_list
            )
        elif keys_list:
            kvrecords_dict, kvrecords = batch_find_records_by_key(
                main_collection, keys_list
            )
        else:
            return {
                "payload": {"error": "either object_list or keys_list must be provided"},
                "status": 500,
            }

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0
        records = []

        # Process each entity
        for kvrecord in kvrecords:
            entity_key = kvrecord.get("_key")
            object_value = kvrecord.get("object", "")

            try:
                # 1. Update variable delay collection (set enabled=false, preserve record)
                try:
                    vd_records = vardelay_collection.data.query(
                        query=json.dumps({"_key": entity_key})
                    )
                    if vd_records and len(vd_records) > 0:
                        vd_record = vd_records[0]
                        vd_record["variable_delay_enabled"] = "false"
                        vd_record["variable_delay_mtime"] = str(time.time())
                        vd_record["variable_delay_updated_by"] = request_info.user
                        vardelay_collection.data.update(
                            str(entity_key), json.dumps(vd_record)
                        )
                except Exception:
                    pass

                # 2. Update main entity collection (revert to static). Preserve
                # allow_adaptive_delay (independent per-entity opt-in) — do not
                # clear a possible explicit opt-out when leaving variable mode.
                kvrecord["variable_delay_policy"] = "static"
                main_collection.data.update(
                    str(entity_key), json.dumps(kvrecord)
                )

                processed_count += 1
                succcess_count += 1
                records.append(
                    {
                        "object": object_value,
                        "action": "disable_variable_delay",
                        "result": "success",
                        "message": f'tenant_id="{tenant_id}", Variable delay disabled for {object_value}, reverted to static threshold',
                    }
                )
            except Exception as e:
                processed_count += 1
                failures_count += 1
                records.append(
                    {
                        "object": object_value,
                        "action": "disable_variable_delay",
                        "result": "failure",
                        "exception": f'tenant_id="{tenant_id}", failed to disable variable delay, object="{object_value}", exception="{str(e)}"',
                    }
                )

        # Batch audit events in a single REST call
        if succcess_count > 0:
            audit_events = []
            for record in records:
                if record.get("result") == "success":
                    audit_events.append(
                        {
                            "action": "success",
                            "change_type": "disable variable delay",
                            "object": str(record.get("object")),
                            "object_category": f"splk-{comp}",
                            "object_attrs": "N/A",
                            "user": request_info.user,
                            "result": "Variable delay was disabled successfully, entity reverted to static delay threshold",
                            "comment": str(update_comment),
                        }
                    )
            if audit_events:
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

        # response
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

    # Delete variable delay config for an entity
    def post_delete(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_variable_delay/write/delete" mode="post" body="{'tenant_id': 'mytenant', 'component': 'dsm', 'object': 'myobject'}"
        """

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
                component = resp_dict["component"]
                object_id = resp_dict.get("object_id")
                object_value = resp_dict.get("object")
                update_comment = resp_dict.get("update_comment") or "API update"
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes the variable delay configuration for an entity and reverts it to static delay. It requires a POST call with the following information:",
                "resource_desc": "Delete variable delay configuration for an entity",
                "resource_spl_example": '| trackme url="/services/trackme/v2/splk_variable_delay/write/delete" mode="post" body=\'{"tenant_id": "mytenant", "component": "dsm", "object": "myobject"}\'',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "MANDATORY, component type: dsm or dhm",
                        "object": "CONDITIONAL, the entity name (either object or object_id is required)",
                        "object_id": "CONDITIONAL, the entity KVstore key (preferred over object for robustness)",
                        "update_comment": "OPTIONAL: a comment for the update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # set log level
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Splunk SDK service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.session_key,
            timeout=600,
        )

        # validate component
        if component not in ("dsm", "dhm", "splk-dsm", "splk-dhm"):
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Invalid component "{component}", must be "dsm", "dhm", "splk-dsm", or "splk-dhm"',
                },
                "status": 400,
            }

        # normalize component
        comp = component.replace("splk-", "")

        # validate that at least one entity identifier is provided
        if not object_id and not object_value:
            return {
                "payload": {
                    "action": "failure",
                    "response": "Either object_id or object is required",
                },
                "status": 400,
            }

        # get entity _key from main collection first
        main_collection_name = f"kv_trackme_{comp}_tenant_{tenant_id}"
        try:
            main_collection = service.kvstore[main_collection_name]
            if object_id:
                main_query = {"_key": object_id}
            else:
                main_query = {"object": object_value}
            main_records = main_collection.data.query(
                query=json.dumps(main_query)
            )
            if not main_records or len(main_records) == 0:
                identifier = object_id or object_value
                return {
                    "payload": {
                        "action": "failure",
                        "response": f"Entity '{identifier}' not found in {main_collection_name}",
                    },
                    "status": 404,
                }
            main_record = main_records[0]
            entity_key = main_record.get("_key")
            if not object_value:
                object_value = main_record.get("object", "")
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"Failed to lookup entity in main collection: {str(e)}",
                },
                "status": 500,
            }

        # delete from variable delay collection (lookup by entity _key)
        collection_name = f"kv_trackme_{comp}_variable_delay_tenant_{tenant_id}"
        try:
            collection = service.kvstore[collection_name]
            collection.data.delete_by_id(str(entity_key))
        except Exception:
            pass

        # update main entity collection
        try:
            # Revert to the static policy only. Do NOT touch allow_adaptive_delay:
            # it is an independent per-entity opt-in (default "true"), so forcing
            # it here would silently clear an explicit opt-out when the entity
            # leaves variable-delay mode. Preserve the operator's stored value.
            main_record["variable_delay_policy"] = "static"
            main_collection.data.update(
                str(entity_key), json.dumps(main_record)
            )
        except Exception as e:
            logger.warning(
                f"Failed to update main entity collection: {str(e)}"
            )

        # audit event
        trackme_audit_event(
            request_info.system_authtoken,
            request_info.server_rest_uri,
            tenant_id,
            request_info.user,
            "success",
            "delete variable delay configuration",
            str(object_value),
            f"splk-{comp}",
            "N/A",
            "Variable delay configuration was deleted, entity reverted to static delay threshold",
            str(update_comment),
        )

        return {
            "payload": {
                "action": "success",
                "response": f"Variable delay configuration deleted for {object_value}",
            },
            "status": 200,
        }
