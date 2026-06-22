# File: infoblox_update_custom_list_items.py
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


class UpdateCustomListItems(BaseAction):
    """Class to handle update custom list items action.

    This action allows inserting or removing individual items (e.g., IPs, domains)
    in a custom list using the PATCH method to modify the list contents incrementally.
    """

    def _validate_params(self):
        """
        Validate action parameters.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        # Validate custom_list_id parameter
        custom_list_id = self._param.get("custom_list_id")
        ret_val = self._connector.validator.validate_integer(
            self._action_result, custom_list_id, "custom_list_id", allow_zero=False, allow_negative=False
        )
        if phantom.is_fail(ret_val):
            return ret_val

        # Validate items parameter format
        items_param = self._param.get("items")

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

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Update custom List Items"))

    def __check_custom_list_exists(self, custom_list_id):
        """
        Check if the custom list exists by making a GET request.

        Args:
            custom_list_id (int): ID of the custom list to check

        Returns:
            tuple: (status, response) - Status code and API response
        """
        endpoint = f"{consts.NAMED_LIST_ENDPOINT}/{custom_list_id}"
        self._connector.debug_print(f"Checking if custom list exists: {endpoint}")

        ret_val, response = self._connector.util.make_rest_call(endpoint=endpoint, action_result=self._action_result, method="get")

        if phantom.is_fail(ret_val):
            error_message = self._action_result.get_message() or ""
            if "not found" in error_message.lower() or "404" in error_message:
                return (
                    self._action_result.set_status(phantom.APP_ERROR, f"custom List not found with ID: {custom_list_id}"),
                    None,
                )
            return ret_val, None

        return ret_val, response

    def __build_payload_and_update_items(self):
        """
        Build the request payload and make the PATCH API call to update custom list items.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        custom_list_id = self._param["custom_list_id"]
        action = self._param.get("action", "Add")

        # Parse items into list
        item_list = self._items_list

        # Build payload based on action using correct API structure
        payload = {"deleted_items_described": [], "inserted_items_described": [], "updated_items_described": []}

        if action == "Add":
            # Add items to inserted_items_described array
            payload["inserted_items_described"] = [
                {
                    "description": "",  # Empty description as default
                    "item": item,
                }
                for item in item_list
            ]
        else:  # Remove
            # Add items to deleted_items_described array
            payload["deleted_items_described"] = [
                {
                    "description": "",  # Empty description as default
                    "item": item,
                }
                for item in item_list
            ]

        # Make the PATCH API call
        endpoint = f"{consts.NAMED_LIST_ENDPOINT}/{custom_list_id}/items"
        self._connector.debug_print(f"Making PATCH request to {endpoint}")
        self._connector.debug_print(f"Request payload: {payload}")

        return self._connector.util.make_rest_call(
            endpoint=endpoint,
            action_result=self._action_result,
            method="patch",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

    def __validate_response(self, response):
        """
        Validate the basic structure of the API response.

        Args:
            response (dict): The API response to validate

        Returns:
            int: phantom.APP_SUCCESS if valid, phantom.APP_ERROR otherwise
        """
        if not isinstance(response, dict):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: expected JSON object")

        # Check for expected response fields based on actual API structure
        expected_fields = ["deleted_items", "inserted_items", "updated_items"]
        if not any(field in response for field in expected_fields):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: missing expected fields")

        return phantom.APP_SUCCESS

    def __handle_response(self, response):
        """
        Handle the API response and process the updated custom list items data.

        Args:
            response (dict): The API response containing results

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        # Validate response structure
        ret_val = self.__validate_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        self._connector.debug_print("Processing custom list items update response")

        # Store complete API response
        self._action_result.add_data(response)

        # Extract information for summary
        deleted_items = response.get("deleted_items", [])
        inserted_items = response.get("inserted_items", [])
        updated_items = response.get("updated_items", [])

        action = self._param.get("action", "Add")
        custom_list_id = self._param["custom_list_id"]

        # Generate comprehensive summary
        summary = {
            "custom_list_id": custom_list_id,
            "action_performed": action,
            "deleted_items_count": len(deleted_items),
            "inserted_items_count": len(inserted_items),
            "updated_items_count": len(updated_items),
            "operation_successful": True,
        }

        self._action_result.update_summary(summary)

        # Generate success message based on action performed
        if action == "Add":
            success_message = consts.ACTION_UPDATE_NAMED_LIST_ITEMS_SUCCESS_RESPONSE.format("added", len(inserted_items), custom_list_id)
        else:
            success_message = consts.ACTION_UPDATE_NAMED_LIST_ITEMS_SUCCESS_RESPONSE.format("removed", len(deleted_items), custom_list_id)

        return self._action_result.set_status(phantom.APP_SUCCESS, success_message)

    def execute(self):
        """
        Execute update custom list items action following the modular approach.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Check if custom list exists
        Step 4: Build payload and update items
        Step 5: Validate and process response
        Step 6: Return results

        Returns:
            int: phantom.APP_SUCCESS on successful execution, phantom.APP_ERROR otherwise
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters
        self._connector.save_progress("Validating parameters")
        ret_val = self._validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        custom_list_id = self._param["custom_list_id"]
        action = self._param.get("action", "Add")

        # Step 3: Check if custom list exists
        self._connector.save_progress(f"Checking if custom list with ID {custom_list_id} exists")
        ret_val, _ = self.__check_custom_list_exists(custom_list_id)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 4: Build payload and update items
        self._connector.save_progress(f"Performing {action.lower()} operation on custom list items")
        ret_val, response = self.__build_payload_and_update_items()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 5: Validate and process response
        ret_val = self.__handle_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 6: Return results
        self._connector.save_progress("custom list items updated successfully")
        return phantom.APP_SUCCESS
