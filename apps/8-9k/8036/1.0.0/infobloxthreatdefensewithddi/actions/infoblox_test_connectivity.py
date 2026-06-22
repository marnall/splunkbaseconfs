# File: infoblox_test_connectivity.py
#
# Copyright 2025 Infoblox Inc.
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

import infoblox_consts as consts
from actions import BaseAction


class TestConnectivity(BaseAction):
    """Class to handle test connectivity action."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.TEST_CONNECTIVITY_START_MSG.format("Infoblox"))

    def __make_api_call(self):
        """Make the REST API call to test connectivity.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        return self._connector.util.make_rest_call(
            endpoint=consts.TEST_CONNECTIVITY_ENDPOINT,
            action_result=self._action_result,
            method="get",
        )

    def __handle_response(self, response):
        """Handle the API response for test connectivity.

        Args:
            response (dict): The API response containing results

        Returns:
            int: phantom.APP_SUCCESS on successful connectivity, phantom.APP_ERROR otherwise
        """
        # Check if response contains expected account data
        if response and isinstance(response, dict):
            if "results" in response:
                self._connector.save_progress(consts.SUCCESS_TEST_CONNECTIVITY)
                return self._action_result.set_status(
                    phantom.APP_SUCCESS,
                    consts.ACTION_TEST_CONNECTIVITY_SUCCESS_RESPONSE,
                )
            else:
                self._connector.save_progress("Unexpected response format")
                return self._action_result.set_status(phantom.APP_ERROR, "Unexpected response format from server")
        else:
            self._connector.save_progress("Empty or invalid response")
            return self._action_result.set_status(phantom.APP_ERROR, "Empty or invalid response from server")

    def execute(self):
        """Execute test connectivity action.

        Step 1: Log action start
        Step 2: Make REST call to test connectivity
        Step 3: Handle the response
        """
        # Log action start
        self.__log_action_start()

        # Make API call
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            self._connector.save_progress(consts.ERROR_TEST_CONNECTIVITY)
            return ret_val

        # Handle response using dedicated method
        return self.__handle_response(response)
