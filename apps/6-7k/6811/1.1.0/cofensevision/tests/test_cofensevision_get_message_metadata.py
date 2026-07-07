# File: test_cofensevision_get_message_metadata.py
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


OBJECT_NOT_FOUND = {"status": "NOT_FOUND", "message": "Object not found", "details": ["Unable to find the requested object"]}

EMAIL_ADDRESS = "testuser@test.com"
MESSAGE_ID = "<CAFRPxWtuVLQ8OspO8OK6bhcA66ahvjA@mail.test.com>"

VALID_PARAMS = {"internet_message_id": MESSAGE_ID, "recipient_address": EMAIL_ADDRESS}

EXPECTED_PARAMS = {"internetMessageId": MESSAGE_ID, "recipientAddress": EMAIL_ADDRESS}


class TestGetMessageMetadataAction(unittest.TestCase):
    """Class to test the get message metadata action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "get message metadata", "identifier": "get_message_metadata"})
        return super().setUp()

    @patch("cofensevision_utils.requests.get")
    def test_get_message_metadata_pass(self, mock_get):
        """
        Test valid case for get message metadata

        Mock the API response of the server
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [VALID_PARAMS]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"id": 2616086}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_GET_METADATA_SUCCESS)

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE_METADATA}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=cofensevision_config.ACTION_HEADER,
            params=EXPECTED_PARAMS,
        )

    @patch("cofensevision_utils.requests.get")
    def test_get_message_metadata_invalid_id_fail(self, mock_get):
        """
        Test invalid id case for get message metadata

        Mock the API response of the server
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"internet_message_id": "<bhcA66ahvjA@mail.test.com>", "recipient_address": EMAIL_ADDRESS}]

        mock_get.return_value.status_code = 404
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = OBJECT_NOT_FOUND
        mock_get.return_value.text = json.dumps(OBJECT_NOT_FOUND)

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Error from server. Status code: 404", ret_val["result_data"][0]["message"])

        expected_params = {"internetMessageId": "<bhcA66ahvjA@mail.test.com>", "recipientAddress": EMAIL_ADDRESS}

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE_METADATA}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=cofensevision_config.ACTION_HEADER,
            params=expected_params,
        )

    @patch("cofensevision_utils.requests.get")
    def test_get_message_metadata_invalid_address_fail(self, mock_get):
        """
        Test invalid address case for get message metadata

        Mock the API response of the server
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"internet_message_id": MESSAGE_ID, "recipient_address": "te@test.com"}]

        mock_get.return_value.status_code = 404
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = OBJECT_NOT_FOUND
        mock_get.return_value.text = json.dumps(OBJECT_NOT_FOUND)

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Error from server. Status code: 404", ret_val["result_data"][0]["message"])

        expected_params = {"internetMessageId": MESSAGE_ID, "recipientAddress": "te@test.com"}

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE_METADATA}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=cofensevision_config.ACTION_HEADER,
            params=expected_params,
        )

    @patch("cofensevision_utils.requests.get")
    def test_get_message_metadata_server_fail(self, mock_get):
        """
        Test the invalid case for the get message metadata action.

        Mock the API response of the server
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [VALID_PARAMS]

        mock_get.return_value.status_code = 500
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"error": "Internal server error"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Error from server. Status code: 500", ret_val["result_data"][0]["message"])

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE_METADATA}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=cofensevision_config.ACTION_HEADER,
            params=EXPECTED_PARAMS,
        )
