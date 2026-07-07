# File: cofensevision_test_connectivity.py
#
# Copyright (c) 2023-2026 Cofense
#
# This unpublished material is proprietary to Cofense.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Cofense.
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

import cofensevision_consts as consts
from actions import BaseAction


class TestConnectivityAction(BaseAction):
    """Class to handle test connectivity action."""

    def execute(self):
        """Execute the test connectivity action."""
        # Connect to the health check endpoint to check the server status
        self._connector.save_progress("Connecting to the endpoint")
        ret_val, response = self._connector.util.make_rest_call(consts.VISION_ENDPOINT_TEST_CONNECTIVITY, self._action_result, headers={})
        if phantom.is_fail(ret_val):
            self._connector.save_progress(consts.VISION_ERROR_SYSTEM_HEALTH)
            self._connector.save_progress(consts.VISION_ERROR_TEST_CONNECTIVITY)
            return self._action_result.get_status()

        if not response:
            self._connector.save_progress(consts.VISION_ERROR_SYSTEM_HEALTH)
            self._connector.save_progress(consts.VISION_ERROR_ACTION_EMPTY_RESPONSE)
            return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_ACTION_EMPTY_RESPONSE)

        if response.get("status", "") != "UP":
            self._connector.save_progress(consts.VISION_ERROR_TEST_CONNECTIVITY)
            return self._action_result.set_status(
                phantom.APP_ERROR, consts.VISION_ERROR_TEST_CONNECTIVITY_INVALID_STATUS.format(response.get("status", ""))
            )

        # For test connectivity action, always generate a new access token. Ignore the state file.
        self._connector.save_progress(consts.VISION_SUCCESS_SYSTEM_HEALTH)
        self._connector.save_progress("Generating new access token")
        ret_val = self._connector.util.generate_token(self._action_result)
        if phantom.is_fail(ret_val):
            self._connector.save_progress(consts.VISION_ERROR_TEST_CONNECTIVITY)
            return self._action_result.get_status()

        self._connector.save_progress(consts.VISION_SUCCESS_TEST_CONNECTIVITY)
        return self._action_result.set_status(phantom.APP_SUCCESS)
