# File: cylance_consts.py
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
CYLANCE_JSON_USERNAME = "username"
CYLANCE_JSON_PASSWORD = "password"  # pragma: allowlist secret
CYLANCE_JSON_REGION_CODE = "region_code"

CYLANCE_JSON_TENANT_ID = "tenant_id"
CYLANCE_JSON_APPLICATION_ID = "application_id"
CYLANCE_JSON_APPLICATION_SECRET = "application_secret"  # pragma: allowlist secret

CYLANCE_REGION_CODES = {
    "Asia-Pacific - North": "-apne1",
    "Asia-Pacific - Southeast": "-au",
    "Europe - Central": "-euc1",
    "Government": ".us",
    "North America": "",
    "South America": "-sae1",
}

CYLANCE_AUTH_TOKEN_ERR = "Could not generate an auth token"
CYLANCE_ACCESS_TOKEN_ERR = "Could not generate an access token"

CYLANCE_BLOCK_HASH_SUCC = "Successfully blocked hash"
CYLANCE_UNBLOCK_HASH_SUCC = "Successfully unblocked hash"
CYLANCE_BLOCK_HASH_ALREADY_BLOCKED_SUCC = "Hash is already blocked"
CYLANCE_UNBLOCK_HASH_ALREADY_UNBLOCKED_SUCC = "Hash is already unblocked"
CYLANCE_UPDATE_ZONE_SUCC = "Successfully updated zone"
CYLANCE_ERR_INVALID_PARAM = "Please provide a non-zero positive integer in {param}"

DEFAULT_MAX_RESULTS = 200
