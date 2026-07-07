# File: vectrandr_consts.py
#
# Copyright (c) Vectra, 2024-2025
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

VECTRA_API_VERSION = "/api/v2.5"
VECTRA_API_2_2_VERSION = "/api/v2.2"
VECTRA_TEST_CONNECTIVITY_ENDPOINT = "/hosts"
VECTRA_ENTITY_ENDPOINT = "/{entity_type}/{entity_id}"
VECTRA_POLL_ENTITY_ENDPOINT = "/{entity_type}"
VECTRA_DESCRIBE_DETECTIONS_ENDPOINT = "/detections/{detection_id}"
VECTRA_DETECTIONS_ENDPOINT = "/detections"
VECTRA_SEARCH_DETECTIONS_ENDPOINT = "/search/detections"
VECTRA_DOWNLOAD_PCAP_ENDPOINT = "/detections/{detection_id}/pcap"
VECTRA_ADD_NOTE_ENDPOINT = "/{object_type}/{object_id}/notes"
VECTRA_UPDATE_REMOVE_NOTE_ENDPOINT = "/{entity_type}/{entity_id}/notes/{note_id}"
VECTRA_ADD_REMOVE_TAGS_ENDPOINT = "/tagging/{entity_type}/{entity_id}"
VECTRA_ADD_ASSIGNMENT_ENDPOINT = "/assignments"
VECTRA_UPDATE_ASSIGNMENT_ENDPOINT = "/assignments/{assignment_id}"
VECTRA_RESOLVE_ASSIGNMENT_ENDPOINT = "/assignments/{assignment_id}/resolve"
VECTRA_OUTCOMES_ENDPOINT = "/assignment_outcomes"
SPLUNK_SOAR_CREATE_SEVERITY_ENDPOINT = "{url}rest/severity"
SPLUNK_SOAR_GET_CONTAINER_ARTIFACT_ENDPOINT = "{url}rest/artifact?_filter_container_id={container_id}"
SPLUNK_SOAR_ARTIFACT_ENDPOINT = "{url}rest/artifact/{artifact_id}"

VECTRA_EMPTY_RESPONSE_STATUS_CODE = [200, 201, 204]
VECTRA_ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
VECTRA_SUCCESS_TEST_CONNECTIVITY = "Test Connectivity Passed"
VECTRA_ERROR_TEST_CONNECTIVITY = "Test Connectivity Failed"
VECTRA_ERROR_JSON_RESPONSE = "Error message: {0}"
VECTRA_ERROR_GENERAL_HTML_MESSAGE = "Error from server. Status code: {0}, Reason: {1}, Error message: {2}"
VECTRA_ERROR_REST_CALL = "Error connecting to server. Details: {0}"
VECTRA_ERROR_INVALID_ENTITY = "Invalid entity"
VECTRA_ERROR_INVALID_DROPDOWN_VALUE = "Please provide a valid dropdown value in the '{key}' parameter"
VECTRA_ERROR_EMPTY_RESPONSE = "Status code: {}. Empty response and no information available"
VECTRA_ERROR_NEGATIVE_INT_PARAM = "Please provide a valid non-negative integer value in the '{key}' parameter"
VECTRA_ERROR_ZERO_INT_PARAM = "Please provide a non-zero positive integer value in the '{key}' parameter"
VECTRA_ERROR_INVALID_INT_PARAM = "Please provide a valid integer value in the '{key}' parameter"
VECTRA_ERROR_GENERAL_MESSAGE = "Status code: {}, Data from server: {}"
VECTRA_ERROR_HTML_RESPONSE = "Error parsing html response"
VECTRA_UTC_SINCE_TIME_ERROR = "Please provide time in the span of UTC time since Unix epoch 1970-01-01T00:00:00Z."
VECTRA_GREATER_EQUAL_TIME_ERROR = "Invalid {0}, can not be greater than or equal to current UTC time"
VECTRA_ERROR_MAX_INT_PARAM = "Please provide a valid integer value upto {max_value} in the '{key}' parameter"
VECTRA_VALID_ENTITIES = ["host", "account"]
ENTITY_TYPE_MAPPING = {"host": "hosts", "account": "accounts", "detection": "detections"}
VECTRA_DETECTION_CATEGORIES_MAPPING = {
    "Command and Control": "command",
    "Botnet": "botnet",
    "Reconnaissance": "reconnaissance",
    "Lateral Movement": "lateral",
    "Exfiltration": "exfiltration",
    "Info": "info",
    "All": "All",
}
VECTRA_CEF_TYPES = {
    "entity": {"id": ["entity id"], "type": ["entity type"]},
    "detection": {"id": ["detection id"], "type": ["detection type"], "category": ["detection category"]},
    "assignment": {"id": ["assignment id"]},
}

DEFAULT_SEVERITY = ["high", "medium", "low", "critical"]
VECTRA_SEVERITY = [
    {"color": "red", "name": "critical"},
    {"color": "orange", "name": "high"},
    {"color": "yellow", "name": "medium"},
    {"color": "dark_grey", "name": "low"},
]

VECTRA_LAST_DETECTION_TIMESTAMP_IN_STATE = "last_detection_timestamp"
VECTRA_LAST_DETECTION_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

VECTRA_WAIT_TIME_FOR_RETRY = 30
VECTRA_NO_OF_RETRIES = 3
VECTRA_REQUEST_TIMEOUT = 240
VECTRA_DEFAULT_MAX_ALLOWED_CONTAINERS = 100
VERIFY_SERVER_CERT_FAIL = False
