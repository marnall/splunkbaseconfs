# File: infoblox_indicator_threat_lookup.py
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

import urllib.parse

import phantom.app as phantom

import infoblox_consts as consts
from actions import BaseAction


class IndicatorThreatLookup(BaseAction):
    """Action to lookup threat intelligence for an indicator using Infoblox TIDE."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Indicator Threat Lookup"))

    def __validate_params(self):
        """
        Validate action parameters.

        Note: Required parameter validation is handled by SOAR's built-in JSON schema validation.
        We validate indicator value formats when specific indicator types are selected.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        # Validate indicator type and value
        indicator_type = self._param.get("indicator_type", "All").lower()
        indicator_value = self._param.get("indicator_value", "")

        # Validate indicator format based on type if an indicator value is provided
        if indicator_value:
            # Use the validator methods from utils
            ret_val, error_msg = self._connector.validator.validate_indicator_value(self._action_result, indicator_type, indicator_value)

            if phantom.is_fail(ret_val):
                # Set the error message and return error status
                return self._action_result.set_status(phantom.APP_ERROR, error_msg)

        # Validate limit parameter if provided
        limit = self._param.get("limit")
        if limit is not None:
            # Use the existing validation method for integers
            ret_val, limit = self._connector.validator.validate_integer(self._action_result, limit, "limit", allow_zero=False)
            if phantom.is_fail(ret_val):
                return phantom.APP_ERROR

            # Check if limit is within range
            if limit > consts.MAX_LIMIT:
                return self._action_result.set_status(
                    phantom.APP_ERROR,
                    consts.ERROR_INVALID_INT_RANGE.format(key="limit", min_value=1, max_value=consts.MAX_LIMIT),
                )

        # Validate expiration date format if provided
        expiration = self._param.get("expiration")
        if expiration:
            if not self._connector.validator.validate_datetime(expiration):
                return self._action_result.set_status(
                    phantom.APP_ERROR,
                    "Expiration has invalid datetime format. Please use ISO format (YYYY-MM-DDThh:mm:ss.sssZ) or "
                    "simple date format (YYYY-MM-DD).",
                )

        return phantom.APP_SUCCESS

    def __make_api_call(self):
        """
        Make the REST API call to lookup threat intelligence.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        # Prepare query parameters
        # Use user-specified limit if provided, otherwise use default
        limit = self._param.get("limit", consts.DEFAULT_LIMIT)
        params = {"data_format": "json", "rlimit": limit}

        self._connector.debug_print(f"Using result limit: {limit}")

        # Add indicator type parameter
        indicator_type = self._param.get("indicator_type", "All").lower()
        if indicator_type != "all":
            params["type"] = indicator_type

            # Add the indicator value under the appropriate parameter name
            indicator_value = self._param.get("indicator_value")
            if indicator_value:
                # If indicator type is URL, URL-encode the value
                if indicator_type == "url":
                    try:
                        indicator_value = urllib.parse.quote(indicator_value, safe="")
                    except Exception as e:
                        self._connector.debug_print(f"Error URL-encoding indicator value: {e!s}")
                        # Continue with the original value if encoding fails

                params[indicator_type] = indicator_value

        # Add optional parameters if provided
        optional_params = ["domain", "tld", "class", "target", "expiration"]
        for param in optional_params:
            if self._param.get(param):
                params[param] = self._param.get(param)

        # Make the GET call
        return self._connector.util.make_rest_call(
            endpoint=consts.TIDE_THREAT_ENDPOINT, action_result=self._action_result, method="get", params=params
        )

    def __handle_response(self, response):
        """
        Handle the API response for indicator threat lookup.

        Args:
            response (dict): The API response containing threat intelligence data

        Returns:
            int: phantom.APP_SUCCESS on successful retrieval, phantom.APP_ERROR otherwise
        """
        if not response:
            return self._action_result.set_status(
                phantom.APP_ERROR,
                consts.ACTION_INDICATOR_THREAT_LOOKUP_ERROR.format(error="Empty response from server"),
            )

        # Add the entire response as data
        self._action_result.add_data(response)

        # Get the count of threat records
        threats = response.get("threat", [])
        count = response.get("record_count", len(threats))

        # Update summary with count and common fields
        summary = {"total_count": count, "indicator_type": self._param.get("indicator_type", "all")}

        # Add indicator value to summary if present
        if self._param.get("indicator_value"):
            summary["indicator_value"] = self._param.get("indicator_value")

        self._action_result.update_summary(summary)

        # Set appropriate message based on results
        if count > 0:
            self._action_result.set_status(phantom.APP_SUCCESS, consts.ACTION_INDICATOR_THREAT_LOOKUP_SUCCESS_RESPONSE.format(count=count))
        else:
            self._action_result.set_status(phantom.APP_SUCCESS, consts.ACTION_INDICATOR_THREAT_LOOKUP_NO_RESULTS)

        return phantom.APP_SUCCESS

    def execute(self):
        """
        Execute the indicator threat lookup action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make REST call to lookup threat intelligence
        Step 4: Handle the response
        """
        # Log action start
        self.__log_action_start()

        # Validate parameters
        ret_val = self.__validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        # Make API call
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            return ret_val

        # Handle response using dedicated method
        return self.__handle_response(response)
