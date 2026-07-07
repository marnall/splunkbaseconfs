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
import random
import re
import sys
from collections import OrderedDict

# Third-party libraries
import requests
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
    "trackme.rest.alerting_admin", "trackme_rest_api_alerting_admin.log"
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    trackme_audit_event,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_reqinfo,
    trackme_send_to_tcm,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerAlertingWriteOps_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerAlertingWriteOps_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_alerting_admin(self, request_info, **kwargs):
        response = {
            "resource_group_name": "alerting/admin",
            "resource_group_desc": "These endpoints handle alerting (admin operations)",
        }

        return {"payload": response, "status": 200}

    # Create a new alert for any or our components
    def post_create_alert(self, request_info, **kwargs):
        # alert options
        tenant_id = None
        alert_name = None
        alert_search = None
        alert_properties = None

        # describe
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
                alert_name = resp_dict["alert_name"]
                alert_search = resp_dict["alert_search"]
                alert_properties = resp_dict["alert_properties"]

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint creates a new tracking alert for the component, it requires a POST call with the following information:",
                "resource_desc": "Create a new TrackMe alert (designed to be used programmatically, spl example not available due to the complexity of the content)",
                "resource_spl_example": "Not available",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "alert_name": "The alert name",
                        "alert_search": "The alert search SPL statement",
                        "alert_properties": "The JSON alert properties",
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

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % request_info.system_authtoken,
            "Content-Type": "application/json",
        }

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
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

        # TrackMe sharing level
        trackme_default_sharing = trackme_conf["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # alert check
        #

        # in alert_properties, check the value for actions (comma separated list of actions)
        # if in actions, we find trackme_stateful_alert, verify that the email_account and email_recipients are set and to non empty values, if not return an error
        trackme_stateful_alert_base_keys = [
            "action.trackme_stateful_alert.param.delivery_target",
            "action.trackme_stateful_alert.param.orange_as_alerting_state",
            "action.trackme_stateful_alert.param.drilldown_root_uri",
        ]

        trackme_stateful_alert_email_keys = [
            "action.trackme_stateful_alert.param.email_account",
            "action.trackme_stateful_alert.param.email_recipients",
            "action.trackme_stateful_alert.param.generate_charts",
            "action.trackme_stateful_alert.param.theme_charts",
            "action.trackme_stateful_alert.param.timerange_charts",
            "action.trackme_stateful_alert.param.environment_name",
            "action.trackme_stateful_alert.param.email_send_update_if_ack_active",
            "action.trackme_stateful_alert.param.priority_levels_emails",
        ]

        trackme_stateful_alert_command_keys = [
            "action.trackme_stateful_alert.param.commands_mode",
            "action.trackme_stateful_alert.param.commands_opened",
            "action.trackme_stateful_alert.param.commands_updated",
            "action.trackme_stateful_alert.param.commands_closed",
            "action.trackme_stateful_alert.param.priority_levels_commands",
        ]

        if "trackme_stateful_alert" in alert_properties.get("actions", ""):
            missing_fields = {}

            # Check base required fields
            for key in trackme_stateful_alert_base_keys:
                value = alert_properties.get(key)
                if value in ("", None):
                    reason = "missing" if value is None else "empty string"
                    missing_fields[key] = reason

            # Conditional check for email parameters
            delivery_target = alert_properties.get(
                "action.trackme_stateful_alert.param.delivery_target"
            )
            if delivery_target in (
                "emails_and_ingest",
                "emails_only",
                "emails_commands_and_ingest",
                "commands_and_emails",
            ):
                for key in trackme_stateful_alert_email_keys:
                    value = alert_properties.get(key)
                    if value in ("", None):
                        reason = "missing" if value is None else "empty string"
                        missing_fields[key] = reason
                    elif (
                        key == "action.trackme_stateful_alert.param.theme_charts"
                        and value not in ("dark", "light")
                    ):
                        missing_fields[key] = (
                            f"invalid value '{value}', must be 'dark' or 'light'"
                        )
                    elif key == "action.trackme_stateful_alert.param.timerange_charts":
                        # Pattern: <digit><time delimiter> where delimiter is h, d, m, s, etc.
                        timerange_pattern = r"^\d+[hdmsy]$"
                        if not re.match(timerange_pattern, value):
                            missing_fields[key] = (
                                f"invalid format '{value}', must be <digit><time delimiter> (e.g., 24h, 7d, 90d, 30d, 48h, 1m)"
                            )

            if delivery_target in (
                "emails_commands_and_ingest",
                "commands_and_ingest",
                "commands_and_emails",
                "commands_only",
            ):
                for key in trackme_stateful_alert_command_keys:
                    value = alert_properties.get(key)
                    if value in ("", None):
                        reason = "missing" if value is None else "empty string"
                        missing_fields[key] = reason

            if missing_fields:
                return {
                    "payload": {
                        "result": "Validation error: one or more required fields are missing or invalid for trackme_stateful_alert.",
                        "failing_fields": missing_fields,
                        "alert_properties": alert_properties,
                        "debug_values": {
                            k: alert_properties.get(k)
                            for k in (
                                trackme_stateful_alert_base_keys
                                + trackme_stateful_alert_email_keys
                                + trackme_stateful_alert_command_keys
                            )
                        },
                    },
                    "status": 400,
                }

        # Step 1: retrieve the current owner of the knowledge objects for this tenant
        # Shall this fail for any reason, the alert will be owned by admin

        collection_vtenants_name = "kv_trackme_virtual_tenants"
        collection_vtenants = service.kvstore[collection_vtenants_name]

        # Define the KV query search string
        query_string = {
            "tenant_id": tenant_id,
        }

        # Get the tenant
        try:
            vtenant_record = collection_vtenants.data.query(
                query=json.dumps(query_string)
            )[0]
            tenant_owner = vtenant_record.get("tenant_owner")

        except Exception as e:
            tenant_owner = "admin"
            logger.error(
                f'tenant_id="{tenant_id}", failed to retrieve the tenant record with exception="{str(e)}"'
            )

        # Step 2: create a new alert with our options

        # create a new alert
        logger.info(
            f'tenant_id="{tenant_id}", attempting to create a new alert alert_name="{alert_name}"'
        )
        try:
            newalert = service.saved_searches.create(str(alert_name), str(alert_search))
            logger.info(
                f'tenant_id="{tenant_id}", action="success", alert_name="{alert_name}"'
            )
        except Exception as e:
            logger.error(
                f'tenant_id="{tenant_id}", failure to create alert alert_name="{alert_name}" with exception="{str(e)}"'
            )
            return {
                "payload": "Warn: exception encountered while creating alert: "
                + str(alert_name)
                + " with exception: "
                + str(e),
                "status": 500,
            }

        # update the properties
        newalert_update = service.saved_searches[str(alert_name)]

        # Complete the report definition
        logger.debug(
            f'tenant_id="{tenant_id}", alert_properties="{json.dumps(alert_properties)}"'
        )
        kwargs = json.loads(json.dumps(alert_properties))

        # For optimization purposes, if the schedule is set to every 5 minutes, randomly choose an every 5 minutes schedule
        if kwargs.get("cron_schedule") == "*/5 * * * *":
            cron_random_list = [
                "*/5 * * * *",
                "1-56/5 * * * *",
                "2-57/5 * * * *",
                "3-58/5 * * * *",
                "4-59/5 * * * *",
            ]
            kwargs["cron_schedule"] = random.choice(cron_random_list)
        elif kwargs.get("cron_schedule") == "*/10 * * * *":
            cron_random_list = [
                "*/10 * * * *",
                "1-59/10 * * * *",
                "2-59/10 * * * *",
                "3-59/10 * * * *",
                "4-59/10 * * * *",
                "5-59/10 * * * *",
                "6-59/10 * * * *",
                "7-59/10 * * * *",
                "8-59/10 * * * *",
                "9-59/10 * * * *",
            ]
            kwargs["cron_schedule"] = random.choice(cron_random_list)
        elif kwargs.get("cron_schedule") == "*/15 * * * *":
            cron_random_list = [
                "*/10 * * * *",
                "1-59/10 * * * *",
                "2-59/10 * * * *",
                "3-59/10 * * * *",
                "4-59/10 * * * *",
                "5-59/10 * * * *",
                "6-59/10 * * * *",
                "7-59/10 * * * *",
                "8-59/10 * * * *",
                "9-59/10 * * * *",
                "10-59/10 * * * *",
                "11-59/10 * * * *",
                "12-59/10 * * * *",
                "13-59/10 * * * *",
                "14-59/10 * * * *",
            ]
            kwargs["cron_schedule"] = random.choice(cron_random_list)
        elif (
            kwargs.get("cron_schedule") == "*/30 * * * *"
            or kwargs.get("cron_schedule") == "30 * * * *"
        ):
            cron_random_list = [
                "*/30 * * * *",
                "1,31 * * * *",
                "2,32 * * * *",
                "3,33 * * * *",
                "4,34 * * * *",
                "5,35 * * * *",
            ]
            kwargs["cron_schedule"] = random.choice(cron_random_list)
        elif kwargs.get("cron_schedule") == "*/60 * * * *":
            cron_random_list = [
                "*/60 * * * *",
                "2,32 * * * *",
                "3,33 * * * *",
                "4,34 * * * *",
                "5,35 * * * *",
                "6,36 * * * *",
                "7,37 * * * *",
                "8,38 * * * *",
                "9,39 * * * *",
            ]
            kwargs["cron_schedule"] = random.choice(cron_random_list)

        # Update the server and refresh the local copy of the object
        logger.info(
            f'tenant_id="{tenant_id}", attempting to update alert_name="{alert_name}" with kwargs="{json.dumps(kwargs, indent=1)}"'
        )
        try:
            newalert_update.update(**kwargs).refresh()
            logger.info(
                f'tenant_id="{tenant_id}", action="success", alert_name="{alert_name}" with kwargs="{json.dumps(kwargs, indent=1)}"'
            )

        except Exception as e:
            logger.error(
                f'tenant_id="{tenant_id}", failure to update report alert_name="{alert_name}" with exception="{str(e)}"'
            )
            return {"payload": "Warn: exception encountered: " + str(e), "status": 500}

        # Handler the owner (cannot be performed via splunklib)
        kwargs = {"sharing": trackme_default_sharing, "owner": str(tenant_owner)}

        record_url = f"{request_info.server_rest_uri}/servicesNS/nobody/trackme/saved/searches/{urllib.parse.quote(alert_name)}/acl"

        logger.info(
            f'tenant_id="{tenant_id}", attempting to update alert_name="{alert_name}"'
        )
        try:
            response = requests.post(
                record_url, headers=header, data=kwargs, verify=False, timeout=600
            )
            logger.info(
                f'tenant_id="{tenant_id}", action="success", alert_name="{alert_name}"'
            )
        except Exception as e:
            logger.error(
                f'tenant_id="{tenant_id}", failure to update alert_name="{alert_name}" with exception="{str(e)}"'
            )
            return {"payload": "Warn: exception encountered: " + str(e), "status": 500}

        # Step 3: Add the alert to the tenant collection

        # Register the new components in the vtenant collection
        collection_vtenants_name = "kv_trackme_virtual_tenants"
        collection_vtenants = service.kvstore[collection_vtenants_name]

        # Define the KV query search string
        query_string = {
            "tenant_id": tenant_id,
        }

        # Get the tenant
        try:
            vtenant_record = collection_vtenants.data.query(
                query=json.dumps(query_string)
            )[0]
            vtenant_key = vtenant_record.get("_key")

        except Exception as e:
            vtenant_key = None
            logger.error(
                f'tenant_id="{tenant_id}", failed to retrieve the tenant record'
            )

        # We can only proceed with a valid tenant record
        if vtenant_key:
            # check if TCM is enabled in receiver mode
            enable_conf_manager_receiver = int(
                trackme_conf["trackme_conf"]["trackme_general"][
                    "enable_conf_manager_receiver"
                ]
            )

            if enable_conf_manager_receiver == 1:
                try:
                    tcm_response = trackme_send_to_tcm(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        resp_dict,
                        "post",
                        "/services/trackme/v2/alerting/admin/create_alert",
                    )
                    logger.info(f"trackme_send_to_tcm was successfully executed")
                except Exception as e:
                    logger.error(
                        f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                    )

            # Try to get the current definition
            try:
                tenant_alert_objects = vtenant_record.get("tenant_alert_objects")
                # logger.debug
                logger.debug(f'tenant_alert_objects="{tenant_alert_objects}"')
            except Exception as e:
                tenant_alert_objects = None

            # add to existing disct
            if tenant_alert_objects and tenant_alert_objects != "None":
                logger.debug("vtenant_dict is not empty")
                vtenant_dict = json.loads(tenant_alert_objects)
                logger.debug(f'vtenant_dict="{json.dumps(vtenant_dict, indent=1)}"')
                alerts = vtenant_dict["alerts"]
                alerts.append(str(alert_name))
                vtenant_dict = dict(
                    [
                        ("alerts", alerts),
                    ]
                )

            # empty dict
            else:
                logger.debug("vtenant_dict is empty")
                alerts = []
                alerts.append(str(alert_name))
                vtenant_dict = dict(
                    [
                        ("alerts", alerts),
                    ]
                )
                logger.debug(
                    f'creating vtenant_dict="{json.dumps(vtenant_dict, indent=1)}"'
                )

            try:
                vtenant_record["tenant_alert_objects"] = json.dumps(
                    vtenant_dict, indent=1
                )
                collection_vtenants.data.update(
                    str(vtenant_key), json.dumps(vtenant_record)
                )

            except Exception as e:
                logger.error(
                    f'failure while trying to update the vtenant KVstore record, exception="{str(e)}"'
                )
                return {
                    "payload": "Warn: exception encountered: "
                    + str(e)  # Payload of the request.
                }

        # end
        summary_properties = json.loads(json.dumps(alert_properties))
        summary_properties["search"] = str(alert_search)
        summary_properties["owner"] = str(tenant_owner)
        logger.info(
            f'tenant_id="{tenant_id}", new alert was successfully created, alert_name="{alert_name}", properties="{json.dumps(summary_properties, indent=1)}"'
        )

        # Record an audit change
        trackme_audit_event(
            request_info.system_authtoken,
            request_info.server_rest_uri,
            tenant_id,
            request_info.user,
            "success",
            "create alert",
            str(alert_name),
            "common",
            json.dumps(summary_properties, indent=1),
            "Alert was successfully created",
            str(update_comment),
        )

        # render response
        return {
            "payload": {"alert.name": alert_name, "properties": summary_properties},
            "status": 200,
        }

    # Delete an existing alert
    def post_del_alert(self, request_info, **kwargs):
        # alert options
        tenant_id = None
        alert_name = None

        # describe
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
                alert_name = resp_dict["alert_name"]

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes a tracking alert for the component, it requires a POST call with the following information:",
                "resource_desc": "Delete a TrackMe alert",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/alerting/admin/del_alert\" body=\"{'tenant_id':'mytenant', 'alert_name': 'my alert'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "alert_name": "The name of the alert to be deleted",
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
            token=request_info.system_authtoken,
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

        # delete alert
        logger.info(
            f'tenant_id="{tenant_id}", attempting to delete alert alert_name="{alert_name}"'
        )
        try:
            service.saved_searches.delete(str(alert_name))
            logger.info(
                f'tenant_id="{tenant_id}", action="success", alert_name="{alert_name}"'
            )

        except Exception as e:
            logger.error(
                f'tenant_id="{tenant_id}", failure to delete alert alert_name="{alert_name}" with exception="{str(e)}"'
            )
            return {
                "payload": "Warn: exception encountered while deleting alert: "
                + str(alert_name)
                + " with exception: "
                + str(e),
                "status": 500,
            }

        # Register the deletion in the vtenant collection
        collection_vtenants_name = "kv_trackme_virtual_tenants"
        collection_vtenants = service.kvstore[collection_vtenants_name]

        # Define the KV query search string
        query_string = {
            "tenant_id": tenant_id,
        }

        # Get the tenant
        try:
            vtenant_record = collection_vtenants.data.query(
                query=json.dumps(query_string)
            )[0]
            vtenant_key = vtenant_record.get("_key")

        except Exception as e:
            vtenant_key = None
            logger.error(
                f'tenant_id="{tenant_id}", failed to retrieve the tenant record'
            )

        # We can only proceed with a valid tenant record
        if vtenant_key:
            # check if TCM is enabled in receiver mode
            enable_conf_manager_receiver = int(
                trackme_conf["trackme_conf"]["trackme_general"][
                    "enable_conf_manager_receiver"
                ]
            )

            if enable_conf_manager_receiver == 1:
                try:
                    tcm_response = trackme_send_to_tcm(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        resp_dict,
                        "post",
                        "/services/trackme/v2/alerting/admin/del_alert",
                    )
                    logger.info(f"trackme_send_to_tcm was successfully executed")
                except Exception as e:
                    logger.error(
                        f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                    )

            # Try to get the current definition
            try:
                tenant_alert_objects = vtenant_record.get("tenant_alert_objects")
                # logger.debug
                logger.debug(f'tenant_alert_objects="{tenant_alert_objects}"')
            except Exception as e:
                tenant_alert_objects = None

            # remove from existing disct
            if tenant_alert_objects and tenant_alert_objects != "None":
                logger.debug("vtenant_dict is not empty")
                vtenant_dict = json.loads(tenant_alert_objects)
                logger.debug(f'vtenant_dict="{json.dumps(vtenant_dict, indent=1)}"')
                alerts = vtenant_dict["alerts"]
                alerts.remove(str(alert_name))
                vtenant_dict = dict(
                    [
                        ("alerts", alerts),
                    ]
                )

            # Update the KVstore
            try:
                vtenant_record["tenant_alert_objects"] = json.dumps(
                    vtenant_dict, indent=1
                )
                collection_vtenants.data.update(
                    str(vtenant_key), json.dumps(vtenant_record)
                )

            except Exception as e:
                logger.error(
                    f'failure while trying to update the vtenant KVstore record, exception="{str(e)}"'
                )
                return {
                    "payload": "Warn: exception encountered: "
                    + str(e)  # Payload of the request.
                }

        # end
        logger.info(
            f'tenant_id="{tenant_id}", alert was successfully deleted, alert_name="{alert_name}"'
        )

        # Record an audit change
        trackme_audit_event(
            request_info.system_authtoken,
            request_info.server_rest_uri,
            tenant_id,
            request_info.user,
            "success",
            "delete alert",
            str(alert_name),
            "common",
            str(alert_name),
            "Alert was successfully deleted",
            str(update_comment),
        )

        # render response
        return {
            "payload": {
                "action": "success",
                "alert_title": str(alert_name),
                "response": "The alert was successfully deleted",
            },
            "status": 200,
        }
