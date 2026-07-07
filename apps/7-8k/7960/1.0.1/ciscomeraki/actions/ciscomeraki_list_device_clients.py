#!/usr/bin/python
# File: ciscomeraki_list_device_clients.py
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


class ListDeviceClients(BaseAction):
    """Class to handle the list device clients action."""

    def execute(self):
        """Execute the list device clients action.

        Returns:
            bool: Success/failure
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("list_device_clients"))

        # Validate required parameters
        serial = self._param.get("serial")
        if not serial:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_REQUIRED_PARAM.format(key="serial"))

        # Validate timespan if provided
        timespan = self._param.get("timespan")
        if timespan:
            try:
                timespan = int(timespan)
                if not 300 <= timespan <= 2592000:  # 5 minutes to 30 days
                    return self._action_result.set_status(phantom.APP_ERROR, "Parameter 'timespan' must be between 300 and 2592000 seconds")
            except ValueError:
                return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_INT_PARAM.format(key="timespan"))

        # Prepare parameters
        params = {}
        if timespan:
            params["timespan"] = timespan

        # Make REST call
        ret_val, response = self._connector._utils._make_rest_call(
            endpoint=consts.LIST_DEVICE_CLIENTS.format(serial=serial), action_result=self._action_result, method="get", params=params
        )

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        # Process response
        for client in response:
            self._action_result.add_data(client)

        summary = {"total_clients": len(response)}
        self._action_result.update_summary(summary)

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_SUCCESS_RESPONSE.format(
                action=" ".join([i.capitalize() if idx > 0 else i for idx, i in enumerate(self._connector.get_action_identifier().split("_"))])
            ),
        )
