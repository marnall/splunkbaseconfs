# File: infoblox_utils.py
#
# Copyright 2025 Infoblox Inc.
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

import ipaddress
import json
import re
from datetime import datetime

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup

import infoblox_consts as consts


class RetVal(tuple):
    """Return a tuple of two elements."""

    def __new__(cls, val1, val2=None):
        """Create a new tuple object."""
        return tuple.__new__(RetVal, (val1, val2))


class InfobloxUtils:
    """This class holds all the util methods."""

    def __init__(self, connector=None):
        self._connector = connector

    def _get_error_message_from_exception(self, e):
        """
        Extracts the error message and error code from an exception object.

        Args:
            e (Exception): The exception object to extract the error message and error code from.

        Returns:
            str: The error message and error code in the format "Error code: {error_code}. Error message: {error_msg}".
                 If the error code is not present, only the error message is returned.
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
            action_result.set_status(
                phantom.APP_ERROR,
                f"Empty response and no information in the header, Status Code: {response.status_code}",
            ),
            None,
        )

    def _process_html_response(self, response, action_result):
        """
        Process an HTML response from a request.

        Args:
            response (requests.Response): The response object from the request.
            action_result (ActionResult): The action result object to set the status on.

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
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
            error_text = consts.ERROR_HTML_RESPONSE

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, response, action_result):
        """
        Process a JSON response from a request.

        Args:
            response (requests.Response): The response object from the request.
            action_result (ActionResult): The action result object to set the status on.

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
        """
        # First check if the response is empty - common with DELETE requests
        if not response.text or response.text.strip() == "":
            # For successful status codes, return success with empty dict
            if 200 <= response.status_code < 300:
                return RetVal(phantom.APP_SUCCESS, {})
            else:
                # For error status codes with empty response, create generic error message
                error_message = f"Error from server. Status Code: {response.status_code}"
                return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), {})
        # Try a json parse
        try:
            # First attempt the built-in json method
            resp_json = response.json()
        except Exception as e:
            # If that fails, try manual JSON parsing for text/plain content
            if "text/plain" in response.headers.get("Content-Type", "") and response.text:
                try:
                    resp_json = json.loads(response.text)
                    self._connector.debug_print("Successfully parsed plain/text response as JSON")
                except Exception as json_e:
                    return RetVal(
                        action_result.set_status(
                            phantom.APP_ERROR,
                            f"Unable to parse response as JSON. Error:{self._get_error_message_from_exception(json_e)}",
                        ),
                        None,
                    )
            else:
                return RetVal(
                    action_result.set_status(
                        phantom.APP_ERROR,
                        f"Unable to parse JSON response. Error: {self._get_error_message_from_exception(e)}",
                    ),
                    None,
                )

        # Please specify the status codes here
        if 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        error_message = f"Error from server. Status Code: {response.status_code}"

        # Try to extract error details from response
        if isinstance(resp_json, dict):
            # Handle nested error structure: {"error": [{"message": "..."}]}
            error_obj = resp_json.get("error")
            if isinstance(error_obj, list) and error_obj[0].get("message"):
                error_message += f" Message: {error_obj[0].get('message')}"
            # Handle direct error field
            elif error_obj:
                error_message += f" Error: {error_obj}"
            # Handle direct message field
            elif resp_json.get("message"):
                error_message += f" Message: {resp_json.get('message')}"
            # Handle detail field
            elif resp_json.get("detail"):
                error_message += f" Detail: {resp_json.get('detail')}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), resp_json)

    def _process_response(self, response, action_result):
        """
        Process the response from a request.

        Args:
            response (requests.Response): The response object from the request.
            action_result (ActionResult): The action result object to set the status on.

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
        """
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": response.status_code})
            action_result.add_debug_data({"r_text": response.text})
            action_result.add_debug_data({"r_headers": response.headers})

        # Process a json response
        content_type = response.headers.get("Content-Type", "")
        if "json" in content_type:
            return self._process_json_response(response, action_result)

        # Special handling for plain/text responses that might contain JSON
        # (specifically for the intel lookup results endpoint which returns JSON as plain/text)
        elif "text/plain" in content_type and response.text and response.text.strip().startswith("{"):
            self._connector.debug_print("Detected JSON data in plain/text response. Attempting to parse as JSON.")
            try:
                return self._process_json_response(response, action_result)
            except Exception as e:
                self._connector.debug_print(f"Failed to parse plain/text as JSON: {e!s}")
                # Continue to other response handlers if JSON parsing fails

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in response.headers.get("Content-Type", ""):
            return self._process_html_response(response, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not response.text:
            return self._process_empty_response(response, action_result)

        # everything else is actually an error at this point
        message = (
            f"Can't process response from server. Status Code: "
            f"{response.status_code} Data from server: "
            f"{response.text.replace('{', '{{').replace('}', '}}')}"
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def make_rest_call(
        self,
        endpoint,
        action_result,
        method="get",
        headers=None,
        params=None,
        data=None,
        timeout=None,
    ):
        """
        Make a REST call to the Infoblox API.

        Args:
            endpoint (str): The API endpoint to call.
            action_result (ActionResult): The action result object to set the status on.
            method (str): The HTTP method to use (default is "get").
            headers (dict): Additional headers to send with the request. Can include Content-Type to override default.
            params (dict): Query parameters to send with the request.
            data (dict): Data to send in the request body.
            timeout (int): Request timeout in seconds.

        Returns:
            tuple: A tuple containing the status of the request and the response data.
        """
        config = self._connector.get_config()

        # Get base URL from config
        base_url = config.get("base_url", consts.BASE_URL).rstrip("/")

        # Get API key from config
        api_key = config.get("api_key")
        if not api_key:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, "API key not configured"),
                None,
            )

        # Build full URL
        url = f"{base_url}{endpoint}"

        # Set up headers - Accept is always JSON, Content-Type handled by action if needed
        request_headers = {
            "Authorization": f"Token {api_key}",
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)

        # Set timeout
        if timeout is None:
            timeout = consts.REQUEST_DEFAULT_TIMEOUT

        try:
            request_func = getattr(requests, method.lower())
        except AttributeError:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"),
                None,
            )

        try:
            kwargs = {"url": url, "headers": request_headers, "timeout": timeout}

            if params:
                kwargs["params"] = params

            if data:
                if method.lower() in ["post", "put", "patch"]:
                    kwargs["json"] = data
                else:
                    kwargs["params"] = {**(kwargs.get("params", {})), **data}

            response = request_func(**kwargs)

        except requests.exceptions.ReadTimeout as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Request timed out after {timeout} seconds. The Infoblox API did not respond within the configured"
                    f" timeout period. Consider breaking down your query or using more specific parameters."
                    f"Error: {e}",
                ),
                None,
            )
        except requests.exceptions.Timeout as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Request timed out after {timeout} seconds. The connection to Infoblox API timed out. "
                    f"Please check network connectivity and try again. Error: {e}",
                ),
                None,
            )
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Error connecting to server. Details: {self._get_error_message_from_exception(e)}",
                ),
                None,
            )

        return self._process_response(response, action_result)

    def validate_filter_quotes(self, action_result, filter_string):
        """Validate that string values in tag filters are properly quoted.
        This function is specifically for tag filters which only support: ==, !=, ~

        Args:
            action_result (ActionResult): The ActionResult object to append error messages to.
            filter_string (str): The filter string to validate

        Returns:
            int: phantom.APP_SUCCESS if valid, phantom.APP_ERROR otherwise
        """
        import re

        # Debug logging
        self._connector.debug_print(f"Validating tag filter: {filter_string}")

        # Check for patterns like: field==value or field!="value" etc.
        # This regex finds tag filter operators (==, !=, ~) followed by values
        pattern = r"(==|!=|~)\s*([^\s]+)"
        matches = re.findall(pattern, filter_string)

        self._connector.debug_print(f"Found matches: {matches}")

        for operator, value in matches:
            self._connector.debug_print(f"Checking operator: {operator}, value: {value}")

            # Skip if value is already properly quoted
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                self._connector.debug_print(f"Value {value} is already quoted - OK")
                continue

            # Allow boolean values without quotes
            if value.lower() in ["true", "false"]:
                self._connector.debug_print(f"Value {value} is boolean - OK")
                continue

            # Allow pure integers without quotes
            if value.isdigit():
                self._connector.debug_print(f"Value {value} is integer - OK")
                continue

            # Everything else (including IP addresses, hostnames, etc.) should be quoted
            self._connector.debug_print(f"Value {value} should be quoted")
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Tag filter value '{value}' must be quoted. Use: {operator}\"{value}\" instead of {operator}{value}",
            )

        return phantom.APP_SUCCESS

    def check_filter_error_in_response(self, action_result, response_text, filter_param_name):
        """Check if API response contains filter validation errors and provide user-friendly message.

        Args:
            action_result (ActionResult): The ActionResult object to append error messages to.
            response_text (str): The API response text to check
            filter_param_name (str): Name of the filter parameter (e.g., 'ip_filter')

        Returns:
            int: phantom.APP_SUCCESS if no filter errors, phantom.APP_ERROR if filter error found
        """
        if "Unexpected symbol" in response_text:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Invalid filter syntax detected in {filter_param_name} parameter. "
                f"Please check your filter expression for proper syntax. "
                f"Supported operators: ==, !=, >, >=, <, <=, and, ~, !~, or, not, ()",
            )

        return phantom.APP_SUCCESS


class Validator:
    """This class contains validation utility methods."""

    def validate_indicator_value(self, action_result, indicator_type, indicator_value):
        """
        Validate an indicator value based on its type.

        Args:
            action_result (ActionResult): The action result object to set status on (used for return value only)
            indicator_type (str): The type of indicator (ip, host, url, email, hash)
            indicator_value (str): The value to validate

        Returns:
            tuple: (phantom.APP_SUCCESS/phantom.APP_ERROR, error_message or None)
        """
        if not indicator_value:
            return (phantom.APP_SUCCESS, None)

        indicator_type = indicator_type.lower()

        # Map of error messages for different indicator types
        error_messages = {
            "ip": f"Invalid IP address format: {indicator_value}",
            "host": f"Invalid host format: {indicator_value}",
            "url": f"Invalid URL format: {indicator_value}",
            "email": f"Invalid email format: {indicator_value}",
            "hash": f"Invalid hash format (must be MD5, SHA-1, or SHA-256): {indicator_value}",
        }

        # Call the appropriate validation method based on indicator type
        # Each validation method now returns a boolean
        if indicator_type == "ip":
            is_valid = self.validate_ip_address(indicator_value)
        elif indicator_type == "host":
            is_valid = self.validate_hostname(indicator_value)
        elif indicator_type == "url":
            is_valid = self.validate_url(indicator_value)
        elif indicator_type == "email":
            is_valid = self.validate_email(indicator_value)
        elif indicator_type == "hash":
            is_valid = self.validate_hash(indicator_value)
        else:
            # No validation for unknown types
            return (phantom.APP_SUCCESS, None)

        # Return success if valid, error with message if invalid
        if is_valid:
            return (phantom.APP_SUCCESS, None)
        else:
            return (
                phantom.APP_ERROR,
                error_messages.get(indicator_type, f"Invalid {indicator_type} format: {indicator_value}"),
            )

    def validate_datetime(self, date_str):
        """
        Validate a datetime string and optionally convert it to ISO 8601 format.

        Args:
            date_str (str): The datetime string to validate
            required_format (bool): If True, converts to ISO format if possible

        Returns:
            is_valid (bool)

        Accepts dates in these formats:
            - ISO 8601 with microseconds: YYYY-MM-DDThh:mm:ss.sssZ
            - Simple date: YYYY-MM-DD
        """
        try:
            # Check if the date format is valid
            datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            return True
        except ValueError:
            try:
                # Try another common format
                datetime.strptime(date_str, "%Y-%m-%d")
                return True
            except ValueError:
                return False

    def validate_url(self, url):
        """
        Validate a URL with custom logic.

        Args:
            url (str): The URL to validate

        Returns:
            bool: True if valid, False otherwise
        """
        return phantom.is_url(url)

    def validate_email(self, email):
        """
        Validate an email address.

        Args:
            email (str): The email to validate

        Returns:
            bool: True if valid, False otherwise
        """
        return phantom.is_email(email)

    def validate_hash(self, hash_value):
        """
        Validate a hash (MD5, SHA-1, SHA-256).

        Args:
            hash_value (str): The hash to validate

        Returns:
            bool: True if valid, False otherwise
        """
        return phantom.is_hash(hash_value)

    def validate_integer(self, action_result, parameter, key, allow_zero=False, allow_negative=False):
        """
        Validate if a given parameter is an integer.

        Args:
            action_result (ActionResult): The ActionResult object to append error messages to.
            parameter (str): The parameter to validate.
            key (str): The key of the parameter to validate.
            allow_zero (bool): Whether to allow zero as a valid integer (default is False).
            allow_negative (bool): Whether to allow negative integers as valid (default is False).

        Returns:
            Tuple[int, int]: A tuple containing the status of the action and the validated integer.
        """
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return (
                        action_result.set_status(
                            phantom.APP_ERROR,
                            consts.ERROR_INVALID_INT_PARAM.format(key=key),
                        ),
                        None,
                    )

                parameter = int(parameter)
            except Exception:
                return (
                    action_result.set_status(
                        phantom.APP_ERROR,
                        consts.ERROR_INVALID_INT_PARAM.format(key=key),
                    ),
                    None,
                )

            if not allow_zero and parameter == 0:
                return (
                    action_result.set_status(phantom.APP_ERROR, consts.ERROR_ZERO_INT_PARAM.format(key=key)),
                    None,
                )

            if not allow_negative and parameter < 0:
                return (
                    action_result.set_status(phantom.APP_ERROR, consts.ERROR_NEG_INT_PARAM.format(key=key)),
                    None,
                )

        return phantom.APP_SUCCESS, parameter

    def validate_list(self, action_result, parameter, key):
        """
        Validate a parameter as a JSON list.

        Args:
            action_result (ActionResult): The ActionResult object.
            parameter (str): The parameter to validate.
            key (str): The key of the parameter to validate.

        Returns:
            tuple[int, list|None]: A tuple containing the status of the validation and the valid parameter value.
        """
        if parameter is None:
            return phantom.APP_SUCCESS, []

        if isinstance(parameter, list):
            return phantom.APP_SUCCESS, parameter

        try:
            parameter = json.loads(parameter)
        except Exception:
            return (
                action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_LIST_PARAM.format(key=key)),
                None,
            )

        if not isinstance(parameter, list):
            return (
                action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_LIST_PARAM.format(key=key)),
                None,
            )

        return phantom.APP_SUCCESS, parameter

    def validate_ip_address(self, ip_str):
        """
        Validate if the given string is a valid IP address.

        Args:
            ip_str (str): The IP address string to validate.

        Returns:
            bool: True if valid IP address, False otherwise.
        """
        try:
            ipaddress.ip_address(ip_str)
            return True
        except ValueError:
            return False

    def validate_hostname(self, hostname):
        """
        Validate if the given string is a valid hostname.

        Args:
            hostname (str): The hostname string to validate.

        Returns:
            bool: True if valid hostname, False otherwise.
        """
        if len(hostname) > 255:
            return False

        # Remove trailing dot if present
        if hostname.endswith("."):
            hostname = hostname[:-1]

        # Check each label
        allowed = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$")

        return all(allowed.match(label) for label in hostname.split("."))

    def validate_mac_address(self, mac_str):
        """
        Validate if the given string is a valid MAC address.

        Args:
            mac_str (str): The MAC address string to validate.

        Returns:
            bool: True if valid MAC address, False otherwise.
        """
        # Regular expression for MAC address validation (XX:XX:XX:XX:XX:XX format)
        pattern = r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
        return bool(re.match(pattern, mac_str))

    def validate_filter_quotes(self, action_result, filter_string, connector=None):
        """Validate that string values in tag filters are properly quoted.
        This function is specifically for tag filters which only support: ==, !=, ~

        Args:
            action_result (ActionResult): The ActionResult object to append error messages to.
            filter_string (str): The filter string to validate
            connector (BaseConnector, optional): Connector instance for debug logging

        Returns:
            int: phantom.APP_SUCCESS if valid, phantom.APP_ERROR otherwise
        """
        import re

        # Debug logging (optional)
        if connector:
            connector.debug_print(f"Validating tag filter: {filter_string}")

        # Check for patterns like: field==value or field!="value" etc.
        # This regex finds tag filter operators (==, !=, ~) followed by values
        pattern = r"(==|!=|~)\s*([^\s]+)"
        matches = re.findall(pattern, filter_string)

        if connector:
            connector.debug_print(f"Found matches: {matches}")

        for operator, value in matches:
            if connector:
                connector.debug_print(f"Checking operator: {operator}, value: {value}")

            # Skip if value is already properly quoted
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                if connector:
                    connector.debug_print(f"Value {value} is already quoted - OK")
                continue

            # Allow boolean values without quotes
            if value.lower() in ["true", "false"]:
                if connector:
                    connector.debug_print(f"Value {value} is boolean - OK")
                continue

            # Allow pure integers without quotes
            if value.isdigit():
                if connector:
                    connector.debug_print(f"Value {value} is integer - OK")
                continue

            # Everything else (including IP addresses, hostnames, etc.) should be quoted
            if connector:
                connector.debug_print(f"Value {value} should be quoted")
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Tag filter value '{value}' must be quoted. Use: {operator}\"{value}\" instead of {operator}{value}",
            )

        return phantom.APP_SUCCESS

    def validate_datetime_format(self, datetime_str):
        """Validate if the given string matches the required datetime format.

        Args:
            datetime_str (str): The datetime string to validate

        Returns:
            bool: True if format is valid, False otherwise
        """
        # Regular expression for YYYY-MM-DDTHH:mm:ss.SSS format
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}$"
        return bool(re.match(pattern, datetime_str))

    def validate_dict(self, action_result, parameter, key):
        """
        Validate a parameter as a JSON dictionary.

        Args:
            action_result (ActionResult): The ActionResult object.
            parameter (str): The parameter to validate.
            key (str): The key of the parameter to validate.

        Returns:
            tuple[int, dict|None]: A tuple containing the status of the validation and the valid parameter value.
        """
        if parameter is None:
            return phantom.APP_SUCCESS, {}

        if isinstance(parameter, dict):
            return phantom.APP_SUCCESS, parameter

        try:
            parameter = json.loads(parameter)
        except Exception:
            return (
                action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_JSON_PARAM.format(key=key)),
                None,
            )

        if not isinstance(parameter, dict):
            return (
                action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_JSON_PARAM.format(key=key)),
                None,
            )

        return phantom.APP_SUCCESS, parameter
