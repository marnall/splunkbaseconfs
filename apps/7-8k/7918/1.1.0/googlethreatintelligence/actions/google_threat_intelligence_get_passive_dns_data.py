# File: google_threat_intelligence_get_passive_dns_data.py
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


class GetPassiveDnsData(BaseAction):
    """Class to handle get passive dns data action."""

    def execute(self):
        """Execute get passive dns data action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("get_passive_dns_data"))

        entity = self._param["entity"]
        entity_type = self._connector.util.get_data_type(entity)

        self._connector.debug_print(f"Running action {self._connector.get_action_identifier()} with {entity} and entity type {entity_type}.")

        if entity_type == consts.IP_ADDRESS or entity_type == consts.DOMAIN:
            endpoint, method = (
                consts.GET_PASSIVE_DNS_DATA_ENDPOINT.format(entity_type=entity_type, entity=entity),
                "get",
            )
        else:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_MESSAGE_INVALID_ENTITY_DNS)

        ret_val, response = self._make_rest_call(url=endpoint, method=method)

        return self.__handle_response(ret_val, response)

    def _make_rest_call(self, url, method, headers=None, param=None, body=None):
        """
        Make a REST call to the API.

        Args:
            self (object): This object
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

        return self._connector.util._paginator(limit=100, **args)

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
                date = item.get("attributes").get("date")
                host_name_last_analysis_stats = item.get("attributes").get("host_name_last_analysis_stats")
                ip_address_last_analysis_stats = item.get("attributes").get("ip_address_last_analysis_stats")
                if date:
                    item["attributes"]["date"] = self._connector.util.convert_unix_to_utc(date)
                self._action_result.add_data(item)
                if host_name_last_analysis_stats:
                    item["attributes"]["host_name_last_analysis_stats"] = ", ".join(
                        f"{key}:{value}" for key, value in host_name_last_analysis_stats.items()
                    )
                if ip_address_last_analysis_stats:
                    item["attributes"]["ip_address_last_analysis_stats"] = ", ".join(
                        f"{key}:{value}" for key, value in ip_address_last_analysis_stats.items()
                    )

        else:
            self._action_result.add_data(response)

        summary = {
            "count_passive_dns_data": len(response),
        }
        self._action_result.update_summary(summary)

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_GET_PASSIVE_DNS_DATA_SUCCESS_RESPONSE,
        )
