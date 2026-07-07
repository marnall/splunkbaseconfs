# File: cofensevision_get_message_search.py
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


class GetMessageSearchAction(BaseAction):
    """Class to handle get message search action."""

    def execute(self):
        """Execute the get message search action."""
        ret_val, search_id = self._connector.util.validate_integer(self._action_result, self._param["id"], "id")
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        # Connect to message search endpoint to get the specified message search
        endpoint = f"{consts.VISION_ENDPOINT_MESSAGE_SEARCH}/{search_id}"
        ret_val, response = self._connector.util.make_rest_call_helper(endpoint, self._action_result)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        self._action_result.add_data(response)

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.VISION_SUCCESS_GET_MESSAGE_SEARCH_ACTION)
