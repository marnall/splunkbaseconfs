#!/usr/bin/python
# File: ciscomeraki_list_organizations.py
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


class ListOrganizations(BaseAction):
    """Class to handle the list organizations action."""

    def execute(self):
        """Execute the list organizations action.

        Returns:
            bool: Success/failure
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("list_organizations"))

        # Use paginator to get all organizations with max limit of 1000 per page
        ret_val, response = self._connector._utils._paginator(
            action_result=self._action_result,
            endpoint=consts.LIST_ORGANIZATIONS,
            limit=1000,  # Meraki API's maximum limit
        )

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        # Process each organization in the response
        for org in response:
            self._action_result.add_data(org)

        # Add summary
        summary = {"total_organizations": len(response)}
        self._action_result.update_summary(summary)

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_SUCCESS_RESPONSE.format(
                action=" ".join([i.capitalize() if idx > 0 else i for idx, i in enumerate(self._connector.get_action_identifier().split("_"))])
            ),
        )
