# File: jupiterone_connector.py
#
# Copyright (c) JupiterOne Inc., 2022-2025
#
# This unpublished material is proprietary to JupiterOne.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of JupiterOne.
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
import sys

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from jupiterone_consts import *


class RetVal(tuple):
    """Represent a class to create a tuple."""

    def __new__(cls, val1, val2=None):
        """Create a tuple from the provided values."""
        return tuple.__new__(RetVal, (val1, val2))


class JupiteroneConnector(BaseConnector):
    """
    Represent a connector module that implements the actions that are provided by the app.

    JupiteroneConnector is a class that is derived from the BaseConnector class.
    """

    def __init__(self):
        """Initialize global variables."""
        # Call the BaseConnectors init first
        super().__init__()

        self._state = {}
        self._account_id = None
        self._api_key = None
        self._headers = {}

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.

        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_msg = ERR_MSG_UNAVAILABLE

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except Exception:
            pass

        if not error_code:
            error_text = f"Error Message: {error_msg}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_msg}"

        return error_text

    def _process_empty_response(self, response, action_result):
        """
        Process empty response.

        :param response: response object
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, JUPITERONE_ERR_EMPTY_RESPONSE.format(response.status_code)), None)

    def _process_html_response(self, response, action_result):
        """
        Process html response.

        :param response: response object
        :param action_result: object of Action Result
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
        except Exception:
            error_text = JUPITERONE_UNABLE_TO_PARSE_ERR_DETAIL

        if not error_text:
            error_text = "Empty response and no information received"
        message = f"Status Code: {status_code}. Data from server: {error_text}"

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _get_error_from_response(self, status_code, resp_json):
        error = resp_json.get("error")
        errors_list = resp_json.get("errors", [])
        try:
            if error:
                message = f"Error from server. Status Code: {status_code}. Error Details: {error}"
                return message

            if errors_list and isinstance(errors_list, list):
                error_msg = ""
                for errors in errors_list:
                    if errors.get("code"):
                        error_msg += "{} - ".format(errors.get("code"))
                    if errors.get("message"):
                        error_msg += "{}. ".format(errors.get("message"))
                if error_msg:
                    message = "Error from server. Error Details: {}".format(error_msg.strip(". "))
                    return message
        except Exception:
            pass

        return None

    def _process_json_response(self, r, action_result):
        """
        Process json response.

        :param r: response object
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """
        status_code = r.status_code
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            error_msg = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, JUPITERONE_ERR_UNABLE_TO_PARSE_JSON_RESPONSE.format(error_msg)), None)

        message = self._get_error_from_response(status_code, resp_json)
        if message:
            return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

        # Please specify the status codes here
        if 200 <= status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {} Data from server: {}".format(status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        """
        Process API response.

        :param r: response object
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """
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

    def _make_rest_call(self, url, action_result, headers=None, params=None, data=None, json=None, method="post", verify=True):
        """
        Make the REST call to the app.

        :param url: URL of the resource
        :param action_result: object of ActionResult class
        :param headers: request headers
        :param params: request parameters
        :param data: request body
        :param json: JSON object
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :param verify: Verify server certificate
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """
        if not headers:
            headers = self._headers

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        try:
            r = request_func(url, verify=verify, data=data, json=json, headers=headers, params=params, timeout=60)
        except Exception as e:
            error_msg = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, JUPITERONE_ERR_CONNECTING_TO_SERVER.format(error_msg)), resp_json)

        return self._process_response(r, action_result)

    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
        """
        Validate an integer.

        :param action_result: Action result or BaseConnector object
        :param parameter: input parameter
        :param key: input parameter message key
        :allow_zero: whether zero should be considered as valid value or not
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS, integer value of the parameter or None in case of failure
        """
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return (action_result.set_status(phantom.APP_ERROR, JUPITERONE_VALID_INT_MSG.format(key)), None)

                parameter = int(parameter)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, JUPITERONE_VALID_INT_MSG.format(key)), None

            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, JUPITERONE_NON_NEG_INT_MSG.format(key)), None

            if not allow_zero and parameter == 0:
                return (action_result.set_status(phantom.APP_ERROR, JUPITERONE_NON_NEG_NON_ZERO_INT_MSG.format(key)), None)

        return phantom.APP_SUCCESS, parameter

    def _handle_test_connectivity(self, param):
        """
        Validate the asset configuration for connectivity using supplied configuration.

        :param param: dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to JupiterOne")

        query = """{
        allEntityCounts
        }
        """
        data = {"query": query, "variables": {}}

        # make rest call
        ret_val, response = self._make_rest_call(JUPITERONE_QUERY_ENDPOINT, action_result, json=data)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress(JUPITERONE_ERR_TEST_CONN_FAILED)
            return action_result.get_status()

        # Return success
        self.save_progress(JUPITERONE_SUCC_TEST_CONN_PASSED)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _paginator(self, action_result, endpoint, json_data, max_results):
        """
        Fetch all the assets using pagination logic.

        :param action_result: object of ActionResult class
        :param endpoint: REST endpoint that needs to appended to the service address
        :param query: query to be passed while calling the API
        :param variables: variables to be considered while calling the API
        :param max_results: maximum number of results to be fetched
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS, successfully fetched results or None in case of failure
        """
        items_list = list()
        while True:
            ret_val, response = self._make_rest_call(action_result=action_result, url=JUPITERONE_QUERY_ENDPOINT, json=json_data, method="post")
            if phantom.is_fail(ret_val):
                return action_result.get_status(), []

            items = response.get("data", {}).get("queryV1", {}).get("data", [])
            if not items:
                break

            items_list.extend(items)

            if len(items_list) >= max_results:
                return phantom.APP_SUCCESS, items_list[:max_results]

            cursor = response.get("data", {}).get("queryV1", {}).get("cursor")
            if not cursor:
                break

            json_data["variables"]["cursor"] = cursor

        return phantom.APP_SUCCESS, items_list

    def _handle_run_query(self, param):
        """
        Fetch query details from the JupiterOne server.

        :param param: dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        self.debug_print("Handling query run action")

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        user_query = param["query"]
        include_deleted = param.get("include_deleted", False)
        max_results = param.get("max_results", JUPITERONE_DEFAULT_LIMIT)
        ret_val, max_results = self._validate_integer(action_result, max_results, "max_results")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        query = """query J1QL(
            $query: String!,
            $cursor: String,
            $includeDeleted: Boolean
            ) {
            queryV1(
                query: $query,
                cursor: $cursor,
                includeDeleted: $includeDeleted
            ) {
                type
                data
                cursor
            }
        }"""
        data = {"query": query, "variables": {"query": user_query, "cursor": "", "includeDeleted": include_deleted}}

        ret_val, results = self._paginator(
            action_result=action_result, endpoint=JUPITERONE_QUERY_ENDPOINT, json_data=data, max_results=max_results
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        result_count = len(results)
        action_result.update_summary({"total_results": result_count})

        if result_count == 0:
            return action_result.set_status(phantom.APP_SUCCESS, JUPITERONE_NO_RESULTS_QUERY_PASSED)

        for result in results:
            action_result.add_data(result)

        self.debug_print("Successfully handled query run action")
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        """
        Get current action identifier and call member function of its own to handle the action.

        :param param: dictionary which contains information about the actions to be executed
        :return: status success/failure
        """
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "run_query":
            ret_val = self._handle_run_query(param)

        return ret_val

    def initialize(self):
        """
        Initialize the global variables with its value and validate it.

        This is an optional function that can be implemented by the AppConnector derived class. Since the
        configuration dictionary is already validated by the time this function is called, it's a good place to do any
        extra initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS or
        phantom.APP_ERROR. If this function returns phantom.APP_ERROR, then AppConnector::handle_action will not get
        called.

        :return: status (success/failure)
        """
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}
            return self.set_status(phantom.APP_ERROR, JUPITERONE_STATE_FILE_CORRUPT_ERR)

        # get the asset config
        config = self.get_config()
        self._api_key = config["api_key"]
        self._account_id = config["account_id"]

        self._headers = {"Authorization": JUPITERONE_AUTHORIZATION_HEADER.format(self._api_key), "JupiterOne-Account": self._account_id}

        return phantom.APP_SUCCESS

    def finalize(self):
        """
        Perform some final operations or clean up operations.

        This function gets called once all the param dictionary elements are looped over and no more handle_action
        calls are left to be made. It gives the AppConnector a chance to loop through all the results that were
        accumulated by multiple handle_action function calls and create any summary if required. Another usage is
        cleanup, disconnect from remote devices etc.

        :return: status (success/failure)
        """
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
            login_url = JupiteroneConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=False, timeout=60)  # nosemgrep
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=False, data=data, headers=headers, timeout=60)  # nosemgrep
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = JupiteroneConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
