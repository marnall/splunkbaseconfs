#!/usr/bin/python
# File: ciscomeraki_adaptive_policies.py
#
# Copyright (c) 2025-2026 Splunk Inc.
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

import ciscomeraki_consts as consts


class AdaptivePolicies:
    """Class to handle adaptive policy management actions."""

    def __init__(self):
        """Initialize the adaptive policies handler.

        Note: The following attributes must be set before calling execute():
        - _param: Action parameters
        - _action_result: ActionResult object
        - _connector: Connector instance
        - _operation_type: Type of operation being performed
        - _get_endpoint: Method to get API endpoint
        """
        # These attributes are set externally before execute() is called
        self._param = None
        self._action_result = None
        self._connector = None
        self._operation_type = None
        self._get_endpoint = None

    def _validate_params(self):
        """Validate parameters.

        Returns:
            bool: Success/failure
        """
        organization_id = self._param.get("organization_id")
        if not organization_id:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_REQUIRED_PARAM.format(key="organization_id"))

        return phantom.APP_SUCCESS

    def execute(self):
        """Execute the adaptive policy operation.

        Returns:
            bool: Success/failure
        """
        # self._param = self._connector.get_current_param()
        #       self._action_result = self._connector.add_action_result(ActionResult(dict(self._param)))

        # Validate parameters
        if phantom.is_fail(self._validate_params()):
            return self._action_result.get_status()

        organization_id = self._param["organization_id"]

        try:
            # Get the appropriate endpoint
            endpoint = self._get_endpoint(organization_id)  # pylint: disable=not-callable

            # Make REST call
            ret_val, response = self._connector._utils._make_rest_call(endpoint, "get")

            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            # Process each item in the response
            for item in response:
                self._action_result.add_data(item)

            # Add summary
            summary = {"total_items": len(response), "operation_type": self._operation_type, "organization_id": organization_id}
            self._action_result.update_summary(summary)

            return self._action_result.set_status(
                phantom.APP_SUCCESS,
                consts.ACTION_SUCCESS_RESPONSE.format(
                    action=" ".join(
                        [i.capitalize() if idx > 0 else i for idx, i in enumerate(self._connector.get_action_identifier().split("_"))]
                    )
                ),
            )

        except Exception as e:
            error_message = self._connector._utils._get_error_message_from_exception(e)
            return self._action_result.set_status(phantom.APP_ERROR, f"Error occurred: {error_message}")
