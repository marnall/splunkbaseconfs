# File: test_cofensevision_list_quarantine_jobs.py
#
# Copyright (c) 2023-2026 Cofense
#
# This unpublished material is proprietary to Cofense.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Cofense.
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

import requests

import cofensevision_consts as consts
from cofensevision_connector import CofenseVisionConnector
from tests import cofensevision_config


class TestListQuarantineJobsAction(unittest.TestCase):
    """Class to test the List Quarantine Jobs action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "list quarantine jobs", "identifier": "list_quarantine_jobs"})

        return super().setUp()

    @patch("cofensevision_utils.requests.post")
    def test_list_quarantine_jobs_pass(self, mock_post):
        """Test the valid case for the list quarantine jobs action.

        Token is available in the state file.
        Patch the post() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [
            {
                "auto_quarantine": True,
                "exclude_quarantine_emails": True,
                "exclude_status": "NEW,QUEUED",
                "include_status": "COMPLETED,,FAILED",
                "iocs": "b93cba4829a00dabef96036bb6765d20 , , 07fa1e91f99050521a87edc784e83fd5",
                "modified_date_after": "2020-08-31",
                "page": 0,
                "size": 50,
                "sort": "createdDate:desc  ,, ,id:asc",
                "sources": "Vision-UI,Intelligence,Triage-1,Vision-UI,Triage-1",
            }
        ]

        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"quarantineJobs": [{"dummy": "data"}, {"dummy": "data2"}]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Total quarantine jobs: 2")

        expected_data = {
            "filterOptions": {
                "autoQuarantine": True,
                "iocs": [
                    "b93cba4829a00dabef96036bb6765d20",  # pragma: allowlist secret
                    "07fa1e91f99050521a87edc784e83fd5",  # pragma: allowlist secret
                ],
                "sources": ["Vision-UI", "Intelligence", "Triage-1"],
                "includeStatus": ["COMPLETED", "FAILED"],
                "excludeStatus": ["NEW", "QUEUED"],
                "modifiedDateAfter": "2020-08-31T00:00:00.000000Z",
            }
        }
        expected_params = {
            "excludeQuarantineEmails": True,
            "page": 0,
            "size": 50,
            "sort": ["createdDate,desc", "id,asc"],
        }

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_FILTER_JOBS}",
            headers=cofensevision_config.ACTION_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            params=expected_params,
            data=json.dumps(expected_data),
            verify=False,
        )

    @patch("cofensevision_utils.requests.post")
    def test_list_quarantine_jobs_expired_token_pass(self, mock_post):
        """Test the valid case for the list quarantine jobs action.

        Token is available in the state file but it is expired.
        Patch the post() to return the valid responses.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"auto_quarantine": True, "exclude_quarantine_emails": True}]

        post_response_1 = requests.Response()
        post_response_1._content = b'{"error": "invalid_token", "error_description": "<dummy_token>"}'
        post_response_1.status_code = 401
        post_response_1.headers = cofensevision_config.DEFAULT_HEADERS

        post_response_2 = requests.Response()
        post_response_2._content = b'{"access_token": "<dummy_token>"}'
        post_response_2.status_code = 200
        post_response_2.headers = cofensevision_config.DEFAULT_HEADERS

        post_response_3 = requests.Response()
        post_response_3._content = b'{"quarantineJobs": [{"dummy": "data"}]}'
        post_response_3.status_code = 200
        post_response_3.headers = cofensevision_config.DEFAULT_HEADERS

        mock_post.side_effect = [post_response_1, post_response_2, post_response_3]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Total quarantine jobs: 1")

        expected_data = {
            "filterOptions": {
                "autoQuarantine": True,
            }
        }
        expected_params = {
            "excludeQuarantineEmails": True,
            "page": 0,
            "size": 50,
        }
        expected_calls = [
            call(
                f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_FILTER_JOBS}",
                timeout=consts.VISION_REQUEST_TIMEOUT,
                verify=False,
                headers=cofensevision_config.ACTION_HEADER,
                params=expected_params,
                data=json.dumps(expected_data),
            ),
            call(
                f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_TOKEN}",
                timeout=consts.VISION_REQUEST_TIMEOUT,
                verify=False,
                data=cofensevision_config.TOKEN_DATA,
                headers=cofensevision_config.TOKEN_HEADER,
            ),
            call(
                f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_FILTER_JOBS}",
                timeout=consts.VISION_REQUEST_TIMEOUT,
                verify=False,
                headers=cofensevision_config.ACTION_HEADER,
                params=expected_params,
                data=json.dumps(expected_data),
            ),
        ]
        mock_post.assert_has_calls(expected_calls)

    @patch("cofensevision_utils.requests.post")
    def test_list_quarantine_jobs_no_token_pass(self, mock_post):
        """Test the valid case for the list quarantine jobs action.

        Token is not available in the state file.
        Patch the post() to return the valid responses.
        """
        cofensevision_config.set_state_file(client_id=True)

        self.test_json["parameters"] = [{"auto_quarantine": True, "exclude_quarantine_emails": True}]

        post_response_1 = requests.Response()
        post_response_1._content = b'{"access_token": "<dummy_token>"}'
        post_response_1.status_code = 200
        post_response_1.headers = cofensevision_config.DEFAULT_HEADERS

        post_response_2 = requests.Response()
        post_response_2._content = b'{"quarantineJobs": [{"dummy": "data"}]}'
        post_response_2.status_code = 200
        post_response_2.headers = cofensevision_config.DEFAULT_HEADERS

        mock_post.side_effect = [post_response_1, post_response_2]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Total quarantine jobs: 1")

        expected_data = {
            "filterOptions": {
                "autoQuarantine": True,
            }
        }
        expected_params = {
            "excludeQuarantineEmails": True,
            "page": 0,
            "size": 50,
        }
        expected_calls = [
            call(
                f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_TOKEN}",
                timeout=consts.VISION_REQUEST_TIMEOUT,
                verify=False,
                data=cofensevision_config.TOKEN_DATA,
                headers=cofensevision_config.TOKEN_HEADER,
            ),
            call(
                f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_FILTER_JOBS}",
                timeout=consts.VISION_REQUEST_TIMEOUT,
                verify=False,
                headers=cofensevision_config.ACTION_HEADER,
                params=expected_params,
                data=json.dumps(expected_data),
            ),
        ]
        mock_post.assert_has_calls(expected_calls)

    def test_list_quarantine_jobs_invalid_page_fail(self):
        """Test the list quarantine jobs action with invalid 'page' parameter.

        Test the invalid state file format. Code should reset the state file.
        """
        # Save the state file with the invalid JSON string.
        cofensevision_config.set_state_file(raw="Invalid state file")

        self.test_json["parameters"] = [
            {
                "page": "non_numeric",
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], "Please provide a valid integer value in the 'page' parameter")

    def test_list_quarantine_jobs_invalid_size_fail(self):
        """Test the list quarantine jobs action with invalid 'size' parameter.

        Test the different client id in the state file. Code should pop the token from the state file.
        """
        # Save the state file with the different client id, token should be removed in the code.
        cofensevision_config.set_state_file(raw='{"client_id": "<other_id>", "token": "This should be popped!"}')

        self.test_json["parameters"] = [
            {
                "size": "non_numeric",
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], "Please provide a valid integer value in the 'size' parameter")

    def test_list_quarantine_jobs_invalid_sort_fail(self):
        """Test the list quarantine jobs action with invalid 'sort' parameter."""
        self.test_json["parameters"] = [
            {
                "sort": "invalid,format",
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("sort"))

    def test_list_quarantine_jobs_invalid_date_fail(self):
        """Test the list quarantine jobs action with invalid 'modified date after' parameter."""
        self.test_json["parameters"] = [
            {
                "modified_date_after": "invalid_date",
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("modified date after"))

    def test_list_quarantine_jobs_invalid_include_status_fail(self):
        """Test the list quarantine jobs action with invalid 'include status' parameter.

        Test the invalid state file format. Code should reset the state file.
        """
        self.test_json["parameters"] = [
            {
                "include_status": "NEw,QUEUED",  # API is case sensitive
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(
            ret_val["result_data"][0]["message"], consts.VISION_ERROR_VALUE_LIST.format("include status", ", ".join(consts.VISION_JOB_STATUS))
        )

    def test_list_quarantine_jobs_invalid_exclude_status_fail(self):
        """Test the list quarantine jobs action with invalid 'exclude status' parameter.

        Test the invalid state file format. Code should reset the state file.
        """
        self.test_json["parameters"] = [
            {
                "exclude_status": "NEw,QUEUED",  # API is case sensitive
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(
            ret_val["result_data"][0]["message"], consts.VISION_ERROR_VALUE_LIST.format("exclude status", ", ".join(consts.VISION_JOB_STATUS))
        )

    @patch("cofensevision_utils.requests.post")
    def test_list_quarantine_jobs_server_fail(self, mock_post):
        """Test the invalid case for the list quarantine jobs action.

        Patch the post() to return the error response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{}]

        mock_post.return_value.status_code = 500
        mock_post.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {"error": "Internal server error"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Error from server. Status code: 500", ret_val["result_data"][0]["message"])

        expected_data = {
            "filterOptions": {
                "autoQuarantine": False,
            }
        }
        expected_params = {
            "excludeQuarantineEmails": False,
            "page": 0,
            "size": 50,
        }

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_FILTER_JOBS}",
            headers=cofensevision_config.ACTION_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            params=expected_params,
            data=json.dumps(expected_data),
            verify=False,
        )

    @patch("cofensevision_utils.requests.post")
    def test_list_quarantine_jobs_empty_response_fail(self, mock_post):
        """Test the invalid case for the list quarantine jobs action.

        Patch the post() to return the empty response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{}]

        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = {}
        mock_post.return_value.text = ""

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], "The server returned an unexpected empty response")

        expected_data = {
            "filterOptions": {
                "autoQuarantine": False,
            }
        }
        expected_params = {
            "excludeQuarantineEmails": False,
            "page": 0,
            "size": 50,
        }

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_FILTER_JOBS}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=cofensevision_config.ACTION_HEADER,
            params=expected_params,
            data=json.dumps(expected_data),
        )
