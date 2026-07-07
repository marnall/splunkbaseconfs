# File: microsoftsqlserver_connector.py
#
# Copyright (c) 2017-2026 Splunk Inc.
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
import binascii
import csv
import datetime
import json
import os
import struct
import tempfile
import traceback

import phantom.app as phantom
import pymssql
import requests
from dateutil.tz import tzoffset
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from pymssql import OperationalError

from microsoftsqlserver_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class MicrosoftSqlServerConnector(BaseConnector):
    def __init__(self):
        super().__init__()
        self._state = None
        self._cursor = None
        self._freetds_conf_path = None

    def _initialize_error(self, msg, exception=None):
        if self.get_action_identifier() == "test_connectivity":
            self.save_progress(msg)
            if exception:
                self.save_progress(str(exception))
            self.set_status(phantom.APP_ERROR, "Test Connectivity Failed")
        else:
            self.set_status(phantom.APP_ERROR, msg, exception)
        return phantom.APP_ERROR

    # fix empty name values in description
    def _remediate_description_names(self, description):
        description = [list(row) for row in description]
        name = "__name_not_provided__"
        for i, row in enumerate(description):
            if not row[0]:
                row[0] = name + str(i)
        return description

    def _bytes_to_date(self, binary_str):
        unpacked = struct.unpack("QIhH", binary_str)
        m = []
        for tup in unpacked:
            m.append(tup)

        days = m[1]
        microseconds = m[0] / 10 if m[0] else 0

        timezone = m[2]
        tz = tzoffset("ANY", timezone * 60)
        date = datetime.datetime(*[1900, 1, 1, 0, 0, 0], tzinfo=tz)
        td = datetime.timedelta(days=days, minutes=m[2], microseconds=microseconds)
        date += td
        return date

    def _remediate_dataset_value(self, dataset, description):
        dataset = [list(row) for row in dataset]
        for row in dataset:
            for i, value in enumerate(row):
                col_type = description[i][1]

                # convert dates to iso8601
                if self._datetime_to_iso8601 and isinstance(value, (datetime.datetime, datetime.date)):
                    row[i] = value.isoformat()

                elif col_type == 2 and value is not None and isinstance(value, bytes):
                    try:
                        date_from_byte = self._bytes_to_date(value)
                        row[i] = str(date_from_byte)
                    except:
                        self.debug_print("Binary Data")
                        row[i] = f"0x{binascii.hexlify(value).decode().upper()}"

                # catchall for oddball column types
                elif self._default_to_string and not (isinstance(value, str) or isinstance(value, int) or isinstance(value, float)):
                    row[i] = str(value)

        return dataset

    def _dataset_to_dict(self, dataset, description):
        newdataset = []
        for row in dataset:
            dictrow = {}
            newdataset += [dictrow]
            for i, col in enumerate(row):
                dictrow[description[i][0]] = col

        # cooler to use list comprehension, but indecipherable
        # {description[i][0]:col for row in dataset for i, col in enumerate(row)}
        return newdataset

    def _description_to_dict(self, description):
        description_labels = ["name", "type_code", "display_size", "internal_size", "precision", "scale", "null_ok"]
        ret = dict()
        for col in description:
            ret[col[0]] = newcol = dict()
            for i, field in enumerate(col):
                if i and field:
                    newcol[description_labels[i]] = field
        return ret

    def _dump_error_log(self, error, message="Exception occurred."):
        self.error_print(message, dump_object=error)

    def _get_error_message_from_exception(self, e):
        """This method is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = None
        error_message = MSSQLSERVER_ERROR_MESSAGE_UNAVAILABLE
        self.error_print(f"Traceback: {traceback.format_stack()}")
        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except Exception as ex:
            self._dump_error_log(ex, "Error occurred while fetching exception information")

        if not error_code:
            error_text = f"Error Message: {error_message}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_message}"

        return error_text

    def _get_query_results(self, action_result):
        summary = {"num_datasets": 0}

        # dataset_results = {}
        all_datasets = []
        try:
            num_dataset = 0
            while True:
                # description property is from DB-API (PEP249)
                description = self._cursor.description
                if not description:  # For non select queries
                    description = list()
                description = self._remediate_description_names(description)
                dataset = self._cursor.fetchall()
                dataset = self._remediate_dataset_value(dataset, description)
                dataset = self._dataset_to_dict(dataset, description)
                description = self._description_to_dict(description)
                all_datasets += [{"dataset": dataset, "description": description}]

                summary[f"dataset:{num_dataset}:rows"] = len(dataset)
                summary[f"dataset:{num_dataset}:columns"] = len(dataset[0]) if len(dataset) > 0 else 0
                num_dataset += 1
                summary["num_datasets"] = num_dataset

                if not self._cursor.nextset():
                    break
        except OperationalError:  # No rows in results
            return RetVal(phantom.APP_SUCCESS, [])
        except Exception as ex:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, "Unable to retrieve results from query", self._get_error_message_from_exception(ex))
            )

        action_result.update_summary(summary)

        if self._add_datasets_as_rows:
            return RetVal(phantom.APP_SUCCESS, all_datasets)
        else:
            # flatten the datasets to a single list of dictionaries
            results = []
            for ds in all_datasets:
                for row in ds["dataset"]:
                    results += [row]
            return RetVal(phantom.APP_SUCCESS, results)

    def _check_for_valid_schema(self, action_result, schema):
        format_vars = (schema,)
        query = "SELECT * FROM sys.schemas WHERE name = %s;"
        try:
            self._cursor.execute(query, format_vars)
        except Exception as ex:
            return action_result.set_status(phantom.APP_ERROR, "Error searching for schema", self._get_error_message_from_exception(ex))

        results = self._cursor.fetchall()
        if len(results) == 0:
            return action_result.set_status(phantom.APP_ERROR, "The specified schema could not be found")

        return phantom.APP_SUCCESS

    def _check_for_valid_table(self, action_result, table, check_single=False):
        # check_single will ensure there is only one table with this name
        # If more are found, it will throw an error saying a schema is required
        format_vars = (table,)
        query = "SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = %s;"
        try:
            self._cursor.execute(query, format_vars)
        except Exception as ex:
            return action_result.set_status(phantom.APP_ERROR, "Error searching for table", self._get_error_message_from_exception(ex))

        results = self._cursor.fetchall()
        if len(results) == 0:
            return action_result.set_status(phantom.APP_ERROR, "The specified table could not be found")
        elif check_single and len(results) > 1:  # There is more than 1 table
            return action_result.set_status(phantom.APP_ERROR, "More than 1 table has that name, specify a table schema")

        return phantom.APP_SUCCESS

    def _get_format_vars(self, param):
        format_vars = param.get("format_vars")
        if format_vars:
            format_vars = tuple(next(csv.reader([format_vars], quotechar='"', skipinitialspace=True, escapechar="\\")))
        return format_vars

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        query = "SELECT @@version;"
        try:
            self._cursor.execute(query)
        except Exception as ex:
            return action_result.set_status(phantom.APP_ERROR, "Test Connectivity Failed", self._get_error_message_from_exception(ex))

        for row in self._cursor:
            self.save_progress(f"{row[0]}")

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _configure_freetds(self, encryption):
        # Workaround for https://github.com/pymssql/pymssql/issues/924:
        # The `encryption` parameter passed to pymssql.connect() is silently ignored due to a
        # known bug in pymssql. As a workaround, we write a temporary FreeTDS config file with
        # the desired encryption setting and point the FREETDSCONF environment variable at it
        # before opening the connection. The temp file is cleaned up in finalize().
        encryption = (encryption or MSSQLSERVER_ENCRYPTION_DEFAULT).lower()
        if encryption not in MSSQLSERVER_ENCRYPTION_VALID_VALUES:
            encryption = MSSQLSERVER_ENCRYPTION_DEFAULT

        lines = [
            "[global]",
            f"encryption = {encryption}",
        ]

        temp_conf = tempfile.NamedTemporaryFile(mode="w", prefix="mssql_freetds_", suffix=".conf", delete=False)
        self._freetds_conf_path = temp_conf.name
        try:
            temp_conf.write("\n".join(lines) + "\n")
            temp_conf.flush()
        finally:
            temp_conf.close()

        os.environ["FREETDSCONF"] = self._freetds_conf_path

    def _handle_list_columns(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        table_name = param["table_name"]
        dbname = param["database"]
        table_schema = param.get("table_schema")

        if phantom.is_fail(self._check_for_valid_table(action_result, table_name, not bool(table_schema))):
            return phantom.APP_ERROR

        query = "SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = %s AND TABLE_CATALOG = %s"

        if table_schema:
            if phantom.is_fail(self._check_for_valid_schema(action_result, table_schema)):
                return phantom.APP_ERROR
            query += " AND TABLE_SCHEMA = %s"
            format_vars = (table_name, dbname, table_schema)
        else:
            format_vars = (table_name, dbname)

        try:
            self._cursor.execute(query, format_vars)
        except Exception as ex:
            self.error_print("Error listing columns")
            return action_result.set_status(phantom.APP_ERROR, "Error listing columns", self._get_error_message_from_exception(ex))

        ret_val, results = self._get_query_results(action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        for row in results:
            action_result.add_data(row)

        summary = action_result.update_summary({})
        summary["num_columns"] = len(results)

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully listed columns")

    def _handle_list_tables(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        dbname = param.get("database")
        table_schema = param.get("table_schema")

        query = "SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = %s AND TABLE_CATALOG = %s"

        if table_schema:
            if phantom.is_fail(self._check_for_valid_schema(action_result, table_schema)):
                return phantom.APP_ERROR
            query += " AND TABLE_SCHEMA = %s"
            format_vars = ("BASE TABLE", dbname, table_schema)
        else:
            format_vars = ("BASE TABLE", dbname)

        try:
            self._cursor.execute(query, format_vars)
        except Exception as ex:
            self.error_print("Error listing tables")
            return action_result.set_status(phantom.APP_ERROR, "Error listing tables", self._get_error_message_from_exception(ex))

        ret_val, results = self._get_query_results(action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        for row in results:
            action_result.add_data(row)

        summary = action_result.update_summary({})
        summary["num_tables"] = len(results)

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully listed tables")

    def _handle_run_query(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        self._default_to_string = param.get("default_to_string", True)
        self._datetime_to_iso8601 = param.get("datetime_to_iso8601", False)
        self._add_datasets_as_rows = param.get("add_datasets_as_rows", False)

        action_result = self.add_action_result(ActionResult(dict(param)))
        query = param["query"]
        format_vars = self._get_format_vars(param)
        non_query = param.get("non_query", False)

        try:
            self.debug_print("Executing run query")
            if non_query:
                self._connection._conn.execute_non_query("ROLLBACK TRAN")
                if format_vars:
                    self._connection._conn.execute_non_query(query, format_vars)
                else:
                    self._connection._conn.execute_non_query(query)
            else:
                if format_vars:
                    self._cursor.execute(query, format_vars)
                else:
                    self._cursor.execute(query)
        except Exception as ex:
            return action_result.set_status(phantom.APP_ERROR, "Error running query", self._get_error_message_from_exception(ex))

        if non_query:
            action_result.update_summary({"num_rows": 0})
            return action_result.set_status(phantom.APP_SUCCESS, "Successfully ran non-query")

        ret_val, results = self._get_query_results(action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        if not param.get("no_commit", False):
            try:
                self._connection.commit()
            except Exception as ex:
                return action_result.set_status(phantom.APP_ERROR, "unable to commit changes", self._get_error_message_from_exception(ex))

        for row in results:
            action_result.add_data(row)

        summary = action_result.update_summary({})
        summary["num_rows"] = len(results)

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully ran query")

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # To make this app work in a targeted mode where you can specify the
        # host with each action, the code to connect to the database was moved
        # from initialize to here.
        if phantom.is_fail(self._connect_sql(param)):
            action_result = self.add_action_result(ActionResult(dict(param)))
            action_result.set_status(phantom.APP_ERROR, "Unable to connect to host: {}".format(param["host"]))
            return phantom.APP_ERROR

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "list_columns":
            ret_val = self._handle_list_columns(param)

        elif action_id == "list_tables":
            ret_val = self._handle_list_tables(param)

        elif action_id == "run_query":
            ret_val = self._handle_run_query(param)

        return ret_val

    def _connect_sql(self, param):
        self._default_to_string = True
        self._datetime_to_iso8601 = False
        self._add_datasets_as_rows = False
        self._state = self.load_state()

        config = self.get_config()
        param = self.get_current_param()
        username = config["username"]
        password = config["password"]
        port = config.get("port", 1433)
        encryption = config.get("encryption", MSSQLSERVER_ENCRYPTION_DEFAULT)
        host = param.get("host", config["host"])
        database = param.get("database", config["database"])
        param["host"] = host
        param["database"] = database

        if not host:
            return self._initialize_error("host not provided or configured")
        if not database:
            return self._initialize_error("database not provided or configured")

        self._cursor = None
        try:
            # `encryption` is passed via the FreeTDS config rather than as a pymssql.connect() argument
            # see _configure_freetds() for details.
            self._configure_freetds(encryption)
            self._connection = pymssql.connect(host, username, password, database, port=port)  # pylint: disable=no-member
            self._cursor = self._connection.cursor()
        except Exception as ex:
            return self._initialize_error("Error authenticating with database", self._get_error_message_from_exception(ex))

        # check for the connection to the host
        if self._cursor is None:
            return self._initialize_error(f"Error connecting to host: {host}")

        self.save_progress("Database connection established")
        return True

    def initialize(self):
        return phantom.APP_SUCCESS

    def finalize(self):
        if self._freetds_conf_path:
            try:
                os.unlink(self._freetds_conf_path)
            except OSError:
                self.debug_print(f"Error deleting FreeTDS config file: {self._freetds_conf_path}")
            self._freetds_conf_path = None

        os.environ.pop("FREETDSCONF", None)

        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == "__main__":
    import argparse
    import sys

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument("-v", "--verify", action="store_true", help="verify", required=False, default=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password
    verify = args.verify

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = BaseConnector._get_phantom_base_url() + "login"
            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=DEFAULT_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = MicrosoftSqlServerConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
