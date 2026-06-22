# File: infoblox_nios_create_rpz_srv_rule.py
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


class CreateRpzSrvRuleAction(BaseAction):
    """Class to handle create RPZ SRV rule action.

    Adds an SRV record override in RPZ for service-based DNS lookups.
    """

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Create RPZ SRV Rule"))

    def _validate_integer_range(self, param_name, max_value=consts.MAX_PORT_VALUE):
        """Validate integer parameter within specified range.

        Args:
            param_name (str): Name of the parameter to validate
            max_value (int): Maximum allowed value

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        param_value = self._param.get(param_name)
        if param_value is not None:
            ret_val, validated_value = self._connector.validator.validate_integer(
                self._action_result,
                param_value,
                param_name,
                allow_zero=True,
                allow_negative=False,
            )
            if phantom.is_fail(ret_val):
                return ret_val

            if validated_value > max_value:
                return self._action_result.set_status(phantom.APP_ERROR, f"{param_name.capitalize()} parameter must be in range 0-{max_value}")

        return phantom.APP_SUCCESS

    def _validate_params(self):
        """
        Validate action parameters for format/content.
        Note: Required parameter validation is handled by SOAR's built-in JSON schema validation.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        # Validate integer range parameters (priority, port, weight)
        for param_name in ["priority", "port", "weight"]:
            ret_val = self._validate_integer_range(param_name)
            if phantom.is_fail(ret_val):
                return ret_val

        # Validate additional_parameters JSON format
        additional_parameters = self._param.get("additional_parameters", "").strip()
        if additional_parameters:
            try:
                self._parsed_additional_params = json.loads(additional_parameters)
            except json.JSONDecodeError as e:
                return self._action_result.set_status(phantom.APP_ERROR, f"Invalid JSON format for additional_parameters: {e!s}")
        else:
            self._parsed_additional_params = {}

        return phantom.APP_SUCCESS

    def __format_name(self):
        """Format name parameter according to requirements.

        If name doesn't include rp_zone, append it.

        :return: formatted_name
        """
        # Required parameters use direct access
        name = self._param["name"]
        rp_zone = self._param["rp_zone"]

        return self._connector.utils.format_rpz_cname_name(name, rp_zone)

    def __build_request_payload(self):
        """
        Build the request payload for creating RPZ SRV rule.

        Returns:
            dict: Request payload for the API call
        """
        # Format the name parameter according to requirements
        success, formatted_name = self.__format_name()
        if not success:
            # If formatting failed, return None to indicate failure
            return None

        # Build the basic payload with required parameters
        payload = {
            "name": formatted_name,
            "priority": self._param["priority"],
            "rp_zone": self._param["rp_zone"].strip(),
            "port": self._param["port"],
            "target": self._param["target"].strip(),
            "weight": self._param["weight"],
        }

        # Add optional comment if provided
        comment = self._param.get("comment", "").strip()
        if comment:
            payload["comment"] = comment

        # Add additional parameters (already parsed and validated)
        if hasattr(self, "_parsed_additional_params") and self._parsed_additional_params:
            # Merge only supported fields into the payload
            for field in consts.RPZ_SUPPORTED_ADDITIONAL_FIELDS:
                if field in self._parsed_additional_params:
                    payload[field] = self._parsed_additional_params[field]

        return payload

    def __make_api_call(self):
        """
        Make the API call to create RPZ SRV rule.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        # Build the request payload
        payload = self.__build_request_payload()

        # Build query parameters with return fields
        params = {"_return_fields": consts.CREATE_RPZ_SRV_RULE_RETURN_FIELDS}

        # Set headers for POST request
        headers = {"Content-Type": "application/json"}

        self._connector.debug_print(f"Creating RPZ SRV rule with payload: {json.dumps(payload, indent=2)}")

        # Make the POST API call
        return self._connector.utils.make_rest_call(
            endpoint=consts.CREATE_RPZ_SRV_RULE_ENDPOINT,
            action_result=self._action_result,
            method="post",
            params=params,
            data=payload,
            headers=headers,
        )

    def __handle_response(self, response):
        """
        Handle the API response and process the RPZ SRV rule creation data.
        Uses .get() method for safe dictionary access to avoid KeyError exceptions.

        Args:
            response (dict): The API response containing the created rule data

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        # Validate response structure using .get() for safe access
        if not isinstance(response, dict):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: expected JSON object")

        self._connector.debug_print("Processing RPZ SRV rule creation response")

        # Create a processed copy for display purposes
        processed_record = dict(response)

        # Process extended attributes for display if present
        extattrs = response.get("extattrs", {})
        processed_record["extattrs_display"] = (
            ", ".join(
                [
                    f"{key}={value_obj.get('value', str(value_obj)) if isinstance(value_obj, dict) else str(value_obj)}"
                    for key, value_obj in extattrs.items()
                ]
            )
            if isinstance(extattrs, dict) and extattrs
            else ""
        )

        # Add the processed record to results
        self._action_result.add_data(processed_record)

        # Generate comprehensive summary using direct response access
        summary = {
            "total_objects": 1,
            "total_objects_successful": 1,
            "rule_reference": response.get("_ref", ""),
            "rule_name": response.get("name", ""),
            "rp_zone": response.get("rp_zone", ""),
            "priority": response.get("priority", ""),
            "port": response.get("port", ""),
            "weight": response.get("weight", ""),
        }

        self._action_result.update_summary(summary)

        # Generate success message using the common format
        success_message = consts.COMMON_SUCCESS_MESSAGE.format(action_verb="created", count=1, object_type="RPZ SRV rule")

        return self._action_result.set_status(phantom.APP_SUCCESS, success_message)

    def execute(self):
        """
        Execute create RPZ SRV rule action following the modular approach.

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
        self._connector.save_progress("Creating RPZ SRV rule")
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 4: Handle response
        ret_val = self.__handle_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 5: Return results
        self._connector.save_progress("RPZ SRV rule created successfully")
        return phantom.APP_SUCCESS
