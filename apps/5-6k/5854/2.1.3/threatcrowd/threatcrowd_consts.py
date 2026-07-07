# File: threatcrowd_consts.py
#
# Copyright (c) 2016-2025 Splunk Inc.
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
THREATCROWD_JSON_DOMAIN = "domain"
THREATCROWD_JSON_EMAIL = "email"
THREATCROWD_JSON_IP = "ip"
THREATCROWD_JSON_FILE = "hash"
THREATCROWD_JSON_LIMIT = "response_limit"
THREATCROWD_BASE_URL = "http://ci-www.threatcrowd.org/"
THREATCROWD_API_URI = "searchApi/v2/"
THREATCROWD_ERROR_SERVER_CONNECTION = "Could not successfully connect to the Threatcrowd API"
THREATCROWD_DOMAIN_URI = "domain/report/"
THREATCROWD_EMAIL_URI = "email/report/"
THREATCROWD_IP_URI = "ip/report/"
THREATCROWD_FILE_URI = "file/report/"
THREATCROWD_DEFAULT_LIMIT = 10

# This value is set by trial and error by quering ThreatCrowd
THREATCROWD_ERROR_CONNECTIVITY_TEST = "Test connectivity failed"
THREATCROWD_SUCC_CONNECTIVITY_TEST = "Test connectivity passed"
THREATCROWD_ERROR_CODE_UNAVAILABLE = "Error code unavailable"
THREATCROWD_ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
THREATCROWD_UNICODE_DAMMIT_TYPE_ERROR_MESSAGE = (
    "Error occurred while connecting to the ThreatCrowd server. Please check the asset configuration and|or the action parameters"
)

# Integer Validation Keys
THREATCROWD_VALIDATE_INTEGER = "Please provide a valid integer value in the '{param}' parameter"
THREATCROWD_NON_ZERO_NON_NEG_INVALID_PARAM = "Please provide a non-zero positive integer value in the '{param}' parameter"
THREATCROWD_NON_NEG_PARAM = "Please provide a valid non-negative integer value in the '{param}' parameter"
