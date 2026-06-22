# File: beyondtrust_connector.py
#
# Copyright (c) 2025-2026 Splunk Inc.
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
from datetime import datetime, timezone

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from beyondtrust_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class BeyondtrustConnector(BaseConnector):
    """
    Beyondtrust connector class that serves as a starting point for new connectors.
    """

    def __init__(self):
        super().__init__()
        self._base_url = None
        self._verify = None
        self._oauth_client_id = None
        self._oauth_client_secret = None
        self._access_token = None

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_message = BT_ERR_MSG_UNAVAILABLE

        self.error_print("Error occurred:", e)

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except Exception:
            self.error_print("Exception occurred while getting error code and message")

        if not error_code:
            error_text = f"Error Message: {error_message}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_message}"

        return error_text

    def _get_token(self, action_result):
        """This function is used to get a token via REST Call.

        :param action_result: Object of action result
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        req_url = f"/{API_OAUTH2_ENDPOINT}"

        payload = {"grant_type": "client_credentials", "client_id": self._oauth_client_id, "client_secret": self._oauth_client_secret}

        ret_val, resp_json = self._make_rest_call(req_url, action_result, data=payload, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self._access_token = resp_json[BT_EP_REST_RESPONSE].get(BT_ACCESS_TOKEN_STRING, None)

        return phantom.APP_SUCCESS

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
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {error_message}"), None)

        response_data = {BT_EP_REST_RESPONSE: resp_json, BT_EP_REST_RESPONSE_HEADERS: r.headers}

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, response_data)

        # Handle Rate Limits
        rlimit_remaining = r.headers.get(BT_RATE_LIMIT_REMAINING)
        if rlimit_remaining and int(rlimit_remaining) < 1:
            self.debug_print(f"{BT_RATE_LIMIT_ERR_MSG} - {resp_json}")
            message = BT_RESPONSE_ERROR_MESSAGE.format(status_code=r.status_code, error_text=BT_RATE_LIMIT_ERR_MSG)
            return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

        # Processing the error returned in json
        errors = resp_json.get("errors", None)
        error_message = f"{resp_json.get('message')}. Error(s): {errors}" if errors else f"{resp_json.get('message')}"
        message = BT_RESPONSE_ERROR_MESSAGE.format(status_code=r.status_code, error_text=error_message)

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

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = f"{self._base_url}{endpoint}"

        try:
            r = request_func(
                url,
                # auth=(username, password),  # basic authentication
                verify=config.get("verify_server_cert", False),
                **kwargs,
            )
        except Exception as e:
            error_message = f"Error Connecting to server. Details: {self._get_error_message_from_exception(e)}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), resp_json)

        return self._process_response(r, action_result)

    def _make_rest_call_helper(self, action_result, endpoint, headers=None, params=None, data=None, method="get"):
        """Function that helps setting REST call to the app.

        :param action_result: object of ActionResult class
        :param endpoint: REST endpoint that needs to appended to the service address
        :param headers: request headers
        :param params: request parameters
        :param data: request body
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        if headers is None:
            headers = {}

        if not self._access_token:
            self.debug_print("Token not found. Refreshing it.")
            ret_val = self._get_token(action_result)

            if phantom.is_fail(ret_val):
                return RetVal(action_result.get_status(), None)

        headers.update({"Authorization": f"Bearer {self._access_token}", "Accept": "application/json", "Content-Type": "application/json"})
        ret_val, resp_json = self._make_rest_call(endpoint, action_result, method=method, headers=headers, params=params, data=data)

        # If token is expired, generate a new token
        msg = action_result.get_message()
        if msg and any(failure_message in msg for failure_message in AUTH_FAILURE_MESSAGES):
            self.save_progress("Token is invalid/expired. Hence, generating a new token.")
            ret_val = self._get_token(action_result)
            if phantom.is_fail(ret_val):
                return RetVal(ret_val, None)

            headers.update({"Authorization": f"Bearer {self._access_token}"})

            ret_val, resp_json = self._make_rest_call(endpoint, action_result, method=method, headers=headers, params=params, data=data)

        if phantom.is_fail(ret_val):
            return RetVal(ret_val, resp_json)

        return RetVal(phantom.APP_SUCCESS, resp_json)

    def _next_page(self, action_result, header_link):
        """
        Function used to extract the link to the next page from a Link Header.

        :param action_result: Object of ActionResult class
        :param header_link: value of the Link header key as string
        :return: string url of the next page, none otherwise
        """
        if header_link.find('rel="next"') == -1:
            return None

        links = header_link.split(",")
        for link in links:
            if 'rel="next"' in link:
                return link.split(";")[0].strip(" <>")

        self.save_progress(BT_ERR_MSG_NEXT_PAGE)
        action_result.set_status(phantom.APP_ERROR, BT_ERR_MSG_NEXT_PAGE)
        return None

    def _make_paginated_call(self, action_result, endpoint, headers=None, params=None):
        """
        Function used to create an iterator that will paginate through responses from called methods.

        :param action_result: Object of ActionResult class
        :param endpoint: REST endpoint that needs to appended to the service address
        :param headers: Dictionary of headers for the rest API calls
        :param params: Dictionary of params for the rest API calls
        """
        # Maximum page size
        page_size = BT_PAGE_SIZE
        result = []
        if isinstance(params, dict):
            params.update({"per_page": page_size})
        else:
            params = {"per_page": page_size}

        while True:
            # make rest call
            ret_val, response = self._make_rest_call_helper(action_result, endpoint, headers=headers, params=params, method="get")

            if phantom.is_fail(ret_val):
                return phantom.APP_ERROR, []

            for item in response.get(BT_EP_REST_RESPONSE):
                result.append(item)

            if BT_USE_X_BT_PAGINATION_HEADERS:
                current_page = response[BT_EP_REST_RESPONSE_HEADERS].get(BT_PAGINATION_CURRENT, 1)
                last_page = response[BT_EP_REST_RESPONSE_HEADERS].get(BT_PAGINATION_LAST, None)

                if not last_page:
                    error_msg = f"Could not find {BT_PAGINATION_LAST} among headers in response: {response[BT_EP_REST_RESPONSE_HEADERS]}"
                    action_result.set_status(phantom.APP_ERROR, error_msg)
                    break

                if last_page == current_page:
                    self.save_progress(f"Page {current_page}/{last_page}. Fetched all data for endpoint '{endpoint}'")
                    break

                params.update({"current_page": int(current_page) + 1})
                self.save_progress(f"Page {current_page}/{last_page}. Fetching from next page: {params['current_page']}")

            else:
                next_endpoint = self._next_page(action_result, response[BT_EP_REST_RESPONSE_HEADERS].get("Link", ""))

                if action_result.is_fail():
                    return phantom.APP_ERROR, []

                if not next_endpoint:
                    self.save_progress(f"Fetched all data for endpoint '{endpoint}'")
                    break

                endpoint = next_endpoint
                self.save_progress(f"Fetching from next page: '{endpoint}")

        return phantom.APP_SUCCESS, result

    def _handle_test_connectivity(self, param):
        """
        Validate the asset configuration for connectivity using supplied credentials.
        """
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress(BT_GENERATING_ACCESS_TOKEN_MESSAGE)

        ret_val = self._get_token(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress("Connecting to endpoint")
        # make rest call
        ret_val, _response = self._make_rest_call_helper(action_result, API_GET_ALL_ACCOUNTS, params=None, headers=None)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _is_user_inactive(self, user, max_inactivity_days):
        """
        Function to calculate whether user is inactive.

        :param user: Dictionary of the user object
        :param max_inactivity_days: Threshold indicating the max amount of days of inactivity
        """
        last_auth = user.get("last_authentication")
        ref_date_str = last_auth if last_auth else user.get("created_at")

        try:
            ref_date = datetime.fromisoformat(ref_date_str.replace("Z", "+00:00"))
        except ValueError:
            ref_date = datetime.strptime(ref_date_str, "%Y-%m-%d %H:%M:%S.%f")

        ref_date = ref_date.replace(tzinfo=timezone.utc)
        inactivity_days = (datetime.now(timezone.utc) - ref_date).days
        return inactivity_days >= max_inactivity_days

    def _handle_list_users(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))
        arguments = ["security_provider_id", "username", "email_address"]
        params = {k: v for k, v in param.items() if k in arguments and v is not None}

        get_inactive = param.get("inactive_only")
        get_enabled = param.get("enabled_only")
        max_inactivity = param.get("max_inactive_days", BT_MAX_INACTIVITY_DAYS)

        # Validity check for inactivity calculation
        if get_inactive == True and max_inactivity <= 0:
            error_msg = f"Invalid parameter 'max_inactive_days': its value must be bigger than 0"
            return action_result.set_status(phantom.APP_ERROR, error_msg)

        try:
            # make rest call
            ret_val, users = self._make_paginated_call(action_result, API_GET_USERS, params=params)
            tot_users = len(users)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            # Filter enabled users
            if get_enabled:
                users = [user for user in users if bool(user.get("enabled")) is True]
                self.debug_print(f"Filtered {len(users)} users out of {tot_users}")

            # Filter inactive users
            if get_inactive:
                users = [user for user in users if self._is_user_inactive(user, max_inactivity)]
                self.debug_print(f"Filtered {len(users)} users out of {tot_users}")

        except Exception as e:
            error_msg = self._get_error_message_from_exception(e)
            self.debug_print(error_msg)
            return action_result.set_status(phantom.APP_ERROR, error_msg)

        for user in users:
            action_result.add_data(user)

        summary = action_result.update_summary({})
        resp_data = action_result.get_data()

        if resp_data and resp_data[action_result.get_data_size() - 1] == "Empty response":
            summary["num_users"] = (action_result.get_data_size()) - 1
        else:
            summary["num_users"] = action_result.get_data_size()

        self.save_progress(f"Completed action handler for: {self.get_action_identifier()}")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_user_groups(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))
        user_id = param.get("user_id")

        try:
            # make rest call
            ret_val, groups = self._make_paginated_call(action_result, API_GET_USER_MEMBERSHIP.format(userid=user_id))

            if phantom.is_fail(ret_val):
                return action_result.get_status()

        except Exception as e:
            error_msg = self._get_error_message_from_exception(e)
            self.debug_print(error_msg)
            return action_result.set_status(phantom.APP_ERROR, error_msg)

        for group in groups:
            action_result.add_data(group)

        summary = action_result.update_summary({})
        resp_data = action_result.get_data()

        if resp_data and resp_data[action_result.get_data_size() - 1] == "Empty response":
            summary["num_groups"] = (action_result.get_data_size()) - 1
        else:
            summary["num_groups"] = action_result.get_data_size()

        self.save_progress(f"Completed action handler for: {self.get_action_identifier()}")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_disable_user(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))
        user_id = param.get("user_id")

        payload = {"enabled": False}

        try:
            # make rest call
            ret_val, response = self._make_rest_call_helper(
                action_result, API_UPDATE_USER.format(userid=user_id), data=json.dumps(payload), method="patch"
            )

            if phantom.is_fail(ret_val):
                return action_result.get_status()

        except Exception as e:
            error_msg = self._get_error_message_from_exception(e)
            self.debug_print(error_msg)
            return action_result.set_status(phantom.APP_ERROR, error_msg)

        action_result.add_data(response.get(BT_EP_REST_RESPONSE))
        summary = action_result.update_summary({})

        self.save_progress(f"Completed action handler for: {self.get_action_identifier()}")
        return action_result.set_status(phantom.APP_SUCCESS)

    def initialize(self):
        """
        Initialize the connector.
        """
        self.debug_print("Initializing connector")
        config = self.get_config()

        # Get configuration parameters
        self._base_url = config.get("base_url")
        if self._base_url.endswith("/"):
            self._base_url = self._base_url[:-1]

        self._oauth_client_id = config.get("oauth_client_id")
        self._oauth_client_secret = config.get("oauth_client_secret")
        self._verify = config.get("verify_server_cert", False)

        return phantom.APP_SUCCESS

    def handle_action(self, param):
        """
        Dispatcher for actions.
        """
        self.debug_print("action_id ", self.get_action_identifier())

        action_mapping = {
            "test_connectivity": self._handle_test_connectivity,
            "list_users": self._handle_list_users,
            "get_user_groups": self._handle_get_user_groups,
            "disable_user": self._handle_disable_user,
        }

        action = self.get_action_identifier()
        action_execution_status = phantom.APP_SUCCESS

        if action in action_mapping:
            action_function = action_mapping[action]
            action_execution_status = action_function(param)

        return action_execution_status


if __name__ == "__main__":
    import sys

    import pudb

    pudb.set_trace()

    connector = BeyondtrustConnector()
    connector.print_progress_message = True

    sys.exit(0)
