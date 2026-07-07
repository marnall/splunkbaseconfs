# File: silentpush_get_indicators_of_future_attack_feed.py
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


class GetFutureAttackFeed(BaseAction):
    """Class to handle get indicators of future attack feed action."""

    def execute(self):
        """Execute get indicators of future attack feed action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MESSAGE.format("get_indicators_of_future_attack_feed"))

        ret_val = self.__validate_params()
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        query_params = self.__get_query_params()
        endpoint, method = self.__get_request_url_and_method()

        ret_val, response = self.__make_rest_call(url=endpoint, method=method, param=query_params)

        return self.__handle_response(ret_val, response)

    def __validate_params(self):
        """Validate parameters"""
        if "page_no" in self._param:
            ret_val, value = self._connector.validator.validate_integer(self._action_result, self._param.get("page_no"), "page_no")

            if not ret_val:
                return ret_val

            self._param["page_no"] = value

        if "page_size" in self._param:
            ret_val, value = self._connector.validator.validate_integer(self._action_result, self._param.get("page_size"), "page_size")

            if not ret_val:
                return ret_val

            self._param["page_size"] = value

        return True

    def __get_query_params(self):
        """Get request query parameters"""
        query_params = {
            "page": "page_no",
            "limit": "page_size",
            "distinct": "distinct",
            "source_uuids": "feed_uuid",
            "order": "order",
            "state": "state",
            "advanced": "advanced",
        }
        default_values = {
            "distinct": False,
            "order": "-total_ioc,-total_source_score",
            "state": "Feed",
            "advanced": "advanced",
            "page_size": 10000,
            "page_no": 1,
        }

        payload = {}
        for key, value in query_params.items():
            if value in self._param:
                payload[key] = self._param[value]
            elif value in default_values:
                payload[key] = default_values[value]

        return payload

    def __get_request_url_and_method(self):
        """Get request endpoint and method"""
        endpoint = consts.GET_FUTURE_ATTACK_FEED_ENDPOINT

        return endpoint, "get"

    def __make_rest_call(self, url, method, headers=None, param=None, body=None):
        """Invoke API"""
        args = {"endpoint": url, "action_result": self._action_result, "method": method.lower(), "headers": headers or {}}

        if param:
            args["endpoint"] = f"{args['endpoint']}?{urlencode(param)}"

        return self._connector.util.make_rest_call(**args)

    def __handle_response(self, ret_val, response):
        """Process response received from the third party API"""
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        for item in response:
            self._action_result.add_data(item)

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.ACTION_FUTURE_ATTACK_FEED_SUCCESS_RESPONSE)
