# File: google_threat_intelligence_consts.py
#
# Copyright 2025-2026 Google LLC
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
BASE_URL = "https://www.virustotal.com"

# messages
EXECUTION_START_MSG = "Executing {0} action"
TEST_CONNECTIVITY_START_MSG = "Connecting to {0}"
ON_POLL_START_MSG = "Executing poll for the {0}"
SUCCESS_TEST_CONNECTIVITY = "Test Connectivity Passed"
SUCCESS_ON_POLL = "Poll executed successfully"
ERROR_TEST_CONNECTIVITY = "Test Connectivity Failed"
REQUEST_DEFAULT_TIMEOUT = 30
ACTION_SUCCESS_RESPONSE = "Action {action} has been executed successfully"

ERROR_INVALID_INT_PARAM = "Please provide a valid integer value in the '{key}' parameter"
ERROR_MESSAGE_INVALID_ENTITY = "Please provide a valid entity (IP, URL, File, Domain) in the entity parameter"
ERROR_MESSAGE_INVALID_ENTITY_FILE = "Please provide a valid file hash (Vault ID or SHA256)"
ERROR_MESSAGE_INVALID_ENTITY_DNS = "Please provide a valid entity (IP, Domain) in the entity parameter"
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
INGESTION_START_MESSAGE = "Ingesting the data"
CONTAINER_ERROR_MESSAGE = "Error occurred while saving the container: ID {}: {}"
ARTIFACT_ERROR_MESSAGE = "Error occurred while saving the artifact(s): {}"


# endpoints
SCAN_PRIVATE_URL_ENDPOINT = "/api/v3/private/urls"
ANALYSES_ENDPOINT = "/api/v3/analyses/{id}"
PRIVATE_ANALYSES_ENDPOINT = "/api/v3/private/analyses/{id}"
PRIVATE_FILE_REPUTATION_ENDPOINT = "/api/v3/private/files/{id}"
FILE_REPUTATION_ENDPOINT = "/api/v3/files/{id}"
URL_REPUTATION_ENDPOINT = "/api/v3/urls/{id}"
GET_REPORT_ENDPOINT = "/api/v3/{entity_type}/{entity}"
GET_COMMENT_ENDPOINT = "/api/v3/{entity_type}/{entity}/comments"
GET_FILE_SANDBOX_ENDPOINT = "/api/v3/files/{file_id}/behaviours"
SCAN_PRIVATE_FILE_ENDPOINT = "/api/v3/private/files/upload_url"
GET_A_PRIVATE_ANALYSIS_ENDPOINT = "/api/v3/private/analyses/{id}"
GET_A_PRIVATE_URL_REPORT_ENDPOINT = "/api/v3/private/urls/{url_id}"
GET_CURATED_THREAT_INTELLIGENCE_ENDPOINT = "/api/v3/{entity_type}/{entity}"
GET_RELATIONSHIP_ENDPOINT = "/api/v3/{entity_type}/{entity}/{relationship}"
ADD_COMMENT_ENDPOINT = "/api/v3/{entity_type}/{entity}/comments"
DELETE_COMMENT_ENDPOINT = "/api/v3/comments/{comment_id}"
GET_PASSIVE_DNS_DATA_ENDPOINT = "/api/v3/{entity_type}/{entity}/resolutions"
TEST_CONNECTIVITY_ENDPOINT = "/api/v3/me"
GET_VULNERABILITY_DETAILS_ENDPOINT = "/api/v3/collections/{vulnerability_id}"
GET_PRIVATE_FILE_UPLOAD_URL_ENDPOINT = "/api/v3/private/files/upload_url"
SCAN_URL_ENDPOINT = "/api/v3/urls"
SCAN_FILE_ENDPOINT = "/api/v3/files/upload_url"
VULN_INTEL_LOOKUP_ENDPOINT = "/api/v3/{entity_type}/{entity}/vulnerabilities"
DTM_ON_POLL_ENDPOINT = "/api/v3/dtm/alerts"
ASM_ON_POLL_ENDPOINT = "/api/v3/asm/search/issues"
IOC_ON_POLL_ENDPOINT = "/api/v3/ioc_stream"
UPDATE_DTM_ALERT_STATUS_ENDPOINT = "/api/v3/dtm/alerts/{id}"
UPDATE_ASM_ISSUE_STATUS_ENDPOINT = "/api/v3/asm/issues/{id}/status"

ACTION_ADD_COMMENT_SUCCESS_RESPONSE = "Successfully added comment"
ACTION_DELETE_COMMENT_SUCCESS_RESPONSE = "Successfully deleted comment"
ACTION_GET_COMMENT_SUCCESS_RESPONSE = "Successfully fetched comments"
ACTION_GET_COMMENTS_NOT_FOUND_RESPONSE = "No comments found for entity"
ACTION_GET_CURATED_THREAT_INTELLIGENCE_SUCCESS_RESPONSE = "Successfully fetched relationship data"
ACTION_GET_FILE_SANDBOX_SUCCESS_RESPONSE = "Successfully fetched file sandbox data"
ACTION_GET_PASSIVE_DNS_DATA_SUCCESS_RESPONSE = "Successfully fetched passive dns data"
ACTION_GET_REPORT_SUCCESS_RESPONSE = "Successfully fetched report for entity"
ACTION_GET_VULNERABILITY_DETAILS_SUCCESS_RESPONSE = "Successfully fetched vulnerability details"
ACTION_SCAN_PRIVATE_FILE_SUCCESS_RESPONSE = "Successfully scanned file and retrieved report"
ACTION_SCAN_PRIVATE_URL_SUCCESS_RESPONSE = "Successfully scanned url and retrieved report"
ACTION_UPDATE_DTM_ALERT_STATUS_SUCCESS_RESPONSE = "Successfully updated DTM alert status"
ACTION_UPDATE_ASM_ISSUE_STATUS_SUCCESS_RESPONSE = "Successfully updated ASM issue status"
ACTION_VULN_INTEL_LOOKUP_SUCCESS_RESPONSE = "Successfully fetched vulnerability details for entity"
ACTION_VULN_INTEL_LOOKUP_NOT_FOUND_RESPONSE = "No vulnerability details found for entity"

# Splunk endpoints
SPLUNK_SOAR_GET_CONTAINER_ARTIFACT_ENDPOINT = "{url}/rest/artifact?_filter_container_id={container_id}"
SPLUNK_SOAR_CONTAINER_ENDPOINT = "{url}/rest/container/{container_id}"
SPLUNK_SOAR_ARTIFACT_ENDPOINT = "{url}/rest/artifact/{artifact_id}"

PASS_ERROR_CODE = {
    400: "NotAvailableYet",
    404: "NotFoundError",
    409: "AlreadyExistsError",
}

SEVERITY_MAPPING = {1: "High", 2: "High", 3: "Medium", 4: "Low", 5: "Low"}

# Map status of ASM issue to status of container
ASM_STATUS_MAPPING = {
    "open_new": "open",
    "open_triaged": "open",
    "open_in_progress": "open",
    "closed": "closed",
    "closed_mitigated": "closed",
    "closed_resolved": "closed",
    "closed_duplicate": "closed",
    "closed_out_of_scope": "closed",
    "closed_benign": "closed",
    "closed_risk_accepted": "closed",
    "closed_false_positive": "closed",
    "closed_no_repro": "closed",
    "closed_tracked_externally": "closed",
}

# Map status of DTM alert to status of container
DTM_STATUS_MAPPING = {
    "new": "new",
    "read": "open",
    "escalated": "open",
    "in_progress": "open",
    "closed": "closed",
    "no_action_required": "closed",
    "duplicate": "closed",
    "not_relevant": "closed",
    "tracked_externally": "closed",
}

# For action: update asm issue status
ASM_ACTION_MAPPING = {
    "Open": "open_new",
    "Triaged": "open_triaged",
    "In Progress": "open_in_progress",
    "Closed": "closed",
    "Mitigated": "closed_mitigated",
    "Resolved": "closed_resolved",
    "Duplicate": "closed_duplicate",
    "Out of Scope": "closed_out_of_scope",
    "Benign": "closed_benign",
    "Risk Accepted": "closed_risk_accepted",
    "False Positive": "closed_false_positive",
    "Unable to Reproduce": "closed_no_repro",
    "Tracked Externally": "closed_tracked_externally",
}

# For actinon: update dtm alert status
DTM_ACTION_MAPPING = {
    "New": "new",
    "Read": "read",
    "Escalated": "escalated",
    "In Progress": "in_progress",
    "Closed": "closed",
    "No Action Required": "no_action_required",
    "Duplicate": "duplicate",
    "Not Relevant": "not_relevant",
    "Tracked External": "tracked_external",
}

# For action: scan private url and scan private file
INTERACTION_TIMEOUT_MIN = 60
INTERACTION_TIMEOUT_MAX = 1800

IP_ADDRESS = "ip_addresses"
DOMAIN = "domains"
URL = "urls"
FILE = "files"

RETRY_COUNT = 5
RETRY_COUNT_PRIVATE_FILE_SCAN = 10
