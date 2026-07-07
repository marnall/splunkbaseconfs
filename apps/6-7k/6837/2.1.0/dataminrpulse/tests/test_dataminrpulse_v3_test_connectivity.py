# File: test_dataminrpulse_test_connectivity.py
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


class TestConnectivityAction(unittest.TestCase):
    """Class to test the Test Connectivity action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = DataminrPulseConnector()
        self.test_json = dict(dataminrpulse_config.TEST_JSON)
        self.test_json.update({"action": "test connectivity", "identifier": "test_connectivity"})

        return super().setUp()

    @patch("dataminrpulse_utils.requests.post")
    def test_connectivity_pass(self, mock_post):
        """
        Test the valid case for the test connectivity action.

        Patch the post() to return valid token.
        """
        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"dmaToken": "dummy_token", "refreshToken": "dummy_refresh_token", "expire": "expire"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_post.assert_called_with(
            f"https://gateway.dataminr.com/auth/2/token",
            headers=dataminrpulse_config.TOKEN_HEADER,
            data=dataminrpulse_config.TOKEN_DATA,
            params=None,
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.post")
    def test_connectivity_token_bad_credentials_fail(self, mock_post):
        """
        Test the fail case for the test connectivity action.

        Patch the post() to return authentication error.
        """
        mock_post.return_value.status_code = 401
        mock_post.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"errors": [{"code": 103, "message": "Authentication error. Invalid token"}]}
        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_post.assert_called_with(
            f"https://gateway.dataminr.com/auth/2/token",
            headers=dataminrpulse_config.TOKEN_HEADER,
            data=dataminrpulse_config.TOKEN_DATA,
            params=None,
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.post")
    def test_connectivity_client_secret_error_fail(self, mock_post):
        """
        Test the fail case for the test connectivity action.

        Patch the post() to return response with incorrect client secret.
        """
        mock_post.return_value.status_code = 401
        mock_post.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"errors": [{"code": 102, "message": "Invalid client Id or client secret"}]}

        self.test_json["config"]["client_secret"] = dataminrpulse_config.CLIENT_SECRET_DUMMY_ENCRYPTED
        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        dataminrpulse_config.TOKEN_DATA["client_secret"] = dataminrpulse_config.CLIENT_DUMMY_ACTUAL
        mock_post.assert_called_with(
            f"https://gateway.dataminr.com/auth/2/token",
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            verify=False,
            params=None,
            data=dataminrpulse_config.TOKEN_DATA,
            headers=dataminrpulse_config.TOKEN_HEADER,
        )

    @patch("dataminrpulse_utils.requests.post")
    def test_connectivity_client_id_error_fail(self, mock_post):
        """
        Test the fail case for the test connectivity action.

        Patch the post() to return response with incorrect client id.
        """
        mock_post.return_value.status_code = 401
        mock_post.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"errors": [{"code": 102, "message": "Invalid client Id or client secret"}]}

        self.test_json["config"]["client_id"] = dataminrpulse_config.CLIENT_DUMMY_ACTUAL
        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        dataminrpulse_config.TOKEN_DATA["client_id"] = dataminrpulse_config.CLIENT_DUMMY_ACTUAL
        mock_post.assert_called_with(
            f"https://gateway.dataminr.com/auth/2/token",
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            verify=False,
            params=None,
            data=dataminrpulse_config.TOKEN_DATA,
            headers=dataminrpulse_config.TOKEN_HEADER,
        )
