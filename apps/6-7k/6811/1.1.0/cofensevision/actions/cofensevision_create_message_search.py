# File: cofensevision_create_message_search.py
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

import phantom.app as phantom
import phantom.utils as utils

import cofensevision_consts as consts
from actions import BaseAction


class CreateMessageSearchAction(BaseAction):
    """Class to handle create message search action."""

    def process_subjects_parameter(self, body):
        """Process values of subjects action parameter.

        :param body: data to be passed in request body
        :return: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        if consts.VISION_PARAM_SUBJECTS in self._param:
            subjects = self._connector.util.split_value_list(self._param[consts.VISION_PARAM_SUBJECTS])
            if len(subjects) > consts.VISION_MAX_ALLOWED_VALUES:
                return self._action_result.set_status(
                    phantom.APP_ERROR, consts.VISION_ERROR_EXTRA_VALUES.format(consts.VISION_PARAM_SUBJECTS, consts.VISION_MAX_ALLOWED_VALUES)
                )

            body["subjects"] = subjects
        return phantom.APP_SUCCESS

    def process_senders_parameter(self, body):
        """Process values of senders action parameter.

        :param body: data to be passed in request body
        :return: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        if consts.VISION_PARAM_SENDERS in self._param:
            senders = self._connector.util.split_value_list(self._param[consts.VISION_PARAM_SENDERS])
            if len(senders) > consts.VISION_MAX_ALLOWED_VALUES:
                return self._action_result.set_status(
                    phantom.APP_ERROR, consts.VISION_ERROR_EXTRA_VALUES.format(consts.VISION_PARAM_SENDERS, consts.VISION_MAX_ALLOWED_VALUES)
                )

            body["senders"] = senders
        return phantom.APP_SUCCESS

    def process_attachment_names_parameter(self, body):
        """Process values of attachment_names action parameter.

        :param body: data to be passed in request body
        :return: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        if consts.VISION_PARAM_ATTACHMENT_NAMES in self._param:
            attachment_names = self._connector.util.split_value_list(self._param[consts.VISION_PARAM_ATTACHMENT_NAMES])
            if len(attachment_names) > consts.VISION_MAX_ALLOWED_VALUES:
                return self._action_result.set_status(
                    phantom.APP_ERROR,
                    consts.VISION_ERROR_EXTRA_VALUES.format(consts.VISION_PARAM_ATTACHMENT_NAMES, consts.VISION_MAX_ALLOWED_VALUES),
                )

            body["attachmentNames"] = attachment_names
        return phantom.APP_SUCCESS

    def create_hash_dict(self, hash_list, hash_dict):
        """Create a dictionary of attachmentHashes.

        :param hash_list: a list containing hashType and hashValue
        :param hash_dict: dictionary to store attachmentHash
        :return: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        hash_type = hash_list[0].upper()
        hash_dict["hashType"] = hash_type
        if hash_type == consts.VISION_HASH_TYPE_MD5:
            if not utils.is_md5(hash_list[1]):
                return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_MD5_VALUE)
            hash_dict["hashString"] = hash_list[1]
        elif hash_type == consts.VISION_HASH_TYPE_SHA256:
            if not utils.is_sha256(hash_list[1]):
                return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_SHA256_VALUE)
            hash_dict["hashString"] = hash_list[1]
        else:
            return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_HASH_TYPE_VALUE)

        return phantom.APP_SUCCESS

    def process_attachment_hashes_parameter(self, body):
        """Process values of attachment_hashes action parameter.

        :param body: data to be passed in request body
        :return: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        if consts.VISION_PARAM_ATTACHMENT_HASHES in self._param:
            match_criteria = self._param.get(consts.VISION_PARAM_ATTACHMENT_HASH_MATCH_CRITERIA, "ANY")
            if match_criteria not in consts.VISION_SUPPORTED_CRITERIA:
                error_message = consts.VISION_ERROR_VALUE_LIST.format(
                    consts.VISION_PARAM_ATTACHMENT_HASH_MATCH_CRITERIA, ", ".join(consts.VISION_SUPPORTED_CRITERIA)
                )
                return self._action_result.set_status(phantom.APP_ERROR, error_message)

            attachment_hashes = self._connector.util.split_value_list(self._param[consts.VISION_PARAM_ATTACHMENT_HASHES])
            if len(attachment_hashes) > consts.VISION_MAX_ALLOWED_VALUES:
                return self._action_result.set_status(
                    phantom.APP_ERROR,
                    consts.VISION_ERROR_EXTRA_VALUES.format(consts.VISION_PARAM_ATTACHMENT_HASHES, consts.VISION_MAX_ALLOWED_VALUES),
                )

            list_hashes = list()
            for hash in attachment_hashes:
                hash_dict = {}
                hash_list = list(filter(None, [hashes.strip() for hashes in hash.split(":")]))
                if len(hash_list) != 2:
                    return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_HASH_VALUE)
                ret_val = self.create_hash_dict(hash_list, hash_dict)
                if phantom.is_fail(ret_val):
                    return self._action_result.get_status()
                list_hashes.append(hash_dict)

            body["attachmentHashCriteria"] = {"type": match_criteria, "attachmentHashes": list_hashes}

        return phantom.APP_SUCCESS

    def process_attachment_mime_types_parameter(self, body):
        """Process values of attachment_mime_types action parameter

        :param body: data to be passed in request body
        :return: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        if consts.VISION_PARAM_ATTACHMENT_MIME_TYPES in self._param:
            attachment_mime_types = self._connector.util.split_value_list(self._param[consts.VISION_PARAM_ATTACHMENT_MIME_TYPES])
            if len(attachment_mime_types) > consts.VISION_MAX_ALLOWED_VALUES:
                return self._action_result.set_status(
                    phantom.APP_ERROR,
                    consts.VISION_ERROR_EXTRA_VALUES.format(consts.VISION_PARAM_ATTACHMENT_MIME_TYPES, consts.VISION_MAX_ALLOWED_VALUES),
                )

            body["attachmentMimeTypes"] = attachment_mime_types
        return phantom.APP_SUCCESS

    def process_attachment_exclude_mime_types_parameter(self, body):
        """Process values of attachment_exclude_mime_types action parameter

        :param body: data to be passed in request body
        :return: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        if consts.VISION_PARAM_ATTACHMENT_EXCLUDE_MIME_TYPES in self._param:
            attachment_exclude_mime_types = self._connector.util.split_value_list(self._param[consts.VISION_PARAM_ATTACHMENT_EXCLUDE_MIME_TYPES])
            if len(attachment_exclude_mime_types) > consts.VISION_MAX_ALLOWED_VALUES:
                return self._action_result.set_status(
                    phantom.APP_ERROR,
                    consts.VISION_ERROR_EXTRA_VALUES.format(consts.VISION_PARAM_ATTACHMENT_EXCLUDE_MIME_TYPES, consts.VISION_MAX_ALLOWED_VALUES),
                )

            body["attachmentExcludeMimeTypes"] = attachment_exclude_mime_types
        return phantom.APP_SUCCESS

    def process_domains_parameter(self, body):
        """Process values of domains action parameter

        :param body: data to be passed in request body
        :return: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        if consts.VISION_PARAM_DOMAINS in self._param:
            match_criteria = self._param.get(consts.VISION_PARAM_DOMAIN_MATCH_CRITERIA, "ANY")
            if match_criteria not in consts.VISION_SUPPORTED_CRITERIA:
                return self._action_result.set_status(
                    phantom.APP_ERROR,
                    consts.VISION_ERROR_VALUE_LIST.format(
                        consts.VISION_PARAM_DOMAIN_MATCH_CRITERIA, ", ".join(consts.VISION_SUPPORTED_CRITERIA)
                    ),
                )
            body["domainCriteria"] = {
                "type": match_criteria,
                "domains": [],
            }

            if consts.VISION_PARAM_DOMAINS in self._param:
                domains = self._connector.util.split_value_list(self._param[consts.VISION_PARAM_DOMAINS])
                if len(domains) > consts.VISION_MAX_ALLOWED_VALUES:
                    return self._action_result.set_status(
                        phantom.APP_ERROR, consts.VISION_ERROR_EXTRA_VALUES.format(consts.VISION_PARAM_DOMAINS, consts.VISION_MAX_ALLOWED_VALUES)
                    )

                body["domainCriteria"]["domains"] = domains

        return phantom.APP_SUCCESS

    def process_internet_message_id_parameter(self, body):
        """Process values of domains and internet_message_id action parameter

        :param body: data to be passed in request body
        """
        if consts.VISION_PARAM_INTERNET_MESSAGE_ID in self._param:
            body["internetMessageId"] = self._param[consts.VISION_PARAM_INTERNET_MESSAGE_ID]

    def process_partial_ingest_parameter(self, body):
        """Process values of partial_ingest action parameter

        :param body: data to be passed in request body
        """
        if consts.VISION_PARAM_PARTIAL_INGEST in self._param:
            body["partialIngest"] = self._param.get(consts.VISION_PARAM_PARTIAL_INGEST, False)

    def process_recipient_parameter(self, body):
        """Process values of recipient action parameter

        :param body: data to be passed in request body
        """
        if consts.VISION_PARAM_RECIPIENT in self._param:
            body["recipient"] = self._param[consts.VISION_PARAM_RECIPIENT]

    def process_url_parameter(self, body):
        """Process values of url action parameter

        :param body: data to be passed in request body
        """
        if consts.VISION_PARAM_URL in self._param:
            body["url"] = self._param[consts.VISION_PARAM_URL]

    def process_received_after_date_parameter(self, body):
        """Process values of received_after_date action parameter

        :param body: data to be passed in request body
        :return: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        if consts.VISION_PARAM_RECEIVED_AFTER_DATE in self._param:
            status, formatted_date = self._connector.util.parse_date_string(self._param.get(consts.VISION_PARAM_RECEIVED_AFTER_DATE))
            if phantom.is_fail(status):
                return self._action_result.set_status(
                    phantom.APP_ERROR, consts.VISION_ERROR_INVALID_DATE_FORMAT.format(consts.VISION_PARAM_RECEIVED_AFTER_DATE)
                )
            body["receivedAfterDate"] = formatted_date
        return phantom.APP_SUCCESS

    def process_received_before_date_parameter(self, body):
        """Process values of received_before_date action parameter

        :param body: data to be passed in request body
        :return: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        if consts.VISION_PARAM_RECEIVED_BEFORE_DATE in self._param:
            status, formatted_date = self._connector.util.parse_date_string(self._param.get(consts.VISION_PARAM_RECEIVED_BEFORE_DATE))
            if phantom.is_fail(status):
                return self._action_result.set_status(
                    phantom.APP_ERROR, consts.VISION_ERROR_INVALID_DATE_FORMAT.format(consts.VISION_PARAM_RECEIVED_BEFORE_DATE)
                )
            body["receivedBeforeDate"] = formatted_date
        return phantom.APP_SUCCESS

    def process_headers_parameter(self, body):
        """Process values of headers action parameter

        :param body: data to be passed in request body
        :return: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        if consts.VISION_PARAM_HEADERS in self._param:
            headers = list()
            header_list = self._connector.util.split_value_list(self._param[consts.VISION_PARAM_HEADERS])
            if len(header_list) > consts.VISION_MAX_ALLOWED_VALUES:
                return self._action_result.set_status(
                    phantom.APP_ERROR, consts.VISION_ERROR_EXTRA_VALUES.format(consts.VISION_PARAM_HEADERS, consts.VISION_MAX_ALLOWED_VALUES)
                )

            for header in header_list:
                header_key_values = list(filter(None, [header_key_value.strip() for header_key_value in header.split(":")]))
                if len(header_key_values) < 2:
                    return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_HEADER)
                header_dict = {
                    "key": header_key_values[0],
                    "values": header_key_values[1:],
                }
                headers.append(header_dict)

            body["headers"] = headers
        return phantom.APP_SUCCESS

    def execute(self):
        """Execute create message search action."""
        body = {}

        ret_val = self.process_subjects_parameter(body)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()
        ret_val = self.process_senders_parameter(body)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()
        ret_val = self.process_attachment_names_parameter(body)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()
        ret_val = self.process_attachment_hashes_parameter(body)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()
        ret_val = self.process_attachment_mime_types_parameter(body)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()
        ret_val = self.process_attachment_exclude_mime_types_parameter(body)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()
        ret_val = self.process_domains_parameter(body)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()
        self.process_internet_message_id_parameter(body)
        self.process_partial_ingest_parameter(body)
        self.process_recipient_parameter(body)
        self.process_url_parameter(body)
        ret_val = self.process_received_after_date_parameter(body)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()
        ret_val = self.process_received_before_date_parameter(body)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()
        ret_val = self.process_headers_parameter(body)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        # Call Search API to create a search with the provided parameters
        ret_val, response = self._connector.util.make_rest_call_helper(
            consts.VISION_ENDPOINT_MESSAGE_SEARCH, self._action_result, method="post", headers={}, json=body
        )

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        self._action_result.add_data(response)
        self._action_result.update_summary({"search_id": response["id"]})

        return self._action_result.set_status(phantom.APP_SUCCESS)
