# File: test_cofensevision_create_quarantine_job.py
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


MESSAGE_ID = "<CAFRPxWtoTSDQirOh+ov-aidDbP9zJuhLLjn16fOq_K1E@test.com>"
MESSAGE_ID2 = "<CAFRPxWtoTSDQirOh+ov-fqwfkmfdknqkfnfiowe_K1E@test.com>"

EMAIL_ADDRESS = "testuser@test.com"
EMAIL_ADDRESS2 = "testuser1@test.com"
EXPECTED_DATA = {
    "quarantineEmails": [
        {"internetMessageId": MESSAGE_ID, "recipientAddress": EMAIL_ADDRESS},
        {"internetMessageId": MESSAGE_ID2, "recipientAddress": EMAIL_ADDRESS},
        {"internetMessageId": MESSAGE_ID2, "recipientAddress": EMAIL_ADDRESS2},
    ]
}


class TestCreateQuarantineJobAction(unittest.TestCase):
    """Class to test the create quarantine job action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "create quarantine job", "identifier": "create_quarantine_job"})

        return super().setUp()

    @patch("cofensevision_utils.requests.post")
    def test_create_quarantine_job_action_pass(self, mock_post):
        """Test the valid case for the create quarantine job action.

        Token is available in the state file.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        quarantine_emails = f"{EMAIL_ADDRESS}:{MESSAGE_ID}"

        expected_data = {"quarantineEmails": [{"internetMessageId": MESSAGE_ID, "recipientAddress": EMAIL_ADDRESS}]}

        self.test_json["parameters"] = [
            {
                "quarantine_emails": quarantine_emails,
            }
        ]

        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"id": ""}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_QUARANTINE_JOBS}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=cofensevision_config.ACTION_HEADER,
            json=expected_data,
        )

    @patch("cofensevision_utils.requests.post")
    def test_create_quarantine_job_action_with_duplicates_pass(self, mock_post):
        """Test the valid case with multiple recipients for the create quarantine job action.

        Token is available in the state file.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        quarantine_emails = f"{EMAIL_ADDRESS}:{MESSAGE_ID}:{MESSAGE_ID2}:{MESSAGE_ID},{EMAIL_ADDRESS2}:{MESSAGE_ID2}:{MESSAGE_ID2}"

        self.test_json["parameters"] = [
            {
                "quarantine_emails": quarantine_emails,
            }
        ]

        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"id": ""}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_QUARANTINE_JOBS}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=cofensevision_config.ACTION_HEADER,
            json=EXPECTED_DATA,
        )

    @patch("cofensevision_utils.requests.post")
    def test_create_quarantine_job_action_fail(self, mock_post):
        """Test the create quarantine job action with authentication error.

        Token is available in the state file.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        quarantine_emails = f"{EMAIL_ADDRESS}:{MESSAGE_ID}"

        expected_data = {"quarantineEmails": [{"internetMessageId": MESSAGE_ID, "recipientAddress": EMAIL_ADDRESS}]}

        self.test_json["parameters"] = [
            {
                "quarantine_emails": quarantine_emails,
            }
        ]

        mock_post.return_value.status_code = 401
        mock_post.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"error": "UNAUTHORIZED", "error_description": "reason"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Status code: 401", ret_val["result_data"][0]["message"])

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_QUARANTINE_JOBS}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=cofensevision_config.ACTION_HEADER,
            json=expected_data,
        )

    def test_create_quarantine_job_invalid_parameter_fail(self):
        """Test the create quarantine job action with invalid parameter.

        Token is available in the state file.
        """
        quarantine_emails = f"{EMAIL_ADDRESS}:"

        self.test_json["parameters"] = [
            {
                "quarantine_emails": quarantine_emails,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        (self.assertEqual(ret_val["status"], "failed"),)
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("quarantine_emails"))
