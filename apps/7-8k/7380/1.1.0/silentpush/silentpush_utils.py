# File: silentpush_utils.py
#
# Copyright (c) 2024-2025 Splunk Inc.
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
import re
import tempfile
import time
import uuid

import phantom.app as phantom
import phantom.rules as ph_rules
import requests
from bs4 import BeautifulSoup
from phantom.vault import Vault

import silentpush_consts as consts


class RetVal(tuple):
    """Return a tuple of two elements."""

    def __new__(cls, val1, val2=None):
        """Create a new tuple object."""
        return tuple.__new__(RetVal, (val1, val2))


class SilentpushUtils:
    """This class holds all the util methods."""

    def __init__(self, connector=None):
        self._connector = connector

    def _get_error_message_from_exception(self, e):
        """Get an appropriate error message from the exception.

        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_msg = consts.ERROR_MESSAGE_UNAVAILABLE

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

    def _process_empty_response(self, response, action_result):
        if response.status_code in consts.EMPTY_RESPONSE_STATUS_CODES:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, f"Empty response and no information in the header, Status Code: {response.status_code}"),
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

        message = consts.ERROR_GENERAL_MESSAGE.format(status_code, error_text)
        message = message.replace("{", "{{").replace("}", "}}")

        # Large HTML pages may be returned by the wrong URLs.
        # Use default error message in place of large HTML page.
        if len(message) > 500:
            return RetVal(action_result.set_status(phantom.APP_ERROR, consts.ERROR_HTML_RESPONSE))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message))

    def _process_json_response(self, r, action_result, error_path=None):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {e!s}"), None)

        # Please specify the status codes here
        self._connector.error_print("Response", resp_json)
        if 200 <= r.status_code <= 399:
            if isinstance(resp_json, dict) and resp_json.get("status_code"):
                if 200 <= resp_json.get("status_code") <= 399:
                    if not error_path or not self.find_value_by_pattern(resp_json, error_path):
                        return RetVal(phantom.APP_SUCCESS, resp_json)
            else:
                return RetVal(phantom.APP_SUCCESS, resp_json)

        if self._connector.get_action_identifier() == "get_data_export":
            if 400 == r.status_code:
                if isinstance(resp_json, dict) and error_path:
                    return RetVal(
                        action_result.set_status(
                            phantom.APP_ERROR, f"Failed to fetch feed data: {self.find_value_by_pattern(resp_json, error_path) or resp_json}"
                        ),
                        resp_json,
                    )

        # You should process the error returned in the json
        message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message))

    def extract_uuid(self, url):
        match = re.search(r"/([a-f0-9A-F\-]{36})", url)
        if match:
            return match.group(1)
        return None

    def find_value_by_pattern(self, data, pattern):
        """Find value in JSON data using pattern."""
        keys = pattern.split(".")
        current_data = data

        for key in keys:
            if isinstance(current_data, dict):
                current_data = current_data.get(key)
            elif isinstance(current_data, list):
                try:
                    index = int(key)
                    current_data = current_data[index]
                except Exception:
                    return None
            else:
                return None

            if current_data is None:
                return None

        return current_data

    def _process_response(self, r, action_result, error_path=None, url=None):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result, error_path)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in r.headers.get("Content-Type", "") and r.text:
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        if self._connector.get_action_identifier() == "get_data_export":
            ret_val, vault_id = self._add_response_to_vault(r.text, action_result, url)
            return RetVal(ret_val, vault_id)
        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _add_response_to_vault(self, response, action_result, endpoint):
        """Add response to vault"""
        self._connector.save_progress("Adding data to vault")
        if not response:
            message = "No data found"
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error adding file to the vault: {message}"), None)

        with tempfile.NamedTemporaryFile(mode="w", dir=Vault.get_vault_tmp_dir(), delete=False, encoding="utf-8") as f:
            tmp_file_path = f.name
            f.write(response)
        feed_uuid = self.extract_uuid(endpoint) or uuid.uuid1()
        file_name = f"feed_{feed_uuid}.csv"
        self._connector.save_progress(f"Filename for vault attachment: {file_name}")
        success, msg, vault_id = ph_rules.vault_add(
            container=self._connector.get_container_id(),
            file_location=tmp_file_path,
            file_name=file_name,
        )
        if not success:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error adding file to the vault, Error: {msg}"), None)

        return RetVal(action_result.set_status(phantom.APP_SUCCESS, consts.ACTION_GET_DATA_EXPORT_SUCCESS_RESPONSE), vault_id)

    def make_rest_call(self, endpoint, action_result, method="get", error_path=None, **kwargs):
        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = f"{consts.BASE_URL.strip('/')}{endpoint}"

        if self._connector.get_action_identifier() == "get_data_export":
            url = endpoint

        kwargs["headers"] = {**self.get_auth_headers(self._connector.config), **(kwargs.get("headers") or {})}

        status, r = self.invoke_api(request_func, url, counter=0, **kwargs)

        if not status:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {r!s}"), resp_json)

        return self._process_response(r, action_result, error_path, url)

    def make_rest_call_for_image(self, url, action_result):
        try:
            response = requests.get(
                url,
                timeout=consts.REQUEST_DEFAULT_TIMEOUT,
            )

            if response.status_code == 200:
                return action_result.set_status(phantom.APP_SUCCESS), response.content
            return action_result.set_status(phantom.APP_ERROR, "Failed to download screenshot")
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to download screenshot. Details: {e}")

    def invoke_api(self, request_func, url, counter=0, **kwargs):
        timeout = consts.REQUEST_DEFAULT_TIMEOUT
        if self._connector.get_action_identifier() == "get_data_export":
            timeout = consts.EXPORT_REQUEST_DEFAULT_TIMEOUT
        try:
            r = request_func(url, timeout=timeout, verify=self._connector.config.get("verify_server_cert", False), **kwargs)
            return True, r
        except Exception as e:
            if "ConnectTimeoutError" in str(e) and counter < consts.MAX_RETRIES:
                self._connector.debug_print(f"Connection timeout while making a rest call. Retrying {counter + 2} time")
                time.sleep(10)
                return self.invoke_api(request_func, url, counter + 1, **kwargs)
            return False, e

    def get_auth_headers(self, config):
        headers = {}

        if config.get("api_key"):
            headers["X-API-KEY"] = config.get("api_key")

        return headers

    def generate_json_body(self, body, allow_none, allow_empty, param, default_values):
        def _get_empty_value(_type):
            empty_values = {"string": "", "boolean": "", "integer": 0, "float": 0, "dict": {}, "list": []}
            return empty_values.get(_type, "")

        def _handle_template_value(key, value, body):
            if not isinstance(value, str) or not value.startswith("{{") or not value.endswith("}}"):
                body[key] = value
                return

            value = value.strip("{}")

            if value in param:
                body[key] = param.get(value)
            elif value in default_values:
                body[key] = default_values.get(value)
            elif value in allow_none:
                body[key] = None
            elif value in allow_empty:
                body[key] = _get_empty_value(allow_empty[value])

        def _format_value(input_body, body, path=()):
            for key, value in input_body.items():
                if isinstance(value, dict):
                    body[key] = _format_value(value, {}, (*path, key))
                else:
                    _handle_template_value(key, value, body)
            return body

        output_body = _format_value(body, {})
        return output_body


class Validator:
    @staticmethod
    def validate_integer(action_result, parameter, key, allow_zero=False, allow_negative=False):
        """Check if the provided input parameter value is valid.

        :param action_result: Action result or BaseConnector object
        :param parameter: Input parameter value
        :param key: Input parameter key
        :param allow_zero: Zero is allowed or not (default True)
        :param allow_negative: Negative values are allowed or not (default False)
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and parameter value itself.
        """
        try:
            if not float(parameter).is_integer():
                return action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_INT_PARAM.format(key=key)), None

            parameter = int(parameter)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_INT_PARAM.format(key=key)), None

        if not allow_zero and parameter == 0:
            return action_result.set_status(phantom.APP_ERROR, consts.ERROR_ZERO_INT_PARAM.format(key=key)), None
        if not allow_negative and parameter < 0:
            return action_result.set_status(phantom.APP_ERROR, consts.ERROR_NEG_INT_PARAM.format(key=key)), None

        return phantom.APP_SUCCESS, parameter

    @staticmethod
    def validate_dict(action_result, parameter, key):
        """Check if the provided input parameter value is a valid dictionary string.

        :param action_result: Action result or BaseConnector object
        :param parameter: Input parameter value
        :param key: Input parameter key
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and parameter value itself.
        """
        try:
            parameter = json.loads(parameter.replace("'", "'"))
        except Exception:
            try:
                parameter = eval(parameter)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_JSON_PARAM.format(key=key)), None

        if not isinstance(parameter, dict):
            return action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_JSON_PARAM.format(key=key)), None

        return phantom.APP_SUCCESS, parameter

    @staticmethod
    def validate_boolean(action_result, parameter, key):
        """Check if the provided input parameter value is a valid boolean.

        :param action_result: Action result or BaseConnector object
        :param parameter: Input parameter value
        :param key: Input parameter key
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and parameter value itself.
        """
        if not isinstance(parameter, bool):
            return action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_BOOL_PARAM.format(key=key)), None

        return phantom.APP_SUCCESS, parameter

    @staticmethod
    def validate_dropdown(action_result, parameter, key, dropdown):
        """Check if the provided input parameter value should be from dropdown.

        :param action_result: Action result or BaseConnector object
        :param parameter: Input parameter value
        :param key: Input parameter key
        :param dropdown: Value list
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and parameter value itself.
        """
        parameter = parameter.lower()
        if parameter not in dropdown:
            return action_result.set_status(
                phantom.APP_ERROR, consts.ERROR_INVALID_SELECTION.format(key, json.dumps(list(dropdown.keys())))
            ), None

        return phantom.APP_SUCCESS, dropdown.get(parameter)
