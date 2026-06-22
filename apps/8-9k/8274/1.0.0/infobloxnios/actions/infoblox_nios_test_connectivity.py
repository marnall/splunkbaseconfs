# File: infoblox_nios_test_connectivity.py
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

import infoblox_nios_consts as consts
from actions import BaseAction


class TestConnectivityAction(BaseAction):
    """Test connectivity action."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.TEST_CONNECTIVITY_MESSAGE)
        self._connector.save_progress(f"Configured URL: {self._connector._url}")

    def __make_api_call(self):
        """Make the REST API call to test connectivity.

        :return: tuple: (status, response) - Status code and API response
        """
        # Querying endpoint to check connection to device
        return self._connector.utils.make_rest_call(consts.TEST_SCHEMA_ENDPOINT, self._action_result, method="get", timeout=30)

    def __handle_response(self, response):
        """Handle the API response for test connectivity.

        :param response: The API response
        :return: status (success/failure)
        """
        # If we got this far, the connection was successful
        self._connector.save_progress(consts.TEST_CONN_SUCCESS)
        return self._action_result.set_status(phantom.APP_SUCCESS, consts.TEST_CONN_SUCCESS)

    def execute(self):
        """Execute the test connectivity action.

        Step 1: Log action start
        Step 2: Make API call to test connectivity
        Step 3: Handle the response

        :return: status (success/failure)
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Make API call to test connectivity
        status, response = self.__make_api_call()

        if phantom.is_fail(status):
            self._connector.save_progress(self._action_result.get_message())
            return self._action_result.set_status(phantom.APP_ERROR, consts.TEST_CONN_FAILED)

        # Step 3: Handle the response
        return self.__handle_response(response)
