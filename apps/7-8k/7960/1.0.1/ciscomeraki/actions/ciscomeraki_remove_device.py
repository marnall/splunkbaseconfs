# File: ciscomeraki_remove_device.py
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


class RemoveDevice(BaseAction):
    """Class to handle the remove device action."""

    def execute(self):
        """Execute the remove device action.

        Returns:
            bool: Success/failure
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("remove_device"))

        # Validate required parameters
        network_id = self._param.get("network_id")
        serial = self._param.get("serial")

        if not network_id:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_REQUIRED_PARAM.format(key="network_id"))

        if not serial:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_REQUIRED_PARAM.format(key="serial"))

        # Make REST call
        ret_val, response = self._connector._utils._make_rest_call(
            endpoint=consts.REMOVE_DEVICE.format(network_id=network_id, serial=serial), action_result=self._action_result, method="delete"
        )

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        # Process response
        self._action_result.add_data({"network_id": network_id, "serial": serial, "removed": True})

        summary = {"device_removed": True, "serial": serial}
        self._action_result.update_summary(summary)

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_SUCCESS_RESPONSE.format(
                action=" ".join([i.capitalize() if idx > 0 else i for idx, i in enumerate(self._connector.get_action_identifier().split("_"))])
            ),
        )
