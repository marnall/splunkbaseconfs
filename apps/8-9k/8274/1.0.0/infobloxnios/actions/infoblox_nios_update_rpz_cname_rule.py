# File: infoblox_nios_update_rpz_cname_rule.py
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


class UpdateRpzCnameRuleAction(BaseAction):
    """Update RPZ CNAME Rule action class."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress("Starting Update RPZ CNAME Rule action")

    def __validate_params(self):
        """Validate action parameters.

        Special validation for:
        1. Rule Type matching Substitute requires substitute_name
        2. Reference ID is provided and valid format
        3. Additional Parameters JSON parsing

        :return: bool: True if parameters are valid, False otherwise
        """
        # Get and validate rule_type parameter - required parameters
        rule_type = self._param["rule_type"]
        reference_id = self._param["reference_id"]
        # Optional parameters
        additional_params_str = self._param.get("additional_parameters", "{}")

        # Validate reference_id is provided and correctly formatted
        if not reference_id or not reference_id.startswith("record:rpz:cname"):
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_REFERENCE_ID)

        # If rule type is Substitute, substitute_name is required
        if rule_type == "Substitute (domain name)" and not self._param.get("substitute_name"):
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_REQUIRED_SUBSTITUTE_NAME)

        # Determine object type from reference_id
        object_type = None
        if ":ipaddress/" in reference_id:
            object_type = "IP address"
        elif ":clientipaddress/" in reference_id:
            object_type = "Client IP Address"
        else:
            object_type = "Domain Name"

        # Check if trying to update to substitute rule for IP or Client IP
        if rule_type == "Substitute (domain name)" and object_type != "Domain Name":
            return self._action_result.set_status(
                phantom.APP_ERROR,
                f"Cannot update to substitute rule for {object_type}. Substitute rules are only supported for Domain Name objects.",
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
        """Determine canonical value based on rule type.

        :return: str: The canonical value for the API request
        """
        rule_type = self._param["rule_type"]
        reference_id = self._param["reference_id"]
        name = self._param["name"]
        substitute_name = self._param.get("substitute_name")

        # Use the shared utility method
        canonical_value = self._connector.utils.prepare_rpz_cname_canonical_value(
            rule_type=rule_type, name=name, substitute_name=substitute_name, reference_id=reference_id
        )

        # If canonical value is None, it means there was an error
        if canonical_value is None and rule_type == "Substitute (domain name)":
            self.save_progress("Cannot update to substitute rule for IP or Client IP address objects")

        return canonical_value

    def __format_name(self):
        """Format name parameter if both name and rp_zone are provided.

        If name doesn't include rp_zone, append it.

        :return: tuple: (success, formatted_name)
        """
        name = self._param["name"]
        rp_zone = self._param["rp_zone"]

        # Use the shared utility method
        return self._connector.utils.format_rpz_cname_name(name, rp_zone)

    def __prepare_data(self):
        """Prepare data for the update request.

        :return: dict: The data dictionary for the update request
        """
        data = {}

        # Format name parameter if both name and rp_zone are provided
        if self._param["name"] and self._param["rp_zone"]:
            success, formatted_name = self.__format_name()
            if not success:
                self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_NAME_FORMAT)
                return None

            if formatted_name:
                data["name"] = formatted_name

        # Add RP zone if provided
        if self._param["rp_zone"]:
            data["rp_zone"] = self._param["rp_zone"]

        # Add canonical value based on rule type
        if self._param["rule_type"]:
            canonical = self.__prepare_canonical_value()
            if canonical is not None:  # Skip if canonical couldn't be determined
                data["canonical"] = canonical

        # Add view if provided
        if self._param.get("view"):
            data["view"] = self._param.get("view")

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

        return data

    def __make_api_call(self):
        """Make the REST API call to update the RPZ CNAME rule.

        :return: tuple: (status, response) - Status code and API response
        """
        # Get reference ID
        reference_id = self._param["reference_id"]

        # Prepare endpoint with reference ID and return fields
        if ":ipaddress/" in reference_id or ":clientipaddress/" in reference_id:
            endpoint = f"/{reference_id}?{consts.RETURN_FIELDS_PARAM_IP}"
        else:
            endpoint = f"/{reference_id}?{consts.RETURN_FIELDS_PARAM}"

        # Prepare data for the update
        data = self.__prepare_data()
        if not data:
            return self._action_result.get_status(), None

        # Log API request details for debugging
        self._connector.debug_print(f"Request data: {data}")

        # Make the API call
        return self._connector.utils.make_rest_call(endpoint, self._action_result, data=data, method="put", timeout=30)

    def __handle_response(self, response):
        """Handle the API response for update RPZ CNAME rule.

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
        message = consts.SUCCESS_UPDATE_RPZ_CNAME_RULE
        if ref_id:
            message += f" with reference ID: {ref_id}"

        return self._action_result.set_status(phantom.APP_SUCCESS, message)

    def execute(self):
        """Execute the Update RPZ CNAME Rule action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make API call to update RPZ CNAME rule
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

            return self._action_result.set_status(phantom.APP_ERROR, f"{consts.ERROR_UPDATE_RPZ_CNAME_RULE}: {error_msg}")

        # Step 4: Handle the response
        return self.__handle_response(response)
