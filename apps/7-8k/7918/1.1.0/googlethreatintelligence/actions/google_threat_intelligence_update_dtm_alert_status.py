# File: google_threat_intelligence_update_dtm_alert_status.py
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


class UpdateDtmAlertStatus(BaseAction):
    """Class to handle update dtm alert status action."""

    def execute(self):
        """Execute update fields of dtm alert action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("update_dtm_alert_status"))

        ret_val = self.__validate_params()
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        request_body = self.__get_request_body()
        endpoint, method = consts.UPDATE_DTM_ALERT_STATUS_ENDPOINT.format(id=self._param.get("id")), "patch"

        ret_val, response = self._make_rest_call(url=endpoint, method=method, body=request_body)

        return self.__handle_response(ret_val, response)

    def __validate_params(self):
        """Validate parameters of the action.

        Args:
            self (object): This object

        Returns:
            bool: True if validation is successful, False otherwise
        """
        if self._param.get("tags"):
            ret_val, value = self._connector.validator.validate_list(self._action_result, self._param.get("tags"), "tags")

            if not ret_val:
                return ret_val

            self._param["tags"] = value

        return True

    def __get_request_body(self):
        """Get request body"""
        status = consts.DTM_ACTION_MAPPING.get(self._param.get("status"))
        body = {"tags": self._param.get("tags"), "status": status}

        return body

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
            args["json"] = body

        return self._connector.util.make_rest_call(**args)

    def __handle_response(self, ret_val, response):
        """
        Handle the response from the API call

        Args:
            ret_val (RetVal): The return value of the API call
            response (dict or list): The response from the API call

        Returns:
            int: The status of the request
        """
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        if isinstance(response, list):
            for item in response:
                self._action_result.add_data(item)
        else:
            self._action_result.add_data(response)

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_UPDATE_DTM_ALERT_STATUS_SUCCESS_RESPONSE,
        )
