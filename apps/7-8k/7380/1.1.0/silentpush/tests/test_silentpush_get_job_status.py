# File: test_silentpush_get_job_status.py
#
# Copyright (c) 2024-2025 Splunk Inc.
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

import silentpush_consts as consts
from silentpush_connector import SilentpushConnector

from . import silentpush_constant, silentpush_responses


@patch("silentpush_utils.requests.get")
class SilentpushAction(unittest.TestCase):
    """Class to test the get job status action."""

    def setUp(self):
        self.connector = SilentpushConnector()
        self.test_json = dict(silentpush_constant.TEST_JSON)
        self.test_json["config"] = {**self.test_json["config"], **{}}
        self.test_json.update({"action": "get job status", "identifier": "get_job_status"})
        self.run_job_endpoint = consts.GET_JOB_STATUS_ENDPOINT.replace("{{job_id}}", "6bd0ba36-9f30-4beb-8a7a-164123ecdc30")

        return super().setUp()

    def test_get_job_status_valid(self, mock_get):
        """Test the valid case for the get job status action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [{"job_id": "6bd0ba36-9f30-4beb-8a7a-164123ecdc30", "max_wait": 25, "result_type": "Status"}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_responses.GET_JOB_STATUS_VALID_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{self.run_job_endpoint}?status_only=1&max_wait=25",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
        )

    def test_get_job_status_invalid(self, mock_get):
        """Test the invalid case for the get job status action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [{"job_id": "6bd0ba36-9f30-4beb-8a7a-164123ecdc30", "max_wait": 25, "result_type": "Status"}]

        mock_get.return_value.status_code = 400
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_constant.MISSING_REQUIRED_PARAMETER

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{self.run_job_endpoint}?status_only=1&max_wait=25",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
        )

    def test_get_job_status_max_wait_type_invalid(self, mock_get):
        """Test the invalid type case for the get job status action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [{"job_id": "6bd0ba36-9f30-4beb-8a7a-164123ecdc30", "max_wait": -10, "result_type": "Status"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_get_job_status_result_type_value_invalid(self, mock_get):
        """Test the invalid case for the get job status action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [{"job_id": "6bd0ba36-9f30-4beb-8a7a-164123ecdc30", "max_wait": 25, "result_type": "{'ok': True}"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
