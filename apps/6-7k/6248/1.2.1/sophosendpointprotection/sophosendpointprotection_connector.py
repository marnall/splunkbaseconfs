# File: sophosendpointprotection_connector.py
#
# Copyright (c) 2021-2025 Splunk Inc.
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
import re

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from sophosendpointprotection_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class SophosEndpointProtectionConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()
        self._state = {}
        self._base_url = None
        self._client_id = None
        self._client_secret = None
        self._JWT_token = None
        self._partner_token = None
        self._id_type = None
        return

    def initialize(self):
        config = self.get_config()
        self._client_id = config[SOPHOS_CLIENT_ID].encode("utf-8")
        self._client_secret = config[SOPHOS_CLIENT_SECRET].encode("utf-8")
        self._state = self.load_state()
        self._JWT_token = self._state.get(SOPHOS_JWT_JSON, {}).get(SOPHOS_JWT_TOKEN)
        pt_json = self._state.get(SOPHOS_PT_JSON, None)
        # self.save_progress("Printing the pt_json: ".format(str(json.dumps(pt_json))))
        if pt_json is not None:
            self._id_type = pt_json["idType"]
            if pt_json["idType"] == "tenant":
                self._base_url = pt_json.get(SOPHOS_PT_API_HOSTS, {}).get(SOPHOS_PT_DATA_REGION_URL, None)
            elif pt_json["idType"] == "organization" or pt_json["idType"] == "partner":
                self._base_url = pt_json.get(SOPHOS_PT_API_HOSTS, {}).get(SOPHOS_PT_GLOBAL_URL, None)
        else:
            self._base_url = None
        self._partner_token = self._state.get(SOPHOS_PT_JSON, {}).get(SOPHOS_PT_TOKEN)
        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _validate_input(self, commaseparated_str, valid_values):
        """Validating input values provided as comma separated strings"""
        for item in commaseparated_str.split(","):
            if item not in valid_values:
                return False
        return True

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {e!s}"), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, json=None, method="get"):
        resp_json = None
        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)
        try:
            r = request_func(endpoint, json=json, data=data, headers=headers, params=params)
            # self.save_progress("Request function results: {}".format(r.text))
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, (f"Error connecting to server. Details: {e!s}")), resp_json)
        # self.save_progress("Returning the results found for the request")
        return self._process_response(r, action_result)

    def _make_rest_call_helper(self, action_result, endpoint, headers=None, params=None, data=None, json=None, method="get"):
        jwt_json = self._state.get(SOPHOS_JWT_JSON, {})
        self.save_progress(f"idType: {self._id_type}")
        if not jwt_json.get(SOPHOS_JWT_TOKEN) or not self._base_url or not self._id_type:
            self.save_progress("Didn't find the JWT token, trying to fetch one.")
            ret_val = self._get_token(action_result)
            if phantom.is_fail(ret_val):
                return (action_result.get_status(), None)
        url = f"{self._base_url}{endpoint}"
        self.save_progress(f"Hitting the URL: {url}")
        # self.save_progress("Calling REST HELPER")
        if headers is None:
            headers = {}
        id_to_xid = {"tenant": "X-Tenant-ID", "organization": "X-Organization-ID", "partner": "X-Partner-ID"}
        headers.update(
            {
                "Authorization": (f"Bearer {self._JWT_token}"),
                f"{id_to_xid[self._id_type]}": f"{self._partner_token}",
                "Content-Type": "application/json",
            }
        )
        self.save_progress("Trying to fetch data from the endpoint")
        ret_val, resp_json = self._make_rest_call(url, action_result, headers, params, data, json, method)
        self.save_progress(f"Response in JSON: {resp_json!s}")
        msg = action_result.get_message()

        if (
            (msg and "token is invalid" in msg)
            or "token has expired" in msg
            or "ExpiredAuthenticationToken" in msg
            or "authorization failed" in msg
            or "access denied " in msg
        ):
            ret_val = self._get_token(action_result)
            headers.update(
                {
                    "Authorization": (f"Bearer {self._JWT_token}"),
                    f"{id_to_xid[self._id_type]}": f"{self._partner_token}",
                    "Content-Type": "application/json",
                }
            )
            ret_val, resp_json = self._make_rest_call(url, action_result, headers, params, data, json, method)

        if ret_val is False:
            ret_val = self._get_token(action_result)
            headers.update(
                {
                    "Authorization": (f"Bearer {self._JWT_token}"),
                    f"{id_to_xid[self._id_type]}": f"{self._partner_token}",
                    "Content-Type": "application/json",
                }
            )
            ret_val, resp_json = self._make_rest_call(url, action_result, headers, params, data, json, method)

        self.save_progress(f"Response in JSON: {resp_json!s}")

        if phantom.is_fail(ret_val):
            return (action_result.get_status(), None)
        else:
            return (phantom.APP_SUCCESS, resp_json)

    def _get_token(self, action_result, from_action=False):
        data = {"client_id": self._client_id, "client_secret": self._client_secret, "scope": "token", "grant_type": "client_credentials"}
        # self.save_progress("Data: {}".format(json.dumps(data)))
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
        url = f"{JWT_TOKEN_ENDPOINT}"
        self.save_progress("Fetching the JWT token")
        self.save_progress(f"Hitting the URL for JWT token: {url}")
        ret_val, resp_json = self._make_rest_call(url, action_result, headers=headers, data=data, method="post")
        self.save_progress(f"Response in JSON: {resp_json}")
        self.save_progress(f"Return value: {ret_val}")
        if not ret_val:
            return self.set_status(phantom.APP_ERROR, "Token not found")

        self.save_progress("Saving to state")
        self._state[SOPHOS_JWT_JSON] = resp_json
        self._JWT_token = resp_json[SOPHOS_JWT_TOKEN]
        self.save_progress(f"Got the token: {self._JWT_token}")

        # Getting the X-Tenant-ID
        data = {}
        headers = {"Authorization": f"Bearer {self._JWT_token}", "Accept": "application/json"}
        url = f"{WHOAMI_ENDPOINT}"
        self.save_progress("Fetching the partner token")
        ret_val, resp_json = self._make_rest_call(url, action_result, headers=headers, data=data, method="get")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self._state[SOPHOS_PT_JSON] = resp_json
        self._partner_token = resp_json[SOPHOS_PT_TOKEN]
        self._id_type = resp_json["idType"]
        # idType = partner | organization | tenant
        if resp_json["idType"] == "tenant":
            self._base_url = resp_json[SOPHOS_PT_API_HOSTS][SOPHOS_PT_DATA_REGION_URL]
        else:
            self._base_url = resp_json[SOPHOS_PT_API_HOSTS][SOPHOS_PT_GLOBAL_URL]
        self.save_state(self._state)
        self.save_progress("Got the partner token")
        return phantom.APP_SUCCESS

    """
    Get Partner Token.
    """
    # def _get_partner_token(self,jwt_token):
    #     self.save_progress("Getting the partner token")
    #     headers = {'Authorization': 'Bearer '.format(jwt_token)}
    #     payload = {}
    #     response = requests.request("POST", WHOAMI_ENDPOINT, headers=headers, data = payload)
    #     return json.loads(response.text)['id']

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Connecting to the endpoint for test connectivity")
        params = {}
        data = {}
        endpoint = ENDPOINTS_ENDPOINT
        ret_val, response = self._make_rest_call_helper(action_result, endpoint, params=params, data=json.dumps(data), method="get")
        if phantom.is_fail(ret_val):
            return self.set_status_save_progress(phantom.APP_ERROR, "Test Connectivity Failed")
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    """
    Handling Test Connectivity.
    Make a GET call to '/endpoints' endpoint.
    """

    def _handle_endpoints(self, action_result, param):
        data = {}
        endpoint = ENDPOINTS_ENDPOINT
        action_name = param.pop("action_name")

        # Casting keys format (e.g. page_from_key --> pageFromKey)
        r_pattern = r"([_])\s*([a-z])"
        params = {re.sub(r_pattern, lambda m: m.group(0).upper(), k).replace("_", ""): v for k, v in param.items() if k != "context"}

        if action_name == "list endpoints":
            params["pageTotal"] = True

            while True:
                ret_val, response = self._make_rest_call_helper(action_result, endpoint, params=params, data=json.dumps(data), method="get")
                if phantom.is_fail(ret_val):
                    return action_result.get_status()

                for item in response["items"]:
                    action_result.add_data(item)

                next_key = response["pages"].get("nextKey", None)
                self.save_progress(f"Next key: {next_key}")
                if next_key is None or next_key == "":
                    break
                params["pageFromKey"] = next_key

            action_result.set_status(phantom.APP_SUCCESS, SOPHOS_OKAY_MESSAGE)
            summary = action_result.update_summary({})
            summary["total_number_of_items"] = len(response["items"])
            return phantom.APP_SUCCESS

        elif action_name == "get individual endpoint":
            final_endpoint = "{}/{}".format(endpoint, params.pop("endpointid"))
            ret_val, response = self._make_rest_call_helper(action_result, final_endpoint, params=params, data=json.dumps(data), method="get")

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            action_result.add_data(response)
            action_result.set_status(phantom.APP_SUCCESS, SOPHOS_OKAY_MESSAGE)
            summary = action_result.update_summary({})
            summary["total_number_of_items"] = 1
            return phantom.APP_SUCCESS

        elif action_name == "delete endpoint":
            final_endpoint = "{}/{}".format(endpoint, params.pop("endpointid"))
            ret_val, response = self._make_rest_call_helper(action_result, final_endpoint, params=params, data=json.dumps(data), method="delete")
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            action_result.set_status(phantom.APP_SUCCESS, SOPHOS_OKAY_MESSAGE)
            action_result.add_data({"endpoint_deleted": response["deleted"]})
            summary = action_result.update_summary({})
            summary["total_endpoints_deleted"] = 1
            return phantom.APP_SUCCESS

    def _list_endpoints(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        view = param.get("view", None)
        endpoint_type = param.get("type", None)
        health_status = param.get("health_status", None)
        lockdown_status = param.get("lockdown_status", None)
        search_fields = param.get("search_fields", None)

        # Validate parameters
        if view and view not in SOPHOS_PARAMS_VIEW:
            return action_result.set_status(phantom.APP_ERROR, SOPHOS_PARAMS_INVALID_ERR.format(name="view"))
        if endpoint_type and not self._validate_input(endpoint_type, SOPHOS_PARAMS_ENDPOINTTYPE):
            return action_result.set_status(phantom.APP_ERROR, SOPHOS_PARAMS_INVALID_ERR.format(name="type"))
        if health_status and not self._validate_input(health_status, SOPHOS_PARAMS_ENDPOINTHEALTH):
            return action_result.set_status(phantom.APP_ERROR, SOPHOS_PARAMS_INVALID_ERR.format(name="health_status"))
        if lockdown_status and not self._validate_input(lockdown_status, SOPHOS_PARAMS_ENDPOINTLOCKDOWN):
            return action_result.set_status(phantom.APP_ERROR, SOPHOS_PARAMS_INVALID_ERR.format(name="lockdown_status"))
        if search_fields and not self._validate_input(search_fields, SOPHOS_PARAM_SEARCHFIELDS):
            return action_result.set_status(phantom.APP_ERROR, SOPHOS_PARAMS_INVALID_ERR.format(name="search_fields"))

        param["action_name"] = "list endpoints"
        ret_val = self._handle_endpoints(action_result, param)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _delete_endpoint(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        param["action_name"] = "delete endpoint"
        ret_val = self._handle_endpoints(action_result, param)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_individual_endpoint(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        view = param.get("view", None)
        fields = param.get("fields", None)

        # Validate and format parameters
        if view and view not in SOPHOS_PARAMS_VIEW:
            return action_result.set_status(phantom.APP_ERROR, SOPHOS_PARAMS_INVALID_ERR.format(name="view"))
        if fields:
            param["fields"] = fields.split(",")

        param["action_name"] = "get individual endpoint"
        ret_val = self._handle_endpoints(action_result, param)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_check_updates(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        data = {}
        endpoint = UPDATE_CHECK_ENDPOINT.format(param["endpointid"])
        ret_val, response = self._make_rest_call_helper(action_result, endpoint, params={}, data=json.dumps(data), method="post")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.set_status(phantom.APP_SUCCESS, SOPHOS_OKAY_MESSAGE)
        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["number_of_endpoints_checked"] = 1
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_tamperprotection_settings(self, action_result, param):
        data = {}
        action_name = param.get("action_name")
        endpoint = TAMPER_PROTECTION_ENDPOINT.format(param["endpointid"])

        if action_name == "get settings":
            self.save_progress("Getting tamper protection settings")
            ret_val, response = self._make_rest_call_helper(action_result, endpoint, params={}, data=json.dumps(data), method="get")
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            action_result.set_status(phantom.APP_SUCCESS, SOPHOS_OKAY_MESSAGE)
            action_result.add_data(response)
            summary = action_result.update_summary({})
            summary["number_of_endpoints_tamperprotection_settings_received"] = "1"
            summary["number_of_times_passwords_changed"] = str(len(response.get("previousPasswords")))
            return phantom.APP_SUCCESS

        elif action_name == "update settings":
            self.save_progress("Updating tamper protection settings")
            data["enabled"] = param["enabled"]
            data["regeneratePassword"] = param.get("regenerate_password", False)
            ret_val, response = self._make_rest_call_helper(action_result, endpoint, params={}, data=json.dumps(data), method="post")
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            action_result.set_status(phantom.APP_SUCCESS, SOPHOS_OKAY_MESSAGE)
            action_result.add_data(response)
            summary = action_result.update_summary({})
            summary["number_of_endpoints_tamperprotection_settings_updated"] = 1
            return phantom.APP_SUCCESS

    def _handle_tamper_protection_switch(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        param["action_name"] = "update settings"
        ret_val = self._handle_tamperprotection_settings(action_result, param)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_tamper_protection_settings(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        param["action_name"] = "get settings"
        ret_val = self._handle_tamperprotection_settings(action_result, param)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _perform_scan(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        data = {}
        endpoint = SCAN_ENDPOINT.format(param["endpointid"])
        ret_val, response = self._make_rest_call_helper(action_result, endpoint, params={}, data=json.dumps(data), method="post")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.set_status(phantom.APP_SUCCESS, SOPHOS_OKAY_MESSAGE)
        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["number_of_scans_performed"] = 1
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_settings(self, action_result, param):
        endpoint = param.pop("action_endpoint")

        # Casting parameters keys format (e.g. page_size --> pageSize)
        r_pattern = r"([_])\s*([a-z])"
        params = {re.sub(r_pattern, lambda m: m.group(0).upper(), k).replace("_", ""): v for k, v in param.items() if k != "context"}
        # Forcing pageTotal = true for pagination
        params["pageTotal"] = True

        curr_items = 0

        while True:
            ret_val, response = self._make_rest_call_helper(action_result, endpoint, params=params, method="get")
            if phantom.is_fail(ret_val):
                return action_result.get_status()

            for item in response["items"]:
                action_result.add_data(item)

            total_items = response["pages"].get("items", 1)
            curr_items += response["pages"].get("size", 1)
            if total_items <= curr_items:
                break

            next_page = response["pages"].get("current", 1) + 1
            params["page"] = next_page
            self.save_progress(f"Next page: {next_page}")

        action_result.set_status(phantom.APP_SUCCESS, SOPHOS_OKAY_MESSAGE)
        summary = action_result.update_summary({})
        summary["total_number_of_items"] = total_items
        return phantom.APP_SUCCESS

    def _handle_delete_settings(self, action_result, param):
        endpoint = param.pop("action_endpoint")
        params = {}

        ret_val, response = self._make_rest_call_helper(action_result, endpoint, params=params, method="delete")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.set_status(phantom.APP_SUCCESS, SOPHOS_OKAY_MESSAGE)
        action_result.add_data(response)
        return phantom.APP_SUCCESS

    def _handle_list_items(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Validate items_type
        items_type = param.pop("items_type")
        if items_type not in SOPHOS_PARAMS_ITEMSTYPE:
            return action_result.set_status(phantom.APP_ERROR, SOPHOS_PARAMS_INVALID_ERR.format(name="items_type"))

        param["action_endpoint"] = LIST_ITEMS.format(items_type)
        ret_val = self._handle_list_settings(action_result, param)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_item(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Validate items_type
        item_type = param.pop("item_type")
        if item_type not in SOPHOS_PARAMS_ITEMSTYPE:
            return action_result.set_status(phantom.APP_ERROR, SOPHOS_PARAMS_INVALID_ERR.format(name="item_type"))

        param["action_endpoint"] = DELETE_ITEM.format(type=item_type, id=param["item_id"])

        ret_val = self._handle_delete_settings(action_result, param)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_block_item(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        r_pattern = r"([_])\s*([a-z])"
        properties = {re.sub(r_pattern, lambda m: m.group(0).upper(), k).replace("_", ""): v for k, v in param.items() if k != "context"}

        params = {}
        data = {"type": "sha256", "comment": properties.pop("comment"), "properties": properties}

        endpoint = LIST_ITEMS.format("blocked")

        ret_val, response = self._make_rest_call_helper(action_result, endpoint, params=params, data=json.dumps(data), method="post")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress(SOPHOS_OKAY_MESSAGE)
        action_result.add_data(response)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_allow_item(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        r_pattern = r"([_])\s*([a-z])"
        properties = {re.sub(r_pattern, lambda m: m.group(0).upper(), k).replace("_", ""): v for k, v in param.items() if k != "context"}

        # Validate 'property_type'
        property_type = properties.pop("propertyType")
        if property_type not in SOPHOS_PARAMS_PROPTYPE:
            return action_result.set_status(phantom.APP_ERROR, SOPHOS_PARAMS_INVALID_ERR.format(name="property_type"))

        params = {}
        data = {"type": property_type, "comment": properties.pop("comment"), "properties": properties}

        endpoint = LIST_ITEMS.format("allowed")

        ret_val, response = self._make_rest_call_helper(action_result, endpoint, params=params, data=json.dumps(data), method="post")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress(SOPHOS_OKAY_MESSAGE)
        action_result.add_data(response)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_sites(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        param["action_endpoint"] = LIST_SITES
        ret_val = self._handle_list_settings(action_result, param)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_site(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        param["action_endpoint"] = DELETE_SITE.format(id=param["site_id"])
        ret_val = self._handle_delete_settings(action_result, param)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_add_site(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        category_id = param.get("category_id", 1)
        data = {"categoryId": category_id, "tags": param.get("tags", "").split(","), "url": param["url"], "comment": param.get("comment", "")}

        # Validate input
        if category_id < 1 and len(data["tags"]) < 1:
            action_result.set_status(phantom.APP_ERROR, SOPHOS_PARAMS_NOTFOUND_ERR.format(name="category_id or tags"))

        ret_val, response = self._make_rest_call_helper(action_result, LIST_SITES, params={}, data=json.dumps(data), method="post")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress(SOPHOS_OKAY_MESSAGE)
        action_result.add_data(response)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_isolation_settings(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = ISOLATION_INDIVIDUAL_ENDPOINT.format(param["endpoint_id"])
        ret_val, response = self._make_rest_call_helper(action_result, endpoint, params={}, method="get")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress(SOPHOS_OKAY_MESSAGE)
        action_result.add_data(response)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_isolation_switch(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        ids = param["ids"].split(",")
        data = {"enabled": param["enabled"], "ids": ids, "comment": param.get("comment", "")}

        ret_val, response = self._make_rest_call_helper(action_result, ISOLATION_ENDPOINT, params={}, data=json.dumps(data), method="post")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for item in response["items"]:
            action_result.add_data(item)
        action_result.set_status(phantom.APP_SUCCESS, SOPHOS_OKAY_MESSAGE)
        summary = action_result.update_summary({})
        summary["number_of_endpoints_isolation_settings_updated"] = len(response["items"])
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "list_endpoints":
            ret_val = self._list_endpoints(param)

        elif action_id == "get_individual_endpoint":
            ret_val = self._get_individual_endpoint(param)

        elif action_id == "delete_endpoint":
            ret_val = self._delete_endpoint(param)

        elif action_id == "check_updates":
            ret_val = self._handle_check_updates(param)

        elif action_id == "tamper_protection_switch":
            ret_val = self._handle_tamper_protection_switch(param)

        elif action_id == "get_tamper_protection_settings":
            ret_val = self._handle_get_tamper_protection_settings(param)

        elif action_id == "perform_scan":
            ret_val = self._perform_scan(param)

        elif action_id == "list_items":
            ret_val = self._handle_list_items(param)

        elif action_id == "delete_item":
            ret_val = self._handle_delete_item(param)

        elif action_id == "block_item":
            ret_val = self._handle_block_item(param)

        elif action_id == "allow_item":
            ret_val = self._handle_allow_item(param)

        elif action_id == "list_sites":
            ret_val = self._handle_list_sites(param)

        elif action_id == "delete_site":
            ret_val = self._handle_delete_site(param)

        elif action_id == "add_site":
            ret_val = self._handle_add_site(param)

        elif action_id == "get_isolation_settings":
            ret_val = self._handle_get_isolation_settings(param)

        elif action_id == "isolation_switch":
            ret_val = self._handle_isolation_switch(param)

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
            login_url = SophosEndpointProtectionConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, timeout=60)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, data=data, headers=headers, timeout=60)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = SophosEndpointProtectionConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
