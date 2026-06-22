# File: infoblox_nios_get_response_policy_zone.py
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


class GetResponsePolicyZoneAction(BaseAction):
    """Get Response Policy Zone action."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.GET_RPZ_START_MESSAGE)
        fqdn = self._param.get("fqdn", "")
        if fqdn:
            self._connector.save_progress(consts.GET_RPZ_PROGRESS_MESSAGE.format(fqdn=fqdn))
        else:
            self._connector.save_progress("Getting Response Policy Zones")

    def __validate_params(self):
        """Validate the parameters for the action.

        Checks that parameters are of the correct type and format.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        max_results = self._param.get("max_results")
        if max_results is not None:
            ret_val, max_results = self._connector.validator.validate_integer(
                self._action_result,
                max_results,
                "max_results",
                allow_zero=False,
                allow_negative=False,
            )

            if phantom.is_fail(ret_val):
                return ret_val

        return phantom.APP_SUCCESS

    def __prepare_params(self):
        """Prepare the query parameters for getting response policy zones.

        :return: dict: Query parameters for the API request
        """
        # Initialize params with return fields
        params = {"_return_fields": consts.RPZ_RETURN_FIELDS}

        # Add optional filter parameters if provided
        if self._param.get("fqdn"):
            params["fqdn"] = self._param.get("fqdn")

        if self._param.get("view"):
            params["view"] = self._param.get("view")

        if self._param.get("comment"):
            params["comment"] = self._param.get("comment")

        return params

    def __handle_response(self, response):
        """Handle the API response for get operation.

        :param response: The API response
        :return: status (success/failure)
        """
        if not isinstance(response, list):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: expected JSON array")

        # Add each zone to the action result
        for zone in response:
            self._action_result.add_data(zone)

        # Add summary metrics
        summary = self._action_result.update_summary({})
        summary["total_zones_found"] = len(response)

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.GET_RPZ_SUCCESS_MESSAGE.format(count=len(response)))

    def execute(self):
        """Execute the get response policy zone action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Prepare query parameters
        Step 4: Use make_paginated_rest_call to fetch response policy zones
        Step 5: Handle the response

        :return: status (success/failure)
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters
        ret_val = self.__validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 3: Prepare query parameters
        params = self.__prepare_params()

        # Step 4: Use make_paginated_rest_call to fetch response policy zones with pagination
        max_results = self._param.get("max_results", consts.DEFAULT_MAX_RESULTS)
        ret_val, response = self._connector.utils.make_paginated_rest_call(
            endpoint=consts.RPZ_ENDPOINT, action_result=self._action_result, params=params, method="get", limit=max_results
        )

        if phantom.is_fail(ret_val):
            error_message = self._action_result.get_message() or consts.GET_RPZ_ERROR_MESSAGE
            self._connector.save_progress(error_message)
            return ret_val

        # Step 5: Handle the response
        return self.__handle_response(response)
