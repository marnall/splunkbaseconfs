# File: infoblox_nios_delete_rpz_rule.py
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

import infoblox_nios_consts as consts
from actions import BaseAction


class DeleteRPZRuleAction(BaseAction):
    """Delete RPZ Rule action."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.DELETE_RPZ_RULE_START_MESSAGE)
        ref = self._param.get("ref", "")
        self._connector.save_progress(consts.DELETE_RPZ_RULE_PROGRESS_MESSAGE.format(ref=ref))

    def __make_api_call(self, reference_id):
        """Make the REST API call to delete the RPZ rule.

        :return: tuple: (status, response) - Status code and API response
        """
        # Make the DELETE request to remove the RPZ rule
        return self._connector.utils.make_rest_call(f"/{reference_id}", self._action_result, method="delete")

    def __handle_response(self, response):
        """Handle the API response for delete RPZ rule.

        :param response: The API response
        :return: status (success/failure)
        """
        # Add the response data to the action result
        if response:
            self._action_result.add_data({"reference_id": response})

        # Set summary
        summary = self._action_result.update_summary({})
        summary["total_objects"] = 1
        summary["total_objects_successful"] = 1

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.DELETE_RPZ_RULE_SUCCESS_MESSAGE.format(reference_id=self._ref))

    def execute(self):
        """Execute the delete RPZ rule action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make API call to delete the RPZ rule
        Step 4: Handle the response

        :return: status (success/failure)
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: get parameter
        reference_id = self._param["ref"]
        # Store the reference ID as an instance attribute
        self._ref = reference_id

        # Step 3: Make API call to delete the RPZ rule
        status, response = self.__make_api_call(reference_id)

        if phantom.is_fail(status):
            error_message = self._action_result.get_message() or consts.ERROR_DELETE_RPZ_RULE
            self._connector.save_progress(error_message)
            return self._action_result.set_status(phantom.APP_ERROR, error_message)

        # Step 4: Handle the response
        return self.__handle_response(response)
