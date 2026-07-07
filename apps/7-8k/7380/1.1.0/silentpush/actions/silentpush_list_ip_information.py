# File: silentpush_list_ip_information.py
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

from ipaddress import IPv4Address, ip_address

import phantom.app as phantom

import silentpush_consts as consts
from actions import BaseAction


class ListIpInformation(BaseAction):
    """Class to handle list ip information action."""

    def execute(self):
        """Execute list ip information action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MESSAGE.format("list_ip_information"))

        ret_val = self.__validate_and_separate_ips()
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        ret_val, ipv4_response, ipv6_response = self.__fetch_data()

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        response = self.__combine_results(ipv4_response, ipv6_response)

        return self.__handle_response(ret_val, response)

    def __valid_ip_address(self, ip: str) -> str:
        try:
            return "IPv4" if type(ip_address(ip)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"

    def __validate_and_separate_ips(self):
        """Validate and separate ips."""
        self._param["ipv4"] = []
        self._param["ipv6"] = []
        invalid_ip = []
        ips = [final_ip for ip in self._param["ips"].split(",") if (final_ip := ip.strip())]

        if not ips:
            return self._action_result.set_status(phantom.APP_ERROR, "Please provide a valid list of IPs")

        for ip in ips:
            if self.__valid_ip_address(ip) == "IPv4":
                self._param["ipv4"].append(ip)
            elif self.__valid_ip_address(ip) == "IPv6":
                self._param["ipv6"].append(ip)
            else:
                invalid_ip.append(ip)

        if invalid_ip:
            return self._action_result.set_status(
                phantom.APP_ERROR,
                f"Invalid Ips : {invalid_ip}. Please provide a valid list of IPs",
            )

        return True

    def __get_request_body(self, resource):
        """Get request body."""
        body = {}
        allow_none = []
        allow_empty = {}
        default_values = {}

        body["ips"] = self._param[resource]

        return self._connector.util.generate_json_body(body, allow_none, allow_empty, self._param, default_values)

    def __get_request_url_and_method(self, resource):
        """Get request endpoint and method."""
        endpoint = consts.LIST_IP_INFORMATION_ENDPOINT.replace("{{resource}}", str(resource))

        return endpoint, "post"

    def __make_rest_call(self, url, method, headers=None, param=None, body=None):
        """Invoke reset API."""
        args = {
            "endpoint": url,
            "action_result": self._action_result,
            "method": method.lower(),
            "headers": headers or {},
        }

        if body:
            args["json"] = body

        return self._connector.util.make_rest_call(**args)

    def __fetch_data(self):
        ipv4_response = {}
        ipv6_response = {}

        if self._param.get("ipv4"):
            request_body = self.__get_request_body("ipv4")
            endpoint, method = self.__get_request_url_and_method("ipv4")

            ret_val, ipv4_response = self.__make_rest_call(url=endpoint, method=method, body=request_body)

            if phantom.is_fail(ret_val):
                return self._action_result.get_status(), None, None

        if self._param.get("ipv6"):
            request_body = self.__get_request_body("ipv6")
            endpoint, method = self.__get_request_url_and_method("ipv6")

            ret_val, ipv6_response = self.__make_rest_call(url=endpoint, method=method, body=request_body)

            if phantom.is_fail(ret_val):
                return self._action_result.get_status(), None, None

        return (
            self._action_result.set_status(phantom.APP_SUCCESS),
            ipv4_response,
            ipv6_response,
        )

    @staticmethod
    def __combine_results(ipv4_response, ipv6_response):
        response = {}
        if ipv4_response:
            response = ipv4_response

        if ipv6_response:
            if response:
                ipv6_response = ipv6_response["response"]["ip2asn"]
                response["response"]["ip2asn"].extend(ipv6_response)
            else:
                response = ipv6_response

        return response

    def __handle_response(self, ret_val, response):
        """Process response received from the third party API."""
        self._action_result.add_data(response)

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.ACTION_LIST_DOMAIN_INFO_SUCCESS_RESPONSE)
