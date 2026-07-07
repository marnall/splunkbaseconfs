# File: test_cofensevision_list_iocs.py
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


EXPECTED_HEADER = dict(cofensevision_config.ACTION_HEADER)
EXPECTED_HEADER.update({"X-Cofense-IOC-Source": "Triage-1"})

VALID_PARAMETERS = {"page": 0, "size": 50, "includeExpired": True, "since": "2021-12-31", "source": "Triage-1", "sort": "updatedAt:asc"}

EXPECTED_PARAMETERS = {"page": 0, "size": 50, "includeExpired": False, "since": "2021-12-31T00:00:00.000000Z", "sort": ["updatedAt,asc"]}


class TestListIocAction(unittest.TestCase):
    """Class to test the list iocs action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "list iocs", "identifier": "list_iocs"})

        return super().setUp()

    @patch("cofensevision_utils.requests.get")
    def test_list_iocs_pass(self, mock_get):
        """Test the valid case for the list iocs action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [VALID_PARAMETERS]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = EXPECTED_HEADER
        mock_get.return_value.json.return_value = {"data": [{"dummy": "data"}]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")
        self.assertGreater(ret_val["result_data"][0]["summary"]["total_iocs"], 0)

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}",
            headers=EXPECTED_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            params=EXPECTED_PARAMETERS,
        )

    @patch("cofensevision_utils.requests.get")
    def test_list_iocs_invalid_source_fail(self, mock_get):
        """Test the list iocs action with invalid source parameter .

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        EXPECTED_DATA = {
            "status": "UNPROCESSABLE_ENTITY",
            "message": "Validation failed for request data",
            "details": ["X-Cofense-IOC-Source must only have alphanumeric characters and - . _ ~"],
        }

        self.test_json["parameters"] = [VALID_PARAMETERS]

        mock_get.return_value.status_code = 422
        mock_get.return_value.headers = EXPECTED_HEADER
        mock_get.return_value.json.return_value = EXPECTED_DATA

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=EXPECTED_HEADER,
            params=EXPECTED_PARAMETERS,
        )

    @patch("cofensevision_utils.requests.get")
    def test_list_iocs_server_fail(self, mock_get):
        """Test the invalid case for the list iocs action.

        Patch the get() to return the error response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        self.test_json["parameters"] = [{"source": "Triage-1"}]

        mock_get.return_value.status_code = 500
        mock_get.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"error": "Internal server error"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Error from server. Status code: 500", ret_val["result_data"][0]["message"])

        expected_params = {"page": 0, "size": 50, "includeExpired": False}
        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=EXPECTED_HEADER,
            params=expected_params,
        )

    @patch("cofensevision_utils.requests.get")
    def test_list_iocs_empty_response_fail(self, mock_get):
        """Test the empty response case for the list iocs action.

        Patch the get() to return the error response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        self.test_json["parameters"] = [{"source": "Triage-1"}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = {}
        mock_get.return_value.text = ""

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], "The server returned an unexpected empty response")

        expected_params = {"page": 0, "size": 50, "includeExpired": False}
        mock_get.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            headers=EXPECTED_HEADER,
            params=expected_params,
        )

    def test_list_iocs_invalid_page_fail(self):
        """Test the list iocs action with invalid 'page' parameter.

        Token is available in the state file.
        """
        # Save the state file with the invalid JSON string.
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"page": "non_numeric", "source": "Triage-1"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_INT_PARAM.format(key="page"))

    def test_list_iocs_invalid_size_fail(self):
        """Test the list iocs action with invalid 'size' parameter.

        Token is available in the state file.
        """
        # Save the state file with the invalid JSON string.
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"size": "non_numeric", "source": "Triage-1"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_INT_PARAM.format(key="size"))

    def test_list_iocs_invalid_sort_format_fail(self):
        """Test the list iocs action with invalid 'sort' parameter.

        Token is available in the state file.
        """
        # Save the state file with the invalid JSON string.
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"sort": "UpdatedAt,asc", "source": "Triage-1"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("sort"))

    def test_list_iocs_invalid_sort_field_fail(self):
        """Test the list iocs action with invalid 'sort' parameter.

        Token is available in the state file.
        """
        # Save the state file with the invalid JSON string.
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"sort": "createdDate:asc", "source": "Triage-1"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("sort"))

    def test_list_iocs_invalid_since_fail(self):
        """Test the list iocs action with invalid 'since' parameter.

        Token is available in the state file.
        """
        # Save the state file with the invalid JSON string.
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{"since": "2021-13-01", "source": "Triage-1"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("since"))
