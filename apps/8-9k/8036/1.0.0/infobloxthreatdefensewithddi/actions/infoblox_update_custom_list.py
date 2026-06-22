# File: infoblox_update_custom_list.py
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

import json

import phantom.app as phantom

import infoblox_consts as consts
from actions import BaseAction


class UpdateCustomList(BaseAction):
    """Action class for updating custom lists in Infoblox Cloud."""

    def _validate_params(self):
        """Validate and process input parameters.

        Returns:
            int: phantom.APP_SUCCESS on successful validation, phantom.APP_ERROR otherwise
        """
        # Validate tags parameter (if provided)
        tags = self._param.get("tags", "").strip()
        if tags:
            if tags.lower() == "empty":
                # Special case: clear tags
                self._param["tags"] = {}
            else:
                try:
                    tags_parsed = json.loads(tags)
                    if not isinstance(tags_parsed, dict):
                        return self._action_result.set_status(phantom.APP_ERROR, "Tags must be a valid JSON object")
                    self._param["tags"] = tags_parsed
                except json.JSONDecodeError as e:
                    return self._action_result.set_status(phantom.APP_ERROR, f"Invalid JSON format for tags: {e!s}")

        return phantom.APP_SUCCESS

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Update Custom List"))

    def __read_custom_list(self, custom_list_id):
        """Read the existing custom list to verify existence and get current data.

        Args:
            custom_list_id (str): The ID of the custom list to read

        Returns:
            tuple: (status, response) - Status code and API response
        """
        endpoint = f"{consts.NAMED_LIST_ENDPOINT}/{custom_list_id}"
        self._connector.debug_print(f"Reading custom list with ID: {custom_list_id} from endpoint: {endpoint}")

        ret_val, response = self._connector.util.make_rest_call(endpoint=endpoint, action_result=self._action_result, method="get")

        if phantom.is_fail(ret_val):
            # Check if this is a "not found" error
            error_message = self._action_result.get_message() or ""
            if "not found" in error_message.lower() or "404" in error_message:
                return (
                    self._action_result.set_status(phantom.APP_ERROR, f"Custom List not found with ID: {custom_list_id}"),
                    None,
                )
            return ret_val, None

        return ret_val, response

    def __build_update_payload(self, existing_data):
        """Build the request payload for updating the custom list.

        Args:
            existing_data (dict): Current custom list data from API

        Returns:
            dict: Request payload for the API call
        """
        # Start with all existing data to preserve everything
        payload = existing_data.get("results", {})

        # Remove read-only fields that shouldn't be sent in update requests
        read_only_fields = ["id", "created_time", "updated_time"]
        for field in read_only_fields:
            payload.pop(field, None)

        # Handle items vs items_described conflict - API expects only one
        # Prioritize items_described (recommended format) over items
        if "items_described" in payload and "items" in payload:
            self._connector.debug_print("Both 'items' and 'items_described' found. Removing 'items' to avoid API conflict.")
            payload.pop("items", None)
        elif "items_described" not in payload and "items" not in payload:
            # If neither exists, ensure at least items_described is present (even if empty)
            payload["items_described"] = []

        # Update only the fields that were provided as parameters
        name = self._param.get("name", "").strip()
        if name:
            payload["name"] = name

        description = self._param.get("description", "").strip()
        if description:
            payload["description"] = description

        confidence_level = self._param.get("confidence_level", "").strip()
        if confidence_level:
            payload["confidence_level"] = confidence_level

        threat_level = self._param.get("threat_level", "").strip()
        if threat_level:
            payload["threat_level"] = threat_level

        # Handle tags - special handling for "empty" keyword and JSON parsing
        tags = self._param.get("tags", "")
        if tags or tags == {}:
            payload["tags"] = tags

        return payload

    def __make_update_api_call(self, custom_list_id, payload):
        """Make the REST API call to update the custom list.

        Args:
            custom_list_id (str): The ID of the custom list to update
            payload (dict): Request payload

        Returns:
            tuple: (status, response) - Status code and API response
        """
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        endpoint = f"{consts.NAMED_LIST_ENDPOINT}/{custom_list_id}"

        self._connector.debug_print(f"Updating custom list with payload: {json.dumps(payload, indent=2)}")

        ret_val, response = self._connector.util.make_rest_call(
            endpoint=endpoint,
            action_result=self._action_result,
            method="put",
            headers=headers,
            data=payload,
        )

        if phantom.is_fail(ret_val):
            # Check for duplicate name error
            error_message = self._action_result.get_message() or ""
            if "duplicate name" in error_message.lower() or "already exists" in error_message.lower():
                return (
                    self._action_result.set_status(
                        phantom.APP_ERROR,
                        f"A custom list with name '{payload.get('name', '')}' already exists. Names must be unique.",
                    ),
                    None,
                )

        return ret_val, response

    def __validate_response(self, response):
        """Validate the API response structure.

        Args:
            response (dict): The API response to validate

        Returns:
            int: phantom.APP_SUCCESS if valid, phantom.APP_ERROR otherwise
        """
        self._connector.debug_print(f"Validating custom list update response: {json.dumps(response, indent=2)}")
        if not response:
            return self._action_result.set_status(phantom.APP_ERROR, "Empty response received from server")

        if not isinstance(response, dict):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format received from server")

        # Check for required fields in response
        required_fields = ["id", "name"]
        for field in required_fields:
            if field not in response.get("results", {}):
                return self._action_result.set_status(phantom.APP_ERROR, f"Response missing required field: {field}")

        return phantom.APP_SUCCESS

    def __handle_response(self, response):
        """Handle the API response and update action result.

        Args:
            response (dict): The API response containing results

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        try:
            self._connector.debug_print(f"Processing custom list update response: {json.dumps(response, indent=2)}")
            results = response.get("results", {})

            # Add the complete results data to action result
            self._action_result.add_data({"results": results})

            # Update summary information
            summary = self._action_result.update_summary({})
            summary["total_objects"] = 1
            summary["total_objects_successful"] = 1
            summary["custom_list_id"] = results.get("id")
            summary["custom_list_name"] = results.get("name", "")
            summary["item_count"] = results.get("item_count", 0)

            return phantom.APP_SUCCESS

        except Exception as e:
            return self._action_result.set_status(phantom.APP_ERROR, f"Error processing response: {e!s}")

    def execute(self):
        """Execute update custom list action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Read existing custom list to verify existence
        Step 4: Build update payload
        Step 5: Make REST call to update custom list
        Step 6: Validate and process response
        Step 7: Return results

        Returns:
            int: phantom.APP_SUCCESS on successful execution, phantom.APP_ERROR otherwise
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters
        ret_val = self._validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        custom_list_id = self._param["custom_list_id"]

        # Step 3: Read existing custom list to verify existence
        ret_val, existing_data = self.__read_custom_list(custom_list_id)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 4: Build update payload
        payload = self.__build_update_payload(existing_data)

        # Step 5: Make API call to update custom list
        ret_val, response = self.__make_update_api_call(custom_list_id, payload)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 6: Validate response structure
        ret_val = self.__validate_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 7: Handle response and update action result
        ret_val = self.__handle_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.ACTION_UPDATE_NAMED_LIST_SUCCESS_RESPONSE)
