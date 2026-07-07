#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_vtenant.py"
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
from collections import OrderedDict
import time
import requests

splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.vtenants_user", "trackme_rest_api_vtenants_user.log"
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_get_version, trackme_getloglevel, trackme_parse_describe_flag, trackme_reqinfo, trackme_vtenant_account

# import trackme load libs
from trackme_libs_load import trackmeload

# import trackme libs schema
from trackme_libs_schema import trackme_schema_format_version

# import trackme decision maker
from trackme_libs_decisionmaker import convert_epoch_to_datetime
from trackme_libs_cmdb import OOTB_CMDB_DEFAULTS

# import the collections dict
from collections_data import vtenant_account_default

# import Splunk SDK client
import splunklib.client as client
import splunklib.results as results


class TrackMeHandlerVtenantsRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerVtenantsRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_vtenants(self, request_info, **kwargs):
        response = {
            "resource_group_name": "vtenants",
            "resource_group_desc": "Endpoints related to the management of TrackMe Virtual Tenants (read only operations)",
        }

        return {"payload": response, "status": 200}

    #
    # Get tenants
    #

    def get_show_tenants(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/vtenants/show_tenants" mode="get"
        """

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        describe = trackme_parse_describe_flag(request_info)


        if describe:
            response = {
                "describe": "This endpoint retrieves the tenants KVStore collection returned as a JSON object, it requires a GET call with no data required",
                "resource_desc": "Retrieve the virtual tenants collection",
                "resource_spl_example": '| trackme url="/services/trackme/v2/vtenants/show_tenants" mode="get"',
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            collection_name = "kv_trackme_virtual_tenants"
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=splunkd_port,
                token=request_info.session_key,
                timeout=600,
            )
            collection = service.kvstore[collection_name]

            # TrackMe version
            trackme_version = trackme_get_version(service)

            # Get schema_version_required
            schema_version_required = trackme_schema_format_version(trackme_version)

            records = collection.data.query()
            results_records = []

            for record in records:
                # Add the schema_version_required to the record
                record["schema_version_required"] = schema_version_required
                # Set the status of tenant_updated_status, if schema_version in the record is equal to schema_version_required,
                # the status is "updated", otherwise it is "pending"
                # If schema_version_required is 0 (version retrieval failed), treat all tenants as "updated"
                # to align with graceful degradation when DB Connect causes permission issues
                if schema_version_required == 0:
                    record["tenant_updated_status"] = "updated"
                else:
                    # Handle case where schema_version is missing from the record (e.g., tenant created when version retrieval failed)
                    schema_version = record.get("schema_version")
                    if schema_version is None:
                        # If schema_version is missing, use "undetermined" to indicate we cannot determine the status
                        # This is different from "pending" which implies an upgrade is in progress
                        # "undetermined" should not block underlying logic like hybrid trackers
                        record["tenant_updated_status"] = "undetermined"
                    elif int(schema_version) == schema_version_required:
                        record["tenant_updated_status"] = "updated"
                    else:
                        record["tenant_updated_status"] = "pending"

                schema_version_mtime = record.get("schema_version_mtime")
                if schema_version_mtime:
                    schema_version_mtime = convert_epoch_to_datetime(
                        schema_version_mtime
                    )
                else:
                    schema_version_mtime = "N/A"
                record["schema_version_mtime"] = schema_version_mtime

                # Add to our final list
                results_records.append(record)

            # Render
            return {"payload": results_records, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    #
    # trackmeload
    #

    def post_trackmeload(self, request_info, **kwargs):
        describe = False
        start = time.time()

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                mode = resp_dict.get("mode", "full")
                if not mode in ("full", "expanded"):
                    response = {
                        "action": "failure",
                        "response": f"Invalid value for mode",
                    }
                    logger.error(json.dumps(response))
                    return {"payload": response, "status": 500}

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves the unified Virtual Tenants view, it requires a POST call with the following data:",
                "resource_desc": "Retrieve the unified Virtual Tenants view",
                "resource_spl_example": '| trackme url="/services/trackme/v2/vtenants/trackmeload" mode="post" body="{\'mode\': \'full\'}"',
                "options": [
                    {
                        "mode": "The mode, valid options: <full|expanded>",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # set service_system
        service_system = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % request_info.session_key,
            "Content-Type": "application/json",
        }

        # TrackMe reqinfo
        reqinfo = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        trackmeconf = reqinfo["trackme_conf"]

        # get current user
        username = request_info.user

        # get users
        users = service_system.users

        # get roles
        roles = service_system.roles

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # the final response
        final_response = {}

        # add the username
        final_response["username"] = username

        # get the number of tenants and add to the response
        collection_name = "kv_trackme_virtual_tenants"
        collection = service_system.kvstore[collection_name]
        vtenants_records = collection.data.query()
        final_response["vtenants_count"] = len(vtenants_records)

        # get the response from trackmeload
        try:
            trackmeload_response = trackmeload(
                request_info.session_key,
                request_info.server_rest_uri,
                service_system,
                users,
                roles,
                username,
                mode,
            )
            trackmeload_response_tenants = trackmeload_response.get("tenants", {})

            # Get the list
            trackmeload_response_tenants_list = trackmeload_response.get("tenants", [])

            # loop and add the account
            virtual_tenants_list = []
            for virtual_tenant in trackmeload_response_tenants_list:

                # Get Virtual Tenant account
                try:
                    vtenant_account = trackme_vtenant_account(
                        request_info.session_key,
                        request_info.server_rest_uri,
                        virtual_tenant.get("tenant_id"),
                    )
                except Exception as e:
                    vtenant_account = {}

                # add
                virtual_tenant["vtenant_account"] = vtenant_account
                virtual_tenants_list.append(virtual_tenant)

            # update the final response
            final_response["tenants_json"] = {"tenants": virtual_tenants_list}

            # pass through faulty tenants if any were detected during loading
            faulty_tenants = trackmeload_response.get("faulty_tenants", [])
            if faulty_tenants:
                final_response["faulty_tenants"] = faulty_tenants
                logger.warning(
                    f"faulty_tenants detected during trackmeload: {json.dumps(faulty_tenants)}"
                )

        except Exception as e:
            # log error and return 500
            response = {
                "action": "failure",
                "response": f"An exception was encountered while retrieving the tenants from the central KVStore, collection={collection_name}, exception={str(e)}",
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

        # active count
        vtenants_count_active = 0
        for vtenant_record in trackmeload_response_tenants:
            logger.debug(f'vtenant_record="{json.dumps(vtenant_record, indent=2)}"')
            if vtenant_record.get("tenant_status") == "enabled":
                vtenants_count_active += 1
        final_response["vtenants_count_active"] = vtenants_count_active

        #
        # Privilege level
        #

        record_url = (
            "%s/services/trackme/v2/configuration/trackme_check_privileges_level"
            % (request_info.server_rest_uri)
        )

        user_level = None

        # retrieve and add to the response
        try:
            response = requests.get(
                record_url,
                headers=header,
                verify=False,
                timeout=600,
            )
            if response.status_code == 200:
                user_level = response.json().get("user_level")
                final_response["user_level"] = user_level
        except Exception as e:
            return {
                "payload": {
                    "response": f"An exception was encountered while retrieving the privileges level, exception={str(e)}",
                    "exception": str(e),
                },
                "status": 500,
            }

        # theme & user prefs are parts of the check_privileges_level endpoint answer
        user_theme_prefs = response.json().get("user_prefs")
        for key in user_theme_prefs:
            final_response[key] = user_theme_prefs.get(key)

        # log perf only in debug
        logger.debug(
            f"function post_trackmeload has terminated, run_time={round(time.time() - start, 3)}"
        )

        # add trackmeconf to the response
        final_response["trackmeconf"] = trackmeconf

        # Sourcetype cap alerts: lightweight query on tiny global KV collection
        try:
            cap_alert_collection = service_system.kvstore["kv_trackme_sourcetype_cap_alerts"]
            cap_alert_records = cap_alert_collection.data.query()
            final_response["sourcetype_cap_alerts"] = cap_alert_records
        except Exception:
            final_response["sourcetype_cap_alerts"] = []

        # Configuration Guardian alerts: RBAC-filtered so non-admin users only see
        # alerts for tenants they are already allowed to see. System-scoped alerts
        # (tenant_id empty) are shown to everyone.
        try:
            guardian_collection = service_system.kvstore[
                "kv_trackme_configuration_guardian_alerts"
            ]
            guardian_records = guardian_collection.data.query() or []
            visible_tenants = (
                final_response.get("tenants_json", {}).get("tenants", []) or []
            )
            visible_tenant_ids = {
                str(tenant.get("tenant_id"))
                for tenant in visible_tenants
                if tenant.get("tenant_id")
            }
            filtered_guardian = []
            for record in guardian_records:
                rec_tenant_id = str(record.get("tenant_id") or "")
                if rec_tenant_id and rec_tenant_id not in visible_tenant_ids:
                    continue
                filtered_guardian.append(record)
            final_response["guardian_alerts"] = filtered_guardian
        except Exception:
            final_response["guardian_alerts"] = []

        # Return
        return {
            "payload": final_response,
            "status": 200,
        }

    #
    # trackmeload legacy: this endpoint uses a search driven approach and was the previous way to retrieve the TrackMe Virtual Tenants json data
    # very view users seems to have had issues with the new faster method, and can switch to this mode in case of an issue with the new method
    #

    def post_trackmeload_legacy(self, request_info, **kwargs):
        describe = False
        start = time.time()

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                mode = resp_dict.get("mode", "full")
                if not mode in ("full", "expanded"):
                    response = {
                        "action": "failure",
                        "response": f"Invalid value for mode",
                    }
                    logger.error(json.dumps(response))
                    return {"payload": response, "status": 500}

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves the unified Virtual Tenants view (legacy search driven method), it requires a POST call with the following data:",
                "resource_desc": "Retrieve the unified Virtual Tenants view",
                "resource_spl_example": '| trackme url="/services/trackme/v2/vtenants/trackmeload_legacy" mode="post" body="{\'mode\': \'full\'}"',
                "options": [
                    {
                        "mode": "The mode, valid options: <full|expanded>",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % request_info.session_key,
            "Content-Type": "application/json",
        }

        # TrackMe reqinfo
        reqinfo = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        trackmeconf = reqinfo["trackme_conf"]

        # get current user
        username = request_info.user

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # the final response
        final_response = {}

        # add the username
        final_response["username"] = username

        # get the number of tenants and add to the response
        collection_name = "kv_trackme_virtual_tenants"
        collection = service.kvstore[collection_name]
        vtenants_records = collection.data.query()
        final_response["vtenants_count"] = len(vtenants_records)

        #
        # trackmeload custom command
        #

        # run trackmeload custom command and add to the response
        search = f"| trackmeload mode={mode}"
        kwargs_oneshot = {
            "earliest_time": "-5m",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }

        try:
            oneshotsearch_results = service.jobs.oneshot(search, **kwargs_oneshot)
            reader = results.JSONResultsReader(oneshotsearch_results)

            for item in reader:
                if isinstance(item, dict):
                    final_response["tenants_json"] = json.loads(item.get("_raw"))

        except Exception as e:
            logger.error(f'execution failed with exception="{str(e)}"')

        #
        # Privilege level
        #

        record_url = (
            "%s/services/trackme/v2/configuration/trackme_check_privileges_level"
            % (request_info.server_rest_uri)
        )

        user_level = None

        # retrieve and add to the response
        try:
            response = requests.get(
                record_url,
                headers=header,
                verify=False,
                timeout=600,
            )
            if response.status_code == 200:
                user_level = response.json().get("user_level")
                final_response["user_level"] = user_level
        except Exception as e:
            return {
                "payload": {
                    "response": "An exception was encountered",
                    "exception": str(e),
                },
                "status": 500,
            }

        # theme & user prefs are parts of the check_privileges_level endpoint answer
        user_theme_prefs = response.json().get("user_prefs")
        for key in user_theme_prefs:
            final_response[key] = user_theme_prefs.get(key)

        # active count
        trackmeload_response_tenants = final_response["tenants_json"].get("tenants", {})

        vtenants_count_active = 0
        virtual_tenants_list = []

        for vtenant_record in trackmeload_response_tenants:
            logger.debug(f'vtenant_record="{json.dumps(vtenant_record, indent=2)}"')
            if vtenant_record.get("tenant_status") == "enabled":
                vtenants_count_active += 1

            # Get Virtual Tenant account
            try:
                vtenant_account = trackme_vtenant_account(
                    request_info.session_key,
                    request_info.server_rest_uri,
                    vtenant_record.get("tenant_id"),
                )
            except Exception as e:
                vtenant_account = {}

            # add
            vtenant_record["vtenant_account"] = vtenant_account

            # add to our final list
            virtual_tenants_list.append(vtenant_record)

        final_response["vtenants_count_active"] = vtenants_count_active

        # update the final response
        final_response["tenants_json"] = {"tenants": virtual_tenants_list}

        # add trackmeconf to the response
        final_response["trackmeconf"] = trackmeconf

        # Sourcetype cap alerts: lightweight query on tiny global KV collection
        try:
            cap_alert_collection = service.kvstore["kv_trackme_sourcetype_cap_alerts"]
            cap_alert_records = cap_alert_collection.data.query()
            final_response["sourcetype_cap_alerts"] = cap_alert_records
        except Exception:
            final_response["sourcetype_cap_alerts"] = []

        # Configuration Guardian alerts: RBAC-filtered against the tenants visible
        # to the caller (same filtering as the non-legacy path).
        try:
            guardian_collection = service.kvstore[
                "kv_trackme_configuration_guardian_alerts"
            ]
            guardian_records = guardian_collection.data.query() or []
            visible_tenants = (
                final_response.get("tenants_json", {}).get("tenants", []) or []
            )
            visible_tenant_ids = {
                str(tenant.get("tenant_id"))
                for tenant in visible_tenants
                if tenant.get("tenant_id")
            }
            filtered_guardian = []
            for record in guardian_records:
                rec_tenant_id = str(record.get("tenant_id") or "")
                if rec_tenant_id and rec_tenant_id not in visible_tenant_ids:
                    continue
                filtered_guardian.append(record)
            final_response["guardian_alerts"] = filtered_guardian
        except Exception:
            final_response["guardian_alerts"] = []

        # log perf only in debug
        logger.debug(
            f"function post_trackmeload_legacy has terminated, run_time={round(time.time() - start, 3)}"
        )

        # Return
        return {
            "payload": final_response,
            "status": 200,
        }

    #
    # Get a single tenant
    #

    def post_show_tenant(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/vtenants/show_tenant" mode="post" body="{'tenant_id': 'mytenant'}"
        """

        tenant_id = None
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
        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        if describe:
            response = {
                "describe": "This endpoint retrieves a single tenant record in the KVStore collection and returns it as a JSON object, it requires a POST call with the following data:",
                "resource_desc": "Retrieve a single virtual tenant",
                "resource_spl_example": '| trackme url="/services/trackme/v2/vtenants/show_tenant" mode="post" body="{\'tenant_id\': \'mytenant\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Get Virtual Tenant account
        try:
            vtenant_account = trackme_vtenant_account(
                request_info.session_key,
                request_info.server_rest_uri,
                tenant_id,
            )
        except Exception as e:
            vtenant_account = None

        try:
            collection_name = "kv_trackme_virtual_tenants"
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=splunkd_port,
                token=request_info.session_key,
                timeout=600,
            )
            collection = service.kvstore[collection_name]

            # Define the KV query search string
            query_string = {
                "tenant_id": tenant_id,
            }

            try:
                vtenant_record = collection.data.query(query=json.dumps(query_string))[
                    0
                ]
                key = vtenant_record.get("_key")

            except Exception as e:
                key = None

            if key:

                # Add the vtenant_account to the vtenant_record
                if vtenant_account:
                    vtenant_record["vtenant_account"] = vtenant_account

                # Render
                return {"payload": vtenant_record, "status": 200}
            else:
                return {
                    "payload": {"response": f"this tenant could not be found, tenant_id={tenant_id}"},
                    "status": 404,
                }

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    #
    # Get indexes configuration for a given tenant
    #

    def post_tenant_idx_settings(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/vtenants/tenant_idx_settings" mode="post" body="{'tenant_id': 'mytenant'}"
        """

        tenant_id = None
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

                # Optionally filter on a given index stanza name
                try:
                    idx_stanza = resp_dict["idx_stanza"]
                except Exception as e:
                    idx_stanza = "all"
                if not idx_stanza in (
                    "all",
                    "trackme_summary_idx",
                    "trackme_audit_idx",
                    "trackme_metric_idx",
                    "trackme_notable_idx",
                ):
                    idx_stanza = "all"

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe or not resp_dict:
            response = {
                "describe": "This endpoint retrieves indexes settings for a given tenant returned as a JSON object, it requires a POST call with the following data:",
                "resource_desc": "Get indexes configuration for a virtual tenant",
                "resource_spl_example": '| trackme url="/services/trackme/v2/vtenants/tenant_idx_settings" mode="post" body="{\'tenant_id\': \'mytenant\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "idx_stanza": "Optional, the index stanza, defaults to: all, valid additional options are: trackme_summary_idx | trackme_audit_idx | trackme_metric_idx | trackme_notable_idx",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # TrackMe reqinfo
        reqinfo = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        trackmeconf = reqinfo["trackme_conf"]["index_settings"]

        # set global indexes
        global_trackme_summary_idx = trackmeconf["trackme_summary_idx"]
        global_trackme_audit_idx = trackmeconf["trackme_audit_idx"]
        global_trackme_metric_idx = trackmeconf["trackme_metric_idx"]
        global_trackme_notable_idx = trackmeconf["trackme_notable_idx"]

        # small function to verify the local idx in the next block
        def get_index_value(
            local_tenant_idx_dict, key, global_value, tenant_idx_settings
        ):
            try:
                return local_tenant_idx_dict[key]
            except Exception as e:
                return global_value

        try:
            collection_name = "kv_trackme_virtual_tenants"
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=splunkd_port,
                token=request_info.session_key,
                timeout=600,
            )
            collection = service.kvstore[collection_name]

            # Define the KV query search string
            query_string = {
                "tenant_id": tenant_id,
            }

            try:
                vtenant_record = collection.data.query(query=json.dumps(query_string))[
                    0
                ]
                key = vtenant_record.get("_key")
                tenant_idx_settings = vtenant_record.get("tenant_idx_settings")

            except Exception as e:
                key = None

            if key:
                # If the tenant_idx_settings record does not equal to global, attempt to the JSON config
                if tenant_idx_settings != "global":
                    try:
                        local_tenant_idx_dict = json.loads(tenant_idx_settings)
                        trackme_summary_idx = get_index_value(
                            local_tenant_idx_dict,
                            "trackme_summary_idx",
                            global_trackme_summary_idx,
                            tenant_idx_settings,
                        )
                        trackme_audit_idx = get_index_value(
                            local_tenant_idx_dict,
                            "trackme_audit_idx",
                            global_trackme_audit_idx,
                            tenant_idx_settings,
                        )
                        trackme_metric_idx = get_index_value(
                            local_tenant_idx_dict,
                            "trackme_metric_idx",
                            global_trackme_metric_idx,
                            tenant_idx_settings,
                        )
                        trackme_notable_idx = get_index_value(
                            local_tenant_idx_dict,
                            "trackme_notable_idx",
                            global_trackme_notable_idx,
                            tenant_idx_settings,
                        )

                        # final dict
                        tenant_idx_dict = {
                            "trackme_summary_idx": trackme_summary_idx,
                            "trackme_audit_idx": trackme_audit_idx,
                            "trackme_metric_idx": trackme_metric_idx,
                            "trackme_notable_idx": trackme_notable_idx,
                        }

                    except Exception as e:
                        # use global if load failed
                        tenant_idx_dict = {
                            "trackme_summary_idx": global_trackme_summary_idx,
                            "trackme_audit_idx": global_trackme_audit_idx,
                            "trackme_metric_idx": global_trackme_metric_idx,
                            "trackme_notable_idx": global_trackme_notable_idx,
                        }

                # use global otherwise
                else:
                    tenant_idx_dict = {
                        "trackme_summary_idx": global_trackme_summary_idx,
                        "trackme_audit_idx": global_trackme_audit_idx,
                        "trackme_metric_idx": global_trackme_metric_idx,
                        "trackme_notable_idx": global_trackme_notable_idx,
                    }

                # Render
                if idx_stanza == "all":
                    return {"payload": tenant_idx_dict, "status": 200}
                else:
                    return {
                        "payload": {idx_stanza: tenant_idx_dict[idx_stanza]},
                        "status": 200,
                    }

            else:  # return default

                if idx_stanza == "all":
                    return {
                        "payload": {
                            "trackme_summary_idx": trackmeconf["trackme_summary_idx"],
                            "trackme_audit_idx": trackmeconf["trackme_audit_idx"],
                            "trackme_metric_idx": trackmeconf["trackme_metric_idx"],
                            "trackme_notable_idx": trackmeconf["trackme_notable_idx"],
                        },
                        "status": 200,
                    }
                else:
                    return {
                        "payload": {idx_stanza: trackmeconf[idx_stanza]},
                        "status": 200,
                    }

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    #
    # Get vtenants account configuration
    #

    def post_vtenants_accounts(self, request_info, **kwargs):
        tenant_id = None
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                # tenant_id is optional
                tenant_id = resp_dict.get("tenant_id", None)
        else:
            describe = False

        if describe:
            response = {
                "describe": "This endpoint retrieves all vtenants accounts and return these as a JSON object, it requires a POST call with the following data:",
                "resource_desc": "Get virtual tenants accounts",
                "resource_spl_example": '| trackme url="/services/trackme/v2/vtenants/vtenants_accounts" mode="post" body="{\'tenant_id\': \'mytenant\'}"',
                "options": [
                    {
                        "tenant_id": "OPTIONAL. The tenant identifier",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # set service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # conf
        conf_file = "trackme_settings"
        confs = service.confs[str(conf_file)]

        # get vtenant account
        conf_file = "trackme_vtenants"

        # if there are no account, raise an exception, otherwise what we would do here?
        try:
            confs = service.confs[str(conf_file)]
        except Exception as e:
            confs = None

        # init
        trackme_vtenant_conf = {}

        # get accounts
        if confs:
            for stanza in confs:
                # Store key-value pairs from the stanza content in the corresponding sub-dictionary
                if not tenant_id or stanza.name == str(tenant_id):
                    trackme_vtenant_conf[stanza.name] = {}
                    for stanzakey, stanzavalue in stanza.content.items():
                        logger.debug(
                            f'get virtual tenant account, Processing stanzakey="{stanzakey}", stanzavalue="{stanzavalue}"'
                        )
                        trackme_vtenant_conf[stanza.name][stanzakey] = stanzavalue

                    # check that we have a field alias defined in trackme_vtenant_conf[stanza.name], otherwise add it equal to stanza.name
                    if not trackme_vtenant_conf[stanza.name].get("alias"):
                        trackme_vtenant_conf[stanza.name]["alias"] = stanza.name

                    #
                    # mloutliers:
                    # - loop troough each component in mloutliers_allowlist,
                    # for each define a new key as mloutliers_<component> which gets 0 if mloutliers is disabled, 0 if enabled and not in the list, 1 if enabled and in the list
                    mloutliers = int(
                        trackme_vtenant_conf[stanza.name].get("mloutliers", 0)
                    )

                    # outliers_allowlist
                    outliers_allowlist = trackme_vtenant_conf[stanza.name].get(
                        "mloutliers_allowlist", "dsm,dhm,flx,wlk,fqm"
                    )

                    # Define the components
                    outliers_components = ["dsm", "dhm", "flx", "wlk", "fqm"]

                    # Convert the allowlist to a set for faster lookups
                    mloutliers_set = set(outliers_allowlist.split(","))

                    # Create a dictionary dynamically
                    mloutliers_dict = {
                        f"mloutliers_{comp}": (
                            1 if comp in mloutliers_set and mloutliers == 1 else 0
                        )
                        for comp in outliers_components
                    }

                    # If you need separate variables, you can unpack the dictionary
                    trackme_vtenant_conf[stanza.name]["mloutliers_dsm"] = (
                        mloutliers_dict["mloutliers_dsm"]
                    )
                    trackme_vtenant_conf[stanza.name]["mloutliers_dhm"] = (
                        mloutliers_dict["mloutliers_dhm"]
                    )
                    trackme_vtenant_conf[stanza.name]["mloutliers_flx"] = (
                        mloutliers_dict["mloutliers_flx"]
                    )
                    trackme_vtenant_conf[stanza.name]["mloutliers_fqm"] = (
                        mloutliers_dict["mloutliers_fqm"]
                    )
                    trackme_vtenant_conf[stanza.name]["mloutliers_wlk"] = (
                        mloutliers_dict["mloutliers_wlk"]
                    )

            # response
            try:
                if tenant_id:
                    return {"payload": trackme_vtenant_conf[tenant_id], "status": 200}
                else:
                    return {"payload": trackme_vtenant_conf, "status": 200}
            except Exception as e:
                msg = f"an exception occurred, either you have requested a wrong tenant_id, either this installation is corrupted? exception={str(e)}"
                logger.error(msg)
                return {"payload": msg, "status": 500}

        else:
            return {"payload": trackme_vtenant_conf, "status": 200}

    #
    # Get tenant score configuration
    #

    def get_tenant_score_config(self, request_info, **kwargs):
        """
        | trackme url=/services/trackme/v2/vtenants/tenant_score_config mode=get params="{'tenant_id': 'mytenant'}"
        """

        # Declare main variables
        tenant_id = None
        describe = False

        # Retrieve from query parameters
        try:
            params_dict = request_info.raw_args["query_parameters"]
        except Exception as e:
            params_dict = None

        if params_dict is not None:
            try:
                tenant_id = params_dict.get("tenant_id")
            except Exception as e:
                tenant_id = None

            # Check if describe is requested
            try:
                describe_param = params_dict.get("describe")
                if describe_param in ("true", "True"):
                    describe = True
            except Exception as e:
                describe = False
        else:
            describe = True

        if describe or tenant_id is None:
            response = {
                "describe": "This endpoint retrieves the impact score configuration for a virtual tenant, it requires a GET call with the following query parameters:",
                "resource_desc": "Get virtual tenant impact score configuration",
                "resource_spl_example": "| trackme url=/services/trackme/v2/vtenants/tenant_score_config mode=get params=\"{'tenant_id': 'mytenant'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Get vtenant account configuration via REST call
        url = f"{request_info.server_rest_uri}/servicesNS/nobody/trackme/trackme_vtenants/{tenant_id}"
        vtenant_data = {}
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
                vtenant_account_found = True
                vtenant_data = dict(vtenant_data_current)
            else:
                error_msg = f"failed to retrieve vtenant configuration, status_code={response.status_code}"
                logger.error(error_msg)

        except Exception as e:
            error_msg = f"failed to retrieve vtenant configuration, exception={str(e)}"
            logger.error(error_msg)

        if not vtenant_account_found:
            error_msg = f'tenant_id="{tenant_id}" cannot be found'
            logger.error(error_msg)
            return {
                "payload": {
                    "response": error_msg,
                },
                "status": 404,
            }

        # Extract all impact_score_* fields from the tenant account configuration
        # If a field is not present, use the default from vtenant_account_default
        score_config = {}
        for field_name in vtenant_account_default.keys():
            if field_name.startswith("impact_score_"):
                score_config[field_name] = vtenant_data.get(
                    field_name, vtenant_account_default[field_name]
                )

        response = {
            "tenant_id": tenant_id,
            "score_config": score_config,
        }

        return {"payload": response, "status": 200}

    #
    # Get tenant default delay configuration
    #

    def get_tenant_default_delay_config(self, request_info, **kwargs):
        """
        | trackme url=/services/trackme/v2/vtenants/tenant_default_delay_config mode=get params="{'tenant_id': 'mytenant'}"
        """

        tenant_id = None
        describe = False

        try:
            params_dict = request_info.raw_args["query_parameters"]
        except Exception as e:
            params_dict = None

        if params_dict is not None:
            tenant_id = params_dict.get("tenant_id")
            describe = params_dict.get("describe") in ("true", "True")
        else:
            describe = True

        if describe or tenant_id is None:
            response = {
                "describe": "This endpoint retrieves the default delay configuration for a virtual tenant.",
                "resource_desc": "Get virtual tenant default delay configuration",
                "resource_spl_example": "| trackme url=/services/trackme/v2/vtenants/tenant_default_delay_config mode=get params=\"{'tenant_id': 'mytenant'}\"",
                "options": [{"tenant_id": "REQUIRED. The tenant identifier"}],
            }
            return {"payload": response, "status": 200}

        url = f"{request_info.server_rest_uri}/servicesNS/nobody/trackme/trackme_vtenants/{tenant_id}"
        vtenant_data = {}
        vtenant_account_found = False

        try:
            response = requests.get(
                url,
                headers={"Authorization": f"Splunk {request_info.system_authtoken}"},
                verify=False,
                params={"output_mode": "json"},
                timeout=600,
            )
            if response.status_code in (200, 201, 204):
                vtenant_data_json = response.json()
                vtenant_data_current = vtenant_data_json["entry"][0]["content"]
                vtenant_account_found = True
                vtenant_data = dict(vtenant_data_current)
        except Exception as e:
            pass

        if not vtenant_account_found:
            return {"payload": {"response": f'tenant_id="{tenant_id}" cannot be found'}, "status": 404}

        def _get_comp(comp_prefix, field, default):
            prefixed = f"{comp_prefix}_{field}"
            val = vtenant_data.get(prefixed)
            if val is not None:
                return val
            val = vtenant_data.get(field)
            if val is not None:
                return val
            return vtenant_account_default.get(prefixed, vtenant_account_default.get(field, default))

        dsm_delay_config = {
            "default_delay_policy": _get_comp("dsm", "default_delay_policy", "static"),
            "default_delay_threshold_sec": _get_comp("dsm", "default_delay_threshold_sec", 3600),
            "variable_delay_default_slots": _get_comp("dsm", "variable_delay_default_slots", "{}"),
            "variable_delay_default": _get_comp("dsm", "variable_delay_default", "3600"),
        }
        dhm_delay_config = {
            "default_delay_policy": _get_comp("dhm", "default_delay_policy", "static"),
            "default_delay_threshold_sec": _get_comp("dhm", "default_delay_threshold_sec", 86400),
            "variable_delay_default_slots": _get_comp("dhm", "variable_delay_default_slots", "{}"),
            "variable_delay_default": _get_comp("dhm", "variable_delay_default", "86400"),
        }
        default_delay_config = {
            "adaptive_delay": vtenant_data.get("adaptive_delay", vtenant_account_default.get("adaptive_delay", 1)),
            "dsm": dsm_delay_config,
            "dhm": dhm_delay_config,
        }

        return {"payload": {"tenant_id": tenant_id, "default_delay_config": default_delay_config}, "status": 200}

    #
    # Get tenant CMDB integration configuration
    #

    def get_tenant_cmdb_config(self, request_info, **kwargs):
        """
        | trackme url=/services/trackme/v2/vtenants/tenant_cmdb_config mode=get params="{'tenant_id': 'mytenant', 'component': 'dsm'}"
        """

        # Declare main variables
        tenant_id = None
        component = None
        describe = False

        # Retrieve from query parameters
        try:
            params_dict = request_info.raw_args["query_parameters"]
        except Exception as e:
            params_dict = None

        if params_dict is not None:
            try:
                tenant_id = params_dict.get("tenant_id")
            except Exception as e:
                tenant_id = None

            try:
                component = params_dict.get("component")
            except Exception as e:
                component = None

            # Check if describe is requested
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = True

        if describe or tenant_id is None or component is None:
            response = {
                "describe": "This endpoint retrieves the CMDB integration configuration for a virtual tenant and component, it requires a GET call with the following query parameters:",
                "resource_desc": "Get virtual tenant CMDB integration configuration",
                "resource_spl_example": '| trackme url=/services/trackme/v2/vtenants/tenant_cmdb_config mode=get params="{ \'tenant_id\': \'mytenant\', \'component\': \'dsm\' }"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "REQUIRED. The component code (one of: dsm, dhm, mhm, flx, fqm, wlk)",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Validate component
        valid_components = {"dsm", "dhm", "mhm", "flx", "fqm", "wlk"}
        if component not in valid_components:
            return {
                "payload": {
                    "response": f'Invalid component "{component}". Must be one of: {", ".join(sorted(valid_components))}',
                },
                "status": 400,
            }

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Get vtenant account configuration via REST call
        url = f"{request_info.server_rest_uri}/servicesNS/nobody/trackme/trackme_vtenants/{tenant_id}"
        vtenant_data = {}
        vtenant_account_found = False

        try:
            response = requests.get(
                url,
                headers={"Authorization": f"Splunk {request_info.system_authtoken}"},
                verify=False,
                params={"output_mode": "json"},
                timeout=600,
            )
            if response.status_code in (200, 201, 204):
                vtenant_data_json = response.json()
                vtenant_data = dict(vtenant_data_json["entry"][0]["content"])
                vtenant_account_found = True
            else:
                error_msg = f"failed to retrieve vtenant configuration, status_code={response.status_code}"
                logger.error(error_msg)

        except Exception as e:
            error_msg = f"failed to retrieve vtenant configuration, exception={str(e)}"
            logger.error(error_msg)

        if not vtenant_account_found:
            return {
                "payload": {"response": f'tenant_id="{tenant_id}" cannot be found'},
                "status": 404,
            }

        # Get system-level CMDB configuration from trackme_settings.conf
        system_cmdb_key = f"splk_general_{component}_cmdb_search"
        system_cmdb_account_key = "splk_general_cmdb_account"
        system_cmdb_search = ""
        system_cmdb_account = "local"

        try:
            settings_url = f"{request_info.server_rest_uri}/servicesNS/nobody/trackme/trackme_settings/splk_general"
            settings_response = requests.get(
                settings_url,
                headers={"Authorization": f"Splunk {request_info.system_authtoken}"},
                verify=False,
                params={"output_mode": "json"},
                timeout=600,
            )
            if settings_response.status_code in (200, 201, 204):
                settings_json = settings_response.json()
                settings_content = settings_json["entry"][0]["content"]
                system_cmdb_search = settings_content.get(system_cmdb_key, "")
                system_cmdb_account = settings_content.get(system_cmdb_account_key, "local")
        except Exception as e:
            logger.warning(f"failed to read system-level CMDB settings, exception={str(e)}")

        # Extract tenant-level CMDB config
        cmdb_lookup = vtenant_data.get("cmdb_lookup", vtenant_account_default.get("cmdb_lookup", 1))
        raw_cmdb_account = vtenant_data.get("cmdb_account", "")
        cmdb_account = str(raw_cmdb_account).strip() if raw_cmdb_account is not None else ""
        raw_tenant_cmdb_search = vtenant_data.get(f"splk_{component}_cmdb_search", "")
        tenant_cmdb_search = str(raw_tenant_cmdb_search).strip() if raw_tenant_cmdb_search is not None else ""

        # Determine effective values using the same chain as execution code:
        # tenant override (if non-empty) → system default → "local"
        effective_cmdb_search = tenant_cmdb_search if tenant_cmdb_search and tenant_cmdb_search.strip() else system_cmdb_search
        effective_cmdb_account = cmdb_account if cmdb_account else system_cmdb_account
        config_source = "tenant" if tenant_cmdb_search and tenant_cmdb_search.strip() else "system"
        is_ootb_default = effective_cmdb_search.strip() in OOTB_CMDB_DEFAULTS if effective_cmdb_search else True

        response = {
            "tenant_id": tenant_id,
            "component": component,
            "cmdb_lookup": cmdb_lookup,
            "cmdb_account": cmdb_account,
            "tenant_cmdb_search": tenant_cmdb_search,
            "system_cmdb_search": system_cmdb_search,
            "system_cmdb_account": system_cmdb_account,
            "effective_cmdb_search": effective_cmdb_search,
            "effective_cmdb_account": effective_cmdb_account,
            "config_source": config_source,
            "is_ootb_default": is_ootb_default,
        }

        return {"payload": response, "status": 200}
