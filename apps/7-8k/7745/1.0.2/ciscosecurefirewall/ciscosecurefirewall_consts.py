# File: ciscosecurefirewall_consts.py
#
# Copyright (c) 2025 Splunk Inc.
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

TOKEN_ENDPOINT = "/api/fmc_platform/v1/auth/generatetoken"
REFRESH_ENDPOINT = "/api/fmc_platform/v1/auth/refreshtoken"
HEADERS = {"Accept": "application/json"}
STATE_FILE_CORRUPT_ERR = "Error occurred while loading the state file due to its unexpected format"
DEFAULT_REQUEST_TIMEOUT = 30  # in seconds
TOKEN_KEY = "X-auth-access-token"
REFRESH_TOKEN_KEY = "X-auth-refresh-token"
REFRESH_COUNT = "REFRESH_COUNT"
GET_HOSTS_ENDPOINT = "/api/fmc_config/v1/domain/{domain_id}/object/hosts"
ENCRYPTION_ERR = "Error occurred while encrypting the state file"
NETWORK_GROUPS_ENDPOINT = "/api/fmc_config/v1/domain/{domain_id}/object/networkgroups"
NETWORK_GROUPS_ID_ENDPOINT = "/api/fmc_config/v1/domain/{domain_id}/object/networkgroups/{group_id}"
NETWORK_OBJECTS_ENDPOINT = "/api/fmc_config/v1/domain/{domain_id}/object/{type}"
NETWORK_OBJECT_ID_ENDPOINT = "/api/fmc_config/v1/domain/{domain_id}/object/{type}/{object_id}"
ACCESS_POLICY_ENDPOINT = "/api/fmc_config/v1/domain/{domain_id}/policy/accesspolicies"
ACCESS_POLICY_ID_ENDPOINT = "/api/fmc_config/v1/domain/{domain_id}/policy/accesspolicies/{policy_id}"
ACCESS_RULES_ENDPOINT = "/api/fmc_config/v1/domain/{domain_id}/policy/accesspolicies/{policy_id}/accessrules"
ACCESS_RULES_ID_ENDPOINT = "/api/fmc_config/v1/domain/{domain_id}/policy/accesspolicies/{policy_id}/accessrules/{rule_id}"
DEVICES_ENDPOINT = "/api/fmc_config/v1/domain/{domain_id}/devices/devicerecords"
GET_DEPLOYABLE_DEVICES_ENDPOINT = "/api/fmc_config/v1/domain/{domain_id}/deployment/deployabledevices"
DEPLOY_DEVICES_ENDPOINT = "/api/fmc_config/v1/domain/{domain_id}/deployment/deploymentrequests"
DEPLOYMENT_STATUS_ENDPOINT = "/api/fmc_config/v1/domain/{domain_id}/job/taskstatuses/{task_id}"
INTRUSION_POLICY_ENDPOINT = "/api/fmc_config/v1/domain/{domain_id}/policy/intrusionpolicies"
INTRUSION_POLICY_ID_ENDPOINT = "/api/fmc_config/v1/domain/{domain_id}/policy/intrusionpolicies/{policy_id}"
OBJECT_TYPES = ["Network", "Host", "Range"]
CLOUD_HOST = "edge.{region}.cdo.cisco.com/api/rest/v1/cdfmc"
