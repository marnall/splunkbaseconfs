# File: test_vectrandr_on_poll.py
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

import requests_mock
from phantom.action_result import ActionResult

import vectrandr_consts as consts
from vectrandr_connector import VectraNDRConnector

from . import vectrandr_config, vectrandr_responses


class TestOnPollAction(unittest.TestCase):
    """Test the on poll action."""

    def setUp(self):
        """
        Set up the test case.

        :param self: The instance of the test case.
        :return: The result of the set up process.
        """
        self.connector = VectraNDRConnector()
        self.action_result = ActionResult()
        self.test_json = dict(vectrandr_config.TEST_JSON)
        self.test_json.update({"action": "on poll", "identifier": "on_poll"})
        self.connector._BaseConnector__action_name = self.connector.get_action_identifier()

        return super().setUp()

    @requests_mock.Mocker(real_http=True)
    def test_on_poll_pass(self, mock_get):
        """Test the valid case for the on poll action.

        Token is available in the state file.
        Mock the get() to return the valid response.
        """
        self.test_json.get("config").update(
            {
                "on_poll_start_time": "2023-05-24T14:13:34",
                "entity_type": "Host",
                "entity_tags": "ckp",
                "detection_category": "Reconnaissance",
                "detection_type": "Reconnaissance",
            }
        )
        self.test_json.update({"user_session_token": vectrandr_config.get_session_id(self.connector)})
        entity_type = "hosts"
        mock_get.get(
            f"{vectrandr_config.DUMMY_BASE_URL}{consts.VECTRA_API_VERSION}{consts.VECTRA_POLL_ENTITY_ENDPOINT.format(entity_type=entity_type)}",
            status_code=200,
            headers=vectrandr_config.DEFAULT_HEADERS,
            json=vectrandr_responses.GET_ENTITY_POLL_RESP,
        )

        mock_get.get(
            f"{vectrandr_config.DUMMY_BASE_URL}{consts.VECTRA_API_2_2_VERSION}{consts.VECTRA_SEARCH_DETECTIONS_ENDPOINT}",
            status_code=200,
            headers=vectrandr_config.DEFAULT_HEADERS,
            json=vectrandr_responses.GET_DETECTION_POLL_RESP,
        )
        SOAR_GET_ARTIFACTS_ENDPOINT = consts.SPLUNK_SOAR_GET_CONTAINER_ARTIFACT_ENDPOINT.format(
            url=self.connector.get_phantom_base_url(), container_id=vectrandr_config.create_container(self.connector)
        )
        mock_get.get(
            SOAR_GET_ARTIFACTS_ENDPOINT, status_code=200, headers=vectrandr_config.DEFAULT_HEADERS, json=vectrandr_responses.GET_ARTIFACT_DETAILS
        )

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_data"][0]["status"], "success")
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], ret_val["result_summary"]["total_objects"])
