#!/usr/bin/python
# File: ciscomeraki_consts.py
#
# Copyright (c) 2025-2026 Splunk Inc.
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

# API path for Meraki
API_PATH = "/api/v1"

# Messages
EXECUTION_START_MSG = "Executing {0} action"
TEST_CONNECTIVITY_START_MSG = "Connecting to {0}"
SUCCESS_TEST_CONNECTIVITY = "Test Connectivity Passed"
ERROR_TEST_CONNECTIVITY = "Test Connectivity Failed"
ACTION_SUCCESS_RESPONSE = "Action {action} has been executed successfully"

# Error Messages
ERROR_INVALID_INT_PARAM = "Please provide a valid integer value in the '{key}' parameter"
ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
ERROR_GENERAL_MESSAGE = "Status code: {0}, Data from server: {1}"
ERROR_HTML_RESPONSE = "Error parsing html response"
ERROR_ZERO_INT_PARAM = "Please provide a non-zero positive integer value in the '{key}' parameter"
ERROR_NEG_INT_PARAM = "Please provide a positive integer value in the '{key}' parameter"
ERROR_REQUIRED_PARAM = "Required parameter '{key}' not specified"
ERROR_INVALID_PARAM = "Please provide a valid value for parameter '{key}'"

# API Endpoints
# Organization endpoints
LIST_ORGANIZATIONS = "/organizations"
ORG_LICENSE_STATE = "/organizations/{organization_id}/licenseState"
ORG_INVENTORY_DEVICES = "/organizations/{organization_id}/inventory/devices"
CLAIM_DEVICES = "/organizations/{organization_id}/inventory/devices/claim"

# Device endpoints
SEARCH_DEVICES = "/organizations/{organization_id}/devices"
LIST_DEVICES = "/networks/{network_id}/devices"
UPDATE_DEVICE = "/networks/{network_id}/devices/{serial}"
REMOVE_DEVICE = "/networks/{network_id}/devices/{serial}"
LIST_DEVICE_CLIENTS = "/devices/{serial}/clients"

# Adaptive Policy endpoints
LIST_ADAPTIVE_POLICIES = "/organizations/{organization_id}/adaptivePolicy/policies"
LIST_ADAPTIVE_POLICY_ACLS = "/organizations/{organization_id}/adaptivePolicy/acls"
LIST_ADAPTIVE_POLICY_GROUPS = "/organizations/{organization_id}/adaptivePolicy/groups"
LIST_ADAPTIVE_POLICY_SETTINGS = "/organizations/{organization_id}/adaptivePolicy/settings"

# Firewall endpoints
LIST_L3_FIREWALL_RULES = "/networks/{network_id}/appliance/firewall/l3FirewallRules"
UPDATE_L3_FIREWALL_RULES = "/networks/{network_id}/appliance/firewall/l3FirewallRules"
LIST_L7_FIREWALL_RULES = "/networks/{network_id}/appliance/firewall/l7FirewallRules"
UPDATE_L7_FIREWALL_RULES = "/networks/{network_id}/appliance/firewall/l7FirewallRules"

# Request Parameters
REQUEST_DEFAULT_TIMEOUT = 30
EMPTY_RESPONSE_STATUS_CODES = [200, 204]
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000

# Auth Headers
AUTH_HEADER = "X-Cisco-Meraki-API-Key"

# Entity Types
ORGANIZATION = "organization"
NETWORK = "network"
DEVICE = "device"
CLIENT = "client"
FIREWALL_RULE = "firewall_rule"

# Firewall Rule Properties
L3_RULE_REQUIRED_FIELDS = ["policy", "protocol", "srcPort", "srcCidr", "destPort", "destCidr", "comment"]
L7_RULE_REQUIRED_FIELDS = ["policy", "type", "value"]

# Parameter Validation
MIN_PAGE_SIZE = 3
MAX_PAGE_SIZE = 1000
VALID_POLICIES = ["allow", "deny"]
VALID_PROTOCOLS = ["tcp", "udp", "icmp", "any"]
VALID_TYPES = ["application", "applicationCategory", "host", "port", "ipRange"]

# Rate limiting constants
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1  # seconds

# API URLs and endpoints
MERAKI_API_BASE_URL = "https://api.meraki.com/api/v1/{}"

# Response codes
EMPTY_RESPONSE_STATUS_CODES = [200, 204]

# Request defaults
REQUEST_DEFAULT_TIMEOUT = 30

# Error messages
ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
