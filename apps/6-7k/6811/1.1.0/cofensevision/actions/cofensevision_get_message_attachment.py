# File: cofensevision_get_message_attachment.py
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

import os

import phantom.app as phantom

import cofensevision_consts as consts
from actions import BaseAction


class GetMessageAttachmentAction(BaseAction):
    """Class to handle get message attachment action."""

    def execute(self):
        """Execute the get message attachment action."""
        md5 = self._param.get("md5")
        sha256 = self._param.get("sha256")

        if not (md5 or sha256):
            return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_NO_HASH_PARAMETER)

        # Check the existence of extension in the filename
        filename = self._param["filename"]
        _, ext = os.path.splitext(filename)
        if not ext or ext == ".":
            return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_FILENAME)
        self._connector.util.filename = filename

        # Create a params dict to pass in the request
        params = dict()

        if md5:
            params.update({"md5": md5})

        if sha256:
            params.update({"sha256": sha256})

        # Make rest call to fetch the file
        status, vault_info = self._connector.util.make_rest_call_helper(
            consts.VISION_ENDPOINT_ATTACHMENT, self._action_result, params=params, stream=True
        )

        if phantom.is_fail(status):
            return self._action_result.get_status()

        self._action_result.add_data(vault_info)
        self._action_result.update_summary({"vault_id": vault_info["vault_id"]})

        return self._action_result.set_status(phantom.APP_SUCCESS)
