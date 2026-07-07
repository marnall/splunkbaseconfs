# File: vectraxdr_consts.py
#
# Copyright (c) Vectra, 2023-2025
#
# This unpublished material is proprietary to Vectra.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Vectra.
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

VECTRA_SUCCESS_TEST_CONNECTIVITY = "Test Connectivity Passed"
VECTRA_ERROR_TEST_CONNECTIVITY = "Test Connectivity Failed"
VECTRA_API_VERSION = "/api/v3.3"

VECTRA_ENDPOINT_TOKEN = "/oauth2/token"
VECTRA_GET_ASSIGNMENTS = "/assignments"
VECTRA_ADD_ASSIGNMENT = "/assignments"
VECTRA_UPDATE_ASSIGNMENT = "/assignments/{assignment_id}"
VECTRA_RESOLVE_ASSIGNMENT = "/assignments/{assignment_id}/resolve"
VECTRA_ASSIGNMENT_OUTCOMES = "/assignment_outcomes"
VECTRA_DETECTIONS_ENDPOINT = "/detections"
VECTRA_DESCRIBE_DETECTIONS_ENDPOINT = "/detections/{detection_id}"
VECTRA_DESCRIBE_ENTITY = "/entities/{entity_id}"
VECTRA_LIST_ENTITIES = "/entities"
VECTRA_TAG_ENDPOINT = "/tagging/entity/{entity_id}"
VECTRA_NOTES_ENDPOINT = "/entities/{entity_id}/notes"
VECTRA_NOTES_UPDATE_ENDPOINT = "/entities/{entity_id}/notes/{note_id}"
VECTRA_PCAP_ENDPOINT = "/detections/{detection_id}/pcap"
VECTRA_CONTAINER_ENDPOINT = "/rest/container"
VECTRA_ARTIFACT_ENDPOINT = "rest/artifact"

VECTRA_REQUEST_TIMEOUT = 240
VECTRA_ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
VECTRA_ERROR_JSON_RESPONSE = "Unable to parse JSON response. Error: {}"
VECTRA_ERROR_REST_CALL = "Error connecting to server. Details: {}"
VECTRA_ERROR_EMPTY_RESPONSE = "Status code: {}. Empty response and no information available"
VECTRA_ERROR_HTML_RESPONSE = "Error parsing html response"
VECTRA_ERROR_GENERAL_MESSAGE = "Status code: {}, Data from server: {}"
VECTRA_ERROR_GENERAL_HTML_MESSAGE = "Status code: {}, Error Details: {}, Data from server: {}"

VECTRA_STATE_TOKEN = "token"
VECTRA_STATE_ACCESS_TOKEN = "access_token"
VECTRA_STATE_REFRESH_TOKEN = "refresh_token"
VECTRA_STATE_CLIENT_ID = "client_id"

VECTRA_EMPTY_RESPONSE_STATUS_CODE = [200, 201, 204]
VECTRA_VALID_ENTITIES = ["account", "host"]

VECTRA_ERROR_INVALID_INT_PARAM = "Please provide a valid integer value in the '{key}' parameter"
VECTRA_ERROR_NEGATIVE_INT_PARAM = "Please provide a valid non-negative integer value in the '{key}' parameter"
VECTRA_ERROR_ZERO_INT_PARAM = "Please provide a non-zero positive integer value in the '{key}' parameter"
VECTRA_ERROR_INVALID_ENTITY = f"Invalid entity type has been provided. Please provide valid entity type value from {VECTRA_VALID_ENTITIES}"

VECTRA_WAIT_TIME_FOR_RETRY = 30
VECTRA_NO_OF_RETRIES = 3

VECTRA_REFRESH_TOKEN_EXPIRE_MESSAGE = "Please try reauthenticating using API client credentials"
VECTRA_REFRESH_TOKEN_INVALID_MESSAGE = "Invalid refresh token. Please reauthenticate using client credentials and try again."
VECTRA_ACCESS_TOKEN_EXPIRE_MESSAGE = "Unauthorized"

ON_POLL_ENTITY_TYPE_MAPPING = {"host": "hosts", "account": "accounts"}

VECTRA_LAST_MODIFIED_TIMESTAMP_IN_STATE = "last_modified_timestamp"
VECTRA_LAST_MODIFIED_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


VECTRA_UTC_SINCE_TIME_ERROR = "Please provide time in the span of UTC time since Unix epoch 1970-01-01T00:00:00Z."
VECTRA_GREATER_EQUAL_TIME_ERROR = "Invalid {0}, can not be greater than or equal to current UTC time"
VECTRA_CONFIG_TIME_POLL_NOW = "'Time range for POLL NOW' or 'Start Time for Schedule/Manual POLL' asset configuration parameter"


VECTRA_VALID_PRIORITIZED_LIST = ["true", "false", "all"]
VECTRA_VALID_ENTITY_TYPES = ["account", "host", "all"]

VECTRA_DETECTION_CATEGORIES_MAPPING = {
    "Command and Control": "command_and_control",
    "Botnet": "botnet",
    "Reconnaissance": "reconnaissance",
    "Lateral Movement": "lateral_movement",
    "Exfiltration": "exfiltration",
    "Info": "info",
    "All": "All",
}

VECTRA_CEF_TYPES = {
    "entity": {"id": ["entity id"], "type": ["entity type"]},
    "detection": {"id": ["detection id"], "type": ["detection type"], "category": ["detection category"]},
    "assignment": {"id": ["assignment id"]},
}
VECTRA_INVALID_SEVERITY = "Please check severity values"

VECTRA_DEFAULT_URGENCY_SCORE = 50
VECTRA_DEFAULT_URGENCY_SCORE_LOW_THRESHOLD = 30
VECTRA_DEFAULT_URGENCY_SCORE_MEDIUM_THRESHOLD = 50
VECTRA_DEFAULT_MAX_ALLOWED_CONTAINERS = 100
