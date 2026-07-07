# File: test_cofensevision_get_message_search_results.py
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


VALID_PARAMETERS = {"id": "4852", "page": 0, "size": 50, "sort": "processedOn:asc"}

EXPECTED_PARAMETERS = {"page": 0, "size": 50, "sort": ["processedOn,asc"]}


class TestGetMessageSearchResultsAction(unittest.TestCase):
    """Class to test the get message search results action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "get messagesearch results", "identifier": "get_message_search_results"})
        return super().setUp()

    @patch("cofensevision_utils.requests.get")
    def test_get_message_search_results_pass(self, mock_get):
        """Test the valid case for the get message search results action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [VALID_PARAMETERS]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = cofensevision_config.ACTION_HEADER
        mock_get.return_value.json.return_value = {"messages": [{"dummy": "data"}]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")
        self.assertGreater(ret_val["result_data"][0]["summary"]["total_results"], 0)

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE_SEARCH}/{VALID_PARAMETERS['id']}/results",
            headers=cofensevision_config.ACTION_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            params=EXPECTED_PARAMETERS,
        )

    @patch("cofensevision_utils.requests.get")
    def test_get_message_search_results_server_fail(self, mock_get):
        """Test the invalid case for the get message search results action.

        Patch the get() to return the error response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        self.test_json["parameters"] = [VALID_PARAMETERS]

        mock_get.return_value.status_code = 500
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"error": "Internal server error"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Error from server. Status code: 500", ret_val["result_data"][0]["message"])

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE_SEARCH}/{VALID_PARAMETERS['id']}/results",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=cofensevision_config.ACTION_HEADER,
            params=EXPECTED_PARAMETERS,
        )

    @patch("cofensevision_utils.requests.get")
    def test_get_message_search_results_empty_response_fail(self, mock_get):
        """Test the empty response case for the get message search results action.

        Patch the get() to return the error response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        self.test_json["parameters"] = [VALID_PARAMETERS]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = {}
        mock_get.return_value.text = ""

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], "The server returned an unexpected empty response")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE_SEARCH}/{VALID_PARAMETERS['id']}/results",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=cofensevision_config.ACTION_HEADER,
            params=EXPECTED_PARAMETERS,
        )

    def test_get_message_search_results_invalid_id_fail(self):
        """Test the get message search results action with invalid 'id' parameter.

        Token is available in the state file.
        """
        # Save the state file with the invalid JSON string.
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"id": "non_numeric"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_INT_PARAM.format(key="id"))

    def test_get_message_search_results_invalid_page_fail(self):
        """Test the get message search results action with invalid 'page' parameter.

        Token is available in the state file.
        """
        # Save the state file with the invalid JSON string.
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"page": "non_numeric", "id": "4852"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_INT_PARAM.format(key="page"))

    def test_get_message_search_results_invalid_size_fail(self):
        """Test the get message search results action with invalid 'size' parameter.

        Token is available in the state file.
        """
        # Save the state file with the invalid JSON string.
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"size": "non_numeric", "id": "4852"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_INT_PARAM.format(key="size"))

    def test_get_message_search_results_invalid_sort_format_fail(self):
        """Test the get message search results action with invalid 'sort' parameter.

        Token is available in the state file.
        """
        # Save the state file with the invalid JSON string.
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"sort": "createdOn,asc", "id": "4852"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("sort"))

    def test_get_message_search_results_invalid_sort_field_fail(self):
        """Test the get message search results action with invalid 'sort' parameter.

        Token is available in the state file.
        """
        # Save the state file with the invalid JSON string.
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"sort": "createdDate:asc", "id": "4852"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("sort"))
