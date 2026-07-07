# File: test_vectraxdr_utils.py
#
# Copyright (c) 2024-2025 Vectra
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

import os
import shutil
import unittest
from unittest.mock import Mock, patch

import phantom.app as phantom
from parameterized import parameterized
from phantom.action_result import ActionResult

import vectrandr_consts as consts
from vectrandr_connector import VectraNDRConnector
from vectrandr_utils import RetVal, VectraNDRUtils


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
        self.util = VectraNDRUtils(None)
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand(
        [
            ["zero_allowed", "0", 0, ""],
            ["integer", "10", 10, ""],
        ]
    )
    def test_validate_integer_pass(self, _, input_value, expected_value, expected_message):
        """Test the valid cases for the validate integer method."""
        ret_val, output = self.util._validate_integer(self.action_result, input_value, "page", True)

        self.assertTrue(ret_val)
        self.assertEqual(output, expected_value)
        self.assertEqual(self.action_result.get_message(), expected_message)

    @parameterized.expand(
        [
            ["float", "10.5", "Please provide a valid integer value in the 'page' parameter"],
            ["negative", "-10", "Please provide a valid non-negative integer value in the 'page' parameter"],
            ["zero_not_allowed", "0", "Please provide a non-zero positive integer value in the 'page' parameter"],
            ["alphanumeric", "abc12", "Please provide a valid integer value in the 'page' parameter"],
        ]
    )
    def test_validate_integer_fail(self, _, input_value, expected_message):
        """Test the failed cases for the validate integer method."""
        ret_val, output = self.util._validate_integer(self.action_result, input_value, "page", False)

        self.assertFalse(ret_val)
        self.assertIsNone(output)
        self.assertEqual(self.action_result.get_message(), expected_message)


class TestGetErrorMessageFromException(unittest.TestCase):
    """Class to test the get error message from exception method."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        connector.error_print.return_value = None
        self.util = VectraNDRUtils(connector)
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
        self.util = VectraNDRUtils(None)
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
        self.util = VectraNDRUtils(None)
        self.action_result = ActionResult(dict())
        return super().setUp()

    @parameterized.expand(
        [
            [
                "normal_response",
                "Oops!<script>document.getElementById('demo')</script>",
                False,
                "Error from server. Status code: 500, Reason: Internal Server Error, Error message: Oops!",
            ],
        ]
    )
    def test_process_html_response(self, _, response_value, expected_value, expected_message):
        """Test the pass and fail cases of process html response method."""
        if response_value:
            self.response.text = response_value
        self.response.status_code = 500
        self.response.reason = "Internal Server Error"
        status, value = self.util._process_html_response(self.response, self.action_result)
        self.assertEqual(status, expected_value)
        self.assertEqual(self.action_result.get_message(), expected_message)
        self.assertIsNone(value)


class TestProcessJsonResponse(unittest.TestCase):
    """Test the pass and fail cases of process json response method."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        connector.error_print.return_value = None
        self.response = Mock()
        self.util = VectraNDRUtils(connector)
        self.action_result = ActionResult(dict())
        return super().setUp()

    def test_successful_response(self):
        """Test the successful response of the _process_json_response function."""
        self.response.status_code = 200
        self.response.json.return_value = {"key": "value"}

        action_result_mock = Mock()

        result = self.util._process_json_response(self.response, self.action_result)

        self.assertEqual(result, (True, {"key": "value"}))
        action_result_mock.set_status.assert_not_called()

    def test_error_response(self):
        """Test the error response handling of the _process_json_response method."""
        self.response.status_code = 400
        self.response.json.return_value = {"error": "Bad request"}

        result = self.util._process_json_response(self.response, self.action_result)

        self.assertEqual(result[0], False)

    def test_json_parsing_error(self):
        """Test the parsing error response handling of the _process_json_response method."""
        self.response = Mock()
        self.response.json.side_effect = ValueError("Invalid JSON")

        result = self.util._process_json_response(self.response, self.action_result)

        self.assertEqual(result[0], False)


class TestProcessPcapResponse(unittest.TestCase):
    """Test the pass and fail cases of process pcap response method."""

    def setUp(self):
        """Set up method for the tests."""
        connector = Mock()
        connector.error_print.return_value = None
        self.response = Mock()
        self.util = VectraNDRUtils(connector)
        self.action_result = ActionResult(dict())

    def tearDown(self):
        """Tear down method for the tests."""
        # Delete the file after the test is complete
        if os.path.exists(self.util.file_path):
            shutil.rmtree(os.path.dirname(self.util.file_path))

    def test_process_pcap_response_success(self):
        """
        Test the process_pcap_response method when the response is successful.

        This function mocks the necessary objects and sets the necessary attributes
        on the response object. It then calls the _process_pcap_response method
        of the util object being tested. The function asserts that the expected
        result is returned and that the progress message is saved. It also asserts
        that the file was written to disk correctly.

        :param self.response: The response object to be used for testing.
        :param self.action_result: The action result object to be used for testing.
        :return: None
        """
        # Mock the necessary objects
        self.response.headers = {"Content-Disposition": 'attachment; filename="test.txt"'}
        self.response.status_code = 200
        self.response.iter_content.return_value = [b"chunk1", b"chunk2"]

        # Call the function being tested
        result = self.util._process_pcap_response(self.response, self.action_result)

        # Assert the expected result
        self.assertEqual(result[0], phantom.APP_SUCCESS)
        self.assertIsNone(result[1])

        # Assert that the progress message was saved
        # self.util._connector.save_progress.assert_called_with_prefix("Using temp directory: /opt/phantom/vault/tmp/{guid}")

        # Assert that the file was written to disk correctly
        with open(self.util.file_path, "rb") as f:
            data = f.read()
            self.assertEqual(data, b"chunk1chunk2")

    def test_process_pcap_response_error(self):
        """
        Test the _process_pcap_response method when there is an error in the response.

        This method sets the headers, status code, and text of the response object
        to simulate an error response. It then calls the _process_pcap_response
        method of the Util class with the response and action_result objects as
        parameters. Finally, it asserts that the result returned by the method
        is as expected.

        Parameters:
        - self: The current instance of the test class.

        Returns:
        - None
        """
        self.response.headers = {"Content-Disposition": 'attachment; filename="test.txt"'}
        self.response.status_code = 400
        self.response.text = "Server Error"

        # Call the function being tested
        result = self.util._process_pcap_response(self.response, self.action_result)

        # Assert the expected result
        self.assertEqual(result[0], phantom.APP_ERROR)
        self.assertIsNone(result[1])


class TestCreateCriticalSeverity(unittest.TestCase):
    """Test the pass and fail cases of create critical severity method."""

    def setUp(self):
        """Set up method for the tests."""
        self._connector = VectraNDRConnector()
        self._connector.config = {"api_token": "new_key"}
        self._connector.get_phantom_base_url = lambda: "http://example:8445/"
        self.util = VectraNDRUtils(self._connector)
        self.action_result = ActionResult(dict())

    @patch("vectrandr_utils.VectraNDRUtils._common_message_handler_for_soar")
    @patch("requests.post")
    @patch("requests.get")
    @patch("requests.delete")
    def test_create_critical_severity(self, mock_delete, mock_get, mock_post, common_handler):
        """
        Test case for creating a critical severity.

        This function tests the successful creation of a critical severity. It mocks the necessary
        dependencies and verifies that the appropriate API calls are made.

        Parameters:
        - mock_delete: The mock object for the 'requests.delete' function.
        - mock_get: The mock object for the 'requests.get' function.
        - mock_post: The mock object for the 'requests.post' function.
        - common_handler: The mock object for the '_common_message_handler_for_soar' function.

        Returns:
        - None
        """
        # Test successful creation of critical severity
        url = consts.SPLUNK_SOAR_CREATE_SEVERITY_ENDPOINT.format(url="http://example:8445/")

        mock_post.return_value.status_code = 200
        mock_get.return_value.status_code = 200
        common_handler.return_value = {"data": [{"id": 1, "name": "high"}]}
        mock_delete.return_value.status_code = 200

        self.util._create_critical_severity()
        self.assertEqual(mock_post.call_count, 2)
        mock_get.assert_called_once_with(url, verify=False)
        mock_delete.assert_called_once_with(f"{url}/1", verify=False)
