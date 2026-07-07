# File: google_threat_intelligence_update_asm_issue_status.py
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


class UpdateAsmIssueStatus(BaseAction):
    """Class to handle update asm issue status action."""

    def execute(self):
        """Execute set status action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("update_asm_issue_status"))

        request_body = self.__get_request_body()
        endpoint, method = consts.UPDATE_ASM_ISSUE_STATUS_ENDPOINT.format(id=self._param.get("id")), "post"

        ret_val, response = self._make_rest_call(url=endpoint, method=method, body=request_body)

        return self.__handle_response(ret_val, response)

    def __get_request_body(self):
        """
        Get request body

        Returns:
            dict: Request body
        """
        status = consts.ASM_ACTION_MAPPING.get(self._param.get("status"))
        body = {"status": status}
        return body

    def _make_rest_call(self, url, method, headers=None, param=None, body=None):
        """
        Make a REST call to the API.

        Args:
            url (str): The endpoint to make the REST call to.
            method (str): The method to use for the REST call.
            headers (dict, optional): The headers to use for the REST call. Defaults to None.
            param (dict, optional): The query parameters to use for the REST call. Defaults to None.
            body (dict, optional): The request body to use for the REST call. Defaults to None.

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
        """
        if self._param.get("project_id"):
            headers = {}
            headers["PROJECT-ID"] = self._param.get("project_id")

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
            return self._action_result.get_status()

        if isinstance(response, list):
            for item in response:
                self._action_result.add_data(item)
        else:
            self._action_result.add_data(response)

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_UPDATE_ASM_ISSUE_STATUS_SUCCESS_RESPONSE,
        )
