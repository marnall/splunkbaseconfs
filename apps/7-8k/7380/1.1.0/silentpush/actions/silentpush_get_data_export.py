# File: silentpush_get_data_export.py
#
# Copyright (c) 2024-2025 Splunk Inc.
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

from actions import BaseAction
from silentpush_consts import EXECUTION_START_MESSAGE


class GetDataExport(BaseAction):
    """Class to handle get data export action."""

    def execute(self):
        """Execute get data export action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(EXECUTION_START_MESSAGE.format("get_data_export"))

        ret_val, response = self.__make_rest_call(url=self._param["feed_url"], method="get")

        return self.__handle_response(ret_val, response)

    def __make_rest_call(self, url, method):
        """Invoke API"""
        args = {
            "endpoint": url,
            "action_result": self._action_result,
            "method": method.lower(),
        }
        self._connector.debug_print(f"args: {args}")

        args["error_path"] = "errors.0.message"

        return self._connector.util.make_rest_call(**args)

    def __handle_response(self, ret_val, response):
        """Process response received from the third party API"""
        if phantom.is_fail(ret_val):
            self._action_result.add_data(response)
        else:
            self._action_result.add_data({"vault_id": response})
        return self._action_result.get_status()
