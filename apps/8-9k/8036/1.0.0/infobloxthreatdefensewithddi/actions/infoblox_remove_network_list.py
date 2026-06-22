# File: infoblox_remove_network_list.py
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


class RemoveNetworkList(BaseAction):
    """Action to remove a network list by ID."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Remove Network List"))

    def __make_api_call(self):
        """
        Make the REST API call to remove the network list.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        network_list_id = self._param["network_list_id"]
        endpoint = consts.NETWORK_LIST_DETAIL_ENDPOINT.format(network_list_id)

        # Make the DELETE call
        return self._connector.util.make_rest_call(endpoint=endpoint, action_result=self._action_result, method="delete")

    def __handle_response(self, response):
        """
        Handle the API response for the delete operation.

        Args:
            response: The API response from the delete call

        Returns:
            int: phantom.APP_SUCCESS on successful delete, phantom.APP_ERROR otherwise
        """
        # For DELETE operations, a 204 No Content is often returned as success
        # The response might be None in case of 204 No Content

        # Add summary information
        summary = {"network_list_id": self._param.get("network_list_id")}
        self._action_result.update_summary(summary)

        # Set success message
        self._action_result.set_status(phantom.APP_SUCCESS, consts.REMOVE_NETWORK_LIST_SUCCESS_MSG.format(self._param.get("network_list_id")))

        return phantom.APP_SUCCESS

    def execute(self):
        """
        Execute the remove network list action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make API call to delete network list
        Step 4: Handle the response
        """
        # Log action start
        self.__log_action_start()

        # Make API call
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            # Special error handling for specific cases
            if hasattr(ret_val, "get_message"):
                error_msg = ret_val.get_message()
                if "404" in error_msg:
                    return self._action_result.set_status(phantom.APP_ERROR, "Network List does not exist.")
                elif "409" in error_msg or "cannot be deleted" in error_msg.lower():
                    return self._action_result.set_status(
                        phantom.APP_ERROR, "Network list cannot be deleted as it is assigned to a security policy."
                    )
            return ret_val

        # Handle response using dedicated method
        return self.__handle_response(response)
