#!/usr/bin/python
# File: ciscomeraki_utils.py
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
import time
from typing import Any, Optional

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup

import ciscomeraki_consts as consts


class CiscoMerakiUtils:
    """This class holds all the util methods."""

    def __init__(self, connector):
        """Initialize the utils class.

        Args:
            connector: The connector instance
        """
        self._connector = connector

    def _get_error_message_from_exception(self, e):
        """Get appropriate error message from the exception.

        Args:
            e: Exception object

        Returns:
            str: error message
        """
        error_code = None
        error_msg = consts.ERROR_MESSAGE_UNAVAILABLE
        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except Exception:
            pass

        return f"Error Code: {error_code}. Error Message: {error_msg}"

    def _process_empty_response(self, response, action_result):
        """Process empty response from server.

        Args:
            response: Response from server
            action_result: ActionResult object

        Returns:
            bool: Success/failure
        """
        if response.status_code in consts.EMPTY_RESPONSE_STATUS_CODES:
            return action_result.set_status(phantom.APP_SUCCESS, f"Status Code: {response.status_code}. Empty response")

        return action_result.set_status(
            phantom.APP_ERROR, f"Status Code: {response.status_code}. Empty response and not in success status codes"
        )

    def _process_html_response(self, response, action_result):
        """Process HTML response.

        Args:
            response: Response from server
            action_result: ActionResult object

        Returns:
            bool: Success/failure
        """
        # An html response, treat it like an error
        status_code = response.status_code
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except Exception:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"
        message = message.replace("{", "{{").replace("}", "}}")
        return action_result.set_status(phantom.APP_ERROR, message)

    def _process_json_response(self, response, action_result):
        """Process JSON response.

        Args:
            response: Response from server
            action_result: ActionResult object

        Returns:
            tuple: Status (bool), processed response (dict)
        """
        try:
            resp_json = response.json()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {error_message}"), None

        if 200 <= response.status_code < 399:
            return phantom.APP_SUCCESS, resp_json

        message = None
        if isinstance(resp_json, dict):
            message = resp_json.get("message", resp_json.get("errors", [{}])[0].get("message"))

        if not message:
            message = consts.ERROR_MESSAGE_UNAVAILABLE

        return action_result.set_status(
            phantom.APP_ERROR, f"Error from server. Status Code: {response.status_code} Data from server: {message}"
        ), None

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        """Makes the REST call to the app with retry mechanism for rate limiting.

        Args:
            endpoint: REST endpoint that needs to be called
            action_result: ActionResult object
            method: GET/POST/PUT/DELETE (Default: get)
            **kwargs: Additional arguments for request

        Returns:
            tuple: Status (bool), response (dict)
        """
        resp_json = None
        retries = 0

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json

        # Get headers from auth module
        headers = self._connector._auth.get_headers()
        if headers is None:
            return action_result.set_status(phantom.APP_ERROR, "Failed to get authentication headers"), resp_json
        headers["User-Agent"] = "Splunk SOAR Cisco Test"  # Add User-Agent
        kwargs["headers"] = headers
        kwargs["timeout"] = consts.REQUEST_DEFAULT_TIMEOUT

        # Get base_url from config
        base_url = self._connector.get_config().get("base_url", "").rstrip("/")
        full_url = f"{base_url}{consts.API_PATH}{endpoint}"

        while retries < consts.MAX_RETRIES:
            try:
                self._connector.debug_print(f"Making {method} request to {full_url}")
                response = request_func(full_url, verify=self._connector.get_config().get("verify_server_cert", True), **kwargs)
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", consts.INITIAL_RETRY_DELAY))
                    self._connector.debug_print(f"Rate limited. Retrying after {retry_after} seconds. Retry {retries + 1}/{consts.MAX_RETRIES}")
                    time.sleep(retry_after)
                    retries += 1
                    continue
                if response.status_code == 401:
                    return action_result.set_status(phantom.APP_ERROR, "API key invalid or expired"), resp_json

                return self._process_response(response, action_result)

            except requests.exceptions.RequestException as e:
                error_message = self._get_error_message_from_exception(e)
                return action_result.set_status(phantom.APP_ERROR, f"Error connecting to server. Details: {error_message}"), resp_json

        return action_result.set_status(phantom.APP_ERROR, "Max retries exceeded for rate limiting"), resp_json

    def _process_response(self, response, action_result):
        """Process API response.

        Args:
            response: Response from server
            action_result: ActionResult object

        Returns:
            tuple: Status (bool), response (dict)
        """
        if not response.ok:
            if response.text:
                json_error_text = json.loads(response.text) if isinstance(response.text, str) else response.text
                return action_result.set_status(
                    phantom.APP_ERROR,
                    f"Status Code: {response.status_code}. Error: {json_error_text.get('error') if json_error_text.get('error', None) else response.text}",
                ), None
            return action_result.set_status(phantom.APP_ERROR, f"Status Code: {response.status_code}. Error: {response.text}"), None

        if not response.text:
            return self._process_empty_response(response, action_result), None

        if "json" in response.headers.get("Content-Type", ""):
            return self._process_json_response(response, action_result)

        if "html" in response.headers.get("Content-Type", ""):
            return self._process_html_response(response, action_result), None

        return action_result.set_status(phantom.APP_ERROR, "Unknown response type"), None

    def _paginator(self, action_result, endpoint, limit=None, **kwargs):
        """Handle pagination for Meraki API responses.

        Args:
            action_result: ActionResult object
            endpoint: API endpoint
            limit: Maximum number of records to return (max 1000 per page)
            **kwargs: Additional arguments for the API call

        Returns:
            tuple: Status (bool), aggregated results (list)
        """
        items = []
        next_url = None

        # Set up pagination parameters
        params = kwargs.get("params", {})
        params["perPage"] = min(limit, consts.MAX_PAGE_SIZE) if limit else consts.MAX_PAGE_SIZE
        kwargs["params"] = params

        # while True:
        # if next_url:
        #     # Get base_url from config
        #     base_url = self._connector.get_config().get('base_url', '').rstrip('/')
        #     endpoint = next_url.replace(f"{base_url}{consts.API_PATH}", '')

        ret_val, response = self._make_rest_call(endpoint, action_result, **kwargs)

        if phantom.is_fail(ret_val):
            return ret_val, None

        if not isinstance(response, list):
            return phantom.APP_ERROR, "Unexpected response format from server"

        items.extend(response)

        # if limit and len(items) >= limit:
        #     items = items[:limit]
        #     break

        # # Check for more pages using Link header
        # link_header = response.headers.get('Link', '')
        # if 'rel="next"' not in link_header:
        #     break

        # next_url = self._parse_link_header(link_header)
        # if not next_url:
        #     break

        return phantom.APP_SUCCESS, items

    def _parse_link_header(self, link_header):
        """Parse Link header to get next URL.

        Args:
            link_header: Link header from response

        Returns:
            str: URL for next page or None
        """
        if not link_header:
            return None

        links = link_header.split(",")
        for link in links:
            if 'rel="next"' in link:
                url = link.split(";")[0].strip(" <>")
                return url

        return None


def validate_params(params: dict[str, Any], required_params: dict[str, Any], operation: Optional[str] = None) -> dict[str, Any]:
    """
    Validate input parameters for actions

    Args:
        params: Input parameters
        required_params: Dictionary of required parameters and their types
        operation: Optional operation name for operation-specific validation

    Returns:
        Dictionary with validation status and message
    """
    missing_params = []
    invalid_params = []

    # Check required parameters
    for param, param_type in required_params.items():
        if param not in params or params[param] is None:
            missing_params.append(param)
        elif not isinstance(params[param], param_type):
            invalid_params.append(f"{param} (expected {param_type.__name__})")

    if missing_params:
        return {"valid": False, "message": f"Missing required parameters: {', '.join(missing_params)}"}

    if invalid_params:
        return {"valid": False, "message": f"Invalid parameter types: {', '.join(invalid_params)}"}

    return {"valid": True, "message": "All parameters valid"}


def format_error_response(error_msg: str, status: str = "failed") -> dict[str, Any]:
    """
    Format error response for consistent error handling

    Args:
        error_msg: Error message
        status: Status string

    Returns:
        Formatted error response dictionary
    """
    return {"status": status, "message": error_msg, "data": []}
