# File: fireamp_consts.py
#
# Copyright (c) 2016-2025 Splunk Inc.
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
AMP_JSON_API_CLIENT_ID = "api_client_id"
AMP_JSON_API_KEY = "api_key"  # pragma: allowlist secret
AMP_JSON_BASE_URL = "base_url"
AMP_JSON_HASH = "hash"
AMP_JSON_IP = "ip"
AMP_JSON_URL = "url"
AMP_JSON_LIST_GUID = "file_list_guid"
AMP_JSON_CONNECTOR_GUID = "connector_guid"
AMP_JSON_QUERY = "query"
AMP_ENDPOINT_NOT_FOUND = "Specified endpoint not found"
AMP_FILE_LIST_NOT_FOUND = "Specified file list not found"
AMP_FILE_UNBLOCK_NOT_FOUND = "File not found in specified list. Verify list and file."
AMP_FILE_HASH_ADDED = "Hash added to list"
AMP_FILE_HASH_REMOVED = "Hash removed from list"
AMP_DUPLICATE_FILE_HASH = "Hash already in list"
AMP_ISOLATION_SUCCESS = ["pending_start", "pending_stop"]
AMP_FIND_DEVICE_ERR_MSG = "Must provide at least one of the following: group_name, group_guid, hostname, external_ip, internal_ip"
AMP_ISOLATION_FAIL = []

BASE_URL = "https://api.amp.sourcefire.com/"
