# File: code42v2_consts.py
#
# Copyright (c) 2022-2026 Splunk Inc., Code42
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

# max_results default value
MAX_RESULTS_DEFAULT = 1000

# default page size
PAGE_SIZE = 10000

# value list for filter_type parameter in list departing employee action
CODE42V2_FILTER_TYPE_DEPARTING_LIST = ["EXFILTRATION_30_DAYS", "EXFILTRATION_24_HOURS", "OPEN", "LEAVING_TODAY"]

# value list for filter_type parameter in list high risk employee action
CODE42V2_FILTER_TYPE_HIGH_RISK_LIST = ["EXFILTRATION_30_DAYS", "EXFILTRATION_24_HOURS", "OPEN"]

# value list for risk_tag parameter in add/remove highrisk tag action
CODE42V2_RISK_TAG_LIST = [
    "HIGH_IMPACT_EMPLOYEE",
    "CONTRACT_EMPLOYEE",
    "POOR_SECURITY_PRACTICES",
    "PERFORMANCE_CONCERNS",
    "FLIGHT_RISK",
    "ELEVATED_ACCESS_PRIVILEGES",
    "SUSPICIOUS_SYSTEM_ACTIVITY",
]

# value list for alert_state parameter in set alert state and search alert action
CODE42V2_ALERT_STATE = ["OPEN", "RESOLVED", "PENDING", "IN_PROGRESS"]

# value list for status parameter in list cases action
CODE42V2_CASE_STATUS_LIST = ["ALL", "OPEN", "CLOSED"]

# value list for file_category parameter in run query action
CODE42V2_FILE_CATEGORY_LIST = [
    "Audio",
    "Document",
    "Executable",
    "Image",
    "Pdf",
    "Presentation",
    "Script",
    "SourceCode",
    "Spreadsheet",
    "Video",
    "VirtualDiskImage",
    "Archive",
]

# value list for exposure_type parameter in run query action
CODE42V2_EXPOSURE_TYPE_LIST = [
    "All",
    "SharedViaLink",
    "SharedToDomain",
    "ApplicationRead",
    "CloudStorage",
    "RemovableMedia",
    "IsPublic",
    "OutsideTrustedDomains",
]

# value list for active_user parameter in list users action
CODE42V2_USER_STATUS_LIST = ["Active", "Inactive", "All"]

# page related keys
PAGE_KEYS = ["pgNum", "pgSize", "pgToken"]

# integer validation constants
CODE42V2_VALID_INT_MSG = "Please provide a valid integer value in the '{param}' action parameter"
CODE42V2_NON_NEG_INT_MSG = "Please provide a valid non-negative integer value in the '{param}' action parameter"
CODE42V2_NON_NEG_NON_ZERO_INT_MSG = "Please provide a valid non-zero positive integer value in '{param}' action parameter"
CODE42V2_CASE_NUM_KEY = "case_number"
CODE42V2_MAX_RESULTS_KEY = "max_results"
CODE42V2_ROLE_ID_KEY = "role_id"

# value_list validation constants
CODE42V2_VALUE_LIST_ERR_MSG = "Please provide a valid value in the '{}' action parameter. Expected values are {}"
