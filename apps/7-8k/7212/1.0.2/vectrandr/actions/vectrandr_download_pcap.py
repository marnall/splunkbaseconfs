# File: vectrandr_download_pcap.py
#
# Copyright (c) 2024-2025 Vectra
#
# This unpublished material is proprietary to Vectra.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Vectra.
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
import phantom.rules as phantom_rules

import vectrandr_consts as consts
from actions import BaseAction


class DownloadPCAPAction(BaseAction):
    """Class to handle download pcap action."""

    def execute(self):
        """Execute the download pcap action."""
        vault_id = None

        ret_val, detection_id = self._connector.util._validate_integer(self._action_result, self._param["detection_id"], "detection_id", True)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_DOWNLOAD_PCAP_ENDPOINT.format(detection_id=detection_id)}"

        ret_val, _ = self._connector.util._make_rest_call_helper(url, self._action_result, is_stream_download=True)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        file_path = self._connector.util.file_path
        file_name = file_path.split("/")[-1] if file_path else None
        if file_path:
            try:
                ret_val, message, vault_id = phantom_rules.vault_add(
                    container=self._connector.get_container_id(), file_location=file_path, file_name=file_name
                )
                if phantom.is_fail(ret_val):
                    return self._action_result.set_status(phantom.APP_ERROR, message)
            except Exception as e:
                return self._action_result.set_status(
                    phantom.APP_ERROR,
                    f"Unable to store file in Splunk SOAR's vault. Error: {self._connector.util._get_error_message_from_exception(e)}",
                )

        # Cleanup temp dir
        try:
            self._connector.debug_print("Deleting temporary directory")
            if os.path.exists(file_path):
                os.rmdir(file_path)
        except Exception as e:
            self._connector.debug_print(f"Unable to delete the temporary directory: {self._connector.util._get_error_message_from_exception(e)}")

        self._action_result.add_data({"vault_id": vault_id, "file_name": file_name})

        return self._action_result.set_status(phantom.APP_SUCCESS, "Successfully downloaded packets")
