# File: test_cofensevision_list_message_searches.py
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
from unittest.mock import patch

import cofensevision_consts as consts
from cofensevision_connector import CofenseVisionConnector
from tests import cofensevision_config


class TestListMessageSearchesAction(unittest.TestCase):
    """Class to test the List Message Searches action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "list message searches", "identifier": "list_message_searches"})

        return super().setUp()

    @patch("cofensevision_utils.requests.get")
    def test_list_message_searches_pass(self, mock_get):
        """Test the valid case for the list message searches action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"page": 0, "size": 50, "sort": "createdDate:desc  ,, ,id"}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"searches": [{"dummy": "data"}]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Total message searches: 1")

        expected_params = {
            "page": 0,
            "size": 50,
            "sort": ["createdDate,desc", "id"],
        }

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE_SEARCH}",
            headers=cofensevision_config.ACTION_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            params=expected_params,
            verify=False,
        )

    def test_list_message_searches_invalid_page_fail(self):
        """Test the list message searches action with invalid 'page' parameter.

        Test the invalid state file format. Code should reset the state file.
        """
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

    def test_list_message_searches_invalid_size_fail(self):
        """Test the list message searches action with invalid 'size' parameter.

        Test the different client id in the state file. Code should pop the token from the state file.
        """
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

    def test_list_message_searches_invalid_sort_fail(self):
        """Test the list message searches action with invalid 'sort' parameter."""
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

    @patch("cofensevision_utils.requests.get")
    def test_list_message_searches_server_fail(self, mock_get):
        """Test the invalid case for the list message searches action.

        Patch the get() to return the error response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{}]

        mock_get.return_value.status_code = 500
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"error": "Internal server error"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Error from server. Status code: 500", ret_val["result_data"][0]["message"])

        expected_params = {
            "page": 0,
            "size": 50,
        }

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE_SEARCH}",
            headers=cofensevision_config.ACTION_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            params=expected_params,
            verify=False,
        )

    @patch("cofensevision_utils.requests.get")
    def test_list_message_searches_empty_response_fail(self, mock_get):
        """Test the invalid case for the list message searches action.

        Patch the get() to return the empty response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = {}
        mock_get.return_value.text = ""

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], "The server returned an unexpected empty response")

        expected_params = {
            "page": 0,
            "size": 50,
        }

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE_SEARCH}",
            headers=cofensevision_config.ACTION_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            params=expected_params,
            verify=False,
        )
