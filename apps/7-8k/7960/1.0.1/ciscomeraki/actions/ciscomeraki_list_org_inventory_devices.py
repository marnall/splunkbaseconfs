#!/usr/bin/python
# File: ciscomeraki_list_org_inventory_devices.py
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
from actions import BaseAction


class ListOrgInventoryDevices(BaseAction):
    """Class to handle the list organization inventory devices action."""

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
        """Execute the list organization inventory devices action.

        Returns:
            bool: Success/failure
        """
        # self._param = self._connector.get_current_param()
        #       self._action_result = self._connector.add_action_result(ActionResult(dict(self._param)))

        # Validate parameters
        if phantom.is_fail(self._validate_params()):
            return self._action_result.get_status()

        organization_id = self._param["organization_id"]

        # Use paginator to get all inventory devices with max limit of 1000 per page
        ret_val, response = self._connector._utils._paginator(
            action_result=self._action_result,
            endpoint=consts.ORG_INVENTORY_DEVICES.format(organization_id=organization_id),
            limit=1000,  # Meraki API's maximum limit
        )

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        # Process each device in the response
        for device in response:
            self._action_result.add_data(device)

        # Add summary
        summary = {"total_devices": len(response), "organization_id": organization_id}
        self._action_result.update_summary(summary)

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_SUCCESS_RESPONSE.format(
                action=" ".join([i.capitalize() if idx > 0 else i for idx, i in enumerate(self._connector.get_action_identifier().split("_"))])
            ),
        )
