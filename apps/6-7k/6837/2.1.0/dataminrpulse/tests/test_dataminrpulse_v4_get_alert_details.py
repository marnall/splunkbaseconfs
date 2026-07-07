# File: test_dataminrpulse_get_alert_details.py
#
# Copyright (c) 2023-2026 Dataminr
#
# This unpublished material is proprietary to Dataminr.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Dataminr.
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

import dataminrpulse_consts as consts
from dataminrpulse_connector import DataminrPulseConnector

from . import dataminrpulse_config


class TestGetAlertDetailsAction(unittest.TestCase):
    """Class to test the get alert details action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = DataminrPulseConnector()
        self.test_json = dict(dataminrpulse_config.TEST_JSON)
        self.test_json.update({"action": "get alert details", "identifier": "get_alert_details"})

        return super().setUp()

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alert_details_with_alert_id_pass(self, mock_get):
        """
        Test the valid case for the get alert details action with alert_id.

        Token is available in the state file.
        Mock the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)

        self.test_json["config"]["api_version"] = "v4"
        self.test_json["parameters"] = [{"alert_id": "1986897266-1757488294202-3"}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {
            "data": {
                "alerts": [
                    {
                        "alertId": "1986897266-1757488294202-3",
                        "watchlistsMatchedByType": [{"id": "3557389", "type": "topics", "name": "Cyber Alerts"}],
                        "eventTime": 1757488302315,
                        "source": {"displayName": "test_source", "entityName": "test_source"},
                        "alertType": "Alert",
                        "metadata": {"cyber": {"threatActors": [{"name": "Test Threat Actor"}], "URL": [{"name": "example.com"}]}},
                        "headline": "Test alert details",
                        "publicPost": {"timestamp": "2025-08-11T15:17:26.296Z", "href": "https://example.com/test"},
                    }
                ]
            }
        }

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Successfully fetched alert details")
        self.assertEqual(len(ret_val["result_data"][0]["data"]), 1)
        self.assertEqual(ret_val["result_data"][0]["data"][0]["data"]["alerts"][0]["alertId"], "1986897266-1757488294202-3")

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alert_details_with_artifact_id_pass(self, mock_get):
        """
        Test the valid case for the get alert details action with artifact_id.

        Mock the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)

        self.test_json["config"]["api_version"] = "v4"
        self.test_json["parameters"] = [{"artifact_id": "12345"}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {
            "cef": {
                "alertId": "test-artifact-alert-id",
                "watchlistsMatchedByType": [{"id": "3557389", "type": "topics", "name": "Cyber Alerts"}],
                "eventTime": 1757488302315,
                "source": {"displayName": "artifact_source", "entityName": "artifact_source"},
                "alertType": "Alert",
                "metadata": {"cyber": {"threatActors": [{"name": "Artifact Threat Actor"}], "URL": [{"name": "artifact-example.com"}]}},
                "headline": "Test artifact alert details",
            }
        }

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Successfully fetched alert details")
        self.assertEqual(ret_val["result_data"][0]["data"][0]["alertId"], "test-artifact-alert-id")

        # Verify artifact API endpoint is called
        expected_url = f"https://127.0.0.1:8443//rest/artifact/12345"
        mock_get.assert_called_with(expected_url, headers=None, timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT, params=None, verify=False)

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alert_details_v3_api_fail(self, mock_get):
        """Test the fail case for the get alert details action with v3 API version."""
        dataminrpulse_config.set_state_file(dmaToken=True)

        self.test_json["config"]["api_version"] = "v3"
        self.test_json["parameters"] = [{"alert_id": "1986897266-1757488294202-3"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Please use the latest v4 API version", ret_val["result_data"][0]["message"])

        # Verify no API call is made
        mock_get.assert_not_called()

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alert_details_missing_parameters_fail(self, mock_get):
        """Test the fail case for the get alert details action with missing parameters."""
        dataminrpulse_config.set_state_file(dmaToken=True)

        self.test_json["config"]["api_version"] = "v4"
        self.test_json["parameters"] = [{}]  # No alert_id or artifact_id

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Please provide either artifact_id or alert_id", ret_val["result_data"][0]["message"])

        # Verify no API call is made
        mock_get.assert_not_called()

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alert_details_api_error_fail(self, mock_get):
        """Test the fail case for the get alert details action with API error."""
        dataminrpulse_config.set_state_file(dmaToken=True)

        self.test_json["config"]["api_version"] = "v4"
        self.test_json["parameters"] = [{"alert_id": "1986897266-1757488294202-3"}]

        mock_get.return_value.status_code = 401
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"error": "unauthorized", "message": "Invalid token"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alert_details_server_error_fail(self, mock_get):
        """Test the fail case for the get alert details action with server error."""
        dataminrpulse_config.set_state_file(dmaToken=True)

        self.test_json["config"]["api_version"] = "v4"
        self.test_json["parameters"] = [{"alert_id": "1986897266-1757488294202-3"}]

        mock_get.return_value.status_code = 500
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"error": "internal_server_error", "message": "Internal server error occurred"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alert_details_with_metadata_transformation(self, mock_get):
        """Test that metadata is properly transformed to list format."""
        dataminrpulse_config.set_state_file(dmaToken=True)

        self.test_json["config"]["api_version"] = "v4"
        self.test_json["parameters"] = [{"alert_id": "1986897266-1757488294202-3"}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {
            "data": {
                "alerts": [
                    {
                        "alertId": "1986897266-1757488294202-3",
                        "headline": "Test metadata transformation",
                        "alertType": "Alert",
                        "metadata": [{"cyber": {"URL": ["example.com"], "hashes": ["abc123"]}}],
                    }
                ]
            }
        }

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")

        # Verify metadata is transformed to list
        alert_data = ret_val["result_data"][0]["data"][0]["data"]["alerts"][0]
        self.assertIsInstance(alert_data["metadata"], list)
        self.assertEqual(len(alert_data["metadata"]), 1)
        self.assertIn("cyber", alert_data["metadata"][0])


if __name__ == "__main__":
    unittest.main()
