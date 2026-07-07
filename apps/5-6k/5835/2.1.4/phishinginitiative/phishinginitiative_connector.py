# File: phishinginitiative_connector.py
#
# Copyright (c) 2017-2025 Splunk Inc.
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


import phantom.app as phantom
import requests
import simplejson as json
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from phishinginitiative_consts import *


class PhishingInitiativeConnector(BaseConnector):
    # actions supported by this script
    ACTION_ID_URL_REPUTATION = "url_reputation"

    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._base_url = None
        self._api_key = None

    def initialize(self):
        config = self.get_config()

        self._base_url = "{}{}".format(config[PHISINIT_JSON_BASE_URL].rstrip("/"), PHISINIT_LOOKUP_URL)
        self._api_key = config[PHISINIT_JSON_API_KEY]

        return phantom.APP_SUCCESS

    def _make_rest_call(self, url, action_result):
        """Function that makes the REST call to the device, generic function that can be called from various action handlers"""

        resp_json = None

        params = {"url": url}
        headers = {"Authorization": f"Token {self._api_key}"}

        # Make the call
        try:
            r = requests.get(self._base_url, params=params, headers=headers, timeout=PHISINIT_DEFAULT_REQUEST_TIMEOUT)
        except Exception as e:
            self.error_print("Error occured while making a REST API call", e)
            return action_result.set_status(phantom.APP_ERROR, PHISINIT_ERROR_SERVER_CONNECTIVITY.format(e)), resp_json

        action_result.add_debug_data({"r_text": r.text if r else "r is None"})

        try:
            resp_json = r.json()
        except Exception as e:
            self.error_print("Error while parsing response to json", e)
            # r.text is guaranteed to be NON None, it will be empty, but not None
            msg_string = r.text.replace("{", "").replace("}", "") + str(e)
            return action_result.set_status(phantom.APP_ERROR, msg_string), resp_json

        # Handle/process any errors that we get back from the device
        if r.status_code == 200:
            return phantom.APP_SUCCESS, resp_json

        # Failure
        action_result.add_data(resp_json)

        details = json.dumps(resp_json).replace("{", "").replace("}", "")

        return (action_result.set_status(phantom.APP_ERROR, PHISINIT_ERROR_FROM_SERVER.format(status=r.status_code, detail=details)), resp_json)

    def _test_connectivity(self, param):
        """Function that handles the test connectivity action, it is much simpler than other action handlers."""

        # Progress
        self.save_progress(PHISINIT_USING_BASE_URL.format(PHISINIT_LOOKUP_URL))

        # Action result to represent the call
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Progress message, since it is test connectivity, it pays to be verbose
        self.save_progress("Querying a domain to check connectivity")

        # Make the rest endpoint call
        ret_val, _ = self._make_rest_call("https://www.google.com", action_result)

        # Process errors
        if phantom.is_fail(ret_val):
            # Dump error messages in the log
            self.debug_print(action_result.get_message())

            # Set the status of the complete connector result
            action_result.set_status(phantom.APP_ERROR, action_result.get_message())

            # Append the message to display
            action_result.append_to_message(PHISINIT_ERROR_CONNECTIVITY_TEST)

            # return error
            return phantom.APP_ERROR

        # Set the status of the connector result
        self.save_progress(PHISINIT_SUCCESS_CONNECTIVITY_TEST)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_url_reputation(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        # start progress
        self.save_progress(PHISINIT_USING_BASE_URL.format(PHISINIT_LOOKUP_URL))

        # Make the rest call
        ret_val, response = self._make_rest_call(param[PHISINIT_JSON_URL], action_result)

        # Process/parse the errors encountered while making the REST call.
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            data = response[0]
        except Exception as e:
            self.error_print("Response not in the expected format", e)
            return action_result.set_status(phantom.APP_ERROR, "Response not in the expected format")

        # set the data
        action_result.add_data(data)
        action_result.update_summary({"tag_label": data.get("tag_label")})

        # set the status
        return action_result.set_status(phantom.APP_SUCCESS)

    def finalize(self):
        return phantom.APP_SUCCESS

    def handle_action(self, param):
        """Function that handles all the actions"""

        # Get the action that we are supposed to carry out, set it in the connection result object
        action = self.get_action_identifier()

        # Intialize it to success
        ret_val = phantom.APP_SUCCESS

        # Bunch if if..elif to process actions
        if action == self.ACTION_ID_URL_REPUTATION:
            ret_val = self._handle_url_reputation(param)
        elif action == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity(param)

        return ret_val


if __name__ == "__main__":
    """ Code that is executed when run in standalone debug mode"""

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
        connector = PhishingInitiativeConnector()

        # Se the member vars
        connector.print_progress_message = True

        # Call BaseConnector::_handle_action(...) to kickoff action handling.
        ret_val = connector._handle_action(json.dumps(in_json), None)

        # Dump the return value
        print(ret_val)

    sys.exit(0)
