# File: beyondtrust_consts.py
#
# Copyright (c) 2025-2026 Splunk Inc.
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

# API endpoints
API_OAUTH2_ENDPOINT = "oauth2/token"
API_VERSION = "/api/config/v1/"
API_GET_ALL_ACCOUNTS = f"{API_VERSION}api-account"
API_GET_USERS = f"{API_VERSION}user"
API_GET_USER_MEMBERSHIP = API_VERSION + "user/{userid}/group-policies"
API_UPDATE_USER = API_VERSION + "user/{userid}"

BT_TOKEN_STRING = "token"
BT_ACCESS_TOKEN_STRING = "access_token"

BT_PAGE_SIZE = 100
BT_MAX_INACTIVITY_DAYS = 90
# Use X-BT-Pagination Headers or Link Header to paginate
BT_USE_X_BT_PAGINATION_HEADERS = True
BT_EP_REST_RESPONSE = "response"
BT_EP_REST_RESPONSE_HEADERS = "headers"
BT_PAGINATION_CURRENT = "X-BT-Pagination-Current-Page"
BT_PAGINATION_LAST = "X-BT-Pagination-Last-Page"
BT_RATE_LIMIT_REMAINING = "X-RateLimit-Remaining"

# Success messages
BT_GENERATING_ACCESS_TOKEN_MESSAGE = "Generating access token"

# Error messages
BT_ERR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters."
BT_RESPONSE_ERROR_MESSAGE = "Error from server. Status Code: {status_code}. Data from server: \n{error_text}\n"
BT_ERR_MSG_NEXT_PAGE = "Unknown Link header format: next page not found"
BT_RATE_LIMIT_ERR_MSG = "API calls rate limit reached. Please wait and retry later."

AUTH_FAILURE_MESSAGES = (
    "access_denied",
    "token is invalid",
    "token has expired",
    "ExpiredAuthenticationToken",
    "AuthenticationFailed",
    "TokenExpired",
    "InvalidAuthenticationToken",
)
