#!/usr/bin/env python3
# File: infoblox_get_soc_insights_comments.py
#
# Copyright 2025 Infoblox Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import phantom.app as phantom

import infoblox_consts as consts
from actions import BaseAction


class GetSocInsightsComments(BaseAction):
    """Class to handle retrieving SOC insights comments.

    This action retrieves the list of comments associated with a specific
    Insight ID from Infoblox, optionally filtered by a time range.
    """

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Get SOC Insights Comments"))

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

        return phantom.APP_SUCCESS

    def __make_api_call(self):
        """
        Make the API call to get SOC insights comments.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        insight_id = self._param.get("insight_id")
        endpoint = consts.SOC_INSIGHTS_COMMENTS_ENDPOINT.format(insight_id)

        # Build query parameters
        params = {}
        from_time = self._param.get("from")
        if from_time:
            params["from"] = from_time

        to_time = self._param.get("to")
        if to_time:
            params["to"] = to_time

        self._connector.debug_print(f"Making API call to get insights comments for insight ID: {insight_id}")
        self._connector.debug_print(f"Endpoint: {endpoint}")
        self._connector.debug_print(f"Query parameters: {params}")

        return self._connector.util.make_rest_call(endpoint=endpoint, action_result=self._action_result, method="get", params=params)

    def __handle_response(self, response):
        """
        Handle the API response and process the insights comments data.
        Uses .get() method for safe dictionary access to avoid KeyError exceptions.

        Args:
            response (dict): The API response containing comments

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        # Validate response structure using .get() for safe access
        if not isinstance(response, dict):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: expected JSON object")

        # Check for comments field (actual API response structure)
        comments = response.get("comments")
        if comments is None:
            # Instead of treating it as an error, handle it as a successful request with no results
            self._action_result.add_data({"comments": []})  # Add empty comments list to data

            # Update summary with zero comments
            summary = {
                "total_comments": 0,
                "insight_id": self._param.get("insight_id", "Unknown"),
                "from_filter": self._param.get("from", "Not specified"),
                "to_filter": self._param.get("to", "Not specified"),
            }
            self._action_result.update_summary(summary)

            # Return success with informative message
            return self._action_result.set_status(phantom.APP_SUCCESS, "No comments found for the specified insight for mentioned time range")

        self._connector.debug_print("Processing insights comments response")

        # Store complete API response
        self._action_result.add_data(response)

        # Count total comments
        total_comments = len(comments) if isinstance(comments, list) else 0

        # Generate comprehensive summary
        summary = {
            "total_comments": total_comments,
            "insight_id": self._param.get("insight_id", "Unknown"),
            "from_filter": self._param.get("from", "Not specified"),
            "to_filter": self._param.get("to", "Not specified"),
        }

        self._action_result.update_summary(summary)

        # Generate success message
        success_message = consts.ACTION_GET_SOC_INSIGHTS_COMMENTS_SUCCESS_RESPONSE.format(count=total_comments)

        return self._action_result.set_status(phantom.APP_SUCCESS, success_message)

    def execute(self):
        """
        Execute get SOC insights comments action following the modular approach.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make API call
        Step 4: Handle response

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
        self._connector.save_progress(f"Retrieving comments for insight ID: {insight_id}")
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 4: Handle response
        ret_val = self.__handle_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 5: Return results
        self._connector.save_progress("SOC insights comments retrieved successfully")
        return phantom.APP_SUCCESS
