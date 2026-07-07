# File: alienvaultotx_connector.py
#
# Copyright (c) 2019-2025 Splunk Inc.
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
import ipaddress
import json

import phantom.app as phantom
import phantom.utils as utils
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from alienvaultotx_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class AlienvaultOtxv2Connector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None

    def _validate_response_type(self, action_result, response_type_input, response_type_list):
        """This method validates the input provided by the user in response_type in the action"""
        if response_type_input not in response_type_list:
            return action_result.set_status(
                phantom.APP_ERROR,
                "Please provide a valid value of 'response type' parameter from the given list: {}".format(", ".join(response_type_list)),
            )

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_error_message_from_exception(self, e):
        """This method is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        self.error_print("Traceback: ", e)
        error_code = None
        error_message = OTX_ERROR_MESSAGE_UNAVAILABLE

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except Exception as e:
            self.error_print("Error occurred while retrieving exception information", e)

        if not error_code:
            error_text = f"Error Message: {error_message}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_message}"

        return error_text

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, f"Status code: {response.status_code}, Empty response and no information in the header"),
            None,
        )

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove the script, style, footer and navigation part from the HTML message
            for element in soup(["script", "style", "footer", "nav"]):
                element.extract()
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except Exception:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"
        self.debug_print(f"Response from Server: {message}")

        # Accounting for incorrect API response
        if self.get_action_identifier() == OTX_DOMAIN_REPUTATION_ACTION:
            message = "Parameter 'domain' failed validation"
        else:
            message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json_unformatted = r.json()
            resp_json = json.loads(json.dumps(resp_json_unformatted).replace("\\u0000", "\\\\u0000"))
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {error_message}"), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        if self.get_action_identifier() == OTX_GET_PULSES_ACTION and r.status_code == 404:
            action_result.set_status(phantom.APP_SUCCESS, OTX_ERROR_NO_PULSE_FOUND)
            return RetVal(phantom.APP_ERROR, None)

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

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        # Create a URL to connect to
        url = f"{self._base_url}{endpoint}"

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        headers = {"X-OTX-API-KEY": self._api_key}
        self.save_progress(f"Connecting to endpoint: {url}")
        try:
            r = request_func(url, headers=headers, verify=self._verify, timeout=OTX_DEFAULT_REQUEST_TIMEOUT_SECONDS, **kwargs)
            self.save_progress("Retrieving Details")
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {error_message}"), resp_json)

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param, action_id):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # make rest call
        ret_val, _ = self._make_rest_call(OTX_TEST_CONNECTIVITY_ENDPOINT, action_result)

        if phantom.is_fail(ret_val):
            self.save_progress(OTX_ERROR_CONNECTIVITY_TEST)
            return action_result.get_status()

        # Return success
        self.save_progress(OTX_SUCC_CONNECTIVITY_TEST)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_domain_reputation(self, param, action_id):
        self.save_progress(f"In action handler for: {action_id}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        domain = param[OTX_JSON_DOMAIN]
        response_type = param.get(OTX_JSON_RESPONSE_TYPE, OTX_JSON_DEFAULT_RESPONSE)
        ret_val = self._validate_response_type(action_result, response_type, OTX_RESPONSE_TYPE_DICT[action_id])
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Check if domain is valid
        if utils.is_domain(domain):
            ret_val, response = self._make_rest_call(OTX_DOMAIN_REPUTATION_ENDPOINT.format(domain, response_type), action_result)
        else:
            return action_result.set_status(phantom.APP_ERROR, OTX_ERROR_MALFORMED_DOMAIN)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        summary = action_result.update_summary({})
        summary[OTX_JSON_NUM_PULSES] = len(response.get(OTX_JSON_PULSE_INFO, {}).get(OTX_JSON_PULSES, []))

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved information for Domain")

    def _is_ip(self, input_ip_address):
        """
        Function that checks given address and return True if address is valid IPv4 or IPV6 address.

        :param input_ip_address: IP address
        :return: status (success/failure)
        """

        try:
            ipaddress.ip_address(input_ip_address)
        except Exception:
            return False
        return True

    def _handle_ip_reputation(self, param, action_id):
        self.save_progress(f"In action handler for: {action_id}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        ip = param[OTX_JSON_IP]
        response_type = param.get(OTX_JSON_RESPONSE_TYPE, OTX_JSON_DEFAULT_RESPONSE)

        # Check and redirect to valid call for the address type
        if utils.is_ip(ip):
            ret_val = self._validate_response_type(action_result, response_type, OTX_RESPONSE_TYPE_DICT[f"{action_id}_ipv4"])
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            ret_val, response = self._make_rest_call(
                OTX_IPV4_REPUTATION_ENDPOINT.format(ip, param.get(OTX_JSON_RESPONSE_TYPE, OTX_JSON_DEFAULT_RESPONSE)), action_result
            )
        elif self._is_ip(ip):
            ret_val = self._validate_response_type(action_result, response_type, OTX_RESPONSE_TYPE_DICT[f"{action_id}_ipv6"])
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            ret_val, response = self._make_rest_call(
                OTX_IPV6_REPUTATION_ENDPOINT.format(ip, param.get(OTX_JSON_RESPONSE_TYPE, OTX_JSON_DEFAULT_RESPONSE)), action_result
            )
        else:
            return action_result.set_status(phantom.APP_ERROR, OTX_ERROR_MALFORMED_IP)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        summary = action_result.update_summary({})
        summary[OTX_JSON_NUM_PULSES] = len(response.get(OTX_JSON_PULSE_INFO, {}).get(OTX_JSON_PULSES, []))

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved information for IP")

    def _handle_file_reputation(self, param, action_id):
        self.save_progress(f"In action handler for: {action_id}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        file_hash = param[OTX_JSON_HASH]
        response_type = param.get(OTX_JSON_RESPONSE_TYPE, OTX_JSON_DEFAULT_RESPONSE)
        ret_val = self._validate_response_type(action_result, response_type, OTX_RESPONSE_TYPE_DICT[action_id])
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # make rest call
        ret_val, response = self._make_rest_call(OTX_FILE_REPUTATION_ENDPOINT.format(file_hash, response_type), action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        summary = action_result.update_summary({})
        summary[OTX_JSON_NUM_PULSES] = len(response.get(OTX_JSON_PULSE_INFO, {}).get(OTX_JSON_PULSES, []))

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved information for File")

    def _handle_url_reputation(self, param, action_id):
        self.save_progress(f"In action handler for: {action_id}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        url = param[OTX_JSON_URL]
        response_type = param.get(OTX_JSON_RESPONSE_TYPE, OTX_JSON_DEFAULT_RESPONSE)
        ret_val = self._validate_response_type(action_result, response_type, OTX_RESPONSE_TYPE_DICT[action_id])
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # make rest call
        ret_val, response = self._make_rest_call(OTX_URL_REPUTATION_ENDPOINT.format(url, response_type), action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        summary = action_result.update_summary({})
        summary[OTX_JSON_NUM_PULSES] = len(response.get(OTX_JSON_PULSE_INFO, {}).get(OTX_JSON_PULSES, []))

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved information for URL")

    def _handle_get_pulses(self, param, action_id):
        self.save_progress(f"In action handler for: {action_id}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        pulse_id = param[OTX_JSON_PULSE_ID]

        # make rest call
        ret_val, response = self._make_rest_call(OTX_GET_PULSES_ENDPOINT.format(pulse_id), action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        summary = action_result.update_summary({})
        summary[OTX_JSON_NUM_INDICATORS] = len(response.get(OTX_JSON_INDICATORS, []))

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", action_id)

        if action_id == OTX_TEST_CONNECTIVITY_ACTION:
            ret_val = self._handle_test_connectivity(param, action_id)

        elif action_id == OTX_DOMAIN_REPUTATION_ACTION:
            ret_val = self._handle_domain_reputation(param, action_id)

        elif action_id == OTX_IP_REPUTATION_ACTION:
            ret_val = self._handle_ip_reputation(param, action_id)

        elif action_id == OTX_FILE_REPUTATION_ACTION:
            ret_val = self._handle_file_reputation(param, action_id)

        elif action_id == OTX_URL_REPUTATION_ACTION:
            ret_val = self._handle_url_reputation(param, action_id)

        elif action_id == OTX_GET_PULSES_ACTION:
            ret_val = self._handle_get_pulses(param, action_id)

        return ret_val

    def initialize(self):
        # Load the state in initialize
        self._state = self.load_state()
        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}

        # get the asset config
        config = self.get_config()

        self._base_url = OTX_BASE_URL
        self._api_key = config.get(OTX_JSON_API_KEY)
        self._verify = config.get("verify_server_cert", True)

        self.set_validator("ipv6", self._is_ip)

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved accross actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == "__main__":
    import argparse
    import sys

    import pudb

    pudb.set_trace()

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
        login_url = f"{BaseConnector._get_phantom_base_url()}login"
        try:
            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=OTX_DEFAULT_REQUEST_TIMEOUT_SECONDS)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = f"csrftoken={csrftoken}"
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=OTX_DEFAULT_REQUEST_TIMEOUT_SECONDS)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print(f"Unable to get session id from the platfrom. Error: {e!s}")
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = AlienvaultOtxv2Connector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
