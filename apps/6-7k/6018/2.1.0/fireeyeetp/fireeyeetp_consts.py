# File: fireeyeetp_consts.py
#
# Copyright (c) Robert Drouin, 2021-2025
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
# Define your constants here
FIREETEETP_API_PATH = "api/v1/"
FIREETEETP_LIST_ALERTS_ENDPOINT = "alerts"
FIREETEETP_GET_ALERT_ENDPOINT = "alerts/{alertId}"
FIREETEETP_GET_ALERT_CASE_FILES_ENDPOINT = "alerts/{alertId}/downloadzip"
FIREETEETP_GET_ALERT_MALWARE_FILES_ENDPOINT = "alerts/{alertId}/downloadmalware"
FIREETEETP_GET_ALERT_PCAP_FILES_ENDPOINT = "alerts/{alertId}/downloadpcap"
FIREETEETP_LIST_MESSAGE_ATTRIBUTES_ENDPOINT = "messages/trace"
FIREETEETP_GET_MESSAGE_ATTRIBUTES_ENDPOINT = "messages/{etp_message_id}"
FIREETEETP_GET_MESSAGE_TRACE_ENDPOINT = "messages"
FIREETEETP_GET_EMAIL_ENDPOINT = "messages/{etp_message_id}/email"
FIREETEETP_REMEDIATE_EMAILS_ENDPOINT = "messages/remediate"
FIREEYEETP_GET_QUARANTINED_EMAIL_ENDPOINT = "quarantine/email/{etp_message_id}"
FIREEYEETP_BULK_RELEASE_QUARANTINE_EMAILS_ENDPOINT = "quarantine/release/"
FIREEYEETP_RELEASE_QUARANTINED_EMAIL_ENDPOINT = "quarantine/release/{etp_message_id}"
FIREEYEETP_BULK_DELETE_QUARANTINE_EMAILS_ENDPOINT = "quarantine/delete/"
FIREEYEETP_DELETE_QUARANTINED_EMAIL_ENDPOINT = "quarantine/delete/{etp_message_id}"
FIREEYEETP_LIST_QUARANTINED_EMAILS_ENDPOINT = "quarantine"
FIREEYEETP_AUTH_URL = "https://auth.trellix.com/auth/realms/IAM/protocol/openid-connect/token"

# Constants relating to '_get_error_message_from_exception'
ERR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
ERR_ISO_FORMAT = "Date supplied in the '{}' field is not ISO8601 compliant. Please make sure it is a valid ISO8601 datetime stamp"

# Constants relating to '_validate_integer'
VALID_INTEGER_MSG = "Please provide a valid integer value in the {}"
NON_NEGATIVE_INTEGER_MSG = "Please provide a valid non-negative integer value in the {}"
POSITIVE_INTEGER_MSG = "Please provide a valid non-zero positive integer value in the {}"
SIZE_KEY = "'size' action parameter"
LEGACY_ID_KEY = "'legacy_id' action parameter"
NUM_DAYS_KEY = "'num_days' action parameter"
CONTAINER_COUNT_KEY = "'container_count' action parameter"

# Constant for corrupt asset file
FIREEYEETP_STATE_FILE_CORRUPT_ERR = "Error occurred while loading the state file due to its unexpected format.\
     Resetting the state file with the default format. Please try again."

# Timeout
FIREETEETP_DEFAULT_TIMEOUT = 30
