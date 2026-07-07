# File: salesforce_connector.py
#
# Copyright (c) 2017-2026 Splunk Inc.
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
# Splunk SOAR App imports

import base64
import hashlib
import json

# import re
import os
import secrets
import sys
import time
from urllib.parse import urlparse

import encryption_helper
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from django.http import HttpResponse
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
import salesforce_consts as sf_consts


DT_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


def _delete_app_state(asset_id, app_connector=None):
    dirpath = os.path.split(__file__)[0]
    state_file = f"{dirpath}/{asset_id}_state.json"
    try:
        os.remove(state_file)
    except:
        pass

    return phantom.APP_SUCCESS


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
    real_state_file_path = os.path.realpath(state_file)
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


def _save_app_state(state, asset_id, app_connector=None):
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

    real_state_file_path = os.path.realpath(state_file)
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


def _return_error(msg, state, asset_id, status):
    state["error"] = True
    _save_app_state(state, asset_id)
    return HttpResponse(msg, status=status, content_type="text/plain")


def _handle_oauth_start(request, path_parts):
    # This is where we land AFTER the redirect callback when the user authenticates on Salesforce.
    # The authorization code is exchanged for tokens using a POST body (not URL params) per OAuth spec.
    # client_secret and code_verifier (PKCE) are read from state and sent only at the token endpoint.
    asset_id = request.GET.get("state")
    if not asset_id:
        return HttpResponse("ERROR: Asset ID not found in URL", content_type="text/plain", status=400)

    state = _load_app_state(asset_id)

    code = request.GET.get("code")
    if code:
        url_get_token = state.get("url_get_token")
        if not url_get_token:
            return _return_error("State file is missing token URL. Please re-run test connectivity.", state, asset_id, 400)

        token_body = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": encryption_helper.decrypt(state["client_id"], asset_id),  # pylint: disable=E1101
            "redirect_uri": encryption_helper.decrypt(state["redirect_uri"], asset_id),  # pylint: disable=E1101
            "client_secret": encryption_helper.decrypt(state["client_secret"], asset_id),  # pylint: disable=E1101
        }

        if state.get("code_verifier"):
            token_body["code_verifier"] = encryption_helper.decrypt(state["code_verifier"], asset_id)  # pylint: disable=E1101

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            # nosemgrep: semgrep.request-sensitive-data — body contains client_secret and code_verifier
            r = requests.post(url_get_token, data=token_body, headers=headers, timeout=sf_consts.SALESFORCE_DEFAULT_TIMEOUT)
            resp_json = r.json()
        except Exception as e:
            return _return_error(f"Error retrieving OAuth Token: {e!s}. URL: {url_get_token}", state, asset_id, 401)

        sf_error = resp_json.get("error_description") or resp_json.get("error")
        if sf_error:
            return _return_error(f"Salesforce token exchange failed: {sf_error}", state, asset_id, 401)

        refresh_token = resp_json.get("refresh_token")
        if not refresh_token:
            return _return_error("Unable to retrieve refresh token. Maybe app scope is set incorrectly?", state, asset_id, 401)
        state["refresh_token"] = encryption_helper.encrypt(refresh_token, asset_id)  # pylint: disable=E1101
        _save_app_state(state, asset_id)
        return HttpResponse("You can now close this page", content_type="text/plain")

    # Salesforce sends `error` and `error_description` when the user denies or an error occurs.
    sf_error = request.GET.get("error_description") or request.GET.get("error")
    msg = f"Authentication failed: {sf_error}" if sf_error else "Something went wrong during authentication"
    return _return_error(msg, state, asset_id, 401)


def _handle_redirect(request, path_parts):
    asset_id = request.GET.get("asset_id")
    if not asset_id:
        return HttpResponse("ERROR: Asset ID not found in URL", content_type="text/plain", status=400)

    state = _load_app_state(asset_id)
    if not state:
        return HttpResponse("ERROR: Invalid asset_id", content_type="text/plain", status=400)

    enc_url = state["url"]
    dec_url = encryption_helper.decrypt(enc_url, asset_id)  # pylint: disable=E1101

    resp = HttpResponse(status=302)
    resp["location"] = dec_url
    return resp


def handle_request(request, path_parts):
    if len(path_parts) < 2:
        return HttpResponse("Invalid REST endpoint request", content_type="text/plain", status=404)

    call_type = path_parts[1]

    if call_type == "redirect":
        return _handle_redirect(request, path_parts)

    if call_type == "start_oauth":
        return _handle_oauth_start(request, path_parts)

    return HttpResponse("Invalid endpoint", content_type="text/plain", status=404)


def _get_dir_name_from_app_name(app_name):
    app_name = "".join([x for x in app_name if x.isalnum()])
    app_name = app_name.lower()

    if not app_name:
        # hardcode it
        app_name = "app_for_phantom"

    return app_name


class SalesforceConnector(BaseConnector):
    OAUTH_FLOW = 1
    USERNAME_PASSWORD = 2
    CLIENT_CREDENTIALS = 3

    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None
        self._base_url = None
        self._oauth_token = None
        self._version_uri = None
        self._auth_flow = self.OAUTH_FLOW
        self._last_viewed_date = None

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        self.error_print("Exception: ", e)

        error_code = None
        error_msg = sf_consts.SALESFORCE_ERR_CODE_UNAVAILABLE

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except Exception:
            pass

        if not error_code:
            error_text = f"Error Message: {error_msg}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_msg}"

        return error_text

    def _get_client_credentials_domain_url(self, action_result):
        """Return the Salesforce My Domain base URL required for client credentials flow."""

        domain_url = (self.get_config().get("domain_url") or "").strip()
        if not domain_url:
            return (
                action_result.set_status(
                    phantom.APP_ERROR,
                    "My Domain URL must be specified for Client Credentials flow. "
                    "In Salesforce Setup, open My Domain and copy the Current My Domain URL "
                    "(for example, https://d3t000000example-dev-ed.my.salesforce.com).",
                ),
                None,
            )

        # Salesforce's "Current My Domain URL" field may display only the hostname, without
        # an explicit scheme. Accept that user input and normalize it to HTTPS.
        if "://" not in domain_url:
            domain_url = f"https://{domain_url}"

        parsed = urlparse(domain_url)
        if parsed.scheme != "https" or not parsed.netloc:
            return (
                action_result.set_status(
                    phantom.APP_ERROR,
                    "My Domain URL must be a full HTTPS URL, for example https://d3t000000example-dev-ed.my.salesforce.com",
                ),
                None,
            )

        host = parsed.netloc.lower()
        if not host.endswith(".my.salesforce.com"):
            return (
                action_result.set_status(
                    phantom.APP_ERROR,
                    "My Domain URL must be your Salesforce Current My Domain URL ending in .my.salesforce.com. "
                    "Do not use a login, test, or any other domain URL. "
                    "Copy only the hostname or HTTPS URL, without helper text such as 'with enhanced domains'.",
                ),
                None,
            )

        return phantom.APP_SUCCESS, f"{parsed.scheme}://{parsed.netloc}"

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
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, f"Please provide a valid integer value in the '{key}' parameter"), None

                parameter = int(parameter)
            except:
                return action_result.set_status(phantom.APP_ERROR, f"Please provide a valid integer value in the '{key}' parameter"), None

            if parameter < 0:
                return action_result.set_status(
                    phantom.APP_ERROR, f"Please provide a valid non-negative integer value in the '{key}' parameter"
                ), None
            if not allow_zero and parameter == 0:
                return action_result.set_status(phantom.APP_ERROR, sf_consts.SALESFORCE_INVALID_INTEGER.format(parameter=key)), None

        return phantom.APP_SUCCESS, parameter

    def _process_empty_response(self, response, action_result):
        """Process empty response.

        Parameters:
            :param response: response data
            :param action_result: object of ActionResult class
        Returns:
            :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message), response
        """

        if self.get_action_identifier() in ("update_ticket", "update_object", "delete_object", "delete_ticket"):
            return RetVal(phantom.APP_SUCCESS, {})

        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    def _process_html_response(self, response, action_result):
        """Process html response.

        Parameters:
            :param response: response data
            :param action_result: object of ActionResult class
        Returns:
            :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message), response
        """
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            for element in soup(["script", "style", "footer", "nav"]):
                element.extract()
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
        """Process json response.

        Parameters:
            :param r: response data
            :param action_result: object of ActionResult class
        Returns:
            :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message), response
        """

        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {error_message}"), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        error_message = r.text.replace("{", "{{").replace("}", "}}")
        message = f"Error from server. Status Code: {r.status_code} Data from server: {error_message}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        """Process API response.

        Parameters:
            :param r: response data
            :param action_result: object of ActionResult class
        Returns:
            :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message), response
        """

        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        if "javascript" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the API talks.
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
        self, endpoint, action_result, headers=None, params=None, data=None, json=None, method="get", ignore_base_url=False, **kwargs
    ):
        """Make the REST call to the app.

        Parameters:
            :param endpoint: REST endpoint
            :param action_result: object of ActionResult class
            :param headers: request headers
            :param params: request parameters
            :param data: request body
            :param json: JSON object
            :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
            :param ignore_base_url: Ignore the base url and use endpoint as url (Default False)
            :param **kwargs: Dictionary of other parameters
        Returns:
            :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message), response obtained by making an API call
        """
        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        if ignore_base_url:
            url = endpoint
        else:
            if self._base_url is None:
                return RetVal(action_result.set_status(phantom.APP_ERROR, "Base URL is None"), resp_json)
            url = f"{self._base_url}{endpoint}"

        try:
            r = request_func(url, json=json, data=data, headers=headers, params=params, **kwargs)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {error_message}"), resp_json)

        return self._process_response(r, action_result)

    def _retrieve_oauth_token(self, action_result):
        """This function is used to get a Oauth token via REST Call.

        Parameters:
            :param action_result: Object of action result
        Returns:
            :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        config = self.get_config()
        client_id = config["client_id"]
        client_secret = config["client_secret"]
        try:
            refresh_token = encryption_helper.decrypt(self._state["refresh_token"], self.get_asset_id())  # pylint: disable=E1101
        except KeyError:
            return action_result.set_status(phantom.APP_ERROR, "Error getting refresh token, has test connectivity been run?")
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, "Error decrypting refresh token", error_message)

        body = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        if config.get("is_test_environment"):
            url_get_token = sf_consts.URL_GET_TOKEN_TEST
        else:
            url_get_token = sf_consts.URL_GET_TOKEN

        ret_val, resp = self._make_rest_call(url_get_token, action_result, data=body, headers=headers, ignore_base_url=True, method="post")
        if phantom.is_fail(ret_val):
            return ret_val

        self._oauth_token = resp["access_token"]
        self._base_url = resp["instance_url"]

        # Refresh token rotation: if Salesforce returns a new refresh token, replace the stored one
        # and persist immediately. The old token is already invalidated at this point, so any
        # unhandled exception after this line would otherwise leave the connector with no valid token.
        new_refresh_token = resp.get("refresh_token")
        if new_refresh_token:
            self._state["refresh_token"] = encryption_helper.encrypt(new_refresh_token, self.get_asset_id())  # pylint: disable=E1101
            self.save_state(self._state)

        return phantom.APP_SUCCESS

    def _retrieve_oauth_token_username_password(self, action_result):
        """This function is used to get a Oauth token via REST Call with username and password.

        Parameters:
            :param action_result: Object of action result
        Returns:
            :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        config = self.get_config()
        client_id = config["client_id"]
        client_secret = config["client_secret"]

        body = {
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": self._username,
            "password": self._password,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        if config.get("is_test_environment"):
            url_get_token = sf_consts.URL_GET_TOKEN_TEST
        else:
            url_get_token = sf_consts.URL_GET_TOKEN

        ret_val, resp = self._make_rest_call(url_get_token, action_result, data=body, headers=headers, ignore_base_url=True, method="post")
        if phantom.is_fail(ret_val):
            return ret_val

        self._oauth_token = resp["access_token"]
        self._base_url = resp["instance_url"]
        return phantom.APP_SUCCESS

    def _retrieve_oauth_token_client_credentials(self, action_result):
        """Get an access token using the OAuth 2.0 Client Credentials flow.

        No browser or user interaction required. Salesforce issues a fresh access token
        on every call. There is no refresh token in this flow.

        Parameters:
            :param action_result: Object of action result
        Returns:
            :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        config = self.get_config()
        body = {
            "grant_type": "client_credentials",
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        ret_val, domain_url = self._get_client_credentials_domain_url(action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        url_get_token = f"{domain_url}{sf_consts.SALESFORCE_OAUTH_TOKEN_PATH}"

        ret_val, resp = self._make_rest_call(url_get_token, action_result, data=body, headers=headers, ignore_base_url=True, method="post")
        if phantom.is_fail(ret_val):
            return ret_val

        self._oauth_token = resp["access_token"]
        self._base_url = resp.get("instance_url") or domain_url
        return phantom.APP_SUCCESS

    def _retrieve_oauth_token_helper(self, action_result):
        """Function that helps to retrieve oauth token for the app.

        Parameters:
            :param action_result: object of ActionResult class
        Returns:
            :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """
        if self._auth_flow == self.OAUTH_FLOW:
            return self._retrieve_oauth_token(action_result)
        if self._auth_flow == self.CLIENT_CREDENTIALS:
            return self._retrieve_oauth_token_client_credentials(action_result)
        return self._retrieve_oauth_token_username_password(action_result)

    def _make_rest_call_helper(self, endpoint, action_result, headers=None, *args, **kwargs):
        """Function that helps setting REST call to the app.

        Parameters:
            :param endpoint: REST endpoint
            :param action_result: object of ActionResult class
            :param headers: request headers
            :param *args: parameters
            :param **kwargs: Dictionary of parameters
        Returns:
            :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message), response obtained by making an API call
        """
        # Add Authorization header before making rest call
        if headers is None:
            headers = {}

        if not self._oauth_token:
            self.save_progress("Retrieving API URL and OAuth Token...")
            ret_val = self._retrieve_oauth_token_helper(action_result)
            if phantom.is_fail(ret_val):
                return RetVal(ret_val)

        headers.update({"Authorization": f"Bearer {self._oauth_token}"})

        return self._make_rest_call(endpoint, action_result, headers=headers, *args, **kwargs)

    def _get_asset_name(self, action_result):
        """Get name of the asset using Phantom URL.

        Parameters:
            :param action_result: object of ActionResult class
        Returns:
            :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message), asset name
        """

        asset_id = self.get_asset_id()

        rest_endpoint = sf_consts.PHANTOM_ASSET_INFO_URL.format(url=self.get_phantom_base_url(), asset_id=asset_id)

        ret_val, resp_json = self._make_rest_call(rest_endpoint, action_result, ignore_base_url=True, verify=False)

        if phantom.is_fail(ret_val):
            return (ret_val, None)

        asset_name = resp_json.get("name")

        if not asset_name:
            return action_result.set_status(phantom.APP_ERROR, f"Asset Name for id: {asset_id} not found.", None)

        return (phantom.APP_SUCCESS, asset_name)

    def _get_phantom_base_url(self, action_result):
        """Get base url of phantom.

        Parameters:
            :param action_result: object of ActionResult class
        Returns:
            :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message), base url of phantom
        """

        ret_val, resp_json = self._make_rest_call(
            sf_consts.PHANTOM_SYS_INFO_URL.format(url=self.get_phantom_base_url()), action_result, ignore_base_url=True, verify=False
        )

        if phantom.is_fail(ret_val):
            return (ret_val, None)

        phantom_base_url = resp_json.get("base_url").rstrip("/")

        if not phantom_base_url:
            return (
                action_result.set_status(
                    phantom.APP_ERROR, "Phantom Base URL not found in System Settings. Please specify this value in System Settings"
                ),
                None,
            )

        return (phantom.APP_SUCCESS, phantom_base_url)

    def _get_url_to_app_rest(self, action_result=None):
        """Get URL for making rest calls.

        Parameters:
            :param action_result: object of ActionResult class
        Returns:
            :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        URL to make rest calls
        """

        if not action_result:
            action_result = ActionResult()

        # get the phantom ip to redirect to
        ret_val, phantom_base_url = self._get_phantom_base_url(action_result)

        if phantom.is_fail(ret_val):
            return (action_result.get_status(), None)

        # get the asset name
        ret_val, asset_name = self._get_asset_name(action_result)

        if phantom.is_fail(ret_val):
            return (action_result.get_status(), None)

        self.save_progress(f"Using Phantom base URL as: {phantom_base_url}")

        app_json = self.get_app_json()

        app_name = app_json["name"]

        app_dir_name = _get_dir_name_from_app_name(app_name)

        url_to_app_rest = "{}/rest/handler/{}_{}/{}".format(phantom_base_url, app_dir_name, app_json["appid"], asset_name)

        return (phantom.APP_SUCCESS, url_to_app_rest)

    def _oauth_flow_test_connect(self, action_result):
        """Function that handles the test connectivity action with Oauth(Authentication method).

        Parameters:
            :param action_result: object of ActionResult class
        Returns:
            :return: status phantom.APP_ERROR/phantom.APP_SUCCESS
        """

        config = self.get_config()
        client_id = config["client_id"]
        client_secret = config["client_secret"]

        ret_val, app_rest_url = self._get_url_to_app_rest(action_result)
        if phantom.is_fail(ret_val):
            self.save_progress("Error getting redirect URL")
            return ret_val

        asset_id = self.get_asset_id()

        # PKCE: generate code_verifier and derive code_challenge (S256 method)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(sf_consts.SALESFORCE_PKCE_VERIFIER_BYTES)).rstrip(b"=").decode()
        code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("ascii")).digest()).rstrip(b"=").decode()

        redirect_uri = app_rest_url + "/start_oauth"

        auth_params = {
            "response_type": "code",
            "state": asset_id,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        if config.get("is_test_environment"):
            url_get_code = sf_consts.URL_GET_CODE_TEST
            url_get_token = sf_consts.URL_GET_TOKEN_TEST
        else:
            url_get_code = sf_consts.URL_GET_CODE
            url_get_token = sf_consts.URL_GET_TOKEN

        prep = requests.Request("get", url_get_code, params=auth_params).prepare()

        state = {}
        state["client_id"] = encryption_helper.encrypt(client_id, asset_id)  # pylint: disable=E1101
        state["redirect_uri"] = encryption_helper.encrypt(redirect_uri, asset_id)  # pylint: disable=E1101
        state["client_secret"] = encryption_helper.encrypt(client_secret, asset_id)  # pylint: disable=E1101
        state["code_verifier"] = encryption_helper.encrypt(code_verifier, asset_id)  # pylint: disable=E1101
        state["url"] = encryption_helper.encrypt(prep.url, asset_id)  # pylint: disable=E1101
        # url_get_token is a well-known public Salesforce endpoint (not a secret), stored plaintext intentionally.
        state["url_get_token"] = url_get_token
        _save_app_state(state, asset_id, self)

        self.save_progress("To Continue, open this link in a new tab in your browser")
        self.save_progress(app_rest_url + f"/redirect?asset_id={asset_id}")

        # Wait for user to authorize Salesforce
        for _ in range(0, 60):
            state = _load_app_state(asset_id)
            refresh_token = state.get("refresh_token")
            if refresh_token:
                break
            elif state.get("error", False):
                self.save_progress("Error retrieving refresh token")
                _delete_app_state(asset_id)
                return action_result.set_status(phantom.APP_ERROR)
            time.sleep(5)
        else:
            _delete_app_state(asset_id)
            self.save_progress("Unable to finish test connectivity due to time out")
            return action_result.set_status(phantom.APP_ERROR)

        _delete_app_state(asset_id)
        # Intentionally wipe any partial/failed state from a previous run before storing the
        # newly acquired refresh token — prevents stale PKCE or error flags from carrying over.
        self._state = {}
        self._state["refresh_token"] = refresh_token

        self.save_progress("Successfully Retrieved Refresh Token")
        return phantom.APP_SUCCESS

    def _handle_test_connectivity(self, param):
        """Function that handles the test connectivity action"""

        action_result = self.add_action_result(ActionResult(dict(param)))
        if self._auth_flow == self.OAUTH_FLOW:
            ret_val = self._oauth_flow_test_connect(action_result)
            if phantom.is_fail(ret_val):
                return ret_val

        self.save_progress("Obtaining API Version")

        ret_val, response = self._make_rest_call_helper("/services/data/", action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        latest_version = response[-1]["url"]
        self._state["latest_version"] = latest_version

        self.save_progress("Testing API Version and Authorization Credentials...")
        ret_val, response = self._make_rest_call_helper(latest_version, action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        self.save_progress("Test Connectivity Passed")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_run_query_results(self, action_result, endpoint, params):
        done = False
        while not done:
            ret_val, response = self._make_rest_call_helper(endpoint, action_result, params=params)
            if phantom.is_fail(ret_val):
                return ret_val
            done = response["done"]
            if not done:
                params = None
                endpoint = response["nextRecordsUrl"]

            for record in response["records"]:
                action_result.add_data(record)

        action_result.update_summary({"num_objects": action_result.get_data_size()})
        return phantom.APP_SUCCESS

    def _handle_run_query(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.debug_print("run query called")
        query = param["query"]
        query_type = param.get("endpoint", "query")

        endpoint = sf_consts.API_ENDPOINT_RUN_QUERY.format(version=self._version_uri, query_type=query_type)
        # Replace all spaces with a '+' sign for URL param
        query = " ".join(query.split()).replace(" ", "+")
        # Pass a string to avoid getting the '+' url encoded
        params = f"q={query}"

        ret_val = self._get_run_query_results(action_result, endpoint, params)
        if phantom.is_fail(ret_val):
            return ret_val

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved query results")

    def _create_object(self, action_result, param, field_values):
        self.debug_print("create object called")
        sobject = param.get("sobject", "Case")

        endpoint = sf_consts.API_ENDPOINT_OBJECT.format(version=self._version_uri, sobject=sobject)

        ret_val, response = self._make_rest_call_helper(endpoint, action_result, json=field_values, method="post")
        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["obj_id"] = response["id"]

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully created a new {sobject}")

    def _handle_create_object(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        other = param["field_values"]
        try:
            other_dict = json.loads(other)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, "Error reading 'field_values'", error_message)

        return self._create_object(action_result, param, other_dict)

    def _handle_create_ticket(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.debug_print("create ticket called")

        other = param.get("field_values")
        if other:
            try:
                other_dict = json.loads(other)
            except Exception as e:
                error_message = self._get_error_message_from_exception(e)
                return action_result.set_status(phantom.APP_ERROR, "Error reading 'field_values'", error_message)
        else:
            other_dict = {}

        for k, v in list(param.items()):
            if k in sf_consts.CASE_FIELD_MAP:
                other_dict[sf_consts.CASE_FIELD_MAP[k]] = v

        return self._create_object(action_result, param, other_dict)

    def _delete_object(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.debug_print("delete object called")
        sobject = param.get("sobject", "Case")
        obj_id = param["id"]

        endpoint = sf_consts.API_ENDPOINT_OBJECT_ID.format(version=self._version_uri, sobject=sobject, id=obj_id)

        ret_val, _response = self._make_rest_call_helper(endpoint, action_result, method="delete")
        if phantom.is_fail(ret_val):
            return ret_val

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully deleted the {sobject}")

    def _handle_delete_object(self, param):
        return self._delete_object(param)

    def _handle_delete_ticket(self, param):
        self.debug_print("delete ticket called")
        return self._delete_object(param)

    def _update_object(self, action_result, param, field_values):
        self.debug_print("update object called")
        sobject = param.get("sobject", "Case")
        obj_id = param["id"]

        endpoint = sf_consts.API_ENDPOINT_OBJECT_ID.format(version=self._version_uri, sobject=sobject, id=obj_id)

        ret_val, response = self._make_rest_call_helper(endpoint, action_result, json=field_values, method="patch")
        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["obj_id"] = obj_id

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully updated the {sobject}")

    def _handle_update_object(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        other = param.get("field_values")
        try:
            other_dict = json.loads(other)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, "Error reading 'field_values'", error_message)

        return self._update_object(action_result, param, other_dict)

    def _handle_update_ticket(self, param):
        self.debug_print("update ticket called")
        action_result = self.add_action_result(ActionResult(dict(param)))

        other = param.get("field_values")
        if other:
            try:
                other_dict = json.loads(other)
            except Exception as e:
                error_message = self._get_error_message_from_exception(e)
                return action_result.set_status(phantom.APP_ERROR, "Error reading 'field_values'", error_message)
        else:
            other_dict = {}

        for k, v in list(param.items()):
            if k in sf_consts.CASE_FIELD_MAP:
                other_dict[sf_consts.CASE_FIELD_MAP[k]] = v

        if not other_dict:
            return action_result.set_status(phantom.APP_ERROR, "Please provide at least one optional parameter for updating the Case")

        return self._update_object(action_result, param, other_dict)

    def _get_listview_results_url(self, action_result, endpoint, view_name):
        found_views = []
        done = False

        while not done:
            ret_val, response = self._make_rest_call_helper(endpoint, action_result)
            if phantom.is_fail(ret_val):
                return ret_val, None, None
            done = response["done"]
            if not done:
                endpoint = response["nextRecordsUrl"]

            for view in response["listviews"]:
                if view_name and view["developerName"] == view_name:
                    return phantom.APP_SUCCESS, view["resultsUrl"], None
                found_views.append(view["developerName"])

        # Was not able to find view
        return phantom.APP_SUCCESS, None, found_views

    def _mogrify_record(self, record):
        # Transform a list of JSON objects into a dictionary
        columns = record["columns"]
        columns_dict = {x.pop("fieldNameOrPath").replace(".", "_"): x for x in columns}
        record["columns"] = columns_dict
        return record

    def _get_listview_results_records(self, action_result, endpoint, offset, limit):
        max_page_size = 2000
        records = []
        while True:
            params = {"limit": max_page_size, "offset": offset}

            ret_val, response = self._make_rest_call_helper(endpoint, action_result, params=params)

            if phantom.is_fail(ret_val):
                if "Maximum SOQL offset allowed is" in action_result.get_message():
                    self.save_progress("Because of the limitation of the offset value in the API, returning the maximum possible records")
                    self.debug_print("Because of the limitation of the offset value in the API, returning the maximum possible records")
                    self.debug_print(f"Response from the API: {action_result.get_message()}")
                    break
                return ret_val

            records.extend(response.get("records", []))

            if len(records) >= limit:
                records = records[:limit]
                break

            if len(response.get("records", [])) < max_page_size:
                break

            offset += max_page_size

        for record in records:
            action_result.add_data(self._mogrify_record(record))

        action_result.update_summary({"num_objects": action_result.get_data_size()})
        return phantom.APP_SUCCESS

    def _list_objects(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        sobject = param.get("sobject", "Case")
        view_name = param.get("view_name")

        endpoint = sf_consts.API_ENDPOINT_GET_LISTVIEWS.format(version=self._version_uri, sobject=sobject)

        ret_val, results_url, views = self._get_listview_results_url(action_result, endpoint, view_name)
        if phantom.is_fail(ret_val):
            return ret_val
        elif not results_url and view_name:
            # They searched for an invalid view
            action_result.update_summary({"view_names": views})
            return action_result.set_status(phantom.APP_ERROR, "Specified list view name was not found")
        elif not results_url and not view_name:
            # Just return a list of valid views
            action_result.update_summary({"view_names": views})
            return action_result.set_status(phantom.APP_SUCCESS, "Listed the valid view names")

        # validate limit parameter
        ret_val, limit = self._validate_integers(action_result, param.get("limit", 25), "limit")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # validate offset parameter
        ret_val, offset = self._validate_integers(action_result, param.get("offset", 0), "offset", allow_zero=True)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Retrieve the list of objects
        endpoint = results_url
        ret_val = self._get_listview_results_records(action_result, endpoint, offset, limit)
        if phantom.is_fail(ret_val):
            return ret_val

        if "Maximum SOQL offset allowed is" in action_result.get_message():
            message = "Because of the limitation of the offset value in the API, returning the maximum possible records."
            message += f"Response from the API: {action_result.get_message()}"
        else:
            message = f"Successfully fetched a list of {sobject} objects"

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _handle_list_objects(self, param):
        return self._list_objects(param)

    def _handle_list_tickets(self, param):
        return self._list_objects(param)

    def _get_object(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        sobject = param.get("sobject", "Case")
        obj_id = param["id"]

        endpoint = sf_consts.API_ENDPOINT_OBJECT_ID.format(version=self._version_uri, sobject=sobject, id=obj_id)

        ret_val, response = self._make_rest_call_helper(endpoint, action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully retrieved {sobject}")

    def _handle_get_object(self, param):
        self.debug_print("update object called")
        return self._get_object(param)

    def _handle_get_ticket(self, param):
        self.debug_print("get ticket called")
        return self._get_object(param)

    def _handle_post_chatter(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.debug_print("post chatter called")

        parent_case_id = param["id"]
        body = param["body"]
        title = param.get("title")

        new_feed_item = {"ParentId": parent_case_id, "Title": title, "Body": body, "Type": "TextPost"}

        ret_val = self._create_object(action_result, {"sobject": "FeedItem"}, new_feed_item)
        if phantom.is_fail(ret_val):
            return ret_val

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully posted to chatter")

    def _object_response_to_container(self, response, sobject):
        container = {}
        artifact = {}
        cef = {}
        cef_types = {}

        container["artifacts"] = [artifact]
        artifact["cef"] = cef
        artifact["cef_types"] = cef_types

        skip_field_names = {"attributes"}

        severity_mapping = {
            "severity 1 (high impact)": "high",
            "severity 2 (medium impact": "medium",
            "severity 3 (low impact)": "low",
            "severity 4 (false positive)": "low",
        }

        sensitivity_mapping = {"sensitive": "red", "not sensitive": "white"}

        container_name = None

        for k, v in list(response.items()):
            if k in skip_field_names:
                continue
            name = self._cef_name_map.get(k, k)
            cef[name] = v
            if k.endswith("Id") and v is not None:
                cef_types[name] = ["salesforce object id"]

            if name == "Subject":
                container_name = v

        if container_name is None:
            number = response.get("CaseNumber") or response.get("Id", "")
            container_name = f"Salesforce {sobject} Object # {number}"

        container["name"] = container_name
        artifact["name"] = sobject

        try:
            if not self._last_viewed_date:
                artifact["cef"].pop("LastViewedDate")
                artifact["cef"].pop("LastReferencedDate")
                self.save_progress("Removed LastViewedDate and LastReferencedDate from the artifact.")
        except:
            self.debug_print(
                "LastViewedDate or LastReferencedDate may not be present in the artifact. Unable to remove LastViewedDate from the artifact"
            )
            pass

        try:
            artifact["source_data_identifier"] = hashlib.sha256(json.dumps(artifact)).hexdigest()
            container["source_data_identifier"] = hashlib.sha256("{}{}".format(sobject, response["Id"])).hexdigest()
        except:
            artifact["source_data_identifier"] = hashlib.sha256(json.dumps(artifact).encode()).hexdigest()
            container["source_data_identifier"] = hashlib.sha256("{}{}".format(sobject, response["Id"]).encode()).hexdigest()

        severity = response.get("Incident_Severity__c")
        if severity:
            container["severity"] = severity_mapping.get(severity.lower(), "medium")

        sensitivity = response.get("Incident_Sensitivity__c")
        if sensitivity:
            container["sensitivity"] = sensitivity_mapping.get(sensitivity.lower(), "amber")

        return container

    def _batch_response_to_containers(self, response, sobject):
        containers = []

        self.debug_print("BATCH REQUEST HAS ERRORS: {}".format(response["hasErrors"]))

        results = response["results"]
        for result in results:
            if result["statusCode"] != 200:
                self.debug_print(f"Got bad status code for response: {result}")
                continue

            # response here matches a single call to get object endpoint
            response = result["result"]
            containers.append(self._object_response_to_container(response, sobject))

        return containers

    def _create_containers_from_records(self, action_result, records, sobject):
        num_records = len(records)
        cur_index = 0
        # Number of requests per batch (API only supports 25)
        num_batch = 25
        containers = []

        endpoint = sf_consts.API_ENDPOINT_BATCH_REQUEST.format(version=self._version_uri)

        # Since we need to individually retrieve each object, we can reduce the total number
        #  of API calls we need to make by using batch requests (up to 25x less!)
        while cur_index < num_records:
            batch_records = records[cur_index : cur_index + num_batch]
            batch_request = []
            for record in batch_records:
                batch_request.append(
                    {
                        "method": "GET",
                        "url": sf_consts.API_ENDPOINT_OBJECT_ID.format(
                            version=self._version_uri, sobject=sobject, id=record["fields"]["Id"]["value"]
                        ),
                    }
                )

            data = {"batchRequests": batch_request}

            ret_val, response = self._make_rest_call_helper(endpoint, action_result, json=data, method="post")
            if phantom.is_fail(ret_val):
                return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error retrieving objects: {action_result.get_message()}"))

            containers.extend(self._batch_response_to_containers(response, sobject))

            cur_index += num_batch

        return RetVal(phantom.APP_SUCCESS, containers)

    def _poll_for_all_objects(self, action_result, endpoint, offset, max_containers):
        MAX_OBJECTS_PER_POLL = 2000

        records = []
        while True:
            params = {"sortBy": "LastModifiedDate", "pageSize": MAX_OBJECTS_PER_POLL, "pageToken": offset}
            ret_val, response = self._make_rest_call_helper(endpoint, action_result, params=params)
            if phantom.is_fail(ret_val):
                if "Maximum SOQL offset allowed is" in action_result.get_message():
                    self.save_progress("Because of the limitation of the offset value in the API, returning the maximum possible records")
                    self.debug_print("Because of the limitation of the offset value in the API, returning the maximum possible records")
                    self.debug_print(f"Response from the API: {action_result.get_message()}")
                    return RetVal(offset, records)
                return RetVal(None, None)

            records.extend(response.get("records", []))

            if max_containers and len(records) >= max_containers:
                offset += len(records[:max_containers])
                records = records[:max_containers]
                break

            if len(response.get("records", [])) < MAX_OBJECTS_PER_POLL:
                offset += len(response.get("records", []))
                break

            offset += MAX_OBJECTS_PER_POLL

        return RetVal(offset, records)

    def _handle_on_poll(self, param):
        config = self.get_config()
        action_result = self.add_action_result(ActionResult(dict(param)))

        sobject = config.get("poll_sobject", "Case")
        view_name = config.get("poll_view_name")
        cef_name_map = config.get("cef_name_map")
        self._last_viewed_date = config.get("last_view_date", False)
        if cef_name_map:
            try:
                self._cef_name_map = json.loads(cef_name_map)
            except Exception as e:
                error_message = self._get_error_message_from_exception(e)
                return action_result.set_status(phantom.APP_ERROR, f"Error parsing cef_name_map {error_message}")

            # Validate JSON file
            for k, v in self._cef_name_map.items():
                if not isinstance(v, str):
                    msg = f"{k} key's value is not string in JSON file which contains mapping of Salesforce to CEF fields"
                    return action_result.set_status(phantom.APP_ERROR, msg)

                if v.strip() == "" or k.strip() == "":
                    msg = "Please add non-empty key or value in JSON file which contains mapping of Salesforce to CEF fields"
                    return action_result.set_status(phantom.APP_ERROR, msg)
        else:
            self._cef_name_map = {}

        max_containers = None

        if view_name is None:
            return action_result.set_status(phantom.APP_ERROR, "Error: Must specify poll_view_name")

        if self.is_poll_now():
            cur_offset = 0
            # validate container_count parameter
            ret_val, max_containers = self._validate_integers(action_result, param.get("container_count", 10), "container_count")
            if phantom.is_fail(ret_val):
                return action_result.get_status()
        else:
            # validate cur_offset parameter
            ret_val, cur_offset = self._validate_integers(action_result, self._state.get("cur_offset", 0), "cur_offset", allow_zero=True)
            if phantom.is_fail(ret_val):
                return action_result.get_status()

            # validate first_ingestion_max parameter
            if not cur_offset:
                ret_val, max_containers = self._validate_integers(action_result, config.get("first_ingestion_max", 10), "first_ingestion_max")
                if phantom.is_fail(ret_val):
                    return action_result.get_status()

        self.save_progress(f"Getting view {view_name} from {sobject} object using {self._version_uri} version")

        list_view_from_obj_url = sf_consts.API_ENDPOINT_GET_LISTVIEWS_FROM_OBJECT.format(
            version=self._version_uri, sobject=sobject, view_name=view_name
        )

        new_offset, records = self._poll_for_all_objects(action_result, list_view_from_obj_url, cur_offset, max_containers)

        if "The requested resource does not exist" in action_result.get_message():
            return action_result.set_status(phantom.APP_ERROR, "No listview with that specified name was found")

        if new_offset is None:
            return action_result.get_status()

        ret_val, containers = self._create_containers_from_records(action_result, records, sobject)
        if phantom.is_fail(ret_val):
            return ret_val

        self.save_progress("Saving containers")

        for container in containers:
            container_artifact = container.pop("artifacts")
            ret_val, msg, container_id = self.save_container(container)
            if phantom.is_fail(ret_val):
                self.save_progress(f"Error saving container: {msg}")

            for artifact in container_artifact:
                artifact["container_id"] = container_id
            ret_val, status_string, _artifact_ids = self.save_artifacts(container_artifact)
            if phantom.is_fail(ret_val):
                self.save_progress(f"Error saving artifacts: {status_string}")

        if not self.is_poll_now():
            self._state["cur_offset"] = new_offset

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully ingested containers")

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "run_query":
            ret_val = self._handle_run_query(param)

        elif action_id == "create_object":
            ret_val = self._handle_create_object(param)

        elif action_id == "create_ticket":
            ret_val = self._handle_create_ticket(param)

        elif action_id == "delete_object":
            ret_val = self._handle_delete_object(param)

        elif action_id == "delete_ticket":
            ret_val = self._handle_delete_ticket(param)

        elif action_id == "update_object":
            ret_val = self._handle_update_object(param)

        elif action_id == "update_ticket":
            ret_val = self._handle_update_ticket(param)

        elif action_id == "get_object":
            ret_val = self._handle_get_object(param)

        elif action_id == "get_ticket":
            ret_val = self._handle_get_ticket(param)

        elif action_id == "list_objects":
            ret_val = self._handle_list_objects(param)

        elif action_id == "list_tickets":
            ret_val = self._handle_list_tickets(param)

        elif action_id == "post_chatter":
            ret_val = self._handle_post_chatter(param)

        elif action_id == "on_poll":
            ret_val = self._handle_on_poll(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()
        config = self.get_config()

        self._username = config.get("username")
        self._password = config.get("password")

        if config.get("use_client_credentials"):
            self._auth_flow = self.CLIENT_CREDENTIALS
        elif self._username:
            if not self._password:
                return self.set_status(phantom.APP_ERROR, "Password must be specified with a username")
            self._auth_flow = self.USERNAME_PASSWORD

        if self.get_action_identifier() != "test_connectivity":
            try:
                self._version_uri = self._state["latest_version"]
            except KeyError:
                return self.set_status(phantom.APP_ERROR, "Unable to retrieve API version. Has test connectivity been ran?")
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
        login_url = BaseConnector._get_phantom_base_url() + "login"
        try:
            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=sf_consts.SALESFORCE_DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, json=data, headers=headers, timeout=sf_consts.SALESFORCE_DEFAULT_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = SalesforceConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
