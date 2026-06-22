# File: infoblox_get_indicator_intel_lookup_result.py
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


class GetIndicatorIntelLookupResult(BaseAction):
    """Class to handle getting indicator intel lookup result action."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Get Indicator Intel Lookup Result"))

    # No custom parameter validation needed as we rely on SOAR's built-in JSON schema validation

    def __make_api_call(self):
        """
        Make the REST API call to retrieve indicator intel lookup results.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        # Get the job_id parameter
        job_id = self._param["job_id"]

        # Prepare the endpoint with the job_id
        endpoint = f"{consts.INDICATOR_INTEL_LOOKUP_JOBS_ENDPOINT}/{job_id}/results"

        # Make the GET call to retrieve results
        return self._connector.util.make_rest_call(endpoint=endpoint, action_result=self._action_result, method="get")

    def __handle_response(self, response):
        """
        Handle the API response for the indicator intel lookup result.

        Args:
            response (dict): The API response containing lookup results

        Returns:
            int: phantom.APP_SUCCESS on successful retrieval, phantom.APP_ERROR otherwise
        """
        if not response:
            return self._action_result.set_status(
                phantom.APP_ERROR,
                consts.ACTION_INDICATOR_INTEL_LOOKUP_RESULT_ERROR.format(error="Empty response from server"),
            )

        # Add the entire response as data
        self._action_result.add_data(response)

        # Create summary with key info
        summary = {"state": response.get("state"), "status": response.get("status"), "job_id": response.get("job_id")}

        # Get the count of result records
        results = response.get("results", [])
        summary["total_results"] = len(results)

        # Update the action result summary
        self._action_result.update_summary(summary)

        # Set the status message based on the job state/status
        job_state = response.get("state", "").lower()
        job_status = response.get("status", "").lower()

        if job_state == "completed" and job_status == "success":
            message = consts.ACTION_INDICATOR_INTEL_LOOKUP_RESULT_SUCCESS_RESPONSE.format(count=len(results), job_id=response.get("job_id"))
            status = phantom.APP_SUCCESS
        elif job_state == "completed" and job_status != "success":
            message = consts.ACTION_INDICATOR_INTEL_LOOKUP_RESULT_FAILED.format(job_id=response.get("job_id"), status=job_status)
            status = phantom.APP_ERROR
        elif job_state == "in_progress":
            message = consts.ACTION_INDICATOR_INTEL_LOOKUP_RESULT_IN_PROGRESS.format(job_id=response.get("job_id"))
            status = phantom.APP_SUCCESS
        else:
            message = consts.ACTION_INDICATOR_INTEL_LOOKUP_RESULT_UNKNOWN.format(
                job_id=response.get("job_id"), state=job_state, status=job_status
            )
            status = phantom.APP_SUCCESS

        return self._action_result.set_status(status, message)

    def execute(self):
        """
        Execute the get indicator intel lookup result action.

        Step 1: Log action start
        Step 2: Make REST call to retrieve indicator intel lookup results
        Step 3: Handle the response
        """
        # Log action start
        self.__log_action_start()

        # Make API call
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            return ret_val

        # Handle response using dedicated method
        return self.__handle_response(response)
