# File: infoblox_dns_record_lookup.py
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


class DnsRecordLookup(BaseAction):
    """Class to handle DNS record lookup action.

    This action allows filtering and retrieving DNS records by specific criteria
    such as DNS record filters, tag filters, with pagination support.
    """

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("DNS Record Lookup"))

    def _validate_params(self):
        """
        Validate action parameters for format/content.
        Note: Required parameter validation is handled by SOAR's built-in JSON schema validation.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        # Validate offset parameter
        offset = self._param.get("offset")
        if offset is not None:
            ret_val, offset = self._connector.validator.validate_integer(
                self._action_result, offset, "offset", allow_zero=True, allow_negative=False
            )
            if phantom.is_fail(ret_val):
                return ret_val

        # Validate limit parameter
        limit = self._param.get("limit")
        if limit is not None:
            ret_val, limit = self._connector.validator.validate_integer(
                self._action_result, limit, "limit", allow_zero=False, allow_negative=False
            )
            if phantom.is_fail(ret_val):
                return ret_val

            # Check limit range
            if limit > consts.MAX_LIMIT:
                return self._action_result.set_status(phantom.APP_ERROR, "Limit parameter must be less than or equal to 1000")

        return phantom.APP_SUCCESS

    def __make_api_call(self):
        """
        Make the API call to retrieve DNS records.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        # Build query parameters with proper UI to API parameter mapping
        params = {}

        # Map UI parameters to API parameters
        dns_record_filter = self._param.get("dns_record_filter")
        if dns_record_filter:
            params["_filter"] = dns_record_filter

        tag_filter = self._param.get("tag_filter")
        if tag_filter:
            params["_tfilter"] = tag_filter

        offset = self._param.get("offset", 0)
        params["_offset"] = offset

        limit = self._param.get("limit", 100)
        params["_limit"] = limit

        # Add order_by parameter if provided (for sorting results)
        order_by = self._param.get("order_by")
        if order_by:
            params["_order_by"] = order_by

        # Make the GET API call
        endpoint = consts.DNS_RECORD_ENDPOINT
        self._connector.debug_print(f"Making GET request to {endpoint}")
        self._connector.debug_print(f"Query parameters: {params}")

        return self._connector.util.make_rest_call(endpoint=endpoint, action_result=self._action_result, method="get", params=params)

    def __handle_response(self, response):
        """
        Handle the API response and process the DNS records data.
        Uses .get() method for safe dictionary access to avoid KeyError exceptions.

        Args:
            response (dict): The API response containing results

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        # Validate response structure using .get() for safe access
        if not isinstance(response, dict):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: expected JSON object")

        # Check for results array
        results = response.get("results")
        if results is None:
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: missing 'results' field")

        self._connector.debug_print("Processing DNS records response")

        # Store complete API response
        self._action_result.add_data(response)

        # Extract information for summary using safe dictionary access
        total_records = len(results)

        # Extract applied filters for summary
        dns_record_filter = self._param.get("dns_record_filter", "")
        tag_filter = self._param.get("tag_filter", "")
        offset = self._param.get("offset", 0)
        limit = self._param.get("limit", 100)

        # Generate comprehensive summary
        summary = {
            "total_records": total_records,
            "offset": offset,
            "limit": limit,
            "dns_record_filter_applied": bool(dns_record_filter),
            "tag_filter_applied": bool(tag_filter),
        }

        self._action_result.update_summary(summary)

        # Generate dynamic success message based on the number of records retrieved
        success_message = consts.ACTION_DNS_RECORD_LOOKUP_SUCCESS_RESPONSE.format(count=total_records)

        return self._action_result.set_status(phantom.APP_SUCCESS, success_message)

    def execute(self):
        """
        Execute DNS record lookup action following the modular approach.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make API call
        Step 4: Handle response
        Step 5: Return results

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

        # Step 3: Make API call
        self._connector.save_progress("Retrieving DNS records")
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 4: Handle response
        ret_val = self.__handle_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 5: Return results
        self._connector.save_progress("DNS records retrieved successfully")
        return phantom.APP_SUCCESS
