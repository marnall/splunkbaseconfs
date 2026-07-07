# File: jupiterone_consts.py
#
# Copyright (c) JupiterOne Inc., 2022-2025
#
# This unpublished material is proprietary to JupiterOne.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of JupiterOne.
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

JUPITERONE_DEFAULT_LIMIT = 250
JUPITERONE_AUTHORIZATION_HEADER = "Bearer {}"

# Endpoints
JUPITERONE_QUERY_ENDPOINT = "https://api.us.jupiterone.io/graphql"

# Constants relating to error messages
JUPITERONE_STATE_FILE_CORRUPT_ERR = (
    "Error occurred while loading the state file due to its unexpected format. "
    "Resetting the state file with the default format. Please try again."
)
JUPITERONE_ERR_TEST_CONN_FAILED = "Test Connectivity Failed"
JUPITERONE_ERR_CREATING_SESSION_OBJECT = "Error occurred while creating the session object"
JUPITERONE_ERR_CONNECTING_TO_SERVER = "Error connecting to server. Details: {}"
JUPITERONE_ERR_EMPTY_RESPONSE = "Status Code {}. Empty response and no information in the header."
JUPITERONE_UNABLE_TO_PARSE_ERR_DETAIL = "Cannot parse error details"
JUPITERONE_ERR_UNABLE_TO_PARSE_JSON_RESPONSE = "Unable to parse response as JSON. {}"

# Constants relating to success messages
JUPITERONE_SUCC_TEST_CONN_PASSED = "Test Connectivity Passed"
JUPITERONE_NO_RESULTS_QUERY_PASSED = "No results found for the query"

# Constants relating to 'get_error_message_from_exception'
ERR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters."

# # Constants relating to "validate_integer"
JUPITERONE_VALID_INT_MSG = "Please provide a valid integer value in the '{}' action parameter"
JUPITERONE_NON_NEG_NON_ZERO_INT_MSG = "Please provide a valid non-zero positive integer value in the '{}' action parameter"
JUPITERONE_NON_NEG_INT_MSG = "Please provide a valid non-negative integer value in the '{}' action parameter"
