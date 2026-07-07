# File: qintelqwatch_consts.py
#
# Copyright (c) 2009-2021 Qintel, LLC
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
VERSION = '1.0.0'
USER_AGENT = 'Splunk-SOAR-'
USER_AGENT += VERSION
QINTELQWATCH_STATE_FILE_CORRUPT_ERR = "Error occurred while loading the state file due to its unexpected format.\
     Resetting the state file with the default format. Please try again."

# constants relating to "get_error_msg_from_exception"
QINTELQWATCH_ERR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"

# Constants relating to 'validate_integer'
VALID_INT_MSG = "Please provide a valid integer value in the '{param}' parameter"
NON_NEG_INT_MSG = "Please provide a valid non-negative integer value in the '{param}' parameter"
