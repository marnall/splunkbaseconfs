# File: smg_connector.py
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


DEFAULT_REQUEST_TIMEOUT = 30  # in seconds


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class SymantecMessagingGatewayConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None
        self._token = None
        self._session = None
        self._base_url = None

    def initialize(self):
        config = self.get_config()

        self._state = self.load_state()
        self._session = requests.Session()
        self._base_url = "{}/{}".format(config["url"].strip("/"), "brightmail")

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved accross actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            # Remove the script, style, footer and navigation part from the HTML message
            for element in soup(["script", "style", "footer", "nav"]):
                element.extract()
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, method="get"):
        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(self._session, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        url = self._base_url + endpoint

        try:
            r = request_func(url, data=data, headers=headers, verify=config.get("verify_server_cert", False), params=params)
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {e!s}"), resp_json)

        if not r:
            return self._process_html_response(r, action_result)

        return RetVal(phantom.APP_SUCCESS, r)

    def _login(self, action_result):
        self.debug_print("Attempting login")

        ret_val, resp = self._make_rest_call("/viewLogin.do", action_result)

        if phantom.is_fail(ret_val):
            return ret_val

        soup = BeautifulSoup(resp.text, "html.parser")
        found_tag = soup.find("input", {"name": "lastlogin"})
        if not found_tag:
            return action_result.set_status(phantom.APP_ERROR, "Could not find last login time in viewLogin response")
        lastlogin = found_tag["value"]

        config = self.get_config()

        params = {"lastlogin": lastlogin, "username": config["username"], "password": config["password"]}

        ret_val, resp = self._make_rest_call("/login.do", action_result, params=params)

        if phantom.is_fail(ret_val):
            return ret_val

        soup = BeautifulSoup(resp.text, "html.parser")
        found_tag = soup.find("input", {"name": "symantec.brightmail.key.TOKEN"})
        if not found_tag:
            return action_result.set_status(phantom.APP_ERROR, "Could not find token in login response")
        self._token = found_tag["value"]

        return phantom.APP_SUCCESS

    def _handle_test_connectivity(self, param):
        SYMANTECCAS_CONNECTION_TEST_MSG = "Querying endpoint to test the connectivity"

        self.save_progress(SYMANTECCAS_CONNECTION_TEST_MSG)

        action_result = self.add_action_result(ActionResult(dict(param)))

        if phantom.is_fail(self._login(action_result)):
            self.save_progress("Login Failed")
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _blocklist_item(self, action_result, item, item_type):
        if phantom.is_fail(self._login(action_result)):
            self.debug_print("Login Failed")
            return action_result.get_status()

        ret_val, resp = self._make_rest_call("/reputation/sender-group/viewSenderGroup.do?view=badSenders", action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        if item_type == "IP":
            sender_group = "1|1"
        else:
            sender_group = "1|3"

        params = {"symantec.brightmail.key.TOKEN": self._token, "view": "badSenders", "selectedSenderGroups": sender_group}
        ret_val, resp = self._make_rest_call("/reputation/sender-group/viewSenderGroup.do", action_result, params=params)
        if phantom.is_fail(ret_val):
            return ret_val

        ret_val, resp = self._make_rest_call("/reputation/sender-group/addSender.do", action_result, params=params)
        if phantom.is_fail(ret_val):
            return ret_val

        params = {"symantec.brightmail.key.TOKEN": self._token, "addEditSenders": item, "view": "badSenders"}
        ret_val, resp = self._make_rest_call("/reputation/sender-group/saveSender.do", action_result, params=params)
        if phantom.is_fail(ret_val):
            return ret_val

        params = {"symantec.brightmail.key.TOKEN": self._token, "view": "badSenders"}
        ret_val, resp = self._make_rest_call("/reputation/sender-group/saveGroup.do", action_result, params=params)
        if phantom.is_fail(ret_val):
            return ret_val

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully blocklisted {item_type}")

    def _unblocklist_item(self, action_result, item, item_type):
        if phantom.is_fail(self._login(action_result)):
            self.debug_print("Login Failed")
            return action_result.get_status()

        ret_val, resp = self._make_rest_call("/reputation/sender-group/viewSenderGroup.do?view=badSenders", action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        if item_type == "IP":
            sender_group = "1|1"
        else:
            sender_group = "1|3"

        params = {"symantec.brightmail.key.TOKEN": self._token, "view": "badSenders", "selectedSenderGroups": sender_group}
        ret_val, resp = self._make_rest_call("/reputation/sender-group/viewSenderGroup.do", action_result, params=params)
        if phantom.is_fail(ret_val):
            return ret_val

        params = {
            "symantec.brightmail.key.TOKEN": self._token,
            "view": "badSenders",
            "selectedSenderGroups": sender_group,
            "entriesPerPage": 500,
        }
        ret_val, resp = self._make_rest_call("/reputation/sender-group/changePageSize.do", action_result, params=params)
        if phantom.is_fail(ret_val):
            return ret_val

        found = False
        cur_page = 1

        while True:
            soup = BeautifulSoup(resp.text, "html.parser")
            member_table = soup.find("table", {"id": "membersList"})
            if not member_table:
                return action_result.set_status(phantom.APP_ERROR, "Could not find member list table")

            item_id = None
            member_tags = soup.findAll("tr")
            if not member_tags:
                return action_result.set_status(phantom.APP_ERROR, "Could not find any items in bad senders list")
            for tag in member_tags:
                if item in tag.text:
                    checkbox = tag.find("input", {"name": "selectedGroupMembers"})
                    if not checkbox:
                        return action_result.set_status(phantom.APP_ERROR, "Could not find item ID")
                    item_id = checkbox["value"]
                    found = True
                    break

            if found:
                break

            next_button = soup.find("button", {"id": "nextButton"})
            if "disabled" in next_button.attrs:
                break

            params = {
                "symantec.brightmail.key.TOKEN": self._token,
                "view": "badSenders",
                "selectedSenderGroups": sender_group,
                "entriesPerPage": 500,
                "pageNumber": cur_page,
            }
            ret_val, resp = self._make_rest_call("/reputation/sender-group/viewNextPage.do", action_result, params=params)
            if phantom.is_fail(ret_val):
                return ret_val
            cur_page += 1

        if not found:
            return action_result.set_status(phantom.APP_SUCCESS, "Given value not found in blocklist. Item cannot be unblocklisted.")

        params = {
            "symantec.brightmail.key.TOKEN": self._token,
            "selectedGroupMembers": item_id,
            "view": "badSenders",
            "selectedSenderGroups": sender_group,
        }
        ret_val, resp = self._make_rest_call("/reputation/sender-group/deleteSender.do", action_result, params=params)
        if phantom.is_fail(ret_val):
            return ret_val

        params = {"symantec.brightmail.key.TOKEN": self._token, "view": "badSenders"}
        ret_val, resp = self._make_rest_call("/reputation/sender-group/saveGroup.do", action_result, params=params)
        if phantom.is_fail(ret_val):
            return ret_val

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully unblocklisted {item_type}")

    def _handle_blocklist_email(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        return self._blocklist_item(action_result, param["email"], "email")

    def _handle_unblocklist_email(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        return self._unblocklist_item(action_result, param["email"], "email")

    def _handle_blocklist_domain(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        return self._blocklist_item(action_result, param["domain"], "domain")

    def _handle_unblocklist_domain(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        return self._unblocklist_item(action_result, param["domain"], "domain")

    def _handle_blocklist_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        return self._blocklist_item(action_result, param["ip"], "IP")

    def _handle_unblocklist_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        return self._unblocklist_item(action_result, param["ip"], "IP")

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)
        elif action_id == "blocklist_email":
            ret_val = self._handle_blocklist_email(param)
        elif action_id == "unblocklist_email":
            ret_val = self._handle_unblocklist_email(param)
        elif action_id == "blocklist_domain":
            ret_val = self._handle_blocklist_domain(param)
        elif action_id == "unblocklist_domain":
            ret_val = self._handle_unblocklist_domain(param)
        elif action_id == "blocklist_ip":
            ret_val = self._handle_blocklist_ip(param)
        elif action_id == "unblocklist_ip":
            ret_val = self._handle_unblocklist_ip(param)

        return ret_val


if __name__ == "__main__":
    # import pudb
    import argparse
    import sys

    # pudb.set_trace()

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
            login_url = BaseConnector._get_phantom_base_url() + "/login"
            r = requests.get(login_url, verify=verify, timeout=DEFAULT_REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, timeout=DEFAULT_REQUEST_TIMEOUT, data=data, headers=headers)
        except Exception as e:
            print("Unable to get session id from the platfrom. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = SymantecMessagingGatewayConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
