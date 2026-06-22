#!/usr/bin/env python3
# File: infoblox_create_custom_list.py
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


class CreateCustomList(BaseAction):
    """Action class for creating custom lists in Infoblox Cloud."""

    def _validate_params(self):
        """Validate and process input parameters.

        Returns:
            int: phantom.APP_SUCCESS on successful validation, phantom.APP_ERROR otherwise
        """
        # Validate tags parameter (if provided)
        tags = self._param.get("tags", "").strip()
        if tags:
            try:
                json.loads(tags)
            except json.JSONDecodeError as e:
                return self._action_result.set_status(
                    phantom.APP_ERROR,
                    f"Invalid JSON format for tags parameter: {e!s}",
                )

        return phantom.APP_SUCCESS

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("create custom list"))

    def __build_request_payload(self):
        """Build the request payload for creating custom list.

        Returns:
            dict: Request payload for the API call
        """
        payload = {
            "name": self._param.get("name", "").strip(),
            "type": self._param.get("type", "custom_list").strip(),
            "confidence_level": self._param.get("confidence_level", "HIGH"),
            "threat_level": self._param.get("threat_level", "LOW"),
        }

        # Add description if provided
        description = self._param.get("description", "").strip()
        if description:
            payload["description"] = description

        # Add tags if provided
        tags = self._param.get("tags", "").strip()
        if tags:
            try:
                payload["tags"] = json.loads(tags)
            except json.JSONDecodeError:
                payload["tags"] = {}
        else:
            payload["tags"] = {}

        # Add items if provided
        items = self._param.get("items", "").strip()
        if items:
            # Process items list
            item_list = []
            for item in items.split(","):
                item = item.strip()
                # Remove surrounding quotes if present
                if (item.startswith('"') and item.endswith('"')) or (item.startswith("'") and item.endswith("'")):
                    item = item[1:-1]
                if item:  # Only add non-empty items
                    item_list.append(item)

            # Use 'items' key instead of 'items_described'
            payload["items"] = item_list
        else:
            # Empty array for items
            payload["items"] = []
        return payload

    def __make_api_call(self, payload):
        """Make the REST API call to create custom list.

        Args:
            payload (dict): Request payload

        Returns:
            int: phantom.APP_SUCCESS on successful API call, phantom.APP_ERROR otherwise
        """
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        self._connector.debug_print(f"Creating custom list with payload: {json.dumps(payload, indent=2)}")

        # Make the API call
        ret_val, response = self._connector.util.make_rest_call(
            consts.NAMED_LIST_ENDPOINT,
            self._action_result,
            method="post",
            headers=headers,
            data=payload,
        )

        if phantom.is_fail(ret_val):
            # Check for specific error messages
            error_message = self._action_result.get_message() or "Unknown error occurred"

            # Handle "already exists" error
            if "already exists" in error_message.lower() or "duplicate name" in error_message.lower():
                return self._action_result.set_status(
                    phantom.APP_ERROR,
                    f"List already exists: A custom list with the name '{self._param.get('name')}' already exists",
                )

            return ret_val

        self._response = response
        return phantom.APP_SUCCESS

    def __validate_response(self, response):
        """Validate the API response structure.

        Args:
            response (dict): The API response

        Returns:
            int: phantom.APP_SUCCESS on valid response, phantom.APP_ERROR otherwise
        """
        if not isinstance(response, dict):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: Expected JSON object")

        if "results" not in response:
            return self._action_result.set_status(phantom.APP_ERROR, "Response missing 'results' field")

        results = response.get("results", {})
        if not isinstance(results, dict):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid results format: Expected JSON object")

        # Check for required fields in results
        required_fields = ["id", "name", "type"]
        for field in required_fields:
            if field not in results:
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
            results = response.get("results", {})

            self._connector.debug_print(f"Processing custom list creation response: {json.dumps(results, indent=2)}")

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
            error_msg = f"Error processing custom list creation response: {e!s}"
            self._connector.debug_print(error_msg)
            return self._action_result.set_status(phantom.APP_ERROR, error_msg)

    def execute(self):
        """Execute create custom list action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Build request payload
        Step 4: Make REST call to create custom list
        Step 5: Validate and process response
        Step 6: Return results

        Returns:
            int: phantom.APP_SUCCESS on successful execution, phantom.APP_ERROR otherwise
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters
        if phantom.is_fail(self._validate_params()):
            return self._action_result.get_status()

        # Step 3: Build request payload
        try:
            payload = self.__build_request_payload()
        except Exception as e:
            error_msg = f"Error building request payload: {e!s}"
            self._connector.debug_print(error_msg)
            return self._action_result.set_status(phantom.APP_ERROR, error_msg)

        # Step 4: Make REST call to create custom list
        if phantom.is_fail(self.__make_api_call(payload)):
            return self._action_result.get_status()

        # Step 5: Validate and process response
        if phantom.is_fail(self.__validate_response(self._response)):
            return self._action_result.get_status()

        if phantom.is_fail(self.__handle_response(self._response)):
            return self._action_result.get_status()

        # Step 6: Return success
        return self._action_result.set_status(phantom.APP_SUCCESS, consts.ACTION_CREATE_NAMED_LIST_SUCCESS_RESPONSE)
