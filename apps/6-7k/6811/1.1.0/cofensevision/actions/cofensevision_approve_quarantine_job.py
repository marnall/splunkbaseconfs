# File: cofensevision_approve_quarantine_job.py
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


class ApproveQuarantineJobAction(BaseAction):
    """Class to handle approve quarantine job action."""

    def execute(self):
        """Execute the approve quarantine job action."""
        ret_val, job_id = self._connector.util.validate_integer(
            self._action_result, self._param[consts.VISION_PARAM_JOB_ID], consts.VISION_PARAM_JOB_ID
        )
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        params = {}
        if "message_count" in self._param:
            ret_val, message_count = self._connector.util.validate_integer(
                self._action_result, self._param.get("message_count"), "message count"
            )
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            params = {"messageCount": message_count}

        endpoint = consts.VISION_ENDPOINT_APPROVE_QUARANTINE_JOBS.format(job_id=job_id)
        # Connect to the quarantine job endpoint to approve the given job.
        ret_val, _ = self._connector.util.make_rest_call_helper(endpoint, self._action_result, method="put", params=params)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.VISION_SUCCESS_APPROVE_JOB_ACTION)
