# File: checkphish_connector.py
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

# Python 3 Compatibility imports

import json
import sys

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Constants imports
from checkphish_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class CheckphishConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = {}

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._api_url = None
        self._api_key = None

    def _get_error_message_from_exception(self, e):
        """This method is used to get appropriate error messages from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = CHECKPHISH_ERR_CODE_MSG
        error_msg = CHECKPHISH_ERR_MSG_UNAVAILABLE
        try:
            if e.args:
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except:
            pass

        return f"Error Code: {error_code}. Error Message: {error_msg}"

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200 or response.status_code == 204:
            return RetVal(phantom.APP_SUCCESS, {})

        error_msg = f"Status code: {response.status_code}. Empty response and no information in the header"
        return RetVal(
            action_result.set_status(phantom.APP_ERROR, error_msg),
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
        except:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server: {error_text}"

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Unable to parse JSON response. Error: {self._get_error_message_from_exception(e)}",
                ),
                None,
            )

        error_message = resp_json.get("errorMessage")
        if error_message:
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
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"),
                resp_json,
            )

        # Create a URL to connect to
        url = f"{self._api_url}{endpoint}"

        try:
            r = request_func(url, verify=config.get("verify_server_cert", False), **kwargs)
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Error Connecting to server. Details: {self._get_error_message_from_exception(e)}",
                ),
                resp_json,
            )

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        url = "https://bolster.ai"
        scan_type = "quick"

        payload = {
            "apiKey": self._api_key,
            "urlInfo": {"url": url},
            "scanType": scan_type,
        }
        self.save_progress(f"Submitting URL: {url}")

        ret_val, response = self._make_rest_call(
            CHECKPHISH_DETONATE_URL_ENDPOINT,
            action_result,
            method="post",
            params=None,
            headers=None,
            json=payload,
        )

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        self.save_progress("Successfully submitted URL")
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_check_status(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        job_id = param["job_id"]

        payload = {"apiKey": self._api_key, "jobID": job_id, "insights": True}

        ret_val, response = self._make_rest_call(
            CHECKPHISH_CHECK_STATUS_ENDPOINT,
            action_result,
            method="post",
            params=None,
            headers=None,
            json=payload,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        summary = action_result.update_summary({})

        summary["job_id"] = response.get("job_id")
        summary["status"] = response.get("status")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_detonate_url(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        url = param["url"]
        scan_type = param["scan_type"]

        payload = {
            "apiKey": self._api_key,
            "urlInfo": {"url": url},
            "scanType": scan_type,
        }

        ret_val, response = self._make_rest_call(
            CHECKPHISH_DETONATE_URL_ENDPOINT,
            action_result,
            method="post",
            params=None,
            headers=None,
            json=payload,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        summary = action_result.update_summary({})

        summary["job_id"] = response.get("jobID")

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "check_status":
            ret_val = self._handle_check_status(param)

        elif action_id == "detonate_url":
            ret_val = self._handle_detonate_url(param)

        return ret_val

    def initialize(self):
        self._state = self.load_state()

        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}
            return self.set_status(phantom.APP_ERROR, CHECKPHISH_STATE_FILE_CORRUPT_ERR)

        config = self.get_config()

        self._api_url = config["api_url"]
        self._api_key = config["api_key"]

        return phantom.APP_SUCCESS

    def finalize(self):
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

    if args.username and args.password:
        login_url = BaseConnector._get_phantom_base_url() + "login"
        try:
            print("Accessing the Login page")
            r = requests.get(login_url, timeout=60)
            csrftoken = r.cookies["csrftoken"]
            data = {"username": args.username, "password": args.password, "csrfmiddlewaretoken": csrftoken}
            headers = {"Cookie": f"csrftoken={csrftoken}", "Referer": login_url}

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, data=data, headers=headers, timeout=60)
            session_id = r2.cookies["sessionid"]

        except Exception as e:
            print(f"Unable to get session id from the platform. Error: {e!s}")
            sys.exit(1)

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=" " * 4))

        # Create the connector class object
        connector = CheckphishConnector()

        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
