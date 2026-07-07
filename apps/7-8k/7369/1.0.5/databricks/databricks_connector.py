# File: databricks_connector.py
#
# Copyright (c) 2024-2026 Splunk Inc.
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

import json
import traceback
from datetime import datetime
from typing import Optional

import phantom.app as phantom
import requests
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

import databricks_consts as consts
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.compute import ClusterSpec, Library
from databricks.sdk.service.iam import AccessControlRequest
from databricks.sdk.service.jobs import GitSource, NotebookTask, Run, RunResultState, SubmitTask
from databricks.sdk.service.sql import AlertOptions, AlertOptionsEmptyResultState, Disposition, ExecuteStatementRequestOnWaitTimeout, Format
from databricks.sdk.service.workspace import ObjectType


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class DatabricksConnector(BaseConnector):
    def __init__(self):
        super().__init__()

        self._state = None

        self._host: Optional[str] = None
        self._username: Optional[str] = None
        self._password: Optional[str] = None
        self._token: Optional[str] = None

    def _get_error_msg_from_exception(self, e):
        error_code = None
        error_message = consts.DATABRICKS_ERROR_MESSAGE_UNAVAILABLE

        self.error_print(traceback.format_exc())

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except Exception as e:
            self.error_print(f"Error occurred while fetching exception information. Details: {e}")

        if not error_code:
            error_text = f"Error Message: {error_message}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_message}"
        return error_text

    @staticmethod
    def _set_key_if_param_defined(
        dict_to_update: dict,
        param: dict,
        key: str,
        is_json: bool = False,
        param_key: Optional[str] = None,
    ):
        if param_key is None:
            param_key = key

        if param_key not in param:
            return

        if is_json:
            value = json.loads(param[param_key])
        else:
            value = param[param_key]

        dict_to_update[key] = value

    def _get_api_client(self) -> WorkspaceClient:
        return WorkspaceClient(
            host=self._host,
            username=self._username,
            password=self._password,
            token=self._token,
        )

    def _report_error(self, action_result, exception, error_prefix):
        error_message = self._get_error_msg_from_exception(exception)
        self.save_progress(error_message)
        return action_result.set_status(phantom.APP_ERROR, error_prefix, error_message)

    def _handle_test_connectivity(self, param):
        self.save_progress(consts.TEST_CONNECTIVITY_PROGRESS_MESSAGE)

        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            api_client = self._get_api_client()
            api_client.dbfs.get_status(consts.TEST_CONNECTIVITY_FILE_PATH)
        except Exception as e:
            return self._report_error(action_result, e, consts.TEST_CONNECTIVITY_ERROR_MESSAGE)

        self.save_progress(consts.TEST_CONNECTIVITY_SUCCESS_MESSAGE)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_alert(self, param):
        self.debug_print(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        kwargs_options = {
            "column": param.get("column"),
            "op": param.get("operator"),
            "value": param.get("value"),
        }
        self._set_key_if_param_defined(kwargs_options, param, "custom_body")
        self._set_key_if_param_defined(kwargs_options, param, "custom_subject")
        self._set_key_if_param_defined(kwargs_options, param, "muted")
        if "empty_result_state" in param:
            kwargs_options["empty_result_state"] = AlertOptionsEmptyResultState(param["empty_result_state"])
        options = AlertOptions(**kwargs_options)

        kwargs_alert = {
            "name": param.get("name"),
            "query_id": param.get("query_id"),
            "options": options,
        }
        self._set_key_if_param_defined(kwargs_alert, param, "rearm")

        try:
            api_client = self._get_api_client()

            if "parent" in param:
                # If the user provided a parent directory, check that it exists
                # and resolve the path to an ID if needed
                parent_path: str = param["parent"]
                if parent_path.startswith("folders/"):
                    # Path is already resolved
                    kwargs_alert["parent"] = parent_path
                else:
                    # Need to resolve the path into a folder ID
                    parent_obj = api_client.workspace.get_status(path=parent_path)
                    if parent_obj.object_type == ObjectType.DIRECTORY:
                        kwargs_alert["parent"] = f"folders/{parent_obj.object_id}"
                    else:
                        raise ValueError(f"parent path is not a folder: {parent_path}")

            result = api_client.alerts.create(**kwargs_alert)
        except Exception as e:
            return self._report_error(action_result, e, consts.CREATE_ALERT_ERROR_MESSAGE)

        action_result.add_data(result.as_dict())
        summary = {
            "status": consts.CREATE_ALERT_SUCCESS_MESSAGE,
        }
        action_result.update_summary(summary)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_alerts(self, param):
        self.debug_print(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            api_client = self._get_api_client()
            result = list(api_client.alerts.list())
        except Exception as e:
            return self._report_error(action_result, e, consts.LIST_ALERTS_ERROR_MESSAGE)

        for item in result:
            action_result.add_data(item.as_dict())

        summary = {
            "status": consts.LIST_ALERTS_SUCCESS_MESSAGE,
            "Total alerts": len(result),
        }

        action_result.update_summary(summary)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_clusters(self, param):
        self.debug_print(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            api_client = self._get_api_client()
            result = list(api_client.clusters.list())
        except Exception as e:
            return self._report_error(action_result, e, consts.LIST_CLUSTERS_ERROR_MESSAGE)

        total_clusters = len(result)

        for cluster in result:
            action_result.add_data(cluster.as_dict())

        summary = {
            "status": consts.LIST_CLUSTERS_SUCCESS_MESSAGE,
            "Total Clusters": total_clusters,
        }

        action_result.update_summary(summary)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_alert(self, param):
        self.debug_print(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        alert_id = param["alert_id"]

        try:
            api_client = self._get_api_client()
            api_client.alerts.delete(alert_id)
        except Exception as e:
            return self._report_error(action_result, e, consts.DELETE_ALERT_ERROR_MESSAGE)

        summary = {
            "status": consts.DELETE_ALERT_SUCCESS_MESSAGE,
        }
        action_result.update_summary(summary)

        # also remove from state file if present
        if "alerts" in self._state and alert_id in self._state["alerts"]:
            del self._state["alerts"][alert_id]

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_perform_query(self, param):
        self.debug_print(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        data = {
            "statement": param["statement"],
            "warehouse_id": param["warehouse_id"],
        }

        if "wait_timeout" in param:
            data["wait_timeout"] = f"{param['wait_timeout']}s"

            # 'on_wait_timeout' can only be set if call is synchronous
            if param["wait_timeout"] != 0:
                on_wait_timeout = param.get("on_wait_timeout")
                data["on_wait_timeout"] = ExecuteStatementRequestOnWaitTimeout[on_wait_timeout]

        self._set_key_if_param_defined(data, param, "byte_limit")
        self._set_key_if_param_defined(data, param, "catalog")
        self._set_key_if_param_defined(data, param, "schema")

        result_format = param.get("format")
        data["format"] = Format[result_format]

        disposition = param.get("disposition")
        data["disposition"] = Disposition[disposition]

        try:
            api_client = self._get_api_client()
            result = api_client.statement_execution.execute_statement(**data)
        except Exception as e:
            return self._report_error(action_result, e, consts.PERFORM_QUERY_ERROR_MESSAGE)

        action_result.add_data(result.as_dict())

        summary = {
            "status": consts.PERFORM_QUERY_SUCCESS_MESSAGE,
        }
        action_result.update_summary(summary)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_query_status(self, param):
        self.debug_print(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        statement_id = param["statement_id"]

        try:
            api_client = self._get_api_client()
            result = api_client.statement_execution.get_statement(statement_id)
        except Exception as e:
            return self._report_error(action_result, e, consts.GET_QUERY_STATUS_ERROR_MESSAGE)

        action_result.add_data(result.as_dict())

        summary = {
            "status": consts.GET_QUERY_STATUS_SUCCESS_MESSAGE,
        }
        action_result.update_summary(summary)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_cancel_query(self, param):
        self.debug_print(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        statement_id = param["statement_id"]

        try:
            api_client = self._get_api_client()
            api_client.statement_execution.cancel_execution(statement_id)
        except Exception as e:
            return self._report_error(action_result, e, consts.CANCEL_QUERY_ERROR_MESSAGE)

        summary = {
            "status": consts.CANCEL_QUERY_SUCCESS_MESSAGE,
        }
        action_result.update_summary(summary)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_job_run(self, param):
        self.debug_print(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        run_id = param["run_id"]

        ret_val, response = self._get_job_run(run_id, action_result)
        action_result.add_data(response)
        summary = {
            "status": consts.GET_JOB_RUN_SUCCESS_MESSAGE,
        }
        action_result.update_summary(summary)

        if phantom.is_fail(ret_val):
            return ret_val

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_job_run(self, run_id, action_result):
        self.debug_print("Getting job run details")

        try:
            api_client = self._get_api_client()
            result = api_client.jobs.get_run(run_id)
        except Exception as e:
            return self._report_error(action_result, e, consts.GET_JOB_RUN_ERROR_MESSAGE)

        return action_result.set_status(phantom.APP_SUCCESS), result.as_dict()

    def _handle_get_job_output(self, param):
        self.debug_print(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        run_id = param["run_id"]

        try:
            api_client = self._get_api_client()
            job_run = api_client.jobs.get_run(run_id)
        except Exception as e:
            return self._report_error(action_result, e, consts.GET_JOB_RUN_ERROR_MESSAGE)

        if job_run.tasks is None:
            return action_result.set_status(phantom.APP_ERROR, "This job run contains no task runs")

        for task_run in job_run.tasks:
            if task_run.run_id is not None:
                task_output = api_client.jobs.get_run_output(task_run.run_id)
                action_result.add_data(task_output.as_dict())
        summary = {
            "status": consts.GET_JOB_OUTPUT_SUCCESS_MESSAGE,
        }
        action_result.update_summary(summary)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_execute_notebook(self, param):
        self.debug_print(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        # Task key needs to be unique per parent job and can be used to set a dependency order
        # within a job. However, for the purposes of this action we always create a one time job
        # with a single task, so we can hardcode a readable value instead of exposing this
        # detail to the user.
        task_info = SubmitTask(
            task_key="soar_execute_notebook_action",
            notebook_task=NotebookTask(notebook_path=param["notebook_path"]),
        )
        if "new_cluster" in param:
            cluster_json = json.loads(param["new_cluster"])
            task_info.new_cluster = ClusterSpec.from_dict(cluster_json)
        if "existing_cluster_id" in param:
            task_info.existing_cluster_id = param["existing_cluster_id"]
        if "libraries" in param:
            libraries_json = json.loads(param["libraries"])
            task_info.libraries = [Library.from_dict(d) for d in libraries_json]

        run_info = {}
        run_info["tasks"] = [task_info]
        if "git_source" in param:
            git_json = json.loads(param["git_source"])
            run_info["git_source"] = GitSource.from_dict(git_json)
        if "access_control_list" in param:
            acl_json = json.loads(param["access_control_list"])
            run_info["access_control_list"] = [AccessControlRequest.from_dict(d) for d in acl_json]
        self._set_key_if_param_defined(run_info, param, "timeout_seconds")
        self._set_key_if_param_defined(run_info, param, "run_name")
        self._set_key_if_param_defined(run_info, param, "idempotency_token")

        def callback(run: Run):
            action_result.add_data(run.as_dict())

            if run.state is None:
                return action_result.set_status(action_result.set_status(phantom.APP_ERROR, "Failed to get execution status"))

            if run.state.result_state == RunResultState.FAILED:
                action_result.update_summary({"status": consts.EXECUTE_NOTEBOOK_ERROR_MESSAGE})
                return action_result.set_status(phantom.APP_ERROR, run.state.state_message)

            action_result.update_summary({"status": consts.EXECUTE_NOTEBOOK_SUCCESS_MESSAGE})
            return action_result.set_status(phantom.APP_SUCCESS)

        try:
            api_client = self._get_api_client()
            api_client.jobs.submit(**run_info).result(callback=callback)
        except Exception as e:
            return self._report_error(action_result, e, consts.EXECUTE_NOTEBOOK_ERROR_MESSAGE)

    def _handle_list_warehouses(self, param):
        self.debug_print(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            api_client = self._get_api_client()
            result = api_client.warehouses.list()
        except Exception as e:
            return self._report_error(action_result, e, consts.LIST_WAREHOUSES_ERROR_MESSAGE)

        total_warehouses = 0

        for warehouse in result:
            action_result.add_data(warehouse.as_dict())
            total_warehouses += 1

        summary = {
            "status": consts.LIST_WAREHOUSES_SUCCESS_MESSAGE,
            "total warehouses": total_warehouses,
        }

        action_result.update_summary(summary)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _is_later_date(self, alert_triggered_date, last_triggered_date):
        return datetime.strptime(alert_triggered_date, consts.DATETIME_FORMAT) > datetime.strptime(last_triggered_date, consts.DATETIME_FORMAT)

    def _handle_on_poll(self, param):
        self.debug_print(f"In action handler for: {self.get_action_identifier()}")

        if self.is_poll_now():
            self.save_progress("Starting polling now")
            self.save_progress("Ignoring maximum number of containers and artifacts during poll now")

        action_result = self.add_action_result(ActionResult(dict(param)))

        api_client = self._get_api_client()
        result = api_client.alerts.list()

        # get list of alerts from state to compare to current list of alerts
        state_alerts = self._state.get("alerts", {})

        for alert in result:
            last_triggered_at = alert.last_triggered_at
            if not last_triggered_at:
                continue

            alert_id = alert.id

            # check to see if the latest alert trigger date is later than the last time it triggered
            if alert_id:
                if alert_id in state_alerts and not self._is_later_date(last_triggered_at, state_alerts[alert_id]):
                    continue

                state_alerts[alert_id] = last_triggered_at

                container = {}
                container["name"] = alert.name if alert.name is not None else "Databricks Alert"
                container["artifacts"] = [{"cef": alert.as_dict()}]
                self.save_container(container)

                self._state["alerts"] = state_alerts

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        try:
            if action_id == "test_connectivity":
                ret_val = self._handle_test_connectivity(param)
            elif action_id == "list_alerts":
                ret_val = self._handle_list_alerts(param)
            elif action_id == "list_clusters":
                ret_val = self._handle_list_clusters(param)
            elif action_id == "create_alert":
                ret_val = self._handle_create_alert(param)
            elif action_id == "delete_alert":
                ret_val = self._handle_delete_alert(param)
            elif action_id == "get_job_run":
                ret_val = self._handle_get_job_run(param)
            elif action_id == "get_job_output":
                ret_val = self._handle_get_job_output(param)
            elif action_id == "perform_query":
                ret_val = self._handle_perform_query(param)
            elif action_id == "get_query_status":
                ret_val = self._handle_get_query_status(param)
            elif action_id == "cancel_query":
                ret_val = self._handle_cancel_query(param)
            elif action_id == "execute_notebook":
                ret_val = self._handle_execute_notebook(param)
            elif action_id == "list_warehouses":
                ret_val = self._handle_list_warehouses(param)
            elif action_id == "on_poll":
                ret_val = self._handle_on_poll(param)
            else:
                action_result = self.add_action_result(ActionResult(dict(param)))
                ret_val = action_result.set_status(
                    phantom.APP_ERROR,
                    consts.UNHANDLED_ACTION_ID_ERROR_MESSAGE.format(action_id),
                )
        except Exception as e:
            ret_val = self._report_error(ActionResult(dict(param)), e, "Action failed")

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()

        self._host = config["host"]
        self._username = config.get("username")
        self._password = config.get("password")
        self._token = config.get("token")

        if (self._username and self._password) or self._token:
            return phantom.APP_SUCCESS

        return self.set_status(phantom.APP_ERROR, consts.MISSING_AUTHENTICATION_ERROR_MESSAGE)

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
    argparser.add_argument("-v", "--verify", help="verify", default=False)

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
            login_url = DatabricksConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=args.verify)
            csrftoken = r.cookies["csrftoken"]

            data = {}
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = {}
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

        connector = DatabricksConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)


if __name__ == "__main__":
    main()
