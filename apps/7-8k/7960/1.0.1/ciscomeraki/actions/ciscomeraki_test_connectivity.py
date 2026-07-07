#!/usr/bin/python
# File: ciscomeraki_test_connectivity.py
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


class TestConnectivity(BaseAction):
    """Class to handle test connectivity action."""

    def execute(self):
        """Execute test connectivity action.

        Returns:
            bool: Success/failure
        """
        self._connector.save_progress(consts.TEST_CONNECTIVITY_START_MSG.format("Cisco Meraki"))
        # self._action_result = self._connector.add_action_result(ActionResult(dict()))

        # Make a REST call to /organizations to verify API access
        # ret_val, response = self._connector._utils._make_rest_call(LIST_ORGANIZATIONS, "get")
        ret_val = self._connector._auth.validate_credentials(self._action_result)
        # ret_val, response = self._connector._utils._make_rest_call(LIST_ORGANIZATIONS, self._action_result, method="get")
        if phantom.is_fail(ret_val):
            self._connector.save_progress(consts.ERROR_TEST_CONNECTIVITY)
            return self._action_result.get_status()

        self._connector.save_progress(consts.SUCCESS_TEST_CONNECTIVITY)
        return self._action_result.set_status(phantom.APP_SUCCESS)
