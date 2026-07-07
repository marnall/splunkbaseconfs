# File: lastline_consts.py
#
# Copyright (c) 2015-2023 Splunk Inc.
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
RESULT_REPORT_KEY = "report"
TASK_ID_KEY = 'id'
TARGET_KEY = 'target'
RESULTS_URL_KEY = 'result_url'
ANALYSIS_TYPE_FILE = 'file'
ANALYSIS_TYPE_URL = 'url'
SUMMARY_TYPE_KEY = 'type'
ANALYSIS_KEY = 'analysis'
URL_ANALYSIS_ENDED_KEY = 'analysis_ended'
FILE_ANALYSIS_END_KEY = 'analysis_end'
ANALYSIS_SUBJECT_KEY = 'analysis_subjects'

VAULT_ERROR_INVALID_VAULT_ID = "Invalid Vault ID"
VAULT_ERROR_FILE_NOT_FOUND = "Vault file could not be found with supplied Vault ID"
VAULT_ARTIFACTS_TOTAL_KEY = 'artifacts_total'
VAULT_ARTIFACTS_STORED_KEY = 'artifacts_stored'
VAULT_ARTIFACTS_FAILED_KEY = 'artifacts_failed'

LASTLINE_GENERATED_RANDOM_HASH = "Generated Random hash '{gen_hash}' to query"
LASTLINE_SUCCESS_CONNECTIVITY_TEST = "Test Connectivity Passed"
LASTLINE_ERROR_CONNECTIVITY_TEST = "Test Connectivity Failed"
LASTLINE_ERROR_GETTING_REPORT = "Error getting report"
LASTLINE_ERROR_SUBMIT_URL = "Error submitting URL"
LASTLINE_ERROR_TASK_ID_NOT_FOUND = "Task ID not found"

LASTLINE_SLEEP_SECS = 10
LASTLINE_DEFAULT_TIMEOUT = 30
LASTLINE_JSON_POLL_TIMEOUT_SECS = "timeout"
LASTLINE_MAX_TIMEOUT_DEF_SECS = 120
LASTLINE_POLL_TIMEOUT = "Polled for the maximum number of times"
LASTLINE_POLL_TIMEOUT += " Report not yet ready. Please try 'get report' action with id: {0} later"
