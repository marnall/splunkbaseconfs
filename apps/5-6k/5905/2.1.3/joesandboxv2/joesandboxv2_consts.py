# File: joesandboxv2_consts.py
#
# Copyright (c) 2019-2025 Splunk Inc.
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

# Config and action keys
JOE_CONFIG_SERVER = "url"
JOE_CONFIG_API_KEY = "api_key"  # pragma: allowlist secret
JOE_CONFIG_TIMEOUT = "timeout"
JOE_CONFIG_VERIFY_SSL = "verify_ssl"
JOE_CONFIG_ANALYSIS_TIME = "analysis_time"
JOE_ACTION_GET_REPORT = "get_report"
JOE_ACTION_GET_PCAP = "get_pcap"

# Endpoints
JOE_LIST_COOKBOOKS_ENDPOINT = "/api/v2/cookbook/list"
JOE_GET_COOKBOOK_ENDPOINT = "/api/v2/cookbook/info"
JOE_CHECK_STATUS_ENDPOINT = "/api/v2/analysis/info"
JOE_TEST_CONNECTIVITY_ENDPOINT = "/api/v2/server/online"
JOE_DETONATE_SAMPLE_ENDPOINT = "/api/v2/analysis/submit"
JOE_REPORT_ENDPOINT = "/api/v2/analysis/download"
JOE_REPUTATION_SEARCH_ENDPOINT = "/api/v2/analysis/search"

# Error and status messages
JOE_ERR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
JOE_URL_SEARCH_ANALYSIS_NOT_FOUND_MSG = "No search analysis found for provided URL"
JOE_HASH_SEARCH_ANALYSIS_NOT_FOUND_MSG = "No search analysis found for provided hash"
JOE_REPORT_ALREADY_AVAILABLE_MSG = "The report is already available in vault"
JOE_CHECK_STATUS_POLLING_MSG = "Polling attempt {polling_attempt} of {total_count}"
JOE_TEST_CONNECTIVITY_INIT_MSG = "Querying endpoint to test connectivity"
JOE_TEST_CONNECTIVITY_PROGRESS_MSG = "Configured URL: {base_url}"
JOE_TEST_CONNECTIVITY_PASSED_MSG = "Connectivity test passed"
JOE_ERR_CONFIG_TIMEOUT_MSG = "Detonate timeout must be an integer between 30 and 300"
JOE_ERR_ANALYSIS_TIME_MSG = "Analysis time must be an integer between 30 and 300"
JOE_ERR_TEST_CONNECTIVITY_FAILED_MSG = "Connectivity test failed"
JOE_ERR_INVALID_DETONATION_TIME_MSG = "Detonate timeout must be an integer between 30 and 300"
JOE_ERR_INVALID_ANALYSIS_TIME_MSG = "Analysis time must be an integer between 30 and 300"
JOE_ERR_REPORT_UNAVAILABLE_MSG = "Analysis of sample with  webid: {webid} is not finished yet"
JOE_ERR_REPORT_DOWNLOAD_MSG = "Error occurred while downloading report of sample with webid: {webid}"
JOE_ERR_SAVE_REPORT_MSG = "Error occurred while saving report in vault for sample with webid: {webid}"
JOE_ERR_INVALID_ANALYSIS_AND_DETONATION_TIME_MSG = "Please provide integer values for both the detonation time and analysis time"
JOE_ERR_JSON_PARSE_MSG = "Unable to parse the fields parameter into a dictionary.\nResponse text - {raw_text}"
JOE_ERR_API_UNSUPPORTED_METHOD_MSG = "Unsupported method to make request"
JOE_ERR_SERVER_CONNECTION_MSG = "Connection failed"
JOE_ERR_INVALID_URL_MSG = "Status Code: {status_code}. Please provide a valid base URL in configuration parameters. The error is: {error_msg}"
JOE_ERR_FROM_SERVER_MSG = "API failed\nStatus code: {status}\nReason: {reason}\n"
JOE_ERR_UNKNOWN_ERR_MSG = "Unknown error occurred"
JOE_ERR_CHECK_STATUS_MSG = "Failed while checking status of sample submitted"
JOE_ERR_JSON_MSG = "Error while converting content data in json format: {error}"
JOE_ERR_FILE_MSG = "Error while creating file"
JOE_ERR_REMOVE_DIRECTORY_MSG = "Error while removing directory"
JOE_PCAP_REPORT_DOWNLOAD_MSG = "PCAP report downloaded successfully"
JOE_ERR_ADDING_TO_VAULT_FAILED_MSG = "Error occurred while adding the file to vault"
JOE_ERR_FILE_OR_COOKBOOK_NOT_FOUND_MSG = "Either the file or the cookbook for the provided hash not found in vault"
JOE_ERR_REPORT_FILENAME_NOT_FOUND_MSG = 'Incorrect response format. Not able to find "Content-Disposition" in headers'

# JSON keys
JOE_JSON_RESPONSE = "response"
JOE_JSON_API_KEY = "apikey"  # pragma: allowlist secret
JOE_JSON_RESPONSE_HEADERS = "headers"
JOE_JSON_DATA = "data"
JOE_JSON_OR = " or "
JOE_JSON_INET_ACCESS = "internet_access"
JOE_JSON_INTERNET_ACCESS = "internet-access"
JOE_JSON_REPORT_CACHE = "report_cache"
JOE_JSON_ENABLE_CACHE = "report-cache"
JOE_JSON_ANALYSIS_TIME = "analysis-time"
JOE_JSON_FILENAME = "filename"
JOE_JSON_REPUTATION_LABEL = "reputation_label"
JOE_JSON_WEBID = "webid"
JOE_JSON_TYPE = "type"
JOE_JSON_ID = "id"
JOE_JSON_URL = "url"
JOE_JSON_HASH = "hash"
JOE_JSON_FILE_VAULT_ID = "vault_id"
JOE_JSON_ERRS = "errors"
JOE_JSON_MSG = "message"
JOE_JSON_ANALYSIS = "analysis"
JOE_JSON_COOKBOOK = "cookbook"
JOE_JSON_NAME = "name"
JOE_JSON_SAMPLE = "sample"
JOE_JSON_FILE = "file"
JOE_JSON_STATUS = "status"
JOE_JSON_FINISHED = "finished"
JOE_JSON_COMMENTS = "comments"
JOE_JSON_ACCEPT_TAC = "accept-tac"
JOE_JSON_WEBIDS = "webids"
JOE_JSON_DOMAIN_INFO = "domaininfo"
JOE_JSON_DOMAIN = "domain"
JOE_JSON_IP_INFO = "ipinfo"
JOE_JSON_IP = "ip"
JOE_JSON_SIGNATURED_DETECTIONS = "signaturedetections"
JOE_JSON_STRATEGY = "strategy"
JOE_JSON_DROPPED_INFO = "droppedinfo"
JOE_JSON_FILE_ACTIVITIES = "fileactivities"
JOE_JSON_FILE_DELETED = "fileDeleted"
JOE_JSON_FILE_MOVED = "fileMoved"
JOE_JSON_REGISTRY_ACTIVITIES = "registryactivities"
JOE_JSON_KEY_CREATED = "keyCreated"
JOE_JSON_KEY_DELETED = "keyDeleted"
JOE_JSON_KEY_VALUE_MODIFIED = "keyValueModified"
JOE_JSON_SAMPLE_STATUS = "sample_status"
JOE_JSON_SAMPLE_DETAILS = "sample_details"
JOE_JSON_DOWNLOAD_REPORT_DETAILS = "download_report_details"
JOE_JSON_COOKBOOK_VAULT_ID = "cookbook_vault_id"
JOE_JSON_REPORT_FILE_NAME = "report_file_name"
JOE_JSON_SHA_256 = "sha256"
JOE_JSON_SHA_1 = "sha1"
JOE_JSON_MD_5 = "md5"
JOE_JSON_GENERAL_INFO = "generalinfo"
JOE_JSON_FILE_INFO = "fileinfo"
JOE_JSON_ANALYSIS_STATUS = "analysis_status"
JOE_JSON_BEHAVIOR = "behavior"
JOE_JSON_PROCESSES = "processes"
JOE_JSON_PROCESS = "process"
JOE_JSON_SYSTEM = "system"
JOE_JSON_SYSTEM_DESCRIPTION = "systemdescription"
JOE_JSON_SYSTEM_BEHAVIOR = "system_behavior"
JOE_JSON_GENERAL = "general"
JOE_JSON_CALL = "call"
JOE_JSON_RUNS = "runs"
JOE_JSON_DETECTION = "detection"
JOE_JSON_CLEAN = "clean"
JOE_JSON_CODE = "code"
JOE_JSON_JBS = ".jbs"
JOE_JSON_Q = "q"
JOE_JSON = "json"
JOE_JSON_SIZE = "size"
JOE_JSON_TARGET = "target"
JOE_JSON_FILE_NAME = "cookbook_file_name"
JOE_JSON_VAULT_ID = "vault_id"
JOE_JSON_CONTENT_DISPOSITION = "Content-Disposition"
JOE_JSON_RESP_SUCCESS_RESPONSE = 200

# Default values
JOE_TIME_DEFAULT = "120"
JOE_TIME_MIN = 30
JOE_TIME_MAX = 300
JOE_SLEEP_SECS = 30
JOE_DEFAULT_REQUEST_TIMEOUT = 30  # in seconds
