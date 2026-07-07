# File: anyrun_consts.py
#
# Copyright (c) ANYRUN FZCO, 2025-2026
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

VERSION = f"Splunk_SOAR:1.5.1"
# Action IDs
ACTION_ID_ANYRUN_TEST_CONNECTIVITY = "test_connectivity"
ACTION_ID_ANYRUN_GET_ANALYSIS_VERDICT = "get_analysis_verdict"
ACTION_ID_ANYRUN_GET_REPUTATION = "get_reputation"
ACTION_ID_ANYRUN_GET_REPORT = "get_report"
ACTION_ID_ANYRUN_GET_REPORT_STIX = "get_report_stix"
ACTION_ID_ANYRUN_GET_REPORT_MISP = "get_report_misp"
ACTION_ID_ANYRUN_GET_REPORT_HTML = "get_report_html"
ACTION_ID_ANYRUN_GET_IOC = "get_ioc"
ACTION_ID_ANYRUN_SEARCH_ANALYSIS_HISTORY = "search_analysis_history"
# ACTION_ID_ANYRUN_DETONATE_URL = "detonate_url"
ACTION_ID_ANYRUN_DETONATE_URL_ANDROID = "detonate_url_android"
ACTION_ID_ANYRUN_DETONATE_URL_LINUX = "detonate_url_linux"
ACTION_ID_ANYRUN_DETONATE_URL_WINDOWS = "detonate_url_windows"
# ACTION_ID_ANYRUN_DETONATE_FILE = "detonate_file"
ACTION_ID_ANYRUN_DETONATE_FILE_ANDROID = "detonate_file_android"
ACTION_ID_ANYRUN_DETONATE_FILE_LINUX = "detonate_file_linux"
ACTION_ID_ANYRUN_DETONATE_FILE_WINDOWS = "detonate_file_windows"
ACTION_ID_ANYRUN_GET_INTELLIGENCE = "get_intelligence"
ACTION_ID_ANYRUN_DELETE_ANALYSIS = "delete_analysis"
ACTION_ID_ANYRUN_DOWNLOAD_PCAP = "download_pcap"
# Error messages
ANYRUN_ERROR_CODE_MSG = "Error code unavailable."
ANYRUN_ERROR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters."
ANYRUN_PARSE_ERROR_MSG = "Unable to parse the error message. Please check the asset configuration and|or action parameters."
ANYRUN_UNABLE_TO_FETCH_FILE_ERROR = "Unable to retrieve the sample from the vault. Key: {}. Vault ID: {}."
ANYRUN_VAULT_MULTIPLE_FILES_ERROR = "Found multiple files for vault_id {}. Using the first one."
ANYRUN_VAULT_NO_FILES_ERROR = "No sample found for vault_id {}."
ANYRUN_SANDBOX_PARAMS_VALIDATION_ERROR = "Error in validating sandbox parameters. {}."
ANYRUN_REST_API_ERROR = "Error processing server response in action '{0}'. {1}."
ANYRUN_ADD_DATA_ERROR = "Error constructing action result in action '{0}'. {1}."
ANYRUN_DELETE_ANALYSIS_ERROR = "Error deleting analysis: {}. {}."
# Action specific messages
ANYRUN_ERROR_TEST_CONNECTIVITY = "Connectivity test failed. {}."
ANYRUN_SUCCESS_TEST_CONNECTIVITY = "Connectivity test passed."
ANYRUN_SUCCESS_GET_REPUTATION = "Successfully retrieved reputation via Threat Intelligence Lookup for '{0}'."
ANYRUN_SUCCESS_SEARCH_ANALYSIS_HISTORY = "Successfully retrieved list of reports for analysis from history '{0}'."
ANYRUN_SUCCESS_GET_REPORT = "Successfully retrieved report for analysis: {}."
ANYRUN_SUCCESS_GET_IOC = "Successfully retrieved IoC report for analysis: {}."
ANYRUN_SUCCESS_DETONATE_URL = "Successfully detonated URL: {}."
ANYRUN_SUCCESS_DETONATE_FILE = "Successfully detonated file with the vault ID : {}."
ANYRUN_SUCCESS_GET_INTELLIGENCE = "Successfully retrieved threat information via Threat Intelligence Lookup for query '{0}'."
ANYRUN_SUCCESS_DELETE_ANALYSIS = "Successfully deleted analysis: {}."
ANYRUN_SUCCESS_DOWNLOAD_PCAP = "Successfully downloaded PCAP file for analysis: {}."
ANYRUN_SUCCESS_GET_ANALYSIS_VERDICT = "Successfully retrieved verdict for analysis: {}."

VERDICT_RESOLVER = {
    0: "No info",
    1: "Suspicious",
    2: "Malicious",
}
