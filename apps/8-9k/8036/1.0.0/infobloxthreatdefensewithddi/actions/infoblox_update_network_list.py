# File: infoblox_update_network_list.py
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


class UpdateNetworkList(BaseAction):
    """Action to update an existing network list with new metadata and CIDRs."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Update Network List"))

    def __validate_params(self):
        """
        Validate action parameters.

        Note: Required parameter validation is handled by SOAR's built-in JSON schema validation.
        We only need to validate format/content when needed.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        # If items parameter is provided, split and clean the list
        if self._param.get("items"):
            items_param = self._param["items"]

            # Process items list
            items_list = []
            for item in items_param.split(","):
                item = item.strip()
                # Remove surrounding quotes if present
                if (item.startswith('"') and item.endswith('"')) or (item.startswith("'") and item.endswith("'")):
                    item = item[1:-1]
                if item:  # Only add non-empty items
                    items_list.append(item)

            self._items_list = items_list

            # Validate we have at least one valid item if provided
            if not self._items_list:
                return self._action_result.set_status(phantom.APP_ERROR, "No valid items found in the items parameter")
        else:
            # Will be filled from existing network list data
            self._items_list = None

        # Check if description is "empty" to intentionally clear it
        if self._param.get("description") == "empty":
            self._param["description"] = ""

        return phantom.APP_SUCCESS

    def __get_network_list(self):
        """
        Fetch current network list data by ID.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        network_list_id = self._param["network_list_id"]
        endpoint = consts.NETWORK_LIST_DETAIL_ENDPOINT.format(network_list_id)

        # Make the GET call to retrieve current data
        return self._connector.util.make_rest_call(endpoint=endpoint, action_result=self._action_result, method="get")

    def __make_api_call(self, current_data):
        """
        Make the REST API call to update the network list.

        Args:
            current_data (dict): The current network list data

        Returns:
            tuple: (status, response) - Status code and API response
        """
        network_list_id = self._param["network_list_id"]
        endpoint = consts.NETWORK_LIST_DETAIL_ENDPOINT.format(network_list_id)

        # Extract the network list data from the response
        if "results" in current_data:
            network_list_data = current_data.get("results")
        else:
            network_list_data = current_data

        # Create a copy of the entire response to preserve all fields
        body = dict(network_list_data)

        # Update only the fields that were provided by the user
        if self._param.get("name"):
            body["name"] = self._param.get("name")

        if self._items_list is not None:
            body["items"] = self._items_list

        # Special handling for description
        if "description" in self._param:
            body["description"] = self._param["description"]

        # Set headers with Content-Type specified
        headers = {"Content-Type": "application/json"}

        # Make the PUT call
        return self._connector.util.make_rest_call(
            endpoint=endpoint, action_result=self._action_result, method="put", data=body, headers=headers
        )

    def __handle_response(self, response):
        """
        Handle the API response for update network list.

        Args:
            response (dict): The API response containing results

        Returns:
            int: phantom.APP_SUCCESS on successful update, phantom.APP_ERROR otherwise
        """
        if not response:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ACTION_EMPTY_RESPONSE)

        # The response structure shows the actual network list data is inside a 'results' key
        if "results" in response:
            # Extract the nested results object
            network_list_data = response.get("results")
        else:
            # If not nested, use the response directly
            network_list_data = response

        # Validate we have the expected fields
        if not isinstance(network_list_data, dict) or "id" not in network_list_data:
            return self._action_result.set_status(
                phantom.APP_ERROR, consts.ACTION_UPDATE_NETWORK_LIST_INVALID_RESPONSE.format(response=response)
            )

        # Add the response as data
        self._action_result.add_data({"results": network_list_data})

        # Create summary with the requested table view fields
        summary = {
            "network_list_id": network_list_data.get("id"),
            "name": network_list_data.get("name"),
            "description": network_list_data.get("description", ""),
            "security_policy_id": network_list_data.get("policy_id"),
        }
        self._action_result.update_summary(summary)

        # Set the message
        self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_UPDATE_NETWORK_LIST_SUCCESS_RESPONSE.format(name=network_list_data.get("name"), id=network_list_data.get("id")),
        )

        return phantom.APP_SUCCESS

    def execute(self):
        """
        Execute the update network list action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Get current network list data
        Step 4: Make API call to update network list
        Step 5: Handle the response
        """
        # Log action start
        self.__log_action_start()

        # Validate parameters
        ret_val = self.__validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        # Get current network list data
        ret_val, current_data = self.__get_network_list()
        if phantom.is_fail(ret_val):
            return ret_val

        # Make API call to update network list
        ret_val, response = self.__make_api_call(current_data)
        if phantom.is_fail(ret_val):
            return ret_val

        # Handle response using dedicated method
        return self.__handle_response(response)
