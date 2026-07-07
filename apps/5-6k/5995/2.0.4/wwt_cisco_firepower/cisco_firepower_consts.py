# File: cisco_firepower_consts.py
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

HOST_NETWORK_GROUPS_ENDPOINT = "/api/fmc_config/v1/domain/{0}/object/networkgroups/{1}"
DEPLOYMENT_REQUESTS_ENDPOINT = "/api/fmc_config/v1/domain/{0}/deployment/deploymentrequests"
DEPLOYABLE_DEVICES_ENDPOINT = "/api/fmc_config/v1/domain/{0}/deployment/deployabledevices?limit={1}&expanded={2}"
NETWORK_GROUPS_ENDPOINT = "/api/fmc_config/v1/domain/{0}/object/networkgroups"
TOKEN_ENDPOINT = "/api/fmc_platform/v1/auth/generatetoken"
HEADERS = {"Accept": "application/json"}
STATE_FILE_CORRUPT_ERR = "Error occurred while loading the state file due to its unexpected format"
DEFAULT_REQUEST_TIMEOUT = 30  # in seconds
TOKEN_KEY = "X-auth-access-token"
DOMAIN_UUID_KEY = "domain_uuid"
DOMAIN_NAME_KEY = "domain_name"
ENCRYPTION_ERR = "Error occurred while encrypting the state file"
LIMIT = 100
EXPANDED = "true"
