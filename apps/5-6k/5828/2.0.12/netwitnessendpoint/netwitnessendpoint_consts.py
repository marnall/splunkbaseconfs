# File: netwitnessendpoint_consts.py
#
# Copyright (c) 2018-2025 Splunk Inc.
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

NWENDPOINT_CONFIG_URL = "url"
NWENDPOINT_CONFIG_USERNAME = "username"
NWENDPOINT_CONFIG_PASSWORD = "password"  # pragma: allowlist secret
NWENDPOINT_CONFIG_VERIFY_SSL = "verify_server_cert"
NWENDPOINT_CONFIG_MAX_IOC_LEVEL = "max_ioc_level"
NWENDPOINT_CONFIG_MAX_IOC_COUNT_SCHEDULED_POLL = "max_ioc_for_scheduled_poll"
NWENDPOINT_DEFAULT_IOC_LEVEL = 2
NWENDPOINT_DEFAULT_IOC_COUNT = 5
NWENDPOINT_TEST_CONNECTIVITY_ENDPOINT = "/api/v2/health?format=json"
NWENDPOINT_BLOCKLIST_DOMAIN_ENDPOINT = "/api/v2/blacklist/domain?format=json"
NWENDPOINT_BLOCK_IP_ENDPOINT = "/api/v2/blacklist/ip?format=json"
NWENDPOINT_GET_SCAN_DATA_ENDPOINT = "/api/v2/machines/{}/scandata/{}?format=json"
NWENDPOINT_INSTANTIOCS_PER_MACHINE_ENDPOINT = "/api/v2/machines/{guid}/instantiocs?format=json"
NWENDPOINT_SCAN_ENDPOINT = "/api/v2/machines/{}/scan?format=json"
NWENDPOINT_GET_SYSTEM_INFO_ENDPOINT = "/api/v2/machines/{}?format=json"
NWENDPOINT_INSTANTIOC_ENDPOINT = "/api/v2/instantiocs?format=json"
NWENDPOINT_MACHINES_MODULES_ENDPOINT = "/api/v2/machines/{}/modules?format=json"
NWENDPOINT_MACHINES_MODULES_INSTANTIOCS_ENDPOINT = "/api/v2/machines/{}/modules/{}/instantiocs?format=json"
NWENDPOINT_LIST_MACHINES_ENDPOINT = "/api/v2/machines?format=json"
NWENDPOINT_CONNECTION_TEST_MSG = "Querying endpoint to verify the credentials provided"
NWENDPOINT_TEST_CONNECTIVITY_FAIL = "Test Connectivity Failed"
NWENDPOINT_TEST_CONNECTIVITY_PASS = "Test Connectivity Passed"
NWENDPOINT_ERROR_SERVER_CONNECTION = "Connection failed: {0}"
NWENDPOINT_ERROR_API_UNSUPPORTED_METHOD = "Unsupported method {method}"
NWENDPOINT_EXCEPTION_OCCURRED = "Exception occurred"
NWENDPOINT_ERROR_IOC_QUERY_NOT_EXIST = "IIOC name not found"
NWENDPOINT_REST_RESP_UNAUTHORIZED = 401
NWENDPOINT_REST_RESP_UNAUTHORIZED_MSG = "Invalid username or password"
NWENDPOINT_REST_RESP_SUCCESS = 200
NWENDPOINT_REST_REQUEST_BINDING_EXCEPTION = 400
NWENDPOINT_REST_REQUEST_BINDING_EXCEPTION_MSG = "Unable to bind request"
NWENDPOINT_REST_INVALID_PERMISSION = 403
NWENDPOINT_REST_INVALID_PERMISSION_MSG = "Invalid permission"
NWENDPOINT_REST_RESOURCE_NOT_FOUND = 404
NWENDPOINT_REST_RESOURCE_NOT_FOUND_MSG = "Request not found"
NWENDPOINT_REST_RESPONSE = "response"
NWENDPOINT_REST_RESPONSE_HEADERS = "headers"
NWENDPOINT_REST_RESP_OTHER_ERROR_MSG = "Error returned"
NWENDPOINT_ERROR_FROM_SERVER = "API failed.\nStatus code: {status}\nDetail: {detail}"
NWENDPOINT_ERROR_JSON_PARSE = "Unable to parse the response into a dictionary.\nResponse text - {raw_text}"
NWENDPOINT_JSON_DOMAIN = "domain"
NWENDPOINT_JSON_GUID = "guid"
NWENDPOINT_JSON_LIMIT = "limit"
NWENDPOINT_JSON_NAME = "name"
NWENDPOINT_JSON_IP_ADDRESS = "ip"
NWENDPOINT_JSON_IOC_SCORE_GTE = "iocscore_gte"
NWENDPOINT_JSON_IOC_SCORE_LTE = "iocscore_lte"
NWENDPOINT_JSON_SCAN_CATEGORY = "scan_category"
NWENDPOINT_JSON_CAPTURE_FLOATING_CODE = "capture_floating_code"
NWENDPOINT_JSON_ALL_NETWORK_CONNECTIONS = "all_network_connections"
NWENDPOINT_JSON_FILTER_HOOKS = "filter_hooks"
NWENDPOINT_JSON_RESET_AGENT_NETWORK_CACHE = "reset_agent_network_cache"
NWENDPOINT_JSON_RETRIEVE_MASTER_BOOT_RECORD = "retrieve_master_boot_record"
NWENDPOINT_JSON_CPUMAX = "cpu_max"
NWENDPOINT_JSON_CPUMAXVM = "cpu_max_vm"
NWENDPOINT_JSON_CPUMIN = "cpu_min"
NWENDPOINT_JSON_NOTIFY = "notify"
NWENDPOINT_JSON_INVALID_LIMIT = "Maximum number of records to be fetched must be a positive integer"
NWENDPOINT_JSON_INVALID_MACHINE_COUNT = "Please provide a valid positive integer for MachineCount"
NWENDPOINT_JSON_INVALID_MODULE_COUNT = "Please provide a valid positive integer for ModuleCount"
NWENDPOINT_JSON_IOC_SCORE_PARAM_ERROR = "Please provide a valid positive integer for filtering IOC Score"
NWENDPOINT_JSON_IOC_SCORE_PARAM_OUT_OF_RANGE = "IOC score must be a positive integer less than or equal to 1024"
NWENDPOINT_JSON_IOC_SCORE_COMPARISION_ERROR = "{upper_bound_var} must be greater than or equal to {lower_bound_var}"
NWENDPOINT_JSON_CPU_MAX_ERROR = "Please provide a valid positive integer for CPU Max"
NWENDPOINT_PERCENTAGE_ERROR = "Value of {perc_var} must not be greater than 100"
NWENDPOINT_JSON_CPU_MAX_VM_ERROR = "Please provide a valid positive integer for CPU Max VM"
NWENDPOINT_JSON_CPU_MIN_ERROR = "Please provide a valid positive integer for CPU Min"
NWENDPOINT_SCAN_ENDPOINT_MSG = "Start Scanning successful"
NWENDPOINT_DEFAULT_POLL_NOW_CONTAINER_COUNT = 5
NWENDPOINT_CONTAINER_ERROR = "Error while creating container"
NWENDPOINT_ARTIFACTS_DESC = "Artifact created by NetWitness Endpoint app"
NWENDPOINT_DEFAULT_LIMIT = 50
NWENDPOINT_BLOCKLIST_DOMAIN_SUCCESS = "Domain blocklisted successfully"
NWENDPOINT_BLOCKLIST_IP_SUCCESS = "IP blocklisted successfully"
NWENDPOINT_JSON_MACHINE_COUNT = "machine_count"
NWENDPOINT_JSON_MODULE_COUNT = "module_count"
NWENDPOINT_DEFAULT_FILTER_HOOKS = "Signed Modules"
NWENDPOINT_DEFAULT_SCAN_CATEGORY = "All"
NWENDPOINT_DEFAULT_MIN_CPU_VALUE = 20
NWENDPOINT_DEFAULT_MAX_CPU_VALUE = 95
NWENDPOINT_DEFAULT_MAX_CPU_VM_VALUE = 25
NWENDPOINT_DEFAULT_IOC_SCORE_GTE = 0
NWENDPOINT_DEFAULT_IOC_SCORE_LTE = 1024
NWENDPOINT_DEFAULT_MIN_MACHINE_COUNT = 0
NWENDPOINT_DEFAULT_MIN_MODULE_COUNT = 0
INVALID_INT = "Please provide a valid integer value in the {param}"
ERROR_NEGATIVE_INT_PARAM = "Please provide a valid non-negative integer value in the {param}"
