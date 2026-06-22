# File: infoblox_initiate_indicator_intel_lookup.py
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


class InitiateIndicatorIntelLookup(BaseAction):
    """Class to handle initiating indicator intel lookup with Dossier."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Initiate Indicator Intel Lookup"))

    def __validate_params(self):
        """
        Validate the parameters for the action.

        Note:
            Required params validation (indicator_type, indicator_value) is handled by SOAR's built-in JSON validation.
        We're only adding extra validation for parameter format/content.

        Returns:
            int: phantom.APP_SUCCESS on success, phantom.APP_ERROR on failure
        """
        # Validate indicator_value based on indicator_type
        indicator_type = self._param.get("indicator_type").lower()
        indicator_value = self._param.get("indicator_value")

        # Use the generic indicator validator
        ret_val, error_msg = self._connector.validator.validate_indicator_value(self._action_result, indicator_type, indicator_value)
        if phantom.is_fail(ret_val):
            return self._action_result.set_status(phantom.APP_ERROR, error_msg)

        # Convert wait_for_results parameter directly to boolean
        self._wait_for_results = self._param.get("wait_for_results", "false").lower() == "true"

        return phantom.APP_SUCCESS

    def __make_api_call(self):
        """
        Make the REST API call to initiate indicator intel lookup.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        # Get parameters
        indicator_type = self._param.get("indicator_type", "").lower()
        indicator_value = self._param.get("indicator_value", "")

        # Prepare the endpoint
        endpoint = f"{consts.INDICATOR_INTEL_LOOKUP_ENDPOINT}/{indicator_type}"

        # Prepare query parameters
        params = {"value": indicator_value}

        # Add source parameter(s) if provided
        # Handle comma-separated values by splitting and adding multiple source parameters
        source = self._param.get("source", "")
        if source:
            # Split by comma and strip whitespace from each non-empty value
            source_values = [s.strip() for s in source.split(",") if s.strip()]
            if source_values:
                # requests library handles both single values and lists correctly
                params["source"] = source_values

        # Add wait parameter if needed
        if self._wait_for_results:
            params["wait"] = "true"

        # Make the GET call
        return self._connector.util.make_rest_call(endpoint=endpoint, action_result=self._action_result, method="get", params=params)

    def __handle_response(self, response):
        """
        Handle the API response for the indicator intel lookup.

        Args:
            response (dict): The API response containing lookup job information or results

        Returns:
            int: phantom.APP_SUCCESS on successful retrieval, phantom.APP_ERROR otherwise
        """
        if not response:
            return self._action_result.set_status(
                phantom.APP_ERROR, consts.ACTION_INDICATOR_INTEL_LOOKUP_ERROR.format(error="Empty response from server")
            )

        # Add the entire response as data
        self._action_result.add_data(response)

        # Extract key information for summary
        job_id = response.get("job_id", "")
        status = response.get("status", "")

        # Create summary with key info
        summary = {"job_id": job_id, "status": status}

        # If we waited for results, add result information
        if self._wait_for_results and response.get("results"):
            results = response.get("results", [])
            summary["total_results"] = len(results)

        # Update the action result summary
        self._action_result.update_summary(summary)

        # Set the status message based on the response
        if self._wait_for_results:
            message = consts.ACTION_INDICATOR_INTEL_LOOKUP_SUCCESS_WITH_RESULTS.format(count=len(response.get("results", [])), job_id=job_id)
        else:
            message = consts.ACTION_INDICATOR_INTEL_LOOKUP_SUCCESS_INITIATED.format(job_id=job_id, status=status)

        return self._action_result.set_status(phantom.APP_SUCCESS, message)

    def execute(self):
        """
        Execute the initiate indicator intel lookup action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make REST call to initiate lookup
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
