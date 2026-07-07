# File: expanse_consts.py
#
# Copyright (c) Expanse, 2020-2025
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
STATUS_CODE_200 = 200
STATUS_CODE_204 = 204
EXPANSE_USER_AGENT = "Expanse_Phantom/1.0.0"
JSON_CONTENT_TYPE = "application/json"
IP_LOOKUP_INCLUDE_PARAMS = "annotations,severityCounts,attributionReasons,relatedRegistrationInformation,locationInformation"

# Constants relating to 'get_error_message_from_exception'
ERR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters."

# Constants relating to error messages
EXPANSE_STATE_FILE_CORRUPT_ERR = (
    "Error occurred while loading the state file due to its unexpected format. "
    "Resetting the state file with the default format. Please try again."
)
