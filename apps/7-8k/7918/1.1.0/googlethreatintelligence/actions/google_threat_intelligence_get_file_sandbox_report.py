# File: google_threat_intelligence_get_file_sandbox_report.py
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


class GetFileSandboxReport(BaseAction):
    """Class to handle get file sandbox report action."""

    def execute(self):
        """Execute get file sandbox action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("get_file_sandbox"))

        file_hash = self._param["file_hash"]
        password = self._param.get("password")

        ret_val, file_id = self._connector.util.get_file_hash_from_input(self._action_result, file_hash, password)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        endpoint, method = (
            consts.GET_FILE_SANDBOX_ENDPOINT.format(file_id=file_id),
            "get",
        )
        ret_val, json_resp = self._make_rest_call(url=endpoint, method=method)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        return self.__handle_response(ret_val, json_resp)

    def _make_rest_call(self, url, method, headers=None, param=None, body=None):
        """Invoke API

        Args:
            url (str): The endpoint to make the REST call to.
            method (str): The method to use for the REST call.
            headers (dict, optional): The headers to use for the REST call. Defaults to None.
            param (dict, optional): The query parameters to use for the REST call. Defaults to None.
            body (dict, optional): The request body to use for the REST call. Defaults to None.

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
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
        """Handle the response of the API.

        Args:
            ret_val (RetVal): The status of the API call.
            response (dict): The response of the API call.

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
        """
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        if isinstance(response, list):
            for item in response:
                self._action_result.add_data(item)
        else:
            for item in response.get("data"):
                analysis_date = item.get("attributes").get("analysis_date")
                verdicts = item.get("attributes").get("verdicts")
                verdict_labels = item.get("attributes").get("verdict_labels")
                tags = item.get("attributes").get("tags")
                if analysis_date:
                    item["attributes"]["analysis_date"] = self._connector.util.convert_unix_to_utc(analysis_date)
                if verdicts:
                    item["attributes"]["verdicts"] = ", ".join(verdicts)
                if verdict_labels:
                    item["attributes"]["verdict_labels"] = ", ".join(verdict_labels)
                if tags:
                    item["attributes"]["tags"] = ", ".join(tags)
            self._action_result.add_data(response)

        summary = {"total_file_sandbox": len(response.get("data"))}
        self._action_result.update_summary(summary)

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_GET_FILE_SANDBOX_SUCCESS_RESPONSE,
        )
