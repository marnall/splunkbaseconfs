# File: zabbix_connector.py
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


import json
import re

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class ZabbixConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"),
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
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Unable to parse JSON response. Error: {e!s}",
                ),
                None,
            )

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
        url = self._base_url + endpoint

        try:
            r = request_func(
                url,
                # auth=(username, password),  # basic authentication
                verify=config.get("verify_server_cert", False),
                **kwargs,
            )
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Error Connecting to server. Details: {e!s}",
                ),
                resp_json,
            )

        return self._process_response(r, action_result)

    def _login(self, action_result, param):
        self.save_progress("Logging in")

        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "user.login",
                "params": {"username": self._username, "password": self._password},
                "id": 1,
            }
        )
        ret_val, response = self._make_rest_call(
            self._endpoint,
            action_result,
            method="post",
            params=None,
            headers=self._headers,
            data=payload,
        )
        auth_token = response.get("result")
        return auth_token

    def _logout(self, action_result, auth_token, param):
        self.save_progress("Logging out")

        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "user.logout",
                "params": [],
                "id": 1,
                "auth": auth_token,
            }
        )
        ret_val, response = self._make_rest_call(
            self._endpoint,
            action_result,
            method="post",
            params=None,
            headers=self._headers,
            data=payload,
        )
        return response

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Connecting to endpoint")

        # make rest call
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "apiinfo.version",
                "auth": None,
                "id": 1,
                "params": {},
            }
        )

        ret_val, response = self._make_rest_call(
            self._endpoint,
            action_result,
            method="post",
            params=None,
            headers=self._headers,
            data=payload,
        )

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_host_info(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        auth_token = self._login(action_result, param=param)

        params = {"filter": {"host": param.get("host")}}
        params["output"] = "extend"
        params["selectItems"] = [
            "itemid",
            "type",
            "name",
            "description",
            "lastvalue",
            "units",
            "value_type",
            "state",
            "status",
        ]

        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "host.get",
                "params": params,
                "auth": auth_token,
                "id": 1,  # This is not important as we're making a single request here
            }
        )

        # make rest call
        ret_val, response = self._make_rest_call(
            self._endpoint,
            action_result,
            method="post",
            params=None,
            headers=self._headers,
            data=payload,
        )

        self._logout(action_result, auth_token, param)
        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            # return action_result.get_status()
            return action_result.set_status(phantom.APP_ERROR, "Action failed while getting host information")

        result = response.get("result")
        items = result[0].get("items")

        host_info = dict()
        for item in items:
            host_info[self._normalize_item_name(item["name"])] = item

        # Add the response into the data section
        action_result.add_data({"host_info": host_info})

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_data"] = len(action_result["data"])

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        self.save_progress("Successfuly fetched host information")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_execute_script(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        auth_token = self._login(action_result, param=param)
        try:
            scriptid = int(param["script"])
        except ValueError:
            scriptid = self._get_script_id_from_name(
                action_result=action_result,
                auth_token=auth_token,
                script_name=param["script"],
            )

        try:
            hostid = int(param["host"])
        except ValueError:
            hostid = self._get_host_id_from_name(
                action_result=action_result,
                auth_token=auth_token,
                host_name=param["host"],
            )

        if not scriptid and hostid:
            ret_val = False
        else:
            params = {"scriptid": scriptid, "hostid": hostid}
            payload = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "script.execute",
                    "params": params,
                    "auth": auth_token,
                    "id": 1,
                }
            )

            # make rest call
            ret_val, response = self._make_rest_call(
                self._endpoint,
                action_result,
                method="post",
                params=None,
                headers=self._headers,
                data=payload,
            )

        self._logout(action_result, auth_token, param)
        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            # return action_result.get_status()
            return action_result.set_status(phantom.APP_ERROR, "Action failed while executing script")

        result = response.get("result")

        # Add the response into the data section
        action_result.add_data({"output": result})

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS, "Action completed successfully")

    def _get_script_id_from_name(self, action_result, auth_token, script_name):
        self.save_progress("Logging in")

        params = {"filter": {"name": [script_name]}, "output": "extend"}
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "script.get",
                "params": params,
                "auth": auth_token,
                "id": 1,
            }
        )
        ret_val, response = self._make_rest_call(
            self._endpoint,
            action_result,
            method="post",
            params=None,
            headers=self._headers,
            data=payload,
        )
        result = response.get("result")
        if len(result) == 1:  # Found exactly ONE matching script
            return result[0].get("scriptid")
        return None

    def _get_host_id_from_name(self, action_result, auth_token, host_name):
        self.save_progress("Logging in")

        params = {"filter": {"name": [host_name]}, "output": "extend"}
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "host.get",
                "params": params,
                "auth": auth_token,
                "id": 1,
            }
        )
        ret_val, response = self._make_rest_call(
            self._endpoint,
            action_result,
            method="post",
            params=None,
            headers=self._headers,
            data=payload,
        )
        result = response.get("result")
        if len(result) == 1:  # Found exactly ONE matching script
            return result[0].get("hostid")
        return None

    def _normalize_item_name(self, item):
        substitutions = dict()
        substitutions["%"] = "perc"
        substitutions["/:"] = "disk"
        substitutions["[ ]"] = "_"
        substitutions["[^a-zA-Z0-9-_ \n.]"] = ""
        for k in substitutions:
            item = re.sub(k, substitutions[k], item).lower()
        return item

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "get_host_info":
            ret_val = self._handle_get_host_info(param)

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        if action_id == "execute_script":
            ret_val = self._handle_execute_script(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()

        self._base_url = config["base_url"]
        self._verify_server_cert = config.get("verify_server_cert", False)
        self._username = config["username"]
        self._password = config["password"]
        self._endpoint = config["endpoint"]

        self._headers = {"Content-Type": "application/json-rpc"}

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
            login_url = ZabbixConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=False)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=False, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = ZabbixConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
