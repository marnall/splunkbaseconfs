# File: test_cofensevision_get_last_ioc.py
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


class TestGetLastIOCAction(unittest.TestCase):
    """Class to test the get last ioc action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "get last ioc", "identifier": "get_last_ioc"})

        return super().setUp()

    @patch("cofensevision_utils.requests.get")
    def test_get_last_ioc_pass(self, mock_get):
        """Test the valid case for the get last ioc action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        source = "Triage-1"

        expected_header = dict(cofensevision_config.ACTION_HEADER)
        expected_header.update({"X-Cofense-IOC-Source": source})

        expected_data = {"data": {"id": "d1c54c37fd53d37094ef1dc7530ca949"}}  # pragma: allowlist secret

        self.test_json["parameters"] = [{"source": source}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = expected_data

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC_LAST}",
            headers=expected_header,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )

    @patch("cofensevision_utils.requests.get")
    def test_get_last_ioc_invalid_source_fail(self, mock_get):
        """Test the get last ioc action with invalid source parameter.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        source = "Triage*=1"

        expected_header = dict(cofensevision_config.ACTION_HEADER)
        expected_header.update({"X-Cofense-IOC-Source": source})

        expected_data = {
            "status": "UNPROCESSABLE_ENTITY",
            "message": "Validation failed for request data",
            "details": ["X-Cofense-IOC-Source must only have alphanumeric characters and - . _ ~"],
        }

        self.test_json["parameters"] = [{"source": source}]

        mock_get.return_value.status_code = 422
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = expected_data

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC_LAST}",
            headers=expected_header,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )

    @patch("cofensevision_utils.requests.get")
    def test_get_last_ioc_source_case_sensitive_fail(self, mock_get):
        """Test the get last ioc action with case sensitive source parameter.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        source = "VISION_UI"

        EXPECTED_HEADER = dict(cofensevision_config.ACTION_HEADER)
        EXPECTED_HEADER.update({"X-Cofense-IOC-Source": source})

        self.test_json["parameters"] = [{"source": source}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"data": None}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC_LAST}",
            headers=EXPECTED_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )
