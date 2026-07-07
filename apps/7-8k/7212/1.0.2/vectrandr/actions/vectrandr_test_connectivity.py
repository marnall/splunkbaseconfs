# File: vectrandr_test_connectivity.py
#
# Copyright (c) 2024-2025 Vectra
#
# This unpublished material is proprietary to Vectra.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Vectra.
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

import vectrandr_consts as consts
from actions import BaseAction


class TestConnectivityAction(BaseAction):
    """Class to handle test connectivity action."""

    def execute(self):
        """Execute the test connectivity action."""
        self._connector.util._create_critical_severity()
        self._connector.save_progress("Getting list of entities")
        url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_TEST_CONNECTIVITY_ENDPOINT}"
        ret_val, _ = self._connector.util._make_rest_call_helper(url, self._action_result, params={"page_size": 1})
        if phantom.is_fail(ret_val):
            self._connector.save_progress(consts.VECTRA_ERROR_TEST_CONNECTIVITY)
            return self._action_result.get_status()

        self._connector.save_progress(consts.VECTRA_SUCCESS_TEST_CONNECTIVITY)

        return self._action_result.set_status(phantom.APP_SUCCESS)
