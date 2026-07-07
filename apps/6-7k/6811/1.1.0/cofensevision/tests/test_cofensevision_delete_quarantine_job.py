# File: test_cofensevision_delete_quarantine_job.py
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


class TestDeleteQuarantineJobAction(unittest.TestCase):
    """Class to test the delete quarantine job action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "delete quarantine job", "identifier": "delete_quarantine_job"})

        return super().setUp()

    @patch("cofensevision_utils.requests.delete")
    def test_delete_quarantine_job_action_pass(self, mock_delete):
        """Test the valid case for the delete quarantine job action.

        Token is available in the state file.
        Patch the delete() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        job_id = "1387"

        self.test_json["parameters"] = [
            {
                "id": job_id,
            }
        ]

        mock_delete.return_value.status_code = 200
        mock_delete.return_value.headers = {}
        mock_delete.return_value.text = ""

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_delete.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_QUARANTINE_JOB.format(job_id=job_id)}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=cofensevision_config.ACTION_HEADER,
        )

    @patch("cofensevision_utils.requests.delete")
    def test_delete_quarantine_job_nonexisting_id_action_fail(self, mock_delete):
        """Test the delete quarantine job action with non existing valid id.

        Token is available in the state file.
        Patch the delete() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        job_id = "1388"

        self.test_json["parameters"] = [
            {
                "id": job_id,
            }
        ]

        mock_delete.return_value.status_code = 404
        mock_delete.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_delete.return_value.text = (
            '{"status": "NOT_FOUND", "message": "Object not found", "details": ["Unable to find the requested object"]}'
        )

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Status code: 404", ret_val["result_data"][0]["message"])

        mock_delete.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_QUARANTINE_JOB.format(job_id=job_id)}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=cofensevision_config.ACTION_HEADER,
        )

    def test_delete_quarantine_job_invalid_id_action_fail(self):
        """Test the delete quarantine job action with invalid id.

        Token is available in the state file.
        Patch the delete() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        job_id = "invalid_id"

        self.test_json["parameters"] = [
            {
                "id": job_id,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_INT_PARAM.format(key="id"))
