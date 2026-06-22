# File: infoblox_get_network_list.py
#
# Copyright 2025 Infoblox Inc.
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

import phantom.app as phantom

import infoblox_consts as consts
from actions import BaseAction


class GetNetworkList(BaseAction):
    """Action to retrieve network lists and their metadata.

    This action can be used to fetch network lists by either:
    - Providing a specific network_list_id to retrieve a single network list directly
    - Using a filter expression to retrieve multiple network lists matching certain criteria

    When network_list_id is provided, it takes precedence over any filter parameter.
    """

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Get Network Lists"))

    def __validate_params(self):
        """
        Validate action parameters.

        Note: Required parameter validation is handled by SOAR's built-in JSON schema validation.
        We only need to validate format/content when needed.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        # Validate network_list_id if provided
        network_list_id = self._param.get("network_list_id")
        if network_list_id is not None:
            ret_val, network_list_id = self._connector.validator.validate_integer(
                self._action_result, network_list_id, "network_list_id", allow_zero=False, allow_negative=False
            )
            if phantom.is_fail(ret_val):
                return ret_val
            # Store validated value back in params
            self._param["network_list_id"] = network_list_id

        # Set default values for offset and limit if not provided
        if not self._param.get("offset"):
            self._param["offset"] = 0

        if not self._param.get("limit"):
            self._param["limit"] = 100

        return phantom.APP_SUCCESS

    def __make_api_call(self):
        """
        Make the REST API call to get network lists.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        # Prepare query parameters
        params = {"_offset": self._param.get("offset"), "_limit": self._param.get("limit")}

        # Check if network_list_id is provided - it takes precedence over any filter
        network_list_id = self._param.get("network_list_id")
        if network_list_id is not None:
            # If ID is provided, create a filter expression to retrieve that specific network list
            params["_filter"] = f"id=={network_list_id}"
        # Otherwise, use any provided filter
        elif self._param.get("filter"):
            params["_filter"] = self._param.get("filter")

        # Make the GET call
        return self._connector.util.make_rest_call(
            endpoint=consts.NETWORK_LIST_ENDPOINT, action_result=self._action_result, method="get", params=params
        )

    def __handle_response(self, response):
        """
        Handle the API response for get network lists.

        Args:
            response (dict): The API response containing results

        Returns:
            int: phantom.APP_SUCCESS on successful retrieval, phantom.APP_ERROR otherwise
        """
        if not response:
            return self._action_result.set_status(phantom.APP_ERROR, "Empty response from server")

        # Check if results key exists and is a list
        if "results" not in response or not isinstance(response.get("results"), list):
            # Return success with empty list if no results found
            self._action_result.add_data({"results": []})
            self._action_result.update_summary({"total_count": 0})
            self._action_result.set_status(phantom.APP_SUCCESS, consts.ACTION_GET_NETWORK_LIST_EMPTY_RESPONSE)
            return phantom.APP_SUCCESS

        # Add the response data
        self._action_result.add_data(response)

        # Count the number of network lists returned
        network_lists = response.get("results", [])
        count = len(network_lists)

        # Create summary
        summary = {"total_count": count}
        self._action_result.update_summary(summary)

        # Set success message
        self._action_result.set_status(phantom.APP_SUCCESS, consts.ACTION_GET_NETWORK_LIST_SUCCESS_RESPONSE.format(count=count))

        return phantom.APP_SUCCESS

    def execute(self):
        """
        Execute the get network lists action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make REST call to get network lists
        Step 4: Handle the response
        """
        # Log action start
        self.__log_action_start()

        # Validate parameters
        ret_val = self.__validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        # Make API call
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            return ret_val

        # Handle response using dedicated method
        return self.__handle_response(response)
