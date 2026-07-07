# File: netwitness_consts.py
#
# Copyright (c) 2017-2024 Splunk Inc.
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
NETWITNESS_ERR_BAD_RANGE = "Session ID parameter has a bad range - smaller number should come first"
NETWITNESS_ERR_BAD_PARAMS = "This action requires a session ID, query, or start and end times"
NETWITNESS_ERR_REVERSE_TIMES = "Given time range is invalid - times appear to be reversed"
NETWITNESS_ERR_VAULT_INFO = "Unable to get Vault item details from Phantom. Details: {0}"
NETWITNESS_ERR_FROM_SERVER = "API failed\nStatus code: {status}\nDetail: {detail}"
NETWITNESS_ERR_TIMEOUT = "Request timed out. Try limiting the scope of the search"
NETWITNESS_ERR_BAD_CAP = "Found no capture data based on the given parameters"
NETWITNESS_ERR_NOT_IN_VAULT = "Specified vault ID not found in vault"
NETWITNESS_ERR_API_UNSUPPORTED_METHOD = "Unsupported method {method}"
NETWITNESS_ERR_SERVER_CONNECTION = "Connection failed"
NETWITNESS_ERR_VAULT = "Could not move file to vault"

NETWITNESS_GET_PCAPS_FAIL = "Response from server was incorrect data type"
NETWITNESS_CONNECTION_TEST_MSG = "Querying endpoint to test connectivity"
NETWITNESS_REPORT_ALREADY_AVAILABLE = "Report already available in vault"
NETWITNESS_CAP_TYPE_DICT = {"log": "application/json", "pcap": "pcap"}
NETWITNESS_SUCC_FILE_ADD_TO_VAULT = "Successfully added file to Vault"
NETWITNESS_SUCC_UPLOAD = "Feed/Parser file successfully uploaded"
NETWITNESS_SUCC_RESTART = "Device successfully restarted"
NETWITNESS_FILE_TYPE_DICT = {"pcap": "pcap", "log": "json"}
NETWITNESS_INVALID_PARAM = "Invalid parameters: {message}"
NETWITNESS_EXCEPTION_OCCURRED = "Exception occurred"
NETWITNESS_FILE_ERR = "Error while creating file"
NETWITNESS_ENDPOINT_GET_CAP = "/sdk/packets"

NETWITNESS_REST_RESP_UNAUTHORIZED_MSG = "Invalid username or password"
NETWITNESS_REST_RESP_RESOURCE_NOT_FOUND_MSG = "No data found"
NETWITNESS_REST_RESP_OTHER_ERR_MSG = "Unknown error occurred"
NETWITNESS_REST_RESP_BAD_REQUEST_MSG = "Bad Request"
NETWITNESS_REST_RESP_RESOURCE_NOT_FOUND = 404
NETWITNESS_REST_RESP_UNAUTHORIZED = 401
NETWITNESS_REST_RESP_BAD_REQUEST = 400
NETWITNESS_REST_RESP_SUCC = 200

NETWITNESS_TEST_CONNECTIVITY_PASS = "Connectivity test succeeded"
NETWITNESS_TEST_CONNECTIVITY_FAIL = "Connectivity test failed"

NETWITNESS_CONFIG_VERIFY = "verify_server_cert"
NETWITNESS_CONFIG_API_USERNAME = "username"
NETWITNESS_CONFIG_API_PASSWORD = "password"  # pragma: allowlist secret
NETWITNESS_CONFIG_SERVER = "url"

NETWITNESS_JSON_START_TIME = "start_time"
NETWITNESS_JSON_SESSION_ID = "session_ids"
NETWITNESS_JSON_FILE_NAME = "file_name"
NETWITNESS_JSON_END_TIME = "end_time"
NETWITNESS_JSON_QUERY = "query"

NETWITNESS_DEFAULT_REST_TIMEOUT = 300
NETWITNESS_DEFAULT_TEST_TIMEOUT = 30

NETWITNESS_CAP_TYPE_PACKET = "pcap"
NETWITNESS_CAP_TYPE_LOG = "log"

NETWITNESS_BAD_CAP_HASHES = [
    "2d59f05b63bda3d74db5685834e137911c7279f282f0d595ac465fd3b97e348f",  # pragma: allowlist secret
    "8eba672603c531f466c75ca729b66378b92271d78ef1570574757cd5fd8244e6",  # pragma: allowlist secret
]

# Updating bad CAP sizes for Python 3 support
NETWITNESS_BAD_CAP_SIZES = [73, 37]

# Constants relating to '_get_error_message_from_exception'
NETWITNESS_ERR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
