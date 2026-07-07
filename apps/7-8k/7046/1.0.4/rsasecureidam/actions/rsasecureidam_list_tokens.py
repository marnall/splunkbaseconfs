# File: rsasecureidam_list_tokens.py
#
# Copyright (c) 2023-2025 Splunk Inc.
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
from rsasecureidam_consts import RSA_LIST_TOKEN_HEADER_LINE, RSA_LIST_TOKENS_QUERY


class ListTokens(BaseAction):
    def execute(self):
        self._connector.save_progress(f"In action handler for: {self._connector.get_action_identifier()}")

        list_only_assigned_tokens = self._param.get("list_only_assigned_tokens", True)
        data = RSA_LIST_TOKEN_HEADER_LINE
        if list_only_assigned_tokens:
            data += RSA_LIST_TOKENS_QUERY.format(compare_field="1", compare_type="1")
        else:
            data += RSA_LIST_TOKENS_QUERY.format(compare_field="0", compare_type="0")
        ret_val, tokens = self.utils._send_command(self._action_result, data)

        if phantom.is_fail(ret_val):
            self._connector.save_progress("Error occured while fetching list of tokens.")
            return self._action_result.get_status()

        for token in tokens:
            self._action_result.add_data(token)

        self._action_result.update_summary({"total_tokens": len(tokens)})

        return self._action_result.set_status(phantom.APP_SUCCESS)
