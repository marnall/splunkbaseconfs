# File: mysql_consts.py
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
# Parameters
MYSQL_TABLE_NAME_JSON = "table_name"
MYSQL_FORMAT_VARS_JSON = "format_vars"
MYSQL_QUERY_JSON = "query"
MYSQL_NO_COMMIT_JSON = "no_commit"
MYSQL_USERNAME_JSON = "username"
MYSQL_PASSWORD_JSON = "password"  # pragma: allowlist secret
MYSQL_DATABASE_JSON = "database"
MYSQL_HOST_JSON = "host"
MYSQL_VERIFY_SERVER_CERT_JSON = "verify_ssl"
MYSQL_TOTAL_ROWS_JSON = "total_rows"

# Queries
MYSQL_VERSION_QUERY = "SELECT version()"
MYSQL_DESCRIBE_TABLE_QUERY = "DESCRIBE {0};"
MYSQL_SHOW_TABLE_QUERY = "SHOW TABLES;"

# Status messages
MYSQL_ERR_CODE_UNAVAILABLE = "Error code unavailable"
MYSQL_ERR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or the action parameters."
MYSQL_TEST_CONNECTIVITY_ERR = "Test Connectivity Failed"
MYSQL_TEST_CONNECTIVITY_SUCC = "Test Connectivity Passed"
MYSQL_INVALID_TABLE_NAME_ERR = "Table name did not pass validation"
MYSQL_COLUMN_LIST_ERR = "Unable to list columns. {}"
MYSQL_RUN_QUERY_ERR = "Unable to run query. {}"
MYSQL_DB_COMMIT_ERR = "Unable to commit changes. {}"
MYSQL_RUN_QUERY_SUCC = "Successfully ran query"
MYSQL_TEST_DB_CONNECTION_MSG = "Testing database connection"
MYSQL_INIT_DB_CONNECTION_MSG = "Starting db initialization"
MYSQL_DB_LOGIN_ERR = "db login error. {}"
MYSQL_DB_CONNECTION_ERR = "Connection failed"
MYSQL_DB_CONNECTION_SUCC = "Database connection established"

# Action names
MYSQL_TEST_CONNECTIVITY_ACTION = "test_connectivity"
MYSQL_LIST_COLUMNS_ACTION = "list_columns"
MYSQL_LIST_TABLES_ACTION = "list_tables"
MYSQL_RUN_QUERY_ACTION = "run_query"
