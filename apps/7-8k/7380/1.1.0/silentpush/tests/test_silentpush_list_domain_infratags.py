# File: test_silentpush_list_domain_infratags.py
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
    """Class to test the list domain infratags action."""

    def setUp(self):
        self.connector = SilentpushConnector()
        self.test_json = dict(silentpush_constant.TEST_JSON)
        self.test_json["config"] = {**self.test_json["config"], **silentpush_constant.APIKEY_AUTH_CONFIG}
        self.test_json.update({"action": "list domain infratags", "identifier": "list_domain_infratags"})
        self.run_job_endpoint = consts.LIST_DOMAIN_INFRATAGS_ENDPOINT

        return super().setUp()

    def test_list_domain_infratags_valid(self, mock_post):
        """Test the valid case for the list domain infratags action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [
            {"mode": "PADNS", "match": "Full", "as_of": "2021-07-09", "clusters": True, "domains": silentpush_constant.MULTIPLE_DOMAINS}
        ]

        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_post.return_value.json.return_value = silentpush_responses.LIST_DOMAIN_INFRATAGS_VALID_RESP

        req_data = {"domains": ["abc.com", "xyz.io", "def.com", "silentpush.com"]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{self.run_job_endpoint}?mode=padns&match=full&as_of=2021-07-09&clusters=1",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
            json=req_data,
        )

    def test_list_domain_infratags_invalid(self, mock_post):
        """Test the invalid case for the list domain infratags action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [
            {"mode": "PADNS", "match": "Full", "as_of": "2021-07-09", "clusters": True, "domains": silentpush_constant.MULTIPLE_DOMAINS}
        ]

        mock_post.return_value.status_code = 400
        mock_post.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_post.return_value.json.return_value = silentpush_constant.MISSING_REQUIRED_PARAMETER

        req_data = {"domains": ["abc.com", "xyz.io", "def.com", "silentpush.com"]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{self.run_job_endpoint}?mode=padns&match=full&as_of=2021-07-09&clusters=1",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
            json=req_data,
        )

    def test_list_domain_infratags_mode_value_invalid(self, mock_post):
        """Test the invalid case for the list domain infratags action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [
            {"mode": "{'ok': True}", "match": "Full", "as_of": "2021-07-09", "clusters": True, "domains": silentpush_constant.MULTIPLE_DOMAINS}
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_list_domain_infratags_domains_value_invalid(self, mock_post):
        """Test the invalid case for the list domain infratags action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [{"mode": "PADNS", "match": "Full", "as_of": "2021-07-09", "clusters": True, "domains": ",,,,,,,,,"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_list_domain_infratags_match_value_invalid(self, mock_post):
        """Test the invalid case for the list domain infratags action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [
            {"mode": "PADNS", "match": "{'ok': True}", "as_of": "2021-07-09", "clusters": True, "domains": silentpush_constant.MULTIPLE_DOMAINS}
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
