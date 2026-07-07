"""Unit test file for mark entity detections."""
# File: test_vectraxdr_mark_entity_detections.py
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


class MarkEntityDetectionsAction(unittest.TestCase):
    """Class to test the mark entity detections action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = VectraxdrConnector()
        self.test_json = dict()
        self.test_json = dict(vectraxdr_config.TEST_JSON)
        self.test_json.update({"action": "mark entity detections", "identifier": "mark_entity_detections"})

        return super().setUp()

    @patch("vectraxdr_utils.requests.get")
    @patch("vectraxdr_utils.requests.patch")
    def test_mark_entity_detections_pass(self, mock_patch, mock_get):
        """
        Test the valid case for the mark entity detections action.

        Patch the patch() to return the valid response.
        """
        vectraxdr_config.set_state_file(Token=True)
        self.test_json["parameters"] = [{"entity_type": "account", "entity_id": 1}]

        mock_patch.return_value.status_code = 200
        mock_patch.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_patch.return_value.json.return_value = vectra_responses.MARK_DETECTION
        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = vectra_responses.GET_ENTITY

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["status"], "success")

    @patch("vectraxdr_utils.requests.get")
    def test_mark_entity_detections_invalid_entity_id(self, mock_get):
        """
        Test the fail case for the  mark entity detections action.

        Patch the patch() to return the valid response.
        """
        vectraxdr_config.set_state_file(Token=True)
        self.test_json["parameters"] = [{"entity_type": "account", "entity_id": 0}]

        mock_get.return_value.status_code = 404
        mock_get.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = vectra_responses.NOT_EXISTS_ENTITY

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["status"], "failed")

    @patch("vectraxdr_utils.requests.get")
    def test_mark_entity_detections_invalid_entity_type(self, mock_get):
        """
        Test the fail case for the  mark entity detections action.

        Patch the patch() to return the valid response.
        """
        vectraxdr_config.set_state_file(Token=True)
        self.test_json["parameters"] = [{"entity_type": "account_not_present", "entity_id": 1}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["status"], "failed")

    @patch("vectraxdr_utils.requests.get")
    @patch("vectraxdr_utils.requests.patch")
    def test_mark_entity_detections_with_empty_detection_set(self, mock_patch, mock_get):
        """
        Test the valid case for the mark entity detections action.

        Patch the patch() to return the valid response.
        """
        vectraxdr_config.set_state_file(Token=True)
        self.test_json["parameters"] = [{"entity_type": "account", "entity_id": 2}]

        mock_patch.return_value.status_code = 404
        mock_patch.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_patch.return_value.json.return_value = vectra_responses.MARK_INVALID_DETECTION
        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = vectra_responses.GET_ENTITY_WITH_EMPTY_DETECTION_SET

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["status"], "failed")
