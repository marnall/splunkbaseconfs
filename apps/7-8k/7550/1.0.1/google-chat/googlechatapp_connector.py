# File: googlechatapp_connector.py

# Copyright (c) Splunk, 2024

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

# Python 3 Compatibility imports
from __future__ import print_function, unicode_literals

import base64
import json

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
from googlechatapp_consts import *


class RetVal(tuple):

    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class GoogleChatAppConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(GoogleChatAppConnector, self).__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None
        self._access_token = None
        self._refresh_token = None
        self._client_id = None
        self._client_secret = None
        self._code = None
        self._redirect_uri = None

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = "Status Code: {0}. Data from server:\n{1}\n".format(status_code, error_text)

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Unable to parse JSON response. Error: {0}".format(str(e))), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), message)

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
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, url, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Invalid method: {0}".format(method)), resp_json)

        try:
            r = request_func(
                url,
                # auth=(username, password),  # basic authentication
                verify=config.get("verify_server_cert", False),
                **kwargs,
            )
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Error Connecting to server. Details: {0}".format(str(e))), resp_json)

        return self._process_response(r, action_result)

    def encode_token(self, token):
        sample_string_bytes = token.encode("ascii")
        base64_bytes = base64.b64encode(sample_string_bytes)
        base64_string = base64_bytes.decode("ascii")
        return base64_string

    def decode_token(self, token_base64):
        base64_bytes = token_base64.encode("ascii")
        sample_string_bytes = base64.b64decode(base64_bytes)
        sample_string = sample_string_bytes.decode("ascii")
        return sample_string

    def _generate_new_access_token(self, action_result, grant_type='"authorization_code"'):
        """This function is used to generate new access token using the code obtained on authorization."""
        token_url = "https://oauth2.googleapis.com/token"

        if grant_type == "refresh_token":
            payload = {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": grant_type,
            }
        else:
            payload = {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": self._code,
                "redirect_uri": self._redirect_uri,
                "grant_type": "authorization_code",
            }

        ret_val, resp_json = self._make_rest_call(action_result=action_result, url=token_url, data=payload, method="post")

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, "Failure in tokenization process {}".format(resp_json))

        try:
            self._access_token = resp_json["access_token"]
        except:
            return action_result.set_status(phantom.APP_ERROR, "There is no access token inside request response: {}".format(resp_json))

        self._state["access_token"] = self.encode_token(resp_json["access_token"])
        if grant_type != "refresh_token":
            self._refresh_token = resp_json.get("refresh_token")
            self._state["refresh_token"] = self.encode_token(resp_json["refresh_token"])

        return phantom.APP_SUCCESS

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Start a token request")
        # make rest call
        ret_val = self._generate_new_access_token(action_result)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Test Connectivity Failed, cannot generate access token")
            return action_result.get_status(phantom.APP_ERROR, "Problem with tokenization")

        # Return success
        self.save_progress("Test Connectivity Passed, token store in state file as encrypted.")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_message(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        gen_ret_val = self._generate_new_access_token(action_result, grant_type="refresh_token")
        if phantom.is_fail(gen_ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            return action_result.get_status(phantom.APP_ERROR, "Problem with Refresh token.")

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        parent = param["parent_space"]
        json_content = {"text": param["text_message"]}

        # Optional values should use the .get() function
        parameters = {}

        if param.get("requestid"):
            parameters.update({"requestid": param.get("requestid")})
        if param.get("messagereplyoption"):
            parameters.update({"messagereplyoption": param.get("messagereplyoption")})
        if param.get("messageid"):
            parameters.update({"messageid": param.get("messageid")})

        headers = {"Authorization": "Bearer " + self._access_token, "Content-Type": "application/json; charset=utf-8"}

        url = self._base_url + "/v1/{}/messages".format(parent)

        # make rest call
        ret_val, response = self._make_rest_call(url, action_result, method="post", params=parameters, headers=headers, json=json_content)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, "Create message request failed: {}".format(response))

        # Add the response into the data section
        action_result.add_data(response)
        self.save_progress("Message sent to {}".format(parent))
        return action_result.set_status(phantom.APP_SUCCESS, "Message sent to {}".format(parent))

    def _handle_read_message(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        gen_ret_val = self._generate_new_access_token(action_result, grant_type="refresh_token")
        if phantom.is_fail(gen_ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            return action_result.get_status(phantom.APP_ERROR, "Problem with Refresh token.")

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        name = param["name"]
        url = self._base_url + "/v1/{}".format(name)

        headers = {"Authorization": "Bearer " + self._access_token, "Content-Type": "application/json; charset=utf-8"}

        # make rest call
        ret_val, response = self._make_rest_call(url, action_result, method="get", params=None, headers=headers)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, "Read message request failed: {}".format(response))

        # Add the response into the data section
        action_result.add_data(response)
        self.save_progress("Reading message {}".format(name))
        return action_result.set_status(phantom.APP_SUCCESS, "Reading message {}".format(name))

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "create_message":
            ret_val = self._handle_create_message(param)

        if action_id == "read_message":
            ret_val = self._handle_read_message(param)

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}
        else:
            if self._state.get("refresh_token"):
                self._refresh_token = self.decode_token(self._state["refresh_token"])
            else:
                self.save_progress(
                    "There is not Refresh token inside the state file, make sure you are runinng test connectivity action \
                                 or do it at first before further app exploration."
                )

        # get the asset config
        config = self.get_config()
        self._client_id = config["client_id"]
        self._client_secret = config["client_secret"]
        self._code = config["code"]
        self._redirect_uri = config["redirect_uri"]

        self._base_url = "https://chat.googleapis.com"

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


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
            login_url = GoogleChatAppConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=FS_DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=FS_DEFAULT_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = GoogleChatAppConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
