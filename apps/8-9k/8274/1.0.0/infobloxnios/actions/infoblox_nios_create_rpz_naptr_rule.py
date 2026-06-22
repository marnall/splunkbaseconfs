# File: infoblox_nios_create_rpz_naptr_rule.py
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


class CreateRpzNaptrRuleAction(BaseAction):
    """Class to handle create RPZ NAPTR rule action.

    Adds a NAPTR override in RPZ to control DNS-based service discovery.
    """

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Create RPZ NAPTR Rule"))

    def _validate_params(self):
        """
        Validate action parameters for format/content.
        Note: Required parameter validation is handled by SOAR's built-in JSON schema validation.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        # Validate order parameter (must be a valid integer)
        order = self._param.get("order")
        if order is not None:
            ret_val, order = self._connector.validator.validate_integer(
                self._action_result,
                order,
                "order",
                allow_zero=True,
                allow_negative=False,
            )
            if phantom.is_fail(ret_val):
                return ret_val
            if order < 0 or order > 65535:
                return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_ORDER_VALUE)

        # Validate preference parameter (must be a valid integer)
        preference = self._param.get("preference")
        if preference is not None:
            ret_val, preference = self._connector.validator.validate_integer(
                self._action_result,
                preference,
                "preference",
                allow_zero=True,
                allow_negative=False,
            )
            if phantom.is_fail(ret_val):
                return ret_val
            if preference < 0 or preference > 65535:
                return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_PREFERENCE_VALUE)

        # Validate additional_parameters (must be valid JSON if provided)
        additional_parameters = self._param.get("additional_parameters", "").strip()
        if additional_parameters:
            try:
                json.loads(additional_parameters)
            except json.JSONDecodeError as e:
                return self._action_result.set_status(phantom.APP_ERROR, f"Invalid JSON format for additional_parameters: {e!s}")

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
        Build the request payload for creating RPZ NAPTR rule.

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
            "rp_zone": self._param["rp_zone"].strip(),
            "order": self._param["order"],
            "preference": self._param["preference"],
            "replacement": self._param["replacement"].strip(),
        }

        # Add optional comment if provided
        comment = self._param.get("comment", "").strip()
        if comment:
            payload["comment"] = comment

        # Add additional parameters if provided
        additional_parameters = self._param.get("additional_parameters", "").strip()
        if additional_parameters:
            try:
                additional_params = json.loads(additional_parameters)
                # Merge additional parameters into the payload
                # Supported fields: disable, extattrs, flags, regexp, services, ttl, use_ttl, view
                supported_fields = ["disable", "extattrs", "flags", "regexp", "services", "ttl", "use_ttl", "view"]
                for field in supported_fields:
                    if field in additional_params:
                        payload[field] = additional_params[field]
            except json.JSONDecodeError:
                # This should have been caught in validation, but handle gracefully
                self._connector.debug_print("Warning: Invalid additional_parameters JSON, skipping")

        return payload

    def __make_api_call(self):
        """
        Make the API call to create RPZ NAPTR rule.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        # Build the request payload
        payload = self.__build_request_payload()

        # Build query parameters with return fields
        params = {"_return_fields": consts.CREATE_RPZ_NAPTR_RULE_RETURN_FIELDS}

        # Set headers for POST request
        headers = {"Content-Type": "application/json"}

        self._connector.debug_print(f"Creating RPZ NAPTR rule with payload: {json.dumps(payload, indent=2)}")

        # Make the POST API call
        return self._connector.utils.make_rest_call(
            endpoint=consts.CREATE_RPZ_NAPTR_RULE_ENDPOINT,
            action_result=self._action_result,
            method="post",
            params=params,
            data=payload,
            headers=headers,
        )

    def __handle_response(self, response):
        """
        Handle the API response and process the RPZ NAPTR rule creation data.
        Uses .get() method for safe dictionary access to avoid KeyError exceptions.

        Args:
            response (dict): The API response containing the created rule data

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        # Validate response structure using .get() for safe access
        if not isinstance(response, dict):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: expected JSON object")

        self._connector.debug_print("Processing RPZ NAPTR rule creation response")

        # Create a processed copy for display purposes
        processed_record = dict(response)

        # Process extended attributes for display if present
        extattrs = response.get("extattrs", {})
        if isinstance(extattrs, dict) and extattrs:
            extattr_display = []
            for key, value_obj in extattrs.items():
                if isinstance(value_obj, dict) and "value" in value_obj:
                    extattr_display.append(f"{key}={value_obj['value']}")
                else:
                    extattr_display.append(f"{key}={value_obj!s}")
            processed_record["extattrs_display"] = ", ".join(extattr_display)
        else:
            processed_record["extattrs_display"] = ""

        # Add the processed record to results
        self._action_result.add_data(processed_record)

        # Generate comprehensive summary
        summary = {
            "total_objects": 1,
            "total_objects_successful": 1,
            "rule_reference": response.get("_ref", ""),
            "rule_name": response.get("name", ""),
            "rp_zone": response.get("rp_zone", ""),
        }

        self._action_result.update_summary(summary)

        # Generate success message using the common format
        success_message = consts.COMMON_SUCCESS_MESSAGE.format(action_verb="created", count=1, object_type="RPZ NAPTR rule")

        return self._action_result.set_status(phantom.APP_SUCCESS, success_message)

    def execute(self):
        """
        Execute create RPZ NAPTR rule action following the modular approach.

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
        self._connector.save_progress("Creating RPZ NAPTR rule")
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 4: Handle response
        ret_val = self.__handle_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 5: Return results
        self._connector.save_progress("RPZ NAPTR rule created successfully")
        return phantom.APP_SUCCESS
