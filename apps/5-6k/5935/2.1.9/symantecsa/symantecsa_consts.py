# File: symantecsa_consts.py
#
# Copyright (c) 2019-2025 Splunk Inc.
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
PHANTOM_ERROR_CODE_UNAVAILABLE = "Error code unavailable"
PHANTOM_ERROR_MESSAGE_UNAVAILABLE = "Unknown error occurred. Please check the asset configuration and|or action parameters."

# Config variables
SYMANTECSA_CONFIG_USERNAME = "username"
SYMANTECSA_CONFIG_API_KEY = "api_key"  # pragma: allowlist secret
SYMANTECSA_CONFIG_DEVICE_IP = "device_ip"

# Action params for get packet details
SYMANTECSA_ACTION_PARAM_START_TIME = "start_time"
SYMANTECSA_ACTION_PARAM_END_TIME = "end_time"
SYMANTECSA_ACTION_PARAM_FILENAME = "filename"
SYMANTECSA_ACTION_PARAM_FILTER = "filter"

# Endpoints
SYMANTECSA_ENDPOINT_GET_PACKET_DETAILS = "/pcap/download/deepsee"
SYMANTECSA_ENDPOINT_BASE_URI = "/api/v6/"
SYMANTECSA_ENDPOINT_TEST_CONNECTIVITY = "/api/v6/list"

SYMANTECSA_API_VERSION = "6"

# Action Result Messages
SYMANTECSA_GET_PCAP_SUCCESS = "PCAP file written to vault successfully"
SYMANTECSA_TEST_CONNECTIVITY_SUCCESS = "Test Connectivity Passed"

# PCAP file download location
SYMANTECSA_PCAP_FILE_DOWNLOAD_LOCATION = "/vault/tmp/{NAME}.pcap"

# No packets file data
SYMANTECSA_EMPTY_FILE = (
    "\n\r\r\n4\x00\x00\x00M<+\x1a\x01\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\x02\x00\x10\x00"
    "Solera Networks\x00\x00\x00\x00\x004\x00\x00\x00\x01\x00\x00\x00\x14\x00\x00\x00\x01\x00\x00"
    "\x00\x00$\x00\x00\x14\x00\x00\x00"
)

# Test Connectivity Errors
SYMANTECSA_TEST_CONNECTIVITY_ERROR = "Error connecting to Symantec Security Analytics. Please check your credentials and try again"
SYMANTECSA_TEST_CONNECTIVITY_FAILED = "Test Connectivity Failed"
SYMANTECSA_TIME_FORMAT_ERROR = "Please provide time in '%Y-%m-%dT%H:%M:%S' format"
SYMANTECSA_TIME_RANGE_ERROR = "The given time range is incorrect"
SYMANTECSA_FILTER_ERROR = "The given filter query is incorrect"
SYMANTECSA_TEST_CONNECTIVITY_START = "Querying Symantec Security Analytics using the base url {base_url}"
SYMANTECSA_NO_DATA_FOUND_MESSAGE = "No packets found"
SYMANTECSA_GET_PCAP_INVALID_INPUT = "Result Code: {}. Error: {} Please provide valid input(s)"
SYMANTECSA_GET_PCAP_PATH_NOT_FOUND = "Unable to find download path"
VAULT_UNABLE_TO_ADD_FILE = "Unable to add file to the vault. Error: {}"

SYMANTECSA_DEFAULT_REQUEST_TIMEOUT = 60  # in seconds
