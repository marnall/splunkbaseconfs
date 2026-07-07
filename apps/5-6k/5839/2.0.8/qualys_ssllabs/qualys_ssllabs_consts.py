# File: qualys_ssllabs_consts.py
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
QUALYS_SSLLABS_ERR_API_INITIALIZATION = "API Initialization failed"
ERR_CONNECTIVITY_TEST = "Connectivity test failed"
SUCC_CONNECTIVITY_TEST = "Connectivity test passed"
ERR_SERVER_CONNECTION = "Connection failed"
ERR_FROM_SERVER = "API failed, Status code: {status}, Detail: {detail}"
ERR_EMPTY_FIELDS = "The fields dictionary was detected to be empty"
ERR_API_UNSUPPORTED_METHOD = "Unsupported method"

USING_BASE_URL = "Using url: {base_url}{api_uri}{endpoint}"
ERR_JSON_PARSE = "Unable to parse reply as a Json, raw string reply: '{raw_text}'"
QUALYS_SSLLABS_BASE_URL = "https://api.ssllabs.com/"
QUALYS_SSLLABS_BASE_API = "/api/v2"
QUALYS_SSLLABS_TICKET_FOOTNOTE = "Added by Phantom for container id: "
QUALYS_SSLLABS_MSG_GET_INFO = "Querying API availability info"
QUALYS_SSLLABS_MAX_AGE = "12"
MSG_REPORT_PENDING = "Report Pending"
MSG_MAX_POLLS_REACHED = "Reached max polling attempts."

POLL_TIMEOUT_MINS = 10
SLEEP_SECS = 30
