# File: dataminrpulse_get_alert_details.py
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


class GetAlertDetailsAction(BaseAction):
    """Class to handle get alert details action."""

    def execute(self):
        """Execute the get alert details action."""
        alert_id = self._param.get("alert_id")
        artifact_id = self._param.get("artifact_id")
        self._action_result.update_summary({"api_version_used": self._connector.util._api_version})
        if self._connector.util._api_version == "v3":
            return self._action_result.set_status(phantom.APP_ERROR, "Please use the latest v4 API version to perform this action")

        if alert_id:
            ret_val, response = self._connector.util._make_rest_call_helper(
                consts.DATAMINRPULSE_GET_ALERT_V4.format(alert_id=alert_id), self._action_result
            )
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            if response:
                # Handle metadata field as a list to maintain consistency with the response received when fetching from artifact ID
                if response.get("metadata"):
                    response["metadata"] = [response["metadata"]]
                self._action_result.add_data(response)
            else:
                return self._action_result.set_status(phantom.APP_ERROR, "No alert details found")

        elif artifact_id:
            base_url = self._connector._get_phantom_base_url()
            url = consts.DATAMINRPULSE_GET_ARTIFACT_DETAILS.format(instance=base_url, artifact_id=artifact_id)
            ret_val, response = self._connector.util._make_rest_call(url, self._action_result)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()
            response = response.get("cef", {})
            if response:
                self._action_result.add_data(response)
            else:
                return self._action_result.set_status(phantom.APP_ERROR, "No alert details found")
        else:
            return self._action_result.set_status(phantom.APP_ERROR, "Please provide either artifact_id or alert_id")

        return self._action_result.set_status(phantom.APP_SUCCESS, "Successfully fetched alert details")
