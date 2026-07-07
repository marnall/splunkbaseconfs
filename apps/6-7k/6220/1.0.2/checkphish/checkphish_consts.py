# File: checkphish_consts.py
#
# Copyright (c) 2021-2025 Splunk Inc.
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

CHECKPHISH_CHECK_STATUS_ENDPOINT = "/neo/scan/status"
CHECKPHISH_DETONATE_URL_ENDPOINT = "/neo/scan/"
CHECKPHISH_STATE_FILE_CORRUPT_ERR = "Error occurred while loading the state file due to its unexpected format.\
     Resetting the state file with the default format. Please try again."

# constants relating to "get_error_msg_from_exception"
CHECKPHISH_ERR_CODE_MSG = "Error code unavailable"
CHECKPHISH_ERR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
