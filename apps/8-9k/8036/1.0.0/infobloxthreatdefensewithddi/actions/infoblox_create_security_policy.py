# File: infoblox_create_security_policy.py
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


class CreateSecurityPolicy(BaseAction):
    """Class to handle create security policy action.

    This action creates a new Security Policy in Infoblox Cloud using the Advanced Threat
    Control and Firewall (ATCFW) API, including its name, rules, network lists, and configuration.
    """

    def _validate_params(self):
        """
        Validate all action parameters comprehensively.

        Returns:
            int: phantom.APP_SUCCESS if all validations pass, phantom.APP_ERROR otherwise
        """

        # Validate JSON parameters
        json_params = ["rules", "tags", "additional_parameters"]
        for param in json_params:
            value = self._param.get(param)
            if value:
                if value.lower() == "empty":
                    continue  # Allow "empty" keyword for clearing fields
                try:
                    json.loads(value)
                except json.JSONDecodeError as e:
                    return self._action_result.set_status(phantom.APP_ERROR, f"Parameter '{param}' must be valid JSON: {e!s}")

        # Validate comma-separated list parameters
        list_params = ["network_lists", "dfps", "roaming_device_groups"]
        for param in list_params:
            value = self._param.get(param)
            if value:
                try:
                    # Split by comma and validate each item as integer
                    items = [item.strip() for item in value.split(",")]
                    for item in items:
                        if not item.isdigit():
                            return self._action_result.set_status(
                                phantom.APP_ERROR, f"Parameter '{param}' must contain comma-separated integer values"
                            )
                except Exception as e:
                    return self._action_result.set_status(phantom.APP_ERROR, f"Parameter '{param}' format error: {e!s}")

        # Validate boolean string parameters
        boolean_params = ["block_dns_rebind_attack", "safe_search"]
        for param in boolean_params:
            value = self._param.get(param)
            if value and value.lower() not in ["true", "false"]:
                return self._action_result.set_status(phantom.APP_ERROR, f"Parameter '{param}' must be 'true' or 'false'")

        return phantom.APP_SUCCESS

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Create Security Policy"))

    def __build_payload_and_create_policy(self):
        """
        Build the request payload from action parameters and make the API call.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        payload = {}

        # Required parameter
        payload["name"] = self._param["name"]

        # Optional description
        description = self._param.get("description")
        if description:
            payload["description"] = description

        # Handle boolean parameters
        block_dns_rebind = self._param.get("block_dns_rebind_attack")
        if block_dns_rebind:
            payload["block_dns_rebind_attack"] = block_dns_rebind.lower() == "true"

        safe_search = self._param.get("safe_search")
        if safe_search:
            payload["safe_search"] = safe_search.lower() == "true"

        # Handle list parameters (comma-separated integers)
        list_params = {
            "network_lists": "network_lists",
            "dfps": "dfps",
            "roaming_device_groups": "roaming_device_groups",
        }

        for param_name, payload_key in list_params.items():
            value = self._param.get(param_name)
            if value:
                # Convert comma-separated string to list of integers
                items = [int(item.strip()) for item in value.split(",")]
                payload[payload_key] = items

        # Handle JSON parameters
        rules = self._param.get("rules")
        if rules and rules.lower() == "empty":
            try:
                payload["rules"] = json.loads(rules)
            except json.JSONDecodeError:
                pass  # Already validated in _validate_params

        tags = self._param.get("tags")
        if tags:
            if tags.lower() == "empty":
                payload["tags"] = {}
            else:
                try:
                    payload["tags"] = json.loads(tags)
                except json.JSONDecodeError:
                    pass  # Already validated in _validate_params

        # Handle additional parameters JSON
        additional_params = self._param.get("additional_parameters")
        if additional_params and additional_params.lower() != "empty":
            try:
                additional_data = json.loads(additional_params)
                # Merge additional parameters into payload
                payload.update(additional_data)
            except json.JSONDecodeError:
                pass  # Already validated in _validate_params

        # Make the API call
        self._connector.debug_print(f"Making POST request to {consts.SECURITY_POLICY_ENDPOINT}")
        self._connector.debug_print(f"Request payload: {payload}")

        return self._connector.util.make_rest_call(
            endpoint=consts.SECURITY_POLICY_ENDPOINT,
            action_result=self._action_result,
            method="post",
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

        if "results" not in response:
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: missing 'results' field")

        if not isinstance(response["results"], dict):
            return self._action_result.set_status(
                phantom.APP_ERROR,
                "Invalid response format: 'results' field must be an object",
            )

        return phantom.APP_SUCCESS

    def __handle_response(self, response):
        """
        Handle the API response and process created security policy data.

        Args:
            response (dict): The API response containing results

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        # Validate response basic structure
        ret_val = self.__validate_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        results = response.get("results", {})

        self._connector.debug_print("Processing created security policy data")

        # Store complete API response
        self._action_result.add_data(response)

        # Extract key information for summary
        policy_id = results.get("id", "")
        policy_name = results.get("name", "")
        description = results.get("description", "")
        default_action = results.get("default_action", "")

        # Generate comprehensive summary
        summary = {
            "security_policy_id": policy_id,
            "policy_name": policy_name,
            "description": description,
            "default_action": default_action,
            "created_successfully": True,
        }

        self._action_result.update_summary(summary)

        success_message = consts.ACTION_CREATE_SECURITY_POLICY_SUCCESS_RESPONSE.format(policy_name, policy_id)
        return self._action_result.set_status(phantom.APP_SUCCESS, success_message)

    def __validate_and_process_response(self, response):
        """
        Validate and process the API response.

        Args:
            response (dict): The API response containing results

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        # Validate response basic structure
        ret_val = self.__validate_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Process response data
        return self.__handle_response(response)

    def execute(self):
        """
        Execute create security policy action following the 6-step modular approach.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Build request payload and create policy
        Step 4: Validate and process response
        Step 5: Return results

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

        # Step 3: Build request payload and create policy
        try:
            ret_val, response = self.__build_payload_and_create_policy()
        except Exception as e:
            self._connector.debug_print(f"Error building request payload and creating policy: {e!s}")
            return self._action_result.set_status(phantom.APP_ERROR, f"Error building request payload and creating policy: {e!s}")

        if phantom.is_fail(ret_val):
            # Check for duplicate name error
            error_message = self._action_result.get_message() or ""
            if "unique" in error_message.lower() or "duplicate" in error_message.lower():
                return self._action_result.set_status(
                    phantom.APP_ERROR,
                    f"Security Policy name '{self._param.get('name', '')}' must be unique within the account",
                )
            return ret_val

        # Step 4: Validate and process response
        ret_val = self.__validate_and_process_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 5: Return results
        self._connector.save_progress("Security policy created successfully")
        return phantom.APP_SUCCESS
