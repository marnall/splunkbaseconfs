# File: infoblox_create_network_list.py
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


class CreateNetworkList(BaseAction):
    """Class to handle create network list action."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Create Network List"))

    def __validate_params(self):
        """
        Validate and process the parameters for the action.

        Returns:
            int: phantom.APP_SUCCESS on success, phantom.APP_ERROR on failure
        """
        # Split and clean the items list from the comma-separated string
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

        # Validate we have at least one valid item
        if not items_list:
            return self._action_result.set_status(phantom.APP_ERROR, "No valid items found in the items parameter")

        # Store the parsed items for later use
        self._items_list = items_list
        return phantom.APP_SUCCESS

    def __make_api_call(self):
        """
        Make the REST API call to create a network list.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        # Prepare request body
        body = {"name": self._param.get("name"), "items": self._items_list}

        # Add optional description if provided
        if self._param.get("description"):
            body["description"] = self._param.get("description")

        # Set headers with Content-Type specified
        headers = {"Content-Type": "application/json"}

        # Make the REST call
        return self._connector.util.make_rest_call(
            endpoint=consts.NETWORK_LIST_ENDPOINT,
            action_result=self._action_result,
            method="post",
            data=body,
            headers=headers,
        )

    def __handle_response(self, response):
        """
        Handle the API response for create network list.

        Args:
            response (dict): The API response containing results

        Returns:
            int: phantom.APP_SUCCESS on successful creation, phantom.APP_ERROR otherwise
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
                phantom.APP_ERROR, consts.ACTION_CREATE_NETWORK_LIST_INVALID_RESPONSE.format(response=response)
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
            consts.ACTION_CREATE_NETWORK_LIST_SUCCESS_RESPONSE.format(name=network_list_data.get("name"), id=network_list_data.get("id")),
        )

        return phantom.APP_SUCCESS

    def execute(self):
        """
        Execute the create network list action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make REST call to create network list
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
