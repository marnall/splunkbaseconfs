# File: google_threat_intelligence_test_connectivity.py
#
# Copyright 2025-2026 Google LLC
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

from urllib.parse import urlencode

import phantom.app as phantom

import google_threat_intelligence_consts as consts
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
        self._connector.save_progress(consts.TEST_CONNECTIVITY_START_MSG.format("Google Threat Intelligence"))

        endpoint, method = self.__get_request_url_and_method()

        ret_val, response = self._make_rest_call(url=endpoint, method=method)

        return self.__handle_response(ret_val, response)

    def __get_request_url_and_method(self):
        """Get request url and method to test connectivity.

        Args:
            None

        Returns:
            tuple: Containing the request url and method
        """
        parameters = []

        endpoint = consts.TEST_CONNECTIVITY_ENDPOINT
        for parameter in parameters:
            endpoint = endpoint.replace("{{##}}".replace("##", parameter), str(self._param.get(parameter)))

        return endpoint, "get"

    def _make_rest_call(self, url, method, headers=None, param=None, body=None):
        """Make a REST call to the API.

        Args:
            url (str): The URL to make the REST call to.
            method (str): The HTTP method to use (e.g. "get", "post").
            headers (dict, optional): A dictionary of headers to send with the request.
            param (dict, optional): A dictionary of query parameters to send with the request.
            body (dict, optional): A dictionary of data to send as the request body.

        Returns:
            tuple: A tuple containing the status of the request and the response.
        """
        args = {
            "endpoint": url,
            "action_result": self._action_result,
            "method": method.lower(),
            "headers": headers or {},
        }

        if param:
            args["endpoint"] = f"{args['endpoint']}?{urlencode(param)}"

        if body:
            args["json"] = body

        return self._connector.util.make_rest_call(**args)

    def __handle_response(self, ret_val, response):
        """
        Process response received from the third party API

        Args:
            ret_val (RetVal): The return value from the REST call.
            response (dict or list): The response data received from the third party API.

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
        """
        if phantom.is_fail(ret_val):
            self._connector.save_progress(consts.ERROR_TEST_CONNECTIVITY)
            return self._action_result.get_status()

        self._connector.save_progress(consts.SUCCESS_TEST_CONNECTIVITY)
        return self._action_result.set_status(phantom.APP_SUCCESS)
