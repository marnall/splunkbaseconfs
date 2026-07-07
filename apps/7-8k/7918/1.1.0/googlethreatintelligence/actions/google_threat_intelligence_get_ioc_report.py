# File: google_threat_intelligence_get_ioc_report.py
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


class GetIocReport(BaseAction):
    """Class to handle get ioc report action."""

    def execute(self):
        """Execute get report action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("get_report"))
        entity = self._param["entity"]
        password = self._param.get("password")
        entity_type = self._connector.util.get_data_type(entity)

        self._connector.debug_print(f"Running action {self._connector.get_action_identifier()} with {entity} and entity type {entity_type}.")

        if entity_type == consts.IP_ADDRESS or entity_type == consts.DOMAIN:
            endpoint, method = (
                consts.GET_REPORT_ENDPOINT.format(entity_type=entity_type, entity=entity),
                "get",
            )
            ret_val, json_resp = self._make_rest_call(url=endpoint, method=method)
        elif entity_type == consts.URL:
            ret_val, url_id = self._connector.util.submit_url_for_analysis(self._action_result, entity)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()
            endpoint, method = (
                consts.GET_REPORT_ENDPOINT.format(entity_type=entity_type, entity=url_id),
                "get",
            )
            ret_val, json_resp = self._make_rest_call(url=endpoint, method="get")
        elif entity_type == consts.FILE:
            ret_val, file_id = self._connector.util.get_file_hash_from_input(self._action_result, entity, password)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()
            endpoint, method = (
                consts.GET_REPORT_ENDPOINT.format(entity_type=entity_type, entity=file_id),
                "get",
            )
            ret_val, json_resp = self._make_rest_call(url=endpoint, method=method)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        return self.__handle_response(ret_val, json_resp)

    def _make_rest_call(self, url, method, headers=None, param=None, body=None):
        """
        Make a REST call to the API.

        Args:
            url (str): The endpoint to make the REST call to.
            method (str): The method to use for the REST call.
            headers (dict): The headers to be sent in the request.
            param (dict): The query parameters to be sent in the request.
            body (dict): The request body to be sent in the request.

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
        """
        args = {
            "endpoint": url,
            "action_result": self._action_result,
            "method": method.lower(),
            "headers": headers or {"x-tool": "splunk soar"},
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
            ret_val (RetVal): The return value from the REST call.
            response (dict): The response from the REST call.

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
        """
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        if isinstance(response, list):
            for item in response:
                self._action_result.add_data(item)
        else:
            last_analysis_date = response.get("data").get("attributes").get("last_analysis_date")
            last_analysis_stats = response.get("data").get("attributes").get("last_analysis_stats")
            tags = response.get("data").get("attributes").get("tags")
            if last_analysis_date:
                response["data"]["attributes"]["last_analysis_date"] = self._connector.util.convert_unix_to_utc(last_analysis_date)
            if last_analysis_stats:
                response["data"]["attributes"]["last_analysis_stats_string"] = ", ".join(
                    f"{key}:{value}" for key, value in last_analysis_stats.items()
                )
            if tags:
                response["data"]["attributes"]["tags"] = ", ".join(tags)
            self._action_result.add_data(response)

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_GET_REPORT_SUCCESS_RESPONSE,
        )
