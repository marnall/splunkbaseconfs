# File: actions/googlesecops_test_connectivity.py
#
# Copyright (c) 2026 Google LLC
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

import googlesecops_consts as consts
from actions import BaseAction  # pylint: disable=import-error,no-name-in-module


class TestConnectivityAction(BaseAction):
    """Test connectivity action."""

    def execute(self):
        """
        Test the connectivity to Google SecOps.

        Returns:
            int: Status code
        """
        self._connector.save_progress(consts.TEST_CONNECTIVITY_START_MSG)
        self._connector.debug_print("[test_connectivity] Action started")

        try:
            test_url = self._connector.client.base_url

            self._connector.debug_print("[test_connectivity] Making test API call to list rules")
            ret_val, _ = self._connector.utils.make_rest_call(test_url, self._action_result, method="get")

            if phantom.is_fail(ret_val):
                self._connector.save_progress(consts.ERROR_TEST_CONNECTIVITY)
                return self._action_result.get_status()

            self._connector.save_progress(consts.SUCCESS_TEST_CONNECTIVITY)
            return self._action_result.set_status(phantom.APP_SUCCESS)

        except Exception as e:
            error_msg = self._connector.utils._get_error_message_from_exception(e)
            self._connector.save_progress(f"{consts.ERROR_TEST_CONNECTIVITY}: {error_msg}")
            return self._action_result.set_status(phantom.APP_ERROR, error_msg)
