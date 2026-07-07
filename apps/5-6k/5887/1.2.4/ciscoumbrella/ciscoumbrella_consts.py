# File: ciscoumbrella_consts.py
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
CISCOUMB_JSON_DOMAIN = "domain"
CISCOUMB_JSON_CUSTKEY = "customer_key"
CISCOUMB_JSON_PAGE_INDEX = "page_index"
CISCOUMB_JSON_DOMAIN_LIMIT = "limit"
CISCOUMB_JSON_TOTAL_DOMAINS = "total_domains"
CISCOUMB_JSON_DISABLE_SAFEGUARDS = "disable_safeguards"
CISCOUMB_LIST_UPDATED_WITH_GUID = "REST API returned success with id: {id}"

CISCOUMB_ERR_CONNECTIVITY_TEST = "Test Connectivity Failed"
CISCOUMB_SUCC_CONNECTIVITY_TEST = "Test Connectivity Passed"
CISCOUMB_ERR_SERVER_CONNECTION = "Connection failed"
CISCOUMB_ERR_FROM_SERVER = "API failed, Status code: {status}, Message: {message}"
CISCOUMB_MSG_GET_DOMAIN_LIST_TEST = "Querying a single domain entry to check credentials"

CISCOUMB_USING_BASE_URL = "Using url: {base_url}"

CISCOUMB_REST_API_URL = "https://s-platform.api.opendns.com"
CISCOUMB_REST_API_VER = "1.0"
CISCOUMB_DEFAULT_PAGE_INDEX = 1
CISCOUMB_DEFAULT_DOMAIN_LIMIT = 200
CISCOUMB_DEFAULT_TIMEOUT = 60  # in seconds
CISCOUMB_DEFAULT_NUMBER_OF_RETRIES = 3
CISCOUMB_DEFAULT_RETRY_WAIT_TIME = 60  # in seconds

# Constants relating to 'validate_integer'
CISCOUMB_VALID_INT_MSG = "Please provide a valid integer value in the {param} parameter"
CISCOUMB_NON_NEG_NON_ZERO_INT_MSG = "Please provide a valid non-zero positive integer value in the {param} parameter"
CISCOUMB_NON_NEG_INT_MSG = "Please provide a valid non-negative integer value in the {param} parameter"
