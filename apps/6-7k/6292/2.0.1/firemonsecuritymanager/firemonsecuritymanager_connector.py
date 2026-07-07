# File: firemonsecuritymanager_connector.py
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
# Python 3 Compatibility imports

# Phantom App imports
import json
import sys

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class FiremonSecurityManagerConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None
        self._test_url = None
        self._username = None
        self._password = None
        self._verify_server_cert = None

    def _process_empty_response(self, response, action_result):
        if response.status_code == 204:
            return RetVal(phantom.APP_SUCCESS, {"message": "Status Code: " + str(response.status_code)})

        return RetVal(
            action_result.set_status(
                phantom.APP_ERROR, "Empty response and no information in the header; Status Code: " + str(response.status_code)
            ),
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

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        # config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = self._base_url + endpoint

        try:
            r = request_func(
                url,
                auth=(self._username, self._password),  # basic authentication
                verify=self._verify_server_cert,
                **kwargs,
            )
        except Exception as e:
            err_msg = f"Error Connecting to server. Details: {e!s}"
            self.error_print(err_msg)
            return RetVal(action_result.set_status(phantom.APP_ERROR, err_msg), resp_json)

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # NOTE: test connectivity does _NOT_ take any parameters
        # i.e. the param dictionary passed to this handler will be empty.
        # Also typically it does not add any data into an action_result either.
        # The status and progress messages are more important.

        self.save_progress("Connecting to endpoint")
        # make rest call
        ret_val, response = self._make_rest_call(self._test_url, action_result, params=None, headers=None)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()

        # Try to parse Firemon version
        try:
            firemon_version = response["version"]
        except Exception:
            firemon_version = "unable to parse version"

        # Return success
        self.save_progress("Test Connectivity Passed - Firemon version: " + str(firemon_version))
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_assign_device_group(self, param):
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        firemon_domain_id = param["firemon_domain_id"]
        firemon_device_group_id = param["firemon_device_group_id"]
        firemon_device_id = param["firemon_device_id"]

        # make rest call
        ret_val, response = self._make_rest_call(
            f"/domain/{firemon_domain_id!s}/devicegroup/{firemon_device_group_id!s}/device/{firemon_device_id!s}",
            action_result,
            method="post",
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            return action_result.get_status()

        # Now post process the data,  uncomment code as you deem fit

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["message"] = response["message"]

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_remove_device_group(self, param):
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        firemon_domain_id = param["firemon_domain_id"]
        firemon_device_group_id = param["firemon_device_group_id"]
        firemon_device_id = param["firemon_device_id"]

        # make rest call
        ret_val, response = self._make_rest_call(
            f"/domain/{firemon_domain_id!s}/devicegroup/{firemon_device_group_id!s}/device/{firemon_device_id!s}",
            action_result,
            method="delete",
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            return action_result.get_status()

        # Now post process the data,  uncomment code as you deem fit

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["message"] = response["message"]

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_device_group(self, param):
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        firemon_domain_id = param["firemon_domain_id"]
        firemon_device_group_id = param["firemon_device_group_id"]

        # make rest call
        ret_val, response = self._make_rest_call(
            f"/domain/{firemon_domain_id!s}/devicegroup/{firemon_device_group_id!s}", action_result, params=None, headers=None
        )

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            return action_result.get_status()

        # Now post process the data,  uncomment code as you deem fit

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["id"] = response["id"]
        summary["domainId"] = response["domainId"]
        summary["name"] = response["name"]

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_domain(self, param):
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        firemon_domain_id = param["firemon_domain_id"]

        # make rest call
        ret_val, response = self._make_rest_call(f"/domain/{firemon_domain_id!s}", action_result, params=None, headers=None)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            return action_result.get_status()

        # Now post process the data,  uncomment code as you deem fit

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["id"] = response["id"]
        summary["name"] = response["name"]

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_device(self, param):
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        firemon_domain_id = param["firemon_domain_id"]
        firemon_device_id = param["firemon_device_id"]
        firemon_device_json = param["firemon_device_json"]
        firemon_manual_retrieval = param["firemon_manual_retrieval"]

        # make rest call to get device
        ret_val, response = self._make_rest_call(
            f"/domain/{firemon_domain_id!s}/device/{firemon_device_id!s}", action_result, method="get", params=None, headers=None
        )

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            return action_result.get_status()

        # Set update params to action_result for get device request and update device field
        data_dict = response
        device_dict = json.loads(firemon_device_json)
        for key, value in device_dict.items():
            data_dict[key] = value
        data = json.dumps(data_dict)

        headers = {"accept": "*/*", "Content-Type": "application/json"}

        # make rest call to update device
        ret_val, response = self._make_rest_call(
            f"/domain/{firemon_domain_id!s}/device/{firemon_device_id!s}?manualRetrieval={firemon_manual_retrieval!s}",
            action_result,
            method="put",
            params=None,
            headers=headers,
            data=data,
        )

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            return action_result.get_status()

        # Now post process the data,  uncomment code as you deem fit

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["message"] = response["message"]

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_device(self, param):
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        firemon_domain_id = param["firemon_domain_id"]
        firemon_device_id = param["firemon_device_id"]

        # make rest call
        ret_val, response = self._make_rest_call(
            f"/domain/{firemon_domain_id!s}/device/{firemon_device_id!s}", action_result, params=None, headers=None
        )

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            return action_result.get_status()

        # Now post process the data,  uncomment code as you deem fit

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["id"] = response["id"]
        summary["domainId"] = response["domainId"]
        summary["name"] = response["name"]
        summary["description"] = response["description"]

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "assign_device_group":
            ret_val = self._handle_assign_device_group(param)

        elif action_id == "remove_device_group":
            ret_val = self._handle_remove_device_group(param)

        elif action_id == "get_device_group":
            ret_val = self._handle_get_device_group(param)

        elif action_id == "get_domain":
            ret_val = self._handle_get_domain(param)

        elif action_id == "update_device":
            ret_val = self._handle_update_device(param)

        elif action_id == "get_device":
            ret_val = self._handle_get_device(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()
        """
        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """

        self._base_url = config["base_url"]
        self._test_url = "/version"
        self._username = config["username"]
        self._password = config["password"]
        self._verify_server_cert = config["verify_server_cert"]

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
            login_url = FiremonSecurityManagerConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=60)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=60)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit()

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = FiremonSecurityManagerConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit()


if __name__ == "__main__":
    main()
