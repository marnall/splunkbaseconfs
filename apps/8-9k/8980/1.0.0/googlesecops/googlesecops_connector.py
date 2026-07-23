# File: googlesecops_connector.py
#
# Copyright (c) 2026 Google
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

from actions import BaseAction  # pylint: disable=import-error,no-name-in-module
from googlesecops_client import GoogleSecOpsClient
from googlesecops_utils import GoogleSecOpsUtils, Validator


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class GoogleSecOpsConnector(BaseConnector):
    def __init__(self):
        super().__init__()

        self._state = None
        self.client = None
        self.validator = None
        self.config = None
        self.utils = None

    def handle_action(self, param):
        """
        Handle the flow of execution, calls the appropriate method for the action.

        This method retrieves the action identifier for the current App Run and imports the corresponding action module.
        It then searches for the appropriate action class within the imported module and creates an instance of it.
        Finally, it executes the action by calling the `execute` method of the action instance.

        Args:
            param (dict): A dictionary containing the parameters for the action.

        Returns:
            int: The status code indicating the success or failure of the action execution.
                - `phantom.APP_SUCCESS`: The action execution was successful.
                - `phantom.APP_ERROR`: The action execution failed.
        """
        action_id = self.get_action_identifier()
        self.debug_print("action_id", self.get_action_identifier())

        action_name = f"actions.googlesecops_{action_id}"
        import_module(action_name, package="actions")

        base_action_sub_classes = BaseAction.__subclasses__()
        self.debug_print(f"Finding action module: {action_name}")
        for action_class in base_action_sub_classes:
            if action_class.__module__ == action_name:
                action = action_class(self, param)
                return action.execute()

        self.debug_print("Action not implemented")
        return phantom.APP_ERROR

    def initialize(self):
        """
        Initializes the connector and creates the utility object.

        Returns:
            int: The status code indicating the success or failure of the initialization.
                - `phantom.APP_SUCCESS`: The initialization was successful.
                - `phantom.APP_ERROR`: The initialization failed.
        """
        self._state = self.load_state()

        if not self._state or not isinstance(self._state, dict):
            self.debug_print("State file is corrupted or missing")
            self._state = {"app_version": self.get_app_json().get("app_version")}

        self.config = self.get_config()

        try:
            self.validator = Validator()
            self.utils = GoogleSecOpsUtils(self)
            self.client = GoogleSecOpsClient(self, self.config)
        except Exception as e:
            error_msg = self.utils._get_error_message_from_exception(e)
            self.save_progress(f"Error initializing client: {error_msg}")
            return phantom.APP_ERROR

        return phantom.APP_SUCCESS

    def finalize(self):
        """
        This is called after all actions are completed and the app is exiting

        This is used to save any state that needs to be saved across actions and app upgrades

        Returns:
            int: The status code indicating the success or failure of the finalize
                - `phantom.APP_SUCCESS`: The finalize was successful
                - `phantom.APP_ERROR`: The finalize failed
        """
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    """Use this method to debug action using input test JSON file."""
    import argparse
    import sys

    import pudb

    pudb.set_trace()

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
            login_url = GoogleSecOpsConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify)  # nosemgrep: python.requests.best-practice.use-timeout.use-timeout
            csrftoken = r.cookies["csrftoken"]

            data = {}
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = {}
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(
                login_url,
                verify=verify,
                data=data,
                headers=headers,  # nosemgrep: python.requests.best-practice.use-timeout.use-timeout
            )
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = GoogleSecOpsConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
