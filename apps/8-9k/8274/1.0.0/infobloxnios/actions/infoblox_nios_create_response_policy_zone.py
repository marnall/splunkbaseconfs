# File: infoblox_nios_create_response_policy_zone.py
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


class CreateResponsePolicyZoneAction(BaseAction):
    """Create Response Policy Zone action."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.CREATE_RPZ_START_MESSAGE)
        fqdn = self._param.get("fqdn", "")
        self._connector.save_progress(consts.CREATE_RPZ_PROGRESS_MESSAGE.format(fqdn=fqdn))

    def __prepare_and_validate_payload(self):
        """Validate parameters and prepare the payload for creating a response policy zone.

        Validates:
        - RPZ Policy values
        - RPZ Severity values
        - RPZ Type values
        - Additional parameters JSON format

        Then prepares the payload with validated parameters.

        :return: tuple: (status, payload, error_message) - Status code, prepared payload, and error message if any
        """
        # Required parameter
        fqdn = self._param["fqdn"]

        # Initialize the payload with the required parameter
        payload = {"fqdn": fqdn}

        # Validate and add RPZ Policy
        rpz_policy = self._param.get("rpz_policy")
        if rpz_policy:
            if rpz_policy not in consts.RPZ_POLICY_VALUES:
                return (
                    phantom.APP_ERROR,
                    None,
                    consts.ERROR_INVALID_ENUM_PARAM.format(key="rpz_policy", valid_values=", ".join(consts.RPZ_POLICY_VALUES)),
                )
            payload["rpz_policy"] = rpz_policy

        # Validate and add RPZ Severity
        rpz_severity = self._param.get("rpz_severity")
        if rpz_severity:
            if rpz_severity not in consts.RPZ_SEVERITY_VALUES:
                return (
                    phantom.APP_ERROR,
                    None,
                    consts.ERROR_INVALID_ENUM_PARAM.format(key="rpz_severity", valid_values=", ".join(consts.RPZ_SEVERITY_VALUES)),
                )
            payload["rpz_severity"] = rpz_severity

        # Validate and add RPZ Type
        rpz_type = self._param.get("rpz_type")
        if rpz_type:
            if rpz_type not in consts.RPZ_TYPE_VALUES:
                return (
                    phantom.APP_ERROR,
                    None,
                    consts.ERROR_INVALID_ENUM_PARAM.format(key="rpz_type", valid_values=", ".join(consts.RPZ_TYPE_VALUES)),
                )
            payload["rpz_type"] = rpz_type

        # Add other simple parameters
        if self._param.get("substitute_name"):
            payload["substitute_name"] = self._param.get("substitute_name")

        if self._param.get("comment"):
            payload["comment"] = self._param.get("comment")

        # Handle fireeye_rule_mapping as JSON object
        if self._param.get("fireeye_rule_mapping"):
            try:
                fireeye_mapping = json.loads(self._param.get("fireeye_rule_mapping"))
                payload["fireeye_rule_mapping"] = fireeye_mapping
            except json.JSONDecodeError:
                return phantom.APP_ERROR, None, consts.CREATE_RPZ_INVALID_JSON_ERROR.format(field="fireeye_rule_mapping")

        # Handle additional parameters provided as JSON
        if self._param.get("additional_parameters"):
            try:
                additional_params = json.loads(self._param.get("additional_parameters"))
                # Merge additional parameters with the payload
                payload.update(additional_params)
            except json.JSONDecodeError:
                return phantom.APP_ERROR, None, consts.CREATE_RPZ_INVALID_JSON_ERROR.format(field="additional_parameters")

        return phantom.APP_SUCCESS, payload, None

    def __make_api_call(self, payload):
        """Make the REST API call to create response policy zone.

        :param payload: The payload for the API request
        :return: tuple: (status, response) - Status code and API response
        """
        # Construct query parameters for return fields
        params = {"_return_fields": consts.RPZ_RETURN_FIELDS}

        # Make POST API call
        return self._connector.utils.make_rest_call(consts.CREATE_RPZ_ENDPOINT, self._action_result, method="post", data=payload, params=params)

    def __handle_response(self, response):
        """Handle the API response for create operation.

        :param response: The API response
        :return: status (success/failure)
        """
        # Add the response data to the action result
        self._action_result.add_data(response)

        # Extract reference ID from the response
        reference_id = response.get("_ref", "")

        # Add summary metrics
        summary = self._action_result.update_summary({})
        summary["total_objects"] = 1
        summary["total_objects_successful"] = 1

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.CREATE_RPZ_SUCCESS_MESSAGE.format(reference_id=reference_id))

    def execute(self):
        """Execute the create response policy zone action.

        Step 1: Log action start
        Step 2: Validate parameters and prepare payload
        Step 3: Make API call to create response policy zone
        Step 4: Handle the response

        :return: status (success/failure)
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters and prepare payload
        status, payload, error_message = self.__prepare_and_validate_payload()
        if phantom.is_fail(status):
            self._connector.save_progress(error_message)
            return self._action_result.set_status(phantom.APP_ERROR, error_message)

        # Step 3: Make API call to create response policy zone
        status, response = self.__make_api_call(payload)

        if phantom.is_fail(status):
            error_message = self._action_result.get_message() or consts.CREATE_RPZ_ERROR_MESSAGE
            self._connector.save_progress(error_message)
            return self._action_result.set_status(phantom.APP_ERROR, error_message)

        # Step 4: Handle the response
        return self.__handle_response(response)
