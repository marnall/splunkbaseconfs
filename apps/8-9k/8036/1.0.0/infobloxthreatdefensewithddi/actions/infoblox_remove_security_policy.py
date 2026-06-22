# File: infoblox_remove_security_policy.py
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


class RemoveSecurityPolicy(BaseAction):
    """Class to handle remove security policy action.

    This action permanently removes a security policy from Infoblox Cloud by its ID.
    """

    def _validate_params(self):
        """Validate the parameters for remove security policy action.

        Verifies that the required security policy ID parameter is present and is a valid integer.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """

        # Validate security_policy_id parameter - must be present and a valid integer
        security_policy_id = self._param["security_policy_id"]

        # Use the validator utility to validate that security_policy_id is an integer
        ret_val, security_policy_id = self._connector.validator.validate_integer(
            self._action_result,
            security_policy_id,
            "security_policy_id",
            allow_zero=False,
            allow_negative=False,
        )

        if phantom.is_fail(ret_val):
            return ret_val

        return phantom.APP_SUCCESS

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Remove security policy"))

    def __make_delete_api_call(self, security_policy_id):
        """Make the REST API call to delete the security policy.

        Args:
            security_policy_id (str): The ID of the security policy to delete

        Returns:
            tuple: (status, response) - Status code and API response
        """
        endpoint = f"{consts.SECURITY_POLICY_ENDPOINT}/{security_policy_id}"
        self._connector.debug_print(f"Making DELETE request to endpoint: {endpoint}")
        self._connector.save_progress(f"Sending request to remove security policy {security_policy_id}")

        ret_val, response = self._connector.util.make_rest_call(endpoint=endpoint, action_result=self._action_result, method="delete")

        if phantom.is_fail(ret_val):
            # Check for specific error cases
            error_message = self._action_result.get_message() or ""
            if "not found" in error_message.lower() or "404" in error_message or "existing security policy identifier" in error_message.lower():
                return self._action_result.set_status(phantom.APP_ERROR, "Security Policy does not exist."), None

        return ret_val, response

    def __handle_response(self, security_policy_id):
        """Handle successful deletion and update action result.

        Args:
            security_policy_id (str): The ID of the security policy that was deleted

        Returns:
            int: phantom.APP_SUCCESS on successful processing
        """

        # Add empty data to action result if not already added
        if not self._action_result.get_data():
            self._action_result.add_data({})

        # Create summary
        summary = {"security_policy_id": security_policy_id, "status_message": "Successfully deleted"}
        self._action_result.update_summary(summary)

        success_message = consts.ACTION_REMOVE_SECURITY_POLICY_SUCCESS_RESPONSE.format(security_policy_id)
        self._connector.save_progress(success_message)

        return self._action_result.set_status(phantom.APP_SUCCESS, success_message)

    def execute(self):
        """Execute remove security policy action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make API call to delete security policy
        Step 4: Handle response and return results

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

        # Get the security policy ID
        security_policy_id = self._param["security_policy_id"]

        # Step 3: Make API call to delete security policy
        self._connector.save_progress(f"Deleting security policy with ID: {security_policy_id}")
        ret_val, response = self.__make_delete_api_call(security_policy_id)

        if phantom.is_fail(ret_val):
            self._connector.debug_print(f"API call failed with status: {self._action_result.get_status()}. Response: {response}")
            self._connector.save_progress("Failed to delete security policy")
            return ret_val

        # Step 4: Handle response and return results
        self._connector.save_progress("Security policy deleted successfully")
        return self.__handle_response(security_policy_id)
