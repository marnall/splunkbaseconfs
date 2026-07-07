# File: arboraps_consts.py
#
# Copyright (c) 2017-2025 Splunk Inc.
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
ARBORAPS_TA_CONFIG_SERVER_URL = "server_url"
ARBORAPS_TA_CONFIG_USERNAME = "username"
ARBORAPS_TA_CONFIG_PASSWORD = "password"  # pragma: allowlist secret
ARBORAPS_TA_CONFIG_VERIFY_SSL = "verify_server_cert"
ARBORAPS_TA_CONNECTION_TEST_MSG = "Querying endpoint to verify the credentials provided"
ARBORAPS_TA_REST_LOGIN = "/platform/login"
ARBORAPS_TA_REST_LOGOUT = "/platform/logout"
ARBORAPS_TEST_CONNECTIVITY_FAIL = "Test Connectivity Failed."
ARBORAPS_TEST_CONNECTIVITY_PASS = "Test Connectivity Passed"
ARBORAPS_TA_PARAM_IP = "ip"
ARBORAPS_TA_REST_BLOCKLISTED_HOSTS = "/api/aps/v1/otf/blacklisted-hosts/"
ARBORAPS_TA_REST_ALLOWLISTED_HOSTS = "/api/aps/v1/otf/whitelisted-hosts/"
ARBORAPS_INVALID_IP = "Parameter 'ip' failed validation"
ARBORAPS_ALREADY_BLOCKLISTED = "IP already in blocklist"
ARBORAPS_ALREADY_ALLOWLISTED = "IP already in allowlist"
ARBORAPS_BLOCKLISTED_SUCCESSFULLY = "IP blocklisted successfully"
ARBORAPS_ALLOWLISTED_SUCCESSFULLY = "IP allowlisted successfully"
ARBORAPS_ALREADY_UNBLOCKLISTED = "IP already un-blockisted"
ARBORAPS_ALREADY_UNALLOWLISTED = "IP already un-allowlisted"
ARBORAPS_UNBLOCKLISTED_SUCCESSFULLY = "IP un-blocklisted successfully"
ARBORAPS_UNALLOWLISTED_SUCCESSFULLY = "IP un-allowlisted successfully"
