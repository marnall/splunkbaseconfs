# File: test_vectrandr_add_assignment.py
#
# Copyright (c) 2024-2025 Vectra
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

from vectrandr_connector import VectraNDRConnector

from . import vectrandr_config, vectrandr_responses


class AddAssignmentAction(unittest.TestCase):
    """Class to test the add assignment action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = VectraNDRConnector()
        self.test_json = dict()
        self.test_json = dict(vectrandr_config.TEST_JSON)
        self.test_json.update({"action": "add assignment", "identifier": "add_assignment"})

        return super().setUp()

    @patch("vectrandr_utils.requests.post")
    def test_add_assignment_pass(self, mock_post):
        """Test the valid case for the add assignment action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        self.test_json["parameters"] = [{"entity_id": 2578, "entity_type": "host", "user_id": 20}]

        mock_post.return_value.status_code = 201
        mock_post.return_value.headers = vectrandr_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = vectrandr_responses.ADD_UPDATE_ASSIGNMENT_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

    @patch("vectrandr_utils.requests.post")
    def test_add_assignment_notexist_entity_id(self, mock_post):
        """Test the invalid case for the add assignment action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        self.test_json["parameters"] = [{"entity_id": 21112, "entity_type": "host", "user_id": 59}]

        mock_post.return_value.status_code = 400
        mock_post.return_value.headers = vectrandr_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = vectrandr_responses.ADD_ASSIGNMENT_INVALID_ENTITY_ID_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    @patch("vectrandr_utils.requests.post")
    def test_add_assignment_notexist_user_id(self, mock_post):
        """Test the notexist user id case for the add assignment action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        self.test_json["parameters"] = [{"entity_id": 2578, "entity_type": "host", "user_id": 55555559}]

        mock_post.return_value.status_code = 400
        mock_post.return_value.headers = vectrandr_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = vectrandr_responses.ADD_ASSIGNMENT_INVALID_USER_ID_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_add_assignment_invalid_entity_type(self):
        """Test the invalid case for the add assignment action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        self.test_json["parameters"] = [{"entity_id": 2578, "entity_type": "account_not_present", "user_id": 59}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
