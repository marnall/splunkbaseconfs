# File: microsoftintune_consts.py
#
# Copyright (c) Splunk, 2023-2025
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

MSADGRAPH_API_URLS = {
    "Global": "https://graph.microsoft.com/v1.0",
    "US Gov L4": "https://graph.microsoft.us",
    "US Gov L5 (DOD)": "https://dod-graph.microsoft.us",
    "Germany": "https://graph.microsoft.de",
    "China (21Vianet)": "https://microsoftgraph.chinacloudapi.cn",
}

MS_AZURE_CONFIG_TENANT = "tenant_id"
MS_AZURE_CONFIG_CLIENT_ID = "client_id"
MS_AZURE_CONFIG_CLIENT_SECRET = "client_secret"  # pragma: allowlist secret
MS_AZURE_CONFIG_ADMIN_ACCESS_REQUIRED = "admin_access_required"
MS_AZURE_CONFIG_ADMIN_ACCESS_GRANTED = "admin_access_granted"
MS_AZURE_URL = "region"
MS_AZURE_TOKEN_STRING = "token"
MS_AZURE_ACCESS_TOKEN_STRING = "access_token"
MS_AZURE_REFRESH_TOKEN_STRING = "refresh_token"

MS_AZURE_BASE_URL_NOT_FOUND_MESSAGE = "SOAR Base URL not found in System Settings. Please specify this value in System Settings."
MS_AZURE_HTML_ERROR = "Bad Request Bad Request - Invalid URL HTTP Error 400. The request URL is invalid."
MS_AZURE_NEXT_LINK_STRING = "odata.nextLink"
MS_AZURE_PAGE_SIZE = 999
MS_AZURE_ERROR_MESSAGE_UNKNOWN = "Unknown error occurred. Please check the asset configuration and|or action parameters."

# status codes
MS_AZURE_BAD_REQUEST_CODE = 400
MS_AZURE_NOT_FOUND_CODE = 404

# For authorization code
SERVER_TOKEN_URL = "https://login.microsoftonline.com/{0}/oauth2/v2.0/token"
MS_AZURE_ADMIN_CONSENT_URL = "https://login.microsoftonline.com/{tenant_id}/adminconsent"
MS_AZURE_AUTHORIZE_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
AUTH_FAILURE_MESSAGES = (
    "token is invalid",
    "token has expired",
    "ExpiredAuthenticationToken",
    "AuthenticationFailed",
    "TokenExpired",
    "InvalidAuthenticationToken",
)
MS_REST_URL_NOT_AVAILABLE_MESSAGE = "Rest URL not available. Error: {error}"
MS_OAUTH_URL_MESSAGE = "Using OAuth URL:\n"

MS_GENERATING_ACCESS_TOKEN_MESSAGE = "Generating access token"
MS_TC_STATUS_SLEEP = 3
MS_AZURE_WAIT_FOR_URL_SLEEP = 5
MS_AZURE_CODE_GENERATION_SCOPE = "offline_access DeviceManagementManagedDevices.Read.All DeviceManagementManagedDevices.ReadWrite.All"
MS_AZURE_AUTHORIZE_TROUBLESHOOT_MESSAGE = (
    "If authorization URL fails to communicate with your SOAR instance, check whether you have:  "
    " 1. Specified the Web Redirect URL of your App -- The Redirect URL should be <POST URL>/result . "
    " 2. Configured the base URL of your SOAR Instance at Administration -> Company Settings -> Info"
)

MS_AZURE_TEST_CONNECTIVITY_FAILURE_MESSAGE = "Test Connectivity Failed"
MS_AZURE_TEST_CONNECTIVITY_PASSED = "Test Connectivity Passed"
MS_AZURE_ENCRYPTION_ERROR = "Error occurred while encrypting the state file"
MS_AZURE_DECRYPTION_ERROR = "Error occurred while decrypting the state file"
MS_AZURE_STATE_FILE_CORRUPT_ERROR = (
    "Error occurred while loading the state file due to it's unexpected format. "
    "Resetting the state file with the default format. Please test the connectivity."
)
MS_AZURE_RESPONSE_ERROR_MESSAGE = "Error from server. Status Code: {status_code}. Data from server: \n{error_text}\n"
MS_AZURE_PROCESS_RESPONSE_ERROR_MESSAGE = "Can't process response from server. Status Code: {status_code} Data from server: {content}"
MS_ADMIN_CONSENT_ERROR_MESSAGE = "Admin consent not received"
MS_AUTHORIZATION_ERROR_MESSAGE = "Authorization code not received or not given"
MS_STATE_FILE_ERROR_MESSAGE = "Unable to load state file"

DEFAULT_TIMEOUT = 30
