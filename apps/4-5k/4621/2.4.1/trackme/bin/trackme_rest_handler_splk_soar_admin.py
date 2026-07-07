#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_soar_admin.py"
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
import traceback
from ast import literal_eval
import time
import random

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_soar_admin",
    "trackme_rest_api_splk_soar_admin.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_getloglevel, trackme_parse_describe_flag

# import trackme libs
from trackme_libs_soar import (
    trackme_get_soar_accounts,
    trackme_get_soar_account,
)

# import Splunk SOAR bin, only if the app is available
# if os.path.isdir(os.path.join(splunkhome, 'etc', 'apps', 'splunk_app_soar', 'bin')):
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", "trackme", "lib", "splunk_soar")
)
from trackme_soar import SOARClient


def handle_comma_separated_values(values):
    return [value.strip() for value in values.split(",")]


class TrackMeHandlerSplkSoarAdmin_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkSoarAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )
    
    def _validate_asset_update_response(self, asset_config_update, asset, asset_id, mode="live"):
        """
        Helper method to validate asset update response structure.
        
        Args:
            asset_config_update: requests.Response object from asset update API call
            asset: Asset name for logging
            asset_id: Asset ID for logging
            mode: Operation mode ("live" or "readonly") for logging
        
        Returns:
            dict: Parsed and validated JSON response
        
        Raises:
            ValueError: If response structure is invalid
            json.JSONDecodeError: If JSON parsing fails
            TypeError: If response type is unexpected
        """
        try:
            asset_config_update_json = asset_config_update.json()
            if not isinstance(asset_config_update_json, dict):
                raise ValueError(
                    f'Unexpected update response type: {type(asset_config_update_json).__name__}'
                )
            return asset_config_update_json
        except (json.JSONDecodeError, ValueError, TypeError) as json_err:
            mode_prefix = "**read only mode** " if mode == "readonly" else ""
            error_msg = (
                f'asset={asset}, id={asset_id}, {mode_prefix}failed to parse update response, '
                f'exception="{str(json_err)}", status_code={asset_config_update.status_code}, '
                f'response_text="{asset_config_update.text[:200]}"'
            )
            logger.error(error_msg)
            raise  # Re-raise to let caller handle error counting and messaging

    def get_resource_group_desc_splk_soar(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_soar/admin",
            "resource_group_desc": "Endpoints specific to Splunk SOAR monitoring, admin operations)",
        }

        return {"payload": response, "status": 200}

    # Get a SOAR API endpoint
    def post_soar_post_endpoint(self, request_info, **kwargs):
        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                soar_server = resp_dict.get("soar_server", None)
                data = resp_dict["data"]
                if not isinstance(data, dict):
                    try:
                        # Try parsing as standard JSON (with double quotes)
                        data = json.loads(data)
                    except ValueError:
                        # If it fails, try parsing with ast.literal_eval (supports single quotes)
                        data = literal_eval(data)

                # optional, params can be added to data by the upstream call, if defined, assign to params and remove from data
                if "params" in data:
                    params = data["params"]
                    del data["params"]
                else:
                    params = None

                endpoint = resp_dict["endpoint"]

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint runs a POST call a SOAR API endpoint, it requires a POST call with the following information:",
                "resource_desc": "Post to a Splunk SOAR API endpoint",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_soar/admin/soar_post_endpoint\" mode=\"post\" body=\"{'soar_server': 'soar_production', 'endpoint': 'asset/1', 'data': '{\"test\": \"true\"}'}\"",
                "options": [
                    {
                        "soar_server": "The SOAR server account as defined in the Splunk App for SOAR, if unspecified or set to *, the first server in the Splunk application for SOAR configuration will be used",
                        "endpoint": "The SOAR API endpoint",
                        "data": "JSON formatted data for the POST call, to include additional params to POST call, include a param field containing the params object",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        else:
            # set loglevel
            loglevel = trackme_getloglevel(
                request_info.system_authtoken, request_info.server_rest_port
            )
            logger.setLevel(loglevel)

            # init
            response = {}

            try:
                # if not specified, attempt to retrieve and use the first configured soar_server
                if not soar_server or soar_server == "*":
                    # get all servers configured
                    soar_servers = trackme_get_soar_accounts(request_info)

                    if soar_servers:
                        soar_server = soar_servers[0]

                    else:
                        msg = "There are no soar_server configured yet in the splunk_app_soar, perform the SOAR configuration first."
                        logger.error(msg)
                        return {
                            "payload": {
                                "action": "failure",
                                "response": msg,
                            },
                            "status": 500,
                        }

                # get info and creds with least privileges approach
                try:
                    soar_account_info = trackme_get_soar_account(
                        request_info, soar_server
                    )

                except Exception as e:
                    msg = f'An exception was encountered while fetching SOAR server configuration, exception="{str(e)}"'
                    logger.error(msg)
                    return {
                        "payload": {
                            "action": "failure",
                            "response": msg,
                        },
                        "status": 500,
                    }

                base_server = soar_account_info["server"]
                soar_token = soar_account_info["password"]

                # get client
                soar_client = SOARClient(base_server, soar_token)

                try:
                    # POST requests may return paginated responses, but subsequent pages use GET
                    # This is a special case, so we handle it manually
                    res = soar_client.make_request(
                        endpoint, "POST", data, extra_params=params, timeout=60, max_retries=3
                    )
                    res_json = res.json()

                    # Handle pagination - POST first page, GET for subsequent pages
                    if isinstance(res_json, dict) and "count" in res_json and "num_pages" in res_json:
                        no_pages = int(res_json.get("num_pages", 1))
                        response = []
                        
                        # First page from POST response - validate structure
                        if "data" in res_json and isinstance(res_json["data"], list):
                            for entry in res_json["data"]:
                                response.append(entry)
                        else:
                            # Missing or invalid "data" key - raise error like get_paginated_response does
                            error_msg = (
                                f'Unexpected paginated POST response format: missing or invalid "data" key, '
                                f'endpoint="{endpoint}", response keys: {list(res_json.keys())}'
                            )
                            logger.error(error_msg)
                            raise ValueError(error_msg)
                        
                        # Subsequent pages use GET (special SOAR API behavior)
                        for page_number in range(1, no_pages):
                            res_page = soar_client.make_request(
                                endpoint, "GET", None, page=page_number, 
                                extra_params=params, timeout=60, max_retries=3
                            )
                            res_page_json = res_page.json()
                            if isinstance(res_page_json, dict) and "data" in res_page_json and isinstance(res_page_json["data"], list):
                                for entry in res_page_json["data"]:
                                    response.append(entry)
                            else:
                                # Missing or invalid "data" key in subsequent page
                                error_msg = (
                                    f'Unexpected paginated GET response format on page {page_number}: '
                                    f'missing or invalid "data" key, endpoint="{endpoint}", '
                                    f'response keys: {list(res_page_json.keys()) if isinstance(res_page_json, dict) else "N/A"}'
                                )
                                logger.error(error_msg)
                                raise ValueError(error_msg)
                    else:
                        # Non-paginated response - preserve original format for soar_post compatibility
                        # Don't wrap dicts in lists as it breaks downstream Splunk searches
                        # Preserve all types (dict, list, string, etc.) as-is
                        response = res_json
                except Exception as e:
                    error_msg = (
                        f'Error processing SOAR POST response, endpoint="{endpoint}", '
                        f'exception="{str(e)}"'
                    )
                    logger.error(error_msg)
                    raise Exception(error_msg)

                entity_info = {
                    "response": response,
                }

                # render response
                return {"payload": entity_info, "status": 200}

            except Exception as e:
                # render response with full context
                error_trace = traceback.format_exc()
                msg = (
                    f'An exception was encountered while processing SOAR POST request, '
                    f'endpoint="{endpoint}", soar_server="{soar_server if "soar_server" in locals() else "unknown"}", '
                    f'exception="{str(e)}", traceback="{error_trace[-500:]}"'
                )
                logger.error(msg)
                return {
                    "payload": {
                        "action": "failure",
                        "response": msg,
                        "endpoint": endpoint if "endpoint" in locals() else "unknown",
                    },
                    "status": 500,
                }

    # Run SOAR assets connectivity test
    def post_soar_test_assets(self, request_info, **kwargs):
        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                soar_server = resp_dict.get("soar_server", None)
                active_check = resp_dict.get("active_check", "True")
                if active_check and active_check in ("true", "True"):
                    active_check = True
                elif active_check and active_check in ("false", "False"):
                    active_check = False
                assets_allow_list = resp_dict.get("assets_allow_list", None)
                if assets_allow_list:
                    if assets_allow_list == "None":
                        assets_allow_list = None
                    else:
                        if not isinstance(assets_allow_list, list):
                            assets_allow_list = assets_allow_list.split(",")
                assets_block_list = resp_dict.get("assets_block_list", None)
                if assets_block_list:
                    if assets_block_list == "None":
                        assets_block_list = None
                    else:
                        if not isinstance(assets_block_list, list):
                            assets_block_list = assets_block_list.split(",")

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint initiates assets connectivity check, loops through the results, verifies and renders the assets connectivity status, it requires a POST call with the following information:",
                "resource_desc": "Initiates the SOAR asset connectivity test, verifies and renders the assets status",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_soar/admin/soar_test_assets\" mode=\"post\" body=\"{'soar_server': 'soar_production', 'assets_block_list': 'internal_smtp,dev_splunk}\"",
                "options": [
                    {
                        "soar_server": "The SOAR server account as defined in the Splunk App for SOAR, if unspecified or set to *, the first server in the Splunk application for SOAR configuration will be used",
                        "active_check": "Performs an active check by requesting the test connectivity for each eligible asset running the associated POST call to the asset SOAR API endpoint, defaults to True, valid options: False|True. Active check requires the edit asset permission for the automation user, you can also rely on SOAR and disable the active check with False, SOAR runs a daily check so it can take up to 24 hours to detect an application connectivity failure if active_check is set to False.",
                        "assets_allow_list": "Optional, a comma separated list of SOAR assets names to be verified, assets not in this list will be ignored",
                        "assets_block_list": "Optional, a comma separated list of SOAR assets names to be verified, assets in this list will be ignored",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        else:
            # set loglevel
            loglevel = trackme_getloglevel(
                request_info.system_authtoken, request_info.server_rest_port
            )
            logger.setLevel(loglevel)

            # perf counter
            start_time = time.time()

            try:
                # if not specified, attempt to retrieve and use the first configured soar_server
                if not soar_server or soar_server == "*":
                    # get all servers configured
                    soar_servers = trackme_get_soar_accounts(request_info)

                    if soar_servers:
                        soar_server = soar_servers[0]

                    else:
                        msg = "There are no soar_server configured yet in the splunk_app_soar, perform the SOAR configuration first."
                        logger.error(msg)
                        return {
                            "payload": {
                                "action": "failure",
                                "response": msg,
                            },
                            "status": 500,
                        }

                # get info and creds with least privileges approach
                try:
                    soar_account_info = trackme_get_soar_account(
                        request_info, soar_server
                    )

                except Exception as e:
                    msg = f'An exception was encountered while fetching SOAR server configuration, exception="{str(e)}"'
                    logger.error(msg)
                    return {
                        "payload": {
                            "action": "failure",
                            "response": msg,
                        },
                        "status": 500,
                    }

                base_server = soar_account_info["server"]
                soar_token = soar_account_info["password"]

                # get client
                soar_client = SOARClient(base_server, soar_token)

                #
                # Get all assets
                #

                logger.info(
                    f'starting get asset, requesting endpoint="/rest/asset", soar_server="{soar_server}"'
                )

                endpoint = "asset"
                res = soar_client.make_request(endpoint, "GET", {"page_size": 100})
                res_json = res.json()

                # final response
                all_assets_raw_list = []

                try:
                    if "count" in res_json and "num_pages" in res_json:
                        no_pages = int(res_json.get("num_pages", 1))

                        if "data" in res_json:
                            for entry in res_json["data"]:
                                all_assets_raw_list.append(entry)
                        else:
                            logger.error(f"Unexpected response format: {res_json}")
                            raise ValueError("Missing 'data' key in response.")

                        for page_number in range(
                            1, no_pages
                        ):  # start from page 1 (which is actually the second page)
                            res = soar_client.make_request(
                                "asset", "GET", None, page=page_number
                            )
                            res_json = res.json()
                            if "data" in res_json:
                                for entry in res_json["data"]:
                                    all_assets_raw_list.append(entry)

                    elif type(res_json) == list:
                        for el in res_json:
                            all_assets_raw_list.append(el)
                    else:
                        all_assets_raw_list = res_json

                except Exception as e:
                    logger.error(f'error in processing response, exception="{str(e)}"')

                # loop
                all_assets_list = []
                all_assets_id_list = []

                for asset in all_assets_raw_list:
                    # handle allow and block lists
                    asset_proceed = False
                    asset_name = asset.get("name")
                    asset_id = asset.get("id")

                    if assets_allow_list:
                        if asset_name in assets_allow_list:
                            asset_proceed = True
                    else:
                        asset_proceed = True

                    if assets_block_list:
                        if asset_name in assets_block_list:
                            asset_proceed = False

                    # this is an exception
                    if asset_name in ("rest - events"):
                        asset_proceed = False

                    if asset_proceed:
                        all_assets_list.append(asset)
                        all_assets_id_list.append(asset_id)

                logger.info(
                    f'terminated requesting endpoint="/rest/asset", server="{soar_server}", {len(all_assets_list)} eligible asset(s) were found'
                )

                #
                # For each asset, loop and call the test endpoint
                #

                assets_test_requested = {}
                assets_test_list = []

                if active_check:
                    logger.info(
                        f'starting requesting connectivity test, soar_server="{soar_server}"'
                    )
                else:
                    logger.info(
                        f'active_check={active_check}, active connectivity test will not be requested, soar_server="{soar_server}"'
                    )

                for asset_dict in all_assets_list:
                    asset_name = asset_dict.get("name")
                    asset_id = asset_dict.get("id")
                    asset_type = asset_dict.get("type")

                    if not active_check:
                        assets_test_requested[asset_id] = {
                            "name": asset_name,
                            "id": asset_id,
                            "type": asset_type,
                            "test_request": "success",
                            "response": "active check was disabled, simply adding the asset for status verification",
                            "mtime": time.time(),
                        }
                        assets_test_list.append(asset_name)

                    else:
                        try:
                            logger.info(
                                f'requested connectivity check for asset={asset_name}, id={asset_id}, soar_server="{soar_server}"'
                            )

                            res = soar_client.make_request(
                                f"asset/{asset_id}", "POST", {"test": "true"}
                            )
                            res_json = res.json()

                            assets_test_requested[asset_id] = {
                                "name": asset_name,
                                "id": asset_id,
                                "type": asset_type,
                                "test_request": "success",
                                "response": res_json,
                                "mtime": time.time(),
                            }
                            assets_test_list.append(asset_name)
                            logger.info(
                                f'connectivity check successfully requested, asset={asset_name}, id={asset_id}, respoonse={json.dumps(res_json)}, soar_server="{soar_server}"'
                            )

                        except Exception as e:
                            assets_test_requested[asset_id] = {
                                "name": asset_name,
                                "id": asset_id,
                                "type": asset_type,
                                "test_request": "failure",
                                "response": str(e),
                                "mtime": time.time(),
                            }
                            assets_test_list.append(asset_name)
                            logger.error(
                                f'connectivity check request has failed, asset={asset_name}, id={asset_id}, exception={str(e)}, soar_server="{soar_server}"'
                            )

                logger.info(
                    f'terminated requesting connectivity test, soar_server="{soar_server}", {len(assets_test_requested)} assets successfully responded to connectivity check request'
                )
                logger.debug(
                    f"assets_test_requested={json.dumps(assets_test_requested, indent=2)}"
                )

                #
                # app_status: retrieve the app_status and merge
                #

                logger.info(
                    f'starting refresh get asset, requesting endpoint="/rest/app_status", soar_server="{soar_server}"'
                )

                count_assets_green = 0
                count_assets_red = 0

                res = soar_client.make_request("app_status", "GET", None)
                res_json = res.json()

                # final response
                refreshed_assets_list = []

                if "count" in res_json and "num_pages" in res_json:
                    no_pages = int(res_json.get("num_pages", 1))
                    for entry in res_json["data"]:
                        refreshed_assets_list.append(entry)
                    for page_number in range(
                        1, no_pages
                    ):  # start from page 1 (which is actually the second page)
                        res = soar_client.make_request(
                            "app_status", "GET", None, page=page_number
                        )
                        res_json = res.json()
                        for entry in res_json["data"]:
                            refreshed_assets_list.append(entry)
                elif type(res_json) == list:
                    for el in res_json:
                        refreshed_assets_list.append(el)
                else:
                    refreshed_assets_list = res_json

                response = []

                # loop and check
                for asset in refreshed_assets_list:
                    logger.debug(f"asset={json.dumps(asset, indent=2)}")

                    result_asset_id = asset.get(
                        "asset"
                    )  # caution the asset id is called asset in this endpoint! and id refers to the id of the check

                    if result_asset_id in all_assets_id_list:
                        result_asset_name = assets_test_requested[result_asset_id].get(
                            "name"
                        )

                        # render if managed in our list of assets
                        if result_asset_name in assets_test_list:
                            result_asset_type = assets_test_requested[
                                result_asset_id
                            ].get("type")
                            result_asset_message = asset.get("message")
                            result_asset_status = asset.get("status")
                            result_test_request = assets_test_requested[
                                result_asset_id
                            ].get("test_request")
                            result_test_response = assets_test_requested[
                                result_asset_id
                            ].get("response")

                            if result_test_request != "success":
                                result_asset_status = "failure"
                                result_asset_message = f"failed to request connectivity check with response={result_test_response}"
                                count_assets_red += 1
                            else:
                                count_assets_green += 1

                            mtime_epoch = assets_test_requested[result_asset_id].get(
                                "mtime"
                            )
                            mtime_human = time.strftime(
                                "%d/%m/%Y %H:%M:%S", time.localtime(mtime_epoch)
                            )

                            # add
                            response.append(
                                {
                                    "id": result_asset_id,
                                    "name": result_asset_name,
                                    "type": result_asset_type,
                                    "message": result_asset_message,
                                    "status": result_asset_status,
                                    "mtime_epoch": mtime_epoch,
                                    "mtime_human": mtime_human,
                                }
                            )

                logger.debug(f"response={response}")

                run_time = round(time.time() - start_time, 3)
                logger.info(
                    f'terminated assets test connectivity, soar_server="{soar_server}", count_assets_green={count_assets_green}, count_assets_red={count_assets_red}, run_time={run_time}'
                )

                # render response
                return {"payload": {"response": response}, "status": 200}

            except Exception as e:
                # render response with full context
                error_trace = traceback.format_exc()
                msg = (
                    f'An exception was encountered while processing SOAR assets connectivity test, '
                    f'soar_server="{soar_server if "soar_server" in locals() else "unknown"}", '
                    f'active_check="{active_check if "active_check" in locals() else "unknown"}", '
                    f'exception="{str(e)}", traceback="{error_trace[-500:]}"'
                )
                logger.error(msg)
                return {
                    "payload": {
                        "action": "failure",
                        "response": msg,
                        "soar_server": soar_server if "soar_server" in locals() else "unknown",
                    },
                    "status": 500,
                }

    # Monitors a given Automation Broker readiness status, if the broker is not active, updates all assets to the specified target
    # automation broker, or if not specified to the next available broker
    def post_soar_automation_broker_manage(self, request_info, **kwargs):

        # Function to remove fields with values starting with "salt:", these are SOAR secrets
        def remove_salt_fields(data):
            if isinstance(data, dict):
                cleaned_data = {}
                for k, v in data.items():
                    if isinstance(v, str) and v.startswith("salt:"):
                        continue
                    cleaned_data[k] = remove_salt_fields(v)
                return cleaned_data
            elif isinstance(data, list):
                return [remove_salt_fields(item) for item in data]
            else:
                return data

        # Function to remove fields which are included in the forbidden fields list
        def remove_forbidden_fields(data, forbidden_fields):
            if isinstance(data, dict):
                cleaned_data = {}
                for k, v in data.items():
                    if k in forbidden_fields:
                        continue
                    cleaned_data[k] = remove_forbidden_fields(v, forbidden_fields)
                return cleaned_data
            elif isinstance(data, list):
                return [
                    remove_forbidden_fields(item, forbidden_fields) for item in data
                ]
            else:
                return data

        # Per-run cache of app-id -> set of secret field names (data_type == 'password').
        # Resolves the schema once per app, reused across every asset bound to that app.
        app_password_fields_cache = {}

        def get_app_password_fields(soar_client_local, app_id):
            """Return the set of configuration field names whose data_type is 'password'
            for the given SOAR app. Returns an empty set on any failure (fail-open: a
            missing manifest must never block broker failover).
            """
            if app_id is None:
                return set()
            if app_id in app_password_fields_cache:
                return app_password_fields_cache[app_id]

            password_fields = set()
            try:
                res = soar_client_local.make_request(
                    f"app/{app_id}", "GET", None, timeout=60
                )
                app_meta = res.json()
                if isinstance(app_meta, dict):
                    configuration = app_meta.get("configuration") or {}
                    if isinstance(configuration, dict):
                        for field_name, field_def in configuration.items():
                            if (
                                isinstance(field_def, dict)
                                and field_def.get("data_type") == "password"
                            ):
                                password_fields.add(field_name)
            except Exception as e:
                logger.warning(
                    f'failed to fetch SOAR app manifest for app_id={app_id}, falling back to static forbidden list, exception="{str(e)}"'
                )

            app_password_fields_cache[app_id] = password_fields
            return password_fields

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                soar_server = resp_dict.get("soar_server", None)
                mode = resp_dict.get("mode", "live")
                if mode:
                    if mode not in ("simulation", "readonly", "live"):
                        msg = "Invalid mode, valid options are: readonly | live."
                        logger.error(msg)
                        return {
                            "payload": {
                                "action": "failure",
                                "response": msg,
                            },
                            "status": 500,
                        }

                # active/active pair scenario

                #
                # deprecation note: the active1/active2 scenario is deprecated, use the pool members instead
                # for backward compatibility we still support the active1/active2 scenario by adding these as the members of the pool
                #

                automation_active1_broker_name = resp_dict.get(
                    "automation_active1_broker_name", None
                )
                if automation_active1_broker_name:
                    if automation_active1_broker_name in "none, None":
                        automation_active1_broker_name = None
                automation_active2_broker_name = resp_dict.get(
                    "automation_active2_broker_name", None
                )
                if automation_active2_broker_name:
                    if automation_active2_broker_name in "none, None":
                        automation_active2_broker_name = None

                # brokers pool scenario
                automation_brokers_pool_members = resp_dict.get(
                    "automation_brokers_pool_members", None
                )
                # turn into list from expected comma separated string
                if automation_brokers_pool_members:
                    if automation_brokers_pool_members == "None":
                        automation_brokers_pool_members = None
                    else:
                        if not isinstance(automation_brokers_pool_members, list):
                            automation_brokers_pool_members = (
                                handle_comma_separated_values(
                                    automation_brokers_pool_members
                                )
                            )
                else:
                    automation_brokers_pool_members = []

                # if automation_active1_broker_name and automation_active2_broker_name are set (deprecated), add to the pool
                if automation_active1_broker_name and automation_active2_broker_name:

                    if (
                        automation_active1_broker_name
                        not in automation_brokers_pool_members
                    ):
                        automation_brokers_pool_members.append(
                            automation_active1_broker_name
                        )
                    if (
                        automation_active2_broker_name
                        not in automation_brokers_pool_members
                    ):
                        automation_brokers_pool_members.append(
                            automation_active2_broker_name
                        )

                # assets_update_forbidden_fields — default list of credential field names
                # commonly used across SOAR apps. Acts as the static safety net behind the
                # schema-based detection below, and as the sole filter when the schema
                # lookup is disabled or fails.
                default_forbidden_fields = [
                    "apikey",
                    "api_key",
                    "api_secret",
                    "password",
                    "passphrase",
                    "auth_token",
                    "access_token",
                    "refresh_token",
                    "bearer_token",
                    "personal_access_token",
                    "token",
                    "client_secret",
                    "secret",
                    "secret_key",
                    "private_key",
                ]
                default_forbidden_fields_csv = ",".join(default_forbidden_fields)
                assets_update_forbidden_fields = resp_dict.get(
                    "assets_update_forbidden_fields",
                    default_forbidden_fields_csv,
                )
                # if not a list, convert to list from CSV
                if not isinstance(assets_update_forbidden_fields, list):
                    assets_update_forbidden_fields = handle_comma_separated_values(
                        assets_update_forbidden_fields
                    )

                # assets_update_forbidden_fields_extra: additive list — appended on top of
                # whatever assets_update_forbidden_fields resolves to. Lets operators add
                # one custom field name without re-enumerating the defaults.
                assets_update_forbidden_fields_extra = resp_dict.get(
                    "assets_update_forbidden_fields_extra", None
                )
                if assets_update_forbidden_fields_extra:
                    if not isinstance(assets_update_forbidden_fields_extra, list):
                        assets_update_forbidden_fields_extra = (
                            handle_comma_separated_values(
                                assets_update_forbidden_fields_extra
                            )
                        )
                    for extra_field in assets_update_forbidden_fields_extra:
                        if extra_field and extra_field not in assets_update_forbidden_fields:
                            assets_update_forbidden_fields.append(extra_field)

                # enable_app_schema_secret_detection: when true (default), look up each
                # asset's app manifest and add any field with data_type=password to the
                # forbidden list for that asset. Cached per app_id for the run.
                enable_app_schema_secret_detection = resp_dict.get(
                    "enable_app_schema_secret_detection", True
                )
                if isinstance(enable_app_schema_secret_detection, str):
                    enable_app_schema_secret_detection = (
                        enable_app_schema_secret_detection.strip().lower()
                        in ("true", "1", "yes")
                    )

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint actively monitors the status of autommation brokers, if an automation broker is detected as inactive, assets related to it are updated to use the next automation broker available or any of the active/failover active member if specified, it requires a POST call with the following information:",
                "resource_desc": "Monitor and detect Automation Brokers failures for high availability purposes, you can specify a pool of members to be used as a failover group, if an asset is configured to use a broker member from the pool which is suffering from an issue, the next available broker from the pool will be used to update the asset, if the pool is exhausted, the asset will be left unchanged. If a pool is not configured, the next available broker will be used to update the asset.",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_soar/admin/soar_automation_broker_manage\" mode=\"post\" body=\"{'soar_server': 'soar_production', 'automation_brokers_pool_members': 'AB-UK-01,AB-UK-02'}\"",
                "options": [
                    {
                        "soar_server": "The SOAR server account as defined in the Splunk App for SOAR, if unspecified or set to *, the first server in the Splunk application for SOAR configuration will be used",
                        "automation_brokers_pool_members": "Optional, a comma separated list of automation brokers to be used as a pool of members, if specified, the pool members will be used to update the assets, when an asset configured to use a broker member from the pool which is suffering from an issue, the next available broker from the pool will be used to update the asset, if the pool is exhausted, the asset will be left unchanged, if the pool is not specified, the next available broker will be used to update the asset.",
                        "automation_active1_broker_name": "Deprecated do not use (replaced by automation_brokers_pool_members), first active automation broker, specify a couple of brokers active1/active2, both must be specified or none should specified, this targets both active1/active2 brokers and will switch Assets configuration depending on the broker status.",
                        "automation_active2_broker_name": "Deprecated do not use (replaced by automation_brokers_pool_members), second active automation broker, specify a couple of brokers active1/active2, both must be specified or none should specified, this targets both active1/active2 brokers and will switch Assets configuration depending on the broker status.",
                        "mode": "Optional, the run mode, valid options are readonly | live, in readonly mode the Asset is not updated and only the message of the action to be performed is registered, in live assets are updated as needed, defaults to live",
                        "assets_update_forbidden_fields": "Optional, a comma separated list of field names to exclude from the POST json data when updating assets. When provided, this REPLACES the built-in default list. Built-in default list: apikey, api_key, api_secret, password, passphrase, auth_token, access_token, refresh_token, bearer_token, personal_access_token, token, client_secret, secret, secret_key, private_key. In addition, fields whose value is a salted secret (prefixed with 'salt:') are always stripped automatically.",
                        "assets_update_forbidden_fields_extra": "Optional, a comma separated list of field names that ADD to the default forbidden list (or to the list provided via assets_update_forbidden_fields). Use this to protect a custom credential field name without re-enumerating the defaults.",
                        "enable_app_schema_secret_detection": "Optional, boolean (defaults to true). When true, the endpoint looks up each asset's SOAR app manifest via /rest/app/<id> and treats any field declared with data_type='password' as a forbidden field for that asset. App manifests are fetched at most once per run and cached by app_id. If a manifest fetch fails, the failover proceeds using the static forbidden list and emits a warning. Set to false to skip the schema lookup entirely.",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        else:
            # set loglevel
            loglevel = trackme_getloglevel(
                request_info.system_authtoken, request_info.server_rest_port
            )
            logger.setLevel(loglevel)

            # perf counter
            start_time = time.time()

            try:
                # if not specified, attempt to retrieve and use the first configured soar_server
                if not soar_server or soar_server == "*":
                    # get all servers configured
                    soar_servers = trackme_get_soar_accounts(request_info)

                    if soar_servers:
                        soar_server = soar_servers[0]

                    else:
                        msg = "There are no soar_server configured yet in the splunk_app_soar, perform the SOAR configuration first."
                        logger.error(msg)
                        return {
                            "payload": {
                                "action": "failure",
                                "response": msg,
                            },
                            "status": 500,
                        }

                # get info and creds with least privileges approach
                try:
                    soar_account_info = trackme_get_soar_account(
                        request_info, soar_server
                    )

                except Exception as e:
                    msg = f'An exception was encountered while fetching SOAR server configuration, exception="{str(e)}"'
                    logger.error(msg)
                    return {
                        "payload": {
                            "action": "failure",
                            "response": msg,
                        },
                        "status": 500,
                    }

                base_server = soar_account_info["server"]
                soar_token = soar_account_info["password"]

                # get client
                soar_client = SOARClient(base_server, soar_token)

                #
                # Get all Automation Brokers
                #

                logger.info(
                    f'starting get Automation Brokers, requesting endpoint="/rest/automation_proxy", soar_server="{soar_server}"'
                )

                endpoint = "automation_proxy"
                extra_params = {"pretty": True, "sort": "create_time", "order": "desc"}
                try:
                    # Use helper method for paginated responses
                    all_ab_raw_list = soar_client.get_paginated_response(
                        endpoint, method="GET", data=None, extra_params=extra_params,
                        timeout=60, max_retries=3, page_size=100
                    )
                except Exception as e:
                    error_msg = (
                        f'Failed to retrieve automation brokers, endpoint="{endpoint}", '
                        f'exception="{str(e)}"'
                    )
                    logger.error(error_msg)
                    raise Exception(error_msg)

                # loop
                all_ab_list = []
                all_ab_id_list = []
                all_ab_dict_by_id = {}
                all_ab_dict_by_name = {}

                active_ab_list = []  # the list of active brokers
                inactive_ab_list = []  # the list of inactive brokers
                selectable_ab_list = (
                    []
                )  # the list of brokers we filter on, defaults to all unless automation_brokers_pool_members is specified
                selectable_ab_id_list = []  # the list of ids

                for ab in all_ab_raw_list:

                    # Get its id
                    ab_id = ab.get("id")

                    # Get its name
                    ab_name = ab.get("name")

                    #
                    # selectable
                    #

                    # if the pool is specified, add all members to the selectable list
                    # otherwise, add the broker if it is part of the pool
                    if automation_brokers_pool_members:
                        if ab_name in automation_brokers_pool_members:
                            selectable_ab_list.append(ab_name)
                            selectable_ab_id_list.append(ab_id)
                    else:
                        selectable_ab_list.append(ab_name)
                        selectable_ab_id_list.append(ab_id)

                    # Only manage if the broker is our scope
                    if ab_id in selectable_ab_id_list:

                        # create a dict of the brokers by name with their id and status
                        all_ab_list.append(ab_name)  # appends to our list of names
                        all_ab_id_list.append(ab_id)  # appends to our list ids
                        ab_last_seen_status = ab.get(
                            "_pretty_last_seen_status", {}
                        ).get("combined_status", "inactive")
                        ab_version = ab.get("version")
                        ab_rest_healthcheck_time = ab.get("rest_healthcheck_time")
                        ab_ws_healthcheck_time = ab.get("ws_healthcheck_time")

                        # add to our lists
                        if ab_last_seen_status == "active":
                            active_ab_list.append(ab_id)
                        elif ab_last_seen_status == "inactive":
                            inactive_ab_list.append(ab_id)

                        # add dict by id
                        all_ab_dict_by_id[ab_id] = {
                            "name": ab_name,
                            "id": ab_id,
                            "last_seen_status": ab_last_seen_status,
                            "last_seen_status_detailed": ab.get(
                                "_pretty_last_seen_status"
                            ),
                            "version": ab_version,
                            "create_time": ab.get("create_time"),
                            "create_time_human": ab.get("_pretty_create_time"),
                            "update_time": ab.get("update_time"),
                            "update_time_human": ab.get("_pretty_update_time"),
                            "keys_rotated_time": ab.get("keys_rotated_time"),
                            "keys_rotated_time_human": ab.get(
                                "_pretty_keys_rotated_time"
                            ),
                            "rest_healthcheck_time": ab_rest_healthcheck_time,
                            "rest_healthcheck_time_human": ab.get(
                                "_pretty_rest_healthcheck_time"
                            ),
                            "ws_healthcheck_time": ab_ws_healthcheck_time,
                            "ws_healthcheck_time_human": ab.get(
                                "_pretty_ws_healthcheck_time"
                            ),
                            "last_started": ab.get("last_started"),
                            "last_started_human": ab.get("_pretty_last_started"),
                            "concurrency_limit": ab.get("concurrency_limit"),
                            "assets": ab.get("_pretty_assets"),
                            "owner": ab.get("owner"),
                            "owner_pretty": ab.get("_pretty_owner"),
                            "service_account": ab.get("service_account"),
                            "service_account_pretty": ab.get("_pretty_service_account"),
                        }

                        # add dict by name
                        all_ab_dict_by_name[ab_name] = {
                            "name": ab_name,
                            "id": ab_id,
                            "last_seen_status": ab_last_seen_status,
                            "version": ab_version,
                        }

                logger.info(
                    f'terminated requesting endpoint="/rest/automation_proxy", server="{soar_server}", {len(all_ab_raw_list)} eligible Automation Broker(s) were found'
                )

                #
                # Now get all assets, create a dict of assets associated with each Automation Broker
                #

                #
                # Get all assets
                #

                logger.info(
                    f'starting get asset, requesting endpoint="/rest/asset", soar_server="{soar_server}"'
                )

                endpoint = "asset"
                try:
                    # Use helper method for paginated responses
                    all_assets_raw_list = soar_client.get_paginated_response(
                        endpoint, method="GET", data={"page_size": 100}, extra_params=None,
                        timeout=60, max_retries=3, page_size=100
                    )
                except Exception as e:
                    error_msg = (
                        f'Error processing asset response, endpoint="{endpoint}", '
                        f'exception="{str(e)}"'
                    )
                    logger.error(error_msg)
                    raise Exception(error_msg)

                # loop
                all_assets_list = []
                all_assets_id_list = []
                all_assets_dict = {}

                for asset in all_assets_raw_list:
                    if not isinstance(asset, dict):
                        logger.warning(
                            f'Skipping invalid asset entry, expected dict but got {type(asset).__name__}'
                        )
                        continue
                    asset_name = asset.get("name")
                    asset_id = asset.get("id")
                    asset_automation_broker = asset.get("automation_broker", None)

                    # if associated with an automation broker and in the scope, add to our dict
                    if (
                        asset_automation_broker
                        and asset_automation_broker in all_ab_dict_by_id
                    ):
                        all_assets_list.append(asset)
                        all_assets_id_list.append(asset_id)
                        all_assets_dict[asset_name] = {
                            "name": asset_name,
                            "id": asset_id,
                            "automation_broker": asset_automation_broker,
                        }

                logger.info(
                    f'terminated requesting endpoint="/rest/asset", server="{soar_server}", {len(all_assets_dict)} eligible asset(s) using an automation broker were found'
                )

                #
                # check and act: loop through assets per automation broker, verify the associated broker status, if inactive, update the asset
                #

                # render as list, one record per automation broker
                final_response = []

                for ab in sorted(all_ab_dict_by_id.keys()):

                    ab_name = all_ab_dict_by_id[ab]["name"]

                    # if in selectable_ab_list
                    if ab_name in selectable_ab_list:

                        update_assets = []
                        update_messages = []
                        update_error_count = 0
                        associated_assets = []

                        ab_response = {}

                        if (
                            all_ab_dict_by_id[ab]["name"] in selectable_ab_list
                        ):  # if we filter on a specific broker
                            for asset in sorted(all_assets_dict.keys()):
                                # get asset info
                                asset_ab_id = all_assets_dict[asset][
                                    "automation_broker"
                                ]
                                asset_id = all_assets_dict[asset]["id"]

                                # handle if match
                                if ab == asset_ab_id:
                                    # add to our list
                                    associated_assets.append(asset)

                                    # get broker info
                                    automation_broker_status = all_ab_dict_by_id[
                                        asset_ab_id
                                    ]["last_seen_status"]
                                    automation_active_broker_name = all_ab_dict_by_id[
                                        asset_ab_id
                                    ]["name"]

                                    logger.info(
                                        f"asset={asset}, id={asset_id} is associated with automation_broker={automation_active_broker_name}, id={asset_ab_id}, status={automation_broker_status}"
                                    )

                                    # if the automation broker is not active, and we have at least one active automation broker, we can act and update the asset
                                    # retrieve the full asset configuration first, then update the configuration dict and run the post call, ingestigate results, logs and add to the response

                                    if (
                                        automation_broker_status != "active"
                                        and len(active_ab_list) > 0
                                        and automation_active_broker_name
                                        in selectable_ab_list
                                    ):
                                        logger.warning(
                                            f"asset={asset}, id={asset_id} is associated with automation_broker={automation_active_broker_name}, id={asset_ab_id}, status={automation_broker_status}, asset will be updated now!"
                                        )

                                        try:
                                            asset_config = soar_client.make_request(
                                                f"asset/{asset_id}", "GET", None, timeout=60
                                            )
                                            asset_config_json = asset_config.json()
                                            
                                            # Validate response structure
                                            if not isinstance(asset_config_json, dict):
                                                raise ValueError(
                                                    f'Unexpected asset config response type: {type(asset_config_json).__name__}, '
                                                    f'expected dict'
                                                )
                                        except Exception as e:
                                            error_msg = (
                                                f'asset={asset}, id={asset_id}, failed to retrieve asset configuration, '
                                                f'exception="{str(e)}"'
                                            )
                                            logger.error(error_msg)
                                            update_error_count += 1
                                            update_messages.append(error_msg)
                                            continue  # Skip this asset and move to next
                                        target_automation_broker = random.choice(
                                            active_ab_list
                                        )
                                        target_automation_broker_name = (
                                            all_ab_dict_by_id[target_automation_broker][
                                                "name"
                                            ]
                                        )
                                        target_automation_broker_status = (
                                            all_ab_dict_by_id[target_automation_broker][
                                                "last_seen_status"
                                            ]
                                        )

                                        logger.info(
                                            f"asset={asset}, id={asset_id} is associated with automation_broker={automation_active_broker_name}, id={automation_broker_status}, status={automation_broker_status}, associating asset with automation_broker={target_automation_broker}"
                                        )

                                        asset_config_json["automation_broker_id"] = (
                                            target_automation_broker
                                        )

                                        # Remove any secret before updating
                                        no_secrets_asset_config_json = (
                                            remove_salt_fields(asset_config_json)
                                        )

                                        # Build the per-asset forbidden list. Static defaults
                                        # apply to every asset; if schema-based detection is
                                        # enabled, augment with the password-typed fields
                                        # declared in this asset's app manifest.
                                        per_asset_forbidden_fields = list(
                                            assets_update_forbidden_fields
                                        )
                                        if enable_app_schema_secret_detection:
                                            asset_app_id = asset_config_json.get("app")
                                            schema_password_fields = (
                                                get_app_password_fields(
                                                    soar_client, asset_app_id
                                                )
                                            )
                                            for schema_field in schema_password_fields:
                                                if (
                                                    schema_field
                                                    and schema_field
                                                    not in per_asset_forbidden_fields
                                                ):
                                                    per_asset_forbidden_fields.append(
                                                        schema_field
                                                    )

                                        # Remove any forbidden fields before updating
                                        no_forbidden_fields_asset_config_json = (
                                            remove_forbidden_fields(
                                                no_secrets_asset_config_json,
                                                per_asset_forbidden_fields,
                                            )
                                        )

                                        # run POST (live) or GET (simulation)
                                        endpoint = f"asset/{asset_id}"
                                        if mode == "live":
                                            try:
                                                asset_config_update = soar_client.make_request(
                                                    endpoint,
                                                    "POST",
                                                    no_forbidden_fields_asset_config_json,
                                                    timeout=60,
                                                    max_retries=3,
                                                    retry_delay=2,
                                                )
                                                
                                                # Validate response structure BEFORE adding to success list
                                                try:
                                                    asset_config_update_json = self._validate_asset_update_response(
                                                        asset_config_update, asset, asset_id, mode="live"
                                                    )
                                                except (json.JSONDecodeError, ValueError, TypeError) as json_err:
                                                    # Error already logged in helper method, but capture message for update_messages
                                                    error_msg = (
                                                        f'asset={asset}, id={asset_id}, failed to parse update response, '
                                                        f'exception="{str(json_err)}"'
                                                    )
                                                    update_error_count += 1
                                                    update_messages.append(error_msg)
                                                    continue  # Skip adding to update_assets since validation failed
                                                
                                                # Only add to success list after validation passes
                                                update_assets.append(asset)
                                                
                                                msg = (
                                                    f'asset={asset}, id={asset_id}, asset automation broker configuration was successfully updated '
                                                    f'from automation_broker={automation_active_broker_name}, id={asset_ab_id}, '
                                                    f'status={automation_broker_status} to automation_broker={target_automation_broker_name}, '
                                                    f'id={target_automation_broker}, status={target_automation_broker_status}, '
                                                    f'response="{asset_config_update_json}"'
                                                )
                                                logger.info(msg)
                                                update_messages.append(msg)

                                            except Exception as e:
                                                error_msg = (
                                                    f'asset={asset}, id={asset_id}, failed to update asset after retries, '
                                                    f'exception="{str(e)}", endpoint="{endpoint}"'
                                                )
                                                logger.error(error_msg)
                                                update_error_count += 1
                                                update_messages.append(error_msg)

                                        elif mode in (
                                            "simulation",
                                            "readonly",
                                        ):  # simulation was replaced by readonly, and is kept for compatibility purposes
                                            try:
                                                asset_config_update = (
                                                    soar_client.make_request(
                                                        endpoint,
                                                        "GET",
                                                        asset_config_json,
                                                        timeout=60,
                                                        max_retries=3,
                                                        retry_delay=2,
                                                    )
                                                )
                                                
                                                # Validate response structure BEFORE adding to success list
                                                try:
                                                    asset_config_update_json = self._validate_asset_update_response(
                                                        asset_config_update, asset, asset_id, mode="readonly"
                                                    )
                                                except (json.JSONDecodeError, ValueError, TypeError) as json_err:
                                                    # Error already logged in helper method, but capture message for update_messages
                                                    error_msg = (
                                                        f'asset={asset}, id={asset_id}, **read only mode** failed to parse update response, '
                                                        f'exception="{str(json_err)}"'
                                                    )
                                                    update_error_count += 1
                                                    update_messages.append(error_msg)
                                                    continue  # Skip adding to update_assets since validation failed
                                                
                                                # Only add to success list after validation passes
                                                update_assets.append(asset)
                                                
                                                current_broker = (
                                                    asset_config_update_json.get(
                                                        "automation_broker"
                                                    )
                                                )
                                                msg = (
                                                    f'asset={asset}, id={asset_id}, **read only mode** asset automation broker configuration was successfully updated '
                                                    f'from automation_broker={automation_active_broker_name}, id={asset_ab_id}, '
                                                    f'status={automation_broker_status} to automation_broker={target_automation_broker_name}, '
                                                    f'id={target_automation_broker}, status={target_automation_broker_status}, '
                                                    f'current_broker="{current_broker}"'
                                                )
                                                logger.info(msg)
                                                update_messages.append(msg)

                                            except Exception as e:
                                                error_msg = (
                                                    f'asset={asset}, id={asset_id}, **read only mode** failed to update asset after retries, '
                                                    f'exception="{str(e)}", endpoint="{endpoint}"'
                                                )
                                                logger.error(error_msg)
                                                update_error_count += 1
                                                update_messages.append(error_msg)

                                    # the associated broker is inactive, but there are no other brokers available
                                    elif (
                                        automation_broker_status != "active"
                                        and len(active_ab_list) == 0
                                    ):
                                        # Log as warning instead of error - this is a transient condition
                                        # The asset will be retried on the next run when brokers become available
                                        warning_msg = (
                                            f"asset={asset}, id={asset_id} is associated with automation_broker={automation_active_broker_name}, "
                                            f"id={asset_ab_id}, status={automation_broker_status}, there are no other active automation brokers "
                                            f"available. Asset will be skipped for now and can be retried when brokers become active. "
                                            f"This is a transient condition and does not indicate a permanent failure."
                                        )
                                        logger.warning(warning_msg)
                                        # Don't increment error_count for this case - it's expected behavior
                                        # Add to update_messages as a string to maintain API contract consistency
                                        update_messages.append(warning_msg)

                            # set response
                            ab_response = {
                                "id": ab,
                                "name": all_ab_dict_by_id[ab]["name"],
                                "last_seen_status": all_ab_dict_by_id[ab][
                                    "last_seen_status"
                                ],
                                "associated_assets": all_ab_dict_by_id[ab]["assets"],
                                "associated_assets_count": len(
                                    all_ab_dict_by_id[ab]["assets"]
                                ),
                                "update_messages": update_messages,
                                "update_error_count": update_error_count,
                                "updated_assets": update_assets,
                                "version": all_ab_dict_by_id[ab]["version"],
                                "rest_healthcheck_time": all_ab_dict_by_id[ab][
                                    "rest_healthcheck_time"
                                ],
                                "ws_healthcheck_time": all_ab_dict_by_id[ab][
                                    "ws_healthcheck_time"
                                ],
                                "automation_proxy_summary": all_ab_dict_by_id[ab],
                            }

                            # add
                            final_response.append(ab_response)

                #
                # Render API response
                #

                run_time = round(time.time() - start_time, 3)
                logger.info(
                    f'terminated soar_automation_proxy_monitor, soar_server="{soar_server}", run_time={run_time}'
                )

                return {
                    "payload": {
                        "response": final_response,
                    },
                    "status": 200,
                }

            except Exception as e:
                # render response with full context
                error_trace = traceback.format_exc()
                msg = (
                    f'An exception was encountered while processing SOAR automation broker management, '
                    f'soar_server="{soar_server}", mode="{mode}", exception="{str(e)}", '
                    f'traceback="{error_trace[-500:]}"'  # Last 500 chars of traceback
                )
                logger.error(msg)
                return {
                    "payload": {
                        "action": "failure",
                        "response": msg,
                        "soar_server": soar_server,
                        "mode": mode,
                    },
                    "status": 500,
                }
