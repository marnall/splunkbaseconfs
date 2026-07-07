"""Unit test file for download pcap action."""
# File: test_vectraxdr_download_pcap.py
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
import os
import unittest

import requests_mock

import vectraxdr_consts as consts
from vectraxdr_connector import VectraxdrConnector

from . import vectraxdr_config


class DownloadPCAPAction(unittest.TestCase):
    """Class to test the download pcap action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = VectraxdrConnector()
        self.test_json = dict()
        self.test_json = dict(vectraxdr_config.TEST_JSON)
        self.test_json.update({"action": "download pcap", "identifier": "download_pcap"})
        self.file_to_zip = "testlogfile.pcap"

        return super().setUp()

    def tearDown(self):
        """Tear down method for the tests."""
        if os.path.exists(self.file_to_zip):
            os.remove(self.file_to_zip)
        return super().tearDown()

    @requests_mock.Mocker(real_http=True)
    def test_download_pcap_pass(self, mock_get):
        """Test the valid case for the download pcap action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        # Define the side_effect function
        vectraxdr_config.set_state_file(Token=True)
        self.test_json.update({"user_session_token": vectraxdr_config.get_session_id(self.connector)})
        self.test_json.update({"container_id": vectraxdr_config.create_container(self.connector)})
        self.test_json["parameters"] = [{"detection_id": 10}]
        with open(self.file_to_zip, "wb") as f:
            f.write(b"Test log data")

        with open(self.file_to_zip, "rb") as binary_data:
            mock_get.get(
                f"{self.test_json['config']['base_url']}{consts.VECTRA_API_VERSION}{consts.VECTRA_PCAP_ENDPOINT.format(detection_id=10)}",
                status_code=200,
                headers={
                    "Content-Type": "application/force-download",
                    "Content-Disposition": "attachement;filename='IP-192.168.199.30_internal_stage_loader_1061.pcap'",
                },
                content=binary_data.read(),
            )

            ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
            ret_val = json.loads(ret_val)

            self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
            self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
            self.assertEqual(ret_val["status"], "success")
