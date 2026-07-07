# File: test_silentpush_get_enrichment_data.py
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
from urllib.parse import urlencode

from parameterized import parameterized

import silentpush_consts as consts
from silentpush_connector import SilentpushConnector

from . import silentpush_constant, silentpush_responses


@patch("silentpush_utils.requests.get")
class SilentpushAction(unittest.TestCase):
    """Class to test the get enrichment data action."""

    def setUp(self):
        self.connector = SilentpushConnector()
        self.test_json = dict(silentpush_constant.TEST_JSON)
        self.test_json["config"] = {
            **self.test_json["config"],
            **silentpush_constant.APIKEY_AUTH_CONFIG,
        }
        self.test_json.update({"action": "get enrichment data", "identifier": "get_enrichment_data"})
        self.run_job_endpoint = consts.GET_ENRICHMENT_DATA_ENDPOINT

        return super().setUp()

    @parameterized.expand(
        [
            ["Domain", "Domain", "google.com", True, True],
            ["Domain", "Domain", "google.com", False, False],
            ["IPv4", "IPv4", "8.8.8.8", True, True],
            ["IPv4", "IPv4", "8.8.8.8", False, False],
            ["IPv6", "IPv6", "2001:db8:3333:4444:CCCC:DDDD:EEEE:FFFF:HHHH", True, True],
            [
                "IPv6",
                "IPv6",
                "2001:db8:3333:4444:CCCC:DDDD:EEEE:FFFF:HHHH",
                False,
                False,
            ],
        ]
    )
    def test_get_enrichment_data_valid(self, mock_get, _, resource, value, explain, scan_data):
        """Test the valid case for the get enrichment data action.

        Patch the get() to run job.
        """
        self.test_json["parameters"][0]["resource"] = resource
        self.test_json["parameters"][0]["value"] = value
        self.test_json["parameters"][0]["explain"] = explain
        self.test_json["parameters"][0]["scan_data"] = scan_data

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_responses.GET_ENRICHMENT_DATA_VALID_RESP

        param = {}
        param["explain"] = 1 if explain else 0
        param["scan_data"] = 1 if scan_data else 0

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}"
            f"{self.run_job_endpoint.replace('{{resource}}', resource.lower()).replace('{{value}}', value)}?{urlencode(param)}",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
        )

    @parameterized.expand(
        [
            ["Domain", "domain", "google.com"],
            ["IPv4", "IPv4", "invalid"],
            ["IPv6", "ipv6", "2001:db8:3333:4444:CCCC:DDDD:EEEE:FFFF"],
        ]
    )
    def test_get_enrichment_data_invalid_param(self, mock_get, _, resource, value):
        """Test the valid case for the get enrichment data action.

        Patch the get() to run job.
        """
        self.test_json["parameters"][0]["resource"] = resource
        self.test_json["parameters"][0]["value"] = value

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
