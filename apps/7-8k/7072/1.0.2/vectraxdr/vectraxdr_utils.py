# File: vectraxdr_utils.py
#
# Copyright (c) Vectra, 2023-2025
#
# This unpublished material is proprietary to Vectra.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Vectra.
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
import time
import uuid
from datetime import datetime, timezone

import dateparser
import encryption_helper
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.vault import Vault

import vectraxdr_consts as consts


class RetVal(tuple):
    """This class returns the tuple of two elements."""

    def __new__(cls, val1, val2=None):
        """Create a new tuple object."""
        return tuple.__new__(RetVal, (val1, val2))


class VectraxdrUtils:
    """This class holds all the util methods."""

    def __init__(self, connector=None):
        """Util constructor method."""
        self._connector = connector
        self._access_token = None
        self._refresh_token = None
        self._response_header = None
        self.file_path = None

        if connector:
            # Decrypt the state file
            connector.state = self._decrypt_state(connector.state)
            self._access_token = connector.state.get(consts.VECTRA_STATE_TOKEN, {}).get(consts.VECTRA_STATE_ACCESS_TOKEN, None)
            self._refresh_token = connector.state.get(consts.VECTRA_STATE_TOKEN, {}).get(consts.VECTRA_STATE_REFRESH_TOKEN, None)

    def _get_error_message_from_exception(self, e):
        """Get an appropriate error message from the exception.

        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_message = consts.VECTRA_ERROR_MESSAGE_UNAVAILABLE

        self._connector.error_print("Error occurred.", e)
        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except Exception as e:
            self._connector.error_print(f"Error occurred while fetching exception information. Details: {e!s}")

        if not error_code:
            error_text = f"Error message: {error_message}"
        else:
            error_text = f"Error code: {error_code}. Error message: {error_message}"

        return error_text

    # Validations
    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
        """Check if the provided input parameter value is valid.

        :param action_result: Action result or BaseConnector object
        :param parameter: Input parameter value
        :param key: Input parameter key
        :param allow_zero: Zero is allowed or not (default False)
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and parameter value itself.
        """
        try:
            if not float(parameter).is_integer():
                return action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_INVALID_INT_PARAM.format(key=key)), None

            parameter = int(parameter)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_INVALID_INT_PARAM.format(key=key)), None

        if parameter < 0:
            return action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_NEGATIVE_INT_PARAM.format(key=key)), None
        if not allow_zero and parameter == 0:
            return action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_ZERO_INT_PARAM.format(key=key)), None

        return phantom.APP_SUCCESS, parameter

    # Parsing
    def _process_empty_response(self, response, action_result):
        """Process the empty response returned from the server.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and an empty dictionary
        """
        if response.status_code in consts.VECTRA_EMPTY_RESPONSE_STATUS_CODE:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_EMPTY_RESPONSE.format(response.status_code)))

    def _process_html_response(self, response, action_result):
        """Process the html response returned from the server.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_ERROR and the None value
        """
        # An html response, treat it like an error
        status_code = response.status_code
        if 200 <= status_code < 399:
            return RetVal(phantom.APP_SUCCESS, response.text)
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove the script, style, footer and navigation part from the HTML message
            for element in soup(["script", "style", "footer", "nav"]):
                element.extract()
            error_text = soup.text or "No data found"
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except Exception:
            error_text = "Cannot parse error details"

        message = consts.VECTRA_ERROR_GENERAL_HTML_MESSAGE.format(status_code, response.reason, error_text)
        message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message))

    def _process_json_response(self, response, action_result):
        """Process the json response returned from the server.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and the response dictionary
        """
        try:
            resp_json = response.json()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_JSON_RESPONSE.format(error_message)))

        if 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        message = f"Error from server. Status code: {response.status_code}, Error message: {resp_json.get('error', resp_json)}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message))

    def _process_pcap_response(self, response, action_result):
        guid = uuid.uuid4()
        if hasattr(Vault, "get_vault_tmp_dir"):
            vault_tmp_dir = Vault.get_vault_tmp_dir().rstrip("/")
            local_dir = f"{vault_tmp_dir}/{guid}"
        else:
            local_dir = f"/opt/phantom/vault/tmp/{guid}"

        self._connector.save_progress(f"Using temp directory: {local_dir}")

        try:
            os.makedirs(local_dir)
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, "Unable to create temporary vault folder.", self._get_error_message_from_exception(e)
            )

        response_headers = response.headers
        filename = response_headers["Content-Disposition"].split("filename=")[-1]
        filename = filename.replace('"', "")
        file_path = f"{local_dir}/{filename}"
        self.file_path = file_path

        try:
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=5 * 1024 * 1024):
                    f.write(chunk)
        except Exception as e:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Unable to write file to disk. Error: {self._get_error_message_from_exception(e)}"),
                None,
            )

        if 200 <= response.status_code <= 399:
            return RetVal(phantom.APP_SUCCESS, None)

        message = "Error from server. Status Code: {} Data from server: {}".format(
            response.status_code, response.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, response, action_result, is_stream_download=False):
        """Process the response returned from the server.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and the response dictionary
        """
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": response.status_code})
            if not is_stream_download:
                action_result.add_debug_data({"r_text": response.text})
            action_result.add_debug_data({"r_headers": response.headers})

        if "json" in response.headers.get("Content-Type", ""):
            return self._process_json_response(response, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in response.headers.get("Content-Type", ""):
            return self._process_html_response(response, action_result)

        if "force-download" in response.headers.get("Content-Type", ""):
            return self._process_pcap_response(response, action_result)

        # Process each 'Content-Type' of response separately
        # Process a json response
        # it's not content-type that is to be parsed, handle an empty response

        if not response.text:
            return self._process_empty_response(response, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. {}".format(
            consts.VECTRA_ERROR_GENERAL_MESSAGE.format(response.status_code, response.text.replace("{", "{{").replace("}", "}}"))
        )

        # Large HTML pages may be returned incase of 500 error from server.
        # Use default error message in place of large HTML page.
        if len(message) > 500:
            return RetVal(action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_HTML_RESPONSE))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message))

    def _make_rest_call(self, endpoint, action_result, method="get", headers=None, params=None, is_stream_download=False, **kwargs):
        """Make an REST API call and passes the response to the process method.

        :param endpoint: The endpoint string to make the REST API request
        :param action_result: Action result or BaseConnector object
        :param method: The HTTP method for API request
        :param headers: The headers to pass in API request
        :param params: The params to pass in API request
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and the response dictionary returned by the process response method
        """
        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"))

        is_stream_download = kwargs.pop("is_stream_download", False)
        # Create a URL to connect to
        next_page_url = kwargs.pop("next_page_url", None)
        url = next_page_url or f"{self._connector.config.get('base_url').rstrip('/')}{endpoint}"

        no_of_retries = consts.VECTRA_NO_OF_RETRIES

        user_agent = "VectraXDR-SplunkSOAR-{}".format(self._connector.get_app_json().get("app_version"))
        headers.update({"User-agent": user_agent})

        while no_of_retries:
            try:
                response = request_func(
                    url,
                    timeout=consts.VECTRA_REQUEST_TIMEOUT,
                    headers=headers,
                    params=params,
                    verify=self._connector.config.get("verify_server_cert", False),
                    stream=is_stream_download,
                    **kwargs,
                )
            except Exception as e:
                error_message = self._get_error_message_from_exception(e)
                return RetVal(action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_REST_CALL.format(error_message)))

            if response.status_code not in [429, 500]:
                break

            self._connector.save_progress(f"Received {response.status_code} status code from the server")
            self._connector.save_progress(f"Retrying after {consts.VECTRA_WAIT_TIME_FOR_RETRY} second(s)...")
            time.sleep(consts.VECTRA_WAIT_TIME_FOR_RETRY)
            no_of_retries -= 1

        return self._process_response(response, action_result, is_stream_download=is_stream_download)

    def _generate_access_token(self, action_result):
        """Generate a new access token using the provided credentials and stores it to the state file.

        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}

        self._connector.debug_print("Generating access token")
        data = {"grant_type": "refresh_token", "refresh_token": self._refresh_token}

        ret_val, resp_json = self._make_rest_call(consts.VECTRA_ENDPOINT_TOKEN, action_result, data=data, method="post", headers=headers)

        if phantom.is_fail(ret_val):
            self._connector.state.get(consts.VECTRA_STATE_TOKEN, {}).pop(consts.VECTRA_STATE_ACCESS_TOKEN, None)
            return action_result.get_status()

        try:
            self._access_token = resp_json[consts.VECTRA_STATE_ACCESS_TOKEN]
        except KeyError:
            self._connector.debug_print("Unable to find the access token from the returned response")
            self._connector.state.get(consts.VECTRA_STATE_TOKEN, {}).pop(consts.VECTRA_STATE_ACCESS_TOKEN, None)
            return action_result.set_status(phantom.APP_ERROR, "Access token generation failed")

        self._connector.state[consts.VECTRA_STATE_TOKEN][consts.VECTRA_STATE_ACCESS_TOKEN] = resp_json[consts.VECTRA_STATE_ACCESS_TOKEN]
        self._connector.debug_print("Access token has been generated successfully")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _generate_refresh_token(self, action_result):
        """Generate a new refresh token using the provided credentials and stores it to the state file.

        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}

        self._connector.debug_print("Generating both tokens")
        data = {"grant_type": "client_credentials"}
        creds = (self._connector.config["client_id"], self._connector.config["client_secret"])
        ret_val, resp_json = self._make_rest_call(
            consts.VECTRA_ENDPOINT_TOKEN, action_result, data=data, method="post", headers=headers, auth=creds
        )

        if phantom.is_fail(ret_val):
            self._connector.state.pop(consts.VECTRA_STATE_TOKEN, None)
            return action_result.get_status()

        try:
            self._access_token = resp_json[consts.VECTRA_STATE_ACCESS_TOKEN]
            self._refresh_token = resp_json[consts.VECTRA_STATE_REFRESH_TOKEN]

        except KeyError:
            self._connector.debug_print("Unable to find the Authentication Tokens from the returned response")
            self._connector.state.pop(consts.VECTRA_STATE_TOKEN, None)
            return action_result.set_status(phantom.APP_ERROR, "Tokens generation failed")

        self._connector.state[consts.VECTRA_STATE_TOKEN] = {
            consts.VECTRA_STATE_ACCESS_TOKEN: resp_json[consts.VECTRA_STATE_ACCESS_TOKEN],
            consts.VECTRA_STATE_REFRESH_TOKEN: resp_json[consts.VECTRA_STATE_REFRESH_TOKEN],
        }
        self._connector.debug_print("Tokens have been generated successfully")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _make_rest_call_helper(self, endpoint, action_result, method="get", headers=None, params=None, **kwargs):
        """Make the REST API call and generates new token if required.

        :param endpoint: The endpoint string to make the REST API request
        :param action_result: Action result or BaseConnector object
        :param method: The HTTP method for API request
        :param headers: The headers to pass in API request
        :param params: The params to pass in API request
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and the response dictionary
        """
        if not headers:
            headers = {}

        if self._access_token:
            headers.update({"Authorization": f"Bearer {self._access_token}"})

        ret_val, resp_json = self._make_rest_call(endpoint, action_result, method, headers=headers, params=params, **kwargs)

        if phantom.is_fail(ret_val):
            # If token is expired, generate a new token
            message = action_result.get_message()
            is_access_token_expired = message and consts.VECTRA_ACCESS_TOKEN_EXPIRE_MESSAGE in message
            is_refresh_token_expired = message and consts.VECTRA_REFRESH_TOKEN_EXPIRE_MESSAGE in message
            is_refresh_token_invalid = message and consts.VECTRA_REFRESH_TOKEN_INVALID_MESSAGE in message
            is_refresh_token_present = self._refresh_token is not None and self._refresh_token != ""
            is_access_token_present = self._access_token is not None and self._access_token != ""

            if is_access_token_expired and is_refresh_token_present:
                ret_val = self._generate_access_token(action_result)
                if phantom.is_fail(ret_val):
                    return_message = action_result.get_message()
                    if consts.VECTRA_REFRESH_TOKEN_EXPIRE_MESSAGE in return_message:
                        is_refresh_token_expired = True

                    elif consts.VECTRA_REFRESH_TOKEN_INVALID_MESSAGE in return_message:
                        is_refresh_token_invalid = True
                    else:
                        return RetVal(action_result.get_status())

            # Generate only if refresh token is not present and access token is expired or not present
            should_generate_refresh = not is_refresh_token_present and (is_access_token_expired or not is_access_token_present)
            if is_refresh_token_expired or is_refresh_token_invalid or should_generate_refresh:
                ret_val = self._generate_refresh_token(action_result)
                if phantom.is_fail(ret_val):
                    return RetVal(action_result.get_status())

            headers.update({"Authorization": f"Bearer {self._access_token}"})
            ret_val, resp_json = self._make_rest_call(endpoint, action_result, method, headers=headers, params=params, **kwargs)
        if phantom.is_fail(ret_val):
            return RetVal(action_result.get_status())

        return RetVal(phantom.APP_SUCCESS, resp_json)

    def _encrypt_state(self, state):
        """Encrypt the state file.

        :param state: state dictionary to be encrypted
        :return: state dictionary with encrypted token
        """
        access_token = state.get(consts.VECTRA_STATE_TOKEN, {}).get(consts.VECTRA_STATE_ACCESS_TOKEN)
        refresh_token = state.get(consts.VECTRA_STATE_TOKEN, {}).get(consts.VECTRA_STATE_REFRESH_TOKEN)
        try:
            if access_token:
                encrypted_access_token = encryption_helper.encrypt(access_token, self._connector.get_asset_id())
                state[consts.VECTRA_STATE_TOKEN][consts.VECTRA_STATE_ACCESS_TOKEN] = encrypted_access_token
            if refresh_token:
                encrypted_refresh_token = encryption_helper.encrypt(refresh_token, self._connector.get_asset_id())
                state[consts.VECTRA_STATE_TOKEN][consts.VECTRA_STATE_REFRESH_TOKEN] = encrypted_refresh_token
            else:
                state.get(consts.VECTRA_STATE_TOKEN, {}).pop(consts.VECTRA_STATE_REFRESH_TOKEN, None)

        except Exception as e:
            self._connector.debug_print("Error occurred while encrypting the state file.", e)
            state.pop(consts.VECTRA_STATE_TOKEN, None)
        return state

    def _decrypt_state(self, state):
        """Decrypt the state file.

        :param state: state dictionary to be decrypted
        :return: state dictionary with decrypted token
        """
        access_token = state.get(consts.VECTRA_STATE_TOKEN, {}).get(consts.VECTRA_STATE_ACCESS_TOKEN)
        refresh_token = state.get(consts.VECTRA_STATE_TOKEN, {}).get(consts.VECTRA_STATE_REFRESH_TOKEN)
        try:
            if access_token:
                state[consts.VECTRA_STATE_TOKEN][consts.VECTRA_STATE_ACCESS_TOKEN] = encryption_helper.decrypt(
                    access_token, self._connector.get_asset_id()
                )
            if refresh_token:
                state[consts.VECTRA_STATE_TOKEN][consts.VECTRA_STATE_REFRESH_TOKEN] = encryption_helper.decrypt(
                    refresh_token, self._connector.get_asset_id()
                )
        except Exception as e:
            self._connector.debug_print("Error occurred while decrypting the state file.", e)
            state.pop(consts.VECTRA_STATE_TOKEN, None)
        return state

    def _sanitize_comma_separated_values(self, field):
        fields_list = [x.strip() for x in field.split(",")]
        fields_list = list(filter(None, fields_list))
        return fields_list

    def _parse_datetime(self, datetime):
        """Convert datetime string to datetime object.

        :param datetime: datetime string
        :return: datetime object
        """
        date_dt = dateparser.parse(datetime)
        if date_dt is None:
            raise Exception(f"Unable to parse {datetime}")
        datetime = date_dt.strftime(consts.VECTRA_LAST_MODIFIED_TIMESTAMP_FORMAT)
        datetime = dateparser.parse(datetime)

        return datetime

    def _check_invalid_since_utc_time(self, time):
        """Determine that given time is not before 1970-01-01T00:00:00Z.

        :param action_result: object of ActionResult class
        :param time: object of time

        :return: status(True/False)
        """
        # Check that given time must not be before 1970-01-01T00:00:00Z.
        return time >= self._parse_datetime("1970-01-01T00:00:00Z")

    def _check_date_format(self, action_result, date):
        """Validate the value of time parameter given in the action parameters.

        :param action_result: object of ActionResult class
        :param date: value of time(start/end/reference) action parameter

        :return: status(True/False)
        """
        # Initialize time for given value of date
        time = None
        try:
            # Check for the time is in valid format or not
            time = self._parse_datetime(date)
            # Taking current UTC time as end time
            end_time = datetime.now(timezone.utc)
            # Check for given time is not before 1970-01-01T00:00:00Z
            ret_val = self._check_invalid_since_utc_time(time)
            if phantom.is_fail(ret_val):
                return action_result.set_status(phantom.APP_ERROR, consts.VECTRA_UTC_SINCE_TIME_ERROR)

            # Checking future date
            if time >= end_time:
                msg = consts.VECTRA_GREATER_EQUAL_TIME_ERROR.format(consts.VECTRA_CONFIG_TIME_POLL_NOW)
                return action_result.set_status(phantom.APP_ERROR, msg)
        except Exception as e:
            err_txt = self._get_error_message_from_exception(e)
            message = f"Invalid date string received for 'Start time for on poll' parameter. Error\
                  occurred while checking date format. Error: {err_txt}"
            return action_result.set_status(phantom.APP_ERROR, message)
        return phantom.APP_SUCCESS

    def _extract_ids_from_param(self, action_result, param, ids, required=False, is_numeric=False):
        if is_numeric:
            ids_list = [int(id.strip()) for id in ids.split(",") if id.strip().isnumeric()]
        else:
            ids_list = [id.strip() for id in ids.split(",") if id.strip()]
        if not ids_list and required:  # If required param
            return action_result.set_status(phantom.APP_ERROR, f"Please provide a valid value in the '{param}' action parameter"), None
        return phantom.APP_SUCCESS, ids_list

    def _mark_detection(self, action_result, detection_ids, mark="True"):
        url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_DETECTIONS_ENDPOINT}"
        payload = {"detectionIdList": detection_ids, "mark_as_fixed": mark}

        ret_val, response = self._make_rest_call_helper(url, action_result, "patch", json=payload)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, response

    def _get_entity(self, action_result, entity_id, entity_type):
        entity_url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_DESCRIBE_ENTITY.format(entity_id=entity_id)}"
        params = {"type": entity_type}
        ret_val, response = self._make_rest_call_helper(entity_url, action_result, params=params)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, response

    def _get_detection_ids_from_entity(self, action_result, entity, data_type):
        detection_ids = []
        try:
            detection_set = entity.get("detection_set", [])
            for detection in detection_set:
                detection_ids.append(data_type(detection.rsplit("/", 1)[1]))
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Error occurred while extracting detection ids"), None
        return phantom.APP_SUCCESS, detection_ids

    def _get_entity_related_detection_ids(self, action_result, entity_id, entity_type):
        ret_val, response = self._get_entity(action_result, entity_id, entity_type)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        ret_val, detection_ids = self._get_detection_ids_from_entity(action_result, response, int)

        return ret_val, detection_ids

    def _get_outcome_map(self, action_result, outcome):
        outcomes_url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_ASSIGNMENT_OUTCOMES}"
        ret_val, response = self._make_rest_call_helper(outcomes_url, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None
        outcomes_map = {result.get("title"): result.get("id") for result in response.get("results", [])}
        if outcomes_map.get(outcome):
            return action_result.set_status(phantom.APP_SUCCESS), str(outcomes_map[outcome])

        return action_result.set_status(
            phantom.APP_ERROR, f"Invalid outcome has been provided. Please provide valid outcome value from {list(outcomes_map.keys())}"
        ), None

    def _get_entity_related_tags(self, action_result, entity_id, entity_type):
        url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_TAG_ENDPOINT.format(entity_id=entity_id)}"
        params = {"type": entity_type}
        ret_val, response = self._make_rest_call_helper(url, action_result, params=params)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        all_tags = response.get("tags")
        return phantom.APP_SUCCESS, all_tags

    def _add_remove_entity_related_tags(self, action_result, entity_id, entity_type, tags):
        url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_TAG_ENDPOINT.format(entity_id=entity_id)}"
        params = {"type": entity_type}
        payload = {"tags": tags}
        ret_val, response = self._make_rest_call_helper(url, action_result, method="patch", params=params, json=payload)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, response

    def _paginator(self, action_result, endpoint, params=None, limit=None):
        """
        Create an iterator that will paginate through responses from called methods.

        :param action_result: Object of ActionResult class
        :param endpoint: Endpoint for pagination
        :param params: Request parameters
        :param limit: Limit number of return items
        """
        list_items = []
        next_page_url = None

        while True:
            self._connector.debug_print(f"hitting url {endpoint}")

            ret_val, response = self._make_rest_call_helper(endpoint, action_result, method="get", params=params, next_page_url=next_page_url)
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            res_val = response.get("results")
            if res_val:
                list_items.extend(res_val)

            if limit and len(list_items) >= limit:
                list_items = list_items[:limit]
                break

            next_link = response.get("next")
            self._connector.debug_print(f"next_link url {next_link}")
            if next_link:
                next_page_url = next_link
                params.clear()
            else:
                break

        return phantom.APP_SUCCESS, list_items

    def _get_detections(self, action_result, detections, filters=None):
        url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_DETECTIONS_ENDPOINT}"
        params = {"id": detections}
        if filters is not None:
            params.update(filters)
        ret_val, response = self._paginator(action_result, url, params=params)
        return ret_val, response

    def _get_assignments(self, action_result, entity):
        url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_GET_ASSIGNMENTS}"
        entity_type = entity.get("type")
        entity_id = entity.get("id")
        params = {}
        if entity_type and entity_id:
            entity_type = consts.ON_POLL_ENTITY_TYPE_MAPPING[entity_type]
            params = {entity_type: entity_id}
        ret_val, response = self._paginator(action_result, url, params=params, limit=1)
        return ret_val, response
