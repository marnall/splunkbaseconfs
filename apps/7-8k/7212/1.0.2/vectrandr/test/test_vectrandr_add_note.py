# File: test_vectrandr_add_note.py
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


class AddNoteAction(unittest.TestCase):
    """Class to test the Add note action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = VectraNDRConnector()
        self.test_json = dict()
        self.test_json = dict(vectrandr_config.TEST_JSON)
        self.test_json.update({"action": "add note", "identifier": "add_note"})

        return super().setUp()

    @patch("vectrandr_utils.requests.post")
    def test_add_note_pass(self, mock_post):
        """Test the valid case for the add note action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        self.test_json["parameters"] = [{"object_id": 212, "object_type": "host", "note": "test note"}]

        mock_post.return_value.status_code = 200
        mock_post.return_value.headers = vectrandr_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = vectrandr_responses.CREATE_NOTE_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

    @patch("vectrandr_utils.requests.post")
    def test_add_note_notexist_object_id(self, mock_post):
        """Test the notexist enity id case for the add tags action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        self.test_json["parameters"] = [{"object_id": 21123445552, "object_type": "host", "note": "test note"}]

        mock_post.return_value.status_code = 404
        mock_post.return_value.json.return_value = ""

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_add_note_invalid_object_type(self):
        """Test the invalid case for the add tags action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        self.test_json["parameters"] = [{"object_type": "account_not_present", "object_id": 1, "note": "test note"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
