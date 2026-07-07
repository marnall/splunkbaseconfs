# File: dataminrpulse_consts.py
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

# Endpoints
DATAMINRPULSE_BASE_URL = "https://{api_version}.dataminr.com"
DATAMINRPULSE_GET_LISTS = "/account/2/get_lists?alertversion=14"
DATAMINRPULSE_GET_LISTS_V4 = "/pulse/v1/lists"
DATAMINRPULSE_GET_ALERTS = "/api/3/alerts?alertversion=14"
DATAMINRPULSE_GET_ALERTS_V4 = "/pulse/v1/alerts"
DATAMINRPULSE_GET_ALERT_V4 = "/pulse/v1/alerts/{alert_id}"
DATAMINRPULSE_ENDPOINT_TOKEN = "/auth/{api_version}/token"
DATAMINRPULSE_GET_ARTIFACT_DETAILS = "{instance}/rest/artifact/{artifact_id}"
DATAMINRPULSE_STATE_TOKEN = "token"
DATAMINRPULSE_STATE_DMA_TOKEN = "dmaToken"
DATAMINRPULSE_STATE_REFRESH_TOKEN = "refreshToken"
DATAMINRPULSE_STATE_EXPIRE = "expire"
DATAMINRPULSE_ERROR_STATE_FILE_CORRUPT = "Error occurred while loading the state file. Resetting the state file with the default format"
DATAMINRPULSE_REQUEST_TIMEOUT = 240
DATAMINRPULSE_ENDPOINT_TEST_CONNECTIVITY = "/auth/2/token"
DATAMINRPULSE_ERROR_SYSTEM_HEALTH = "Failed to get the system health status"
DATAMINRPULSE_ACTION_EMPTY_ALERTS_RESPONSE = "No alerts found"
DATAMINRPULSE_ERROR_TEST_CONNECTIVITY_INVALID_STATUS = "Error message: Server status is {}"
DATAMINRPULSE_SUCCESS_TEST_CONNECTIVITY = "Test Connectivity Passed"
DATAMINRPULSE_ERROR_TEST_CONNECTIVITY = "Test Connectivity Failed"
DATAMINRPULSE_ERROR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
DATAMINRPULSE_ERROR_GENERAL_MSG = "Status code: {0}, Data from server: {1}"
DATAMINRPULSE_ERROR_INVALID_INT_PARAM = "Please provide a valid integer value in the '{key}' parameter"
DATAMINRPULSE_ERROR_NEGATIVE_INT_PARAM = "Please provide a valid non-negative integer value in the '{key}' parameter"
DATAMINRPULSE_ERROR_ZERO_INT_PARAM = "Please provide a non-zero positive integer value in the '{key}' parameter"
DATAMINRPULSE_STATE_FROM_VALUE = "from"
DATAMINRPULSE_STATE_TO_VALUE = "to"
DATAMINRPULSE_STATE_LIST_ID_VALUE = "list_id"
DATAMINRPULSE_STATE_QUERY_VALUE = "query"
DATAMINRPULSE_STATE_API_VERSION = "api_version"
DATAMINRPULSE_ERROR_JSON_RESPONSE = "Unable to parse JSON response. Error: {0}"
DATAMINRPULSE_ERROR_REST_CALL = "Error connecting to server. Details: {0}"
DATAMINRPULSE_ERROR_EMPTY_RESPONSE = "Status code: {}. Empty response and no information available"
DATAMINRPULSE_ERROR_HTML_RESPONSE = "Error parsing html response"
DATAMINRPULSE_DUPLICATE_CONTAINER_FOUND_MSG = "duplicate container found"
DATAMINRPULSE_ACTION_EMPTY_ALERTS = "No alerts found"
DATAMINRPULSE_ALERT_TYPE_VALUE = ["All", "Alert", "Urgent", "Flash"]
DATAMINRPULSE_ERROR_INVALID_PARAMETER_VALUE = "Please provide valid value in the 'Alert Type' asset parameter"
DATAMINRPULSE_APP_ID = "8630b723-b317-4765-b923-5be5229c71d1"
DATAMINRPULSE_EMPTY_RESPONSE_STATUS_CODE = [200, 201, 204]
DATAMINRPULSE_DECODE_FROM_ERROR = 'Error from server. Error message: Unable to decode "from" cursor, invalid format'
DATAMINRPULSE_SEVERITY_ENDPOINT = "rest/severity"
DATAMINRPULSE_SEVERITY_PAYLOAD = [{"color": "red", "name": "Flash"}, {"color": "orange", "name": "Urgent"}, {"color": "yellow", "name": "Alert"}]
DATAMINR_V3_V4_API_ERROR_MSG = "Please ensure credentials are correct and correspond to the intended API version (v3 or v4)"
