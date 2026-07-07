# File: test_silentpush_forward_padns_lookup.py
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


DOMAIN_REGEX = "^sil[[:alpha:]]{3}\\.[a-z]{2,}$"
SORT = "last_seen/desc"
INVALID_VALUE_LIST = "{'ok': True}"


@patch("silentpush_utils.requests.get")
class SilentpushAction(unittest.TestCase):
    """Class to test the forward padns lookup action."""

    def setUp(self):
        self.connector = SilentpushConnector()
        self.test_json = dict(silentpush_constant.TEST_JSON)
        self.test_json["config"] = {**self.test_json["config"], **silentpush_constant.APIKEY_AUTH_CONFIG}
        self.test_json.update({"action": "forward padns lookup", "identifier": "forward_padns_lookup"})
        self.run_job_endpoint = consts.FORWARD_PADNS_LOOKUP_ENDPOINT.replace("{{qtype}}", "a").replace("{{qname}}", "8.8.8.8")

        return super().setUp()

    def test_forward_padns_lookup_valid(self, mock_get):
        """Test the valid case for the forward padns lookup action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "qtype": "a",
                "qname": "8.8.8.8",
                "netmask": 32,
                "subdomains": True,
                "regex": DOMAIN_REGEX,
                "match": "Strict",
                "first_seen_after": "1625834953",
                "first_seen_before": "2021-07-09",
                "last_seen_after": "2021-07-09",
                "last_seen_before": "1625834953",
                "as_of": "-172800",
                "sort": "last_seen/desc,answer/asc",
                "output_format": "padns",
                "prefer": "result",
                "with_metadata": True,
                "max_wait": 20,
                "skip": 20,
                "limit": 100,
            }
        ]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_responses.FORWARD_PADNS_LOOKUP_VALID_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}"
            f"{self.run_job_endpoint}"
            "?netmask=32&subdomains=1&regex=%5Esil%5B%5B%3Aalpha%3A%5D%5D%7B3%7D%5C.%5Ba-z%5D%7B2%2C%7D%24"
            "&match=strict&first_seen_after=1625834953&first_seen_before=2021-07-09"
            "&last_seen_after=2021-07-09&last_seen_before=1625834953&as_of=-172800"
            "&sort=last_seen%2Fdesc%26sort%3Danswer%2Fasc&output_format=padns"
            "&prefer=result&with_metadata=1&max_wait=20&skip=20&limit=100",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
        )

    def test_forward_padns_lookup_invalid(self, mock_get):
        """Test the invalid case for the forward padns lookup action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "qtype": "a",
                "qname": "domain",
                "netmask": 32,
                "subdomains": True,
                "match": "strict",
                "first_seen_after": "1625834953",
                "first_seen_before": "2021-07-09",
                "last_seen_after": "2021-07-09",
                "last_seen_before": "1625834953",
                "as_of": "-172800",
                "sort": SORT,
                "output_format": "padns",
                "prefer": "result",
                "with_metadata": True,
                "max_wait": 20,
                "skip": 20,
                "limit": 100,
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
            f"{self.test_json['config']['base_url']}"
            f"{self.run_job_endpoint.replace('8.8.8.8', 'domain')}"
            "?netmask=32&subdomains=1&match=strict&first_seen_after=1625834953"
            "&first_seen_before=2021-07-09&last_seen_after=2021-07-09"
            "&last_seen_before=1625834953&as_of=-172800&sort=last_seen%2Fdesc"
            "&output_format=padns&prefer=result&with_metadata=1&max_wait=20"
            "&skip=20&limit=100",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
        )

    def test_forward_padns_lookup_netmask_type_invalid(self, mock_get):
        """Test the invalid type case for the forward padns lookup action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "qtype": "mx",
                "qname": "silentpush.com",
                "netmask": -10,
                "subdomains": True,
                "regex": DOMAIN_REGEX,
                "match": "Strict",
                "first_seen_after": "1625834953",
                "first_seen_before": "2021-07-09",
                "last_seen_after": "-172800",
                "last_seen_before": "1625834953",
                "as_of": "2021-07-09",
                "sort": SORT,
                "output_format": "PADNS",
                "prefer": "Result",
                "with_metadata": True,
                "max_wait": 20,
                "skip": 20,
                "limit": 100,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_forward_padns_lookup_match_value_invalid(self, mock_get):
        """Test the invalid case for the forward padns lookup action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "qtype": "a",
                "qname": "8.8.8.8",
                "netmask": 32,
                "subdomains": True,
                "match": INVALID_VALUE_LIST,
                "first_seen_after": "1625834953",
                "first_seen_before": "2021-07-09",
                "last_seen_after": "2021-07-09",
                "last_seen_before": "1625834953",
                "as_of": "-172800",
                "sort": SORT,
                "output_format": "PADNS",
                "prefer": "Result",
                "with_metadata": True,
                "max_wait": 20,
                "skip": 20,
                "limit": 100,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_forward_padns_lookup_output_format_value_invalid(self, mock_get):
        """Test the invalid case for the forward padns lookup action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "qtype": "a",
                "qname": "8.8.8.8",
                "netmask": 32,
                "subdomains": True,
                "match": "strict",
                "first_seen_after": "1625834953",
                "first_seen_before": "2021-07-09",
                "last_seen_after": "-172800",
                "last_seen_before": "1625834953",
                "as_of": "2021-07-09",
                "sort": SORT,
                "output_format": INVALID_VALUE_LIST,
                "prefer": "Result",
                "with_metadata": True,
                "max_wait": 20,
                "skip": 20,
                "limit": 100,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_forward_padns_lookup_prefer_value_invalid(self, mock_get):
        """Test the invalid case for the forward padns lookup action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "qtype": "a",
                "qname": "8.8.8.8",
                "netmask": 32,
                "subdomains": True,
                "match": "strict",
                "first_seen_after": "1625834953",
                "first_seen_before": "2021-07-09",
                "last_seen_after": "-172800",
                "last_seen_before": "1625834953",
                "as_of": "2021-07-09",
                "sort": SORT,
                "output_format": "PADNS",
                "prefer": INVALID_VALUE_LIST,
                "with_metadata": True,
                "max_wait": 20,
                "skip": 20,
                "limit": 100,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_forward_padns_lookup_max_wait_type_invalid(self, mock_get):
        """Test the invalid type case for the forward padns lookup action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "qtype": "a",
                "qname": "8.8.8.8",
                "netmask": 32,
                "subdomains": True,
                "regex": DOMAIN_REGEX,
                "match": "strict",
                "first_seen_after": "1625834953",
                "first_seen_before": "2021-07-09",
                "last_seen_after": "-172800",
                "last_seen_before": "1625834953",
                "as_of": "2021-07-09",
                "sort": SORT,
                "output_format": "padns",
                "prefer": "result",
                "with_metadata": True,
                "max_wait": -10,
                "skip": 20,
                "limit": 100,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_forward_padns_lookup_skip_type_invalid(self, mock_get):
        """Test the invalid type case for the forward padns lookup action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "qtype": "a",
                "qname": "8.8.8.8",
                "netmask": 32,
                "subdomains": True,
                "match": "Strict",
                "first_seen_after": "1625834953",
                "first_seen_before": "2021-07-09",
                "last_seen_after": "-172800",
                "last_seen_before": "1625834953",
                "as_of": "2021-07-09",
                "sort": SORT,
                "output_format": "padns",
                "prefer": "result",
                "with_metadata": True,
                "max_wait": 20,
                "skip": -10,
                "limit": 100,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_forward_padns_lookup_limit_type_invalid(self, mock_get):
        """Test the invalid type case for the forward padns lookup action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "qtype": "a",
                "qname": "8.8.8.8",
                "netmask": 32,
                "subdomains": True,
                "match": "strict",
                "first_seen_after": "1625834953",
                "first_seen_before": "2021-07-09",
                "last_seen_after": "-172800",
                "last_seen_before": "1625834953",
                "as_of": "2021-07-09",
                "sort": SORT,
                "output_format": "padns",
                "prefer": "result",
                "with_metadata": True,
                "max_wait": 20,
                "skip": 20,
                "limit": -10,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_forward_padns_lookup_qtype_value_invalid(self, mock_get):
        """Test the invalid type case for the forward padns lookup action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "qtype": INVALID_VALUE_LIST,
                "qname": "8.8.8.8",
                "netmask": 32,
                "subdomains": True,
                "match": "strict",
                "first_seen_after": "1625834953",
                "first_seen_before": "2021-07-09",
                "last_seen_after": "-172800",
                "last_seen_before": "1625834953",
                "as_of": "2021-07-09",
                "sort": SORT,
                "output_format": "padns",
                "prefer": "result",
                "with_metadata": True,
                "max_wait": 20,
                "skip": 20,
                "limit": -10,
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_forward_padns_sort_empty_valid(self, mock_get):
        """Test the invalid type case for the forward padns lookup action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {
                "qtype": "a",
                "qname": "8.8.8.8",
                "netmask": 32,
                "subdomains": False,
                "match": "strict",
                "first_seen_after": "1625834953",
                "first_seen_before": "2021-07-09",
                "last_seen_after": "2021-08-09",
                "last_seen_before": "1625834953",
                "as_of": "-172800",
                "sort": ",,,,,,,",
                "output_format": "padns",
                "prefer": "result",
                "with_metadata": True,
                "max_wait": 20,
                "skip": 20,
                "limit": 10,
            }
        ]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_responses.FORWARD_PADNS_LOOKUP_VALID_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}"
            f"{self.run_job_endpoint}"
            "?netmask=32&subdomains=0&match=strict&first_seen_after=1625834953"
            "&first_seen_before=2021-07-09&last_seen_after=2021-08-09"
            "&last_seen_before=1625834953&as_of=-172800&output_format=padns"
            "&prefer=result&with_metadata=1&max_wait=20&skip=20&limit=10",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
        )
