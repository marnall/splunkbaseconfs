# File: insightvm_consts.py
#
# Copyright (c) 2017-2026 Splunk Inc.
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
INSIGHTVM_ERROR_BAD_STATUS = "Call to InsightVM failed"
INSIGHTVM_ERROR_TEST_CONNECTIVITY = "Test Connectivity Failed"
INSIGHTVM_ERROR_NEED_AUTH = "Authorization required for API access"
INSIGHTVM_ERROR_PARSE_XML = "Could not parse XML response from InsightVM server"
INSIGHTVM_ERROR_BAD_SITE = "The given site could not be found on the InsightVM server"
INSIGHTVM_ERROR_BAD_IP = "This error usually indicates that the IP or port is incorrect"
INSIGHTVM_ERROR_BAD_CREDS = "The provided credentials were rejected by the InsightVM server"
INSIGHTVM_ERROR_NO_SESSION_ID = "Could not get session ID from login call to InsightVM server"
INSIGHTVM_ERROR_SERVER_CONNECTION = "Could not connect to the InsightVM server. Error string: {0}"
INSIGHTVM_ERROR_BAD_CERT = "This error usually indicates that the certificate on the server could not be verified"

INSIGHT_SUCCESS_TEST_CONNECTIVITY = "Test Connectivity Passed"

INSIGHTVM_API_URL = "https://{0}:{1}/api/3"

INSIGHTVM_DEFAULT_CONTAINER_COUNT = 10

INSIGHTVM_DEFAULT_TIMEOUT = 30

DEFAULT_MAX_RESULTS = 10

MATCH_LIST = ["any", "all"]

# Constants related to "_get_error_message_from_exception"
INSIGHTVM_ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"

# Constants related to "_validate_integer"
INSIGHT_INVALID_INTEGER_ERROR_MESSAGE = "Please provide a valid integer value in the {} parameter"
INSIGHT_NEGATIVE_INTEGER_ERROR_MESSAGE = "Please provide a valid non-negative integer value in the {} parameter"
INSIGHT_ZERO_INTEGER_ERROR_MESSAGE = "Please provide a valid non-zero integer value in the {} parameter"
