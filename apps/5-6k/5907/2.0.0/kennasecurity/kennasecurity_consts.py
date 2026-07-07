# File: kennasecurity_consts.py
#
# Copyright (c) 2018-2022 Splunk Inc.
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
KENNA_CONFIG_RISK_TOKEN = 'risk_token'
KENNA_API_BASE_URL = 'https://api.kennasecurity.com'
KENNA_USERS_ENDPOINT = '/users'
KENNA_VULNERABILITY_SEARCH_ENDPOINT = '/vulnerabilities/search'
KENNA_ASSET_SEARCH_ENDPOINT = '/assets/search'
KENNA_GET_VULNERABILITIES_ENDPOINT = '/assets/{id}/vulnerabilities'
KENNA_VULNERABILITIES_ENDPOINT = '/vulnerabilities/{id}'
KENNA_CONNECTORS_ENDPOINT = '/connectors'
KENNA_RUN_CONNECTOR_ENDPOINT = '/connectors/{id}/data_file'
KENNA_FIXES_SEARCH_ENDPOINT = '/fixes/search'
KENNA_ASSET_ENDPOINT = '/assets/{id}'
KENNA_JSON_IP = 'ip'
KENNA_JSON_HOSTNAME = 'hostname'
KENNA_JSON_VAULT_ID = 'vault_id'
KENNA_JSON_SEARCH = 'search'
KENNA_JSON_VULNERABILITY_ID = 'vulnerability_id'
KENNA_JSON_DEVICE_ID = 'device_id'
KENNA_JSON_VULNERABILITY_STATUS = 'vulnerability_status'
KENNA_JSON_ACTIVE = 'active'
KENNA_JSON_CONNECTOR = 'connector'
KENNA_JSON_FILTER_TYPE = 'filter_type'
KENNA_JSON_FILTER = 'filter'
KENNA_JSON_NOTES = 'notes'
KENNA_JSON_PRIORITY = 'priority'
KENNA_JSON_DUE_DATE = 'due_date'
KENNA_JSON_OWNER = 'owner'
KENNA_JSON_TAGS = 'tags'
KENNA_CONST_TRUE = 'True'
KENNA_CONST_FALSE = 'False'
KENNA_CONST_ALL = 'All'
KENNA_CONST_OPEN = 'Open'
KENNA_CONST_CLOSED = 'Closed'
KENNA_CONST_RISK_ACCEPTED = 'Risk accepted'
KENNA_CONST_FALSE_POSITIVE = 'False positive'
KENNA_CONST_IP = 'IP'
KENNA_CONST_HOSTNAME = 'Hostname'
KENNA_CONST_MAC_ADDR = 'MAC Address'
KENNA_FILTER_IP = 'ip_address'
KENNA_FILTER_HOSTNAME = 'hostname'
KENNA_FILTER_MAC_ADDR = 'mac_address'
KENNA_FILTER_OPEN = 'open'
KENNA_FILTER_CLOSED = 'closed'
KENNA_FILTER_RISK_ACCEPTED = 'risk_accepted'
KENNA_FILTER_FALSE_POSITIVE = 'false_positive'
KENNA_FILTER_MISSING_MSG = 'Filter value needs to be provided for given type'
KENNA_FILTER_TYPE_MISSING_MSG = 'Filter type needs to be set for given value'
KENNA_ID_VALIDATION_FAILED_MSG = 'ID should be a positive integer'
KENNA_PARAM_VALIDATION_FAILED_MSG = 'Parameter validation failed. Invalid {}'
KENNA_DATE_VALIDATION_FAILED_MSG = 'Incorrect date format, please enter date in YYYY-MM-DD or valid iso8061 format.'
KENNA_TEST_CONNECTIVITY_FAILED_MSG = 'Test connectivity failed'
KENNA_TEST_CONNECTIVITY_PASSED_MSG = 'Test connectivity passed'
KENNA_MAKING_CONNECTION_MSG = 'Making Connection...'
KENNA_USERS_FOUND_MSG = 'User information retrieved.'
KENNA_TEST_CONNECTIVITY_TIMEOUT = 30
