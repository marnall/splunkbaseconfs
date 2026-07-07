# File: mfeepo_connector.py
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

import threading
import time

import phantom.app as phantom
import requests
import simplejson as json
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Local imports
from mfeepo_consts import *


class EpoConnector(BaseConnector):
    ACTION_ID_ADD_TAG = "add_tag"
    ACTION_ID_REMOVE_TAG = "remove_tag"
    ACTION_ID_GET_DEVICE_INFO = "get_device_info"
    ACTION_ID_QUARANTINE_DEVICE = "quarantine_device"
    ACTION_ID_UNQUARANTINE_DEVICE = "unquarantine_device"

    def __init__(self):
        self._username = None
        self._password = None
        self._host = None
        self._port = None

        self._lock = threading.Lock()
        self._done = False  # Is it done waking up agent?

        super().__init__()
        return

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_message = ERROR_MESSAGE_UNAVAILABLE

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except Exception as e:
            self.debug_print(f"Error occurred while fetching exception information. Details: {e!s}")

        if not error_code:
            error_text = f"Error Message: {error_message}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_message}"

        return error_text

    def _make_rest_call(self, endpoint, params, action_result):
        config = self.get_config()

        res = {}

        if params:
            params.update({":output": "json"})

        # Make a REST call
        try:
            url = f"{self._url}{endpoint}"
            res = requests.get(
                url,
                auth=(self._username, self._password),
                params=params,
                verify=config.get(phantom.APP_JSON_VERIFY, False),
                timeout=DEFAULT_TIMEOUT,
            )
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            msg = f"Error Connecting to server. Details: {error_message}"
            self.debug_print(msg)
            return action_result.set_status(phantom.APP_ERROR, msg), res

        if not (200 <= res.status_code < 399):
            msg = f"The server {self._host}:{self._port} could not fulfill the request. Error code: {res.status_code}, Reason: {res.reason}"
            return action_result.set_status(phantom.APP_ERROR, msg), res

        # Parse the response
        try:
            res = res.text
            res = json.loads(res[3:])
        except Exception as e:
            msg = f"Error while parsing the JSON. Error: {e!s}"
            self.debug_print(msg)
            return action_result.set_status(phantom.APP_ERROR, msg), res

        return phantom.APP_SUCCESS, res

    def _check_tag(self, tags, tag):
        """Check if tag is present in tags
        " Tags is expected to be a string, like "tag1, tag2..."
        """
        # Convert tags to a list from a string
        tags = [x.strip() for x in tags.split(",")]
        if tag in tags:
            return True
        else:
            return False

    def _transmogrify_dict(self, x):
        """Turn the tags from the literal string "tag1, tag2,...
        "  into a list
        " Replace periods w/ underscores in key names
        """
        try:
            x[KEY_TAGS] = [{"Tag": v.strip()} for v in x[KEY_TAGS].split(",")]
            x[KEY_ETAGS] = [{"Tag": v.strip()} for v in x[KEY_ETAGS].split(",")]
        except Exception:  # Something went wrong. Probably the wrong dictionary
            pass
        return dict((k.replace(".", "_"), v) for k, v in x.items())

    def _test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Attempting to connect to ePO")

        ret_val, _ = self._make_rest_call("system.find", {"param1": self._host}, action_result)

        if phantom.is_fail(ret_val):
            self.save_progress("Connectivity test failed")
            return action_result.get_status()

        self.save_progress("Connectivity test passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _wakeup_agent(self, action_result, host):
        self.save_progress("Attempting to wake up agent")
        thread = threading.Thread(target=self._wait_for_wakeup)
        thread.start()
        try:
            _, res = self._make_rest_call("system.wakeupAgent", {"param1": host}, action_result)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self._join_thread(thread)
            return action_result.set_status(phantom.APP_ERROR, error_message)

        self._join_thread(thread)
        self.debug_print(f"Response after attempting to wake up agent: {res}")
        if res == 0:
            return action_result.set_status(phantom.APP_ERROR, "Failed to wakeup agent")
        else:
            return action_result.set_status(phantom.APP_SUCCESS, "Successfully woke up agent")

    def _join_thread(self, thread):
        self._lock.acquire()
        self._done = True
        self._lock.release()
        thread.join()
        return

    def _wait_for_wakeup(self):
        """Keep message updated while waking up host"""
        i = 0
        while True:
            self._lock.acquire()
            if self._done:
                self._lock.release()
                break
            self.send_progress("Attempting to wake up agent" + "." * i)
            self._lock.release()
            i = i % 5 + 1
            time.sleep(1)
        return

    def _validate_tag(self, action_result, host, tag):
        """Validate that a tag exists
        " Also, fix the case of the tag
        """
        try:
            ret_val, tag_dicts = self._make_rest_call("system.findTag", {"param1": tag}, action_result)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, error_message), None

        if phantom.is_fail(ret_val):
            return action_result.get_status(), tag

        for tag_dict in tag_dicts:
            if tag_dict["tagName"].lower() == tag.lower():
                return action_result.set_status(phantom.APP_SUCCESS), tag_dict["tagName"]

        # Couldn't find tag
        return action_result.set_status(phantom.APP_ERROR, f"There is no tag: {tag}"), None

    def _add_tag(self, param):
        """Actual handler for add_tag action"""
        return self.__add_tag(param)

    def _quarantine_device(self, param):
        return self.__add_tag(param, quarantine=True)

    def __add_tag(self, param, quarantine=False):
        action_result = self.add_action_result(ActionResult(dict(param)))

        host = param[EPO_JSON_HOST]  # Endpoint to add tag to
        wakeup_agent = param.get(EPO_JSON_WAKEUP_AGENT, False)
        if quarantine:
            tag = self.get_config().get(EPO_JSON_QTAG, "")
            if not tag:
                return action_result.set_status(phantom.APP_ERROR, "Please provide the quarantine tag in asset configuration parameter")
        else:
            tag = param[EPO_JSON_TAG]

        ret_val, tag = self._validate_tag(action_result, host, tag)

        # Tag doesn't exist
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, r_dict = self._find(action_result, host)

        # Host doesn't exist
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Endpoint already has tag
        if self._check_tag(r_dict[KEY_TAGS], tag):
            return action_result.set_status(phantom.APP_SUCCESS, "Success, tag already added")

        ret_val = self._apply_tag(action_result, host, tag)

        if not wakeup_agent or phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val = self._wakeup_agent(action_result, host)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, "Assigned tag but host did not receive configuration")

        return action_result.set_status(phantom.APP_SUCCESS, "Assigned tag and host received configuration")

    def _apply_tag(self, action_result, host, tag):
        try:
            _, res = self._make_rest_call("system.applyTag", {"param1": host, "param2": tag}, action_result)

        except Exception:  # Something went wrong
            return action_result.set_status(phantom.APP_ERROR, "Failed to assign tag")

        if res == 0:  # Something else went wrong
            return action_result.set_status(phantom.APP_ERROR, "Failed to assign tag")
        else:
            return action_result.set_status(phantom.APP_SUCCESS, "Successfully assigned tag")

    def _remove_tag(self, param):
        """actual handler for remove_tag action"""
        return self.__remove_tag(param)

    def _unquarantine_device(self, param):
        return self.__remove_tag(param, quarantine=True)

    def __remove_tag(self, param, quarantine=False):
        action_result = self.add_action_result(ActionResult(dict(param)))

        host = param[EPO_JSON_HOST]  # Endpoint to remove tag from
        wakeup_agent = param.get(EPO_JSON_WAKEUP_AGENT, False)
        if quarantine:
            tag = self.get_config().get(EPO_JSON_QTAG, "")
            if not tag:
                return action_result.set_status(phantom.APP_ERROR, "Please provide the quarantine tag in asset configuration parameter")
        else:
            tag = param[EPO_JSON_TAG]

        ret_val, tag = self._validate_tag(action_result, host, tag)

        # Tag doesn't exist
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, r_dict = self._find(action_result, host)

        # Host doesn't exist
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Endpoint already has tag
        if not self._check_tag(r_dict[KEY_TAGS], tag):
            return action_result.set_status(phantom.APP_SUCCESS, "Success, tag not present")

        ret_val = self._clear_tag(action_result, host, tag)

        if not wakeup_agent or phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val = self._wakeup_agent(action_result, host)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, "Removed tag but host did not receive configuration")

        return action_result.set_status(phantom.APP_SUCCESS, "Removed tag and host received configuration")

    def _clear_tag(self, action_result, host, tag):
        try:
            _, resp = self._make_rest_call("system.clearTag", {"param1": host, "param2": tag}, action_result)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Failed to remove tag")

        if resp == 0:
            return action_result.set_status(phantom.APP_ERROR, "Failed to remove tag")
        else:
            return action_result.set_status(phantom.APP_SUCCESS, "Successfully removed tag")

    def _get_device_info(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        host = param[EPO_JSON_HOST]  # Endpoint to get info from

        ret_val, r_dict = self._find(action_result, host)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        config = self.get_config()
        r_dict = self._transmogrify_dict(r_dict)
        r_dict["EPO_IP/Hostname"] = config[EPO_JSON_HOST]
        r_dict["EPO_Port"] = config[EPO_JSON_PORT]
        action_result.add_data(r_dict)
        return action_result.get_status()

    def _find(self, action_result, host):
        """Get device info and add it to action result
        " Also used to confirm that device exists / is connectable
        """
        try:
            # result is a list of matching hosts
            ret_val, result = self._make_rest_call("system.find", {"param1": host}, action_result)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, error_message), None

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        for r in result:
            if r[IP_ADDR] == host or r[NAME].lower() == host.lower():
                return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved device info"), r

        return action_result.set_status(phantom.APP_ERROR, "Failed to locate host"), None

    def handle_action(self, param):
        action = self.get_action_identifier()
        ret_val = phantom.APP_SUCCESS

        if action == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity(param)
        elif action == self.ACTION_ID_ADD_TAG:
            ret_val = self._add_tag(param)
        elif action == self.ACTION_ID_REMOVE_TAG:
            ret_val = self._remove_tag(param)
        elif action == self.ACTION_ID_GET_DEVICE_INFO:
            ret_val = self._get_device_info(param)
        elif action == self.ACTION_ID_QUARANTINE_DEVICE:
            ret_val = self._quarantine_device(param)
        elif action == self.ACTION_ID_UNQUARANTINE_DEVICE:
            ret_val = self._unquarantine_device(param)

        return ret_val

    def initialize(self):
        # get the asset config
        config = self.get_config()

        self._host = config[EPO_JSON_HOST]
        self._port = config[EPO_JSON_PORT]
        self._url = f"https://{self._host}:{self._port}/remote/"
        self._username = config[EPO_JSON_USERNAME]
        self._password = config[EPO_JSON_PASSWORD]

        return phantom.APP_SUCCESS


if __name__ == "__main__":
    # Imports
    import sys

    import pudb

    # Breakpoint at runtime
    pudb.set_trace()

    # The first param is the input json file
    with open(sys.argv[1]) as f:
        # Load the input json file
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=" " * 4))

        # Create the connector class object
        connector = EpoConnector()

        # Se the member vars
        connector.print_progress_message = True

        # Call BaseConnector::_handle_action(...) to kickoff action handling.
        ret_val = connector._handle_action(json.dumps(in_json), None)

        # Dump the return value
        print(ret_val)

    sys.exit(0)
