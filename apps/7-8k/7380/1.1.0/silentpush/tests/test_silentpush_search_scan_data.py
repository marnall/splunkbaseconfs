# File: test_silentpush_search_scan_data.py
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


@patch("silentpush_utils.requests.post")
class SilentpushAction(unittest.TestCase):
    """Class to test the search scan data action."""

    def setUp(self):
        self.connector = SilentpushConnector()
        self.test_json = dict(silentpush_constant.TEST_JSON)
        self.test_json["config"] = {**self.test_json["config"], **silentpush_constant.APIKEY_AUTH_CONFIG}
        self.test_json.update({"action": "search scan data", "identifier": "search_scan_data"})
        self.run_job_endpoint = consts.SEARCH_SCAN_DATA_ENDPOINT

        return super().setUp()

    def test_search_scan_data_valid(self, mock_post):
        """Test the valid case for the search scan data action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [
            {"skip": 1, "limit": 1, "with_metadata": True, "query": "domain = silentpush.com", "fields": "domain", "sort": "scan_date/asc"}
        ]

        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_post.return_value.json.return_value = silentpush_responses.SEARCH_SCAN_DATA_VALID_RESP

        req_data = {"query": "domain = silentpush.com", "fields": ["domain"], "sort": ["scan_date/asc"]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{self.run_job_endpoint}?skip=1&limit=1&with_metadata=1",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": "<dummy_api_token>"},
            json=req_data,
        )

    def test_search_scan_data_invalid(self, mock_post):
        """Test the invalid case for the search scan data action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [
            {"skip": 1, "limit": 1, "with_metadata": True, "query": "domain_inv = silentpush.com", "fields": "domain", "sort": "scan_date/asc"}
        ]

        mock_post.return_value.status_code = 400
        mock_post.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_post.return_value.json.return_value = silentpush_constant.MISSING_REQUIRED_PARAMETER

        req_data = {"query": "domain_inv = silentpush.com", "fields": ["domain"], "sort": ["scan_date/asc"]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{self.run_job_endpoint}?skip=1&limit=1&with_metadata=1",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": "<dummy_api_token>"},
            json=req_data,
        )

    def test_search_scan_data_skip_type_invalid(self, mock_post):
        """Test the invalid type case for the search scan data action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [
            {
                "skip": -10,
                "limit": 1,
                "with_metadata": True,
                "query": "domain = silentpush.com",
                "fields": "domain, scan_date",
                "sort": "scan_date/asc, domain/desc",
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_search_scan_data_limit_type_invalid(self, mock_post):
        """Test the invalid type case for the search scan data action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [
            {
                "skip": 1,
                "limit": -10,
                "with_metadata": True,
                "query": "domain = silentpush.com",
                "fields": "domain, scan_date",
                "sort": "scan_date/asc, domain/desc",
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
