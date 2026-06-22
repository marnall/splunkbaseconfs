# File: infoblox_consts.py
#
# Copyright 2025 Infoblox Inc.
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

# base_url
BASE_URL = "https://csp.infoblox.com"

# messages
EXECUTION_START_MSG = "Executing {0} action"
TEST_CONNECTIVITY_START_MSG = "Connecting to {0}"
SUCCESS_TEST_CONNECTIVITY = "Test Connectivity Passed"
ERROR_TEST_CONNECTIVITY = "Test Connectivity Failed"
REQUEST_DEFAULT_TIMEOUT = 60
ACTION_SUCCESS_RESPONSE = "Action {action} has been executed successfully"
INFOBLOX_ON_POLL_START_MSG = "Starting Infoblox on_poll action"

ERROR_INVALID_INT_PARAM = "Please provide a valid integer value in the '{key}' parameter"
ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
EMPTY_RESPONSE_STATUS_CODES = [200, 204]
ERROR_INVALID_SELECTION = "Invalid '{0}' selected. Must be one of: {1}."
ERROR_GENERAL_MESSAGE = "Status code: {0}, Data from server: {1}"
ERROR_HTML_RESPONSE = "Error parsing html response"
ERROR_ZERO_INT_PARAM = "Please provide a non-zero positive integer value in the '{key}' parameter"
ERROR_NEG_INT_PARAM = "Please provide a positive integer value in the '{key}' parameter"
ERROR_INVALID_JSON_PARAM = "Please provide a valid JSON value for the '{key}' parameter"
ERROR_INVALID_LIST_PARAM = "Please provide a valid list value for the '{key}' parameter"
ERROR_INVALID_BOOL_PARAM = "Please provide a valid boolean value for the '{key}' parameter"
ERROR_MISSING_REQUIRED_PARAM = "'{key}' is required parameter"
ERROR_INVALID_INT_RANGE = "Please provide a valid integer value in the '{key}' parameter between {min_value} and {max_value}"
ERROR_INSIGHT_NOT_FOUND = "Insight ID does not exist."
ERROR_INVALID_DATETIME_FORMAT = "Please provide datetime in the format 'YYYY-MM-DDTHH:mm:ss.SSS' for the '{key}' parameter"
ERROR_NAMED_LIST_NOT_FOUND = "Custom List does not exist"
ERROR_NAME_WITHOUT_TYPE = "When querying by name, both 'name' and 'type' parameters must be provided"

ACTION_EMPTY_RESPONSE = "Empty response from server"
ACTION_CREATE_NETWORK_LIST_INVALID_RESPONSE = "Network list creation failed: unexpected response format. Response: {response}"
ACTION_UPDATE_NETWORK_LIST_INVALID_RESPONSE = "Network list update failed: unexpected response format. Response: {response}"
ACTION_GET_NETWORK_LIST_EMPTY_RESPONSE = "No network lists found matching the criteria"
ACTION_INDICATOR_INTEL_LOOKUP_ERROR = "Error initiating indicator intel lookup: {error}"
ACTION_INDICATOR_INTEL_LOOKUP_RESULT_IN_PROGRESS = "Job ID: {job_id} is still in progress. Please try again later."
ACTION_INDICATOR_INTEL_LOOKUP_RESULT_FAILED = "Job ID: {job_id} failed with status: {status}"
ACTION_INDICATOR_INTEL_LOOKUP_RESULT_UNKNOWN = "Job ID: {job_id} is in state: {state} with status: {status}"
ACTION_INDICATOR_THREAT_LOOKUP_NO_RESULTS = "No threat intelligence records found matching the criteria"
ACTION_INDICATOR_THREAT_LOOKUP_ERROR = "Error retrieving threat intelligence: {error}"
ACTION_INDICATOR_INTEL_LOOKUP_RESULT_ERROR = "Error retrieving intel lookup results: {error}"
ACTION_DNS_SECURITY_EVENTS_EMPTY = "No DNS security events found matching the criteria"
ACTION_DNS_SECURITY_EVENTS_ERROR = "Error retrieving DNS security events: {error}"

# endpoints
TEST_CONNECTIVITY_ENDPOINT = "/api/authn/v1/account"
NETWORK_LIST_ENDPOINT = "/api/atcfw/v1/network_lists"
NETWORK_LIST_DETAIL_ENDPOINT = "/api/atcfw/v1/network_lists/{}"
IPAM_ADDRESS_ENDPOINT = "/api/ddi/v1/ipam/address"
INDICATOR_INTEL_LOOKUP_JOBS_ENDPOINT = "/tide/api/services/intel/lookup/jobs"
NAMED_LIST_ENDPOINT = "/api/atcfw/v1/named_lists"
TIDE_THREAT_ENDPOINT = "/tide/api/data/threats"
DNS_RECORD_ENDPOINT = "/api/ddi/v1/dns/record"
SOC_INSIGHTS_ENDPOINT = "/api/v1/insights"
INDICATOR_INTEL_LOOKUP_ENDPOINT = "/tide/api/services/intel/lookup/indicator"
SOC_INSIGHTS_COMMENTS_ENDPOINT = "/api/v1/insights/{}/comments"
DNS_SECURITY_EVENTS_ENDPOINT = "/api/dnsdata/v2/dns_event"
SOC_INSIGHTS_EVENTS_ENDPOINT = "/api/v1/insights/{}/events"
IPAM_HOST_ENDPOINT = "/api/ddi/v1/ipam/host"
DHCP_LEASE_ENDPOINT = "/api/ddi/v1/dhcp/lease"
SECURITY_POLICY_ENDPOINT = "/api/atcfw/v1/security_policies"
SOC_INSIGHTS_INDICATORS_ENDPOINT = "/api/v1/insights/{}/indicators"

# success messages
ACTION_TEST_CONNECTIVITY_SUCCESS_RESPONSE = "Successfully connected to Infoblox"
REMOVE_NETWORK_LIST_SUCCESS_MSG = "Successfully removed network list with ID: {}"
ACTION_GET_NETWORK_LIST_SUCCESS_RESPONSE = "Successfully retrieved {count} network lists"
ACTION_UPDATE_NETWORK_LIST_SUCCESS_RESPONSE = "Successfully updated network list '{name}' with ID: {id}"
ACTION_CREATE_NETWORK_LIST_SUCCESS_RESPONSE = "Successfully created network list '{name}' with ID: {id}"
ACTION_IP_ASSET_DATA_LOOKUP_SUCCESS_RESPONSE = "Successfully retrieved {0} IP asset record(s)"
ACTION_GET_NAMED_LIST_SUCCESS_SINGLE = "Successfully retrieved custom list"
ACTION_GET_NAMED_LIST_SUCCESS_MULTIPLE = "Successfully retrieved {0} custom list(s)"
ACTION_GET_NAMED_LIST_START_MSG = "Retrieving custom lists from Infoblox"
ACTION_CREATE_NETWORK_LIST_EMPTY_RESPONSE = "Empty response from server"
ACTION_REMOVE_NAMED_LIST_SUCCESS = "Successfully removed custom list with ID: {0}"
ACTION_INDICATOR_INTEL_LOOKUP_RESULT_SUCCESS_RESPONSE = "Successfully retrieved {count} results for job ID: {job_id}"
ACTION_INDICATOR_THREAT_LOOKUP_SUCCESS_RESPONSE = "Successfully retrieved {count} threat intelligence records"
ACTION_HOST_ASSET_DATA_LOOKUP_SUCCESS_RESPONSE = "Successfully retrieved {count} host asset records"
ACTION_DNS_RECORD_LOOKUP_SUCCESS_RESPONSE = "Successfully retrieved {count} DNS records"
ACTION_GET_SOC_INSIGHTS_COMMENTS_SUCCESS_RESPONSE = "Successfully retrieved {count} comments for the insight"
SUCCESS_GET_INSIGHTS_ASSETS_MULTIPLE = "Successfully retrieved {0} insight asset(s)"
SUCCESS_GET_INSIGHTS_ASSETS_SINGLE = "Successfully retrieved insight asset"
SUCCESS_GET_INSIGHTS_EVENTS = "Successfully retrieved {0} insight event(s)"
ACTION_INDICATOR_INTEL_LOOKUP_SUCCESS_INITIATED = "Successfully initiated indicator intel lookup with job ID: {job_id}, status: {status}"
ACTION_INDICATOR_INTEL_LOOKUP_SUCCESS_WITH_RESULTS = "Successfully retrieved {count} results for job ID: {job_id}"
SUCCESS_GET_INSIGHTS_COMMENTS = "Successfully retrieved insights comments"

ACTION_GET_INSIGHTS_INDICATORS_SUCCESS_RESPONSE = "Successfully retrieved {0} insight indicator(s)"
ACTION_DHCP_LEASE_LOOKUP_SUCCESS_RESPONSE = "Successfully retrieved {count} DHCP lease data"
ACTION_CREATE_NAMED_LIST_SUCCESS_RESPONSE = "Successfully created custom list"
ACTION_UPDATE_NAMED_LIST_SUCCESS_RESPONSE = "Successfully updated custom list"
ACTION_REMOVE_SECURITY_POLICY_SUCCESS_RESPONSE = "Successfully removed security policy with ID: {0}"
ACTION_GET_SECURITY_POLICY_SUCCESS_RESPONSE = "Successfully retrieved {count} security policies"
ACTION_CREATE_SECURITY_POLICY_SUCCESS_RESPONSE = "Successfully created security policy '{0}' with ID: {1}"
ACTION_UPDATE_SECURITY_POLICY_SUCCESS_RESPONSE = "Successfully updated security policy '{name}' with ID: {id}"
ACTION_UPDATE_NAMED_LIST_ITEMS_SUCCESS_RESPONSE = "Successfully {0} {1} items to/from custom list with ID: {2}"
ACTION_DNS_SECURITY_EVENTS_SUCCESS = "Successfully retrieved {count} DNS security events"

ACTION_SOC_INSIGHTS_SUCCESS = "Successfully retrieved {count} SOC insights for polling"
ACTION_SOC_INSIGHTS_CONTAINERS_CREATED = "Successfully created {count} containers from SOC insights"
ACTION_SOC_INSIGHTS_EMPTY = "No SOC Insights data found for the specified time period"

# On-poll specific messages
INFOBLOX_SOC_INSIGHTS_POLL_START = "Starting SOC insights polling"
INFOBLOX_SOC_INSIGHTS_POLL_FINISH = "SOC insights polling completed"
INFOBLOX_DNS_EVENTS_POLL_START = "Starting DNS security events polling"
INFOBLOX_DNS_EVENTS_POLL_FINISH = "DNS security events polling completed"

# Container and artifact messages
CONTAINER_CREATED_MSG = "Created container for insight: {insight_id}"
CONTAINER_UPDATED_MSG = "Updated container for insight: {insight_id}"
ARTIFACT_CREATED_MSG = "Created artifact for insight: {insight_id}"

# Named List Types
NAMED_LIST_TYPES = {
    "custom_list": "custom_list",
    "security_category": "security_category",
    "threat_intelligence": "threat_intelligence",
}

# SOC Insights specific constants
SOC_INSIGHTS_CONTAINER_SOURCE_ID_KEY = "infoblox_insight_id"

# Phantom severity mapping for SOC insights
PHANTOM_SEVERITY_MAP = {"LOW": "low", "INFO": "low", "MEDIUM": "medium", "HIGH": "high", "CRITICAL": "high"}

# Default limits
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000

# Address states for validation
VALID_ADDRESS_STATES = ["Free", "Used", "Any"]

# Severity mapping for DNS Security Events
SEVERITY_MAPPING = {"LOW": "low", "INFO": "low", "MEDIUM": "medium", "HIGH": "high"}
