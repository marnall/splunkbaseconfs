"""Unit test file for resolve assignment."""
# File: test_vectraxdr_resolve_assignment.py
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


class ResolveAssignmentAction(unittest.TestCase):
    """Class to test the resolve assignment action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = VectraxdrConnector()
        self.test_json = dict()
        self.test_json = dict(vectraxdr_config.TEST_JSON)
        self.test_json.update({"action": "resolve assignment", "identifier": "resolve_assignment"})

        return super().setUp()

    @patch("vectraxdr_utils.requests.get")
    @patch("vectraxdr_utils.requests.put")
    def test_resolve_assignment_pass(self, mock_put, mock_get):
        """Test the valid case for the resolve assignment action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        vectraxdr_config.set_state_file(Token=True)
        self.test_json["parameters"] = [
            {"assignment_id": 212, "outcome": "Benign True Positive", "note": "Test Note", "triage_as": "Test", "detection_ids": "1000,1001"}
        ]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = vectra_responses.OUTCOMES_VALID

        mock_put.return_value.status_code = 200
        mock_put.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_put.return_value.json.return_value = vectra_responses.RESOLVE_ASSIGNMENT_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

    @patch("vectraxdr_utils.requests.put")
    @patch("vectraxdr_utils.requests.get")
    def test_resolve_assignment_notexist_assignment_id(self, mock_put, mock_get):
        """Test the notexidt note id case for the resolve assignment action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        vectraxdr_config.set_state_file(Token=True)
        self.test_json["parameters"] = [
            {"assignment_id": 21112, "outcome": "Benign True Positive", "note": "Test Note", "triage_as": "Test", "detection_ids": "1000,1001"}
        ]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = vectra_responses.OUTCOMES_VALID

        mock_put.return_value.status_code = 404
        mock_put.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_put.return_value.json.return_value = vectra_responses.NOT_FOUND_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    @patch("vectraxdr_utils.requests.get")
    @patch("vectraxdr_utils.requests.put")
    def test_resolve_assignment_invalid_outcome(self, mock_put, mock_get):
        """Test the notexist user id case for the resolve assignment action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        vectraxdr_config.set_state_file(Token=True)
        self.test_json["parameters"] = [
            {"assignment_id": 212, "outcome": "False True", "note": "Test Note", "triage_as": "Test", "detection_ids": "1000,1001"}
        ]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = vectra_responses.OUTCOMES_VALID

        mock_put.return_value.status_code = 400
        mock_put.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_put.return_value.json.return_value = vectra_responses.ADD_ASSIGNMENT_INVALID_USER_ID_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    @patch("vectraxdr_utils.requests.get")
    @patch("vectraxdr_utils.requests.put")
    def test_resolve_assignment_invalid_detection_ids(self, mock_put, mock_get):
        """Test the notexist user id case for the resolve assignment action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        vectraxdr_config.set_state_file(Token=True)
        self.test_json["parameters"] = [
            {
                "assignment_id": 212,
                "outcome": "Benign True Positive",
                "note": "Test Note",
                "triage_as": "Test",
                "detection_ids": "detection1, detection2",
            }
        ]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = vectra_responses.OUTCOMES_VALID

        mock_put.return_value.status_code = 400
        mock_put.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_put.return_value.json.return_value = vectra_responses.ADD_ASSIGNMENT_INVALID_USER_ID_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    @patch("vectraxdr_utils.requests.get")
    @patch("vectraxdr_utils.requests.put")
    def test_resolve_assignment_notpresent_detection_ids(self, mock_put, mock_get):
        """Test the notexist user id case for the resolve assignment action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        vectraxdr_config.set_state_file(Token=True)
        self.test_json["parameters"] = [
            {"assignment_id": 212, "outcome": "Benign True Positive", "note": "Test Note", "triage_as": "Test", "detection_ids": "12345, 67890"}
        ]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = vectra_responses.OUTCOMES_VALID

        mock_put.return_value.status_code = 400
        mock_put.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_put.return_value.json.return_value = vectra_responses.DETECTION_ID_NOT_EXIST

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
