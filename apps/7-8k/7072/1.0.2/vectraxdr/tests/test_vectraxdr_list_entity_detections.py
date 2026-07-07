"""Unit test file for list entity detections action."""
# File: test_vectraxdr_list_entity_detections.py
#
# Copyright (c) 2023-2025 Vectra
#
# This unpublished material is proprietary to Vectra.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Vectra.
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

from vectraxdr_connector import VectraxdrConnector

from . import vectra_responses, vectraxdr_config


class ListEntityDetectionsAction(unittest.TestCase):
    """Class to test the list entity detections action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = VectraxdrConnector()
        self.test_json = dict()
        self.test_json = dict(vectraxdr_config.TEST_JSON)
        self.test_json.update({"action": "list entity detections", "identifier": "list_entity_detections"})

        return super().setUp()

    @patch("vectraxdr_utils.requests.get")
    def test_list_entity_detections_pass(self, mock_get):
        """Test the valid case for the list entity detections action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """

        # Define the side_effect function
        def mock_get_response(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "")
            if "entities" in url:
                return MockResponse(status_code=200, headers=vectraxdr_config.DEFAULT_HEADERS, text=vectra_responses.GET_ENTITY)
            elif "detections" in url:
                return MockResponse(status_code=200, headers=vectraxdr_config.DEFAULT_HEADERS, text=vectra_responses.GET_DETECTION)

        vectraxdr_config.set_state_file(Token=True)
        self.test_json["parameters"] = [{"entity_id": 100, "entity_type": "host"}]

        mock_get.side_effect = mock_get_response

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

    @patch("vectraxdr_utils.requests.get")
    def test_list_entity_detections_entity_id_notexist(self, mock_get):
        """Test the invalid case for the list entity detections action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """

        # Define the side_effect function
        def mock_get_response(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "")
            if "entities" in url:
                return MockResponse(status_code=404, headers=vectraxdr_config.DEFAULT_HEADERS, text=vectra_responses.NOT_EXISTS_ENTITY)
            elif "detections" in url:
                return MockResponse(status_code=200, headers=vectraxdr_config.DEFAULT_HEADERS, text=vectra_responses.GET_DETECTION)

        vectraxdr_config.set_state_file(Token=True)
        self.test_json["parameters"] = [{"entity_id": 1000, "entity_type": "host"}]

        mock_get.side_effect = mock_get_response

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_list_entity_detections_entity_type_invalid(self):
        """Test the invalid case for the list entity detections action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        # Define the side_effect function
        vectraxdr_config.set_state_file(Token=True)
        self.test_json["parameters"] = [{"entity_id": 1000, "entity_type": "invalid_host"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")


# Helper class to create a mock response object
class MockResponse:
    """A helper class to create a mock response object for testing purposes.

    This class is used to simulate HTTP responses during unit tests for functions
    that make API requests using libraries like `requests`.

    Attributes:
        status_code (int): The HTTP status code of the mock response.
        text (str): The content of the mock response as a string.
    """

    def __init__(self, status_code, text):
        """Initialize a new MockResponse object.

        Args:
            status_code (int): The HTTP status code of the mock response.
            text (str): The content of the mock response as a string.
        """
        self.status_code = status_code
        self.text = text

    def json(self):
        """Parse the content of the mock response as JSON.

        Returns:
            dict: A dictionary representation of the JSON content.
        """
        return json.loads(self.text)
