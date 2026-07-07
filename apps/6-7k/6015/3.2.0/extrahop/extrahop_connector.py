# File: extrahop_connector.py
#
# Copyright (c) 2018-2026 ExtraHop
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
import copy
import hashlib
import ipaddress
import json
import math
import os
import re
import time
import uuid

import encryption_helper
import phantom.app as phantom
import phantom.rules as phantom_rules
import requests
from bs4 import BeautifulSoup, UnicodeDammit
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault
from phantom_common import install_info

from extrahop_consts import *


class RetVal(tuple):
    """Represent the Tuple as a return value."""

    def __new__(cls, val1, val2=None):
        """Recursive call for tuple."""
        return tuple.__new__(RetVal, (val1, val2))


class ExtrahopConnector(BaseConnector):
    """Represent a connector module that implements the actions that are provided by the app."""

    def __init__(self):
        """Initialize class variables."""
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None
        self._access_token = None
        self._base_url = None
        self._platform_url = None
        self._instance_type = None
        self._client_id = None
        self._client_secret = None
        self._is_poll_now = None
        self._is_on_poll = False
        self._api_key = None
        self._verify_server_cert = None
        self.file_path = ""
        self.last_time = None
        self.calc_type = dict()
        self.percentiles = dict()
        self._response_headers = None

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.

        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_message = EXTRAHOP_ERROR_MESSAGE_UNAVAILABLE

        self.error_print("Error occurred.", e)
        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except Exception as e:
            self.error_print(f"Error occurred while fetching exception information. Details: {e!s}")

        if not error_code:
            error_text = f"Error Message: {error_message}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_message}"

        return error_text

    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
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
                    return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_VALID_INT_MESSAGE.format(param=key)), None

                parameter = int(parameter)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_VALID_INT_MESSAGE.format(param=key)), None

            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_NON_NEG_INT_MESSAGE.format(param=key)), None
            if not allow_zero and parameter == 0:
                return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_NON_NEG_NON_ZERO_INT_MESSAGE.format(param=key)), None

        return phantom.APP_SUCCESS, parameter

    def _parse_extrahop_location_header(self, location, action_result):
        # Parse the object id from the location header
        if location:
            last_slash_index = location.rindex("/") + 1
            location_id = location[last_slash_index:]
            if location_id.isdigit():
                return RetVal(phantom.APP_SUCCESS, int(location_id))
        # return error in any other case
        return RetVal(action_result.set_status(phantom.APP_ERROR, "Unable to parse ExtraHop location header"), location)

    def _get_extrahop_api_device_id(self, param, action_result):
        eh_api_id = param.get("eh_api_id")
        active_from = param.get("minutes")
        if eh_api_id is not None:
            ret_val, eh_api_id = self._validate_integer(action_result, eh_api_id, EXTRAHOP_EH_API_ID_KEY, True)
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None
            return RetVal(phantom.APP_SUCCESS, eh_api_id)

        ip_address = param.get("ip")
        if not ip_address:
            return action_result.set_status(phantom.APP_ERROR, "Please provide at least one of 'ip' and 'eh_api_id' parameters"), None

        data = {"limit": 1, "filter": {"field": "ipaddr", "operator": "=", "operand": ip_address}}
        if active_from:
            data["active_from"] = active_from

        self.save_progress(EXTRAHOP_DEBUG_REST_ENDPOINT.format(EXTRAHOP_DEVICES_ENDPOINT))

        # make rest call to get the device
        ret_val, get_devices_response = self._make_rest_call(EXTRAHOP_DEVICES_ENDPOINT, action_result, json=data, method="post")

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, reassemble RetVal and return
            return RetVal(ret_val, None)

        # Grab device ID from response
        # TODO how to handle more than one device being returned (currently will just take the first)
        if get_devices_response and get_devices_response[0] and "id" in get_devices_response[0]:
            ret_val, eh_api_id = self._validate_integer(action_result, get_devices_response[0]["id"], EXTRAHOP_EH_API_ID_KEY)
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None
            return RetVal(phantom.APP_SUCCESS, eh_api_id)
        else:
            # Handle device not being found
            return action_result.set_status(phantom.APP_ERROR, f"ExtraHop device not found with IP {ip_address}"), None

    def _process_empty_response(self, response, action_result):
        if response.status_code in [200, 201, 204, 207]:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, f"Status code: {response.status_code}. Empty response and no information in the header"),
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

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")

        if len(message) > 500:
            message = "Error occurred while connecting to the ExtraHop server"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        # For the valid 201 response, we are getting application/json in the header and empty json response in the body
        try:
            resp_json = r.json() if r.text else {}
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {error_message}"), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_pcap_response(self, r, action_result):
        guid = uuid.uuid4()
        if hasattr(Vault, "get_vault_tmp_dir"):
            vault_tmp_dir = Vault.get_vault_tmp_dir().rstrip("/")
            local_dir = f"{vault_tmp_dir}/{guid}"
        else:
            local_dir = f"/opt/phantom/vault/tmp/{guid}"

        self.save_progress(f"Using temp directory: {local_dir}")
        self.debug_print(f"Using temp directory: {local_dir}")

        try:
            os.makedirs(local_dir)
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, "Unable to create temporary vault folder.", self._get_error_message_from_exception(e)
            )

        filename = self._response_headers["Content-Disposition"].split("filename=")[-1]
        filename = filename.replace('"', "")
        file_path = f"{local_dir}/{filename}"
        self.file_path = file_path
        try:
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=10 * 1024 * 1024):
                    f.write(chunk)
        except Exception as e:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Unable to write file to disk. Error: {self._get_error_message_from_exception(e)}"),
                None,
            )

        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, None)

        message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result, is_download):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            if not is_download:
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

        if "vnd.tcpdump.pcap" in r.headers.get("Content-Type", ""):
            return self._process_pcap_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _generate_new_access_token(self, action_result):
        """
        Generate a new access token.

        :param action_result: object of ActionResult class
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        self.debug_print("Generating new token with provided client ID and secret")

        data = {"grant_type": "client_credentials"}

        to_encode = f"{self._client_id}:{self._client_secret}"
        base64_encoded_id_secret = base64.b64encode(to_encode.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {base64_encoded_id_secret}",
        }
        url = f"{self._base_url}{EXTRAHOP_TOKEN_ENDPOINT}"

        ret_val, resp_json = self._make_main_rest_call(url, action_result, headers=headers, data=data, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self._access_token = resp_json[EXTRAHOP_OAUTH_ACCESS_TOKEN_STRING]
        self._state[EXTRAHOP_OAUTH_TOKEN_STRING] = resp_json

        return phantom.APP_SUCCESS

    def post_process_peers(self, get_activitymap_response, eh_api_id, peer_role):
        """Post process the peers."""
        # Now post process the data
        # Initialize peer sets
        unique_client_ids = set()
        unique_server_ids = set()
        # Determine the peers
        for edge in get_activitymap_response["edges"]:
            if edge["to"] == eh_api_id:
                unique_client_ids.add(edge["from"])
            elif edge["from"] == eh_api_id:
                unique_server_ids.add(edge["to"])

        # By peer role filter
        if peer_role.lower() == "client":
            unique_peer_ids = unique_client_ids
        elif peer_role.lower() == "server":
            unique_peer_ids = unique_server_ids
        else:
            unique_peer_ids = unique_client_ids.union(unique_server_ids)

        return unique_peer_ids

    def post_process_protocols(self, get_activitymap_response, eh_api_id):
        """Post process the protocols."""
        # Now post process the data
        # Initialize protocol sets
        unique_client_protocols = set()
        unique_server_protocols = set()
        # Determine the sets of active protocols
        for edge in get_activitymap_response["edges"]:
            if "annotations" in edge and "protocols" in edge["annotations"]:
                for protocol_list in edge["annotations"]["protocols"]:
                    if edge["from"] == eh_api_id:
                        unique_client_protocols.update(protocol_list["protocol"])
                    elif edge["to"] == eh_api_id:
                        unique_server_protocols.update(protocol_list["protocol"])

        return unique_client_protocols, unique_server_protocols

    def _manage_cloud_rest_calls(self, url, action_result, headers, params, data, json, method):
        """Manage token and make rest call for cloud."""
        # If no access token then create one
        if not self._access_token:
            ret_val = self._generate_new_access_token(action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

        headers["Authorization"] = f"Bearer {self._access_token}"

        ret_val, resp_json = self._make_main_rest_call(url, action_result, headers, params, data, json, method)

        # If token is expired or invalid, generate a new token
        msg = action_result.get_message()
        if phantom.is_fail(ret_val) and msg and any(invalid_msg in msg for invalid_msg in EXTRAHOP_EXPIRED_TOKEN_MESSAGES):
            self.debug_print("Token is expired or invalid")
            ret_val = self._generate_new_access_token(action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            headers.update({"Authorization": f"Bearer {self._access_token}"})
            ret_val, resp_json = self._make_main_rest_call(url, action_result, headers, params, data, json, method)
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None
        elif phantom.is_fail(ret_val):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, resp_json

    def _make_main_rest_call(self, url, action_result, headers=None, params=None, data=None, json=None, method="get"):
        resp_json = None
        if headers is None:
            headers = {}
        headers["ExtraHop-Integration"] = "Splunk-SOAR-{}-Extrahop-{}".format(self.get_product_version(), self.get_app_json().get("app_version"))

        is_stream_download = False
        if EXTRAHOP_PACKET_SEARCH_ENDPOINT in url:
            is_stream_download = True

        try:
            r = requests.request(
                method,
                url,
                data=data,
                json=json,
                headers=headers,
                verify=self._verify_server_cert,
                params=params,
                timeout=EXTRAHOP_DEFAULT_TIMEOUT,
                stream=is_stream_download,
            )

        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {error_message}"), resp_json)

        self._response_headers = r.headers
        return self._process_response(r, action_result, is_stream_download)

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, json=None, method="get"):
        url = f"{self._base_url}{endpoint}"
        resp_json = None

        # Add ExtraHop headers to each request
        if not headers:
            headers = {}

        headers["Accept"] = "application/json"
        if self._instance_type == EXTRAHOP_INSTANCE_CLOUD:
            ret_val, resp_json = self._manage_cloud_rest_calls(url, action_result, headers, params, data, json, method)
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None
        else:
            headers["Authorization"] = f"ExtraHop apikey={self._api_key}"
            ret_val, resp_json = self._make_main_rest_call(url, action_result, headers, params, data, json, method)
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

        return phantom.APP_SUCCESS, resp_json

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to ExtraHop")

        if self._instance_type == EXTRAHOP_INSTANCE_CLOUD:
            ret_val = self._generate_new_access_token(action_result)
            if phantom.is_fail(ret_val):
                if EXTRAHOP_INVALID_CLIENT_MESSAGE in action_result.get_message():
                    self._state.pop(EXTRAHOP_OAUTH_TOKEN_STRING, {})
                    self._state.pop("is_encrypted", {})
                self.save_progress("Test Connectivity to ExtraHop Failed")
                return action_result.get_status()

        # make rest call to get basic extrahop details
        ret_val, _ = self._make_rest_call(EXTRAHOP_BASIC_DETAILS_ENDPOINT, action_result)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            self.save_progress("Test Connectivity to ExtraHop Failed")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity to ExtraHop Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_device(self, param):
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(EXTRAHOP_ACTION_HANDLER_MESSAGE.format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        # Required values can be accessed directly
        ip_addresses = [x.strip() for x in param["ip"].split(",")]
        ip_addresses = list(filter(None, ip_addresses))

        # Remove duplicate IPs from the list
        ip_addresses = list(set(ip_addresses))

        data = {"filter": {"field": "ipaddr", "operator": "=", "operand": None}}
        for ip in ip_addresses:
            data["filter"]["operand"] = ip

            self.save_progress(EXTRAHOP_DEBUG_REST_ENDPOINT.format(EXTRAHOP_DEVICES_ENDPOINT))

            # make rest call to get list of devices
            ret_val, get_devices_response = self._paginator(EXTRAHOP_DEVICES_ENDPOINT, action_result, data=data)
            if phantom.is_fail(ret_val):
                # the call to the 3rd party device or service failed, action result should contain all the error details
                # so just return from here
                return action_result.get_status()

            # Now post process the data
            # Add the response into the data section
            for device_obj in get_devices_response:
                action_result.add_data(self._sanitize_object(device_obj))

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["device_count"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_peers(self, param):
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(EXTRAHOP_ACTION_HANDLER_MESSAGE.format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val, minutes = self._validate_integer(action_result, param.get("minutes", 30), EXTRAHOP_MINUTES_KEY)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        peer_role = param.get("peer_role", "any")
        if peer_role not in EXTRAHOP_PEER_ROLE_LIST:
            return action_result.set_status(
                phantom.APP_ERROR, EXTRAHOP_INVALID_SELECTION.format("peer_role", ", ".join(EXTRAHOP_PEER_ROLE_LIST))
            )
        protocol = param.get("protocol", "any")

        # get extrahop api device id by ip address
        ret_val, eh_api_id = self._get_extrahop_api_device_id(param, action_result)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        body = {
            "from": f"-{minutes}m",
            "walks": [
                {
                    "origins": [{"object_id": eh_api_id, "object_type": "device"}],
                    "steps": [{"relationships": [{"protocol": protocol, "role": peer_role}]}],
                }
            ],
        }

        self.save_progress(EXTRAHOP_DEBUG_REST_ENDPOINT.format(EXTRAHOP_ACTIVITY_MAP_ENDPOINT))

        # make rest call to get live activity map conversation data
        ret_val, get_activitymap_response = self._make_rest_call(EXTRAHOP_ACTIVITY_MAP_ENDPOINT, action_result, json=body, method="post")

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        unique_peer_ids = self.post_process_peers(get_activitymap_response, eh_api_id, peer_role)

        # Lookup each EH device id
        for peer_id in unique_peer_ids:
            device_uri = EXTRAHOP_DEVICE_WITH_ID_ENDPOINT.format(peer_id)

            self.save_progress(EXTRAHOP_DEBUG_REST_ENDPOINT.format(device_uri))

            # make rest call to get the device
            ret_val, get_device_response = self._make_rest_call(device_uri, action_result)

            if phantom.is_fail(ret_val):
                # the call to the 3rd party device or service failed, action result should contain all the error details
                # so just return from here
                return action_result.get_status()

            # Add device object to the results list
            if get_device_response:
                # Add the peer into the data section
                action_result.add_data(self._sanitize_object(get_device_response))

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["peer_count"] = len(unique_peer_ids)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_protocols(self, param):
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(EXTRAHOP_ACTION_HANDLER_MESSAGE.format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        # Required values can be accessed directly

        ret_val, minutes = self._validate_integer(action_result, param.get("minutes", 30), EXTRAHOP_MINUTES_KEY)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # get extrahop api device id by ip address
        ret_val, eh_api_id = self._get_extrahop_api_device_id(param, action_result)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        body = {
            "edge_annotations": ["protocols"],
            "from": f"-{minutes}m",
            "walks": [{"origins": [{"object_id": eh_api_id, "object_type": "device"}], "steps": [{}]}],
        }

        self.save_progress(EXTRAHOP_DEBUG_REST_ENDPOINT.format(EXTRAHOP_ACTIVITY_MAP_ENDPOINT))

        # make rest call to get live activity map protocol data
        ret_val, get_activitymap_response = self._make_rest_call(EXTRAHOP_ACTIVITY_MAP_ENDPOINT, action_result, json=body, method="post")

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        unique_client_protocols, unique_server_protocols = self.post_process_protocols(get_activitymap_response, eh_api_id)

        # Clean up sets for presentation
        # TODO remove OTHER? does it have value?
        unique_client_protocols.discard("OTHER")
        unique_client_protocols_str = ", ".join(sorted(unique_client_protocols))
        unique_server_protocols.discard("OTHER")
        unique_server_protocols_str = ", ".join(sorted(unique_server_protocols))

        # Add the protocols into the data section
        action_result.add_data(
            {
                "client_protocols": unique_client_protocols_str if unique_client_protocols_str else None,
                "server_protocols": unique_server_protocols_str if unique_server_protocols_str else None,
            }
        )

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["client_protocol_count"] = len(unique_client_protocols)
        summary["server_protocol_count"] = len(unique_server_protocols)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _paginator(self, endpoint, action_result, data=None, offset=0, limit=1000):
        action_id = self.get_action_identifier()
        records_list = []

        if not data:
            data = {}

        if limit:
            data["limit"] = min(EXTRAHOP_DEFAULT_LIMIT, limit)
        else:
            data["limit"] = EXTRAHOP_DEFAULT_LIMIT
        data["offset"] = offset

        while True:
            self.debug_print(f"Fetching {data['limit']} records from offset {data['offset']}")
            ret_val, response = self._make_rest_call(endpoint, action_result, json=data, method="post")
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            records_list.extend(response)
            if len(response) < EXTRAHOP_DEFAULT_LIMIT:
                self.debug_print("Got all the available records, break the loop")
                break

            if ((action_id == "on_poll" and self._is_poll_now) or action_id != "on_poll") and len(records_list) >= limit:
                self.debug_print("Got the required count, returning the result")
                return phantom.APP_SUCCESS, records_list[:limit]

            data["offset"] += EXTRAHOP_DEFAULT_LIMIT

        return phantom.APP_SUCCESS, records_list

    def _sanitize_object(self, object):
        """
        Recursively remove empty lists, empty dicts, or None elements from a dictionary.

        :param d: Input dictionary.
        :type d: dict
        :return: Dictionary with all empty lists, and empty dictionaries removed.
        :rtype: dict
        """

        def empty(x):
            return x is None or x == {} or x == [] or x == ""

        if isinstance(object, list):
            return [v for v in (self._sanitize_object(v) for v in object) if not empty(v)]
        if isinstance(object, dict):
            return {k: v for k, v in ((k, self._sanitize_object(v)) for k, v in object.items()) if not empty(v)}
        return object

    def _handle_detect_devices(self, param):
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(EXTRAHOP_ACTION_HANDLER_MESSAGE.format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        # Required values can be accessed directly
        json_object = param.get("json_object")
        is_json_object = False
        if json_object:
            is_json_object = True
            try:
                data = json.loads(json_object)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_INVALID_FILTER_MESSAGE.format("json_object"))
        else:
            field_type = param.get("field_type", "custom_filter")
            custom_filter = param.get("filter")
            if field_type not in EXTRAHOP_FIELD_TYPE_LIST:
                return action_result.set_status(
                    phantom.APP_ERROR, EXTRAHOP_INVALID_SELECTION.format("field_type", ", ".join(EXTRAHOP_FIELD_TYPE_LIST))
                )

            ret_val, minutes = self._validate_integer(action_result, param.get("minutes", 30), EXTRAHOP_MINUTES_KEY)
            if phantom.is_fail(ret_val):
                return action_result.get_status()

            ret_val, offset = self._validate_integer(action_result, param.get("offset", 0), EXTRAHOP_OFFSET_KEY, allow_zero=True)
            if phantom.is_fail(ret_val):
                return action_result.get_status()

            ret_val, limit = self._validate_integer(action_result, param.get("limit", 1000), EXTRAHOP_LIMIT_KEY)
            if phantom.is_fail(ret_val):
                return action_result.get_status()

            if field_type == "custom_filter":
                data = {"active_from": f"-{minutes}m"}
                if custom_filter:
                    try:
                        data["filter"] = json.loads(custom_filter)
                    except Exception:
                        return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_INVALID_FILTER_MESSAGE.format("filter"))
            else:
                data = {"active_from": f"-{minutes}m", "filter": {"field": field_type, "operator": "exists"}}

        self.save_progress(EXTRAHOP_DEBUG_REST_ENDPOINT.format(EXTRAHOP_DEVICES_ENDPOINT))
        # make rest call to get devices
        if not is_json_object:
            ret_val, get_devices_response = self._paginator(EXTRAHOP_DEVICES_ENDPOINT, action_result, data=data, offset=offset, limit=limit)
        else:
            ret_val, get_devices_response = self._make_rest_call(EXTRAHOP_DEVICES_ENDPOINT, action_result, json=data, method="post")
        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        for device_obj in get_devices_response:
            action_result.add_data(self._sanitize_object(device_obj))

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["active_devices_count"] = len(get_devices_response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_device(self, param):
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(EXTRAHOP_ACTION_HANDLER_MESSAGE.format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        # Required values can be accessed directly
        json_object = param.get("json_object")
        is_json_object = False
        if json_object:
            is_json_object = True
            try:
                custom_device_body = json.loads(json_object)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_INVALID_FILTER_MESSAGE.format("json_object"))
        else:
            ip_address = param.get("ip")
            # Optional values should use the .get() function
            # Custom device definition
            name = param.get("name", f"Phantom-{ip_address}")
            author = param.get("author", "Phantom")
            description = param.get("description", "Device created by Phantom integration for endpoint inspection")
            cidr = param.get("cidr")

            # Create the new [device]
            custom_device_body = {
                "name": name,
                "author": author,
                "description": description,
                "disabled": False,
                "criteria": [
                    {
                        "ipaddr": ip_address + cidr if ip_address and cidr else ip_address,
                    }
                ],
            }

        self.save_progress(EXTRAHOP_DEBUG_REST_ENDPOINT.format(EXTRAHOP_CUSTOM_DEVICES_ENDPOINT))

        # make rest call to create the custom device
        ret_val, _ = self._make_rest_call(EXTRAHOP_CUSTOM_DEVICES_ENDPOINT, action_result, json=custom_device_body, method="post")

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        # Add the response into the data section
        name = custom_device_body.get("name") if is_json_object else name
        data = {"name": name}
        if not is_json_object and cidr:
            data["cidr"] = cidr
        action_result.add_data(data)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["name"] = name

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_tag_device(self, param):
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(EXTRAHOP_ACTION_HANDLER_MESSAGE.format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        tag = param["tag"]

        ret_val, eh_api_id = self._get_extrahop_api_device_id(param, action_result)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        self.save_progress(EXTRAHOP_DEBUG_REST_ENDPOINT.format(EXTRAHOP_TAGS_ENDPOINT))

        # make rest call to get all tags
        ret_val, get_tags_response = self._make_rest_call(EXTRAHOP_TAGS_ENDPOINT, action_result)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        # Search for tag in tags
        for tag_obj in get_tags_response:
            # if tag names match then grab the tag id
            if tag_obj["name"] == tag:
                tag_id = tag_obj["id"]
                break
        else:
            # If tag doesn't exist then create it
            tag_body = {"name": tag}

            self.save_progress(EXTRAHOP_DEBUG_REST_ENDPOINT.format(EXTRAHOP_TAGS_ENDPOINT))

            # make rest call to create the tag
            ret_val, _ = self._make_rest_call(EXTRAHOP_TAGS_ENDPOINT, action_result, json=tag_body, method="post")

            if phantom.is_fail(ret_val):
                # the call to the 3rd party device or service failed, action result should contain all the error details
                # so just return from here
                return action_result.get_status()

            returned_location = self._response_headers.get("location")
            ret_val, tag_id = self._parse_extrahop_location_header(returned_location, action_result)

            if phantom.is_fail(ret_val):
                # the call to the 3rd party device or service failed, action result should contain all the error details
                # so just return from here
                return action_result.get_status()

        assign_tag_body = {"assign": [eh_api_id]}

        tag_assign_uri = EXTRAHOP_TAG_TO_DEVICE_ENDPOINT.format(tag_id)

        self.save_progress(EXTRAHOP_DEBUG_REST_ENDPOINT.format(tag_assign_uri))

        # make rest call to assign the tag to the device
        ret_val, _ = self._make_rest_call(tag_assign_uri, action_result, json=assign_tag_body, method="post")

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data({"tag_id": tag_id})

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["tag"] = tag
        summary["extrahop_device_id"] = eh_api_id

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_metrics(self, param):
        self.save_progress(EXTRAHOP_ACTION_HANDLER_MESSAGE.format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        json_object = param.get("json_object")
        if json_object:
            self.debug_print("Validating JSON object")
            ret_val, json_object = self._validate_json_object(action_result, param)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            start_time = json_object.get("from")
            end_time = json_object.get("until")
            param["start_time"] = start_time
            param["end_time"] = end_time
            param["json_object"] = json_object
        else:
            ret_val, minutes = self._validate_integer(action_result, param.get("minutes", 30), "minutes")
            if phantom.is_fail(ret_val):
                return action_result.get_status()

            param["start_time"] = f"-{minutes}m"
            param["end_time"] = 0

        ret_val, metrics = self._process_metrics(param, action_result)
        if phantom.is_fail(ret_val):
            self.debug_print(EXTRAHOP_DEFAULT_ERROR.format(action_result.get_message()))
            return action_result.get_status()

        message = "Successfully received metrics data"
        if not len(metrics):
            message = "No metrics found"
        self.debug_print(message)
        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _add_container_data(self, data, data_type, start_time=None):
        if data_type == "detections":
            container = {"name": data.get("title", data.get("id")), "source_data_identifier": "detection id {}".format(data.get("id"))}
        elif data_type == "metrics":
            container = {
                "name": "{}_{}".format(data.get("oid"), start_time),
                "source_data_identifier": "{}_{}".format(data.get("oid"), start_time),
            }
        elif data_type == "PCAP":
            container = {"name": start_time, "source_data_identifier": start_time}

        return container

    def _choose_severity(self, data):
        if not data.get("risk_score"):
            return "low"
        else:
            risk_score = data.get("risk_score")
            if risk_score > 80:
                return "high"
            elif risk_score > 30:
                return "medium"
            else:
                return "low"

    def _add_markdown(self, data, container_id, artifact_id):
        """Add note to the container."""
        description = data.get("description")
        title = data.get("title")
        if self._platform_url:
            new_link = f"{self._platform_url}/extrahop/#"

            markdown_data = re.findall(EXTRAHOP_MARKDOWN_REGEX, description)

            for markdown in markdown_data:
                # Replacing the '#' to the extrahop platform url
                new_markdown = markdown.replace("#", new_link)
                description = description.replace(markdown, new_markdown)

        ret_val, message, _ = phantom_rules.add_note(
            container=container_id, artifact_id=artifact_id, title=title, content=description, note_type="general", note_format="markdown"
        )

        if phantom.is_fail(ret_val):
            self.debug_print(f"Error occurred while adding the note: {message}")

    def _create_hash(self, data):
        input_dict_str = None

        if not data:
            return None

        try:
            input_dict_str = json.dumps(data, sort_keys=True)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.debug_print(f"Error occurred in _create_hash. {error_message}")
            return None

        return hashlib.sha256(UnicodeDammit(input_dict_str).unicode_markup.encode("utf-8")).hexdigest()

    def _make_rest_call_to_soar(self, endpoint, method="get", soar_data=""):
        """Get the artifact data."""
        soar_baseurl = install_info.get_rest_base_url().rstrip("/")
        url = f"{soar_baseurl}{endpoint}"
        request_func = getattr(requests, method)
        try:
            resp = request_func(url, verify=EXTRAHOP_VERIFY_SERVER_FAIL)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.debug_print(f"Error connecting to server. Details: {error_message}")
        else:
            try:
                soar_data = json.loads(resp.text)
            except Exception as e:
                error_message = self._get_error_message_from_exception(e)
                self.debug_print(f"Error while parsing the response. {error_message}")

        return soar_data

    def _modify_description(self, updated_description):
        markdown_data = re.findall(EXTRAHOP_MARKDOWN_REGEX, updated_description)

        for markdown in markdown_data:
            # Discarded the fields after '?' in markdown as the timestamps
            # for from and until is changing frequently. which cause the
            # artifact duplication (only timestamp is changing)
            new_markdown = markdown.split("?")
            updated_description = updated_description.replace(markdown, new_markdown[0])
        return updated_description

    def _ingest_detection(self, action_result, data_list, param, data_type):
        """
        Ingest data into Phantom.

        :param action_result: object of ActionResult class
        :param data: data to ingest
        :param param: dictionary of input parameters
        :param data_type: type of data to ingest
        :return: phantom.APP_SUCCESS
        """
        self.save_progress(EXTRAHOP_INGESTION_START_MESSAGE)
        self.debug_print(EXTRAHOP_INGESTION_START_MESSAGE)

        for data in data_list:
            artifacts = []
            data = self._update_object_participants(action_result, data)
            data_id = data.get("id")
            artifact_name = "{} Artifact".format(data.get("title"))

            container = self._add_container_data(data, data_type)

            severity_level = self._choose_severity(data)
            container["severity"] = severity_level
            status, message, container_id = self.save_container(container)
            if phantom.is_fail(status):
                self.debug_print(EXTRHOP_CONTAINER_ERROR_MESSAGE.format(container_id, message))
                continue

            artifact_info = None
            if self._platform_url:
                extrahop_link = f"{self._platform_url}/extrahop/#/detections/detail/{data_id}"
                data["extrahop_link"] = extrahop_link

            if EXTRAHOP_DUPLICATE_CONTAINER_MESSAGE in message:
                self.debug_print(EXTRAHOP_DUPLICATE_CONTAINER_MESSAGE)
                artifact_info = self._make_rest_call_to_soar(EXTRAHOP_SOAR_ARTIFACT_ENDPOINT.format(container_id), soar_data=artifact_info)

            old_sdi = ""
            old_description = ""
            mod_time = None
            if artifact_info and artifact_info.get("data"):
                # taking the source_data_identifier of latest artifact
                old_sdi = artifact_info.get("data")[0].get("source_data_identifier")
                old_description = artifact_info.get("data")[0].get("cef", "").get("description", "")
            if data.get("update_time"):
                update_time = data.pop("update_time")
            if data.get("mod_time"):
                mod_time = data.pop("mod_time")
            description = data.pop("description")
            if description is None:
                description = ""
            updated_description = description
            updated_description = self._modify_description(updated_description)
            old_updated_description = self._modify_description(old_description)

            data["description"] = updated_description
            sdi = self._create_hash(data)
            if old_sdi == sdi:
                self.debug_print(EXTRAHOP_ARTIFACT_SAME_SDI.format(sdi, container_id))
                continue

            data.update({"description": description, "update_time": update_time})
            if mod_time:
                data["mod_time"] = mod_time

            # construct artifacts
            artifacts = [
                {
                    "source_data_identifier": sdi,
                    "label": param.get("label"),
                    "name": artifact_name,
                    "cef": data,
                    "container_id": container_id,
                    "severity": severity_level,
                }
            ]

            if not self._platform_url and self._instance_type == EXTRAHOP_INSTANCE_CLOUD:
                self.debug_print("Please specify the platform URL in the asset configuration to add 'extrahop_link' in the detection artifact")

            status, message, artifact_id = self.save_artifacts(artifacts)
            if phantom.is_fail(status):
                self.debug_print(EXTRHOP_ARTIFACT_ERROR_MESSAGE.format(message))
                continue

            if not data.get("description"):
                continue

            if updated_description != old_updated_description:
                self._add_markdown(data, container_id, artifact_id)

        self.debug_print(EXTRAHOP_INGESTION_MESSAGE.format(data_type, data_id, container_id))

        return phantom.APP_SUCCESS

    def _validate_process_detections_parameters(self, param, action_result):
        """
        Validate parameters of process_detections method.

        :param param: dictionary of params
        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS, processed_params
        """
        processed_params = dict()

        detection_category = param.get("detection_category", EXTRAHOP_DEFAULT_DETECTION_CATEGORY)
        detection_category = [x.strip() for x in detection_category.split(",")]
        detection_category = list(set(filter(None, detection_category)))

        processed_params["detection_category"] = detection_category

        detection_status = param.get("detection_status")
        final_status = set()
        if detection_status:
            detection_status = [x.strip() for x in detection_status.split(",")]
            detection_status = list(filter(None, detection_status))
            for status in detection_status:
                if status.lower() not in EXTRAHOP_STATUS_LIST:
                    return action_result.set_status(
                        phantom.APP_ERROR, EXTRAHOP_INVALID_STATUS.format("detection_status", EXTRAHOP_STATUS_LIST)
                    ), None
                else:
                    final_status.add(status.lower())

        processed_params["detection_status"] = list(final_status)

        return phantom.APP_SUCCESS, processed_params

    def _update_object_participants(self, action_result, data):
        """Modify the participants information."""
        for index, participant in enumerate(data["participants"]):
            all_keys = participant.keys()
            if EXTRAHOP_DETECTION_OBJECT_VALUE not in all_keys and EXTRAHOP_DETECTION_OBJECT_ID in all_keys:
                ret_val, response = self._make_rest_call(EXTRAHOP_DEVICE_WITH_ID_ENDPOINT.format(participant.get("object_id")), action_result)
                if phantom.is_fail(ret_val):
                    self.debug_print("Not able to find the object value for the device with {} ID".format(participant.get("object_id")))
                    continue
                if response.get("ipaddr4"):
                    data["participants"][index]["object_value"] = response.get("ipaddr4")
                elif response.get("ipaddr6"):
                    data["participants"][index]["object_value"] = response.get("ipaddr6")
                else:
                    data["participants"][index]["object_value"] = None
        return data

    def _process_detections(self, param, action_result):
        """
        Process the detections.

        :param action_result: object of ActionResult class
        :param param: dictionary of params
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS, detections
        """
        detections = list()
        data = dict()
        self.save_progress(EXTRAHOP_PARAM_VALIDATION_MESSAGE)
        self.debug_print(EXTRAHOP_PARAM_VALIDATION_MESSAGE)

        is_json_object = False
        json_object = param.get("json_object")
        if json_object:
            is_json_object = True
            try:
                data = json.loads(json_object)
                if not data.get("filter"):
                    data["filter"] = {"categories": [EXTRAHOP_DEFAULT_DETECTION_CATEGORY]}
                if data.get("filter") and not data["filter"].get("categories"):
                    data["filter"]["categories"] = [EXTRAHOP_DEFAULT_DETECTION_CATEGORY]
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_INVALID_FILTER_MESSAGE.format("json_object")), detections
        if not is_json_object:
            status, processed_params = self._validate_process_detections_parameters(param, action_result)
            if phantom.is_fail(status):
                return action_result.get_status(), detections

            detection_status = processed_params.get("detection_status")
            detection_category = processed_params.get("detection_category")
        limit = param.get("container_count")
        mod_time = param.get("mod_time")

        self.save_progress(EXTRAHOP_RETRIEVING_DATA_MESSAGE.format("detections"))
        self.debug_print(EXTRAHOP_RETRIEVING_DATA_MESSAGE.format("detections"))

        data.update({"mod_time": mod_time})
        if not is_json_object:
            data["filter"] = dict()
            if detection_status:
                data["filter"]["status"] = detection_status

            if detection_category:
                data["filter"]["categories"] = detection_category
        self.debug_print(f"Json_data: {data}")
        status, detections = self._paginator(EXTRAHOP_DETECTIONS_ENDPOINT, action_result, data=data, limit=limit)
        if phantom.is_fail(status):
            return action_result.get_status(), detections

        if not detections:
            return phantom.APP_SUCCESS, detections

        self._ingest_detection(action_result, detections, param, data_type="detections")

        return phantom.APP_SUCCESS, detections

    def _poll_for_detections(self, action_result, params, config):
        """
        Perform the on poll ingest functionality for detections.

        :param action_result: object of ActionResult class
        :param params: dictionary of input parameters
        :param config: dictionary of asset configuration parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        now = int(time.time()) * 1000
        if self._is_poll_now:
            params["mod_time"] = now - (EXTRAHOP_DETECTION_DEFAULT_INTERVAL * 1000)
        else:
            params["mod_time"] = self._state.get(EXTRAHOP_DETECTION_LAST_INGESTED_TIME, now - (EXTRAHOP_DETECTION_DEFAULT_INTERVAL * 1000))

        if isinstance(params["mod_time"], int):
            for key in EXTRAHOP_INGESTION_DETECTION_KEYS:
                params[key] = config.get(key)
            for key, value in list(params.items()):
                if value is None:
                    params.pop(key)

            status, _ = self._process_detections(params, action_result)
            if phantom.is_fail(status):
                return action_result.get_status()
        else:
            self._state[EXTRAHOP_DETECTION_LAST_INGESTED_TIME] = now
            return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_CORRUPTED_KEY_MESSAGE.format(EXTRAHOP_DETECTION_LAST_INGESTED_TIME))

        if not self._is_poll_now:
            self._state[EXTRAHOP_DETECTION_LAST_INGESTED_TIME] = now

        return phantom.APP_SUCCESS

    def metric_processor_factory(self, mtype):
        """Process the function for given metric type."""

        # BASIC METRICS
        def process_dcount(metric, value, tset_key=None):
            """Process the detail count metrics from metric payload.

            extrahop.device.ssl_client.cipher
            {
                "key": {
                "key_type": "string",
                "str": "TLS_RSA_WITH_AES_256_GCM_SHA384"
                },
                "vtype": "count",
                "value": 1
            }
            """
            detail = self.extract_detail_key(value["key"])
            outputdata = [(metric, value["value"]), ("detail", detail)]
            if tset_key:
                outputdata.append(("key", tset_key))
            return outputdata

        def process_sset(metric, value):
            """Process the sampleset metrics from metric payload.

            Expect only to be called through process_dsset()
            {
                "count": 1,
                "sum": 43.062,
                "sum2": 1854.335844
            }
            """
            # calculate mean
            ndig = 3  # number of digits to round to
            count = value["count"]
            if count > 0:
                mean = round(float(value["sum"]) / float(count), ndig)
            else:
                mean = value["sum"]
            # calculate standard deviation
            if count > 1:
                std_dev = round(math.sqrt(float(value["sum2"]) / (float(count) - 1)), ndig)
            else:
                std_dev = 0
            return [
                (".".join([metric, "mean"]), mean),
                (".".join([metric, "sd"]), std_dev),
                (".".join([metric, "count"]), count),
            ]

        def process_dset(metric, value):
            """Process the dataset metrics from metric payload.

            Expect five percentiles as the result
            extrahop.device.ssl_client.rtt
            [
            7.0265,
            9.2685,
            18.947,
            30.17,
            50.9552
            ]
            """
            if self.calc_type[metric] == "mean":
                return [(f"{metric}.mean", value)]
            else:
                quantiles = list()
                for per in self.percentiles[metric]:
                    quantiles.append(f"p{per}")
                return [(".".join([metric, q]), v) for (q, v) in zip(quantiles, value)]

        # DETAIL METRIC FUNCTIONS
        #   For these metrics, we can rely on the above processors
        #   with some additional finesse for handling the detail keys
        def process_dsset(metric, value, tset_key=None):
            """Process the detail sampleset metrics from metric payload.

            extrahop.device.http_client_detail.tprocess
            {
                "key": {
                "key_type": "ipaddr",
                "addr": "1.2.3.4",
                "device_oid": 15,
                "host": "somehost.extrahop.com"
                },
                "vtype": "sset",
                "value": {
                "count": 1,
                "sum": 43.062,
                "sum2": 1854.335844
                }
            }
            """
            detail = self.extract_detail_key(value["key"])
            outputdata = process_sset(metric, value["value"])
            outputdata.append(("detail", detail))
            if tset_key:
                outputdata.append(("key", tset_key))
            return outputdata

        def process_ddset(metric, value, tset_key=None):
            """Process the detail dataset metrics from metric payload.

            Expect five percentiles as the result
            extrahop.device.ssl_client_detail.handshake_time_version
            {
                "key": {
                "key_type": "string",
                "str": "TLSv1.2"
                },
                "vtype": "dset",
                "value": [
                1.03225,
                1.80775,
                2.7965,
                3.6535,
                9.22515
                ]
            }
            """
            detail = self.extract_detail_key(value["key"])
            outputdata = process_dset(metric, value["value"])
            outputdata.append(("detail", detail))
            if tset_key:
                outputdata.append(("key", tset_key))
            return outputdata

        def process_dmax(metric, value, tset_key=None):
            """Process the detail max metrics from metric payload.

            extrahop.device.tcp_detail.established_max
            {
                "key": {
                "key_type": "ipaddr",
                "addr": "1.2.3.4",
                "device_oid": 15,
                "host": "somehost.extrahop.com"
                },
                "vtype": "max",
                "value": 1
            }
            """
            return process_dcount(metric, value, tset_key)

        def process_time(metric, value, tset_key=None):
            """Process the time metrics from metric payload.

            extrahop.device.ssl_server.
            {
                "key": {
                "key_type": "string",
                "str": "somehost.extrahop.com:RSA_2048"
                },
                "vtype": "time",
                "value": 1564778310000
            }
            """
            return process_dcount(metric, value, tset_key)

        def process_dsnap(metric, value, tset_key=None):
            """Process the detail snap metrics from metric payload.

            extrahop.device.tcp_detail.established
            {
                "key": {
                "key_type": "ipaddr",
                "addr": "1.2.3.4",
                "device_oid": 15
                },
                "vtype": "snap",
                "value": 1
            }
            """
            return process_dcount(metric, value, tset_key)

        # metric_processor_factory body
        return locals().get(f"process_{mtype}")

    def identify_metric_type(self, action_result, data, metric_name):
        """
        Retrives the metric type

        :param action_result: object of ActionResult class
        :param data: metrics input data
        :param metric_name: list of metric names
        :return: phantom.APP_SUCCESS, metric_name_ordered(mapped metric name and type)
        """
        if self._is_on_poll:
            look_back = data["from"] - 86400000
        else:
            look_back = data["from"]
        json_data = {
            "cycle": "auto",
            "from": look_back,
            "metric_category": data["metric_category"],
            "metric_specs": data["metric_specs"],
            "object_ids": data["object_ids"],
            "object_type": data["object_type"],
        }
        metric_name_ordered = dict()
        for name in metric_name:
            json_data["metric_specs"] = [{"name": name}]
            ret_val, metrics_response = self._make_rest_call(EXTRAHOP_METRICS_TOTAL_ENDPOINT, action_result, json=json_data, method="post")
            if phantom.is_fail(ret_val):
                return action_result.get_status(), metric_name_ordered

            xid = metrics_response.get("xid")
            num_results = metrics_response.get("num_results", 0)

            for _ in range(num_results):
                ret_val, metrics_response = self._make_rest_call(EXTRAHOP_METRICS_XID_ENDPOINT.format(xid), action_result)
                if phantom.is_fail(ret_val):
                    self.debug_print(EXTRAHOP_DEFAULT_ERROR.format(action_result.get_message()))
                    continue
                if metrics_response["stats"][0]["values"][0]:
                    break
            if phantom.is_fail(ret_val):
                return action_result.get_status(), metric_name_ordered

            value = metrics_response["stats"][0]["values"][0]
            vtype = self.infer_metric_type(value, name)
            metric_name_ordered.update({name: vtype})
        return phantom.APP_SUCCESS, metric_name_ordered

    def extract_detail_key(self, key):
        """Process the detail key data from metric payload."""
        if key["key_type"] == "string":
            return key["str"]
        if key["key_type"] == "ipaddr":
            return key["addr"]

    def infer_metric_type(self, data, metric_name):
        """Guess what metric type we've been given.

        :param data: a metric value from EH REST API
        :type data: int or list
        :param str metric_name: name of the metric (needed for sset/dsset discrimination)
        :return: string representing metric type
        """
        if isinstance(data, int):
            return "count"
        if isinstance(data, list) and len(data) > 0:
            # non-tsets will wrap the data object in a list
            # for tset processing, we've already unwrapped
            data = data[0]
        if "vtype" in data:
            vtype = data["vtype"]
            if vtype == "sset":
                if self.extract_detail_key(data["key"]) == metric_name:
                    return "sset"
                return "dsset"
            else:
                return EXTRAHOP_VTYPE[vtype]
        elif "freq" in data:
            return "dset"

        return ""

    def cycle_to_msecs(self, cycle):
        """Cycle name to milliseconds."""
        default_cycle = "30sec"
        cyclesizes = {"1sec": 1000, "30sec": 30000, "5min": 300000, "1hr": 3600000, "24hr": 86400000}
        default_cyclesize = cyclesizes[default_cycle]
        return cyclesizes.get(cycle, default_cyclesize)

    def get_cycle_boundary(self, timestamp, cycle):
        """Epoch time Which is compatible with cycle length"""
        return timestamp - (timestamp % self.cycle_to_msecs(cycle))

    def initial_response(self, item_oid, timestamp, data):
        """Structure for response"""
        return {
            "oid": item_oid,
            "cycle": data["cycle"],
            "metric_category": data["metric_category"],
            "object_type": data["object_type"],
            "time": timestamp // 1000,
        }

    def update_final_response(self, final_response, vlist):
        """Postprocessed data to response"""
        response = copy.deepcopy(final_response)
        for key, value in vlist:
            response[key] = value

        return response

    def update_data_by_type(self, data, metric_name_type):
        """Update the data if metric type is dset or ddset"""
        for index in range(len(data["metric_specs"])):
            name = data["metric_specs"][index]["name"]
            calc_type = data["metric_specs"][index].get("calc_type")
            if name in metric_name_type.keys() and metric_name_type[name] not in ("dset", "ddset") and calc_type:
                data["metric_specs"][index].pop("calc_type")
                self.calc_type.pop(name)
                if data["metric_specs"][index].get("percentiles"):
                    data["metric_specs"][index].pop("percentiles")
                    self.percentiles.pop(name)

            if name in metric_name_type.keys() and metric_name_type[name] in ("dset", "ddset") and calc_type is None:
                data["metric_specs"][index]["calc_type"] = "percentiles"
                data["metric_specs"][index]["percentiles"] = [5, 25, 50, 75, 95]
                self.calc_type[name] = "percentiles"
                self.percentiles[name] = [5, 25, 50, 75, 95]

        return data

    def _validate_json_object(self, action_result, params):
        json_object = params.get("json_object")
        try:
            json_object = json.loads(json_object)
            if not isinstance(json_object, dict):
                return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_INVALID_FILTER_MESSAGE.format("json_object")), None
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_INVALID_FILTER_MESSAGE.format("json_object")), None

        for key in EXTRAHOP_INGESTION_METRICS_API_KEYS:
            if json_object.get(key) is None:
                return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_METRIC_REQUIRED_API_PARAM), None
        return phantom.APP_SUCCESS, json_object

    def postprocess_tset(self, final_response, metric, value):
        """Postprocess for tset type of data"""
        list_final_response = []
        for val in value:
            key_value = self.extract_detail_key(val["key"])
            tset_key = key_value if key_value != metric else None

            for v in val["value"]:
                sub_metric_type = self.infer_metric_type(v, metric)
                processor = self.metric_processor_factory(sub_metric_type)
                list_final_response.append(self.update_final_response(final_response, processor(metric, v, tset_key)))

        return list_final_response

    def postprocess_response(self, final_response, item, metric_name, metric_name_type):
        """
        Post process the response by given type

        :param final_response: Initial structure for post-processed response
        :param item: stat from the response
        :param metric_name: list of metric names
        :param metric_name_type: type of the metric according to the name {metric_name: metric_type}
        :return final_response, list_final_response
        """
        list_final_response = []
        initial_response = copy.deepcopy(final_response)
        for metric, value in zip(metric_name, item["values"]):
            metric_type = metric_name_type[metric]

            if metric_type == "tset":
                list_final_response.extend(self.postprocess_tset(initial_response, metric, value))
            elif metric_type in ("count", "max"):
                final_response = self.update_final_response(final_response, [(metric, value)])
            elif metric_type in ("dset", "sset"):
                processor = self.metric_processor_factory(metric_type)
                final_response = self.update_final_response(final_response, processor(metric, value))
            elif metric_type in (
                "dcount",
                "ddset",
                "dsset",
                "dmax",
                "time",
                "dsnap",
            ):
                # we expect an array of detail metrics, so for each object in the array:
                for val in value:
                    if len(val) > 0:
                        processor = self.metric_processor_factory(metric_type)
                        list_final_response.append(self.update_final_response(initial_response, processor(metric, val)))

        return copy.deepcopy(final_response), list_final_response

    def _ingest_metrics(self, action_result, data_list, param, data_type, start_time=None):
        """
        Ingest data into Phantom.

        :param action_result: object of ActionResult class
        :param data_list: list of data to ingest
        :param param: dictionary of input parameters
        :param data_type: type of data to ingest
        :return: phantom.APP_SUCCESS
        """
        artifacts = []
        data_id = data_list[0].get("oid")

        container = self._add_container_data(data_list[0], data_type, start_time)

        status, message, container_id = self.save_container(container)
        if phantom.is_fail(status):
            self.debug_print(EXTRHOP_CONTAINER_ERROR_MESSAGE.format(container_id, message))

        if EXTRAHOP_DUPLICATE_CONTAINER_MESSAGE in message:
            self.debug_print(EXTRAHOP_DUPLICATE_CONTAINER_MESSAGE)

        # construct artifacts
        for data in data_list:
            cef = data
            artifact_name = "{}_{} Artifact".format(data.get("oid"), data.get("time"))

            artifacts.append({"label": param.get("label"), "name": artifact_name, "cef": cef, "container_id": container_id})

        status, message, _ = self.save_artifacts(artifacts)
        if phantom.is_fail(status):
            self.debug_print(EXTRHOP_ARTIFACT_ERROR_MESSAGE.format(message))

        self.debug_print(EXTRAHOP_INGESTION_MESSAGE.format(data_type, data_id, container_id))

        return phantom.APP_SUCCESS

    def csv_to_list(self, data):
        """Comma separated values to list"""
        data = [x.strip() for x in data.split(",")]
        data = set(filter(None, data))
        data = list(data)
        return data

    def get_metric_name(self, json_object):
        """Get Metrics name from json payload"""
        metric_name = []
        for spec in json_object.get("metric_specs"):
            metric_name.append(spec.get("name"))
        return metric_name

    def _validate_process_metrics_parameters(self, param, action_result):
        """
        Validate parameters of process_metrics method.

        :param param: dictionary of params
        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS, processed_params
        """
        processed_params = dict()

        processed_params["metric_cycle_length"] = param.get("metric_cycle_length", "30sec")
        if processed_params["metric_cycle_length"] not in EXTRHOP_CYCLE_SELECTION:
            return action_result.set_status(
                phantom.APP_ERROR, EXTRAHOP_INVALID_SELECTION.format(processed_params["metric_cycle_length"], EXTRHOP_CYCLE_SELECTION)
            ), processed_params

        object_type = param.get("object_type", "Application")
        if object_type not in EXTRHOP_METRIC_OBJECT_TYPE:
            return action_result.set_status(
                phantom.APP_ERROR, EXTRAHOP_INVALID_SELECTION.format(object_type, EXTRHOP_METRIC_OBJECT_TYPE)
            ), processed_params
        processed_params["object_type"] = EXTRAHOP_OBJECT_TYPE.get(object_type)

        object_id = param.get("object_id")
        if object_id:
            object_id = self.csv_to_list(object_id)
            for index, oid in enumerate(object_id):
                ret_val, object_id[index] = self._validate_integer(action_result, oid, "object_id", True)
                if phantom.is_fail(ret_val):
                    return action_result.get_status(), processed_params
        else:
            return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_METRIC_REQUIRED_PARAM), processed_params
        processed_params["object_id"] = object_id

        if (
            self._is_on_poll
            and self._is_poll_now
            and "Device Group" not in object_type
            and param.get("container_count") < len(processed_params["object_id"])
        ):
            return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_CONTAINER_LIMIT_ERROR), processed_params

        metric_category = param.get("metric_category")
        if metric_category:
            processed_params["metric_category"] = metric_category
        else:
            return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_METRIC_REQUIRED_PARAM), processed_params

        metric_name = param.get("metric_name")

        metric_specs = []
        if metric_name:
            metric_name = self.csv_to_list(metric_name)
            processed_params["metric_name"] = metric_name
            for name in metric_name:
                metric_specs.append({"name": name})
        else:
            return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_METRIC_REQUIRED_PARAM), processed_params
        processed_params["metric_specs"] = metric_specs

        return phantom.APP_SUCCESS, processed_params

    def _process_metrics(self, param, action_result):
        """
        Process the Metrics.

        :param action_result: object of ActionResult class
        :param param: dictionary of params
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS, metrics
        """
        metrics = list()
        container_limit = set()
        self.save_progress(EXTRAHOP_PARAM_VALIDATION_MESSAGE)
        self.debug_print(EXTRAHOP_PARAM_VALIDATION_MESSAGE)
        is_json_object = False

        json_object = param.get("json_object")
        if not json_object:
            status, processed_params = self._validate_process_metrics_parameters(param, action_result)
            if phantom.is_fail(status):
                return action_result.get_status(), metrics

            metric_cycle_length = processed_params.get("metric_cycle_length")
            object_type = processed_params.get("object_type")
            object_id = processed_params.get("object_id")
            metric_category = processed_params.get("metric_category")
            metric_name = processed_params.get("metric_name")
            metric_specs = processed_params.get("metric_specs")
        else:
            is_json_object = True
            metric_name = self.get_metric_name(json_object)
            object_id = json_object.get("object_ids")
            object_type = json_object.get("object_type")
            if self._is_on_poll and self._is_poll_now and "device_group" not in object_type and param.get("container_count") < len(object_id):
                return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_CONTAINER_LIMIT_ERROR), metrics
            for index, name in enumerate(metric_name):
                self.calc_type[name] = json_object["metric_specs"][index].get("calc_type")
                self.percentiles[name] = json_object["metric_specs"][index].get("percentiles")

        start_time = param.get("start_time")
        end_time = param.get("end_time")

        self.save_progress(EXTRAHOP_RETRIEVING_DATA_MESSAGE.format("metrics"))
        self.debug_print(EXTRAHOP_RETRIEVING_DATA_MESSAGE.format("metrics"))

        if not is_json_object:
            data = {
                "cycle": metric_cycle_length,
                "from": start_time,
                "until": end_time,
                "metric_category": metric_category,
                "metric_specs": metric_specs,
                "object_ids": object_id,
                "object_type": object_type,
            }
        else:
            data = json_object
            data.update({"from": start_time, "until": end_time})

        if data["from"] is None:
            data.pop("from")
        if data["until"] is None:
            data.pop("until")
        # identify what type of metric is given according to metric_name
        status, metric_name_type = self.identify_metric_type(action_result, data, metric_name)
        if phantom.is_fail(status):
            return action_result.get_status(), None

        # update the data for (dset, ddset) types
        data = self.update_data_by_type(data, metric_name_type)

        # identify which endpoint to use
        endpoint = EXTRAHOP_METRICS_ENDPOINT
        if not is_json_object:
            endpoint_object_type = param.get("object_type")
            if endpoint_object_type == "Device Group Summary":
                endpoint = EXTRAHOP_METRICS_TOTAL_ENDPOINT

        status, metrics_response = self._make_rest_call(endpoint, action_result, json=data, method="post")
        if phantom.is_fail(status):
            return action_result.get_status(), metrics_response

        if not metrics_response:
            return phantom.APP_SUCCESS, metrics_response

        # test for ECA or EDA results
        # ECA will return an xid and num_results:
        #   u /metrics/next/{xid} will return stats,p to {num_results} times
        # EDA will return a simple stats response, once

        xid = metrics_response.get("xid")
        # num_results by default 1 for EDA
        num_results = metrics_response.get("num_results", 1)

        self.debug_print(f"Extrahop response xid: {xid}, num_results: {num_results}")
        timestamp = None
        all_postprocessed_items = []
        for _ in range(num_results):
            if xid:
                ret_val, metrics_data = self._make_rest_call(EXTRAHOP_METRICS_XID_ENDPOINT.format(xid), action_result)

                if phantom.is_fail(ret_val):
                    self.debug_print(EXTRAHOP_DEFAULT_ERROR.format(action_result.get_message()))
                    continue
            else:
                metrics_data = metrics_response

            for item in metrics_data.get("stats"):
                # Device group summary metrics produce oid=-1 in API response
                item_oid = item["oid"] if item["oid"] != -1 else str(object_id)
                container_limit.add(item_oid)
                if self._is_on_poll and self._is_poll_now and len(container_limit) > param.get("container_count"):
                    container_limit.remove(item_oid)
                    continue
                timestamp = item["time"]
                final_response = self.initial_response(item_oid, timestamp, data)
                updated_final_response, list_final_response = self.postprocess_response(final_response, item, metric_name, metric_name_type)

                if self._is_on_poll:
                    if list_final_response:
                        self._ingest_metrics(action_result, list_final_response, param, "metrics", start_time)
                    if updated_final_response != final_response:
                        self._ingest_metrics(action_result, [updated_final_response], param, "metrics", start_time)
                else:
                    if list_final_response:
                        all_postprocessed_items.extend(list_final_response)
                    if updated_final_response != final_response:
                        all_postprocessed_items.append(updated_final_response)

        if not self._is_on_poll:
            for response_item in all_postprocessed_items:
                action_result.add_data(response_item)

        if self._is_on_poll and data["cycle"] == "auto" and timestamp:
            self.last_time = timestamp
        return phantom.APP_SUCCESS, all_postprocessed_items

    def _poll_for_metrics(self, action_result, params, config):
        now = int(time.time()) * 1000
        if self._is_poll_now:
            params["start_time"] = now - (EXTRAHOP_METRICS_DEFAULT_INTERVAL * 1000)
        else:
            params["start_time"] = self._state.get(EXTRAHOP_METRICS_LAST_INGESTED_TIME, now - (EXTRAHOP_METRICS_DEFAULT_INTERVAL * 1000))

        if isinstance(params["start_time"], int):
            for key in EXTRAHOP_INGESTION_METRICS_KEYS:
                params[key] = config.get(key)
            for key, value in list(params.items()):
                if value is None:
                    params.pop(key)

            if params.get("json_object"):
                ret_val, params["json_object"] = self._validate_json_object(action_result, params)
                if phantom.is_fail(ret_val):
                    return action_result.get_status()
                metrics_cycle = params["json_object"].get("cycle")
            else:
                metrics_cycle = params["metric_cycle_length"]

            params["end_time"] = now
            if params["metric_cycle_length"] != "auto":
                params["start_time"] = self.get_cycle_boundary(params["start_time"], metrics_cycle)
                params["end_time"] = self.get_cycle_boundary(now, metrics_cycle)
                if params["start_time"] == params["end_time"]:
                    return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_METRIC_NOT_NEEDED_MESSAGE.format(self.get_asset_id()))

            status, _ = self._process_metrics(params, action_result)
            if phantom.is_fail(status):
                return action_result.get_status()
        else:
            self._state[EXTRAHOP_METRICS_LAST_INGESTED_TIME] = now
            return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_CORRUPTED_KEY_MESSAGE.format(EXTRAHOP_METRICS_LAST_INGESTED_TIME))

        if not self._is_poll_now:
            self._state[EXTRAHOP_METRICS_LAST_INGESTED_TIME] = self.last_time if self.last_time else params["end_time"]

        return phantom.APP_SUCCESS

    def _validate_json_object_packets(self, action_result, json_object):
        try:
            json_object = json.loads(json_object)

            if not isinstance(json_object, dict):
                return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_INVALID_FILTER_MESSAGE.format("json_object")), None
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_INVALID_FILTER_MESSAGE.format("json_object")), None

        return phantom.APP_SUCCESS, json_object

    def _handle_get_packets(self, param):
        self.save_progress(EXTRAHOP_ACTION_HANDLER_MESSAGE.format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        json_object = param.get("json_object")
        if json_object:
            self.debug_print("Validating JSON object")
            ret_val, json_object = self._validate_json_object_packets(action_result, json_object)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            start_time = json_object.get("from")
            end_time = json_object.get("until")
            param["start_time"] = start_time
            param["end_time"] = end_time
        else:
            ret_val, minutes = self._validate_integer(action_result, param.get("minutes", 30), "minutes")
            if phantom.is_fail(ret_val):
                return action_result.get_status()

            param["start_time"] = f"-{minutes}m"
            param["end_time"] = 0

        ret_val, vault_id = self._process_packets(param, action_result)
        if phantom.is_fail(ret_val):
            self.debug_print(EXTRAHOP_DEFAULT_ERROR.format(action_result.get_message()))
            return action_result.get_status()

        vault_id = vault_id if vault_id else None
        file_name = self.file_path.split("/")[-1] if self.file_path else None

        action_result.add_data({"vault_id": vault_id, "file_name": file_name})

        message = "Successfully added packets"
        if not file_name:
            message = "No packets found"
        self.debug_print(message)
        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _ingest_packets(self, action_result, packets, param, data_type):
        artifacts = []
        file_path = param.get("file_path")
        filename = param.get("file_name")
        container_name = filename.split(".pcap")[0]
        container = self._add_container_data([], data_type, container_name)

        status, message, container_id = self.save_container(container)
        if phantom.is_fail(status):
            self.debug_print(EXTRHOP_CONTAINER_ERROR_MESSAGE.format(container_id, message))

        if EXTRAHOP_DUPLICATE_CONTAINER_MESSAGE in message:
            self.debug_print(EXTRAHOP_DUPLICATE_CONTAINER_MESSAGE)

        ret_val, message, vault_id = phantom_rules.vault_add(container=container_id, file_location=file_path, file_name=filename)
        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, message)

        cef = {"vault_id": vault_id}
        artifacts = [{"label": param.get("label"), "name": container_name, "cef": cef, "container_id": container_id}]

        ret_val, message, _ = self.save_artifacts(artifacts)
        if phantom.is_fail(ret_val):
            self.debug_print(EXTRHOP_ARTIFACT_ERROR_MESSAGE.format(message))

        return phantom.APP_SUCCESS

    def _validate_process_packets_parameters(self, param, action_result):
        processed_params = dict()

        key_list = ["bpf", "limit_bytes", "limit_search_duration"]
        for key in key_list:
            value = param.get(key)
            if value is not None:
                processed_params[key] = value

        ip1 = param.get("ip1")
        if ip1:
            ret_val = self._validate_ip(ip1)
            if not ret_val:
                return action_result.set_status(phantom.APP_ERROR, "Parameter 'ip1' is not a valid ip address"), processed_params
            processed_params["ip1"] = ip1.strip()

        ip2 = param.get("ip2")
        if ip2:
            ret_val = self._validate_ip(ip2)
            if not ret_val:
                return action_result.set_status(phantom.APP_ERROR, "Parameter 'ip2' is not a valid ip address"), processed_params
            processed_params["ip2"] = ip2.strip()

        port1 = param.get("port1")
        ret_val, processed_params["port1"] = self._validate_integer(action_result, port1, "port1", True)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), processed_params

        port2 = param.get("port2")
        ret_val, processed_params["port2"] = self._validate_integer(action_result, port2, "port2", True)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), processed_params

        return phantom.APP_SUCCESS, processed_params

    def _process_packets(self, params, action_result):
        packets = list()
        data = dict()
        self.save_progress(EXTRAHOP_PARAM_VALIDATION_MESSAGE)
        self.debug_print(EXTRAHOP_PARAM_VALIDATION_MESSAGE)

        is_json_object = False
        json_object = params.get("json_object")
        if json_object:
            is_json_object = True
            try:
                data = json.loads(json_object)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_INVALID_FILTER_MESSAGE.format("json_object")), packets
        if not is_json_object:
            ret_val, processed_params = self._validate_process_packets_parameters(params, action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status(), packets

        start_time = params.get("start_time")
        end_time = params.get("end_time")

        self.save_progress(EXTRAHOP_RETRIEVING_DATA_MESSAGE.format("packets"))
        self.debug_print(EXTRAHOP_RETRIEVING_DATA_MESSAGE.format("packets"))

        data.update({"from": start_time, "until": end_time, "output": "pcap"})

        if not is_json_object:
            for key, value in processed_params.items():
                if value is not None:
                    data[key] = value

        if data["from"] is None:
            data.pop("from")
        if data["until"] is None:
            data.pop("until")

        ret_val, packets = self._make_rest_call(EXTRAHOP_PACKET_SEARCH_ENDPOINT, action_result, json=data, method="post")
        if phantom.is_fail(ret_val):
            return action_result.get_status(), packets

        if self.file_path:
            params["file_path"] = self.file_path
            params["file_name"] = self.file_path.split("/")[-1]
        else:
            return phantom.APP_SUCCESS, packets

        if self._is_on_poll:
            ret_val = self._ingest_packets(action_result, packets, params, data_type="PCAP")
            if phantom.is_fail(ret_val):
                return action_result.get_status(), packets
        else:
            try:
                ret_val, message, vault_id = phantom_rules.vault_add(
                    container=self.get_container_id(), file_location=params["file_path"], file_name=params["file_name"]
                )
                if phantom.is_fail(ret_val):
                    return action_result.set_status(phantom.APP_ERROR, message), None
            except Exception as e:
                return RetVal(
                    action_result.set_status(
                        phantom.APP_ERROR, f"Unable to store file in Phantom Vault. Error: {self._get_error_message_from_exception(e)}"
                    ),
                    None,
                )
            return phantom.APP_SUCCESS, vault_id

        return phantom.APP_SUCCESS, packets

    def _poll_for_packets(self, action_result, params, config):
        now = int(time.time()) * 1000
        if self._is_poll_now:
            params["start_time"] = now - (EXTRAHOP_PACKETS_DEFAULT_INTERVAL * 1000)
        else:
            params["start_time"] = self._state.get(EXTRAHOP_PACKETS_LAST_INGESTED_TIME, now - (EXTRAHOP_PACKETS_DEFAULT_INTERVAL * 1000))
        params["end_time"] = now
        if isinstance(params["start_time"], int):
            for key in EXTRAHOP_INGESTION_PACKETS_KEYS:
                params[key] = config.get(key)
            for key, value in list(params.items()):
                if value is None:
                    params.pop(key)

            status, _ = self._process_packets(params, action_result)
            if phantom.is_fail(status):
                return action_result.get_status()
        else:
            self._state[EXTRAHOP_PACKETS_LAST_INGESTED_TIME] = now
            return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_CORRUPTED_KEY_MESSAGE.format(EXTRAHOP_PACKETS_LAST_INGESTED_TIME))

        if not self._is_poll_now:
            self._state[EXTRAHOP_PACKETS_LAST_INGESTED_TIME] = now

        return phantom.APP_SUCCESS

    def _handle_on_poll(self, param):
        """
         Perform the on poll ingest functionality.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        action_result = self.add_action_result(ActionResult(dict(param)))

        config = self.get_config()
        ingestion_type = config.get("ingestion_type")

        if ingestion_type not in EXTRAHOP_INGESTION_TYPE_LIST:
            return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_INVALID_SELECTION.format("ingestion_type", EXTRAHOP_INGESTION_TYPE_LIST))

        self._is_poll_now = self.is_poll_now()
        self._is_on_poll = True
        params = dict()
        params["label"] = config.get("ingest", {}).get("container_label")

        if self._is_poll_now:
            params["container_count"] = param.get("container_count")

        json_object = config.get("json_object")
        if json_object is not None:
            try:
                json_object = json.loads(json_object)
                if not isinstance(json_object, dict):
                    return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_INVALID_FILTER_MESSAGE.format("json_object")), None
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, EXTRAHOP_INVALID_FILTER_MESSAGE.format("json_object")), None

        if ingestion_type == "Detections":
            status = self._poll_for_detections(action_result, params, config)
            if phantom.is_fail(status):
                self.debug_print(EXTRAHOP_DEFAULT_ERROR.format(action_result.get_message()))
                return action_result.get_status()
        elif ingestion_type == "Metrics":
            status = self._poll_for_metrics(action_result, params, config)
            if phantom.is_fail(status):
                self.debug_print(EXTRAHOP_DEFAULT_ERROR.format(action_result.get_message()))
                return action_result.get_status()
        elif ingestion_type == "PCAP":
            status = self._poll_for_packets(action_result, params, config)
            if phantom.is_fail(status):
                self.debug_print(EXTRAHOP_DEFAULT_ERROR.format(action_result.get_message()))
                return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        """Get current action identifier and call member function of its own to handle the action."""
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "get_device":
            ret_val = self._handle_get_device(param)

        elif action_id == "get_peers":
            ret_val = self._handle_get_peers(param)

        elif action_id == "get_protocols":
            ret_val = self._handle_get_protocols(param)

        elif action_id == "detect_devices":
            ret_val = self._handle_detect_devices(param)

        elif action_id == "create_device":
            ret_val = self._handle_create_device(param)

        elif action_id == "tag_device":
            ret_val = self._handle_tag_device(param)

        elif action_id == "get_metrics":
            ret_val = self._handle_get_metrics(param)

        elif action_id == "get_packets":
            ret_val = self._handle_get_packets(param)

        elif action_id == "on_poll":
            ret_val = self._handle_on_poll(param)

        return ret_val

    def _validate_ip(self, input_data):
        ip_addresses = [x.strip() for x in input_data.split(",")]
        ip_addresses = list(filter(None, ip_addresses))

        for ip in ip_addresses:
            try:
                ipaddress.ip_address(ip.strip())
            except Exception:
                return False

        return True

    def initialize(self):
        """Initialize the global variables with its value and validate it."""
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()
        if not isinstance(self._state, dict):
            self.debug_print(EXTRAHOP_STATE_FILE_CORRUPT_ERROR)
            self._state = {"app_version": self.get_app_json().get("app_version")}

        # get the asset config
        config = self.get_config()

        self._base_url = "https://{}".format(config["base_url"])
        self._asset_id = self.get_asset_id()
        self.set_validator("ip", self._validate_ip)
        self._instance_type = config["instance_type"]

        if self._instance_type == EXTRAHOP_INSTANCE_ON_PREM:
            self._platform_url = self._base_url
        else:
            self._platform_url = config.get("platform_url", "").strip("/")

        self._api_key = config.get("api_key")
        if self._instance_type == EXTRAHOP_INSTANCE_ON_PREM and not self._api_key:
            return self.set_status(phantom.APP_ERROR, "Rest API key is Required")

        self._client_id = config.get("client_id")
        self._client_secret = config.get("client_secret")
        if self._instance_type == EXTRAHOP_INSTANCE_CLOUD and (not self._client_id or not self._client_secret):
            return self.set_status(phantom.APP_ERROR, "Client ID and Client secret are Required")

        if self._instance_type == EXTRAHOP_INSTANCE_CLOUD:
            self._verify_server_cert = True
        else:
            self._verify_server_cert = config.get("verify_server_cert", True)
        self._access_token = self.decrypt_state()

        return phantom.APP_SUCCESS

    def finalize(self):
        """Perform some final operations or clean up operations."""
        if self._instance_type == EXTRAHOP_INSTANCE_CLOUD and self._state.get(EXTRAHOP_OAUTH_TOKEN_STRING) and self._access_token:
            self._state[EXTRAHOP_OAUTH_TOKEN_STRING][EXTRAHOP_OAUTH_ACCESS_TOKEN_STRING] = self.encrypt_state()
            self._state[EXTRAHOP_OAUTH_ACCESS_TOKEN_IS_ENCRYPTED] = True
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def decrypt_state(self):
        """Decrypt the token."""
        state_access_token = self._state.get(EXTRAHOP_OAUTH_TOKEN_STRING, {}).get(EXTRAHOP_OAUTH_ACCESS_TOKEN_STRING)
        if state_access_token and self._state.get(EXTRAHOP_OAUTH_ACCESS_TOKEN_IS_ENCRYPTED, False):
            try:
                return encryption_helper.decrypt(
                    self._state.get(EXTRAHOP_OAUTH_TOKEN_STRING).get(EXTRAHOP_OAUTH_ACCESS_TOKEN_STRING), self._asset_id
                )
            except Exception as ex:
                self.debug_print(f"{EXTRAHOP_DECRYPTION_ERROR}: {self._get_error_message_from_exception(ex)}")
        return None

    def encrypt_state(self):
        """Encrypt the token."""
        try:
            return encryption_helper.encrypt(self._access_token, self._asset_id)
        except Exception as ex:
            self.debug_print(f"{EXTRAHOP_ENCRYPTION_ERROR}: {self._get_error_message_from_exception(ex)}")
        return None


if __name__ == "__main__":
    import argparse
    import sys

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
        try:
            login_url = f"{BaseConnector._get_phantom_base_url()}login"
            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=EXTRAHOP_DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=EXTRAHOP_DEFAULT_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = ExtrahopConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
