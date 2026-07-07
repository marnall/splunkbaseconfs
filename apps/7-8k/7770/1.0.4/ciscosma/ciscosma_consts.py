# File: ciscosma_consts.py
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

# Cisco SMA Constants

CISCOSMA_VALID_ORDER_BY = ["from_address", "to_address", "subject"]
CISCOSMA_VALID_ORDER_DIRECTIONS = ["asc", "desc"]
CISCOSMA_VALID_FILTER_OPERATORS = ["contains", "is", "begins_with", "ends_with", "does_not_contain"]
CISCOSMA_VALID_FILTER_OPERATORS_REPORT = ["begins_with", "is"]
CISCOSMA_VALID_SUBJECT_FILTERS = [
    "contains",
    "starts_with",
    "ends_with",
    "matches_exactly",
    "does_not_contain",
    "does_not_start_with",
    "does_not_end_with",
    "does_not_match",
]
CISCOSMA_VALID_SIZE_FILTERS = ["range", "less_than", "more_than"]
CISCOSMA_VALID_QUARANTINE_ORDER_BY = ["sender", "subject", "received", "scheduledExit", "size"]
CISCOSMA_VALID_LIST_TYPES = ["safelist", "blocklist"]
CISCOSMA_VALID_LIST_VIEW_BY = ["sender", "recipient"]
CISCOSMA_VALID_LIST_ORDER_BY = ["sender", "recipient"]
CISCOSMA_DEFAULT_LIST_LIMIT = 100
CISCOSMA_DEFAULT_LIST_OFFSET = 0

CISCOSMA_GET_TOKEN_ENDPOINT = "/sma/api/v2.0/login"
CISCOSMA_GET_SUBSCRIPTION_ENDPOINT = "/sma/api/v2.0/config/logs/subscriptions"
CISCOSMA_GET_MESSAGE_DETAILS_ENDPOINT = "/sma/api/v2.0/quarantine/messages/details"
CISCOSMA_GET_MESSAGE_TRACKING_DETAILS_ENDPOINT = "/sma/api/v2.0/message-tracking/details"
CISCOSMA_SEARCH_MESSAGES_ENDPOINT = "/sma/api/v2.0/quarantine/messages"
CISCOSMA_SEARCH_TRACKING_MESSAGES_ENDPOINT = "/sma/api/v2.0/message-tracking/messages"
CISCOSMA_RELEASE_MESSAGES_ENDPOINT = "/sma/api/v2.0/quarantine/messages"
CISCOSMA_DELETE_MESSAGES_ENDPOINT = "/sma/api/v2.0/quarantine/messages"
CISCOSMA_SAFELIST_ENDPOINT = "/sma/api/v2.0/quarantine/safelist"
CISCOSMA_BLOCKLIST_ENDPOINT = "/sma/api/v2.0/quarantine/blocklist"
CISCOSMA_REPORTING_ENDPOINT = "/sma/api/v2.0/reporting/{}"
CISCOSMA_DOWNLOAD_ATTACHMENT_ENDPOINT = "/sma/api/v2.0/quarantine/messages/attachment"
