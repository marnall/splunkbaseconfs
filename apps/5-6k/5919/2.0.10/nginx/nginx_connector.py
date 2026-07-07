# File: nginx_connector.py
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
# Phantom App imports
import json
import sys

import phantom.app as phantom

# Usage of the consts file is recommended
# from nginx_consts import *
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector


DEFAULT_REQUEST_TIMEOUT = 30  # in seconds


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class NginxConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._auth = None
        self._state = None
        self._base_url = None

    def initialize(self):
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()

        self._auth = (config["username"], config["password"])

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

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

        resp_json = r.json()

        if "error" in resp_json:
            error = resp_json["error"].get("text", "unknown error")
        else:
            error = r.text.replace("{", "{{").replace("}", "}}")

        # You should process the error returned in the json
        message = f"Error from server. Status Code: {r.status_code} Message from server: {error}"

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
        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = self._base_url + endpoint

        try:
            r = request_func(url, auth=self._auth, verify=config.get("verify_server_cert", False), **kwargs)
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {e!s}"), resp_json)

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param, action_result):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        self.save_progress("Querying info about NGINX instance to test connectivity")

        ret_val, response = self._make_rest_call("/nginx", action_result)

        # Check for failure
        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_remove_server(self, param, action_result):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        upstream_name = param["upstream_name"]
        server_id = param["server_id"]

        # make rest call
        ret_val, response = self._make_rest_call(f"/http/upstreams/{upstream_name}/servers/{server_id}", action_result, method="delete")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress("Successfully removed server")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully removed server")

    def _handle_add_server(self, param, action_result):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        upstream_name = param["upstream_name"]
        server_ip = param["ip"]

        # make rest call
        ret_val, response = self._make_rest_call(
            f"/http/upstreams/{upstream_name}/servers", action_result, method="post", json={"server": server_ip}
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        summary = action_result.update_summary({})
        summary["server_id"] = response["id"]

        self.save_progress("Successfully added server")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully added server")

    def _patch_server(self, action_result, param, down):
        upstream_name = param["upstream_name"]
        server_id = param["server_id"]

        # make rest call
        ret_val, response = self._make_rest_call(
            f"/http/upstreams/{upstream_name}/servers/{server_id}", action_result, method="patch", json={"down": down}
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, "Server successfully updated")

    def _handle_disable_server(self, param, action_result):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        self.save_progress("")
        return self._patch_server(action_result, param, True)

    def _handle_enable_server(self, param, action_result):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        self.save_progress("")
        return self._patch_server(action_result, param, False)

    def _handle_describe_server(self, param, action_result):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        upstream_name = param["upstream_name"]
        server_id = param["server_id"]

        # make rest call
        ret_val, response = self._make_rest_call(f"/http/upstreams/{upstream_name}/servers/{server_id}", action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        self.save_progress("Successfully retrieved server info")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved server info")

    def _handle_list_servers(self, param, action_result):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        upstream_name = param["upstream_name"]

        # make rest call
        ret_val, response = self._make_rest_call(f"/http/upstreams/{upstream_name}", action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        for peer in response["peers"]:
            action_result.add_data(peer)

        summary = action_result.update_summary({})
        summary["num_servers"] = len(action_result.get_data())

        self.save_progress("Successfully listed server")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_upstreams(self, param, action_result):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # make rest call
        ret_val, response = self._make_rest_call("/http/upstreams", action_result, params=None, headers=None)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Refactor data and add the response into the data section
        for k, v in list(response.items()):
            v.pop("peers")
            action_result.add_data(v)

        summary = action_result.update_summary({})
        summary["num_upstreams"] = len(response)

        self.save_progress("Successfully list upstreams")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _set_base_url(self, param):
        base_url = param.get("url", self.get_config().get("base_url"))

        if not base_url:
            return phantom.APP_ERROR

        self._base_url = "{}api/4".format(base_url + ("" if base_url.endswith("/") else "/"))

        return phantom.APP_SUCCESS

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", action_id)

        action_result = self.add_action_result(ActionResult(dict(param)))
        if phantom.is_fail(self._set_base_url(param)):
            error_message = "Please set either a base_url in the asset configuration or a url in the action parameters"
            return action_result.set_status(phantom.APP_ERROR, error_message)

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param, action_result)
        elif action_id == "remove_server":
            ret_val = self._handle_remove_server(param, action_result)
        elif action_id == "add_server":
            ret_val = self._handle_add_server(param, action_result)
        elif action_id == "disable_server":
            ret_val = self._handle_disable_server(param, action_result)
        elif action_id == "enable_server":
            ret_val = self._handle_enable_server(param, action_result)
        elif action_id == "describe_server":
            ret_val = self._handle_describe_server(param, action_result)
        elif action_id == "list_servers":
            ret_val = self._handle_list_servers(param, action_result)
        elif action_id == "list_upstreams":
            ret_val = self._handle_list_upstreams(param, action_result)

        return ret_val


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
            login_url = NginxConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=DEFAULT_REQUEST_TIMEOUT)

            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = NginxConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
