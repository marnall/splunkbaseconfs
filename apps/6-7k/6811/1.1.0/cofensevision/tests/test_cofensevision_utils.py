# File: test_cofensevision_utils.py
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

import unittest
from unittest.mock import Mock, patch

import requests
from freezegun import freeze_time
from parameterized import parameterized
from phantom.action_result import ActionResult

from cofensevision_utils import CofenseVisionUtils, RetVal
from tests import cofensevision_config


class TestRetValClass(unittest.TestCase):
    """Class to test the RetVal"""

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
        self.util = CofenseVisionUtils(None)
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand(
        [
            ["zero_allowed", "0", 0, ""],
            ["integer", "10", 10, ""],
            ["max_value", "2000", 2000, ""],
        ]
    )
    def test_validate_integer_pass(self, _, input_value, expected_value, expected_message):
        """Test the valid cases for the validate integer method."""
        ret_val, output = self.util.validate_integer(self.action_result, input_value, "page", True, max_value=2000)

        self.assertTrue(ret_val)
        self.assertEqual(output, expected_value)
        self.assertEqual(self.action_result.get_message(), expected_message)

    @parameterized.expand(
        [
            ["float", "10.5", "Please provide a valid integer value in the 'page' parameter"],
            ["negative", "-10", "Please provide a valid non-negative integer value in the 'page' parameter"],
            ["zero_not_allowed", "0", "Please provide a non-zero positive integer value in the 'page' parameter"],
            ["alphanumeric", "abc12", "Please provide a valid integer value in the 'page' parameter"],
            ["max_value", "2001", "Please provide a non-zero positive integer value upto 2000 in the 'page' parameter"],
        ]
    )
    def test_validate_integer_fail(self, _, input_value, expected_message):
        """Test the failed cases for the validate integer method."""
        ret_val, output = self.util.validate_integer(self.action_result, input_value, "page", False, max_value=2000)

        self.assertFalse(ret_val)
        self.assertIsNone(output)
        self.assertEqual(self.action_result.get_message(), expected_message)


class TestEncryptionMethod(unittest.TestCase):
    """Class to test the encryption/decryption methods."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        connector.get_app_json.return_value = {"app_version": "1.0.0"}
        connector.get_asset_id.return_value = "20000"
        connector.error_print.return_value = None
        self.util = CofenseVisionUtils(connector)
        return super().setUp()

    @parameterized.expand(
        [
            ["token1", {"token": {"access_token": cofensevision_config.TOKEN_DUMMY_TEXT_1}}, cofensevision_config.TOKEN_DUMMY_CIPHER_1],
            ["token2", {"token": {"access_token": cofensevision_config.TOKEN_DUMMY_TEXT_2}}, cofensevision_config.TOKEN_DUMMY_CIPHER_2],
            ["no_token", {"app_version": "1.0.0"}, ""],
        ]
    )
    def test_encrypt_state_pass(self, _, input_value, expected_value):
        """Test the pass cases for the encrypt state method."""
        output = self.util.encrypt_state(input_value)
        self.assertEqual(output.get("token", {}).get("access_token", ""), expected_value)

    @parameterized.expand(
        [
            ["token1", {"token": {"access_token": cofensevision_config.TOKEN_DUMMY_CIPHER_1}}, cofensevision_config.TOKEN_DUMMY_TEXT_1],
            ["token2", {"token": {"access_token": cofensevision_config.TOKEN_DUMMY_CIPHER_2}}, cofensevision_config.TOKEN_DUMMY_TEXT_2],
            ["no_token", {"app_version": "1.0.0"}, ""],
        ]
    )
    def test_decrypt_state_pass(self, _, input_value, expected_value):
        """Test the pass cases for the decrypt state method."""
        output = self.util._decrypt_state(input_value)
        self.assertEqual(output.get("token", {}).get("access_token", ""), expected_value)

    @patch("cofensevision_utils.encryption_helper.encrypt")
    def test_encrypt_state_fail(self, mock_encrypt):
        """Test the fail cases for the encrypt state method."""
        mock_encrypt.side_effect = Exception("Couldn't encrypt")

        output = self.util.encrypt_state({"token": {"access_token": cofensevision_config.TOKEN_DUMMY_CIPHER_1}})
        self.assertEqual(output, {"app_version": "1.0.0"})

    @patch("cofensevision_utils.encryption_helper.decrypt")
    def test_decrypt_state_fail(self, mock_decrypt):
        """Test the fail cases for the decrypt state method."""
        mock_decrypt.side_effect = Exception("Couldn't decrypt")

        output = self.util._decrypt_state({"token": {"access_token": cofensevision_config.TOKEN_DUMMY_CIPHER_1}})
        self.assertEqual(output, {"app_version": "1.0.0"})


class TestSplitSeparatedValuesMethod(unittest.TestCase):
    """Class to test the split value list method."""

    def setUp(self):
        """Set up method for the tests."""
        self.util = CofenseVisionUtils(None)
        return super().setUp()

    def test_split_value_list_pass(self):
        """Test the pass cases for the split values method."""
        output = self.util.split_value_list("abc,pqr", ",")
        self.assertEqual(output, ["abc", "pqr"])


class TestParseDateMethod(unittest.TestCase):
    """Class to test the parse date method."""

    def setUp(self):
        """Set up method for the tests."""
        self.util = CofenseVisionUtils(None)
        return super().setUp()

    @parameterized.expand(
        [
            ["date", "01 Mar 2021", "2021-03-01T00:00:00.000000Z"],
            ["date_time", "01 Feb 2021 04:45:33", "2021-02-01T04:45:33.000000Z"],
            ["iso_format", "2022-04-17T14:05:44Z", "2022-04-17T14:05:44.000000Z"],
            ["empty_value", "", None],
        ]
    )
    def test_parse_date_string_pass(self, _, input_val, expected):
        """Test the pass cases for the parse date method."""
        ret_val, output = self.util.parse_date_string(input_val)
        self.assertTrue(ret_val)
        self.assertEqual(output, expected)

    @parameterized.expand(
        [
            ["date", "01 Month 2021"],
            ["date_time", "35 Feb 2021 04:45:33"],
            ["iso_format", "20222-04-17T14:05:44Z"],
            ["large_epoch", "912345678987654321"],
        ]
    )
    def test_parse_date_string_fail(self, _, input_val):
        """Test the fail cases for the parse date method."""
        ret_val, output = self.util.parse_date_string(input_val)
        self.assertFalse(ret_val)
        self.assertIsNone(output)

    @freeze_time("2012-01-01")
    def test_default_value(self):
        """Test the valid case for the parse date method."""
        ret_val, output = self.util.parse_date_string("", default_value=True)
        self.assertTrue(ret_val)
        self.assertEqual(output, "2012-01-01T00:00:00.000000Z")


class TestValidateSortParam(unittest.TestCase):
    """Class to test the validate sort param method."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        self.util = CofenseVisionUtils(connector)
        return super().setUp()

    @parameterized.expand(
        [
            ["no_fields", "", True, None],
            ["single_field", "id:desc", True, ["id,desc"]],
            ["multiple_fields_valid_format", "id:desc,modifiedDate:asc", True, ["id,desc", "modifiedDate,asc"]],
            ["multiple_fields_valid_without_order", "id:desc,modifiedDate", True, ["id,desc", "modifiedDate"]],
            ["multiple_fields_invalid_field", "receivedAfterDate:desc,modifiedDate", False, None],
            ["multiple_fields_invalid_field_without_order", "id:desc,receivedAfterDate", False, None],
            ["multiple_fields_invalid_order", "id:invalid,modifiedDate", False, None],
            ["more_than_2_properties_invalid", "id:asc:3rd,modifiedDate", False, None],
        ]
    )
    def test_validate_sort_param_for_list_quarantine_jobs(self, _, input_value, expected_status, expected_values):
        """Test the pass and fail cases to validate sort param for 'list_quarantine_jobs' action."""
        self.util._connector.get_action_identifier.return_value = "list_quarantine_jobs"
        ret_val, values = self.util.validate_sort_param(input_value)
        self.assertEqual(ret_val, expected_status)
        self.assertEqual(values, expected_values)

    @parameterized.expand(
        [
            ["no_fields", "", True, None],
            ["single_field", "id:desc", True, ["id,desc"]],
            ["multiple_fields_valid_format", "id:desc,modifiedDate:asc", True, ["id,desc", "modifiedDate,asc"]],
            ["multiple_fields_valid_without_order", "id:desc,modifiedDate", True, ["id,desc", "modifiedDate"]],
            ["multiple_fields_invalid_field", "stopRequested:desc,modifiedDate", False, None],
            ["multiple_fields_invalid_field_without_order", "id:desc,updatedAt", False, None],
            ["multiple_fields_invalid_order", "id:invalid,modifiedDate", False, None],
            ["more_than_2_properties_invalid", "id:asc:3rd,modifiedDate", False, None],
        ]
    )
    def test_validate_sort_param_for_list_message_searches(self, _, input_value, expected_status, expected_values):
        """Test the pass and fail cases to validate sort param for 'list_message_searches' action."""
        self.util._connector.get_action_identifier.return_value = "list_message_searches"
        ret_val, values = self.util.validate_sort_param(input_value)
        self.assertEqual(ret_val, expected_status)
        self.assertEqual(values, expected_values)

    @parameterized.expand(
        [
            ["no_fields", "", True, None],
            ["single_field", "updatedAt:desc", True, ["updatedAt,desc"]],
            ["single_field_valid_without_order", "updatedAt", True, ["updatedAt"]],
            ["single_field_invalid_order", "updatedAt:invalid", False, None],
            ["single_field_invalid_field", "modifiedDate:asc", False, None],
            ["multiple_fields_invalid_field", "updatedAt:desc,modifiedDate", False, None],
            ["more_than_2_properties_invalid", "updatedAt:asc:3rd", False, None],
        ]
    )
    def test_validate_sort_param_for_list_iocs(self, _, input_value, expected_status, expected_values):
        """Test the pass and fail cases of validate sort param method."""
        self.util._connector.get_action_identifier.return_value = "list_iocs"
        ret_val, values = self.util.validate_sort_param(input_value)
        self.assertEqual(ret_val, expected_status)
        self.assertEqual(values, expected_values)

    @parameterized.expand(
        [
            ["no_fields", "", True, None],
            ["single_field", "id:desc", True, ["id,desc"]],
            ["multiple_fields_valid_format", "id:desc,processedOn:asc", True, ["id,desc", "processedOn,asc"]],
            ["multiple_fields_valid_without_order", "id:desc,processedOn", True, ["id,desc", "processedOn"]],
            ["multiple_fields_invalid_field", "stopRequested:desc,processedOn", False, None],
            ["multiple_fields_invalid_field_without_order", "id:desc,updatedAt", False, None],
            ["multiple_fields_invalid_order", "id:invalid,processedOn", False, None],
            ["more_than_2_properties_invalid", "id:asc:3rd,processedOn", False, None],
        ]
    )
    def test_validate_sort_param_for_get_message_search_results(self, _, input_value, expected_status, expected_values):
        """Test the pass and fail cases to validate sort param for 'get_message_search_results' action."""
        self.util._connector.get_action_identifier.return_value = "get_message_search_results"
        ret_val, values = self.util.validate_sort_param(input_value)
        self.assertEqual(ret_val, expected_status)
        self.assertEqual(values, expected_values)


class TestGetErrorMessageFromException(unittest.TestCase):
    """Class to test the get error message from exception method."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        connector.error_print.return_value = None
        self.util = CofenseVisionUtils(connector)
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
        self.util = CofenseVisionUtils(None)
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
    """Class to test the process html response method."""

    def setUp(self):
        """Set up method for the tests."""
        self.response = Mock()
        self.util = CofenseVisionUtils(None)
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
    """Class to test the process json response method."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        connector.error_print.return_value = None
        self.response = Mock()
        self.util = CofenseVisionUtils(connector)
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand(
        [
            ["token_response", 200, True, "dummy_token_value", {"token": "dummy_token_value"}],
            ["valid_success_json_response", 200, True, {"results": []}, {"results": []}],
            ["valid_failure_json_response", 404, False, {"status": "NOT_FOUND"}, None],
            ["invalid_json_response", 404, False, KeyError("Invalid Json"), None],
        ]
    )
    def test_process_json_response(self, name, mock_code, expected_status, mock_response, expected_value):
        """Test the pass and fail cases of process json response method."""
        self.response.status_code = mock_code
        if "token_response" in name:
            self.util._get_token = True
            self.util._is_generate_token = False
            self.response.text = mock_response
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
        connector.config = {"base_url": "https://<base_url>/"}
        self.util = CofenseVisionUtils(connector)
        self.action_result = ActionResult(dict())
        return super().setUp()

    def test_make_rest_call_invalid_method(self):
        """Test the _make_rest_call with invalid method."""
        ret_val, response = self.util.make_rest_call("/endpoint", self.action_result, method="invalid_method")
        self.assertFalse(ret_val)
        self.assertIsNone(response)
        self.assertEqual(self.action_result.get_message(), "Invalid method: invalid_method")

    @patch("cofensevision_utils.requests.get")
    def test_make_rest_call_throw_exception(self, mock_get):
        """Test the _make_rest_call for error case."""
        mock_get.side_effect = Exception("error code", "error message")

        ret_val, response = self.util.make_rest_call("/endpoint", self.action_result)
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
