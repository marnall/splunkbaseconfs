# File: test_dataminrpulse_get_alerts_v4.py
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


class TestGetAlertsActionV4(unittest.TestCase):
    """Class to test the get alerts action for v4 API."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = DataminrPulseConnector()
        self.test_json = dict(dataminrpulse_config.TEST_JSON_V4)
        self.test_json.update({"action": "get alerts", "identifier": "get_alerts"})
        # Force v4 API usage
        self.connector._use_v4_api = True
        return super().setUp()

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_v4_pass(self, mock_get):
        """Test the valid case for the get alerts action with v4 API.

        Token is available in the state file.
        Mock the get() to return the valid response.
        """
        dataminrpulse_config.v4_set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{"list_id": "4773235", "query": None, "from": None, "to": None, "num": 1}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        # v4 API response format based on Postman collection
        mock_get.return_value.json.return_value = {
            "previousPage": None,
            "nextPage": "/v1/alerts?lists=4773235&from=H4sIAAAAAAAA...",
            "alerts": [
                {
                    "metadata": {"cyber": {"threatActors": [{"name": "Test Threat Actor"}], "URL": [{"name": "example.com"}]}},
                    "headline": "Test alert headline for v4 API",
                    "publicPost": {"timestamp": "2025-08-11T15:17:26.296Z", "href": "https://example.com/test", "media": []},
                    "alertId": "test-alert-id-v4",
                    "alertType": "Alert",
                }
            ],
        }

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Api version used: v4, Total alerts: 1")

        # Verify v4 API endpoint is called
        mock_get.assert_called_with(
            f"https://api.dataminr.com/pulse/v1/alerts",
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            headers=dataminrpulse_config.V4_ACTION_HEADER,
            params={"lists": "4773235", "query": None, "from": None, "to": None, "pageSize": 40},
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_v4_with_query_pass(self, mock_get):
        """Test the valid case for the get alerts action with query parameter for v4 API."""
        dataminrpulse_config.v4_set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{"list_id": None, "query": "test_query_v4", "from": None, "to": None, "num": 1}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {
            "previousPage": None,
            "nextPage": None,
            "alerts": [
                {
                    "metadata": {"cyber": {}},
                    "headline": "Test query alert for v4 API",
                    "publicPost": {"timestamp": "2025-08-11T15:17:26.296Z", "href": "https://example.com/query-test"},
                    "alertId": "test-query-alert-id-v4",
                    "alertType": "Alert",
                }
            ],
        }

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Api version used: v4, Total alerts: 1")

        mock_get.assert_called_with(
            f"https://api.dataminr.com/pulse/v1/alerts",
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            headers=dataminrpulse_config.V4_ACTION_HEADER,
            params={"lists": None, "query": "test_query_v4", "from": None, "to": None, "pageSize": 40},
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_v4_with_pagination_pass(self, mock_get):
        """Test the valid case for the get alerts action with pagination for v4 API."""
        dataminrpulse_config.v4_set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{"list_id": "4773235", "query": None, "from": None, "to": None, "num": 100}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {
            "previousPage": None,
            "nextPage": "/v1/alerts?lists=4773235&from=H4sIAAAAAAAA...",
            "alerts": [],  # Empty alerts for pagination test
        }

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Api version used: v4, Total alerts: 0")

        mock_get.assert_called_with(
            f"https://api.dataminr.com/pulse/v1/alerts",
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            headers=dataminrpulse_config.V4_ACTION_HEADER,
            params={"lists": "4773235", "query": None, "from": None, "to": None, "pageSize": 40},
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_v4_fail_unauthorized(self, mock_get):
        """Test the fail case for the get alerts action with unauthorized error for v4 API."""
        dataminrpulse_config.v4_set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{"list_id": "4773235", "query": None, "from": None, "to": None, "num": 1}]

        mock_get.return_value.status_code = 401
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"error": "Unauthorized", "message": "Invalid token"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_v4_fail_bad_request(self, mock_get):
        """Test the fail case for the get alerts action with bad request error for v4 API."""
        dataminrpulse_config.v4_set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{"list_id": "invalid_list", "query": None, "from": None, "to": None, "num": 1}]

        mock_get.return_value.status_code = 400
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"error": "Bad Request", "message": "Invalid list ID"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_v4_empty_response(self, mock_get):
        """Test the case where v4 API returns empty alerts."""
        dataminrpulse_config.v4_set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{"list_id": "4773235", "query": None, "from": None, "to": None, "num": 1}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"previousPage": None, "nextPage": None, "alerts": []}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Api version used: v4, Total alerts: 0")


if __name__ == "__main__":
    unittest.main()
