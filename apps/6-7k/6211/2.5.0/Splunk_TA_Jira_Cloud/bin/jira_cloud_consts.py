##
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
SETTINGS_CONFIG_FILE = "splunk_ta_jira_cloud_settings"
API_TOKEN_DETAILS_CONF_FILE = "splunk_ta_jira_cloud_api_token"
JIRA_CLOUD_ISSUES_LOGFILE_PREFIX = "splunk_ta_jira_cloud_issues_input_"
JIRA_CLOUD_AUDIT_LOGFILE_PREFIX = "splunk_ta_jira_cloud_input"
JIRA_CLOUD_ALERT_ACTION_LOGFILE_PREFIX = "splunk_ta_jira_cloud_alert_action_"
JIRA_CLOUD_CUSTOM_COMMAND = "splunk_ta_jira_cloud_custom_command"
JIRA_CLOUD_VALIDATION = "splunk_ta_jira_cloud_validation"
JIRA_CLOUD_RH_INPUT_VALIDATION = "splunk_ta_jira_cloud_rh_input_validation"
LOG_FILE_PREFIX = "splunk_ta_jira_cloud_issues_input_"
COLLECTION_NAME = "jira_cloud_issues_input"
JIRA_CLOUD_RH_SETTINGS = "splunk_ta_jira_cloud_settings"
INPUTS_CONFIG_FILE = "inputs"

# Jira_cloud_issues costants
KVSTORE_COLLECTION_NAME = "jira_cloud_issues_input"
JQL_QUERY_FORMAT = 'project IN ({}) {} AND {}>="{}" AND {}<"{}" ORDER BY {} ASC'
JIRA_QUERY_DATE_FORMAT = "%Y-%m-%d %H:%M"
JIRA_EVENT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
JIRA_AUDIT_DATE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
API_VERSION = 3
JIRA_ISSUE_DEFAULT_FIELDS_PARAM = (
    "*all,-comment,-attachment,-worklog,-timetracking,-issuerestriction"
)
JIRA_ISSUE_DEFAULT_EXCLUDED_FIELDS = [
    "comment",
    "attachment",
    "worklog",
    "timetracking",
    "issuerestriction",
]
# Jira_cloud_issues Endpoints
JIRA_PROJECT_SEARCH_ENDPOINT = "https://{}.atlassian.net/rest/api/{}/project/search"
JIRA_ISSUES_SEARCH_ENDPOINT = "/rest/api/3/search/jql"
JIRA_ISSUES_GET_TIMEZONE = "/rest/api/3/myself"
JIRA_ISSUE_PROJECT_ENDPOINT = "https://{}.atlassian.net/rest/api/3/project/{}"
JIRA_ISSUE_PRIORITY_ENDPOINT = "https://{}.atlassian.net/rest/api/3/priority/search"
JIRA_ISSUE_FIELDS_ENDPOINT = "https://{}.atlassian.net/rest/api/3/field"
JIRA_ISSUE_CREATE_ENDPOINT = "https://{}.atlassian.net/rest/api/3/issue"
JIRA_ISSUE_UPDATE_ENDPOINT = "https://{}.atlassian.net/rest/api/3/issue/{}"
JIRA_ISSUE_ENDPOINT = "https://{}.atlassian.net/browse/{}"
JIRA_ISSUE_TRANSITION_ENDPOINT = (
    "https://{}.atlassian.net/rest/api/3/issue/{}/transitions"
)

CONNECTION_ERROR = "log_connection_error"
SERVER_ERROR = "log_server_error"
GENERAL_EXCEPTION = "log_exception"
JIRA_CLOUD_ERROR = "jira_cloud_ta_error"
UCC_EXCEPTION_EXE_LABEL = "splunk_ta_jira_cloud_exception_{}"
JIRA_AUDITS_SOURCETYPE = "jira:cloud:audit:log"
JIRA_ISSUES_SOURCETYPE = "jira:cloud:issues"
MAX_DESCRIPTION_LENGTH = 32750

# Jira_cloud_users constants
JIRA_USERS_SOURCETYPE = "jira:cloud:users"
JIRA_CLOUD_USERS_LOGFILE_PREFIX = "splunk_ta_jira_cloud_users_input_"
KVSTORE_USERS_COLLECTION_NAME = "jira_cloud_users_input"
JIRA_USERS_ENDPOINT = "/rest/api/3/users"
JIRA_USERS_MAX_RESULTS = 1000
