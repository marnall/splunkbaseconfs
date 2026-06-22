#!/usr/bin/env python3
# File: infoblox_update_security_policy.py
#
# Copyright 2025 Infoblox Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

import phantom.app as phantom

import infoblox_consts as consts
from actions import BaseAction


class UpdateSecurityPolicy(BaseAction):
    """Class to handle updating security policies.

    This action updates a specific Security Policy, including its name, rules,
    associated network lists, DNS Forwarding Proxies (DFPs), etc.
    """

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Update Security Policy"))

    def _validate_params(self):
        """
        Validate action parameters for format/content.
        Note: Required parameter validation is handled by SOAR's built-in JSON schema validation.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        # Validate security_policy_id parameter
        security_policy_id = self._param.get("security_policy_id")
        if security_policy_id is not None:
            ret_val, security_policy_id = self._connector.validator.validate_integer(
                self._action_result, security_policy_id, "security_policy_id", allow_zero=False, allow_negative=False
            )
            if phantom.is_fail(ret_val):
                return ret_val

        # Validate rules parameter if provided
        rules = self._param.get("rules")
        if rules:
            if rules.strip().lower() != "empty":
                try:
                    rules_parsed = json.loads(rules)
                    if not isinstance(rules_parsed, list):
                        return self._action_result.set_status(
                            phantom.APP_ERROR,
                            "Rules parameter must be a JSON array. Example: "
                            '[{"action": "action_block", "type": "custom_list", "data": "block_list_1", '
                            '"policy_name": "policy1", "redirect_name": "redirect1"}]',
                        )
                except json.JSONDecodeError as e:
                    return self._action_result.set_status(phantom.APP_ERROR, f"Rules parameter contains invalid JSON: {e!s}")

        # Validate network_lists parameter if provided
        network_lists = self._param.get("network_lists")
        if network_lists:
            if network_lists.strip().lower() != "empty":
                try:
                    network_list_ids = [int(x.strip()) for x in network_lists.split(",") if x.strip()]
                    for nid in network_list_ids:
                        if nid <= 0:
                            return self._action_result.set_status(
                                phantom.APP_ERROR,
                                "Network Lists parameter must contain positive integers. Example: '522436, 522438'",
                            )
                except ValueError:
                    return self._action_result.set_status(
                        phantom.APP_ERROR,
                        "Network Lists parameter must be comma-separated integers. Example: '522436, 522438'",
                    )

        # Validate dfps parameter if provided
        dfps = self._param.get("dfps")
        if dfps:
            if dfps.strip().lower() != "empty":
                try:
                    dfp_ids = [int(x.strip()) for x in dfps.split(",") if x.strip()]
                    for did in dfp_ids:
                        if did <= 0:
                            return self._action_result.set_status(
                                phantom.APP_ERROR,
                                "DFPS parameter must contain positive integers. Example: '12456, 12458'",
                            )
                except ValueError:
                    return self._action_result.set_status(
                        phantom.APP_ERROR, "DFPS parameter must be comma-separated integers. Example: '12456, 12458'"
                    )

        # Validate roaming_device_groups parameter if provided
        roaming_device_groups = self._param.get("roaming_device_groups")
        if roaming_device_groups:
            if roaming_device_groups.strip().lower() != "empty":
                try:
                    rdg_ids = [int(x.strip()) for x in roaming_device_groups.split(",") if x.strip()]
                    for rid in rdg_ids:
                        if rid <= 0:
                            return self._action_result.set_status(
                                phantom.APP_ERROR,
                                "Roaming Device Groups parameter must contain positive integers. Example: '56312, 56316'",
                            )
                except ValueError:
                    return self._action_result.set_status(
                        phantom.APP_ERROR,
                        "Roaming Device Groups parameter must be comma-separated integers. Example: '56312, 56316'",
                    )

        # Validate block_dns_rebind_attack parameter if provided
        block_dns_rebind_attack = self._param.get("block_dns_rebind_attack")
        if block_dns_rebind_attack:
            if block_dns_rebind_attack.lower() not in ["true", "false"]:
                return self._action_result.set_status(phantom.APP_ERROR, "Block DNS Rebinding parameter must be 'true' or 'false'")

        # Validate safe_search parameter if provided
        safe_search = self._param.get("safe_search")
        if safe_search:
            if safe_search.lower() not in ["true", "false"]:
                return self._action_result.set_status(phantom.APP_ERROR, "Safe Search parameter must be 'true' or 'false'")

        # Validate tags parameter if provided
        tags = self._param.get("tags")
        if tags:
            if tags.strip().lower() != "empty":
                try:
                    tags_parsed = json.loads(tags)
                    if not isinstance(tags_parsed, dict):
                        return self._action_result.set_status(
                            phantom.APP_ERROR,
                            'Tags parameter must be a JSON object. Example: \'{"category": "security", "priority": "high"}\'',
                        )
                except json.JSONDecodeError as e:
                    return self._action_result.set_status(phantom.APP_ERROR, f"Tags parameter contains invalid JSON: {e!s}")

        # Validate additional_parameters parameter if provided
        additional_parameters = self._param.get("additional_parameters")
        if additional_parameters:
            if additional_parameters.strip().lower() != "empty":
                try:
                    additional_parsed = json.loads(additional_parameters)
                    if not isinstance(additional_parsed, dict):
                        return self._action_result.set_status(
                            phantom.APP_ERROR,
                            'Additional Parameters must be a JSON object. Example: \'{"precedence": 10, "doh_enabled": true}\'',
                        )
                except json.JSONDecodeError as e:
                    return self._action_result.set_status(phantom.APP_ERROR, f"Additional Parameters contains invalid JSON: {e!s}")

        return phantom.APP_SUCCESS

    def __get_existing_policy(self, security_policy_id):
        """
        Get existing security policy data to use as base for updates.

        Args:
            security_policy_id (int): The ID of the security policy to retrieve

        Returns:
            tuple: (status, policy_data) - Status code and existing policy data
        """
        endpoint = f"{consts.SECURITY_POLICY_ENDPOINT}/{security_policy_id}"
        params = {"include_access_codes": "true"}

        self._connector.debug_print(f"Retrieving existing security policy with ID: {security_policy_id}")

        ret_val, response = self._connector.util.make_rest_call(
            endpoint=endpoint, action_result=self._action_result, method="get", params=params
        )

        if phantom.is_fail(ret_val):
            return ret_val, None

        # Extract the policy data from the response
        policy_data = response.get("results")
        if not policy_data:
            return (
                self._action_result.set_status(phantom.APP_ERROR, f"Security policy with ID {security_policy_id} not found"),
                None,
            )

        return phantom.APP_SUCCESS, policy_data

    def __build_update_payload(self, existing_policy):
        """
        Build the payload for updating security policy.

        Args:
            existing_policy (dict): The existing security policy data

        Returns:
            dict: The payload for the PUT request
        """
        # Start with existing policy data
        payload = existing_policy.copy()

        # Remove read-only fields that shouldn't be in the update payload
        read_only_fields = ["id", "created_time", "updated_time", "is_default", "migration_status"]
        for field in read_only_fields:
            payload.pop(field, None)

        # Update with provided parameters
        name = self._param.get("name")
        if name:
            payload["name"] = name

        description = self._param.get("description")
        if description is not None:
            if description.strip().lower() == "empty":
                payload["description"] = ""
            else:
                payload["description"] = description

        # Handle rules parameter
        rules = self._param.get("rules")
        if rules is not None:
            if rules.strip().lower() == "empty":
                payload["rules"] = []
            else:
                payload["rules"] = json.loads(rules)

        # Handle network_lists parameter
        network_lists = self._param.get("network_lists")
        if network_lists is not None:
            if network_lists.strip().lower() == "empty":
                payload["network_lists"] = []
            else:
                payload["network_lists"] = [int(x.strip()) for x in network_lists.split(",") if x.strip()]

        # Handle dfps parameter
        dfps = self._param.get("dfps")
        if dfps is not None:
            if dfps.strip().lower() == "empty":
                payload["dfps"] = []
            else:
                payload["dfps"] = [int(x.strip()) for x in dfps.split(",") if x.strip()]

        # Handle roaming_device_groups parameter
        roaming_device_groups = self._param.get("roaming_device_groups")
        if roaming_device_groups is not None:
            if roaming_device_groups.strip().lower() == "empty":
                payload["roaming_device_groups"] = []
            else:
                payload["roaming_device_groups"] = [int(x.strip()) for x in roaming_device_groups.split(",") if x.strip()]

        # Handle boolean parameters
        block_dns_rebind_attack = self._param.get("block_dns_rebind_attack")
        if block_dns_rebind_attack:
            payload["block_dns_rebind_attack"] = block_dns_rebind_attack.lower() == "true"

        safe_search = self._param.get("safe_search")
        if safe_search:
            payload["safe_search"] = safe_search.lower() == "true"

        # Handle tags parameter
        tags = self._param.get("tags")
        if tags is not None:
            if tags.strip().lower() == "empty":
                payload["tags"] = {}
            else:
                payload["tags"] = json.loads(tags)

        # Handle additional_parameters
        additional_parameters = self._param.get("additional_parameters")
        if additional_parameters is not None:
            if additional_parameters.strip().lower() != "empty":
                additional_data = json.loads(additional_parameters)
                # Merge additional parameters into payload
                payload.update(additional_data)

        return payload

    def __make_api_call(self, security_policy_id, payload):
        """
        Make the API call to update the security policy.

        Args:
            security_policy_id (int): The ID of the security policy to update
            payload (dict): The payload for the PUT request

        Returns:
            tuple: (status, response) - Status code and API response
        """
        endpoint = f"{consts.SECURITY_POLICY_ENDPOINT}/{security_policy_id}"

        self._connector.debug_print(f"Updating security policy with ID: {security_policy_id}")
        self._connector.debug_print(f"Update payload: {json.dumps(payload, indent=2)}")

        return self._connector.util.make_rest_call(endpoint=endpoint, action_result=self._action_result, method="put", data=payload)

    def __handle_response(self, response):
        """
        Handle the API response and process the updated security policy data.
        Uses .get() method for safe dictionary access to avoid KeyError exceptions.

        Args:
            response (dict): The API response containing results

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        # Validate response structure using .get() for safe access
        if not isinstance(response, dict):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: expected JSON object")

        # Check for results field
        results = response.get("results")
        if results is None:
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: missing 'results' field")

        self._connector.debug_print("Processing security policy update response")

        # Store complete API response
        self._action_result.add_data({"results": results})

        # Extract information for summary using safe dictionary access
        policy_id = results.get("id", "Unknown")
        policy_name = results.get("name", "Unknown")
        description = results.get("description", "")
        default_action = results.get("default_action", "Unknown")
        updated_time = results.get("updated_time", "")

        # Generate comprehensive summary
        summary = {
            "policy_id": policy_id,
            "name": policy_name,
            "description": description,
            "default_action": default_action,
            "updated_time": updated_time,
            "update_status": "Success",
        }

        self._action_result.update_summary(summary)

        # Generate success message
        success_message = consts.ACTION_UPDATE_SECURITY_POLICY_SUCCESS_RESPONSE.format(name=policy_name, id=policy_id)

        return self._action_result.set_status(phantom.APP_SUCCESS, success_message)

    def execute(self):
        """
        Execute update security policy action following the modular approach.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Get existing policy data
        Step 4: Build update payload
        Step 5: Make API call
        Step 6: Handle response

        Returns:
            int: phantom.APP_SUCCESS on successful execution, phantom.APP_ERROR otherwise
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters (format/content only, required validation handled by SOAR)
        self._connector.save_progress("Validating parameters")
        ret_val = self._validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 3: Get existing policy data
        security_policy_id = self._param.get("security_policy_id")
        self._connector.save_progress(f"Retrieving existing security policy with ID: {security_policy_id}")
        ret_val, existing_policy = self.__get_existing_policy(security_policy_id)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 4: Build update payload
        self._connector.save_progress("Building update payload")
        payload = self.__build_update_payload(existing_policy)

        # Step 5: Make API call
        self._connector.save_progress("Updating security policy")
        ret_val, response = self.__make_api_call(security_policy_id, payload)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 6: Handle response
        ret_val = self.__handle_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 7: Return results
        self._connector.save_progress("Security policy updated successfully")
        return phantom.APP_SUCCESS
