# File: test_dataminrpulse_test_connectivity_v4.py
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


class TestConnectivityActionV4(unittest.TestCase):
    """Class to test the Test Connectivity action for v4 API."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = DataminrPulseConnector()
        self.test_json = dict(dataminrpulse_config.TEST_JSON_V4)
        self.test_json.update({"action": "test connectivity", "identifier": "test_connectivity"})

        return super().setUp()

    @patch("dataminrpulse_utils.requests.post")
    def test_connectivity_v4_pass(self, mock_post):
        """
        Test the valid case for the test connectivity action with v4 API.

        Patch the post() to return valid token.
        """
        dataminrpulse_config.v4_set_state_file()

        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = dataminrpulse_config.V4_DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"dmaToken": "dummy_token", "expire": "expire"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")

        # Verify v4 API token endpoint is called
        mock_post.assert_called_with(
            "https://api.dataminr.com/auth/v1/token",
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            headers=dataminrpulse_config.V4_TOKEN_HEADER,
            params=None,
            verify=False,
            data=dataminrpulse_config.V4_TOKEN_DATA,
        )

    @patch("dataminrpulse_utils.requests.post")
    def test_connectivity_v4_fail_unauthorized(self, mock_post):
        """Test the fail case for the test connectivity action with v4 API - unauthorized error."""
        dataminrpulse_config.v4_set_state_file()

        mock_post.return_value.status_code = 401
        mock_post.return_value.headers = dataminrpulse_config.V4_DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"error": "invalid_client", "error_description": "Invalid client credentials"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("invalid_client", ret_val["result_data"][0]["message"])

    @patch("dataminrpulse_utils.requests.post")
    def test_connectivity_v4_fail_bad_request(self, mock_post):
        """Test the fail case for the test connectivity action with v4 API - bad request error."""
        dataminrpulse_config.v4_set_state_file()

        mock_post.return_value.status_code = 400
        mock_post.return_value.headers = dataminrpulse_config.V4_DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"error": "invalid_request", "error_description": "Missing required parameter"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")


if __name__ == "__main__":
    unittest.main()
