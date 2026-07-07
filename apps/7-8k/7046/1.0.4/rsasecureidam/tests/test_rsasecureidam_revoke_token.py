# File: test_rsasecureidam_revoke_token.py
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

import json
import unittest
from unittest.mock import patch

from rsasecureidam_connector import RsaSecureidAM
from tests import rsasecureidam_config


@patch("rsasecureidam_utils._send_command")
class RevokeTokenAction(unittest.TestCase):
    def setUp(self):
        self._connector = RsaSecureidAM()
        self.test_json = dict(rsasecureidam_config.TEST_JSON)
        self.test_json.update({"action": "revoke token", "identifier": "revoke_token"})

        return super().setUp()

    def test_revoke_token_valid(self, mock_get):
        """
        Test the valid case for the revoke token action.
        """

        mock_get.return_value.ret_val = True
        mock_get.return_value.response = None

        self.test_json["parameters"] = [{"token": "001883707613"}]

        ret_val = self._connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        print(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

    def test_revoke_token_invalid(self, mock_get):
        """
        Test the invalid case for the revoke token action.
        """

        mock_get.return_value.ret_val = False
        mock_get.return_value.response = "Error occured. Details:a bytes-like object is required, not 'str'"

        self.test_json["parameters"] = [{"token": "dghghj2"}]

        ret_val = self._connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        print(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
