# File: hackertarget_consts.py
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
#
#
# HACKERTARGET_ERR_API_INITIALIZATION = "API Initialization failed"
ERR_CONNECTIVITY_TEST = "Connectivity test failed"
SUCC_CONNECTIVITY_TEST = "Connectivity test passed"
ERR_404_MSG = "Requested resource not found"
ERR_SERVER_CONNECTION = "Connection failed"
ERR_FROM_SERVER = "API failed, Status code: {status}, Detail: {detail}"
# ERR_EMPTY_FIELDS = "The fields dictionary was detected to be empty"
ERR_API_UNSUPPORTED_METHOD = "Unsupported method"

USING_BASE_URL = "Using url: {base_url}{api_uri}{endpoint}"
# ERR_JSON_PARSE = "Unable to parse reply as a Json, raw string reply: '{raw_text}'"
HACKERTARGET_BASE_URL = "https://api.hackertarget.com/"
HACKERTARGET_BASE_API = "/"
# HACKERTARGET_MSG_GET_INFO = "Querying API availability info"
HACKERTARGET_FAIL_ERR = "error check your api query"
HACKERTARGET_INPUT_INVALID = "error input invalid"
HACKERTARGET_NO_RESULTS = "No results found"
# MSG_MAX_POLLS_REACHED = "Reached max polling attempts."

HACKERTARGET_MTR_URI = "/mtr/"
HACKERTARGET_PING_URI = "/nping/"
# HACKERTARGET_DNSLOOKUP_URI = "/dnslookup/"
HACKERTARGET_REVERSEDNS_URI = "/reversedns/"
HACKERTARGET_REVERSEIP_URI = "/reverseiplookup/"
HACKERTARGET_WHOIS_URI = "/whois/"
HACKERTARGET_GEOIP_URI = "/geoip/"
HACKERTARGET_HTTPHEADERS_URI = "/httpheaders/"
HACKERTARGET_PAGELINKS_URI = "/pagelinks/"

HACKERTARGET_INVALID_KEY = "Error invalid key"

MAX_TIMEOUT_DEF = 5
SLEEP_SECS = 15

# cannot put 'error' in this list because it causes error when 'error' is present in domain name
# replaced with all the error strings instead of the word "error"
API_ERR = [
    "API count exceeded",
    "no record",
    "No PTR records found",
    "error input",
    "error input",
    "error check your search parameter",
    "error check your api query",
    "error getting result",
]
