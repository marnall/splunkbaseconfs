# File: mobileiron_consts.py
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
MOBILEIRON_DEFAULT_TIMEOUT = 30
MOBILEIRON_JSON_DEVICE_URL = "url"
MOBILEIRON_JSON_USERNAME = "username"
MOBILEIRON_JSON_PASSSWORD = "password"
MOBILEIRON_JSON_START_INDEX = "start_index"
MOBILEIRON_JSON_LIMIT = "limit"
MOBILEIRON_JSON_TOTAL_DEVICES = "total_devices"
MOBILEIRON_JSON_UUID = "uuid"
MOBILEIRON_JSON_REASON = "reason"

MOBILEIRON_ERR_INVALID_UUID = "Input device uuid not proper format"
MOBILEIRON_ERR_CONNECTIVITY_TEST = "Connectivity test failed"
MOBILEIRON_SUCC_CONNECTIVITY_TEST = "Connectivity test passed"
MOBILEIRON_ERR_SERVER_CONNECTION = "Connection failed"
MOBILEIRON_ERR_FROM_SERVER = "API failed, Status code: {status}, Detail: {detail}"
MOBILEIRON_MSG_GET_DEVICES_TEST = "Querying devices to check credentials"
MOBILEIRON_ERR_JSON_PARSE = "Unable to parse response as JSON, response '{data}'"
MOBILEIRON_USING_BASE_URL = "Using url: {base_url}"
MOBILEIRON_ERR_INVALID_INPUT = "Invalid '{param}' input value"
