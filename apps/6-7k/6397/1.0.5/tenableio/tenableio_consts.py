# File: tenableio_consts.py
#
# Copyright (c) 2022-2025 Splunk Inc.
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

TENABLE_IO_CONFIG_ACCESS_KEY = "access_key"  # pragma: allowlist secret
TENABLE_IO_CONFIG_SECRET_KEY = "secret_key"  # pragma: allowlist secret

TENABLE_IO_ACTION_ID_TEST_CONNECTIVITY = "test_connectivity"
TENABLE_IO_ACTION_ID_LIST_SCANS = "list_scans"
TENABLE_IO_ACTION_ID_LIST_SCANNERS = "list_scanners"
TENABLE_IO_ACTION_ID_LIST_POLICIES = "list_policies"
TENABLE_IO_ACTION_ID_SCAN_HOST = "scan_host"
TENABLE_IO_ACTION_ID_DELETE_SCAN = "delete_scan"

TENABLE_IO_PARAM_FOLDER_ID = "folder_id"
TENABLE_IO_PARAM_LAST_MODIFIED = "last_modified"
TENABLE_IO_PARAM_TARGET_TO_SCAN = "target_to_scan"
TENABLE_IO_PARAM_POLICY_ID = "policy_id"
TENABLE_IO_PARAM_SCAN_NAME = "scan_name"
TENABLE_IO_PARAM_SCAN_TIMEOUT = "scan_timeout"
TENABLE_IO_PARAM_SCAN_ID = "scan_id"
TENABLE_IO_PARAM_SCANNER_ID = "scanner_id"

TENABLE_IO_MESSAGE_INVALID_VALUE = "Invalid value specified for {}. Value must be between {} and {}."
TENABLE_IO_MESSAGE_BAD_ASSET_CONFIG = "Please provide values for Access Key and Secret Key in asset configuration"
TENABLE_IO_MESSAGE_CREATING_CLIENT = "Creating tenable.io client"
TENABLE_IO_MESSAGE_FAILED_TO_CREATE_CLIENT = "Could not create tenable.io client"
TENABLE_IO_MESSAGE_CONNECTING_TO_ENDPOINT = "Connecting to endpoint"
TENABLE_IO_MESSAGE_TEST_CONNECTIVITY_PASSED = "Test Connectivity Passed"
TENABLE_IO_MESSAGE_TEST_CONNECTIVITY_FAILED = "Test Connectivity Failed."
TENABLE_IO_MESSAGE_LIST_POLICIES_FAILED = "List Policies Failed."
TENABLE_IO_MESSAGE_LIST_SCANS_FAILED = "List Scans Failed."
TENABLE_IO_MESSAGE_INVALID_DATETIME = "Invalid datetime parameter"
TENABLE_IO_MESSAGE_LIST_SCANNERS_FAILED = "List Scanners Failed."
TENABLE_IO_MESSAGE_CREATING_SCAN = "Creating scan against: {}"
TENABLE_IO_MESSAGE_LAUNCHING_SCAN = "Launching scan against {} using {}"
TENABLE_IO_MESSAGE_WAITING_FOR_SCAN = "Waiting for scan to complete. Current status: {}"
TENABLE_IO_MESSAGE_SCAN_DID_NOT_COMPLETE = "Scan was not successful within {} seconds. Last status: {}."
TENABLE_IO_MESSAGE_SCAN_RESPONSE_IS_EMPTY = "Response is empty. Please check the input parameters."
TENABLE_IO_MESSAGE_SCAN_COMPLETED = "Scan completed"
TENABLE_IO_MESSAGE_GETTING_SCAN_DETAILS = "Getting details for scan {} using scan instance {}"
TENABLE_IO_MESSAGE_SCAN_ENDPOINT_FAILED = "Scan Endpoint Failed"
TENABLE_IO_MESSAGE_DELETE_SCAN_COMPLETED = "Delete Scan completed"
TENABLE_IO_MESSAGE_DELETE_SCAN_FAILED = "Delete Scan Failed."

TENABLE_IO_OUTPUT_SCAN_ID = TENABLE_IO_PARAM_SCAN_ID
TENABLE_IO_OUTPUT_SCAN_COUNT = "scan_count"
TENABLE_IO_OUTPUT_SCANNER_COUNT = "scanner_count"
TENABLE_IO_OUTPUT_POLICY_COUNT = "policy_count"
TENABLE_IO_OUTPUT_TOTAL_VULNS = "total_vulns"
TENABLE_IO_OUTPUT_DELETE_STATUS = "delete_status"

# See https://developer.tenable.com/docs/scan-status-tio
TENABLE_IO_SCAN_STATUS_COMPLETE = "completed"
TENABLE_IO_TERMINAL_SCAN_STATUS = ["aborted", "canceled", "completed", "stopped"]
TENABLE_IO_VULNERABILITY_SEVERITIES_FOR_SUMMARY = ["low", "medium", "high", "critical"]

TENABLE_IO_DEFAULT_SCAN_NAME = "Scan Launched from Splunk SOAR"
TENABLE_IO_DEFAULT_SCAN_STATUS_RATE_LIMITING_TIMEOUT = 120  # in seconds
TENABLE_IO_DEFAULT_SCAN_RUNNING_TIMEOUT = 3600  # in seconds
TENABLE_IO_DEFAULT_SCAN_STATUS_POLLING_INTERVAL = 60  # in seconds
TENABLE_IO_DEFAULT_REQUEST_TIMEOUT = 60  # in seconds

TENABLE_IO_MIN_PARAM_SCAN_TIMEOUT = 0  # in seconds
TENABLE_IO_MAX_PARAM_SCAN_TIMEOUT = 4 * TENABLE_IO_DEFAULT_SCAN_RUNNING_TIMEOUT  # in seconds

TENABLE_IO_MAX_ERROR_MESSAGE_LENGTH = 900  # SOAR UI doesn't properly display the beginning of long lines
