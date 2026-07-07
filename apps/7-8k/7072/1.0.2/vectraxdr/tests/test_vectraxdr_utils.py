"""Unit test file for utils."""
# File: test_vectraxdr_utils.py
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
import unittest
from unittest.mock import Mock, patch

import requests
from parameterized import parameterized
from phantom.action_result import ActionResult

from vectraxdr_utils import RetVal, VectraxdrUtils

from . import vectraxdr_config


class TestRetValClass(unittest.TestCase):
    """Class to test the RetVal."""

    @parameterized.expand(
        [
            ["single_value", [True], (True, None)],
            ["two_value", [True, {"key": "value"}], (True, {"key": "value"})],
        ]
    )
    def test_ret_val_pass(self, _, input_val, expected):
        """Tests the valid cases for the ret_val class."""
        output = RetVal(*input_val)
        self.assertEqual(output, expected)


class TestValidateIntegerMethod(unittest.TestCase):
    """Class to test the _validate_integer method."""

    def setUp(self):
        """Set up method for the tests."""
        self.util = VectraxdrUtils(None)
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand(
        [
            ["zero_allowed", 0, 0, ""],
            ["integer", 10, 10, ""],
        ]
    )
    def test_validate_integer_pass(self, _, input_value, expected_value, expected_message):
        """Test the valid cases for the validate integer method."""
        ret_val, output = self.util._validate_integer(self.action_result, input_value, "id", True)

        self.assertTrue(ret_val)
        self.assertEqual(output, expected_value)
        self.assertEqual(self.action_result.get_message(), expected_message)

    @parameterized.expand(
        [
            ["negative", -10, "Please provide a valid non-negative integer value in the 'id' parameter"],
            ["zero_not_allowed", 0, "Please provide a non-zero positive integer value in the 'id' parameter"],
        ]
    )
    def test_validate_integer_fail(self, _, input_value, expected_message):
        """Test the failed cases for the validate integer method."""
        ret_val, output = self.util._validate_integer(self.action_result, input_value, "id", False)
        self.assertFalse(ret_val)
        self.assertIsNone(output)
        self.assertEqual(self.action_result.get_message(), expected_message)


class TestEncryptionMethod(unittest.TestCase):
    """Class to test the encryption/decryption methods."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        connector.get_app_json.return_value = {"app_version": "1.0.0"}
        connector.get_asset_id.return_value = vectraxdr_config.DEFAULT_ASSET_ID
        connector.error_print.return_value = None
        self.util = VectraxdrUtils(connector)
        return super().setUp()

    @parameterized.expand(
        [
            [
                "token1",
                {
                    "token": {
                        "access_token": vectraxdr_config.TOKEN_DUMMY_ACCESS_TOKEN_1,
                        "refresh_token": vectraxdr_config.TOKEN_DUMMY_REFRESH_TOKEN_1,
                        "expire": 12345,
                    }
                },
                vectraxdr_config.TOKEN_DUMMY_ACCESS_CIPHER_1,
            ],
            [
                "token2",
                {
                    "token": {
                        "access_token": vectraxdr_config.TOKEN_DUMMY_ACCESS_TOKEN_2,
                        "refresh_token": vectraxdr_config.TOKEN_DUMMY_REFRESH_TOKEN_2,
                        "expire": 67891,
                    }
                },
                vectraxdr_config.TOKEN_DUMMY_REFRESH_CIPHER_2,
            ],
            ["no_token", {"app_version": "1.0.0"}, {}],
        ]
    )
    def test_encrypt_state_pass(self, name, input_value, expected_value):
        """Test the pass cases for the encrypt state method."""
        output = self.util._encrypt_state(input_value)
        if "token1" in name:
            self.assertEqual(output.get("token", {}).get("access_token", ""), expected_value)
        elif "token2" in name:
            self.assertEqual(output.get("token", {}).get("refresh_token", ""), expected_value)
        else:
            self.assertEqual(output.get("token", {}), expected_value)

    @parameterized.expand(
        [
            [
                "token1",
                {
                    "token": {
                        "access_token": vectraxdr_config.TOKEN_DUMMY_ACCESS_CIPHER_1,
                        "refresh_token": vectraxdr_config.TOKEN_DUMMY_REFRESH_CIPHER_1,
                        "expire": 12345,
                    }
                },
                vectraxdr_config.TOKEN_DUMMY_ACCESS_TOKEN_1,
            ],
            [
                "token2",
                {
                    "token": {
                        "access_token": vectraxdr_config.TOKEN_DUMMY_ACCESS_CIPHER_2,
                        "refresh_token": vectraxdr_config.TOKEN_DUMMY_REFRESH_CIPHER_2,
                        "expire": 12345,
                    }
                },
                vectraxdr_config.TOKEN_DUMMY_REFRESH_TOKEN_2,
            ],
            ["no_token", {"app_version": "1.0.0"}, {}],
        ]
    )
    def test_decrypt_state_pass(self, name, input_value, expected_value):
        """Test the pass cases for the decrypt state method."""
        output = self.util._decrypt_state(input_value)
        if "token1" in name:
            self.assertEqual(output.get("token", {}).get("access_token", ""), expected_value)
        elif "token2" in name:
            self.assertEqual(output.get("token", {}).get("refresh_token", ""), expected_value)
        else:
            self.assertEqual(output.get("token", {}), expected_value)

    @patch("vectraxdr_utils.encryption_helper.encrypt")
    def test_encrypt_state_fail(self, mock_encrypt):
        """Test the fail cases for the encrypt state method."""
        mock_encrypt.side_effect = Exception("Couldn't encrypt")

        output = self.util._encrypt_state(
            {
                "token": {
                    "access_token": vectraxdr_config.TOKEN_DUMMY_ACCESS_CIPHER_1,
                    "refresh_token": vectraxdr_config.TOKEN_DUMMY_REFRESH_CIPHER_1,
                    "expire": 123456,
                }
            }
        )
        self.assertEqual(output, {})

    @patch("vectraxdr_utils.encryption_helper.decrypt")
    def test_decrypt_state_fail(self, mock_decrypt):
        """Test the fail cases for the decrypt state method."""
        mock_decrypt.side_effect = Exception("Couldn't decrypt")

        output = self.util._decrypt_state(
            {
                "token": {
                    "access_token": vectraxdr_config.TOKEN_DUMMY_ACCESS_CIPHER_1,
                    "refresh_token": vectraxdr_config.TOKEN_DUMMY_REFRESH_CIPHER_1,
                    "expire": 123456,
                }
            }
        )
        self.assertEqual(output, {})


class TestGetErrorMessageFromException(unittest.TestCase):
    """Class to test the get error message from exception method."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        connector.error_print.return_value = None
        self.util = VectraxdrUtils(connector)
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand(
        [
            [
                "exception_without_args",
                Exception(),
                "Error message: Error message unavailable. Please check the asset configuration and|or action parameters",
            ],
            ["exception_with_single_arg", Exception("test message"), "Error message: test message"],
            ["exception_with_multiple_args", Exception("test code", "test message"), "Error code: test code. Error message: test message"],
        ]
    )
    def test_get_error_message_from_exception(self, _, input_value, expected_message):
        """Test the pass and fail cases of get error message from exception method."""
        error_text = self.util._get_error_message_from_exception(input_value)
        self.assertEqual(error_text, expected_message)


class TestProcessEmptyResponse(unittest.TestCase):
    """Class to test the process empty response method."""

    def setUp(self):
        """Set up method for the tests."""
        self.response = Mock()
        self.util = VectraxdrUtils(None)
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand(
        [["success_code", 200, True, {}], ["success_code", 201, True, {}], ["success_code", 204, True, {}], ["error_code", 401, False, None]]
    )
    def test_process_empty_response(self, _, mock_code, expected_status, expected_value):
        """Test the pass and fail cases of process empty response method."""
        self.response.status_code = mock_code
        status, value = self.util._process_empty_response(self.response, self.action_result)
        self.assertEqual(status, expected_status)
        self.assertEqual(value, expected_value)


class TestProcessHtmlResponse(unittest.TestCase):
    """Class to test the process html response method."""

    def setUp(self):
        """Set up method for the tests."""
        self.response = Mock()
        self.util = VectraxdrUtils(None)
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand(
        [
            ["normal_response", "Oops!<script>document.getElementById('demo')</script>", False, "Status code: 500, Data from server: Oops!"],
        ]
    )
    def test_process_html_response(self, _, response_value, expected_value, expected_message):
        """Test the pass and fail cases of process html response method."""
        if response_value:
            self.response.text = response_value
        self.response.status_code = 500
        status, value = self.util._process_html_response(self.response, self.action_result)
        self.assertEqual(status, expected_value)
        self.assertEqual(self.action_result.get_message(), expected_message)
        self.assertIsNone(value)

    def test_process_response_html_fail(self):
        """Test the _process_response for html response."""
        response_obj = requests.Response()
        response_obj._content = b"<html><title>Login Page</title><body>Please login to the system.</body></html>"
        response_obj.status_code = 500
        response_obj.headers = {"Content-Type": "text/html; charset=utf-8"}

        ret_val, response = self.util._process_response(response_obj, self.action_result)
        self.assertFalse(ret_val)
        self.assertIsNone(response)


class TestProcessJsonResponse(unittest.TestCase):
    """Class to test the process json response method."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        connector.error_print.return_value = None
        self.response = Mock()
        self.util = VectraxdrUtils(connector)
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand(
        [
            [
                "token_response",
                200,
                True,
                {
                    "access_token": "dummy_access_token",
                    "refresh_token": "dummy_refresh_token",
                    "expires_in": 21600,
                    "refresh_expires_in": 86400,
                    "token_type": "Bearer",
                },
                {
                    "access_token": "dummy_access_token",
                    "refresh_token": "dummy_refresh_token",
                    "expires_in": 21600,
                    "refresh_expires_in": 86400,
                    "token_type": "Bearer",
                },
            ],
            [
                "valid_failure_json_response",
                401,
                False,
                {"error": "Authentication Error. Please try reauthenticating using API client credentials."},
                None,
            ],
            ["invalid_json_response", 404, False, KeyError("Invalid Json"), None],
        ]
    )
    def test_process_json_response(self, name, mock_code, expected_status, mock_response, expected_value):
        """Test the pass and fail cases of process json response method."""
        self.response.status_code = mock_code
        if "token_response" in name:
            self.response.json.return_value = mock_response
        elif "invalid_json_response" in name:
            self.util._get_token = False
            self.response.json.side_effect = mock_response
        else:
            self.util._get_token = False
            self.response.json.return_value = mock_response
        status, value = self.util._process_json_response(self.response, self.action_result)
        self.assertEqual(status, expected_status)
        self.assertEqual(value, expected_value)


class TestGeneralCases(unittest.TestCase):
    """Class to test the general cases."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        connector.error_print.return_value = None
        self.util = VectraxdrUtils(connector)
        self.action_result = ActionResult(dict())
        return super().setUp()

    def test_make_rest_call_invalid_method(self):
        """Test the _make_rest_call with invalid method."""
        ret_val, response = self.util._make_rest_call("/endpoint", self.action_result, method="invalid_method")
        self.assertFalse(ret_val)
        self.assertIsNone(response)
        self.assertEqual(self.action_result.get_message(), "Invalid method: invalid_method")

    @patch("vectraxdr_utils.requests.get")
    def test_make_rest_call_throw_exception(self, mock_get):
        """Test the _make_rest_call for error case."""
        mock_get.side_effect = Exception("error code", "error message")

        ret_val, response = self.util._make_rest_call("/endpoint", self.action_result, headers={})
        self.assertFalse(ret_val)
        self.assertIsNone(response)
        self.assertEqual(
            self.action_result.get_message(), "Error connecting to server. Details: Error code: error code. Error message: error message"
        )

    def test_process_response_unknown_fail(self):
        """Test the _process_response for unknown response."""
        response_obj = requests.Response()
        response_obj._content = b"dummy content"
        response_obj.status_code = 500
        response_obj.headers = {}

        ret_val, response = self.util._process_response(response_obj, self.action_result)
        self.assertFalse(ret_val)
        self.assertIsNone(response)
        self.assertIn("Can't process response from server. Status code: 500", self.action_result.get_message())

    def test_process_response_long_message_fail(self):
        """Test the _process_response for long response."""
        long_data = "".join([str(i) for i in range(502)])
        response_obj = requests.Response()
        response_obj._content = json.dumps(long_data).encode()
        response_obj.status_code = 500
        response_obj.headers = {}

        ret_val, response = self.util._process_response(response_obj, self.action_result)
        self.assertFalse(ret_val)
        self.assertIsNone(response)
        self.assertIn("Error parsing html response", self.action_result.get_message())


class TestGenerateAccessToken(unittest.TestCase):
    """Class to test the generate access token method."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        connector.error_print.return_value = None
        connector.state = {"token": {}}
        self.response = Mock()
        self.util = VectraxdrUtils(connector)
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand(
        [
            ["token_response", 200, True, "", {"access_token": "dummy_access_token", "expires_in": 21600, "token_type": "Bearer"}],
            [
                "valid_failure",
                401,
                False,
                "Error from server. Status code: 401,\
                  Error message: Authentication Error. Please try reauthenticating using API client credentials.",
                {"error": "Authentication Error. Please try reauthenticating using API client credentials."},
            ],
            ["invalid_json_response", 200, False, "Access token generation failed", {"not_avaliable": "access token"}],
        ]
    )
    @patch("vectraxdr_utils.requests.post")
    def test_generate_access_token(self, name, mock_code, expected_status, expected_message, mock_response, mock_post):
        """Test the pass and fail cases of generate token method."""
        mock_post.return_value.status_code = mock_code
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        status = self.util._generate_access_token(self.action_result)
        self.assertEqual(status, expected_status)
        self.assertEqual(self.action_result.get_message(), expected_message)


class TestGenerateRefreshToken(unittest.TestCase):
    """Class to test the generate refresh token method."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        connector.error_print.return_value = None
        connector.config = {
            "client_id": "12345",
            "client_secret": "secret",  # pragma: allowlist secret`
        }
        connector.state = {"token": {}}
        self.response = Mock()
        self.util = VectraxdrUtils(connector)
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand(
        [
            [
                "token_response",
                200,
                True,
                "",
                {
                    "access_token": "dummy_access_token",
                    "refresh_token": "dummy_refresh_token",
                    "expires_in": 21600,
                    "refresh_expires_in": 86400,
                    "token_type": "Bearer",
                },
            ],
            [
                "valid_failure",
                401,
                False,
                "Error from server. Status code: 401,\
                  Error message: Authentication Error. Please try reauthenticating using API client credentials.",
                {"error": "Authentication Error. Please try reauthenticating using API client credentials."},
            ],
            ["invalid_json_response", 200, False, "Tokens generation failed", {"not_avaliable": "access token"}],
        ]
    )
    @patch("vectraxdr_utils.requests.post")
    def test_generate_access_token(self, name, mock_code, expected_status, expected_message, mock_response, mock_post):
        """Test the pass and fail cases of generate token method."""
        mock_post.return_value.status_code = mock_code
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.headers = vectraxdr_config.DEFAULT_HEADERS
        status = self.util._generate_refresh_token(self.action_result)
        self.assertEqual(status, expected_status)
        self.assertEqual(self.action_result.get_message(), expected_message)
