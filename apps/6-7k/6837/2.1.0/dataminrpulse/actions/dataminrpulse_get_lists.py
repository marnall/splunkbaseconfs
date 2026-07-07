# File: dataminrpulse_get_lists.py
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


import phantom.app as phantom

import dataminrpulse_consts as consts
from actions import BaseAction


class GetListsAction(BaseAction):
    """Class to handle get lists action."""

    def execute(self):
        """Execute the get lists action."""
        self._action_result.update_summary({"api_version_used": self._connector.util._api_version})

        if self._connector.util._api_version == "v4":
            endpoint = consts.DATAMINRPULSE_GET_LISTS_V4
        elif self._connector.util._api_version == "v3":
            endpoint = consts.DATAMINRPULSE_GET_LISTS

        ret_val, response = self._connector.util._make_rest_call_helper(endpoint, self._action_result)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        if self._connector.util._api_version == "v4":
            resp_data = response.get("lists", {})
        elif self._connector.util._api_version == "v3":
            resp_data = response.get("watchlists", {})

        for _, watchlist_type in resp_data.items():
            for list_data in watchlist_type:
                self._action_result.add_data(list_data)

        self._action_result.update_summary({"total_watchlists": self._action_result.get_data_size()})

        return self._action_result.set_status(phantom.APP_SUCCESS)
