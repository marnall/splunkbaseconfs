# File: proofpointsoarapp_consts.py
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

TOKENIZATION_ERR_MSG = "Problem with tokenization during action execution. {}"

TOKEN_URL = "https://auth.proofpoint.com/v1/token"
BEARER_STRING = "Bearer {}"

SAFE_LIST_ENTRIES_ENDPOINT = "/api/v1/emailProtection/modules/spam/orgSafeList"
BLOCK_LIST_ENTRIES_ENDPOINT = "/api/v1/emailProtection/modules/spam/orgBlockList"
