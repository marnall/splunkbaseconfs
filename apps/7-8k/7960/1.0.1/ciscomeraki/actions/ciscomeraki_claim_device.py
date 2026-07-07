# File: ciscomeraki_claim_device.py
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

import json

import phantom.app as phantom

import ciscomeraki_consts as consts
from actions import BaseAction


class ClaimDevice(BaseAction):
    """Class to handle the claim device action."""

    def execute(self):
        """Execute the claim device action.

        Returns:
            bool: Success/failure
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("claim_device"))

        # Validate required parameters
        organization_id = self._param.get("organization_id")
        serials = self._param.get("serials")

        if not organization_id:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_REQUIRED_PARAM.format(key="organization_id"))

        if not serials:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_REQUIRED_PARAM.format(key="serials"))

        # Convert serials string to list if needed
        if isinstance(serials, str):
            try:
                serials = json.loads(serials)
            except json.JSONDecodeError:
                # If not JSON, split by comma
                serials = [s.strip() for s in serials.split(",")]

        # Make REST call
        ret_val, response = self._connector._utils._make_rest_call(
            endpoint=consts.CLAIM_DEVICES.format(organization_id=organization_id),
            action_result=self._action_result,
            method="post",
            json={"serials": serials},
        )

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        # Process response
        self._action_result.add_data({"organization_id": organization_id, "serials": serials, "claimed": True})

        summary = {"total_devices_claimed": len(serials)}
        self._action_result.update_summary(summary)

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_SUCCESS_RESPONSE.format(
                action=" ".join([i.capitalize() if idx > 0 else i for idx, i in enumerate(self._connector.get_action_identifier().split("_"))])
            ),
        )
