# File: cofensevision_update_ioc.py
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


class UpdateIocAction(BaseAction):
    """Class to handle update ioc action."""

    def execute(self):
        """Execute the update ioc action."""
        # Validate the date
        expires_at = self._param["expires_at"]
        status, expires_at = self._connector.util.parse_date_string(expires_at)
        if phantom.is_fail(status):
            return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("expires_at"))

        # Construct the body
        data = {"data": {"type": "ioc", "metadata": {"quarantine": {"expires_at": expires_at}}}}

        endpoint = f"{consts.VISION_ENDPOINT_IOC}/{self._param['id']}"
        status, response = self._connector.util.make_rest_call_helper(endpoint, self._action_result, method="put", json=data)
        if phantom.is_fail(status):
            return self._action_result.get_status()

        self._action_result.add_data(response.get("data", {}))
        return self._action_result.set_status(phantom.APP_SUCCESS, consts.VISION_UPDATE_IOC_SUCCESS)
