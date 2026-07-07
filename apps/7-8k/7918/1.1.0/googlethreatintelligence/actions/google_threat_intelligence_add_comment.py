# File: google_threat_intelligence_add_comment.py
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


class AddComment(BaseAction):
    """Class to handle add comment action."""

    def execute(self):
        """Execute add comment action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("add_comment"))

        entity = self._param["entity"]
        password = self._param.get("password")
        comment_text = self._param.get("comment_text")

        entity_type = self._connector.util.get_data_type(entity)
        request_body = self.__get_request_body(comment_text)

        self._connector.debug_print(f"Running action add_comment with {entity} and entity type {entity_type}.")

        if entity_type == consts.IP_ADDRESS or entity_type == consts.DOMAIN:
            endpoint, method = (
                consts.ADD_COMMENT_ENDPOINT.format(entity_type=entity_type, entity=entity),
                "post",
            )

        elif entity_type == consts.URL:
            ret_val, url_id = self._connector.util.submit_url_for_analysis(self._action_result, entity)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            endpoint, method = (
                consts.ADD_COMMENT_ENDPOINT.format(entity_type=entity_type, entity=url_id),
                "post",
            )

        elif entity_type == consts.FILE:
            ret_val, file_id = self._connector.util.get_file_hash_from_input(self._action_result, entity, password)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            endpoint, method = (
                consts.ADD_COMMENT_ENDPOINT.format(entity_type=entity_type, entity=file_id),
                "post",
            )

        else:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_MESSAGE_INVALID_ENTITY)

        self._connector.debug_print(f"endpoint: {endpoint}, method: {method}")
        ret_val, response = self._make_rest_call(url=endpoint, method=method, body=request_body)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        return self.__handle_response(ret_val, response)

    def __get_request_body(self, comment_text):
        """
        Generates a request body for adding a comment.

        Args:
            comment_text (str): The text of the comment to be added.

        Returns:
            dict: The generated request body.
        """
        body = {"data": {"type": "comment", "attributes": {"text": f"{comment_text}"}}}
        allow_none = []
        allow_empty = {}
        default_values = {}

        return self._connector.util.generate_json_body(body, allow_none, allow_empty, self._param, default_values)

    def _make_rest_call(self, url, method, headers=None, param=None, body=None):
        """
        Invoke API.

        Args:
            url (str): The URL to make the REST call to.
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
            "headers": headers or {},
        }

        if param:
            args["endpoint"] = f"{args['endpoint']}?{urlencode(param)}"

        if body:
            args["json"] = body

        return self._connector.util.make_rest_call(**args)

    def __handle_response(self, ret_val, response):
        """Process response received from the third party API

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
                self._action_result.add_data(item)
        else:
            self._action_result.add_data(response)

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_ADD_COMMENT_SUCCESS_RESPONSE,
        )
