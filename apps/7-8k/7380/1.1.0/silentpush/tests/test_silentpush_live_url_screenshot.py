# File: test_silentpush_live_url_screenshot.py
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
from unittest.mock import call, patch

import silentpush_consts as consts
from silentpush_connector import SilentpushConnector

from . import silentpush_constant, silentpush_responses


class SilentpushAction(unittest.TestCase):
    """Class to test the live url screenshot action."""

    def setUp(self):
        self.connector = SilentpushConnector()
        self.test_json = dict(silentpush_constant.TEST_JSON)
        self.test_json["config"] = {**self.test_json["config"], **silentpush_constant.APIKEY_AUTH_CONFIG}
        self.test_json.update({"action": "live url screenshot", "identifier": "live_url_screenshot"})
        self.run_job_endpoint = consts.LIVE_URL_SCREENSHOT_ENDPOINT

        return super().setUp()

    @patch("silentpush_utils.requests.get")
    def test_live_url_screenshot_valid(self, mock_get):
        """Test the valid case for the live url screenshot action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [{"url": "http://www.silentpush.com"}]

        # Define the side_effect function
        def mock_get_response(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "")
            if "https://api.silentpush.com" in url:
                return MockResponse(
                    status_code=200, headers=silentpush_constant.DEFAULT_JSON_HEADERS, text=silentpush_responses.LIVE_URL_SCREENSHOT_VALID_RESP
                )
            else:
                return MockResponse(
                    status_code=200, headers=silentpush_constant.DEFAULT_IMAGE_HEADERS, content=silentpush_responses.IMAGE_RESPONSE
                )

        mock_get.side_effect = mock_get_response

        with patch("phantom.rules.vault_add") as mock_vault_add, patch("phantom.rules.vault_info") as mock_vault_info:
            # Mock the return values of ph_rules.vault_add() and ph_rules.vault_info()
            mock_vault_add.return_value = (True, "Success", "ba9d018bb2fb512b3fb58c4a015d804372c4f3cb")  # pragma: allowlist secret
            mock_vault_info.return_value = (True, "meta_info", silentpush_responses.VAULT_META_INFO)

            ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
            ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        expected_calls = [
            call(
                f"{self.test_json['config']['base_url']}{self.run_job_endpoint}?url=http%3A%2F%2Fwww.silentpush.com",
                timeout=consts.REQUEST_DEFAULT_TIMEOUT,
                verify=False,
                headers={"X-API-KEY": "<dummy_api_token>"},
            ),
            call(
                "https://fs.silentpush.com/screenshots/silentpush.com/82ec8d7fc8af8d322959dead594c7f8e.jpg",
                timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            ),
        ]

        mock_get.assert_has_calls(expected_calls, any_order=True)

    @patch("silentpush_utils.requests.get")
    def test_live_url_screenshot_invalid(self, mock_get):
        """Test the valid case for the live url screenshot action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [{"url": "http://www.silentpush.com"}]

        mock_get.return_value.status_code = 400
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_responses.LIVE_URL_SCREENSHOT_VALID_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    @patch("silentpush_utils.requests.get")
    def test_live_url_screenshot_invalid_image_response(self, mock_get):
        """Test the valid case for the live url screenshot action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [{"url": "http://www.silentpush.com"}]

        # Define the side_effect function
        def mock_get_response(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "")
            if "https://api.silentpush.com" in url:
                return MockResponse(
                    status_code=200, headers=silentpush_constant.DEFAULT_JSON_HEADERS, text=silentpush_responses.LIVE_URL_SCREENSHOT_VALID_RESP
                )
            else:
                return MockResponse(
                    status_code=400, headers=silentpush_constant.DEFAULT_IMAGE_HEADERS, content=silentpush_responses.IMAGE_RESPONSE
                )

        mock_get.side_effect = mock_get_response

        with patch("phantom.rules.vault_add") as mock_vault_add, patch("phantom.rules.vault_info") as mock_vault_info:
            # Mock the return values of ph_rules.vault_add() and ph_rules.vault_info()
            mock_vault_add.return_value = (True, "Success", "ba9d018bb2fb512b3fb58c4a015d804372c4f3cb")  # pragma: allowlist secret
            mock_vault_info.return_value = (True, "meta_info", silentpush_responses.VAULT_META_INFO)

            ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
            ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 2)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        expected_calls = [
            call(
                f"{self.test_json['config']['base_url']}{self.run_job_endpoint}?url=http%3A%2F%2Fwww.silentpush.com",
                timeout=consts.REQUEST_DEFAULT_TIMEOUT,
                verify=False,
                headers={"X-API-KEY": "<dummy_api_token>"},
            ),
            call(
                "https://fs.silentpush.com/screenshots/silentpush.com/82ec8d7fc8af8d322959dead594c7f8e.jpg",
                timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            ),
        ]

        mock_get.assert_has_calls(expected_calls, any_order=True)

    @patch("silentpush_utils.requests.get")
    def test_live_url_screenshot_error_in_vault_add(self, mock_get):
        """Test the valid case for the live url screenshot action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [{"url": "http://www.silentpush.com"}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_responses.LIVE_URL_SCREENSHOT_VALID_RESP
        mock_get.return_value.content = silentpush_responses.IMAGE_RESPONSE

        with patch("phantom.rules.vault_add") as mock_vault_add:
            # Mock the return values of ph_rules.vault_add() and ph_rules.vault_info()
            mock_vault_add.return_value = (False, "Success", "ba9d018bb2fb512b3fb58c4a015d804372c4f3cb")  # pragma: allowlist secret

            ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
            ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    @patch("silentpush_utils.requests.get")
    def test_live_url_screenshot_error_in_vault_info(self, mock_get):
        """Test the valid case for the live url screenshot action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [{"url": "http://www.silentpush.com"}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_responses.LIVE_URL_SCREENSHOT_VALID_RESP
        mock_get.return_value.content = silentpush_responses.IMAGE_RESPONSE

        with patch("phantom.rules.vault_add") as mock_vault_add, patch("phantom.rules.vault_info") as mock_vault_info:
            # Mock the return values of ph_rules.vault_add() and ph_rules.vault_info()
            mock_vault_add.return_value = (True, "Success", "ba9d018bb2fb512b3fb58c4a015d804372c4f3cb")  # pragma: allowlist secret
            mock_vault_info.return_value = (True, "meta_info", "")

            ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
            ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    @patch("silentpush_utils.requests.get")
    def test_live_url_screenshot_error_in_vault(self, mock_get):
        """Test the valid case for the live url screenshot action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [{"url": "http://www.silentpush.com"}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = silentpush_responses.LIVE_URL_SCREENSHOT_VALID_RESP

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    @patch("silentpush_utils.requests.get")
    def test_live_url_screenshot_invalid_response_url(self, mock_get):
        """Test the valid case for the live url screenshot action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [{"url": "http://www.silentpush.com"}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = {"response": {"screenshot": {"message": "error message"}}}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

    @patch("silentpush_utils.requests.get")
    def test_live_url_screenshot_invalid_response(self, mock_get):
        """Test the valid case for the live url screenshot action.

        Patch the get() to run job.
        """
        self.test_json["parameters"] = [{"url": "http://www.silentpush.com"}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = silentpush_constant.DEFAULT_JSON_HEADERS
        mock_get.return_value.json.return_value = {"response": {"screenshot": {"response": 400}}}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")


# Helper class to create a mock response object
class MockResponse:
    """A helper class to create a mock response object for testing purposes.

    This class is used to simulate HTTP responses during unit tests for functions
    that make API requests using libraries like `requests`.

    Attributes:
        status_code (int): The HTTP status code of the mock response.
        text (str): The content of the mock response as a string.
    """

    def __init__(self, status_code, headers, text=None, content=None):
        """Initialize a new MockResponse object.

        Args:
            status_code (int): The HTTP status code of the mock response.
            text (str): The content of the mock response as a string.
        """
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self.text = text

    def json(self):
        """Parse the content of the mock response as JSON.

        Returns:
            dict: A dictionary representation of the JSON content.
        """
        return self.text
