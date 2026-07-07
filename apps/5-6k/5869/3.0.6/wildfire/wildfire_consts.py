# File: wildfire_consts.py
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
WILDFIRE_JSON_BASE_URL = "base_url"
WILDFIRE_JSON_TASK_ID = "task_id"
WILDFIRE_JSON_API_KEY = "api_key"  # pragma: allowlist secret
WILDFIRE_JSON_MALWARE = "malware"
WILDFIRE_JSON_TASK_ID = "id"
WILDFIRE_JSON_URL = "url"
WILDFIRE_JSON_HASH = "hash"
WILDFIRE_JSON_PLATFORM = "platform"
WILDFIRE_JSON_POLL_TIMEOUT_MINS = "timeout"

WILDFIRE_ERR_UNABLE_TO_PARSE_REPLY = "Unable to parse reply from device"
WILDFIRE_ERR_REPLY_FORMAT_KEY_MISSING = "None '{key}' missing in reply from device"
WILDFIRE_ERR_REPLY_NOT_SUCC = "REST call returned '{status}'"
WILDFIRE_SUCC_REST_CALL_SUCC = "REST Api call succeeded"
WILDFIRE_ERR_REST_API = "REST Api Call returned error, status_code: {status_code}, detail: {detail}"
WILDFIRE_ERR_FILE_NOT_FOUND_IN_VAULT = "File not found in vault"
WILDFIRE_INVALID_INT = "Please provide a valid integer value in the {param}"
WILDFIRE_ERR_INVALID_PARAM = "Please provide a non-zero positive integer in the {param}"
WILDFIRE_ERR_NEGATIVE_INT_PARAM = "Please provide a valid non-negative integer value in the {param}"

WILDFIRE_TEST_PDF_FILE = "wildfire_test_connectivity.pdf"
WILDFIRE_SLEEP_SECS = 10
WILDFIRE_MESSAGE_REPORT_PENDING = "Report Pending"
WILDFIRE_MESSAGE_MAX_POLLS_REACHED = (
    "Reached max polling attempts. Please use the MD5 or Sha256 of the file as a parameter to <b>get report</b> to query the report status."
)

WILDFIRE_TIMEOUT = "'timeout' action parameter"

# in minutes
WILDFIRE_MAX_TIMEOUT_DEF = 10
