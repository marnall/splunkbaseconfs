# File: junipersrx_consts.py
#
# Copyright (c) 2016-2025 Splunk Inc.
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
JUNIPERSRX_SUCC_TEST_CONNECTIVITY_PASSED = "Test connectivity passed"
JUNIPERSRX_ERR_TEST_CONNECTIVITY_FAILED = "Test connectivity failed"
JUNIPERSRX_ERR_DEVICE_CONNECTIVITY = "Error in connecting to device"
JUNIPERSRX_ERR_PARSE_POLICY_DATA = "Unable to parse security policy config"
JUNIPERSRX_ERR_NO_POLICY_ENTRIES_FOUND = "Could not find any security policies to update"
JUNIPERSRX_ERR_NO_ALLOW_POLICY_ENTRIES_FOUND = "Did not find any policies with a 'permit' action. Need atleast one such policy."
JUNIPERSRX_ERR_CONFIG_VALIDATION_FAILED = "Config validation failed"
JUNIPERSRX_ERR_CONFIG_LOAD_FAILED = "Config load failed"
JUNIPERSRX_ERR_CONFIG_COMMIT_FAILED = "Config commit failed"
JUNIPERSRX_ERR_QUERY_ADDR_BOOK_FAILED = "Failed to get address book details"
JUNIPERSRX_ERR_REPLY_FORMAT_KEY_MISSING = "'{key}' missing in reply from device"
JUNIPERSRX_ERR_PARSE_RESPONSE = "Unable to parse response from device"
JUNIPERSRX_ERR_EMPTY_RESPONSE = "Got empty response from device"
JUNIPERSRX_ERR_COMMAND_EXEC = "Command exec on device failed"
JUNIPERSRX_SUCC_ADDRESS_NOT_FOUND = "Address not found in set, ignoring action"
JUNIPERSRX_SUCC_APP_NOT_FOUND = "Application not found in set, ignoring action"

JUNIPERSRX_MSG_ADDING_POLICY = "Adding/Updating policy"
JUNIPERSRX_MSG_REMOVING_POLICY = "Removing/Updating policy"
JUNIPERSRX_MSG_MOVING_POLICY = "Moving Policy to the proper location"

JUNIPERSRX_JSON_APPLICATION = "application"
JUNIPERSRX_JSON_IP = "ip"
JUNIPERSRX_JSON_TOTAL_APPLICATIONS = "total_applications"
JUNIPERSRX_JSON_FROM_ZONE = "from_zone"
JUNIPERSRX_JSON_TO_ZONE = "to_zone"

# Constants
JUNIPERSRX_ADDRESS_BOOK = "global"  # Just use the global address book, anything other than that needs to be attached to a zone
JUNIPERSRX_ADDRESS_SET = "phantom-addr-set"
JUNIPERSRX_ADDRESS_POLICY = "phantom-block-addr-policy"
JUNIPERSRX_APP_SET = "phantom-app-set"
JUNIPERSRX_APP_POLICY = "phantom-block-app-policy"
DEFAULT_TIMEOUT = 100
DEFAULT_PORT = "22"
