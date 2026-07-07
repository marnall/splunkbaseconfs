# File: microsoftintune_connector.py
#
# Copyright (c) Splunk, 2023-2025
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

# Phantom App imports
import grp
import json
import os
import pathlib
import pwd
import sys
import time
import urllib.parse as urlparse

import encryption_helper
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from django.http import HttpResponse
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from microsoftintune_consts import *


MAX_END_OFFSET_VAL = 2147483646


def _handle_login_redirect(request, key):
    """This function is used to redirect login request to microsoft login page.

    :param request: Data given to REST endpoint
    :param key: Key to search in state file
    :return: response authorization_url/admin_consent_url
    """

    asset_id = request.GET.get("asset_id")
    if not asset_id:
        return HttpResponse(
            "ERROR: Asset ID not found in URL",
            content_type="text/plain",
            status=MS_AZURE_BAD_REQUEST_CODE,
        )
    state = _load_app_state(asset_id)
    if not state:
        return HttpResponse(
            "ERROR: Invalid asset_id",
            content_type="text/plain",
            status=MS_AZURE_BAD_REQUEST_CODE,
        )
    url = state.get(key)
    if not url:
        return HttpResponse(
            f"App state is invalid, {key} not found.",
            content_type="text/plain",
            status=MS_AZURE_BAD_REQUEST_CODE,
        )
    response = HttpResponse(status=302)
    response["Location"] = url
    return response


def _is_valid_asset_id(asset_id):
    """This function validates an asset id.
    Must be an alphanumeric string of less than 128 characters.

    :param asset_id: asset_id
    :return: is_valid: Boolean True if valid, False if not.
    """
    if not isinstance(asset_id, str):
        return False
    if not asset_id.isalnum():
        return False
    if len(asset_id) > 128:
        return False
    return True


def _get_file_path(asset_id, is_state_file=True):
    """This function gets the path of the auth status file of an asset id.

    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :param is_state_file: boolean parameter for state file
    :return: file_path: Path object of the file
    """
    current_file_path = pathlib.Path(__file__).resolve()
    if is_state_file:
        input_file = f"{asset_id}_state.json"
    else:
        input_file = f"{asset_id}_oauth_task.out"
    output_file_path = current_file_path.with_name(input_file)
    return output_file_path


def _decrypt_state(state, salt):
    """
    Decrypts the state.
    :param state: state dictionary
    :param salt: salt used for decryption
    :return: decrypted state
    """

    if not state.get("is_encrypted"):
        return state

    access_token = state.get("token", {}).get("access_token")
    if access_token:
        state["token"]["access_token"] = encryption_helper.decrypt(access_token, salt)

    refresh_token = state.get("token", {}).get("refresh_token")
    if refresh_token:
        state["token"]["refresh_token"] = encryption_helper.decrypt(refresh_token, salt)

    code = state.get("code")
    if code:
        state["code"] = encryption_helper.decrypt(code, salt)

    return state


def _encrypt_state(state, salt):
    """
    Encrypts the state.
    :param state: state dictionary
    :param salt: salt used for encryption
    :return: encrypted state
    """

    access_token = state.get("token", {}).get("access_token")
    if access_token:
        state["token"]["access_token"] = encryption_helper.encrypt(access_token, salt)

    refresh_token = state.get("token", {}).get("refresh_token")
    if refresh_token:
        state["token"]["refresh_token"] = encryption_helper.encrypt(refresh_token, salt)

    code = state.get("code")
    if code:
        state["code"] = encryption_helper.encrypt(code, salt)

    state["is_encrypted"] = True

    return state


def _load_app_state(asset_id, app_connector=None):
    """This function is used to load the current state file.

    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :return: state: Current state file as a dictionary
    """

    asset_id = str(asset_id)
    if not _is_valid_asset_id(asset_id):
        if app_connector:
            app_connector.debug_print("In _load_app_state: Invalid asset_id")
        return {}

    state_file_path = _get_file_path(asset_id)

    state = {}
    try:
        with open(state_file_path) as state_file:
            state = json.load(state_file)
    except Exception as e:
        if app_connector:
            app_connector.error_print(f"In _load_app_state: Exception: {e!s}")

    if app_connector:
        app_connector.debug_print("Loaded state: ", state)

    try:
        state = _decrypt_state(state, asset_id)
    except Exception as e:
        if app_connector:
            app_connector.error_print(f"{MS_AZURE_DECRYPTION_ERROR}: {e!s}")
        state = {}

    return state


def _save_app_state(state, asset_id, app_connector):
    """This function is used to save current state in file.

    :param state: Dictionary which contains data to write in state file
    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :return: status: phantom.APP_SUCCESS
    """
    asset_id = str(asset_id)
    if not _is_valid_asset_id(asset_id):
        if app_connector:
            app_connector.debug_print("In _save_app_state: Invalid asset_id")
        return {}

    state_file_path = _get_file_path(asset_id)

    try:
        state = _encrypt_state(state, asset_id)
    except Exception as e:
        if app_connector:
            app_connector.error_print(f"{MS_AZURE_ENCRYPTION_ERROR}: {e!s}")
        return phantom.APP_ERROR

    if app_connector:
        app_connector.debug_print("Saving state: ", state)

    try:
        with open(state_file_path, "w+") as state_file:
            json.dump(state, state_file)
    except Exception as e:
        if app_connector:
            app_connector.error_print(f"Unable to save state file: {e!s}")

    return phantom.APP_SUCCESS


def _handle_login_response(request):
    """This function is used to get the login response of authorization request from microsoft login page.

    :param request: Data given to REST endpoint
    :return: HttpResponse. The response displayed on authorization URL page
    """

    asset_id = request.GET.get("state")
    if not asset_id:
        return HttpResponse(
            f"ERROR: Asset ID not found in URL\n{json.dumps(request.GET)}",
            content_type="text/plain",
            status=MS_AZURE_BAD_REQUEST_CODE,
        )

    # Check for error in URL
    error = request.GET.get("error")
    error_description = request.GET.get("error_description")

    # If there is an error in response
    if error:
        message = f"Error: {error}"
        if error_description:
            message = f"{message} Details: {error_description}"
        return HttpResponse(
            f"Server returned {message}",
            content_type="text/plain",
            status=MS_AZURE_BAD_REQUEST_CODE,
        )

    code = request.GET.get("code")
    admin_consent = request.GET.get("admin_consent")

    # If none of the code or admin_consent is available
    if not (code or admin_consent):
        return HttpResponse(
            f"Error while authenticating\n{json.dumps(request.GET)}",
            content_type="text/plain",
            status=MS_AZURE_BAD_REQUEST_CODE,
        )

    state = _load_app_state(asset_id)

    # If value of admin_consent is available
    if admin_consent:
        if admin_consent == "True":
            admin_consent = True
        else:
            admin_consent = False

        state["admin_consent"] = admin_consent
        _save_app_state(state, asset_id, None)

        # If admin_consent is True
        if admin_consent:
            return HttpResponse(
                "Admin Consent received. Please close this window.",
                content_type="text/plain",
            )
        return HttpResponse(
            "Admin Consent declined. Please close this window and try again later.",
            content_type="text/plain",
            status=MS_AZURE_BAD_REQUEST_CODE,
        )

    # If value of admin_consent is not available, value of code is available
    state["code"] = code
    _save_app_state(state, asset_id, None)

    return HttpResponse(
        "Code received. Please close this window, the action will continue to get new token.",
        content_type="text/plain",
    )


def _handle_rest_request(request, path_parts):
    """Handle requests for authorization.

    :param request: Data given to REST endpoint
    :param path_parts: parts of the URL passed
    :return: dictionary containing response parameters
    """

    if len(path_parts) < 2:
        return HttpResponse(
            "error: True, message: Invalid REST endpoint request",
            content_type="text/plain",
            status=MS_AZURE_BAD_REQUEST_CODE,
        )

    call_type = path_parts[1]

    # To handle authorize request in test connectivity action
    if call_type == "start_oauth":
        return _handle_login_redirect(request, "admin_consent_url")

    # To handle response from microsoft login page
    if call_type == "result":
        return_val = _handle_login_response(request)
        asset_id = request.GET.get("state")
        if asset_id:
            if not _is_valid_asset_id(asset_id):
                return HttpResponse(
                    "Error: Invalid asset_id",
                    content_type="text/plain",
                    status=MS_AZURE_BAD_REQUEST_CODE,
                )
            auth_status_file_path = _get_file_path(asset_id, is_state_file=False)
            auth_status_file_path.touch(mode=664, exist_ok=True)
            try:
                uid = pwd.getpwnam("apache").pw_uid
                gid = grp.getgrnam("phantom").gr_gid
                os.chown(auth_status_file_path, uid, gid)  # nosemgrep file traversal risk is handled by blocking non-alphanum strings
            except Exception:
                pass

        return return_val
    return HttpResponse(
        "error: Invalid endpoint",
        content_type="text/plain",
        status=MS_AZURE_NOT_FOUND_CODE,
    )


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
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class MicrosoftIntuneConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None
        self._tenant = None
        self._client_id = None
        self._client_secret = None
        self._access_token = None
        self._refresh_token = None
        self._base_url = None
        self._admin_access_required = None
        self._admin_access_granted = None

    def load_state(self):
        """
        Load the contents of the state file to the state dictionary and decrypt it.
        :return: loaded state
        """
        state = super().load_state()
        if not isinstance(state, dict):
            self.debug_print("Reseting the state file with the default format")
            state = {"app_version": self.get_app_json().get("app_version")}
            return state
        try:
            state = _decrypt_state(state, self.get_asset_id())
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.error_print(f"{MS_AZURE_DECRYPTION_ERROR}: {error_message}")
            state = None

        return state

    def save_state(self, state):
        """
        Encrypt and save the current state dictionary to the the state file.
        :param state: state dictionary
        :return: status
        """
        try:
            state = _encrypt_state(state, self.get_asset_id())
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.error_print(f"{MS_AZURE_ENCRYPTION_ERROR}: {error_message}")
            return phantom.APP_ERROR

        return super().save_state(state)

    def _dump_error_log(self, error, message="Exception occurred."):
        self.error_print(message, dump_object=error)

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_message = MS_AZURE_ERROR_MESSAGE_UNKNOWN

        self._dump_error_log(e)

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

    def _process_empty_response(self, response, action_result):
        """This function is used to process empty response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        if response.status_code == 200 or response.status_code == 202:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"),
            None,
        )

    def _process_html_response(self, response, action_result):
        """This function is used to process html response.

        :param response: response data
        :param action_result: object of Action Result
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
        except:
            error_text = "Cannot parse error details"

        message = MS_AZURE_RESPONSE_ERROR_MESSAGE.format(status_code=status_code, error_text=error_text)

        message = message.replace("{", "{{").replace("}", "}}")

        if status_code == MS_AZURE_BAD_REQUEST_CODE:
            message = MS_AZURE_RESPONSE_ERROR_MESSAGE.format(status_code=status_code, error_text=MS_AZURE_HTML_ERROR)

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, response, action_result):
        """This function is used to process json response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # Try a json parse
        try:
            resp_json = response.json()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Unable to parse JSON response. Error: {error_message}",
                ),
                None,
            )

        # Please specify the status codes here
        if 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        error_message = response.text.replace("{", "{{").replace("}", "}}")
        message = MS_AZURE_RESPONSE_ERROR_MESSAGE.format(status_code=response.status_code, error_text=error_message)

        # Show only error message if available
        if isinstance(resp_json.get("error", {}), dict):
            if resp_json.get("error", {}).get("message"):
                error_message = resp_json["error"]["message"]
                message = MS_AZURE_RESPONSE_ERROR_MESSAGE.format(status_code=response.status_code, error_text=error_message)
        else:
            error_message = resp_json["error"]
            message = MS_AZURE_RESPONSE_ERROR_MESSAGE.format(status_code=response.status_code, error_text=error_message)

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, response, action_result):
        """This function is used to process html response.

        :param response: response data
        :param action_result: object of Action Result
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

        if "text/javascript" in response.headers.get("Content-Type", ""):
            return self._process_json_response(response, action_result)

        # Process an HTML response, Do this no matter what the API talks.
        # There is a high chance of a PROXY in between SOAR and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in response.headers.get("Content-Type", ""):
            return self._process_html_response(response, action_result)

        # Reset_password returns empty body
        if not response.text and 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, {})

        # it's not content-type that is to be parsed, handle an empty response
        if not response.text:
            return self._process_empty_response(response, action_result)

        # everything else is actually an error at this point
        response_content = response.text.replace("{", "{{").replace("}", "}}")
        message = MS_AZURE_PROCESS_RESPONSE_ERROR_MESSAGE.format(status_code=response.status_code, content=response_content)

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _get_asset_name(self, action_result):
        """Get name of the asset using SOAR URL.

        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message), asset name
        """

        url = urlparse.urljoin(self.get_phantom_base_url(), f"rest/asset/{self._asset_id}")
        ret_val, resp_json = self._make_rest_call(action_result=action_result, endpoint=url, verify=False)  # nosemgrep

        if phantom.is_fail(ret_val):
            return ret_val, None

        asset_name = resp_json.get("name")
        if not asset_name:
            return (
                action_result.set_status(phantom.APP_ERROR, f"Asset Name for id: {self._asset_id} not found."),
                None,
            )
        return phantom.APP_SUCCESS, asset_name

    def _get_external_phantom_base_url(self, action_result):
        """Get base url of SOAR.

        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        base url of SOAR
        """

        url = urlparse.urljoin(self.get_phantom_base_url(), "rest/system_info")
        ret_val, resp_json = self._make_rest_call(action_result=action_result, endpoint=url, verify=False)  # nosemgrep
        if phantom.is_fail(ret_val):
            return ret_val, None

        phantom_base_url = resp_json.get("base_url").rstrip("/")
        if not phantom_base_url:
            return (
                action_result.set_status(phantom.APP_ERROR, MS_AZURE_BASE_URL_NOT_FOUND_MESSAGE),
                None,
            )
        return phantom.APP_SUCCESS, phantom_base_url

    def _get_app_rest_url(self, action_result):
        """Get URL for making rest calls.

        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        URL to make rest calls
        """

        ret_val, phantom_base_url = self._get_external_phantom_base_url(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        ret_val, asset_name = self._get_asset_name(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        self.save_progress(f"Using SOAR base URL: {phantom_base_url}")
        app_json = self.get_app_json()
        app_id = app_json["appid"]
        app_name = app_json["name"]

        app_dir_name = _get_dir_name_from_app_name(app_name)
        url_to_app_rest = f"{phantom_base_url}/rest/handler/{app_dir_name}_{app_id}/{asset_name}"
        return phantom.APP_SUCCESS, url_to_app_rest

    def _make_rest_call(
        self,
        endpoint,
        action_result,
        verify=True,
        headers=None,
        params=None,
        data=None,
        json=None,
        method="get",
    ):
        """Function that makes the REST call to the app.

        :param endpoint: REST endpoint that needs to appended to the service address
        :param action_result: object of ActionResult class
        :param headers: request headers
        :param params: request parameters
        :param data: request body
        :param json: JSON object
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :param verify: verify server certificate (Default True)
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"),
                resp_json,
            )

        try:
            r = request_func(
                endpoint,
                json=json,
                data=data,
                headers=headers,
                verify=verify,
                params=params,
                timeout=DEFAULT_TIMEOUT,
            )
        except Exception as e:
            error_message = f"Error connecting to server. Details: {self._get_error_message_from_exception(e)}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), r)

        return self._process_response(r, action_result)

    def _make_rest_call_helper(
        self,
        action_result,
        endpoint,
        verify=True,
        headers=None,
        params=None,
        data=None,
        json=None,
        method="get",
    ):
        """Function that helps setting REST call to the app.

        :param endpoint: REST endpoint that needs to appended to the service address
        :param action_result: object of ActionResult class
        :param headers: request headers
        :param params: request parameters
        :param data: request body
        :param json: JSON object
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :param verify: verify server certificate (Default True)
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        url = f"{self._base_url}{endpoint}"
        if headers is None:
            headers = {}

        token = self._state.get(MS_AZURE_TOKEN_STRING, {})
        if not token.get(MS_AZURE_ACCESS_TOKEN_STRING):
            ret_val = self._get_token(action_result)

            if phantom.is_fail(ret_val):
                return RetVal(action_result.get_status(), None)
        headers.update(
            {
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        ret_val, resp_json = self._make_rest_call(url, action_result, verify, headers, params, data, json, method)

        # If token is expired, generate a new token
        msg = action_result.get_message()
        if msg and any(failure_message in msg for failure_message in AUTH_FAILURE_MESSAGES):
            self.save_progress("Token is invalid/expired. Hence, generating a new token.")
            ret_val = self._get_token(action_result)
            if phantom.is_fail(ret_val):
                return RetVal(ret_val, None)

            headers.update({"Authorization": f"Bearer {self._access_token}"})

            ret_val, resp_json = self._make_rest_call(url, action_result, verify, headers, params, data, json, method)

        if phantom.is_fail(ret_val):
            return RetVal(ret_val, resp_json)

        return RetVal(phantom.APP_SUCCESS, resp_json)

    def _handle_test_connectivity(self, param):
        """Function that handles the test connectivity action, it is much simpler than other action handlers."""

        # Progress
        # self.save_progress("Generating Authentication URL")
        app_state = {}
        action_result = self.add_action_result(ActionResult(param))

        if not (self._admin_access_required and self._admin_access_granted):
            self.save_progress("Getting App REST endpoint URL")
            # Get the URL to the app's REST Endpoint, this is the url that the TC dialog
            # box will ask the user to connect to
            ret_val, app_rest_url = self._get_app_rest_url(action_result)

            if phantom.is_fail(ret_val):
                self.save_progress(MS_REST_URL_NOT_AVAILABLE_MESSAGE.format(error=self.get_status()))
                return self.set_status(phantom.APP_ERROR)

            # create the url that the oauth server should re-direct to after the auth is completed
            # (success and failure), this is added to the state so that the request handler will access
            # it later on
            redirect_uri = f"{app_rest_url}/result"
            app_state["redirect_uri"] = redirect_uri

            self.save_progress("-" * 175)
            self.save_progress(MS_OAUTH_URL_MESSAGE)
            self.save_progress(redirect_uri)

            self._client_id = urlparse.quote(self._client_id)
            self._tenant = urlparse.quote(self._tenant)

            query_params = {
                "client_id": self._client_id,
                "redirect_uri": redirect_uri,
                "state": self._asset_id,
            }

            if self._admin_access_required:
                # Create the url for fetching administrator consent
                admin_consent_url_base = MS_AZURE_ADMIN_CONSENT_URL.format(tenant_id=self._tenant)
            else:
                # Create the url authorization, this is the one pointing to the oauth server side
                admin_consent_url_base = MS_AZURE_AUTHORIZE_URL.format(tenant_id=self._tenant)
                query_params["scope"] = MS_AZURE_CODE_GENERATION_SCOPE
                query_params["response_type"] = "code"

            query_string = "&".join(f"{key}={value}" for key, value in query_params.items())

            admin_consent_url = f"{admin_consent_url_base}?{query_string}"

            app_state["admin_consent_url"] = admin_consent_url

            # The URL that the user should open in a different tab.
            # This is pointing to a REST endpoint that points to the app
            url_to_show = f"{app_rest_url}/start_oauth?asset_id={self._asset_id}&"

            # Save the state, will be used by the request handler
            _save_app_state(app_state, self._asset_id, self)

            self.save_progress("-" * 175)
            self.save_progress("Please connect to the following URL from a different tab to continue the connectivity process")
            self.save_progress(" ")
            self.save_progress(url_to_show)
            self.save_progress("-" * 175)
            self.save_progress(MS_AZURE_AUTHORIZE_TROUBLESHOOT_MESSAGE)
            self.save_progress("-" * 175)
            time.sleep(MS_AZURE_WAIT_FOR_URL_SLEEP)

            completed = False
            if not _is_valid_asset_id(self._asset_id):
                return action_result.set_status(phantom.APP_ERROR, "Invalid asset id")

            auth_status_file_path = _get_file_path(self._asset_id, is_state_file=False)
            self.save_progress("\nWaiting for authorization to complete...")

            for i in range(0, 40):
                if auth_status_file_path.is_file():
                    completed = True
                    auth_status_file_path.unlink()
                    break

                time.sleep(MS_TC_STATUS_SLEEP)

            if not completed:
                self.save_progress("Authentication process does not seem to be completed. Timing out")
                self.save_progress(MS_AZURE_TEST_CONNECTIVITY_FAILURE_MESSAGE)
                return self.set_status(phantom.APP_ERROR)

            self.send_progress("")

            # Load the state again, since the http request handlers would have saved the result of the admin consent
            self._state = _load_app_state(self._asset_id, self)
            if not self._state:
                self.save_progress(MS_STATE_FILE_ERROR_MESSAGE)
                self.save_progress(MS_AZURE_TEST_CONNECTIVITY_FAILURE_MESSAGE)
                return action_result.set_status(phantom.APP_ERROR)

            self._state.setdefault("admin_consent", False)

            if self._admin_access_required and not self._state.get("admin_consent"):
                self.save_progress(MS_ADMIN_CONSENT_ERROR_MESSAGE)
                self.save_progress(MS_AZURE_TEST_CONNECTIVITY_FAILURE_MESSAGE)
                return action_result.set_status(phantom.APP_ERROR)

            if not self._admin_access_required and not self._state.get("code"):
                self.save_progress(MS_AUTHORIZATION_ERROR_MESSAGE)
                self.save_progress(MS_AZURE_TEST_CONNECTIVITY_FAILURE_MESSAGE)
                return action_result.set_status(phantom.APP_ERROR)

            if self._admin_access_required:
                self.save_progress("Admin consent received")
                self.save_progress(
                    "Waiting for 30 seconds before generating token. If action fails with '403: AccessDenied' error, "
                    "please check permissions and re-run the 'test connectivity' after some time."
                )
                self.save_progress(
                    "Admin consent is already received. You can mark 'Admin Consent Already Provided' to True, "
                    "unless you make changes in the permissions."
                )
                time.sleep(30)

        self.save_progress(MS_GENERATING_ACCESS_TOKEN_MESSAGE)
        ret_val = self._get_token(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress("Getting managed devices")
        params = {"$top": "1"}
        ret_val, response = self._make_rest_call_helper(action_result, "/deviceManagement/managedDevices", params=params)

        if phantom.is_fail(ret_val):
            self.save_progress("API to get users failed")
            self.save_progress(MS_AZURE_TEST_CONNECTIVITY_FAILURE_MESSAGE)
            return self.set_status(phantom.APP_ERROR)

        value = response.get("value")

        if value:
            self.save_progress("Got device info")

        self.save_progress(MS_AZURE_TEST_CONNECTIVITY_PASSED)

        return self.set_status(phantom.APP_SUCCESS)

    def _get_token(self, action_result):
        """This function is used to get a token via REST Call.

        :param action_result: Object of action result
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }

        req_url = SERVER_TOKEN_URL.format(self._tenant)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        if not self._admin_access_required:
            data["scope"] = MS_AZURE_CODE_GENERATION_SCOPE
            data["redirect_uri"] = self._state.get("redirect_uri")
            auth_code = self._state.get("code", None)
            if self._state.get(MS_AZURE_TOKEN_STRING, {}).get(MS_AZURE_REFRESH_TOKEN_STRING, None):
                data["refresh_token"] = self._refresh_token
                data["grant_type"] = "refresh_token"
            elif auth_code:
                data["code"] = auth_code
                data["grant_type"] = "authorization_code"
            else:
                return action_result.set_status(
                    phantom.APP_ERROR,
                    "Unexpected details retrieved from the state file.",
                )
        else:
            data["scope"] = "https://graph.microsoft.com/.default"
            data["grant_type"] = "client_credentials"

        ret_val, resp_json = self._make_rest_call(req_url, action_result, headers=headers, data=data, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if self._admin_access_required and self._admin_access_granted:
            self._state["admin_consent"] = True

        self._state[MS_AZURE_TOKEN_STRING] = resp_json
        self._access_token = resp_json.get(MS_AZURE_ACCESS_TOKEN_STRING, None)
        self._refresh_token = resp_json.get(MS_AZURE_REFRESH_TOKEN_STRING, None)

        return phantom.APP_SUCCESS

    def _handle_pagination(self, action_result, endpoint, headers=None, params=None):
        """
        This action is used to create an iterator that will paginate through responses from called methods.

        :param action_result: Object of ActionResult class
        :param endpoint: REST endpoint that needs to appended to the service address
        :param headers: Dictionary of headers for the rest API calls
        :param params: Dictionary of params for the rest API calls
        """
        # maximum page size
        page_size = MS_AZURE_PAGE_SIZE
        if isinstance(params, dict):
            params.update({"$top": page_size})
        else:
            params = {"$top": page_size}

        while True:
            # make rest call
            ret_val, response = self._make_rest_call_helper(action_result, endpoint, headers=headers, params=params, method="get")

            if phantom.is_fail(ret_val):
                return None

            if "value" in response:
                for each in response.get("value", []):
                    action_result.add_data(each)
                if len(response.get("value")) > 0 and response.get("value")[0] == {}:
                    action_result.add_data("Empty response")
            else:
                action_result.add_data(response)

            if response.get(MS_AZURE_NEXT_LINK_STRING):
                parsed_url = urlparse.urlparse(response.get(MS_AZURE_NEXT_LINK_STRING))
                try:
                    params["$skiptoken"] = urlparse.parse_qs(parsed_url.query).get("$skiptoken")[0]
                except:
                    self.debug_print(f"odata.nextLink is {response.get(MS_AZURE_NEXT_LINK_STRING)}")
                    self.debug_print("Error occurred while extracting skiptoken from the odata.nextLink")
                    break
            else:
                break

        return phantom.APP_SUCCESS

    def _handle_list_managed_devices(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        filter_string = param.get("filter_string")

        headers = {}
        parameters = {}

        if filter_string:
            parameters["$filter"] = filter_string

        ret_val = self._handle_pagination(
            action_result,
            "/deviceManagement/managedDevices",
            headers=headers,
            params=parameters,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        summary = action_result.update_summary({})
        resp_data = action_result.get_data()

        if resp_data and resp_data[action_result.get_data_size() - 1] == "Empty response":
            summary["num_devices"] = (action_result.get_data_size()) - 1
        else:
            summary["num_devices"] = action_result.get_data_size()

        self.save_progress(f"Completed action handler for: {self.get_action_identifier()}")
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "list_managed_devices":
            ret_val = self._handle_list_managed_devices(param)

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        return ret_val

    def initialize(self):
        """This is an optional function that can be implemented by the AppConnector derived class. Since the
        configuration dictionary is already validated by the time this function is called, it's a good place to do any
        extra initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS or
        phantom.APP_ERROR. If this function returns phantom.APP_ERROR, then AppConnector::handle_action will not get
        called.
        """

        self._state = self.load_state()

        if self._state is None:
            return self.set_status(phantom.APP_ERROR, MS_AZURE_STATE_FILE_CORRUPT_ERROR)

        # get the asset config
        config = self.get_config()
        self._asset_id = self.get_asset_id()

        self._tenant = config[MS_AZURE_CONFIG_TENANT]
        self._client_id = config[MS_AZURE_CONFIG_CLIENT_ID]
        self._client_secret = config[MS_AZURE_CONFIG_CLIENT_SECRET]
        self._admin_access_required = config.get(MS_AZURE_CONFIG_ADMIN_ACCESS_REQUIRED, False)
        self._admin_access_granted = config.get(MS_AZURE_CONFIG_ADMIN_ACCESS_GRANTED, False)
        self._access_token = self._state.get(MS_AZURE_TOKEN_STRING, {}).get(MS_AZURE_ACCESS_TOKEN_STRING)
        self._refresh_token = self._state.get(MS_AZURE_TOKEN_STRING, {}).get(MS_AZURE_REFRESH_TOKEN_STRING)
        self._base_url = MSADGRAPH_API_URLS[config.get(MS_AZURE_URL, "Global")]

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == "__main__":
    import argparse

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument(
        "-v",
        "--verify",
        action="store_true",
        help="verify",
        required=False,
        default=False,
    )

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
        login_url = BaseConnector._get_phantom_base_url() + "login"
        try:
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

        connector = MicrosoftIntuneConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
