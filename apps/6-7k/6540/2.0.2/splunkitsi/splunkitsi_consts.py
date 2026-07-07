# File: splunkitsi_consts.py
#
# Copyright (c) 2020-2025 Splunk Inc.
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
# Define your constants here

# Error constants
ERROR_CODE_MESSAGE = "Error code unavailable"
ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
PARSE_ERROR_MESSAGE = "Unable to parse the error message. Please check the asset configuration and|or action parameters"
TYPE_ERROR_MESSAGE = (
    "Error occurred while connecting to the Splunk IT Service Intelligence Server. "
    "Please check the asset configuration and|or the action parameters"
)

VALID_INTEGER_MESSAGE = "Please provide a valid integer value in the {key}"
NON_NEGATIVE_INTEGER_MESSAGE = "Please provide a valid non-negative integer value in the {key}"
NON_ZERO_INTEGER_MESSAGE = "Please provide a valid non-zero positive integer value in the {key}"
SPLUNKITSI_STATE_FILE_CORRUPT_ERROR = (
    "Error occurred while loading the state file due to its unexpected format. "
    "Resetting the state file with the default format. Please try again."
)

# Value list constants
SPLUNKITSI_TICKET_SYSTEMS = ["ServiceNow", "Remedy", "Phantom", "VictorOps", "New Custom Ticketing System"]
SPLUNKITSI_EVENT_TIME_RANGE = ["15 min", "60 mins", "4 hours", "24 hours", "7 days", "30 days"]
ITSI_EPISODE_SEVERITY_VALUES = {"Info": "1", "Normal": "2", "Low": "3", "Medium": "4", "High": "5", "Critical": "6"}
ITSI_EPISODE_STATUS_VALUES = {"Unassigned": "0", "New": "1", "In Progress": "2", "Pending": "3", "Resolved": "4", "Closed": "5"}
OBJECT_STATUS_VALUES = {"Disabled": 0, "Enabled": 1}
RELATIVE_TIME_VALUES = {"15 min": "15m", "60 mins": "60m", "4 hours": "4h", "24 hours": "24h", "7 days": "7d", "30 days": "30d"}

# Based on high volume data
SPLUNKITSI_DEFAULT_REQUEST_TIMEOUT = 600  # in seconds
