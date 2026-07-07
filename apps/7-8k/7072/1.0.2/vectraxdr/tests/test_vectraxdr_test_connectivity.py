"""Unit test file for test connectivity."""
# File: test_vectraxdr_test_connectivity.py
#
# Copyright (c) 2023-2025 Vectra
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

import vectraxdr_consts as consts
from vectraxdr_connector import VectraxdrConnector

from . import vectra_responses, vectraxdr_config


class TestConnectivityAction(unittest.TestCase):
    """Class to test the Test Connectivity action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = VectraxdrConnector()
        self.test_json = dict(vectraxdr_config.TEST_JSON)
        self.test_json.update({"action": "test connectivity", "identifier": "test_connectivity"})

        return super().setUp()

    @patch("vectraxdr_utils.requests.post")
    @patch("vectraxdr_utils.requests.get")
    def test_connectivity_pass(self, mock_get, mock_post):
        """
        Test the valid case for the test connectivity action.

        Patch the post() to return valid token.
        """
        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = vectra_responses.GET_REFRESH_TOKEN
        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = vectra_responses.GET_ENTITY

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")

        mock_post.assert_called_with(
            f"{vectraxdr_config.DUMMY_BASE_URL}{consts.VECTRA_ENDPOINT_TOKEN}",
            headers=vectraxdr_config.TOKEN_HEADER,
            data={"grant_type": "client_credentials"},
            auth=("<client_id>", "<dummy_client_secret>"),
            timeout=consts.VECTRA_REQUEST_TIMEOUT,
            params=None,
            verify=False,
        )

        mock_get.assert_called_with(
            f"{vectraxdr_config.DUMMY_BASE_URL}{consts.VECTRA_API_VERSION}{consts.VECTRA_LIST_ENTITIES}",
            headers=vectraxdr_config.ACTION_HEADER,
            params={"page_size": 1},
            timeout=consts.VECTRA_REQUEST_TIMEOUT,
            verify=False,
        )

    @patch("vectraxdr_utils.requests.post")
    def test_connectivity_token_bad_credentials_fail(self, mock_post):
        """
        Test the fail case for the test connectivity action.

        Patch the post() to return authentication error.
        """
        mock_post.return_value.status_code = 401
        mock_post.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"error": "Authentication Error. Please try reauthenticating using API client credentials."}
        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")

        mock_post.assert_called_with(
            f"{vectraxdr_config.DUMMY_BASE_URL}{consts.VECTRA_ENDPOINT_TOKEN}",
            headers=vectraxdr_config.TOKEN_HEADER,
            data={"grant_type": "client_credentials"},
            auth=("<client_id>", "<dummy_client_secret>"),
            timeout=consts.VECTRA_REQUEST_TIMEOUT,
            params=None,
            verify=False,
        )
