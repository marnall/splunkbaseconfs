"""Unit test file for on poll."""
# File: test_vectraxdr_on_poll.py
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

import phantom.base_connector as base_conn
import requests_mock

import vectraxdr_consts as consts
from vectraxdr_connector import VectraxdrConnector

from . import vectra_responses, vectraxdr_config


class TestOnPollAction(unittest.TestCase):
    """Class to test the on poll action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = VectraxdrConnector()
        # Reset the global object to avoid failures
        base_conn.connector_obj = None

        self.test_json = dict(vectraxdr_config.TEST_JSON)
        self.test_json.update({"action": "on poll", "identifier": "on_poll"})

        return super().setUp()

    @requests_mock.Mocker(real_http=True)
    def test_on_poll_pass(self, mock_get):
        """Test the valid case for the on poll action.

        Token is available in the state file.
        Mock the get() to return the valid response.
        """
        vectraxdr_config.set_state_file(Token=True)

        self.test_json.get("config").update(
            {
                "on_poll_start_time": "2023-05-24T14:13:34",
                "is_entity_prioritized": "all",
                "entity_type": "Account",
                "entity_tags": "test1,test2",
                "detection_category": "Command and Control",
                "detection_type": "test2",
            }
        )
        self.test_json.update({"user_session_token": vectraxdr_config.get_session_id(self.connector)})
        mock_get.get(
            f"{vectraxdr_config.DUMMY_BASE_URL}{consts.VECTRA_API_VERSION}{consts.VECTRA_LIST_ENTITIES}",
            status_code=200,
            headers=vectraxdr_config.DEFAULT_HEADERS,
            json=vectra_responses.GET_ENTITIES_ON_POLL,
        )

        mock_get.get(
            f"{vectraxdr_config.DUMMY_BASE_URL}{consts.VECTRA_API_VERSION}{consts.VECTRA_GET_ASSIGNMENTS}",
            status_code=200,
            headers=vectraxdr_config.DEFAULT_HEADERS,
            json=vectra_responses.GET_ASSIGNMENT_ON_POLL,
        )

        mock_get.get(
            f"{vectraxdr_config.DUMMY_BASE_URL}{consts.VECTRA_API_VERSION}{consts.VECTRA_DETECTIONS_ENDPOINT}",
            status_code=200,
            headers=vectraxdr_config.DEFAULT_HEADERS,
            json=vectra_responses.GET_DETECTION_ON_POLL,
        )

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_data"][0]["status"], "success")
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], ret_val["result_summary"]["total_objects"])

    def test_on_poll_invalid_entity_type(self):
        """Test the valid case for the on poll action.

        Token is available in the state file.
        Mock the get() to return the valid response.
        """
        vectraxdr_config.set_state_file(Token=True)

        self.test_json.get("config").update(
            {
                "on_poll_start_time": "2023-05-24T14:13:34",
                "is_entity_prioritized": "true",
                "entity_type": "invalid",
                "entity_tags": "test1,test2",
                "detection_category": "Command and Control",
                "detection_type": "test2",
                "urgency_score_medium_threshold": 50,
                "urgency_score_low_threshold": 30,
            }
        )
        self.test_json.update({"user_session_token": vectraxdr_config.get_session_id(self.connector)})

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_data"][0]["status"], "failed")
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)

    def test_on_poll_invalid_detection_category(self):
        """Test the valid case for the on poll action.

        Token is available in the state file.
        Mock the get() to return the valid response.
        """
        self.test_json.get("config").update(
            {
                "on_poll_start_time": "2023-05-24T14:13:34",
                "is_entity_prioritized": "all",
                "entity_type": "all",
                "entity_tags": "test1,test2",
                "detection_category": "invalid",
                "detection_type": "test2",
            }
        )
        self.test_json.update({"user_session_token": vectraxdr_config.get_session_id(self.connector)})

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_data"][0]["status"], "failed")
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
