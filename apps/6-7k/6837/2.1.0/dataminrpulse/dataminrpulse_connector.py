# File: dataminrpulse_connector.py
#
# Copyright (c) 2023-2026 Dataminr
#
# This unpublished material is proprietary to Dataminr.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Dataminr.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

import json
from importlib import import_module

import phantom.app as phantom
import requests
from phantom.base_connector import BaseConnector

import dataminrpulse_consts as consts
from actions import BaseAction
from dataminrpulse_utils import DataminrPulseUtils


class DataminrPulseConnector(BaseConnector):
    """Dataminr Pulse Connector class to interact with service API."""

    def __init__(self):
        """Prepare constructor for Dataminr Pulse."""
        # Call the BaseConnectors init first
        super().__init__()

        self.state = None
        self.util = None
        self.config = None
        self.is_state_updated = False

    def initialize(self):
        """Set up method for the connector"""
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self.state = self.load_state()
        if not self.state or not isinstance(self.state, dict):
            self.debug_print(consts.DATAMINRPULSE_ERROR_STATE_FILE_CORRUPT)
            self.state = {"app_version": self.get_app_json().get("app_version")}
            self.is_state_updated = True

        self.config = self.get_config()

        # Create the util object and use it throughout the action lifecycle
        self.util = DataminrPulseUtils(self)
        api_version = self.state.get(consts.DATAMINRPULSE_STATE_API_VERSION, None)
        if api_version and api_version != self.util._api_version:
            self.debug_print(f"API version is changed from {api_version} to {self.util._api_version} hence resetting state file")
            self.state = {"app_version": self.get_app_json().get("app_version")}
            self.is_state_updated = True

        self.state[consts.DATAMINRPULSE_STATE_API_VERSION] = self.util._api_version

        return phantom.APP_SUCCESS

    def finalize(self):
        """Tear down method for the connector"""
        if self.is_state_updated:
            # Encrypt and Save the state, this data is saved across actions and app upgrades
            self.state = self.util._encrypt_state(self.state)
            self.save_state(self.state)
        return phantom.APP_SUCCESS

    def handle_action(self, param):
        """Handle the flow of execution, calls the appropriate method for the action."""
        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()
        self.debug_print("action_id", self.get_action_identifier())

        action_name = f"actions.dataminrpulse_{action_id}"
        import_module(action_name, package="actions")

        base_action_sub_classes = BaseAction.__subclasses__()
        self.debug_print(f"Finding action module: {action_name}")
        for action_class in base_action_sub_classes:
            if action_class.__module__ == action_name:
                action = action_class(self, param)
                return action.execute()

        self.debug_print("Action not implemented")
        return phantom.APP_ERROR


def main():  # pragma: no cover
    import argparse
    import sys

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument("-v", "--verify", help="verify", required=False, default=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password
    verify = args.verify

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = DataminrPulseConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = DataminrPulseConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
