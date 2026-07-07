# File: abnormalsecurity_consts.py
#
# Copyright (c) 2022-2025 Splunk Inc.
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

# Config parameters
ABNORMAL_JSON_URL_OAuth = "url"
ABNORMAL_AUTHORIZATION_TOKEN = "access_token"

# responses
ABNORMAL_ERR_EMPTY_RESPONSE = "Status Code {code}. Empty response and no information in the header"
ABNORMAL_ERR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
ABNORMAL_INVALID_INTEGER_MSG = "Please provide a valid integer value in the {key} parameter"
REQUEST_TIMEOUT = 60

# endpoints
ABNORMAL_GET_THREATS = "/threats"
ABNORMAL_GET_ABUSE_MAILBOX = "/abusecampaigns"
ABNORMAL_GET_ACTION_STATUS = "actions"
