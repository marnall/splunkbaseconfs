# File: apivoid_consts.py
#
# Copyright (c) 2019-2025 Splunk Inc.
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
APIVOID_ACTUAL_URL = "{base_url}/{endpoint}/pay-as-you-go"
APIVOID_TEST_CONNECTIVITY_ENDPOINT = "sslinfo/v1"
APIVOID_SSL_INFO_ENDPOINT = "sslinfo/v1"
APIVOID_IP_REPUTATION_ENDPOINT = "iprep/v1"
APIVOID_DOMAIN_REPUTATION_ENDPOINT = "domainbl/v1"
APIVOID_CONFIG_SERVER_URL = "server_url"
APIVOID_CONFIG_APIKEY = "api_key"  # pragma: allowlist secret
APIVOID_CONST_STATS = "stats"
APIVOID_CONST_HOST = "host"
APIVOID_CONST_IP = "ip"
APIVOID_CONST_DOMAIN = "domain"
APIVOID_INVALID_IP_MSG = "Invalid IP provided: {ip}"
APIVOID_GET_CERT_INFO_SUCCESS_MSG = "Received Certificate information for domain {domain}"
APIVOID_NO_ENGINES_FOUND_MSG = "No engines found in blacklist category"
APIVOID_CONNECTIVITY_MSG = "Connecting to server"
APIVOID_TEST_CONNECTIVITY_PASS_MSG = "Test Connectivity Passed"
APIVOID_TEST_CONNECTIVITY_FAIL_MSG = "Test Connectivity Failed"
APIVOID_DEFAULT_REQUEST_TIMEOUT = 30
