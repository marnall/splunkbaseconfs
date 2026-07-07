# File: test_silentpush_list_ip_information.py
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
from unittest.mock import call, patch

from parameterized import parameterized

import silentpush_consts as consts
from silentpush_connector import SilentpushConnector

from . import silentpush_constant, silentpush_responses


@patch("silentpush_utils.requests.post")
class SilentpushAction(unittest.TestCase):
    """Class to test the list ip information action."""

    def setUp(self):
        self.connector = SilentpushConnector()
        self.test_json = dict(silentpush_constant.TEST_JSON)
        self.test_json["config"] = {
            **self.test_json["config"],
            **silentpush_constant.APIKEY_AUTH_CONFIG,
        }
        self.test_json.update({"action": "list ip information", "identifier": "list_ip_information"})
        self.run_job_endpoint = consts.LIST_IP_INFORMATION_ENDPOINT

        return super().setUp()

    def test_list_ip_information_valid(self, mock_post):
        """Test the valid case for the list ip information action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [{"ips": "8.8.8.8, 2001:0db8:85a3:0000:0000:8a2e:0370:7363"}]

        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_post.return_value.json.return_value = silentpush_responses.LIST_IP_INFORMATION_VALID_RESP

        req_data_ipv4 = {"ips": ["8.8.8.8"]}
        req_data_ipv6 = {"ips": ["2001:0db8:85a3:0000:0000:8a2e:0370:7363"]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        expected_calls = [
            call(
                f"{self.test_json['config']['base_url']}{self.run_job_endpoint.replace('{{resource}}', 'ipv4')}",
                timeout=consts.REQUEST_DEFAULT_TIMEOUT,
                verify=False,
                headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
                json=req_data_ipv4,
            ),
            call(
                f"{self.test_json['config']['base_url']}{self.run_job_endpoint.replace('{{resource}}', 'ipv6')}",
                timeout=consts.REQUEST_DEFAULT_TIMEOUT,
                verify=False,
                headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
                json=req_data_ipv6,
            ),
        ]

        mock_post.assert_has_calls(expected_calls, any_order=True)

    @parameterized.expand(
        [
            ["case1", "10.20.5., 8.8.8.8, 2001:db8:3333:4444:5555:6666:7777:8888,"],
            ["case2", "invalid"],
            ["case3", "8.8.8.8, 2001:db8:3333:4444:CCCC:DDDD:EEEE:FFFF:HHHH"],
            ["case4", ",,,,,"],
        ]
    )
    def test_list_ip_information_invalid(self, mock_post, _, ips):
        """Test the invalid case for the list ip information action.

        Patch the post() to run job.
        """
        self.test_json["parameters"][0]["ips"] = ips

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_list_ip_information_invalid_ipv4_response(self, mock_post):
        """Test the invalid case for the list ip information action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [{"ips": "8.8.8.8, 10.10.10.10"}]

        mock_post.return_value.status_code = 400
        mock_post.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_post.return_value.json.return_value = silentpush_responses.LIST_IP_INFORMATION_VALID_RESP

        req_data = {"ips": ["8.8.8.8", "10.10.10.10"]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{self.run_job_endpoint.replace('{{resource}}', 'ipv4')}",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
            json=req_data,
        )

    def test_list_ip_information_invalid_ipv6_response(self, mock_post):
        """Test the invalid case for the list ip information action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [{"ips": "2001:db8:3333:4444:5555:6666:7777:8888, 2001:db8:3333:4444:CCCC:DDDD:EEEE:FFFF"}]

        mock_post.return_value.status_code = 400
        mock_post.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_post.return_value.json.return_value = silentpush_responses.LIST_IP_INFORMATION_VALID_RESP

        req_data = {"ips": ["2001:db8:3333:4444:5555:6666:7777:8888", "2001:db8:3333:4444:CCCC:DDDD:EEEE:FFFF"]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{self.run_job_endpoint.replace('{{resource}}', 'ipv6')}",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
            json=req_data,
        )

    def test_list_ip_information_valid_only_ipv4(self, mock_post):
        """Test the valid case(only ipv4) for the list ip information action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [{"ips": "8.8.8.8, 10.10.10.10"}]

        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_post.return_value.json.return_value = silentpush_responses.LIST_IP_INFORMATION_VALID_RESP

        req_data = {"ips": ["8.8.8.8", "10.10.10.10"]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{self.run_job_endpoint.replace('{{resource}}', 'ipv4')}",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
            json=req_data,
        )

    def test_list_ip_information_valid_only_ipv6(self, mock_post):
        """Test the valid case(only ipv6) for the list ip information action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [{"ips": "2001:db8:3333:4444:5555:6666:7777:8888, 2001:db8:3333:4444:CCCC:DDDD:EEEE:FFFF"}]

        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_post.return_value.json.return_value = silentpush_responses.LIST_IP_INFORMATION_VALID_RESP

        req_data = {
            "ips": [
                "2001:db8:3333:4444:5555:6666:7777:8888",
                "2001:db8:3333:4444:CCCC:DDDD:EEEE:FFFF",
            ]
        }

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{self.run_job_endpoint.replace('{{resource}}', 'ipv6')}",
            timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
            json=req_data,
        )
