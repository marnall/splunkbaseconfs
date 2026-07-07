# File: bitdefendergravityzone_connector.py
#
# Copyright (c) 2022-2025 Splunk Inc.
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
#
#
# Python 3 Compatibility imports

import json
import sys
import uuid

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
from bitdefendergravityzone_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class BitdefenderGravityzoneConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {e!s}"), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        r_error = resp_json.get("error", {})
        message = f"Error from server. Status Code: {r.status_code} Data from server: {r_error}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = self._base_url + endpoint

        try:
            r = request_func(
                url,
                auth=(self._username, ""),  # basic authentication
                verify=config.get("verify_server_cert", False),
                headers=self._headers,
                **kwargs,
            )
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {e!s}"), resp_json)

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        payload = {"params": {}, "jsonrpc": "2.0", "method": "getQuarantineItemsList", "id": str(uuid.uuid1())}

        self.save_progress("Connecting to endpoint")
        # make rest call
        ret_val, response = self._make_rest_call(
            QUARANTINE_ENDPOINT.format(service="computers"), action_result, method="post", data=json.dumps(payload)
        )

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            self.save_progress(f"Error {action_result.get_message()}")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _validate_task_response(self, response):
        return response.get("result") is True

    def _handle_delete_quarantine(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        service_name = param["service_name"]

        if param.get("empty_all", False):
            self.save_progress(f"Cleaning up quarantine for service {service_name}")
            method = "createEmptyQuarantineTask"
            params = {}
        else:
            self.save_progress(f"Deleting {service_name} items from quarantine")
            method = "createRemoveQuarantineItemTask"
            params = {"quarantineItemsIds": param.get("item_ids", [])}

        payload = {"params": params, "jsonrpc": "2.0", "method": method, "id": str(uuid.uuid1())}

        # make rest call
        ret_val, response = self._make_rest_call(
            QUARANTINE_ENDPOINT.format(service=service_name), action_result, method="post", data=json.dumps(payload)
        )

        if phantom.is_fail(ret_val):
            self.save_progress(f"Error {action_result.get_message()}")
            return action_result.get_status()

        self.save_progress(BDGZ_OK)

        action_result.add_data(response)

        if not self._validate_task_response(response):
            return action_result.set_status(phantom.APP_ERROR, f"{BDGZ_ERR}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_unquarantine_computer(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        location = param.get("location", None)
        add_exclusion = param.get("add_exclusion_policy", None)

        payload = {
            "params": {"quarantineItemsIds": param["item_ids"].split(",")},
            "jsonrpc": "2.0",
            "method": "createRestoreQuarantineItemTask",
            "id": str(uuid.uuid1()),
        }

        # Add optional fields to parameters
        if location:
            payload["params"]["locationToRestore"] = location

        if add_exclusion is not None:
            payload["params"]["addExclusionInPolicy"] = add_exclusion

        # make rest call
        ret_val, response = self._make_rest_call(
            QUARANTINE_ENDPOINT.format(service="computers"), action_result, method="post", data=json.dumps(payload)
        )

        if phantom.is_fail(ret_val):
            self.save_progress(f"Error {action_result.get_message()}")
            return action_result.get_status()

        self.save_progress(BDGZ_OK)

        action_result.add_data(response)

        if not self._validate_task_response(response):
            return action_result.set_status(phantom.APP_ERROR, f"{BDGZ_ERR}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_unquarantine_exchange(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        email = param.get("email", None)
        ews_url = param.get("ews_url", None)

        payload = {
            "params": {"quarantineItemsIds": param["item_ids"].split(","), "username": param["username"], "password": param["password"]},
            "jsonrpc": "2.0",
            "method": "createRestoreQuarantineExchangeItemTask",
            "id": str(uuid.uuid1()),
        }

        # Add optional fields to parameters
        if email:
            payload["params"]["email"] = email

        if ews_url:
            payload["params"]["ewsUrl"] = ews_url

        # make rest call
        ret_val, response = self._make_rest_call(
            QUARANTINE_ENDPOINT.format(service="exchange"), action_result, method="post", data=json.dumps(payload)
        )

        if phantom.is_fail(ret_val):
            self.save_progress(f"Error {action_result.get_message()}")
            return action_result.get_status()

        self.save_progress(BDGZ_OK)

        action_result.add_data(response)

        if not self._validate_task_response(response):
            return action_result.set_status(phantom.APP_ERROR, f"{BDGZ_ERR}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_quarantine(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint_id = param.get("endpoint_id", None)
        page = param.get("page", None)
        per_page = param.get("per_page", None)

        payload = {"params": {}, "jsonrpc": "2.0", "method": "getQuarantineItemsList", "id": str(uuid.uuid1())}

        # Add optional fields to parameters
        if endpoint_id:
            payload["params"]["endpointId"] = endpoint_id

        if page:
            payload["params"]["page"] = page

        if per_page:
            payload["params"]["perPage"] = per_page

        curr_items = 0

        while True:
            # make rest call with pagination
            ret_val, response = self._make_rest_call(
                QUARANTINE_ENDPOINT.format(service=param["service_name"]), action_result, method="post", data=json.dumps(payload)
            )

            if phantom.is_fail(ret_val):
                self.save_progress(f"Error {action_result.get_message()}")
                return action_result.get_status()

            for item in response["result"]["items"]:
                action_result.add_data(item)

            total_items = response["result"]["total"]
            curr_items += response["result"]["perPage"]
            if total_items <= curr_items:
                break

            next_page = response["result"]["page"] + 1
            payload["params"]["page"] = next_page
            self.save_progress(f"Next page: {next_page}")

        self.save_progress(BDGZ_OK)
        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_items"] = response["result"]["total"]

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "delete_quarantine":
            ret_val = self._handle_delete_quarantine(param)

        elif action_id == "unquarantine_computer":
            ret_val = self._handle_unquarantine_computer(param)

        elif action_id == "unquarantine_exchange":
            ret_val = self._handle_unquarantine_exchange(param)

        elif action_id == "list_quarantine":
            ret_val = self._handle_list_quarantine(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()
        """
        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """

        self._headers = {"Content-Type": "application/json"}

        self._username = config["api_key"]
        self._base_url = config.get("base_url")

        # Security check on URL format
        if not self._base_url.endswith("/"):
            self._base_url += "/"

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = BitdefenderGravityzoneConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=True, timeout=30)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=True, data=data, headers=headers, timeout=30)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = BitdefenderGravityzoneConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
