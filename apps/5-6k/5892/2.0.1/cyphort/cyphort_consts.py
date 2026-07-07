# --
# File: cyphort_consts.py
# Copyright (c) 2014-2021 Splunk Inc.
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

CYPHORT_ERR_CONNECTIVITY_TEST = "Connectivity test failed"
CYPHORT_SUCC_CONNECTIVITY_TEST = "Connectivity test passed"
CYPHORT_ERR_SERVER_CONNECTION = "Connection failed"
CYPHORT_ERR_FROM_SERVER = "API failed, Status Code: {status_code}, Status: {status}, Message: {message}"
CYPHORT_USING_BASE_URL = "Using url: {base_url}"
CYPHORT_MSG_QUERYING_USERS_CHECK_CREDS = "Querying users to check for credentials"
CYPHORT_MSG_FILE_SUBMITTED = "Submitted file"
CYPHORT_MSG_POLL_TRY = "Polling attempt {0}. Analysis pending"
CYPHORT_MSG_ANALYSIS_COMPLETE = "Analysis complete, getting results"

CYPHORT_REST_API_URL = "https://{server}/cyadmin/api.php"
CYPHORT_REST_API_UPLOAD_FILE_URL = "https://{server}/cyadmin/cgi-bin/file_submit"
CYPHORT_JSON_APIKEY = "api_key"  # pragma: allowlist secret
CYPHORT_JSON_SERVER = "server"
CYPHORT_JSON_ID = "id"
CYPHORT_JSON_ANALYSIS = "analysis_details"
CYPHORT_JSON_BEHAVIOR = "behavior_details"
CYPHORT_JSON_EVENT_ID = "event_id"
CYPHORT_JSON_TARGET = "target"

CYPHORT_SUCC_ANALYSIS_INCOMPLETE = "Reached max polling attempts. Please use the <b>event_id</b>" \
                                   " as a parameter to <b>get report</b> to query the report status."
CYPHORT_POLL_SLEEP_SECS = 10
CYPHORT_MAX_POLL_TIMES = 20
