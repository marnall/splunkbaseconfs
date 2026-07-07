#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_entity_maintenance_power.py"
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
    "trackme.rest.entity_maintenance_power",
    "trackme_rest_api_entity_maintenance_power.log",
)

import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    extract_keys_list,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_register_tenant_component_summary,
)

# import trackme libs audit
from trackme_libs_audit import trackme_audits_callback

# per-entity maintenance helpers
from trackme_libs_entity_maintenance import resolve_maintenance_epoch

# Splunk libs
import splunklib.client as client

VALID_COMPONENTS = ("dsm", "dhm", "mhm", "flx", "wlk", "fqm")


class TrackMeHandlerEntityMaintenanceWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerEntityMaintenanceWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_entity_maintenance(self, request_info, **kwargs):
        response = {
            "resource_group_name": "entity_maintenance/write",
            "resource_group_desc": "Per-entity maintenance mode — power operations (set / clear). While a maintenance window is active, the decision maker forces the entity into BLUE (protected) state with top precedence, suppressing alerting until the window expires.",
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

    def _connect(self, request_info):
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.session_key,
            timeout=600,
        )
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)
        return service

    # Set per-entity maintenance window
    def post_set_maintenance(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/entity_maintenance/write/set_maintenance" mode="post" body="{'tenant_id': 'mytenant', 'component': 'dsm', 'keys_list': ['key1', 'key2'], 'maintenance_start_epoch': 1716900000, 'maintenance_end_epoch': 1716986400, 'maintenance_comment': 'planned upgrade'}"
        """

        keys_list = None
        describe = False

        raw_payload = str(request_info.raw_args.get("payload", "")).strip()
        if not raw_payload:
            # No body — fall through to describe (usage) mode below.
            resp_dict = None
        else:
            try:
                resp_dict = json.loads(raw_payload)
            except json.JSONDecodeError:
                # A present-but-malformed body is a client error, not a
                # describe request — surface it instead of a silent no-op.
                return self._fail("invalid JSON payload", 400)

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception:
                    return self._fail("the tenant_id is required", 400)

                try:
                    component = resp_dict["component"]
                except Exception:
                    return self._fail("the component is required", 400)
                if component not in VALID_COMPONENTS:
                    return self._fail(
                        f"the component {component} is invalid, valid components are: {', '.join(VALID_COMPONENTS)}",
                        400,
                    )

                # handle keys_list (accepts object_id alias)
                keys_list = extract_keys_list(resp_dict)
                if keys_list:
                    if not isinstance(keys_list, list):
                        keys_list = keys_list.split(",")
                else:
                    return self._fail("the keys_list is required", 400)

                # Resolve the window bounds. Accepts epoch seconds, "now", a
                # relative offset ("+24h" / "+86400" / "-1h"), or an ISO
                # datetime — so LLM callers (Concierge / advisors) can express
                # "the next 24 hours" naturally instead of fabricating epochs.
                if "maintenance_start_epoch" not in resp_dict or "maintenance_end_epoch" not in resp_dict:
                    return self._fail(
                        "maintenance_start_epoch and maintenance_end_epoch are required",
                        400,
                    )
                now = time.time()
                try:
                    maintenance_start_epoch = resolve_maintenance_epoch(
                        resp_dict["maintenance_start_epoch"], now=now
                    )
                    maintenance_end_epoch = resolve_maintenance_epoch(
                        resp_dict["maintenance_end_epoch"], now=now
                    )
                except (ValueError, TypeError) as e:
                    return self._fail(
                        f"invalid maintenance window: {str(e)}",
                        400,
                    )

                if maintenance_end_epoch <= maintenance_start_epoch:
                    return self._fail(
                        "maintenance_end_epoch must be strictly greater than maintenance_start_epoch",
                        400,
                    )
                if maintenance_end_epoch <= now:
                    return self._fail(
                        "maintenance_end_epoch must be in the future (the window has already expired)",
                        400,
                    )
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint places one or many entities into a maintenance window. While active, the entity is forced to BLUE (protected). It requires a POST call with the following information:",
                "resource_desc": "Set a per-entity maintenance window. Upserts one record per key (object_id). Existing windows for the same entity are overwritten.",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/entity_maintenance/write/set_maintenance\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'keys_list': ['key1', 'key2'], 'maintenance_start_epoch': 'now', 'maintenance_end_epoch': '+24h', 'maintenance_comment': 'planned upgrade'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": f"REQUIRED. One of: {', '.join(VALID_COMPONENTS)}",
                        "keys_list": "REQUIRED. List of entity keys (object_id) to put under maintenance. The object_id alias is accepted.",
                        "maintenance_start_epoch": "REQUIRED. Window start. Accepts: the literal string 'now' (start immediately), a relative offset such as '+30m' / '+2h' / '+1d' (units s/m/h/d/w) or bare seconds '+1800', an absolute epoch in seconds (e.g. 1716900000), or an ISO datetime 'YYYY-MM-DDTHH:MM'. For 'starting now', send 'now'. Do NOT invent a 10-digit epoch.",
                        "maintenance_end_epoch": "REQUIRED. Window end, same accepted formats as maintenance_start_epoch. For a window of N hours starting now, send maintenance_start_epoch='now' and maintenance_end_epoch='+Nh' (e.g. '+24h' for 24 hours). Must resolve to a time after the start and in the future.",
                        "maintenance_comment": "OPTIONAL. A free-text reason surfaced in the status message, the UI, describe, and the audit record.",
                        "update_comment": "OPTIONAL. Audit comment, defaults to 'API update'.",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        update_comment = resp_dict.get("update_comment") or "API update"
        maintenance_comment = str(resp_dict.get("maintenance_comment", "") or "")

        service = self._connect(request_info)

        collection_name = f"kv_trackme_common_entity_maintenance_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]
        collection_data_name = f"kv_trackme_{component}_tenant_{tenant_id}"
        collection_data = service.kvstore[collection_data_name]

        updated_records = []
        created_records = []
        failed_records = []
        audits_events_list = []
        now = time.time()
        object_category = f"splk-{component}"

        for key in keys_list:
            try:
                # resolve object / object_category from the entity data collection
                entity_object = key
                try:
                    entity_records = collection_data.data.query(
                        query=json.dumps({"_key": key})
                    )
                    if entity_records:
                        entity_object = entity_records[0].get("object", key)
                        object_category = entity_records[0].get(
                            "object_category", object_category
                        )
                except Exception as e:
                    # Non-fatal: fall back to key as object + the component
                    # default category, but surface the degradation for
                    # diagnostics rather than swallowing it silently.
                    logger.warning(
                        f'failed to resolve object/object_category for key="{key}" '
                        f'from collection="{collection_data_name}", exception="{str(e)}"'
                    )

                existing = collection.data.query(query=json.dumps({"_key": key}))
                if existing:
                    record = existing[0]
                    record["object"] = entity_object
                    record["object_category"] = object_category
                    record["component"] = component
                    record["maintenance_start_epoch"] = maintenance_start_epoch
                    record["maintenance_end_epoch"] = maintenance_end_epoch
                    record["maintenance_comment"] = maintenance_comment
                    record["src_user"] = request_info.user
                    record["mtime"] = now
                    collection.data.update(key, json.dumps(record))
                    updated_records.append(key)
                    change_type = "inline update"
                else:
                    new_record = {
                        "_key": key,
                        "object": entity_object,
                        "object_category": object_category,
                        "component": component,
                        "maintenance_start_epoch": maintenance_start_epoch,
                        "maintenance_end_epoch": maintenance_end_epoch,
                        "maintenance_comment": maintenance_comment,
                        "src_user": request_info.user,
                        "ctime": now,
                        "mtime": now,
                    }
                    collection.data.insert(json.dumps(new_record))
                    created_records.append(key)
                    change_type = "create"

                audit_attrs = [
                    {
                        "field": "maintenance_start_epoch",
                        "new_value": maintenance_start_epoch,
                    },
                    {
                        "field": "maintenance_end_epoch",
                        "new_value": maintenance_end_epoch,
                    },
                    {"field": "maintenance_comment", "new_value": maintenance_comment},
                ]
                audits_events_list.append(
                    {
                        "tenant_id": tenant_id,
                        "action": "success",
                        "user": request_info.user,
                        "change_type": change_type,
                        "object_id": key,
                        "object": entity_object,
                        "object_category": object_category,
                        "object_attrs": json.dumps(audit_attrs),
                        "result": "success: entity maintenance window was set successfully",
                        "comment": str(update_comment),
                    }
                )

            except Exception as e:
                logger.error(f"Error processing key {key}: {str(e)}")
                failed_records.append(key)

        self._emit_audit(request_info, tenant_id, audits_events_list)
        self._register_summary(request_info, tenant_id, object_category)

        response = {
            "action": "success" if not failed_records else "failure",
            "response": "success" if not failed_records else "failure",
            "updated_records": updated_records,
            "created_records": created_records,
            "failed_records": failed_records,
        }
        return {"payload": response, "status": 200 if not failed_records else 500}

    # Clear per-entity maintenance window
    def post_clear_maintenance(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/entity_maintenance/write/clear_maintenance" mode="post" body="{'tenant_id': 'mytenant', 'keys_list': ['key1', 'key2']}"
        """

        keys_list = None
        describe = False

        raw_payload = str(request_info.raw_args.get("payload", "")).strip()
        if not raw_payload:
            # No body — fall through to describe (usage) mode below.
            resp_dict = None
        else:
            try:
                resp_dict = json.loads(raw_payload)
            except json.JSONDecodeError:
                # A present-but-malformed body is a client error, not a
                # describe request — surface it instead of a silent no-op.
                return self._fail("invalid JSON payload", 400)

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception:
                    return self._fail("the tenant_id is required", 400)

                keys_list = extract_keys_list(resp_dict)
                if keys_list:
                    if not isinstance(keys_list, list):
                        keys_list = keys_list.split(",")
                else:
                    return self._fail("the keys_list is required", 400)
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint clears (ends immediately) the maintenance window for one or many entities. It requires a POST call with the following information:",
                "resource_desc": "Clear a per-entity maintenance window by deleting its record. The entity returns to its computed state on the next decision-maker cycle.",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/entity_maintenance/write/clear_maintenance\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'keys_list': ['key1', 'key2']}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "keys_list": "REQUIRED. List of entity keys (object_id) to clear. The object_id alias is accepted.",
                        "update_comment": "OPTIONAL. Audit comment, defaults to 'API update'.",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        update_comment = resp_dict.get("update_comment") or "API update"
        service = self._connect(request_info)

        collection_name = f"kv_trackme_common_entity_maintenance_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        cleared_records = []
        failed_records = []
        audits_events_list = []
        # A single clear can span entities from multiple components, so refresh
        # every touched component summary — not just the last one seen.
        touched_object_categories = set()

        for key in keys_list:
            try:
                existing = collection.data.query(query=json.dumps({"_key": key}))
                if not existing:
                    # nothing to clear — idempotent
                    cleared_records.append(key)
                    continue
                record = existing[0]
                object_category = record.get("object_category")
                if object_category:
                    touched_object_categories.add(object_category)
                collection.data.delete(json.dumps({"_key": key}))
                cleared_records.append(key)
                audits_events_list.append(
                    {
                        "tenant_id": tenant_id,
                        "action": "success",
                        "user": request_info.user,
                        "change_type": "delete",
                        "object_id": key,
                        "object": record.get("object"),
                        "object_category": record.get("object_category"),
                        "object_attrs": json.dumps([]),
                        "result": "success: entity maintenance window was cleared successfully",
                        "comment": str(update_comment),
                    }
                )
            except Exception as e:
                logger.error(f"Error clearing key {key}: {str(e)}")
                failed_records.append(key)

        self._emit_audit(request_info, tenant_id, audits_events_list)
        for object_category in touched_object_categories:
            self._register_summary(request_info, tenant_id, object_category)

        response = {
            "action": "success" if not failed_records else "failure",
            "response": "success" if not failed_records else "failure",
            "cleared_records": cleared_records,
            "failed_records": failed_records,
        }
        return {"payload": response, "status": 200 if not failed_records else 500}

    # ---------------------------------------------------------------- helpers

    def _fail(self, message, status):
        return {
            "payload": {"action": "failure", "response": message},
            "status": status,
        }

    def _emit_audit(self, request_info, tenant_id, audits_events_list):
        if not audits_events_list:
            return
        try:
            audit_response = trackme_audits_callback(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                json.dumps(audits_events_list),
            )
            logger.info(
                f'trackme_audits_callback was called successfully, tenant_id="{tenant_id}", audit_response="{audit_response}"'
            )
        except Exception as e:
            logger.error(
                f'Function trackme_audits_callback has failed, exception="{str(e)}"'
            )

    def _register_summary(self, request_info, tenant_id, object_category):
        try:
            thread = threading.Thread(
                target=self.register_component_summary_async,
                args=(
                    request_info.session_key,
                    request_info.server_rest_uri,
                    tenant_id,
                    object_category,
                ),
            )
            thread.start()
        except Exception as e:
            logger.error(f"Error starting component summary update thread: {str(e)}")
