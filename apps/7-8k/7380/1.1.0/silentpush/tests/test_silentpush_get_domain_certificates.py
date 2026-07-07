# File: test_silentpush_get_domain_certificates.py
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


DOMAIN = "silentpush.com"


@patch("silentpush_utils.requests.get")
class SilentpushAction(unittest.TestCase):
    """Class to test the get domain certificates action."""

    def setUp(self):
        self.connector = SilentpushConnector()
        self.test_json = dict(silentpush_constant.TEST_JSON)
        self.test_json["config"] = {
            **self.test_json["config"],
            **silentpush_constant.APIKEY_AUTH_CONFIG,
        }
        self.test_json.update(
            {
                "action": "get domain certificates",
                "identifier": "get_domain_certificates",
            }
        )
        self.run_job_endpoint = consts.GET_DOMAIN_CERTIFICATES_ENDPOINT.replace("{{domain}}", "domain")

        return super().setUp()

    def test_get_domain_certificates_valid(self, mock_get):
        """
        Test the valid case for the get domain certificates action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domain": "domain",
                "domain_regex": "silentpush",
                "certificate_issuer": "GTS CA 1P5",
                "date_min": "2021-01-01",
                "date_max": "2024-01-01",
                "prefer": "result",
                "max_wait": 25,
                "with_metadata": True,
                "limit": 4,
                "skip": 1,
            }
        ]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_responses.GET_DOMAIN_CERTIFICATES_VALID_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}"
            f"{self.run_job_endpoint}?domain_regex=silentpush&cert_issuer=GTS+CA+1P5&date_min=2021-01-01&date_max"
            f"=2024-01-01&prefer=result&max_wait=25&with_metadata=1&limit=4&skip=1",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
        )

    def test_get_domain_certificates_domain_valid(self, mock_get):
        """
        Test the valid case for the get domain certificates action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domain": DOMAIN,
                "certificate_issuer": "GTS CA 1P5",
                "date_min": "2021-01-01",
                "date_max": "2024-01-01",
                "prefer": "result",
                "max_wait": 25,
                "with_metadata": True,
                "limit": 4,
                "skip": 1,
            }
        ]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_responses.GET_DOMAIN_CERTIFICATES_VALID_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

    def test_get_domain_certificates_prefer_value_invalid(self, mock_get):
        """
        Test the invalid case for the get domain certificates action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domain": DOMAIN,
                "certificate_issuer": "GTS CA 1P5",
                "date_min": "2021-01-01",
                "date_max": "2024-01-01",
                "prefer": "{'ok': True}",
                "max_wait": 25,
                "with_metadata": True,
                "limit": 4,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_get_domain_certificates_domain_regex_invalid(self, mock_get):
        """
        Test the invalid case for the get domain certificates action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domain": DOMAIN,
                "domain_regex": ".silent.push",
                "prefer": "Result",
                "limit": 4,
                "with_metadata": True,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_get_domain_certificates_max_wait_type_invalid(self, mock_get):
        """
        Test the invalid type case for the get domain certificates action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domain": DOMAIN,
                "prefer": "Result",
                "max_wait": -10,
                "with_metadata": True,
                "limit": 4,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_get_domain_certificates_limit_type_invalid(self, mock_get):
        """
        Test the invalid type case for the get domain certificates action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domain": DOMAIN,
                "prefer": "Result",
                "max_wait": 25,
                "with_metadata": True,
                "limit": -10,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_get_domain_certificates_skip_type_invalid(self, mock_get):
        """
        Test the invalid type case for the get domain certificates action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domain": DOMAIN,
                "prefer": "Result",
                "with_metadata": True,
                "limit": 10,
                "skip": -1,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_get_domain_certificates_with_metadata_type_invalid(self, mock_get):
        """
        Test the invalid type case for the get domain certificates action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domain": DOMAIN,
                "prefer": "Result",
                "with_metadata": 1,
                "limit": 10,
                "skip": 1,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
