# File: infoblox_nios_search_rpz_rule.py
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


class SearchRPZRuleAction(BaseAction):
    """Search RPZ Rule action."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.SEARCH_RPZ_RULE_START_MESSAGE)
        rule_name = self._param.get("rule_name", "")
        if rule_name:
            self._connector.save_progress(consts.SEARCH_RPZ_RULE_PROGRESS_MESSAGE.format(name=rule_name))
        else:
            self._connector.save_progress("Searching for RPZ Rules")

    def __validate_params(self):
        """Validate the parameters for the action.

        Checks that parameters are of the correct type and format.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        limit = self._param.get("limit")
        if limit is not None:
            ret_val, limit = self._connector.validator.validate_integer(
                self._action_result,
                limit,
                "limit",
                allow_zero=False,
                allow_negative=False,
            )

            if phantom.is_fail(ret_val):
                return ret_val

        return phantom.APP_SUCCESS

    def __prepare_params(self):
        """Prepare the query parameters for searching RPZ rules.

        :return: dict: Query parameters for the API request, str: object_type
        """
        # Get the object type from parameters
        object_type = self._param["object_type"]

        # Initialize params
        params = {}

        # Add output fields if provided - use exactly what the user specified
        output_fields = self._param.get("output_fields")
        if output_fields:
            params["_return_fields"] = output_fields

        # Add rule name if provided
        if self._param.get("rule_name"):
            params["name"] = self._param.get("rule_name")

        return params, object_type

    def __handle_response(self, response):
        """Handle the API response for search operation.

        :param response: The API response
        :return: status (success/failure)
        """
        # Check if response is empty
        if not isinstance(response, list):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: expected JSON array")

        # Add each rule to the action result
        for rule in response:
            # Create a modified copy of the rule with _ref renamed to ref
            modified_rule = {}
            for key, value in rule.items():
                if key == "_ref":
                    modified_rule["ref"] = value
                else:
                    modified_rule[key] = value

            self._action_result.add_data(modified_rule)

        # Add summary metrics
        summary = self._action_result.update_summary({})
        summary["total_rules_found"] = len(response)

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.SEARCH_RPZ_RULE_SUCCESS_MESSAGE.format(count=len(response)))

    def execute(self):
        """Execute the search RPZ rule action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Prepare query parameters
        Step 4: Use make_paginated_rest_call to fetch RPZ rules
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
        params, object_type = self.__prepare_params()

        # Construct the endpoint using the object_type
        endpoint = f"/{object_type}"

        # Step 4: Use make_paginated_rest_call to fetch RPZ rules with pagination
        limit = self._param.get("limit", consts.DEFAULT_MAX_RESULTS)
        ret_val, response = self._connector.utils.make_paginated_rest_call(
            endpoint=endpoint, action_result=self._action_result, params=params, method="get", limit=limit
        )

        if phantom.is_fail(ret_val):
            error_message = self._action_result.get_message() or consts.SEARCH_RPZ_RULE_ERROR_MESSAGE
            self._connector.save_progress(error_message)
            return ret_val

        # Step 5: Handle the response
        return self.__handle_response(response)
