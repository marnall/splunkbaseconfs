# File: msgraphforsharepoint_connector.py
#
# Copyright (c) 2022-2026 Splunk Inc.
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
import math
import os
import sys
import tempfile
import time
import urllib.parse

import encryption_helper
import phantom.app as phantom
import phantom.rules as ph_rules
import requests
from bs4 import BeautifulSoup
from django.http import HttpResponse
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault
from phantom_common import paths

from msgraphforsharepoint_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


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
    state_file = STATE_FILE_PATH.format(app_dir, asset_id)
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
            app_connector.debug_print(f"In _load_app_state: {e!s}")

    if app_connector:
        app_connector.debug_print(f"Loaded state: {state}")

    return state


def _save_app_state(state, asset_id, app_connector=None):
    """This function is used to save current state in file.

    :param state: Dictionary which contains data to write in state file
    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :return: status: phantom.APP_SUCCESS/phantom.APP_ERROR
    """

    asset_id = str(asset_id)
    if not asset_id or not asset_id.isalnum():
        if app_connector:
            app_connector.debug_print("In _save_app_state: Invalid asset_id")
        return phantom.APP_ERROR

    app_dir = os.path.dirname(os.path.abspath(__file__))
    state_file = STATE_FILE_PATH.format(app_dir, asset_id)

    real_state_file_path = os.path.abspath(state_file)
    if not os.path.dirname(real_state_file_path) == app_dir:
        if app_connector:
            app_connector.debug_print("In _save_app_state: Invalid asset_id")
        return phantom.APP_ERROR

    if app_connector:
        app_connector.debug_print(f"Saving state: {state}")

    try:
        with open(real_state_file_path, "w+") as state_file_obj:
            state_file_obj.write(json.dumps(state))
    except Exception as e:
        if app_connector:
            app_connector.debug_print(f"Unable to save state file. Error: {e!s}")
        return phantom.APP_ERROR

    return phantom.APP_SUCCESS


def _remove_app_state(asset_id, app_connector=None):
    """This function is used to delete the current state in file.

    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :return: status: phantom.APP_SUCCESS/phantom.APP_ERROR
    """

    asset_id = str(asset_id)
    if not asset_id or not asset_id.isalnum():
        if app_connector:
            app_connector.debug_print("In _remove_app_state: Invalid asset_id")
        return phantom.APP_ERROR

    app_dir = os.path.dirname(os.path.abspath(__file__))
    state_file = STATE_FILE_PATH.format(app_dir, asset_id)

    real_state_file_path = os.path.abspath(state_file)
    if not os.path.dirname(real_state_file_path) == app_dir:
        if app_connector:
            app_connector.debug_print("In _remove_app_state: Invalid asset_id")
        return phantom.APP_ERROR

    try:
        os.remove(state_file)
    except Exception as e:
        if app_connector:
            app_connector.debug_print(f"Unable to remove state file. Error: {e!s}")
        return phantom.APP_ERROR


def _return_response(asset_id, error_msg, status, error=True):
    state = _load_app_state(asset_id)
    state["error"] = error
    _save_app_state(state, asset_id)
    return HttpResponse(error_msg, status=status, content_type="text/plain")


def handle_request(request, path_parts):
    """
    request contains the data posted to the rest endpoint, it is the django http request object
    path_parts is a list of the URL tokenized
    """

    resp_dict = request.GET
    asset_id = resp_dict.get("state")
    error = resp_dict.get("error")
    try:
        if error:
            error_msg = resp_dict.get("error_description")
            return _return_response(asset_id, error_msg, 401)

        return _return_response(asset_id, "You can now close this page", 200, False)
    except Exception as e:
        return _return_response(asset_id, f"Error handling request: {e!s}", 400)


def _get_dir_name_from_app_name(app_name):
    app_name = "".join([x for x in app_name if x.isalnum()])
    app_name = app_name.lower()

    if not app_name:
        app_name = "app_for_phantom"

    return app_name


class MsGraphForSharepointConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._client_id = None
        self._client_secret = None
        self._tenant = None
        self._state = None
        self._base_url = None
        self._access_token = None
        self._admin_consent = None
        self._site_id = None
        self.asset_id = self.get_asset_id()

    def encrypt_state(self, encrypt_var, token_name):
        """Handle encryption of token.
        :param encrypt_var: Variable needs to be encrypted
        :return: encrypted variable
        """
        self.debug_print(MS_SHAREPOINT_ENCRYPT_TOKEN.format(token_name))  # nosemgrep
        return encryption_helper.encrypt(encrypt_var, self.asset_id)

    def decrypt_state(self, decrypt_var, token_name):
        """Handle decryption of token.
        :param decrypt_var: Variable needs to be decrypted
        :return: decrypted variable
        """
        self.debug_print(MS_SHAREPOINT_DECRYPT_TOKEN.format(token_name))  # nosemgrep
        if self._state.get(MS_SHAREPOINT_STATE_IS_ENCRYPTED):
            return encryption_helper.decrypt(decrypt_var, self.asset_id)
        else:
            return

    def _get_error_message_from_exception(self, e):
        """This method is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = None
        error_msg = MS_SHAREPOINT_ERROR_MSG

        self.error_print("Error Occurred.", e)
        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except Exception:
            self.debug_print("Error occurred while retrieving exception information")

        return f"Error Code: {error_code}. Error Message: {error_msg}"

    def _validate_integer(self, action_result, parameter, key, allow_zero=True):
        """
        Validate an integer.

        :param action_result: Action result or BaseConnector object
        :param parameter: input parameter
        :param key: input parameter message key
        :allow_zero: whether zero should be considered as valid value or not
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS, integer value of the parameter or None in case of failure
        """

        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, MS_SHAREPOINT_VALID_INTEGER_MSG.format(key)), None

                parameter = int(parameter)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, MS_SHAREPOINT_VALID_INTEGER_MSG.format(key)), None

            # Negative value validation
            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, MS_SHAREPOINT_NON_NEGATIVE_INTEGER_MSG.format(key)), None

            # Zero value validation
            if not allow_zero and parameter == 0:
                return action_result.set_status(phantom.APP_ERROR, MS_SHAREPOINT_POSITIVE_INTEGER_MSG.format(key)), None

        return phantom.APP_SUCCESS, parameter

    def _process_empty_response(self, response, action_result):
        if response.status_code in [200, 202, 204]:
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

        message = f"Status Code: {status_code}. Data from server: {error_text}"

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {error_message}"), None)

        resp_json = self._sanitize_non_finite_floats(resp_json)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        try:
            error_code = ""
            error_text = ""
            error_message = ""
            error = resp_json.get("error", "")
            error_desc = resp_json.get("error_description", "")
            if isinstance(error, dict):
                error_code = error.get("code")
                error_message = error.get("message")

            if error_message:
                try:
                    soup = BeautifulSoup(resp_json.get("error", {}).get("message"), "html.parser")
                    # Remove the script, style, footer and navigation part from the HTML message
                    for element in soup(["script", "style", "footer", "nav"]):
                        element.extract()
                    error_text = soup.text
                    split_lines = error_text.split("\n")
                    split_lines = [x.strip() for x in split_lines if x.strip()]
                    error_text = "\n".join(split_lines)
                    if len(error_text) > 500:
                        error_text = "Error while connecting to a server (Please check input parameters or asset configuration parameters)"
                except Exception:
                    error_text = "Cannot parse error details"

            if error_code:
                error_text = f"{error_code}. {error_text}"

            if error_desc:
                error_text = f"{error_desc}. {error_text}"

            if not error_text:
                error_text = r.text.replace("{", "{{").replace("}", "}}")
        except Exception:
            error_text = r.text.replace("{", "{{").replace("}", "}}")

        # You should process the error returned in the json
        message = f"Error from server. Status Code: {r.status_code} Data from server: {error_text}"

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

    def _make_rest_call(
        self, endpoint, action_result, verify=True, headers=None, params=None, data=None, json=None, method="get", download=False
    ):
        """Function that makes the REST call to the app.
        :param endpoint: REST endpoint that needs to appended to the service address
        :param action_result: object of ActionResult class
        :param verify: verify server certificate (Default True)
        :param headers: request headers
        :param params: request parameters
        :param data: request body
        :param json: JSON object
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :param download: use streaming for the file download to handle large files
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        try:
            if download:
                if hasattr(Vault, "get_vault_tmp_dir"):
                    fd, tmp_file_path = tempfile.mkstemp(dir=Vault.get_vault_tmp_dir())
                else:
                    vault_tmp = os.path.join(paths.PHANTOM_VAULT, "tmp")
                    fd, tmp_file_path = tempfile.mkstemp(dir=vault_tmp)
                os.close(fd)

                r = request_func(endpoint, json=json, data=data, headers=headers, params=params, stream=True)
                if 200 <= r.status_code < 399:
                    with open(tmp_file_path, "wb") as fp:
                        for chunk in r.iter_content(chunk_size=10 * 1024 * 1024):
                            fp.write(chunk)
                    return RetVal(phantom.APP_SUCCESS, tmp_file_path)
                self.debug_print(f"Error while downloading file. StatusCode: {r.status_code}, text: {r.text}")
            else:
                r = request_func(endpoint, json=json, data=data, headers=headers, verify=verify, params=params)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {error_message}"), resp_json)

        return self._process_response(r, action_result)

    def _get_token(self, action_result):
        """This function is used to get a token via REST Call.
        :param action_result: Object of action result
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "client_credentials",
            "scope": "https://graph.microsoft.com/.default",
        }

        req_url = MS_SERVER_TOKEN_URL.format(self._tenant)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        ret_val, resp_json = self._make_rest_call(req_url, action_result, headers=headers, data=data, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self._state[MS_SHAREPOINT_JSON_TOKEN] = resp_json
        self._access_token = resp_json[MS_SHAREPOINT_JSON_ACCESS_TOKEN]

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully fetched access token")

    def _make_rest_call_helper(
        self,
        endpoint,
        action_result,
        verify=True,
        headers=None,
        params=None,
        data=None,
        json=None,
        method="get",
        download=False,
        next_link=None,
        is_force=False,
    ):
        """Function that helps to set a REST call to the app.
        :param endpoint: REST endpoint that needs to appended to the service address
        :param action_result: object of ActionResult class
        :param verify: verify server certificate (Default True)
        :param headers: request headers
        :param params: request parameters
        :param data: request body
        :param json: JSON object
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :param download: use streaming for the file download to handle large files
        :param next_link: used for pagination, next_link is returned in the API response
        :param is_force: ignore the token available in the state file
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        if next_link:
            url = next_link
        else:
            url = f"{self._base_url}{endpoint}"

        if headers is None:
            headers = {}

        if not self._access_token or is_force:
            self.save_progress("Generating a token")
            ret_val = self._get_token(action_result)

            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

        headers.update({"Authorization": f"Bearer {self._access_token}", "Accept": "application/json", "Content-Type": "application/json"})

        self.save_progress(f"Connecting to endpoint {endpoint}")
        ret_val, resp_json = self._make_rest_call(url, action_result, verify, headers, params, data, json, method, download)

        # If token is expired, generate a new token
        message = action_result.get_message()
        self.debug_print(f"message: {message}")
        if message and ("token" in message and "expired" in message):
            self.save_progress("Bad token, generating a new one")
            ret_val = self._get_token(action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            headers.update({"Authorization": f"Bearer {self._access_token}"})

            self.save_progress(f"Connecting to endpoint {endpoint}")
            ret_val, resp_json = self._make_rest_call(url, action_result, verify, headers, params, data, json, method, download)

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, resp_json

    def _make_rest_calls_to_phantom(self, url, action_result, verify=False):
        r = requests.get(url, verify=verify, timeout=DEFAULT_REQUEST_TIMEOUT)
        if not r:
            message = f"Status Code: {r.status_code}"
            if r.text:
                message = "{} Error from Server: {}".format(message, r.text.replace("{", "{{").replace("}", "}}"))
            return action_result.set_status(phantom.APP_ERROR, f"Error retrieving system info, {message}"), None

        try:
            resp_json = r.json()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error processing response JSON. Error: {error_message}"), None

        return phantom.APP_SUCCESS, resp_json

    def _get_asset_name(self, action_result):
        asset_id = self.get_asset_id()
        rest_endpoint = SOAR_ASSET_INFO_URL.format(url=self.get_phantom_base_url(), asset_id=asset_id)
        ret_val, resp_json = self._make_rest_calls_to_phantom(rest_endpoint, action_result)
        if phantom.is_fail(ret_val):
            return ret_val, None

        asset_name = resp_json.get("name")
        if not asset_name:
            return action_result.set_status(phantom.APP_ERROR, f"Asset Name for ID: {asset_id} not found"), None

        return phantom.APP_SUCCESS, asset_name

    def _get_phantom_base_url(self, action_result):
        ret_val, resp_json = self._make_rest_calls_to_phantom(SOAR_SYS_INFO_URL.format(url=self.get_phantom_base_url()), action_result)
        if phantom.is_fail(ret_val):
            return ret_val, None

        phantom_base_url = resp_json.get("base_url").rstrip("/")
        if not phantom_base_url:
            return (
                action_result.set_status(
                    phantom.APP_ERROR, "Phantom Base URL not found in System Settings. Please specify this value in System Settings"
                ),
                None,
            )

        return phantom.APP_SUCCESS, phantom_base_url

    def _get_url_to_app_rest(self, action_result=None):
        if not action_result:
            action_result = ActionResult()

        # get the phantom ip to redirect to
        ret_val, phantom_base_url = self._get_phantom_base_url(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        # get the asset name
        ret_val, asset_name = self._get_asset_name(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        self.save_progress(f"Using Phantom base URL as: {phantom_base_url}")

        app_json = self.get_app_json()
        app_name = app_json["name"]
        app_dir_name = _get_dir_name_from_app_name(app_name)

        url_to_app_rest = "{}/rest/handler/{}_{}/{}".format(phantom_base_url, app_dir_name, app_json["appid"], asset_name)

        return phantom.APP_SUCCESS, url_to_app_rest

    def _get_admin_consent(self, action_result):
        self.save_progress("Getting App REST endpoint URL")

        # Get the URL to the app's REST Endpoint, this is the url that the TC dialog
        # box will ask the user to connect to
        ret_val, app_rest_url = self._get_url_to_app_rest(action_result)
        app_state = {}
        if phantom.is_fail(ret_val):
            self.save_progress(f"Unable to get the URL to the app's REST Endpoint. Error: {action_result.get_message()}")
            return action_result.set_status(phantom.APP_ERROR)

        app_state["redirect_uri"] = app_rest_url

        self.save_progress("Using OAuth Redirect URL as:")
        self.save_progress(app_rest_url)

        admin_consent_url = f"https://login.microsoftonline.com/{self._tenant}/adminconsent?client_id={self._client_id}&redirect_uri={app_rest_url}&state={self.get_asset_id()}"
        self.save_progress("Please connect to the following URL from a different tab to continue the connectivity process")
        self.save_progress(admin_consent_url)
        self.save_progress("Waiting for Admin Consent to complete")

        for i in range(0, 60):
            time.sleep(5)
            self.send_progress("{}".format("." * (i % 10)))

            state = _load_app_state(self.get_asset_id(), self)
            if not state:
                continue

            # Got the state dict, remove the temp file and process further
            _remove_app_state(self.get_asset_id(), self)

            if state.get("error"):
                self.save_progress("Admin consent not received or not given")
                return action_result.set_status(phantom.APP_ERROR)
            else:
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
                return action_result.set_status(phantom.APP_SUCCESS)

        self.save_progress("Timed out waiting for login, please try again")
        return action_result.set_status(phantom.APP_ERROR)

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._admin_consent:
            ret_val = self._get_admin_consent(action_result)
            if phantom.is_fail(ret_val):
                self._state = {"app_version": self.get_app_json().get("app_version")}
                self.save_progress("Test Connectivity Failed")
                return action_result.get_status()

        endpoint = self._endpoint_test_connectivity
        if endpoint[0] != "/":
            endpoint = f"/{endpoint}"

        ret_val, _ = self._make_rest_call_helper(endpoint, action_result, is_force=True)
        if phantom.is_fail(ret_val):
            self._state = {"app_version": self.get_app_json().get("app_version")}
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _sanitize_non_finite_floats(self, data):
        """Recursively replace non-finite float values (Infinity, -Infinity, NaN) with None.

        PostgreSQL's JSONB type rejects these values because they are not valid JSON.
        The MS Graph API can return them in column metadata (e.g., "maximum": Infinity).
        """
        if isinstance(data, dict):
            return {k: self._sanitize_non_finite_floats(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._sanitize_non_finite_floats(item) for item in data]
        if isinstance(data, float) and not math.isfinite(data):
            return None
        return data

    def _paginator(self, action_result, endpoint, limit=None, params=None):
        """
        This action is used to create an iterator that will paginate through responses from called methods.

        :param action_result: Object of ActionResult class
        :param endpoint: API endpoint whose response is to be paginated
        :param **kwargs: Dictionary of Input parameters
        """

        list_items = list()
        next_link = None

        # maximum page size
        page_size = MS_SHAREPOINT_PER_PAGE_COUNT

        if limit and limit < page_size:
            page_size = limit

        if isinstance(params, dict):
            params.update({"$top": page_size})
        else:
            params = {"$top": page_size}

        while True:
            if next_link:
                ret_val, response = self._make_rest_call_helper(endpoint, action_result, next_link=next_link)
            else:
                ret_val, response = self._make_rest_call_helper(endpoint, action_result, params=params)

            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            if response.get("value"):
                list_items.extend(response.get("value", []))

            if limit and len(list_items) >= limit:
                return phantom.APP_SUCCESS, list_items[:limit]

            next_link = response.get("@odata.nextLink", None)
            if not next_link:
                break

        return phantom.APP_SUCCESS, list_items

    def _handle_add_item(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        item = param.get("item")
        endpoint = f"{MS_GET_LIST_ENDPOINT.format(site_id=self._site_id, list=urllib.parse.quote(param[MS_SHAREPOINT_JSON_LIST]))}/items"
        ret_val, item = self._make_rest_call_helper(method="post", endpoint=endpoint, data=item.encode("utf-8"), action_result=action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(item)

        summary = action_result.update_summary({})
        summary[MS_SHAREPOINT_JSON_SITES_COUNT] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_item(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        item = param.get("item")
        item_id = param.get("item_id")

        list_endpoint = MS_GET_LIST_ENDPOINT.format(site_id=self._site_id, list=urllib.parse.quote(param[MS_SHAREPOINT_JSON_LIST]))
        endpoint = f"{list_endpoint}/items/{item_id}"

        ret_val, item = self._make_rest_call_helper(method="patch", endpoint=endpoint, data=item.encode("utf-8"), action_result=action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(item)

        summary = action_result.update_summary({})
        summary[MS_SHAREPOINT_JSON_SITES_COUNT] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_drive_children(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        drive_id = param.get(MS_SHAREPOINT_JSON_DRIVE_ID, "")

        endpoint = f"{self.build_drive_endpoint(drive_id)}/items/root/children"

        ret_val, children = self._paginator(action_result, endpoint)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for child in children:
            action_result.add_data(child)

        summary = action_result.update_summary({})
        summary[MS_SHAREPOINT_JSON_DRIVE_CHILDREN_COUNT] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_copy_drive_item(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        source_drive_id = param.get("source_drive_id", "")
        source_item_id = param["source_item_id"]

        endpoint = f"{self.build_drive_endpoint(source_drive_id)}{MS_DRIVE_COPY_ITEM_ENDPOINT.format(item_id=source_item_id)}"

        dest_drive_id = param.get("dest_drive_id", "")
        dest_folder_id = param.get("dest_folder_id", "")
        file_name = param.get("file_name", "")

        parent_reference = {"id": dest_folder_id}
        if dest_drive_id:
            parent_reference["driveId"] = dest_drive_id
        data = {"parentReference": parent_reference}

        if file_name:
            data["name"] = file_name

        payload = json.dumps(data)

        ret_val, response = self._make_rest_call_helper(
            method="post",
            endpoint=endpoint,
            data=payload,
            action_result=action_result,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully copied an item")

    def _handle_create_folder(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        drive_id = param.get(MS_SHAREPOINT_JSON_DRIVE_ID, "")
        parent_item_id = param["parent_item_id"]
        endpoint = f"{self.build_drive_endpoint(drive_id)}{MS_DRIVE_CREATE_FOLDER_ENDPOINT.format(parent_id=parent_item_id)}"

        data = {
            "name": param["folder_name"],
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename",
        }

        payload = json.dumps(data)

        ret_val, response = self._make_rest_call_helper(
            method="post",
            endpoint=endpoint,
            data=payload,
            action_result=action_result,
        )
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully created a folder")

    def _handle_list_sites(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val, limit = self._validate_integer(
            action_result,
            param.get(MS_SHAREPOINT_JSON_LIMIT),
            MS_SHAREPOINT_LIMIT_KEY,
            False,
        )
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, sites = self._paginator(action_result, MS_LIST_SITES_ENDPOINT, limit=limit)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for site in sites:
            action_result.add_data(site)

        summary = action_result.update_summary({})
        summary[MS_SHAREPOINT_JSON_SITES_COUNT] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_lists(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._site_id:
            return action_result.set_status(phantom.APP_ERROR, MS_SHAREPOINT_ERROR_MISSING_SITE_ID.format("retrieving lists information"))

        ret_val, limit = self._validate_integer(action_result, param.get(MS_SHAREPOINT_JSON_LIMIT), MS_SHAREPOINT_LIMIT_KEY, False)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, lists = self._paginator(action_result, MS_LIST_LISTS_ENDPOINT.format(site_id=self._site_id), limit=limit)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for list_info in lists:
            action_result.add_data(list_info)

        summary = action_result.update_summary({})
        summary[MS_SHAREPOINT_JSON_LISTS_COUNT] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_drives(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._site_id:
            return action_result.set_status(phantom.APP_ERROR, MS_SHAREPOINT_ERROR_MISSING_SITE_ID.format("retrieving drives information"))

        ret_val, limit = self._validate_integer(action_result, param.get(MS_SHAREPOINT_JSON_LIMIT), MS_SHAREPOINT_LIMIT_KEY, False)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, drives = self._paginator(action_result, MS_DRIVES_ROOT_ENDPOINT.format(site_id=self._site_id), limit=limit)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for drive_info in drives:
            action_result.add_data(drive_info)

        summary = action_result.update_summary({})
        summary["drives_count"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_list(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._site_id:
            return action_result.set_status(phantom.APP_ERROR, MS_SHAREPOINT_ERROR_MISSING_SITE_ID.format("retrieving a list"))

        ret_val, limit = self._validate_integer(action_result, param.get(MS_SHAREPOINT_JSON_LIMIT), MS_SHAREPOINT_LIMIT_KEY, False)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        endpoint = MS_GET_LIST_ENDPOINT.format(site_id=self._site_id, list=urllib.parse.quote(param[MS_SHAREPOINT_JSON_LIST]))
        params = {"expand": "columns"}
        ret_val, response = self._make_rest_call_helper(endpoint, action_result, params=params)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        params = {"expand": "fields"}
        endpoint = f"{endpoint}/items"
        ret_val, list_items = self._paginator(action_result, endpoint, params=params, limit=limit)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        response["items"] = list_items
        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary[MS_SHAREPOINT_JSON_ITEM_COUNT] = len(response.get("items", []))

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_file(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._site_id:
            return action_result.set_status(phantom.APP_ERROR, MS_SHAREPOINT_ERROR_MISSING_SITE_ID.format("retrieving a file"))

        sp_path = urllib.parse.quote(param[MS_SHAREPOINT_JSON_FILE_PATH].strip("/"))
        sp_file = urllib.parse.quote(param[MS_SHAREPOINT_JSON_FILE_NAME])
        sp_drive = param.get(MS_SHAREPOINT_JSON_DRIVE_ID, "")
        endpoint = f"{self.build_drive_endpoint(sp_drive)}{MS_GET_FILE_METADATA_ENDPOINT.format(path=sp_path, file=sp_file)}"

        # Get the file metadata
        ret_val, file_meta = self._make_rest_call_helper(endpoint, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Get the file content
        ret_val, tmp_file_path = self._make_rest_call_helper(MS_GET_FILE_CONTENT_ENDPOINT.format(endpoint), action_result, download=True)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Save attachment file to the vault
        try:
            success, message, attachment_vault_id = ph_rules.vault_add(
                container=self.get_container_id(), file_location=tmp_file_path, file_name=sp_file
            )
            if not success:
                return action_result.set_status(phantom.APP_ERROR, message)
        except Exception as e:
            error_message = f"Unable to add file to the vault for attachment name: {sp_file}. Error: {self._get_error_message_from_exception(e)}"
            return action_result.set_status(phantom.APP_ERROR, error_message)

        action_result.add_data(file_meta)
        summary = action_result.update_summary({})
        summary[MS_SHAREPOINT_JSON_VAULT_ID] = attachment_vault_id

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_remove_file(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._site_id:
            return action_result.set_status(phantom.APP_ERROR, MS_SHAREPOINT_ERROR_MISSING_SITE_ID.format("removing a file"))

        sp_path = urllib.parse.quote(param[MS_SHAREPOINT_JSON_FILE_PATH].rstrip("/"))
        sp_file = urllib.parse.quote(param[MS_SHAREPOINT_JSON_FILE_NAME])
        sp_drive = param.get(MS_SHAREPOINT_JSON_DRIVE_ID, "")
        endpoint = f"{self.build_drive_endpoint(sp_drive)}{MS_GET_FILE_METADATA_ENDPOINT.format(path=sp_path, file=sp_file)}"

        ret_val, _ = self._make_rest_call_helper(endpoint, action_result, method="delete")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully deleted file")

    def _handle_list_folder_items(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._site_id:
            return action_result.set_status(phantom.APP_ERROR, MS_SHAREPOINT_ERROR_MISSING_SITE_ID.format("removing a file"))

        drive_id = param.get(MS_SHAREPOINT_JSON_DRIVE_ID, "")
        folder_path = param["folder_path"].strip("/")

        endpoint = f"{self.build_drive_endpoint(drive_id)}{MS_GET_FOLDER_ITEMS_ENDPOINT.format(folder_path=folder_path)}"

        ret_val, children = self._paginator(action_result, endpoint)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for child in children:
            action_result.add_data(child)

        summary = action_result.update_summary({})
        summary["items_count"] = action_result.get_data_size()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_remove_folder(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._site_id:
            return action_result.set_status(phantom.APP_ERROR, MS_SHAREPOINT_ERROR_MISSING_SITE_ID.format("removing a file"))

        drive_id = param.get(MS_SHAREPOINT_JSON_DRIVE_ID, "")
        folder_path = param["folder_path"].strip("/")

        endpoint = f"{self.build_drive_endpoint(drive_id)}{MS_FOLDER_ENDPOINT.format(folder_path=folder_path)}"

        ret_val, _ = self._make_rest_call_helper(endpoint, action_result, method="delete")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully deleted folder")

    def build_drive_endpoint(self, drive_id: str = ""):
        return (
            MS_CUSTOM_DRIVE_ROOT_ENDPOINT.format(site_id=self._site_id, drive_id=drive_id)
            if drive_id
            else MS_DRIVE_ROOT_ENDPOINT.format(site_id=self._site_id)
        )

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()
        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)
        elif action_id == "list_sites":
            ret_val = self._handle_list_sites(param)
        elif action_id == "get_list":
            ret_val = self._handle_get_list(param)
        elif action_id == "get_file":
            ret_val = self._handle_get_file(param)
        elif action_id == "remove_file":
            ret_val = self._handle_remove_file(param)
        elif action_id == "list_lists":
            ret_val = self._handle_list_lists(param)
        elif action_id == "add_item":
            ret_val = self._handle_add_item(param)
        elif action_id == "update_item":
            ret_val = self._handle_update_item(param)
        elif action_id == "list_drive_children":
            ret_val = self._handle_list_drive_children(param)
        elif action_id == "create_folder":
            ret_val = self._handle_create_folder(param)
        elif action_id == "copy_drive_item":
            ret_val = self._handle_copy_drive_item(param)
        elif action_id == "list_drives":
            ret_val = self._handle_list_drives(param)
        elif action_id == "list_folder_items":
            ret_val = self._handle_list_folder_items(param)
        elif action_id == "remove_folder":
            ret_val = self._handle_remove_folder(param)

        return ret_val

    def initialize(self):
        # Load the state and check the format
        self._state = self.load_state()
        if not isinstance(self._state, dict):
            self.debug_print(MS_SHAREPOINT_ERROR_STATE_FILE_CORRUPT)
            self._state = {"app_version": self.get_app_json().get("app_version")}

        # get the asset config
        config = self.get_config()

        self._tenant = config[MS_SHAREPOINT_CONFIG_TENANT]
        self._client_id = config[MS_SHAREPOINT_CONFIG_CLIENT_ID]
        self._client_secret = config[MS_SHAREPOINT_CONFIG_CLIENT_SECRET]
        self._site_id = config.get("site_id")
        self._admin_consent = config.get("admin_consent")
        self._endpoint_test_connectivity = config.get("endpoint_test_connectivity", MS_TEST_CONNECTIVITY_ENDPOINT)
        self._access_token = self._state.get(MS_SHAREPOINT_JSON_TOKEN, {}).get(MS_SHAREPOINT_JSON_ACCESS_TOKEN, None)
        if self._state.get(MS_SHAREPOINT_STATE_IS_ENCRYPTED) and self._access_token:
            try:
                self._access_token = self.decrypt_state(self._access_token, "access")
            except Exception as e:
                self.error_print(MS_SHAREPOINT_DECRYPTION_ERROR, e)
                self._access_token = None

        self._base_url = MS_GRAPH_BASE_URL

        return phantom.APP_SUCCESS

    def finalize(self):
        try:
            if self._state.get(MS_SHAREPOINT_JSON_TOKEN, {}).get(MS_SHAREPOINT_JSON_ACCESS_TOKEN):
                self._state[MS_SHAREPOINT_JSON_TOKEN][MS_SHAREPOINT_JSON_ACCESS_TOKEN] = self.encrypt_state(self._access_token, "access")
                self._state[MS_SHAREPOINT_STATE_IS_ENCRYPTED] = True
        except Exception as e:
            self.error_print(MS_SHAREPOINT_ENCRYPTION_ERROR, e)
            return self.set_status(phantom.APP_ERROR, MS_SHAREPOINT_ENCRYPTION_ERROR)
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

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
            login_url = BaseConnector._get_phantom_base_url() + "login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=DEFAULT_REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = f"csrftoken={csrftoken}"
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print(f"Unable to get session id from the platform. Error: {e!s}")
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = MsGraphForSharepointConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
