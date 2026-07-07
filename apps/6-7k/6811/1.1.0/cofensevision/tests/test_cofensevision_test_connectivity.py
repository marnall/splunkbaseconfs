# File: test_cofensevision_test_connectivity.py
#
# Copyright (c) 2023-2026 Cofense
#
# This unpublished material is proprietary to Cofense.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Cofense.
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

import cofensevision_consts as consts
from cofensevision_connector import CofenseVisionConnector
from tests import cofensevision_config


class TestConnectivityAction(unittest.TestCase):
    """Class to test the Test Connectivity action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "test connectivity", "identifier": "test_connectivity"})

        return super().setUp()

    @patch("cofensevision_utils.requests.post")
    @patch("cofensevision_utils.requests.get")
    def test_connectivity_pass(self, mock_get, mock_post):
        """
        Test the valid case for the test connectivity action.

        Patch the get() to return UP status and post() to return valid token.
        """
        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"access_token": "dummy_token"}

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"status": "UP"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_TEST_CONNECTIVITY}",
            headers={},
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_TOKEN}",
            headers=cofensevision_config.TOKEN_HEADER,
            data=cofensevision_config.TOKEN_DATA,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )

    @patch("cofensevision_utils.requests.get")
    def test_connectivity_instance_down_fail(self, mock_get):
        """
        Test the fail case for the test connectivity action.

        Patch the get() to return DOWN status and post() to return valid token.
        """
        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"status": "DOWN"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_TEST_CONNECTIVITY}",
            headers={},
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )

    @patch("cofensevision_utils.requests.post")
    @patch("cofensevision_utils.requests.get")
    def test_connectivity_token_bad_credentials_fail(self, mock_get, mock_post):
        """
        Test the fail case for the test connectivity action.

        Patch the get() to return valid response.
        Patch the post() to return authentication error.
        """
        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"status": "UP"}

        mock_post.return_value.status_code = 401
        mock_post.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"error": "unauthorized", "error_description": "Bad credentials"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_TEST_CONNECTIVITY}",
            headers={},
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_TOKEN}",
            headers=cofensevision_config.TOKEN_HEADER,
            data=cofensevision_config.TOKEN_DATA,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )

    @patch("cofensevision_utils.requests.get")
    def test_connectivity_health_check_fail(self, mock_get):
        """
        Tests the fail case for the test connectivity action.

        Patches the get() to return server error.
        """
        mock_get.return_value.status_code = 500
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"error": "Internal server error"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_TEST_CONNECTIVITY}",
            headers={},
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )

    @patch("cofensevision_utils.requests.get")
    def test_connectivity_no_content_fail(self, mock_get):
        """
        Tests the fail case for the test connectivity action.

        Patches the get() to return no content.
        """
        mock_get.return_value.status_code = 204
        mock_get.return_value.text = ""

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_TEST_CONNECTIVITY}",
            headers={},
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )

    @patch("cofensevision_utils.requests.post")
    @patch("cofensevision_utils.requests.get")
    def test_connectivity_key_error_fail(self, mock_get, mock_post):
        """
        Test the fail case for the test connectivity action.

        Patch the get() to return valid response.
        Patch the post() to return response without the access_token key.
        """
        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"status": "UP"}

        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"message": "token generated"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_TEST_CONNECTIVITY}",
            headers={},
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_TOKEN}",
            headers=cofensevision_config.TOKEN_HEADER,
            data=cofensevision_config.TOKEN_DATA,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )
