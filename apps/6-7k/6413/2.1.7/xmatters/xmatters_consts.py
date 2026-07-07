# File: xmatters_consts.py
# Copyright (c) 2017-2025 Splunk Inc.
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
PHANTOM_ERR_CODE_UNAVAILABLE = "Error code unavailable"
PHANTOM_ERR_MSG_UNAVAILABLE = "Unknown error occurred. Please check the asset configuration and|or action parameters."

XM_EXCEPTION_CAUGHT = "Exception caught: {0}"

XM_CONFIG_USERNAME = "username"
XM_CONFIG_PASSWORD = "password"  # pragma: allowlist secret
XM_CONFIG_BASE_URL = "base_url"
XM_CONFIG_CLIENT_ID = "client_id"

XM_ENDPOINT_TEST_CONNECTIVITY = "/api/xm/1/events?limit=1"
XM_ENDPOINT_LIST_EVENTS = "/api/xm/1/events"
XM_ENDPOINT_TRIGGER_EVENT = "/reapi/2015-04-01/forms/{0}/triggers"
XM_ENDPOINT_GET_EVENT = "/api/xm/1/events/{0}"
XM_ENDPOINT_UPDATE_EVENT = "/api/xm/1/events"
XM_ENDPOINT_LIST_PEOPLE = "/api/xm/1/people"
XM_ENDPOINT_GET_PEOPLE = "/api/xm/1/people/{0}"
XM_ENDPOINT_LIST_GROUPS = "/api/xm/1//groups"
XM_ENDPOINT_GET_ONCALL = "/api/xm/1//on-call"

XM_SUCCESS_TEST_CONNECTIVITY = "Test Connectivity Passed"
XM_LIST_EVENTS_SUCCESS = "Events retrieved successfully"
XM_LIST_GROUPS_SUCCESS = "Groups retrieved successfully"
XM_CREATE_EVENT_SUCCESS = "Event created successfully"
XM_GET_EVENT_SUCCESS = "Successfully retrieved event"
XM_WHO_IS_ONCALL_SUCCESS = "Successfully retrieved who is on call"
XM_UPDATE_EVENT_SUCCESS = "Successfully updated event"
XM_LIST_PEOPLE_SUCCESS = "Users retrieved successfully"
XM_GET_PERSON_SUCCESS = "Successfully retrieved user"
XM_WHO_IS_ONCALL_TIME_FAILURE = "Please provide both from and to value for timeframe"
XM_WHO_IS_ONCALL_FAILURE = "No shift found for the given input parameters"
XM_WHO_IS_ONCALL_INVALID_MEM_FAILURE = "Please provide a valid integer from 1 to 100 in members_per_shift"

XM_ERR_TOKEN_REQUEST = "Error in token request"
XM_ERR_PARSE_ACCESS_TOKEN = "Unable to parse access token"
XM_ERR_AUTHORIZE_OAUTH_TOKEN = "Unable to authorize with OAuth token"
XM_ERR_INVALID_JSON_PARAMS = "Unable to parse parameter '{0}' to json: {1}"

XM_ERR_TEST_CONNECTIVITY_FAILURE = "Test Connectivity Failed"
XMATTERS_DEFAULT_REQUEST_TIMEOUT = 30  # in seconds
