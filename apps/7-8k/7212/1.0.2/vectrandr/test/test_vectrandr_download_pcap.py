# File: test_vectrandr_download_pcap.py
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
import os
import unittest
from unittest.mock import patch

from vectrandr_connector import VectraNDRConnector

from . import vectrandr_config, vectrandr_responses


class DownloadPCAPAction(unittest.TestCase):
    """Class to test the download pcap action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = VectraNDRConnector()
        self.test_json = dict()
        self.test_json = dict(vectrandr_config.TEST_JSON)
        self.test_json.update({"action": "download pcap", "identifier": "download_pcap"})
        self.file_to_zip = "testlogfile.pcap"
        if self.__dict__["_testMethodName"] == "test_download_pcap_pass":
            self.connector._BaseConnector__action_name = self.connector.get_action_identifier()
            self.test_json.update({"user_session_token": vectrandr_config.get_session_id(self.connector)})
            self.test_json.update({"container_id": vectrandr_config.create_container(self.connector)})

        return super().setUp()

    def tearDown(self):
        """Tear down method for the tests."""
        if os.path.exists(self.file_to_zip):
            os.remove(self.file_to_zip)
        return super().tearDown()

    @patch("vectrandr_utils.requests.get")
    def test_download_pcap_pass(self, mock_get):
        """
        Test the valid case for the download pcap action.

        Patch the get() to return the valid response.
        """
        self.test_json["parameters"] = [{"detection_id": 101010}]
        with open(self.file_to_zip, "wb") as f:
            f.write(b"Test log data")

        # Mock requests.get to return a response
        with open(self.file_to_zip, "rb") as binary_data:
            mock_get.return_value.status_code = 200
            mock_get.return_value.headers = {
                "Content-Type": "application/force-download",
                "Content-Disposition": "attachement;filename='IP-192.168.199.30_internal_stage_loader_1061.pcap'",
            }
            mock_get.return_value.content = binary_data.read()

            ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
            ret_val = json.loads(ret_val)

            self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
            self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
            self.assertEqual(ret_val["status"], "success")

    @patch("vectrandr_utils.requests.get")
    def test_download_pcap_invalid_detection_id(self, mock_get):
        """
        Test the fail case for the download pcap action.

        Patch the get() to return the valid response.
        """
        self.test_json["parameters"] = [{"detection_id": 999999999}]

        mock_get.return_value.status_code = 404
        mock_get.return_value.headers = vectrandr_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = vectrandr_responses.PCAP_INVALID_DETECTION_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")
