# File: silentpush_list_domain_information.py
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


class ListDomainInformation(BaseAction):
    """Class to handle list domain information action."""

    def execute(self):
        """Execute list domain information action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Fetch Risk Score, Optional
        Step 8: Fetch Whois Information, Optional
        Step 9: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MESSAGE.format("list_domain_information"))

        ret_val = self.__validate_params()
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        request_body = self.__get_request_body("domains", self._param["domains"])
        endpoint, method = self.__get_request_url_and_method("domain_info")

        ret_val, response = self.__make_rest_call(url=endpoint, method=method, body=request_body)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        output_response = {}
        output_response["domain_information"] = response

        if self._param.get("fetch_risk_score", False):
            endpoint, method = self.__get_request_url_and_method("risk_score")
            ret_val, response = self.__make_rest_call(url=endpoint, method=method, body=request_body)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()
            output_response["risk_score"] = response

        if self._param.get("fetch_whois_info", False):
            result = []
            for domain in self._param["domains"]:
                endpoint, method = self.__get_request_url_and_method("live_whois", domain)
                ret_val, response = self.__make_rest_call(url=endpoint, method=method)
                if phantom.is_fail(ret_val):
                    return self._action_result.get_status()
                result.append(response)

            output_response["live_whois_information"] = result

        return self.__handle_response(ret_val, output_response)

    def __validate_params(self):
        """Validate parameters."""
        if "fetch_risk_score" in self._param:
            ret_val, value = self._connector.validator.validate_boolean(
                self._action_result,
                self._param.get("fetch_risk_score"),
                "fetch_risk_score",
            )

            if not ret_val:
                return ret_val

            self._param["fetch_risk_score"] = value

        if "fetch_whois_info" in self._param:
            ret_val, value = self._connector.validator.validate_boolean(
                self._action_result,
                self._param.get("fetch_whois_info"),
                "fetch_whois_info",
            )

            if not ret_val:
                return ret_val

            self._param["fetch_whois_info"] = value

        if "domains" in self._param:
            domain_list = [clean_domain for domain in self._param["domains"].split(",") if (clean_domain := domain.strip())]
            if not domain_list:
                return self._action_result.set_status(
                    phantom.APP_ERROR,
                    consts.ERROR_INVALID_PARAM.format(key="domains"),
                )

            self._param["domains"] = domain_list

        return True

    def __get_request_body(self, key, param_list):
        """Get request body."""
        body = {f"{key}": param_list}
        allow_none = []
        allow_empty = {}
        default_values = {}

        return self._connector.util.generate_json_body(body, allow_none, allow_empty, self._param, default_values)

    def __get_request_url_and_method(self, request, query_param=None):
        """Get request endpoint and method."""
        method = "post"
        if request == "domain_info":
            endpoint = consts.LIST_DOMAIN_INFORMATION_ENDPOINT
        elif request == "risk_score":
            endpoint = consts.LIST_DOMAIN_ENDPOINT_RISK_SCORE_ENDPOINT
        elif request == "live_whois":
            endpoint = consts.LIST_DOMAIN_ENDPOINT_WHOIS_INFO_ENDPOINT.format(query_param)
            method = "get"

        return endpoint, method

    def __make_rest_call(self, url, method, headers=None, param=None, body=None):
        """Invoke API."""
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

        args["error_path"] = "response.error"

        return self._connector.util.make_rest_call(**args)

    def __handle_response(self, ret_val, response):
        """Process response received from the third party API."""
        if response.get("domain_information"):
            response["domain_information"] = response["domain_information"].get("response", {}).get("domaininfo", {})

        if response.get("risk_score"):
            response["risk_score"] = response["risk_score"].get("response", {})

        if response.get("live_whois_information"):
            response["live_whois_information"] = [
                result.get("response", {}).get("whois_live", {}) for result in response["live_whois_information"]
            ]

        self._action_result.add_data(response)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.ACTION_LIST_DOMAIN_INFO_SUCCESS_RESPONSE)
