# File: test_rsasecureidam_test_connectivity.py
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


@patch("rsasecureidam_utils._start_connection")
class TestConnectivityAction(unittest.TestCase):
    """Class to test the Test Connectivity action."""

    def setUp(self):
        self.connector = RsaSecureidAM()
        self.test_json = dict(rsasecureidam_config.TEST_JSON)
        self.test_json.update({"action": "test connectivity", "identifier": "test_connectivity"})

        return super().setUp()

    def test_connectivity_pass(self, mock_get):
        """
        Test the valid case for the test connectivity action.
        """

        mock_get.return_value.ret_val = True
        mock_get.return_value.response = "SSH connection successful"

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

    def test_connectivity_invalid_base_url_fail(self, mock_get):
        """
        Test the invalid case for the test connectivity action.
        """

        mock_get.return_value.ret_val = False
        mock_get.return_value.response = "SSH connection attempt failed. Please enter valid values for asset parameters"

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
