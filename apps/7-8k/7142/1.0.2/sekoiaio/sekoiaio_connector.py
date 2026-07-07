# File: sekoiaio_connector.py
#
# Copyright (c) 2023-2025 SEKOIA.IO
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

# Phantom App imports
import phantom.app as phantom

# Useful libraries
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
import sekoiaio_consts as consts


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class SekoiaioConnector(BaseConnector):
    def __init__(self):
        super().__init__()
        self.state = None
        self.base_url = None
        self.api_key = None

    def initialize(self):
        self.state = self.load_state()
        config = self.get_config()
        self.base_url = config["base_url"]
        self.api_key = config["api_key"]

        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self.state)
        return phantom.APP_SUCCESS

    def _process_brackets(self, text_response):
        return text_response.replace("{", "{{").replace("}", "}}")

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, consts.EMPTY_RESPONSE_ERROR_LOG),
            None,
        )

    def _process_html_response(self, response, action_result):
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            error_text = "\n".join(x.strip() for x in split_lines if x.strip())
        except Exception as e:
            error_text = f"Cannot parse error details : {e}"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = self._process_brackets(message)
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, response, action_result):
        try:
            resp_json = response.json()
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Unable to parse JSON response. Error: {e!s}",
                ),
                None,
            )

        if 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        if response.status_code == 400:
            return action_result.set_status(phantom.APP_ERROR, consts.JSON_RESPONSE_400_ERROR_LOG)

        if response.status_code == 401:
            return action_result.set_status(phantom.APP_ERROR, consts.JSON_RESPONSE_401_ERROR_LOG)

        if response.status_code == 403:
            return action_result.set_status(phantom.APP_ERROR, consts.JSON_RESPONSE_403_ERROR_LOG)

        message = f"Error from server. Status Code: {response.status_code} \
                Data from server: {self._process_brackets(response.text)}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, response, action_result):
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"response_status_code": response.status_code})
            action_result.add_debug_data({"response_text": response.text})
            action_result.add_debug_data({"response_headers": response.headers})

        if "json" in response.headers.get("Content-Type", ""):
            return self._process_json_response(response, action_result)

        if "html" in response.headers.get("Content-Type", ""):
            return self._process_html_response(response, action_result)

        if not response.text:
            return self._process_empty_response(response, action_result)

        message = f"Can't process response from server. \
            Status Code: {response.status_code} Data from server: \
            {self._process_brackets(response.text)}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        config = self.get_config()
        resp_json = None
        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"),
                resp_json,
            )
        url = self.base_url + endpoint
        try:
            response = request_func(url, verify=config.get("verify_server_cert", True), **kwargs)
        except requests.exceptions.InvalidURL:
            error_message = f"Error connecting to server. Invalid URL: {url}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), resp_json)
        except requests.exceptions.InvalidSchema:
            error_message = f"Error connecting to server. \
                No connection adapters were found for {url}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), resp_json)
        except requests.exceptions.ConnectionError:
            error_message = f"Error connecting to server. \
                Connection Refused from the Server for {url}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), resp_json)
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Error Connecting to server. Details: {e!s}",
                ),
                resp_json,
            )

        return self._process_response(response, action_result)

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Start Connecting to endpoint ..... !!")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        ret_val, response = self._make_rest_call("/v1/auth/validate", action_result, params=None, headers=headers)

        if phantom.is_fail(ret_val):
            self.save_progress(f"Test Connectivity Failed. {consts.DOCUMENTATION_LOG}")
            return action_result.get_status()

        self.save_progress("Test connectivity passed, your token is valid. You can use it.")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_indicator(self, param):
        self.save_progress(f"In get indicator action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        # This 2 required parameters to requests this endpoint
        # Take a look at
        # /cti/develop/rest_api/intelligences/Indicators
        value, type_ = param.get("value", ""), param.get("type", "")
        params, headers = {"value": value, "type": type_}, {"Authorization": f"Bearer {self.api_key}"}
        ret_val, response = self._make_rest_call("/v2/inthreat/indicators", action_result, params=params, headers=headers)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress("Received response from endpoint")
        # Add the response into the data section
        action_result.add_data(response.get("items", []))

        # Add a dictionary that is made up of the
        # most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_data"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_indicator_context(self, param):
        self.save_progress(f"In get indicator context action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        # This 2 required parameters to requests this endpoint
        # Take a look at
        # cti/develop/rest_api/intelligence/Indicators/operation/get_indicator_context_resource
        value, type_ = param.get("value", ""), param.get("type", "")
        params, headers = {"value": value, "type": type_}, {"Authorization": f"Bearer {self.api_key}"}
        ret_val, response = self._make_rest_call(
            "/v2/inthreat/indicators/context",
            action_result,
            params=params,
            headers=headers,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress("Great, we get response from the endpoint !!")

        action_result.add_data(response)

        # Add a dictionary that is made up of
        # the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_data"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_observable(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        value, type_, limit = (
            param.get("value", ""),
            param.get("type", ""),
            param.get("limit", 20),
        )
        params, headers = {"value": value, "type": type_, "limit": limit}, {"Authorization": f"Bearer {self.api_key}"}
        # make rest call
        ret_val, response = self._make_rest_call("/v2/inthreat/observables", action_result, params=params, headers=headers)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress("Great, we get response from the endpoint !!")

        # Add the response into the data section
        action_result.add_data(response.get("items", []))

        # Add a dictionary that is made up of the
        # most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_data_get_observable"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "get_indicator":
            ret_val = self._handle_get_indicator(param)

        if action_id == "get_indicator_context":
            ret_val = self._handle_get_indicator_context(param)

        if action_id == "get_observable":
            ret_val = self._handle_get_observable(param)

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        return ret_val


def main():
    import argparse
    import sys

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument(
        "-v",
        "--verify",
        action="store_true",
        help="verify",
        required=False,
        default=False,
    )

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
            login_url = SekoiaioConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=False)
            csrftoken = r.cookies["csrftoken"]

            data = {
                "username": username,
                "password": password,
                "csrfmiddlewaretoken": csrftoken,
            }

            headers = {"Cookie": "csrftoken=" + csrftoken, "Referer": login_url}

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print(
                f"Unable to get session id \
                from the platform. Error: {e!s}"
            )
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = SekoiaioConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
