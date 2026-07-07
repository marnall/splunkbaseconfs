# File: test_silentpush_list_domain_information.py
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


class SilentpushAction(unittest.TestCase):
    """Class to test the list domain information action."""

    def setUp(self):
        self.connector = SilentpushConnector()
        self.test_json = dict(silentpush_constant.TEST_JSON)
        self.test_json["config"] = {
            **self.test_json["config"],
            **silentpush_constant.APIKEY_AUTH_CONFIG,
        }
        self.test_json.update(
            {
                "action": "list domain information",
                "identifier": "list_domain_information",
            }
        )
        self.run_domain_info_job_endpoint = consts.LIST_DOMAIN_INFORMATION_ENDPOINT
        self.run_risk_score_job_endpoint = consts.LIST_DOMAIN_ENDPOINT_RISK_SCORE_ENDPOINT
        self.run_whois_info_job_endpoint = consts.LIST_DOMAIN_ENDPOINT_WHOIS_INFO_ENDPOINT

        return super().setUp()

    def test_list_domain_information_valid(self):
        """
        Test the valid case for the list domain information action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domains": "google.com,silentpush.com",
                "fetch_risk_score": True,
                "fetch_whois_info": True,
            }
        ]

        req_data = {"domains": ["google.com", "silentpush.com"]}
        with patch("silentpush_utils.requests.post") as mock_post, patch("silentpush_utils.requests.get") as mock_get:
            mock_post.return_value.status_code = 200
            mock_post.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
            mock_post.return_value.json.return_value = silentpush_responses.LIST_DOMAIN_INFORMATION_DOMAIN_VALID_RESP

            mock_get.return_value.status_code = 200
            mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
            mock_get.return_value.json.return_value = silentpush_responses.LIST_DOMAIN_INFORMATION_WHOIS_VALID_RESP

            ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
            ret_val = json.loads(ret_val)
            self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
            self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
            self.assertEqual(ret_val["status"], "success")

            expected_post_calls = [
                call(
                    f"{self.test_json['config']['base_url']}{self.run_domain_info_job_endpoint}",
                    timeout=consts.REQUEST_DEFAULT_TIMEOUT,
                    verify=False,
                    headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
                    json=req_data,
                ),
                call(
                    f"{self.test_json['config']['base_url']}{self.run_risk_score_job_endpoint}",
                    timeout=consts.REQUEST_DEFAULT_TIMEOUT,
                    verify=False,
                    headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
                    json=req_data,
                ),
            ]
            expected_get_calls = [
                call(
                    f"{self.test_json['config']['base_url']}{self.run_whois_info_job_endpoint.format('google.com')}",
                    timeout=consts.REQUEST_DEFAULT_TIMEOUT,
                    verify=False,
                    headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
                ),
                call(
                    f"{self.test_json['config']['base_url']}{self.run_whois_info_job_endpoint.format('silentpush.com')}",
                    timeout=consts.REQUEST_DEFAULT_TIMEOUT,
                    verify=False,
                    headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
                ),
            ]
            mock_post.assert_has_calls(expected_post_calls, any_order=True)
            mock_get.assert_has_calls(expected_get_calls, any_order=True)

    def test_list_domain_information_invalid(self):
        """
        Test the valid case for the list domain information action.

        Patch the post() to run job.
        """
        self.test_json["parameters"] = [
            {
                "domains": "silent",
                "fetch_risk_score": False,
                "fetch_whois_info": False,
            }
        ]

        req_data = {"domains": ["silent"]}

        with patch("silentpush_utils.requests.post") as mock_post:
            mock_post.return_value.status_code = 400
            mock_post.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
            mock_post.return_value.json.return_value = silentpush_responses.LIST_DOMAIN_INFORMATION_DOMAIN_VALID_RESP

            ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
            ret_val = json.loads(ret_val)
            self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
            self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
            self.assertEqual(ret_val["status"], "failed")

            mock_post.assert_called_with(
                f"{self.test_json['config']['base_url']}{self.run_domain_info_job_endpoint}",
                timeout=consts.REQUEST_DEFAULT_TIMEOUT,
                verify=False,
                headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
                json=req_data,
            )

    @parameterized.expand([["silentpush.com", "test", False], ["silentpush.com", False, "test"], [",,,,", False, False]])
    def test_list_domain_information_boolean_invalid(self, domains, risk_score, whois):
        """
        Test the invalid case for the list domain information action.

        Patch the post() to run job.
        """
        self.test_json["parameters"][0]["domains"] = domains
        self.test_json["parameters"][0]["fetch_risk_score"] = risk_score
        self.test_json["parameters"][0]["fetch_whois_info"] = whois

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
