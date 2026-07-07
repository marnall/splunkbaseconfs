# File: test_silentpush_live_url_scan.py
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
    """Class to test the live url scan action."""

    def setUp(self):
        self.connector = SilentpushConnector()
        self.test_json = dict(silentpush_constant.TEST_JSON)
        self.test_json["config"] = {
            **self.test_json["config"],
            **silentpush_constant.APIKEY_AUTH_CONFIG,
        }
        self.test_json.update({"action": "live url scan", "identifier": "live_url_scan"})
        self.run_job_endpoint = consts.LIVE_URL_SCAN_ENDPOINT

        return super().setUp()

    def test_live_url_scan_valid(self, mock_get):
        """Test the valid case for the live url scan action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "url": silentpush_constant.DEFAULT_DOMAIN,
                "platform": "Desktop",
                "os": "Windows",
                "browser": "Firefox",
                "region": "US",
            }
        ]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_responses.LIVE_URL_SCAN_VALID_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{self.run_job_endpoint}?url=\
                www.silentpush.com&platform=Desktop&OS=Windows&browser=Firefox&region=US",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
        )

    def test_live_url_scan_invalid(self, mock_get):
        """Test the invalid case for the live url scan action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "url": silentpush_constant.DEFAULT_DOMAIN,
                "platform": "Desktop",
                "os": "Windows",
                "browser": "Firefox",
                "region": "US",
            }
        ]

        mock_get.return_value.status_code = 400
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_constant.MISSING_REQUIRED_PARAMETER

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{self.run_job_endpoint}?url\
                =www.silentpush.com&platform=Desktop&OS=Windows&browser=Firefox&region=US",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
        )

    def test_live_url_scan_platform_value_invalid(self, mock_get):
        """Test the invalid case for the live url scan action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "url": silentpush_constant.DEFAULT_DOMAIN,
                "platform": silentpush_constant.INVALID_DROPDOWN_RESPONSE,
                "os": "Windows",
                "browser": "Firefox",
                "region": "US",
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_live_url_scan_os_value_invalid(self, mock_get):
        """Test the invalid case for the live url scan action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "url": silentpush_constant.DEFAULT_DOMAIN,
                "platform": "Desktop",
                "os": silentpush_constant.INVALID_DROPDOWN_RESPONSE,
                "browser": "Firefox",
                "region": "US",
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_live_url_scan_browser_value_invalid(self, mock_get):
        """Test the invalid case for the live url scan action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "url": silentpush_constant.DEFAULT_DOMAIN,
                "platform": "Desktop",
                "os": "Windows",
                "browser": silentpush_constant.INVALID_DROPDOWN_RESPONSE,
                "region": "US",
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_live_url_scan_region_value_invalid(self, mock_get):
        """Test the invalid case for the live url scan action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "url": silentpush_constant.DEFAULT_DOMAIN,
                "platform": "Desktop",
                "os": "Windows",
                "browser": "Firefox",
                "region": silentpush_constant.INVALID_DROPDOWN_RESPONSE,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
