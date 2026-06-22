# File: infoblox_get_security_policy.py
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


class GetSecurityPolicy(BaseAction):
    """Class to handle get security policy action.

    This action retrieves Security Policies and their metadata from Infoblox Cloud
    using the Advanced Threat Control and Firewall (ATCFW) API.
    """

    def _validate_params(self):
        """
        Validate all action parameters comprehensively.

        Returns:
            int: phantom.APP_SUCCESS if all validations pass, phantom.APP_ERROR otherwise
        """

        # Validate string parameters
        string_params = [
            "security_policy_filter",
            "tag_filter",
            "tag_sort_filter",
        ]

        for param in string_params:
            value = self._param.get(param)
            if value is not None and not isinstance(value, str):
                return self._action_result.set_status(phantom.APP_ERROR, f"Parameter '{param}' must be a string")

        # limit parameter: 1-1000 range
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
            if limit > consts.MAX_LIMIT:
                return self._action_result.set_status(
                    phantom.APP_ERROR,
                    f"Parameter 'limit' must be between 1 and {consts.MAX_LIMIT}",
                )

        # offset parameter: allow zero, validate non-negative
        offset = self._param.get("offset")
        if offset is not None:
            ret_val, offset = self._connector.validator.validate_integer(
                self._action_result,
                offset,
                "offset",
                allow_zero=True,
                allow_negative=False,
            )
            if phantom.is_fail(ret_val):
                return ret_val

        # Validate tag filters for proper quote usage
        tag_filter = self._param.get("tag_filter")
        if tag_filter:
            ret_val = self._connector.validator.validate_filter_quotes(self._action_result, tag_filter, self._connector)
            if phantom.is_fail(ret_val):
                return ret_val

        tag_sort_filter = self._param.get("tag_sort_filter")
        if tag_sort_filter:
            ret_val = self._connector.validator.validate_filter_quotes(self._action_result, tag_sort_filter, self._connector)
            if phantom.is_fail(ret_val):
                return ret_val

        return phantom.APP_SUCCESS

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Get Security Policy"))

    def __build_query_params(self):
        """
        Build query parameters from action parameters with intelligent handling.
        Maps UI-friendly parameter names to API parameter names.

        Returns:
            dict: Dictionary of query parameters for the API call
        """
        params = {}

        # Handle limit parameter
        limit = self._param.get("limit")
        if limit is not None:
            params["_limit"] = limit
        else:
            params["_limit"] = consts.DEFAULT_LIMIT

        # Handle offset parameter
        offset = self._param.get("offset")
        if offset is not None:
            params["_offset"] = offset

        # Handle security policy filter (UI parameter: security_policy_filter, API parameter: _filter)
        security_policy_filter = self._param.get("security_policy_filter")
        if security_policy_filter:
            params["_filter"] = security_policy_filter

        # Handle tag filters separately using _tfilter parameter
        tag_filter = self._param.get("tag_filter")
        if tag_filter:
            params["_tfilter"] = tag_filter

        # Handle tag sort filter using _torder_by parameter
        tag_sort_filter = self._param.get("tag_sort_filter")
        if tag_sort_filter:
            params["_torder_by"] = tag_sort_filter

        # Always include access codes for complete data
        params["include_access_codes"] = "true"

        return params

    def __make_rest_call(self, params):
        """
        Make REST call to get security policies from Infoblox ATCFW.

        Args:
            params (dict): Query parameters for the API call

        Returns:
            tuple: (status, response) - Status code and API response
        """
        self._connector.debug_print(f"Making API call to {consts.SECURITY_POLICY_ENDPOINT}")
        self._connector.debug_print(f"Request params: {params}")

        return self._connector.util.make_rest_call(
            endpoint=consts.SECURITY_POLICY_ENDPOINT,
            action_result=self._action_result,
            method="get",
            params=params,
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

        if not isinstance(response["results"], list):
            return self._action_result.set_status(
                phantom.APP_ERROR,
                "Invalid response format: 'results' field must be an array",
            )

        return phantom.APP_SUCCESS

    def __handle_response(self, response):
        """
        Handle the API response with dual data structure approach.

        Args:
            response (dict): The API response containing results

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        # Validate response basic structure
        ret_val = self.__validate_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        results = response.get("results", [])
        total_count = len(results)

        self._connector.debug_print(f"Processing {total_count} security policy records")

        # Preserve complete nested response structure
        self._action_result.add_data(response)

        # Generate comprehensive summary with total count and applied filters information
        applied_filters = []
        if self._param.get("security_policy_filter"):
            applied_filters.append(f"Policy Filter: {self._param.get('security_policy_filter')}")
        if self._param.get("tag_filter"):
            applied_filters.append(f"Tag Filter: {self._param.get('tag_filter')}")
        if self._param.get("tag_sort_filter"):
            applied_filters.append(f"Tag Sort: {self._param.get('tag_sort_filter')}")

        summary = {
            "total_policies": total_count,
            "filters_applied": "; ".join(applied_filters) if applied_filters else "None",
        }

        self._action_result.update_summary(summary)

        # Dynamic message based on the number of policies retrieved
        message = consts.ACTION_GET_SECURITY_POLICY_SUCCESS_RESPONSE.format(count=total_count)

        return self._action_result.set_status(phantom.APP_SUCCESS, message)

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
        Execute get security policy action following the 6-step modular approach.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Build query parameters
        Step 4: Make REST call to get security policies
        Step 5: Validate and process response
        Step 6: Return results

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

        # Step 3: Build query parameters
        try:
            params = self.__build_query_params()
        except Exception as e:
            self._connector.debug_print(f"Error building query parameters: {e!s}")
            return self._action_result.set_status(phantom.APP_ERROR, f"Error building query parameters: {e!s}")

        # Step 4: Make REST call to get security policies
        self._connector.save_progress("Retrieving security policies")
        ret_val, response = self.__make_rest_call(params)
        if phantom.is_fail(ret_val):
            # Check for filter syntax errors in response
            error_message = self._action_result.get_message() or ""
            filter_error_check = self._connector.util.check_filter_error_in_response(
                self._action_result, error_message, "security_policy_filter"
            )
            if phantom.is_fail(filter_error_check):
                return filter_error_check
            return ret_val

        # Step 5: Validate and process response
        ret_val = self.__validate_and_process_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 6: Return results
        self._connector.save_progress("Security policies retrieved successfully")
        return phantom.APP_SUCCESS
