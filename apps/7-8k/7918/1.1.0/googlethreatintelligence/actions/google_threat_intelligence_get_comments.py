# File: google_threat_intelligence_get_comments.py
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


class GetComments(BaseAction):
    """Class to handle get comments action."""

    def execute(self):
        """Execute get comment action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("get_comment"))
        ret_val = self._validate_params()
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        entity = self._param["entity"]
        password = self._param.get("password")
        limit = self._param.get("limit")
        entity_type = self._connector.util.get_data_type(entity)

        self._connector.debug_print(f"Running action {self._connector.get_action_identifier()} with {entity} and entity type {entity_type}.")

        if entity_type == consts.IP_ADDRESS or entity_type == consts.DOMAIN:
            endpoint, method = (
                consts.GET_COMMENT_ENDPOINT.format(entity_type=entity_type, entity=entity),
                "get",
            )
            ret_val, json_resp = self._make_rest_call(url=endpoint, method=method, limit=limit)
        elif entity_type == consts.URL:
            ret_val, url_id = self._connector.util.submit_url_for_analysis(self._action_result, entity)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            endpoint, method = (
                consts.GET_COMMENT_ENDPOINT.format(entity_type=entity_type, entity=url_id),
                "get",
            )
            ret_val, json_resp = self._make_rest_call(url=endpoint, method=method, limit=limit)
        elif entity_type == consts.FILE:
            ret_val, file_id = self._connector.util.get_file_hash_from_input(self._action_result, entity, password)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            endpoint, method = (
                consts.GET_COMMENT_ENDPOINT.format(entity_type=entity_type, entity=file_id),
                "get",
            )
            ret_val, json_resp = self._make_rest_call(url=endpoint, method=method, limit=limit)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        return self.__handle_response(ret_val, json_resp)

    def _validate_params(self):
        """
        Validate parameters of the action

        Args:
            self (object): This object

        Returns:
            bool: True if validation is successful, False otherwise
        """
        if "limit" in self._param:
            ret_val, value = self._connector.validator.validate_integer(self._action_result, self._param.get("limit"), "limit")

            if not ret_val:
                return ret_val

            self._param["limit"] = value
        return True

    def _make_rest_call(self, url, method, limit, headers=None, param=None, body=None):
        """
        Make a REST call to the API.

        Args:
            self (object): This object
            url (str): The URL of the API endpoint
            method (str): The HTTP method to use (e.g. "get", "post")
            limit (int): The maximum number of items to return
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

        return self._connector.util._paginator(limit=limit, **args)

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
                if date:
                    item["attributes"]["date"] = self._connector.util.convert_unix_to_utc(date)

                self._action_result.add_data(item)
        else:
            self._action_result.add_data(response)

        comments_count = len(response)

        summary = {
            "comments_retrieved": comments_count,
        }
        self._action_result.update_summary(summary)

        if comments_count == 0:
            return self._action_result.set_status(
                phantom.APP_SUCCESS,
                consts.ACTION_GET_COMMENTS_NOT_FOUND_RESPONSE,
            )

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_GET_COMMENT_SUCCESS_RESPONSE,
        )
