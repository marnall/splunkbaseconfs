# File: infoblox_nios_utils.py
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

import phantom.app as phantom
import requests

# Local imports
import infoblox_nios_consts as consts


class RetVal(tuple):
    """Return value class for process_response methods."""

    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class InfobloxNIOSUtils:
    """Utility class for Infoblox NIOS connector."""

    def __init__(self, connector):
        """Initialize the utility class.

        :param connector: InfobloxNIOSConnector object
        """
        self._connector = connector

    def get_error_message_from_exception(self, e):
        """Extract error message from exception.

        :param e: Exception object
        :return: Error message string
        """
        error_code = None
        error_msg = consts.UNKNOWN_ERROR_MSG

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
            error_text = f"Error message: {error_msg}"
        else:
            error_text = f"Error code: {error_code}. Error message: {error_msg}"

        return error_text

    def _process_json_response(self, response, action_result):
        """Process a JSON response from the server.

        :param response: Response from the server
        :param action_result: ActionResult object
        :return: RetVal object with status and processed data
        """
        # First check if the response is empty
        if not response.text or response.text.strip() == "":
            # For successful status codes, return success with empty dict
            if 200 <= response.status_code < 300:
                return RetVal(phantom.APP_SUCCESS, {})
            else:
                # For error status codes with empty response, create generic error message
                error_message = f"Error from server. Status Code: {response.status_code}"
                return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), {})

        # Try to parse the response as JSON
        try:
            resp_json = response.json()
        except Exception as e:
            error_message = self.get_error_message_from_exception(e)
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Unable to parse JSON response. Error: {error_message}",
                ),
                None,
            )

        # Process successful responses
        if 200 <= response.status_code < 300:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # Process error responses
        error_message = f"Error from server. Status Code: {response.status_code}"

        # Try to extract error details from response
        if isinstance(resp_json, dict):
            # Handle common error response patterns
            if resp_json.get("Error") or resp_json.get("error"):
                error_obj = resp_json.get("Error") or resp_json.get("error")
                error_message += f" Error: {error_obj}"
            elif resp_json.get("text"):
                error_message += f" Details: {resp_json.get('text')}"
            elif resp_json.get("msg"):
                error_message += f" Message: {resp_json.get('msg')}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), resp_json)

    def _process_html_response(self, response, action_result):
        """Process an HTML response from the server.

        :param response: Response from the server
        :param action_result: ActionResult object
        :return: RetVal object with status and processed data
        """
        # Get status code
        status_code = response.status_code

        # Process HTML
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "html.parser")
            # Remove script, style, footer and navigation elements
            for element in soup(["script", "style", "footer", "nav"]):
                element.extract()
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except Exception:
            error_text = "Cannot parse HTML response"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        # Escape curly braces to prevent format string interpretation issues
        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_empty_response(self, response, action_result):
        """Process an empty response from the server.

        :param response: Response from the server
        :param action_result: ActionResult object
        :return: RetVal object with status and processed data
        """
        if 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, {})

        error_message = f"Status Code: {response.status_code}. Empty response with no data."
        return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), None)

    def _process_response(self, response, action_result):
        """Process API response with appropriate handler based on content type.

        :param response: Response from the API call
        :param action_result: Object of ActionResult class
        :return: RetVal object with status and processed data
        """
        # Add debug data if available
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": response.status_code})
            action_result.add_debug_data({"r_text": response.text})
            action_result.add_debug_data({"r_headers": response.headers})

        # Process response based on content type
        content_type = response.headers.get("Content-Type", "")

        # Process JSON response
        if "json" in content_type:
            return self._process_json_response(response, action_result)

        # Special handling for plain/text responses that might contain JSON
        elif "text/plain" in content_type and response.text and response.text.strip().startswith("{"):
            try:
                return self._process_json_response(response, action_result)
            except Exception as e:
                self._connector.debug_print(f"Failed to parse plain/text as JSON: {e}")
                # Continue to other response handlers if JSON parsing fails

        # Process HTML response
        if "html" in content_type:
            return self._process_html_response(response, action_result)

        # Process empty response
        if not response.text:
            return self._process_empty_response(response, action_result)

        # Handle unexpected response format
        message = (
            f"Can't process response from server. Status Code: {response.status_code} "
            f"Data from server: {response.text.replace('{', '{{').replace('}', '}}')}"
        )
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def format_rpz_cname_name(self, name, rp_zone):
        """Format name parameter according to requirements for RPZ CNAME rules.

        If name doesn't include rp_zone, append it.

        :param name: The name parameter value
        :param rp_zone: The rp_zone parameter value
        :return: tuple: (success, formatted_name)
        """
        # If either parameter is missing, skip formatting
        if not name or not rp_zone:
            return True, None

        try:
            # Check if name already ends with rp_zone
            if name.endswith(f".{rp_zone}"):
                return True, name
            else:
                return True, f"{name}.{rp_zone}"
        except Exception as e:
            self._connector.debug_print(f"Error formatting RPZ CNAME name: {e!s}")
            return False, None

    def prepare_rpz_cname_canonical_value(self, rule_type, name, substitute_name=None, object_type=None, reference_id=None):
        """Determine canonical value based on rule type and object type.

        This method supports both create and update actions:
        - For create: provide rule_type, name, object_type (and substitute_name if applicable)
        - For update: provide rule_type, name, reference_id (and substitute_name if applicable)

        :param rule_type: The type of rule (Block No Domain, Block No Data, etc.)
        :param name: The name parameter value
        :param substitute_name: The substitute_name parameter value (for Substitute rule type)
        :param object_type: The object type (Domain Name, IP Address, Client IP Address)
        :param reference_id: The reference ID (for update action)
        :return: str: The canonical value for the API request
        """
        # If reference_id is provided, determine object_type from it
        if reference_id and not object_type:
            if ":ipaddress/" in reference_id:
                object_type = consts.OBJECT_TYPE_IP
            elif ":clientipaddress/" in reference_id:
                object_type = consts.OBJECT_TYPE_CLIENT_IP
            else:
                object_type = consts.OBJECT_TYPE_DOMAIN

        # For Block No Domain - all object types use empty string
        if rule_type == consts.RULE_TYPE_BLOCK_NO_DOMAIN:
            return consts.CANONICAL_BLOCK_NO_DOMAIN

        # For Block No Data - all object types use asterisk
        elif rule_type == consts.RULE_TYPE_BLOCK_NO_DATA:
            return consts.CANONICAL_BLOCK_NO_DATA

        # For Passthru - depends on object type
        elif rule_type == consts.RULE_TYPE_PASSTHRU:
            if object_type == consts.OBJECT_TYPE_DOMAIN:
                # Special case: If domain name starts with wildcard, use "infoblox-passthru"
                if name and name.startswith("*"):
                    return "infoblox-passthru"
                # Otherwise, use the name itself for domain passthru
                return name
            elif object_type == consts.OBJECT_TYPE_IP:
                # For IP address, use the name itself for passthru
                return name
            else:  # Client IP Address
                # For client IP address, always use rpz-passthru
                return consts.CANONICAL_PASSTHRU

        # For Substitute
        elif rule_type == consts.RULE_TYPE_SUBSTITUTE:
            # Only domain names can have substitution rules
            if object_type == consts.OBJECT_TYPE_DOMAIN:
                return substitute_name
            else:
                self._connector.debug_print("Cannot create/update substitute rule for IP or Client IP address objects")
                return None

        # Default to block no data if for some reason we get here
        return consts.CANONICAL_BLOCK_NO_DATA

    def make_rest_call(self, endpoint, action_result, params=None, data=None, headers=None, method="get", timeout=None):
        """Make the REST call to the app.

        :param endpoint: REST endpoint
        :param action_result: Object of ActionResult class
        :param params: Request parameters
        :param data: Request body
        :param headers: Request headers
        :param method: GET/POST/PUT/DELETE/PATCH (Default: GET)
        :param timeout: Request timeout
        :return: RetVal object with status and processed data
        """
        if headers is None:
            headers = {}

        # Add JSON content type if not specified
        if consts.JSON_CONTENT_TYPE not in headers:
            headers[consts.JSON_CONTENT_TYPE] = "application/json"

        # Add basic authorization
        auth = (self._connector._username, self._connector._password)

        # Build URL
        url = f"{self._connector._url}{consts.BASE_ENDPOINT}{endpoint}"

        # Set default timeout if not provided
        if timeout is None:
            timeout = 30

        # Execute request
        try:
            # Check method
            method = method.lower()
            if method not in ["get", "post", "put", "patch", "delete"]:
                return RetVal(action_result.set_status(phantom.APP_ERROR, consts.ERROR_API_UNSUPPORTED_METHOD.format(method=method)), None)

            request_func = getattr(requests, method)
            self._connector.debug_print(f"Making REST call to URL: {url}")

            response = request_func(url, auth=auth, json=data, params=params, headers=headers, verify=self._connector._verify, timeout=timeout)

        except Exception as e:
            error_message = self.get_error_message_from_exception(e)
            self._connector.debug_print(f"{consts.EXCEPTION_OCCURRED}: {error_message}")
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error connecting to server. {error_message}"), None)

        return self._process_response(response, action_result)

    def make_paginated_rest_call(
        self, endpoint, action_result, params=None, data=None, headers=None, method="get", timeout=None, limit=None, page_size=None
    ):
        """Make paginated REST calls to fetch all results from the API.

        This method handles Infoblox WAPI pagination automatically, making multiple
        requests as needed to fetch all available results up to the specified limit.

        :param endpoint: REST endpoint
        :param action_result: Object of ActionResult class
        :param params: Request parameters
        :param data: Request body
        :param headers: Request headers
        :param method: GET/POST/PUT/DELETE/PATCH (Default: GET)
        :param timeout: Request timeout
        :param limit: Maximum number of results to return (Default: DEFAULT_MAX_RESULTS)
        :param page_size: Results per page (Default: DEFAULT_PAGE_SIZE)
        :return: RetVal object with status and list of all paginated results
        """
        # Set defaults for pagination parameters
        if limit is None:
            limit = consts.DEFAULT_MAX_RESULTS
        if page_size is None:
            page_size = consts.DEFAULT_PAGE_SIZE

        # Create a copy of params to avoid modifying the original
        paginated_params = params.copy() if params else {}

        # Enable pagination parameters for Infoblox WAPI
        paginated_params["_paging"] = 1
        paginated_params["_return_as_object"] = 1
        # Enforce maximum of 1000 records per single API call
        paginated_params["_max_results"] = min(page_size, limit)

        # Initialize results collection and pagination tracking
        all_results = []
        page_id = None

        self._connector.debug_print(f"Starting paginated REST call to {endpoint}, limit: {limit}")

        # Fetch pages until we have enough results or no more pages available
        while True:
            # Add page_id parameter if we're fetching subsequent pages
            if page_id:
                paginated_params["_page_id"] = page_id
            else:
                paginated_params.pop("_page_id", None)

            self._connector.debug_print(
                f"Fetching page page_id: {page_id}, max_results: {paginated_params['_max_results']}, paginated_params : {paginated_params}"
            )

            # Make the REST call for current page
            ret_val, response = self.make_rest_call(
                endpoint=endpoint,
                action_result=action_result,
                params=paginated_params,
                data=data,
                headers=headers,
                method=method,
                timeout=timeout,
            )

            # If the REST call failed, return the error
            if phantom.is_fail(ret_val):
                self._connector.debug_print("Paginated REST call failed")
                return RetVal(ret_val, None)

            # Extract results and next page info from response
            if isinstance(response, dict):
                # Response is in object format with result array and pagination info
                page_results = response.get("result", [])
                page_id = response.get("next_page_id")
                self._connector.debug_print(f"Received {len(page_results)} results, next_page_id: {page_id}")
            else:
                # Response is in array format (fallback for non-paginated responses)
                page_results = response if isinstance(response, list) else [response]
                page_id = None
                self._connector.debug_print(f"Received non-object response with {len(page_results)} results")

            # Add current page results to our collection
            all_results.extend(page_results)

            # Stop pagination if we've reached the limit or no more pages
            if not page_id or len(all_results) >= limit:
                break

            # Adjust page size for next request if approaching limit
            remaining = limit - len(all_results)
            paginated_params["_max_results"] = min(page_size, remaining)

        # Trim results to exact limit and return
        final_results = all_results[:limit]
        self._connector.debug_print(f"Pagination complete: returning {len(final_results)} total results")

        return RetVal(phantom.APP_SUCCESS, final_results)


class Validator:
    """This class contains validation utility methods."""

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
                            f"Please provide a valid integer value in the '{key}' parameter",
                        ),
                        None,
                    )

                parameter = int(parameter)
            except Exception:
                return (
                    action_result.set_status(
                        phantom.APP_ERROR,
                        f"Please provide a valid integer value in the '{key}' parameter",
                    ),
                    None,
                )

            if not allow_zero and parameter == 0:
                return (
                    action_result.set_status(phantom.APP_ERROR, f"Please provide a non-zero integer value in the '{key}' parameter"),
                    None,
                )

            if not allow_negative and parameter < 0:
                return (
                    action_result.set_status(phantom.APP_ERROR, f"Please provide a non-negative integer value in the '{key}' parameter"),
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

        # Check each label in the hostname
        import re

        hostname_pattern = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$")

        for label in hostname.split("."):
            if not label or not hostname_pattern.match(label):
                return False

        return True

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
                action_result.set_status(phantom.APP_ERROR, f"Please provide a valid JSON list in the '{key}' parameter"),
                None,
            )

        if not isinstance(parameter, list):
            return (
                action_result.set_status(phantom.APP_ERROR, f"Please provide a valid JSON list in the '{key}' parameter"),
                None,
            )

        return phantom.APP_SUCCESS, parameter
