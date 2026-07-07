# File: test_dataminrpulse_on_poll.py
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
import uuid
from unittest.mock import patch

import phantom.base_connector as base_conn
import requests_mock

import dataminrpulse_consts as consts
from dataminrpulse_connector import DataminrPulseConnector

from . import dataminrpulse_config


class TestOnPollAction(unittest.TestCase):
    """Class to test the on poll action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = DataminrPulseConnector()
        # Reset the global object to avoid failures
        base_conn.connector_obj = None

        self.test_json = dict(dataminrpulse_config.TEST_JSON)
        self.test_json.update({"action": "on poll", "identifier": "on_poll"})

        return super().setUp()

    @requests_mock.Mocker(real_http=True)
    def test_on_poll_pass(self, mock_get):
        """Test the valid case for the on poll action.

        Token is available in the state file.
        Mock the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)

        self.test_json.update({"user_session_token": dataminrpulse_config.get_session_id(self.connector)})
        self.test_json.get("config").update({"query": "query", "list_names": None, "alert_type": "All", "page_size_for_polling": 40})

        dataminrpulse_config.ALERT_DATA.update({"alertId": str(uuid.uuid4())})

        mock_get.get(
            f"https://gateway.dataminr.com{consts.DATAMINRPULSE_GET_ALERTS}",
            status_code=200,
            headers=dataminrpulse_config.DEFAULT_HEADERS,
            json={"data": {"alerts": [dataminrpulse_config.ALERT_DATA], "from": "from", "to": "to"}},
        )

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_data"][0]["status"], "success")
        self.assertEqual(ret_val["result_summary"]["containers_successful"], 1)
        self.assertEqual(ret_val["result_summary"]["artifacts_successful"], 4)

    @requests_mock.Mocker(real_http=True)
    def test_on_poll_query_pass(self, mock_get):
        """Test the valid case for the on poll action.

        Token is available in the state file.
        Mock the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)

        self.test_json.update({"user_session_token": dataminrpulse_config.get_session_id(self.connector)})
        dataminrpulse_config.ALERT_DATA.update({"alertId": str(uuid.uuid4())})
        self.test_json.update({"query": dataminrpulse_config.ALERT_DATA.get("alertId"), "list_names": None})

        mock_get.get(
            f"https://gateway.dataminr.com{consts.DATAMINRPULSE_GET_ALERTS}",
            status_code=200,
            headers=dataminrpulse_config.DEFAULT_HEADERS,
            json={"data": {"alerts": [dataminrpulse_config.ALERT_DATA], "from": "from", "to": "to"}},
        )

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_data"][0]["status"], "success")
        self.assertEqual(ret_val["result_summary"]["containers_successful"], 1)
        self.assertEqual(ret_val["result_summary"]["artifacts_successful"], 4)

    @requests_mock.Mocker(real_http=True)
    def test_on_poll_listnames_pass(self, mock_get):
        """Test the valid case for the on poll action.

        Token is available in the state file.
        Mock the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)

        self.test_json.update({"user_session_token": dataminrpulse_config.get_session_id(self.connector)})
        dataminrpulse_config.ALERT_DATA.update({"alertId": str(uuid.uuid4())})
        self.test_json.update({"query": dataminrpulse_config.ALERT_DATA.get("alertId"), "list_names": "3557389"})

        mock_get.get(
            f"https://gateway.dataminr.com{consts.DATAMINRPULSE_GET_ALERTS}",
            status_code=200,
            headers=dataminrpulse_config.DEFAULT_HEADERS,
            json={"data": {"alerts": [], "from": "from", "to": "to"}},
        )

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_data"][0]["status"], "success")
        self.assertEqual(ret_val["result_summary"]["containers_successful"], 0)
        self.assertEqual(ret_val["result_summary"]["artifacts_successful"], 0)

    @patch("dataminrpulse_utils.requests.get")
    def test_on_poll_fail(self, mock_get):
        """Test the invalid case for the on poll action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json.get("config").update({"query": "query", "list_names": None, "alert_type": "All", "page_size_for_polling": 40})

        mock_get.return_value.status_code = 401
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"errors": [{"code": 102, "message": "Invalid client Id or client secret"}]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Error code: 102", ret_val["result_data"][0]["message"])

        mock_get.assert_called_with(
            f"https://gateway.dataminr.com{consts.DATAMINRPULSE_GET_ALERTS}",
            headers=dataminrpulse_config.ACTION_HEADER,
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            params={
                "lists": None,
                "query": "query",
                "num": 40,
                "application": "splunk_soar",
                "application_version": dataminrpulse_config.APPLICATION_VERSION,
                "integration_version": dataminrpulse_config.INTEGRATION_VERSION,
            },
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_on_poll_blank_listid_query_fail(self, mock_get):
        """Test the invalid case for the on poll action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json.get("config").update({"query": None, "list_names": None})

        mock_get.return_value.status_code = 401
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = "Please provide either valid 'list names' or 'query' in the asset configuration parameter."

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("provide either valid 'list names' or 'query'", ret_val["result_data"][0]["message"])

    @patch("dataminrpulse_utils.requests.get")
    def test_on_poll_alerttype_fail(self, mock_get):
        """Test the invalid case for the on poll action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json.get("config").update({"list_names": None, "query": "query", "alert_type": "TEST", "page_size_for_polling": 40})

        mock_get.return_value.status_code = 401
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = "Please provide valid value in the 'Alert Type' asset parameter"

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("provide valid value in the 'Alert Type'", ret_val["result_data"][0]["message"])

    @patch("dataminrpulse_utils.requests.get")
    def test_on_poll_pagesize_fail(self, mock_get):
        """Test the invalid case for the on poll action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json.get("config").update({"list_names": None, "query": "query", "alert_type": "All", "page_size_for_polling": -1})

        mock_get.return_value.status_code = 401
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = "Please provide a valid non-negative integer value in the 'Page Size for Polling' parameter"

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("provide a valid non-negative integer", ret_val["result_data"][0]["message"])
