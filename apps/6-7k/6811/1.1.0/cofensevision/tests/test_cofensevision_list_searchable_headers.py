# File: test_cofensevision_list_searchable_headers.py
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


class TestListSearchableHeadersAction(unittest.TestCase):
    """Class to test the list searchable headers action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "list searchable headers", "identifier": "list_searchable_headers"})

        return super().setUp()

    @patch("cofensevision_utils.requests.get")
    def test_list_searchable_headers_pass(self, mock_get):
        """Test the valid case for the list searchable headers action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        self.test_json["parameters"] = [{}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"headers": ["dummy", "data"]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_SEARCHABLE_HEADER}",
            headers=cofensevision_config.ACTION_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )

    @patch("cofensevision_utils.requests.get")
    def test_list_searchable_headers_invalid(self, mock_get):
        """Test the list searchable headers action with unauthorized error.

        Token is available in the state file.
        Patch the get() to return the unauthorized response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        self.test_json["parameters"] = [{}]

        mock_get.return_value.status_code = 401
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"error": "UNAUTHORIZED", "error_description": "reason"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Status code: 401", ret_val["result_data"][0]["message"])

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_SEARCHABLE_HEADER}",
            headers=cofensevision_config.ACTION_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )
