# File: google_threat_intelligence_utils.py
#
# Copyright 2025-2026 Google LLC
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

import base64
import ipaddress
import json
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse, urlunparse

import phantom.app as phantom
import phantom.rules as ph_rules
import requests
from bs4 import BeautifulSoup
from phantom.utils import config as ph_config

import google_threat_intelligence_consts as consts


class RetVal(tuple):
    """Return a tuple of two elements."""

    def __new__(cls, val1, val2=None):
        """Create a new tuple object."""
        return tuple.__new__(RetVal, (val1, val2))


class GoogleThreatIntelligenceUtils:
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
            error_text = "Cannot parse error details"

        message = consts.ERROR_GENERAL_MESSAGE.format(status_code, error_text)
        message = message.replace("{", "{{").replace("}", "}}")

        # Large HTML pages may be returned by the wrong URLs.
        # Use default error message in place of large HTML page.
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
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Unable to parse JSON response. Error: {e!s}",
                ),
                None,
            )

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # Extract error message from JSON response
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
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        """
        Process a response from a request.

        This function takes a response object from a request and an action result object
        and processes the response into a RetVal object.

        If the response is a JSON response, it is processed using `_process_json_response`.
        If the response is an HTML response, it is processed using `_process_html_response`.
        If the response is empty, it is processed using `_process_empty_response`.
        Otherwise, an error is raised.

        Args:
            r (requests.Response): The response object from the request.
            action_result (ActionResult): The action result object to set the status on.

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
        """
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
        if "html" in r.headers.get("Content-Type", "") and r.text:
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = (
            f"Can't process response from server. Status Code: {r.status_code} Data from server: {r.text.replace('{', '{{').replace('}', '}}')}"
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def make_rest_call(self, endpoint, action_result, method="get", large_file=False, return_response_headers=False, **kwargs):
        """
        Make a REST call to the API.

        Args:
            endpoint (str): The endpoint to make the REST call to.
            action_result (ActionResult): The action result object to set the status on.
            method (str, optional): The method to use for the REST call. Defaults to "get".
            large_file (bool, optional): If True, the endpoint is a full URL. Defaults to False.

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
        """
        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"),
                resp_json,
            )

        # Create a URL to connect to
        if large_file:
            url = endpoint
        else:
            url = f"{consts.BASE_URL.strip('/')}{endpoint}"

        kwargs["headers"] = {
            **self.get_auth_headers(self._connector.config),
            **(kwargs.get("headers") or {}),
        }
        try:
            r = request_func(
                url,
                timeout=consts.REQUEST_DEFAULT_TIMEOUT,
                **kwargs,
            )
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Error Connecting to server. Details: {e!s}",
                ),
                resp_json,
            )
        processed_response = self._process_response(r, action_result)
        return (processed_response, r.headers) if return_response_headers else processed_response

    def _paginator(self, endpoint, action_result, method, limit=None, is_on_poll=False, **kwargs):
        """
        Handle paginated API responses by automatically fetching all pages.

        This method handles the API's pagination mechanism to retrieve complete result sets
        that span multiple pages, up to the specified limit.

        Args:
            endpoint (str): The API endpoint.
            action_result (ActionResult): The result of the action.
            method (str): The method of the request (GET, POST, PUT, DELETE, PATCH).
            limit (int, optional): The limit of the results. Defaults to 40.
            is_on_poll (bool, optional): True if the action is on poll.

        Returns:
            list: List of results.
        """
        results = []
        cursor = None
        if limit is None and is_on_poll:
            limit = 1000

        if limit is None:
            while True:
                updated_endpoint = f"{endpoint}?limit=40" if "?" not in endpoint else f"{endpoint}&limit=40"
                if cursor:
                    updated_endpoint += f"&cursor={cursor}"

                ret_val, json_resp = self.make_rest_call(updated_endpoint, action_result, method, **kwargs)
                if phantom.is_fail(ret_val):
                    return ret_val, []

                results.extend(json_resp.get("data", []))
                cursor = json_resp.get("meta", {}).get("cursor")
                if not cursor:
                    break
        else:
            limit = int(limit)
            remaining = limit

            while remaining > 0:
                batch_size = min(remaining, 40)
                updated_endpoint = f"{endpoint}?limit={batch_size}" if "?" not in endpoint else f"{endpoint}&limit={batch_size}"

                if cursor:
                    updated_endpoint += f"&cursor={cursor}"

                ret_val, json_resp = self.make_rest_call(updated_endpoint, action_result, method, **kwargs)
                if phantom.is_fail(ret_val):
                    return ret_val, []

                results.extend(json_resp.get("data", []))
                cursor = json_resp.get("meta", {}).get("cursor")
                remaining -= batch_size
                if not cursor:
                    break

        return phantom.APP_SUCCESS, results

    def _paginator_dtm(self, endpoint, action_result, method, limit=1000, **kwargs):
        """
        Handle paginated API responses by automatically fetching all pages for DTM alert.

        This method handles the API's pagination mechanism to retrieve complete result sets
        that span multiple pages, up to the specified limit.

        Args:
            endpoint (str): The API endpoint with the query parameters.
            action_result (ActionResult): The result of the action.
            method (str): The method of the request (GET, POST, PUT, DELETE, PATCH).
            limit (int, optional): The limit of the results. Defaults to 1000.

        Returns:
            tuple: A tuple of two elements. Success flag and a list of results.
        """
        page_size = 25  # Using max page size of 25 since DTM ref parameter is true
        limit = int(limit)
        remaining = limit
        results = []

        if limit <= page_size:
            self._connector.debug_print(f"The limit for DTM alerts ({limit}) is less than the page size ({page_size}).")
            updated_endpoint = f"{endpoint}?size={limit}" if "?" not in endpoint else f"{endpoint}&size={limit}"

            ret_val, json_resp = self.make_rest_call(updated_endpoint, action_result, method, **kwargs)
            if phantom.is_fail(ret_val):
                return ret_val, []

            results = json_resp.get("alerts", [])
            return phantom.APP_SUCCESS, results

        else:
            self._connector.debug_print(f"The limit for DTM alerts ({limit}) is greater than the page size ({page_size}).")
            next_page_token = None
            remaining = limit
            while remaining > 0:
                if next_page_token:
                    parsed = urlparse(endpoint)
                    new_query = urlencode({"page": next_page_token})
                    updated = parsed._replace(query=new_query)
                    updated_endpoint = urlunparse(updated)
                else:
                    updated_endpoint = f"{endpoint}?size={page_size}" if "?" not in endpoint else f"{endpoint}&size={page_size}"
                (ret_val, json_resp), response_headers = self.make_rest_call(
                    updated_endpoint, action_result, method, return_response_headers=True, **kwargs
                )

                if phantom.is_fail(ret_val):
                    return ret_val, []

                alerts_list = json_resp.get("alerts", [])
                alert_count = len(alerts_list)
                if remaining <= alert_count:
                    self._connector.debug_print(f"Remaining alerts ({remaining}) are less than or equal to the alert count ({alert_count}).")
                    results.extend(json_resp.get("alerts")[:remaining])
                    break

                self._connector.debug_print(f"Remaining alerts ({remaining}) are greater than the alert count ({alert_count}).")
                results.extend(json_resp.get("alerts"))
                remaining -= alert_count

                next_page_link = response_headers.get("link")
                if not next_page_link:
                    self._connector.debug_print("No 'next' page link found in response headers.")
                    break  # Break as there is no next page

                m = re.search(r"[?&]page=([^&>;]+)", next_page_link)
                if not m:
                    self._connector.debug_print("No page token found in the 'next' page link.")
                    break  # Break as there is no next page

                next_page_token = m.group(1)
                self._connector.debug_print(f"Remaining alerts to fetch: {remaining}")
            return phantom.APP_SUCCESS, results

    def get_auth_headers(self, config):
        """
        Generate headers with API key from the asset configuration.

        Args:
            config (dict): Asset configuration.

        Returns:
            dict: Headers with API key.
        """
        headers = {}

        if config.get("x-apikey"):
            headers["x-apikey"] = config.get("x-apikey")

        return headers

    @staticmethod
    def generate_basic_auth_header(username, password):
        """
        Generate a Basic Auth header given a username and password.

        Args:
            username (str): The username to use for Basic Auth.
            password (str): The password to use for Basic Auth.

        Returns:
            str: The Basic Auth header.
        """
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        return f"Basic {encoded_credentials}"

    def generate_json_body(self, body, allow_none, allow_empty, param, default_values):
        """
        Generate a JSON body given a body and template values.

        Args:
            body (dict): The body to generate the JSON from.
            allow_none (list): A list of keys that can have a value of None.
            allow_empty (dict): A dictionary of keys that can have an empty value.
            param (dict): A dictionary of template values.
            default_values (dict): A dictionary of default values.

        Returns:
            dict: The generated JSON body.
        """

        def _get_empty_value(_type):
            empty_values = {
                "string": "",
                "boolean": "",
                "integer": 0,
                "float": 0,
                "dict": {},
                "list": [],
            }
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

    def get_data_type(self, entity):
        """
        Determine the data type of the given entity.

        Args:
            entity (str): The entity to determine the data type for.

        Returns:
            str: The data type of the entity (e.g. "file", "ip", "domain", "url").
        """

        try:
            ipaddress.ip_address(entity)
            return consts.IP_ADDRESS
        except Exception:
            domain_regex = re.compile(r"^(?=.{1,253}$)(?!://)([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")
            if phantom.is_url(entity):
                return consts.URL
            elif bool(domain_regex.match(entity)):
                return consts.DOMAIN
            else:
                return consts.FILE

    def _get_id_from_scan_entity(self, action_result, scan_result):
        """
        Get the ID from the response.

        Args:
        - action_result (ActionResult): The result of the action.
        - scan_result (dict): The response from the API.

        Returns:
        - Tuple[str, str]: A tuple containing the status of the action and the ID.
        """
        try:
            analysis_id = scan_result.get("data", {}).get("id")
            if not analysis_id:
                return action_result.set_status(phantom.APP_ERROR, f"Analysis ID not found in response: {scan_result}"), None
        except Exception:
            return (
                action_result.set_status(phantom.APP_ERROR, "Error occurred while extracting 'id'"),
                None,
            )
        return phantom.APP_SUCCESS, analysis_id

    def _get_file_id_from_analysis(self, action_result, analysis):
        """
        Get the File ID from the response.

        Args:
        - action_result (ActionResult): The result of the action.
        - analysis (dict): The response from the API.

        Returns:
        - Tuple[str, str]: A tuple containing the status of the action and the ID.
        """
        try:
            file_id = analysis.get("meta", {}).get("file_info", {}).get("sha256")
        except Exception:
            return (
                action_result.set_status(phantom.APP_ERROR, "Error occurred while extracting 'file_id'"),
                None,
            )
        return phantom.APP_SUCCESS, file_id

    def _get_url_id_from_analysis(self, action_result, analysis):
        """
        Get the URL ID from the response.

        Args:
        - action_result (ActionResult): The result of the action.
        - analysis (dict): The response from the API.

        Returns:
        - Tuple[str, str]: A tuple containing the status of the action and the ID.
        """
        try:
            url_id = analysis.get("meta", {}).get("url_info", {}).get("id")
        except Exception:
            return (
                action_result.set_status(phantom.APP_ERROR, "Error occurred while extracting 'url_id'"),
                None,
            )
        return phantom.APP_SUCCESS, url_id

    def _poll_analysis_until_complete(self, action_result, entity_type, analysis_id, poll_interval, is_private=False):
        """
        Poll the GTI API for analysis results until completion or timeout.

        Args:
            self: The instance of the class.
            action_result (ActionResult): The result of the action.
            entity_type (str): The type of entity (e.g. "file", "url").
            analysis_id (str): The ID of the analysis.
            poll_interval (int): The interval to poll for the analysis.
            is_private (bool): To check if it's private anlaysis. Defaults to False

        Returns:
            Tuple[str, str]: A tuple containing the status of the action and the ID.
        """

        attempt = 1
        if is_private:
            endpoint, method = (
                consts.PRIVATE_ANALYSES_ENDPOINT.format(id=analysis_id),
                "get",
            )
        else:
            endpoint, method = consts.ANALYSES_ENDPOINT.format(id=analysis_id), "get"
        args = {
            "endpoint": endpoint,
            "action_result": action_result,
            "method": method.lower(),
            "headers": {},
        }

        # equal to the number of attempts
        poll_attempts = poll_interval
        while attempt <= poll_attempts:
            self._connector.save_progress(f"Analysing the entity... attempt {attempt} of {poll_attempts}")

            ret_val, json_resp = self.make_rest_call(**args)

            if phantom.is_fail(ret_val):
                return ret_val, None
            if json_resp.get("error", {}).get("code") in consts.PASS_ERROR_CODE.values():
                return action_result.set_status(phantom.APP_SUCCESS, "Got error"), None

            if json_resp.get("data").get("attributes").get("status") == "completed":
                # Get id from the analysis
                if entity_type == consts.URL:
                    ret_val, entity_id = self._get_url_id_from_analysis(action_result, json_resp)
                elif entity_type == consts.FILE:
                    ret_val, entity_id = self._get_file_id_from_analysis(action_result, json_resp)
                if phantom.is_fail(ret_val):
                    return action_result.get_status(), None
                return phantom.APP_SUCCESS, entity_id

            attempt += 1
            time.sleep(60)

        return (
            action_result.set_status(
                phantom.APP_ERROR,
                "Reached max polling attempts. Try rerunning the action",
            ),
            None,
        )

    def submit_url_for_analysis(self, action_result, url):
        """
        Submit a URL to GTI API for scanning and retrieve its identifier.

        Args:
            self: The instance of the class.
            action_result (ActionResult): The result of the action.
            url (str): The URL to retrieve the ID for.

        Returns:
            Tuple[str, str]: A tuple containing the status of the action and the ID.
        """
        endpoint, method = consts.SCAN_URL_ENDPOINT, "post"

        args = {
            "endpoint": endpoint,
            "action_result": action_result,
            "method": method.lower(),
            "headers": {},
            "data": {"url": url},
        }
        ret_val, json_resp = self.make_rest_call(**args)

        if phantom.is_fail(ret_val):
            return ret_val, None

        # Get analysis id from the scan_result
        ret_val, analysis_id = self._get_id_from_scan_entity(action_result, json_resp)

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        return self._poll_analysis_until_complete(action_result, consts.URL, analysis_id, consts.RETRY_COUNT)

    def get_file_hash_from_input(self, action_result, file_hash, password=None):
        """
        Retrieve a file from the Phantom vault and submit it to GTI API to obtain its file hash identifier.

        Args:
            self: The instance of the class.
            action_result (ActionResult): The result of the action.
            file_hash (str): The file_hash which could be a vault ID or a file hash.
            password (str, optional): The password for the file (if required). Defaults to None.

        Returns:
            Tuple[str, str]: A tuple containing the status of the action and the ID.
        """

        # Check if the file_hash is a known hash type (sha256, md5)
        if phantom.is_sha256(file_hash) or phantom.is_md5(file_hash):
            return phantom.APP_SUCCESS, file_hash

        # If the file_hash might be a SHA1, check if it is a Vault ID
        # Vault ID is a SHA1 hash format, ref:https://docs.splunk.com/Documentation/SOAR/current/PlaybookAPI/VaultAPI
        if not phantom.is_sha1(file_hash):
            return (
                action_result.set_status(phantom.APP_ERROR, consts.ERROR_MESSAGE_INVALID_ENTITY),
                None,
            )

        # Attempt to retrieve the file information from the vault
        try:
            _, _, file_info = ph_rules.vault_info(container_id=self._connector.get_container_id(), vault_id=file_hash)
            if not file_info:
                # If file_info is empty, the vault ID is not valid, but we treat it as a regular SHA1 file_hash
                return phantom.APP_SUCCESS, file_hash

            # File info found, meaning the file_hash is a valid Vault ID
            # Extract the first item from the file_info list
            file_info = next(iter(file_info))

            file_path = file_info["path"]
            file_name = file_info["name"]
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return (
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Unable to retrieve file from vault: {error_message}",
                ),
                None,
            )

        try:
            files = [("file", (file_name, open(file_path, "rb"), "application/octet-stream"))]
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return (
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Error occurred while reading file. {error_message}",
                ),
                None,
            )

        endpoint, method = consts.SCAN_FILE_ENDPOINT, "get"

        args = {
            "endpoint": endpoint,
            "action_result": action_result,
            "method": method.lower(),
            "headers": {},
        }

        ret_val, json_resp = self.make_rest_call(**args)

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        try:
            upload_url = json_resp["data"]
        except KeyError:
            return (
                action_result.set_status(phantom.APP_ERROR, "Couldn't fetch URL for uploading file"),
                None,
            )

        args = {
            "endpoint": upload_url,
            "action_result": action_result,
            "method": "post",
            "headers": {},
            "data": {"password": password},
            "files": files,
        }
        ret_val, json_resp = self.make_rest_call(large_file=True, **args)

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        # Get analysis id from the scan_result
        ret_val, analysis_id = self._get_id_from_scan_entity(action_result, json_resp)

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        return self._poll_analysis_until_complete(action_result, consts.FILE, analysis_id, consts.RETRY_COUNT)

    def convert_unix_to_utc(self, unix_time):
        """
        Convert a Unix timestamp to a UTC datetime string in ISO 8601 format.

        Args:
            self: The instance of the class.
            unix_time (int): The Unix timestamp to convert.

        Returns:
            str: The UTC datetime string in ISO 8601 format.

        """
        dt_utc = datetime.fromtimestamp(unix_time, tz=timezone.utc)

        # Format the datetime as a string in ISO 8601 format
        formatted_timestamp = dt_utc.strftime("%Y-%m-%dT%H:%M:%S")

        return formatted_timestamp

    def build_last_seen_after(self, days: int = 0, hours: int = 0) -> str:
        """
        Returns last_seen_after in formatted UTC time string (e.g., 2025-05-14T11:00:00Z)
        that is `days` and `hours` before the current UTC time.

        Args:
            days (int): Number of days before now
            hours (int): Number of hours before now

        Returns:
            str: last_seen_after formatted string (e.g., '2025-05-14T10:00:00Z')
        """
        target_time = datetime.now(timezone.utc) - timedelta(days=days, hours=hours)
        value = target_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        self._connector.debug_print(f"last_seen_after value {days} days, {hours} hours before the current UTC time: {value}")
        return value

    def clean_search_string(self, search_string):
        """
        Cleans the given search string by removing keyword:value pairs and normalizing spacing.

        Args:
            search_string (str): The search string to be cleaned.

        Returns:
            str: The cleaned search string.

        Steps:
            1. Inserts a space before any known keyword that is stuck to the previous word.
            2. Builds a regex pattern to remove keyword:value pairs.
            3. Removes all matching pairs from the search string.
            4. Normalizes spacing by removing multiple consecutive spaces and trimming leading/trailing spaces.
            5. Prints the cleaned search string for debugging purposes.
        """
        keywords = ["last_seen_after", "last_seen_before", "first_seen_after"]

        # Step 1: Insert space before any known keyword that is stuck to previous word
        for keyword in keywords:
            search_string = re.sub(r"(?<![\s])(" + re.escape(keyword) + r")\s*:", r" \1:", search_string)

        # Step 2: Build regex to remove keyword:value pairs
        pattern = r"\b(?:" + "|".join(re.escape(k) for k in keywords) + r")\s*:\s*[^ \n\t]+"

        # Remove all matching pairs
        cleaned = re.sub(pattern, "", search_string)

        # Step 3: Normalize spacing
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        self._connector.debug_print(f"Cleaned search string for ASM: {cleaned}")
        return cleaned

    def _common_message_handler_for_soar(self, response, operation):
        """
        Message handler to handle the logs from SOAR APIs

        Parameters:
            response (object): The response object received from the API call.
            operation (str): The operation being performed.

        Returns:
            dict: The parsed response data.
        """
        data = {}
        try:
            data = json.loads(response.text)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self._connector.debug_print(f"Failed while parsing the response {error_message}")
            return data

        if isinstance(data, dict) and data.get("failed", False) and data.get("message"):
            self._connector.debug_print("Error occurred while {}: {}".format(operation, data.get("message")))

        return data

    def get_container_details(self, container_id):
        """
        Retrieves the container details from the Phantom server.

        Args:
            container_id (str): The ID of the container to retrieve.

        Returns:
            dict: The container details if successful, else an empty dictionary.
        """
        url = consts.SPLUNK_SOAR_CONTAINER_ENDPOINT.format(url=self._connector.get_phantom_base_url(), container_id=container_id)
        data = {}
        try:
            r = requests.get(url, verify=ph_config.platform_strict_tls)
        except Exception as e:
            self._connector.debug_print(f"Unable to get the container deatale for {container_id}", e)
            return data

        data = self._common_message_handler_for_soar(r, "getting the container details")
        return data

    def update_container_status(self, container_id, status):
        """
        Updates the status of a container in Phantom.

        Args:
            container_id (str): The ID of the container to update.
            status (str): The status to update the container with.

        Returns:
            None
        """
        body = self.get_container_details(container_id)
        if body:
            body["status"] = status
        self._connector.debug_print("Updating the status of container")
        url = consts.SPLUNK_SOAR_CONTAINER_ENDPOINT.format(url=self._connector.get_phantom_base_url(), container_id=container_id)
        try:
            r = requests.post(url, json=body, verify=ph_config.platform_strict_tls)
        except Exception as e:
            self._connector.debug_print(f"Unable to update the status of container for {container_id}", e)

        self._common_message_handler_for_soar(r, "Updating the container status")

    def _get_artifact_of_container_id(self, container_id):
        """
        Retrieve the artifact associated with container.

        Args:
            container_id (str): The ID of the container.

        Returns:
            dict: A dictionary containing the artifact IDs as keys and the corresponding IDs as values.
            Returns an empty dictionary if no artifact is found.
        """
        url = consts.SPLUNK_SOAR_GET_CONTAINER_ARTIFACT_ENDPOINT.format(url=self._connector.get_phantom_base_url(), container_id=container_id)
        artifact_ids = {}
        try:
            r = requests.get(url, verify=ph_config.platform_strict_tls)
        except Exception as e:
            self._connector.debug_print("Unable to query for artifact", e)
            return artifact_ids

        resp_json = self._common_message_handler_for_soar(r, "querying for artifact")

        if resp_json.get("count", 0) <= 0:
            self._connector.debug_print("No artifact matched")
            return artifact_ids
        try:
            artifact_ids.update({artifact.get("source_data_identifier"): artifact.get("id") for artifact in resp_json.get("data", [])})
            self._connector.debug_print(f"Artifact ids updated: {artifact_ids}")
        except Exception as e:
            self._connector.debug_print("Artifact results are not proper: ", e)
            return artifact_ids

        return artifact_ids

    def _update_artifact(self, artifact_id, artifact):
        """
        Update an artifact.

        Parameters:
            artifact_id (str): The ID of the artifact to be updated.

        Returns:
            None
        """
        url = consts.SPLUNK_SOAR_ARTIFACT_ENDPOINT.format(url=self._connector.get_phantom_base_url(), artifact_id=artifact_id)
        self._connector.debug_print(f"Updating artifact with id {artifact_id}")
        try:
            resp = requests.post(url, json=artifact, verify=ph_config.platform_strict_tls)
        except Exception as e:
            self._connector.debug_print("Unable to update the artifact", e)

        self._common_message_handler_for_soar(resp, "updating artifact")


class Validator:
    @staticmethod
    def validate_integer(action_result, parameter, key, allow_zero=False, allow_negative=False):
        """
        Validate if a given parameter is an integer.

        Args:
            action_result (ActionResult): The ActionResult object to append
                error messages to.
            parameter (str): The parameter to validate.
            key (str): The key of the parameter to validate.
            allow_zero (bool): Whether to allow zero as a valid integer
                (default is False).
            allow_negative (bool): Whether to allow negative integers as valid
                (default is False).

        Returns:
            Tuple[int, int]: A tuple containing the status of the action and the
                validated integer. If the parameter is not a valid integer, the
                status will be phantom.APP_ERROR and the second element of the
                tuple will be None.
        """
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
                action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_INT_PARAM.format(key=key)),
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

    @staticmethod
    def validate_dict(action_result, parameter, key):
        """
        Validate a parameter as a JSON dictionary.

        Args:
            action_result (ActionResult): The ActionResult object.
            parameter (str): The parameter to validate.
            key (str): The key of the parameter to validate.

        Returns:
            tuple[int, dict|None]: A tuple containing the status of the validation and the valid parameter value.
        """
        try:
            parameter = json.loads(parameter.replace("'", "'"))
        except Exception:
            try:
                parameter = eval(parameter)
            except Exception:
                return (
                    action_result.set_status(
                        phantom.APP_ERROR,
                        consts.ERROR_INVALID_JSON_PARAM.format(key=key),
                    ),
                    None,
                )

        if not isinstance(parameter, dict):
            return (
                action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_JSON_PARAM.format(key=key)),
                None,
            )

        return phantom.APP_SUCCESS, parameter

    @staticmethod
    def validate_list(action_result, parameter, key):
        """
        Validate a parameter as a JSON list.

        Args:
            action_result (ActionResult): The ActionResult object.
            parameter (str): The parameter to validate.
            key (str): The key of the parameter to validate.

        Returns:
            tuple[int, list|None]: A tuple containing the status of the validation and the valid parameter value.
        """
        try:
            parameter = json.loads(parameter.replace("'", "'"))
        except Exception:
            try:
                parameter = eval(parameter)
                if isinstance(parameter, tuple):
                    parameter = list(parameter)
            except Exception:
                parameter = [result for value in parameter.split(",") if (result := value.strip())]

        if not isinstance(parameter, list):
            return (
                action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_LIST_PARAM.format(key=key)),
                None,
            )

        return phantom.APP_SUCCESS, parameter

    @staticmethod
    def validate_dropdown(action_result, parameter, key, dropdown):
        """
        Validate a parameter as a value from a given dropdown.

        Args:
            action_result (ActionResult): The ActionResult object.
            parameter (str): The parameter to validate.
            key (str): The key of the parameter to validate.
            dropdown (dict): The available options for the parameter.

        Returns:
            tuple[int, str|None]: A tuple containing the status of the validation and the valid parameter value.
        """
        parameter = parameter.lower()
        if parameter not in dropdown:
            return (
                action_result.set_status(
                    phantom.APP_ERROR,
                    consts.ERROR_INVALID_SELECTION.format(key, json.dumps(list(dropdown.keys()))),
                ),
                None,
            )

        return phantom.APP_SUCCESS, dropdown.get(parameter)

    @staticmethod
    def validate_integer_range(action_result, parameter, key, min_value, max_value):
        """
        Validate a parameter as an integer within a given range.

        Args:
            action_result (ActionResult): The ActionResult object.
            parameter (str): The parameter to validate.
            key (str): The key of the parameter to validate.
            min_value (int): The minimum allowed value.
            max_value (int): The maximum allowed value.

        Returns:
            tuple[int, int|None]: A tuple containing the status of the validation and the valid parameter value.
        """
        try:
            parameter = int(parameter)
        except Exception:
            return (
                action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_INT_PARAM.format(key=key)),
                None,
            )

        if parameter < min_value or parameter > max_value:
            return (
                action_result.set_status(
                    phantom.APP_ERROR,
                    consts.ERROR_INVALID_INT_RANGE.format(key=key, min_value=min_value, max_value=max_value),
                ),
                None,
            )

        return phantom.APP_SUCCESS, parameter
