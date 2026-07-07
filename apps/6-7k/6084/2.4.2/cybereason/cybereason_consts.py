# Copyright (c) 2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# File: cybereason_consts.py
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

SOAR_TO_CYBEREASON_STATUS = {
    "Unread": "UNREAD",
    "To Review": "TODO",
    "Not Relevant": "FP",
    "Remediated": "CLOSE",
    "Reopend": "REOPEN",
    "Under Investigation": "OPEN",
}
CUSTOM_REPUTATION_LIST = ["whitelist", "blacklist", "remove"]

# Constants relating to '_get_error_message_from_exception'
ERROR_CODE_MESSAGE = "Error code unavailable"
ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"

# Constants relating to '_validate_integer'
INVALID_INTEGER_ERROR_MESSAGE = "Please provide a valid integer value in the {}"
INVALID_NON_NEGATIVE_INTEGER_ERROR_MESSAGE = "Please provide a valid non-negative integer value in the {}"

MALOP_HISTORICAL_DAYS_KEY = "malop_historical_days asset configuration parameter"
MALWARE_HISTORICAL_DAYS_KEY = "malware_historical_days asset configuration parameter"

DEFAULT_REQUEST_TIMEOUT = 60  # in seconds
