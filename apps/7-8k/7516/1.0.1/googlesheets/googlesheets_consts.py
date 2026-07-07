# File: googlesheets_consts.py

# Copyright (c) Splunk, 2024

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

# Define your constants here
SERVICE_CREATION_ERROR = "Couldn't create {0}, version {1} service"
SERVICE_PARAM_MISSING_ERROR = "Required parameters are missing!"
SERVICE_SUCCESS = "{0} Service Created Successfully!"
IAM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
DRIVE_AUTH_SCOPE = "https://www.googleapis.com/auth/drive"
PROJECT_NAME_PATH = "projects/-/serviceAccounts/"
TEST_CONNECTIVITY_FAILED = "Test Connectivity Failed."
TEST_CONNECTIVITY_PASSED = "Test Connectivity Passed."

INVALID_ROW_DATA = "Could not parse the row data to list of lists"
INVALID_EMAIL = "Invalid email provided: {0}"
SPREADSHEET_CREATE_FAILED = "Could not create Spreadsheet {0}"
SPREADSHEET_CREATE_SUCCESS = "Spreadsheet successfully created with ID: {0}"
ADD_ROWS_ERROR = "Could not add rows to sheet {0}"
ADD_ROWS_SUCCESS = "{0} rows successfully added to sheet."
