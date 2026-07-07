# File: test_silentpush_density_lookup.py
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

from parameterized import parameterized

import silentpush_consts as consts
from silentpush_connector import SilentpushConnector

from . import silentpush_constant, silentpush_responses


@patch("silentpush_utils.requests.get")
class SilentpushAction(unittest.TestCase):
    """Class to test the density lookup action."""

    def setUp(self):
        self.connector = SilentpushConnector()
        self.run_job_endpoint = consts.DENSITY_LOOKUP_ENDPOINT
        self.test_json = dict(silentpush_constant.TEST_JSON)
        self.test_json["config"] = {
            **self.test_json["config"],
            **silentpush_constant.APIKEY_AUTH_CONFIG,
        }
        self.test_json.update({"action": "density lookup", "identifier": "density_lookup"})

        return super().setUp()

    def test_density_lookup_valid(self, mock_get):
        """Test the valid case for the density lookup action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [{"qtype": "NSSRV", "query": "1.1.1.1", "scope": "IP"}]
        self.run_job_endpoint = self.run_job_endpoint.replace("{{qtype}}", "nssrv").replace("{{query}}", "1.1.1.1")
        scope = "ip"

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_responses.DENSITY_LOOKUP_VALID_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{self.run_job_endpoint}?scope={scope}",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
        )

    def test_density_lookup_invalid(self, mock_get):
        """Test the invalid case for the density lookup action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [{"qtype": "NSSRV", "query": "1.1.1.1", "scope": "IP"}]
        self.run_job_endpoint = self.run_job_endpoint.replace("{{qtype}}", "nssrv").replace("{{query}}", "1.1.1.1")
        scope = "ip"

        mock_get.return_value.status_code = 400
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_constant.MISSING_REQUIRED_PARAMETER

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{self.run_job_endpoint}?scope={scope}",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
        )

    @parameterized.expand(
        [
            ["case1", "Invalid", "1.1.1.1", "ip"],
            ["case2", "NSSRV", "1.1.1.1", "Invalid"],
            ["case3", "Invalid", "1.1.1.1", "Invalid"],
        ]
    )
    def test_density_lookup_parameter_invalid(self, mock_get, _, qtype, query, scope):
        """Test the invalid parameter case for the density lookup action.

        Patch the get() to run job.
        """
        self.test_json["parameters"][0]["qtype"] = qtype
        self.test_json["parameters"][0]["query"] = query
        self.test_json["parameters"][0]["scope"] = scope

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
