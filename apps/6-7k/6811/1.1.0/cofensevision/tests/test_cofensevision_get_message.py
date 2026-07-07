# File: test_cofensevision_get_message.py
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
import os
import unittest
from unittest.mock import patch

import phantom.base_connector as base_conn
import pyzipper
import requests_mock

import cofensevision_consts as consts
from cofensevision_connector import CofenseVisionConnector
from tests import cofensevision_config


EMAIL_ADDRESS = "testuser@test.com"
MESSAGE_ID = "<CAFRPxWtuVLQ8OspO8OK6bhcA66ahvjA@mail.test.com>"


class TestGetMessageAction(unittest.TestCase):
    """Class to test the get message action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        # Reset the global object to avoid failures
        base_conn.connector_obj = None
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "get message", "identifier": "get_message"})
        self.tempfile = "test.zip"
        return super().setUp()

    def tearDown(self):
        """Tear down method for the tests."""
        if os.path.exists(self.tempfile):
            os.remove(self.tempfile)
        return super().tearDown()

    @requests_mock.Mocker(real_http=True)
    @requests_mock.Mocker(real_http=True)
    def test_get_message_pass(self, mock_get, mock_post):
        """
        Test the valid case for the get message action.

        Mock the API response to test the stream data handling.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        password = os.environ.get("PASSWORD")
        self.test_json["parameters"] = [{"internet_message_id": MESSAGE_ID, "recipient_address": EMAIL_ADDRESS, "password": password}]

        self.test_json.update({"user_session_token": cofensevision_config.get_session_id(self.connector)})
        self.test_json.update({"container_id": cofensevision_config.create_container(self.connector)})

        mock_post.post(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE}",
            status_code=200,
            headers=cofensevision_config.DEFAULT_HEADERS,
            text="dummy_message_token",
        )

        with pyzipper.AESZipFile(self.tempfile, "w", compression=pyzipper.ZIP_LZMA, encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(password.encode())
            zf.writestr("testfile.txt", "Test data")

        with open(self.tempfile, "rb") as binary_zip:
            mock_get.get(
                f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE}",
                status_code=200,
                headers={"Content-Type": "application/octet-stream"},
                content=binary_zip.read(),
            )

            ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
            ret_val = json.loads(ret_val)
            self.assertEqual(ret_val["result_data"][0]["data"][0]["container_id"], self.test_json["container_id"])
            self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
            self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
            self.assertEqual(ret_val["status"], "success")

    @patch("cofensevision_utils.requests.post")
    @patch("cofensevision_utils.requests.get")
    def test_get_message_invalid_message_id_fail(self, mock_get, mock_post):
        """
        Test invalid case for message id parameter.

        Mock the API response for the invalid message id
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"internet_message_id": MESSAGE_ID, "recipient_address": EMAIL_ADDRESS}]

        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_post.return_value.text = "dummy_token"

        mock_get.return_value.status_code = 404
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.text = '{"status": "NOT_FOUND", "message": "Object not found", "details": ["Unable to find the requested object"]}'

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertIn("Error from server. Status code: 404", ret_val["result_data"][0]["message"])
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        expected_body = {"internetMessageId": MESSAGE_ID, "recipientAddress": EMAIL_ADDRESS}

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            headers=cofensevision_config.ACTION_HEADER,
            json=expected_body,
            verify=False,
        )

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            headers=cofensevision_config.STREAM_ACTION_HEADER,
            params={"token": "dummy_token"},
            verify=False,
            stream=True,
        )

    @patch("cofensevision_utils.requests.post")
    def test_get_message_server_fail(self, mock_post):
        """
        Test the server side error case

        Mock the APi response for server side error
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"internet_message_id": MESSAGE_ID, "recipient_address": EMAIL_ADDRESS}]

        mock_post.return_value.status_code = 500
        mock_post.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"error": "Internal server error"}
        mock_post.return_value.text = '{"error": "Internal server error"}'

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertIn("Error from server. Status code: 500", ret_val["result_data"][0]["message"])
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        expected_params = {"internetMessageId": MESSAGE_ID, "recipientAddress": EMAIL_ADDRESS}

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=cofensevision_config.ACTION_HEADER,
            json=expected_params,
        )
