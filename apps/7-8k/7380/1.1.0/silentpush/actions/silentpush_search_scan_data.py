# File: silentpush_search_scan_data.py
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

from urllib.parse import urlencode

import phantom.app as phantom

import silentpush_consts as consts
from actions import BaseAction


class SearchScanData(BaseAction):
    """Class to handle search scan data action."""

    def execute(self):
        """Execute search scan data action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MESSAGE.format("search_scan_data"))

        ret_val = self.__validate_params()
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        query_params = self.__get_query_params()
        request_body = self.__get_request_body()
        endpoint, method = self.__get_request_url_and_method()

        ret_val, response = self.__make_rest_call(url=endpoint, method=method, param=query_params, body=request_body)

        return self.__handle_response(ret_val, response)

    def __validate_params(self):
        """Validate parameters"""
        if "skip" in self._param:
            ret_val, value = self._connector.validator.validate_integer(
                self._action_result, self._param.get("skip"), "skip", allow_zero=True, allow_negative=False
            )

            if not ret_val:
                return ret_val

            self._param["skip"] = value

        if "limit" in self._param:
            ret_val, value = self._connector.validator.validate_integer(
                self._action_result, self._param.get("limit"), "limit", allow_negative=False
            )

            if not ret_val:
                return ret_val

            self._param["limit"] = value

        if "query" in self._param:
            value = self._param.get("query", "").replace('"', '"').replace("\\", "\\\\")
            self._param["query"] = value

        if "sort" in self._param:
            sort_list = [clean_sort for sort in self._param["sort"].split(",") if (clean_sort := sort.strip())]

            self._param["sort"] = sort_list

        if "fields" in self._param:
            fields_list = [clean_fields for fields in self._param["fields"].split(",") if (clean_fields := fields.strip())]

            self._param["fields"] = fields_list

        if "with_metadata" in self._param:
            value = self._param.get("with_metadata", False)

            self._param["with_metadata"] = int(value)

        return True

    def __get_query_params(self):
        """Get request query parameters"""
        query_params = {"skip": "skip", "limit": "limit", "with_metadata": "with_metadata"}

        payload = {}
        for key, value in query_params.items():
            if value in self._param:
                payload[key] = self._param[value]

        return payload

    def __get_request_body(self):
        """Get request body"""
        body = {"query": "{{query}}", "fields": "{{fields}}", "sort": "{{sort}}"}
        allow_none = []
        allow_empty = {"query": "string"}
        default_values = {}

        return self._connector.util.generate_json_body(body, allow_none, allow_empty, self._param, default_values)

    def __get_request_url_and_method(self):
        """Get request endpoint and method"""
        parameters = []

        endpoint = consts.SEARCH_SCAN_DATA_ENDPOINT
        for parameter in parameters:
            endpoint = endpoint.replace("{{##}}".replace("##", parameter), str(self._param.get(parameter)))

        return endpoint, "post"

    def __make_rest_call(self, url, method, headers=None, param=None, body=None):
        """Invoke API"""
        args = {"endpoint": url, "action_result": self._action_result, "method": method.lower(), "headers": headers or {}}

        if param:
            args["endpoint"] = f"{args['endpoint']}?{urlencode(param)}"

        if body:
            args["json"] = body

        args["error_path"] = "response.error"
        return self._connector.util.make_rest_call(**args)

    def __handle_response(self, ret_val, response):
        """Process response received from the third party API"""
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        self._action_result.add_data(response)

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.ACTION_SEARCH_SCAN_DATA_SUCCESS_RESPONSE)
