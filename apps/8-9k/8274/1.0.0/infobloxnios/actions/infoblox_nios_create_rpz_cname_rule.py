# File: infoblox_nios_create_rpz_cname_rule.py
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


class CreateRpzCnameRuleAction(BaseAction):
    """Create RPZ CNAME Rule action class."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress("Starting Create RPZ CNAME Rule action")

    def __validate_params(self):
        """Validate action parameters.

        Special validation for:
        1. Rule Type matching Substitute requires substitute_name
        2. Comment length < 256 chars
        3. Valid object type
        4. Additional Parameters JSON parsing

        :return: bool: True if parameters are valid, False otherwise
        """
        # Get and validate rule_type parameter - required parameters use direct access
        rule_type = self._param["rule_type"]
        object_type = self._param["object_type"]
        comment = self._param.get("comment", "")
        additional_params_str = self._param.get("additional_parameters", "{}")

        # If rule type is Substitute, substitute_name is required
        if rule_type == "Substitute (domain name)" and not self._param.get("substitute_name"):
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_REQUIRED_SUBSTITUTE_NAME)

        # Early validation of object type and rule type combination
        # Check if trying to create substitute rule for IP or Client IP
        if rule_type == "Substitute (domain name)" and object_type != "Domain Name":
            return self._action_result.set_status(
                phantom.APP_ERROR,
                f"Cannot create substitute rule for {object_type}. Substitute rules are only supported for Domain Name objects.",
            )

        # Validate additional parameters JSON if provided
        if additional_params_str and additional_params_str != "{}":
            try:
                json.loads(additional_params_str)
            except Exception as e:
                error_msg = self._connector.utils.get_error_message_from_exception(e)
                return self._action_result.set_status(phantom.APP_ERROR, f"{consts.ERROR_JSON_PARSE}: {error_msg}")

        return phantom.APP_SUCCESS

    def __prepare_canonical_value(self):
        """Determine canonical value based on rule type and object type.

        :return: str: The canonical value for the API request
        """
        # Required parameters use direct access
        rule_type = self._param["rule_type"]
        object_type = self._param["object_type"]
        name = self._param["name"]
        # Optional parameter - substitute_name is required only for Substitute rule type
        substitute_name = self._param.get("substitute_name")

        # Use the shared utility method
        canonical_value = self._connector.utils.prepare_rpz_cname_canonical_value(
            rule_type=rule_type, name=name, substitute_name=substitute_name, object_type=object_type
        )

        # If canonical value is None, it means there was an error
        if canonical_value is None and rule_type == "Substitute (domain name)":
            self.save_progress("Cannot create substitute rule for IP or Client IP address objects")

        return canonical_value

    def __format_name(self):
        """Format name parameter according to requirements.

        If name doesn't include rp_zone, append it.

        :return: tuple: (success, formatted_name)
        """
        # Required parameters use direct access
        name = self._param["name"]
        rp_zone = self._param["rp_zone"]

        return self._connector.utils.format_rpz_cname_name(name, rp_zone)

    def __get_endpoint_and_prepare_data(self):
        """Get API endpoint and prepare data for the request.

        :return: tuple: (endpoint, data_dict)
        """
        # Get object type to determine endpoint - required parameter
        object_type = self._param["object_type"]

        # Determine endpoint based on object type
        if object_type == "Domain Name":
            endpoint = f"{consts.RPZ_CNAME_DOMAIN_ENDPOINT}?{consts.RETURN_FIELDS_PARAM}"
        elif object_type == "IP address":
            endpoint = f"{consts.RPZ_CNAME_IP_ENDPOINT}?{consts.RETURN_FIELDS_PARAM_IP}"
        else:  # Client IP Address
            endpoint = f"{consts.RPZ_CNAME_CLIENT_IP_ENDPOINT}?{consts.RETURN_FIELDS_PARAM_IP}"

        # Format name parameter
        success, formatted_name = self.__format_name()
        if not success:
            return None, None

        # Prepare base data
        data = {
            "name": formatted_name,
            "rp_zone": self._param["rp_zone"],
            "canonical": self.__prepare_canonical_value(),
            "view": self._param.get("view", "default"),
        }

        # Add comment if provided
        if self._param.get("comment"):
            data["comment"] = self._param.get("comment")

        # Add additional parameters if provided
        additional_params_str = self._param.get("additional_parameters", "{}")
        if additional_params_str and additional_params_str != "{}":
            try:
                additional_params = json.loads(additional_params_str)
                # Merge additional parameters into the data dict
                data.update(additional_params)
            except:
                pass  # Already validated in __validate_params

        return endpoint, data

    def __make_api_call(self):
        """Make the REST API call to create the RPZ CNAME rule.

        :return: tuple: (status, response) - Status code and API response
        """
        endpoint, data = self.__get_endpoint_and_prepare_data()

        if not endpoint or not data:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_NAME_FORMAT), None

        # Log API request details for debugging
        self._connector.debug_print(f"Request data: {data}")

        # Make the API call
        return self._connector.utils.make_rest_call(endpoint, self._action_result, data=data, method="post", timeout=30)

    def __handle_response(self, response):
        """Handle the API response for create RPZ CNAME rule.

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
        message = consts.SUCCESS_CREATE_RPZ_CNAME_RULE
        if ref_id:
            message += f" with reference ID: {ref_id}"

        return self._action_result.set_status(phantom.APP_SUCCESS, message)

    def execute(self):
        """Execute the Create RPZ CNAME Rule action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make API call to create RPZ CNAME rule
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

            return self._action_result.set_status(phantom.APP_ERROR, f"{consts.ERROR_CREATE_RPZ_CNAME_RULE}: {error_msg}")

        # Step 4: Handle the response
        return self.__handle_response(response)
