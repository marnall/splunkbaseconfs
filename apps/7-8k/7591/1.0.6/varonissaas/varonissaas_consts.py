# File: varonissaas_consts.py
#
# Copyright (c) Varonis, 2024-2025
#
# This unpublished material is proprietary to Varonis SaaS. All
# rights reserved. The methods and techniques described herein are
# considered trade secrets and/or confidential. Reproduction or
# distribution, in whole or in part, is forbidden except by express
# written permission of Varonis SaaS.
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

# Define your constants here
VDSP_JSON_BASE_URL_KEY = "base_url"
VDSP_AUTH_DATA = "grant_type=client_credentials"
VDSP_SCRT = "api_key"
VDSP_ACCESS_TOKEN_KEY = "access_token"
VDSP_TOKEN_TYPE_KEY = "token_type"
VDSP_EXPIRES_IN_KEY = "expires_in"
VDSP_REQUEST_TIMEOUT = 120
VDSP_MAX_USERS_TO_SEARCH = 5
VDSP_MAX_ALERTS = 50
VDSP_MAX_ALERTED_EVENTS = 5000
VDSP_THREAT_MODEL_ENUM_ID = 5821
VDSP_DISPLAY_NAME_KEY = "DisplayName"
VDSP_SAM_ACCOUNT_NAME_KEY = "SAMAccountName"
VDSP_EMAIL_KEY = "Email"
VDSP_AUTH_ENDPOINT = "/api/authentication/api_keys/token"
VDSP_TEST_CONNECTION_ENDPOINT = "/auth/configuration"
VDSP_SEARCH_ENDPOINT = "/app/dataquery/api/search/v2/search"
VDSP_SEARCH_RESULT_ENDPOINT = "/app/dataquery/api/search"
VDSP_UPDATE_ALET_STATUS_ENDPOINT = "/api/alert/alert/SetStatusToAlerts"
VDSP_INGEST_PERIOD_KEY = "ingest_period"
VDSP_INGEST_ARTIFACTS_FLAG = "ingest_artifacts"
VDSP_LAST_FETCH_TIME = "last_fetch_time"
VDSP_DEFAULT_INGEST_PERIOD = "2 week"
VDSP_ALERT_SEVERITY_KEY = "severity"
VDSP_ALERT_STATUS_KEY = "alert_status"
VDSP_THREAT_MODEL_KEY = "threat_model"
VDSP_DEFAULT_TIMEOUT = 30
VDSP_MAX_DAYS_BACK = 180
