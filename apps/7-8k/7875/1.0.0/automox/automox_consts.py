# File: automox_consts.py
#
# Copyright (c) Automox, 2025
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
AUTOMOX_CONSOLE_API_URL = "https://console.automox.com/api"
AUTOMOX_CONSOLE_API_KEY = "ax_console_api_key"  # pragma: allowlist secret

# Endpoints
AUTOMOX_ORGS_LIST_ENDPOINT = "/orgs"
AUTOMOX_USERS_LIST_ENDPOINT = "/users"
AUTOMOX_USERS_LIST_SPECIFIC_ENDPOINT = "/users/{user_id}"
AUTOMOX_USERS_SELF_ENDPOINT = "/users/self"
AUTOMOX_GROUPS_LIST_ENDPOINT = "/servergroups"
AUTOMOX_POLICY_LIST_ENDPOINT = "/policies"
AUTOMOX_POLICY_LIST_SPECIFIC_ENDPOINT = "/policies/{policy_id}"
AUTOMOX_POLICY_RUN_ENDPOINT = "/policies/{policy_id}/action"
AUTOMOX_DEVICE_LIST_ENDPOINT = "/servers"
AUTOMOX_DEVICE_SPECIFIC_ENDPOINT = "/servers/{device_id}"
AUTOMOX_DEVICE_LIST_PACKAGES_ENDPOINT = "/servers/{device_id}/packages"
AUTOMOX_PACKAGE_LIST_ALL_ENDPOINT = "/orgs/{org_id}/packages"
AUTOMOX_COMMAND_QUEUE_LIST_ENDPOINT = "/servers/{device_id}/queues"
AUTOMOX_REMOVE_USER_FROM_ACCOUNT_ENDPOINT = "/accounts/{account_uuid}/users/{user_uuid}"
