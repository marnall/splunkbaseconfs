# File: pagerduty_connector.py
#
# Copyright (c) 2016-2024 Splunk Inc.
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
import sys

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup, UnicodeDammit
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Imports local to this App
from pagerduty_consts import *


class RetVal4(tuple):
    def __new__(cls, val1, val2, val3, val4):
        return tuple.__new__(RetVal4, (val1, val2, val3, val4))


class RetVal2(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal2, (val1, val2))


# Define the App Class
class PagerDutyConnector(BaseConnector):

    ACTION_ID_LIST_USERS = "list_users"
    ACTION_ID_LIST_TEAMS = "list_teams"
    ACTION_ID_LIST_ONCALLS = "list_oncalls"
    ACTION_ID_LIST_SERVICES = "list_services"
    ACTION_ID_CREATE_INCIDENT = "create_incident"
    ACTION_ID_LIST_ESCALATIONS = "list_escalations"
    ACTION_ID_GET_ONCALL_USER = "get_oncall_user"
    ACTION_ID_GET_USER_INFO = "get_user_info"

    def __init__(self):

        # Call the BaseConnectors init first
        super(PagerDutyConnector, self).__init__()

        self._headers = None
        self._python_version = None

    def _handle_py_ver_compat_for_input_str(self, input_str):
        """
        This method returns the encoded|original string based on the Python version.
        :param input_str: Input string to be processed
        :return: input_str (Processed input string based on following logic 'input_str - Python 3; encoded input_str - Python 2')
        """
        try:
            if input_str and self._python_version < 3:
                input_str = UnicodeDammit(input_str).unicode_markup.encode("utf-8")
        except:
            self.debug_print("Error occurred while handling python 2to3 compatibility for the input string")

        return input_str

    def initialize(self):

        # Fetching the Python major version
        try:
            self._python_version = int(sys.version_info[0])
        except:
            return self.set_status(phantom.APP_ERROR, "Error occurred while getting the Phantom server's Python major version.")

        config = self.get_config()

        self._rest_url = self._handle_py_ver_compat_for_input_str(config[PAGERDUTY_JSON_BASEURL].rstrip("/"))
        api_key = config[PAGERDUTY_API_KEY]

        self._headers = {
            "Authorization": "Token token={0}".format(api_key),
            "Content-Type": "application/json",
            "Accept": "application/vnd.pagerduty+json;version=2",
        }

        return phantom.APP_SUCCESS

    def _normalize_text(self, text):
        if text:
            return text.replace("}", "}}").replace("{", "{{")
        else:
            return "Response data is None"

    def _parse_response(self, result, r):

        content_type = r.headers.get("content-type")
        resp_type = content_type

        status_code = r.status_code

        resp_data = None
        error = None

        # It's ok if r.text is None, dump that, if the result object supports recording it
        if hasattr(result, "add_debug_data"):
            result.add_debug_data({"r_text": r.text if r else "r is None"})

        if "json" in content_type:

            # Try a json parse
            try:
                resp_data = r.json()
            except:
                result.set_status(
                    phantom.APP_ERROR,
                    "Unable to parse response as a JSON status_code: {0}, data: {1}".format(r.status_code, self._normalize_text(r.text)),
                )

            if resp_data:
                error = resp_data.get("error")

            if error:

                if error.get("code", -1) == 2016:
                    return RetVal4(
                        result.set_status(phantom.APP_ERROR, "The email parameter is required to create incidents on this PagerDuty instance"),
                        None,
                        None,
                        None,
                    )

                error_message = "message: {0}, code: {1}, details: {2}".format(
                    error.get("message", "None"), error.get("code", "None"), "\n".join(error.get("errors", []))
                )

                return RetVal4(
                    result.set_status(phantom.APP_ERROR, "Error detected, status_code: {0}, data: {1}".format(r.status_code, error_message)),
                    None,
                    None,
                    None,
                )

        elif "html" in content_type:
            try:
                soup = BeautifulSoup(r.text, "html.parser")
                for element in soup(["script", "style", "footer", "nav"]):
                    element.extract()
                resp_data = soup.text
            except Exception as e:
                self.debug_print("Handled exception", e)
                result.set_status(
                    phantom.APP_ERROR,
                    "Unable to parse response as a HTML status_code: {0}, data: {1}".format(r.status_code, self._normalize_text(r.text)),
                )
        else:
            resp_data = r.text

        if not (200 <= r.status_code < 300):
            return RetVal4(
                result.set_status(
                    phantom.APP_ERROR,
                    "Call returned error, status_code: {0}, data: {1}".format(
                        r.status_code, self._handle_py_ver_compat_for_input_str(self._normalize_text(resp_data))
                    ),
                ),
                None,
                None,
                None,
            )

        return RetVal4(phantom.APP_SUCCESS, status_code, resp_type, resp_data)

    def _make_rest_call(self, endpoint, result, params=None, headers=None, data=None, method="get"):

        url = "{0}{1}".format(self._rest_url, endpoint)

        if headers:
            headers.update(self._headers)
        else:
            headers = self._headers

        request_func = getattr(requests, method)

        if not request_func:
            return RetVal2(result.set_status(phantom.APP_ERROR, "Invalid method call: {0} for requests module".format(method)), None)

        if data is not None:
            data = json.dumps(data)

        try:
            r = request_func(url, headers=headers, params=params, data=data)
        except Exception as e:
            return RetVal2(result.set_status(phantom.APP_ERROR, "REST Api to server failed", e), None)

        ret_val, status_code, resp_type, resp_data = self._parse_response(result, r)

        # Any http or parsing error is handled by the _parse_response function
        if phantom.is_fail(ret_val):
            return RetVal2(result.get_status(), resp_data)

        return RetVal2(phantom.APP_SUCCESS, resp_data)

    def _test_connectivity(self, param):

        self.save_progress("Querying a single incident, to verify API key")
        action_result = self.add_action_result(ActionResult(dict(param)))

        params = {"limit": 1}
        ret_val, resp_data = self._make_rest_call("/incidents", action_result, params)

        if phantom.is_fail(ret_val):
            self.save_progress(action_result.get_message())
            self.append_to_message("Test connectivity failed")
            return self.get_status()

        return self.set_status_save_progress(phantom.APP_SUCCESS, "Test connectivity passed")

    def _paginator(self, endpoint, action_result):

        dic_map = {
            self.ACTION_ID_LIST_USERS: "users",
            self.ACTION_ID_LIST_TEAMS: "teams",
            self.ACTION_ID_LIST_ONCALLS: "oncalls",
            self.ACTION_ID_LIST_SERVICES: "services",
            self.ACTION_ID_LIST_ESCALATIONS: "escalation_policies",
        }
        result_list = list()
        offset = 0

        set_name = dic_map.get(self.get_action_identifier())

        while True:
            endpoint = "{}{}{}".format(endpoint, "&offset=", offset)
            ret_val, resp_json = self._make_rest_call(endpoint, action_result)

            if phantom.is_fail(ret_val):
                return action_result.set_status(phantom.APP_ERROR, "Error while getting the {}".format(set_name))

            if resp_json.get(set_name):
                result_list.extend(resp_json[set_name])
            elif len(result_list) == 0:
                return action_result.set_status(phantom.APP_ERROR, "No data found")

            if not resp_json.get("more"):
                break
            else:
                offset = offset + PAGERDUTY_DEFAULT_LIMIT

        return result_list

    def _handle_list_oncalls(self, param):

        # Add an action result to the App Run
        self.debug_print("Running action - list oncalls")
        action_result = self.add_action_result(ActionResult(dict(param)))

        result_list = self._paginator("/oncalls?", action_result)

        if phantom.is_fail(result_list):
            self.debug_print("Action 'list oncalls' failed")
            return action_result.get_status()

        for oncall in result_list:
            action_result.add_data(oncall)

        action_result.update_summary({"num_oncalls": len(result_list)})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_teams(self, param):

        # Add an action result to the App Run
        self.debug_print("Running action - list teams")
        action_result = self.add_action_result(ActionResult(dict(param)))

        result_list = self._paginator("/teams?", action_result)

        if phantom.is_fail(result_list):
            self.debug_print("Action 'list teams' failed")
            return action_result.get_status()

        for team in result_list:
            action_result.add_data(team)

        action_result.update_summary({"total_teams": len(result_list)})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_services(self, param):

        # Add an action result to the App Run
        self.debug_print("Running action - list services")
        action_result = self.add_action_result(ActionResult(dict(param)))

        str_endpoint = ""
        if param.get("team_ids"):
            list_teams_id = [x.strip() for x in param.get("team_ids").split(",")]
            list_teams_id = " ".join(list_teams_id).split()
            if list_teams_id:
                for team_id in list_teams_id:
                    str_endpoint = "{}{}{}{}".format(str_endpoint, "team_ids[]=", team_id, "&")
                str_endpoint = str_endpoint[:-1]
            else:
                return action_result.set_status(phantom.APP_ERROR, "Please provide valid team_ids")

        endpoint = "/services?{}".format(str_endpoint)

        result_list = self._paginator(endpoint, action_result)

        if phantom.is_fail(result_list):
            self.debug_print("Action 'list services' failed")
            return action_result.get_status()

        for service in result_list:
            action_result.add_data(service)

        action_result.update_summary({"num_services": len(result_list)})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_users(self, param):

        # Add an action result to the App Run
        self.debug_print("Running action - list users")
        action_result = self.add_action_result(ActionResult(dict(param)))

        str_endpoint = ""
        if "team_ids" in param:
            list_teams_id = [x.strip() for x in param.get("team_ids").split(",")]
            list_teams_id = " ".join(list_teams_id).split()
            if list_teams_id:
                for team_id in list_teams_id:
                    str_endpoint = "{}{}{}{}".format(str_endpoint, "team_ids[]=", team_id, "&")
                str_endpoint = str_endpoint[:-1]
            else:
                return action_result.set_status(phantom.APP_ERROR, "Please provide valid team_ids")

        endpoint = "/users?{}".format(str_endpoint)

        result_list = self._paginator(endpoint, action_result)

        if phantom.is_fail(result_list):
            self.debug_print("Action 'list users' failed")
            return action_result.get_status()

        for user in result_list:
            action_result.add_data(user)

        action_result.update_summary({"num_users": len(result_list)})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_escalations(self, param):

        # Add an action result to the App Run
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.debug_print("Running action - list escalations")

        str_endpoint = ""
        if param.get("team_ids"):
            list_teams_id = [x.strip() for x in param.get("team_ids").split(",")]
            list_teams_id = " ".join(list_teams_id).split()
            if list_teams_id:
                for team_id in list_teams_id:
                    str_endpoint = "{}{}{}{}".format(str_endpoint, "team_ids[]=", team_id, "&")
                if param.get("user_ids") is None:
                    str_endpoint = str_endpoint[:-1]
            else:
                return action_result.set_status(phantom.APP_ERROR, "Please provide valid team_ids")

        if param.get("user_ids"):
            list_users_id = [x.strip() for x in param.get("user_ids").split(",")]
            list_users_id = " ".join(list_users_id).split()
            if list_users_id:
                for user_id in list_users_id:
                    str_endpoint = "{}{}{}{}".format(str_endpoint, "user_ids[]=", user_id, "&")
                str_endpoint = str_endpoint[:-1]
            else:
                return action_result.set_status(phantom.APP_ERROR, "Please provide valid user_ids")

        endpoint = "/escalation_policies?{}".format(str_endpoint)

        result_list = self._paginator(endpoint, action_result)

        if phantom.is_fail(result_list):
            self.debug_print("Action 'list escalations' failed")
            return action_result.get_status()

        if result_list is None:
            return action_result.set_status(phantom.APP_ERROR, "Error while connecting")

        for esc_pol in result_list:
            action_result.add_data(esc_pol)

        action_result.update_summary({"num_policies": len(result_list)})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_incident(self, param):

        # Add an action result to the App Run
        self.debug_print("Running action - create incident")
        action_result = self.add_action_result(ActionResult(dict(param)))

        body = {
            "incident": {
                "type": "incident",
                "title": param["title"],
                "service": {"id": param["service_id"], "type": "service"},
                "body": {"type": "incident_body", "details": param["description"]},
            }
        }

        if "escalation_id" in param:
            body["incident"]["escalation_policy"] = {"id": param["escalation_id"], "type": "escalation_policy"}
        if "assignee_id" in param:
            body["incident"]["assignments"] = [{"assignee": {"id": param["assignee_id"], "type": "user"}}]

        headers = {}
        if "email" in param:
            headers["From"] = param["email"]

        ret_val, resp_data = self._make_rest_call("/incidents", action_result, data=body, headers=headers, method="post")

        if phantom.is_fail(ret_val):
            self.debug_print("Action 'create incident' failed")
            return action_result.get_status()

        action_result.add_data(resp_data)

        action_result.update_summary({"incident_key": resp_data.get("incident", {}).get("incident_key", "Unknown")})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_oncall_user(self, param):

        # Add an action result to the App Run
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.debug_print("Running action - get oncall user")

        # Setup params
        params = {"escalation_policy_ids[]": param["escalation_id"]}

        # Find user IDs associated with escalation ID
        ret_val, resp_data_oncalls = self._make_rest_call("/oncalls", action_result, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        oncalls = resp_data_oncalls.get("oncalls")
        action_result.update_summary({"num_users": len(oncalls)})

        # Find additional info about each user
        for user in oncalls:
            try:
                user_id = user["user"]["id"]
            except KeyError as e:
                return action_result.set_status(phantom.APP_ERROR, "No user id in response", e)

            ret_val, resp_data_user = self._make_rest_call("/users/{0}".format(user_id), action_result, params={})

            if phantom.is_fail(ret_val):
                self.debug_print("Action 'get oncall users' failed")
                return action_result.get_status()

            user["user"] = resp_data_user.get("user")
            action_result.add_data(user)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_user_info(self, param):

        self.debug_print("Running action - get user info")
        # Add an action result to the App Run
        action_result = self.add_action_result(ActionResult(dict(param)))

        user_id = param.get("user_id")

        ret_val, resp_data = self._make_rest_call("/users/{0}".format(user_id), action_result, params={})

        if phantom.is_fail(ret_val):
            self.debug_print("Action 'get user info' failed")
            return action_result.get_status()

        try:
            action_result.add_data(resp_data["user"])
            action_result.update_summary({"name": resp_data["user"]["name"]})
        except KeyError as e:
            return action_result.set_status(phantom.APP_ERROR, "No user in response", e)

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):

        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == self.ACTION_ID_LIST_TEAMS:
            ret_val = self._handle_list_teams(param)
        elif action_id == self.ACTION_ID_LIST_USERS:
            ret_val = self._handle_list_users(param)
        elif action_id == self.ACTION_ID_LIST_ONCALLS:
            ret_val = self._handle_list_oncalls(param)
        elif action_id == self.ACTION_ID_LIST_SERVICES:
            ret_val = self._handle_list_services(param)
        elif action_id == self.ACTION_ID_CREATE_INCIDENT:
            ret_val = self._handle_create_incident(param)
        elif action_id == self.ACTION_ID_LIST_ESCALATIONS:
            ret_val = self._handle_list_escalations(param)
        elif action_id == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity(param)
        elif action_id == self.ACTION_ID_GET_ONCALL_USER:
            ret_val = self._handle_get_oncall_user(param)
        elif action_id == self.ACTION_ID_GET_USER_INFO:
            ret_val = self._handle_get_user_info(param)

        return ret_val


if __name__ == "__main__":

    import pudb

    pudb.set_trace()

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = PagerDutyConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
