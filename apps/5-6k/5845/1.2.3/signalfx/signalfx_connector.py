# File: signalfx_connector.py
#
# Copyright (c) 2021-2025 Splunk Inc.
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

import json

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
from signalfx_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class SignalfxConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = None
        error_msg = ERROR_MSG_UNAVAILABLE

        self.error_print("Error occurred.", e)

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except Exception as e:
            self.error_print(f"Error occurred while fetching exception information. Details: {e!s}")

        if not error_code:
            error_text = f"Error Message: {error_msg}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_msg}"

        return error_text

    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
        try:
            if not float(parameter).is_integer():
                return action_result.set_status(phantom.APP_ERROR, VALID_INTEGER_MSG.format(key=key)), None
            parameter = int(parameter)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, VALID_INTEGER_MSG.format(key=key)), None
        if parameter <= 0:
            if allow_zero:
                if parameter < 0:
                    return action_result.set_status(phantom.APP_ERROR, NON_NEGATIVE_INTEGER_MSG.format(key=key)), None
            else:
                return action_result.set_status(phantom.APP_ERROR, POSITIVE_INTEGER_MSG.format(key=key)), None

        return phantom.APP_SUCCESS, parameter

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, f"Status code: {response.status_code}. Empty response and no information in the header"),
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

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            error_text = self._get_error_message_from_exception(e)
            error_message = f"Unable to parse JSON response. Error: {error_text}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), None)

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

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        if endpoint == "/v2/event":
            url = "{}{}".format(str(self._base_url).replace("api", "ingest"), endpoint)
        else:
            url = f"{self._base_url}{endpoint}"

        try:
            r = request_func(url, verify=config.get("verify_server_cert", False), **kwargs)
        except requests.exceptions.InvalidSchema:
            error_message = f"Error connecting to server. No connection adapters were found for {url}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), resp_json)
        except requests.exceptions.InvalidURL:
            error_message = f"Error connecting to server. Invalid URL {url}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), resp_json)
        except Exception as e:
            error_text = self._get_error_message_from_exception(e)
            error_message = f"Error Connecting to server. {error_text}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), resp_json)

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to endpoint")

        # make rest call
        ret_val, response = self._make_rest_call("/v2/dimension", action_result, params=None, headers=self._headers)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_run_query(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        query_string = param["query"]

        params = {"query": query_string}

        ret_val, response = self._make_rest_call("/v2/dimension", action_result, params=params, headers=self._headers)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        summary = action_result.update_summary({})
        summary["total_results"] = response.get("count", 0)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_observability_event(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        headers = self._headers
        headers.update({"Content-Type": "application/json"})

        dimensions = param.get("dimensions")
        title = param.get("title")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            data_blob = [{"category": "Splunk SOAR", "eventType": title}]
            if dimensions:
                dimensions = json.loads(dimensions)
                data_blob[0]["dimensions"] = dimensions
        except Exception as dimensions:
            error_message = f"Error converting dimensions to JSON. {dimensions}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), dimensions)

        json_blob = json.dumps(data_blob)

        # Show request body for easier troubleshooting
        self.save_progress(f"Request body: {json_blob!s}")

        # make rest call
        ret_val, response = self._make_rest_call("/v2/event", action_result, method="post", headers=headers, data=json_blob)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        if response == "OK":
            self.save_progress("Observability event sent")
            return action_result.set_status(phantom.APP_SUCCESS, "Observability event sent")

    def _handle_clear_incident(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = "{}{}{}".format("/v2/incident/", param["incidentid"], "/clear")
        ret_val, response = self._make_rest_call(endpoint, action_result, method="put", headers=self._headers)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, "Resolved Incident successfully")

    def _handle_get_incident(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = "{}{}".format("/v2/incident/", param["incidentid"])
        ret_val, response = self._make_rest_call(endpoint, action_result, headers=self._headers)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, "Incident details fetched successfully")

    def _paginator(self, action_result, user_limit, params, offset=0):
        incident_list = list()

        while True:
            params["limit"] = PAGE_SIZE
            params["offset"] = offset

            ret_val, response = self._make_rest_call("/v2/incident", action_result, headers=self._headers, params=params)
            if phantom.is_fail(ret_val):
                return RetVal(action_result.get_status(), None)

            if not response:
                return RetVal(phantom.APP_SUCCESS, incident_list)

            try:
                incident_list.extend(response)
            except Exception:
                return RetVal(action_result.set_status(phantom.APP_ERROR, "Failed to parse the response"), None)

            if len(incident_list) >= user_limit:
                return RetVal(phantom.APP_SUCCESS, incident_list[:user_limit])

            offset += PAGE_SIZE
            """
            This is because the API currently returns a '500' error when queried for an alert with index value greater than 10000
            """
            if offset + PAGE_SIZE > 10000:
                break

        return RetVal(phantom.APP_SUCCESS, incident_list)

    def _handle_list_incidents(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        params = {}
        params["includeResolved"] = param.get("include_resolved", False)
        limit = param.get("limit", PAGE_SIZE)

        # Validate 'limit' action parameter
        ret_val, limit = self._validate_integer(action_result, limit, LIMIT_PARAM_KEY)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, incident_list = self._paginator(action_result, limit, params)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        count = 0
        try:
            if incident_list:
                count = len(incident_list)
                action_result.update_data(incident_list)
        except Exception as e:
            error_text = self._get_error_message_from_exception(e)
            error_msg = f"Failed to parse the response data. {error_text}"
            return action_result.set_status(phantom.APP_ERROR, error_msg)

        summary = action_result.update_summary({})
        summary["total_incidents"] = count
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print(f"action_id: {action_id}")

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "run_query":
            ret_val = self._handle_run_query(param)

        elif action_id == "observability_event":
            ret_val = self._handle_observability_event(param)

        elif action_id == "clear_incident":
            ret_val = self._handle_clear_incident(param)

        elif action_id == "get_incident":
            ret_val = self._handle_get_incident(param)

        elif action_id == "list_incidents":
            ret_val = self._handle_list_incidents(param)
        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()

        self._base_url = config["base_url"].strip("/")
        self._token = config["token"]
        self._headers = {"X-SF-TOKEN": self._token}
        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
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
        try:
            login_url = BaseConnector._get_phantom_base_url() + "login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=DEFAULT_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print(f"Unable to get session id from the platform. Error: {e!s}")
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = SignalfxConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
