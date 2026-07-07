"""Unit test file for remove note."""
# File: test_vectraxdr_remove_note.py
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


class RemoveNoteAction(unittest.TestCase):
    """Class to test the remove note action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = VectraxdrConnector()
        self.test_json = dict()
        self.test_json = dict(vectraxdr_config.TEST_JSON)
        self.test_json.update({"action": "remove note", "identifier": "remove_note"})

        return super().setUp()

    @patch("vectraxdr_utils.requests.delete")
    def test_remove_note_pass(self, mock_delete):
        """Test the valid case for the remove note action.

        Token is available in the state file.
        Patch the delete() to return the valid response.
        """
        vectraxdr_config.set_state_file(Token=True)
        self.test_json["parameters"] = [{"entity_id": 212, "entity_type": "host", "note_id": 123}]

        mock_delete.return_value.status_code = 204
        mock_delete.return_value.headers = {"Content-Type": vectraxdr_config.CONTENT_HTML_TYPE}
        mock_delete.return_value.json.return_value = ""

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

    @patch("vectraxdr_utils.requests.delete")
    def test_remove_note_notexist_note_id(self, mock_delete):
        """Test the notexidt note id case for the remove note action.

        Token is available in the state file.
        Patch the delete() to return the valid response.
        """
        vectraxdr_config.set_state_file(Token=True)
        self.test_json["parameters"] = [{"entity_id": 212, "entity_type": "host", "note_id": 456}]

        mock_delete.return_value.status_code = 404
        mock_delete.return_value.headers = {"Content-Type": vectraxdr_config.CONTENT_HTML_TYPE}
        mock_delete.return_value.json.return_value = vectra_responses.REMOVE_NOTE_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    def test_remove_note_invalid_entity_type(self):
        """Test the invalid case for the remove note action.

        Token is available in the state file.
        Patch the delete() to return the valid response.
        """
        vectraxdr_config.set_state_file(Token=True)
        self.test_json["parameters"] = [{"entity_type": "account_not_present", "entity_id": 1, "note_id": 123}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
