# File: databricks_consts.py
#
# Copyright (c) 2024-2026 Splunk Inc.
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
#

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

MISSING_AUTHENTICATION_ERROR_MESSAGE = "Either username/password or an authentication token must be specified in the app configuration"

TEST_CONNECTIVITY_SUCCESS_MESSAGE = "Test connectivity passed"
TEST_CONNECTIVITY_ERROR_MESSAGE = "Test connectivity failed"
TEST_CONNECTIVITY_PROGRESS_MESSAGE = "Connecting to Databricks host"
TEST_CONNECTIVITY_FILE_PATH = "dbfs:/"

CREATE_ALERT_SUCCESS_MESSAGE = "Successfully created alert"
CREATE_ALERT_ERROR_MESSAGE = "Alert creation failed"
DELETE_ALERT_SUCCESS_MESSAGE = "Successfully deleted alert"
DELETE_ALERT_ERROR_MESSAGE = "Alert deletion failed"
LIST_ALERTS_SUCCESS_MESSAGE = "Successfully listed alerts"
LIST_ALERTS_ERROR_MESSAGE = "List alerts failed"
LIST_CLUSTERS_SUCCESS_MESSAGE = "Successfully listed clusters"
LIST_CLUSTERS_ERROR_MESSAGE = "List clusters failed"
LIST_WAREHOUSES_SUCCESS_MESSAGE = "Successfully listed warehouses"
LIST_WAREHOUSES_ERROR_MESSAGE = "List warehouses failed"
PERFORM_QUERY_SUCCESS_MESSAGE = "Successfully performed SQL query"
PERFORM_QUERY_ERROR_MESSAGE = "Failed to perform SQL query"

EXECUTE_NOTEBOOK_SUCCESS_MESSAGE = "Successfully executed notebook"
EXECUTE_NOTEBOOK_ERROR_MESSAGE = "Failed to execute notebook"

GET_JOB_RUN_SUCCESS_MESSAGE = "Successfully retrieved job run"
GET_JOB_RUN_ERROR_MESSAGE = "Failed to retrieve job run"

GET_JOB_OUTPUT_SUCCESS_MESSAGE = "Successfully retrieved job run output"
GET_JOB_OUTPUT_ERROR_MESSAGE = "Failed to retrieve job run output"

GET_QUERY_STATUS_SUCCESS_MESSAGE = "Successfully retrieved query status"
GET_QUERY_STATUS_ERROR_MESSAGE = "Failed to retrieve query status"

CANCEL_QUERY_SUCCESS_MESSAGE = "Successfully submitted query cancellation request"
CANCEL_QUERY_ERROR_MESSAGE = "Failed to submit query cancellation request"

DATABRICKS_ERROR_MESSAGE_UNAVAILABLE = "Unavailable. Please check the asset configuration and|or the action parameters."

UNHANDLED_ACTION_ID_ERROR_MESSAGE = "Action ID {} does not have a code handler."
