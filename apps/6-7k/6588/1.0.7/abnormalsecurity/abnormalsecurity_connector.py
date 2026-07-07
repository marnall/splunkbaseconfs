# File: abnormalsecurity_connector.py
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

import json
import traceback

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
from abnormalsecurity_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class AbnormalSecurityConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()
        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None
        self._basic_auth_token = None

    def initialize(self):
        """Automatically called by the BaseConnector before the calls to the handle_action function"""
        config = self.get_config()

        # Base URL
        self._base_url = config[ABNORMAL_JSON_URL_OAuth].rstrip("/").replace("\\", "/")
        self._basic_auth_token = config[ABNORMAL_AUTHORIZATION_TOKEN]

        # The headers, initialize them here once and use them for all other REST calls
        self._headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self._basic_auth_token}"}

        return phantom.APP_SUCCESS

    def finalize(self):
        return phantom.APP_SUCCESS

    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, ABNORMAL_INVALID_INTEGER_MSG.format(key=key)), None

                parameter = int(parameter)
            except Exception as ex:
                return action_result.set_status(
                    phantom.APP_ERROR, f"{ABNORMAL_INVALID_INTEGER_MSG.format(key=key)}: {self._get_error_message_from_exception(ex)}"
                ), None

            if key == "Limit" and parameter == -1:
                return phantom.APP_SUCCESS, parameter
            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, ABNORMAL_INVALID_INTEGER_MSG.format(key=key)), None
            if not allow_zero and parameter == 0:
                return action_result.set_status(phantom.APP_ERROR, ABNORMAL_INVALID_INTEGER_MSG.format(key=key)), None

        return phantom.APP_SUCCESS, parameter

    def _process_empty_response(self, response, action_result):
        """This function is used to process empty response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """
        if response.status_code == 200 or response.status_code == 204:
            return RetVal(phantom.APP_SUCCESS, f"Status code: {response.status_code}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, ABNORMAL_ERR_EMPTY_RESPONSE.format(code=response.status_code)), None)

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

    def _dump_error_log(self, error, message="Exception occurred."):
        self.error_print(message, dump_object=error)

    def _get_error_message_from_exception(self, e):
        """This method is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = None
        error_msg = ABNORMAL_ERR_MSG_UNAVAILABLE

        self.error_print(f"Traceback: {traceback.format_stack()}")
        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except Exception as ex:
            self._dump_error_log(ex, "Error occurred while fetching exception information")

        if not error_code:
            error_text = f"Error Message: {error_msg}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_msg}"

        return error_text

    def _make_rest_call(self, action_result, endpoint, headers=None, params=None, data=None, json_data=None, method="get"):
        """Function that makes the REST call to the app.

        :param endpoint: REST endpoint that needs to appended to the service address
        :param action_result: object of ActionResult class
        :param headers: request headers
        :param params: request parameters
        :param data: request body
        :param json: JSON object
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        resp_json = None
        if not headers:
            headers = self._headers

        # Create a URL to connect to
        url = f"{self._base_url}{endpoint}"
        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        try:
            resp_json = request_func(url, json=json_data, data=data, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, f"Error connecting to server. Details: {self._get_error_message_from_exception(e)}"
            ), resp_json

        return self._process_response(resp_json, action_result)

    def _paginator(self, action_result, endpoint, params, key):
        custom_resp = {}
        api_params = {}
        custom_resp[key] = []

        if "limit" not in params:
            limit = 100
        else:
            ret_val, limit = self._validate_integer(action_result, params.pop("limit"), "Limit")
            if phantom.is_fail(ret_val):
                return None

        # set default page_size
        api_params["pageSize"] = min(limit, 1000)
        while True:
            ret_val, response = self._make_rest_call(action_result, endpoint, params=api_params)
            if phantom.is_fail(ret_val):
                return None

            if not response[key]:
                return custom_resp

            if len(response[key]) >= limit:
                custom_resp[key].extend(response[key][:limit])
                return custom_resp

            custom_resp[key].extend(response[key])
            limit -= 1000

            if "nextPageNumber" not in response:
                return custom_resp

            api_params["pageNumber"] = response["nextPageNumber"]

    def _handle_list_threats(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        resp = self._paginator(action_result, ABNORMAL_GET_THREATS, param, "threats")
        if resp is None:
            return action_result.get_status()

        action_result.set_summary({"total_threats": len(resp["threats"])})

        self.debug_print("Threats found successfully")
        [action_result.add_data(threat) for threat in resp["threats"]]

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_threat_details(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        resp = self._paginator(action_result, "{}/{}".format(ABNORMAL_GET_THREATS, param.get("threat_id")), param, "messages")
        if resp is None:
            return action_result.get_status()

        action_result.set_summary({"total_threat_details": len(resp["messages"])})

        self.debug_print("Threat details found successfully")
        [action_result.add_data(threat_message) for threat_message in resp["messages"]]

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_abuse_mailboxes(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        resp = self._paginator(action_result, ABNORMAL_GET_ABUSE_MAILBOX, param, "campaigns")
        if resp is None:
            return action_result.get_status()

        action_result.set_summary({"total_abuse_mailboxes": len(resp["campaigns"])})

        self.debug_print("Mailboxes found successfully")
        [action_result.add_data(campaign) for campaign in resp["campaigns"]]
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_threat_status(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        action_status = param.get("action")
        if action_status not in ["remediate", "unremediate"]:
            return action_result.set_status(phantom.APP_ERROR, "Invalid action is given")
        endpoint = "{threats}/{threatid}".format(threats=ABNORMAL_GET_THREATS, threatid=param.get("threat_id"))

        data = {"action": action_status}

        ret_val, resp = self._make_rest_call(action_result, endpoint, json_data=data, method="post")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.debug_print("Action created for update status")
        action_result.add_data(resp)
        return action_result.set_status(phantom.APP_SUCCESS, "Created action for update threat status successfully")

    def _handle_get_threat_status(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = "{}/{}/{}/{}".format(ABNORMAL_GET_THREATS, param.get("threat_id"), ABNORMAL_GET_ACTION_STATUS, param.get("action_id"))
        ret_val, resp = self._make_rest_call(action_result, endpoint)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.debug_print("Status found for given threat")
        action_result.add_data(resp)
        return action_result.set_status(phantom.APP_SUCCESS, "Fetched status successfully")

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        param = {"pageSize": 1}

        self.save_progress("Connecting to endpoint")
        # make rest call
        ret_val, response = self._make_rest_call(action_result, ABNORMAL_GET_THREATS, params=param)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)
        elif action_id == "list_threats":
            ret_val = self._handle_list_threats(param)
        elif action_id == "get_threat_details":
            ret_val = self._handle_get_threat_details(param)
        elif action_id == "list_abuse_mailboxes":
            ret_val = self._handle_list_abuse_mailboxes(param)
        elif action_id == "update_threat_status":
            ret_val = self._handle_update_threat_status(param)
        elif action_id == "get_threat_status":
            ret_val = self._handle_get_threat_status(param)
        return ret_val


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
            login_url = AbnormalSecurityConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=REQUEST_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = AbnormalSecurityConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
