# File: threatcrowd_connector.py
#
# Copyright (c) 2016-2025 Splunk Inc.
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
# Phantom Imports below
import ipaddress
import json
import os
import sys

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.app import ActionResult, BaseConnector

from threatcrowd_consts import *


try:
    from urllib.parse import unquote
except:
    from urllib import unquote


class ThreatCrowdConnector(BaseConnector):
    # Supported actions
    ACTION_ID_LOOKUP_EMAIL = "lookup_email"
    ACTION_ID_LOOKUP_DOMAIN = "lookup_domain"
    ACTION_ID_LOOKUP_IP = "lookup_ip"
    ACTION_ID_FILE_REPUTATION = "file_reputation"
    ACTION_ID_TEST_CONNECTIVITY = "test_asset_connectivity"

    def __init__(self):
        super().__init__()
        self._proxy = None

    def _is_ipv6(self, input_ip_address):
        """Function that checks given address and returns True if the address is a valid IPV6 address.
        :param input_ip_address: IP address
        :return: status (success/failure)
        """

        ip_address_input = input_ip_address

        # If interface is present in the IP, it will be separated by the %
        if "%" in input_ip_address:
            ip_address_input = input_ip_address.split("%")[0]

        try:
            ipaddress.ip_address(ip_address_input)
        except:
            return False

        return True

    def initialize(self):
        """Called once for every action. All member initializations occur here"""

        config = self.get_config()
        # Get the base URL from the consts file
        self._base_url = THREATCROWD_BASE_URL

        # Initialize the headers here for use elsewhere
        self._headers = {"Accept": "application/json"}

        self.set_validator("ipv6", self._is_ipv6)

        # The URI is initialized and is used in every rest endpoint call
        self._api_uri = THREATCROWD_API_URI
        self._proxy = {}
        env_vars = config.get("_reserved_environment_variables", {})
        if "HTTP_PROXY" in env_vars:
            self._proxy["http"] = env_vars["HTTP_PROXY"]["value"]
        elif "HTTP_PROXY" in os.environ:
            self._proxy["http"] = os.environ.get("HTTP_PROXY")

        if "HTTPS_PROXY" in env_vars:
            self._proxy["https"] = env_vars["HTTPS_PROXY"]["value"]
        elif "HTTPS_PROXY" in os.environ:
            self._proxy["https"] = os.environ.get("HTTPS_PROXY")

        return phantom.APP_SUCCESS

    def _get_error_message_from_exception(self, e):
        """This method is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        error_code = THREATCROWD_ERROR_CODE_UNAVAILABLE
        error_message = THREATCROWD_ERROR_MESSAGE_UNAVAILABLE

        try:
            if e.args:
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_code = THREATCROWD_ERROR_CODE_UNAVAILABLE
                    error_message = e.args[0]
        except:
            pass

        return f"Error Code: {error_code}. Error Message: {error_message}"

    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, THREATCROWD_VALIDATE_INTEGER.format(param=key)), None

                parameter = int(parameter)
            except:
                return action_result.set_status(phantom.APP_ERROR, THREATCROWD_VALIDATE_INTEGER.format(param=key)), None

            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, THREATCROWD_NON_NEG_PARAM.format(param=key)), None
            if not allow_zero and parameter == 0:
                return action_result.set_status(phantom.APP_ERROR, THREATCROWD_NON_ZERO_NON_NEG_INVALID_PARAM.format(param=key)), None

        return phantom.APP_SUCCESS, parameter

    def _process_empty_response(self, action_result):
        return (action_result.set_status(phantom.APP_ERROR, "Received empty response from the server"), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            error_message = unquote(self._get_error_message_from_exception(e))
            return (action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. {error_message}"), None)

        # Check the status code if anything useful was returned
        if (200 <= r.status_code <= 399) and resp_json.get("response_code") == "1":
            return (phantom.APP_SUCCESS, resp_json)

        elif resp_json.get("response_code") == "0":
            return (phantom.APP_ERROR, resp_json)

        else:
            return (action_result.set_status(phantom.APP_ERROR, THREATCROWD_ERROR_SERVER_CONNECTION), resp_json)

    def _process_html_response(self, response, action_result):
        status_code = response.status_code

        if 200 <= status_code <= 399 and self.get_action_identifier() == self.ACTION_ID_LOOKUP_IP:
            # The https://www.threatcrowd.org/searchApi/v2/ip/report/?ip=<<ip_address>>
            # this endpoint returns JSON response for a valid IP addresses but
            # in the content-type it shows HTML so due this we call _process_json_response.
            return self._process_json_response(response, action_result)

        if 200 <= status_code <= 399 and self.get_action_identifier() == self.ACTION_ID_TEST_CONNECTIVITY:
            return (action_result.set_status(phantom.APP_SUCCESS, THREATCROWD_SUCC_CONNECTIVITY_TEST), None)

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove the script, style, footer, navigation and span part from the HTML message
            for element in soup(["script", "style", "footer", "nav", "span"]):
                element.extract()
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")

        return (action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process each 'Content-Type' of response separately

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(action_result)

        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return (action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, params):
        # Build the URL
        if self.get_action_identifier() == self.ACTION_ID_TEST_CONNECTIVITY:
            call_url = f"{self._base_url}"
        else:
            call_url = f"{self._base_url}{self._api_uri}{endpoint}"

        resp_json = {}

        # Make the rest call
        try:
            r = requests.get(call_url, params=params, headers=self._headers, proxies=self._proxy, timeout=30)
        except Exception as e:
            error_message = unquote(self._get_error_message_from_exception(e))
            return (action_result.set_status(phantom.APP_ERROR, f"{THREATCROWD_ERROR_SERVER_CONNECTION} {error_message}"), resp_json)

        return self._process_response(r, action_result)

    def _limit_response(self, response, keys_to_limit, limit):
        """
        This method updates the response based on the provided limit.
        :param response: API response
        :param keys_to_limit: Keys to limit
        :param limit: Limit provided by the user
        :return: Updated response
        """
        for resp, value in list(response.items()):
            # Sometimes the result will have an empty entry. This gets rid of it
            if isinstance(value, list):
                response[resp] = list(filter(None, value))
            if resp in keys_to_limit:
                temp_list = []
                resp_len = len(response[resp])
                for x in range(0, limit):
                    if resp_len > 0 and resp_len > x:
                        temp_list.append(response[resp][x])
                    elif resp_len <= x:
                        break
                response[resp] = temp_list

        return response

    def _lookup_domain(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        # Create an action result to add data to

        action_result = self.add_action_result(ActionResult(param))

        params = {}

        params["domain"] = param[THREATCROWD_JSON_DOMAIN]

        limit = param.get(THREATCROWD_JSON_LIMIT, THREATCROWD_DEFAULT_LIMIT)
        ret_val, limit = self._validate_integer(action_result, limit, THREATCROWD_JSON_LIMIT, True)
        if phantom.is_fail(ret_val):
            self.debug_print("Error occurred while validating the integer")
            return action_result.get_status()

        endpoint = THREATCROWD_DOMAIN_URI

        ret_val, response = self._make_rest_call(endpoint, action_result, params)

        if phantom.is_fail(ret_val):
            if response and "response_code" in response and response["response_code"] == "0":
                self.debug_print("Response code is 0")
                action_result.set_summary({"Message": "Did not receive any information"})
                return action_result.set_status(phantom.APP_SUCCESS)
            self.debug_print("Error response returned from the API")
            return action_result.get_status()

        keys_to_limit = ["hashes", "subdomains", "resolutions"]
        total_res = len(response.get("resolutions", []))

        if limit > 0:
            response = self._limit_response(response, keys_to_limit, limit)

        action_result.add_data(response)
        action_result.update_summary({"total_objects": limit if limit < total_res and limit != 0 else total_res})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _lookup_email(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        # Create an action result to add data to

        action_result = self.add_action_result(ActionResult(param))

        params = {}

        params["email"] = param[THREATCROWD_JSON_EMAIL]

        limit = param.get(THREATCROWD_JSON_LIMIT, THREATCROWD_DEFAULT_LIMIT)
        ret_val, limit = self._validate_integer(action_result, limit, THREATCROWD_JSON_LIMIT, True)
        if phantom.is_fail(ret_val):
            self.debug_print("Error occurred while validating the integer")
            return action_result.get_status()

        endpoint = THREATCROWD_EMAIL_URI

        ret_val, response = self._make_rest_call(endpoint, action_result, params)

        if phantom.is_fail(ret_val):
            if response and "response_code" in response and response["response_code"] == "0":
                self.debug_print("Response code is 0")
                action_result.set_summary({"Message": "Did not receive any information"})
                return action_result.set_status(phantom.APP_SUCCESS)
            self.debug_print("Error response returned from the API")
            return action_result.get_status()

        keys_to_limit = ["domains"]
        total_res = len(response.get("domains", []))

        if limit > 0:
            response = self._limit_response(response, keys_to_limit, limit)

        for resp, _ in list(response.items()):
            temp_list = []
            if resp == "domains":
                for value in list(response[resp]):
                    temp_dict = {"domain": value}
                    temp_list.append(temp_dict)
                response[resp] = temp_list

        action_result.add_data(response)

        action_result.update_summary({"total_objects": limit if limit < total_res and limit != 0 else total_res})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _lookup_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        # Create an action result to add data to

        action_result = self.add_action_result(ActionResult(param))

        params = {}

        params["ip"] = param[THREATCROWD_JSON_IP]

        limit = param.get(THREATCROWD_JSON_LIMIT, THREATCROWD_DEFAULT_LIMIT)
        ret_val, limit = self._validate_integer(action_result, limit, THREATCROWD_JSON_LIMIT, True)
        if phantom.is_fail(ret_val):
            self.debug_print("Error occurred while validating the integer")
            return action_result.get_status()

        endpoint = THREATCROWD_IP_URI

        ret_val, response = self._make_rest_call(endpoint, action_result, params)

        if phantom.is_fail(ret_val):
            if response and "response_code" in response and response["response_code"] == "0":
                self.debug_print("Response code is 0")
                action_result.set_summary({"Message": "Did not receive any information"})
                return action_result.set_status(phantom.APP_SUCCESS)
            self.debug_print("Error response returned from the API")
            return action_result.get_status()

        keys_to_limit = ["resolutions", "hashes"]
        total_res = len(response.get("resolutions", []))

        if limit > 0:
            response = self._limit_response(response, keys_to_limit, limit)

        action_result.add_data(response)

        action_result.update_summary({"total_objects": limit if limit < total_res and limit != 0 else total_res})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _file_reputation(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        # Create an action result
        action_result = self.add_action_result(ActionResult(param))

        # Make an empty params dict in order to pass to the rest call
        params = {}

        # Populate the params
        params["resource"] = param[THREATCROWD_JSON_FILE]

        endpoint = THREATCROWD_FILE_URI

        ret_val, response = self._make_rest_call(endpoint, action_result, params)

        if phantom.is_fail(ret_val):
            if response and "response_code" in response and response["response_code"] == "0":
                self.debug_print("Response code is 0")
                action_result.set_summary({"Message": "Did not receive any information"})
                return action_result.set_status(phantom.APP_SUCCESS)
            self.debug_print("Error response returned from the API")
            return action_result.get_status()

        # Sometimes the scans result will have an empty entry. This gets rid of it
        for resp, value in list(response.items()):
            if isinstance(value, list):
                response[resp] = list(filter(None, value))

        action_result.add_data(response)

        action_result.update_summary({"total_objects": len(response.get("scans", []))})

        return action_result.set_status(phantom.APP_SUCCESS)

    def test_asset_connectivity(self, param):
        # Create an action result to add data to

        action_result = self.add_action_result(ActionResult(param))

        params = {}

        endpoint = ""

        self.save_progress("Querying base URL for checking connectivity")

        ret_val, response = self._make_rest_call(endpoint, action_result, params)
        if phantom.is_fail(ret_val):
            self.save_progress(THREATCROWD_ERROR_CONNECTIVITY_TEST)
            return action_result.get_status()

        self.save_progress(THREATCROWD_SUCC_CONNECTIVITY_TEST)
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        """This is the function that handles all of the actions"""

        # Gets the action that we are supposed to carry out, and set it in the connection result object
        action = self.get_action_identifier()

        # Initialize it to success by default
        ret_val = phantom.APP_SUCCESS

        # Find the right action
        if action == self.ACTION_ID_LOOKUP_DOMAIN:
            ret_val = self._lookup_domain(param)
        elif action == self.ACTION_ID_LOOKUP_EMAIL:
            ret_val = self._lookup_email(param)
        elif action == self.ACTION_ID_LOOKUP_IP:
            ret_val = self._lookup_ip(param)
        elif action == self.ACTION_ID_FILE_REPUTATION:
            ret_val = self._file_reputation(param)
        elif action == self.ACTION_ID_TEST_CONNECTIVITY:
            ret_val = self.test_asset_connectivity(param)

        return ret_val


if __name__ == "__main__":
    import argparse

    import pudb

    pudb.set_trace()

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
            login_url = ThreatCrowdConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = f"csrftoken={csrftoken}"
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print(f"Unable to get session id from the platform. Error: {e}")
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = ThreatCrowdConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
