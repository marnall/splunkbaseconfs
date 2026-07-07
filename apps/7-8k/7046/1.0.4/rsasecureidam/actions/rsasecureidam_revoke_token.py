# File: rsasecureidam_revoke_token.py
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
from rsasecureidam_consts import RSA_HEADER_LINE, RSA_REVOKE_TOKEN_QUERY, RSA_TOKEN_REVOKE_MESSAGE


class RevokeToken(BaseAction):
    def execute(self):
        self._connector.save_progress(f"In action handler for: {self._connector.get_action_identifier()}")

        token = self._param["token_serial"]
        data = RSA_HEADER_LINE
        data += RSA_REVOKE_TOKEN_QUERY.format(token=token)
        ret_val, response = self.utils._send_command(self._action_result, data)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        return self._action_result.set_status(phantom.APP_SUCCESS, RSA_TOKEN_REVOKE_MESSAGE)
