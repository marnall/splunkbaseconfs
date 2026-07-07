# File: metadefender_connector.py
#
# Copyright (c) 2016-2025 Splunk Inc.
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
# Phantom imports
import phantom.app as phantom
import requests

# Required library imports
import simplejson as json
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# THIS Connector imports
from metadefender_consts import *


class MetadefenderConnector(BaseConnector):
    ACTION_ID_IP_REPUTATION = "ip_reputation"
    ACTION_ID_FILE_REPUTATION = "file_reputation"
    ACTION_ID_TEST_ASSET_CONNECTIVITY = "test_connectivity"

    def __init__(self):
        super().__init__()

    def _make_rest_call(self, endpoint, headers):
        full_url = METADEFENDER_API_BASE_URL + endpoint

        try:
            r = requests.get(full_url, headers=headers, timeout=DEFAULT_TIMEOUT)

        except Exception as e:
            return (phantom.APP_ERROR, f"Could not complete rest call. {e}")

        if r.status_code == 403:
            return (phantom.APP_ERROR, "API call limit reached.  See Metadefender's Portal for more information")

        if 400 <= r.status_code:
            return (phantom.APP_ERROR, f"Response failed. {r.reason}")
        try:
            resp_json = r.json()
        except Exception as e:
            return (phantom.APP_ERROR, f"Could not convert response to JSON. {e}")

        return (phantom.APP_SUCCESS, resp_json)

    def _ip_reputation(self, params):
        action_result = self.add_action_result(ActionResult(params))
        self.save_progress(f"In action handler for {self.get_action_identifier()}")

        ip = params[METADEFENDER_JSON_IP]

        endpoint = METADEFENDER_API_IP_REPUTATION.format(ip=ip)

        config = self.get_config()

        headers = {"apikey": config[METADEFENDER_CONFIG_API_KEY]}
        self.save_progress("Querying Metadefender...")

        ret_val, response = self._make_rest_call(endpoint, headers)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, "Could not complete rest call", response)

        action_result.add_data(response)

        action_result.set_summary({"detected_by": response["lookup_results"]["detected_by"]})
        return action_result.set_status(phantom.APP_SUCCESS)

    def _file_reputation(self, params):
        action_result = self.add_action_result(ActionResult(params))

        file = params[METADEFENDER_JSON_HASH]
        additional_info = params.get(METADEFENDER_JSON_ADDITIONAL_INFO, True)

        config = self.get_config()

        headers = {"apikey": config[METADEFENDER_CONFIG_API_KEY]}

        endpoint = METADEFENDER_API_FILE_REPUTATION.format(file=file)

        ret_val, response = self._make_rest_call(endpoint, headers)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, "Could not complete rest call", response)

        try:
            response["additional_details"] = additional_details = dict()
            additional_info_keys = response.get("additional_info", list())
            # if action parameter additional_info is checked and response has keys to fetch additional data
            if additional_info and additional_info_keys:
                for key in additional_info_keys:
                    info_endpoint = METADEFENDER_API_ADDITIONAL_INFO.format(file=file, additional_info_key=key)
                    ret_val, additional_info_response = self._make_rest_call(info_endpoint, headers)
                    if phantom.is_fail(ret_val):  # Not throwing error for additional_data, just logging
                        self.debug_print(f"Could not fetch additional_info for key {key}")
                    else:
                        additional_details[key] = additional_info_response
        except Exception as e:
            self.debug_print(f"Error while fetching additional info. Error: {e}")

        action_result.add_data(response)
        if "scan_results" in response:
            action_result.set_summary({"file_result": response["scan_results"]["scan_all_result_a"]})
        else:
            action_result.set_summary({"file_result": "Clean"})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _test_connectivity(self):
        # set the endpoint
        endpoint = METADEFENDER_API_IP_REPUTATION.format(ip="8.8.8.8")

        # Action result to represent the call
        action_result = ActionResult()

        # Progress message, since it is test connectivity, it pays to be verbose
        self.save_progress("Querying Metadefender...")

        config = self.get_config()

        headers = {"apikey": config[METADEFENDER_CONFIG_API_KEY]}

        ret_val, response = self._make_rest_call(endpoint, headers)

        # Process errors
        if phantom.is_fail(ret_val):
            # Dump error messages in the log
            self.debug_print(action_result.get_message())

            # Set the status of the complete connector result
            self.set_status(phantom.APP_ERROR, action_result.get_message())

            # Append the message to display
            self.append_to_message(response)

            # return error
            return phantom.APP_ERROR

        # Set the status of the connector result
        return self.set_status_save_progress(phantom.APP_SUCCESS, "Test Connectivity succeeded")

    def handle_action(self, params):
        action = self.get_action_identifier()

        ret_val = phantom.APP_SUCCESS

        if action == self.ACTION_ID_IP_REPUTATION:
            ret_val = self._ip_reputation(params)
        elif action == self.ACTION_ID_FILE_REPUTATION:
            ret_val = self._file_reputation(params)
        if action == self.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity()
        return ret_val


if __name__ == "__main__":
    # Imports
    import sys

    import pudb

    # Breakpoint at runtime
    pudb.set_trace()

    # The first param is the input json file
    with open(sys.argv[1]) as f:
        # Load the input json file
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=" " * 4))

        # Create the connector class object
        connector = MetadefenderConnector()

        # Se the member vars
        connector.print_progress_message = True

        # Call BaseConnector::_handle_action(...) to kickoff action handling.
        ret_val = connector._handle_action(json.dumps(in_json), None)

        # Dump the return value
        print(ret_val)

    sys.exit(0)
