# File: infoblox_nios_create_rpz_txt_rule.py
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

import json

import phantom.app as phantom

import infoblox_nios_consts as consts
from actions import BaseAction


class CreateRpzTXTRuleAction(BaseAction):
    """Create RPZ TXT Rule action class."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress("Starting Create RPZ TXT Rule action")

    def __validate_params(self):
        """Validate action parameters.

        Validates additional parameters JSON parsing

        :return: bool: True if parameters are valid, False otherwise
        """

        # Validate additional parameters JSON if provided
        additional_params_str = self._param.get("additional_parameters")
        if additional_params_str and additional_params_str != "{}":
            try:
                json.loads(additional_params_str)
            except Exception as e:
                error_msg = self._connector.utils.get_error_message_from_exception(e)
                return self._action_result.set_status(phantom.APP_ERROR, f"{consts.ERROR_JSON_PARSE}: {error_msg}")

        return phantom.APP_SUCCESS

    def __get_endpoint_and_prepare_data(self):
        """Get API endpoint and prepare data for the request.

        :return: tuple: (endpoint, data_dict)
        """
        # Use the RPZ TXT endpoint with return fields
        endpoint = f"{consts.RPZ_TXT_ENDPOINT}?{consts.RETURN_FIELDS_PARAM_RPZ_TXT}"

        # Get name parameter
        name = self._param["name"]

        # Try to format name with RP zone if necessary
        success, formatted_name = self._connector.utils.format_rpz_cname_name(name, self._param["rp_zone"])
        if not success:
            self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_NAME_FORMAT)
            return None, None

        # Prepare base data
        data = {"rp_zone": self._param["rp_zone"], "name": formatted_name, "text": self._param["text"]}

        # Add comment if provided
        if self._param.get("comment"):
            data["comment"] = self._param.get("comment")

        # Add additional parameters if provided
        additional_params_str = self._param.get("additional_parameters")
        if additional_params_str and additional_params_str != "{}":
            try:
                additional_params = json.loads(additional_params_str)
                # Merge additional parameters into the data dict
                data.update(additional_params)
            except:
                pass  # Already validated in __validate_params

        return endpoint, data

    def __make_api_call(self):
        """Make the REST API call to create the RPZ TXT rule.

        :return: tuple: (status, response) - Status code and API response
        """
        endpoint, data = self.__get_endpoint_and_prepare_data()
        if not endpoint or not data:
            return phantom.APP_ERROR, None

        # Log API request details for debugging
        self._connector.debug_print(f"Request data: {data}")

        # Make the API call
        return self._connector.utils.make_rest_call(endpoint, self._action_result, data=data, method="post", timeout=30)

    def __handle_response(self, response):
        """Handle the API response for create RPZ TXT rule.

        Process response data and set action result.

        :param response: The API response
        :return: status (success/failure)
        """
        # Add response data to action result
        self._action_result.add_data(response)

        # Get reference ID from response for summary
        ref_id = response.get("_ref", "")

        # Set summary
        summary = {"total_objects": 1, "total_objects_successful": 1}
        self._action_result.update_summary(summary)

        # Generate success message with ref ID if available
        message = consts.SUCCESS_CREATE_RPZ_TXT_RULE
        if ref_id:
            message += f" with reference ID: {ref_id}"

        return self._action_result.set_status(phantom.APP_SUCCESS, message)

    def execute(self):
        """Execute the Create RPZ TXT Rule action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make API call to create RPZ TXT rule
        Step 4: Handle the response

        :return: status (success/failure)
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters
        status = self.__validate_params()
        if phantom.is_fail(status):
            return status

        # Step 3: Make API call
        status, response = self.__make_api_call()

        if phantom.is_fail(status):
            # Handle error in response - try to extract error message
            error_msg = self._action_result.get_message()

            # Check if the error is from API with specific format
            if isinstance(response, dict):
                if response.get("text"):
                    error_msg = response.get("text")
                elif response.get("Error", {}).get("text"):
                    error_msg = response.get("Error", {}).get("text")

            return self._action_result.set_status(phantom.APP_ERROR, f"{consts.ERROR_CREATE_RPZ_TXT_RULE}: {error_msg}")

        # Step 4: Handle the response
        return self.__handle_response(response)
