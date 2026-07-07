# File: snowflake_consts.py
#
# Copyright (c) 2023-2026 Splunk Inc.
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

# Database admin config parameters
SNOWFLAKE_DATABASE = "SNOWFLAKE"
SNOWFLAKE_ACCOUNT_ADMIN_ROLE = "ACCOUNTADMIN"
DEFAULT_NUM_ROWS_TO_FETCH = 100

# Test connectivity constants
SNOWFLAKE_VERSION_QUERY = "select current_version();"
TEST_CONNECTIVITY_PROGRESS_MSG = "Connecting to Snowflake endpoint"

# Action SQL statements
DESCRIBE_SNOWFLAKE_USER_SQL = "desc user {username};"
DISABLE_SNOWFLAKE_USER_SQL = "alter user {username} set disabled=true;"
SHOW_NETWORK_POLICIES_SQL = "show network policies;"
DESCRIBE_NETWORK_POLICY_SQL = "describe network policy {policy_name};"
UPDATE_NETWORK_POLICY_SQL = (
    "alter network policy {policy_name} set allowed_ip_list=({allowed_ip_list}) blocked_ip_list=({blocked_ip_list}) comment='{comment}';"
)
REMOVE_GRANTS_SQL = "revoke role {role_to_remove} from user {username};"

# Action error messages
TEST_CONNECTIVITY_ERROR_MSG = "Test connectivity failed"
SQL_QUERY_ERROR_MSG = "SQL query failed"
DISABLE_USER_ERROR_MSG = "Disable user failed"
SHOW_NETWORK_POLICIES_ERROR_MSG = "Show network policies failed"
DESCRIBE_NETWORK_POLICY_ERROR_MSG = "Describe network policy failed"

# Action success messages
TEST_CONNECTIVITY_SUCCESS_MSG = "Test connectivity passed"
REMOVE_GRANTS_SUCCESS_MSG = "Role {role} was successfully removed from user"
UPDATE_NETWORK_POLICY_SUCCESS_MSG = "Network policy {policy_name} was updated successfully"

# Default error messages
SNOWFLAKE_ERROR_CODE_UNAVAILABLE = "Unavailable"
SNOWFLAKE_ERROR_MSG_UNAVAILABLE = "Unavailable. Please check the asset configuration and|or the action parameters."

SNOWFLAKE_TOTAL_ROWS_JSON = "total_rows"
