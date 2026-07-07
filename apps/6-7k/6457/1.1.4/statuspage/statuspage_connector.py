# File: statuspage_connector.py
#
# Copyright (c) 2022-2025 Splunk Inc.
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
import json

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from statuspage_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class StatuspageConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None

        self._api_key = None

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.

        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_message = ERROR_MESSAGE_UNAVAILABLE

        self.error_print("Error occurred.", e)

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except Exception:
            self.debug_print("Error occurred while getting message from html response")

        if not error_code:
            error_text = f"Error Message: {error_message}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_message}"

        return error_text

    def _process_empty_reponse(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(
                phantom.APP_ERROR, f"Status Code: {response.status_code}. Empty response and no information in the header."
            ),
            None,
        )

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove the script, style, footer and navigation part from the HTML message
            for element in soup(["script", "style", "footer", "nav"]):
                element.extract()
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except Exception:
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

        try:
            if resp_json.get("type") and resp_json.get("message"):
                message = "Error from server. Status Code: {} Data from server: Error Type: {}. Error Message: {}".format(
                    r.status_code, resp_json.get("type"), resp_json.get("message")
                )
            if resp_json.get("errors", [])[0][0].get("message"):
                message = "Error from server. Status Code: {} Data from server: {}".format(
                    r.status_code, resp_json.get("errors", [])[0][0].get("message")
                )
        except Exception:
            self.debug_print("Error occurred while getting message from json response")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        # Process an HTML resonse, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between SOAR and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_reponse(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, json=None, method="get"):
        resp_json = None
        config = self.get_config()
        headers = {"Authorization": f"API Key {self._api_key}"}

        if json:
            headers.update({"Content-Type": "application/json"})

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = f"{self._base_url}{endpoint}"

        try:
            r = request_func(url, data=data, json=json, headers=headers, verify=True, params=params, timeout=config.get("timeout"))
        except requests.exceptions.InvalidURL as e:
            self.debug_print(self._get_error_message_from_exception(e))
            return RetVal(action_result.set_status(phantom.APP_ERROR, STATUSPAGE_ERROR_INVALID_URL.format(url=url)), resp_json)
        except requests.exceptions.ConnectionError as e:
            self.debug_print(self._get_error_message_from_exception(e))
            return RetVal(action_result.set_status(phantom.APP_ERROR, STATUSPAGE_ERROR_CONNECTION_REFUSED.format(url=url)), resp_json)
        except requests.exceptions.InvalidSchema as e:
            self.debug_print(self._get_error_message_from_exception(e))
            return RetVal(action_result.set_status(phantom.APP_ERROR, STATUSPAGE_ERROR_INVALID_SCHEMA.format(url=url)), resp_json)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.debug_print(self._get_error_message_from_exception(error_message))
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    STATUSPAGE_ERROR_CONNECTING_TO_SERVER.format(error=error_message),
                ),
                resp_json,
            )

        return self._process_response(r, action_result)

    def _validate_integers(self, action_result, parameter, key, allow_zero=False):
        """Validate the provided input parameter value is a non-zero positive integer and returns the integer value of the parameter itself.

        Parameters:
            :param action_result: object of ActionResult class
            :param parameter: input parameter
            :param key: string value of parameter name
            :param allow_zero: indicator for given parameter that whether zero value is allowed or not
        Returns:
            :return: integer value of the parameter
        """
        try:
            parameter = int(parameter)

            if parameter <= 0:
                if allow_zero:
                    if parameter < 0:
                        action_result.set_status(phantom.APP_ERROR, STATUSPAGE_LIMIT_VALIDATION_ALLOW_ZERO_MESSAGE.format(parameter=key))
                        return None
                else:
                    action_result.set_status(phantom.APP_ERROR, STATUSPAGE_LIMIT_VALIDATION_MESSAGE.format(parameter=key))
                    return None
        except Exception as e:
            self.debug_print(f"Integer validation failed. Error occurred while validating integer value. Error: {e!s}")
            if allow_zero:
                error_text = STATUSPAGE_LIMIT_VALIDATION_ALLOW_ZERO_MESSAGE.format(parameter=key)
            else:
                error_text = STATUSPAGE_LIMIT_VALIDATION_MESSAGE.format(parameter=key)
            action_result.set_status(phantom.APP_ERROR, error_text)
            return None

        return parameter

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Starting connectivity test")

        # make rest call
        endpoint = STATUSPAGE_INCIDENTS_ENDPOINT.format(self._page_id)

        ret_val, _ = self._make_rest_call(endpoint, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_incident(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        incident_id = param["incident_id"]

        endpoint = STATUSPAGE_FOR_INCIDENT_ENDPOINT.format(self._page_id, incident_id)

        ret_val, response = self._make_rest_call(endpoint, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully fetched incident")

    def _handle_list_incidents(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        parameters = dict()
        query = param.get("query")
        page = param.get("page_offset")

        limit = self._validate_integers(action_result, param.get("limit", 100), "limit")
        if limit is None:
            return action_result.get_status()

        if page:
            page = self._validate_integers(action_result, page, "page offset", allow_zero=True)
            if page is None:
                return action_result.get_status()
            parameters["page"] = page

        if query:
            parameters["q"] = query
        parameters["limit"] = limit

        endpoint = STATUSPAGE_INCIDENTS_ENDPOINT.format(self._page_id)

        ret_val, response = self._make_rest_call(endpoint, action_result, params=parameters)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for incident in response:
            action_result.add_data(incident)

        summary = action_result.set_summary({})
        summary["num_incidents"] = len(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_incident(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        data = dict()

        ret_val, components = self._get_fields(param, action_result)

        data["incident"] = {
            "name": param["name"],
            "status": param.get("status"),
            "impact_override": param.get("impact_override"),
            "body": param.get("body"),
            "component_ids": param.get("component_ids"),
            "components": components,
        }

        endpoint = STATUSPAGE_INCIDENTS_ENDPOINT.format(self._page_id)
        ret_val, response = self._make_rest_call(endpoint, action_result, json=data, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully created incident")

    def _handle_update_incident(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        data = dict()
        ret_val, components = self._get_fields(param, action_result)

        incident_id = param["incident_id"]

        name = param.get("name")
        status = param.get("status")
        impact_override = param.get("impact_override")
        body = param.get("body")
        component_ids = param.get("component_ids")

        incident = dict()
        if name:
            incident["name"] = name
        if status:
            incident["status"] = status
        if impact_override:
            incident["impact_override"] = impact_override
        if body:
            incident["body"] = body
        if component_ids:
            incident["component_ids"] = component_ids
        if components:
            incident["components"] = components

        data["incident"] = incident

        endpoint = STATUSPAGE_FOR_INCIDENT_ENDPOINT.format(self._page_id, incident_id)
        ret_val, response = self._make_rest_call(endpoint, action_result, json=data, method="patch")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully updated incident")

    def _get_fields(self, param, action_result):
        components = param.get("components")

        # fields is an optional field
        if not components:
            return RetVal(phantom.APP_SUCCESS, None)

        # we take in as a dictionary string, first try to load it as is
        try:
            components = json.loads(components)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, STATUSPAGE_ERROR_FIELDS_JSON_PARSE.format(error=error_message)), None)

        return RetVal(phantom.APP_SUCCESS, components)

    def _handle_create_incident_subscriber(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        incident_id = param["incident_id"]

        data = dict()
        data["subscriber"] = {
            "email": param["email"]
            # 'phone_country': param.get('phone_country'),
            # 'phone_number': param.get('phone_number'),
            # 'skip_confirmation_notification': param.get('skip_confirmation_notification')
        }

        endpoint = STATUSPAGE_INCIDENT_SUBSCRIBERS_ENDPOINT.format(self._page_id, incident_id)
        ret_val, response = self._make_rest_call(endpoint, action_result, json=data, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully created incident subscriber")

    def _handle_list_incident_subscribers(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        parameter = dict()
        incident_id = param["incident_id"]
        page = param.get("page")
        per_page = param.get("per_page", 100)

        if page:
            page = self._validate_integers(action_result, page, "page", allow_zero=True)
            if page is None:
                return action_result.get_status()
            parameter["page"] = page

        per_page = self._validate_integers(action_result, per_page, "per_page")
        if per_page is None:
            return action_result.get_status()

        parameter["per_page"] = per_page

        endpoint = STATUSPAGE_INCIDENT_SUBSCRIBERS_ENDPOINT.format(self._page_id, incident_id)

        ret_val, response = self._make_rest_call(endpoint, action_result, params=parameter)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for incident in response:
            action_result.add_data(incident)

        summary = action_result.set_summary({})
        summary["num_of_subscribers"] = len(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print(f"action_id: {self.get_action_identifier()}")

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)
        elif action_id == "list_incidents":
            ret_val = self._handle_list_incidents(param)
        elif action_id == "create_incident":
            ret_val = self._handle_create_incident(param)
        elif action_id == "get_incident":
            ret_val = self._handle_get_incident(param)
        elif action_id == "update_incident":
            ret_val = self._handle_update_incident(param)
        elif action_id == "create_incident_subscriber":
            ret_val = self._handle_create_incident_subscriber(param)
        elif action_id == "list_incident_subscribers":
            ret_val = self._handle_list_incident_subscribers(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()
        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}

        config = self.get_config()
        self._base_url = config["base_url"]
        if not self._base_url.endswith("/"):
            self._base_url = f"{self._base_url}/"

        self._api_key = config["api_key"]
        self._page_id = config["page_id"]

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved accross actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == "__main__":
    import argparse
    import sys

    import pudb

    pudb.set_trace()

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
            login_url = StatuspageConnector._get_phantom_base_url() + "/login"
            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=60)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=60)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = StatuspageConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
