# File: cofensevision_get_last_ioc.py
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


class GetLastIocAction(BaseAction):
    """Class to handle get last IOC action."""

    def execute(self):
        """Execute the get last IOC action."""
        ioc_source = self._param[consts.VISION_PARAM_IOC_SOURCE]

        headers = {}
        headers[consts.VISION_IOC_SOURCE_HEADER] = ioc_source

        # Connect to the ioc endpoint to get the last updated IOC from the local IOC Repository
        ret_val, response = self._connector.util.make_rest_call_helper(consts.VISION_ENDPOINT_IOC_LAST, self._action_result, headers=headers)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        if not response or not response.get("data"):
            return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_ACTION_EMPTY_RESPONSE)

        self._action_result.add_data(response["data"])
        self._action_result.update_summary({"ioc_id ": response["data"]["id"]})

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.VISION_SUCCESS_GET_LAST_IOC_ACTION.format(response["data"]["id"]))
