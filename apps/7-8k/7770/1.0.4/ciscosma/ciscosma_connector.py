# File: ciscosma_connector.py
#
# Copyright (c) 2025 Splunk Inc.
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

# Cisco SMA Connector

import base64
import os
import re
import tempfile

import dateutil.parser as parser
import phantom.app as phantom
import requests
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault

from ciscosma_consts import (
    CISCOSMA_BLOCKLIST_ENDPOINT,
    CISCOSMA_DEFAULT_LIST_LIMIT,
    CISCOSMA_DEFAULT_LIST_OFFSET,
    CISCOSMA_DELETE_MESSAGES_ENDPOINT,
    CISCOSMA_DOWNLOAD_ATTACHMENT_ENDPOINT,
    CISCOSMA_GET_MESSAGE_DETAILS_ENDPOINT,
    CISCOSMA_GET_MESSAGE_TRACKING_DETAILS_ENDPOINT,
    CISCOSMA_GET_SUBSCRIPTION_ENDPOINT,
    CISCOSMA_RELEASE_MESSAGES_ENDPOINT,
    CISCOSMA_REPORTING_ENDPOINT,
    CISCOSMA_SAFELIST_ENDPOINT,
    CISCOSMA_SEARCH_MESSAGES_ENDPOINT,
    CISCOSMA_SEARCH_TRACKING_MESSAGES_ENDPOINT,
    CISCOSMA_VALID_FILTER_OPERATORS,
    CISCOSMA_VALID_FILTER_OPERATORS_REPORT,
    CISCOSMA_VALID_LIST_ORDER_BY,
    CISCOSMA_VALID_LIST_TYPES,
    CISCOSMA_VALID_LIST_VIEW_BY,
    CISCOSMA_VALID_ORDER_BY,
    CISCOSMA_VALID_ORDER_DIRECTIONS,
    CISCOSMA_VALID_QUARANTINE_ORDER_BY,
    CISCOSMA_VALID_SIZE_FILTERS,
    CISCOSMA_VALID_SUBJECT_FILTERS,
)


class CiscoSmaConnector(BaseConnector):
    def __init__(self):
        super().__init__()
        self._base_url = None
        self._username = None
        self._password = None
        self._verify = False

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, json=None, method="get"):
        """Function that makes the REST call to the app.

        :param endpoint: REST endpoint that needs to be appended to the service address
        :param action_result: object of ActionResult class
        :param headers: request headers
        :param params: request parameters
        :param data: request body
        :param json: JSON object
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """
        try:
            kwargs = {"json": json, "data": data, "headers": headers, "params": params, "verify": self._verify}

            response = requests.request(method, endpoint, **kwargs)

            # Check if response is JSON
            content_type = response.headers.get("Content-Type", "").lower()
            if "application/json" in content_type:
                try:
                    resp_json = response.json()
                except ValueError:
                    return action_result.set_status(phantom.APP_ERROR, f"Invalid JSON response from server: {response.text}"), None

                if response.status_code != 200:
                    return (
                        action_result.set_status(
                            phantom.APP_ERROR, f"API call failed. Status code: {response.status_code}. Response: {response.text}"
                        ),
                        None,
                    )

                return phantom.APP_SUCCESS, resp_json
            else:
                # Return raw response object for non-JSON responses (downloading attachment)
                if response.status_code != 200:
                    return (
                        action_result.set_status(
                            phantom.APP_ERROR, f"API call failed. Status code: {response.status_code}. Response: {response.text}"
                        ),
                        None,
                    )

                return phantom.APP_SUCCESS, response

        except requests.exceptions.RequestException as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error connecting to server: {e!s}"), None
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error making REST call: {e!s}"), None

    def _make_authenticated_request(self, action_result, endpoint, headers=None, params=None, data=None, json_data=None, method="get"):
        """Function that makes authenticated REST calls to the app with auth details.

        :param endpoint: REST endpoint that needs to be appended to the service address
        :param action_result: object of ActionResult class
        :param headers: request headers
        :param params: request parameters
        :param data: request body
        :param json_data: JSON object
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """
        url = f"{self._base_url}{endpoint}"
        if headers is None:
            headers = {"Content-Type": "application/json", "Accept": "application/json"}

        # Basic Auth header with encoded credentials
        basic_auth = base64.b64encode(f"{self._username}:{self._password}".encode()).decode()
        headers.update({"Authorization": f"Basic {basic_auth}"})

        ret_val, resp_json = self._make_rest_call(url, action_result, headers, params, data, json_data, method)

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, resp_json

    def _parse_and_format_date(self, date_str, zero_minutes=False, zero_seconds=False):
        """Helper to parse and format date for Cisco SMA API restrictions.

        Args:
            date_str: Input date string in any reasonable format
            zero_minutes: Set minutes to 00
            zero_seconds: Set seconds to 00
        """
        dt = parser.parse(date_str)

        if zero_minutes:
            dt = dt.replace(minute=0)
        if zero_seconds:
            dt = dt.replace(second=0, microsecond=0)

        return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def _sanitize_file_name(self, file_name):
        """Helper to sanitize file name.

        Args:
            file_name (str): The file name to sanitize

        Returns:
            str: Sanitized file name
        """
        return re.sub(r"""[,"']""", "", file_name)

    def _download_to_vault(self, action_result, response, default_filename=None):
        """Helper function to download content and add to vault.

        Args:
            action_result (ActionResult): The action result object
            response (Response): Response object from requests
            default_filename (str): Fallback filename if none found in headers

        Returns:
            tuple: (success (bool), vault_id (str), filename (str), error_message (str))
        """
        try:
            content_disposition = response.headers.get("Content-Disposition", "")
            filename = None

            if "filename=" in content_disposition:
                filename = content_disposition.split("filename=")[-1].strip('"')
            elif "filename*=" in content_disposition:
                filename = content_disposition.split("filename*=")[-1].split("''")[-1]

            filename = filename or default_filename or "unknown_file"
            filename = self._sanitize_file_name(filename)

            content = response.text.strip()

            # Decode base64 (SMA returns base64 encoded content)
            try:
                decoded_content = base64.b64decode(content)
                content = decoded_content
            except:
                pass

            fd, tmp_file_path = tempfile.mkstemp(dir=Vault.get_vault_tmp_dir())
            os.close(fd)

            with open(tmp_file_path, "wb") as f:
                f.write(content if isinstance(content, bytes) else content.encode())

            # Add to vault
            vault_ret = Vault.add_attachment(file_location=tmp_file_path, container_id=self.get_container_id(), file_name=filename)

            try:
                os.unlink(tmp_file_path)
            except:
                pass

            if not vault_ret.get("succeeded"):
                return False, None, None, f"Error adding file to vault: {vault_ret.get('message', 'Unknown error')}"

            vault_id = vault_ret.get("vault_id")
            if not vault_id:
                return False, None, None, "No vault ID returned from vault_add"

            return True, vault_id, filename, None

        except Exception as e:
            error_msg = f"Error downloading to vault: {e!s}"
            return False, None, None, error_msg

    def _list_entry_operation_setup(self, param, action):
        """Helper for safelist and blocklist entry operations.

        Args:
            param (dict): Parameters for action
            action (str): Action type ('add', 'edit', 'delete')

        Returns:
            tuple: (action_result, payload, endpoint)
        """
        action_result = self.add_action_result(ActionResult(dict(param)))

        list_type = param.get("list_type", "safelist").lower()
        if list_type not in CISCOSMA_VALID_LIST_TYPES:
            action_result.set_status(phantom.APP_ERROR, f"Invalid parameter 'list_type'. Must be one of: {CISCOSMA_VALID_LIST_TYPES}")
            return action_result, None, None

        view_by = param.get("view_by", "recipient")
        if view_by not in CISCOSMA_VALID_LIST_VIEW_BY:
            action_result.set_status(phantom.APP_ERROR, f"Invalid parameter 'view_by'. Must be one of: {CISCOSMA_VALID_LIST_VIEW_BY}")
            return action_result, None, None

        payload = {"quarantineType": "spam", "viewBy": view_by}

        # Add action only for add/edit operations
        if action != "delete":
            payload["action"] = action

        if view_by == "recipient":
            if action == "delete":
                recipient_list = param.get("recipient_list")
                if not recipient_list:
                    action_result.set_status(phantom.APP_ERROR, "Parameter 'recipient_list' is required when view_by is 'recipient'")
                    return action_result, None, None

                # Convert to list
                if isinstance(recipient_list, str):
                    recipient_list = [addr.strip() for addr in recipient_list.split(",")]
                payload["recipientList"] = recipient_list
            else:
                recipient_addresses = param.get("recipient_addresses")
                if not recipient_addresses:
                    action_result.set_status(phantom.APP_ERROR, "Parameter 'recipient_addresses' is required when view_by is 'recipient'")
                    return action_result, None, None

                sender_list = param.get("sender_list")
                if not sender_list:
                    action_result.set_status(phantom.APP_ERROR, "Parameter 'sender_list' is required when view_by is 'recipient'")
                    return action_result, None, None

                # Convert to list
                if isinstance(recipient_addresses, str):
                    recipient_addresses = [addr.strip() for addr in recipient_addresses.split(",")]
                if isinstance(sender_list, str):
                    sender_list = [sender.strip() for sender in sender_list.split(",")]

                payload["recipientAddresses"] = recipient_addresses
                payload["senderList"] = sender_list

        else:  # sender
            if action == "delete":
                sender_list = param.get("sender_list")
                if not sender_list:
                    action_result.set_status(phantom.APP_ERROR, "Parameter 'sender_list' is required when view_by is 'sender'")
                    return action_result, None, None

                # Convert to list
                if isinstance(sender_list, str):
                    sender_list = [sender.strip() for sender in sender_list.split(",")]
                payload["senderList"] = sender_list
            else:
                sender_addresses = param.get("sender_addresses")
                if not sender_addresses:
                    action_result.set_status(phantom.APP_ERROR, "Parameter 'sender_addresses' is required when view_by is 'sender'")
                    return action_result, None, None

                recipient_list = param.get("recipient_list")
                if not recipient_list:
                    action_result.set_status(phantom.APP_ERROR, "Parameter 'recipient_list' is required when view_by is 'sender'")
                    return action_result, None, None

                # Convert to list
                if isinstance(sender_addresses, str):
                    sender_addresses = [addr.strip() for addr in sender_addresses.split(",")]
                if isinstance(recipient_list, str):
                    recipient_list = [recip.strip() for recip in recipient_list.split(",")]

                payload["senderAddresses"] = sender_addresses
                payload["recipientList"] = recipient_list

        endpoint = CISCOSMA_SAFELIST_ENDPOINT if list_type == "safelist" else CISCOSMA_BLOCKLIST_ENDPOINT

        return action_result, payload, endpoint

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to Cisco SMA...")

        # Simple test for connection
        ret_val, response = self._make_authenticated_request(action_result, CISCOSMA_GET_SUBSCRIPTION_ENDPOINT)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_search_spam_quarantine_messages(self, param):
        self.save_progress("Searching for spam quarantine messages...")

        action_result = self.add_action_result(ActionResult(dict(param)))

        start_date = param.get("start_date")
        end_date = param.get("end_date")
        if not start_date or not end_date:
            return action_result.set_status(phantom.APP_ERROR, "Both 'start_date' and 'end_date' parameters are required")

        start_date = self._parse_and_format_date(start_date, zero_seconds=True)
        end_date = self._parse_and_format_date(end_date, zero_seconds=True)

        offset = param.get("offset", CISCOSMA_DEFAULT_LIST_OFFSET)
        limit = param.get("limit", CISCOSMA_DEFAULT_LIST_LIMIT)

        params = {"startDate": start_date, "endDate": end_date, "quarantineType": "spam", "offset": offset, "limit": limit}

        optional_params = {
            "order_by": "orderBy",
            "order_direction": "orderDir",
            "envelope_recipient_filter_operator": "envelopeRecipientFilterOperator",
            "envelope_recipient_filter_value": "envelopeRecipientFilterValue",
            "filter_by": "filterBy",
            "filter_operator": "filterOperator",
            "filter_value": "filterValue",
        }

        for param_name, api_param in optional_params.items():
            if value := param.get(param_name):
                params[api_param] = value

        if order_by := params.get("orderBy"):
            if order_by not in CISCOSMA_VALID_ORDER_BY:
                return action_result.set_status(phantom.APP_ERROR, f"Invalid 'order_by' parameter. Must be one of: {CISCOSMA_VALID_ORDER_BY}")

        if order_dir := params.get("orderDir"):
            if order_dir not in CISCOSMA_VALID_ORDER_DIRECTIONS:
                return action_result.set_status(
                    phantom.APP_ERROR, f"Invalid 'order_direction' parameter. Must be one of: {CISCOSMA_VALID_ORDER_DIRECTIONS}"
                )

        if envelope_recipient_operator := params.get("envelopeRecipientFilterOperator"):
            if envelope_recipient_operator not in CISCOSMA_VALID_FILTER_OPERATORS:
                return action_result.set_status(
                    phantom.APP_ERROR,
                    f"Invalid 'envelope_recipient_filter_operator' parameter. Must be one of: {CISCOSMA_VALID_FILTER_OPERATORS}",
                )

        if filter_operator := params.get("filterOperator"):
            if filter_operator not in CISCOSMA_VALID_FILTER_OPERATORS:
                return action_result.set_status(
                    phantom.APP_ERROR, f"Invalid 'filter_operator' parameter. Must be one of: {CISCOSMA_VALID_FILTER_OPERATORS}"
                )

        ret_val, response = self._make_authenticated_request(action_result, CISCOSMA_SEARCH_MESSAGES_ENDPOINT, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            messages = response.get("data", [])
            total_count = response.get("meta", {}).get("totalCount", 0)

            for message in messages:
                action_result.add_data(message)

            summary = {"total_messages": total_count, "messages_returned": len(messages)}
            action_result.update_summary(summary)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response: {e!s}")

        self.save_progress("Successfully completed search_spam_quarantine_messages")

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved messages")

    def _handle_search_general_quarantine_messages(self, param):
        self.save_progress("Searching for general quarantine messages...")

        action_result = self.add_action_result(ActionResult(dict(param)))

        start_date = param.get("start_date")
        end_date = param.get("end_date")
        if not start_date or not end_date:
            return action_result.set_status(phantom.APP_ERROR, "Both 'start_date' and 'end_date' parameters are required")

        start_date = self._parse_and_format_date(start_date, zero_seconds=True)
        end_date = self._parse_and_format_date(end_date, zero_seconds=True)

        offset = param.get("offset", CISCOSMA_DEFAULT_LIST_OFFSET)
        limit = param.get("limit", CISCOSMA_DEFAULT_LIST_LIMIT)

        params = {"startDate": start_date, "endDate": end_date, "quarantineType": "pvo", "offset": offset, "limit": limit}

        quarantines = param.get("quarantines")
        if not quarantines:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'quarantines' is required")
        params["quarantines"] = quarantines

        optional_params = {
            "subject_filter_by": "subjectFilterBy",
            "subject_filter_value": "subjectFilterValue",
            "originating_esa_ip": "originatingEsaIp",
            "attachment_name": "attachmentName",
            "attachment_size_filter_by": "attachmentSizeFilterBy",
            "attachment_size_from": "attachmentSizeFromValue",
            "attachment_size_to": "attachmentSizeToValue",
            "order_by": "orderBy",
            "order_direction": "orderDir",
            "envelope_recipient_filter_by": "envelopeRecipientFilterBy",
            "envelope_recipient_filter_value": "envelopeRecipientFilterValue",
            "envelope_sender_filter_by": "envelopeSenderFilterBy",
            "envelope_sender_filter_value": "envelopeSenderFilterValue",
        }

        for param_name, api_param in optional_params.items():
            if value := param.get(param_name):
                params[api_param] = value

        if subject_filter := params.get("subjectFilterBy"):
            if subject_filter not in CISCOSMA_VALID_SUBJECT_FILTERS:
                return action_result.set_status(
                    phantom.APP_ERROR, f"Invalid subject_filter_by. Must be one of: {CISCOSMA_VALID_SUBJECT_FILTERS}"
                )

        if size_filter := params.get("attachmentSizeFilterBy"):
            if size_filter not in CISCOSMA_VALID_SIZE_FILTERS:
                return action_result.set_status(
                    phantom.APP_ERROR, f"Invalid attachment_size_filter_by. Must be one of: {CISCOSMA_VALID_SIZE_FILTERS}"
                )

        if order_by := params.get("orderBy"):
            if order_by not in CISCOSMA_VALID_QUARANTINE_ORDER_BY:
                return action_result.set_status(phantom.APP_ERROR, f"Invalid order_by. Must be one of: {CISCOSMA_VALID_QUARANTINE_ORDER_BY}")

        if order_dir := params.get("orderDir"):
            if order_dir not in CISCOSMA_VALID_ORDER_DIRECTIONS:
                return action_result.set_status(phantom.APP_ERROR, f"Invalid order_direction. Must be one of: {CISCOSMA_VALID_ORDER_DIRECTIONS}")

        ret_val, response = self._make_authenticated_request(action_result, CISCOSMA_SEARCH_MESSAGES_ENDPOINT, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            messages = response.get("data", [])
            total_count = response.get("meta", {}).get("totalCount", 0)

            for message in messages:
                action_result.add_data(message)

            summary = {"total_messages": total_count, "messages_returned": len(messages), "quarantines": quarantines}
            action_result.update_summary(summary)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response: {e!s}")

        self.save_progress("Successfully completed search_general_quarantine_messages")

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved quarantine messages")

    def _handle_get_spam_quarantine_message_details(self, param):
        self.save_progress("Getting details for spam quarantine message...")

        action_result = self.add_action_result(ActionResult(dict(param)))

        message_id = param.get("message_id")
        if not message_id:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'message_id' is required")

        endpoint = CISCOSMA_GET_MESSAGE_DETAILS_ENDPOINT
        params = {"mid": message_id, "quarantineType": "spam"}

        ret_val, response = self._make_authenticated_request(action_result, endpoint, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            message_data = response.get("data", {})
            action_result.add_data(message_data)

            summary = {"subject": message_data.get("attributes", {}).get("subject")}
            action_result.update_summary(summary)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response: {e!s}")

        self.save_progress("Successfully completed get_spam_quarantine_message_details")

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved message details")

    def _handle_get_general_quarantine_message_details(self, param):
        self.save_progress("Getting details for general quarantine message...")

        action_result = self.add_action_result(ActionResult(dict(param)))

        message_id = param.get("message_id")
        if not message_id:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'message_id' is required")

        endpoint = CISCOSMA_GET_MESSAGE_DETAILS_ENDPOINT
        params = {"mid": message_id, "quarantineType": "pvo"}

        ret_val, response = self._make_authenticated_request(action_result, endpoint, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            message_data = response.get("data", {})
            action_result.add_data(message_data)

            attributes = message_data.get("attributes", {})
            message_details = attributes.get("messageDetails", {})
            quarantine_details = attributes.get("quarantineDetails", [{}])[0]

            summary = {
                "subject": message_details.get("subject"),
                "quarantine_name": quarantine_details.get("quarantineName"),
                "reason": quarantine_details.get("reason", []),
            }
            action_result.update_summary(summary)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response: {e!s}")

        self.save_progress("Successfully completed get_general_quarantine_message_details")

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved general quarantine message details")

    def _handle_release_spam_message(self, param):
        self.save_progress("Releasing spam message...")

        action_result = self.add_action_result(ActionResult(dict(param)))

        message_id = param.get("message_id")
        if not message_id:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'message_id' is required")

        try:
            message_id = int(message_id)
        except ValueError:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'message_id' must be a valid integer")

        payload = {"action": "release", "quarantineType": "spam", "mids": [message_id]}

        ret_val, response = self._make_authenticated_request(action_result, CISCOSMA_RELEASE_MESSAGES_ENDPOINT, json_data=payload, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            release_data = response.get("data", {})
            action_result.add_data(release_data)

            summary = {"total_released": release_data.get("totalCount", 0), "action": release_data.get("action")}
            action_result.update_summary(summary)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response: {e!s}")

        self.save_progress("Successfully completed release_spam_message")

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully released message")

    def _handle_release_general_quarantine_message(self, param):
        self.save_progress("Releasing general quarantine message...")

        action_result = self.add_action_result(ActionResult(dict(param)))

        message_id = param.get("message_id")
        quarantine_name = param.get("quarantine_name")

        if not message_id:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'message_id' is required")
        if not quarantine_name:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'quarantine_name' is required")

        try:
            message_id = int(message_id)
        except ValueError:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'message_id' must be a valid integer")

        payload = {"action": "release", "quarantineType": "pvo", "quarantineName": quarantine_name, "mids": [message_id]}

        ret_val, response = self._make_authenticated_request(action_result, CISCOSMA_RELEASE_MESSAGES_ENDPOINT, json_data=payload, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            release_data = response.get("data", {})
            action_result.add_data(release_data)

            summary = {
                "total_released": release_data.get("totalCount", 0),
                "action": release_data.get("action"),
                "quarantine_name": quarantine_name,
            }
            action_result.update_summary(summary)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response: {e!s}")

        self.save_progress("Successfully completed release_general_quarantine_message")

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully released message from general quarantine")

    def _handle_delete_spam_message(self, param):
        self.save_progress("Deleting spam message...")

        action_result = self.add_action_result(ActionResult(dict(param)))

        message_id = param.get("message_id")
        if not message_id:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'message_id' is required")

        try:
            message_id = int(message_id)
        except ValueError:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'message_id' must be a valid integer")

        payload = {"quarantineType": "spam", "mids": [message_id]}

        ret_val, response = self._make_authenticated_request(
            action_result, CISCOSMA_DELETE_MESSAGES_ENDPOINT, json_data=payload, method="delete"
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            delete_data = response.get("data", {})
            action_result.add_data(delete_data)

            summary = {"total_deleted": delete_data.get("totalCount", 0), "action": delete_data.get("action")}
            action_result.update_summary(summary)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response: {e!s}")

        self.save_progress("Successfully completed delete_spam_message")

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully deleted message")

    def _handle_delete_general_quarantine_message(self, param):
        self.save_progress("Deleting general quarantine message...")

        action_result = self.add_action_result(ActionResult(dict(param)))

        message_id = param.get("message_id")
        quarantine_name = param.get("quarantine_name")

        if not message_id:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'message_id' is required")
        if not quarantine_name:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'quarantine_name' is required")

        try:
            # This should be acceptable validation as the mid is just a number
            message_id = int(message_id)
        except ValueError:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'message_id' must be a valid integer")

        payload = {"quarantineType": "pvo", "quarantineName": quarantine_name, "mids": [message_id]}

        ret_val, response = self._make_authenticated_request(
            action_result, CISCOSMA_DELETE_MESSAGES_ENDPOINT, json_data=payload, method="delete"
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            delete_data = response.get("data", {})
            action_result.add_data(delete_data)

            summary = {
                "total_deleted": delete_data.get("totalCount", 0),
                "action": delete_data.get("action"),
                "quarantine_name": quarantine_name,
            }
            action_result.update_summary(summary)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response: {e!s}")

        self.save_progress("Successfully completed delete_general_quarantine_message")

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully deleted message from general quarantine")

    def _handle_search_tracking_messages(self, param):
        self.save_progress("Searching for tracking messages...")

        action_result = self.add_action_result(ActionResult(dict(param)))

        start_date = param.get("start_date")
        end_date = param.get("end_date")
        if not start_date or not end_date:
            return action_result.set_status(phantom.APP_ERROR, "Both 'start_date' and 'end_date' parameters are required")

        start_date = self._parse_and_format_date(start_date, zero_seconds=True)
        end_date = self._parse_and_format_date(end_date, zero_seconds=True)

        offset = param.get("offset", CISCOSMA_DEFAULT_LIST_OFFSET)
        limit = param.get("limit", CISCOSMA_DEFAULT_LIST_LIMIT)
        search_option = param.get("search_option", "messages")

        params = {"startDate": start_date, "endDate": end_date, "searchOption": search_option, "offset": offset, "limit": limit}

        # Filter pairs
        filter_pairs = {
            ("sender_filter_operator", "sender_filter_value"): ("envelopeSenderfilterOperator", "envelopeSenderfilterValue"),
            ("recipient_filter_operator", "recipient_filter_value"): ("envelopeRecipientfilterOperator", "envelopeRecipientfilterValue"),
            ("subject_filter_operator", "subject_filter_value"): ("subjectfilterOperator", "subjectfilterValue"),
            ("attachment_name_operator", "attachment_name_value"): ("attachmentNameOperator", "attachmentNameValue"),
        }

        for (op_param, val_param), (op_name, val_name) in filter_pairs.items():
            operator = param.get(op_param)
            value = param.get(val_param)
            if operator and value:
                params[op_name] = operator
                params[val_name] = value
            elif operator or value:
                return action_result.set_status(phantom.APP_ERROR, f"Both {op_param} and {val_param} must be provided together")

        optional_params = {
            "cisco_host": "ciscoHost",
            "sender_ip": "senderIp",
            "file_sha_256": "fileSha256",
            "message_id_header": "messageIdHeader",
        }

        for param_name, api_param in optional_params.items():
            if value := param.get(param_name):
                params[api_param] = value

        ret_val, response = self._make_authenticated_request(action_result, CISCOSMA_SEARCH_TRACKING_MESSAGES_ENDPOINT, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            messages = response.get("data", [])
            total_count = response.get("meta", {}).get("totalCount", 0)
            bad_records = response.get("meta", {}).get("num_bad_records", 0)

            for message in messages:
                action_result.add_data(message)

            summary = {"total_messages": total_count, "messages_returned": len(messages), "bad_records": bad_records}
            action_result.update_summary(summary)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response: {e!s}")

        self.save_progress("Successfully completed search_tracking_messages")

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved tracking messages")

    def _handle_get_message_tracking_details(self, param):
        self.save_progress("Getting details for tracking message...")

        action_result = self.add_action_result(ActionResult(dict(param)))

        message_id = param.get("message_id")
        serial_number = param.get("serial_number")
        if not message_id:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'message_id' is required")
        if not serial_number:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'serial_number' is required")

        try:
            message_id = int(message_id)
        except ValueError:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'message_id' must be a valid integer")

        if param.get("start_date"):
            param["start_date"] = self._parse_and_format_date(param.get("start_date"), zero_seconds=True)
        if param.get("end_date"):
            param["end_date"] = self._parse_and_format_date(param.get("end_date"), zero_seconds=True)

        params = {"mid": message_id, "serialNumber": serial_number}

        optional_params = {"icid": "icid", "start_date": "startDate", "end_date": "endDate"}

        for param_name, api_param in optional_params.items():
            if value := param.get(param_name):
                params[api_param] = value

        ret_val, response = self._make_authenticated_request(action_result, CISCOSMA_GET_MESSAGE_TRACKING_DETAILS_ENDPOINT, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            message_data = response.get("data", {}).get("messages", {})
            action_result.add_data(message_data)

            summary = {
                "subject": message_data.get("subject"),
                "status": message_data.get("messageStatus"),
                "direction": message_data.get("direction"),
            }
            action_result.update_summary(summary)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response: {e!s}")

        self.save_progress("Successfully completed get_message_tracking_details")

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved message tracking details")

    def _handle_search_list(self, param):
        self.save_progress("Searching for list entries...")

        action_result = self.add_action_result(ActionResult(dict(param)))

        list_type = param.get("list_type", "safelist").lower()
        if list_type not in CISCOSMA_VALID_LIST_TYPES:
            return action_result.set_status(phantom.APP_ERROR, f"Invalid parameter 'list_type'. Must be one of: {CISCOSMA_VALID_LIST_TYPES}")

        endpoint = CISCOSMA_SAFELIST_ENDPOINT if list_type == "safelist" else CISCOSMA_BLOCKLIST_ENDPOINT

        params = {"action": "view", "quarantineType": "spam"}

        view_by = param.get("view_by", "recipient")
        if view_by not in CISCOSMA_VALID_LIST_VIEW_BY:
            return action_result.set_status(phantom.APP_ERROR, f"Invalid parameter 'view_by'. Must be one of: {CISCOSMA_VALID_LIST_VIEW_BY}")
        params["viewBy"] = view_by

        order_by = param.get("order_by", "recipient")
        if order_by not in CISCOSMA_VALID_LIST_ORDER_BY:
            return action_result.set_status(phantom.APP_ERROR, f"Invalid parameter 'order_by'. Must be one of: {CISCOSMA_VALID_LIST_ORDER_BY}")
        params["orderBy"] = order_by

        order_dir = param.get("order_direction", "desc")
        if order_dir not in CISCOSMA_VALID_ORDER_DIRECTIONS:
            return action_result.set_status(
                phantom.APP_ERROR, f"Invalid parameter 'order_direction'. Must be one of: {CISCOSMA_VALID_ORDER_DIRECTIONS}"
            )
        params["orderDir"] = order_dir

        offset = param.get("offset", CISCOSMA_DEFAULT_LIST_OFFSET)
        limit = param.get("limit", CISCOSMA_DEFAULT_LIST_LIMIT)
        params["offset"] = offset
        params["limit"] = limit

        # Handle search (only when orderBy=recipient)
        if search := param.get("search"):
            if order_by != "recipient":
                return action_result.set_status(phantom.APP_ERROR, "Search parameter is only supported when order_by is set to 'recipient'")
            params["search"] = search

        ret_val, response = self._make_authenticated_request(action_result, endpoint, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            entries = response.get("data", [])
            total_count = response.get("meta", {}).get("totalCount", 0)

            for entry in entries:
                action_result.add_data(entry)

            summary = {"total_entries": total_count, "entries_returned": len(entries), "list_type": list_type}
            action_result.update_summary(summary)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response: {e!s}")

        self.save_progress("Successfully completed search_list")

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully retrieved {list_type} entries")

    def _handle_add_list_entry(self, param):
        self.save_progress("Adding list entry...")

        action_result, payload, endpoint = self._list_entry_operation_setup(param, "add")
        if payload is None:
            return action_result.get_status()

        ret_val, response = self._make_authenticated_request(action_result, endpoint, json_data=payload, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            action_result.add_data(response.get("data", {}))

            summary = {
                "list_type": "safelist" if CISCOSMA_SAFELIST_ENDPOINT in endpoint else "blocklist",
                "view_by": payload["viewBy"],
                "status": "success",
            }
            action_result.update_summary(summary)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response: {e!s}")

        self.save_progress("Successfully completed add_list_entry")

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully added entry in {summary['list_type']}")

    def _handle_edit_list_entry(self, param):
        self.save_progress("Editing list entry...")

        action_result, payload, endpoint = self._list_entry_operation_setup(param, "edit")
        if payload is None:
            return action_result.get_status()

        ret_val, response = self._make_authenticated_request(action_result, endpoint, json_data=payload, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            action_result.add_data(response.get("data", {}))

            summary = {
                "list_type": "safelist" if CISCOSMA_SAFELIST_ENDPOINT in endpoint else "blocklist",
                "view_by": payload["viewBy"],
                "status": "success",
            }
            action_result.update_summary(summary)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response: {e!s}")

        self.save_progress("Successfully completed edit_list_entry")

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully edited entry in {summary['list_type']}")

    def _handle_delete_list_entry(self, param):
        self.save_progress("Deleting list entry...")

        action_result, payload, endpoint = self._list_entry_operation_setup(param, "delete")
        if payload is None:
            return action_result.get_status()

        summary = {
            "payload": payload,
        }
        action_result.update_summary(summary)

        ret_val, response = self._make_authenticated_request(action_result, endpoint, json_data=payload, method="delete")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            delete_data = response.get("data", {})
            action_result.add_data(delete_data)

            summary = {
                "list_type": "safelist" if CISCOSMA_SAFELIST_ENDPOINT in endpoint else "blocklist",
                "view_by": payload["viewBy"],
                "total_deleted": delete_data.get("totalCount", 0),
                "status": "success",
            }
            action_result.update_summary(summary)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response: {e!s}")

        self.save_progress("Successfully completed delete_list_entry")

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully deleted entries from {summary['list_type']}")

    def _handle_get_statistics_report(self, param):
        self.save_progress("Getting statistics report...")

        action_result = self.add_action_result(ActionResult(dict(param)))

        start_date = param.get("start_date")
        end_date = param.get("end_date")
        report_type = param.get("report_type")
        device_type = param.get("device_type", "esa")
        if not start_date or not end_date:
            return action_result.set_status(phantom.APP_ERROR, "Both 'start_date' and 'end_date' parameters are required")

        start_date = self._parse_and_format_date(start_date, zero_minutes=True, zero_seconds=True)
        end_date = self._parse_and_format_date(end_date, zero_minutes=True, zero_seconds=True)

        if not report_type:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'report_type' is required")

        offset = param.get("offset", CISCOSMA_DEFAULT_LIST_OFFSET)
        limit = param.get("limit", CISCOSMA_DEFAULT_LIST_LIMIT)

        params = {"startDate": start_date, "endDate": end_date, "device_type": device_type, "offset": offset, "limit": limit}

        optional_params = {
            "query_type": "query_type",
            "order_by": "orderBy",
            "order_direction": "orderDir",
            "top": "top",
            "filter_value": "filterValue",
            "filter_by": "filterBy",
            "filter_operator": "filterOperator",
            "device_group_name": "device_group_name",
            "device_name": "device_name",
        }

        for param_name, api_param in optional_params.items():
            if value := param.get(param_name):
                params[api_param] = value

        if order_dir := params.get("orderDir"):
            if order_dir not in CISCOSMA_VALID_ORDER_DIRECTIONS:
                return action_result.set_status(
                    phantom.APP_ERROR, f"Invalid parameter 'order_direction'. Must be one of: {CISCOSMA_VALID_ORDER_DIRECTIONS}"
                )

        if filter_op := params.get("filterOperator"):
            if filter_op not in CISCOSMA_VALID_FILTER_OPERATORS_REPORT:
                return action_result.set_status(
                    phantom.APP_ERROR, f"Invalid parameter 'filter_operator'. Must be one of: {CISCOSMA_VALID_FILTER_OPERATORS_REPORT}"
                )

        counter = param.get("counter")

        if counter:
            endpoint = CISCOSMA_REPORTING_ENDPOINT.format(f"{report_type}/{counter}")
        else:
            endpoint = CISCOSMA_REPORTING_ENDPOINT.format(report_type)

        ret_val, response = self._make_authenticated_request(action_result, endpoint, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            action_result.add_data(response.get("data", {}))

            summary = {"report_type": report_type, "total_count": response.get("meta", {}).get("totalCount", 0)}
            action_result.update_summary(summary)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response: {e!s}")

        self.save_progress("Successfully completed get_statistics_report")

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved statistics report")

    def _handle_download_attachment(self, param):
        self.save_progress("Downloading attachment...")

        action_result = self.add_action_result(ActionResult(dict(param)))

        message_id = param.get("message_id")
        attachment_id = param.get("attachment_id")
        if not message_id:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'message_id' is required")
        if not attachment_id:
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'attachment_id' is required")

        params = {"mid": message_id, "attachmentId": attachment_id, "quarantineType": "pvo"}

        headers = {"Accept": "*/*", "Content-Type": "application/json"}

        try:
            ret_val, response = self._make_authenticated_request(
                action_result, CISCOSMA_DOWNLOAD_ATTACHMENT_ENDPOINT, params=params, headers=headers
            )

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            # JSON error response handling
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type.lower():
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error", {}).get("message", "Unknown error occurred")
                    return action_result.set_status(phantom.APP_ERROR, f"API Error: {error_msg}")
                except Exception:
                    pass

            # Download and add to vault
            default_filename = f"attachment_{message_id}_{attachment_id}"
            success, vault_id, filename, error_message = self._download_to_vault(action_result, response, default_filename)

            if not success:
                return action_result.set_status(phantom.APP_ERROR, error_message)

            action_result.add_data(
                {
                    "vault_id": vault_id,
                    "filename": filename,
                }
            )

            summary = {"vault_id": vault_id, "filename": filename, "size": response.headers.get("Content-Length", "Unknown")}
            action_result.update_summary(summary)

            self.save_progress("Successfully completed download_attachment")

            return action_result.set_status(phantom.APP_SUCCESS, f"Successfully downloaded attachment '{filename}' to vault")

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error downloading attachment: {e!s}")

    def initialize(self):
        config = self.get_config()
        self._base_url = config["host"].rstrip("/")
        self._username = config["username"]
        self._password = config["password"]
        self._verify = config.get("verify_server_cert", False)
        return phantom.APP_SUCCESS

    def handle_action(self, param):
        self.debug_print("action_id ", self.get_action_identifier())

        action_mapping = {
            "test_connectivity": self._handle_test_connectivity,
            "search_spam_quarantine_messages": self._handle_search_spam_quarantine_messages,
            "search_general_quarantine_messages": self._handle_search_general_quarantine_messages,
            "search_tracking_messages": self._handle_search_tracking_messages,
            "get_spam_quarantine_message_details": self._handle_get_spam_quarantine_message_details,
            "get_general_quarantine_message_details": self._handle_get_general_quarantine_message_details,
            "get_message_tracking_details": self._handle_get_message_tracking_details,
            "release_spam_message": self._handle_release_spam_message,
            "release_general_quarantine_message": self._handle_release_general_quarantine_message,
            "delete_spam_message": self._handle_delete_spam_message,
            "delete_general_quarantine_message": self._handle_delete_general_quarantine_message,
            "search_list": self._handle_search_list,
            "add_list_entry": self._handle_add_list_entry,
            "edit_list_entry": self._handle_edit_list_entry,
            "delete_list_entry": self._handle_delete_list_entry,
            "get_statistics_report": self._handle_get_statistics_report,
            "download_attachment": self._handle_download_attachment,
        }

        action = self.get_action_identifier()
        action_execution_status = phantom.APP_SUCCESS

        action_keys = list(action_mapping.keys())
        if action in action_keys:
            action_function = action_mapping[action]
            action_execution_status = action_function(param)

        return action_execution_status


if __name__ == "__main__":
    import sys

    import pudb

    pudb.set_trace()

    connector = CiscoSmaConnector()
    connector.print_progress_message = True

    sys.exit(0)
