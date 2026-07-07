# File: sophosendpointprotection_consts.py
#
# Copyright (c) 2021-2025 Splunk Inc.
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
SOPHOS_CLIENT_ID = "client_id"
SOPHOS_CLIENT_SECRET = "client_secret"  # pragma: allowlist secret

SOPHOS_JWT_JSON = "jwt_json"
SOPHOS_JWT_TOKEN = "access_token"

SOPHOS_PT_JSON = "pt_json"
SOPHOS_PT_API_HOSTS = "apiHosts"
SOPHOS_PT_DATA_REGION_URL = "dataRegion"
SOPHOS_PT_GLOBAL_URL = "global"
SOPHOS_PT_TOKEN = "id"

SOPHOS_PARAMS_VIEW = ["basic", "summary", "full"]
SOPHOS_PARAM_SEARCHFIELDS = ["hostname", "groupName", "associatedPersonName", "ipAddresses"]
SOPHOS_PARAMS_ITEMSTYPE = ["blocked", "allowed"]
SOPHOS_PARAMS_PROPTYPE = ["path", "sha256", "certificateSigner"]
SOPHOS_PARAMS_ENDPOINTTYPE = ["computer", "server", "securityVm"]
SOPHOS_PARAMS_ENDPOINTHEALTH = ["bad", "good", "suspicious", "unknown"]
SOPHOS_PARAMS_ENDPOINTLOCKDOWN = [
    "creatingWhitelist",
    "installing",
    "locked",
    "notInstalled",
    "registering",
    "starting",
    "stopping",
    "unavailable",
    "uninstalled",
    "unlocked",
]

# Endpoints
JWT_TOKEN_ENDPOINT = "https://id.sophos.com/api/v2/oauth2/token"
WHOAMI_ENDPOINT = "https://api.central.sophos.com/whoami/v1"

ENDPOINTS_ENDPOINT = "/endpoint/v1/endpoints"
ENDPOINTS_SETTINGS = "/endpoint/v1/settings"
TAMPER_PROTECTION_ENDPOINT = ENDPOINTS_ENDPOINT + "/{}/tamper-protection"
ISOLATION_ENDPOINT = ENDPOINTS_ENDPOINT + "/isolation"
ISOLATION_INDIVIDUAL_ENDPOINT = ENDPOINTS_ENDPOINT + "/{}/isolation"
SCAN_ENDPOINT = ENDPOINTS_ENDPOINT + "/{}/scans"
UPDATE_CHECK_ENDPOINT = ENDPOINTS_ENDPOINT + "/{}/update-checks"
LIST_ITEMS = ENDPOINTS_SETTINGS + "/{}-items"
DELETE_ITEM = ENDPOINTS_SETTINGS + "/{type}-items/{id}"
LIST_SITES = ENDPOINTS_SETTINGS + "/web-control/local-sites"
DELETE_SITE = ENDPOINTS_SETTINGS + "/web-control/local-sites/{id}"

# Messages
SOPHOS_PARAMS_NOTFOUND_ERR = "Error - Required parameter '{name}' not found"
SOPHOS_PARAMS_INVALID_ERR = "Error - Parameter '{name}' is invalid. Please check specs for valid values."
SOPHOS_OKAY_MESSAGE = "Endpoint hit correctly. Returning data if possible"
