# File: cofensevision_utils.py
#
# Copyright (c) 2023-2026 Cofense
#
# This unpublished material is proprietary to Cofense.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Cofense.
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


import os
import uuid
from collections import OrderedDict
from datetime import datetime

import encryption_helper
import phantom.app as phantom
import phantom.rules as phantom_rules
import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
from phantom.vault import Vault

import cofensevision_consts as consts


class RetVal(tuple):
    """This class returns the tuple of two elements."""

    def __new__(cls, val1, val2=None):
        """Create a new tuple object."""
        return tuple.__new__(RetVal, (val1, val2))


class CofenseVisionUtils:
    """This class holds all the util methods."""

    def __init__(self, connector=None):
        """Util constructor method."""
        self._connector = connector
        self._access_token = None
        self.filename = None

        # The response from the 'get message' action comes as plain text with an application/json header.
        # These variables are used to process a response for this peculiar API behavior.
        self._get_token = False
        self._is_generate_token = False

        if connector:
            # Decrypt the state file
            connector.state = self._decrypt_state(connector.state)
            self._access_token = connector.state.get(consts.VISION_STATE_TOKEN, {}).get(consts.VISION_STATE_ACCESS_TOKEN)

    def _get_error_message_from_exception(self, e):
        """Get an appropriate error message from the exception.

        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_msg = consts.VISION_ERROR_MESSAGE_UNAVAILABLE

        self._connector.error_print("Error occurred.", e)
        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except Exception as e:
            self._connector.error_print(f"Error occurred while fetching exception information. Details: {e!s}")

        if not error_code:
            error_text = f"Error message: {error_msg}"
        else:
            error_text = f"Error code: {error_code}. Error message: {error_msg}"

        return error_text

    # Validations
    def validate_integer(self, action_result, parameter, key, allow_zero=False, max_value=None):
        """Check if the provided input parameter value is valid.

        :param action_result: Action result or BaseConnector object
        :param parameter: Input parameter value
        :param key: Input parameter key
        :param allow_zero: Zero is allowed or not (default False)
        :param max_value: Maximum allowed value
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and parameter value itself.
        """
        try:
            if not float(parameter).is_integer():
                return action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_INT_PARAM.format(key=key)), None

            parameter = int(parameter)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_INT_PARAM.format(key=key)), None

        if parameter < 0:
            return action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_NEGATIVE_INT_PARAM.format(key=key)), None
        if not allow_zero and parameter == 0:
            return action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_ZERO_INT_PARAM.format(key=key)), None
        if max_value and parameter > max_value:
            return action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_MAX_ALLOWED_INT_PARAM.format(max=max_value, key=key)), None

        return phantom.APP_SUCCESS, parameter

    # Parsing
    def _process_empty_response(self, response, action_result):
        """Process the empty response returned from the server.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and an empty dictionary
        """
        if response.status_code in [200, 204]:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_EMPTY_RESPONSE.format(response.status_code)))

    def _process_html_response(self, response, action_result):
        """Process the html response returned from the server.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_ERROR and the None value
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

        message = consts.VISION_ERROR_GENERAL_MESSAGE.format(status_code, error_text)
        message = message.replace("{", "{{").replace("}", "}}")

        # Large HTML pages may be returned by the wrong URLs.
        # Use default error message in place of large HTML page.
        if len(message) > 500:
            return RetVal(action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_HTML_RESPONSE))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message))

    def _process_json_response(self, response, action_result):
        """Process the json response returned from the server.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and the response dictionary
        """
        try:
            # Token endpoint doesn't return json response
            if self._get_token and not self._is_generate_token:
                resp_json = {"token": response.text}
            else:
                resp_json = response.json()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_JSON_RESPONSE.format(error_message)))

        # Please specify the status codes here
        if 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = consts.VISION_ERROR_GENERAL_MESSAGE.format(response.status_code, response.text.replace("{", "{{").replace("}", "}}"))
        message = f"Error from server. {message}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message))

    def _add_file_to_vault(self, action_result, local_dir, long_filename=None):
        """Add the file to the Vault.

        :param action_result: Action result or BaseConnector object
        :param local_dir: Directory where the file to be saved is stored
        param long_filename: Long filename of the file
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and the vault information
        """
        container_id = self._connector.get_container_id()
        file_name = long_filename or self.filename
        vault_file = None

        # Add file to the vault
        self._connector.debug_print("Adding file to the Vault")
        success, message, vault_id = phantom_rules.vault_add(
            container=container_id, file_location=f"{local_dir}/{self.filename}", file_name=file_name
        )

        if not success:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Could not add file to the Vault: {message}"))

        self._connector.debug_print("Added file to the Vault")

        # Retrieve stored file information
        success, message, vault_info = phantom_rules.vault_info(vault_id, container_id=container_id)

        if not (success or vault_info):
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Could not find the file in the Vault: {message}"))

        # Find the file with the current filename from the list of files having the same ID
        for file in vault_info:
            if file.get("name") == file_name:
                vault_file = file
                break

        # Cleanup temp dir
        try:
            self._connector.debug_print("Deleting temporary directory")
            if os.path.exists(local_dir):
                os.rmdir(local_dir)
        except Exception as e:
            self._connector.debug_print(f"Unable to delete the temporary directory: {self._get_error_message_from_exception(e)}")

        if vault_file:
            return RetVal(phantom.APP_SUCCESS, vault_file)

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Could not find the file in the Vault"))

    def _process_stream_response(self, response, action_result):
        """Process the stream response returned from the server, saves it to a file and adds it to the vault.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and vault info
        """
        long_filename = None
        if not (200 <= response.status_code < 399):
            message = consts.VISION_ERROR_GENERAL_MESSAGE.format(response.status_code, response.text.replace("{", "{{").replace("}", "}}"))
            message = f"Error from server. {message}"

            return RetVal(action_result.set_status(phantom.APP_ERROR, message))

        guid = uuid.uuid4()

        if hasattr(Vault, "get_vault_tmp_dir"):
            vault_tmp_dir = Vault.get_vault_tmp_dir().rstrip("/")
            local_dir = f"{vault_tmp_dir}/{guid}"
        else:
            local_dir = f"/opt/phantom/vault/tmp/{guid}"

        self._connector.debug_print("Creating temporary vault directory")

        try:
            os.makedirs(local_dir)
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, f"Unable to create temporary Vault folder {self._get_error_message_from_exception(e)}"
                )
            )

        if len(self.filename) >= 255:
            long_filename, ext = os.path.splitext(self.filename)
            self.filename = f"{uuid.uuid4()}{ext}"

        file_path = f"{local_dir}/{self.filename}"

        # Save the stream response to the file
        try:
            with open(file_path, "wb") as f:
                self._connector.debug_print("Writing data to the file")
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Unable to write file to disk. Error: {self._get_error_message_from_exception(e)}"),
                None,
            )

        return self._add_file_to_vault(action_result, local_dir, long_filename)

    def _process_response(self, response, action_result):
        """Process the response returned from the server.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and the response dictionary
        """
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": response.status_code})
            action_result.add_debug_data({"r_headers": response.headers})
            if "stream" not in response.headers.get("Content-Type", ""):
                action_result.add_debug_data({"r_text": response.text})

        # Process each 'Content-Type' of response separately
        # Process a json response
        if "json" in response.headers.get("Content-Type", ""):
            return self._process_json_response(response, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in response.headers.get("Content-Type", ""):
            return self._process_html_response(response, action_result)

        # Process file response
        if "stream" in response.headers.get("Content-Type", ""):
            return self._process_stream_response(response, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not response.text:
            return self._process_empty_response(response, action_result)

        # everything else is actually an error at this point
        message = consts.VISION_ERROR_GENERAL_MESSAGE.format(response.status_code, response.text.replace("{", "{{").replace("}", "}}"))
        message = f"Can't process response from server. {message}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message))

    def make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        """Make an REST API call and passes the response to the process method.

        :param endpoint: The endpoint string to make the REST API request
        :param action_result: Action result or BaseConnector object
        :param method: The HTTP method for API request
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and the response dictionary returned by the process response method
        """
        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"))

        # Create a URL to connect to
        url = f"{self._connector.config['base_url'].strip('/')}{endpoint}"

        try:
            response = request_func(
                url, timeout=consts.VISION_REQUEST_TIMEOUT, verify=self._connector.config.get("verify_server_cert", False), **kwargs
            )
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_REST_CALL.format(error_message)))

        return self._process_response(response, action_result)

    def _set_is_generate_token(func):
        """Set the flags for the generate token method."""

        def inner_func(self, action_result):
            self._is_generate_token = True
            self._connector.is_state_updated = True
            ret_val = func(self, action_result)
            self._is_generate_token = False
            return ret_val

        return inner_func

    @_set_is_generate_token
    def generate_token(self, action_result):
        """Generate a new access token using the provided credentials and stores it to the state file.

        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        data = {
            "client_id": self._connector.config["client_id"],
            "client_secret": self._connector.config["client_secret"],
            "grant_type": "client_credentials",
        }

        ret_val, resp_json = self.make_rest_call(consts.VISION_ENDPOINT_TOKEN, action_result, data=data, method="post", headers=headers)
        if phantom.is_fail(ret_val):
            self._connector.state.pop(consts.VISION_STATE_TOKEN, None)
            return action_result.get_status()

        # Reset the header with authorization key
        try:
            self._access_token = resp_json[consts.VISION_STATE_ACCESS_TOKEN]
        except KeyError:
            self._connector.debug_print("Unable to find the access token from the returned response")
            self._connector.state.pop(consts.VISION_STATE_TOKEN, None)
            return action_result.set_status(phantom.APP_ERROR, "Token generation failed")

        self._connector.state[consts.VISION_STATE_TOKEN] = resp_json

        self._connector.debug_print("Token generated successfully")
        return action_result.set_status(phantom.APP_SUCCESS)

    def make_rest_call_helper(self, endpoint, action_result, method="get", headers=None, **kwargs):
        """Make the REST API call and generates new token if required.

        :param endpoint: The endpoint string to make the REST API request
        :param action_result: Action result or BaseConnector object
        :param method: The HTTP method for API request
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and the response dictionary
        """
        if not headers or not isinstance(headers, dict):
            headers = dict(consts.VISION_DEFAULT_HEADERS)
        else:
            headers.update(consts.VISION_DEFAULT_HEADERS)

        if kwargs.get("stream"):
            headers.pop("Accept", None)

        if self._access_token:
            headers.update({"Authorization": f"Bearer {self._access_token}"})
            ret_val, resp_json = self.make_rest_call(endpoint, action_result, method, headers=headers, **kwargs)
            if phantom.is_success(ret_val):
                return RetVal(phantom.APP_SUCCESS, resp_json)
            if consts.VISION_MESSAGE_EXPIRED_TOKEN not in action_result.get_message():
                return RetVal(action_result.get_status())
            self._connector.debug_print("Token is invalid/expired. Hence, generating a new token.")
        else:
            self._connector.debug_print("Token is not available. Hence, generating a new token.")

        # The token is either expired or not present in the state file, generate a new token.
        ret_val = self.generate_token(action_result)
        if phantom.is_fail(ret_val):
            return RetVal(action_result.get_status())

        headers.update({"Authorization": f"Bearer {self._access_token}"})
        ret_val, resp_json = self.make_rest_call(endpoint, action_result, method, headers=headers, **kwargs)
        if phantom.is_fail(ret_val):
            return RetVal(action_result.get_status())

        return RetVal(phantom.APP_SUCCESS, resp_json)

    def encrypt_state(self, state):
        """Encrypt the state file.

        :param state: state dictionary to be encrypted
        :return: state dictionary with encrypted token
        """
        try:
            if state.get(consts.VISION_STATE_TOKEN, {}).get(consts.VISION_STATE_ACCESS_TOKEN):
                state[consts.VISION_STATE_TOKEN][consts.VISION_STATE_ACCESS_TOKEN] = encryption_helper.encrypt(
                    state[consts.VISION_STATE_TOKEN][consts.VISION_STATE_ACCESS_TOKEN], self._connector.get_asset_id()
                )
        except Exception as e:
            self._connector.debug_print("Error occurred while encrypting the state file.", e)
            state = {"app_version": self._connector.get_app_json().get("app_version")}
        return state

    def _decrypt_state(self, state):
        """Decrypt the state file.

        :param state: state dictionary to be decrypted
        :return: state dictionary with decrypted token
        """
        try:
            if state.get(consts.VISION_STATE_TOKEN, {}).get(consts.VISION_STATE_ACCESS_TOKEN):
                state[consts.VISION_STATE_TOKEN][consts.VISION_STATE_ACCESS_TOKEN] = encryption_helper.decrypt(
                    state[consts.VISION_STATE_TOKEN][consts.VISION_STATE_ACCESS_TOKEN], self._connector.get_asset_id()
                )
        except Exception as e:
            self._connector.debug_print("Error occurred while decrypting the state file.", e)
            state = {"app_version": self._connector.get_app_json().get("app_version")}
        return state

    def split_value_list(self, values, delimiter=","):
        """Separate values with the provided delimiter.

        :param values: string value to split
        :param delimiter: delimiter to split with
        :return: list of separated values
        """
        values = [value.strip() for value in values.split(delimiter)]
        values = list(filter(None, values))
        # Remove duplicates by preserving the order
        values = list(OrderedDict.fromkeys(values))
        return values

    def parse_date_string(self, value, default_value=False):
        """Parse the date and converts it to the specified format.

        :param values: string value to parse
        :param default_value: Boolean to return the default value if not provided
        :return: phantom.APP_SUCCESS/phantom.APP_ERROR and parsed date
        """
        if not value:
            if default_value:
                return phantom.APP_SUCCESS, datetime.utcnow().strftime(consts.VISION_DATE_FORMAT)
            return phantom.APP_SUCCESS, None
        try:
            date = parse(value)
            return phantom.APP_SUCCESS, date.strftime(consts.VISION_DATE_FORMAT)
        except Exception:
            return phantom.APP_ERROR, None

    def validate_sort_param(self, values):
        """Parse the sort parameter and converts it to the required format.

        :param values: string value to parse
        :return: phantom.APP_SUCCESS/phantom.APP_ERROR and list of sort order
        """
        if not values:
            return phantom.APP_SUCCESS, None

        sort_fields = consts.VISION_SUPPORTED_SORT_FIELDS.get(self._connector.get_action_identifier(), [])
        final_list = []
        value_list = self.split_value_list(values)
        for value in value_list:
            sort_property = self.split_value_list(value, ":")
            if len(sort_property) == 1:
                if sort_property[0] not in sort_fields:
                    return phantom.APP_ERROR, None
            elif len(sort_property) == 2:
                if sort_property[0] not in sort_fields:
                    return phantom.APP_ERROR, None
                if sort_property[1] not in consts.VISION_VALID_SORT_ORDER:
                    return phantom.APP_ERROR, None
            else:
                return phantom.APP_ERROR, None
            final_list.append(",".join(sort_property))

        return phantom.APP_SUCCESS, final_list
