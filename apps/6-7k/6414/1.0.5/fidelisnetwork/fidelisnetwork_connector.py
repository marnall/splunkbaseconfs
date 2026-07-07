# File: fidelisnetwork_connector.py
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
# Phantom imports
import json
from datetime import datetime

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# imports specific to this connector
from fidelisnetwork_consts import *
from request_handler import RequestStateHandler


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


# Define the App Class
class FidelisnetworkConnector(BaseConnector):
    # The actions supported by this connector
    ACTION_ID_TEST_CONNECTIVITY = "test_connectivity"
    ACTION_ID_LIST_ALERTS = "list_alerts"
    ACTION_ID_GET_ALERT_DETAILS = "get_alert_details"
    ACTION_ID_DELETE_ALERT = "delete_alert"

    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._base_url = None
        self._state = {}
        self._retry_access_token = None
        self._retry_one_more = None
        self._retry_with_latest_header = None
        self._retry_header = None

    def initialize(self):
        """This is an optional function that can be implemented by the AppConnector derived class. Since the
        configuration dictionary is already validated by the time this function is called, it's a good place to do any
        extra initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS or
        phantom.APP_ERROR. If this function returns phantom.APP_ERROR, then AppConnector::handle_action will not get
        called.

        Returns:
            :return: status success/failure
        """
        config = self.get_config()
        asset_id = self.get_asset_id()
        self.rsh = RequestStateHandler(asset_id)
        self._state = self.rsh.load_state()
        # Below variable uses for retrying rest call purpose
        self._retry_access_token = True
        self._retry_one_more = True
        self._retry_with_latest_header = True
        self._retry_header = True
        # Base URL
        base_url = config["host_url"]

        self._base_url = base_url + ("" if base_url.endswith("/") else "/")

        return phantom.APP_SUCCESS

    def finalize(self):
        """Perform some final operations or clean up operations.

        Returns:
            :return: status success
        """
        self.rsh.save_state(self._state)
        return phantom.APP_SUCCESS

    def _login(self, action_result):
        """Authenticate and set header with latest access token

        Args:
            action_result: _description_

        Returns:
            headers (dict): Headers
        """

        headers = {"Content-Type": "application/json"}

        if self._state.get("x_uid") is None or self.get_action_identifier() == self.ACTION_ID_TEST_CONNECTIVITY:
            config = self.get_config()
            self.save_progress(APP_PROG_CONNECTING_TO_FIDELIS.format(self._base_url))
            username = config["username"].strip()
            password = config["password"].strip()
            data = json.dumps({"user": username, "password": password})
            endpoint = "j/rest/v2/access/token/"

            ret_val, response = self._make_rest_call(endpoint, action_result, data=data, method="post", headers=headers)

            if phantom.is_fail(ret_val):
                return headers

            self._state["x_uid"] = response.get("uid", None)

        headers["x-uid"] = self._state.get("x_uid", None)

        return headers

    def _process_empty_response(self, response, action_result):
        self.save_progress(f"{response.status_code}")
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})
        elif response.status_code == 401:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Unauthorized. Invalid username or password"), None)

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

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
            if "404" in error_text:
                error_text = "Invalid Fidelis API URL"
        except Exception as ex:
            self.debug_print(f"Exception in _process_html_response: {ex}")
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as ex:
            self.debug_print(f"Exception in _download_file_to_vault: {ex}")
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {ex!s}"), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        if "detailMessage" in resp_json and "errorCode" in resp_json:
            message = resp_json["detailMessage"]
            if "Unauthorized access from Java with invalid session" in resp_json["detailMessage"]:
                message = FIDELIS_TEST_CONN_MSG
            elif any(error_msg in resp_json["detailMessage"] for error_msg in FIDELIS_ERROR_STRINGS):
                message = "Please enter valid Alert ID [Numeric]"
        # You should process the error returned in the json
        else:
            message = "Error from server. Status Code: {} Data from server: {}".format(
                r.status_code, r.text.encode("ascii", "backslashreplace").decode("unicode-escape").replace("{", "{{").replace("}", "}}")
            )

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

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts
        resp_json = None
        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = self._base_url + endpoint

        try:
            r = request_func(
                url,
                data=data,
                headers=headers,
                verify=True,
            )
            # makes rest call again with new x-uid token in case old one gave 401 error
            if r.status_code == 401 and self._retry_access_token:
                # Retry the same rest call one more time to checking for avoiding token random behavior
                if self._retry_one_more:
                    self._retry_one_more = False  # make it to false to avoid rest call after one time (prevents recursive loop)
                    return self._make_rest_call(endpoint, action_result, headers, params, data, method, **kwargs)

                if self._retry_header:
                    if self._state.get("x_uid"):
                        self._state.pop("x_uid")
                    headers = self._login(action_result)
                    self._retry_header = False
                    self._retry_one_more = True

                # Retry the same rest call one more time with latest headers for avoiding token random behavior
                if self._retry_with_latest_header:
                    self._retry_with_latest_header = False  # make it to false to avoid rest call after one time (prevents recursive loop)
                    return self._make_rest_call(endpoint, action_result, headers, params, data, method, **kwargs)
                self._retry_access_token = False  # make it to false to avoid getting access token after one time (prevents recursive loop)

        except Exception as ex:
            self.debug_print(f"Exception in _make_rest_call: {ex}")
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {ex!s}"), resp_json)

        return self._process_response(r, action_result)

    def _test_connectivity(self, param):
        """Testing of given credentials and obtaining authorization for all other actions.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress(FIDELIS_PROG_USING_BASE_URL, base_url=self._base_url)

        headers = self._login(action_result)

        if not headers.get("x-uid"):
            self.save_progress(FIDELIS_ERROR_CONNECTIVITY_TEST)
            return action_result.get_status()

        self.save_progress(FIDELIS_SUCC_CONNECTIVITY_TEST)
        return action_result.set_status(phantom.APP_SUCCESS)

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
                        action_result.set_status(phantom.APP_ERROR, FIDELIS_LIMIT_VALIDATION_ALLOW_ZERO_MSG.format(parameter=key))
                        return None
                else:
                    action_result.set_status(phantom.APP_ERROR, FIDELIS_LIMIT_VALIDATION_MSG.format(parameter=key))
                    return None
        except Exception as e:
            self.debug_print(f"Integer validation failed. Error occurred while validating integer value. Error: {e!s}")
            if allow_zero:
                error_text = FIDELIS_LIMIT_VALIDATION_ALLOW_ZERO_MSG.format(parameter=key)
            else:
                error_text = FIDELIS_LIMIT_VALIDATION_MSG.format(parameter=key)
            action_result.set_status(phantom.APP_ERROR, error_text)
            return None

        return parameter

    def _validate_time_format(self, action_result, time=None):
        try:
            datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
            return True
        except Exception as e:
            action_result.set_status(phantom.APP_ERROR, f"Wrong format for '{time}' please use this '%Y-%m-%d %H:%M:%S' format. Exception : {e}")
            return False

    def _list_alerts(self, param):
        """List alerts

        Args:
            param : Dictionary of input parameters

        Returns:
            status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        order = [{"column": param.get("column", "ALERT_TIME"), "direction": param.get("direction", "DESC")}]

        limit = self._validate_integers(action_result, param.get("limit", 100), "limit")
        if limit is None:
            return action_result.get_status(), None

        pagination = {"size": limit, "page": 1}

        time_settings = {"from": "", "to": "", "key": "all"}

        start_time = param.get("start_time", None)
        end_time = param.get("end_time", None)

        if start_time is None and end_time is None:
            self.debug_print("Time is not given by user.")
        if start_time is not None:
            if not self._validate_time_format(action_result, start_time):
                return action_result.get_status()
            time_settings["key"] = "custom"
            time_settings["from"] = start_time
        if end_time is not None:
            if not self._validate_time_format(action_result, end_time):
                return action_result.get_status()
            time_settings["key"] = "custom"
            time_settings["to"] = end_time

        data = json.dumps(
            {
                "columns": ["ALERT_ID", "ALERT_TIME", "SEVERITY", "HOST_IP", "SUMMARY", "ALERT_TYPE"],
                "order": order,
                "pagination": pagination,
                "timeSettings": time_settings,
            }
        )

        headers = self._login(action_result)

        endpoint = "j/rest/v1/alert/search/"

        ret_val, resp_json = self._make_rest_call(endpoint, action_result, data=data, method="post", headers=headers)
        if not ret_val and not resp_json:
            return action_result.get_status()

        action_result.add_data(resp_json)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        total_alert = len(resp_json.get("aaData"))
        summary["total_alerts"] = total_alert

        return action_result.set_status(phantom.APP_SUCCESS, FIDELIS_SUCC_LIST_ALERTS.format(total_alert))

    def _get_alert_details(self, param):
        """Get alert detail

        Args:
            param : Dictionary of input parameters

        Returns:
            status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        headers = self._login(action_result)

        alert_id = param["alert_id"]

        endpoint = f"j/rest/v1/alert/info/{alert_id}/"

        ret_val, resp_json = self._make_rest_call(endpoint, action_result, headers=headers)

        if not ret_val and not resp_json:
            return action_result.get_status()

        action_result.add_data(resp_json)

        summary = action_result.update_summary({})
        summary["alert_id"] = "Fetched details of {} alert".format(resp_json.get("alertId"))

        return action_result.set_status(phantom.APP_SUCCESS, FIDELIS_SUCC_GET_ALERT_DETAILS)

    def _delete_alert(self, param):
        """Delete alert

        Args:
            param : Dictionary of input parameters

        Returns:
            status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        headers = self._login(action_result)

        alert_ids = param["alert_id"]

        alert_ids = [x.strip() for x in alert_ids.split(",")]
        alert_ids = list(filter(None, alert_ids))

        if not (len(alert_ids)):
            return action_result.set_status(phantom.APP_ERROR, FIDELIS_ALERT_ID_VALIDATION_MSG.format(parameter="alert_id"))

        data = json.dumps({"type": "byAlertID", "alertIds": alert_ids})

        endpoint = "j/rest/v1/alert/delete/"

        ret_val, resp_json = self._make_rest_call(endpoint, action_result, data=data, method="post", headers=headers)

        if not ret_val and not resp_json:
            return action_result.get_status()

        alert_lis = []
        for i in range(0, len(alert_ids)):
            alert_lis.append({"ALERT_ID": alert_ids[i]})

        action_result.add_data({"ALERT_DATA": alert_lis})

        summary = action_result.update_summary({})
        summary["alert_ids"] = f"Deleted {len(alert_ids)} alerts from Fidelis Network"

        return action_result.set_status(phantom.APP_SUCCESS, FIDELIS_SUCC_DELETE_ALERTS)

    def handle_action(self, param):
        """Get current action identifier and call member function of its own to handle the action.

        Args:
            param : dictionary which contains information about the actions to be executed
        Returns:
            return : status success/failure
        """
        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()
        result = None

        self._param = param

        if action_id == self.ACTION_ID_TEST_CONNECTIVITY:
            result = self._test_connectivity(param)
        elif action_id == self.ACTION_ID_LIST_ALERTS:
            result = self._list_alerts(param)
        elif action_id == self.ACTION_ID_GET_ALERT_DETAILS:
            result = self._get_alert_details(param)
        elif action_id == self.ACTION_ID_DELETE_ALERT:
            result = self._delete_alert(param)
        return result


if __name__ == "__main__":
    import sys

    # import pudb
    # pudb.set_trace()

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = FidelisnetworkConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
