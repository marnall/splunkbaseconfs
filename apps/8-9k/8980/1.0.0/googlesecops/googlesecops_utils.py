# File: googlesecops_utils.py
#
# Copyright (c) 2026 Google
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
import re
import time
from datetime import UTC

import phantom.app as phantom
import requests.exceptions
from bs4 import BeautifulSoup

import googlesecops_consts as consts


class RetVal(tuple):
    """Return a tuple of two elements."""

    def __new__(cls, val1, val2=None):
        """Create a new tuple object."""
        return tuple.__new__(RetVal, (val1, val2))


class GoogleSecOpsUtils:
    """This class holds all the util methods."""

    def __init__(self, connector=None):
        self._connector = connector

    _JWT_ALLOWED_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")
    _JWT_SCAN_CHARS = _JWT_ALLOWED_CHARS.union({"."})

    @staticmethod
    def _is_sensitive_key(key):
        """Check whether a dictionary key is likely to contain sensitive auth data."""
        if not isinstance(key, str):
            return False

        key_lower = key.strip().lower().replace("-", "_")
        explicit_sensitive_keys = {
            "id_token",
            "access_token",
            "refresh_token",
            "authorization",
            "client_secret",
            "private_key",
            "service_account_json",
            "password",
            "assertion",
            "api_key",
        }

        if key_lower in explicit_sensitive_keys:
            return True

        return "secret" in key_lower or key_lower.endswith("_token")

    @classmethod
    def _is_jwt_like_token(cls, token):
        """Validate whether token looks like a JWT value."""
        parts = token.split(".")
        if len(parts) != 3:
            return False

        for part in parts:
            if len(part) < 16:
                return False
            if any(char not in cls._JWT_ALLOWED_CHARS for char in part):
                return False

        return True

    @classmethod
    def _redact_jwt_like_strings(cls, value):
        """
        Redact JWT-like strings using linear scanning to avoid regex backtracking.
        """
        if not value or "." not in value:
            return value

        redacted_chunks = []
        index = 0
        value_length = len(value)

        while index < value_length:
            current_char = value[index]

            if current_char not in cls._JWT_SCAN_CHARS:
                redacted_chunks.append(current_char)
                index += 1
                continue

            start = index
            while index < value_length and value[index] in cls._JWT_SCAN_CHARS:
                index += 1
            candidate = value[start:index]

            if cls._is_jwt_like_token(candidate):
                redacted_chunks.append("<redacted_jwt>")
            else:
                redacted_chunks.append(candidate)

        return "".join(redacted_chunks)

    def _sanitize_sensitive_data(self, value):
        """Recursively redact sensitive fields from structured/unstyled values."""
        if isinstance(value, dict):
            sanitized = {}
            redacted = False
            for key, item in value.items():
                if self._is_sensitive_key(key):
                    redacted = True
                    continue
                sanitized[key] = self._sanitize_sensitive_data(item)

            if redacted and not sanitized:
                return consts.ERROR_SENSITIVE_DATA
            if redacted:
                sanitized["redacted"] = consts.ERROR_SENSITIVE_DATA
            return sanitized

        if isinstance(value, list):
            return [self._sanitize_sensitive_data(item) for item in value]

        if isinstance(value, tuple):
            return tuple(self._sanitize_sensitive_data(item) for item in value)

        if isinstance(value, str):
            sanitized = value

            # Redact sensitive auth field names in unstructured strings
            sanitized = re.sub(
                r"(?i)\b(id_token|access_token|refresh_token|authorization|client_secret|private_key|assertion|password|api_key)\b",
                "<redacted_field>",
                sanitized,
            )

            # Redact JWT-like strings
            sanitized = self._redact_jwt_like_strings(sanitized)

            # Redact bearer token values
            sanitized = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/\-=]+", r"\1<redacted>", sanitized)  # NOSONAR

            # Redact key/value token-like string representations
            sanitized = re.sub(  # NOSONAR
                r"(?i)((?:id_token|access_token|refresh_token|authorization|client_secret|private_key|assertion|password|api_key)\s*[:=]\s*)([^,\s}\]]+)",
                r"\1<redacted>",
                sanitized,
            )

            return sanitized

        return value

    @staticmethod
    def _is_redacted_placeholder(value):
        """Check whether the value is only a redaction placeholder."""
        if value is None:
            return False

        value_str = str(value).strip()
        return value_str in {
            consts.ERROR_SENSITIVE_DATA,
            "<redacted>",
            "<redacted_jwt>",
            "<redacted_field>",
        }

    def _get_error_message_from_exception(self, e):
        """Get appropriate error message from the exception.

        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_message = consts.GOOGLESECOPS_UNAVAILABLE_MESSAGE_ERROR

        if self._connector:
            sanitized_exception = self._sanitize_sensitive_data(getattr(e, "args", str(e)))
            self._connector.error_print("Error occurred.", sanitized_exception)

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = self._sanitize_sensitive_data(e.args[0])
                    error_message = self._sanitize_sensitive_data(e.args[1])
                elif len(e.args) == 1:
                    error_message = self._sanitize_sensitive_data(e.args[0])
        except Exception as ex:
            if self._connector:
                self._connector.error_print(
                    f"Error occurred while fetching exception information. Details: {self._sanitize_sensitive_data(ex)!s}"
                )

        if self._is_redacted_placeholder(error_message):
            if error_code:
                error_text = f"Error Code: {error_code}"
            else:
                error_text = consts.ERROR_MESSAGE_UNAVAILABLE
        elif not error_code:
            error_text = f"Error Message: {error_message}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_message}"

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
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
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

        if len(message) > 500:
            return RetVal(action_result.set_status(phantom.APP_ERROR, consts.ERROR_HTML_RESPONSE))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message))

    def _process_json_response(self, r, action_result):
        """
        Process a JSON response from a request.

        Args:
            r (requests.Response): The response object from the request.
            action_result (ActionResult): The action result object to set the status on.

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
        """
        try:
            resp_json = r.json()
        except Exception as e:
            error_msg = self._get_error_message_from_exception(e)
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Unable to parse JSON response. {error_msg}",
                ),
                None,
            )

        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        error_message = resp_json.get("error", {}).get("message", "No error message provided")

        if resp_json.get("message"):
            error_message = resp_json.get("message", "No error message provided")
        message = f"Error from server. Status Code: {r.status_code} Data from server: {error_message}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message))

    def _process_response(self, r, action_result):
        """
        Processes the response from the server.

        Args:
            r (requests.response): Response from the server.
            action_result (phantom.action_result): Action result to store the results.

        Returns:
            RetVal: A RetVal of phantom.APP_SUCCESS or phantom.APP_ERROR.
        """
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        if "html" in r.headers.get("Content-Type", "") and r.text:
            return self._process_html_response(r, action_result)

        if not r.text:
            return self._process_empty_response(r, action_result)

        message = (
            f"Can't process response from server. Status Code: {r.status_code} Data from server: {r.text.replace('{', '{{').replace('}', '}}')}"
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def make_rest_call(
        self,
        endpoint,
        action_result,
        method="get",
        timeout=consts.REQUEST_DEFAULT_TIMEOUT,
        **kwargs,
    ):
        """
        Make a REST call to the API with exponential backoff retry for timeout errors.

        Args:
            endpoint (str): The endpoint to make the REST call to.
            action_result (ActionResult): The action result object to set the status on.
            method (str, optional): The method to use for the REST call. Defaults to "get".

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
        """
        self._connector.debug_print(f"Starting REST call: method={method}, endpoint={endpoint}...")
        resp_json = None

        try:
            request_func = getattr(self._connector.client.http_client, method, timeout)
        except AttributeError:
            self._connector.debug_print(f"Invalid method: {method}")
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"),
                resp_json,
            )

        # Retry configuration
        timeout_values = [30, 60, 90]
        retry_wait_time = 30
        max_attempts = len(timeout_values)

        for attempt in range(max_attempts):
            result = self._attempt_request(
                request_func,
                endpoint,
                action_result,
                attempt,
                max_attempts,
                timeout_values,
                retry_wait_time,
                kwargs,
            )
            if result is not None:
                return result

        # Should never reach here
        self._connector.debug_print("Unexpected: reached end of retry loop")
        return RetVal(
            action_result.set_status(
                phantom.APP_ERROR,
                "Unexpected error in retry logic",
            ),
            resp_json,
        )

    def _attempt_request(
        self,
        request_func,
        url,
        action_result,
        attempt,
        max_attempts,
        timeout_values,
        retry_wait_time,
        kwargs,
    ):
        """Attempt a single request with error handling."""
        current_timeout = timeout_values[attempt]

        try:
            r = request_func(url, timeout=current_timeout, **kwargs)
            return self._process_response(r, action_result)

        except (
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectTimeout,
        ) as e:
            return self._handle_timeout_error(
                e,
                attempt,
                max_attempts,
                timeout_values,
                retry_wait_time,
                action_result,
            )

        except requests.exceptions.ConnectionError as e:
            return self._handle_connection_error(
                e,
                attempt,
                max_attempts,
                timeout_values,
                retry_wait_time,
                action_result,
            )

        except Exception as e:
            error_msg = self._get_error_message_from_exception(e)
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Error connecting to server. {error_msg}",
                ),
                None,
            )

    def _handle_timeout_error(
        self,
        error,
        attempt,
        max_attempts,
        timeout_values,
        retry_wait_time,
        action_result,
    ):
        """Handle timeout errors with retry logic."""

        if attempt == max_attempts - 1:
            self._connector.debug_print(f"All {max_attempts} attempts exhausted, failing")
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Request timed out after {max_attempts} attempts. Last error: {error!s}",
                ),
                None,
            )

        self._wait_before_retry(attempt, max_attempts, timeout_values, retry_wait_time)
        return None

    def _handle_connection_error(
        self,
        error,
        attempt,
        max_attempts,
        timeout_values,
        retry_wait_time,
        action_result,
    ):
        """Handle connection errors with retry logic."""

        if attempt == max_attempts - 1:
            self._connector.debug_print(f"All {max_attempts} attempts exhausted, failing")
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Connection error after {max_attempts} attempts. Last error: {error!s}",
                ),
                None,
            )

        self._wait_before_retry(attempt, max_attempts, timeout_values, retry_wait_time)
        return None

    def _wait_before_retry(self, attempt, max_attempts, timeout_values, retry_wait_time):
        """Wait before retrying the request."""
        self._connector.save_progress(
            f"Request failed (attempt {attempt + 1}/{max_attempts}). "
            f"Retrying in {retry_wait_time} seconds with timeout={timeout_values[attempt + 1]}s..."
        )
        self._connector.debug_print(f"Sleeping for {retry_wait_time} seconds before retry")
        time.sleep(retry_wait_time)

    def paginated_rest_call(
        self,
        endpoint_template,
        action_result,
        max_results,
        params_dict={},
        data_key="detections",
        initial_page_token=None,
        method="get",
        **kwargs,
    ):
        """
        Make paginated REST calls to fetch results beyond API limits.

        Args:
            endpoint_template (str): The endpoint URL template (without query params)
            action_result (ActionResult): The action result object
            max_results (int): Maximum total results to fetch
            params_dict (dict): Base parameters for the API call
            data_key (str): Key in response containing data array (default: "detections")
            initial_page_token (str): Initial page token if resuming
            method (str): HTTP method (default: "get")
            **kwargs: Additional arguments for make_rest_call

        Returns:
            tuple: (status, dict with 'data', 'next_page_token', 'metadata')
        """
        all_data = []
        total_fetched = 0
        current_page_token = initial_page_token
        metadata = {}

        self._connector.save_progress(
            f"Fetching up to {max_results} items (page size: {min(max_results, 10000)})...and params_dict {params_dict}"
        )

        while total_fetched < max_results:
            result = self._fetch_page(
                endpoint_template,
                action_result,
                max_results,
                total_fetched,
                current_page_token,
                params_dict,
                data_key,
                method,
                kwargs,
            )

            if result is None:
                break

            ret_val, response, data_items = result
            if phantom.is_fail(ret_val):
                return RetVal(ret_val, None)

            if not data_items:
                self._connector.debug_print("No data items in response, stopping pagination")
                break

            # Capture metadata from first response
            if not metadata:
                metadata = self._extract_metadata(response, data_key)

            all_data.extend(data_items)
            total_fetched += len(data_items)
            self._connector.debug_print(f"Added {len(data_items)} items, total_fetched now: {total_fetched}")
            self._connector.save_progress(f"Fetched {total_fetched} items so far...")

            # Check if we should continue pagination
            should_continue, next_token = self._should_continue_pagination(response, total_fetched, max_results)

            if not should_continue:
                break

            current_page_token = next_token

        result_data = self._build_result_data(all_data, response if all_data else {}, metadata)
        self._connector.debug_print(
            f"Pagination complete: total items={len(all_data)}, next_page_token={'<present>' if result_data['next_page_token'] else '<none>'}"
        )
        return RetVal(phantom.APP_SUCCESS, result_data)

    def _fetch_page(
        self,
        endpoint_template,
        action_result,
        max_results,
        total_fetched,
        current_page_token,
        params_dict,
        data_key,
        method,
        kwargs,
    ):
        """Fetch a single page of results."""
        self._connector.debug_print(f"Pagination loop iteration: total_fetched={total_fetched}/{max_results}")

        request_params = self._build_request_params(params_dict, max_results, total_fetched, current_page_token)

        self._connector.debug_print(f"Making API call with page_token={'<present>' if current_page_token else '<none>'}")

        ret_val, response = self.make_rest_call(
            endpoint_template,
            action_result,
            method=method,
            params=request_params,
            **kwargs,
        )

        if phantom.is_fail(ret_val):
            return (ret_val, None, None)

        data_items = response.get(data_key, [])
        self._connector.debug_print(f"Extracted {len(data_items)} items from response (key: {data_key})")

        return (ret_val, response, data_items)

    def _build_request_params(self, params_dict, max_results, total_fetched, current_page_token):
        """Build request parameters for pagination."""
        remaining = max_results - total_fetched
        current_page_size = min(remaining, 10000)

        request_params = params_dict.copy() if params_dict else {}

        # Update page size parameter
        if "pageSize" in request_params:
            request_params["pageSize"] = current_page_size
        elif "maxResults" in request_params:
            request_params["maxResults"] = current_page_size

        # Add page token if available
        if current_page_token:
            request_params["pageToken"] = current_page_token

        return request_params

    def _extract_metadata(self, response, data_key):
        """Extract metadata from the first response."""
        metadata = {}

        if "uri" in response:
            uri_list = response.get("uri", [])
            metadata["uri"] = uri_list[0] if len(uri_list) == 1 else uri_list

        for key in response:
            if key not in [data_key, "nextPageToken", "moreDataAvailable"]:
                metadata[key] = response[key]

        return metadata

    def _should_continue_pagination(self, response, total_fetched, max_results):
        """Determine if pagination should continue."""
        next_page_token = response.get("nextPageToken", "")
        more_data_available = response.get("moreDataAvailable", False)

        self._connector.debug_print(
            f"Next page info: nextPageToken={'<present>' if next_page_token else '<none>'}, moreDataAvailable={more_data_available}"
        )

        if not next_page_token and not more_data_available:
            self._connector.debug_print("No more pages available, stopping pagination")
            return False, None

        if total_fetched >= max_results:
            self._connector.debug_print(f"Reached max_results ({max_results}), stopping pagination")
            return False, None

        if next_page_token:
            self._connector.debug_print("Continuing to next page")
            return True, next_page_token

        self._connector.debug_print("No page token available, stopping pagination")
        return False, None

    def _build_result_data(self, all_data, response, metadata):
        """Build the final result data structure."""
        return {
            "data": all_data,
            "next_page_token": response.get("nextPageToken", "") if all_data else "",
            "more_data_available": response.get("moreDataAvailable", False) if all_data else False,
            "metadata": metadata,
        }


class Validator:
    """Validator class for input validation."""

    @staticmethod
    def validate_time_parameter(
        action_result,
        time_value,
        param_name,
        allow_future=False,
        required=False,
        max_days_past=None,
    ):
        """
        Validate a time parameter (start_time, end_time, reference_time).

        Accepts two formats:
        1. RFC 3339 format with:
           - Z-normalization (e.g., "2014-10-02T15:01:23Z")
           - Fractional seconds with 0, 3, 6, or 9 digits (e.g., "2014-10-02T15:01:23.045123456Z")
           - Timezone offsets (e.g., "2014-10-02T15:01:23+05:30")
        2. Relative time format: <digit><d/h/m/s>
           - Examples: "7d", "24h", "30m", "3600s"

        Args:
            action_result: Action result object
            time_value: The time value to validate (string or None)
            param_name: Parameter name for error messages
            allow_future: Whether to allow future dates (default: False)
            required: Whether the parameter is required (default: False)
            max_days_past: Maximum days in the past allowed (default: None, no limit)

        Returns:
            tuple: (status, parsed_datetime_object or None)
        """
        import re

        # Handle None/empty values
        if not time_value:
            if required:
                return action_result.set_status(
                    phantom.APP_ERROR,
                    f"{param_name} is required but not provided.",
                ), None
            return phantom.APP_SUCCESS, None

        try:
            # Check for relative time format
            relative_pattern = re.compile(r"^(\d+)([dhms])$")
            relative_match = relative_pattern.match(time_value.strip())

            if relative_match:
                return Validator._parse_relative_time(
                    action_result,
                    time_value,
                    param_name,
                    relative_match,
                    max_days_past,
                )

            if param_name != "preset_time_range":
                # Try RFC 3339 format
                return Validator._parse_rfc3339_time(
                    action_result,
                    time_value,
                    param_name,
                    allow_future,
                    max_days_past,
                )
            else:
                raise ValueError("Invalid format")

        except ValueError as e:
            if param_name == "preset_time_range":
                format_message = "Expected relative format (e.g., '7d', '24h'). "
            elif param_name in ["start_time", "end_time"]:
                format_message = "Expected RFC 3339 format (e.g., '2014-10-02T15:01:23Z'). "
            else:
                format_message = "Expected RFC 3339 format (e.g., '2014-10-02T15:01:23Z') or relative format (e.g., '7d', '24h'). "
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Invalid {param_name} format: {time_value}. {format_message}Error: {e!s}",
            ), None
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Invalid {param_name}: {time_value}. Error: {e!s}",
            ), None

    @staticmethod
    def _parse_relative_time(action_result, time_value, param_name, relative_match, max_days_past):
        """Parse relative time format like '7d', '24h', '30m', '3600s'."""
        from datetime import datetime

        value = int(relative_match.group(1))
        unit = relative_match.group(2)

        delta = Validator._get_timedelta_from_unit(unit, value)
        if delta is None:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Invalid {param_name} unit: {unit}. Must be d, h, m, or s.",
            ), None

        parsed_time = datetime.now(UTC) - delta

        # Validate against max_days_past
        if max_days_past is not None:
            validation_result = Validator._validate_max_days_past(
                action_result,
                param_name,
                time_value,
                parsed_time,
                max_days_past,
            )
            if validation_result:
                return validation_result

        return phantom.APP_SUCCESS, parsed_time

    @staticmethod
    def _get_timedelta_from_unit(unit, value):
        """Convert unit and value to timedelta."""
        from datetime import timedelta

        unit_map = {
            "d": timedelta(days=value),
            "h": timedelta(hours=value),
            "m": timedelta(minutes=value),
            "s": timedelta(seconds=value),
        }
        return unit_map.get(unit)

    @staticmethod
    def _parse_rfc3339_time(action_result, time_value, param_name, allow_future, max_days_past):
        """Parse RFC 3339 time format."""
        import re
        from datetime import datetime

        rfc3339_pattern = re.compile(
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
            r"(?:\.\d{1,9})?"
            r"(?:Z|[+-]\d{2}:\d{2})$"
        )

        if not rfc3339_pattern.match(time_value):
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Invalid {param_name} format: {time_value}. "
                f"Expected RFC 3339 format (e.g., '2014-10-02T15:01:23Z') or relative format (e.g., '7d', '24h', '30m', '3600s').",
            ), None

        time_str_normalized = time_value.replace("Z", "+00:00")
        parsed_time = datetime.fromisoformat(time_str_normalized)
        parsed_time = parsed_time.astimezone(UTC)

        # Validate future time
        if not allow_future:
            validation_result = Validator._validate_not_future(action_result, param_name, time_value, parsed_time)
            if validation_result:
                return validation_result

        # Validate max_days_past
        if max_days_past is not None:
            validation_result = Validator._validate_max_days_past(
                action_result,
                param_name,
                time_value,
                parsed_time,
                max_days_past,
            )
            if validation_result:
                return validation_result

        return phantom.APP_SUCCESS, parsed_time

    @staticmethod
    def _validate_not_future(action_result, param_name, time_value, parsed_time):
        """Validate that time is not in the future."""
        from datetime import datetime

        now = datetime.now(UTC)
        if parsed_time > now:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Invalid {param_name}: Cannot be in the future. Provided: {time_value}",
            ), None
        return None

    @staticmethod
    def _validate_max_days_past(action_result, param_name, time_value, parsed_time, max_days_past):
        """Validate that time is not too far in the past."""
        from datetime import datetime

        age = datetime.now(UTC) - parsed_time
        if age.days > max_days_past:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Invalid {param_name}: {time_value} is more than {max_days_past} days in the past ({age.days} days ago).",
            ), None
        return None

    @staticmethod
    def validate_ip_address(ip_address_value):
        """
        Validate IPv4/IPv6 address value.

        Validation flow:
        1. Validate IPv4 using `phantom.is_ip(...)`.
        2. If IPv4 validation fails, validate IPv6.

        Args:
            ip_address_value: IP address string value.

        Returns:
            bool: True if valid IPv4 or IPv6 address, else False.
        """

        if ip_address_value is None:
            return False

        ip_address_value = str(ip_address_value).strip()
        if not ip_address_value:
            return False

        if phantom.is_ip(ip_address_value):
            return True

        try:
            ipaddress.IPv6Address(ip_address_value)
            return True
        except Exception:
            return False

    @staticmethod
    def validate_mac_address(mac_address_value):
        """
        Validate MAC address value.

        Supported formats:
        - XX:XX:XX:XX:XX:XX
        - XX-XX-XX-XX-XX-XX
        - XXXX.XXXX.XXXX
        - XXXXXXXXXXXX

        Args:
            mac_address_value: MAC address string value.

        Returns:
            bool: True if valid MAC address, else False.
        """
        if mac_address_value is None:
            return False

        mac_address_value = str(mac_address_value).strip()
        if not mac_address_value:
            return False

        patterns = [
            r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$",
            r"^([0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}$",
            r"^([0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}$",
            r"^[0-9A-Fa-f]{12}$",
        ]

        return any(re.match(pattern, mac_address_value) for pattern in patterns)

    @staticmethod
    def validate_integer(
        action_result,
        parameter,
        key,
        allow_zero=False,
        min_value=None,
        max_value=None,
    ):
        """
        Validate an integer parameter.

        Args:
            action_result: Action result object
            parameter: The parameter value
            key: Parameter name
            allow_zero: Whether to allow zero
            min_value: Minimum allowed value
            max_value: Maximum allowed value

        Returns:
            tuple: (status, validated_value)
        """
        try:
            if not float(parameter).is_integer():
                return action_result.set_status(
                    phantom.APP_ERROR,
                    consts.ERROR_INVALID_INT_PARAM.format(key=key),
                ), None

            parameter = int(parameter)
        except Exception:
            return action_result.set_status(
                phantom.APP_ERROR,
                consts.ERROR_INVALID_INT_PARAM.format(key=key),
            ), None

        if parameter < 0:
            return action_result.set_status(phantom.APP_ERROR, consts.ERROR_NEG_INT_PARAM.format(key=key)), None

        if not allow_zero and parameter == 0:
            return action_result.set_status(phantom.APP_ERROR, consts.ERROR_ZERO_INT_PARAM.format(key=key)), None

        if min_value is not None and parameter < min_value:
            return action_result.set_status(
                phantom.APP_ERROR,
                consts.ERROR_INVALID_INT_RANGE.format(
                    key=key,
                    min_value=min_value,
                    max_value=max_value or "infinity",
                ),
            ), None

        if max_value is not None and parameter > max_value:
            return action_result.set_status(
                phantom.APP_ERROR,
                consts.ERROR_INVALID_INT_RANGE.format(key=key, min_value=min_value or 0, max_value=max_value),
            ), None

        return phantom.APP_SUCCESS, parameter
