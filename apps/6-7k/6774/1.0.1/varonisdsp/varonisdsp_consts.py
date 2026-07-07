# File: varonisdsp_consts.py
#
# Copyright (c) Varonis, 2023
#
# This unpublished material is proprietary to Varonis DSP. All
# rights reserved. The methods and techniques described herein are
# considered trade secrets and/or confidential. Reproduction or
# distribution, in whole or in part, is forbidden except by express
# written permission of Varonis DSP.
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
VDSP_JSON_BASE_URL_KEY = 'base_url'
VDSP_AUTH_DATA = 'grant_type=client_credentials'
VDSP_ACCESS_TOKEN_KEY = 'access_token'
VDSP_TOKEN_TYPE_KEY = 'token_type'
VDSP_EXPIRES_IN_KEY = 'expires_in'
VDSP_REQUEST_TIMEOUT = 120
VDSP_MAX_USERS_TO_SEARCH = 5
VDSP_MAX_ALERTS = 50
VDSP_MAX_ALERTED_EVENTS = 5000
VDSP_THREAT_MODEL_ENUM_ID = 5821
VDSP_DISPLAY_NAME_KEY = 'DisplayName'
VDSP_SAM_ACCOUNT_NAME_KEY = 'SAMAccountName'
VDSP_EMAIL_KEY = 'Email'
VDSP_GET_ALERTS_ENDPOINT = '/api/alert/alert/GetAlerts'
VDSP_GET_ALERTED_EVENTS_ENDPOINT = '/api/alert/alert/GetAlertedEvents'
VDSP_UPDATE_ALET_STATUS_ENDPOINT = '/api/alert/alert/SetStatusToAlerts'
VDSP_INGEST_PERIOD_KEY = 'ingest_period'
VDSP_INGEST_ARTIFACTS_KEY = 'ingest_artifacts'
VDSP_LAST_FETCH_ID_KEY = 'last_fetch_id'
VDSP_DEFAULT_INGEST_PERIOD = '2 week'
DEFAULT_TIMEOUT = 30
