# File: mobileiron_connector.py
#
# Copyright (c) 2016-2025 Splunk Inc.
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
import re

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Imports local to this App
from mobileiron_consts import *


# Define the App Class
class MobileIronConnector(BaseConnector):
    ACTION_ID_LIST_DEVICES = "list_devices"
    ACTION_ID_LOCK_DEVICE = "lock_device"
    ACTION_ID_UNLOCK_DEVICE = "unlock_device"
    ACTION_ID_GET_SYSTEM_INFO = "get_system_info"

    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

    def initialize(self):
        config = self.get_config()

        # Base URL
        self._base_url = config[MOBILEIRON_JSON_DEVICE_URL]
        if self._base_url.endswith("/"):
            self._base_url = self._base_url[:-1]

        self._host = self._base_url[self._base_url.find("//") + 2 :]
        self._headers = {"Accept": "application/json"}
        self._api_uri = "/api/v1"

        self.__uuid_regex = re.compile(r"[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}\Z", re.I)

        return phantom.APP_SUCCESS

    def finalize(self):
        return phantom.APP_SUCCESS

    def _make_rest_call(self, endpoint, request_params, action_result, method="get"):
        config = self.get_config()

        username = config[MOBILEIRON_JSON_USERNAME]
        password = config[MOBILEIRON_JSON_PASSSWORD]

        # Create the headers
        headers = self._headers
        resp_json = None

        try:
            if method == "get":
                r = requests.get(
                    self._base_url + self._api_uri + endpoint,
                    auth=(username, password),
                    params=request_params,
                    headers=headers,
                    verify=config[phantom.APP_JSON_VERIFY],
                    timeout=MOBILEIRON_DEFAULT_TIMEOUT,
                )
            else:
                r = requests.put(
                    self._base_url + self._api_uri + endpoint,
                    auth=(username, password),
                    params=request_params,
                    headers=headers,
                    verify=config[phantom.APP_JSON_VERIFY],
                    timeout=MOBILEIRON_DEFAULT_TIMEOUT,
                )
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, MOBILEIRON_ERR_SERVER_CONNECTION, e), resp_json

        # self.debug_print('REST url: {0}'.format(r.url))

        if r.status_code != requests.codes.ok:  # pylint: disable=E1101
            try:
                soup = BeautifulSoup(r.text)
                # Remove the script, style, footer and navigation part from the HTML message
                for element in soup(["script", "style", "footer", "nav"]):
                    element.extract()
                text = soup.get_text()
            except Exception:
                return (action_result.set_status(phantom.APP_ERROR, MOBILEIRON_ERR_FROM_SERVER, status=r.status_code, detail=r.text), resp_json)
            else:
                return (action_result.set_status(phantom.APP_ERROR, MOBILEIRON_ERR_FROM_SERVER, status=r.status_code, detail=text), resp_json)

        try:
            resp_json = r.json()
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, MOBILEIRON_ERR_JSON_PARSE, data=r.text), None

        return phantom.APP_SUCCESS, resp_json

    def _test_connectivity(self, param):
        # Progress
        self.save_progress(MOBILEIRON_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        endpoint = "/dm/devices"
        request_params = {"limit": "1"}

        action_result = ActionResult()

        self.save_progress(MOBILEIRON_MSG_GET_DEVICES_TEST)

        ret_val, response = self._make_rest_call(endpoint, request_params, action_result)

        if phantom.is_fail(ret_val):
            self.debug_print(action_result.get_message())
            self.set_status(phantom.APP_ERROR, action_result.get_message())
            self.append_to_message(MOBILEIRON_ERR_CONNECTIVITY_TEST)
            return phantom.APP_ERROR

        return self.set_status_save_progress(phantom.APP_SUCCESS, MOBILEIRON_SUCC_CONNECTIVITY_TEST)

    def _list_devices(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            offset = int(param[MOBILEIRON_JSON_START_INDEX])
            if offset < 0:
                return action_result.set_status(phantom.APP_ERROR, MOBILEIRON_ERR_INVALID_INPUT, param=MOBILEIRON_JSON_START_INDEX)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, MOBILEIRON_ERR_INVALID_INPUT, param=MOBILEIRON_JSON_START_INDEX)

        try:
            limit = int(param[MOBILEIRON_JSON_LIMIT])
            if limit <= 0:
                return action_result.set_status(phantom.APP_ERROR, MOBILEIRON_ERR_INVALID_INPUT, param=MOBILEIRON_JSON_LIMIT)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, MOBILEIRON_ERR_INVALID_INPUT, param=MOBILEIRON_JSON_LIMIT)

        # Progress
        self.save_progress(MOBILEIRON_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        endpoint = "/dm/devices"
        request_params = {"offset": str(param[MOBILEIRON_JSON_START_INDEX]), "limit": str(param[MOBILEIRON_JSON_LIMIT])}

        action_result.update_summary({MOBILEIRON_JSON_TOTAL_DEVICES: 0})

        ret_val, response = self._make_rest_call(endpoint, request_params, action_result)

        if phantom.is_fail(ret_val):
            self.debug_print(action_result.get_message())
            return action_result.get_status()

        if not response.get("totalCount"):
            return action_result.get_status()

        if not response.get("devices"):
            return action_result.get_status()

        device_list = response["devices"].get("device")
        if not device_list:
            return action_result.get_status()

        # if there is only one device, then we get a dictionary
        if type(device_list) == dict:
            device_list = [device_list]

        action_result.update_summary({MOBILEIRON_JSON_TOTAL_DEVICES: len(device_list)})

        for device in device_list:
            action_result.add_data(device)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _lock_device(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self.__uuid_regex.match(param[MOBILEIRON_JSON_UUID]):
            return action_result.set_status(phantom.APP_ERROR, MOBILEIRON_ERR_INVALID_UUID)

        # Progress
        self.save_progress(MOBILEIRON_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        endpoint = f"/dm/devices/lock/{param[MOBILEIRON_JSON_UUID]}"
        reason = param.get(MOBILEIRON_JSON_REASON, "")
        reason += ". " if reason else ""
        reason += "Locked via Phantom"
        request_params = {"reason": reason}

        ret_val, response = self._make_rest_call(endpoint, request_params, action_result, "put")

        message = ""

        if response:
            if "messages" in response:
                if "message" in response["messages"]:
                    message = "Message from server: {}".format(response["messages"]["message"])

        if phantom.is_fail(ret_val):
            action_result.append_to_message(message)
            self.debug_print(action_result.get_message())
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _unlock_device(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self.__uuid_regex.match(param[MOBILEIRON_JSON_UUID]):
            return action_result.set_status(phantom.APP_ERROR, MOBILEIRON_ERR_INVALID_UUID)

        # Progress
        self.save_progress(MOBILEIRON_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        endpoint = f"/dm/devices/unlock/{param[MOBILEIRON_JSON_UUID]}"
        reason = param.get(MOBILEIRON_JSON_REASON, "")
        reason += ". " if reason else ""
        reason += "Unlocked via Phantom"
        request_params = {"reason": reason}

        ret_val, response = self._make_rest_call(endpoint, request_params, action_result)

        message = ""

        if response:
            if "messages" in response:
                if "message" in response["messages"]:
                    message = "Message from server: {}".format(response["messages"]["message"])

        if phantom.is_fail(ret_val):
            action_result.append_to_message(message)
            self.debug_print(action_result.get_message())
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _get_system_info(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self.__uuid_regex.match(param[MOBILEIRON_JSON_UUID]):
            return action_result.set_status(phantom.APP_ERROR, MOBILEIRON_ERR_INVALID_UUID)

        # Progress
        self.save_progress(MOBILEIRON_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        endpoint = f"/dm/devices/{param[MOBILEIRON_JSON_UUID]}"

        ret_val, response = self._make_rest_call(endpoint, None, action_result)

        message = ""

        if response:
            if "messages" in response:
                if "message" in response["messages"]:
                    message = "Message from server: {}".format(response["messages"]["message"])

        if response:
            action_result.add_data(response)

        if phantom.is_fail(ret_val):
            action_result.append_to_message(message)
            self.debug_print(action_result.get_message())
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this connector run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity(param)
        elif action_id == self.ACTION_ID_LIST_DEVICES:
            ret_val = self._list_devices(param)
        elif action_id == self.ACTION_ID_LOCK_DEVICE:
            ret_val = self._lock_device(param)
        elif action_id == self.ACTION_ID_UNLOCK_DEVICE:
            ret_val = self._unlock_device(param)
        elif action_id == self.ACTION_ID_GET_SYSTEM_INFO:
            ret_val = self._get_system_info(param)

        return ret_val


if __name__ == "__main__":
    import json
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

        connector = MobileIronConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
