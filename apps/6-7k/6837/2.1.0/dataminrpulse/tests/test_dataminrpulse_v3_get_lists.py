# File: test_dataminrpulse_get_lists.py
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


class TestGetListsAction(unittest.TestCase):
    """Class to test the get lists action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = DataminrPulseConnector()
        self.test_json = dict(dataminrpulse_config.TEST_JSON)
        self.test_json.update({"action": "get lists", "identifier": "get_lists"})

        return super().setUp()

    @patch("dataminrpulse_utils.requests.get")
    def test_get_lists_pass(self, mock_get):
        """Test the valid case for the get lists action.

        Token is available in the state file.
        Patch the get() to return the valid response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{}]

        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {
            "watchlists": {"TOPIC": [{"data": "dummy_data"}], "CUSTOM": [{"data": "dummy_data"}], "COMPANY": [{"data": "dummy_data"}]}
        }

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)

        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_get.assert_called_with(
            f"https://gateway.dataminr.com{consts.DATAMINRPULSE_GET_LISTS}",
            headers=dataminrpulse_config.ACTION_HEADER,
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            params=None,
            verify=False,
        )

    @patch("dataminrpulse_utils.requests.get")
    def test_get_lists_invalid(self, mock_get):
        """Test the get lists action with unauthorized error.

        Token is available in the state file.
        Patch the get() to return the unauthorized response.
        """
        dataminrpulse_config.set_state_file(dmaToken=True)
        self.test_json["parameters"] = [{}]

        mock_get.return_value.status_code = 401
        mock_get.return_value.headers = dataminrpulse_config.DEFAULT_HEADERS
        mock_get.return_value.json.return_value = {"errors": [{"code": 102, "message": "Invalid client Id or client secret"}]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(
            ret_val["result_data"][0]["message"],
            "Error from server. Error code: 102. Error message: Invalid client Id or client secret",
        )

        mock_get.assert_called_with(
            f"https://gateway.dataminr.com{consts.DATAMINRPULSE_GET_LISTS}",
            headers={"Authorization": "Dmauth <dummy_token>"},
            timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
            params=None,
            verify=False,
        )
