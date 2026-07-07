# File: test_rsasecureidam_list_tokens.py
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

# import rsasecureidam_consts as consts
from rsasecureidam_connector import RsaSecureidAM
from tests import rsasecureidam_config


# from unittest.mock import patch


@patch("rsasecureidam_utils._send_command")
class ListTokensAction(unittest.TestCase):
    def setUp(self):
        self._connector = RsaSecureidAM()
        self.test_json = dict(rsasecureidam_config.TEST_JSON)
        self.test_json.update({"action": "list tokens", "identifier": "list_tokens"})

        return super().setUp()

    def test_list_tokens_assigned_tokens_valid(self, mock_get):
        """
        Test the valid case for the list token action.
        """

        mock_get.return_value.ret_val = True
        mock_get.return_value.response = ["list_of_tokens"]

        self.test_json["parameters"] = [{"list_only_assigned_tokens": True}]

        ret_val = self._connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

    def test_list_tokens_all_tokens_valid(self, mock_get):
        """
        Test the valid case for the list token action.
        """

        mock_get.return_value.ret_val = True
        mock_get.return_value.response = ["list_of_tokens"]

        self.test_json["parameters"] = [{"list_only_assigned_tokens": False}]

        ret_val = self._connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

    def test_list_tokens_invalid(self, mock_get):
        """
        Test the valid case for the list token action.
        """

        mock_get.return_value.ret_val = False
        mock_get.return_value.response = None

        self.test_json["parameters"] = [{"list_only_assigned_tokens": False}]

        ret_val = self._connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
