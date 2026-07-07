# File: test_cofensevision_delete_ioc.py
#
# Copyright (c) 2023-2026 Cofense
#
# This unpublished material is proprietary to Cofense.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Cofense.
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

import cofensevision_consts as consts
from cofensevision_connector import CofenseVisionConnector
from tests import cofensevision_config


class TestDeleteIOCAction(unittest.TestCase):
    """Class to test the delete ioc action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "delete ioc", "identifier": "delete_ioc"})

        return super().setUp()

    @patch("cofensevision_utils.requests.delete")
    def test_delete_ioc_action_pass(self, mock_delete):
        """Test the valid case for the delete ioc action.

        Token is available in the state file.
        Patch the delete() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        ioc_id = "41ecc26bd356dd706cc1a0cd839cad2c"
        source = "Triage-1"

        expected_header = dict(cofensevision_config.ACTION_HEADER)
        expected_header.update({"X-Cofense-IOC-Source": source})

        expected_data = {"data": {"id": ioc_id}}

        self.test_json["parameters"] = [{"id": ioc_id, "source": source}]

        mock_delete.return_value.status_code = 200
        mock_delete.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_delete.return_value.json.return_value = expected_data

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_delete.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}/{ioc_id}",
            headers=expected_header,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )

    @patch("cofensevision_utils.requests.delete")
    def test_delete_ioc_invalid_source_action_fail(self, mock_delete):
        """Test the delete ioc action with invalid source parameter.

        Token is available in the state file.
        Patch the delete() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        ioc_id = "41ecc26bd356dd706cc1a0cd839cad2c"
        source = "Triage*=1"

        expected_header = dict(cofensevision_config.ACTION_HEADER)
        expected_header.update({"X-Cofense-IOC-Source": source})

        expected_data = {
            "status": "UNPROCESSABLE_ENTITY",
            "message": "Validation failed for request data",
            "details": ["X-Cofense-IOC-Source must only have alphanumeric characters and - . _ ~"],
        }

        self.test_json["parameters"] = [{"id": ioc_id, "source": source}]

        mock_delete.return_value.status_code = 422
        mock_delete.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_delete.return_value.json.return_value = expected_data

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_delete.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}/{ioc_id}",
            headers=expected_header,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )

    @patch("cofensevision_utils.requests.delete")
    def test_delete_ioc_not_found_action_fail(self, mock_delete):
        """Test the delete ioc action with valid id and source parameters but that do not exist in cofense.

        Token is available in the state file.
        Patch the delete() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        ioc_id = "41ecc26bd356dd706121a0cd839cad2c"
        source = "Triage-1"

        expected_header = dict(cofensevision_config.ACTION_HEADER)
        expected_header.update({"X-Cofense-IOC-Source": source})

        self.test_json["parameters"] = [{"id": ioc_id, "source": source}]

        mock_delete.return_value.status_code = 404
        mock_delete.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_delete.return_value.text = ""

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Status code: 404", ret_val["result_data"][0]["message"])

        mock_delete.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}/{ioc_id}",
            headers=expected_header,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )
