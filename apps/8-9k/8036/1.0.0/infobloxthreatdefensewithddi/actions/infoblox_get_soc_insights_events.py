# File: infoblox_get_soc_insights_events.py
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


class GetSocInsightsEvents(BaseAction):
    """Class to handle retrieving SOC insights events.

    This action retrieves a detailed list of threat-related events for a specific
    Insight ID from Infoblox SOC Insights, supporting multiple filter parameters.
    """

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Get SOC Insights Events"))

    def _validate_params(self):
        """
        Validate action parameters for format/content.
        Note: Required parameter validation is handled by SOAR's built-in JSON schema validation.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        # Validate from parameter if provided
        from_time = self._param.get("from")
        if from_time:
            if not self._connector.validator.validate_datetime_format(from_time):
                return self._action_result.set_status(
                    phantom.APP_ERROR,
                    "From parameter must be in format YYYY-MM-DDTHH:mm:ss.SSS. Example: '2025-06-11T04:10:00.000'",
                )

        # Validate to parameter if provided
        to_time = self._param.get("to")
        if to_time:
            if not self._connector.validator.validate_datetime_format(to_time):
                return self._action_result.set_status(
                    phantom.APP_ERROR,
                    "To parameter must be in format YYYY-MM-DDTHH:mm:ss.SSS. Example: '2025-06-11T04:10:00.000'",
                )

        # Validate limit parameter if provided
        limit = self._param.get("limit")
        if limit is not None:
            ret_val, limit = self._connector.validator.validate_integer(
                self._action_result, limit, "limit", allow_zero=False, allow_negative=False
            )
            if phantom.is_fail(ret_val):
                return ret_val

            # Check limit range
            if limit > consts.MAX_LIMIT:
                return self._action_result.set_status(phantom.APP_ERROR, f"Limit parameter must be less than or equal to {consts.MAX_LIMIT}")

        # Validate device_ip parameter if provided
        device_ip = self._param.get("device_ip")
        if device_ip:
            if not self._connector.validator.validate_ip_address(device_ip):
                return self._action_result.set_status(phantom.APP_ERROR, f"Invalid device IP address format: {device_ip}")

        return phantom.APP_SUCCESS

    def __make_api_call(self):
        """
        Make API call to retrieve SOC insights events.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        insight_id = self._param.get("insight_id")

        # Build endpoint
        endpoint = consts.SOC_INSIGHTS_EVENTS_ENDPOINT.format(insight_id)

        # Build query parameters dynamically
        params = {}

        # Add optional filter parameters if provided
        # Note: Exclude threat_level and confidence_level if set to "All" as API doesn't support it
        threat_level = self._param.get("threat_level")
        if threat_level and threat_level.lower() != "all":
            params["threat_level"] = threat_level

        confidence_level = self._param.get("confidence_level")
        if confidence_level and confidence_level.lower() != "all":
            params["confidence_level"] = confidence_level

        if self._param.get("query"):
            params["query"] = self._param.get("query")
        if self._param.get("query_type"):
            params["query_type"] = self._param.get("query_type")
        if self._param.get("source"):
            params["source"] = self._param.get("source")
        if self._param.get("device_ip"):
            params["device_ip"] = self._param.get("device_ip")
        if self._param.get("indicator"):
            params["indicator"] = self._param.get("indicator")
        if self._param.get("from"):
            params["from"] = self._param.get("from")
        if self._param.get("to"):
            params["to"] = self._param.get("to")
        if self._param.get("limit"):
            params["limit"] = self._param.get("limit")

        self._connector.debug_print(f"Making API call to {endpoint}")
        self._connector.debug_print(f"Query parameters: {params}")

        # Make the API call
        ret_val, response = self._connector.util.make_rest_call(endpoint, self._action_result, params=params, method="get")

        if phantom.is_fail(ret_val):
            return ret_val, None

        return phantom.APP_SUCCESS, response

    def __handle_response(self, response):
        """
        Handle the API response and process the insights events data.
        Uses .get() method for safe dictionary access to avoid KeyError exceptions.

        Args:
            response (dict): The API response containing events

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        # Validate response structure using .get() for safe access
        if not isinstance(response, dict):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: expected JSON object")

        # Check for events field (actual API response structure)
        events = response.get("events")
        if events is None:
            # Instead of treating it as an error, handle it as a successful request with no results
            self._action_result.add_data({"events": []})  # Add empty events list to data

            # Update summary with zero events
            summary = {
                "total_events": 0,
                "insight_id": self._param.get("insight_id", "Unknown"),
                "limit_applied": self._param.get("limit", 100),
            }
            self._action_result.update_summary(summary)

            # Return success with simple informative message
            return self._action_result.set_status(phantom.APP_SUCCESS, "No events found for the specified insight ID")

        self._connector.debug_print("Processing insights events response")

        # Store complete API response
        self._action_result.add_data(response)

        # Count total events
        total_events = len(events) if isinstance(events, list) else 0

        # Generate summary
        summary = {
            "total_events": total_events,
            "insight_id": self._param.get("insight_id", "Unknown"),
            "limit_applied": self._param.get("limit", 100),
        }

        self._action_result.update_summary(summary)

        # Set success message using single constant with placeholder
        message = consts.SUCCESS_GET_INSIGHTS_EVENTS.format(total_events)

        return self._action_result.set_status(phantom.APP_SUCCESS, message)

    def execute(self):
        """
        Execute get SOC insights events action following the modular approach.

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
        insight_id = self._param.get("insight_id")
        self._connector.save_progress(f"Retrieving events for insight ID: {insight_id}")
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 4: Handle response
        ret_val = self.__handle_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 5: Return results
        self._connector.save_progress("SOC insights events retrieved successfully")
        return phantom.APP_SUCCESS
