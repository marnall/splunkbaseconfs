# File: microsoftscom_consts.py
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
#
#
# Define your constants here
MSSCOM_CONFIG_SERVER_URL = "server_url"
MSSCOM_CONFIG_USERNAME = "username"
MSSCOM_CONFIG_PASSWORD = "password"  # pragma: allowlist secret
MSSCOM_CONFIG_VERIFY_SSL = "verify_server_cert"
MSSCOM_SERVER_URL = "{url}/wsman"
MSSCOM_CONNECTING_ENDPOINT_MSG = "Connecting to endpoint"
MSSCOM_ERROR_SERVER_CONNECTION = "Connection failed"
MSSCOM_TRANSPORT_ERROR = "Connection error: Bad configuration in SCOM"
MSSCOM_ERROR_BAD_HANDSHAKE = "Bad Handshake"
MSSCOM_INVALID_CREDENTIAL_ERROR = "Invalid Credentials"
MSSCOM_EXCEPTION_OCCURRED = "Exception occurred"
MSSCOM_TEST_CONNECTIVITY_FAIL = "Test Connectivity Failed"
MSSCOM_TEST_CONNECTIVITY_PASS = "Test Connectivity Passed"
MSSCOM_PS_COMMAND = 'powershell -command "{command}"'
MSSCOM_PARAM_DOMAIN = "domain"
MSSCOM_GET_SCOM_AGENT_COMMAND = "Get-SCOMAgent"
MSSCOM_GET_SCOM_ALERT_COMMAND = "Get-SCOMAlert"
MSSCOM_CONVERT_TO_CSV_JSON_COMMAND = "ConvertTo-Csv | ConvertFrom-Csv | ConvertTo-Json"
MSSCOM_PARAM_COMPUTER_NAME = "computer_name"
MSSCOM_JSON_FORMAT_ERROR = "JSON format error"
MSSCOM_PARAM_NOT_SPECIFIED = "Neither {0} nor {1} specified. Please specify at least one of them."
