# File: hyasprotect_consts.py
#
# Copyright (c) Hyas, 2022-2025
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

# Define your constants here
IP = "ip"
DOMAIN = "domain"
NAMESERVER = "nameserver"
FQDN = "fqdn"

HYAS_ERROR_MESSAGE_INVALID_INDICATOR_VALUE = "Error: Invalid Indicator value"

BASE_URL = "https://api.hyas.com"
IP_REPUTATION_ENDPOINT = "/protect/ip/"
FQDN_REPUTATION_ENDPOINT = "/protect/fqdn/"
NAMESERVER_REPUTATION_ENDPOINT = "/protect/nameserver/"
DOMAIN_REPUTATION_ENDPOINT = "/protect/domain/"
BLOCK_DNS_ENDPOINT = "/data/list"

APIKEY_HEADER = "x-api-key"  # pragma: allowlist secret
API_KEY = "apikey"  # pragma: allowlist secret

DOMAIN_TEST_ENDPOINT = "/protect/domain/"
DOMAIN_TEST_VALUE = "google"

# error messages
HYAS_ERROR_CODE_MESSAGE = "Error code unavailable"
HYAS_ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"

HYAS_PARSE_ERROR_MESSAGE = "Unable to parse the error message. Please check the asset configuration and|or action parameters"

HYAS_MESSAGE_CREATED_URL = "Created Query URL"
HYAS_UNKNOWN_ERROR_CODE_MESSAGE = "Error code unavailable"
HYAS_INVALID_APIKEY_ERROR = "Please provide a valid api key"  # pragma: allowlist secret
HYAS_ASSET_ERROR_MESSAGE = "Please provide the valid indicator value"
IP_REG = (
    r"\b((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2["
    r"0-4]["
    r"0-9]|[01]?[0-9][0-9]?)\b([^\/]|$)"
)
IPV6_REG = (
    r"(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{"
    r"1,4}:){1,"
    r"7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,"
    r"4}|([0-9a-fA-F]{1,"
    r"4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,"
    r"4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,"
    r"3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,"
    r"2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:["
    r"0-9a-fA-F]{1,"
    r"4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:["
    r"0-9a-fA-F]{0,"
    r"4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,"
    r"1}((25[0-5]|("
    r"2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2["
    r"0-4]|1{0,"
    r"1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|("
    r"2["
    r"0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{"
    r"0,"
    r"1}[0-9]){0,1}[0-9]))"
)
DOMAIN_REG = (
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-_]{0,"
    r"61}[A-Za-z0-9])?\.)+["
    r"A-Za-z0-9][A-Za-z0-9-_]{0,61}[A-Za-z]$"
)

IOC_NAME = {
    "ip": IP_REG,
    "domain": DOMAIN_REG,
    "fqdn": DOMAIN_REG,
    "nameserver": DOMAIN_REG,
}
EMPTY_RESPONSE = "Empty response and no information in the header"
ERROR_TEXT = "Cannot parse error details"
UNABLE_TO_FLATTEN_JSON = "unable to flatten action json response."
IP_VERDICT = "ip_verdict"
DOMAIN_VERDICT = "domain_verdict"
FQDN_VERDICT = "fqdn_verdict"
NAMESERVER_VERDICT = "nameserver_verdict"
BLOCK_DNS = "block_dns"
SPLUNK_SOAR_LIST = "SPLUNK SOAR list"
SPLUNK_SOAR_LIST_NOTES = "SPLUNK SOAR list for blocked domains"
TEST_CONNECTIVITY = "test_connectivity"
HYAS_DEFAULT_REQUEST_TIMEOUT = 30  # in seconds
