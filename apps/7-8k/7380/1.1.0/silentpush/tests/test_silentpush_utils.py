# File: test_silentpush_utils.py
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

import unittest
from unittest.mock import Mock, patch

import requests
from parameterized import parameterized
from phantom.action_result import ActionResult

from silentpush_utils import RetVal, SilentpushUtils, Validator


PARAM_VALUE = "{{param_value}}"


class TestRetValClass(unittest.TestCase):
    """Class to tests the RetVal"""

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
    """Class to tests the validate_integer method."""

    def setUp(self):
        """Set up method for the tests."""
        self.util = Validator()
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand(
        [
            ["zero_allowed", 0, 0, ""],
            ["integer", 10, 10.0, ""],
        ]
    )
    def test_validate_integer_pass(self, _, input_value, expected_value, expected_message):
        """Test the valid cases for the validate integer method."""
        ret_val, output = self.util.validate_integer(self.action_result, input_value, "delta", True)

        self.assertTrue(ret_val)
        self.assertEqual(output, expected_value)
        self.assertEqual(self.action_result.get_message(), expected_message)

    @parameterized.expand(
        [
            ["zero_not_allowed", "0", "Please provide a non-zero integer value in the 'delta' parameter"],
            ["alphanumeric", "abc12", "Please provide a valid integer value in the 'delta' parameter"],
            ["unicode", "ト日本標準時ﬗ╬⎋⅍ⅎ€", "Please provide a valid integer value in the 'delta' parameter"],
            ["float", "10.5", "Please provide a valid integer value in the 'delta' parameter"],
            ["negative", -10, "Please provide a positive integer value in the 'delta' parameter"],
        ]
    )
    def test_validate_integer_fail(self, _, input_value, expected_message, allow_negative=False):
        """Test the failed cases for the validate integer method."""
        ret_val, output = self.util.validate_integer(self.action_result, input_value, "delta", False, allow_negative)

        self.assertFalse(ret_val)
        self.assertIsNone(output)
        self.assertEqual(self.action_result.get_message(), expected_message)


class TestValidateDictMethod(unittest.TestCase):
    """Class to tests the validate_dict method."""

    def setUp(self):
        """Set up method for the tests."""
        self.util = Validator()
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand([["valid JSON string", "{'ok': True}", "", {"ok": True}, ""]])
    def test_validate_dict_pass(self, _, input_value, key, expected_value, expected_message):
        """Test the valid cases for the validate dict method."""
        ret_val, output = self.util.validate_dict(self.action_result, input_value, key)

        self.assertTrue(ret_val)
        self.assertEqual(output, expected_value)
        self.assertEqual(self.action_result.get_message(), expected_message)

    @parameterized.expand(
        [
            ["invalid JSON", "{'ok': abc}", "payload", None, "Please provide a valid JSON value for the 'payload' parameter"],
            ["Not dict type", "[{'ok': True}]", "payload", None, "Please provide a valid JSON value for the 'payload' parameter"],
        ]
    )
    def test_validate_dict_fail(self, _, input_value, key, expected_value, expected_message):
        """Test the failed cases for the validate dict method."""
        ret_val, output = self.util.validate_dict(self.action_result, input_value, key)

        self.assertFalse(ret_val)
        self.assertEqual(output, expected_value)
        self.assertEqual(self.action_result.get_message(), expected_message)


class TestValidateBooleanMethod(unittest.TestCase):
    """Class to tests the validate_boolean method."""

    def setUp(self):
        """Set up method for the tests."""
        self.util = Validator()
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand([["valid Boolean", True, "", True, ""]])
    def test_validate_boolean_pass(self, _, input_value, key, expected_value, expected_message):
        """Test the valid cases for the validate boolean method."""
        ret_val, output = self.util.validate_boolean(self.action_result, input_value, key)

        self.assertTrue(ret_val)
        self.assertEqual(output, expected_value)
        self.assertEqual(self.action_result.get_message(), expected_message)

    @parameterized.expand(
        [["invalid Boolean", "abc", "is_allowed", None, "Please provide a valid boolean value for the 'is_allowed' parameter"]]
    )
    def test_validate_boolean_fail(self, _, input_value, key, expected_value, expected_message):
        """Test the failed cases for the validate boolean method."""
        ret_val, output = self.util.validate_boolean(self.action_result, input_value, key)

        self.assertFalse(ret_val)
        self.assertEqual(output, expected_value)
        self.assertEqual(self.action_result.get_message(), expected_message)


class TestGetErrorMessageFromException(unittest.TestCase):
    """Class to tests the get error message from exception method."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        connector.error_print.return_value = None
        self.util = SilentpushUtils(connector)
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand(
        [
            [
                "exception_without_args",
                Exception(),
                "Error message: Error message unavailable. Please check the asset configuration and|or action parameters",
            ],
            ["exception_with_single_arg", Exception("tests message"), "Error message: tests message"],
            ["exception_with_multiple_args", Exception("tests code", "tests message"), "Error code: tests code. Error message: tests message"],
        ]
    )
    def test_get_error_message_from_exception(self, _, input_value, expected_message):
        """Test the pass and fail cases of get error message from exception method."""
        error_text = self.util._get_error_message_from_exception(input_value)
        self.assertEqual(error_text, expected_message)


class TestProcessEmptyResponse(unittest.TestCase):
    """Class to tests the process empty response method."""

    def setUp(self):
        """Set up method for the tests."""
        self.response = Mock()
        self.util = SilentpushUtils(None)
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand([["success_code", 200, True, {}], ["error_code", 404, False, None]])
    def test_process_empty_response(self, _, mock_code, expected_status, expected_value):
        """Test the pass and fail cases of process empty response method."""
        self.response.status_code = mock_code
        status, value = self.util._process_empty_response(self.response, self.action_result)
        self.assertEqual(status, expected_status)
        self.assertEqual(value, expected_value)


class TestProcessHtmlResponse(unittest.TestCase):
    """Class to tests the process html response method."""

    def setUp(self):
        """Set up method for the tests."""
        self.response = Mock()
        self.util = SilentpushUtils(None)
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand(
        [
            ["no_response_text", "", False, "Status code: 402, Data from server: Cannot parse error details"],
            ["normal_response", "Oops!<script>document.getElementById('demo')</script>", False, "Status code: 402, Data from server: Oops!"],
            ["large_response", "".join([str(i) for i in range(502)]), False, "Error parsing html response"],
        ]
    )
    def test_process_html_response(self, _, response_value, expected_value, expected_message):
        """Test the pass and fail cases of process html response method."""
        if response_value:
            self.response.text = response_value
        self.response.status_code = 402
        status, value = self.util._process_html_response(self.response, self.action_result)
        self.assertEqual(status, expected_value)
        self.assertEqual(self.action_result.get_message(), expected_message)
        self.assertIsNone(value)

    def test_process_response_html_fail(self):
        """Test the _process_response for html response."""
        response_obj = requests.Response()
        response_obj._content = b"<html><title>Login Page</title><body>Please login to the system.</body></html>"
        response_obj.status_code = 200
        response_obj.headers = {"Content-Type": "text/html; charset=utf-8"}

        ret_val, response = self.util._process_response(response_obj, self.action_result)
        self.assertFalse(ret_val)
        self.assertIsNone(response)


class TestProcessJsonResponse(unittest.TestCase):
    """Class to tests the process json response method."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        connector.error_print.return_value = None
        self.response = Mock()
        self.util = SilentpushUtils(connector)
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand(
        [
            ["valid_success_json_response", 200, True, {"results": []}, {"results": []}],
            ["valid_failure_json_response", 404, False, {"status": "NOT_FOUND"}, None],
            ["invalid_json_response", 404, False, KeyError("Invalid Json"), None],
            ["valid_error_json_response", 200, False, {"status_code": 200, "response": {"error": "ERROR"}}, None, "response.error"],
            [
                "valid_error_json_response",
                200,
                True,
                {"status_code": 200, "response": {"value": "ERROR"}},
                {"status_code": 200, "response": {"value": "ERROR"}},
                "response.error",
            ],
        ]
    )
    def test_process_json_response(self, name, mock_code, expected_status, mock_response, expected_value, error_path=None):
        """Test the pass and fail cases of process json response method."""
        self.response.status_code = mock_code
        if "invalid_json_response" in name:
            self.response.json.side_effect = mock_response
        else:
            self.response.json.return_value = mock_response
        status, value = self.util._process_json_response(self.response, self.action_result, error_path)
        self.assertEqual(status, expected_status)
        self.assertEqual(value, expected_value)


class TestGeneralCases(unittest.TestCase):
    """Class to tests the general cases."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        connector.error_print.return_value = None
        connector.config = {"": "https://<base_url>/"}
        self.util = SilentpushUtils(connector)
        self.action_result = ActionResult(dict())
        return super().setUp()

    def test_make_rest_call_invalid_method(self):
        """Test the make_rest_call with invalid method."""
        ret_val, response = self.util.make_rest_call("/endpoint", self.action_result, method="invalid_method")
        self.assertFalse(ret_val)
        self.assertIsNone(response)
        self.assertEqual(self.action_result.get_message(), "Invalid method: invalid_method")

    @patch("silentpush_utils.requests.get")
    def test_make_rest_call_throw_exception(self, mock_get):
        """Test the make_rest_call for error case."""
        mock_get.side_effect = Exception("error code", "error message")

        ret_val, response = self.util.make_rest_call("/endpoint", self.action_result)
        self.assertFalse(ret_val)
        self.assertIsNone(response)
        self.assertEqual(self.action_result.get_message(), "Error Connecting to server. Details: ('error code', 'error message')")

    def test_process_response_unknown_fail(self):
        """Test the _process_response for unknown response."""
        response_obj = requests.Response()
        response_obj._content = b"dummy content"
        response_obj.status_code = 500
        response_obj.headers = {}

        ret_val, response = self.util._process_response(response_obj, self.action_result)
        self.assertFalse(ret_val)
        self.assertIsNone(response)
        self.assertIn("Can't process response from server. Status Code: 500 Data from server: dummy content", self.action_result.get_message())


class TestFindValueByPattern(unittest.TestCase):
    """Class to test the find_value_by_pattern method."""

    def setUp(self):
        """Set up method for the tests."""
        self.util = SilentpushUtils(None)
        return super().setUp()

    def test_find_value_by_pattern_found(self):
        """Test value found in JSON data."""
        data = {"level1": {"level2": {"key": "value"}}}
        pattern = "level1.level2.key"
        self.assertEqual(self.util.find_value_by_pattern(data, pattern), "value")

    def test_find_value_by_pattern_not_found(self):
        """Test value not found in JSON data."""
        data = {"level1": {"level2": {"key": "value"}}}
        pattern = "level1.level3.key"
        self.assertIsNone(self.util.find_value_by_pattern(data, pattern))

    def test_find_value_by_pattern_with_list(self):
        """Test value found in list."""
        data = {"level1": [{"key": "value1"}, {"key": "value2"}]}
        pattern = "level1.1.key"
        self.assertEqual(self.util.find_value_by_pattern(data, pattern), "value2")


class TestGenerateJsonBody(unittest.TestCase):
    """Class to test the generate_json_body method."""

    def test_generate_json_body(self):
        """Test JSON body generation."""
        util = SilentpushUtils(None)
        body = {"key1": "value1", "key2": PARAM_VALUE, "key3": "{{default_value}}"}
        allow_none = []
        allow_empty = {}
        param = {"param_value": "dynamic_value"}
        default_values = {"default_value": "default_value"}
        expected_body = {"key1": "value1", "key2": "dynamic_value", "key3": "default_value"}
        self.assertEqual(util.generate_json_body(body, allow_none, allow_empty, param, default_values), expected_body)

    def test_generate_json_body_allow_none(self):
        """Test JSON body generation with fields allowed to be None."""
        util = SilentpushUtils(None)
        body = {"key1": "value1", "key2": PARAM_VALUE, "key3": "{{should_be_none}}"}
        allow_none = ["should_be_none"]
        allow_empty = {}
        param = {"param_value": "dynamic_value"}
        default_values = {}
        expected_body = {"key1": "value1", "key2": "dynamic_value", "key3": None}
        self.assertEqual(util.generate_json_body(body, allow_none, allow_empty, param, default_values), expected_body)

    def test_generate_json_body_allow_empty(self):
        """Test JSON body generation with fields that can be empty based on their type."""
        util = SilentpushUtils(None)
        body = {
            "key1": "value1",
            "key2": PARAM_VALUE,
            "key3": "{{should_be_empty_string}}",
            "key4": "{{should_be_empty_list}}",
            "key5": "{{should_be_empty_dict}}",
        }
        allow_none = []
        allow_empty = {"should_be_empty_string": "string", "should_be_empty_list": "list", "should_be_empty_dict": "dict"}
        param = {"param_value": "dynamic_value"}
        default_values = {}
        expected_body = {"key1": "value1", "key2": "dynamic_value", "key3": "", "key4": [], "key5": {}}
        self.assertEqual(util.generate_json_body(body, allow_none, allow_empty, param, default_values), expected_body)


class TestInvokeAPI(unittest.TestCase):
    """Class to test the invoke_api method."""

    def setUp(self):
        """Set up method for the tests."""
        self.mock_connector = Mock()
        self.mock_connector.config = {"verify_server_cert": False}
        self.util = SilentpushUtils(self.mock_connector)
        return super().setUp()

    @patch("silentpush_utils.requests.get")
    def test_invoke_api_success(self, mock_get):
        """Test successful API invocation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"key": "value"}'
        mock_get.return_value = mock_response
        status, response = self.util.invoke_api(mock_get, "http://example.com")
        self.assertTrue(status)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, '{"key": "value"}')

    @patch("silentpush_utils.requests.get")
    def test_invoke_api_failure(self, mock_get):
        """Test API invocation with an exception."""
        mock_get.side_effect = requests.exceptions.ConnectTimeout
        status, response = self.util.invoke_api(mock_get, "http://example.com")
        self.assertFalse(status)
        self.assertIsInstance(response, requests.exceptions.ConnectTimeout)


class TestValidateDropdownMethod(unittest.TestCase):
    """Class to test the validate_dropdown method."""

    def setUp(self):
        """Set up method for the tests."""
        self.util = Validator()
        self.action_result = ActionResult(dict())
        self.dropdown = {"option1": "value1", "option2": "value2", "option3": "value3"}
        return super().setUp()

    @parameterized.expand(
        [["valid_option1", "option1", "value1", ""], ["valid_option2", "option2", "value2", ""], ["valid_option3", "option3", "value3", ""]]
    )
    def test_validate_dropdown_pass(self, _, input_value, expected_value, expected_message):
        """Test the valid cases for the validate dropdown method."""
        ret_val, output = self.util.validate_dropdown(self.action_result, input_value, "choice", self.dropdown)

        self.assertTrue(ret_val)
        self.assertEqual(output, expected_value)
        self.assertEqual(self.action_result.get_message(), expected_message)

    @parameterized.expand(
        [["invalid_option", "option4", None, 'Invalid \'choice\' selected. Must be one of: ["option1", "option2", "option3"].']]
    )
    def test_validate_dropdown_fail(self, _, input_value, expected_value, expected_message):
        """Test the failed cases for the validate dropdown method."""
        ret_val, output = self.util.validate_dropdown(self.action_result, input_value, "choice", self.dropdown)

        self.assertFalse(ret_val)
        self.assertIsNone(output)
        self.assertEqual(self.action_result.get_message(), expected_message)
