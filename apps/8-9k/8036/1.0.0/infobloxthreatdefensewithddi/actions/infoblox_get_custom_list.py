# File: infoblox_get_custom_list.py
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


class GetCustomList(BaseAction):
    """Class to handle get custom list action.

    This action retrieves custom lists from Infoblox BloxOne based on various query parameters.
    """

    def _validate_params(self):
        """Validate the parameters for the get custom list action.

        Checks that parameters are of the correct type and format.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        self._connector.debug_print("Validating parameters for get custom list action")

        # Validate limit if provided (must be a positive integer)
        limit = self._param.get("limit")
        if limit is not None:
            self._connector.debug_print(f"Validating limit parameter: {limit}")
            ret_val, limit = self._connector.validator.validate_integer(
                self._action_result, limit, "limit", allow_zero=False, allow_negative=False
            )
            if phantom.is_fail(ret_val):
                self._connector.debug_print(f"Limit validation failed: {self._action_result.get_message()}")
                return ret_val

        # Validate offset if provided (must be a non-negative integer)
        offset = self._param.get("offset")
        if offset is not None:
            self._connector.debug_print(f"Validating offset parameter: {offset}")
            ret_val, offset = self._connector.validator.validate_integer(
                self._action_result, offset, "offset", allow_zero=True, allow_negative=False
            )
            if phantom.is_fail(ret_val):
                self._connector.debug_print(f"Offset validation failed: {self._action_result.get_message()}")
                return ret_val

            # Validate custom_list_id if provided (must be an integer)
            custom_list_id = self._param.get("custom_list_id")
            if custom_list_id is not None:
                self._connector.debug_print(f"Validating ID parameter: {custom_list_id}")
                ret_val, custom_list_id = self._connector.validator.validate_integer(
                    self._action_result,
                    custom_list_id,
                    "custom_list_id",
                    allow_zero=True,  # ID=0 is allowed in some API cases
                    allow_negative=False,
                )
            if phantom.is_fail(ret_val):
                self._connector.debug_print(f"ID validation failed: {self._action_result.get_message()}")
                return ret_val

        # Check if name is provided without type
        name = self._param.get("name")
        type_val = self._param.get("type")

        if name and not type_val:
            self._connector.debug_print("Error: Name provided without Type")
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_NAME_WITHOUT_TYPE)

        return phantom.APP_SUCCESS

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Get custom list"))

    def __build_endpoint_and_params(self):
        """Build the endpoint and query parameters for the API call.

        Creates the appropriate endpoint and parameters based on the provided inputs
        according to the specified business logic.

        Returns:
            tuple: (endpoint, params)
        """
        custom_list_id = self._param.get("custom_list_id")
        name = self._param.get("name")
        type_val = self._param.get("type")
        tag_filter = self._param.get("tag_filter")
        tag_sort = self._param.get("tag_sort_order")
        limit = self._param.get("limit", 100)
        offset = self._param.get("offset", 0)

        params = {}

        # Add pagination parameters always
        if limit:
            params["_limit"] = limit
        if offset:
            params["_offset"] = offset

        # Rule 1: If both ID and Name are provided, prioritize ID
        if custom_list_id:
            # Single ID - use direct endpoint
            self._connector.debug_print(f"Single ID provided: {custom_list_id}, using direct endpoint")
            endpoint = f"{consts.NAMED_LIST_ENDPOINT}/{custom_list_id}"

            self._connector.debug_print(f"Using endpoint: {endpoint} with params: {params}")

            return endpoint, params

        # Rule 2: If both Name and Type are provided, use ID=0
        elif name and type_val:
            self._connector.debug_print("Both name and type provided, using ID=0 approach")
            endpoint = f"{consts.NAMED_LIST_ENDPOINT}/0"

            params["name"] = name
            params["type"] = type_val

            # If "Custom List ID" or "Name" is provided, the "Filter Tags" and “Sort By Filter"
            # parameters will be skipped.
            self._connector.debug_print(f"Using endpoint: {endpoint} with params: {params}")

            return endpoint, params

        # Rule 3: If neither ID nor Name is provided, use API without ID
        else:
            self._connector.debug_print("Using list endpoint with filters")
            endpoint = f"{consts.NAMED_LIST_ENDPOINT}"

            # Add name filter if provided
            if name:
                params["name"] = name

            # Add type filter
            if type_val:
                params["_filter"] = f'type=="{type_val}"'

            # Rule 4: Add tag filters if ID or Name is not provided
            if tag_filter:
                params["_tfilter"] = tag_filter
            if tag_sort:
                params["_torder_by"] = tag_sort

        self._connector.debug_print(f"Using endpoint: {endpoint} with params: {params}")

        return endpoint, params

    def __process_response(self, response):
        """Process the API response and update action result.

        Args:
            response (dict): The API response to process

        Returns:
            int: phantom.APP_SUCCESS on successful processing
        """
        self._connector.debug_print(f"Processing response: {response}")

        # Check if response contains 'results' key
        if isinstance(response, dict) and "results" in response:
            # Check if results is a list or a single object
            if isinstance(response["results"], list):
                # Multiple custom lists - add each item to action result
                for item in response["results"]:
                    self._action_result.add_data({"results": [item]})

                # Create summary
                summary = {"total_objects": len(response["results"])}

                message = consts.ACTION_GET_NAMED_LIST_SUCCESS_MULTIPLE.format(len(response["results"]))

            else:
                # Single custom list - convert to list format for consistent data paths
                # Add as a single item array in the results key for consistent data paths
                self._action_result.add_data({"results": [response["results"]]})

                # Create summary
                summary = {
                    "total_objects": 1,
                    "custom_list_id": response["results"].get("id"),
                    "name": response["results"].get("name"),
                }

                message = consts.ACTION_GET_NAMED_LIST_SUCCESS_SINGLE
        # Handle direct object or array responses (no 'results' key)
        elif isinstance(response, list):
            # Direct array response
            self._action_result.add_data({"results": response})

            # Create summary
            summary = {"total_objects": len(response)}

            message = consts.ACTION_GET_NAMED_LIST_SUCCESS_MULTIPLE.format(len(response))
        else:
            # Direct object response
            # Convert to list format for consistent data paths
            self._action_result.add_data({"results": [response]})

            # Create summary
            summary = {"total_objects": 1, "custom_list_id": response.get("id"), "name": response.get("name")}

            message = consts.ACTION_GET_NAMED_LIST_SUCCESS_SINGLE

        # Update summary
        self._action_result.update_summary(summary)

        return self._action_result.set_status(phantom.APP_SUCCESS, message)

    def __handle_error(self, ret_val, response):
        """Handle error responses from the API.

        Args:
            ret_val (int): The return value from the API call
            response (dict): The error response from the API

        Returns:
            int: phantom.APP_ERROR with an appropriate error message
        """
        # Check if the error response contains a specific message about the custom list not existing
        if isinstance(response, dict) and "error" in response:
            error_message = response.get("error")
            if "not found" in str(error_message).lower():
                return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_NAMED_LIST_NOT_FOUND)

        # Otherwise, return the status that was already set by the utility
        return self._action_result.get_status()

    def execute(self):
        """Execute get custom list action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Build endpoint and parameters
        Step 4: Make API call
        Step 5: Process response or handle errors
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters
        ret_val = self._validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 3: Build endpoint and parameters
        endpoint, params = self.__build_endpoint_and_params()

        # Step 4: Make API call
        self._connector.save_progress(consts.ACTION_GET_NAMED_LIST_START_MSG)
        ret_val, response = self._connector.util.make_rest_call(
            endpoint=endpoint, action_result=self._action_result, method="get", params=params
        )

        # Step 5: Process response or handle errors
        if phantom.is_fail(ret_val):
            return self.__handle_error(ret_val, response)

        return self.__process_response(response)
