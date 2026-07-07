# File: test_dataminrpulse_on_poll_v4.py
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

import phantom.base_connector as base_conn


try:
    import requests_mock
except ImportError:
    requests_mock = None

from dataminrpulse_connector import DataminrPulseConnector

from . import dataminrpulse_config


class TestOnPollActionV4(unittest.TestCase):
    """Class to test the on poll action for v4 API."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = DataminrPulseConnector()
        # Reset the global object to avoid failures
        base_conn.connector_obj = None

        self.test_json = dict(dataminrpulse_config.TEST_JSON_V4)
        self.test_json.update({"action": "on poll", "identifier": "on_poll"})

        return super().setUp()

    @unittest.skipIf(requests_mock is None, "requests_mock not available")
    @requests_mock.Mocker(real_http=True)
    def test_on_poll_v4_pass(self, mock_get):
        """Test the valid case for the on poll action with v4 API.

        Token is available in the state file.
        Mock the get() to return the valid response.
        """
        dataminrpulse_config.v4_set_state_file(dmaToken=True)
        self.test_json.update({"user_session_token": dataminrpulse_config.get_session_id(self.connector)})

        # Mock v4 API response
        mock_get.get(
            f"https://api.dataminr.com/pulse/v1/alerts",
            status_code=200,
            headers=dataminrpulse_config.V4_DEFAULT_HEADERS,
            json={
                "data": {
                    "alerts": [
                        {
                            "alertId": "test-on-poll-alert-v4",
                            "watchlistsMatchedByType": [{"id": "3557389", "type": "topics", "name": "Cyber Alerts"}],
                            "eventTime": 1757488302315,
                            "source": {"displayName": "test_source", "entityName": "test_source"},
                            "alertType": "Alert",
                            "metadata": {"cyber": {"threatActors": [{"name": "Test Threat Actor"}], "URL": [{"name": "example.com"}]}},
                            "headline": "Test alert for v4 on poll",
                            "publicPost": {"timestamp": "2025-08-11T15:17:26.296Z", "href": "https://example.com/test"},
                        }
                    ]
                }
            },
        )
        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_data"][0]["status"], "success")

    @unittest.skipIf(requests_mock is None, "requests_mock not available")
    @requests_mock.Mocker(real_http=True)
    def test_on_poll_v4_query_pass(self, mock_get):
        """Test the valid case for the on poll action with query for v4 API.

        Token is available in the state file.
        Mock the get() to return the valid response.
        """
        dataminrpulse_config.v4_set_state_file(dmaToken=True)

        self.test_json["config"]["query"] = "test_query_v4"

        mock_get.get(
            f"https://api.dataminr.com/pulse/v1/alerts",
            status_code=200,
            headers=dataminrpulse_config.V4_DEFAULT_HEADERS,
            json={
                "data": {
                    "alerts": [
                        {
                            "alertId": "test-query-on-poll-alert-v4",
                            "watchlistsMatchedByType": [{"id": "3557389", "type": "topics", "name": "Cyber Alerts"}],
                            "eventTime": 1757488302315,
                            "source": {"displayName": "test_source", "entityName": "test_source"},
                            "alertType": "Alert",
                            "metadata": {"cyber": {}},
                            "headline": "Test query alert for v4 on poll",
                            "publicPost": {"timestamp": "2025-08-11T15:17:26.296Z", "href": "https://example.com/query-test"},
                        }
                    ]
                }
            },
        )

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_data"][0]["status"], "success")

    @unittest.skipIf(requests_mock is None, "requests_mock not available")
    @requests_mock.Mocker(real_http=True)
    def test_on_poll_v4_listnames_pass(self, mock_get):
        """Test the valid case for the on poll action with list names for v4 API.

        Token is available in the state file.
        Mock the get() to return the valid response.
        """
        dataminrpulse_config.v4_set_state_file(dmaToken=True)

        # Mock get alerts call
        mock_get.get(
            f"https://api.dataminr.com/pulse/v1/alerts",
            status_code=200,
            headers=dataminrpulse_config.V4_DEFAULT_HEADERS,
            json={
                "data": {
                    "alerts": [
                        {
                            "alertId": "test-list-on-poll-alert-v4",
                            "watchlistsMatchedByType": [{"id": "3557389", "type": "topics", "name": "Cyber Alerts"}],
                            "eventTime": 1757488302315,
                            "source": {"displayName": "test_source", "entityName": "test_source"},
                            "alertType": "Alert",
                            "metadata": {"cyber": {}},
                            "headline": "Test list alert for v4 on poll",
                            "publicPost": {"timestamp": "2025-08-11T15:17:26.296Z", "href": "https://example.com/list-test"},
                        }
                    ]
                }
            },
        )

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_data"][0]["status"], "success")

    @unittest.skipIf(requests_mock is None, "requests_mock not available")
    @requests_mock.Mocker(real_http=True)
    def test_on_poll_v4_fail_unauthorized(self, mock_get):
        """Test the fail case for the on poll action with unauthorized error for v4 API."""
        dataminrpulse_config.v4_set_state_file(dmaToken=True)

        mock_get.get(
            f"https://api.dataminr.com/pulse/v1/alerts",
            status_code=401,
            headers=dataminrpulse_config.V4_DEFAULT_HEADERS,
            json={"error": "Unauthorized", "message": "Invalid token"},
        )

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_data"][0]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
