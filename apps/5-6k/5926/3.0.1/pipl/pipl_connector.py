# File: pipl_connector.py
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
# Phantom App imports
import json

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
from pipl_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class PiplConnector(BaseConnector):
    def __init__(self):
        super().__init__()

        self._state = None
        self._api_key = None

    def initialize(self):
        self._state = self.load_state()

        config = self.get_config()
        self._api_key = config["api_key"]

        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _process_empty_reponse(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    def _process_html_response(self, response, action_result):
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
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {e!s}"), None)

        if r.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, self._sanatize_data(resp_json))

        if "error" in resp_json:
            message = "Error from server: {}".format(resp_json["error"])
        else:
            message = "Error from server. Status Code: {} Message: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        if not r.text:
            return self._process_empty_reponse(r, action_result)

        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, action_result, params=None):
        if params:
            params["key"] = self._api_key
        else:
            params = {"key": self._api_key}

        try:
            r = requests.get(PIPL_BASE_URL, params=params, timeout=DEFAULT_TIMEOUT)
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {e!s}"))

        return self._process_response(r, action_result)

    def _sanatize_data(self, cur_obj):
        if isinstance(cur_obj, dict):
            new_dict = {}
            for k, v in cur_obj.items():
                if isinstance(k, str) and k.startswith("@"):
                    k = k[1:]
                new_dict[k] = self._sanatize_data(v)
            return new_dict

        if isinstance(cur_obj, list):
            new_list = []
            for v in cur_obj:
                new_list.append(self._sanatize_data(v))
            return new_list

        return cur_obj

    def _handle_test_connectivity(self, param):
        self.save_progress(f"Querying example person, {PIPL_EXAMPLE_EMAIL}, to check API key")
        action_result = self.add_action_result(ActionResult(dict(param)))

        params = {"email": PIPL_EXAMPLE_EMAIL}

        ret_val, response = self._make_rest_call(action_result, params=params)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return ret_val

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_user(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        first_name = param.get("first_name")
        last_name = param.get("last_name")
        house_no = param.get("house_number")
        street = param.get("street")
        city = param.get("city")
        zip_code = param.get("city")
        state = param.get("state")
        country = param.get("country")
        username = param.get("username")
        email = param.get("email")
        phone = param.get("phone")
        url = param.get("url")
        age = param.get("age")

        if not ((first_name and last_name) or (house_no and street and city and state) or email or phone or url or username):
            return action_result.set_status(
                phantom.APP_ERROR, "Not enough information provided to run a search. See documentation for requirements."
            )

        params = {}

        if first_name:
            params["first_name"] = first_name
        if last_name:
            params["last_name"] = last_name
        if email:
            params["email"] = email
        if phone:
            params["phone"] = phone
        if url:
            params["url"] = url
        if house_no:
            params["house"] = house_no
        if street:
            params["street"] = street
        if city:
            params["city"] = city
        if zip_code:
            params["zipcode"] = zip_code
        if state:
            params["state"] = state
        if country:
            params["country"] = country
        if age:
            params["age"] = age
        if username:
            if "@" in username:
                params["user_id"] = username
            else:
                params["username"] = username

        ret_val, resp_json = self._make_rest_call(action_result, params=params)

        if phantom.is_fail(ret_val):
            return ret_val

        summary = action_result.update_summary({})
        if "possible_persons" in resp_json:
            summary["exact_match_found"] = False
            summary["possible_matches"] = len(resp_json["possible_persons"])
            resp_json["people"] = resp_json.pop("possible_persons")
        elif "person" in resp_json:
            summary["exact_match_found"] = True
            resp_json["people"] = [resp_json.pop("person")]
        else:
            summary["exact_match_found"] = False
            summary["possible_matches"] = 0
            resp_json["people"] = []

        action_result.add_data(resp_json)

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "get_user":
            ret_val = self._handle_get_user(param)

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

        connector = PiplConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
