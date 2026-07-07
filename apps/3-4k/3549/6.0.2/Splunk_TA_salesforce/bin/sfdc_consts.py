#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

APP_NAME = "Splunk_TA_salesforce"
SETTINGS_CONF_FILE = "splunk_ta_salesforce_settings"
ACCOUNT_CONF_FILE = "splunk_ta_salesforce_account"
SERVER_URL_REGEX = "\\<serverUrl\\>(?P<serverUrl>https:\\/\\/[a-zA-Z0-9\\-\\.]+)\\/.*\\<\\/serverUrl\\>"
SESSION_ID_REGEX = "\\<sessionId\\>(?P<sessionId>.*)\\<\\/sessionId\\>"
USER_ID_BASIC_REGEX = "\\<userId\\>(?P<userid>.*?)\\<\\/userId\\>"
FAULT_STRING_REGEX = "\\<faultstring\\>(?P<faultstring>.*)\\<\\/faultstring\\>"
FAULT_CODE_REGEX = "\\<faultcode\\>sf:(?P<faultcode>.*)\\<\\/faultcode\\>"
DEFAULT_ERROR = (
    "Login Salesforce failed. Please check your network environment and credentials."
)
DEFAULT_CSV_LIMIT = 10485760
MAX_CSV_LIMIT = 2147483647
EVENTS_BATCH_SIZE = 50000

SFDC_EVENTLOG_CHECKPOINT_COLLECTION_NAME = (
    "Splunk_TA_salesforce_sfdc_event_log_input_checkpointer"
)
SFDC_OBJECT_CHECKPOINT_COLLECTION_NAME = (
    "Splunk_TA_salesforce_sfdc_object_input_checkpointer"
)
__LOG_FORMAT__ = (
    "%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s "
    "file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s"
)
