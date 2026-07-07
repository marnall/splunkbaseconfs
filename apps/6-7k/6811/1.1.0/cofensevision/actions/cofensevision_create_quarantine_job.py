# File: cofensevision_create_quarantine_job.py
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


class CreateQuarantineJobAction(BaseAction):
    """Class to handle create quarantine job action."""

    def execute(self):
        """Execute the create quarantine job action."""
        quarantine_emails = self._param["quarantine_emails"]

        emails = list()
        email_list = self._connector.util.split_value_list(quarantine_emails)
        if not email_list:
            return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("quarantine_emails"))
        for email in email_list:
            values = self._connector.util.split_value_list(email, ":")
            if len(values) < 2:
                return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("quarantine_emails"))
            for message_id in values[1:]:
                emails.append({"internetMessageId": message_id, "recipientAddress": values[0]})
        ret_val, response = self._connector.util.make_rest_call_helper(
            consts.VISION_ENDPOINT_QUARANTINE_JOBS, self._action_result, method="post", json={"quarantineEmails": emails}
        )

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        self._action_result.add_data(response)

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.VISION_SUCCESS_CREATE_QUARANTINE_JOB)
