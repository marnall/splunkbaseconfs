# File: cbdefense_consts.py
#
# Copyright (c) 2018-2025 Splunk Inc.
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
CBD_POLICY_API = "/integrationServices/v3/policy/"
CBD_POLICY_API_DEL = "/integrationServices/v3/policy/{0}"
CBD_POLICY_DELETED = "Policy successfully deleted"
CBD_RULE_DELETED = "Rule successfully deleted"
CBD_ADD_RULE_API = "/integrationServices/v3/policy/{0}/rule"
CBD_DEL_RULE_API = "/integrationServices/v3/policy/{0}/rule/{1}"
CBD_LIST_DEVICE_API = "/appservices/v6/orgs/{0}/devices/_search"
CBD_UPDATE_DEVICE_API = "/appservices/v6/orgs/{0}/device_actions"
CBD_UPDATED_DEVICE_POLICY = "Successfully updated device's policy"
CBD_LIST_PROCESS_GET_JOB_API = "/api/investigate/v2/orgs/{0}/processes/search_jobs"
CBD_LIST_PROCESS_VERIFY_JOB_API = "/api/investigate/v1/orgs/{0}/processes/search_jobs/{1}"
CBD_LIST_PROCESS_RESULT_API = "/api/investigate/v2/orgs/{0}/processes/search_jobs/{1}/results"
CBD_LIST_EVENT_GET_JOB_API = "/api/investigate/v2/orgs/{0}/enriched_events/search_jobs"
CBD_EVENT_JOB_DETAILS_API = "/api/investigate/v2/orgs/{1}/enriched_events/{2}/{0}"
CBD_EVENT_JOB_SEARCH_API = "/api/investigate/v1/orgs/{1}/enriched_events/{2}/{0}"
CBD_EVENT_JOB_RESULT_API = "/api/investigate/v2/orgs/{1}/enriched_events/{2}/{0}/results"
CBD_GET_ALERT_API = "/appservices/v6/orgs/{1}/alerts/{0}"
CBD_GET_EVENT_API = "/api/investigate/v2/orgs/{0}/enriched_events/detail_jobs"
CBD_SEARCH_ALERT_API = "/appservices/v6/orgs/{0}/alerts/_search"
CBD_DEFAULT_REQUEST_TIMEOUT = 30  # in seconds
CBD_STATE_FILE_CORRUPT_ERROR = (
    "Error occurred while loading the state file due to its unexpected format. "
    "Resetting the state file with the default format. Please try again"
)
ERROR_CODE_EXCEPTION = "Error code unavailable"
CBD_JSON_FORMAT_ERROR = "Please provide data in correct json format"
ERROR_MSG_EXCEPTION = "Unknown error occurred. Please check the asset configuration and|or action parameters."
EXCEPTION_OCCURRED = "Exception occurred: "
CBD_EMPTY_RESPONSE_NO_HEADER = "Empty response and no information in the header"
CBD_ERROR_TEXT = "Cannot parse error details"
CBD_SIEM_ERROR = "The asset configuration parameters siem_key and siem_connector_id are required to run this action."
CBD_CUSTOM_API_ERROR = "The asset configuration parameters custom_api_key and custom_api_connector_id are required to run this action."
CBD_ORG_KEY_ERROR = "The asset configuration parameter org_key is required to run this action."
CBD_API_ERROR = "The asset configuration parameters api_key and api_connector_id are required to run this action."
CBD_COMPLETED_NOT_EQ_CONTACTED = ", process still not completed so results may vary. please re-try after sometime."
CBD_NOTIFICATION_API = "/integrationServices/v3/notification"
CBD_POLICY_UPDATED_SUCCESS = "Policy updated successfully"
CBD_POLICY_RETRIEVED_SUCCESS = "Policy retrieved successfully"
CBD_REQUIRED_FIELD_MSG = "Add at least value in one of the following fields: event_type, ip, host name, hash, application, owner"
CBD_REQUIRED_FIELD_MSG_PROCESS = "Add at least value in one of the following fields: ip, host name, owner"
INVALID_INT = "Please provide a valid integer value in the {param}"
ERROR_NEGATIVE_INT_PARAM = "Please provide a valid non-negative integer value in the {param}"
NON_ZERO_ERROR = "Please provide non-zero positive integer in {param}"
TEST_CONNECTIVITY_FAILED = "Test Connectivity Failed"
TEST_CONNECTIVITY_PASSED = "Test Connectivity Passed"
