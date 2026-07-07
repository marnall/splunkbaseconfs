#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_dsm.py"
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
    "trackme.rest.splk_dsm_power", "trackme_rest_api_splk_dsm_power.log"
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    extract_keys_list,
    run_splunk_search,
    trackme_audit_event,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_register_tenant_component_summary,
    trackme_reqinfo,
    trackme_vtenant_account_from_service,
)

# import trackme libs get data
from trackme_libs_get_data import (
    batch_find_records_by_object,
    batch_find_records_by_key,
)

# import threshold intent-lock helpers
from trackme_libs_threshold_intent import (
    apply_threshold_intent_on_manual_update,
    threshold_lock_enabled,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces, convert_time_to_seconds

# import trackme libs persistent fields definition
from collections_data import (
    persistent_fields_dsm,
)

# import trackme libs bulk edit
from trackme_libs_bulk_edit import post_bulk_edit, generic_batch_update

# import shadow copy libs
from trackme_libs_shadow import delete_shadow_records


# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkDsmWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkDsmWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_dsm(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_dsm/write",
            "resource_group_desc": "Endpoints specific to the splk-dsm TrackMe component (Splunk Data Sources monitoring, power operations)",
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
    def post_ds_bulk_edit(self, request_info, **kwargs):
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
            component_name="dsm",
            persistent_fields=persistent_fields_dsm,
            collection_name_suffix="dsm",
            endpoint_suffix="dsm",
            function_name="ds_bulk_edit",
            **kwargs,
        )

        return {
            "payload": response,
            "status": http_status,
        }

    # Enable/Disable monitoring by object name
    def post_ds_monitoring(self, request_info, **kwargs):
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
                        "payload": "Invalid option for action, valid options are: enable | disable",
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
                "describe": "This endpoint enables data monitoring for an existing data source by the data source name (object), it requires a POST call with the following information:",
                "resource_desc": "Enable/Disable monitoring for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/write/ds_monitoring\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'action': 'disable', 'object_list': 'netscreen:netscreen:firewall,wineventlog:WinEventLog'}\"",
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
        collection_name = f"kv_trackme_dsm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "dsm",
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
            persistent_fields=persistent_fields_dsm,
            component="dsm",
            update_comment=update_comment,
            audit_context="update monitoring",
            audit_message="Monitoring state was updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Update priority by object name
    def post_ds_update_priority(self, request_info, **kwargs):
        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]

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
                "describe": "This endpoint defines the priority for an existing data source, it requires a POST call with the following information:",
                "resource_desc": "Update priority for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/write/ds_update_priority\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'priority': 'high', 'object_list': 'netscreen:netscreen:firewall,wineventlog:WinEventLog'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_list": "REQUIRED (with keys_list as alternative). Comma-separated list of entity object names. Either object_list or keys_list must be provided",
                        "keys_list": "REQUIRED (with object_list as alternative). Comma-separated list of entity KV record _keys. Either object_list or keys_list must be provided",
                        "priority": "the value for priority, valid options are low / medium / high / critical / pending",
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
        collection_name = f"kv_trackme_dsm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "dsm",
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
            persistent_fields=persistent_fields_dsm,
            component="dsm",
            update_comment=update_comment,
            audit_context="update priority",
            audit_message="Priority was updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Update lagging policy by object name
    def post_ds_update_lag_policy(self, request_info, **kwargs):
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
                    data_max_lag_allowed = resp_dict["data_max_lag_allowed"]
                    data_max_lag_allowed = convert_time_to_seconds(data_max_lag_allowed)
                except Exception as e:
                    data_max_lag_allowed = None

                try:
                    data_max_delay_allowed = resp_dict["data_max_delay_allowed"]
                    data_max_delay_allowed = convert_time_to_seconds(
                        data_max_delay_allowed
                    )
                except Exception as e:
                    data_max_delay_allowed = None

                # NOTE: data_override_lagging_class / allow_adaptive_delay are no
                # longer accepted as direct request inputs. They are DERIVED from
                # the unified threshold lock (see the orchestration block below):
                # the lock is the single source of truth, so accepting the legacy
                # fields directly would let a caller persist a value that
                # contradicts the *_locked state.

                try:
                    variable_delay_policy = resp_dict[
                        "variable_delay_policy"
                    ]  # static / variable
                    if variable_delay_policy not in ("static", "variable"):
                        variable_delay_policy = None
                except Exception as e:
                    variable_delay_policy = None

                # Threshold intent lock (true / false). Tri-state: when omitted
                # (None) the lock state is preserved — only an explicit value
                # pins or unpins the entity. Non-locking callers (adaptive delay
                # write-back, bulk edits) thus never toggle a lock by accident.
                try:
                    lock_threshold = str(resp_dict["lock_threshold"]).strip().lower()
                    if lock_threshold not in ("true", "false"):
                        lock_threshold = None
                except Exception as e:
                    lock_threshold = None

                try:
                    future_tolerance = resp_dict["future_tolerance"]
                except Exception as e:
                    future_tolerance = None

                try:
                    impact_score_weights = resp_dict.get("impact_score_weights")
                    if impact_score_weights:
                        # Validate it's a dict or can be parsed as JSON
                        if isinstance(impact_score_weights, str):
                            impact_score_weights = json.loads(impact_score_weights)
                        if isinstance(impact_score_weights, dict):
                            # Validate keys are 'delay' and/or 'latency' with integer values 0-100
                            validated_weights = {}
                            for key in ["delay", "latency"]:
                                if key in impact_score_weights:
                                    try:
                                        weight_value = int(impact_score_weights[key])
                                        if 0 <= weight_value <= 100:
                                            validated_weights[key] = weight_value
                                    except (ValueError, TypeError):
                                        pass
                            # Only set if we have at least one valid weight
                            if validated_weights:
                                impact_score_weights = json.dumps(validated_weights)
                            else:
                                impact_score_weights = None
                        else:
                            impact_score_weights = None
                    else:
                        impact_score_weights = None
                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    impact_score_weights = None

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint configures the lagging policy for an existing data source, it requires a POST call with the following information:",
                "resource_desc": "Update lag policies for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/write/ds_update_lag_policy\" mode=\"post\" body=\"{'tenant_id':'mytenant','object_list':'netscreen:netscreen:firewall','data_max_lag_allowed':'1h','data_max_delay_allowed':'1d','lock_threshold':'true'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_list": "REQUIRED (with keys_list as alternative). Comma-separated list of entity object names. Either object_list or keys_list must be provided",
                        "keys_list": "REQUIRED (with object_list as alternative). Comma-separated list of entity KV record _keys. Either object_list or keys_list must be provided",
                        "data_max_lag_allowed": "OPTIONAL, maximal accepted lagging value in seconds or with unit suffix (m/h/d/w), e.g. 3600 or '15m' or '1h' or '1d' or '1w'",
                        "data_max_delay_allowed": "OPTIONAL, maximal accepted delay value in seconds or with unit suffix (m/h/d/w), e.g. 3600 or '15m' or '1h' or '1d' or '1w'",
                        "future_tolerance": "OPTIONAL, the negative value for future tolerance, specify system to rely on the system level setting, disabled to allow data in the future up to 7 days without affecting the status of the entity",
                        "variable_delay_policy": "OPTIONAL, delay threshold policy: static (default single threshold) or variable (time-aware thresholds by day/hour).",
                        "lock_threshold": "OPTIONAL, true / false. When true, pins the delay/lag thresholds: background auto-writers (adaptive delay, variable-delay review, lagging-class override) skip the entity and a reconcile routine restores the requested values on drift. When false, unpins. When omitted, the existing lock state is preserved.",
                        "impact_score_weights": "OPTIONAL, JSON object with custom impact score weights for delay and/or latency (0-100), e.g. {'delay': 100, 'latency': 48}. If not set, tenant-level defaults are used.",
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
        collection_name = f"kv_trackme_dsm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "dsm",
            "object_list": object_list,
            "keys_list": keys_list,
        }

        # Prepare the update fields. Use `is not None` (not truthiness) so an
        # explicit 0 ("any delay/lag is a breach") persists consistently with the
        # intent-ledger path below — otherwise the ledger could pin 0 while the
        # live entity field is left unchanged until reconcile repairs the drift.
        update_fields = {}
        if data_max_lag_allowed is not None:
            update_fields["data_max_lag_allowed"] = data_max_lag_allowed
        if data_max_delay_allowed is not None:
            update_fields["data_max_delay_allowed"] = data_max_delay_allowed
        # data_override_lagging_class / allow_adaptive_delay are NOT set from the
        # request — they are derived from the threshold lock in the orchestration
        # block below (the lock is the single source of truth).
        if variable_delay_policy:
            update_fields["variable_delay_policy"] = variable_delay_policy
        if future_tolerance:
            update_fields["future_tolerance"] = future_tolerance
        if impact_score_weights:
            update_fields["impact_score_weights"] = impact_score_weights
        # NOTE: the "no valid fields to update" guard is deferred until AFTER the
        # threshold intent-lock block below, so a lock-only request (toggling
        # lock_threshold while preserving the existing thresholds) still reaches
        # the intent path and contributes the *_locked flags to update_fields.

        # Maintain the per-entity adaptive-delay trace on the main
        # collection record. Three cases, gated on a real
        # data_max_delay_allowed change so the trace genuinely tracks
        # threshold ownership rather than e.g. isolated future_tolerance
        # updates that also flow through this handler:
        #
        # 1. Caller is trackmesplkadaptivedelay — it submits update_comment
        #    as a JSON object whose "context" field is the string
        #    "automated adaptive delay update". Stamp the trace.
        #
        # 2. Caller is anything else (operator UI manual edit, generic
        #    API caller, malformed JSON comment) — *clear* any
        #    previously-stamped trace by writing empty strings. Without
        #    this, the trace fields persist (they are in persistent_fields
        #    so the decision-maker preserves them) and the UI banner
        #    would falsely report "last refreshed by adaptive delay" with
        #    a stale date after a manual override (bugbot R1 on PR #1655).
        #    The frontend banner condition treats an empty updated_by as
        #    "no trace", so the empty strings correctly hide the banner.
        if data_max_delay_allowed is not None:
            # Default to "no trace" — the adaptive-context branch below
            # overrides this with the actual stamp when applicable.
            update_fields["data_max_delay_allowed_updated_by"] = ""
            update_fields["data_max_delay_allowed_mtime"] = ""
            if update_comment:
                try:
                    parsed_comment = (
                        json.loads(update_comment)
                        if isinstance(update_comment, str)
                        else update_comment
                    )
                    if (
                        isinstance(parsed_comment, dict)
                        and parsed_comment.get("context")
                        == "automated adaptive delay update"
                    ):
                        update_fields[
                            "data_max_delay_allowed_updated_by"
                        ] = "trackmesplkadaptivedelay"
                        update_fields["data_max_delay_allowed_mtime"] = str(
                            int(time.time())
                        )
                except (ValueError, TypeError):
                    # Malformed comment from a non-adaptive caller — the
                    # empty-string defaults set above stand. Never block the
                    # actual threshold update on a trace-stamp parsing error.
                    pass

        # Maintain the threshold intent-lock ledger whenever a request touches a
        # threshold or the lock state. We deliberately do NOT special-case the
        # adaptive-delay write-back caller via update_comment: that field is
        # public request input and must never be trusted as a caller-auth signal
        # (a client could spoof the adaptive context string to bypass intent
        # maintenance and strand a stale pin). The cost is bounded by the EDITED
        # entities (a handful), not the collection size, and the "preserve" path
        # only refreshes entities that are ALREADY locked — so running it on the
        # (always-unlocked, gate-protected) adaptive write-back path is a safe
        # no-op rather than an optimisation worth a spoofable shortcut.
        if (
            lock_threshold is not None
            or data_max_delay_allowed is not None
            or data_max_lag_allowed is not None
        ):
            try:
                vtenant_account = trackme_vtenant_account_from_service(
                    service, tenant_id
                )
            except Exception:
                vtenant_account = None
            # An explicit pin/unpin on a tenant where locking is disabled must
            # fail loudly, not be silently dropped (for a mixed threshold+lock
            # request that would otherwise return success while ignoring the lock).
            if lock_threshold is not None and not threshold_lock_enabled(
                vtenant_account
            ):
                return {
                    "payload": {
                        "error": "delay/latency threshold locking is disabled for this tenant"
                    },
                    "status": 400,
                }
            if threshold_lock_enabled(vtenant_account):
                lock_update_fields, _intent_counts = (
                    apply_threshold_intent_on_manual_update(
                        service,
                        tenant_id,
                        "dsm",
                        collection,
                        object_list,
                        keys_list,
                        lock_threshold,
                        data_max_delay_allowed,
                        data_max_lag_allowed,
                        requested_by="manual",
                        logger=logger,
                    )
                )
                # A preserve-path ledger refresh failure leaves the ledger with
                # the OLD requested value; proceeding would let reconcile later
                # revert the operator's new manual edit. Reject so the entity and
                # ledger stay consistent (operator retries).
                if _intent_counts.get("preserve_refresh_failed"):
                    return {
                        "payload": {
                            "error": "failed to record the pinned threshold update; please retry"
                        },
                        "status": 500,
                    }
                if lock_update_fields:
                    update_fields.update(lock_update_fields)
                # Unified-lock orchestration: the lock is the single user-facing
                # control. Keep the legacy per-entity automation flags in lockstep
                # so the existing gates AND any direct readers (AI advisor, SPL,
                # bulk edit) agree with the lock state. lock=true => no automation
                # (adaptive off, lagging-class overridden); lock=false => fully
                # auto-managed (adaptive on, lagging-class applies).
                if lock_threshold == "true":
                    update_fields["allow_adaptive_delay"] = "false"
                    update_fields["data_override_lagging_class"] = "true"
                elif lock_threshold == "false":
                    update_fields["allow_adaptive_delay"] = "true"
                    update_fields["data_override_lagging_class"] = "false"

        # Deferred guard (see note above): reject only if there is genuinely
        # nothing to write — after the intent block a lock-only request has
        # contributed its *_locked flags here.
        if not update_fields:
            return {
                "payload": {"error": "no valid fields to update"},
                "status": 500,
            }

        # Call the generic update function
        response, status_code = generic_batch_update(
            self,
            request_info,
            update_request_info=update_request_info,
            collection=collection,
            update_fields=update_fields,
            persistent_fields=persistent_fields_dsm,
            component="dsm",
            update_comment=update_comment,
            audit_context="update monitoring lag policy",
            audit_message="Lag policy was updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Update min dcount host by object name
    def post_ds_update_min_dcount_host(self, request_info, **kwargs):
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

                min_dcount_host = resp_dict["min_dcount_host"]
                # We need to accept the string any (to disable the fearure) or an integer
                if str(min_dcount_host) not in ("any"):
                    # anything else than "any" or an integer will fail here
                    min_dcount_host = int(min_dcount_host)

                # min_dcount_field is optional, if not provided we will use global_dcount_host
                try:
                    min_dcount_field = resp_dict["min_dcount_field"]
                    if not min_dcount_field in (
                        "avg_dcount_host_5m",
                        "latest_dcount_host_5m",
                        "perc95_dcount_host_5m",
                        "stdev_dcount_host_5m",
                        "global_dcount_host",
                    ):
                        min_dcount_field = "global_dcount_host"
                except Exception as e:
                    min_dcount_field = "global_dcount_host"

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint configures the minimal number of distinct hosts count for an existing data source, it requires a POST call with the following information:",
                "resource_desc": "Update lag policies for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/write/ds_update_min_dcount_host\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'min_dcount_host': '0', 'min_dcount_field': 'stdev_dcount_host_5m', 'object_list': 'netscreen:netscreen:firewall'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_list": "REQUIRED (with keys_list as alternative). Comma-separated list of entity object names. Either object_list or keys_list must be provided",
                        "keys_list": "REQUIRED (with object_list as alternative). Comma-separated list of entity KV record _keys. Either object_list or keys_list must be provided",
                        "min_dcount_host": "minimal accepted number of distinct count hosts, must be an integer or the string any",
                        "min_dcount_field": "The dictinct count metric to be used for this entity, valid options are: avg_dcount_host_5m, latest_dcount_host_5m, perc95_dcount_host_5m, stdev_dcount_host_5m, global_dcount_host",
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
        collection_name = f"kv_trackme_dsm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "dsm",
            "object_list": object_list,
            "keys_list": keys_list,
        }

        # Prepare the update fields
        update_fields = {
            "min_dcount_host": min_dcount_host,
            "min_dcount_field": min_dcount_field,
        }

        # Call the generic update function
        response, status_code = generic_batch_update(
            self,
            request_info,
            update_request_info=update_request_info,
            collection=collection,
            update_fields=update_fields,
            persistent_fields=persistent_fields_dsm,
            component="dsm",
            update_comment=update_comment,
            audit_context="update min distinct host count",
            audit_message="The min distinct count number of hosts was updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Update monitoring week days by object name
    def post_ds_update_wdays(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/write/ds_update_wdays\" mode=\"post\" body=\"{'tenant_id':'mytenant','object_list':'netscreen:netscreen:firewall','data_monitoring_wdays':'manual:1,2,3,4,5'}\"",
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
        collection_name = f"kv_trackme_dsm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "dsm",
            "object_list": object_list,
            "keys_list": keys_list,
        }

        # Prepare the update fields
        update_fields = {"data_monitoring_wdays": monitoring_wdays}

        # Call the generic update function
        response, status_code = generic_batch_update(
            self,
            request_info,
            update_request_info=update_request_info,
            collection=collection,
            update_fields=update_fields,
            persistent_fields=persistent_fields_dsm,
            component="dsm",
            update_comment=update_comment,
            audit_context="update week days monitoring",
            audit_message="Week days monitoring was updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Update monitoring hours ranges by object name
    def post_ds_update_hours_ranges(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/write/ds_update_hours_ranges\" mode=\"post\" body=\"{'tenant_id':'mytenant', 'object_list':'netscreen:netscreen:firewall', 'data_monitoring_hours_ranges':'manual:8,9,10,11,12,13,14,15,16,17'}\"",
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
        collection_name = f"kv_trackme_dsm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "dsm",
            "object_list": object_list,
            "keys_list": keys_list,
        }

        # Prepare the update fields
        update_fields = {"data_monitoring_hours_ranges": monitoring_hours_ranges}

        # Call the generic update function
        response, status_code = generic_batch_update(
            self,
            request_info,
            update_request_info=update_request_info,
            collection=collection,
            update_fields=update_fields,
            persistent_fields=persistent_fields_dsm,
            component="dsm",
            update_comment=update_comment,
            audit_context="update hours ranges monitoring",
            audit_message="Monitoring hours ranges were updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Update monitoring time policy and rules by object name
    def post_ds_update_monitoring_time(self, request_info, **kwargs):
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
                "describe": "This endpoint configures the monitoring time policy and rules for an existing data source, it requires a POST call with the following information:",
                "resource_desc": "Update monitoring time policy/rules for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/write/ds_update_monitoring_time\" mode=\"post\" body=\"{'tenant_id':'mytenant','object_list':'netscreen:netscreen:firewall','monitoring_time_policy':'business_days_08h_20h'}\"",
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
        collection_name = f"kv_trackme_dsm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "dsm",
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
            persistent_fields=persistent_fields_dsm,
            component="dsm",
            update_comment=update_comment,
            audit_context="update monitoring time policy/rules",
            audit_message="Monitoring time policy/rules were updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Remove object entities
    def post_ds_delete(self, request_info, **kwargs):
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
                "describe": "This endpoint performs a temporary deletion of an existing data source, it requires a POST call with the following information:",
                "resource_desc": "Delete one or more entities, either temporarily or permanently",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/write/ds_delete\" mode=\"post\" body=\"{'tenant_id':'mytenant', 'deletion_type': 'temporary', 'object_list':'netscreen:netscreen:firewall,wineventlog:WinEventLog'}\"",
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
        collection_name = f"kv_trackme_dsm_tenant_{tenant_id}"
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
            f"kv_trackme_dsm_outliers_entity_rules_tenant_{tenant_id}"
        )
        collection_entity_rules = service.kvstore[collection_outliers_entity_rules_name]

        # data rules collection
        collection_outliers_entity_data_name = (
            f"kv_trackme_dsm_outliers_entity_data_tenant_{tenant_id}"
        )
        collection_outliers_entity_data = service.kvstore[
            collection_outliers_entity_data_name
        ]

        #
        # Data sampling collection
        #

        # sampling
        collection_sampling_name = f"kv_trackme_dsm_data_sampling_tenant_{tenant_id}"
        collection_sampling = service.kvstore[collection_sampling_name]

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
                                    {"object": obj, "object_category": "splk-dsm"}
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
                                    "object_category": "splk-dsm",
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

            # Batch delete data sampling records
            try:
                collection_sampling.data.delete(
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
                        "object_category": "splk-dsm",
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
                    delete_shadow_records(service_system, tenant_id, "dsm", deleted_keys, shadow_enabled=shadow_enabled)
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
                "dsm",
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

    # Enable/Disable Data Sampling by object name
    def post_ds_manage_data_sampling(self, request_info, **kwargs):
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
                if action not in ("enable", "disable", "reset", "run"):
                    return {
                        "payload": 'invalid value for action="{}", valid options are: enable | disable | reset| run',
                        "status": 200,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint allows management of the data sampling feature for an existing data source by the data source name (object), it requires a POST call with the following information:",
                "resource_desc": "Enable/Disable/Reset/Run Data Sampling for one or more entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/write/ds_manage_data_sampling\" mode=\"post\" body=\"{'tenant_id':'mytenant', 'action': 'reset', 'object_list': 'netscreen:netscreen:firewall'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_list": "REQUIRED (with keys_list as alternative). Comma-separated list of entity object names. Either object_list or keys_list must be provided",
                        "keys_list": "REQUIRED (with object_list as alternative). Comma-separated list of entity KV record _keys. Either object_list or keys_list must be provided",
                        "action": "the action to be performed, valid options are: enable | disable | reset | run",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Set the value for data_sample_feature
        if action == "enable":
            data_sample_feature = "enabled"
        elif action == "disable":
            data_sample_feature = "disabled"
        elif action == "reset":
            data_sample_feature = "enabled"
        elif action == "run":
            data_sample_feature = "enabled"

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

        # get TrackMe conf
        trackme_conf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        logger.debug(f'trackme_conf="{json.dumps(trackme_conf, indent=2)}"')

        # Data collections

        # component
        collection_name = f"kv_trackme_dsm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # sampling
        collection_sampling_name = f"kv_trackme_dsm_data_sampling_tenant_{tenant_id}"
        collection_sampling = service.kvstore[collection_sampling_name]

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
                    kvrecord = {}
                    key = None

        for key in keys_list:
            try:
                # check if we have a KVrecord already for this object
                query_string = {
                    "$and": [
                        {
                            "_key": key,
                        }
                    ]
                }

                # record from the component
                try:
                    kvrecord = collection.data.query(query=(json.dumps(query_string)))[
                        0
                    ]
                    # object_value
                    object_value = kvrecord.get("object")
                except Exception as e:
                    kvrecord = {}

                # if this entity could not be found
                if not kvrecord:
                    logger.error(
                        f'tenant_id="{tenant_id}", entity not found, object="{object_value}"'
                    )

                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    result = {
                        "object": object_value,
                        "action": action,
                        "result": "failure",
                        "exception": f'tenant_id="{tenant_id}", entity not found, object="{object_value}"',
                    }
                    records.append(result)

                # record from sampling
                try:
                    # try get to get the key
                    kvrecord_sampling = collection_sampling.data.query(
                        query=(json.dumps(query_string))
                    )[0]
                    key_sampling = kvrecord_sampling.get("_key")
                except Exception as e:
                    key_sampling = None
                    kvrecord_sampling = {}

                # if action is enable / disable
                if action in ("enable", "disable"):

                    try:

                        if not kvrecord_sampling:

                            if action == "enable":

                                kvrecord_sampling = {
                                    "_key": key,
                                    "anomaly_reason": "pending",
                                    "current_detected_format": ["pending"],
                                    "data_sample_anomaly_detected": 0,
                                    "data_sample_feature": "pending",
                                    "data_sample_mtime": "pending",
                                    "data_sample_status_colour": "yellow",
                                    "data_sample_status_message": json.dumps(
                                        {
                                            "state": "pending",
                                            "desc": "Data Sampling is pending and was reset for this entity",
                                        }
                                    ),
                                    "data_sampling_nr": trackme_conf["trackme_conf"][
                                        "splk_data_sampling"
                                    ][
                                        "splk_data_sampling_default_sample_record_at_run"
                                    ],
                                    "direction": "none",
                                    "data_sample_feature": "enabled",
                                    "mtime": "pending",
                                    "object": object_value,
                                    "previous_detected_format": ["pending"],
                                }

                            elif action == "disable":

                                kvrecord_sampling = {
                                    "_key": key,
                                    "anomaly_reason": "N/A",
                                    "current_detected_format": ["N/A"],
                                    "data_sample_anomaly_detected": 0,
                                    "data_sample_feature": "N/A",
                                    "data_sample_mtime": "N/A",
                                    "data_sample_status_colour": "N/A",
                                    "data_sample_status_message": json.dumps(
                                        {
                                            "state": "pending",
                                            "desc": "Data Sampling is pending and was reset for this entity",
                                        }
                                    ),
                                    "data_sampling_nr": "N/A",
                                    "direction": "N/A",
                                    "data_sample_feature": "disabled",
                                    "mtime": "N/A",
                                    "object": object_value,
                                    "previous_detected_format": ["N/A"],
                                }

                            # insert the record
                            collection_sampling.data.insert(
                                json.dumps(kvrecord_sampling)
                            )

                        else:

                            # Update the record
                            kvrecord_sampling["data_sample_feature"] = (
                                data_sample_feature
                            )
                            collection_sampling.data.update(
                                key, json.dumps(kvrecord_sampling)
                            )

                        # Record an audit change
                        record = {
                            "object": str(object_value),
                            "data_sample_feature": str(data_sample_feature),
                        }
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "success",
                            f"{action} data sampling",
                            str(object_value),
                            "splk-dsm",
                            str(json.dumps(record, indent=1)),
                            "Data sampling was managed successfully",
                            str(update_comment),
                        )

                        logger.info(
                            f'tenant_id="{tenant_id}", The object was successfully updated'
                        )

                        # increment counter
                        processed_count += 1
                        succcess_count += 1
                        failures_count += 0

                        # append for summary
                        result = {
                            "object": object_value,
                            "action": action,
                            "result": "success",
                            "message": f'tenant_id="{tenant_id}", The object was successfully updated',
                        }
                        records.append(result)

                    except Exception as e:
                        logger.error(
                            f'tenant_id="{tenant_id}", failed to update the entity, object="{object_value}", exception="{str(e)}"'
                        )

                        # increment counter
                        processed_count += 1
                        succcess_count += 0
                        failures_count += 1

                        result = {
                            "object": object_value,
                            "action": action,
                            "result": "failure",
                            "exception": f'tenant_id="{tenant_id}", failed to update the entity, object="{object_value}", exception="{str(e)}"',
                        }
                        records.append(result)

                # if action is reset
                elif action in ("reset", "run"):
                    try:

                        #
                        # reset
                        #

                        if action == "reset":

                            if (
                                kvrecord_sampling
                            ):  # reset is only possible if the record exists
                                try:
                                    # reset the sampling record
                                    current_data_sampling_nr = kvrecord.get("kvrecord")
                                    kvrecord_sampling = {
                                        "anomaly_reason": "pending",
                                        "current_detected_format": ["pending"],
                                        "data_sample_anomaly_detected": 0,
                                        "data_sample_feature": "pending",
                                        "data_sample_mtime": "pending",
                                        "data_sample_status_colour": "yellow",
                                        "data_sample_status_message": json.dumps(
                                            {
                                                "state": "pending",
                                                "desc": "Data Sampling is pending and was reset for this entity",
                                            }
                                        ),
                                        "data_sampling_nr": current_data_sampling_nr,
                                        "direction": "none",
                                        "data_sample_feature": "enabled",
                                        "mtime": "pending",
                                        "object": object_value,
                                        "previous_detected_format": ["pending"],
                                    }
                                    collection_sampling.data.update(
                                        str(key_sampling), json.dumps(kvrecord_sampling)
                                    )
                                    logger.info(
                                        f'tenant_id="{tenant_id}", object="{object_value}", action="{action}", KVstore sampling record was successfully reset'
                                    )

                                    # audit
                                    trackme_audit_event(
                                        request_info.system_authtoken,
                                        request_info.server_rest_uri,
                                        tenant_id,
                                        request_info.user,
                                        "success",
                                        "reset data sampling",
                                        str(object_value),
                                        "splk-dsm",
                                        str(json.dumps(kvrecord_sampling, indent=1)),
                                        "Data sampling was reset successfully",
                                        str(update_comment),
                                    )

                                except Exception as e:
                                    logger.error(
                                        f'tenant_id="{tenant_id}", object="{object_value}", failed to update the KVstore sampling record with exception="{str(e)}"'
                                    )

                                try:
                                    # reset the record
                                    kvrecord["isAnomaly"] = 0
                                    kvrecord["data_sample_lastrun"] = 0

                                    collection.data.update(
                                        str(key), json.dumps(kvrecord)
                                    )
                                    logger.info(
                                        f'tenant_id="{tenant_id}", object="{object_value}", action="{action}", KVstore entity record was successfully reset'
                                    )

                                except Exception as e:
                                    logger.error(
                                        f'tenant_id="{tenant_id}", object="{object_value}", failed to update the entity KVstore record with exception="{str(e)}"'
                                    )

                        #
                        # run
                        #

                        # Define the SPL query
                        kwargs_search = {
                            "app": "trackme",
                            "earliest_time": "-5m",
                            "latest_time": "now",
                            "output_mode": "json",
                            "count": 0,
                        }
                        searchquery = remove_leading_spaces(
                            f"""\
                            | trackmesamplingexecutor tenant_id={tenant_id} object="{object_value}" mode="run_sampling"
                            """
                        )

                        # log debug
                        logger.debug(
                            f'tenant_id="{tenant_id}", object="{object_value}", searchquery="{searchquery}"'
                        )

                        query_results = []
                        # spawn the search and get the results
                        reader = run_splunk_search(
                            service,
                            searchquery,
                            kwargs_search,
                            24,
                            5,
                        )

                        for item in reader:
                            if isinstance(item, dict):
                                query_results.append(item)

                        # increment counter
                        processed_count += 1
                        succcess_count += 1
                        failures_count += 0

                        # append for summary
                        result = {
                            "object": object_value,
                            "action": action,
                            "result": "success",
                            "message": f'tenant_id="{tenant_id}", The action="{action}" was successfully performed',
                            "searchquery": searchquery,
                            "results": query_results,
                        }
                        records.append(result)

                    except Exception as e:
                        logger.error(
                            f'tenant_id="{tenant_id}", failed to perform the action="{action}" for the entity, object="{object_value}", exception="{str(e)}"'
                        )

                        # increment counter
                        processed_count += 1
                        succcess_count += 0
                        failures_count += 1

                        result = {
                            "object": object_value,
                            "action": action,
                            "result": "failure",
                            "exception": f'tenant_id="{tenant_id}", failed to perform the action="{action}" for the entity, object="{object_value}", exception="{str(e)}"',
                        }
                        records.append(result)

            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", general exception, object="{object_value}", exception="{str(e)}"'
                )

                # increment counter
                processed_count += 1
                succcess_count += 0
                failures_count += 1

                result = {
                    "object": object_value,
                    "action": action,
                    "result": "failure",
                    "exception": f'tenant_id="{tenant_id}", failed to update the entity, object="{object_value}", general exception="{str(e)}"',
                }
                records.append(result)

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

    # Update entity specific data sampling settings
    def post_ds_update_data_sampling_entity_settings(self, request_info, **kwargs):
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

                # get params
                min_time_btw_iterations_seconds = resp_dict.get(
                    "min_time_btw_iterations_seconds", None
                )
                pct_min_major_inclusive_model_match = resp_dict.get(
                    "pct_min_major_inclusive_model_match", None
                )
                pct_max_exclusive_model_match = resp_dict.get(
                    "pct_max_exclusive_model_match", None
                )
                max_events_per_sampling_iteration = resp_dict.get(
                    "max_events_per_sampling_iteration", None
                )
                relative_time_window_seconds = resp_dict.get(
                    "relative_time_window_seconds", None
                )

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint allows managing data sampling entities settings, it requires a POST call with the following information:",
                "resource_desc": "Update data sampling entities settings for a comma separated list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/write/ds_update_data_sampling_entity_settings\" mode=\"post\" body=\"{'tenant_id':'mytenant', 'object_list': 'netscreen:netscreen:firewall', 'pct_min_major_inclusive_model_match': 95, 'max_events_per_sampling_iteration': 0, 'max_events_per_sampling_iteration': 10000, 'relative_time_window_seconds': 3600}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_list": "REQUIRED (with keys_list as alternative). Comma-separated list of entity object names. Either object_list or keys_list must be provided",
                        "keys_list": "REQUIRED (with object_list as alternative). Comma-separated list of entity KV record _keys. Either object_list or keys_list must be provided",
                        "min_time_btw_iterations_seconds": "OPTIONAL: the minimum time in seconds between sampling iterations, ex: 3600",
                        "pct_min_major_inclusive_model_match": "OPTIONAL: the minimum percentage of major inclusive model match per sampling iteration, ex: 95",
                        "pct_max_exclusive_model_match": "OPTIONAL: the maximum percentage of exclusive model match per sampling iteration, ex: 0",
                        "max_events_per_sampling_iteration": "OPTIONAL: the maximum number of events per sampling iteration, ex: 10000",
                        "relative_time_window_seconds": "OPTIONAL: the size in seconds of the time window for the sampling operation, relative to the latest event time know for the entity. This setting is used to calculate the earliest_time when performing the sampling search, for instance 3600 means the search will run against the time window will cover up to 1 hour of events according to the latest event time known for the entity, ex: 3600",
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

        collection_name = f"kv_trackme_dsm_data_sampling_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "dsm",
            "object_list": object_list,
            "keys_list": keys_list,
        }

        # Prepare the update fields
        update_fields = {}
        if min_time_btw_iterations_seconds:
            update_fields["min_time_btw_iterations_seconds"] = (
                min_time_btw_iterations_seconds
            )
        if pct_min_major_inclusive_model_match:
            update_fields["pct_min_major_inclusive_model_match"] = (
                pct_min_major_inclusive_model_match
            )
        if pct_max_exclusive_model_match:
            update_fields["pct_max_exclusive_model_match"] = (
                pct_max_exclusive_model_match
            )
        if max_events_per_sampling_iteration:
            update_fields["max_events_per_sampling_iteration"] = (
                max_events_per_sampling_iteration
            )
        if relative_time_window_seconds:
            update_fields["relative_time_window_seconds"] = relative_time_window_seconds

        # Call the generic update function
        response, status_code = generic_batch_update(
            self,
            request_info,
            update_request_info=update_request_info,
            collection=collection,
            update_fields=update_fields,
            persistent_fields=persistent_fields_dsm,
            component="dsm",
            update_comment=update_comment,
            audit_context="update data sampling entity settings",
            audit_message="Data sampling entity settings were updated successfully",
        )

        return {"payload": response, "status": status_code}

    # Update list of manual tags
    def post_ds_update_manual_tags(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/write/ds_update_manual_tags\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'tags_manual': 'mytag1,maytag2,mytag3', 'object_list': 'netscreen:netscreen:firewall,wineventlog:WinEventLog'}\"",
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
        collection_name = f"kv_trackme_dsm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Tags policies collection
        collection_tags_policies_name = f"kv_trackme_dsm_tags_tenant_{tenant_id}"
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
                    "splk-dsm",
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
                "dsm",
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
    def post_ds_update_sla_class(self, request_info, **kwargs):
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
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_dsm/write/ds_update_sla_class\" mode=\"post\" body=\"{'tenant_id':'mytenant','object_list':'netscreen:netscreen:firewall','sla_class':'gold'}\"",
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
        collection_name = f"kv_trackme_dsm_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Prepare the request_info with the necessary data
        update_request_info = {
            "tenant_id": tenant_id,
            "component": "dsm",
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
            persistent_fields=persistent_fields_dsm,
            component="dsm",
            update_comment=update_comment,
            audit_context="update SLA class",
            audit_message="SLA class was updated successfully",
        )

        return {"payload": response, "status": status_code}
