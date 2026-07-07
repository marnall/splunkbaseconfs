# File: silentpush_list_domain_infratags.py
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


class ListDomainInfratags(BaseAction):
    """Class to handle list domain infratags action."""

    def execute(self):
        """Execute list domain infratags action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MESSAGE.format("list_domain_infratags"))

        ret_val = self.__validate_params()
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        query_params = self.__get_query_params()
        request_body = self.__get_request_body()
        endpoint, method = self.__get_request_url_and_method()

        ret_val, response = self.__make_rest_call(url=endpoint, method=method, param=query_params, body=request_body)

        return self.__handle_response(ret_val, response)

    def __validate_params(self):
        """Validate parameters."""
        domains = [final_domain for domain in self._param["domains"].split(",") if (final_domain := domain.strip())]

        if not domains:
            return self._action_result.set_status(phantom.APP_ERROR, "Please provide a valid list of domains")

        self._param["domains"] = domains

        if "mode" in self._param:
            ret_val, value = self._connector.validator.validate_dropdown(
                self._action_result, self._param.get("mode"), "mode", consts.LIST_DOMAIN_INFRATAGS_MODE_OPTIONS
            )

            if not ret_val:
                return ret_val

            self._param["mode"] = value

        if "match" in self._param:
            ret_val, value = self._connector.validator.validate_dropdown(
                self._action_result, self._param.get("match"), "match", consts.LIST_DOMAIN_INFRATAGS_MATCH_OPTIONS
            )

            if not ret_val:
                return ret_val

            self._param["match"] = value

        if "clusters" in self._param:
            ret_val, value = self._connector.validator.validate_boolean(self._action_result, self._param.get("clusters"), "clusters")

            if not ret_val:
                return ret_val

            self._param["clusters"] = int(value)

        return True

    def __get_query_params(self):
        """Get request query parameters."""
        query_params = {"mode": "mode", "match": "match", "as_of": "as_of", "clusters": "clusters"}

        payload = {}
        for key, value in query_params.items():
            if value in self._param:
                payload[key] = self._param[value]

        return payload

    def __get_request_body(self):
        """Get request body."""
        body = {"domains": "{{domains}}"}
        allow_none = []
        allow_empty = {}
        default_values = {}

        return self._connector.util.generate_json_body(body, allow_none, allow_empty, self._param, default_values)

    def __get_request_url_and_method(self):
        """Get request endpoint and method."""
        endpoint = consts.LIST_DOMAIN_INFRATAGS_ENDPOINT

        return endpoint, "post"

    def __make_rest_call(self, url, method, headers=None, param=None, body=None):
        """Invoke API."""
        args = {"endpoint": url, "action_result": self._action_result, "method": method.lower(), "headers": headers or {}}

        if param:
            args["endpoint"] = f"{args['endpoint']}?{urlencode(param)}"

        if body:
            args["json"] = body

        return self._connector.util.make_rest_call(**args)

    def __handle_response(self, ret_val, response):
        """Process response received from the third party API."""
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        self._action_result.add_data(response)

        summary = {"total_infratags": len(response.get("response", {}).get("infratags", []))}
        self._action_result.update_summary(summary)

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.ACTION_DOMAIN_INFRATAGS_SUCCESS_RESPONSE)
