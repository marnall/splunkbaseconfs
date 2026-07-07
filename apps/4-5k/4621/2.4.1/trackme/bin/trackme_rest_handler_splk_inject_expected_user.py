#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_inject_expected.py"
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

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_inject_expected_user",
    "trackme_rest_api_splk_inject_expected_user.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_getloglevel, trackme_parse_describe_flag
from trackme_libs_policies import (
    list_available_transforms,
    get_lookup_fields,
    resolve_service_for_account,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkInjectExpectedRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkInjectExpectedRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_inject_expected(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_inject_expected",
            "resource_group_desc": "Endpoints related to injecting expected sources and hosts (read only operations)",
        }

        return {"payload": response, "status": 200}

    # List available Splunk lookup transforms
    def post_inject_list_transforms(self, request_info, **kwargs):

        # Declare
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint lists available Splunk lookup transforms for expected sources/hosts injection, it requires a POST call with the following information:",
                "resource_desc": "List available lookup transforms for expected sources/hosts injection",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_inject_expected/inject_list_transforms" body="{}"',
                "options": [
                    {
                        "filter": "(optional) A substring filter to match against transform names",
                        "account": "(optional) The remote Splunk deployment account name, defaults to local",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # optional filter
        name_filter = None
        if resp_dict:
            name_filter = resp_dict.get("filter", None)

        # optional account (for remote Splunk deployment)
        account = resp_dict.get("account", "local") if resp_dict else "local"

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

        # Resolve target service (local or remote)
        try:
            target_service = resolve_service_for_account(service, request_info, account, logger)
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Failed to connect to remote account "{account}": {str(e)}',
                },
                "status": 503,
            }

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        return list_available_transforms(target_service, logger, name_filter)

    # Get fields from a specific lookup transform
    def post_inject_get_lookup_fields(self, request_info, **kwargs):

        # Declare
        lookup_name = None
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
                    lookup_name = resp_dict["lookup_name"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "lookup_name is required",
                        },
                        "status": 400,
                    }
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves the fields from a Splunk lookup transform for expected sources/hosts injection, it requires a POST call with the following information:",
                "resource_desc": "Get fields from a lookup transform for field mapping",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_inject_expected/inject_get_lookup_fields" body="{\'lookup_name\': \'example_expected_hosts\'}"',
                "options": [
                    {
                        "lookup_name": "(required) The name of the lookup transform",
                        "account": "(optional) The remote Splunk deployment account name, defaults to local",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # optional account (for remote Splunk deployment)
        account = resp_dict.get("account", "local") if resp_dict else "local"

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

        # Resolve target service (local or remote)
        try:
            target_service = resolve_service_for_account(service, request_info, account, logger)
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Failed to connect to remote account "{account}": {str(e)}',
                },
                "status": 503,
            }

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        return get_lookup_fields(target_service, logger, lookup_name)
