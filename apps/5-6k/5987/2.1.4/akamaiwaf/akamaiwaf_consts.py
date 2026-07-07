# File: akamaiwaf_consts.py
#
# Copyright (c) Robert Drouin, 2021-2026
#
# Licensed under Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt)
#
# Define your constants here
AKAMAI_API_PATH = "/network-list/v2/"
AKAMAI_NETWORK_LIST_ENDPOINT = "network-lists"
AKAMAI_ACTIVATIONS_ENDPOINT = "activations"

DEFAULT_TIMEOUT = 30

# Constants relating to '_get_error_message_from_exception'
ERROR_CODE_MSG = "Error code unavailable"
ERROR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
PARSE_ERROR_MSG = "Unable to parse the error message. Please check the asset configuration and|or action parameters"
TYPE_ERROR_MSG = "Error occurred while connecting to the Akamai WAF Server. Please check the asset configuration and|or the action parameters"

# Constants relating to '_validate_integer'
VALID_INTEGER_MSG = "Please provide a valid integer value in the {}"
NON_NEGATIVE_INTEGER_MSG = "Please provide a valid non-negative integer value in the {}"
SYNCPOINT_KEY = "'syncpoint' action parameter"
ACTIVATIONID_KEY = "'activationid' action parameter"

# Constants relating to value_list check
ENVIRONMENT_VALUE_LIST = ["PRODUCTION", "STAGING"]
TYPE_VALUE_LIST = ["IP", "GEO"]
