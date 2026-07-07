# File: isightpartners_consts.py
#
# Copyright (c) 2014-2025 Splunk Inc.
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
ISIGHTPARTNERS_JSON_API_URL = "api_url"
ISIGHTPARTNERS_JSON_API_KEY = "api_key"  # pragma: allowlist secret
ISIGHTPARTNERS_JSON_SECRET = "secret"  # pragma: allowlist secret

ISIGHTPARTNERS_JSON_HASH = "hash"
ISIGHTPARTNERS_JSON_NUM_RESULTS = "number_of_results"
ISIGHTPARTNERS_JSON_DOMAIN = "domain"
ISIGHTPARTNERS_JSON_URL = "url"
ISIGHTPARTNERS_JSON_IP = "ip"
ISIGHTPARTNERS_JSON_REPORTS_MATCHED = "reports_matched"
ISIGHTPARTNERS_JSON_PUBLISHED_DATE = "published_date"
ISIGHTPARTNERS_JSON_THREADSCAPE_INFO = "threatscape_info"
ISIGHTPARTNERS_JSON_REPORT_ID = "id"
ISIGHTPARTNERS_JSON_DOWNLOAD_REPORT = "download_report"
ISIGHTPARTNERS_JSON_DEF_NUM_DAYS = "interval_days"

ISIGHTPARTNERS_ERR_CONNECTIVITY_TEST = "Connectivity test failed"
ISIGHTPARTNERS_SUCC_CONNECTIVITY_TEST = "Connectivity test passed"
ISIGHTPARTNERS_ERR_SERVER_CONNECTION = "Connection to server failed"
ISIGHTPARTNERS_ERR_REPLY_FORMAT = "Invalid format of reply from server"
ISIGHTPARTNERS_ERR_FROM_SERVER = "From server, error: {error}, description: {description}"
ISIGHTPARTNERS_ERR_INVALID_HASH = "Unable to detect the type of hash, possibly invalid hash type"
ISIGHTPARTNERS_ERR_END_TIME_LT_START_TIME = "End time less than start time"
ISIGHTPARTNERS_ERR_RANGE_MORE_THAN_MAX = "The date range specified exceeds {max_days} days, the maximum allowed number of days."
ISIGHTPARTNERS_MSG_NO_RESULTS = "Search did not return any results"
ISIGHTPARTNERS_USING_API_URL = "Using api url: {api_url}"
ISIGHTPARTNERS_MSG_GOT_REPORTS = "Got {number_of_reports} within the time range"
ISIGHTPARTNERS_MSG_GETTING_REPORT = "Getting Report: {report_id}, published on: {published_on}"
ISIGHTPARTNERS_ERR_GETTING_REPORT = "Error getting Report: {report_id}.{error_str}"
ISIGHTPARTNERS_MSG_NO_OBSERVABLES_FOUND = "No artifacts collected"
ISIGHTPARTNERS_ERR_REPORT_FORMAT = "Report format invalid"
ISIGHTPARTNERS_ERR_SAVE_CONTAINER = "Failed to save container. Response: {response}"
ISIGHTPARTNERS_USING_TIMERANGE = "Getting reports published between {start_time} and {end_time}"
ISIGHTPARTNERS_MSG_GETTING_MOST_N_RECENT = "Getting most {number_of_reports} recent reports"
ISIGHTPARTNERS_MSG_NO_RESULTS_CONTAINER_ID = "The queried container id was not found in the time range"
ISIGHTPARTNERS_MSG_RESULTS_CONTAINER_ID = "Got Reports matching specified container id"
ISIGHTPARTNERS_SUCC_FILE_ADD_TO_VAULT = "Report file added to vault"
ISIGHTPARTNERS_MSG_DOWNLOADING_REPORT = "Downloading report pdf"
ISIGHTPARTNERS_SUCC_GOT_REPORT_DETAILS = "Successfully got report details"
ISIGHTPARTNERS_MSG_SET_CORRECT_TIME = "\r\nPlease make sure the system time is correct."
ISIGHTPARTNERS_MSG_SET_CORRECT_TIME += "\r\niSight credentials validation might fail in case the time is misconfigured"
ISIGHTPARTNERS_ERR_JSON_PARSE = "Unable to parse reply as a Json, raw string reply: '{raw_text}'"

ISIGHTPARTNERS_MILLISECONDS_IN_A_DAY = 86400000
ISIGHTPARTNERS_NUMBER_OF_DAYS_BEFORE_ENDTIME = 1
ISIGHTPARTNERS_SECONDS_IN_A_DAY = 86400
ISIGHTPARTNERS_MAX_DAYS_RANGE = 90
ISIGHTPARTNERS_MAX_DAYS_SECONDS = ISIGHTPARTNERS_SECONDS_IN_A_DAY * ISIGHTPARTNERS_MAX_DAYS_RANGE
ISIGHTPARTNER_DEFAULT_CONTAINER_COUNT = 1000
ISIGHTPARTNER_DEFAULT_ARTIFACT_COUNT = 1000
ISIGHTPARTNER_REPORT_FILE_TYPE = "isightpartners report file"
MAX_COUNT_VALUE = 4294967295

DEFAULT_TIMEOUT = 30  # seconds
