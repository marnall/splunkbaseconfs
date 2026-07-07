# File: cofensevision_download_logs.py
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

from datetime import datetime

import phantom.app as phantom

import cofensevision_consts as consts
from actions import BaseAction


class DownloadLogsAction(BaseAction):
    """Class to handle download logs action."""

    def execute(self):
        """Execute the download logs action."""
        self._connector.util.filename = f"logfile_{datetime.utcnow().strftime('%Y-%m-%d_%H:%M:%S.%f')}.zip"
        # Make rest call to fetch the file
        status, vault_info = self._connector.util.make_rest_call_helper(consts.VISION_ENDPOINT_DOWNLOAD_LOGS, self._action_result, stream=True)

        if phantom.is_fail(status):
            return self._action_result.get_status()

        self._action_result.add_data(vault_info)
        self._action_result.update_summary({"vault_id": vault_info["vault_id"]})

        return self._action_result.set_status(phantom.APP_SUCCESS)
