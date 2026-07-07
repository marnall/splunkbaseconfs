# File: silentpush_forward_padns_lookup.py
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


class ForwardPadnsLookup(BaseAction):
    """Class to handle forward padns lookup action."""

    def execute(self):
        """Execute forward padns lookup action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MESSAGE.format("forward_padns_lookup"))
        ret_val = self.__validate_params()
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        query_params = self.__get_query_params()
        endpoint, method = self.__get_request_url_and_method()

        ret_val, response = self.__make_rest_call(url=endpoint, method=method, param=query_params)

        return self.__handle_response(ret_val, response)

    def __validate_params(self):
        """Validate parameters"""
        if "qtype" in self._param:
            ret_val, value = self._connector.validator.validate_dropdown(
                self._action_result,
                self._param.get("qtype"),
                "qtype",
                consts.FORWARD_PADNS_LOOKUP_QTYPE_OPTIONS,
            )

            if not ret_val:
                return ret_val

            self._param["qtype"] = value

        if "netmask" in self._param:
            ret_val, value = self._connector.validator.validate_integer(self._action_result, self._param.get("netmask"), "netmask")

            if not ret_val:
                return ret_val

            self._param["netmask"] = value

        if "match" in self._param:
            ret_val, value = self._connector.validator.validate_dropdown(
                self._action_result,
                self._param.get("match"),
                "match",
                consts.PADNS_LOOKUP_MATCH_OPTIONS,
            )

            if not ret_val:
                return ret_val

            self._param["match"] = value

        if "output_format" in self._param:
            ret_val, value = self._connector.validator.validate_dropdown(
                self._action_result,
                self._param.get("output_format"),
                "output_format",
                consts.PADNS_LOOKUP_OUTPUT_FORMAT_OPTIONS,
            )

            if not ret_val:
                return ret_val

            self._param["output_format"] = value

        if "prefer" in self._param:
            ret_val, value = self._connector.validator.validate_dropdown(
                self._action_result,
                self._param.get("prefer"),
                "prefer",
                consts.PADNS_LOOKUP_PREFER_OPTIONS,
            )

            if not ret_val:
                return ret_val

            self._param["prefer"] = value

        if "max_wait" in self._param:
            ret_val, value = self._connector.validator.validate_integer(self._action_result, self._param.get("max_wait"), "max_wait")

            if not ret_val:
                return ret_val

            self._param["max_wait"] = value

        if "skip" in self._param:
            ret_val, value = self._connector.validator.validate_integer(
                self._action_result,
                self._param.get("skip"),
                "skip",
                allow_negative=False,
                allow_zero=True,
            )

            if not ret_val:
                return ret_val

            self._param["skip"] = value

        if "limit" in self._param:
            ret_val, value = self._connector.validator.validate_integer(self._action_result, self._param.get("limit"), "limit")

            if not ret_val:
                return ret_val

            self._param["limit"] = value

        if "sort" in self._param:
            sort_list = [clean_sort for sort in self._param.get("sort", "").split(",") if (clean_sort := sort.strip())]

            if len(sort_list):
                self._param["sort"] = "&sort=".join(sort_list)
            else:
                del self._param["sort"]

        if "with_metadata" in self._param:
            value = self._param.get("with_metadata", False)

            self._param["with_metadata"] = int(value)

        if "subdomains" in self._param:
            value = self._param.get("subdomains", False)

            self._param["subdomains"] = int(value)

        return True

    def __get_query_params(self):
        """Get request query parameters"""
        query_params = {
            "netmask": "netmask",
            "subdomains": "subdomains",
            "regex": "regex",
            "match": "match",
            "first_seen_after": "first_seen_after",
            "first_seen_before": "first_seen_before",
            "last_seen_after": "last_seen_after",
            "last_seen_before": "last_seen_before",
            "as_of": "as_of",
            "sort": "sort",
            "output_format": "output_format",
            "prefer": "prefer",
            "with_metadata": "with_metadata",
            "max_wait": "max_wait",
            "skip": "skip",
            "limit": "limit",
        }
        payload = {}
        for key, value in query_params.items():
            if value in self._param:
                payload[key] = self._param[value]

        return payload

    def __get_request_url_and_method(self):
        """Get request endpoint and method"""
        parameters = ["qtype", "qname"]

        endpoint = consts.FORWARD_PADNS_LOOKUP_ENDPOINT
        for parameter in parameters:
            endpoint = endpoint.replace("{{##}}".replace("##", parameter), str(self._param.get(parameter)))

        return endpoint, "get"

    def __make_rest_call(self, url, method, headers=None, param=None, body=None):
        """Invoke API"""
        args = {
            "endpoint": url,
            "action_result": self._action_result,
            "method": method.lower(),
            "headers": headers or {},
        }

        if param:
            args["endpoint"] = f"{args['endpoint']}?{urlencode(param)}"

        args["error_path"] = "response.error"

        return self._connector.util.make_rest_call(**args)

    def __handle_response(self, ret_val, response):
        """Process response received from the third party API"""
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        self._action_result.add_data(response)

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.ACTION_FORWARD_LOOKUP_SUCCESS_RESPONSE)
