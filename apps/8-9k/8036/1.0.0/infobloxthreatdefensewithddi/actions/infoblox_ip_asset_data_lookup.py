# File: infoblox_ip_asset_data_lookup.py
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


class IpAssetDataLookup(BaseAction):
    """Class to handle IP asset data lookup action."""

    def _validate_params(self):
        """
        Validate all action parameters comprehensively.

        Returns:
            int: phantom.APP_SUCCESS if all validations pass, phantom.APP_ERROR otherwise
        """
        # Validate string parameters
        string_params = [
            "ip_filter",
            "scope",
            "tag_filter",
            "order_by",
        ]

        for param in string_params:
            value = self._param.get(param)
            if value is not None and not isinstance(value, str):
                return self._action_result.set_status(phantom.APP_ERROR, f"Parameter '{param}' must be a string")

        # Validate integer parameters with specific rules
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

        # offset parameter: allow zero, validate non-negative (UI parameter name: offset, API parameter name: _offset)
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

        return phantom.APP_SUCCESS

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("IP Asset Data Lookup"))

    def __make_api_call(self):
        """
        Build query parameters from action parameters with intelligent handling.
        Maps UI-friendly parameter names to API parameter names.

        Returns:
            dict: Dictionary of query parameters for the API call
        """

        params = {}

        # Handle precedence: limit parameter
        limit = self._param.get("limit")
        if limit is not None:
            params["_limit"] = limit
        else:
            params["_limit"] = consts.DEFAULT_LIMIT

        # Handle offset parameter (UI parameter: offset, API parameter: _offset)
        offset = self._param.get("offset")
        if offset is not None:
            params["_offset"] = offset

        # Handle address_state parameter (UI parameter: address_state, API parameter: address_state)
        address_state = self._param.get("address_state")
        if address_state:
            params["address_state"] = address_state.lower()

        # Add scope as separate parameter (not in _filter)
        scope = self._param.get("scope")
        if scope:
            params["scope"] = scope

        # Build combined filter using AND operator
        filter_parts = []

        # Add ip_filter if provided (UI parameter: ip_filter, API parameter: _filter)
        ip_filter = self._param.get("ip_filter")
        if ip_filter:
            filter_parts.append(f"({ip_filter})")

        # Combine all filters with AND
        if filter_parts:
            params["_filter"] = " and ".join(filter_parts)

        # Handle tag filters separately using _tfilter parameter (UI parameter: tag_filter, API parameter: _tfilter)
        tag_filter = self._param.get("tag_filter")
        if tag_filter:
            params["_tfilter"] = f"({tag_filter})"

        # Add order_by parameter if provided (for sorting results)
        order_by = self._param.get("order_by")
        if order_by:
            params["_order_by"] = order_by

        return self._connector.util.make_rest_call(
            endpoint=consts.IPAM_ADDRESS_ENDPOINT,
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

        self._connector.debug_print(f"Processing {total_count} IP asset records")

        # Process only the usage field to convert arrays to strings for better table display
        # while preserving the original response structure
        for result in results:
            usage = result.get("usage", [])
            if isinstance(usage, list):
                # Convert list to comma-separated string for table display
                result["usage"] = ", ".join(str(u) for u in usage) if usage else ""
            elif usage is not None:
                # Ensure it's a string if it's not None
                result["usage"] = str(usage)
            else:
                # Handle None case
                result["usage"] = ""

        # Preserve the original response structure with enhanced usage field
        self._action_result.add_data(response)

        # Generate comprehensive summary with total count and applied filters information
        applied_filters = []
        if self._param.get("ip_filter"):
            applied_filters.append(f"IP Filter: {self._param.get('ip_filter')}")
        if self._param.get("address_state") and self._param.get("address_state") != "Any":
            applied_filters.append(f"Address State: {self._param.get('address_state')}")
        if self._param.get("scope"):
            applied_filters.append(f"Scope: {self._param.get('scope')}")
        if self._param.get("tag_filter"):
            applied_filters.append(f"Tag Filter: {self._param.get('tag_filter')}")
        if self._param.get("order_by"):
            applied_filters.append(f"Order By: {self._param.get('order_by')}")

        summary = {
            "total_addresses": total_count,
            "filters_applied": "; ".join(applied_filters) if applied_filters else "None",
        }

        self._action_result.update_summary(summary)
        message = consts.ACTION_IP_ASSET_DATA_LOOKUP_SUCCESS_RESPONSE.format(total_count)
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
        Execute IP asset data lookup action following the 6-step modular approach.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Build query parameters and Make REST call to get IP asset data
        Step 4: Validate and process response
        Step 5: Return results
        """

        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters
        ret_val = self._validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 3: Build query parameters and Make REST call to get IP asset data
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            # Check for filter syntax errors in response
            error_message = self._action_result.get_message() or ""
            filter_error_check = self._connector.util.check_filter_error_in_response(self._action_result, error_message, "ip_filter")
            if phantom.is_fail(filter_error_check):
                return filter_error_check
            return ret_val

        # Step 4: Validate and process response
        ret_val = self.__validate_and_process_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 5: Return results
        return phantom.APP_SUCCESS
