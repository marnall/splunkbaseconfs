# File: test_dataminrpulse_get_lists_v4.py
#
# Copyright (c) 2023-2026 Dataminr
#
# This unpublished material is proprietary to Dataminr.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Dataminr.
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

import dataminrpulse_consts as consts
from dataminrpulse_connector import DataminrPulseConnector

from . import dataminrpulse_config


class TestGetListsActionV4(unittest.TestCase):
    """Class to test the get lists action for v4 API."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = DataminrPulseConnector()
        self.test_json = dict(dataminrpulse_config.TEST_JSON_V4)
        self.test_json.update({"action": "get lists", "identifier": "get_lists"})
        # Force v4 API usage
        self.connector._use_v4_api = True
        return super().setUp()

    @patch("dataminrpulse_utils.requests.get")
    def test_get_lists_v4_pass(self, mock_get):
        """Test the valid case for the get lists action with v4 API.

        Token is available in the state file.
        Mock the get() to return the valid response.
        """
        dataminrpulse_config.v4_set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.V4_DEFAULT_HEADERS

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Api version used: v4, Total watchlists: 0")

        # Verify v4 API endpoint is called
        mock_get.assert_called_with(
            f"https://api.dataminr.com/pulse/v1/lists",
            headers={"Authorization": "Bearer <dummy_token>", "X-Application-Name": "splunk_soar"},
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            params=None,
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_lists_v4_empty_response(self, mock_get):
        """Test the case where v4 API returns empty lists."""
        dataminrpulse_config.v4_set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.V4_DEFAULT_HEADERS

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Api version used: v4, Total watchlists: 0")

    @patch("dataminrpulse_utils.requests.get")
    def test_get_lists_v4_fail_unauthorized(self, mock_get):
        """Test the fail case for the get lists action with unauthorized error for v4 API."""
        dataminrpulse_config.v4_set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{}]

        mock_get.return_value.status_code = 401
        mock_get.return_value.headers = dataminrpulse_config.V4_DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"error": "Unauthorized", "message": "Invalid token"}
        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")


if __name__ == "__main__":
    unittest.main()
