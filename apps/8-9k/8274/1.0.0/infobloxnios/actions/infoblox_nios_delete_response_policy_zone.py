# File: infoblox_nios_delete_response_policy_zone.py
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


class DeleteResponsePolicyZoneAction(BaseAction):
    """Delete Response Policy Zone action."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.DELETE_RPZ_START_MESSAGE)
        reference_id = self._param.get("reference_id", "")
        self._connector.save_progress(consts.DELETE_RPZ_PROGRESS_MESSAGE.format(reference_id=reference_id))

    def __make_api_call(self):
        """Make the REST API call to delete response policy zone.

        :return: tuple: (status, response) - Status code and API response
        """
        reference_id = self._param["reference_id"]

        # Make DELETE API call
        return self._connector.utils.make_rest_call(
            consts.DELETE_RPZ_ENDPOINT.format(reference_id=reference_id), self._action_result, method="delete"
        )

    def __handle_response(self, response):
        """Handle the API response for delete operation.

        :param response: The API response
        :return: status (success/failure)
        """
        self._action_result.add_data({"reference_id": response})

        # Add summary metrics
        summary = self._action_result.update_summary({})
        summary["total_objects"] = 1
        summary["total_objects_successful"] = 1

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.DELETE_RPZ_SUCCESS_MESSAGE.format(reference_id=response))

    def execute(self):
        """Execute the delete response policy zone action.

        Step 1: Log action start
        Step 2: Make API call to delete response policy zone
        Step 3: Handle the response

        :return: status (success/failure)
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Make API call to delete response policy zone
        status, response = self.__make_api_call()

        if phantom.is_fail(status):
            error_message = self._action_result.get_message() or consts.ERROR_DELETE_RPZ
            self._connector.save_progress(error_message)
            return self._action_result.set_status(phantom.APP_ERROR, error_message)

        # Step 3: Handle the response
        return self.__handle_response(response)
