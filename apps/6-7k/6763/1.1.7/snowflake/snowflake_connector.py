# File: snowflake_connector.py
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

# Import order matters here - if isort is allowed to put the Snowflake connector
# import later in the file, the connector crashes at runtime.
import snowflake.connector  # isort: skip
from snowflake_consts import *  # isort: skip

import datetime
import json
import traceback

# Phantom App imports
import phantom.app as phantom
import requests
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class SnowflakeConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        self._account = None
        self._username = None
        self._password = None

    def _get_error_msg_from_exception(self, e):
        error_code = SNOWFLAKE_ERROR_CODE_UNAVAILABLE
        error_msg = SNOWFLAKE_ERROR_MSG_UNAVAILABLE

        self.error_print(traceback.format_exc())

        try:
            if e.args:
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                    return f"Error Code: {error_code}. Error Message: {error_msg}"
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except Exception:
            pass

        return f"Error Message: {error_msg}"

    def convert_value(self, value):
        if isinstance(value, (bytearray, bytes)):
            return value.decode("utf-8")
        elif isinstance(value, (datetime.datetime, datetime.timedelta, datetime.date)):
            return str(value)
        else:
            return value

    def _cleanup_row_values(self, row):
        return {k: self.convert_value(v) for k, v in row.items()}

    def _handle_test_connectivity(self, param):
        self.save_progress(TEST_CONNECTIVITY_PROGRESS_MSG)

        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            self._connection = self._handle_create_connection()
            cursor = self._connection.cursor()

            cursor.execute(SNOWFLAKE_VERSION_QUERY)
            if cursor:
                self.save_progress(TEST_CONNECTIVITY_SUCCESS_MSG)
                return action_result.set_status(phantom.APP_SUCCESS)
        except Exception as e:
            self.save_progress(self._get_error_msg_from_exception(e))
            return action_result.set_status(phantom.APP_ERROR, TEST_CONNECTIVITY_ERROR_MSG)

    def _handle_run_query(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        query = param["query"]
        role = param.get("role")
        warehouse = param.get("warehouse")
        database = param.get("database")
        schema = param.get("schema")

        try:
            self._connection = self._handle_create_connection(role, warehouse, database, schema)
            cursor = self._connection.cursor(snowflake.connector.DictCursor)
            cursor.execute(query)
            returned_rows = cursor.fetchmany(DEFAULT_NUM_ROWS_TO_FETCH)

            for row in returned_rows:
                action_result.add_data(self._cleanup_row_values(row))

            while len(returned_rows) > 0:
                returned_rows = cursor.fetchmany(DEFAULT_NUM_ROWS_TO_FETCH)
                for row in returned_rows:
                    action_result.add_data(self._cleanup_row_values(row))
        except Exception as e:
            error_msg = self._get_error_msg_from_exception(e)
            self.save_progress(f"Error: {error_msg}")
            return action_result.set_status(phantom.APP_ERROR, f"{SQL_QUERY_ERROR_MSG}: {error_msg}")
        finally:
            if self._connection:
                cursor.close()
                self._connection.close()

        summary = action_result.update_summary({})

        if cursor.rowcount > 0:
            summary[SNOWFLAKE_TOTAL_ROWS_JSON] = cursor.rowcount
        else:
            summary[SNOWFLAKE_TOTAL_ROWS_JSON] = 0

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_disable_user(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        database = SNOWFLAKE_DATABASE
        username = param["username"]
        role = param.get("role")

        try:
            self._connection = self._handle_create_connection(database=database, role=role)
            cursor = self._connection.cursor(snowflake.connector.DictCursor)
            cursor.execute(DISABLE_SNOWFLAKE_USER_SQL.format(username=username))
            row = cursor.fetchone()
            action_result.add_data(row)
        except Exception as e:
            error_msg = self._get_error_msg_from_exception(e)
            self.save_progress(f"Error: {error_msg}")
            return action_result.set_status(phantom.APP_ERROR, f"{DISABLE_USER_ERROR_MSG}: {error_msg}")
        finally:
            if self._connection:
                cursor.close()
                self._connection.close()

        summary = action_result.update_summary({})
        summary["user_status"] = "disabled"

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_show_network_policies(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        database = SNOWFLAKE_DATABASE
        role = param.get("role")

        try:
            self._connection = self._handle_create_connection(database=database, role=role)
            cursor = self._connection.cursor(snowflake.connector.DictCursor)
            cursor.execute(SHOW_NETWORK_POLICIES_SQL)
            returned_rows = cursor.fetchmany(DEFAULT_NUM_ROWS_TO_FETCH)
            for row in returned_rows:
                action_result.add_data(self._cleanup_row_values(row))
            self.debug_print(f"returned_rows: {returned_rows}")

            while len(returned_rows) > 0:
                returned_rows = cursor.fetchmany(DEFAULT_NUM_ROWS_TO_FETCH)
                for row in returned_rows:
                    action_result.add_data(self._cleanup_row_values(row))

        except Exception as e:
            error_msg = self._get_error_msg_from_exception(e)
            self.save_progress(f"Error: {error_msg}")
            return action_result.set_status(phantom.APP_ERROR, error_msg)
        finally:
            if self._connection:
                cursor.close()
                self._connection.close()

        summary = action_result.update_summary({})
        summary["total_policies"] = len(action_result.get_data())

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_describe_network_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        database = SNOWFLAKE_DATABASE
        role = param.get("role")

        policy_name = param["policy_name"]

        try:
            self._connection = self._handle_create_connection(database=database, role=role)
            cursor = self._connection.cursor(snowflake.connector.DictCursor)
            cursor.execute(DESCRIBE_NETWORK_POLICY_SQL.format(policy_name=policy_name))
            returned_rows = cursor.fetchmany(DEFAULT_NUM_ROWS_TO_FETCH)
            for row in returned_rows:
                action_result.add_data(self._cleanup_row_values(row))
            self.debug_print(f"returned_rows: {returned_rows}")

            while len(returned_rows) > 0:
                returned_rows = cursor.fetchmany(DEFAULT_NUM_ROWS_TO_FETCH)
                for row in returned_rows:
                    action_result.add_data(self._cleanup_row_values(row))

        except Exception as e:
            error_msg = self._get_error_msg_from_exception(e)
            self.save_progress(f"Error: {error_msg}")
            return action_result.set_status(phantom.APP_ERROR, error_msg)
        finally:
            if self._connection:
                cursor.close()
                self._connection.close()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_network_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        database = SNOWFLAKE_DATABASE
        policy_name = param["policy_name"]
        role = param.get("role")

        # Putting single quotes around each IP address in the list to satisfy SQL formatting. Empty string to clear.
        try:
            allowed_ip_list = param.get("allowed_ip_list")
            if allowed_ip_list:
                allowed_ip_list = ",".join(f"'{ip.strip()}'" for ip in allowed_ip_list.split(","))
            else:
                allowed_ip_list = ""

            blocked_ip_list = param.get("blocked_ip_list")
            if blocked_ip_list:
                blocked_ip_list = ",".join(f"'{ip.strip()}'" for ip in blocked_ip_list.split(","))
            else:
                blocked_ip_list = ""

            comment = param.get("comment")
        except Exception as e:
            error_msg = self._get_error_msg_from_exception(e)
            self.save_progress(f"Error: {error_msg}")
            return action_result.set_status(phantom.APP_ERROR, error_msg)

        try:
            self._connection = self._handle_create_connection(database=database, role=role)
            cursor = self._connection.cursor(snowflake.connector.DictCursor)
            cursor.execute(
                UPDATE_NETWORK_POLICY_SQL.format(
                    policy_name=policy_name, allowed_ip_list=allowed_ip_list, blocked_ip_list=blocked_ip_list, comment=comment
                )
            )
            row = cursor.fetchone()
            action_result.add_data(row)
        except Exception as e:
            error_msg = self._get_error_msg_from_exception(e)
            self.save_progress(f"Error: {error_msg}")
            return action_result.set_status(phantom.APP_ERROR, error_msg)
        finally:
            if self._connection:
                cursor.close()
                self._connection.close()

        return action_result.set_status(phantom.APP_SUCCESS, UPDATE_NETWORK_POLICY_SUCCESS_MSG.format(policy_name=policy_name))

    def _handle_remove_grants(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        database = SNOWFLAKE_DATABASE
        username = param["username"]
        role_to_remove = param["role_to_remove"]
        role = param.get("role")

        try:
            self._connection = self._handle_create_connection(role=role, database=database)
            cursor = self._connection.cursor(snowflake.connector.DictCursor)
            cursor.execute(REMOVE_GRANTS_SQL.format(username=username, role_to_remove=role_to_remove))
            row = cursor.fetchone()
            action_result.add_data(row)

        except Exception as e:
            error_msg = self._get_error_msg_from_exception(e)
            self.save_progress(f"Error: {error_msg}")
            return action_result.set_status(phantom.APP_ERROR, error_msg)

        finally:
            if self._connection:
                cursor.close()
                self._connection.close()

        return action_result.set_status(phantom.APP_SUCCESS, REMOVE_GRANTS_SUCCESS_MSG.format(role=role_to_remove))

    def _handle_create_connection(self, role=None, warehouse=None, database=None, schema=None):
        ctx = snowflake.connector.connect(
            user=self._username, password=self._password, account=self._account, role=role, warehouse=warehouse, database=database, schema=schema
        )
        return ctx

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        if action_id == "run_query":
            ret_val = self._handle_run_query(param)

        if action_id == "disable_user":
            ret_val = self._handle_disable_user(param)

        if action_id == "remove_grants":
            ret_val = self._handle_remove_grants(param)

        if action_id == "show_network_policies":
            ret_val = self._handle_show_network_policies(param)

        if action_id == "describe_network_policy":
            ret_val = self._handle_describe_network_policy(param)

        if action_id == "update_network_policy":
            ret_val = self._handle_update_network_policy(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()

        self._account = config["account"]
        self._username = config["username"]
        self._password = config["password"]
        self._connection = None

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = SnowflakeConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=False)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=False, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = SnowflakeConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)


if __name__ == "__main__":
    main()
