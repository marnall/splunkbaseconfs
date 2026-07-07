# File: mysql_connector.py
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
# Phantom App imports
import csv
import datetime
import json
import re

import phantom.app as phantom
import pymysql
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from mysql_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class MysqlConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None
        self._my_connection = None

    def _get_error_message_from_exception(self, e):
        """This method is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = MYSQL_ERR_CODE_UNAVAILABLE
        error_msg = MYSQL_ERR_MSG_UNAVAILABLE

        try:
            if e.args:
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except:
            pass

        return f"Error Code: {error_code}. Error Message: {error_msg}"

    def convert_value(self, value):
        if isinstance(value, (bytearray, bytes)):
            return value.decode("utf-8")
        elif isinstance(value, (datetime.datetime, datetime.timedelta, datetime.date)):
            return str(value)
        else:
            return value

    def _cleanup_row_values(self, row):
        # The MySQL column values is supposed to be a bytearray as opposed to a string
        return {k: self.convert_value(v) for k, v in row.items()}

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector)
        # to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress(MYSQL_TEST_DB_CONNECTION_MSG)
        cursor = self._my_connection.cursor()

        query = MYSQL_VERSION_QUERY

        cursor.execute(query)
        if cursor:
            self.save_progress(MYSQL_TEST_CONNECTIVITY_SUCC)
            return action_result.set_status(phantom.APP_SUCCESS)
        else:
            return action_result.set_status(phantom.APP_ERROR, MYSQL_DB_CONNECTION_ERR)

    def _handle_list_columns(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector)
        # to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        my_table = param[MYSQL_TABLE_NAME_JSON]
        if not re.match(r"^[a-zA-Z0-9$_]+$", my_table):
            return action_result.set_status(phantom.APP_ERROR, MYSQL_INVALID_TABLE_NAME_ERR)

        query = MYSQL_DESCRIBE_TABLE_QUERY.format(my_table)
        cursor = self._my_connection.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute(query)
        except Exception as e:
            error_msg = self._get_error_message_from_exception(e)
            self.save_progress(f"Error: {error_msg}")
            return action_result.set_status(phantom.APP_ERROR, MYSQL_COLUMN_LIST_ERR.format(error_msg))

        for row in cursor:
            action_result.add_data(self._cleanup_row_values(row))

        summary = action_result.update_summary({})
        summary[MYSQL_TOTAL_ROWS_JSON] = cursor.rowcount

        self.save_progress(f"Action: {self.get_action_identifier()} - Status: {phantom.APP_SUCCESS}")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_tables(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector)
        # to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        query = MYSQL_SHOW_TABLE_QUERY
        cursor = self._my_connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query)
        for row in cursor:
            row = self._cleanup_row_values(row)
            # Rename column name so it will be the same for every asset
            #  running the app
            # There should only be one column per row, but let's double check first
            if len(row) == 1:
                row = dict(table_name=next(iter(row.values())))
            action_result.add_data(row)

        summary = action_result.update_summary({})
        summary[MYSQL_TOTAL_ROWS_JSON] = cursor.rowcount

        self.save_progress(f"Action: {self.get_action_identifier()} - Status: {phantom.APP_SUCCESS}")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_format_vars(self, param):
        format_vars = param.get(MYSQL_FORMAT_VARS_JSON)
        if format_vars:
            format_vars = next(csv.reader([format_vars], quotechar='"', skipinitialspace=True, escapechar="\\"))
        return format_vars

    def _handle_run_query(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector)
        # to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        my_query = param.get(MYSQL_QUERY_JSON)
        format_vars = self._get_format_vars(param)

        cursor = self._my_connection.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute(my_query, format_vars)
        except Exception as e:
            error_msg = self._get_error_message_from_exception(e)
            self.save_progress(f"Error: {error_msg}")
            return action_result.set_status(phantom.APP_ERROR, MYSQL_RUN_QUERY_ERR.format(error_msg))

        for row in cursor:
            action_result.add_data(self._cleanup_row_values(row))

        if not param.get(MYSQL_NO_COMMIT_JSON, False):
            try:
                self._my_connection.commit()
            except Exception as e:
                error_msg = self._get_error_message_from_exception(e)
                self.save_progress(f"Error: {error_msg}")
                return action_result.set_status(phantom.APP_ERROR, MYSQL_DB_COMMIT_ERR.format(error_msg))

        summary = action_result.update_summary({})

        # cursor.rowcount returns -1 if no rows returned
        if cursor.rowcount > 0:
            summary[MYSQL_TOTAL_ROWS_JSON] = cursor.rowcount
        else:
            summary[MYSQL_TOTAL_ROWS_JSON] = 0

        self.save_progress(f"Action: {self.get_action_identifier()} - Status: {phantom.APP_SUCCESS}")
        return action_result.set_status(phantom.APP_SUCCESS, MYSQL_RUN_QUERY_SUCC)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == MYSQL_TEST_CONNECTIVITY_ACTION:
            ret_val = self._handle_test_connectivity(param)

        elif action_id == MYSQL_LIST_COLUMNS_ACTION:
            ret_val = self._handle_list_columns(param)

        elif action_id == MYSQL_LIST_TABLES_ACTION:
            ret_val = self._handle_list_tables(param)

        elif action_id == MYSQL_RUN_QUERY_ACTION:
            ret_val = self._handle_run_query(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()

        self.save_progress(MYSQL_INIT_DB_CONNECTION_MSG)
        try:
            # Configure SSL certificate verification based on asset setting
            # Defaults to False for backward compatibility with self-signed certificates
            # Python 3.13 has stricter SSL/TLS defaults, so explicit configuration is required
            verify_ssl = config.get(MYSQL_VERIFY_SERVER_CERT_JSON, False)
            ssl_config = {"ssl_verify_cert": verify_ssl, "ssl_verify_identity": verify_ssl}

            self._my_connection = pymysql.connect(
                user=config[MYSQL_USERNAME_JSON],
                password=config[MYSQL_PASSWORD_JSON],
                database=config[MYSQL_DATABASE_JSON],
                host=config[MYSQL_HOST_JSON],
                ssl=ssl_config,
            )
            # self._my_connection.autocommit = True
        except pymysql.Error as e:
            error_msg = self._get_error_message_from_exception(e)
            if self.get_action_identifier() == MYSQL_TEST_CONNECTIVITY_ACTION:
                self.save_progress(MYSQL_DB_LOGIN_ERR.format(error_msg))
                self.set_status(phantom.APP_ERROR, MYSQL_TEST_CONNECTIVITY_ERR)
            else:
                self.set_status(phantom.APP_ERROR, MYSQL_DB_LOGIN_ERR.format(error_msg))
            return phantom.APP_ERROR
        self.save_progress(MYSQL_DB_CONNECTION_SUCC)

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved accross actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == "__main__":
    import sys

    import pudb

    pudb.set_trace()

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = MysqlConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
