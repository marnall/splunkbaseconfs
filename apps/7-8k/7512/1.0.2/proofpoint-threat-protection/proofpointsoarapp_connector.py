# File: proofpointsoarapp_connector.py
#
# Copyright (c) 2024-2026 Splunk Inc.
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

import base64
import json

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
from proofpointsoarapp_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class ProofpointSoarAppConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None
        self._client_id = None
        self._client_secret = None
        self._access_token = None

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
        message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

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

    def encode_token(self, token):
        sample_string_bytes = token.encode("ascii")
        base64_bytes = base64.b64encode(sample_string_bytes)
        base64_string = base64_bytes.decode("ascii")
        return base64_string

    def decode_token(self, token_base64):
        base64_bytes = token_base64.encode("ascii")
        sample_string_bytes = base64.b64decode(base64_bytes)
        sample_string = sample_string_bytes.decode("ascii")
        return sample_string

    def _generate_new_access_token(self, action_result, test_connectivity=False):
        """This function is used to generate new access token using the code obtained on authorization."""

        payload = {"grant_type": "client_credentials", "client_id": self._client_id, "client_secret": self._client_secret}

        ret_val, resp_json = self._make_rest_call(
            action_result=action_result,
            url=TOKEN_URL,
            data=payload,
            method="post",
            test_connectivity=test_connectivity,
            token_generating_call=False,
        )
        self.save_progress("Generating token...")

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, f"Failure in tokenization process {resp_json}")

        try:
            self._access_token = resp_json["access_token"]
        except:
            return action_result.set_status(phantom.APP_ERROR, f"There is no access token inside request response: {resp_json}")

        self.save_progress("Token generated.")

        self._state["access_token"] = self.encode_token(resp_json["access_token"])

        return phantom.APP_SUCCESS

    def _make_rest_call(self, url, action_result, test_connectivity=False, token_generating_call=True, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        config = self.get_config()

        resp_json = None

        if not self._access_token and not test_connectivity and token_generating_call:
            ret_val_tokenization = self._generate_new_access_token(action_result)
            if phantom.is_fail(ret_val_tokenization):
                error_message = action_result.get_message()
                return RetVal(action_result.get_status(), TOKENIZATION_ERR_MSG.format(error_message))

        if self._access_token:
            headers = {"headers": {"Authorization": BEARER_STRING.format(self._access_token), "Content-Type": "application/json"}}
            kwargs.update(headers)

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        try:
            r = request_func(
                url,
                # auth=(username, password),  # basic authentication
                verify=config.get("verify_server_cert", False),
                **kwargs,
            )
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {e!s}"), resp_json)

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val = self._generate_new_access_token(action_result, test_connectivity=True)

        if phantom.is_fail(ret_val):
            error_message = action_result.get_message()
            return action_result.set_status(phantom.APP_ERROR, error_message)

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_safe_list_entries(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        url = self._base_url + SAFE_LIST_ENTRIES_ENDPOINT

        parameters = {"clusterId": param["clusterid"]}

        # make rest call
        ret_val, response = self._make_rest_call(url, action_result, params=parameters)

        if phantom.is_fail(ret_val):
            message = f"Error during Get Safe list entries endpoint execution, response: {response}"
            return action_result.set_status(phantom.APP_ERROR, message)

        action_result.add_data(response.get("entries"))

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_add_to_delete_from_safe_list(self, param, request_action):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        url = self._base_url + SAFE_LIST_ENTRIES_ENDPOINT

        parameters = {"clusterId": param["clusterid"]}

        body = {"action": request_action.split(" ")[0], "attribute": param["attribute"], "operator": param["operator"], "value": param["value"]}

        if param.get("comment"):
            body.update({"comment": param.get("comment")})

        # make rest call
        ret_val, response = self._make_rest_call(url, action_result, method="post", params=parameters, json=body)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, f"Error during {request_action} Safe list, response: {response}")

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, f"{request_action.capitalize()} Safe list correctly")

    def _handle_get_block_list_entries(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        url = self._base_url + BLOCK_LIST_ENTRIES_ENDPOINT

        parameters = {"clusterId": param["clusterid"]}

        # make rest call
        ret_val, response = self._make_rest_call(url, action_result, params=parameters)

        if phantom.is_fail(ret_val):
            message = f"Error during Get block list entries endpoint execution, response: {response}"
            return action_result.set_status(phantom.APP_ERROR, message)

        action_result.add_data(response.get("entries"))

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_add_to_delete_from_block_list(self, param, request_action):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        url = self._base_url + BLOCK_LIST_ENTRIES_ENDPOINT

        parameters = {"clusterId": param["clusterid"]}

        body = {"action": request_action.split(" ")[0], "attribute": param["attribute"], "operator": param["operator"], "value": param["value"]}

        if param.get("comment"):
            body.update({"comment": param.get("comment")})

        # make rest call
        ret_val, response = self._make_rest_call(url, action_result, method="post", params=parameters, json=body)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, f"Error during {request_action} Block list, response: {response}")

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, f"{request_action.capitalize()} Block list correctly")

    def _handle_add_to_safe_list(self, param):
        return self._handle_add_to_delete_from_safe_list(param, "add to")

    def _handle_delete_from_safe_list(self, param):
        return self._handle_add_to_delete_from_safe_list(param, "delete from")

    def _handle_add_to_block_list(self, param):
        return self._handle_add_to_delete_from_block_list(param, "add to")

    def _handle_delete_from_block_list(self, param):
        return self._handle_add_to_delete_from_block_list(param, "delete from")

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "get_safe_list_entries":
            ret_val = self._handle_get_safe_list_entries(param)

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        if action_id == "add_to_safe_list":
            ret_val = self._handle_add_to_safe_list(param)

        if action_id == "delete_from_safe_list":
            ret_val = self._handle_delete_from_safe_list(param)

        if action_id == "get_block_list_entries":
            ret_val = self._handle_get_block_list_entries(param)

        if action_id == "add_to_block_list":
            ret_val = self._handle_add_to_block_list(param)

        if action_id == "delete_from_block_list":
            ret_val = self._handle_delete_from_block_list(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()
        if self._state and not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}

        # get the asset config
        config = self.get_config()

        self._client_id = config.get("client_id")
        self._client_secret = config.get("client_secret")
        self._base_url = config.get("base_url")

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse
    import sys

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument("-v", "--verify", action="store_true", help="verify", required=False, default=False)

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
            login_url = ProofpointSoarAppConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = ProofpointSoarAppConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
