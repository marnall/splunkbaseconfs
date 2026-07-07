# File: bigquery_connector.py
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
#
#

# The import order matters because of an issue kind of like https://github.com/grpc/grpc/issues/26279 (although that issue
# is for ARM and we're on x86). So bigquery should be imported before everything else
from google.cloud import bigquery  # isort:skip

import json
from concurrent.futures import TimeoutError
from importlib.metadata import distribution

import phantom.app as phantom
import requests
from google.oauth2 import service_account
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from bigquery_consts import *


# "What's going on here?"
# Wheel files don't install how you expect (want?) them to if they would all go into the same directory
# For example, bigquery gets installed to google/cloud/bigquery, their auth gets installed to google/auth
# Pip wont be able to install these since they are all in the google directory (you'll need to use --upgrade, which will delete
#  the old files which were there). To  get around this, we can package all of the wheels in one wheel file.
# The problem with this is that each of Google's module's __init__.py have these two lines
#
#  from pkg_resources import get_distribution
#  __version__ = get_distribution('google-python-module-name').version
#
# This will throw an exception, because get_distribution isn't going to be able to find any of those modules
# This patch fixes that. Granted, every file is now going to be __version__ 1.0.0, but that shouldn't cause any problems


class VersionObj(object):  # noqa
    version = "1.0.0"


_old_distribution = distribution


def _tmp_distribution(package_name):
    return VersionObj()


# Monkey-patch importlib.metadata.distribution temporarily
import importlib.metadata


importlib.metadata.distribution = _tmp_distribution
importlib.metadata.distribution = _old_distribution


class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class BigQueryConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()
        self._state = None

    def is_positive_non_zero_int(self, value):
        try:
            value = int(value)
            return value > 0
        except Exception:
            return False

    def initialize(self):
        self._state = self.load_state()
        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _create_client(self):
        config = self.get_config()
        service_account_json = json.loads(config["key_json"])

        credentials = service_account.Credentials.from_service_account_info(service_account_json)

        client = bigquery.Client(project=service_account_json["project_id"], credentials=credentials)

        return client

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Creating BigQuery client...")
        try:
            client = self._create_client()
        except Exception as e:
            self.save_progress("Test Connectivity Failed")
            return action_result.set_status(phantom.APP_ERROR, "Error creating client", e)

        self.save_progress("Making test call to BigQuery...")
        try:
            [x.reference for x in client.list_datasets(max_results=1)]
        except Exception as e:
            self.save_progress("Test Connectivity Failed")
            return action_result.set_status(phantom.APP_ERROR, "Error listing datasets", e)

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_tables(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        dataset = param.get("dataset")

        try:
            client = self._create_client()
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Error creating client", e)

        self.save_progress("Querying tables list...")
        if dataset:
            try:
                dataset_ref_list = [client.dataset(dataset)]
            except Exception as e:
                return action_result.set_status(phantom.APP_ERROR, "Unable to retrieve specified dataset", e)
        else:
            try:
                dataset_ref_list = [x.reference for x in client.list_datasets()]
            except Exception as e:
                return action_result.set_status(phantom.APP_ERROR, "Error creating a list of datasets", e)

        self.save_progress("Processing tables list...")
        try:
            for dataset_ref in dataset_ref_list:
                for table in client.list_tables(dataset_ref):
                    action_result.add_data(
                        {
                            "table_id": table.table_id,
                            "dataset_id": dataset_ref.dataset_id,
                            "project_id": dataset_ref.project,
                            "full_table_id": table.full_table_id,
                        }
                    )
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Error listing dataset", e)

        action_result.update_summary({"total_tables": action_result.get_data_size()})

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully listed tables")

    def _get_query_results(self, action_result, query_job, timeout):
        self.save_progress("Waiting for query results...")
        try:
            result = query_job.result(timeout=timeout)
        except TimeoutError:
            action_result.update_summary({"job_id": query_job.job_id})
            return action_result.set_status(phantom.APP_SUCCESS, "Timed out while waiting for results")
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Error getting results from query", e)

        try:
            for row in result:
                action_result.add_data(dict(row))
        except:
            pass

        action_result.update_summary({"num_rows": action_result.get_data_size(), "job_id": query_job.job_id})

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved results from Query")

    def _handle_get_results(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        job_id = param["job_id"]
        timeout = param.get("timeout")
        if not (timeout is None or self.is_positive_non_zero_int(timeout)):
            return action_result.set_status(phantom.APP_ERROR, "Please provide a positive integer in timeout")

        try:
            client = self._create_client()
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Error creating client", e)

        self.save_progress("Fetching jobs...")
        try:
            query_job = client.get_job(job_id)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Error fetching results", e)

        return self._get_query_results(action_result, query_job, timeout)

    def _handle_run_query(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        query = param["query"]
        timeout = param.get("timeout")
        if not (timeout is None or self.is_positive_non_zero_int(timeout)):
            return action_result.set_status(phantom.APP_ERROR, "Please provide a positive integer in timeout")

        self.save_progress("Running query...")
        try:
            client = self._create_client()
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Error creating client", e)

        query_job = client.query(query)

        return self._get_query_results(action_result, query_job, timeout)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "get_results":
            ret_val = self._handle_get_results(param)

        elif action_id == "list_tables":
            ret_val = self._handle_list_tables(param)

        elif action_id == "run_query":
            ret_val = self._handle_run_query(param)

        return ret_val


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
            print("Accessing the Login page")
            r = requests.get(f"{BaseConnector._get_phantom_base_url()}login", verify=verify, timeout=DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = f"{BaseConnector._get_phantom_base_url()}login"

            print("Logging into Platform to get the session id")
            r2 = requests.post(
                f"{BaseConnector._get_phantom_base_url()}login", verify=verify, data=data, headers=headers, timeout=DEFAULT_TIMEOUT
            )
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platfrom. Error: " + str(e))
            sys.exit(1)

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = BigQueryConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
