# File: apivoid_connector.py
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

import ipaddress
import json
import sys

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup, UnicodeDammit
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from apivoid_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class ApivoidConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None
        self._server_url = None
        self._api_key = None

    @staticmethod
    def _process_empty_response(response, action_result):
        """This function is used to process empty response.

        :param response: Response data
        :param action_result: Object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    @staticmethod
    def _process_html_response(response, action_result):
        """This function is used to process html response.

        :param response: Response data
        :param action_result: Object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

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
        except:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    @staticmethod
    def _process_json_response(response, action_result):
        """This function is used to process json response.

        :param response: Response data
        :param action_result: Object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # Try a json parse
        try:
            resp_json = response.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {e!s}"), None)

        # Please specify the status codes here
        if 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {} Data from server: {}".format(
            response.status_code, response.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, response, action_result):
        """This function is used to process html response.

        :param response: Response data
        :param action_result: Object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": response.status_code})
            action_result.add_debug_data({"r_text": response.text})
            action_result.add_debug_data({"r_headers": response.headers})

        # Process a json response
        if "json" in response.headers.get("Content-Type", ""):
            return self._process_json_response(response, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in response.headers.get("Content-Type", ""):
            return self._process_html_response(response, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not response.text:
            return self._process_empty_response(response, action_result)

        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            response.status_code, response.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, json=None, data=None, method="get"):
        """This function is used to make the REST call.

        :param endpoint: REST endpoint that needs to be called
        :param action_result: Object of ActionResult class
        :param headers: Request headers
        :param params: Request parameters
        :param json: Request JSON
        :param data: Request body
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :return: Status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        resp_json = None

        params.update({"key": self._api_key})

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to make REST call
        url = APIVOID_ACTUAL_URL.format(base_url=self._server_url, endpoint=endpoint)

        try:
            response = request_func(url, json=json, data=data, headers=headers, params=params)
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {e!s}"), resp_json)

        return self._process_response(response, action_result)

    def _handle_test_connectivity(self, param):
        """This function is used to handle the test connectivity action.

        :param param: Dictionary of input parameters
        :return: Status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress(APIVOID_CONNECTIVITY_MSG)

        params = dict()
        params[APIVOID_CONST_STATS] = ""

        # make rest call
        ret_val, response = self._make_rest_call(endpoint=APIVOID_TEST_CONNECTIVITY_ENDPOINT, action_result=action_result, params=params)

        if phantom.is_fail(ret_val):
            self.save_progress(APIVOID_TEST_CONNECTIVITY_FAIL_MSG)
            return action_result.get_status()

        if response.get("error"):
            self.save_progress(response.get("error"))
            self.save_progress(APIVOID_TEST_CONNECTIVITY_FAIL_MSG)
            return action_result.set_status(phantom.APP_ERROR)

        self.save_progress(APIVOID_TEST_CONNECTIVITY_PASS_MSG)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_cert_info(self, param):
        """This function is used to handle get cert info action.

        :param param: Dictionary of input params
        :return: status (success/failed)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        domain = param[APIVOID_CONST_DOMAIN]

        params = dict()
        params[APIVOID_CONST_HOST] = domain

        ret_val, response = self._make_rest_call(endpoint=APIVOID_SSL_INFO_ENDPOINT, action_result=action_result, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if "data" in response:
            action_result.add_data(response)
        elif "error" in response:
            self.save_progress(response.get("error"))
            return action_result.set_status(phantom.APP_ERROR, response.get("error"))

        self.save_progress("")
        summary = action_result.update_summary({})
        summary["certificate_found"] = response.get("data", {}).get("certificate", {}).get("found")

        return action_result.set_status(phantom.APP_SUCCESS, APIVOID_GET_CERT_INFO_SUCCESS_MSG.format(domain=domain))

    def _process_reputation_data(self, action_result, data):
        """This function is used to process reputation data.

        :param action_result: Object of ActionResult class
        :param data: Dictionary of received data
        :return: processed_data: Dictionary of processed data
        """

        processed_data = dict()

        if not data:
            return processed_data

        if self.get_action_identifier() == "domain_reputation":
            processed_data["alexa_top_10k"] = data.get("alexa_top_10k")
            processed_data["alexa_top_100k"] = data.get("alexa_top_100k")
            processed_data["alexa_top_250k"] = data.get("alexa_top_250k")
            processed_data["most_abused_tld"] = data.get("most_abused_tld")
            processed_data["domain_length"] = data.get("domain_length")
        processed_data["detections"] = data.get("blacklists", {}).get("detections")
        processed_data["engines_count"] = data.get("blacklists", {}).get("engines_count")
        processed_data["detection_rate"] = data.get("blacklists", {}).get("detection_rate")
        processed_data["scantime"] = data.get("blacklists", {}).get("scantime")

        engines_list = []
        engines_data = data.get("blacklists", {}).get("engines")
        for engine in engines_data:
            engines_list.append(engines_data[engine])

        processed_data["engines"] = engines_list

        return processed_data

    def _handle_domain_reputation(self, param):
        """This function is used to handle domain reputation info action.

        :param param: Dictionary of input params
        :return: status (success/failed)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        domain = param[APIVOID_CONST_DOMAIN]

        params = dict()
        params[APIVOID_CONST_HOST] = domain

        ret_val, response = self._make_rest_call(endpoint=APIVOID_DOMAIN_REPUTATION_ENDPOINT, action_result=action_result, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if response.get("error"):
            self.save_progress(response.get("error"))
            return action_result.set_status(phantom.APP_ERROR, response.get("error"))

        processed_data = None
        if response.get("data"):
            data = response.get("data").get("report")
            processed_data = self._process_reputation_data(action_result, data)

        if processed_data:
            action_result.add_data(processed_data)
        else:
            return action_result.set_status(phantom.APP_ERROR, APIVOID_NO_ENGINES_FOUND_MSG)

        summary = action_result.update_summary({})
        summary["detections"] = processed_data.get("detections")
        summary["engines_count"] = processed_data.get("engines_count")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_ip_reputation(self, param):
        """This function is used to handle domain reputation info action.

        :param param: Dictionary of input params
        :return: status (success/failed)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        ip = param[APIVOID_CONST_IP]

        try:
            ipaddress.ip_address(UnicodeDammit(ip).unicode_markup)
        except:
            return action_result.set_status(phantom.APP_ERROR, APIVOID_INVALID_IP_MSG.format(ip=ip))

        params = dict()
        params[APIVOID_CONST_IP] = ip

        ret_val, response = self._make_rest_call(endpoint=APIVOID_IP_REPUTATION_ENDPOINT, action_result=action_result, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if response.get("error"):
            self.save_progress(response.get("error"))
            return action_result.set_status(phantom.APP_ERROR, response.get("error"))

        processed_data = None
        if response.get("data"):
            data = response.get("data").get("report")
            processed_data = self._process_reputation_data(action_result, data)

        if processed_data:
            action_result.add_data(processed_data)
        else:
            return action_result.set_status(phantom.APP_ERROR, APIVOID_NO_ENGINES_FOUND_MSG)

        summary = action_result.update_summary({})
        summary["detections"] = processed_data.get("detections")
        summary["engines_count"] = processed_data.get("engines_count")

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        """This function gets current action identifier and calls member function of its own to handle the action.

        :param param: dictionary which contains information about the actions to be executed
        :return: status success/failure
        """

        self.debug_print("action_id", self.get_action_identifier())

        # Dictionary mapping each action with its corresponding actions
        action_mapping = {
            "test_connectivity": self._handle_test_connectivity,
            "domain_reputation": self._handle_domain_reputation,
            "get_cert_info": self._handle_get_cert_info,
            "ip_reputation": self._handle_ip_reputation,
        }

        action = self.get_action_identifier()
        action_execution_status = phantom.APP_SUCCESS

        if action in list(action_mapping.keys()):
            action_function = action_mapping[action]
            action_execution_status = action_function(param)

        return action_execution_status

    def initialize(self):
        """This is an optional function that can be implemented by the AppConnector derived class. Since the
        configuration dictionary is already validated by the time this function is called, it's a good place to do any
        extra initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS.

        :return: status (success/failure)
        """

        self._state = self.load_state()

        # get the asset config
        config = self.get_config()

        self._server_url = config[APIVOID_CONFIG_SERVER_URL].strip("/")
        self._api_key = config[APIVOID_CONFIG_APIKEY]

        return phantom.APP_SUCCESS

    def finalize(self):
        """This function gets called once all the param dictionary elements are looped over and no more handle_action
        calls are left to be made. It gives the AppConnector a chance to loop through all the results that were
        accumulated by multiple handle_action function calls and create any summary if required. Another usage is
        cleanup, disconnect from remote devices etc.

        :return: status (success/failure)
        """

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
        login_url = "{}{}".format(BaseConnector._get_phantom_base_url(), "login")

        try:
            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=APIVOID_DEFAULT_REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = f"csrftoken={csrftoken}"
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=APIVOID_DEFAULT_REQUEST_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = ApivoidConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
