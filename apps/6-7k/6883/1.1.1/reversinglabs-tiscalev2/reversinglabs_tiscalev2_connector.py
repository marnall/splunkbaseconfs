# File: reversinglabs_tiscalev2_connector.py
#
# Copyright (c) ReversingLabs, 2023-2025
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

# Python 3 Compatibility imports
import json

# Phantom App imports
import phantom.app as phantom
from phantom import vault
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from ReversingLabs.SDK.tiscale import TitaniumScale


# Our helper lib reversinglabs-sdk-py3 internally utilizes pypi requests (with named parameters) which is shadowed by Phantom
# requests (which has renamed parameters (url>>uri), hence this workarounds
old_get = phantom.requests.get


def new_get(url, **kwargs):
    return old_get(url, **kwargs)


phantom.requests.get = new_get

old_post = phantom.requests.post


def new_post(url, **kwargs):
    return old_post(url, **kwargs)


phantom.requests.post = new_post

old_delete = phantom.requests.delete


def new_delete(url, **kwargs):
    return old_delete(url, **kwargs)


phantom.requests.delete = new_delete


class ReversinglabsTitaniumScaleConnector(BaseConnector):
    USER_AGENT = "ReversingLabs Splunk SOAR TitaniumScale v1.1.0"

    # The actions supported by this connector
    ACTION_ID_TEST_CONNECTIVITY = "test_connectivity"
    ACTION_ID_DETONATE_FILE = "detonate_file"
    ACTION_ID_DETONATE_FILE_AND_GET_REPORT = "detonate_file_and_get_report"
    ACTION_ID_GET_REPORT = "get_report"
    ACTION_ID_GET_REPORT_BY_ID = "get_report_by_id"
    ACTION_ID_GET_TASK_LIST = "get_task_list"
    ACTION_ID_DELETE_PROCESSING_TASK = "delete_processing_task"
    ACTION_ID_DELETE_PROCESSING_TASKS = "delete_processing_tasks"
    ACTION_ID_GET_YARA_ID = "get_yara_id"

    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self.ACTIONS = {
            self.ACTION_ID_TEST_CONNECTIVITY: self._handle_test_connectivity,
            self.ACTION_ID_DETONATE_FILE: self._handle_detonate_file,
            self.ACTION_ID_DETONATE_FILE_AND_GET_REPORT: self._handle_detonate_file_and_get_report,
            self.ACTION_ID_GET_REPORT: self._handle_get_report,
            self.ACTION_ID_GET_REPORT_BY_ID: self._handle_get_report_by_id,
            self.ACTION_ID_GET_TASK_LIST: self._handle_get_task_list,
            self.ACTION_ID_DELETE_PROCESSING_TASK: self._handle_delete_processing_task,
            self.ACTION_ID_DELETE_PROCESSING_TASKS: self._handle_delete_processing_tasks,
            self.ACTION_ID_GET_YARA_ID: self._handle_get_yara_id,
        }

        self._state = None

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()
        self.tiscale_url = config["url"]
        self.tiscale_token = config["token"]
        self.wait_time = config.get("wait_time", 2)
        self.retries = config.get("retries", 10)

        self.tiscale = TitaniumScale(
            host=self.tiscale_url, token=self.tiscale_token, wait_time_seconds=self.wait_time, retries=self.retries, user_agent=self.USER_AGENT
        )

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def handle_action(self, param):
        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()
        action = self.ACTIONS.get(action_id)
        if not action:
            return

        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            action(action_result, param)
        except Exception as err:
            return action_result.set_status(phantom.APP_ERROR, str(err))

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_detonate_file_and_get_report(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        file_vault_id = param["vault_id"]
        success, msg, files_array = vault.vault_info(container_id=self.get_container_id())
        if not success:
            raise Exception(f"Unable to get Vault item details. Error details: {msg}")

        file = next(filter(lambda x: x["vault_id"] == file_vault_id, files_array), None)
        if not file:
            raise Exception(f"Unable to get Vault item details. Error details: {msg}")

        response = self.tiscale.upload_sample_and_get_results(file_path=file["path"], full_report=param.get("full_report", False))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    def _handle_detonate_file(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        file_vault_id = param["vault_id"]
        success, msg, files_array = vault.vault_info(container_id=self.get_container_id())
        if not success:
            raise Exception(f"Unable to get Vault item details. Error details: {msg}")

        file = next(filter(lambda x: x["vault_id"] == file_vault_id, files_array), None)
        if not file:
            raise Exception(f"Unable to get Vault item details. Error details: {msg}")

        response = self.tiscale.upload_sample_from_path(
            file_path=file["path"],
            custom_token=param.get("custom_token"),
            user_data=param.get("user_data"),
            custom_data=param.get("custom_data"),
        )

        print(response.json())

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    def _handle_get_report(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        response = self.tiscale.get_results(task_url=param.get("task_url"), full_report=param.get("full_report", False))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    def _handle_get_report_by_id(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())
        response = self.tiscale.get_processing_task_info(
            task_id=param.get("task_id"),
            full=param.get("full", True),
            v13=param.get("v13", False),
            view=param.get("view"),
        )
        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json())

    def _handle_test_connectivity(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        self.tiscale.test_connection()

        self.debug_print("Executed", self.get_action_identifier())
        self.save_progress("Test Connectivity Passed")

    def _handle_get_task_list(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())
        response = self.tiscale.list_processing_tasks(
            age=param.get("age"),
            custom_token=param.get("custom_token"),
        )
        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json())

    def _handle_delete_processing_task(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())
        self.tiscale.delete_processing_task(
            task_id=param.get("task_id"),
        )
        self.debug_print("Executed", self.get_action_identifier())

    def _handle_delete_processing_tasks(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())
        self.tiscale.delete_multiple_tasks(
            age=param.get("age"),
        )
        self.debug_print("Executed", self.get_action_identifier())

    def _handle_get_yara_id(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())
        response = self.tiscale.get_yara_id()
        action_result.add_data(response.json())
        self.debug_print("Executed", self.get_action_identifier())


def main():
    import argparse
    import sys

    argparser = argparse.ArgumentParser()
    args = argparser.parse_args()
    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)

        connector = ReversinglabsTitaniumScaleConnector()
        connector.print_progress_message = True

        connector._handle_action(json.dumps(in_json), None)
    sys.exit(0)


if __name__ == "__main__":
    main()
