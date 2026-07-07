# File: test_silentpush_search_domains.py
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
    """Class to test the domain search action."""

    def setUp(self):
        self.connector = SilentpushConnector()
        self.test_json = dict(silentpush_constant.TEST_JSON)
        self.test_json["config"] = {**self.test_json["config"], **silentpush_constant.APIKEY_AUTH_CONFIG}
        self.test_json.update({"action": "search domains", "identifier": "search_domains"})
        self.run_job_endpoint = consts.DOMAIN_SEARCH_ENDPOINT

        return super().setUp()

    def test_domain_search_valid(self, mock_get):
        """
        Test the valid case for the domain search action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domain": "*.silentpush.com",
                "domain_regex": "silent*",
                "name_server": "self",
                "asnum": 15169,
                "asname": silentpush_constant.AS_NAME,
                "min_ip_diversity": 2,
                "registrar": "Mark",
                "min_asn_diversity": 1,
                "certificate_issuer": "GTS CA 1P5",
                "whois_date_after": "1980-01-01",
                "limit": 5,
                "skip": 1,
            }
        ]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_responses.DOMAIN_SEARCH_VALID_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}"
            f"{self.run_job_endpoint}?domain=%2A.silentpush.com&domain_regex=silent%2A&nsname=self&asnum=15169&asname"
            f"=BCD-AES%2C+US&ip_diversity_all_min=2&registrar=Mark&asn_diversity_min=1&cert_issuer=GTS+CA+1P5"
            f"&whois_date_after=1980-01-01&limit=5&skip=1",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
        )

    def test_domain_search_invalid(self, mock_get):
        """
        Test the invalid case for the domain search action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [{"domain": "googlecom", "limit": 5}]

        mock_get.return_value.status_code = 200

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{self.run_job_endpoint}?domain=googlecom&limit=5",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
        )

    def test_domain_search_domain_regex_invalid(self, mock_get):
        """
        Test the invalid case for the domain search action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domain": silentpush_constant.DEFAULT_DOMAIN_WITHOUT_WWW,
                "domain_regex": "*.silentpush.com",
                "name_server": "self",
                "asnum": 15169,
                "asname": silentpush_constant.AS_NAME,
                "min_ip_diversity": 2,
                "registrar": "Mark",
                "min_asn_diversity": 1,
                "certificate_issuer": "GTS CA 1P5",
                "whois_date_after": "1980-01-01",
                "limit": 5,
                "skip": 1,
            }
        ]

        mock_get.return_value.status_code = 200

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}"
            f"{self.run_job_endpoint}?domain=silentpush.com&domain_regex=%2A.silentpush.com&nsname=self&asnum=15169"
            f"&asname=BCD-AES%2C+US&ip_diversity_all_min=2&registrar=Mark&asn_diversity_min=1&cert_issuer=GTS+CA+1P5"
            f"&whois_date_after=1980-01-01&limit=5&skip=1",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
        )

    def test_domain_search_asnum_type_invalid(self, mock_get):
        """
        Test the invalid type case for the domain search action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domain": silentpush_constant.DEFAULT_DOMAIN_WITHOUT_WWW,
                "name_server": "self",
                "asnum": -10,
                "asname": silentpush_constant.AS_NAME,
                "min_ip_diversity": 2,
                "registrar": "Mark",
                "min_asn_diversity": 1,
                "certificate_issuer": "GTS CA 1P5",
                "whois_date_after": "1980-01-01",
                "limit": 5,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_domain_search_min_ip_diversity_type_invalid(self, mock_get):
        """
        Test the invalid type case for the domain search action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domain": silentpush_constant.DEFAULT_DOMAIN_WITHOUT_WWW,
                "name_server": "self",
                "asnum": 15169,
                "asname": silentpush_constant.AS_NAME,
                "min_ip_diversity": -10,
                "registrar": "Mark",
                "min_asn_diversity": 1,
                "certificate_issuer": "GTS CA 1P5",
                "whois_date_after": "1980-01-01",
                "limit": 5,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_domain_search_min_asn_diversity_type_invalid(self, mock_get):
        """
        Test the invalid type case for the domain search action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domain": silentpush_constant.DEFAULT_DOMAIN_WITHOUT_WWW,
                "name_server": "self",
                "asnum": 15169,
                "asname": silentpush_constant.AS_NAME,
                "min_ip_diversity": 2,
                "registrar": "Mark",
                "min_asn_diversity": -10,
                "certificate_issuer": "GTS CA 1P5",
                "whois_date_after": "1980-01-01",
                "limit": 5,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_domain_search_limit_type_invalid(self, mock_get):
        """
        Test the invalid type case for the domain search action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domain": silentpush_constant.DEFAULT_DOMAIN_WITHOUT_WWW,
                "name_server": "self",
                "asnum": 15169,
                "asname": silentpush_constant.AS_NAME,
                "min_ip_diversity": 2,
                "registrar": "Mark",
                "min_asn_diversity": 1,
                "certificate_issuer": "GTS CA 1P5",
                "whois_date_after": "1980-01-01",
                "limit": -10,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_domain_search_skip_type_invalid(self, mock_get):
        """
        Test the invalid type case for the domain search action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domain": silentpush_constant.DEFAULT_DOMAIN_WITHOUT_WWW,
                "name_server": "self",
                "asnum": 15169,
                "asname": silentpush_constant.AS_NAME,
                "min_ip_diversity": 2,
                "registrar": "Mark",
                "min_asn_diversity": 1,
                "certificate_issuer": "GTS CA 1P5",
                "whois_date_after": "1980-01-01",
                "skip": -1,
                "limit": 10,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
