# File: mattermost_connector.py
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
# Phantom sample App Connector python file
import grp
import json
import os
import pwd
import re
import sys
import time
from datetime import datetime

import dateutil
import dateutil.parser

# Phantom App imports
import phantom.app as phantom
import phantom.rules as ph_rules
import requests
from bs4 import BeautifulSoup, UnicodeDammit
from django.http import HttpResponse
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from mattermost_consts import *


def _handle_login_redirect(request, key):
    """This function is used to redirect login request to the Mattermost login page.

    :param request: Data given to REST endpoint
    :param key: Key to search in state file
    :return: response authorization_url/admin_consent_url
    """

    asset_id = request.GET.get("asset_id")
    if not asset_id:
        return HttpResponse("ERROR: Asset ID not found in URL", content_type="text/plain", status=400)
    state = _load_app_state(asset_id)
    if not state:
        return HttpResponse("ERROR: Invalid asset_id", content_type="text/plain", status=400)
    url = state.get(key)
    if not url:
        return HttpResponse(f"App state is invalid, {key} not found.", content_type="text/plain", status=400)
    response = HttpResponse(status=302)
    response["Location"] = url
    return response


def _load_app_state(asset_id, app_connector=None):
    """This function is used to load the current state file.

    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :return: state: Current state file as a dictionary
    """

    asset_id = str(asset_id)
    if not asset_id or not asset_id.isalnum():
        if app_connector:
            app_connector.debug_print("In _load_app_state: Invalid asset_id")
        return {}

    app_dir = os.path.dirname(os.path.abspath(__file__))
    state_file = f"{app_dir}/{asset_id}_state.json"
    real_state_file_path = os.path.abspath(state_file)
    if not os.path.dirname(real_state_file_path) == app_dir:
        if app_connector:
            app_connector.debug_print("In _load_app_state: Invalid asset_id")
        return {}

    state = {}
    try:
        with open(real_state_file_path) as state_file_obj:
            state_file_data = state_file_obj.read()
            state = json.loads(state_file_data)
    except Exception as e:
        if app_connector:
            app_connector.debug_print(f"In _load_app_state: Exception: {e!s}")

    if app_connector:
        app_connector.debug_print("Loaded state: ", state)

    return state


def _save_app_state(state, asset_id, app_connector):
    """This function is used to save current state in file.

    :param state: Dictionary which contains data to write in state file
    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :return: status: phantom.APP_SUCCESS
    """

    asset_id = str(asset_id)
    if not asset_id or not asset_id.isalnum():
        if app_connector:
            app_connector.debug_print("In _save_app_state: Invalid asset_id")
        return {}

    app_dir = os.path.split(__file__)[0]
    state_file = f"{app_dir}/{asset_id}_state.json"

    real_state_file_path = os.path.abspath(state_file)
    if not os.path.dirname(real_state_file_path) == app_dir:
        if app_connector:
            app_connector.debug_print("In _save_app_state: Invalid asset_id")
        return {}

    if app_connector:
        app_connector.debug_print("Saving state: ", state)

    try:
        with open(real_state_file_path, "w+") as state_file_obj:
            state_file_obj.write(json.dumps(state))
    except Exception as e:
        print(f"Unable to save state file: {e!s}")

    return phantom.APP_SUCCESS


def _handle_login_response(request):
    """This function is used to get the login response of authorization request from Mattermost.

    :param request: Data given to REST endpoint
    :return: HttpResponse. The response displayed on authorization URL page
    """

    asset_id = request.GET.get("state")
    if not asset_id:
        return HttpResponse(f"ERROR: Asset ID not found in URL\n{json.dumps(request.GET)}", content_type="text/plain", status=400)

    # Check for error in URL
    error = request.GET.get("error")
    error_description = request.GET.get("error_description")

    # If there is an error in response
    if error:
        message = f"Error: {error}"
        if error_description:
            message = f"{message} Details: {error_description}"
        return HttpResponse(f"Server returned {message}", content_type="text/plain", status=400)

    code = request.GET.get("code")

    # If code is not available
    if not code:
        return HttpResponse(f"Error while authenticating\n{json.dumps(request.GET)}", content_type="text/plain", status=400)

    state = _load_app_state(asset_id)
    state["code"] = code
    _save_app_state(state, asset_id, None)

    return HttpResponse("Code received. Please close this window, the action will continue to get new token.", content_type="text/plain")


def _handle_rest_request(request, path_parts):
    """Handle requests for authorization.

    :param request: Data given to REST endpoint
    :param path_parts: Parts of the URL passed
    :return: Dictionary containing response parameters
    """

    if len(path_parts) < 2:
        return HttpResponse("error: True, message: Invalid REST endpoint request", content_type="text/plain", status=404)

    call_type = path_parts[1]

    # To handle authorize request in test connectivity action
    if call_type == "start_oauth":
        return _handle_login_redirect(request, "authorization_url")

    # To handle response from Mattermost
    if call_type == "result":
        return_val = _handle_login_response(request)
        asset_id = request.GET.get("state")  # nosemgrep
        if asset_id and asset_id.isalnum():
            app_dir = os.path.dirname(os.path.abspath(__file__))
            auth_status_file_path = f"{app_dir}/{asset_id}_{MATTERMOST_TC_FILE}"
            real_auth_status_file_path = os.path.abspath(auth_status_file_path)
            if not os.path.dirname(real_auth_status_file_path) == app_dir:
                return HttpResponse("Error: Invalid asset_id", content_type="text/plain", status=400)
            open(auth_status_file_path, "w").close()
            try:
                uid = pwd.getpwnam("apache").pw_uid
                gid = grp.getgrnam("phantom").gr_gid
                os.chown(auth_status_file_path, uid, gid)
                os.chmod(auth_status_file_path, "0664")
            except Exception:
                pass

        return return_val
    return HttpResponse("error: Invalid endpoint", content_type="text/plain", status=404)


def _get_dir_name_from_app_name(app_name):
    """Get name of the directory for the app.

    :param app_name: Name of the application for which directory name is required
    :return: app_name: Name of the directory for the application
    """

    app_name = "".join([x for x in app_name if x.isalnum()])
    app_name = app_name.lower()
    if not app_name:
        app_name = "app_for_phantom"
    return app_name


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class MattermostConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None
        self._verify_server_cert = False
        self._server_url = None
        self._client_id = None
        self._client_secret = None
        self._personal_token = None
        self._access_token = None

    def _process_empty_response(self, response, action_result):
        """This function is used to process empty response.

        :param response: Response data
        :param action_result: Object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # If response is OK or No-Content
        if response.status_code in [200, 204]:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    def _process_html_response(self, response, action_result):
        """This function is used to process html response.

        :param response: Response data
        :param action_result: Object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

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

        message = f"Status Code: {status_code}. Data from server:\n{self._handle_py_ver_compat_for_input_str(error_text)}\n"

        # For successful status_codes, HTML pages are retrieved in response
        success_status_codes = [200, 201, 204]

        if status_code in success_status_codes:
            message = "Status Code: {}. Data from server:\n{}\n".format(status_code, "Invalid URL. Cannot parse response.")

        # For forbidden scenarios, HTML response is retrieved in response
        if status_code == 403:
            message = "Status Code: {}. Data from server:\n{}\n".format(status_code, "Forbidden. Please verify credentials.")
        message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, response, action_result):
        """This function is used to process json response.

        :param response: Response data
        :param action_result: Object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # Try a json parse
        try:
            resp_json = response.json()
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, f"Unable to parse JSON response. Error: {self._get_error_message_from_exception(e)}"
                ),
                None,
            )

        if 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        message = None

        # Check if error has detailed error field
        if resp_json.get("detailed_error"):
            err = self._handle_py_ver_compat_for_input_str(resp_json["detailed_error"])
            message = f"Error from server. Status Code: {response.status_code} Data from server: {err}"
        # Check for message in error
        elif resp_json.get("message"):
            resp_msg = self._handle_py_ver_compat_for_input_str(resp_json["message"])
            message = f"Error from server. Status Code: {response.status_code} Data from server: {resp_msg}"

        if not message:
            resp_txt = self._handle_py_ver_compat_for_input_str(response.text.replace("{", "{{").replace("}", "}}"))
            message = f"Error from server. Status Code: {response.status_code} Data from server: {resp_txt}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, response, action_result):
        """This function is used to process html response.

        :param response: Response data
        :param action_result: Object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": response.status_code})
            action_result.add_debug_data({"r_text": response.text})
            action_result.add_debug_data({"r_headers": response.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in response.headers.get("Content-Type", ""):
            return self._process_json_response(response, action_result)

        # Process a javascript response
        if "text/javascript" in response.headers.get("Content-Type", ""):
            return self._process_json_response(response, action_result)

        # Process a text response
        if "text/plain" in response.headers.get("Content-Type", ""):
            return self._process_json_response(response, action_result)

        # Process an HTML response, Do this no matter what the API talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in response.headers.get("Content-Type", ""):
            return self._process_html_response(response, action_result)

        # if no content-type is to be parsed, handle an empty response
        if not response.text:
            return self._process_empty_response(response, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            response.status_code, self._handle_py_ver_compat_for_input_str(response.text.replace("{", "{{").replace("}", "}}"))
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _handle_py_ver_compat_for_input_str(self, input_str):
        """
        This method returns the encoded|original string based on the Python version.
        :param python_version: Python major version
        :param input_str: Input string to be processed
        :return: input_str (Processed input string based on following logic 'input_str - Python 3; encoded input_str - Python 2')
        """

        try:
            if input_str and self._python_version == 2:
                input_str = UnicodeDammit(input_str).unicode_markup.encode("utf-8")
        except Exception:
            self.debug_print("Error occurred while handling python 2to3 compatibility for the input string")

        return input_str

    def _get_error_message_from_exception(self, e):
        """This method is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_code = "Error code unavailable"
                    error_msg = e.args[0]
            else:
                error_code = "Error code unavailable"
                error_msg = "Unknown error occurred. Please check the asset configuration and|or action parameters."
        except Exception:
            error_code = "Error code unavailable"
            error_msg = "Unknown error occurred. Please check the asset configuration and|or action parameters."

        try:
            error_msg = self._handle_py_ver_compat_for_input_str(error_msg)
        except TypeError:
            error_msg = "Error occurred while connecting to the Mattermost server. "
            error_msg += "Please check the asset configuration and|or the action parameters."
        except Exception:
            error_msg = "Unknown error occurred. Please check the asset configuration and|or action parameters."

        return f"Error Code: {error_code}. Error Message: {error_msg}"

    def _make_rest_call(self, url, action_result, headers=None, params=None, data=None, method="get", verify=False, timeout=None, files=None):
        """This function is used to make the REST call.

        :param url: url for making REST call
        :param action_result: Object of ActionResult class
        :param headers: Request headers
        :param params: Request parameters
        :param data: Request body
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :param verify: Verify server certificate
        :param timeout: Timeout of request
        :param files: File to be uploaded
        :return: Status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        resp_json = None

        # If no headers are passed, set empty headers
        if not headers:
            headers = {}

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        try:
            request_response = request_func(url, data=data, headers=headers, params=params, verify=verify, timeout=timeout, files=files)
        except Exception as e:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {self._get_error_message_from_exception(e)}"),
                resp_json,
            )

        return self._process_response(request_response, action_result)

    def _handle_update_request(self, url, action_result, params=None, data=None, verify=False, method="get", files=None):
        """This method is used to call maker_rest_call using different authentication methods.

        :param url: REST URL that needs to be called
        :param action_result: Object of ActionResult class
        :param params: Request params
        :param data: Request data
        :param verify: Verify server certificate(Default: True)
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :param files: File to be uploaded
        :return: Status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        # If the personal access token is provided
        if self._personal_token:
            headers = {"Authorization": f"Bearer {self._personal_token}"}
            ret_val, response = self._make_rest_call(
                url=url, action_result=action_result, headers=headers, data=data, params=params, verify=verify, method=method, files=files
            )

            if phantom.is_fail(ret_val):
                # If error is not 401 or other config parameters are not provided, return error
                if "401" not in action_result.get_message() or not self._access_token:
                    return action_result.get_status(), None
            else:
                return phantom.APP_SUCCESS, response

        if self._access_token:
            # Call using access_token
            headers = {"Authorization": f"Bearer {self._access_token}"}
            ret_val, response = self._make_rest_call(
                url=url, action_result=action_result, headers=headers, data=data, params=params, verify=verify, method=method, files=files
            )

            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            return phantom.APP_SUCCESS, response

        return action_result.set_status(phantom.APP_ERROR, status_message="Authentication failed"), None

    def _handle_test_connectivity(self, param):
        """This function is used to handle the test connectivity action.

        :param param: Dictionary of input parameters
        :return: Status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        action_result = self.add_action_result(ActionResult(dict(param)))

        app_state = {}

        # If none of the config parameters are present, return error
        if not (self._client_id and self._client_secret) and not self._personal_token:
            self.save_progress(MATTERMOST_TEST_CONNECTIVITY_FAILED_MSG)
            return action_result.set_status(phantom.APP_ERROR, status_message=MATTERMOST_CONFIG_PARAMS_REQUIRED_CONNECTIVITY)

        self.save_progress(MATTERMOST_MAKING_CONNECTION_MSG)
        url = f"{MATTERMOST_API_BASE_URL.format(server_url=self._server_url)}{MATTERMOST_CURRENT_USER_ENDPOINT}"

        if self._personal_token:
            headers = {"Authorization": f"Bearer {self._personal_token}"}
            ret_val, _ = self._make_rest_call(url=url, action_result=action_result, headers=headers)

            if phantom.is_fail(ret_val):
                # If error is not 401 or other config parameters are not provided, return error
                if "401" not in action_result.get_message() or not (self._client_id and self._client_secret):
                    self.save_progress(MATTERMOST_TEST_CONNECTIVITY_FAILED_MSG)
                    return action_result.get_status()
            else:
                self.save_progress(MATTERMOST_TEST_CONNECTIVITY_PASSED_MSG)
                return action_result.set_status(phantom.APP_SUCCESS)

        if self._client_id and self._client_secret:
            # If client_id and client_secret is provided, go for interactive login
            ret_val = self._handle_interactive_login(app_state, action_result=action_result)

            if phantom.is_fail(ret_val):
                self.save_progress(MATTERMOST_TEST_CONNECTIVITY_FAILED_MSG)
                return action_result.get_status()

            # Call using access_token
            headers = {"Authorization": f"Bearer {self._access_token}"}
            ret_val, _ = self._make_rest_call(url=url, action_result=action_result, headers=headers)

            if phantom.is_fail(ret_val):
                self.save_progress(MATTERMOST_TEST_CONNECTIVITY_FAILED_MSG)
                return action_result.get_status()

            self.save_progress(MATTERMOST_TEST_CONNECTIVITY_PASSED_MSG)
            return action_result.set_status(phantom.APP_SUCCESS)

        return action_result.set_status(phantom.APP_ERROR, status_message="Authentication failed")

    def _handle_interactive_login(self, app_state, action_result):
        """This function is used to handle the interactive login during test connectivity
        while client_id and client_secret is provided.

        :param action_result: Object of ActionResult class
        :return: status(success/failure)
        """

        ret_val, app_rest_url = self._get_app_rest_url(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Append /result to create redirect_uri
        redirect_uri = f"{app_rest_url}/result"
        app_state["redirect_uri"] = redirect_uri

        self.save_progress(MATTERMOST_OAUTH_URL_MSG)
        self.save_progress(redirect_uri)

        # Get asset ID
        asset_id = self.get_asset_id()

        # Authorization URL used to make request for getting code which is used to generate access token
        authorization_url = MATTERMOST_AUTHORIZE_URL.format(
            server_url=self._server_url, client_id=self._client_id, redirect_uri=redirect_uri, state=asset_id
        )

        app_state["authorization_url"] = authorization_url

        # URL which would be shown to the user
        url_for_authorize_request = f"{app_rest_url}/start_oauth?asset_id={asset_id}&"
        _save_app_state(app_state, asset_id, self)

        self.save_progress(MATTERMOST_AUTHORIZE_USER_MSG)
        self.save_progress(url_for_authorize_request)  # nosemgrep

        # Wait for 15 seconds for authorization
        time.sleep(MATTERMOST_AUTHORIZE_WAIT_TIME)

        # Wait for 105 seconds while user login to Mattermost
        status = self._wait(action_result=action_result)

        # Empty message to override last message of waiting
        self.send_progress("")
        if phantom.is_fail(status):
            return action_result.get_status()

        self.save_progress(MATTERMOST_CODE_RECEIVED_MSG)
        self._state = _load_app_state(asset_id, self)

        # if code is not available in the state file
        if not self._state or not self._state.get("code"):
            return action_result.set_status(phantom.APP_ERROR, status_message=MATTERMOST_TEST_CONNECTIVITY_FAILED_MSG)

        current_code = self._state["code"]
        self.save_state(self._state)
        _save_app_state(self._state, asset_id, self)

        self.save_progress(MATTERMOST_GENERATING_ACCESS_TOKEN_MSG)

        # Generate access_token using code
        request_data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": current_code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        ret_val, response = self._make_rest_call(
            url=MATTERMOST_ACCESS_TOKEN_URL.format(server_url=self._server_url), action_result=action_result, method="post", data=request_data
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # If there is any error while generating access_token, API returns 200 with error and error_description fields
        if not response.get(MATTERMOST_ACCESS_TOKEN):
            if response.get("message"):
                return action_result.set_status(phantom.APP_ERROR, status_message=self._handle_py_ver_compat_for_input_str(response["message"]))

            return action_result.set_status(phantom.APP_ERROR, status_message="Error while generating access_token")

        self._state["token"] = response
        self._access_token = response[MATTERMOST_ACCESS_TOKEN]
        self.save_state(self._state)
        _save_app_state(self._state, asset_id, self)

        self._state = self.load_state()

        # Scenario -
        #
        # If the corresponding state file doesn't have the correct owner, owner group or permissions,
        # the newly generated token is not being saved to the state file
        # and the automatic workflow for the token has been stopped.
        # So we have to check that token from response and the tokens
        # which are saved to state file after successful generation of the new tokens are same or not.

        if self._access_token != self._state.get("token", {}).get(MATTERMOST_ACCESS_TOKEN):
            message = "Error occurred while saving the newly generated access token (in place of the expired token) in the state file."
            message += " Please check the owner, owner group, and the permissions of the state file. The Phantom "
            message += "user should have the correct access rights and ownership for the corresponding state file "
            message += "(refer to the readme file for more information)."
            return action_result.set_status(phantom.APP_ERROR, message)

        return phantom.APP_SUCCESS

    def _get_app_rest_url(self, action_result):
        """Get URL for making rest calls.

        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        URL to make rest calls
        """

        ret_val, phantom_base_url = self._get_phantom_base_url(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        ret_val, asset_name = self._get_asset_name(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        self.save_progress(f"Using Phantom base URL as: {phantom_base_url}")
        app_json = self.get_app_json()
        app_name = app_json["name"]

        app_dir_name = _get_dir_name_from_app_name(app_name)
        url_to_app_rest = "{}/rest/handler/{}_{}/{}".format(phantom_base_url.rstrip("/"), app_dir_name, app_json["appid"], asset_name)
        return phantom.APP_SUCCESS, url_to_app_rest

    def _get_phantom_base_url(self, action_result):
        """Get base url of phantom.

        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        base url of phantom
        """

        mattermost_phantom_base_url = self.get_phantom_base_url()

        url = f"{mattermost_phantom_base_url}rest{MATTERMOST_PHANTOM_SYS_INFO_URL}"
        ret_val, resp_json = self._make_rest_call(action_result=action_result, url=url, verify=False)
        if phantom.is_fail(ret_val):
            return ret_val, None

        phantom_base_url = resp_json.get("base_url")
        if not phantom_base_url:
            return action_result.set_status(phantom.APP_ERROR, status_message=MATTERMOST_BASE_URL_NOT_FOUND_MSG), None
        return phantom.APP_SUCCESS, phantom_base_url

    def _get_asset_name(self, action_result):
        """Get name of the asset using Phantom URL.

        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message), asset name
        """

        mattermost_phantom_base_url = self.get_phantom_base_url()

        asset_id = self.get_asset_id()
        rest_endpoint = MATTERMOST_PHANTOM_ASSET_INFO_URL.format(asset_id=asset_id)
        url = f"{mattermost_phantom_base_url}rest{rest_endpoint}"
        ret_val, resp_json = self._make_rest_call(action_result=action_result, url=url, verify=False)

        if phantom.is_fail(ret_val):
            return ret_val, None

        asset_name = resp_json.get("name")
        if not asset_name:
            return action_result.set_status(phantom.APP_ERROR, status_message=f"Asset Name for id: {asset_id} not found."), None
        return phantom.APP_SUCCESS, asset_name

    def _wait(self, action_result):
        """This function is used to hold the action till user login for 105 seconds.

        :param action_result: Object of ActionResult class
        :return: status (success/failed)
        """

        app_dir = os.path.dirname(os.path.abspath(__file__))
        # file to check whether the request has been granted or not
        auth_status_file_path = f"{app_dir}/{self.get_asset_id()}_{MATTERMOST_TC_FILE}"

        # wait-time while request is being granted for 105 seconds
        for _ in range(0, 35):
            self.send_progress("Waiting...")
            # If file is generated
            if os.path.isfile(auth_status_file_path):
                os.unlink(auth_status_file_path)
                break
            time.sleep(MATTERMOST_TC_STATUS_SLEEP)
        else:
            self.send_progress("")
            return action_result.set_status(phantom.APP_ERROR, status_message="Timeout. Please try again later.")
        self.send_progress("Authenticated")
        return phantom.APP_SUCCESS

    def _validate_date(self, date_timestamp):
        """This function is used to validate date timestamp as per YYYY-MM-DD format or valid ISO 8601 format.

        :param date_timestamp: Value of the date timestamp
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        regex = (
            r"^(-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])T(2[0-3]|[01][0-9]):"
            r"([0-5][0-9]):([0-5][0-9])(\.[0-9]+)?(Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$"
        )
        match_iso8601 = re.compile(regex).match
        try:
            if match_iso8601(date_timestamp) is not None:
                return phantom.APP_SUCCESS
            elif datetime.strptime(date_timestamp, "%Y-%m-%d"):
                return phantom.APP_SUCCESS
        except Exception:
            return phantom.APP_ERROR

        return phantom.APP_ERROR

    def _convert_time(self, time_stamp):
        """This function is used to convert formatted timestamp into millisecond epoch.

        :param time_stamp: formatted timestamp of start_time or end_time
        :return: status success/failure, epoch time in milliseconds
        """

        try:
            epoch = datetime.utcfromtimestamp(0)
            epoch = epoch.replace(tzinfo=dateutil.tz.UTC)
            epoch = epoch.astimezone(dateutil.tz.tzlocal())
            parsed_time = dateutil.parser.parse(time_stamp)

            if not parsed_time.tzinfo:
                parsed_time = parsed_time.replace(tzinfo=dateutil.tz.UTC)

            parsed_time = parsed_time.astimezone(dateutil.tz.tzlocal())
            epoch_time = int((parsed_time - epoch).total_seconds() * 1000)
        except Exception as e:
            self.debug_print("conversion failed")
            return phantom.APP_ERROR, self._get_error_message_from_exception(e)
        return phantom.APP_SUCCESS, epoch_time

    def _verify_time(self, time_value):
        """This function is used to verify time parameters.

        :param time_value: start_time or end_time epoch
        :return: status success/failure with appropriate message
        """

        # Validate time parameter
        try:
            time_value = int(float(time_value))
        except Exception:
            self.debug_print(MATTERMOST_INVALID_TIME)
            return phantom.APP_ERROR, MATTERMOST_INVALID_TIME

        # Validate start_time and end_time for negation
        if time_value < 0:
            self.debug_print(MATTERMOST_NEGATIVE_TIME)
            return phantom.APP_ERROR, MATTERMOST_NEGATIVE_TIME

        return phantom.APP_SUCCESS, MATTERMOST_VALID_TIME

    def _process_posts(self, action_result, url, params, start_time, end_time):
        """This function is used to process posts for a given channel.

        :param action_result: Object of ActionResult class
        :param url: url for making REST call
        :param params: dictionary of query parameters
        :param start_time: start time in epoch
        :param end_time: end time in epoch
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        if not end_time:
            if start_time:
                params.update({"since": start_time})

            # Get posts for given channel
            post_status, post_list = self._get_posts(action_result, url, params)

            if phantom.is_fail(post_status):
                return action_result.get_status()

            if not post_list:
                return action_result.set_status(phantom.APP_SUCCESS, MATTERMOST_NO_POSTS_FOUND)

            for each_post in post_list:
                action_result.add_data(each_post)

        elif not start_time and end_time:
            params.update({"since": end_time})

            # Get posts for given channel
            post_status, post_list = self._get_posts(action_result, url, params)

            if phantom.is_fail(post_status):
                return action_result.get_status()

            params = {}
            if post_list:
                end_time_id = post_list[-1]["id"]
                params.update({"before": end_time_id})

            # Get posts for given channel
            post_status, post_list = self._get_posts(action_result, url, params)

            if phantom.is_fail(post_status):
                return action_result.get_status()

            if not post_list:
                return action_result.set_status(phantom.APP_SUCCESS, MATTERMOST_NO_POSTS_FOUND)

            for each_post in post_list:
                action_result.add_data(each_post)

        elif start_time and end_time:
            params.update({"since": start_time})

            # Get posts for given channel
            post_status, post_list = self._get_posts(action_result, url, params)

            if phantom.is_fail(post_status):
                return action_result.get_status()

            if not post_list:
                return action_result.set_status(phantom.APP_SUCCESS, MATTERMOST_NO_POSTS_FOUND)

            for each_post in reversed(post_list):
                if each_post["create_at"] <= end_time:
                    action_result.add_data(each_post)
                else:
                    break

        return phantom.APP_SUCCESS

    def _get_posts(self, action_result, url, params):
        """This function is used to list posts for a given channel.

        :param action_result: Object of ActionResult class
        :param url: url for making REST call
        :param params: dictionary of query parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR), list of posts
        """

        page_number = 0
        params.update({"page": page_number})

        post_list = []
        while True:
            # make rest call
            ret_val, response_json = self._handle_update_request(url=url, action_result=action_result, params=params)

            if phantom.is_fail(ret_val):
                return action_result.get_status(), post_list

            # If empty list then break
            if not response_json["posts"]:
                break

            # Add post to the post list
            for each_post in response_json["order"]:
                post_list.append(response_json.get("posts", "")[each_post])

            # Increment page_number for fetching next page in upcoming cycle
            if not params.get("since"):
                page_number += 1
                params.update({"page": page_number})
            else:
                break

        return phantom.APP_SUCCESS, post_list

    def _create_post(self, action_result, request_data):
        """This function is used to create post in a channel.

        :param action_result: Object of ActionResult class
        :param request_data: Dictionary of request body
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR), response dict
        """
        # Endpoint for creating post
        url = f"{MATTERMOST_API_BASE_URL.format(server_url=self._server_url)}{MATTERMOST_SEND_MSG_ENDPOINT}"

        # make rest call
        ret_val, response_json = self._handle_update_request(url=url, action_result=action_result, data=json.dumps(request_data), method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, response_json

    def _verify_channel(self, action_result, team_id, channel):
        """This function is used to verify given channel and list channels.

        :param action_result: Object of ActionResult class
        :param team_id: ID of the team
        :param channel: ID or name of the channel
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR), ID of the channel
        """

        channel_id = None

        # Endpoint for fetching channels
        url = f"{MATTERMOST_API_BASE_URL.format(server_url=self._server_url)}{MATTERMOST_LIST_CHANNELS_ENDPOINT.format(team=team_id)}"

        # make rest call
        ret_val, response_json = self._handle_update_request(url=url, action_result=action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        # If an empty list of channels, then return
        if not response_json and not self.get_action_identifier() == "list_channels":
            return phantom.APP_ERROR, MATTERMOST_CONST_NOT_FOUND

        # For any action other than list channel
        if not self.get_action_identifier() == "list_channels":
            # Fetch Channel ID from Channel name
            for each_channel in response_json:
                # Check if either channel name or channel ID matches
                if channel.lower() == each_channel.get("id").lower() or channel.lower() == each_channel.get("name").lower():
                    channel_id = each_channel.get("id")
                    return phantom.APP_SUCCESS, channel_id

        else:
            for each_channel in response_json:
                # Allow public(O) and private(P) channels only
                if each_channel.get("type").lower() in ["o", "p"]:
                    action_result.add_data(each_channel)

        if not channel_id and not self.get_action_identifier() == "list_channels":
            return phantom.APP_ERROR, MATTERMOST_CONST_NOT_FOUND

        return phantom.APP_SUCCESS, channel_id

    def _verify_team(self, action_result, team):
        """This function is used to verify given team and list teams.

        :param action_result: Object of ActionResult class
        :param team: ID or name of the team
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR), ID of the team
        """

        team_id = None
        params = {}
        # Endpoint for fetching teams
        url = f"{MATTERMOST_API_BASE_URL.format(server_url=self._server_url)}{MATTERMOST_TEAMS_ENDPOINT}"

        page_number = 0
        params.update({"page": page_number})

        duplicate_entry = 0
        previous_teams = []
        while True:
            # make rest call
            ret_val, response_json = self._handle_update_request(url=url, action_result=action_result, params=params)

            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            # If an empty list of teams, then break
            if not response_json:
                break

            # For any action other than list teams
            if not self.get_action_identifier() == "list_teams":
                # Fetch Team ID from Team name
                for each_team in response_json:
                    # Check if either team name or team ID matches
                    if team.lower() == each_team.get("id").lower() or team.lower() == each_team.get("name").lower():
                        team_id = each_team.get("id")
                        return phantom.APP_SUCCESS, team_id

            else:
                new_team = []
                if previous_teams:
                    duplicate_entry = len([value for value in response_json if value in previous_teams])
                    new_team = [value for value in response_json if value not in previous_teams]
                previous_teams = response_json
                if not new_team and page_number == 0:
                    for each_team in response_json:
                        action_result.add_data(each_team)
                else:
                    for each_team in new_team:
                        action_result.add_data(each_team)
            # Increment page_number for fetching next page in upcoming cycle
            page_number += 1 + duplicate_entry
            params.update({"page": page_number})

        if not self.get_action_identifier() == "list_teams":
            return phantom.APP_ERROR, MATTERMOST_CONST_NOT_FOUND

        return phantom.APP_SUCCESS, team_id

    def _handle_list_users(self, param):
        """This function is used to handle list users action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        # If neither personal token nor access token are present, action fails
        if not self._personal_token and not self._access_token:
            return action_result.set_status(phantom.APP_ERROR, status_message=MATTERMOST_CONFIG_PARAMS_REQUIRED_MSG)

        team = param.get(MATTERMOST_JSON_TEAM, "")
        params = {}

        if team:
            # Verify valid team name or team ID
            team_status, team_id = self._verify_team(action_result, team)

            if phantom.is_fail(team_status):
                if team_id == MATTERMOST_CONST_NOT_FOUND:
                    return action_result.set_status(phantom.APP_ERROR, MATTERMOST_TEAM_NOT_FOUND_MSG)
                return action_result.get_status()

            params.update({"in_team": team_id})

        # Endpoint for fetching users
        url = f"{MATTERMOST_API_BASE_URL.format(server_url=self._server_url)}{MATTERMOST_USERS_ENDPOINT}"

        page_number = 0
        params.update({"page": page_number})

        while True:
            # make rest call
            ret_val, response_json = self._handle_update_request(url=url, action_result=action_result, params=params)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            # If empty list then break
            if not response_json:
                break

            # Add user to action result data
            for each_user in response_json:
                action_result.add_data(each_user)

            # Increment page_number for fetching next page in upcoming cycle
            page_number += 1
            params.update({"page": page_number})

        summary = action_result.update_summary({})
        summary["total_users"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_vault_info(self, vault_id, action_result):
        vault_meta = None
        # Check for file in vault
        try:
            success, _, vault_meta = ph_rules.vault_info(vault_id=vault_id)  # Vault IDs are unique
            if not success:
                self.debug_print(f"Error while fetching meta information for vault ID: {vault_id}")
                action_result.set_status(phantom.APP_ERROR, f"Error while fetching meta information for vault ID: {vault_id}")
                return None
            vault_meta = list(vault_meta)

        except Exception as e:
            self.debug_print(
                f"Error while fetching meta information for vault ID: {vault_id}. Error Details: {self._get_error_message_from_exception(e)}"
            )
            msg = f"Error while fetching meta information for vault ID: {vault_id}. Error Details: {self._get_error_message_from_exception(e)}"
            action_result.set_status(phantom.APP_ERROR, msg)
            return None

        file_meta = None
        try:
            for meta in vault_meta:
                if meta.get("container_id") == self.get_container_id():
                    file_meta = meta
                    break
            else:
                self.debug_print(f"Unable to find a file for the vault ID: '{vault_id}' in the container ID: '{self.get_container_id()}'")

        except Exception:
            self.debug_print(
                f"Error occurred while finding a file for the vault ID: '{vault_id}' in the container ID: '{self.get_container_id()}'"
            )
            self.debug_print("Considering the first file as the required file")
            file_meta = vault_meta[0]

        if not file_meta:
            self.debug_print(f"Unable to find a file for the vault ID: '{vault_id}' in the container ID: '{self.get_container_id()}'")
            self.debug_print("Considering the first file as the required file")
            file_meta = vault_meta[0]

        return file_meta

    def _handle_upload_file(self, param):
        """This function is used to handle upload file action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        # If neither personal token nor access token are present, action fails
        if not self._personal_token and not self._access_token:
            return action_result.set_status(phantom.APP_ERROR, status_message=MATTERMOST_CONFIG_PARAMS_REQUIRED_MSG)

        team = param[MATTERMOST_JSON_TEAM]
        channel = param[MATTERMOST_JSON_CHANNEL]
        vault_id = self._handle_py_ver_compat_for_input_str(param[MATTERMOST_JSON_VAULT_ID])
        message = param.get(MATTERMOST_JSON_MSG, MATTERMOST_FILE_UPLOAD_MSG)

        file_info = self._get_vault_info(vault_id, action_result)

        if file_info is None:
            return action_result.get_status()

        # Find vault path and info for given vault ID
        try:
            _, _, vault_meta = ph_rules.vault_info(vault_id=vault_id)
            vault_meta = next(iter(vault_meta))
            vault_path = vault_meta.get("path")
            # check if vault path is accessible
            if not vault_path:
                return action_result.set_status(phantom.APP_ERROR, MATTERMOST_VAULT_ID_NOT_FOUND)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, MATTERMOST_VAULT_ID_NOT_FOUND)

        # Verify valid team name or team ID
        team_status, team_id = self._verify_team(action_result, team)

        if phantom.is_fail(team_status):
            if team_id == MATTERMOST_CONST_NOT_FOUND:
                return action_result.set_status(phantom.APP_ERROR, MATTERMOST_TEAM_NOT_FOUND_MSG)
            return action_result.get_status()

        # Verify valid channel name or channel ID
        channel_status, channel_id = self._verify_channel(action_result, team_id, channel)

        if phantom.is_fail(channel_status):
            if channel_id == MATTERMOST_CONST_NOT_FOUND:
                return action_result.set_status(phantom.APP_ERROR, MATTERMOST_CHANNEL_NOT_FOUND_MSG)
            return action_result.get_status()

        file_name = self._handle_py_ver_compat_for_input_str(file_info["name"])

        content = None

        with open(vault_path, "rb") as fin:
            # Set file to be uploaded
            content = fin.read()

        # Recreate field form binary file
        worker_dir = self.get_state_dir()
        file_path = f"{worker_dir}/{file_name}"
        try:
            with open(file_path, "wb") as fout:
                fout.write(content)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, self._get_error_message_from_exception(e))

        # Set channel ID for uploading file
        data = {"channel_id": channel_id}

        # Endpoint for uploading file
        file_url = f"{MATTERMOST_API_BASE_URL.format(server_url=self._server_url)}{MATTERMOST_FILES_ENDPOINT}"

        with open(file_path, "rb") as f:
            # Set file to be uploaded
            files = {"files": f}

            # make rest call
            file_ret_val, file_response_json = self._handle_update_request(
                url=file_url, action_result=action_result, data=data, method="post", files=files
            )

        # Remove the file
        os.remove(file_path)

        if phantom.is_fail(file_ret_val):
            return action_result.get_status()

        if not file_response_json.get("file_infos", []):
            return action_result.set_status(phantom.APP_ERROR, MATTERMOST_FILE_UPLOAD_FAILED)

        file_ids = []

        for _file in file_response_json["file_infos"]:
            file_ids.append(_file["id"])

        request_data = {"channel_id": channel_id, "message": message, "file_ids": file_ids}

        # make rest call
        ret_val, response_json = self._create_post(action_result, request_data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response_json)

        return action_result.set_status(phantom.APP_SUCCESS, MATTERMOST_FILE_UPLOAD_SUCCESS)

    def _handle_send_message(self, param):
        """This function is used to handle send message action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        # If neither personal token nor access token are present, action fails
        if not self._personal_token and not self._access_token:
            return action_result.set_status(phantom.APP_ERROR, status_message=MATTERMOST_CONFIG_PARAMS_REQUIRED_MSG)

        team = param[MATTERMOST_JSON_TEAM]
        channel = param[MATTERMOST_JSON_CHANNEL]
        message = param[MATTERMOST_JSON_MSG]

        # Verify valid team name or team ID
        team_status, team_id = self._verify_team(action_result, team)

        if phantom.is_fail(team_status):
            if team_id == MATTERMOST_CONST_NOT_FOUND:
                return action_result.set_status(phantom.APP_ERROR, MATTERMOST_TEAM_NOT_FOUND_MSG)
            return action_result.get_status()

        # Verify valid channel name or channel ID
        channel_status, channel_id = self._verify_channel(action_result, team_id, channel)

        if phantom.is_fail(channel_status):
            if channel_id == MATTERMOST_CONST_NOT_FOUND:
                return action_result.set_status(phantom.APP_ERROR, MATTERMOST_CHANNEL_NOT_FOUND_MSG)
            return action_result.get_status()

        request_data = {"channel_id": channel_id, "message": message}

        # make rest call
        ret_val, response_json = self._create_post(action_result, request_data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response_json)

        return action_result.set_status(phantom.APP_SUCCESS, MATTERMOST_SEND_MSG_SUCCESS)

    def _handle_list_posts(self, param):
        """This function is used to handle list posts action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        # If neither personal token nor access token are present, action fails
        if not self._personal_token and not self._access_token:
            return action_result.set_status(phantom.APP_ERROR, status_message=MATTERMOST_CONFIG_PARAMS_REQUIRED_MSG)

        team = param[MATTERMOST_JSON_TEAM]
        channel = param[MATTERMOST_JSON_CHANNEL]
        start_time = param.get(MATTERMOST_JSON_START_TIME, None)
        end_time = param.get(MATTERMOST_JSON_END_TIME, None)
        params = {}

        if start_time or end_time:
            if start_time and end_time:
                date_status = self._validate_date(start_time)
                if not date_status:
                    return action_result.set_status(phantom.APP_ERROR, MATTERMOST_TIMESTAMP_VALIDATION_FAILED_MSG)

                # convert start_time
                convert_status, start_time = self._convert_time(start_time)

                if phantom.is_fail(convert_status):
                    msg = f"{MATTERMOST_TIMESTAMP_CONVERSION_FAILED_MSG}. Error Details: {start_time}"
                    return action_result.set_status(phantom.APP_ERROR, msg)

                # verify start_time
                time_status, time_response = self._verify_time(start_time)

                if phantom.is_fail(time_status):
                    return action_result.set_status(phantom.APP_ERROR, time_response)

                date_status = self._validate_date(end_time)
                if not date_status:
                    return action_result.set_status(phantom.APP_ERROR, MATTERMOST_TIMESTAMP_VALIDATION_FAILED_MSG)

                # convert end_time
                convert_status, end_time = self._convert_time(end_time)

                if phantom.is_fail(convert_status):
                    msg = f"{MATTERMOST_TIMESTAMP_CONVERSION_FAILED_MSG}. Error Details: {end_time}"
                    return action_result.set_status(phantom.APP_ERROR, msg)

                # verify end_time
                time_status, time_response = self._verify_time(end_time)

                if phantom.is_fail(time_status):
                    return action_result.set_status(phantom.APP_ERROR, time_response)

                # Compare value of start_time and end_time
                if int(start_time) >= int(end_time):
                    self.debug_print(MATTERMOST_INVALID_TIME_RANGE)
                    return action_result.set_status(phantom.APP_ERROR, MATTERMOST_INVALID_TIME_RANGE)

            elif start_time:
                date_status = self._validate_date(start_time)
                if not date_status:
                    return action_result.set_status(phantom.APP_ERROR, MATTERMOST_TIMESTAMP_VALIDATION_FAILED_MSG)

                # convert start_time
                convert_status, start_time = self._convert_time(start_time)

                if phantom.is_fail(convert_status):
                    msg = f"{MATTERMOST_TIMESTAMP_CONVERSION_FAILED_MSG}. Error Details: {start_time}"
                    return action_result.set_status(phantom.APP_ERROR, msg)

                # verify start_time
                time_status, time_response = self._verify_time(start_time)

                if phantom.is_fail(time_status):
                    return action_result.set_status(phantom.APP_ERROR, time_response)

            elif end_time:
                date_status = self._validate_date(end_time)
                if not date_status:
                    return action_result.set_status(phantom.APP_ERROR, MATTERMOST_TIMESTAMP_VALIDATION_FAILED_MSG)

                # convert end_time
                convert_status, end_time = self._convert_time(end_time)

                if phantom.is_fail(convert_status):
                    msg = f"{MATTERMOST_TIMESTAMP_CONVERSION_FAILED_MSG}. Error Details: {end_time}"
                    return action_result.set_status(phantom.APP_ERROR, msg)

                # verify end_time
                time_status, time_response = self._verify_time(end_time)

                if phantom.is_fail(time_status):
                    return action_result.set_status(phantom.APP_ERROR, time_response)

        # Verify valid team name or team ID
        team_status, team_id = self._verify_team(action_result, team)

        if phantom.is_fail(team_status):
            if team_id == MATTERMOST_CONST_NOT_FOUND:
                return action_result.set_status(phantom.APP_ERROR, MATTERMOST_TEAM_NOT_FOUND_MSG)
            return action_result.get_status()

        # Verify valid channel name or channel ID
        channel_status, channel_id = self._verify_channel(action_result, team_id, channel)

        if phantom.is_fail(channel_status):
            if channel_id == MATTERMOST_CONST_NOT_FOUND:
                return action_result.set_status(phantom.APP_ERROR, MATTERMOST_CHANNEL_NOT_FOUND_MSG)
            return action_result.get_status()

        # Endpoint for fetching posts
        url = f"{MATTERMOST_API_BASE_URL.format(server_url=self._server_url)}{MATTERMOST_LIST_POSTS_ENDPOINT.format(channel=channel_id)}"

        # Get posts for given channel
        post_status = self._process_posts(action_result, url, params, start_time, end_time)

        if phantom.is_fail(post_status):
            return action_result.get_status()

        summary = action_result.update_summary({})
        summary["total_posts"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_channels(self, param):
        """This function is used to handle list channels action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        # If neither personal token nor access token are present, action fails
        if not self._personal_token and not self._access_token:
            return action_result.set_status(phantom.APP_ERROR, status_message=MATTERMOST_CONFIG_PARAMS_REQUIRED_MSG)

        team = param[MATTERMOST_JSON_TEAM]

        # Verify valid team name or team ID
        team_status, team_id = self._verify_team(action_result, team)

        if phantom.is_fail(team_status):
            if team_id == MATTERMOST_CONST_NOT_FOUND:
                return action_result.set_status(phantom.APP_ERROR, MATTERMOST_TEAM_NOT_FOUND_MSG)
            return action_result.get_status()

        # Fetch list of all channels
        ret_val, _ = self._verify_channel(action_result, team_id, "all")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        summary = action_result.update_summary({})
        summary["total_channels"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_teams(self, param):
        """This function is used to handle list teams action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        # If neither personal token nor access token are present, action fails
        if not self._personal_token and not self._access_token:
            return action_result.set_status(phantom.APP_ERROR, status_message=MATTERMOST_CONFIG_PARAMS_REQUIRED_MSG)

        # Fetch list of all teams
        ret_val, _ = self._verify_team(action_result, "all")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        summary = action_result.update_summary({})
        summary["total_teams"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        """This function gets current action identifier and calls member function of its own to handle the action.

        :param param: dictionary which contains information about the actions to be executed
        :return: status(success/failure)
        """
        self.debug_print("action_id", self.get_action_identifier())

        action_mapping = {
            "test_connectivity": self._handle_test_connectivity,
            "list_users": self._handle_list_users,
            "upload_file": self._handle_upload_file,
            "send_message": self._handle_send_message,
            "list_posts": self._handle_list_posts,
            "list_channels": self._handle_list_channels,
            "list_teams": self._handle_list_teams,
        }

        action = self.get_action_identifier()
        action_execution_status = phantom.APP_SUCCESS

        if action in list(action_mapping.keys()):
            action_function = action_mapping[action]
            action_execution_status = action_function(param)

        return action_execution_status

    def initialize(self):
        """This is an optional function that can be implemented by the AppConnector derived class. Since the
        configuration dictionary is already validated by the time this function is called, it's a good place to do any
        extra initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS.
        """

        self._state = self.load_state()
        config = self.get_config()

        # Fetching the Python major version
        try:
            self._python_version = int(sys.version_info[0])
        except Exception:
            return self.set_status(phantom.APP_ERROR, "Error occurred while getting the Phantom server's Python major version.")

        self._server_url = self._handle_py_ver_compat_for_input_str(config[MATTERMOST_CONFIG_SERVER_URL].strip("/"))
        self._verify_server_cert = config.get(MATTERMOST_CONFIG_VERIFY_SERVER_CERT, False)
        self._personal_token = config.get(MATTERMOST_CONFIG_PERSONAL_TOKEN)
        self._client_id = self._handle_py_ver_compat_for_input_str(config.get(MATTERMOST_CONFIG_CLIENT_ID))
        self._client_secret = config.get(MATTERMOST_CONFIG_CLIENT_SECRET)

        self._access_token = self._state.get("token", {}).get(MATTERMOST_ACCESS_TOKEN, "")
        return phantom.APP_SUCCESS

    def finalize(self):
        """This function gets called once all the param dictionary elements are looped over and no more handle_action
        calls are left to be made. It gives the AppConnector a chance to loop through all the results that were
        accumulated by multiple handle_action function calls and create any summary if required. Another usage is
        cleanup, disconnect from remote devices etc.

        :return: status (success/failure)
        """

        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        _save_app_state(self._state, self.get_asset_id(), self)
        return phantom.APP_SUCCESS


if __name__ == "__main__":
    import argparse

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
            print("Accessing the Login page")
            login_url = BaseConnector._get_phantom_base_url() + "login"
            r = requests.get(login_url, verify=verify, timeout=60)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = f"csrftoken={csrftoken}"
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, data=data, headers=headers, verify=verify, timeout=60)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print(f"Unable to get session id from the platform. Error: {e!s}")
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = MattermostConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
