# Copyright (c) 2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#!/usr/bin/python
# -----------------------------------------
# Phantom sample App Connector python file
# -----------------------------------------

# Python 3 Compatibility imports

import json
import time

# Phantom App imports
import phantom.app as phantom

# Usage of the consts file is recommended
# from tehtris_consts import *
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from tehtris_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class TehtrisConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None
        self._api_key = None

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200 or response.status_code == 204:
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
        username = "api"
        password = self._api_key

        try:
            r = request_func(
                url,
                auth=(username, password),  # basic authentication
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

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # NOTE: test connectivity does _NOT_ take any parameters
        # i.e. the param dictionary passed to this handler will be empty.
        # Also typically it does not add any data into an action_result either.
        # The status and progress messages are more important.

        self.save_progress("Connecting to endpoint")

        t = time.time()

        params = {"fromDate": t}
        # make rest call
        ret_val, response = self._make_rest_call(TEHTRIS_GET_EVENTS_ENDPOINT, action_result, params=params, headers=None)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

        # For now return Error with a message, in case of success we don't set the message, but use the summary
        # return action_result.set_status(phantom.APP_ERROR, "Action not yet implemented")

    def _handle_get_events(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        from_date = param.get("from_date")
        to_date = param.get("to_date")
        limit = param.get("limit", 100)
        offset = param.get("offset", 0)
        filter_id = param.get("filter_id")
        hostname = param.get("hostname")

        params = {
            "fromDate": from_date,
            "toDate": to_date,
            "limit": limit,
            "offset": offset,
            "filterID": filter_id,
        }
        # make rest call
        fetched_all_events = False
        while not fetched_all_events:
            ret_val, response = self._make_rest_call(
                TEHTRIS_GET_EVENTS_ENDPOINT,
                action_result,
                params=params,
                headers=None,
                method="get",
            )

            if phantom.is_fail(ret_val):
                # the call to the 3rd party device or service failed, action result should contain all the error details
                # for now the return is commented out, but after implementation, return from here
                self.save_progress("Failed to fetch events")
                return action_result.get_status()

            # If success
            for event in response:
                if event.get("hostname__") == hostname:
                    action_result.add_data(event)

            if len(response) == limit:
                params["offset"] += limit
            else:
                fetched_all_events = True
                self.save_progress("Successfully collected events")

        summary = action_result.update_summary({})
        summary["num_events"] = action_result.get_data_size()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_send_for_isolation(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        hostname = param.get("hostname")
        self.save_progress("Obtaining uuids")

        # Getting uuid and appliance id
        params = {"hostname": hostname}

        ret_val, response = self._make_rest_call(
            TEHTRIS_GET_INVENTORY_ENDPOINT,
            action_result,
            params=params,
            headers=None,
            method="get",
        )
        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Failed to obtain uuid")
            return action_result.get_status()

        self.save_progress(f"Successfully fetched uuid for hostname {hostname}")

        uuid = response.get("data")[0].get("uuid")
        appliance_id = response.get("data")[0].get("applianceId")
        self.save_progress(f"UUID: {uuid} APPLIANCE_ID: {appliance_id}")

        # Sending uuid to isolation
        params = {"isolationAction": "enable"}

        ret_val, response = self._make_rest_call(
            TEHTRIS_POST_FOR_ISOLATION_ENDPOINT.format(appliance_id, uuid),
            action_result,
            params=params,
            headers=None,
            method="post",
        )

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Failed to post uuid for isolation")
            return action_result.get_status()

        # When succeeded
        action_result.add_data(response)
        self.save_progress(f"Successfully posted uuid {uuid} for isolation")
        summary = action_result.update_summary({})
        summary["result"] = f"Successfully posted uuid {uuid} for isolation"

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_remove_from_isolation(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        hostname = param.get("hostname")
        self.save_progress("Obtaining uuids")

        # Getting uuid and appliance id
        params = {"hostname": hostname}

        ret_val, response = self._make_rest_call(
            TEHTRIS_GET_INVENTORY_ENDPOINT,
            action_result,
            params=params,
            headers=None,
            method="get",
        )
        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Failed to obtain uuid")
            return action_result.get_status()

        self.save_progress(f"Successfully fetched uuid for hostname {hostname}")
        uuid = response.get("data")[0].get("uuid")
        appliance_id = response.get("data")[0].get("applianceId")
        self.save_progress(f"UUID: {uuid} APPLIANCE_ID: {appliance_id}")

        # Sending uuid to isolation
        params = {"isolationAction": "disable"}

        ret_val, response = self._make_rest_call(
            TEHTRIS_POST_FOR_ISOLATION_ENDPOINT.format(appliance_id, uuid),
            action_result,
            params=params,
            headers=None,
            method="post",
        )

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Failed to post uuid for isolation")
            return action_result.get_status()

        # When succeeded
        action_result.add_data(response)
        message = f"Successfully romoved uuid {uuid} from isolation"
        self.save_progress(message)
        summary = action_result.update_summary({})
        summary["result"] = message

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_processes(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        hostname = param.get("hostname")
        pid = param.get("pid")
        create_time = param.get("create_time")
        number_of_parents = param.get("number_of_parents")
        limit = param.get("limit", 1000)

        # Getting uuid and applianceId
        self.save_progress("Obtaining uuid and applianceId")

        params = {"hostname": hostname}

        ret_val, response = self._make_rest_call(
            TEHTRIS_GET_INVENTORY_ENDPOINT,
            action_result,
            params=params,
            headers=None,
            method="get",
        )
        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Failed to obtain uuid")
            return action_result.get_status()

        uuid = response.get("data")[0].get("uuid")
        appliance_id = response.get("data")[0].get("applianceId")
        self.save_progress(f"Successfully fetched uuid and applianceID for hostname {hostname}")
        self.save_progress(f"UUID: {uuid} APPLIANCE_ID: {appliance_id}")

        # Geting process tree
        params = {
            "pid": pid,
            "createTime": create_time,
            "nbParents": number_of_parents,
            "limit": limit,
        }

        ret_val, response = self._make_rest_call(
            TEHTRIS_GET_PROCESSES_TREE.format(appliance_id, uuid),
            action_result,
            params=params,
            headers=None,
            method="get",
        )

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Failed to get processes tree")
            return action_result.get_status()

        # When succeeded
        action_result.add_data(response)
        self.save_progress(f"Successfully fetched processes for {uuid}")
        summary = action_result.update_summary({})
        summary["num_events"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_tag(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        hostname = param.get("hostname")
        tag = param.get("tag")

        self.save_progress("Obtaining uuids")

        # Getting uuid list
        params = {"hostname": hostname}

        ret_val, response = self._make_rest_call(
            TEHTRIS_GET_INVENTORY_ENDPOINT,
            action_result,
            params=params,
            headers=None,
            method="get",
        )
        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Failed to obtain uuid")
            return action_result.get_status()

        self.save_progress(f"Successfully fetched uuid for hostname {hostname}")
        uuid = response.get("data")[0].get("uuid")
        uuid_list = []
        uuid_list.append(uuid)
        self.save_progress(f"UUID: {uuid}")

        # Sending uuid to isolation
        data = {"edrUuidList": uuid_list, "tags": tag}

        ret_val, response = self._make_rest_call(TEHTRIS_PUT_TAG, action_result, json=data, headers=None, method="put")

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Failed to update tags")
            return action_result.get_status()

        # When succeeded
        self.save_progress(f"Successfully updated tags for {uuid}")
        summary = action_result.update_summary({})
        summary["result"] = f"Successfully added tag '{tag}' for {uuid}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_app_policy(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        # policy_name = param.get('policy_name')
        sha256 = param.get("sha256").strip(" ").split(",")
        hostnames = param.get("hostnames").strip(" ").split(",")
        order = param.get("order")
        self.save_progress("Obtaining uuids")

        # Getting uuid and appliance id
        appliance_id_list = []
        for hostname in hostnames:
            params = {"hostname": hostname}

            ret_val, response = self._make_rest_call(
                TEHTRIS_GET_INVENTORY_ENDPOINT,
                action_result,
                params=params,
                headers=None,
                method="get",
            )
            if phantom.is_fail(ret_val):
                # the call to the 3rd party device or service failed, action result should contain all the error details
                # for now the return is commented out, but after implementation, return from here
                self.save_progress("Failed to obtain uuid")
                return action_result.get_status()

            self.save_progress(f"Successfully fetched uuid for hostname {hostname}")
            uuid = response.get("data")[0].get("uuid")
            appliance_id = response.get("data")[0].get("applianceId")
            appliance_id_list.append(appliance_id)
            self.save_progress(f"UUID: {uuid} APPLIANCE_ID: {appliance_id}")

        # Creating new policy
        body = {
            "name": f"New test policy for appliances {appliance_id_list}",
            "appliances": appliance_id_list,
            "orderedRules": [
                {
                    "name": f"New test policy for appliances {appliance_id_list}",
                    "order": order,
                    "conditions": [{"type": "Sha256", "content": sha256}],
                },
            ],
        }

        ret_val, response = self._make_rest_call(
            TEHTRIS_POST_APP_POLICY,
            action_result,
            params=None,
            json=body,
            headers=None,
            method="post",
        )

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress(f"Failed to post app policy for {uuid}")
            return action_result.get_status()

        # When succeeded
        action_result.add_data(response)
        self.save_progress(f"Successfully posted new app policy for {uuid}")
        summary = action_result.update_summary({})
        summary["result"] = f"Successfully posted new app policy for {uuid}"

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)
        if action_id == "get_events":
            ret_val = self._handle_get_events(param)
        if action_id == "send_for_isolation":
            ret_val = self._handle_send_for_isolation(param)
        if action_id == "list_processes":
            ret_val = self._handle_list_processes(param)
        if action_id == "update_tag":
            ret_val = self._handle_update_tag(param)
        if action_id == "remove_from_isolation":
            ret_val = self._handle_remove_from_isolation(param)
        if action_id == "create_app_policy":
            ret_val = self._handle_create_app_policy(param)

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

        self._base_url = config.get("base_url")
        self._api_key = config.get("api_key")

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

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
            login_url = TehtrisConnector._get_phantom_base_url() + "/login"

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
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = TehtrisConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)


if __name__ == "__main__":
    main()
