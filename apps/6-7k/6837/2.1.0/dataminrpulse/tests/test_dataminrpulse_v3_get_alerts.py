# File: test_dataminrpulse_get_alerts.py
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

import requests

import dataminrpulse_consts as consts
from dataminrpulse_connector import DataminrPulseConnector

from . import dataminrpulse_config


class TestGetAlertsAction(unittest.TestCase):
    """Class to test the get alerts action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = DataminrPulseConnector()
        self.test_json = dict(dataminrpulse_config.TEST_JSON)
        self.test_json.update({"action": "get alerts", "identifier": "get_alerts"})

        return super().setUp()

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_pass(self, mock_get):
        """Test the valid case for the get alerts action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{"list_id": "3557389", "query": "1247060284", "from": None, "to": None, "num": 1}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"data": {"alerts": ["dummy_data"], "from": "dummy_from", "to": "dummy_to"}}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Api version used: v3, Total alerts: 1")

        mock_get.assert_called_with(
            f"https://gateway.dataminr.com{consts.DATAMINRPULSE_GET_ALERTS}",
            headers={"Authorization": "Dmauth <dummy_token>"},
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            params={
                "lists": "3557389",
                "query": "1247060284",
                "from": None,
                "to": None,
                "num": 40,
                "application": "splunk_soar",
                "application_version": dataminrpulse_config.APPLICATION_VERSION,
                "integration_version": dataminrpulse_config.INTEGRATION_VERSION,
            },
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_fail(self, mock_get):
        """Test the get alerts action with unauthorized error.

        Token is available in the state file.
        Patch the get() to return the unauthorized response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{"list_id": "3557389", "query": "1247060284", "from": None, "to": None, "num": 1}]

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
                "lists": "3557389",
                "query": "1247060284",
                "from": None,
                "to": None,
                "num": 40,
                "application": "splunk_soar",
                "application_version": dataminrpulse_config.APPLICATION_VERSION,
                "integration_version": dataminrpulse_config.INTEGRATION_VERSION,
            },
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_listid_pass(self, mock_get):
        """Test the valid case for the get alerts action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{"list_id": "3557389", "query": None, "from": None, "to": None, "num": 1}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"data": {"alerts": ["dummy_data"], "from": "dummy_from", "to": "dummy_to"}}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Api version used: v3, Total alerts: 1")

        mock_get.assert_called_with(
            f"https://gateway.dataminr.com{consts.DATAMINRPULSE_GET_ALERTS}",
            headers=dataminrpulse_config.ACTION_HEADER,
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            params={
                "lists": "3557389",
                "query": None,
                "from": None,
                "to": None,
                "num": 40,
                "application": "splunk_soar",
                "application_version": dataminrpulse_config.APPLICATION_VERSION,
                "integration_version": dataminrpulse_config.INTEGRATION_VERSION,
            },
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_use_asset_configured_lists_fail(self, mock_get):
        """Test the valid case for the get alerts action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)

        self.test_json["parameters"] = [{"list_id": None, "query": None, "from": None, "to": None, "num": 1, "use_asset_configured_lists": True}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"data": {"alerts": ["dummy_data"], "from": "dummy_from", "to": "dummy_to"}}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(
            ret_val["result_data"][0]["message"],
            "Please provide either valid 'list names' in asset configuration parameter or 'query' in action parameter",
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_use_asset_configured_lists_pass(self, mock_get):
        """Test the valid case for the get alerts action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["config"]["list_names"] = "test1"
        self.test_json["parameters"] = [{"list_id": None, "query": None, "from": None, "to": None, "num": 1, "use_asset_configured_lists": True}]

        get_response_1 = requests.Response()
        get_response_1._content = json.dumps(dataminrpulse_config.JSON_DATA).encode()
        get_response_1.status_code = 200
        get_response_1.headers = dataminrpulse_config.DEFAULT_HEADERS

        get_response_2 = requests.Response()
        get_response_2._content = json.dumps({}).encode()
        get_response_2.status_code = 200
        get_response_2.headers = dataminrpulse_config.DEFAULT_HEADERS

        mock_get.side_effect = [get_response_1, get_response_2]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Api version used: v3, Total alerts: 0")

        mock_get.assert_called_with(
            f"https://gateway.dataminr.com{consts.DATAMINRPULSE_GET_ALERTS}",
            headers={"Authorization": "Dmauth <dummy_token>"},
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            params={
                "lists": "3557389",
                "query": None,
                "from": None,
                "to": None,
                "num": 40,
                "application": "splunk_soar",
                "application_version": dataminrpulse_config.APPLICATION_VERSION,
                "integration_version": dataminrpulse_config.INTEGRATION_VERSION,
            },
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_listid_use_asset_configured_lists_pass(self, mock_get):
        """Test the valid case for the get alerts action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["config"]["list_names"] = "test1"
        self.test_json["parameters"] = [
            {"list_id": ",,,", "query": None, "from": None, "to": None, "num": 1, "use_asset_configured_lists": True}
        ]

        get_response_1 = requests.Response()
        get_response_1._content = json.dumps(dataminrpulse_config.JSON_DATA).encode()
        get_response_1.status_code = 200
        get_response_1.headers = dataminrpulse_config.DEFAULT_HEADERS

        get_response_2 = requests.Response()
        get_response_2._content = json.dumps({}).encode()
        get_response_2.status_code = 200
        get_response_2.headers = dataminrpulse_config.DEFAULT_HEADERS

        mock_get.side_effect = [get_response_1, get_response_2]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Api version used: v3, Total alerts: 0")

        mock_get.assert_called_with(
            f"https://gateway.dataminr.com{consts.DATAMINRPULSE_GET_ALERTS}",
            headers={"Authorization": "Dmauth <dummy_token>"},
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            params={
                "lists": "3557389",
                "query": None,
                "from": None,
                "to": None,
                "num": 40,
                "application": "splunk_soar",
                "application_version": dataminrpulse_config.APPLICATION_VERSION,
                "integration_version": dataminrpulse_config.INTEGRATION_VERSION,
            },
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_query_pass(self, mock_get):
        """Test the valid case for the get alerts action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{"list_id": None, "query": "1247060284", "from": None, "to": None, "num": 1}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"data": {"alerts": ["dummy_data"], "from": "dummy_from", "to": "dummy_to"}}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Api version used: v3, Total alerts: 1")

        mock_get.assert_called_with(
            f"https://gateway.dataminr.com{consts.DATAMINRPULSE_GET_ALERTS}",
            headers=dataminrpulse_config.ACTION_HEADER,
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            params={
                "lists": None,
                "query": "1247060284",
                "from": None,
                "to": None,
                "num": 40,
                "application": "splunk_soar",
                "application_version": dataminrpulse_config.APPLICATION_VERSION,
                "integration_version": dataminrpulse_config.INTEGRATION_VERSION,
            },
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_from_pass(self, mock_get):
        """Test the valid case for the get alerts action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["parameters"] = [
            {
                "list_id": None,
                "query": "1247060284",
                "from": "H4sIAAAAAAAAAFXQ3StDcQDG8fOsX5IkSZIkSZLQWpIkIU6SJEmSZLWl1do05x+glYlWxCwkSWueiZCXyKJ2RdmSK++"  # pragma: allowlist secret
                "NpIXOrhw1i1t336vPxVcn9IpxaMhsarSaHcpIxbDRoVgUi91mNg2+jhLN/kWiPzRPNHkjxMDKtIos1wbRFzkhSqI"  # pragma: allowlist secret
                "+ov5ql2jQ7lRkr015hM61RXQ7tTmRcrQdQKu2TrTziih1h4jy4DGRv3xPlLmO4kjfCHtEajCuInP5j+9ZvSC6xq"  # pragma: allowlist secret
                "JE59OKihx1h6jZPyTk6wOiyOf0COE/Iyo/H4i62DNRnUzOijRta05Ilx9E8dsPkbepErkvl4TBtUAULoWJgpvJODK0"  # pragma: allowlist secret
                "v9LzkaidiREdpxNE790XUXUeINokw78VNrutxWRR7A6L0Zru/fDKaYnxaVmE/DNyavD2ewFSIuyRU9yn87JOktTd99ie8ReGnElETwEAAA==",  # pragma: allowlist secret
                "to": None,
                "num": 1,
            }
        ]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"data": {"alerts": ["dummy_data"], "from": "dummy_from", "to": "dummy_to"}}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Api version used: v3, Total alerts: 1")

        mock_get.assert_called_with(
            f"https://gateway.dataminr.com{consts.DATAMINRPULSE_GET_ALERTS}",
            headers=dataminrpulse_config.ACTION_HEADER,
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            params={
                "lists": None,
                "query": "1247060284",
                "from": "H4sIAAAAAAAAAFXQ3StDcQDG8fOsX5IkSZIkSZLQWpIkIU6SJEmSZLWl1do05x+glYlWxCwkSWueiZCXyKJ2RdmSK++"  # pragma: allowlist secret
                "NpIXOrhw1i1t336vPxVcn9IpxaMhsarSaHcpIxbDRoVgUi91mNg2+jhLN/kWiPzRPNHkjxMDKtIos1wbRFzkhSqI"  # pragma: allowlist secret
                "+ov5ql2jQ7lRkr015hM61RXQ7tTmRcrQdQKu2TrTziih1h4jy4DGRv3xPlLmO4kjfCHtEajCuInP5j+9ZvSC6xq"  # pragma: allowlist secret
                "JE59OKihx1h6jZPyTk6wOiyOf0COE/Iyo/H4i62DNRnUzOijRta05Ilx9E8dsPkbepErkvl4TBtUAULoWJgpvJODK0"  # pragma: allowlist secret
                "v9LzkaidiREdpxNE790XUXUeINokw78VNrutxWRR7A6L0Zru/fDKaYnxaVmE/DNyavD2ewFSIuyRU9yn87JOktTd99ie8ReGnElETwEAAA==",  # pragma: allowlist secret
                "to": None,
                "num": 40,
                "application": "splunk_soar",
                "application_version": dataminrpulse_config.APPLICATION_VERSION,
                "integration_version": dataminrpulse_config.INTEGRATION_VERSION,
            },
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_to_pass(self, mock_get):
        """Test the valid case for the get alerts action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["parameters"] = [
            {
                "list_id": None,
                "query": "1247060284",
                "from": None,
                "to": "H4sIAAAAAAAAAFXQ3StDcQDG8fOsX5IkSZIkSZLQWpIkIU6SJEmSZLWl1do05x+glYlWxCwkSWueiZCXyKJ2RdmSK++"  # pragma: allowlist secret
                "NpIXOrhw1i1t336vPxVcn9IpxaMhsarSaHcpIxbDRoVgUi91mNg2+jhLN/kWiPzRPNHkjxMDKtIos1wbRFzkhSqI"  # pragma: allowlist secret
                "+ov5ql2jQ7lRkr015hM61RXQ7tTmRcrQdQKu2TrTziih1h4jy4DGRv3xPlLmO4kjfCHtEajCuInP5j+9ZvSC6xq"  # pragma: allowlist secret
                "JE59OKihx1h6jZPyTk6wOiyOf0COE/Iyo/H4i62DNRnUzOijRta05Ilx9E8dsPkbepErkvl4TBtUAULoWJgpvJODK0"  # pragma: allowlist secret
                "v9LzkaidiREdpxNE790XUXUeINokw78VNrutxWRR7A6L0Zru/fDKaYnxaVmE/DNyavD2ewFSIuyRU9yn87JOktTd99ie8ReGnElETwEAAA==",  # pragma: allowlist secret
                "num": 1,
            }
        ]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"data": {"alerts": ["dummy_data"], "from": "dummy_from", "to": "dummy_to"}}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Api version used: v3, Total alerts: 1")

        mock_get.assert_called_with(
            f"https://gateway.dataminr.com{consts.DATAMINRPULSE_GET_ALERTS}",
            headers=dataminrpulse_config.ACTION_HEADER,
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            params={
                "lists": None,
                "query": "1247060284",
                "from": None,
                "to": "H4sIAAAAAAAAAFXQ3StDcQDG8fOsX5IkSZIkSZLQWpIkIU6SJEmSZLWl1do05x+glYlWxCwkSWueiZCXyKJ2RdmSK++"  # pragma: allowlist secret
                "NpIXOrhw1i1t336vPxVcn9IpxaMhsarSaHcpIxbDRoVgUi91mNg2+jhLN/kWiPzRPNHkjxMDKtIos1wbRFzkhSqI"  # pragma: allowlist secret
                "+ov5ql2jQ7lRkr015hM61RXQ7tTmRcrQdQKu2TrTziih1h4jy4DGRv3xPlLmO4kjfCHtEajCuInP5j+9ZvSC6xq"  # pragma: allowlist secret
                "JE59OKihx1h6jZPyTk6wOiyOf0COE/Iyo/H4i62DNRnUzOijRta05Ilx9E8dsPkbepErkvl4TBtUAULoWJgpvJODK0"  # pragma: allowlist secret
                "v9LzkaidiREdpxNE790XUXUeINokw78VNrutxWRR7A6L0Zru/fDKaYnxaVmE/DNyavD2ewFSIuyRU9yn87JOktTd99ie8ReGnElETwEAAA==",  # pragma: allowlist secret
                "num": 40,
                "application": "splunk_soar",
                "application_version": dataminrpulse_config.APPLICATION_VERSION,
                "integration_version": dataminrpulse_config.INTEGRATION_VERSION,
            },
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_invalid_list_pass(self, mock_get):
        """Test the valid case for the get alerts action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{"list_id": "123", "query": None, "from": None, "to": None, "num": 1}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {
            "data": {
                "alerts": [],
                "from": "dummy_from",
                "to": "dummy_to",
            }
        }

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Api version used: v3, Total alerts: 0")

        mock_get.assert_called_with(
            f"https://gateway.dataminr.com{consts.DATAMINRPULSE_GET_ALERTS}",
            headers=dataminrpulse_config.ACTION_HEADER,
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            params={
                "lists": "123",
                "query": None,
                "from": None,
                "to": None,
                "num": 40,
                "application": "splunk_soar",
                "application_version": dataminrpulse_config.APPLICATION_VERSION,
                "integration_version": dataminrpulse_config.INTEGRATION_VERSION,
            },
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_invalid_num_fail(self, mock_get):
        """Test the invalid case for the get alerts action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{"list_id": "123", "query": None, "from": None, "to": None, "num": -1}]

        mock_get.return_value.status_code = 400
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = "Please provide a valid non-negative integer value in the 'Max Alerts' parameter"

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(
            ret_val["result_data"][0]["message"],
            "Error from server. Please provide a valid non-negative integer value in the 'Max Alerts' parameter",
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_blank_list_query_fail(self, mock_get):
        """Test the invalid case for the get alerts action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{"list_id": None, "query": None, "from": None, "to": None, "num": 1}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], "Please provide either 'list id' or 'query' action parameter")

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_to_from_both_fail(self, mock_get):
        """Test the invalid case for the get alerts action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["parameters"] = [
            {
                "list_id": "3557389",
                "query": None,
                "from": "H4sIAAAAAAAAAFXQ3StDcQDG8fOsX5IkSZIkSZLQWpIkIU6SJEmSZLWl1do05x+glYlWxCwkSWueiZCXyKJ2RdmSK++"  # pragma: allowlist secret
                "NpIXOrhw1i1t336vPxVcn9IpxaMhsarSaHcpIxbDRoVgUi91mNg2+jhLN/kWiPzRPNHkjxMDKtIos1wbRFzkhSqI"  # pragma: allowlist secret
                "+ov5ql2jQ7lRkr015hM61RXQ7tTmRcrQdQKu2TrTziih1h4jy4DGRv3xPlLmO4kjfCHtEajCuInP5j+9ZvSC6xq"  # pragma: allowlist secret
                "JE59OKihx1h6jZPyTk6wOiyOf0COE/Iyo/H4i62DNRnUzOijRta05Ilx9E8dsPkbepErkvl4TBtUAULoWJgpvJODK0"  # pragma: allowlist secret
                "v9LzkaidiREdpxNE790XUXUeINokw78VNrutxWRR7A6L0Zru/78945regtr/DNyavD2ewFSIuyRU9yn87JOktTd99ie8ReGnElETwEAAA==",  # pragma: allowlist secret
                "to": "H4-23AAAFXQ3StDcQDG8fOsX5IkSZIkSZLQWpIkIU6SJEmSZLWl1do05x+glYlWxCwkSWueiZCXyKJ2RdmSK++"  # pragma: allowlist secret
                "NpIXOrhw1i1t336vPxVcn9IpxaMhsarSaHcpIxbDRoVgUi91mNg2+jhLN/kWiPzRPNHkjxMDKtIos1wbRFzkhSqI"  # pragma: allowlist secret
                "+ov5ql2jQ7lRkr015hM61RXQ7tTmRcrQdQKu2TrTziih1h4jy4DGRv3xPlLmO4kjfCHtEajCuInP5j+9ZvSC6xq"  # pragma: allowlist secret
                "JE59OKihx1h6jZPyTk6wOiyOf0COE/Iyo/H4i62DNRnUzOijRta05Ilx9E8dsPkbepErkvl4TBtUAULoWJgpvJODK0"  # pragma: allowlist secret
                "v9LzkaidiREdpxNE790XUXUeINokw78VNrutxWRR7A6L0Zru/78945regtr/DNyavD2ewFSIuyRU9yn87JOktTd99ie8ReGnElETwEAAA==",  # pragma: allowlist secret
                "num": 1,
            }
        ]

        mock_get.return_value.status_code = 400
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = "Error message: Only one of 'from' and 'to' can be present"

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], "Error from server. Error message: Only one of 'from' and 'to' can be present")

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_invalid_from_fail(self, mock_get):
        """Test the invalid case for the get alerts action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{"list_id": "3557389", "query": None, "from": "abc", "to": None, "num": 1}]

        mock_get.return_value.status_code = 400
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = 'Error message: Unable to decode "from" cursor, invalid format'

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(
            ret_val["result_data"][0]["message"],
            'Error from server. Error message: Unable to decode "from" cursor, invalid format',
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_alerts_invalid_to_fail(self, mock_get):
        """Test the invalid case for the get alerts action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{"list_id": "3557389", "query": None, "from": None, "to": "abc", "num": 1}]

        mock_get.return_value.status_code = 400
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = 'Error message: Unable to decode "to" cursor, invalid format'

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], 'Error from server. Error message: Unable to decode "to" cursor, invalid format')
