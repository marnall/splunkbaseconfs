# File: ipstack_connector.py
#
# Copyright (c) 2018-2025 Splunk Inc.
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
# Phantom App imports
import ipaddress
import json
import sys

import phantom.app as phantom

# Usage of the consts file is recommended
# from ipstack_consts import *
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector


DEFAULT_REQUEST_TIMEOUT = 30  # in seconds


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class IpstackConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variables to hold a base_url, use_ssl, and an access_key in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None
        self._use_ssl = None
        self._access_key = None

    @staticmethod
    def _process_empty_reponse(response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    @staticmethod
    def _process_html_response(response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except Exception:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    @staticmethod
    def _process_json_response(r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {e!s}"), None)

        # Please specify the status codes here
        # For ipstack, an error may be returned with status code 200
        #   in this case, there will be a 'success': False in the response json
        #   in the case of true success, there is no 'success' key present
        if 200 <= r.status_code < 399 and resp_json.get("success", True):
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

        # Process an HTML resonse, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_reponse(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _is_ip(self, input_ip_address):
        """Function that checks given address and return True if address is valid IPv4 or IPV6 address.

        :param input_ip_address: IP address
        :return: status (success/failure)
        """

        ip_address_input = input_ip_address

        try:
            ipaddress.ip_address(str(ip_address_input))
        except:
            return False

        return True

    def _get_error_message_from_exception(self, e):
        """This function is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        error_msg = "Unknown error occurred. Please check the asset configuration and|or action parameters."
        error_code = "Error code unavailable"
        try:
            if e.args:
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_code = "Error code unavailable"
                    error_msg = e.args[0]
            else:
                error_code = "Error code unavailable"
                error_msg = "Unknown error occurred. Please check the asset configuration and|or action parameters."
        except:
            error_code = "Error code unavailable"
            error_msg = "Unknown error occurred. Please check the asset configuration and|or action parameters."

        return f"Error Code: {error_code}. Error Message: {error_msg}"

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, method="get"):
        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = self._base_url + endpoint

        # Populate params with access_key
        params = {"access_key": self._access_key}

        try:
            r = request_func(url, data=data, headers=headers, params=params)
        except Exception as e:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {self._get_error_message_from_exception(e)}"),
                resp_json,
            )

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Querying a domain to check connectivity")

        # make rest call
        ret_val, response = self._make_rest_call("/ipstack.com", action_result, params=None, headers=None)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_geolocate_ip(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        ip = param["ip"]

        self.save_progress("Querying geolocate IP")
        # make rest call
        ret_val, response = self._make_rest_call(f"/{ip}", action_result, params=None, headers=None)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        # Add the response into the data section
        for key, value in response.items():
            if not value:
                response[key] = None
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        summary["city"] = response.get("city")
        summary["country_code"] = response.get("country_code")

        self.save_progress("Querying geolocate IP succeeded")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_geolocate_domain(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        domain = param["domain"]

        if phantom.is_url(domain):
            domain = phantom.get_host_from_url(domain)

        self.save_progress("Querying geolocate domain")
        # make rest call
        ret_val, response = self._make_rest_call(f"/{domain}", action_result, params=None, headers=None)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        # Fail the action if the type of provided input is not getting identified by the IPStack API,
        # as in that case, provided input is invalid
        if not response["type"]:
            return action_result.set_status(phantom.APP_SUCCESS, "Provided domain was not found. Please provide a valid domain.")

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        summary["city"] = response.get("city")
        summary["country_code"] = response.get("country_code")

        self.save_progress("Querying geolocate domain succeeded")
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "geolocate_ip":
            ret_val = self._handle_geolocate_ip(param)

        elif action_id == "geolocate_domain":
            ret_val = self._handle_geolocate_domain(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()

        self._use_ssl = not not config["use_ssl"]
        self._access_key = config["access_key"].strip()

        if self._use_ssl:
            self._base_url = "https://api.ipstack.com"
        else:
            self._base_url = "http://api.ipstack.com"

        self.set_validator("ipv6", self._is_ip)

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == "__main__":
    import argparse

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
        try:
            print("Accessing the Login page")
            r = requests.get("https://127.0.0.1/login", verify=verify, timeout=DEFAULT_REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = "https://127.0.0.1/login"

            print("Logging into Platform to get the session id")
            r2 = requests.post("https://127.0.0.1/login", verify=verify, data=data, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = IpstackConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
