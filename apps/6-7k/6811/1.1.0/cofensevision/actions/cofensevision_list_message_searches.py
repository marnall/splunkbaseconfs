# File: cofensevision_list_message_searches.py
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


class ListMessageSearchesAction(BaseAction):
    """Class to handle list message searches action."""

    def execute(self):
        """Execute the list message searches action."""
        page = self._param.get("page", consts.VISION_DEFAULT_PAGE_NUMBER)
        ret_val, page = self._connector.util.validate_integer(self._action_result, page, "page", True)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        size = self._param.get("size", consts.VISION_DEFAULT_PAGE_SIZE)
        ret_val, size = self._connector.util.validate_integer(self._action_result, size, "size", max_value=consts.VISION_MAX_PAGE_SIZE)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        # Prepare query parameters
        params = {
            "page": page,
            "size": size,
        }
        ret_val, sort = self._connector.util.validate_sort_param(self._param.get("sort"))
        if phantom.is_fail(ret_val):
            return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("sort"))
        if sort:
            params["sort"] = sort

        ret_val, response = self._connector.util.make_rest_call_helper(
            consts.VISION_ENDPOINT_MESSAGE_SEARCH, self._action_result, method="get", params=params
        )
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        if not response:
            return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_ACTION_EMPTY_RESPONSE)

        # Add data into action result object
        for data in response.get("searches", []):
            self._action_result.add_data(data)

        # Add summary
        self._action_result.update_summary({"total_message_searches": self._action_result.get_data_size()})

        return self._action_result.set_status(phantom.APP_SUCCESS)
