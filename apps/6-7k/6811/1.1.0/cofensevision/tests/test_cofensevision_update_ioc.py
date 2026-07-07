# File: test_cofensevision_update_ioc.py
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


VALID_PARAMETERS = {
    "id": "7a785c76033e6e2f1464ba3f41ffb23a",  # pragma: allowlist secret
    "expires_at": "2080-05-15",
}

EXPECTED_BODY = {"data": {"type": "ioc", "metadata": {"quarantine": {"expires_at": "2080-05-15T00:00:00.000000Z"}}}}


class TestUpdateIocAction(unittest.TestCase):
    """Class to test the update ioc action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "update ioc", "identifier": "update_ioc"})

        return super().setUp()

    @patch("cofensevision_utils.requests.put")
    def test_update_ioc_pass(self, mock_put):
        """Test the valid case for the update ioc action.

        Token is available in the state file.
        Patch the put() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [VALID_PARAMETERS]

        mock_put.return_value.status_code = 200
        mock_put.return_value.headers = cofensevision_config.ACTION_HEADER
        mock_put.return_value.json.return_value = {"data": {"dummy": "data"}}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_UPDATE_IOC_SUCCESS)

        mock_put.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}/{VALID_PARAMETERS['id']}",
            headers=cofensevision_config.ACTION_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            json=EXPECTED_BODY,
        )

    @patch("cofensevision_utils.requests.put")
    def test_update_ioc_invalid_id_fail(self, mock_put):
        """Test the update ioc action with invalid id parameter .

        Token is available in the state file.
        Patch the put() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        EXPECTED_DATA = {
            "status": "UNPROCESSABLE_ENTITY",
            "message": "Validation failed for request data",
            "details": ["id for IOCs should be a 32-character MD5"],
        }

        PARAMS = {"id": "7a78", "expires_at": "2080-05-15"}
        self.test_json["parameters"] = [PARAMS]

        mock_put.return_value.status_code = 422
        mock_put.return_value.headers = cofensevision_config.ACTION_HEADER
        mock_put.return_value.json.return_value = EXPECTED_DATA

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_put.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}/{PARAMS['id']}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=cofensevision_config.ACTION_HEADER,
            json=EXPECTED_BODY,
        )

    @patch("cofensevision_utils.requests.put")
    def test_update_ioc_server_fail(self, mock_put):
        """Test the server error case for the update ioc action.

        Patch the get() to return the error response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        self.test_json["parameters"] = [VALID_PARAMETERS]

        mock_put.return_value.status_code = 500
        mock_put.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_put.return_value.json.return_value = {"error": "Internal server error"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Error from server. Status code: 500", ret_val["result_data"][0]["message"])

        mock_put.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}/{VALID_PARAMETERS['id']}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=cofensevision_config.ACTION_HEADER,
            json=EXPECTED_BODY,
        )

    def test_update_ioc_invalid_expires_at_fail(self):
        """Test the update ioc action with invalid 'expires_at' parameter.

        Token is available in the state file.
        """
        # Save the state file with the invalid JSON string.
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [
            {
                "id": "7a785c76033e6e2f1464ba3f41ffb23a",  # pragma: allowlist secret
                "expires_at": "2080-16-45",
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("expires_at"))
