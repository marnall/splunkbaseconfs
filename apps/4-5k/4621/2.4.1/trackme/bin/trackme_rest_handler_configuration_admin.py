#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_configuration.py"
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
import datetime
import requests
import random
from collections import OrderedDict
import urllib.parse

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.configuration_admin", "trackme_rest_api_configuration_admin.log"
)


# import test handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    is_reachable_with_retry,
    trackme_audit_event,
    trackme_create_kvcollection,
    trackme_create_kvtransform,
    trackme_create_macro,
    trackme_create_report,
    trackme_delete_kvcollection,
    trackme_delete_kvtransform,
    trackme_delete_macro,
    trackme_delete_report,
    trackme_getloglevel,
    trackme_parse_describe_flag,
)

# import the collections dict
from collections_data import (
    vtenant_account_default,
    remote_account_default,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerConfigurationAdmin_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerConfigurationAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_configuration(self, request_info, **kwargs):
        response = {
            "resource_group_name": "configuration/admin",
            "resource_group_desc": "These endpoints provide various generic application level configuration capabilities (admin operations)",
        }

        return {"payload": response, "status": 200}

    # Create a Kvstore transforms with privileges escalation
    def post_create_kvtransform(self, request_info, **kwargs):
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
                transform_name = resp_dict["transform_name"]
                transform_fields = resp_dict["transform_fields"]
                collection_name = resp_dict["collection_name"]
                transform_acl = resp_dict["transform_acl"]
                owner = resp_dict["owner"]

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows creating a KVstore transforms knowledge object, it requires a POST with the following options:",
                "resource_desc": "Create KVstore transforms",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/create_kvstore_transforms" body="{\\"tenant_id\\": \\"<tenant_id>\\", \\"transform_name\\": \\"<transform_name>\\", \\"transform_fields\\": \\"<transform_fields>\\", \\"collection_name\\": \\"<collection_name>\\", \\"owner\\": \\"<owner>\\", \\"transform_acl\\": \\"<transform_acl>\\"}"',
                "options": [
                    {
                        "tenant_id": 'REQUIRED. The tenant identifier',
                        "transform_name": 'REQUIRED. Name of the lookup transform to create',
                        "transform_fields": "REQUIRED. Comma-separated list of fields the transform will expose (e.g. 'index,sourcetype,priority')",
                        "collection_name": 'REQUIRED. Name of the underlying KV collection the transform reads from',
                        "owner": 'REQUIRED. The Splunk user that will own the transform',
                        "transform_acl": 'REQUIRED. ACL definition for the transform — JSON object with sharing/owner/perms keys (passed straight to the Splunk transforms.conf endpoint)',
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # create the transform
        try:
            action_create = trackme_create_kvtransform(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                transform_name,
                transform_fields,
                collection_name,
                owner,
                transform_acl,
            )
            return {"payload": action_create, "status": 200}

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'

            # Check if this is a 409 Conflict error (object already exists)
            if "409 Conflict" in str(e) or "already exists" in str(e):
                warning_msg = f'tenant_id="{tenant_id}", transform "{transform_name}" already exists, skipping creation'
                logger.warning(warning_msg)
                return {
                    "payload": {
                        "result": "warning",
                        "message": warning_msg,
                        "transform_name": transform_name,
                        "details": "The transform already exists and was not created",
                    },
                    "status": 202,
                }
            else:
                logger.error(error_msg)
                return {"payload": error_msg, "status": 500}

    # Delete a Kvstore transforms with privileges escalation
    def post_delete_kvtransform(self, request_info, **kwargs):
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
                transform_name = resp_dict["transform_name"]

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows deleting a KVstore transforms knowledge object, it requires a POST with the following options:",
                "resource_desc": "Delete KVstore transforms",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/delete_kvstore_transforms" body="{\\"tenant_id\\": \\"<tenant_id>\\", \\"transform_name\\": \\"<transform_name>\\"}"',
                "options": [
                    {
                        "tenant_id": 'REQUIRED. The tenant identifier',
                        "transform_name": 'REQUIRED. Name of the lookup transform to delete',
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # create the transform
        try:
            action_delete = trackme_delete_kvtransform(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                transform_name,
            )
            return {"payload": action_delete, "status": 200}

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}

    # Delete a Kvstore collection with privileges escalation
    def post_delete_kvcollection(self, request_info, **kwargs):
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
                collection_name = resp_dict["collection_name"]

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows deleting a KVstore collection, it requires a POST with the following options:",
                "resource_desc": "Delete KVstore collection",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/delete_kvstore_collection" body="{\\"tenant_id\\": \\"<tenant_id>\\", \\"collection_name\\": \\"<collection_name>\\"}"',
                "options": [
                    {
                        "tenant_id": 'REQUIRED. The tenant identifier',
                        "collection_name": 'REQUIRED. Name of the KV collection to delete',
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # create the transform
        try:
            action_delete = trackme_delete_kvcollection(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                collection_name,
            )
            return {"payload": action_delete, "status": 200}

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failed to delete the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}

    # Dismiss (delete) a sourcetype cap alert record
    def post_delete_sourcetype_cap_alert(self, request_info, **kwargs):
        describe = False
        alert_key = None

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            alert_key = resp_dict.get("alert_key")
        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows dismissing (deleting) a sourcetype cap alert record, it requires a POST with the following options:",
                "resource_desc": "Dismiss sourcetype cap alert",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/delete_sourcetype_cap_alert" body="{\\"alert_key\\": \\"<_key>\\"}"',
                "options": [
                    {
                        "alert_key": "The _key of the sourcetype cap alert record to dismiss",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        if not alert_key:
            return {"payload": "alert_key is required", "status": 400}

        try:
            # Get service
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=request_info.server_rest_port,
                token=request_info.system_authtoken,
                timeout=600,
            )

            cap_alert_collection = service.kvstore["kv_trackme_sourcetype_cap_alerts"]
            cap_alert_collection.data.delete_by_id(alert_key)

            return {
                "payload": {"status": "success", "deleted": alert_key},
                "status": 200,
            }

        except Exception as e:
            error_msg = f'failed to dismiss sourcetype cap alert, alert_key="{alert_key}", exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}

    # Dismiss (delete) a Configuration Guardian alert record
    def post_dismiss_guardian_alert(self, request_info, **kwargs):
        describe = False
        alert_key = None

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            alert_key = resp_dict.get("alert_key")
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint dismisses (deletes) a Configuration Guardian alert record. It requires a POST with the following options:",
                "resource_desc": "Dismiss Configuration Guardian alert",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/dismiss_guardian_alert" body="{\\"alert_key\\": \\"<_key>\\"}"',
                "options": [
                    {
                        "alert_key": "The _key of the Configuration Guardian alert record to dismiss. Dismissal is temporary — if the underlying condition persists, the alert is re-created at the next detection cycle.",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        if not alert_key:
            return {"payload": "alert_key is required", "status": 400}

        try:
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=request_info.server_rest_port,
                token=request_info.system_authtoken,
                timeout=600,
            )

            from trackme_libs_guardian import (
                dismiss_guardian_alert_by_key,
                resolve_audit_index_name,
            )

            # Route the dismissal through the helper so the audit trail
            # records the transition (action=guardian_alert_cleared,
            # reason=dismissed_by_admin) — bypassing it would leave a hole in
            # the post-mortem timeline.
            audit_index_name = resolve_audit_index_name(service)
            deleted = dismiss_guardian_alert_by_key(
                service, alert_key, audit_index_name=audit_index_name
            )

            return {
                "payload": {
                    "status": "success" if deleted else "not_found",
                    "deleted": alert_key if deleted else None,
                },
                "status": 200,
            }

        except Exception as e:
            error_msg = (
                f'failed to dismiss guardian alert, alert_key="{alert_key}", '
                f'exception="{str(e)}"'
            )
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}

    # Run Configuration Guardian checks on demand
    def post_run_guardian_checks(self, request_info, **kwargs):
        describe = False
        tenant_id_filter = None
        check_type_filter = None

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            tenant_id_filter = resp_dict.get("tenant_id") or None
            check_type_filter = resp_dict.get("check_type") or None
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint runs the Configuration Guardian checks on demand. If no filters are provided, every registered check runs against every enabled Virtual Tenant (for tenant-scoped checks). Returns a delta describing which alerts were created, cleared, or unchanged.",
                "resource_desc": "Run Configuration Guardian checks on demand",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/run_guardian_checks" body="{\\"tenant_id\\": \\"<optional>\\", \\"check_type\\": \\"<optional>\\"}"',
                "options": [
                    {
                        "tenant_id": "Optional — restrict the scan to a single tenant.",
                        "check_type": "Optional — restrict the scan to a single check (e.g. insufficient_tenant_owner_capabilities).",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        try:
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=request_info.server_rest_port,
                token=request_info.system_authtoken,
                timeout=600,
            )

            # Load tenant records once for tenant-scoped checks
            tenant_records = []
            try:
                vtenants_collection = service.kvstore["kv_trackme_virtual_tenants"]
                if tenant_id_filter:
                    query = json.dumps({"tenant_id": str(tenant_id_filter)})
                    tenant_records = list(vtenants_collection.data.query(query=query))
                else:
                    tenant_records = list(vtenants_collection.data.query())
            except Exception as e:
                logger.error(
                    f'failed to load tenant records for guardian checks, exception="{str(e)}"'
                )
                return {
                    "payload": f"failed to load tenant records, exception={str(e)}",
                    "status": 500,
                }

            from trackme_libs_guardian import run_checks, resolve_audit_index_name

            # Resolve the configured audit index so on-demand check runs write
            # their transition events to the same destination as the scheduled
            # tasks (trackmetrackerhealth.py / trackmegeneralhealthmanager.py).
            # Fails open to the hardcoded default if trackme_settings is unreadable.
            audit_index_name = resolve_audit_index_name(service)

            delta = run_checks(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                service,
                tenant_records,
                tenant_id=str(tenant_id_filter) if tenant_id_filter else None,
                check_type=check_type_filter,
                audit_index_name=audit_index_name,
            )

            return {
                "payload": {
                    "status": "success",
                    "tenant_id_filter": tenant_id_filter,
                    "check_type_filter": check_type_filter,
                    "delta": delta,
                    "counts": {
                        "created": len(delta.get("created", [])),
                        "cleared": len(delta.get("cleared", [])),
                        "unchanged": len(delta.get("unchanged", [])),
                        "skipped": len(delta.get("skipped", [])),
                    },
                },
                "status": 200,
            }

        except Exception as e:
            error_msg = (
                f'failed to run guardian checks, exception="{str(e)}"'
            )
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}

    # List active Configuration Guardian alerts, enriched for AI consumption
    def get_guardian_alerts(self, request_info, **kwargs):
        """List every active Configuration Guardian alert with full context.

        Designed as the canonical read endpoint for both admins and AI agents —
        the payload de-serialises ``metadata`` (stored as a JSON string in the
        KV) and exposes a structured ``recommended_actions`` array that the
        agent can parse directly.

        Optional query-string (or JSON body) filters: ``tenant_id``,
        ``check_type``, ``severity``, ``scope``.
        """
        describe = False
        tenant_id_filter = None
        check_type_filter = None
        severity_filter = None
        scope_filter = None

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id_filter = resp_dict.get("tenant_id") or None
                check_type_filter = resp_dict.get("check_type") or None
                severity_filter = resp_dict.get("severity") or None
                scope_filter = resp_dict.get("scope") or None

        if describe:
            response = {
                "describe": (
                    "Lists every active Configuration Guardian alert with a "
                    "ready-to-consume payload — `metadata` is parsed from JSON "
                    "and each alert exposes `recommended_actions`. Optional "
                    "body filters narrow the result set."
                ),
                "resource_desc": "List active Configuration Guardian alerts (AI-ready)",
                "resource_spl_example": (
                    '| trackme mode=get url="/services/trackme/v2/configuration/admin/guardian_alerts"'
                ),
                "options": [
                    {
                        "tenant_id": "Optional — restrict to a single tenant.",
                        "check_type": "Optional — e.g. insufficient_tenant_owner_capabilities.",
                        "severity": "Optional — 'warning' or 'critical'.",
                        "scope": "Optional — 'tenant' or 'system'.",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        try:
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=request_info.server_rest_port,
                token=request_info.system_authtoken,
                timeout=600,
            )

            from trackme_libs_guardian import GUARDIAN_COLLECTION_NAME

            collection = service.kvstore[GUARDIAN_COLLECTION_NAME]
            rows = list(collection.data.query() or [])

            enriched = []
            counts_by_check_type = {}
            counts_by_severity = {"warning": 0, "critical": 0}
            for row in rows:
                if tenant_id_filter and str(row.get("tenant_id") or "") != str(tenant_id_filter):
                    continue
                if check_type_filter and row.get("check_type") != check_type_filter:
                    continue
                if severity_filter and row.get("severity") != severity_filter:
                    continue
                if scope_filter and row.get("scope") != scope_filter:
                    continue

                # Parse metadata from string into structured JSON for AI consumption
                metadata_raw = row.get("metadata")
                metadata_parsed = None
                if isinstance(metadata_raw, str) and metadata_raw.strip():
                    try:
                        metadata_parsed = json.loads(metadata_raw)
                    except Exception:
                        metadata_parsed = None

                recommended_actions = []
                if isinstance(metadata_parsed, dict):
                    ra = metadata_parsed.get("recommended_actions")
                    if isinstance(ra, list):
                        recommended_actions = ra

                enriched_row = {
                    "_key": row.get("_key"),
                    "check_type": row.get("check_type"),
                    "severity": row.get("severity"),
                    "scope": row.get("scope"),
                    "tenant_id": row.get("tenant_id") or "",
                    "subject": row.get("subject") or "",
                    "title": row.get("title"),
                    "message": row.get("message"),
                    "remediation": row.get("remediation"),
                    "metadata_json": metadata_parsed,
                    "metadata_raw": metadata_raw,
                    "recommended_actions": recommended_actions,
                    "mtime": row.get("mtime"),
                }
                enriched.append(enriched_row)

                check_type_value = row.get("check_type") or "unknown"
                counts_by_check_type[check_type_value] = (
                    counts_by_check_type.get(check_type_value, 0) + 1
                )
                sev = row.get("severity") or "warning"
                if sev in counts_by_severity:
                    counts_by_severity[sev] += 1

            return {
                "payload": {
                    "status": "success",
                    "count": len(enriched),
                    "counts_by_check_type": counts_by_check_type,
                    "counts_by_severity": counts_by_severity,
                    "filters": {
                        "tenant_id": tenant_id_filter,
                        "check_type": check_type_filter,
                        "severity": severity_filter,
                        "scope": scope_filter,
                    },
                    "alerts": enriched,
                },
                "status": 200,
            }

        except Exception as e:
            error_msg = f'failed to list guardian alerts, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}

    # Create a report with privileges escalation
    def post_create_report(self, request_info, **kwargs):
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
                report_name = resp_dict["report_name"]
                report_search = resp_dict["report_search"]
                report_properties = resp_dict["report_properties"]
                report_acl = resp_dict["report_acl"]

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows creating a TrackMe report knowledge object, it requires a POST with the following options:",
                "resource_desc": "Create TrackMe report",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/create_report" body="{\\"tenant_id\\": \\"<tenant_id>\\", \\"report_name\\": \\"<report_name>\\", \\"report_search\\": \\"<report_search>\\", \\"report_properties\\": \\"<report_properties>\\", \\"report_acl\\": \\"<report_acl>\\"}"',
                "options": [
                    {
                        "tenant_id": 'REQUIRED. The tenant identifier',
                        "report_name": 'REQUIRED. Name of the saved-search (report) to create',
                        "report_search": 'REQUIRED. The SPL search string the report will execute',
                        "report_properties": 'REQUIRED. JSON object of saved-search properties (cron_schedule, earliest_time, latest_time, dispatch.*, etc.) to apply to the report',
                        "report_acl": 'REQUIRED. ACL definition for the report — JSON object with sharing/owner/perms keys (passed straight to the Splunk savedsearches endpoint)',
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # create the transform
        try:
            action_create = trackme_create_report(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                report_name,
                report_search,
                report_properties,
                report_acl,
            )
            return {"payload": action_create, "status": 200}

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failed to create the report definition, report="{report_name}", exception="{str(e)}"'

            # Check if this is a 409 Conflict error (object already exists)
            if "409 Conflict" in str(e) or "already exists" in str(e):
                warning_msg = f'tenant_id="{tenant_id}", report "{report_name}" already exists, skipping creation'
                logger.warning(warning_msg)
                return {
                    "payload": {
                        "result": "warning",
                        "message": warning_msg,
                        "report_name": report_name,
                        "details": "The report already exists and was not created",
                    },
                    "status": 202,
                }
            else:
                logger.error(error_msg)
                return {"payload": error_msg, "status": 500}

    # Delete a report with privileges escalation
    def post_delete_report(self, request_info, **kwargs):
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
                report_name = resp_dict["report_name"]

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows deleting a TrackMe report knowledge object, it requires a POST with the following options:",
                "resource_desc": "Create delete report",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/delete_report" body="{\\"tenant_id\\": \\"<tenant_id>\\", \\"report_name\\": \\"<report_name>\\"}"',
                "options": [
                    {
                        "tenant_id": 'REQUIRED. The tenant identifier',
                        "report_name": 'REQUIRED. Name of the saved-search (report) to delete',
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # create the transform
        try:
            action_delete = trackme_delete_report(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                report_name,
            )
            return {"payload": action_delete, "status": 200}

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failed to delete the report definition, report="{report_name}", exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}

    # Update a report with privileges escalation
    def post_update_report(self, request_info, **kwargs):
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
                report_name = resp_dict["report_name"]
                report_search = resp_dict.get("report_search")
                # Retrieving earliest and latest time from the request
                earliest_time = resp_dict.get("earliest_time")
                latest_time = resp_dict.get("latest_time")
                # schedule_window from the request
                schedule_window = resp_dict.get("schedule_window")
                # cron_schedule from the request
                cron_schedule = resp_dict.get("cron_schedule")

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows updating a TrackMe report knowledge object, it requires a POST with the following options:",
                "resource_desc": "Update TrackMe report",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/update_report" body="{\\"tenant_id\\": \\"<tenant_id>\\", \\"report_name\\": \\"<report_name>\\", \\"report_search\\": \\"<report_search>\\"}"',
                "options": [
                    {
                        "tenant_id": 'REQUIRED. The tenant identifier',
                        "report_name": 'REQUIRED. Name of the saved-search (report) to update',
                        "report_search": 'OPTIONAL. New SPL search string. Omit to leave unchanged',
                        "cron_schedule": 'OPTIONAL. New cron schedule',
                        "earliest_time": 'OPTIONAL. New earliest time quantifier',
                        "latest_time": 'OPTIONAL. New latest time quantifier',
                        "schedule_window": "OPTIONAL. New schedule_window value (in seconds, or 'auto')",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # update the report
        report_current = service.saved_searches[report_name]

        try:
            update_params = {}
            if report_search is not None:
                update_params["search"] = report_search
            if earliest_time is not None:
                update_params["dispatch.earliest_time"] = earliest_time
            if latest_time is not None:
                update_params["dispatch.latest_time"] = latest_time
            if schedule_window is not None:
                update_params["schedule_window"] = schedule_window
            if cron_schedule is not None:
                update_params["cron_schedule"] = cron_schedule

            action_update = report_current.update(**update_params)

            return {
                "payload": {
                    "action": "success",
                    "response": "The report was updated successfully",
                    "report_name": report_name,
                },
                "status": 200,
            }

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failed to update the report definition, report="{report_name}", exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}

    # Create a macro with privileges escalation
    def post_create_macro(self, request_info, **kwargs):
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
                macro_name = resp_dict["macro_name"]
                macro_definition = resp_dict["macro_definition"]
                macro_owner = resp_dict["macro_owner"]
                macro_acl = resp_dict["macro_acl"]
        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows creating a macro knowledge object, it requires a POST with the following options:",
                "resource_desc": "Create macro",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/create_macro" body="{\\"tenant_id\\": \\"<tenant_id>\\", \\"macro_name\\": \\"<macro_name>\\", \\"macro_definition\\": \\"<macro_definition>\\", \\"macro_owner\\": \\"<macro_owner>\\", \\"macro_acl\\": \\"<macro_acl>\\"}"',
                "options": [
                    {
                        "tenant_id": 'REQUIRED. The tenant identifier',
                        "macro_name": 'REQUIRED. Name of the macro to create',
                        "macro_definition": 'REQUIRED. The SPL fragment that the macro expands to',
                        "macro_owner": 'REQUIRED. The Splunk user that will own the macro',
                        "macro_acl": 'REQUIRED. ACL definition for the macro — JSON object with sharing/owner/perms keys',
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # create the transform
        try:
            action_create = trackme_create_macro(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                macro_name,
                macro_definition,
                macro_owner,
                macro_acl,
            )
            return {"payload": action_create, "status": 200}

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failed to create the macro definition, macro="{macro_name}", exception="{str(e)}"'

            # Check if this is a 409 Conflict error (object already exists)
            if "409 Conflict" in str(e) or "already exists" in str(e):
                warning_msg = f'tenant_id="{tenant_id}", macro "{macro_name}" already exists, skipping creation'
                logger.warning(warning_msg)
                return {
                    "payload": {
                        "result": "warning",
                        "message": warning_msg,
                        "macro_name": macro_name,
                        "details": "The macro already exists and was not created",
                    },
                    "status": 202,
                }
            else:
                logger.error(error_msg)
                return {"payload": error_msg, "status": 500}

    # Update a macro with privileges escalation
    def post_update_macro(self, request_info, **kwargs):
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
                macro_name = resp_dict["macro_name"]
                macro_definition = resp_dict["macro_definition"]

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows updating a TrackMe macro knowledge object, it requires a POST with the following options:",
                "resource_desc": "update TrackMe macro",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/update_macro" body="{\\"tenant_id\\": \\"<tenant_id>\\", \\"macro_name\\": \\"<macro_name>\\", \\"macro_definition\\": \\"<macro_definition>\\"}"',
                "options": [
                    {
                        "tenant_id": 'REQUIRED. The tenant identifier',
                        "macro_name": 'REQUIRED. Name of the macro to update',
                        "macro_definition": 'REQUIRED. The new SPL fragment that the macro expands to',
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # update the macro

        macro_current = service.confs["macros"][macro_name]

        try:
            action_update = macro_current.update(definition=macro_definition)
            return {
                "payload": {
                    "action": "success",
                    "response": "The macro was updated successfully",
                    "macro_name": macro_name,
                },
                "status": 200,
            }

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failed to update the macro definition, macro="{macro_name}", exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}

    # Delete a macro with privileges escalation
    def post_delete_macro(self, request_info, **kwargs):
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
                macro_name = resp_dict["macro_name"]

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows deleting a macro knowledge object, it requires a POST with the following options:",
                "resource_desc": "Delete macro",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/delete_macro" body="{\\"tenant_id\\": \\"<tenant_id>\\", \\"macro_name\\": \\"<macro_name>\\"}"',
                "options": [
                    {
                        "tenant_id": 'REQUIRED. The tenant identifier',
                        "macro_name": 'REQUIRED. Name of the macro to delete',
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # create the transform
        try:
            action_delete = trackme_delete_macro(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                macro_name,
            )
            return {"payload": action_delete, "status": 200}

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failed to delete the macro definition, macro="{macro_name}", exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}

    # Create a KVstore collection with privileges escalation
    def post_create_kvcollection(self, request_info, **kwargs):
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
                collection_name = resp_dict["collection_name"]
                collection_acl = resp_dict["collection_acl"]
        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows creating a Kvstore collection, it requires a POST with the following options:",
                "resource_desc": "Create KVstore collection",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/create_kvcollection" body="{\\"tenant_id\\": \\"<tenant_id>\\", \\"collection_name\\": \\"<collection_name>\\", \\"collection_acl\\": \\"<collection_acl>\\"}"',
                "options": [
                    {
                        "tenant_id": 'REQUIRED. The tenant identifier',
                        "collection_name": 'REQUIRED. Name of the KV collection to create',
                        "collection_acl": 'REQUIRED. ACL definition for the collection — JSON object with sharing/owner/perms keys',
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # create the transform
        try:
            action_create = trackme_create_kvcollection(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                collection_name,
                collection_acl,
            )
            return {"payload": action_create, "status": 200}

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'

            # Check if this is a 409 Conflict error (object already exists)
            if "409 Conflict" in str(e) or "already exists" in str(e):
                warning_msg = f'tenant_id="{tenant_id}", KVstore collection "{collection_name}" already exists, skipping creation'
                logger.warning(warning_msg)
                return {
                    "payload": {
                        "result": "warning",
                        "message": warning_msg,
                        "collection_name": collection_name,
                        "details": "The KVstore collection already exists and was not created",
                    },
                    "status": 202,
                }
            else:
                logger.error(error_msg)
                return {"payload": error_msg, "status": 500}

    # Verify and update the Virtual Tenant account with privileges escalation
    def post_maintain_vtenant_account(self, request_info, **kwargs):
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

                # updated_vtenant_data is optional
                try:
                    updated_vtenant_data = resp_dict["updated_vtenant_data"]
                    # if not a dictionary, attempt to load it
                    if not isinstance(updated_vtenant_data, dict):
                        try:
                            updated_vtenant_data = json.loads(updated_vtenant_data)
                        except Exception as e:
                            error_msg = f"failed to load updated_vtenant_data, exception={str(e)}"
                            logger.error(error_msg)
                            return {"payload": error_msg, "status": 500}

                except Exception as e:
                    updated_vtenant_data = None

                # force_create_missing is optional, accept true/false case insensitive and turn it into a boolean
                try:
                    force_create_missing = resp_dict["force_create_missing"]
                    if not isinstance(force_create_missing, bool):
                        force_create_missing = force_create_missing.lower()
                        if force_create_missing in ("true"):
                            force_create_missing = True
                        elif force_create_missing in ("false"):
                            force_create_missing = False
                        else:
                            return {
                                "payload": "force_create_missing must be a boolean, true or false",
                                "status": 500,
                            }

                except Exception as e:
                    force_create_missing = False

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoints allows verifying and updating the Virtual Tenant account with privileges escalation, it requires a POST with the following options:",
                "resource_desc": "Create KVstore collection",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/maintain_vtenant_account" body="{\\"tenant_id\\": \\"<tenant_id>\\"}"',
                "options": [
                    {
                        "tenant_id": "The Virtual Tenant ID",
                        "updated_vtenant_data": "Optional, a dictionary with the updated Virtual Tenant data",
                        "force_create_missing": "Optional, if set to true, will force the creation of the Virtual Tenant account if it entirely missing, defaults to false.",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        #
        # main
        #

        url = f"{request_info.server_rest_uri}/servicesNS/nobody/trackme/trackme_vtenants/{tenant_id}"
        vtenant_data = {}

        # vtenant_account_found boolean
        vtenant_account_found = False

        # update boolean - if the current of the Virtual Tenants is missing any key from the default config, we need to update it
        update_is_required = False

        try:
            # Get current vtenant account configuration
            response = requests.get(
                url,
                headers={"Authorization": f"Splunk {request_info.system_authtoken}"},
                verify=False,
                params={"output_mode": "json"},
                timeout=600,
            )
            if response.status_code in (200, 201, 204):

                logger.info(f"successfully retrieved vtenant configuration")
                vtenant_data_json = response.json()
                vtenant_data_current = vtenant_data_json["entry"][0]["content"]

                # Set vtenant_account_found to True
                vtenant_account_found = True

                # Start with the current configuration and add missing keys from the default config
                # We keep all keys from the current configuration
                for key, value in vtenant_data_current.items():
                    if key in vtenant_account_default:
                        vtenant_data[key] = value

                # before merging with the default config, check if any key is missing
                for key in vtenant_account_default.keys():
                    if key not in vtenant_data:
                        update_is_required = True

                # Merge with default config, only adding missing default keys
                for key, value in vtenant_account_default.items():
                    if key not in vtenant_data:
                        vtenant_data[key] = value

                # If updated_vtenant_data is provided, it takes precedence over the defaults and current config
                if updated_vtenant_data:
                    vtenant_data.update(updated_vtenant_data)

                # Finally, ensures that each key in vtenant_data exists in vtenant_account_default, otherwise drop it
                vtenant_data = {
                    key: value
                    for key, value in vtenant_data.items()
                    if key in vtenant_account_default
                }

                logger.info(
                    f'vtenant_data="{json.dumps(vtenant_data, indent=2)}", update_is_required={update_is_required}'
                )

            else:
                error_msg = f"failed to retrieve vtenant configuration, status_code={response.status_code}"
                logger.error(error_msg)

        except Exception as e:
            error_msg = f"failed to retrieve vtenant configuration, exception={str(e)}"
            logger.error(error_msg)

        # init return_response
        return_response = {}

        #
        # if Virtual Tenant account is not found
        #

        # not found and force_create_missing is set to true
        if not vtenant_account_found and force_create_missing:
            url = f"{request_info.server_rest_uri}/servicesNS/nobody/trackme/trackme_vtenants"

            # load default vtenant config
            data = dict(vtenant_account_default)

            # add the name value
            data["name"] = tenant_id

            # Retrieve and set the tenant idx, if any failure, logs and use the global index
            try:
                response = requests.post(
                    url,
                    headers={
                        "Authorization": f"Splunk {request_info.system_authtoken}",
                        "Content-Type": "application/json",
                    },
                    data=data,
                    params={"output_mode": "json"},
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 204):

                    # set response
                    return_response["result"] = "failed"
                    return_response["message"] = (
                        f"failed to create vtenant account, status_code={response.status_code}, response={response.text}"
                    )
                    return_response["vtenant_account"] = None

                    # log
                    logger.error(return_response.get("message"))

                    # return return_response
                    return {"payload": return_response, "status": 500}

                else:

                    # set response
                    return_response["result"] = "success"
                    return_response["message"] = (
                        f"vtenant account created successfully, status_code={response.status_code}"
                    )
                    return_response["vtenant_account"] = data

                    # log
                    logger.info(return_response.get("message"))

                    # return response
                    return {"payload": return_response, "status": 200}

            except Exception as e:

                # set response
                return_response["result"] = "failed"
                return_response["message"] = (
                    f"failed to create vtenant account, exception={str(e)}"
                )
                return_response["vtenant_account"] = None

                # log
                logger.error(return_response.get("message"))

                # return response
                return {"payload": return_response, "status": 500}

        # not found and force_create_missing is not set to true
        elif not vtenant_account_found and not force_create_missing:

            # set response
            return_response["result"] = "failed"
            return_response["message"] = (
                f"vtenant account not found and force_create_missing is not set to true"
            )
            return_response["vtenant_account"] = None

            # log
            logger.error(return_response.get("message"))

            # return return_response
            return {"payload": return_response, "status": 500}

        #
        # main: Virtual Tenant account is found, if update is required, proceed with updating, otherwise return the account
        #

        # no update required
        if not update_is_required:

            # set response
            return_response["result"] = "success"
            return_response["message"] = (
                f"vtenant configuration checked successfully, no update required, status_code={response.status_code}"
            )
            return_response["vtenant_account"] = vtenant_data

            # log
            logger.info(return_response.get("message"))

            # return return_response
            return {"payload": return_response, "status": 200}

        # update required
        else:

            try:
                logger.info(
                    f'attempting to update vtenant configuration, vtenant_data="{json.dumps(vtenant_data, indent=2)}"'
                )
                response = requests.post(
                    url,
                    headers={
                        "Authorization": f"Splunk {request_info.system_authtoken}",
                        "Content-Type": "application/json",
                    },
                    data=vtenant_data,
                    verify=False,
                    timeout=600,
                )
                if response.status_code in (200, 201, 204):

                    # set response
                    return_response["result"] = "success"
                    return_response["message"] = (
                        f"vtenant configuration updated successfully, status_code={response.status_code}"
                    )
                    return_response["vtenant_account"] = vtenant_data

                    # log
                    logger.info(return_response.get("message"))

                    # return response
                    return {"payload": return_response, "status": 200}

                else:

                    # set return_response
                    return_response["result"] = "failed"
                    return_response["message"] = (
                        f"failed to update vtenant configuration, status_code={response.status_code}, response={response.text}"
                    )
                    return_response["vtenant_account"] = None

                    # log
                    logger.error(return_response.get("message"))

                    # return return_response
                    return {"payload": return_response, "status": 500}

            except Exception as e:

                # set response
                return_response["result"] = "failed"
                return_response["message"] = (
                    f"failed to update vtenant configuration, exception={str(e)}"
                )
                return_response["vtenant_account"] = None

                # log
                logger.error(return_response.get("message"))

                # return response
                return {"payload": return_response, "status": 500}

    # Retrieve the Virtual Tenant account configuration
    def post_get_vtenant_account(self, request_info, **kwargs):
        # Initialize response
        return_response = {}
        describe = False

        try:
            # Parse the request payload
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
            describe = resp_dict.get("describe", False)

            # Convert describe to boolean if it's a string
            if isinstance(describe, str) and describe.lower() in ("true", "false"):
                describe = describe.lower() == "true"

            tenant_id = resp_dict.get("tenant_id")
            if not tenant_id and not describe:
                return {
                    "payload": "Missing tenant_id in the request payload.",
                    "status": 400,
                }
        except Exception as e:
            if not describe:
                error_msg = f"Invalid payload format: {str(e)}"
                logger.error(error_msg)
                return {"payload": error_msg, "status": 400}

        # If describe is requested, return the endpoint usage details
        if describe:
            response = {
                "describe": "This endpoint retrieves the Virtual Tenant account configuration, it requires a POST with the following options",
                "resource_desc": "Retrieve Virtual Tenant account",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/get_vtenant_account" body="{\\"tenant_id\\": \\"<tenant_id>\\"}"',
                "options": [
                    {
                        "tenant_id": "The Virtual Tenant ID",
                        "describe": "Optional, if set to true, returns the endpoint description and usage details.",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Build the URL for retrieving the Virtual Tenant account
        url = f"{request_info.server_rest_uri}/servicesNS/nobody/trackme/trackme_vtenants/{tenant_id}"

        try:
            # Send a GET request to retrieve the account configuration
            response = requests.get(
                url,
                headers={"Authorization": f"Splunk {request_info.system_authtoken}"},
                verify=False,
                params={"output_mode": "json"},
                timeout=600,
            )

            if response.status_code in (200, 201, 204):
                # Parse the response JSON
                vtenant_data_json = response.json()

                # Extract the account content
                if "entry" in vtenant_data_json and len(vtenant_data_json["entry"]) > 0:
                    vtenant_data = vtenant_data_json["entry"][0]["content"]

                    # Set successful response
                    return_response["result"] = "success"
                    return_response["message"] = (
                        "Virtual Tenant account retrieved successfully."
                    )
                    return_response["vtenant_account"] = vtenant_data

                    logger.info(return_response["message"])
                    return {"payload": return_response, "status": 200}
                else:
                    # Handle case where account content is not found
                    return_response["result"] = "failed"
                    return_response["message"] = (
                        "Virtual Tenant account content not found."
                    )
                    return_response["vtenant_account"] = None

                    logger.error(return_response["message"])
                    return {"payload": return_response, "status": 404}
            else:
                # Handle HTTP error responses
                error_msg = f"Failed to retrieve Virtual Tenant account, status_code={response.status_code}, response={response.text}"
                logger.error(error_msg)
                return {"payload": error_msg, "status": response.status_code}

        except Exception as e:
            # Handle exceptions during the GET request
            error_msg = (
                f"Exception occurred while retrieving Virtual Tenant account: {str(e)}"
            )
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}

    # Verify and update the Splunk Remote Accounts with privileges escalation
    def post_maintain_remote_account(self, request_info, **kwargs):
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

            if not describe:

                # accounts, if not a list, attempt to load it from csv
                accounts = resp_dict.get("accounts", "*")
                if not isinstance(accounts, list) and accounts != "*":
                    accounts = accounts.split(",")

                # show_token is optional, accept true/false case insensitive and turn it into a boolean
                try:
                    show_token = resp_dict["show_token"]
                    if isinstance(show_token, str):
                        show_token = show_token.lower()
                        if show_token in ("true"):
                            show_token = True
                        elif show_token in ("false"):
                            show_token = False
                    elif isinstance(show_token, bool):
                        pass
                    elif isinstance(show_token, int):
                        show_token = bool(show_token)
                    else:
                        return {
                            "payload": "show_token must be a boolean, true or false",
                            "status": 500,
                        }

                except Exception as e:
                    show_token = False

                # force_tokens_rotation is optional, accept true/false case insensitive and turn it into a boolean
                try:
                    force_tokens_rotation = resp_dict["force_tokens_rotation"]
                    if isinstance(force_tokens_rotation, str):
                        force_tokens_rotation = force_tokens_rotation.lower()
                        if force_tokens_rotation in ("true"):
                            force_tokens_rotation = True
                        elif force_tokens_rotation in ("false"):
                            force_tokens_rotation = False
                    elif isinstance(force_tokens_rotation, bool):
                        pass
                    elif isinstance(force_tokens_rotation, int):
                        force_tokens_rotation = bool(force_tokens_rotation)
                    else:
                        return {
                            "payload": "force_tokens_rotation must be a boolean, true or false",
                            "status": 500,
                        }

                except Exception as e:
                    force_tokens_rotation = False

                update_comment = resp_dict.get("update_comment") or "API update"

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint maintains (verify and update parameters, perform bearer token rotation) Splunk Remote Accounts, it requires a POST with the following options:",
                "resource_desc": "Verify, maintain and tokens rotation for Splunk Remote Accounts",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/maintain_remote_account" body="{\\"accounts\\": \\"<comma separated list of accounts, use * to target all existing accounts>\\"}"',
                "options": [
                    {
                        "accounts": "comma separated list of accounts, use * to target all existing accounts",
                        "show_token": "Optional, if set to true, will show the bearer token value in the response, defaults to false.",
                        "force_tokens_rotation": "Optional, if set to true, will force the rotation of the bearer tokens, defaults to false.",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        #
        # main
        #

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
        collection_name = "kv_trackme_remote_account_token_expiration"
        collection = service.kvstore[collection_name]

        # init return_response
        return_response = {}

        # init warnings counters
        warnings_count = 0
        warnings_list = []

        # init errors counters
        errors_count = 0
        errors_list = []

        # init actions_list
        actions_list = []

        def is_reachable(session, url, timeout):
            try:
                session.get(url, timeout=timeout, verify=False)
                return True, None
            except Exception as e:
                return False, str(e)

        def select_url(session, splunk_url, timeout=15, retry_config=None):
            splunk_urls = splunk_url.split(",")
            unreachable_errors = []

            reachable_urls = []
            for url in splunk_urls:
                if retry_config:
                    # Pass local is_reachable function to ensure consistency
                    reachable, error = is_reachable_with_retry(session, url, timeout, retry_config, is_reachable)
                else:
                    reachable, error = is_reachable(session, url, timeout)
                
                if reachable:
                    reachable_urls.append(url)
                else:
                    unreachable_errors.append((url, error))

            selected_url = random.choice(reachable_urls) if reachable_urls else False
            return selected_url, unreachable_errors

        def establish_remote_service(
            account,
            parsed_url,
            bearer_token,
            app_namespace,
            timeout=600,
        ):
            try:
                service = client.connect(
                    host=parsed_url.hostname,
                    splunkToken=str(bearer_token),
                    owner="nobody",
                    app=app_namespace,
                    port=parsed_url.port,
                    autologin=True,
                    timeout=timeout,
                )

                remote_apps = [app.label for app in service.apps]
                if remote_apps:
                    logger.info(
                        f'endpoint=maintain_remote_account, remote search connectivity check for account="{account}" with host="{parsed_url.hostname}" on port="{parsed_url.port}" was successful'
                    )
                    return service

            except Exception as e:
                error_msg = f'Remote search for account="{account}" has failed at connectivity check, host="{parsed_url.hostname}" on port="{parsed_url.port}" with exception="{str(e)}"'
                raise Exception(error_msg)

        def get_all_accounts():
            """
            Update the configuration of any existing remote account, to ensure that the configuration is up to date.

            :param reqinfo: dict containing Splunk session information (e.g., server URI, session key).
            :param task_name: Name of the task for logger.purposes.
            :param task_instance_id: ID of the task instance for logger.purposes.
            :param tenant_id: ID of the vtenant.
            :param default_account_values: manadatory dict of default values.
            """

            # endpoint target
            url = f"{request_info.server_rest_uri}/servicesNS/nobody/trackme/trackme_account"

            # current_remote_accounts_dict
            current_remote_accounts_dict = {}

            # current_remote_accounts_list
            current_remote_accounts_list = []

            # first, get the list of remote accounts
            try:
                response = requests.get(
                    url,
                    headers={
                        "Authorization": f"Splunk {request_info.system_authtoken}",
                        "Content-Type": "application/json",
                    },
                    verify=False,
                    params={
                        "output_mode": "json",
                        "count": -1,
                    },
                    timeout=600,
                )

                response.raise_for_status()
                response_json = response.json()

                # The list of remote accounts is stored as a list in entry
                remote_accounts = response_json.get("entry", [])

                # iterate through the remote accounts, adding them to the dict, name is the key, then we care about "content" which is a dict of our parameters
                # for this account

                for remote_account in remote_accounts:
                    remote_account_name = remote_account.get("name", None)
                    remote_account_content = remote_account.get("content", {})

                    # add to list
                    current_remote_accounts_list.append(remote_account_name)

                    if remote_account_name and remote_account_content:

                        # from remote_account_content, remove the following fields: bearer_token, disabled, eai:acl, eai:appName, eai:userName
                        remote_account_content.pop("bearer_token", None)
                        remote_account_content.pop("disabled", None)
                        remote_account_content.pop("eai:acl", None)
                        remote_account_content.pop("eai:appName", None)
                        remote_account_content.pop("eai:userName", None)
                        # add to the dict
                        current_remote_accounts_dict[remote_account_name] = (
                            remote_account_content
                        )

                return current_remote_accounts_list, current_remote_accounts_dict

            except Exception as e:
                logger.error(
                    f"endpoint=maintain_remote_account, error while fetching remote account list: {str(e)}"
                )
                return False

        def check_and_update_accounts(
            accounts,
            default_account_values,
            warnings_count=0,
            warnings_list=[],
            errors_count=0,
            errors_list=[],
            actions_list=[],
        ):

            # Second, iterate through our current_remote_accounts_dict, if any of the account is missing key/values from the default_account_values, we will update it
            # running a POST request to the remote account endpoint

            # in memory dict to store bearer tokens per account
            current_accounts_secrets = {}

            for remote_account_name in current_remote_accounts_dict:
                current_account_config = current_remote_accounts_dict[
                    remote_account_name
                ]

                if remote_account_name in accounts or accounts == "*":

                    # run a request against /services/trackme/v2/configuration/get_remote_account, body{'account': 'myaccount'} to retrieve the current bearer_token value (field token) and add to the content
                    try:
                        url = f"{request_info.server_rest_uri}/services/trackme/v2/configuration/get_remote_account"
                        data = {
                            "account": remote_account_name,
                        }
                        response_account_secret = requests.post(
                            url,
                            headers={
                                "Authorization": f"Splunk {request_info.system_authtoken}",
                                "Content-Type": "application/json",
                            },
                            verify=False,
                            data=json.dumps(data),
                            timeout=600,
                        )
                        response_account_secret.raise_for_status()
                        response_account_secret_json = response_account_secret.json()

                    except Exception as e:
                        error_msg = f"endpoint=maintain_remote_account, account={remote_account_name}, error while fetching remote account secret: {str(e)}"
                        logger.error(error_msg)
                        errors_count += 1
                        errors_list.append(error_msg)
                        account_must_be_updated = False

                    # retrieve and store the current bearer token
                    current_token = response_account_secret_json.get("token", None)

                    if not current_token:
                        error_msg = f"endpoint=maintain_remote_account, account={remote_account_name}, error while fetching remote account secret: token not found"
                        logger.error(error_msg)
                        errors_count += 1
                        errors_list.append(error_msg)
                        account_must_be_updated = False

                    else:
                        current_account_config["bearer_token"] = current_token
                        current_accounts_secrets[remote_account_name] = current_token

                    # check if the account is missing any key/values from the default_account_values
                    account_must_be_updated = False
                    for key in default_account_values:
                        if key not in current_account_config:
                            account_must_be_updated = True
                            # update the current_account_config with the default value
                            current_account_config[key] = default_account_values[key]

                    # if the account must be updated, we will run a POST request to the remote account endpoint
                    if not account_must_be_updated:
                        info_msg = f"endpoint=maintain_remote_account, successfully verified options for account={remote_account_name}, no update required"
                        logger.info(info_msg)
                        actions_list.append(info_msg)

                    else:
                        info_msg = f"endpoint=maintain_remote_account, update is required, account={remote_account_name}, must be updated due to outdated or missing options"
                        logger.info(info_msg)
                        actions_list.append(info_msg)

                        # endpoint target
                        url = f"{request_info.server_rest_uri}/servicesNS/nobody/trackme/trackme_account/{remote_account_name}?output_mode=json"

                        try:
                            response = requests.post(
                                url,
                                headers={
                                    "Authorization": f"Splunk {request_info.system_authtoken}",
                                    "Content-Type": "application/json",
                                },
                                verify=False,
                                params=current_account_config,
                                timeout=600,
                            )
                            response.raise_for_status()
                            info_msg = f"endpoint=maintain_remote_account, successfully updated remote account configuration for missing default values, account={remote_account_name}, status={response.status_code}"
                            logger.info(info_msg)
                            actions_list.append(info_msg)

                        except Exception as e:
                            error_msg = f"endpoint=maintain_remote_account, failed to update remote account configuration for missing default values, account={remote_account_name}, exception={str(e)}"
                            logger.error(error_msg)
                            errors_count += 1
                            errors_list.append(error_msg)

            # return
            return (
                current_remote_accounts_dict,
                current_accounts_secrets,
                warnings_count,
                warnings_list,
                errors_count,
                errors_list,
                actions_list,
            )

        def check_and_rotate_tokens(
            accounts,
            current_remote_accounts_list,
            current_remote_accounts_dict,
            current_accounts_secrets,
            force=False,
            warnings_count=0,
            warnings_list=[],
            errors_count=0,
            errors_list=[],
            actions_list=[],
        ):

            accounts_to_be_processed = []
            if accounts == "*":
                for account in current_remote_accounts_list:
                    accounts_to_be_processed.append(account)
            else:
                accounts_to_be_processed = accounts

            for account in accounts_to_be_processed:

                # get the current remote account dict
                current_remote_account_dict = current_remote_accounts_dict.get(account)

                # Check if a metadata record exists for the account
                try:
                    kvrecord = collection.data.query(
                        query=json.dumps({"account": account})
                    )[0]
                    key = kvrecord.get("_key")
                except Exception as e:
                    key = None

                # if no metadata record exists, create one
                if not key:

                    new_record = {
                        "account": account,
                        "mtime": time.time(),
                        "last_message": "Bearer token rotation tracking initiated",
                        "last_result": "success",
                    }

                    # insert a new record
                    try:
                        collection.data.insert(json.dumps(new_record))
                        info_msg = f'endpoint=maintain_remote_account, created new metadata record for account="{account}"'
                        logger.info(info_msg)
                        actions_list.append(info_msg)

                    except Exception as e:
                        error_msg = f'endpoint=maintain_remote_account, failed to insert the maintenance record with exception="{str(e)}"'
                        logger.error(error_msg)
                        errors_count += 1
                        errors_list.append(error_msg)

                # if a metadata record exists, check if the token needs to be renewed
                else:

                    token_must_be_renewed = False

                    # first, get and check renewal preferences
                    token_rotation_enablement = bool(
                        current_remote_account_dict.get("token_rotation_enablement", 1)
                    )
                    token_rotation_frequency = int(
                        current_remote_account_dict.get("token_rotation_frequency", 7)
                    )  # in days

                    # get the last token rotation timestamp
                    last_rotation_timestamp = kvrecord.get("mtime")

                    # calculate the time spent since the last rotation (seconds)
                    time_since_last_rotation = time.time() - last_rotation_timestamp

                    # check if the token must be renewed
                    if (
                        time_since_last_rotation > token_rotation_frequency * 86400
                        and token_rotation_enablement
                    ):
                        token_must_be_renewed = True

                    if force:
                        token_must_be_renewed = True

                    else:
                        last_rotation_timestamp_human = datetime.datetime.fromtimestamp(
                            last_rotation_timestamp
                        ).strftime("%Y-%m-%d %H:%M:%S")

                        if not token_rotation_enablement:
                            info_msg = f'endpoint=maintain_remote_account, account="{account}", token rotation is disabled, last_rotation_timestamp="{last_rotation_timestamp_human}", token_rotation_enablement="{token_rotation_enablement}"'
                            logger.info(info_msg)
                            actions_list.append(info_msg)

                        else:
                            if not token_must_be_renewed:
                                info_msg = f'endpoint=maintain_remote_account, account="{account}", token is not due for renewal, last_rotation_timestamp="{last_rotation_timestamp_human}", token_rotation_enablement="{token_rotation_enablement}", token_rotation_frequency="{token_rotation_frequency}"'
                                logger.info(info_msg)
                                actions_list.append(info_msg)
                            else:
                                info_msg = f'endpoint=maintain_remote_account, account="{account}", token must be renewed, last_rotation_timestamp="{last_rotation_timestamp_human}", token_rotation_enablement="{token_rotation_enablement}", token_rotation_frequency="{token_rotation_frequency}"'
                                logger.info(info_msg)
                                actions_list.append(info_msg)

                    # if the token must be renewed, proceed with the renewal
                    if token_must_be_renewed:

                        # Create a session within the generate function
                        session = requests.Session()

                        # splunk_url, app_namespace, timeout_connect_check
                        splunk_url = current_remote_account_dict.get("splunk_url")
                        timeout_connect_check = int(
                            current_remote_account_dict.get("timeout_connect_check", 15)
                        )
                        app_namespace = current_remote_account_dict.get("app_namespace")

                        # retry configuration - use defaults if not configured
                        retry_config = {
                            "retry_enabled": current_remote_account_dict.get("retry_enabled", "1"),
                            "retry_max_total_time": current_remote_account_dict.get("retry_max_total_time", "30"),
                            "retry_initial_delay": current_remote_account_dict.get("retry_initial_delay", "2"),
                            "retry_backoff_multiplier": current_remote_account_dict.get("retry_backoff_multiplier", "2.0"),
                            "retry_max_attempts": current_remote_account_dict.get("retry_max_attempts", "10"),
                        }

                        # bearer_token
                        bearer_token = current_accounts_secrets[account]

                        # Call target selector and pass the session as an argument
                        selected_url, errors = select_url(
                            session, splunk_url, timeout_connect_check, retry_config=retry_config
                        )

                        # end of get configuration

                        # If none of the endpoints could be reached
                        if not selected_url:
                            error_msg = f"endpoint=maintain_remote_account, none of the endpoints provided in the account URLs could be reached successfully, verify your network connectivity! (timeout_connect_check={timeout_connect_check})"
                            error_msg += f"Errors: {' '.join([f'{url}: {error}' for url, error in errors])}"
                            logger.error(error_msg)
                            errors_count += 1
                            errors_list.append(error_msg)

                        else:
                            # Enforce https and remove trailing slash in the URL, if any
                            selected_url = f"https://{selected_url.replace('https://', '').rstrip('/')}"

                            # Use urlparse to extract relevant info from target
                            parsed_url = urllib.parse.urlparse(selected_url)

                            # Establish the remote service
                            info_msg = f'endpoint=maintain_remote_account, establishing connection to host="{parsed_url.hostname}" on port="{parsed_url.port}", selected_url="{selected_url}"'
                            logger.info(info_msg)
                            actions_list.append(info_msg)

                            try:
                                remoteservice = establish_remote_service(
                                    account,
                                    parsed_url,
                                    bearer_token,
                                    app_namespace,
                                    timeout=timeout_connect_check,
                                )

                            except Exception as e:
                                remoteservice = None
                                errors_count += 1
                                errors_list.append(str(e))

                            # continue only if remoteservice is established
                            if remoteservice:

                                info_msg = f"endpoint=maintain_remote_account, successfully established remote service connection for account={account}"
                                logger.info(info_msg)
                                actions_list.append(info_msg)

                                #
                                # user context
                                #

                                user_context_username = None
                                user_context_capabilities = []

                                # Run a GET call against /services/authentication/current-context to discover our user context
                                try:
                                    url = f"{selected_url}/services/authentication/current-context?output_mode=json"
                                    response = requests.get(
                                        url,
                                        headers={
                                            "Authorization": f"Bearer {bearer_token}",
                                            "Content-Type": "application/json",
                                        },
                                        verify=False,
                                        timeout=600,
                                    )
                                    response.raise_for_status()
                                    response_json = response.json()
                                    user_context_entry = response_json.get("entry", {})[
                                        0
                                    ]
                                    user_context_content = user_context_entry.get(
                                        "content", {}
                                    )
                                    user_context_username = user_context_content.get(
                                        "username", None
                                    )
                                    user_context_capabilities = (
                                        user_context_content.get("capabilities", [])
                                    )
                                    info_msg = f'endpoint=maintain_remote_account, successfully retrieved current context for account="{account}", username="{user_context_username}"'
                                    logger.info(info_msg)
                                    actions_list.append(info_msg)

                                except Exception as e:
                                    error_msg = f"endpoint=maintain_remote_account, failed to retrieve current context for account={account}, exception={str(e)}"
                                    logger.error(error_msg)
                                    errors_count += 1
                                    errors_list.append(error_msg)

                                #
                                # Renew token
                                #

                                bearer_token_can_be_renewed = False
                                new_bearer_token_id = None
                                new_bearer_token = None
                                new_bearer_token_generated = False

                                # if user_context_username is not null, and we have either edit_tokens_all or edit_tokens_own, the token can be renewed
                                if user_context_username:
                                    if (
                                        "edit_tokens_all" in user_context_capabilities
                                        or "edit_tokens_own"
                                        in user_context_capabilities
                                    ):
                                        bearer_token_can_be_renewed = True

                                if not bearer_token_can_be_renewed:
                                    warnings_count += 1
                                    warning_msg = f'endpoint=maintain_remote_account, account="{account}", token cannot be renewed, the following capabilities are required for automated token renewal: edit_tokens_all or edit_tokens_own, user_context_username="{user_context_username}", user_context_capabilities="{user_context_capabilities}"'
                                    logger.warning(warning_msg)
                                    warnings_list.append(warning_msg)

                                else:
                                    # Generate a new token, run a POST request against /services/authorization/tokens, body audience=TrackMe

                                    try:
                                        url = f"{selected_url}/services/authorization/tokens?output_mode=json"
                                        data = {
                                            "name": user_context_username,
                                            "audience": f"TrackMe bearer token auto-renewal operated at {time.strftime('%Y-%m-%d %H:%M:%S')}, account={account}",
                                        }
                                        response = requests.post(
                                            url,
                                            headers={
                                                "Authorization": f"Bearer {bearer_token}",
                                                "Content-Type": "application/json",
                                            },
                                            data=data,
                                            verify=False,
                                            timeout=600,
                                        )
                                        response.raise_for_status()
                                        response_json = response.json()
                                        bearer_token_context_entry = response_json.get(
                                            "entry", {}
                                        )[0]
                                        bearer_token_context_content = (
                                            bearer_token_context_entry.get(
                                                "content", {}
                                            )
                                        )
                                        new_bearer_token_id = (
                                            bearer_token_context_content.get("id", None)
                                        )
                                        new_bearer_token = (
                                            bearer_token_context_content.get(
                                                "token", None
                                            )
                                        )

                                        if new_bearer_token_id and new_bearer_token:
                                            info_msg = f'endpoint=maintain_remote_account, successfully generated a token for account="{account}", new_bearer_token_id="{new_bearer_token_id}"'
                                            logger.info(info_msg)
                                            actions_list.append(info_msg)
                                            new_bearer_token_generated = True

                                    except Exception as e:
                                        error_msg = f"endpoint=maintain_remote_account, failed to generate a new token for account={account}, exception={str(e)}"
                                        logger.error(error_msg)
                                        errors_count += 1
                                        errors_list.append(error_msg)

                                #
                                # Test connection with new bearer token before updating account configuration
                                #

                                if new_bearer_token_generated:
                                    # Test the new bearer token by establishing a new remote service connection
                                    info_msg = f'endpoint=maintain_remote_account, testing new bearer token connection for account="{account}" with host="{parsed_url.hostname}" on port="{parsed_url.port}"'
                                    logger.info(info_msg)
                                    actions_list.append(info_msg)

                                    try:
                                        # Attempt to establish a new remote service using the new bearer token
                                        new_remoteservice = establish_remote_service(
                                            account,
                                            parsed_url,
                                            new_bearer_token,
                                            app_namespace,
                                            timeout=timeout_connect_check,
                                        )

                                        if new_remoteservice:
                                            info_msg = f"endpoint=maintain_remote_account, successfully tested new bearer token connection for account={account}"
                                            logger.info(info_msg)
                                            actions_list.append(info_msg)
                                        else:
                                            raise Exception("Failed to establish remote service with new bearer token")

                                    except Exception as e:
                                        error_msg = f"endpoint=maintain_remote_account, new bearer token connection test failed for account={account}, exception={str(e)}"
                                        logger.error(error_msg)
                                        errors_count += 1
                                        errors_list.append(error_msg)
                                        # Stop here - don't update the account if the new token doesn't work
                                        continue

                                #
                                # Update bearer token in the account configuration
                                #

                                remote_account_bearer_token_was_updated = False
                                previous_bearer_token_id = None

                                if new_bearer_token_generated:

                                    #
                                    # subtask: update the remote account with the new bearer token
                                    #

                                    # update the current_remote_accounts_dict with the new bearer token
                                    current_remote_account_dict["bearer_token"] = (
                                        new_bearer_token
                                    )

                                    # endpoint target
                                    url = f"{request_info.server_rest_uri}/servicesNS/nobody/trackme/trackme_account/{account}?output_mode=json"

                                    try:
                                        response = requests.post(
                                            url,
                                            headers={
                                                "Authorization": f"Splunk {request_info.system_authtoken}",
                                                "Content-Type": "application/json",
                                            },
                                            verify=False,
                                            params=current_remote_account_dict,
                                            timeout=600,
                                        )
                                        response.raise_for_status()
                                        remote_account_bearer_token_was_updated = True
                                        info_msg = f"endpoint=maintain_remote_account, successfully updated remote account configuration in TrackMe with new bearer_token id={new_bearer_token_id}, account={account}, status={response.status_code}"
                                        logger.info(info_msg)
                                        actions_list.append(info_msg)

                                    except Exception as e:

                                        error_msg = f"endpoint=maintain_remote_account, failed to update remote account configuration in TrackMe with new bearer_token id={new_bearer_token_id}, account={account}, exception={str(e)}"
                                        logger.error(error_msg)
                                        errors_count += 1
                                        errors_list.append(error_msg)

                                    #
                                    # subtask: Update the metadata KVstore collection
                                    #

                                    # get records
                                    try:
                                        kvrecord = collection.data.query(
                                            query=json.dumps({"account": account})
                                        )[0]
                                        key = kvrecord.get("_key")
                                        previous_bearer_token_id = kvrecord.get(
                                            "remote_bearer_token_id"
                                        )
                                    except Exception as e:
                                        key = None

                                    # new record
                                    if not key:
                                        # Set the response record
                                        new_record = {
                                            "account": account,
                                            "mtime": time.time(),
                                            "last_message": f"Bearer token renewal operated at {time.strftime('%Y-%m-%d %H:%M:%S')}",
                                            "remote_bearer_token_id": new_bearer_token_id,
                                        }

                                        # insert a new record
                                        try:
                                            collection.data.insert(
                                                json.dumps(new_record)
                                            )
                                            return {
                                                "payload": new_record,
                                                "status": 200,
                                            }

                                        except Exception as e:
                                            error_msg = f'endpoint=maintain_remote_account, failed to insert the metadata kvstore record with exception="{str(e)}"'
                                            logger.error(error_msg)
                                            errors_count += 1
                                            errors_list.append(error_msg)

                                    # existing record
                                    else:

                                        # update record
                                        kvrecord["mtime"] = time.time()
                                        kvrecord["last_message"] = (
                                            f"Bearer token renewal operated at {time.strftime('%Y-%m-%d %H:%M:%S')}"
                                        )
                                        kvrecord["remote_bearer_token_id"] = (
                                            new_bearer_token_id
                                        )

                                        try:
                                            collection.data.update(
                                                str(key), json.dumps(kvrecord)
                                            )

                                        except Exception as e:
                                            error_msg = f'endpoint=maintain_remote_account, failed to update the metadata kvstore record with exception="{str(e)}"'
                                            logger.error(error_msg)
                                            errors_count += 1
                                            errors_list.append(error_msg)

                                    #
                                    # subtask: Revoke the previous bearer token
                                    #

                                    if (
                                        remote_account_bearer_token_was_updated
                                        and previous_bearer_token_id
                                    ):

                                        try:
                                            url = f"{selected_url}/services/authorization/tokens/{user_context_username}?output_mode=json"
                                            data = {
                                                "id": previous_bearer_token_id,
                                            }
                                            response = requests.delete(
                                                url,
                                                headers={
                                                    "Authorization": f"Bearer {bearer_token}",
                                                    "Content-Type": "application/json",
                                                },
                                                data=data,
                                                verify=False,
                                                timeout=600,
                                            )
                                            response.raise_for_status()
                                            info_msg = f'endpoint=maintain_remote_account, successfully revoked previous bearer token for account="{account}", previous_bearer_token_id="{previous_bearer_token_id}"'
                                            logger.info(info_msg)
                                            actions_list.append(info_msg)

                                        except Exception as e:
                                            error_msg = f'endpoint=maintain_remote_account, failed to revoke previous bearer token for account="{account}", previous_bearer_token_id="{previous_bearer_token_id}", exception="{str(e)}"'
                                            logger.error(error_msg)
                                            errors_count += 1
                                            errors_list.append(error_msg)

                                    #
                                    # subtask: List all tokens for the user
                                    #

                                    try:
                                        url = f"{selected_url}/services/authorization/tokens?output_mode=json"
                                        response = requests.get(
                                            url,
                                            headers={
                                                "Authorization": f"Bearer {new_bearer_token}",
                                                "Content-Type": "application/json",
                                            },
                                            data={
                                                "username": user_context_username,
                                                "status": "enabled",
                                            },
                                            verify=False,
                                            timeout=600,
                                        )
                                        response.raise_for_status()
                                        response_json = response.json()
                                        existing_tokens = response_json.get("entry", [])
                                        existing_tokens_response_list = []

                                        for existing_token_entry in existing_tokens:
                                            existing_token_name = (
                                                existing_token_entry.get("name", None)
                                            )
                                            existing_token_content = (
                                                existing_token_entry.get("content", {})
                                            )
                                            existing_token_claims = (
                                                existing_token_content.get("claims", {})
                                            )
                                            existing_token_lastused = (
                                                existing_token_content.get(
                                                    "lastUsed", None
                                                )
                                            )
                                            existing_token_status = (
                                                existing_token_content.get(
                                                    "status", None
                                                )
                                            )
                                            existing_tokens_response_list.append(
                                                {
                                                    existing_token_name: {
                                                        "claims": existing_token_claims,
                                                        "lastUsed": existing_token_lastused,
                                                        "status": existing_token_status,
                                                    }
                                                }
                                            )

                                        info_msg = f'endpoint=maintain_remote_account, successfully retrieved all tokens for remote_user="{user_context_username}", tokens="{json.dumps(existing_tokens_response_list, indent=2)}"'
                                        logger.info(info_msg)
                                        actions_list.append(info_msg)

                                    except Exception as e:
                                        error_msg = f'endpoint=maintain_remote_account, failed to retrieve all tokens for remote_user="{user_context_username}", exception="{str(e)}"'
                                        logger.error(error_msg)
                                        errors_count += 1
                                        errors_list.append(error_msg)

            # return
            return (
                warnings_count,
                warnings_list,
                errors_count,
                errors_list,
                actions_list,
            )

        #
        # Process main
        #

        # get all remote accounts
        try:
            current_remote_accounts_list, current_remote_accounts_dict = (
                get_all_accounts()
            )
        except Exception as e:
            logger.error(
                f"endpoint=maintain_remote_account, error while fetching remote accounts: {str(e)}"
            )
            return {"payload": "failed", "status": 500}

        # check accounts
        if accounts != "*":
            for account in accounts:
                if account not in current_remote_accounts_list:

                    # set response
                    return_response["result"] = "failed"
                    return_response["message"] = (
                        f"endpoint=maintain_remote_account, remote account {account} not found"
                    )
                    return_response["remote_account"] = None

                    # log
                    logger.error(return_response.get("message"))

                    # return return_response
                    return {"payload": return_response, "status": 500}

        # check and update accounts configuration, as needed
        try:
            (
                current_remote_accounts_dict,
                current_accounts_secrets,
                warnings_count,
                warnings_list,
                errors_count,
                errors_list,
                actions_list,
            ) = check_and_update_accounts(accounts, remote_account_default)

        except Exception as e:
            logger.error(
                f"endpoint=maintain_remote_account, error while checking and updating remote accounts: {str(e)}"
            )
            return {"payload": "failed", "status": 500}

        # check and renew tokens, as needed
        try:
            warnings_count, warnings_list, errors_count, errors_list, actions_list = (
                check_and_rotate_tokens(
                    accounts,
                    current_remote_accounts_list,
                    current_remote_accounts_dict,
                    current_accounts_secrets,
                    force=force_tokens_rotation,
                )
            )

        except Exception as e:
            logger.error(
                f"endpoint=maintain_remote_account, error while checking and renewing tokens: {str(e)}"
            )
            return {"payload": "failed", "status": 500}

        # handle show_token, if not set to true, anonymize the token for each account in current_remote_accounts_dict
        if not show_token:
            for account in current_remote_accounts_dict:
                current_remote_accounts_dict[account]["bearer_token"] = "********"

        # return response
        if errors_count > 0:
            return_response["result"] = "failed"
            return_response["message"] = (
                f"endpoint=maintain_remote_account, failed to update remote accounts, error_counts={errors_count}"
            )
            return_response["remote_accounts"] = current_remote_accounts_dict
            return_response["errors"] = errors_list
            return_response["actions"] = actions_list

            logger.error(return_response.get("message"))
            return {"payload": return_response, "status": 500}

        else:

            if warnings_count > 0:
                return_response["result"] = "warning"
            else:
                return_response["result"] = "success"

            # Audit success/warning outcomes (only emit when something actually
            # happened — actions_list is non-empty when accounts were updated
            # or tokens rotated; otherwise the call was a no-op probe).
            if actions_list:
                try:
                    accounts_audited = (
                        "all"
                        if accounts == "*"
                        else ",".join(accounts) if isinstance(accounts, list) else str(accounts)
                    )
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        "all",
                        request_info.user,
                        return_response["result"],
                        "maintain remote accounts",
                        accounts_audited,
                        "remote_accounts",
                        json.dumps(
                            {
                                "actions": actions_list,
                                "warnings": warnings_list,
                                "force_tokens_rotation": force_tokens_rotation,
                            },
                            default=str,
                        ),
                        f"Remote accounts maintenance completed by user=\"{request_info.user}\" "
                        f"(actions={len(actions_list)}, warnings={warnings_count})",
                        str(update_comment),
                    )
                except Exception as audit_e:
                    logger.warning(
                        f'function=post_maintain_remote_account, step="audit", '
                        f'exception="{str(audit_e)}"'
                    )

            if accounts == "*":
                return_response["accounts"] = current_remote_accounts_dict
                return_response["actions"] = actions_list
                if warnings_count > 0:
                    return_response["warnings"] = warnings_list
                return {"payload": return_response, "status": 200}

            else:
                return_response["accounts"] = {}
                for account in accounts:
                    return_response["accounts"][account] = (
                        current_remote_accounts_dict.get(account)
                    )
                return_response["actions"] = actions_list
                if warnings_count > 0:
                    return_response["warnings"] = warnings_list
                return {"payload": return_response, "status": 200}

    # Update splunk_url for a remote account
    def post_update_remote_account_url(self, request_info, **kwargs):
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                account = resp_dict.get("account")
                splunk_url_value = resp_dict.get("splunk_url_value")
        else:
            # body is required in this endpoint
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint updates the splunk_url value for a remote account. It requires a POST call with the following options:",
                "resource_desc": "Update the splunk_url value for a remote account",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/update_remote_account_url" body="{\\"account\\": \\"myaccount\\", \\"splunk_url_value\\": \\"https://splunk1:8089,https://splunk2:8089\\"}"',
                "options": [
                    {
                        "account": "The account configuration identifier",
                        "splunk_url_value": "Required, comma separated list of URL values to be used for the account.",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Check required parameters
        if not account:
            return {
                "payload": "account parameter is required",
                "status": 500,
            }

        if not splunk_url_value:
            return {
                "payload": "splunk_url_value parameter is required",
                "status": 500,
            }

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Retrieve the account configuration with bearer token
        try:
            url = f"{request_info.server_rest_uri}/services/trackme/v2/configuration/get_remote_account"
            data = {
                "account": account,
            }
            response_account = requests.post(
                url,
                headers={
                    "Authorization": f"Splunk {request_info.system_authtoken}",
                    "Content-Type": "application/json",
                },
                verify=False,
                data=json.dumps(data),
                timeout=600,
            )
            response_account.raise_for_status()  # an exception is raised if the account is not found
            account_config = response_account.json()

        except Exception as e:
            error_msg = f"endpoint=update_remote_account_url, account={account}, error while fetching account info: {str(e)}"
            logger.error(error_msg)
            return {
                "payload": {"result": "failed", "message": error_msg},
                "status": 500,
            }

        #
        # Test connectivity with the new splunk_url
        #

        try:
            url = f"{request_info.server_rest_uri}/services/trackme/v2/configuration/test_remote_connectivity"
            data = {
                "target_endpoints": splunk_url_value,
                "bearer_token": account_config.get("token"),
                "app_namespace": account_config.get("app_namespace", "search"),
                "timeout_connect_check": int(
                    account_config.get("timeout_connect_check", 15)
                ),
                "timeout_search_check": int(
                    account_config.get("timeout_search_check", 300)
                ),
            }
            
            # Add retry configuration if present
            if "retry_enabled" in account_config:
                data["retry_enabled"] = account_config.get("retry_enabled")
            if "retry_max_total_time" in account_config:
                data["retry_max_total_time"] = account_config.get("retry_max_total_time")
            if "retry_initial_delay" in account_config:
                data["retry_initial_delay"] = account_config.get("retry_initial_delay")
            if "retry_backoff_multiplier" in account_config:
                data["retry_backoff_multiplier"] = account_config.get("retry_backoff_multiplier")
            if "retry_max_attempts" in account_config:
                data["retry_max_attempts"] = account_config.get("retry_max_attempts")
            response_test = requests.post(
                url,
                headers={
                    "Authorization": f"Splunk {request_info.system_authtoken}",
                    "Content-Type": "application/json",
                },
                verify=False,
                data=json.dumps(data),
                timeout=600,
            )
            response_test.raise_for_status()
            test_result = response_test.json()

            logger.info(
                f"endpoint=update_remote_account_url, account={account}, new_splunk_url={splunk_url_value}, connection was successfully established, test_result={test_result}"
            )

        except Exception as e:
            error_msg = f"endpoint=update_remote_account_url, connectivity test failed for account={account}, new_splunk_url={splunk_url_value}, exception={str(e)}"
            logger.error(error_msg)
            return {
                "payload": {"result": "failed", "message": error_msg},
                "status": 500,
            }

        #
        # Update the account configuration
        #

        # update the account configuration
        account_config["splunk_url"] = splunk_url_value

        # remove account key/pair from account_config
        account_config.pop("account", None)

        # remove message and status from account_config
        account_config.pop("message", None)
        account_config.pop("status", None)

        # turn rbac_roles from list to comma separated string
        account_config["rbac_roles"] = ",".join(account_config["rbac_roles"])

        # rename token as the expected bearer_token
        account_config["bearer_token"] = account_config["token"]
        account_config.pop("token", None)

        # endpoint target
        url = f"{request_info.server_rest_uri}/servicesNS/nobody/trackme/trackme_account/{account}?output_mode=json"

        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Splunk {request_info.system_authtoken}",
                    "Content-Type": "application/json",
                },
                verify=False,
                params=account_config,
                timeout=600,
            )
            response.raise_for_status()
            info_msg = f"endpoint=update_remote_account_url, successfully updated remote account configuration in TrackMe, account={account}, status={response.status_code}"
            logger.info(info_msg)
            # remote the bearer token from the account configuration
            account_config.pop("bearer_token", None)
            return {
                "payload": {
                    "result": "success",
                    "message": info_msg,
                    "account_config": account_config,
                },
                "status": 200,
            }

        except Exception as e:
            error_msg = f"endpoint=update_remote_account_url, failed to update remote account configuration in TrackMe, account={account}, exception={str(e)}"
            logger.error(error_msg)
            return {
                "payload": {
                    "result": "failed",
                    "message": error_msg,
                    "account_config": account_config,
                },
                "status": 500,
            }

    # Update specific parameters of a Virtual Tenant account with privileges escalation
    def post_update_vtenant_account(self, request_info, **kwargs):
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
                
                # parameters_to_update is required - a dictionary with the parameters to be updated
                try:
                    parameters_to_update = resp_dict["parameters_to_update"]
                    # if not a dictionary, attempt to load it
                    if not isinstance(parameters_to_update, dict):
                        try:
                            parameters_to_update = json.loads(parameters_to_update)
                        except Exception as e:
                            error_msg = f"failed to load parameters_to_update, exception={str(e)}"
                            logger.error(error_msg)
                            return {"payload": error_msg, "status": 500}
                except Exception as e:
                    error_msg = "parameters_to_update is required and must be a dictionary"
                    logger.error(error_msg)
                    return {"payload": error_msg, "status": 500}

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows updating specific parameters of a Virtual Tenant account with privileges escalation, it requires a POST with the following options:",
                "resource_desc": "Update Virtual Tenant account parameters",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/admin/update_vtenant_account" body="{\'tenant_id\': \'<tenant_id>\', \'parameters_to_update\': {\'ui_default_timerange\': \'48h\', \'ui_min_object_width\': 400}}"',
                "options": [
                    {
                        "tenant_id": "The Virtual Tenant ID",
                        "parameters_to_update": "Required, a dictionary with the parameters to be updated (only valid parameters from the default configuration are accepted)",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        #
        # main
        #

        # Validate that all requested parameters are valid (exist in vtenant_account_default)
        invalid_parameters = []
        for param in parameters_to_update.keys():
            if param not in vtenant_account_default:
                invalid_parameters.append(param)
        
        if invalid_parameters:
            error_msg = f"Invalid parameters requested: {invalid_parameters}. Only parameters from the default configuration are allowed."
            logger.error(error_msg)
            return {"payload": error_msg, "status": 400}

        url = f"{request_info.server_rest_uri}/servicesNS/nobody/trackme/trackme_vtenants/{tenant_id}"
        vtenant_data = {}

        # vtenant_account_found boolean
        vtenant_account_found = False

        try:
            # Get current vtenant account configuration
            response = requests.get(
                url,
                headers={"Authorization": f"Splunk {request_info.system_authtoken}"},
                verify=False,
                params={"output_mode": "json"},
                timeout=600,
            )
            if response.status_code in (200, 201, 204):

                logger.info(f"successfully retrieved vtenant configuration")
                vtenant_data_json = response.json()
                vtenant_data_current = vtenant_data_json["entry"][0]["content"]

                # Set vtenant_account_found to True
                vtenant_account_found = True

                # Start with the current configuration
                vtenant_data = dict(vtenant_data_current)

                # Update only the requested parameters
                vtenant_data.update(parameters_to_update)

                logger.info(
                    f'vtenant_data updated="{json.dumps(vtenant_data, indent=2)}", parameters_to_update="{json.dumps(parameters_to_update, indent=2)}"'
                )

            else:
                error_msg = f"failed to retrieve vtenant configuration, status_code={response.status_code}"
                logger.error(error_msg)

        except Exception as e:
            error_msg = f"failed to retrieve vtenant configuration, exception={str(e)}"
            logger.error(error_msg)

        # init return_response
        return_response = {}

        #
        # if Virtual Tenant account is not found
        #

        if not vtenant_account_found:
            # set response
            return_response["result"] = "failed"
            return_response["message"] = f"vtenant account '{tenant_id}' not found"
            return_response["vtenant_account"] = None

            # log
            logger.error(return_response.get("message"))

            # return return_response
            return {"payload": return_response, "status": 404}

        #
        # main: Virtual Tenant account is found, proceed with updating
        #

        # in vtenant_data, remote the following fields: disabled, eai:acl, eai:appName, eai:userName
        vtenant_data.pop("disabled", None)
        vtenant_data.pop("eai:acl", None)
        vtenant_data.pop("eai:appName", None)
        vtenant_data.pop("eai:userName", None)

        try:
            logger.info(
                f'attempting to update vtenant configuration, vtenant_data="{json.dumps(vtenant_data, indent=2)}"'
            )
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Splunk {request_info.system_authtoken}",
                    "Content-Type": "application/json",
                },
                data=vtenant_data,
                verify=False,
                timeout=600,
            )
            if response.status_code in (200, 201, 204):

                # set response
                return_response["result"] = "success"
                return_response["message"] = (
                    f"vtenant configuration updated successfully, status_code={response.status_code}"
                )
                return_response["vtenant_account"] = vtenant_data
                return_response["updated_parameters"] = parameters_to_update

                # log
                logger.info(return_response.get("message"))

                # return response
                return {"payload": return_response, "status": 200}

            else:

                # set return_response
                return_response["result"] = "failed"
                return_response["message"] = (
                    f"failed to update vtenant configuration, status_code={response.status_code}, response={response.text}"
                )
                return_response["vtenant_account"] = None

                # log
                logger.error(return_response.get("message"))

                # return return_response
                return {"payload": return_response, "status": 500}

        except Exception as e:

            # set response
            return_response["result"] = "failed"
            return_response["message"] = (
                f"failed to update vtenant configuration, exception={str(e)}"
            )
            return_response["vtenant_account"] = None

            # log
            logger.error(return_response.get("message"))

            # return response
            return {"payload": return_response, "status": 500}
