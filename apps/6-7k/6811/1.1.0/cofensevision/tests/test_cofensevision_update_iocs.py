# File: test_cofensevision_update_iocs.py
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

import json
import unittest
from unittest.mock import call, patch

import requests
from freezegun import freeze_time

import cofensevision_consts as consts
from cofensevision_connector import CofenseVisionConnector
from tests import cofensevision_config


PARAM_LIST = [
    {
        "source": "Vision-UI",
        "threat_type": "URL",
        "threat_value": "https://testdomain.com",
        "source_id": "test_source_1",
        "created_at": "01 Mar 2022",
        "updated_at": "01 Feb 2022 04:45:33",
        "threat_level": "Malicious",
        "requested_expiration": "2023-04-17T14:05:44Z",
    }
]

EXPECTED_DATA = {
    "data": [
        {
            "type": "ioc",
            "attributes": {"threat_type": "URL", "threat_value": "https://testdomain.com"},
            "metadata": {
                "source": {
                    "id": "test_source_1",
                    "threat_level": "Malicious",
                    "created_at": "2022-03-01T00:00:00.000000Z",
                    "updated_at": "2022-02-01T04:45:33.000000Z",
                    "requested_expiration": "2023-04-17T14:05:44.000000Z",
                }
            },
        }
    ]
}

EXPECTED_HEADER = dict(cofensevision_config.ACTION_HEADER)
EXPECTED_HEADER.update({"X-Cofense-IOC-Source": "Vision-UI"})

PLACEHOLDER = "dummy_value"
SUCCESS_MSG = "Total iocs updated: 1"


class TestUpdateIocsAction(unittest.TestCase):
    """Class to test the Update IOCs action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "update iocs", "identifier": "update_iocs"})

        return super().setUp()

    @patch("cofensevision_utils.requests.put")
    def test_update_iocs_json_pass(self, mock_put):
        """Test the valid case for the update iocs action.

        Token is available in the state file.
        Patch the put() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        iocs_json = [
            {
                "threat_type": "Domain",
                "threat_value": "test1.com",
                "threat_level": "Malicious",
                "created_at": "01 Mar 2021",
                "source_id": "test_source_1",
                "updated_at": "01 Feb 2021 04:45:33",
                "requested_expiration": "2022-04-17T14:05:44Z",
            },
            {
                "threat_type": "Domain",
                "threat_value": "test2.com",
                "threat_level": "Malicious",
                "created_at": "01 Mar 2021",
                "source_id": "test_source_2",
                "updated_at": "01 Feb 2021 04:45:33",
                "requested_expiration": "2022-04-17T14:05:44Z",
            },
        ]
        self.test_json["parameters"] = [
            {
                "source": "Vision-UI",
                "iocs_json": json.dumps(iocs_json),
            }
        ]

        mock_put.return_value.status_code = 200
        mock_put.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_put.return_value.json.return_value = {"data": [{"dummy": "data1"}, {"dummy": "data2"}]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Total iocs updated: 2")

        expected_data = {
            "data": [
                {
                    "type": "ioc",
                    "attributes": {"threat_type": "Domain", "threat_value": "test1.com"},
                    "metadata": {
                        "source": {
                            "id": "test_source_1",
                            "threat_level": "Malicious",
                            "created_at": "2021-03-01T00:00:00.000000Z",
                            "updated_at": "2021-02-01T04:45:33.000000Z",
                            "requested_expiration": "2022-04-17T14:05:44.000000Z",
                        }
                    },
                },
                {
                    "type": "ioc",
                    "attributes": {"threat_type": "Domain", "threat_value": "test2.com"},
                    "metadata": {
                        "source": {
                            "id": "test_source_2",
                            "threat_level": "Malicious",
                            "created_at": "2021-03-01T00:00:00.000000Z",
                            "updated_at": "2021-02-01T04:45:33.000000Z",
                            "requested_expiration": "2022-04-17T14:05:44.000000Z",
                        }
                    },
                },
            ]
        }

        mock_put.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}",
            headers=EXPECTED_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            data=json.dumps(expected_data),
            verify=False,
        )

    @patch("cofensevision_utils.requests.put")
    def test_update_iocs_other_params_pass(self, mock_put):
        """Test the valid case for the update iocs action.

        Token is available in the state file.
        Patch the put() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = PARAM_LIST

        mock_put.return_value.status_code = 200
        mock_put.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_put.return_value.json.return_value = {"data": [{"dummy": "data"}]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], SUCCESS_MSG)

        mock_put.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}",
            headers=EXPECTED_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            data=json.dumps(EXPECTED_DATA),
            verify=False,
        )

    @patch("cofensevision_utils.requests.put")
    @patch("cofensevision_utils.requests.post")
    def test_update_iocs_expired_token_pass(self, mock_post, mock_put):
        """Test the valid case for the update iocs action.

        Token is available in the state file but it is expired.
        Patch the put() to return the invalid token first and then valid response.
        Patch the post() to return the valid responses.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = PARAM_LIST

        post_response = requests.Response()
        post_response._content = b'{"access_token": "<dummy_token>"}'
        post_response.status_code = 200
        post_response.headers = cofensevision_config.DEFAULT_HEADERS
        mock_post.return_value = post_response

        put_response_1 = requests.Response()
        put_response_1._content = b'{"error": "invalid_token", "error_description": "<dummy_token>"}'
        put_response_1.status_code = 401
        put_response_1.headers = cofensevision_config.DEFAULT_HEADERS

        put_response_2 = requests.Response()
        put_response_2._content = b'{"data": [{"dummy": "data"}]}'
        put_response_2.status_code = 200
        put_response_2.headers = cofensevision_config.DEFAULT_HEADERS

        mock_put.side_effect = [put_response_1, put_response_2]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], SUCCESS_MSG)

        expected_put_calls = [
            call(
                f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}",
                timeout=consts.VISION_REQUEST_TIMEOUT,
                verify=False,
                headers=EXPECTED_HEADER,
                data=json.dumps(EXPECTED_DATA),
            ),
            call(
                f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}",
                timeout=consts.VISION_REQUEST_TIMEOUT,
                verify=False,
                headers=EXPECTED_HEADER,
                data=json.dumps(EXPECTED_DATA),
            ),
        ]
        mock_put.assert_has_calls(expected_put_calls)

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_TOKEN}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            data=cofensevision_config.TOKEN_DATA,
            headers=cofensevision_config.TOKEN_HEADER,
        )

    @patch("cofensevision_utils.requests.put")
    @patch("cofensevision_utils.requests.post")
    def test_update_iocs_no_token_pass(self, mock_post, mock_put):
        """Test the valid case for the update iocs action.

        Token is not available in the state file.
        Patch the post() to return the valid response.
        Patch the put() to return the valid response.
        """
        cofensevision_config.set_state_file(client_id=True)

        self.test_json["parameters"] = PARAM_LIST

        post_response = requests.Response()
        post_response._content = b'{"access_token": "<dummy_token>"}'
        post_response.status_code = 200
        post_response.headers = cofensevision_config.DEFAULT_HEADERS
        mock_post.return_value = post_response

        put_response = requests.Response()
        put_response._content = b'{"data": [{"dummy": "data"}]}'
        put_response.status_code = 200
        put_response.headers = cofensevision_config.DEFAULT_HEADERS
        mock_put.return_value = put_response

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], SUCCESS_MSG)

        mock_put.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}",
            headers=EXPECTED_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            data=json.dumps(EXPECTED_DATA),
            verify=False,
        )

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_TOKEN}",
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
            data=cofensevision_config.TOKEN_DATA,
            headers=cofensevision_config.TOKEN_HEADER,
        )

    @freeze_time("2012-01-01")
    @patch("cofensevision_utils.requests.put")
    def test_update_iocs_default_update_time_pass(self, mock_put):
        """Test the valid case for the update iocs action.

        Patch the put() to return the valid response.
        """
        # Set the token in the state file.
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        iocs_json = [
            {
                "threat_type": "Domain",
                "threat_value": "test3.com",
                "threat_level": "Malicious",
                "created_at": "01 Mar 2023",
                "source_id": "test_source_3",
                "requested_expiration": "2023-04-17T14:05:44Z",
            }
        ]
        self.test_json["parameters"] = [
            {
                "source": "Vision-UI",
                "iocs_json": json.dumps(iocs_json),
            }
        ]

        mock_put.return_value.status_code = 200
        mock_put.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_put.return_value.json.return_value = {"data": [{"dummy": "data1"}, {"dummy": "data2"}]}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")
        self.assertEqual(ret_val["result_data"][0]["message"], "Total iocs updated: 2")

        expected_data = {
            "data": [
                {
                    "type": "ioc",
                    "attributes": {"threat_type": "Domain", "threat_value": "test3.com"},
                    "metadata": {
                        "source": {
                            "id": "test_source_3",
                            "threat_level": "Malicious",
                            "created_at": "2023-03-01T00:00:00.000000Z",
                            "updated_at": "2012-01-01T00:00:00.000000Z",
                            "requested_expiration": "2023-04-17T14:05:44.000000Z",
                        }
                    },
                }
            ]
        }

        mock_put.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}",
            headers=EXPECTED_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            data=json.dumps(expected_data),
            verify=False,
        )

    def test_update_iocs_invalid_json_fail(self):
        """Test the update iocs action with invalid 'iocs_json' parameter."""
        self.test_json["parameters"] = [{"source": "Vision-UI", "iocs_json": '[{"Invalid": "json", format}]'}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], "Error occurred while parsing the provided JSON")

    def test_update_iocs_missing_params_fail(self):
        """Test the update iocs action with missing parameters."""
        self.test_json["parameters"] = [{"source": "Vision-UI", "iocs_json": '[{"Valid": "json", "Insufficient": "Keys"}]'}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Please provide all the required parameters:", ret_val["result_data"][0]["message"])

    def test_update_iocs_invalid_created_at_fail(self):
        """Test the update iocs action with invalid 'created at' parameter."""
        self.test_json["parameters"] = [
            {
                "source": PLACEHOLDER,
                "threat_type": PLACEHOLDER,
                "threat_value": PLACEHOLDER,
                "source_id": PLACEHOLDER,
                "created_at": "01 Month 2022",
                "updated_at": "01 Jan 2022 04:45:33",
                "threat_level": PLACEHOLDER,
                "requested_expiration": "2023-05-17T14:05:44Z",
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("created at"))

    def test_update_iocs_invalid_updated_at_fail(self):
        """Test the update iocs action with invalid 'updated at' parameter."""
        self.test_json["parameters"] = [
            {
                "source": PLACEHOLDER,
                "threat_type": PLACEHOLDER,
                "threat_value": PLACEHOLDER,
                "source_id": PLACEHOLDER,
                "created_at": "01 Jan 2022",
                "updated_at": "01 Jan 2022 25:45:33",
                "threat_level": PLACEHOLDER,
                "requested_expiration": "2023-04-18T14:05:44Z",
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("updated at"))

    def test_update_iocs_invalid_requested_expiration_fail(self):
        """Test the update iocs action with invalid 'requested expiration' parameter."""
        self.test_json["parameters"] = [
            {
                "source": PLACEHOLDER,
                "threat_type": PLACEHOLDER,
                "threat_value": PLACEHOLDER,
                "source_id": PLACEHOLDER,
                "created_at": "01 Jan 2022",
                "updated_at": "01 Jan 2022 10:45:33",
                "threat_level": PLACEHOLDER,
                "requested_expiration": "2023-14-17T14:05:44Z",
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("requested expiration"))

    @patch("cofensevision_utils.requests.put")
    def test_update_iocs_server_fail(self, mock_put):
        """Test the invalid case for the update iocs action.

        Patch the put() to return the error response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = PARAM_LIST

        mock_put.return_value.status_code = 500
        mock_put.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_put.return_value.json.return_value = {"error": "Internal server error"}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertIn("Error from server. Status code: 500", ret_val["result_data"][0]["message"])

        mock_put.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}",
            headers=EXPECTED_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            data=json.dumps(EXPECTED_DATA),
            verify=False,
        )

    @patch("cofensevision_utils.requests.put")
    def test_update_iocs_empty_response_fail(self, mock_put):
        """Test the invalid case for the update iocs action.

        Patch the put() to return the empty response.
        """
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = PARAM_LIST

        mock_put.return_value.status_code = 200
        mock_put.return_value.headers = {}
        mock_put.return_value.text = ""

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], "The server returned an unexpected empty response")

        mock_put.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_IOC}",
            headers=EXPECTED_HEADER,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            data=json.dumps(EXPECTED_DATA),
            verify=False,
        )

    def test_update_iocs_invalid_threat_type_fail(self):
        """Test the update iocs action with invalid 'threat_type' parameter."""
        params = dict(PARAM_LIST[0])
        params["threat_type"] = "Invalid"
        self.test_json["parameters"] = [params]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("threat type"))
