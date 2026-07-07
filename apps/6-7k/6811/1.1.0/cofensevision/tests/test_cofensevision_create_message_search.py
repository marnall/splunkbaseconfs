# File: test_cofensevision_create_message_search.py
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
from unittest.mock import patch

from parameterized import parameterized

import cofensevision_consts as consts
from cofensevision_connector import CofenseVisionConnector
from tests import cofensevision_config


HTML_CONTENT_TYPE = "text/html"
PNG_CONTENT_TYPE = "images/png"
ATTACHMENT_NAME = "abc.png"
DOMAIN = "abc.com"
MESSAGE_ID = "<1C626FCE-6749-4DE9-884C-C025173F80BB@phishme.com>"
RECIPIENT = "xyz@gmail.com"
SUBJECT = "This is test subject"
URL = "https://google.com"


class TestCreateMessageSearchAction(unittest.TestCase):
    """Class to test the create message search action."""

    def setUp(self):
        """Set up method for the tests."""
        self.connector = CofenseVisionConnector()
        self.test_json = dict(cofensevision_config.TEST_JSON)
        self.test_json.update({"action": "create message search", "identifier": "create_message_search"})

        return super().setUp()

    @patch("cofensevision_utils.requests.post")
    def test_create_message_search_pass(self, mock_post):
        """Test the valid case for the create message search action."""
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [
            {
                "attachment_exclude_mime_types": HTML_CONTENT_TYPE,
                "attachment_hash_match_criteria": "ANY",
                "attachment_hashes": "md5:938c2cc0dcc05f2b68c4287040cfcf71, sha256:8ad4b470b20a7d3876c403695a2f9be0d45b91301c9ea2b23cea6859e854796a",
                "attachment_mime_types": PNG_CONTENT_TYPE,
                "attachment_names": ATTACHMENT_NAME,
                "domain_match_criteria": "ANY",
                "domains": DOMAIN,
                "headers": "X-MS-Exchange-Organization-AuthSource:BN8NAM12FT053.eop-nam12.prod.protection.outlook.com",
                "internet_message_id": MESSAGE_ID,
                "partial_ingest": False,
                "received_after_date": "2022-09-29T17:17:19.000",
                "received_before_date": "2022-10-31T17:17:19.000",
                "recipient": RECIPIENT,
                "senders": "mail*.com, def*.com, cof*.com",
                "subjects": SUBJECT,
                "url": URL,
            }
        ]

        expected_req_data = {
            "subjects": [SUBJECT],
            "senders": ["mail*.com", "def*.com", "cof*.com"],
            "attachmentNames": [ATTACHMENT_NAME],
            "attachmentHashCriteria": {
                "type": "ANY",
                "attachmentHashes": [
                    {
                        "hashType": "MD5",
                        "hashString": "938c2cc0dcc05f2b68c4287040cfcf71",  # pragma: allowlist secret
                    },
                    {
                        "hashType": "SHA256",
                        "hashString": "8ad4b470b20a7d3876c403695a2f9be0d45b91301c9ea2b23cea6859e854796a",  # pragma: allowlist secret
                    },
                ],
            },
            "attachmentMimeTypes": [PNG_CONTENT_TYPE],
            "attachmentExcludeMimeTypes": [HTML_CONTENT_TYPE],
            "domainCriteria": {"type": "ANY", "domains": [DOMAIN]},
            "internetMessageId": MESSAGE_ID,
            "partialIngest": False,
            "recipient": RECIPIENT,
            "url": URL,
            "receivedAfterDate": "2022-09-29T17:17:19.000000Z",
            "receivedBeforeDate": "2022-10-31T17:17:19.000000Z",
            "headers": [{"key": "X-MS-Exchange-Organization-AuthSource", "values": ["BN8NAM12FT053.eop-nam12.prod.protection.outlook.com"]}],
        }

        mocked_resp_data = {"id": 4951}

        mock_post.return_value.status_code = 201
        mock_post.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = mocked_resp_data

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 1)
        self.assertEqual(ret_val["status"], "success")

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE_SEARCH}",
            headers=cofensevision_config.ACTION_HEADER,
            json=expected_req_data,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )

    @patch("cofensevision_utils.requests.post")
    def test_create_message_search_fail(self, mock_post):
        """Test the invalid case for the create message search action."""
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [
            {
                "attachment_exclude_mime_types": HTML_CONTENT_TYPE,
                "attachment_hash_match_criteria": "ANY",
                "attachment_hashes": "md5:938c2cc0dcc05f2b68c4287040cfcf71, sha256:8ad4b470b20a7d3876c403695a2f9be0d45b91301c9ea2b23cea6859e854796a",
                "attachment_mime_types": PNG_CONTENT_TYPE,
                "attachment_names": ATTACHMENT_NAME,
                "domain_match_criteria": "ANY",
                "domains": DOMAIN,
                "headers": "X-MS-Exchange-Organization-AuthSource:BN8NAM12FT053.eop-nam12.prod.protection.outlook.com",
                "internet_message_id": MESSAGE_ID,
                "partial_ingest": False,
                "received_after_date": "2022-09-29T17:17:19.000",
                "received_before_date": "2022-10-31T17:17:19.000",
                "recipient": RECIPIENT,
                "senders": "mail*.com, def*.com, cof*.com",
                "subjects": SUBJECT,
                "url": URL,
            }
        ]

        expected_req_data = {
            "subjects": [SUBJECT],
            "senders": ["mail*.com", "def*.com", "cof*.com"],
            "attachmentNames": [ATTACHMENT_NAME],
            "attachmentHashCriteria": {
                "type": "ANY",
                "attachmentHashes": [
                    {
                        "hashType": "MD5",
                        "hashString": "938c2cc0dcc05f2b68c4287040cfcf71",  # pragma: allowlist secret
                    },
                    {
                        "hashType": "SHA256",
                        "hashString": "8ad4b470b20a7d3876c403695a2f9be0d45b91301c9ea2b23cea6859e854796a",  # pragma: allowlist secret
                    },
                ],
            },
            "attachmentMimeTypes": [PNG_CONTENT_TYPE],
            "attachmentExcludeMimeTypes": [HTML_CONTENT_TYPE],
            "domainCriteria": {"type": "ANY", "domains": [DOMAIN]},
            "internetMessageId": MESSAGE_ID,
            "partialIngest": False,
            "recipient": RECIPIENT,
            "url": URL,
            "receivedAfterDate": "2022-09-29T17:17:19.000000Z",
            "receivedBeforeDate": "2022-10-31T17:17:19.000000Z",
            "headers": [{"key": "X-MS-Exchange-Organization-AuthSource", "values": ["BN8NAM12FT053.eop-nam12.prod.protection.outlook.com"]}],
        }

        mock_post.return_value.status_code = 400
        mock_post.return_value.headers = cofensevision_config.DEFAULT_HEADERS
        mock_post.return_value.json.return_value = {}

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")

        mock_post.assert_called_with(
            f"{self.test_json['config']['base_url']}{consts.VISION_ENDPOINT_MESSAGE_SEARCH}",
            headers=cofensevision_config.ACTION_HEADER,
            json=expected_req_data,
            timeout=consts.VISION_REQUEST_TIMEOUT,
            verify=False,
        )

    @parameterized.expand(
        [
            (consts.VISION_PARAM_SENDERS),
            (consts.VISION_PARAM_SUBJECTS),
            (consts.VISION_PARAM_ATTACHMENT_NAMES),
            (consts.VISION_PARAM_ATTACHMENT_HASHES),
            (consts.VISION_PARAM_ATTACHMENT_MIME_TYPES),
            (consts.VISION_PARAM_ATTACHMENT_EXCLUDE_MIME_TYPES),
            (consts.VISION_PARAM_DOMAINS),
            (consts.VISION_PARAM_HEADERS),
        ]
    )
    def test_paramvalues_greater_than_max_allowed_fail(self, param_name):
        """Tests the action failure when parameters have more than 3 elements"""
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        invalid_param_dict = {
            consts.VISION_PARAM_SENDERS: "mail*.com, def*.com, cof*.com, gty.com",
            consts.VISION_PARAM_SUBJECTS: "sub1, sub2, sub3, sub4",
            consts.VISION_PARAM_ATTACHMENT_NAMES: "abc.png, xyz.png, test.txt, abcd.txt",
            consts.VISION_PARAM_ATTACHMENT_HASHES: "md5:938c2cc0dcc05f2b68c4287040cfcf71, md5:938c2cc0dcc05f2b68c4287040cfcf81,"
            "md5:938c2cc0dcc05f2b68c4287040cfcf72, md5:938c2cc0dcc05f2b68c4287040cfcf73",
            consts.VISION_PARAM_ATTACHMENT_MIME_TYPES: "text/html, image/png, application/json, video.mp4",
            consts.VISION_PARAM_ATTACHMENT_EXCLUDE_MIME_TYPES: "text/html, image/png, application/json, video.mp4",
            consts.VISION_PARAM_DOMAINS: "google, godaddy, aws, testdomain",
            consts.VISION_PARAM_HEADERS: "X-MS-Exchange-Organization-AuthSource:BN8NAM12FT053.eop-nam12.prod.protection.outlook.com,"
            "User-Agent: Mozilla/5.0, Accept: text/html, Accept-Language: en-US, Accept-Encoding: gzip",
        }

        self.test_json["parameters"] = [
            {
                param_name: invalid_param_dict[param_name],
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(
            ret_val["result_data"][0]["message"], consts.VISION_ERROR_EXTRA_VALUES.format(param_name, consts.VISION_MAX_ALLOWED_VALUES)
        )
        self.fail_assertions(ret_val)

    @parameterized.expand([consts.VISION_HASH_TYPE_MD5, consts.VISION_HASH_TYPE_SHA256, "invalid_hash_type", "invalid_attachment_hashes"])
    def test_invalid_hash_fail(self, test_name):
        """Tests the action failure when invalid hashType or hashValue is provided"""
        cofensevision_config.set_state_file(client_id=True, access_token=True)
        invalid_param_dict = {
            consts.VISION_HASH_TYPE_MD5: ["md5:b719518f3a8d55ceebe7c95f8d1c", consts.VISION_ERROR_INVALID_MD5_VALUE],
            consts.VISION_HASH_TYPE_SHA256: [
                "sha256:8ad4b470b20a7d3876c403695a2f9be0d45b91301c9ea2b23cea6859796a",
                consts.VISION_ERROR_INVALID_SHA256_VALUE,
            ],
            "invalid_hash_type": ["xyz:b719518f3a8d55ceebe7c95f8d1c6754", consts.VISION_ERROR_INVALID_HASH_TYPE_VALUE],
            "invalid_attachment_hashes": ["md5: ", consts.VISION_ERROR_INVALID_HASH_VALUE],
        }

        self.test_json["parameters"] = [
            {
                consts.VISION_PARAM_ATTACHMENT_HASHES: invalid_param_dict[test_name][0],
            }
        ]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_data"][0]["message"], invalid_param_dict[test_name][1])
        self.fail_assertions(ret_val)

    @parameterized.expand([consts.VISION_PARAM_DOMAIN_MATCH_CRITERIA, consts.VISION_PARAM_ATTACHMENT_HASH_MATCH_CRITERIA])
    def test_invalid_hash_or_domain_criteria_fail(self, param_name):
        """Tests the action failure when invalid hash criteria or domain criteria is provided"""
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        invalid_param_dict = {
            consts.VISION_PARAM_ATTACHMENT_HASH_MATCH_CRITERIA: {
                "attachment_hash_match_criteria": "NONE",
                "attachment_hashes": "md5:938c2cc0dcc05f2b68c4287040cfcf71",
            },
            consts.VISION_PARAM_DOMAIN_MATCH_CRITERIA: {"domain_match_criteria": "NONE", "domains": DOMAIN},
        }

        self.test_json["parameters"] = [invalid_param_dict[param_name]]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(
            ret_val["result_data"][0]["message"], consts.VISION_ERROR_VALUE_LIST.format(param_name, ", ".join(consts.VISION_SUPPORTED_CRITERIA))
        )
        self.fail_assertions(ret_val)

    @parameterized.expand([consts.VISION_PARAM_RECEIVED_BEFORE_DATE, consts.VISION_PARAM_RECEIVED_AFTER_DATE])
    def test_invalid_received_before_after_date_fail(self, param_name):
        """Test the action failure when invalid value is provided for received before and received after date parameters"""
        cofensevision_config.set_state_file(client_id=True, access_token=True)

        self.test_json["parameters"] = [{param_name: "31 Sep 2021 04:45:33"}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_DATE_FORMAT.format(param_name))
        self.fail_assertions(ret_val)

    def test_invalid_header_fail(self):
        """Test the action failure when invalid value is provided for header parameter"""
        self.test_json["parameters"] = [{"headers": "X-MS-Exchange-Organization-AuthSource: "}]

        ret_val = self.connector._handle_action(json.dumps(self.test_json), None)
        ret_val = json.loads(ret_val)
        self.assertEqual(ret_val["result_data"][0]["message"], consts.VISION_ERROR_INVALID_HEADER)
        self.fail_assertions(ret_val)

    def fail_assertions(self, ret_val):
        """Do assertions for failed cases"""
        self.assertEqual(ret_val["result_summary"]["total_objects"], 1)
        self.assertEqual(ret_val["result_summary"]["total_objects_successful"], 0)
        self.assertEqual(ret_val["status"], "failed")
