# File: mattermost_consts.py
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
MATTERMOST_API_BASE_URL = "{server_url}/api/v4"
MATTERMOST_CONFIG_SERVER_URL = "server_url"
MATTERMOST_CONFIG_VERIFY_SERVER_CERT = "verify_server_cert"
MATTERMOST_CONFIG_CLIENT_ID = "client_id"
MATTERMOST_CONFIG_CLIENT_SECRET = "client_secret"  # pragma: allowlist secret
MATTERMOST_CONFIG_PERSONAL_TOKEN = "personal_token"
MATTERMOST_ACCESS_TOKEN = "access_token"
MATTERMOST_PHANTOM_SYS_INFO_URL = "/system_info"
MATTERMOST_PHANTOM_ASSET_INFO_URL = "/asset/{asset_id}"
MATTERMOST_AUTHORIZE_URL = "{server_url}/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&state={state}"
MATTERMOST_ACCESS_TOKEN_URL = "{server_url}/oauth/access_token"
MATTERMOST_CURRENT_USER_ENDPOINT = "/users/me"
MATTERMOST_USERS_ENDPOINT = "/users"
MATTERMOST_TEAMS_ENDPOINT = "/teams"
MATTERMOST_LIST_CHANNELS_ENDPOINT = "/users/me/teams/{team}/channels"
MATTERMOST_LIST_POSTS_ENDPOINT = "/channels/{channel}/posts"
MATTERMOST_SEND_MSG_ENDPOINT = "/posts"
MATTERMOST_FILES_ENDPOINT = "/files"
MATTERMOST_JSON_TEAM = "team"
MATTERMOST_JSON_CHANNEL = "channel"
MATTERMOST_JSON_MSG = "message"
MATTERMOST_JSON_VAULT_ID = "vault_id"
MATTERMOST_JSON_START_TIME = "start_time"
MATTERMOST_JSON_END_TIME = "end_time"
MATTERMOST_CONST_NOT_FOUND = "Not found"
MATTERMOST_NO_POSTS_FOUND = "No posts found"
MATTERMOST_TEAM_NOT_FOUND_MSG = "Team with given name or ID not found"
MATTERMOST_CHANNEL_NOT_FOUND_MSG = "Channel with given name or ID not found"
MATTERMOST_SEND_MSG_SUCCESS = "Message sent successfully"
MATTERMOST_FILE_UPLOAD_MSG = "Phantom file upload"
MATTERMOST_FILE_UPLOAD_SUCCESS = "File uploaded successfully"
MATTERMOST_VAULT_ID_NOT_FOUND = "Vault ID not found"
MATTERMOST_FILE_UPLOAD_FAILED = "Cannot upload file to the given channel"
MATTERMOST_INVALID_TIME = "Parameter 'start_time' or 'end_time' failed validation"
MATTERMOST_INVALID_TIME_RANGE = "Invalid time range. 'end_time' should be greater than 'start_time'."
MATTERMOST_NEGATIVE_TIME = "Invalid time. Time cannot be negative."
MATTERMOST_TIMESTAMP_VALIDATION_FAILED_MSG = "Incorrect timestamp format, please enter in YYYY-MM-DD or valid ISO 8601 timestamp format."
MATTERMOST_TIMESTAMP_CONVERSION_FAILED_MSG = "Cannot convert given timestamp into valid millisecond epoch"
MATTERMOST_VALID_TIME = "Time validation successful"
MATTERMOST_CONFIG_PARAMS_REQUIRED_CONNECTIVITY = "Either 'personal_token' or 'client_id' and 'client_secret' are required for test connectivity"
MATTERMOST_CONFIG_PARAMS_REQUIRED_MSG = "Please provide 'personal_token' or run test connectivity with 'client_id' and 'client_secret'"
MATTERMOST_BASE_URL_NOT_FOUND_MSG = "Phantom Base URL not found in System Settings. Please specify the value in System Settings."
MATTERMOST_OAUTH_URL_MSG = "Using OAuth URL:"
MATTERMOST_AUTHORIZE_USER_MSG = "Please authorize user in a separate tab using URL"
MATTERMOST_CODE_RECEIVED_MSG = "Code Received"
MATTERMOST_GENERATING_ACCESS_TOKEN_MSG = "Generating access token"
MATTERMOST_MAKING_CONNECTION_MSG = "Connecting to an endpoint"
MATTERMOST_TEST_CONNECTIVITY_FAILED_MSG = "Test connectivity failed"
MATTERMOST_TEST_CONNECTIVITY_PASSED_MSG = "Test connectivity passed"
MATTERMOST_TC_FILE = "oauth_task.out"
MATTERMOST_TC_STATUS_SLEEP = 3
MATTERMOST_AUTHORIZE_WAIT_TIME = 15
