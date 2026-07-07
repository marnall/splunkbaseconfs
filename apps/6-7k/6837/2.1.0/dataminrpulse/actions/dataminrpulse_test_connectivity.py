# File: dataminrpulse_test_connectivity.py
#
# Copyright (c) 2023-2026 Dataminr
#
# This unpublished material is proprietary to Dataminr.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Dataminr.
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
import requests

import dataminrpulse_consts as consts
from actions import BaseAction


class TestConnectivityAction(BaseAction):
    """Class to handle test connectivity action."""

    def execute(self):
        """Execute the test connectivity action."""
        # Add severity
        base_url = self._connector._get_phantom_base_url()
        url = f"{base_url}{consts.DATAMINRPULSE_SEVERITY_ENDPOINT}"

        _ = requests.request("POST", url, data=json.dumps(consts.DATAMINRPULSE_SEVERITY_PAYLOAD), verify=False)  # nosemgrep

        self._connector.save_progress("Connecting to the endpoint")

        # For test connectivity action, always generate a new dmaToken. Ignore the state file.
        self._connector.save_progress("Generating new access token")
        ret_val = self._connector.util._generate_token(self._action_result)
        if phantom.is_fail(ret_val):
            self._connector.save_progress(consts.DATAMINRPULSE_ERROR_TEST_CONNECTIVITY)
            return self._action_result.get_status()

        # Auth endpoints return 200 and issue tokens even when v3 credentials are used with v4 API (and vice versa).
        # We call the lists API to validate token access until the auth endpoints correctly return 401/403 for wrong-version credentials.
        if self._connector.util._api_version == "v4":
            endpoint = consts.DATAMINRPULSE_GET_LISTS_V4
        elif self._connector.util._api_version == "v3":
            endpoint = consts.DATAMINRPULSE_GET_LISTS

        ret_val, response = self._connector.util._make_rest_call_helper(endpoint, self._action_result)
        if phantom.is_fail(ret_val):
            self._action_result.append_to_message(consts.DATAMINR_V3_V4_API_ERROR_MSG)
            return self._action_result.get_status()

        # Reset values of from and to on running Test connectivity
        self._connector.state.pop(consts.DATAMINRPULSE_STATE_FROM_VALUE, None)
        self._connector.state.pop(consts.DATAMINRPULSE_STATE_TO_VALUE, None)
        self._connector.state.pop(consts.DATAMINRPULSE_STATE_LIST_ID_VALUE, None)
        self._connector.state.pop(consts.DATAMINRPULSE_STATE_QUERY_VALUE, None)

        self._connector.save_progress(consts.DATAMINRPULSE_SUCCESS_TEST_CONNECTIVITY)
        return self._action_result.set_status(phantom.APP_SUCCESS)
