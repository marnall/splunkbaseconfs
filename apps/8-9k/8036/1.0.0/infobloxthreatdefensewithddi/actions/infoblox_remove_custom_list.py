# File: infoblox_remove_custom_list.py
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


class RemoveCustomList(BaseAction):
    """Class to handle remove custom list action.

    This action permanently removes a custom list from Infoblox BloxOne by its ID.
    """

    def _validate_params(self):
        """Validate the parameters for remove custom list action.

        Verifies that the required custom list ID parameter is present and is a valid integer.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """

        # Validate id parameter - must be present and a valid integer
        custom_list_id = self._param["id"]

        # Use the validator utility to validate that id is an integer
        ret_val, custom_list_id = self._connector.validator.validate_integer(
            self._action_result,
            custom_list_id,
            "id",
            allow_zero=False,
            allow_negative=False,
        )

        if phantom.is_fail(ret_val):
            return ret_val

        return phantom.APP_SUCCESS

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Remove custom list"))

    def __make_delete_api_call(self, list_id):
        """Make the REST API call to delete the custom list.

        Args:
            list_id (str): The ID of the custom list to delete

        Returns:
            tuple: (status, response) - Status code and API response
        """
        endpoint = f"{consts.NAMED_LIST_ENDPOINT}/{list_id}"
        self._connector.debug_print(f"Making DELETE request to endpoint: {endpoint}")
        self._connector.save_progress(f"Sending request to remove custom list {list_id}")

        return self._connector.util.make_rest_call(endpoint=endpoint, action_result=self._action_result, method="delete")

    def __handle_response(self, list_id):
        """Handle successful deletion and update action result.

        Args:
            list_id (str): The ID of the custom list that was deleted

        Returns:
            int: phantom.APP_SUCCESS on successful processing
        """

        # Add empty data to action result if not already added
        if not self._action_result.get_data():
            self._action_result.add_data({})

        # Create summary
        summary = {"list_id": list_id, "status": "deleted"}
        self._action_result.update_summary(summary)

        success_message = consts.ACTION_REMOVE_NAMED_LIST_SUCCESS.format(list_id)
        self._connector.save_progress(success_message)

        return self._action_result.set_status(phantom.APP_SUCCESS, success_message)

    def execute(self):
        """Execute remove custom list action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make API call to delete custom list
        Step 4: Handle response and return results
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters
        self._connector.save_progress("Validating parameters")
        ret_val = self._validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        # Get the custom list ID
        list_id = self._param["id"]

        # Step 3: Make API call to delete custom list
        self._connector.save_progress(f"Deleting custom list with ID: {list_id}")
        ret_val, response = self.__make_delete_api_call(list_id)

        if phantom.is_fail(ret_val):
            self._connector.debug_print(f"API call failed with status: {self._action_result.get_status()}. Response: {response}")
            self._connector.save_progress("Failed to delete custom list")
            return ret_val

        # Step 4: Handle response and return results
        return self.__handle_response(list_id)
