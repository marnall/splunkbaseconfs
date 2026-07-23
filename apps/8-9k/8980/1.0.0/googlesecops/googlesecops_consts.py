# File: googlesecops_consts.py
#
# Copyright (c) 2026 Google
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

# API URLs
SECOPS_V1_ALPHA_URL = "https://chronicle.{}.rep.googleapis.com/v1alpha"

# Date Formats
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
IOC_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Retry Configuration
STATUS_LIST_TO_RETRY = [429, *list(range(500, 600))]
MAX_RETRIES = 4
BACKOFF_FACTOR = 7.5

# Default Values
DEFAULT_FIRST_FETCH = "3 days"
DEFAULT_MAX_FETCH = 100
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000
DEFAULT_MAX_RESULTS_POLL_NOW = 10000
DEFAULT_MAX_RESULTS_SCHEDULED_POLL = 10000
POLL_TIMEOUT = 50 * 60
DEFAULT_BATCH_SIZE = 100
MAX_CHECKPOINT_AGE_DAYS = 7
DEFAULT_CHECKPOINT = 1

# Messages
EXECUTION_START_MSG = "Executing {0} action"
TEST_CONNECTIVITY_START_MSG = "Connecting to Google SecOps"
SUCCESS_TEST_CONNECTIVITY = "Test Connectivity Passed"
ERROR_TEST_CONNECTIVITY = "Test Connectivity Failed"
REQUEST_DEFAULT_TIMEOUT = 30
ACTION_SUCCESS_RESPONSE = "Action {action} has been executed successfully"
GOOGLESECOPS_UNAVAILABLE_MESSAGE_ERROR = "Error message unavailable. Please check the asset configuration and|or action parameters."

ERROR_INVALID_INT_PARAM = "Please provide a valid integer value in the '{key}' parameter"
ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
EMPTY_RESPONSE_STATUS_CODES = [200, 204]
ERROR_INVALID_SELECTION = "Invalid '{0}' selected. Must be one of: {1}."
ERROR_GENERAL_MESSAGE = "Status code: {0}, Data from server: {1}"
ERROR_HTML_RESPONSE = "Error parsing html response"
ERROR_ZERO_INT_PARAM = "Please provide a non-zero positive integer value in the '{key}' parameter"
ERROR_NEG_INT_PARAM = "Please provide a positive integer value in the '{key}' parameter"
ERROR_INVALID_JSON_PARAM = "Please provide a valid JSON value for the '{key}' parameter"
ERROR_MISSING_REQUIRED_PARAM = "'{key}' is required parameter"
ERROR_INVALID_INT_RANGE = "Please provide a valid integer value in the '{key}' parameter between {min_value} and {max_value}"
ERROR_INVALID_PAGE_SIZE = "Page size should be in the range from 1 to {0}."
ERROR_REQUIRED_ARGUMENT = "Missing argument {0}."
ERROR_INVALID_SERVICE_ACCOUNT = "User's Service Account JSON has invalid format"
ERROR_INVALID_PROJECT_NUMBER = "Google SecOps Project Number should be a positive number."
ERROR_MISSING_PROJECT_INSTANCE = "Please Provide the Google SecOps Project Instance ID."
ERROR_MISSING_REGION = "Please Provide the valid region."
ERROR_SENSITIVE_DATA = "Sensitive authentication details were redacted."

# Asset Identifier Mapping
ASSET_IDENTIFIER_NAME_DICT = {
    "host name": "hostname",
    "ip address": "assetIpAddress",
    "mac address": "mac",
    "product id": "productId",
}

# Valid Values
VALID_DETECTIONS_ALERT_STATE = ["ALERTING", "NOT_ALERTING"]
VALID_DETECTIONS_LIST_BASIS = ["DETECTION_TIME", "CREATED_TIME"]
VALID_ASSET_INDICATOR_TYPES = ["hostname", "assetIpAddress", "mac", "productId"]

# Limits
MAX_RESULTS_WARNING_THRESHOLD = 100000  # Warn if max_results exceeds this

# Context Output Paths
SECOPS_OUTPUT_PATHS = {
    "Events": "GoogleSecOps.Events(val.id == obj.id)",
    "Detections": "GoogleSecOps.Detections(val.id == obj.id && val.ruleVersion == obj.ruleVersion)",
}
