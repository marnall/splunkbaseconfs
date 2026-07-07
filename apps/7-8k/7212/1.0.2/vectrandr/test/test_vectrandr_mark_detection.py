# File: test_vectrandr_mark_detection.py
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

import vectrandr_consts as consts
from vectrandr_connector import VectraNDRConnector

from . import vectrandr_config, vectrandr_responses


class MarkDetectionAction(unittest.TestCase):
    """Class to test the mark detection action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = VectraNDRConnector()
        self.test_json = dict()
        self.test_json = dict(vectrandr_config.TEST_JSON)
        self.test_json.update({"action": "mark detection", "identifier": "mark_detection"})

        return super().setUp()

    @patch("vectrandr_utils.requests.patch")
    def test_mark_detection_pass(self, mock_patch):
        """
        Test the valid case for the mark detection action.

        Patch the patch() to return the valid response.
        """
        detection_id = 1952
        self.test_json["parameters"] = [{"detection_id": detection_id}]

        mock_patch.return_value.status_code = 200
        mock_patch.return_value.headers = vectrandr_config.DEFAULT_HEADERS
        mock_patch.return_value.json.return_value = vectrandr_responses.MARK_DETECTION_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")

        mock_patch.assert_called_with(
            f"{vectrandr_config.DUMMY_BASE_URL}{consts.VECTRA_API_VERSION}{consts.VECTRA_DETECTIONS_ENDPOINT}",
            headers=vectrandr_config.ACTION_HEADER,
            params=None,
            verify=False,
            stream=False,
            json={"detectionIdList": [detection_id], "mark_as_fixed": "True"},
            timeout=consts.VECTRA_REQUEST_TIMEOUT,
        )

    @patch("vectrandr_utils.requests.patch")
    def test_mark_detection_invalid_detection_id(self, mock_patch):
        """
        Test the fail case for the  mark detection action.

        Patch the patch() to return the valid response.
        """
        detection_id = 9999999999
        self.test_json["parameters"] = [{"detection_id": detection_id}]

        mock_patch.return_value.status_code = 404
        mock_patch.return_value.headers = vectrandr_config.DEFAULT_HEADERS
        mock_patch.return_value.json.return_value = vectrandr_responses.MARK_INVALID_DETECTION_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")

        mock_patch.assert_called_with(
            f"{vectrandr_config.DUMMY_BASE_URL}{consts.VECTRA_API_VERSION}{consts.VECTRA_DETECTIONS_ENDPOINT}",
            headers=vectrandr_config.ACTION_HEADER,
            params=None,
            verify=False,
            stream=False,
            json={"detectionIdList": [detection_id], "mark_as_fixed": "True"},
            timeout=consts.VECTRA_REQUEST_TIMEOUT,
        )
