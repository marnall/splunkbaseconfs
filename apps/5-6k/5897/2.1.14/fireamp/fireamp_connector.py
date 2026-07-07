# File: fireamp_connector.py
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
# Phantom imports
import base64 as b64
from datetime import datetime
from uuid import UUID

import phantom.app as phantom
import requests
import simplejson as json
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Local Imports
from fireamp_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class FireAMPConnector(BaseConnector):
    ACTION_ID_LIST_ENDPOINTS = "list_endpoints"
    ACTION_ID_HUNT_FILE = "hunt_file"
    ACTION_ID_HUNT_IP = "hunt_ip"
    ACTION_ID_HUNT_URL = "hunt_url"
    ACTION_ID_GET_DEVICE_INFO = "get_device_info"
    ACTION_ID_BLOCK_HASH = "block_hash"
    ACTION_ID_UNBLOCK_HASH = "unblock_hash"
    ACTION_ID_LIST_FILELISTS = "list_filelists"
    ACTION_ID_GET_FILELIST = "get_filelist"
    ACTION_ID_FIND_LISTITEM = "find_listitem"
    ACTION_ID_REMOVE_LISTITEM = "remove_listitem"
    ACTION_ID_FIND_DEVICE = "find_device"
    ACTION_ID_LIST_GROUPS = "list_groups"
    ACTION_ID_CHANGE_GROUP = "change_group"
    ACTION_ID_LIST_POLICIES = "list_policies"
    ACTION_ID_CHANGE_POLICY = "change_policy"
    ACTION_ID_QUARANTINE = "quarantine_device"
    ACTION_ID_UNQUARANTINE = "unquarantine_device"
    ACTION_ID_ALLOW_HASH = "allow_hash"
    ACTION_ID_DISALLOW_HASH = "disallow_hash"
    ACTION_ID_GET_DEVICE_TRAJECTORY = "get_device_trajectory"
    ACTION_ID_GET_DEVICE_EVENTS = "get_device_events"
    ACTION_ID_ADD_LISTITEM = "add_listitem"

    def __init__(self):
        self._base_url = None

        super().__init__()

    def initialize(self):
        """Called once for every action, all member initializations occur here"""

        config = self.get_config()

        # Get the Base URL from the asset config and so some cleanup
        self._base_url = config.get(AMP_JSON_BASE_URL, BASE_URL)
        if self._base_url.endswith("/"):
            self._base_url = self._base_url[:-1]

        return phantom.APP_SUCCESS

    def _create_auth_header(self):
        config = self.get_config()
        client_id = config[AMP_JSON_API_CLIENT_ID]
        api_key = config[AMP_JSON_API_KEY]
        # Authtoken is client id an api_key encoded with : between them
        auth_string = f"{client_id}:{api_key}"
        auth = b64.b64encode(auth_string.encode("utf-8")).decode()
        header = {"Authorization": f"Basic {auth}"}
        return header

    def _make_rest_call(self, endpoint, method="get", params=None, data=None):
        url = f"{self._base_url}{endpoint}"
        headers = self._create_auth_header()

        if data:
            headers["Accept"] = "application/json"
            headers["Content-Type"] = "application/json"

        request_func = getattr(requests, method)
        if not request_func:
            return (phantom.APP_ERROR, f"Invalid method call: {method} for requests module")

        self.send_progress("Making API Call")

        try:
            r = request_func(url, headers=headers, params=params, data=data)
        except Exception as e:
            # Some error making request
            return (phantom.APP_ERROR, f"REST call to server failed: {e}")

        if r.status_code != 200 and r.status_code != 201 and r.status_code != 202:
            if r.reason == "Not Found" and "computers" in endpoint:
                return (phantom.APP_SUCCESS, AMP_ENDPOINT_NOT_FOUND)
            if r.reason == "Not Found" and "file_lists" in endpoint:
                if method == "post":
                    return (phantom.APP_SUCCESS, AMP_FILE_LIST_NOT_FOUND)
                else:
                    return (phantom.APP_SUCCESS, AMP_FILE_UNBLOCK_NOT_FOUND)
            if r.status_code == 409 and "file_lists" in endpoint:
                return (phantom.APP_SUCCESS, AMP_DUPLICATE_FILE_HASH)

            try:
                resp_json = json.loads(r.content)
                error = resp_json.get("error")

                if error:
                    return (phantom.APP_ERROR, "Error processing request: {}".format(error.get("message")))

                return (phantom.APP_ERROR, "Error processing request: {}".format(resp_json["errors"][0]["details"][0]))

            except Exception:
                return (phantom.APP_ERROR, f"Error processing request: {r.content}")

        try:
            resp_json = r.json()
            return (phantom.APP_SUCCESS, resp_json)
        except Exception as e:
            # Some error parsing response
            return (phantom.APP_ERROR, f"Error while parsing response: {e}")

    def _test_asset_connectivity(self):
        action_result = ActionResult()

        endpoint = "/v1/version"

        self.save_progress("Testing asset connectivity")

        ret_val, resp_json = self._make_rest_call(endpoint)

        # Process errors
        if phantom.is_fail(ret_val):
            # Dump error messages in the log
            self.debug_print(action_result.get_message())

            # Set the status of the complete connector result
            self.set_status(phantom.APP_ERROR, action_result.get_message())

            # Append the message to display
            self.append_to_message("Test Connectivity Failed. Please provide valid configuration parameters")

            # return error
            return phantom.APP_ERROR

        # Set the status of the connector result
        return self.set_status_save_progress(phantom.APP_SUCCESS, "Test Connectivity Passed")

    def _list_endpoints(self, param):
        self.save_progress("Running action - list endpoint")

        action_result = self.add_action_result(ActionResult(param))
        endpoint = "/v1/computers"

        action_result.update_summary({"total_endpoints": 0})

        self.save_progress("sending http request to list endpoint")
        ret_val, resp_json = self._make_rest_call(endpoint)
        if phantom.is_fail(ret_val) or resp_json == AMP_ENDPOINT_NOT_FOUND:
            return action_result.set_status(ret_val, resp_json)

        action_result.add_data(resp_json)

        metadata = resp_json.get("metadata")
        if metadata:
            action_result.update_summary({"total_endpoints": metadata.get("results", {}).get("total", 0)})
        return action_result.set_status(phantom.APP_SUCCESS)

    def _hunt_action(self, action_result, query, check_execution=False):
        endpoint = "/v1/computers/activity"
        params = {"q": query}
        ret_val, response = self._make_rest_call(endpoint, params=params)

        if phantom.is_fail(ret_val) or response == AMP_ENDPOINT_NOT_FOUND:
            return action_result.set_status(ret_val, response)

        if check_execution:
            response["data"] = self._check_file_execution(response.get("data"), query)

        action_result.add_data(response)

        action_result.set_summary({"device_count": len(response["data"])})

        return phantom.APP_SUCCESS

    def _check_file_execution(self, response_data, file_hash):
        guids = [(i, entry["connector_guid"]) for i, entry in enumerate(response_data)]

        for index, guid in guids:
            endpoint = f"/v1/computers/{guid}/trajectory"
            params = {"q": file_hash}
            ret_val, response = self._make_rest_call(endpoint, params=params)
            response_data[index]["file_execution_details"] = {"executed": False, "file_name": "", "file_path": "", "message": ""}
            if phantom.is_fail(ret_val):
                response_data[index]["file_execution_details"]["message"] = f"Unable to retrieve execution details. Details - {response!s}"
            else:
                events = response.get("data", {}).get("events") or []

                for event in events:
                    event_type = event.get("event_type")
                    if event_type == "Executed by" and file_hash == event["file"]["identity"]["sha256"]:
                        response_data[index]["file_execution_details"]["executed"] = True
                        response_data[index]["file_execution_details"]["file_name"] = event["file"]["file_name"]
                        response_data[index]["file_execution_details"]["file_path"] = event["file"]["file_path"]
                        response_data[index]["file_execution_details"]["message"] = "File executed"
                if response_data[index]["file_execution_details"]["message"] == "":
                    response_data[index]["file_execution_details"]["message"] = "File not executed"

        return response_data

    def _hunt_file(self, param):
        action_result = self.add_action_result(ActionResult(param))
        ret_val = self._hunt_action(action_result, param[AMP_JSON_HASH], check_execution=param.get("check_execution"))
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _hunt_ip(self, param):
        action_result = self.add_action_result(ActionResult(param))
        ret_val = self._hunt_action(action_result, param[AMP_JSON_IP])

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _hunt_url(self, param):
        action_result = self.add_action_result(ActionResult(param))
        ret_val = self._hunt_action(action_result, param[AMP_JSON_URL])

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_unquarantine_device(self, param):
        self.save_progress("Running action - unquarantine device")
        self.save_progress("Changing status of quarantine to stop")
        return self._quarantine_status_change(param, "stop")

    def _handle_quarantine_device(self, param):
        self.save_progress("Running action - quarantine device")
        self.save_progress("Changing status of quarantine to start")
        return self._quarantine_status_change(param, "start")

    def _quarantine_status_change(self, param, quarantine_action):
        action_result = self.add_action_result(ActionResult(param))
        c_guid = None

        try:
            c_guid = param[AMP_JSON_CONNECTOR_GUID]  # Connector GUID
            UUID(c_guid, version=4)
        except ValueError:
            return action_result.set_status(phantom.APP_ERROR, "Parameter connector_guid failed validation")

        http_method = "put" if quarantine_action == "start" else "delete"
        ret_val, resp_json = self._make_rest_call(f"/v1/computers/{c_guid}/isolation", method=http_method)
        action_result.add_data(resp_json)
        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, f"Failed to {quarantine_action} quarantine on {c_guid}. Details: {resp_json!s}")
        elif resp_json == AMP_ENDPOINT_NOT_FOUND:
            return action_result.set_status(ret_val, resp_json)

        return action_result.set_status(phantom.APP_SUCCESS, f"Success: {quarantine_action} quarantine on {c_guid}")

    def _get_group_guid_by_name(self, group_name, action_result):
        endpoint = f"/v1/groups?name={group_name}"

        ret_val, resp_json = self._make_rest_call(endpoint)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, "Unable to retrieve group"), None

        if not resp_json.get("data"):
            return action_result.set_status(phantom.APP_ERROR, "Unable to find specified group"), None

        return phantom.APP_SUCCESS, resp_json["data"][0]["guid"]

    def _list_groups(self, param):
        self.save_progress("Running action - list groups")
        action_result = self.add_action_result(ActionResult(param))

        self.save_progress("Sending http request for list groups")
        ret_val, resp_json = self._make_rest_call("/v1/groups")

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, resp_json)

        summary = {"group_count": len(resp_json["data"])}

        action_result.add_data(resp_json)
        action_result.update_summary(summary)

        return action_result.set_status(phantom.APP_SUCCESS, "Found {} groups".format(len(resp_json.get("data", []))))

    def _list_policies(self, param):
        self.save_progress("Running action - list policies")
        action_result = self.add_action_result(ActionResult(param))
        params = {}

        if param.get("product"):
            params["product[]"] = param.get("product")
        if param.get("name"):
            params["name[]"] = param.get("name")

        self.save_progress("sending http request to list policies")
        ret_val, resp_json = self._make_rest_call("/v1/policies", params=params)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, resp_json)

        summary = {"policy_count": len(resp_json["data"])}

        action_result.add_data(resp_json)
        action_result.update_summary(summary)

        return action_result.set_status(phantom.APP_SUCCESS, "Found {} policies".format(len(resp_json["data"])))

    def _get_policy_guid_by_name(self, policy_name, action_result):
        endpoint = "/v1/policies"

        params = {"name[]": policy_name, "product[]": "windows"}

        ret_val, resp_json = self._make_rest_call(endpoint, params=params)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, "Unable to retrieve policy"), None

        if not resp_json.get("data"):
            return action_result.set_status(phantom.APP_ERROR, "Unable to find specified policy"), None

        return phantom.APP_SUCCESS, resp_json["data"][0]["guid"]

    def _change_policy(self, param):
        action_result = self.add_action_result(ActionResult(param))

        policy_guid = None
        group_guid = None
        if param.get("group_name") and param.get("group_guid"):
            return action_result.set_status(phantom.APP_ERROR, "Provide either a group name or group guid, not both")

        if param.get("policy_name") and param.get("policy_guid"):
            return action_result.set_status(phantom.APP_ERROR, "Provide either a policy name or policy guid, not both")

        if not (param.get("group_name") or param.get("group_guid")):
            return action_result.set_status(phantom.APP_ERROR, "Provide either a group name or group guid")

        if not (param.get("policy_name") or param.get("policy_guid")):
            return action_result.set_status(phantom.APP_ERROR, "Provide either a policy name or policy guid")

        if param.get("group_name"):
            ret_val, group_guid = self._get_group_guid_by_name(param.get("group_name"), action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
        elif param.get("group_guid"):
            group_guid = param.get("group_guid")

        if param.get("policy_name"):
            ret_val, policy_guid = self._get_policy_guid_by_name(param.get("policy_name"), action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status()

        elif param.get("policy_guid"):
            policy_guid = param.get("policy_guid")

        payload = json.dumps({"windows_policy_guid": policy_guid})

        ret_val, resp_json = self._make_rest_call(f"/v1/groups/{group_guid}", data=payload, method="patch")

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, resp_json)

        summary = {"policy_changed": True, "policy_guid": policy_guid}

        action_result.update_summary(summary)
        action_result.add_data(summary)

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully changed windows policy")

    def _change_group(self, param):
        action_result = self.add_action_result(ActionResult(param))
        c_guid = None
        group_guid = None

        try:
            c_guid = param[AMP_JSON_CONNECTOR_GUID]  # Connector GUID
            UUID(c_guid, version=4)
        except ValueError:
            return action_result.set_status(phantom.APP_ERROR, "Parameter connector_guid failed validation")

        if param.get("group_name") and param.get("group_guid"):
            return action_result.set_status(phantom.APP_ERROR, "Provide either a group name or group guid, not both")

        if not (param.get("group_name") or param.get("group_guid")):
            return action_result.set_status(phantom.APP_ERROR, "Provide either a group name or group guid")

        if param.get("group_name"):
            ret_val, group_guid = self._get_group_guid_by_name(param.get("group_name"), action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status()

        elif param.get("group_guid"):
            group_guid = param.get("group_guid")

        payload = json.dumps({"group_guid": group_guid})

        ret_val, resp_json = self._make_rest_call(f"/v1/computers/{c_guid}", data=payload, method="patch")
        if phantom.is_fail(ret_val) or resp_json == AMP_ENDPOINT_NOT_FOUND:
            return action_result.set_status(ret_val, resp_json)

        summary = {"group_changed": True, "group_guid": group_guid}

        action_result.update_summary(summary)
        action_result.add_data(summary)

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully changed group")

    def _find_device(self, param):
        action_result = self.add_action_result(ActionResult(param))

        params = {}

        if param.get("group_name") and param.get("group_guid"):
            return action_result.set_status(phantom.APP_ERROR, "Provide either a group name or group guid, not both")

        if param.get("group_name"):
            ret_val, params["group_guid[]"] = self._get_group_guid_by_name(param.get("group_name"), action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
        elif param.get("group_guid"):
            params["group_guid[]"] = param.get("group_guid")
        if param.get("hostname"):
            params["hostname[]"] = param.get("hostname")
        if param.get("external_ip"):
            params["external_ip"] = param.get("external_ip")
        if param.get("internal_ip"):
            params["internal_ip"] = param.get("internal_ip")

        if params and param.get("user"):
            return action_result.set_status(phantom.APP_ERROR, "User cannot be used in conjunction with any other search option")

        if not (params or param.get("user")):
            return action_result.set_status(phantom.APP_ERROR, AMP_FIND_DEVICE_ERR_MSG)

        if param.get("user"):
            ret_val, resp_json = self._make_rest_call("/v1/computers/user_activity?q={}".format(param.get("user")))

            if phantom.is_fail(ret_val) or resp_json == AMP_ENDPOINT_NOT_FOUND:
                return action_result.set_status(ret_val, resp_json)

            results_data = resp_json.get("metadata")
            results_data["version"] = resp_json.get("version")
            results_data["data"] = []

            if not resp_json.get("data"):
                return action_result.set_status(phantom.APP_SUCCESS, "Unable to find endpoint by user")

            for datum in resp_json["data"]:
                ret_val, resp_json = self._make_rest_call("/v1/computers/{}".format(datum["connector_guid"]))
                if phantom.is_fail(ret_val):
                    return action_result.set_status(phantom.APP_ERROR, "Unable to get computer details")
                elif resp_json == AMP_ENDPOINT_NOT_FOUND:
                    return action_result.set_status(ret_val, resp_json)

                results_data["data"].append(resp_json.get("data"))

            resp_json = results_data

        else:
            endpoint = "/v1/computers"

            ret_val, resp_json = self._make_rest_call(endpoint, params=params)

            if phantom.is_fail(ret_val) or resp_json == AMP_ENDPOINT_NOT_FOUND:
                return action_result.set_status(ret_val, resp_json)

        action_result.update_summary({"total_endpoints": len(resp_json["data"])})

        action_result.add_data(resp_json)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_device_info(self, param):
        self.save_progress("Running action - get device info")

        action_result = self.add_action_result(ActionResult(param))

        try:
            c_guid = param[AMP_JSON_CONNECTOR_GUID]  # Connector GUID
            UUID(c_guid, version=4)
        except ValueError:
            return action_result.set_status(phantom.APP_ERROR, "Parameter connector_guid failed validation")

        endpoint = f"/v1/computers/{c_guid}"

        self.save_progress("Making rest call to get device info")

        ret_val, resp_json = self._make_rest_call(endpoint)

        action_result.update_summary({"total_endpoints": 0})

        if phantom.is_fail(ret_val) or resp_json == AMP_ENDPOINT_NOT_FOUND:
            return action_result.set_status(ret_val, resp_json)

        action_result.update_summary({"total_endpoints": 1})
        action_result.add_data(resp_json)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_disallow_hash(self, param):
        self.save_progress("Running action - block hash")
        self.save_progress("Calling function block hash")
        return self._handle_unblock_hash(param)

    def _handle_allow_hash(self, param):
        self.save_progress("Running action - block hash")
        self.save_progress("calling function unblock hash")
        return self._handle_block_hash(param)

    def _handle_block_hash(self, param):
        self.save_progress("Running action - allow hash")
        action_result = self.add_action_result(ActionResult(param))
        sha256_hash = param[AMP_JSON_HASH]

        try:
            list_guid = param[AMP_JSON_LIST_GUID]  # List GUID
            UUID(list_guid, version=4)
        except ValueError:
            return action_result.set_status(phantom.APP_ERROR, "Parameter file_list_guid failed validation")

        endpoint = f"/v1/file_lists/{list_guid}/files/{sha256_hash}"
        action_result.update_summary({"file_added_to_list": False})
        ret_val, resp_json = self._make_rest_call(endpoint, method="post")

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, resp_json)

        elif resp_json == AMP_DUPLICATE_FILE_HASH or resp_json == AMP_FILE_LIST_NOT_FOUND:
            return action_result.set_status(ret_val, resp_json)

        elif resp_json.get("data", {}).get("sha256"):
            action_result.update_summary({"file_added_to_list": True})
            action_result.add_data(resp_json)
            return action_result.set_status(phantom.APP_SUCCESS, AMP_FILE_HASH_ADDED)

        else:
            self.save_progress(f"Error occurred for action - block hash json_response: {resp_json}")
            return action_result.set_status(phantom.APP_ERROR, resp_json)

    def _handle_unblock_hash(self, param):
        self.save_progress("Running action - disallow hash")
        action_result = self.add_action_result(ActionResult(param))
        sha256_hash = param[AMP_JSON_HASH]

        try:
            list_guid = param[AMP_JSON_LIST_GUID]  # List GUID
            UUID(list_guid, version=4)
        except ValueError:
            return action_result.set_status(phantom.APP_ERROR, "Parameter file_list_guid failed validation")

        endpoint = f"/v1/file_lists/{list_guid}/files/{sha256_hash}"
        action_result.update_summary({"file_removed_from_list": False})
        self.save_progress("Making rest call to unblock hash")
        ret_val, resp_json = self._make_rest_call(endpoint, method="delete")

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, resp_json)

        elif resp_json == AMP_FILE_UNBLOCK_NOT_FOUND:
            return action_result.set_status(phantom.APP_SUCCESS, AMP_FILE_UNBLOCK_NOT_FOUND)

        elif resp_json.get("errors") is None:
            action_result.update_summary({"file_removed_from_list": True})
            action_result.add_data(resp_json)
            return action_result.set_status(phantom.APP_SUCCESS, AMP_FILE_HASH_REMOVED)

        else:
            return action_result.set_status(phantom.APP_ERROR, resp_json)

    def _list_filelists(self, param):
        action_result = self.add_action_result(ActionResult(param))
        endpoint1 = "/v1/file_lists/application_blocking"
        endpoint2 = "/v1/file_lists/simple_custom_detections"

        action_result.update_summary({"total_lists": 0})

        ret_val, resp_json = self._make_rest_call(endpoint1)
        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, resp_json)
        if resp_json.get("data"):
            for item in resp_json["data"]:
                action_result.add_data(item)
        else:
            action_result.add_data(resp_json)

        total_lists = 0
        metadata = resp_json.get("metadata")
        if metadata:
            total_lists = metadata.get("results", {}).get("total", 0)
            action_result.update_summary({"total_lists": total_lists})

        ret_val, resp_json = self._make_rest_call(endpoint2)
        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, resp_json)
        if resp_json.get("data"):
            for item in resp_json["data"]:
                action_result.add_data(item)
        else:
            action_result.add_data(resp_json)

        metadata = resp_json.get("metadata")
        if metadata:
            total_lists += metadata.get("results", {}).get("total", 0)
            action_result.update_summary({"total_lists": total_lists})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_list_guid_by_name(self, list_type, file_list_name, action_result):
        endpoint = f"/v1/file_lists/{list_type}"

        ret_val, resp_json = self._make_rest_call(endpoint)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, str(resp_json)), None

        if "data" not in resp_json:
            return action_result.set_status(phantom.APP_ERROR, "No " + list_type + " list found"), None

        list_guid = [datum["guid"] for datum in resp_json["data"] if datum["name"].lower() == file_list_name.lower()]

        if len(list_guid) == 0:
            return action_result.set_status(phantom.APP_ERROR, "File list (" + file_list_name + ") not found"), None

        return phantom.APP_SUCCESS, list_guid[0]

    def _remove_listitem(self, param):
        action_result = self.add_action_result(ActionResult(param))
        list_guid = None

        if not param.get(AMP_JSON_LIST_GUID):
            if not (param.get("type") and param.get("name")):
                return action_result.set_status(phantom.APP_ERROR, "Either type and name, or GUID are required for retrieving a file list")

            ret_val, list_guid = self._get_list_guid_by_name(param.get("type"), param.get("name"), action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status()

        else:
            try:
                list_guid = param.get(AMP_JSON_LIST_GUID)
                UUID(list_guid, version=4)
            except ValueError:
                return action_result.set_status(phantom.APP_ERROR, "Parameter file_list_guid failed validation")

        endpoint = f"/v1/file_lists/{list_guid}/files/{param[AMP_JSON_HASH]}"

        ret_val, resp_json = self._make_rest_call(endpoint, method="delete")

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, resp_json)

        summary = {"file_deleted": True}

        action_result.add_data(summary)
        action_result.update_summary(summary)

        return action_result.set_status(phantom.APP_SUCCESS, "File deleted from list")

    def _find_listitem(self, param):
        action_result = self.add_action_result(ActionResult(param))
        list_guid = None
        if not param.get(AMP_JSON_LIST_GUID):
            if not (param.get("type") and param.get("name")):
                return action_result.set_status(phantom.APP_ERROR, "Either type and name, or GUID are required for retrieving a file list")

            ret_val, list_guid = self._get_list_guid_by_name(param.get("type"), param.get("name"), action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
        else:
            try:
                list_guid = param.get(AMP_JSON_LIST_GUID)
                UUID(list_guid, version=4)
            except ValueError:
                return action_result.set_status(phantom.APP_ERROR, "Parameter file_list_guid failed validation")

        endpoint = f"/v1/file_lists/{list_guid}/files/{param[AMP_JSON_HASH]}"

        ret_val, resp_json = self._make_rest_call(endpoint)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, resp_json)

        action_result.add_data(resp_json)

        summary = {"file_found": True}

        action_result.update_summary(summary)

        return action_result.set_status(phantom.APP_SUCCESS, "File found")

    def _get_filelist(self, param):
        action_result = self.add_action_result(ActionResult(param))

        list_guid = None

        if not param.get(AMP_JSON_LIST_GUID):
            if not (param.get("type") and param.get("name")):
                return action_result.set_status(phantom.APP_ERROR, "Either type and name, or GUID are required for retrieving a file list")

            ret_val, list_guid = self._get_list_guid_by_name(param.get("type"), param.get("name"), action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
        else:
            try:
                list_guid = param.get(AMP_JSON_LIST_GUID)
                UUID(list_guid, version=4)
            except ValueError:
                return action_result.set_status(phantom.APP_ERROR, "Parameter file_list_guid failed validation")

        endpoint = f"/v1/file_lists/{list_guid}/files"

        action_result.update_summary({"total_hashes": 0})

        ret_val, resp_json = self._make_rest_call(endpoint)
        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, resp_json)
        elif resp_json == AMP_FILE_LIST_NOT_FOUND:
            return action_result.set_status(phantom.APP_SUCCESS, AMP_FILE_LIST_NOT_FOUND)

        action_result.add_data(resp_json)

        metadata = resp_json.get("metadata")
        if metadata:
            action_result.update_summary({"total_hashes": metadata["results"].get("total", 0)})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_device_trajectory(self, param):
        self.save_progress("Running action - get device trajectory")
        action_result = self.add_action_result(ActionResult(param))

        connector_guid = param["connector_guid"]
        limit = "?limit={}".format(param.get("limit", 500))
        hash_filter = "&q=" + param.get("filter") if param.get("filter") else ""
        days_back = param.get("days_back")

        if param.get("days_back"):
            if days_back < 0:
                return action_result.set_status(
                    phantom.APP_ERROR, "Please provide a valid non-negative integer value in the ‘days_back’ parameter"
                )

        endpoint = f"/v1/computers/{connector_guid}/trajectory{limit}{hash_filter}"

        self.save_progress("making rest request to get device trajectory")
        ret_val, resp_json = self._make_rest_call(endpoint)
        if phantom.is_fail(ret_val) or resp_json == AMP_ENDPOINT_NOT_FOUND:
            return action_result.set_status(ret_val, resp_json)

        resp_json["events"] = resp_json.get("data", {}).get("events")
        resp_json["computer"] = resp_json.get("data", {}).get("computer")
        resp_json.pop("data")

        if days_back:
            filtered_events = []
            for event in resp_json["events"]:
                event_date = datetime.strptime(event["date"].split("+")[0], "%Y-%m-%dT%H:%M:%S")
                if (datetime.now() - event_date).days <= days_back:
                    filtered_events.append(event)
            resp_json["events"] = filtered_events
        action_result.add_data(resp_json)

        action_result.update_summary({"total_trajectories": len(resp_json)})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_device_events(self, param):
        self.save_progress("Running action - get device events")

        action_result = self.add_action_result(ActionResult(param))

        event_params = {
            "detection_sha256": param.get("detection_sha256"),
            "application_sha256": param.get("application_sha256"),
            "connector_guid": param.get("connector_guid"),
            "group_guid": param.get("group_guid"),
            "start_date": param.get("start_date"),
            "offset": param.get("offset"),
            "event_type": param.get("event_type"),
            "limit": param.get("limit"),
        }

        query_params = {k: v for k, v in event_params.items() if v is not None}

        endpoint = "/v1/events"

        self.save_progress("making rest request to get device event")
        ret_val, resp_json = self._make_rest_call(endpoint, params=query_params)
        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, resp_json)

        resp_json["events"] = resp_json.get("data")
        resp_json.pop("data")

        action_result.add_data(resp_json)

        action_result.update_summary({"total_events": len(resp_json.get("events"))})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _add_listitem(self, param):
        action_result = self.add_action_result(ActionResult(param))
        list_guid = None

        if not param.get(AMP_JSON_LIST_GUID):
            if not (param.get("type") and param.get("name")):
                return action_result.set_status(phantom.APP_ERROR, "Either type and name, or GUID are required for retrieving a file list")

            ret_val, list_guid = self._get_list_guid_by_name(param.get("type"), param.get("name"), action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status()

        else:
            try:
                list_guid = param.get(AMP_JSON_LIST_GUID)
                UUID(list_guid, version=4)
            except ValueError:
                return action_result.set_status(phantom.APP_ERROR, "Parameter file_list_guid failed validation")

        endpoint = f"/v1/file_lists/{list_guid}/files/{param[AMP_JSON_HASH]}"

        ret_val, resp_json = self._make_rest_call(endpoint, method="post")

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, resp_json)

        summary = {"file_added": True}

        action_result.add_data(resp_json)
        action_result.update_summary(summary)

        return action_result.set_status(phantom.APP_SUCCESS, "File successfully added")

    def handle_action(self, param):
        action = self.get_action_identifier()
        ret_val = phantom.APP_SUCCESS
        if action == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_asset_connectivity()
        elif action == self.ACTION_ID_LIST_ENDPOINTS:
            ret_val = self._list_endpoints(param)
        elif action == self.ACTION_ID_HUNT_FILE:
            ret_val = self._hunt_file(param)
        elif action == self.ACTION_ID_HUNT_IP:
            ret_val = self._hunt_ip(param)
        elif action == self.ACTION_ID_HUNT_URL:
            ret_val = self._hunt_url(param)
        elif action == self.ACTION_ID_GET_DEVICE_INFO:
            ret_val = self._get_device_info(param)
        elif action == self.ACTION_ID_BLOCK_HASH:
            ret_val = self._handle_block_hash(param)
        elif action == self.ACTION_ID_UNBLOCK_HASH:
            ret_val = self._handle_unblock_hash(param)
        elif action == self.ACTION_ID_LIST_FILELISTS:
            ret_val = self._list_filelists(param)
        elif action == self.ACTION_ID_GET_FILELIST:
            ret_val = self._get_filelist(param)
        elif action == self.ACTION_ID_FIND_LISTITEM:
            ret_val = self._find_listitem(param)
        elif action == self.ACTION_ID_REMOVE_LISTITEM:
            ret_val = self._remove_listitem(param)
        elif action == self.ACTION_ID_FIND_DEVICE:
            ret_val = self._find_device(param)
        elif action == self.ACTION_ID_LIST_GROUPS:
            ret_val = self._list_groups(param)
        elif action == self.ACTION_ID_CHANGE_GROUP:
            ret_val = self._change_group(param)
        elif action == self.ACTION_ID_CHANGE_POLICY:
            ret_val = self._change_policy(param)
        elif action == self.ACTION_ID_LIST_POLICIES:
            ret_val = self._list_policies(param)
        elif action == self.ACTION_ID_QUARANTINE:
            ret_val = self._handle_quarantine_device(param)
        elif action == self.ACTION_ID_UNQUARANTINE:
            ret_val = self._handle_unquarantine_device(param)
        elif action == self.ACTION_ID_ALLOW_HASH:
            ret_val = self._handle_allow_hash(param)
        elif action == self.ACTION_ID_DISALLOW_HASH:
            ret_val = self._handle_disallow_hash(param)
        elif action == self.ACTION_ID_GET_DEVICE_TRAJECTORY:
            ret_val = self._get_device_trajectory(param)
        elif action == self.ACTION_ID_GET_DEVICE_EVENTS:
            ret_val = self._get_device_events(param)
        elif action == self.ACTION_ID_ADD_LISTITEM:
            ret_val = self._add_listitem(param)

        return ret_val


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
        connector = FireAMPConnector()
        connector.print_progress_message = True
        r_val = connector._handle_action(json.dumps(in_json), None)
        print(r_val)
    sys.exit(0)
