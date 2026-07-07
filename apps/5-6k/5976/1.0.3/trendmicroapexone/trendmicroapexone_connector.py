# File: trendmicroapexone_connector.py
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
#
#
# Python 3 Compatibility imports

import base64
import hashlib
import json
import time

import jwt

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from trendmicroapexone_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class TrendMicroApexOneConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        self._base_url = None
        self._application_id = None
        self._api_key = None

    def _get_error_message_from_exception(self, e):
        """This method is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        try:
            if e.args:
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_code = APEX_ONE_ERR_CODE_MSG
                    error_msg = e.args[0]
            else:
                error_code = APEX_ONE_ERR_CODE_MSG
                error_msg = APEX_ONE_ERR_MSG_UNAVAILABLE
        except:
            error_code = APEX_ONE_ERR_CODE_MSG
            error_msg = APEX_ONE_ERR_MSG_UNAVAILABLE

        try:
            if error_code in APEX_ONE_ERR_CODE_MSG:
                error_text = f"Error Message: {error_msg}"
            else:
                error_text = f"Error Code: {error_code}. Error Message: {error_msg}"
        except:
            self.debug_print(APEX_ONE_PARSE_ERR_MSG)
            error_text = APEX_ONE_PARSE_ERR_MSG

        return error_text

    def _create_checksum(self, http_method, raw_url, headers, request_body):
        """This method is used to derive the checksum that is sent  with the HTTP request so that the request is accepted by the API"""
        string_to_hash = f"{http_method.upper()}|{raw_url.lower()}|{headers}|{request_body}"
        base64_string = base64.b64encode(hashlib.sha256(str.encode(string_to_hash)).digest()).decode("utf-8")
        return base64_string

    def _create_jwt_token(
        self,
        application_id,
        api_key,
        http_method,
        raw_url,
        headers,
        request_body,
        iat=time.time(),
        algorithm="HS256",
        version="V1",
    ):
        """This method is used to convert request and auth information into a JWT token to use with the request"""
        payload = {
            "appid": application_id,
            "iat": iat,
            "version": version,
            "checksum": self._create_checksum(http_method, raw_url, headers, request_body),
        }
        token = jwt.encode(payload, api_key, algorithm=algorithm)
        return token

    def _process_empty_response(self, response, action_result):
        """This function is used to process empty responses"""
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, f"Status Code: {response.status_code}. Empty response, no information in header"), None
        )

    def _process_html_response(self, response, action_result):
        """This function is used to process html responses"""
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
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
        """This function is used to process json responses"""
        try:
            resp_json = r.json()
        except Exception as e:
            err = self._get_error_message_from_exception(e)
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Unable to parse JSON response. Error: {err}",
                ),
                None,
            )

        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        """This function is used to process responses from the API"""
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

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
        """This function is used to issue rest requests"""

        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = f"{self._base_url}{endpoint}"

        # Add authentication information
        token = self._create_jwt_token(
            self._application_id,
            self._api_key,
            method,
            endpoint,
            kwargs.get("headers", ""),
            kwargs.get("data", ""),
            time.time(),
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json;charset=utf-8",
        }

        try:
            r = request_func(
                url,
                verify=config.get("verify_server_cert", False),
                headers=headers,
                **kwargs,
            )
        except requests.exceptions.ConnectionError:
            error_reason = f"Error Details: Connection refused from the server for URL: {url}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_reason), resp_json)
        except Exception as e:
            error_reason = self._get_error_message_from_exception(e)

            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {error_reason}"), resp_json)

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to endpoint")

        endpoint = APEX_ONE_PRODUCT_AGENTS_ENDPOINT

        self.save_progress("Retrieving list of agents")

        ret_val, response = self._make_rest_call(endpoint, action_result, params=None)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        self.save_progress("Test Connectivity Passed")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _modify_device(self, action_result, ip_hostname, action="cmd_isolate_agent"):
        endpoint = APEX_ONE_PRODUCT_AGENTS_ENDPOINT

        payload = {"act": action, "allow_multiple_match": False}

        if phantom.is_ip(ip_hostname):
            payload["ip_address"] = ip_hostname
        else:
            payload["host_name"] = ip_hostname

        req_payload = json.dumps(payload)

        ret_val, response = self._make_rest_call(endpoint, action_result, "post", data=req_payload)

        return ret_val, response

    def _handle_quarantine_device(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        ip_hostname = param["ip_hostname"]

        ret_val, response = self._modify_device(action_result, ip_hostname, action="cmd_isolate_agent")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if response and not response.get("result_content"):
            return action_result.set_status(phantom.APP_ERROR, APEX_ONE_RESPONSE_EMPTY_MSG)

        try:
            action_result.add_data(response["result_content"][0])

            summary = action_result.update_summary({})
            summary["status"] = response["result_content"][0].get("isolation_status")
            summary["msg"] = response.get("result_description", "")
        except:
            return action_result.set_status(phantom.APP_ERROR, APEX_ONE_ERR_SERVER_RES)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_unquarantine_device(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        ip_hostname = param["ip_hostname"]

        ret_val, response = self._modify_device(action_result, ip_hostname, action="cmd_restore_isolated_agent")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if response and (not response.get("result_content") or response.get("result_code") != 1):
            return action_result.set_status(phantom.APP_ERROR, APEX_ONE_RESPONSE_EMPTY_MSG)

        try:
            action_result.add_data(response["result_content"][0])

            summary = action_result.update_summary({})
            summary["status"] = response["result_content"][0].get("isolation_status")
            summary["msg"] = response.get("result_description", "")
        except:
            return action_result.set_status(phantom.APP_ERROR, APEX_ONE_ERR_SERVER_RES)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_endpoints(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = APEX_ONE_PRODUCT_AGENTS_ENDPOINT

        ret_val, response = self._make_rest_call(endpoint, action_result, params=None)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if response and not response.get("result_content"):
            return action_result.set_status(phantom.APP_ERROR, APEX_ONE_RESPONSE_EMPTY_MSG)

        try:
            action_result.add_data({"endpoints": response["result_content"]})

            summary = action_result.update_summary({})
            summary["total_objects"] = len(response["result_content"])
            summary["msg"] = response.get("result_description", "")
        except:
            return action_result.set_status(phantom.APP_ERROR, APEX_ONE_ERR_SERVER_RES)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_system_info(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        ip_hostname = param["ip_hostname"]

        endpoint = APEX_ONE_PRODUCT_AGENTS_ENDPOINT
        if phantom.is_ip(ip_hostname):
            qs = f"?ip_address={ip_hostname}"
        else:
            qs = f"?host_name={ip_hostname}"

        ret_val, response = self._make_rest_call(f"{endpoint}{qs}", action_result, params=None)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if response and (not response.get("result_content") or response.get("result_code") != 1):
            return action_result.set_status(phantom.APP_ERROR, APEX_ONE_RESPONSE_EMPTY_MSG)

        try:
            action_result.add_data(response["result_content"][0])

            summary = action_result.update_summary({})
            summary["msg"] = response.get("result_description", "")
            summary["total_objects"] = len(response["result_content"])
        except:
            return action_result.set_status(phantom.APP_ERROR, APEX_ONE_ERR_SERVER_RES)

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "quarantine_device":
            ret_val = self._handle_quarantine_device(param)

        elif action_id == "unquarantine_device":
            ret_val = self._handle_unquarantine_device(param)

        elif action_id == "list_endpoints":
            ret_val = self._handle_list_endpoints(param)

        elif action_id == "get_system_info":
            ret_val = self._handle_get_system_info(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()
        self._base_url = config["base_url"].strip("/")
        self._application_id = config["application_id"]
        self._api_key = config["api_key"]

        return phantom.APP_SUCCESS

    def finalize(self):
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
            login_url = TrendMicroApexOneConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, timeout=DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, timeout=DEFAULT_TIMEOUT, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = TrendMicroApexOneConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
