# File: test_vectrandr_test_connectivity.py
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


import json
import unittest
from unittest.mock import patch

import vectrandr_consts as consts
from vectrandr_connector import VectraNDRConnector

from . import vectrandr_config, vectrandr_responses


class TestConnectivityAction(unittest.TestCase):
    """Class to test the Test Connectivity action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = VectraNDRConnector()
        self.test_json = dict(vectrandr_config.TEST_JSON)
        self.test_json.update({"action": "test connectivity", "identifier": "test_connectivity"})

        return super().setUp()

    @patch("vectrandr_utils.VectraNDRUtils._create_critical_severity")
    @patch("vectrandr_utils.requests.get")
    def test_connectivity_pass(self, mock_get, requests_mock):
        """
        Test the valid case for the test connectivity action.

        Patch the post() to return valid token.
        """
        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = vectrandr_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = vectrandr_responses.GET_ENTITY_RESP

        requests_mock.return_value = None

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")

        mock_get.assert_called_with(
            f"{vectrandr_config.DUMMY_BASE_URL}{consts.VECTRA_API_VERSION}{consts.VECTRA_TEST_CONNECTIVITY_ENDPOINT}",
            timeout=consts.VECTRA_REQUEST_TIMEOUT,
            headers=vectrandr_config.ACTION_HEADER,
            params={"page_size": 1},
            verify=False,
            stream=False,
        )

    @patch("vectrandr_utils.VectraNDRUtils._create_critical_severity")
    @patch("vectrandr_utils.requests.get")
    def test_connectivity_token_bad_credentials_fail(self, mock_get, requests_mock):
        """
        Test the fail case for the test connectivity action.

        Patch the post() to return authentication error.
        """
        mock_get.return_value.status_code = 401
        mock_get.return_value.headers = vectrandr_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"detail": "Invalid token."}
        requests_mock.return_value = None

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")

        mock_get.assert_called_with(
            f"{vectrandr_config.DUMMY_BASE_URL}{consts.VECTRA_API_VERSION}{consts.VECTRA_TEST_CONNECTIVITY_ENDPOINT}",
            timeout=consts.VECTRA_REQUEST_TIMEOUT,
            headers=vectrandr_config.ACTION_HEADER,
            params={"page_size": 1},
            verify=False,
            stream=False,
        )
