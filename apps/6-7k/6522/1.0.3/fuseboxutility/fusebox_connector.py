# File: fusebox_connector.py
#
# Copyright (c) Mhike, 2022-2025
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
import json
import time
from datetime import datetime, timedelta

import phantom.app as phantom
from phantom.action_result import ActionResult


class FuseBoxConnector(phantom.BaseConnector):
    is_polling_action = False

    def __init__(self):
        super().__init__()
        return

    def __print(self, value, is_debug):
        print_debug = False
        message = "Failed to cast message to string"
        try:
            print_debug = self.get_config()["debug"]
        except:
            pass
        try:
            message = str(value)
        except:
            pass
        if is_debug and not print_debug:
            return
        else:
            self.save_progress(message)
            if self.is_polling_action:
                self.debug_print(self.__class__.__name__, message)

    def _get_base_url(self):
        self.__print("_get_base_url()", True)
        return self.get_phantom_base_url()

    def _get_list_data(self, list_name):
        self.__print("_get_list_data()", True)
        endpoint = f"/rest/decided_list/{list_name}"
        list_response = self._get_rest_data(endpoint)
        try:
            return list_response["content"]
        except Exception as e:
            self.__print("Getting data from list failed with an exception:", True)
            self.__print(e, True)
            return None

    def _get_rest_data(self, endpoint):
        self.__print("_get_rest_data()", True)
        try:
            url = f"{self._get_base_url()}/{endpoint}"
            self.__print(url, True)
            response = phantom.requests.get(url, verify=False, timeout=30)
            code = response.status_code
            self.__print(code, True)
            content = json.loads(response.text)
            if 199 < code < 300:
                if "data" in content and "container/" not in url:
                    return content["data"]
                else:
                    return content
            else:
                return None
        except Exception as e:
            self.__print("Exception occur while getting rest data. Exception:", False)
            self.__print(e, False)
            return None

    def _get_playbook_name(self):
        playbook_name = None
        current_container = self.get_container_id()
        endpoint = (
            f'rest/action_run?_filter_container="{current_container}"&_filter_status="running"&_filter_action="check fuse"&pretty&page_size=1'
        )
        action = self._get_rest_data(endpoint)
        if action:
            playbook_name = action[0]["_pretty_playbook"]
        self.__print(f"Playbook pretty name: {playbook_name}", True)
        return playbook_name

    def _post_update(self, payload, endpoint):
        self.__print("_post_update()", True)
        try:
            url = f"{self._get_base_url()}/{endpoint}"
            self.__print(url, True)
            response = phantom.requests.post(url, data=payload, verify=False, timeout=30)
            self.__print(response.text, True)
            code = response.status_code
            if 199 < code < 300:
                return True
            else:
                return False
        except Exception as e:
            self.__print("Post to list failed with an exception:", False)
            self.__print(e, False)
            return False

    def _build_append_payload(self, playbook_name, unique_string):
        data = json.dumps({"append_rows": [[playbook_name, unique_string, str(int(time.time()))]]})
        return data

    def _handle_check_fuse(self, param):
        self.__print(f"In action handler for: {self.get_action_identifier()}", True)
        action_result = self.add_action_result(ActionResult(dict(param)))
        try:
            list_name = self.get_config()["dedicated_custom_list"]
            unique_string = param.get("unique_identifier")
            playbook_name = self._get_playbook_name()
            list_data = self._get_list_data(list_name)
            for row in list_data:
                if playbook_name in row:
                    if unique_string in row:
                        self.__print(f"[{playbook_name}, {unique_string}] found in row, tripping fuse", True)
                        action_result.add_data({"playbook_name": playbook_name, "tripped_fuse": True, "is_duplicate": True})
                        self.__print("tripped_fuse == True", True)
                        action_result.set_status(phantom.APP_SUCCESS, "tripped_fuse == True")
                        return phantom.APP_SUCCESS
            self.__print(f"[{playbook_name}, {unique_string}] not found. Adding new fuse", True)
            endpoint = f"rest/decided_list/{list_name}"
            payload = self._build_append_payload(playbook_name, unique_string)
            success = self._post_update(payload, endpoint)
            if success:
                action_result.add_data({"playbook_name": playbook_name, "tripped_fuse": False, "is_duplicate": False})
                self.__print("Successfully added new fuse", True)
                action_result.set_status(phantom.APP_SUCCESS, "Successfully added new fuse")
                return phantom.APP_SUCCESS
            else:
                self.__print("Failed to add new fuse", False)
                action_result.set_status(phantom.APP_ERROR, "Failed to add new fuse")
                return phantom.APP_ERROR
        except Exception as e:
            self.__print("Check Fuse failed with an error:", False)
            self.__print(e, False)
            action_result.set_status(phantom.APP_ERROR, "Failed to check fuse")
            return phantom.APP_ERROR

    def _handle_test_connectivity(self, param):
        self.__print(f"In action handler for: {self.get_action_identifier()}", True)
        action_result = self.add_action_result(ActionResult(dict(param)))
        list_name = self.get_config()["dedicated_custom_list"]
        list_endpoint = "rest/decided_list"
        self.__print(f"Attempting http get for {list_endpoint}", False)
        lists = self._get_rest_data(list_endpoint)
        if lists:
            self.__print("Successfully retrieved custom lists", False)
            for entry in lists:
                if entry["name"] == list_name:
                    self.__print("Dedicated list already exists. Testing access", False)
                    list_content = self._get_list_data(list_name)
                    if list_content:
                        self.__print("Successfully retrieved custom list", False)
                        self.__print("Passed connection test", False)
                        return action_result.set_status(phantom.APP_SUCCESS)
                    else:
                        self.__print("Failed to retrieve custom list", False)
                        self.__print("Failed connection test", False)
                        return action_result.set_status(phantom.APP_ERROR, "Failed connection test")
            self.__print("Dedicated list does not exist. Attempting to create it", False)
            endpoint = "rest/decided_list"
            payload = self._build_append_payload("Test Connectivity", "Initial List Creation")
            payload = json.loads(payload)
            payload["content"] = payload["append_rows"]
            del payload["append_rows"]
            payload["name"] = list_name
            payload = json.dumps(payload)
            response = self._post_update(payload, endpoint)
            if response:
                self.__print("Successfully added custom list", False)
                self.__print("Passed connection test", False)
                return action_result.set_status(phantom.APP_SUCCESS)
            else:
                self.__print("Failed to add custom list", False)
                self.__print("Failed connection test", False)
                return action_result.set_status(phantom.APP_ERROR, "Failed connection test")

    def _handle_on_poll(self, param):
        self.__print(f"In action handler for: {self.get_action_identifier()}", True)
        self.is_polling_action = True
        action_result = self.add_action_result(ActionResult(dict(param)))
        list_name = self.get_config()["dedicated_custom_list"]
        retention_limit = self.get_config()["retention_limit"]
        list_content = self._get_list_data(list_name)
        for row in list_content:
            self.__print(row, True)
            expired = int((datetime.now() - timedelta(days=retention_limit)).timestamp())
            self.__print(expired, True)
            if int(row[2]) > expired and list_content.index(row) == 0:
                self.__print("No list pruning required", False)
                return action_result.set_status(phantom.APP_SUCCESS, "No list pruning required")
            if int(row[2]) > expired and list_content.index(row) > 0:
                self.__print(f"Found earliest unexpired row at row {list_content.index(row)}", False)
                list_content = list_content[list_content.index(row) :]
                endpoint = f"rest/decided_list/{list_name}"
                payload = json.dumps({"content": list_content})
                response = self._post_update(payload, endpoint)
                if response:
                    self.__print("List successfully pruned", False)
                    return action_result.set_status(phantom.APP_SUCCESS, "List successfully pruned")
                else:
                    self.__print("List pruning failed", False)
                    return action_result.set_status(phantom.APP_ERROR, "List pruning failed")

    def handle_action(self, param):
        action = self.get_action_identifier()
        ret_val = phantom.APP_SUCCESS

        if action == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action == "check_fuse":
            ret_val = self._handle_check_fuse(param)

        elif action == "on_poll":
            ret_val = self._handle_on_poll(param)

        return ret_val
