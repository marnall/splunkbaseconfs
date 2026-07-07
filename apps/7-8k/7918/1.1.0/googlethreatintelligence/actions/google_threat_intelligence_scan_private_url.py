# File: google_threat_intelligence_scan_private_url.py
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


class ScanPrivateUrl(BaseAction):
    """Class to handle scan private url action."""

    def execute(self):
        """Execute scan private url action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("scan_private_url"))

        ret_val = self.__validate_params()
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        request_body = self.__get_request_body()

        endpoint, method = consts.SCAN_PRIVATE_URL_ENDPOINT, "post"

        # Scan Private URL
        ret_val, private_scan_result = self._make_rest_call(url=endpoint, method=method, body=request_body)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        # Get private analysis id from the private_scan_result
        ret_val, private_analysis_id = self._connector.util._get_id_from_scan_entity(self._action_result, private_scan_result)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        analysis_status, url_id = self._connector.util._poll_analysis_until_complete(
            self._action_result,
            consts.URL,
            private_analysis_id,
            consts.RETRY_COUNT,
            is_private=True,
        )

        # Check if the analysis is completed
        if analysis_status:
            # Get id from the private_analysis
            endpoint, method = (
                f"{consts.GET_A_PRIVATE_URL_REPORT_ENDPOINT.format(url_id=url_id)}",
                "get",
            )

            ret_val, response = self._make_rest_call(
                url=endpoint,
                method=method,
                headers={"x-tool": "splunk soar", "Content-Type": "application/json"},
            )

            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            return self.__handle_response(ret_val, response)

        return self.__handle_response(ret_val, "Retry Scanning the URL")

    def __validate_params(self):
        """
        Validate parameters of the action.

        Args:
            self (object): This object

        Returns:
            bool: True if validation is successful, False otherwise
        """
        if "retention_period_days" in self._param:
            ret_val, value = self._connector.validator.validate_integer(
                self._action_result,
                self._param.get("retention_period_days"),
                "retention_period_days",
            )

            if not ret_val:
                return ret_val

            self._param["retention_period_days"] = value

        if "interaction_timeout" in self._param:
            ret_val, value = self._connector.validator.validate_integer(
                self._action_result,
                self._param.get("interaction_timeout"),
                "interaction_timeout",
            )

            if not ret_val:
                return ret_val

            ret_val, value = self._connector.validator.validate_integer_range(
                self._action_result,
                self._param.get("interaction_timeout"),
                "interaction_timeout",
                consts.INTERACTION_TIMEOUT_MIN,
                consts.INTERACTION_TIMEOUT_MAX,
            )

            if not ret_val:
                return ret_val

            self._param["interaction_timeout"] = value

        return True

    def __get_request_body(self):
        """
        Generates a request body given a body and template values.

        Args:
            body (dict): The body to generate the JSON from.
            allow_none (list): A list of keys that can have a value of None.
            allow_empty (dict): A dictionary of keys that can have an empty value.
            param (dict): A dictionary of template values.
            default_values (dict): A dictionary of default values.

        Returns:
            dict: The generated request body.
        """
        output_body = {}
        formdata = {
            "url": "url",
            "user_agent": "user_agent",
            "sandboxes": "sandboxes",
            "retention_period_days": "retention_period_days",
            "storage_region": "storage_region",
            "interaction_sandbox": "interaction_sandbox",
            "interaction_timeout": "interaction_timeout",
        }
        default_values = {}

        for key, value in formdata.items():
            if value in self._param:
                output_body[key] = self._param[value]
            elif value in default_values:
                output_body[key] = default_values[value]

        return output_body

    def _make_rest_call(self, url, method, headers=None, param=None, body=None):
        """
        Make a REST call to the API.

        Args:
            url (str): The URL of the API endpoint
            method (str): The HTTP method to use (e.g. "get", "post")
            headers (dict, optional): A dictionary of headers to send with the request
            param (dict, optional): A dictionary of query parameters to send with the request
            body (dict, optional): A dictionary of data to send as the request body

        Returns:
            tuple: A tuple containing the status of the request and the response
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
            args["data"] = body

        return self._connector.util.make_rest_call(**args)

    def __handle_response(self, ret_val, response):
        """
        Handle the response from the API.

        Args:
            ret_val (RetVal): The status of the API call
            response (list or dict): The response from the API

        Returns:
            int: The status of the action
        """
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        if isinstance(response, list):
            for item in response:
                tags = item.get("data").get("attributes").get("tags")
                if tags:
                    item["data"]["attributes"]["tags"] = ", ".join(tags)
                    self._action_result.add_data(item)
        else:
            tags = response.get("data").get("attributes").get("tags")
            if tags:
                response["data"]["attributes"]["tags"] = ", ".join(tags)
            self._action_result.add_data(response)

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_SCAN_PRIVATE_URL_SUCCESS_RESPONSE,
        )
