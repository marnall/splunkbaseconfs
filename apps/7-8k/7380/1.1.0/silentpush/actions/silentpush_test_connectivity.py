# File: silentpush_test_connectivity.py
#
# Copyright (c) 2024-2025 Splunk Inc.
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

import silentpush_consts as consts
from actions import BaseAction


class TestConnectivity(BaseAction):
    """Class to handle test connectivity action."""

    def execute(self):
        """Execute test connectivity action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.TEST_CONNECTIVITY_START_MESSAGE.format("Silent Push"))

        endpoint, method = self.__get_request_url_and_method()

        ret_val, response = self.__make_rest_call(url=endpoint, method=method)

        return self.__handle_response(ret_val, response)

    def __get_request_url_and_method(self):
        """Get request endpoint and method."""
        endpoint = consts.TEST_CONNECTIVITY_ENDPOINT

        return endpoint, "get"

    def __make_rest_call(self, url, method, headers=None, param=None, body=None):
        """Invoke reset API."""
        args = {"endpoint": url, "action_result": self._action_result, "method": method.lower(), "headers": headers or {}}

        return self._connector.util.make_rest_call(**args)

    def __handle_response(self, ret_val, response):
        """Process response received from the third party API."""
        if phantom.is_fail(ret_val):
            self._connector.save_progress(consts.ERROR_TEST_CONNECTIVITY)
            return self._action_result.get_status()

        self._connector.save_progress(consts.SUCCESS_TEST_CONNECTIVITY)
        return self._action_result.set_status(phantom.APP_SUCCESS)
