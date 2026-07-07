# File: test_silentpush_get_data_export.py
#
# Copyright (c) 2024-2025 Splunk Inc.
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

import silentpush_consts as consts
from silentpush_connector import SilentpushConnector

from . import silentpush_constant, silentpush_responses


@patch("silentpush_utils.requests.get")
class SilentpushAction(unittest.TestCase):
    """Class to test the get data export action."""

    def setUp(self):
        self.connector = SilentpushConnector()
        self.test_json = dict(silentpush_constant.TEST_JSON)
        self.test_json["config"] = {**self.test_json["config"], **silentpush_constant.APIKEY_AUTH_CONFIG}
        self.test_json.update({"action": "get data export", "identifier": "get_data_export"})

        return super().setUp()

    def test_get_data_export_valid(self, mock_get):
        """Test the valid case for the get data export action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {"feed_url": "https://app.silentpush.com/app/v1/export/organization-exports/294ed3e2-112d-424e-9a93-9e4e1a071f98_indicators.csv"}
        ]

        # Define the side_effect function
        def mock_vault_response(*args, **kwargs):
            return MockResponse(
                status_code=200, headers={"Content-Type": "binary/octet-stream"}, text=silentpush_responses.GET_DATA_EXPORT_VALID_RESP
            )

        mock_get.side_effect = mock_vault_response

        with patch("phantom.rules.vault_add") as mock_vault_add:
            # Mock the return values of ph_rules.vault_add() and ph_rules.vault_info()
            mock_vault_add.return_value = (True, "Success", "ba9d018bb2fb512b3fb58c4a015d804372c4f3cb")  # pragma: allowlist secret

            ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
            ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")

        mock_get.assert_called_with(
            "https://app.silentpush.com/app/v1/export/organization-exports/294ed3e2-112d-424e-9a93-9e4e1a071f98_indicators.csv",
            timeout=consts.EXPORT_REQUEST_DEFAULT_TIMEOUT,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
            verify=False,
        )

    def test_get_data_export_invalid(self, mock_get):
        """Test the invalid case for the get data export action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [
            {"feed_url": "https://app.silentpush.com/app/v1/export/organization-exports/222222-2222-2222-2222-22222222222_indicators.txt"}
        ]

        mock_get.return_value.status_code = 400
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_responses.GET_EXPORT_DATA_INVALID_RESPONSE

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")

        mock_get.assert_called_with(
            "https://app.silentpush.com/app/v1/export/organization-exports/222222-2222-2222-2222-22222222222_indicators.txt",
            timeout=180,
            verify=False,
            headers={"X-API-KEY": silentpush_constant.DUMMY_API_TOKEN},
        )


class MockResponse:
    """A helper class to create a mock response object for testing purposes.

    This class is used to simulate HTTP responses during unit tests for functions
    that make API requests using libraries like `requests`.

    Attributes:
        status_code (int): The HTTP status code of the mock response.
        text (str): The content of the mock response as a string.
    """

    def __init__(self, status_code, headers, text=None, content=None, timeout=30, verify=False):
        """Initialize a new MockResponse object.

        Args:
            status_code (int): The HTTP status code of the mock response.
            text (str): The content of the mock response as a string.
        """
        self.status_code = status_code
        self.headers = headers
        self.text = text
