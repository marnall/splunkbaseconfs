# File: test_cofensevision_get_message_attachment.py
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
import requests_mock

import cofensevision_consts as consts
from cofensevision_connector import CofenseVisionConnector
from tests import cofensevision_config


class TestGetMessageAttachmentAction(unittest.TestCase):
    """Class to test the get message attachment action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        # Reset the global object to avoid failures
        base_conn.connector_obj = None
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "get message attachment", "identifier": "get_message_attachment"})
        self.tempfile = "test_file.txt"
        return super().setUp()

    def tearDown(self):
        """Tear down method for the tests."""
        if os.path.exists(self.tempfile):
            os.remove(self.tempfile)
        return super().tearDown()

    def test_get_message_attachment_filename_without_ext_fail(self):
        """Test invalid case for filename parameter."""
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [
            {
                "md5": "098f6bcd4621d373cade4e832627b4f6",  # pragma: allowlist secret
                "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",  # pragma: allowlist secret
                "filename": "just_name",
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(
            ret_val["result_data"][0]["message"], "Please provide a valid file name including the extension in the 'filename' parameter"
        )
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    @requests_mock.Mocker(real_http=True)
    def test_get_message_attachment_pass(self, mock_get):
        """
        Test the valid case for the get message attachment action.

        Mock the API response to test the stream data handling.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [
            {
                "md5": "098f6bcd4621d373cade4e832627b4f6",  # pragma: allowlist secret
                "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",  # pragma: allowlist secret
                "filename": self.tempfile,
            }
        ]

        self.test_json.update({"user_session_token": cofensevision_config.get_session_id(self.connector)})
        self.test_json.update({"container_id": cofensevision_config.create_container(self.connector)})

        with open(self.tempfile, "w") as f:
            f.write("Test data")

        with open(self.tempfile, "rb") as fp:
            mock_get.get(
                f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_ATTACHMENT}",
                status_code=200,
                headers={"Content-Type": "application/octet-stream"},
                content=fp.read(),
            )

            ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
            ret_val = json.loads(ret_val)
            self.assertEqual(ret_val["result_data"][0]["data"][0]["container_id"], self.test_json["container_id"])
            self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
            self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
            self.assertEqual(ret_val["status"], "success")

    @patch("cofensevision_utils.requests.get")
    def test_get_message_attachment_invalid_hash_fail(self, mock_get):
        """
        Test invalid case for hash parameter.

        Mock the API response for the invalid hash
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [
            {
                "md5": "098f6bcd4621d373cade4e832627b4f6",  # pragma: allowlist secret
                "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",  # pragma: allowlist secret
                "filename": self.tempfile,
            }
        ]

        mock_get.return_value.status_code = 404
        mock_get.return_value.headers = {"Content-Type": "application/json"}
        mock_get.return_value.text = '{"status": "NOT_FOUND", "message": "Object not found", "details": ["Unable to find the requested object"]}'

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertIn("Error from server. Status code: 404", ret_val["result_data"][0]["message"])
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        expected_params = {
            "md5": "098f6bcd4621d373cade4e832627b4f6",  # pragma: allowlist secret
            "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",  # pragma: allowlist secret
        }

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_ATTACHMENT}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            params=expected_params,
            headers=cofensevision_config.STREAM_ACTION_HEADER,
            verify=False,
            stream=True,
        )

    @patch("cofensevision_utils.requests.get")
    def test_get_message_attachment_server_fail(self, mock_get):
        """
        Test the server side error case

        Mock the APi response for server side error
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [
            {
                "md5": "098f6bcd4621d373cade4e832627b4f6",  # pragma: allowlist secret
                "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",  # pragma: allowlist secret
                "filename": self.tempfile,
            }
        ]

        mock_get.return_value.status_code = 500
        mock_get.return_value.headers = {"Content-Type": "application/json"}
        mock_get.return_value.json.return_value = {"error": "Internal server error"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertIn("Error from server. Status code: 500", ret_val["result_data"][0]["message"])
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        expected_params = {
            "md5": "098f6bcd4621d373cade4e832627b4f6",  # pragma: allowlist secret
            "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",  # pragma: allowlist secret
        }

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_ATTACHMENT}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            params=expected_params,
            headers=cofensevision_config.STREAM_ACTION_HEADER,
            verify=False,
            stream=True,
        )

    def test_get_message_attachment_no_hash_fail(self):
        """Test the list iocs action with no hash parameter.

        Token is available in the state file.
        """
        # Save the state file with the invalid JSON string.
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"filename": self.tempfile}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_NO_HASH_PARAMETER)
