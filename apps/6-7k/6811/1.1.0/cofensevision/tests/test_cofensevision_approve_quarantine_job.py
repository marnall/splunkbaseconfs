# File: test_cofensevision_approve_quarantine_job.py
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


class TestApproveQuarantineJobAction(unittest.TestCase):
    """Class to test the approve quarantine job action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "approve quarantine job", "identifier": "approve_quarantine_job"})

        return super().setUp()

    @patch("cofensevision_utils.requests.put")
    def test_approve_quarantine_job_pass(self, mock_put):
        """Test the valid case for the approve quarantine job action.

        Token is available in the state file.
        Patch the put() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        job_id = 1234

        self.test_json["parameters"] = [{consts.VISION_PARAM_JOB_ID: job_id, "message_count": "3"}]

        mock_put.return_value.status_code = 200
        mock_put.return_value.headers = {}
        mock_put.return_value.text = ""

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_SUCCESS_APPROVE_JOB_ACTION)

        mock_put.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_APPROVE_QUARANTINE_JOBS.format(job_id=job_id)}",
            headers=cofensevision_config.ACTION_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            params={"messageCount": 3},
            verify=False,
        )

    def test_approve_quarantine_job_invalid_id_fail(self):
        """Test the approve quarantine job action with invalid 'job id' parameter."""
        self.test_json["parameters"] = [{consts.VISION_PARAM_JOB_ID: "non_numeric"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_INT_PARAM.format(key=consts.VISION_PARAM_JOB_ID))

    def test_approve_quarantine_job_invalid_message_count_fail(self):
        """Test the approve quarantine job action with invalid 'message count' parameter."""
        self.test_json["parameters"] = [{consts.VISION_PARAM_JOB_ID: "1234", "message_count": "non_numeric"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_INT_PARAM.format(key="message count"))

    @patch("cofensevision_utils.requests.put")
    def test_approve_quarantine_job_non_pending_fail(self, mock_put):
        """Test the approve quarantine job action with valid id, but the job is not pending on approval.

        Token is available in the state file.
        Patch the put() to return the 'non processable entity' response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        job_id = 1234

        self.test_json["parameters"] = [
            {
                consts.VISION_PARAM_JOB_ID: job_id,
            }
        ]

        response_json = {
            "status": "UNPROCESSABLE_ENTITY",
            "message": "Invalid data, please check the request body",
            "details": ["Quarantine Job is not Pending Approval"],
        }

        mock_put.return_value.status_code = 422
        mock_put.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_put.return_value.json.return_value = response_json
        mock_put.return_value.text = json.dumps(response_json)

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Status code: 422", ret_val["result_data"][0]["message"])
        self.assertIn("UNPROCESSABLE_ENTITY", ret_val["result_data"][0]["message"])

        mock_put.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_APPROVE_QUARANTINE_JOBS.format(job_id=job_id)}",
            headers=cofensevision_config.ACTION_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            params={},
            verify=False,
        )
