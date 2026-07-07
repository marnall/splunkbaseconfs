#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_soar_user.py"
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

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_soar_user",
    "trackme_rest_api_splk_soar_user.log",
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

# Splunk libs
import splunklib.client as client

# import Splunk SOAR bin, only if the app is available
# if os.path.isdir(os.path.join(splunkhome, 'etc', 'apps', 'splunk_app_soar', 'bin')):
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", "trackme", "lib", "splunk_soar")
)
from trackme_soar import SOARClient


class TrackMeHandlerSplkSoarRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkSoarRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_soar(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_soar",
            "resource_group_desc": "Endpoints specific to Splunk SOAR monitoring, read only operations)",
        }

        return {"payload": response, "status": 200}

    # Get soar account credentials with a least privileges approach
    def post_get_soar_account(self, request_info, **kwargs):
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                account = resp_dict["account"]
        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint provides connection details for a Splunk SOAR account to be used in a programmatic manner with a least privileges approach, it requires a POST call with the following options:",
                "resource_desc": "Return a remote account credential details for programmatic access with a least privileges approach",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_soar/get_soar_account\" body=\"{'account': 'lab'}\"",
                "options": [
                    {
                        "account": "The account configuration identifier",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="splunk_app_soar",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # get all accounts
        try:
            accounts = []
            conf_file = "ta_splunk_app_soar_account"
            confs = service.confs[str(conf_file)]
            for stanza in confs:
                # get all accounts
                for name in stanza.name:
                    accounts.append(stanza.name)
                    break

        except Exception as e:
            error_msg = "There are no Splunk SOAR account configured yet"
            return {
                "payload": {
                    "status": "failure",
                    "message": error_msg,
                    "account": account,
                },
                "status": 500,
            }

        else:
            try:
                response = trackme_get_soar_account(request_info, account)
                return {"payload": response, "status": 200}

            # note: the exception is returned as a JSON object
            except Exception as e:
                return {"payload": str(e), "status": 500}

    # Get a SOAR API endpoint
    def post_soar_get_endpoint(self, request_info, **kwargs):
        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                soar_server = resp_dict.get("soar_server", None)
                endpoint = resp_dict.get("endpoint", "health")
                params = resp_dict.get("params", None)

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoints queries a SOAR API endpoint (GET only), it requires a POST call with the following information:",
                "resource_desc": "Query a Splunk SOAR API endpoint",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_soar/soar_get_endpoint\" mode=\"post\" body=\"{'soar_server': 'soar_production', 'endpoint': 'health'}\"",
                "options": [
                    {
                        "soar_server": "The SOAR server account as defined in the Splunk App for SOAR, if unspecified or set to *, the first server in the Splunk application for SOAR configuration will be used",
                        "endpoint": "The SOAR API endpoint, some examples: version, system_info, license, health, app_status",
                        "params": "Optional parameters to be passed to the endpoint",
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
                    # Use helper method for all endpoints
                    # preserve_dict_format=True maintains backward compatibility by preserving
                    # non-paginated dict responses as dicts instead of wrapping in lists
                    response = soar_client.get_paginated_response(
                        endpoint, method="GET", data=None, extra_params=params,
                        timeout=60, max_retries=3, page_size=100, preserve_dict_format=True
                    )
                    
                    # Health endpoint must return a dict, not a list
                    # If get_paginated_response returns a list (e.g., if SOAR API wraps it), unwrap it
                    if endpoint == "health":
                        if isinstance(response, list):
                            if len(response) == 1 and isinstance(response[0], dict):
                                # Unwrap single dict from list
                                response = response[0]
                            else:
                                raise ValueError(
                                    f'Health endpoint returned unexpected list format: '
                                    f'expected list with single dict, got list with {len(response)} items'
                                )
                        elif not isinstance(response, dict):
                            raise ValueError(
                                f'Health endpoint returned unexpected type: {type(response).__name__}, '
                                f'expected dict'
                            )
                except Exception as e:
                    error_msg = (
                        f'Error processing SOAR response, endpoint="{endpoint}", '
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
                    f'An exception was encountered while processing SOAR GET request, '
                    f'endpoint="{endpoint if "endpoint" in locals() else "unknown"}", '
                    f'soar_server="{soar_server if "soar_server" in locals() else "unknown"}", '
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
