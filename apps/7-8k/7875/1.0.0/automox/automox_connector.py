# File: automox_connector.py
#
# Copyright (c) Automox, 2025
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
from datetime import time, timedelta
from functools import wraps
from math import ceil
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union
from urllib.parse import quote, urlencode

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from automox_consts import (
    AUTOMOX_COMMAND_QUEUE_LIST_ENDPOINT,
    AUTOMOX_CONSOLE_API_URL,
    AUTOMOX_DEVICE_LIST_ENDPOINT,
    AUTOMOX_DEVICE_LIST_PACKAGES_ENDPOINT,
    AUTOMOX_DEVICE_SPECIFIC_ENDPOINT,
    AUTOMOX_GROUPS_LIST_ENDPOINT,
    AUTOMOX_ORGS_LIST_ENDPOINT,
    AUTOMOX_PACKAGE_LIST_ALL_ENDPOINT,
    AUTOMOX_POLICY_LIST_ENDPOINT,
    AUTOMOX_POLICY_LIST_SPECIFIC_ENDPOINT,
    AUTOMOX_POLICY_RUN_ENDPOINT,
    AUTOMOX_REMOVE_USER_FROM_ACCOUNT_ENDPOINT,
    AUTOMOX_USERS_LIST_ENDPOINT,
    AUTOMOX_USERS_LIST_SPECIFIC_ENDPOINT,
    AUTOMOX_USERS_SELF_ENDPOINT,
)


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class Params:
    """
    A class to handle various parameter types used in API requests.
    """

    def __init__(self, query_params=None, path_params=None, **kwargs) -> None:
        if path_params is None:
            path_params = {}
        if query_params is None:
            query_params = {}

        self._query_params = (
            query_params  # {"description": "Query parameters for the API request"}
        )
        self._path_params = (
            path_params  # {"description": "Path parameters for the API request"}
        )
        self._aux_params = dict(
            kwargs
        )  # {"description": "Additional parameters for the API request"}

    def get_query_params(self) -> Dict[str, str]:
        """Get a copy of query parameters"""
        return self._query_params.copy() if self._query_params else {}

    def get_query_param_by_key(self, key: str) -> Union[str, None]:
        """Get a specific query parameter value by key"""
        return self._query_params.get(key, None)

    def get_path_params(self) -> Dict[str, str]:
        """Get a copy of path parameters"""
        return self._path_params.copy() if self._path_params else {}

    def get_path_param_by_key(self, key: str) -> Union[str, None]:
        """Get a specific path parameter value by key"""
        return self._path_params.get(key, None)

    def get_aux_params(self) -> Dict[str, Any]:
        """Get a copy of auxiliary parameters"""
        return self._aux_params.copy()

    def get_aux_param_by_key(self, key: str) -> Union[str, None]:
        """Get a specific auxiliary parameter value by key"""
        return self._aux_params.get(key, None)

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Get all parameters as a dictionary"""
        return {
            "query_params": self.get_query_params(),
            "path_params": self.get_path_params(),
            "aux_params": self.get_aux_params(),
        }

    def get_params(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Get parameters for URL building"""
        return self.get_path_params(), self.get_query_params()


class Device(TypedDict, total=False):
    id: int  # {"description": "Device ID"}
    name: str  # {"description": "Device hostname/name"}
    display_name: str  # {"description": "Custom display name"}
    ip_addrs: List[str]  # {"description": "List of public IP addresses"}
    ip_addrs_private: List[str]  # {"description": "List of private IP addresses"}
    os_family: str  # {"description": "Operating system family"}
    os_name: str  # {"description": "Operating system name"}
    os_version: str  # {"description": "Operating system version"}
    server_group_id: int  # {"description": "Group ID the device belongs to"}
    tags: List[str]  # {"description": "List of tags assigned to device"}
    total_count: int  # {"description": "Total count for paginated responses"}
    status: str  # {"description": "Device status"}
    last_refresh: str  # {"description": "Last device refresh timestamp"}
    custom_name: str  # {"description": "User-defined device name"}
    exception: bool  # {"description": "Whether device has 'exclude from reports' flag"}


class AutomoxConnector(BaseConnector):
    ACTION_MAPPING = {
        "test_connectivity": "_handle_test_connectivity",
        "list_organizations": "_handle_list_organizations",
        "list_organization_users": "_handle_list_organization_users",
        "get_organization_user": "_handle_get_organization_user",
        "remove_user_from_account": "_handle_remove_user_from_account",
        "get_device": "_handle_get_device",
        "list_devices": "_handle_list_devices",
        "get_device_by_ip_address": "_handle_get_device_by_ip_address",
        "get_device_by_hostname": "_handle_get_device_by_hostname",
        "update_device": "_handle_update_device",
        "delete_device": "_handle_delete_device",
        "get_device_software": "_handle_get_device_software",
        "list_software": "_handle_list_software",
        "list_groups": "_handle_list_groups",
        "list_policies": "_handle_list_policies",
        "get_policy": "_handle_get_policy",
        "run_policy": "_handle_run_policy",
        "get_command_queues": "_handle_get_command_queues",
    }

    def action_handler(action_config):
        """Decorator for creating standardized action handlers"""

        def decorator(func):
            @wraps(func)
            def wrapper(self, param):
                # init params
                processed_params = {}

                param_mappings = {
                    "org_id": "o"
                }  # Map org_id to o since that's what the API uses

                # Extract path parameters from input param if they exist
                if "params" in action_config:
                    if "path_params" in action_config["params"]:
                        processed_params["path_params"] = {
                            key: param[key]
                            for key in action_config["params"]["path_params"]
                            if key in param
                        }

                    # Handle query parameters if defined
                    if "query_params" in action_config["params"]:
                        processed_params["query_params"] = {
                            param_mappings.get(key, key): param[
                                key
                            ]  # Use mapped name if exists
                            for key in action_config["params"]["query_params"]
                            if key in param
                        }

                    # Handle auxiliary parameters if defined (like POST body params)
                    if "aux_params" in action_config["params"]:
                        processed_params.update(
                            {
                                key: param[key]
                                for key in action_config["params"]["aux_params"]
                                if key in param
                            }
                        )

                # Create action object with updated parameters
                action = self.AutomoxAction(
                    base_endpoint=action_config["base_endpoint"],
                    handle_function=getattr(
                        self, action_config.get("handler_function", "_handle_generic")
                    ),
                    fetch_function=getattr(self, action_config.get("fetch_function"))
                    if action_config.get("fetch_function")
                    else None,
                    fetch_function_method=action_config.get(
                        "fetch_function_method", "get"
                    ),
                    params=Params(**processed_params)
                    if processed_params
                    else Params(**param),
                    summary_key=action_config.get("summary_key"),
                )

                # If the action has a specific handler implementation function, use that
                if "handler_function" in action_config and action_config[
                    "handler_function"
                ].endswith("_impl"):
                    return getattr(self, action_config["handler_function"])(action)

                # or just use the generic handler
                return self._handle_generic(action)

            return wrapper

        return decorator

    class AutomoxAction:
        """
        Class representing an Automox API action with its configuration and parameters
        """

        def __init__(
            self,
            base_endpoint: str,
            handle_function: callable,
            fetch_function: callable = None,
            fetch_function_method: str = "get",
            params: Optional[Union[Params, Dict[str, Any]]] = None,
            summary_key: str = None,
        ):
            """
            Initialize an AutomoxAction instance

            Args:
                base_endpoint: Base API endpoint for the action
                handle_function: Function that handles the action logic
                fetch_function: Function that fetches data from the API
                fetch_function_method: HTTP method to use (get/post/put/delete)
                params: Request parameters (query, path, auxiliary)
                summary_key: Key used in action summary response
            """
            self.base_endpoint = base_endpoint
            self.handle_function = handle_function
            self.fetch_function = fetch_function
            self.fetch_function_method = fetch_function_method.lower()
            # Convert dict to Params at creation time
            self.params = (
                Params()
                if params is None
                else (params if isinstance(params, Params) else Params(**params))
            )
            self.summary_key = summary_key

    def __init__(self):
        super(AutomoxConnector, self).__init__()

        self._page_limit = None
        self._headers = None
        self._state = None
        self._base_url = None

    def initialize(self) -> int:
        config = self.get_config()

        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()
        self._base_url = AUTOMOX_CONSOLE_API_URL
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['ax_console_api_key']}",
        }
        self._page_limit = int(config.get("page_limit", 100))

        return phantom.APP_SUCCESS

    # Helper functions

    def _get_endpoint(self, action: AutomoxAction) -> str:
        return self._build_url_for_action(
            base_endpoint=action.base_endpoint, action=action
        )

    def _build_url_for_action(self, base_endpoint: str, action: AutomoxAction) -> str:
        """
        Constructs a full URL by replacing placeholders in the base endpoint and appending query parameters

        Args:
            base_endpoint (str): Base API endpoint for the action
            action (AutomoxAction): Action object containing parameters
        """
        path_params, query_params = action.params.get_params()

        # Replace path params
        if path_params:
            for key, value in path_params.items():
                safe_value = quote(str(value), safe="")
                placeholder = f"{{{key}}}"

                if placeholder in base_endpoint:
                    base_endpoint = base_endpoint.replace(placeholder, safe_value)
                else:
                    self.debug_print(
                        f"Warning: Path param key '{key}' not found in endpoint."
                    )

        # Filter out None or empty values from query parameters
        if query_params:
            query_params = {k: v for k, v in query_params.items() if v}

        # Append query params
        full_url = base_endpoint
        if query_params:
            query_string = urlencode(query_params)
            full_url = f"{base_endpoint}?{query_string}"

        self.debug_print(f"The full URL we're returning: {full_url}")
        return full_url

    @staticmethod
    def _process_empty_response(
        response: requests.Response, action_result: ActionResult
    ) -> RetVal:
        if response.status_code in [200, 204]:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(
                phantom.APP_ERROR, "Empty response and no information in the header"
            ),
            None,
        )

    @staticmethod
    def _process_html_response(
        response: requests.Response, action_result: ActionResult
    ) -> RetVal:
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except Exception as e:
            error_text = f"Cannot parse error details: {e}"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    @staticmethod
    def _process_json_response(
        r: requests.Response, action_result: ActionResult
    ) -> RetVal:
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, f"Unable to parse JSON response. Error: {str(e)}"
                ),
                None,
            )

        if 200 <= r.status_code < 400:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        message = f"Error from server. Status Code: {r.status_code} Data from server: {r.text.replace('{', '{{').replace('}', '}}')}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(
        self, r: requests.Response, action_result: ActionResult
    ) -> RetVal:
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)
        elif "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        if not r.text:
            return self._process_empty_response(r, action_result)

        message = f"Can't process response from server. Status Code: {r.status_code} Data from server: {r.text.replace('{', '{{').replace('}', '}}')}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(
        self,
        endpoint: str,
        action_result: ActionResult,
        method: str = "get",
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> RetVal:
        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, f"Invalid method: {method}"
                ),
                resp_json,
            )

        url = self._base_url + endpoint

        try:
            r = request_func(
                url,
                verify=config.get("verify_server_cert", False),
                headers=headers,
                **kwargs,
            )
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, f"Error Connecting to server. Details: {str(e)}"
                ),
                resp_json,
            )

        return self._process_response(r, action_result)

    def _fetch_paginated_data(
        self,
        endpoint: str,
        params: Union[Params, Dict[str, Any]],
        action_result: ActionResult,
        headers: Dict[str, str],
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """Fetches all pages of data from a paginated API endpoint."""
        params_obj = params if isinstance(params, Params) else Params(**params)
        paginated_params = self.first_page(params_obj)
        all_items = []

        while True:
            ret_val, response = self._make_rest_call(
                endpoint=endpoint,
                action_result=action_result,
                params=paginated_params.get_query_params(),
                headers=headers,
            )

            if phantom.is_fail(ret_val):
                return phantom.APP_ERROR, []

            all_items.extend(response)

            # If we receive fewer items than the limit, we've hit the last page
            if len(response) < self._page_limit:
                self.debug_print(
                    f"Received {len(response)} items, which is less than page limit {self._page_limit}. This is the last page."
                )
                break

            # If we receive exact the limit, check for next page
            if len(response) == self._page_limit:
                self.debug_print(
                    "Got full page per page limit, checking for next page..."
                )
                paginated_params = self.next_page(paginated_params)  # get the next page
                self.debug_print(f"Next page params: {paginated_params.to_dict()}")
                continue

        self.debug_print(f"Total items fetched: {len(all_items)}")
        return phantom.APP_SUCCESS, all_items

    def first_page(self, params: Union[Params, Dict[str, Any]]) -> Params:
        """Initialize pagination parameters"""
        if not isinstance(params, Params):
            params = Params(**params)

        query_params = params.get_query_params()
        query_params.update({"limit": self._page_limit, "page": 0})

        return Params(query_params=query_params, path_params=params.get_path_params())

    @staticmethod
    def next_page(params: Params) -> Params:
        """Get parameters for the next page"""
        query_params = params.get_query_params()
        current_page = query_params.get("page", 0)
        query_params["page"] = current_page + 1
        query_params["limit"] = query_params.get("limit", 100)

        return Params(query_params=query_params, path_params=params.get_path_params())

    def _get_total_device_count(
        self, endpoint: str, action_result: ActionResult
    ) -> int:
        ret_val, response = self._make_rest_call(
            endpoint=endpoint,
            action_result=action_result,
            params={"limit": 1},  # Fetch only one device to get the total count
            headers=self._headers,
        )

        if phantom.is_fail(ret_val):
            raise Exception(
                f"Failed to get total device count: {action_result.get_message()}"
            )

        return response[0].get("total_count", 0)

    @staticmethod
    def _is_valid_number(value: Any) -> bool:
        """
        Check if value is valid (not None and either a number or any other non-None type)

        Args:
            value: Value to check

        Returns:
            bool: True if value is valid, False otherwise
        """
        return value is not None

    def remove_null_values(
        self, item: Union[Dict[str, Any], List[Any], Any]
    ) -> Union[Dict[str, Any], List[Any], Any]:
        """
        Recursively remove null values from a dictionary or list
        """
        if isinstance(item, dict):
            return {
                key: self.remove_null_values(value)
                for key, value in item.items()
                if self._is_valid_number(value)
                and self._is_valid_number(self.remove_null_values(value))
            }
        elif isinstance(item, list):
            return [
                self.remove_null_values(value)
                for value in item
                if self._is_valid_number(value)
                and self._is_valid_number(self.remove_null_values(value))
            ]
        return item

    @staticmethod
    def _find_matching_devices(
        devices: List[Device], attributes: List[str], value: str
    ) -> List[Device]:
        """
        Searches for all devices matching specified attributes and value.

        Args:
            devices (List[Device]): List of device dictionaries to search
            attributes (List[str]): Device attributes to check
            value (str): Value to match against

        Returns:
            List[Device]: List of matching device dictionaries
        """
        matches = []
        for device in devices:
            for attr in attributes:
                attr_value = device.get(attr)

                if attr_value is None:
                    continue
                if (
                    isinstance(attr_value, str)
                    and attr_value.casefold() == value.casefold()
                ):
                    matches.append(device)
                    break
                if isinstance(attr_value, list) and value.lower() in (
                    v.lower() for v in attr_value
                ):
                    matches.append(device)
                    break
        return matches

    def find_devices_by_attribute_with_value(
        self,
        endpoint: str,
        attributes: List[str],
        value: str,
        action_result: ActionResult,
        params: Optional[Union[Params, Dict[str, Any]]] = None,
    ) -> Optional[List[Device]]:
        """
        Searches through all devices to find all matching specified attributes with given value.

        Args:
            endpoint (str): API endpoint for device listing
            attributes (List[str]): Device attributes to check
            value (str): Value to match against the attributes
            action_result (ActionResult): Action result object for status tracking
            params (Optional[Union[Params, Dict[str, Any]]]): Parameters for the request

        Returns:
            Optional[List[Device]]: List of matching device dictionaries or None if no matches found

        Raises:
            Exception: If API call fails
        """
        matches = []
        total_devices = self._get_total_device_count(endpoint, action_result)
        if total_devices is None:
            return None

        max_pages = ceil(total_devices / self._page_limit)
        paginated_params = self.first_page(params)

        for current_page in range(max_pages):
            self.debug_print(
                f"Fetching devices with params: {paginated_params.to_dict()}"
            )

            ret_val, devices = self._make_rest_call(
                endpoint=endpoint,
                action_result=action_result,
                params=paginated_params.get_query_params(),
                headers=self._headers,
            )

            if phantom.is_fail(ret_val):
                self.debug_print(
                    f"Failed to get devices: {action_result.get_message()}"
                )
                raise Exception(f"Failed to get devices: {action_result.get_message()}")

            page_matches = self._find_matching_devices(devices, attributes, value)
            matches.extend(self.remove_null_values(device) for device in page_matches)

            if len(devices) < self._page_limit:
                break

            paginated_params = self.next_page(paginated_params)
            current_page += 1

        self.debug_print(f"Found {len(matches)} devices matching {value}")
        return matches if matches else None

    # Action implementations

    def _handle_generic(self, action: AutomoxAction) -> int:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(action.params.to_dict()))
        endpoint = self._get_endpoint(action)

        fetch_function_kwargs = {
            "endpoint": endpoint,
            "params": action.params.get_query_params(),
            "action_result": action_result,
            "headers": self._headers,
        }

        # Include POST body if fetch_function_method is POST
        if action.fetch_function_method.lower() == "post":
            fetch_function_kwargs["method"] = "post"
            fetch_function_kwargs["data"] = json.dumps(
                action.params.get_aux_param_by_key("body")
            )

        # Do a DELETE if fetch_function_method is DELETE
        if action.fetch_function_method.lower() == "delete":
            fetch_function_kwargs["method"] = "delete"

        ret_val, response = action.fetch_function(**fetch_function_kwargs)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        if action.summary_key:
            summary = action_result.update_summary({})
            summary[action.summary_key] = len(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_device_by_ip_address_impl(self, action: AutomoxAction) -> int:
        """
        Handles the get_device_by_ip_address action.
        Returns all devices that match the given IP address.

        Args:
            action (AutomoxAction): Action configuration object

        Returns:
            int: Action status code (success/failure)
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(action.params.to_dict()))
        endpoint = self._get_endpoint(action)

        ip_address = action.params.get_aux_param_by_key("ip_address")
        ip_pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")

        if not ip_pattern.match(ip_address):
            return action_result.set_status(
                phantom.APP_ERROR, f"Invalid IP address format: {ip_address}"
            )

        try:
            # Search for devices with matching public IP
            matches = self.find_devices_by_attribute_with_value(
                endpoint=endpoint,
                attributes=["ip_addrs"],
                value=ip_address,
                action_result=action_result,
                params=action.params,
            )

            # If no matches found with public IP, try private IPs
            if not matches:
                self.save_progress(
                    "No devices found using public IP. Trying private IPs..."
                )
                matches = self.find_devices_by_attribute_with_value(
                    endpoint=endpoint,
                    attributes=["ip_addrs_private"],
                    value=ip_address,
                    action_result=action_result,
                    params=action.params,
                )

            if not matches:
                return action_result.set_status(
                    phantom.APP_ERROR, f"No devices found with IP address {ip_address}"
                )

            # Add all matching devices to the result
            for device in matches:
                action_result.add_data(device)

            if action.summary_key:
                summary = action_result.update_summary({})
                summary[action.summary_key] = len(matches)

            return action_result.set_status(phantom.APP_SUCCESS)

        except Exception as e:
            self.debug_print(f"Exception occurred: {str(e)}")
            return action_result.set_status(
                phantom.APP_ERROR, f"Error finding devices by IP address: {str(e)}"
            )

    def _handle_get_device_by_hostname_impl(self, action: AutomoxAction) -> int:
        """
        Handles the get_device_by_hostname action.
        Returns all devices that match the given hostname.

        Args:
            action (AutomoxAction): Action configuration object

        Returns:
            int: Action status code (success/failure)
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(action.params.to_dict()))
        endpoint = self._get_endpoint(action)

        hostname = action.params.get_aux_param_by_key("hostname")
        self.debug_print(f"Searching for devices with hostname: {hostname}")

        try:
            matches = self.find_devices_by_attribute_with_value(
                endpoint=endpoint,
                attributes=["name"],
                value=hostname,
                action_result=action_result,
                params=action.params,
            )

            if not matches:
                return action_result.set_status(
                    phantom.APP_ERROR, f"No devices found with hostname {hostname}"
                )

            # Add all matching devices to the result
            for device in matches:
                action_result.add_data(device)

            if action.summary_key:
                summary = action_result.update_summary({})
                summary[action.summary_key] = len(matches)

            return action_result.set_status(phantom.APP_SUCCESS)

        except Exception as e:
            self.debug_print(f"Exception occurred: {str(e)}")
            return action_result.set_status(
                phantom.APP_ERROR, f"Error finding devices by hostname: {str(e)}"
            )

    def _handle_update_device_impl(self, action: AutomoxAction):
        """
        Handles the update_device action.

        Args:
            action (AutomoxAction): Action configuration object

        Returns:
            int: Action status code (success/failure)
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(action.params.to_dict()))
        endpoint = self._get_endpoint(action)

        # Extract aux params for POST body
        exception = action.params.get_aux_param_by_key("exception")
        server_group_id = action.params.get_aux_param_by_key("server_group_id")
        tags = action.params.get_aux_param_by_key("tags")
        custom_name = action.params.get_aux_param_by_key("custom_name")

        # Validate and process tags
        tag_list = []
        if tags:
            # Check if the string is a valid comma-separated value
            if not re.match(r"^[a-zA-Z0-9_]+(,[a-zA-Z0-9_]+)*$", tags.strip()):
                return action_result.set_status(
                    phantom.APP_ERROR,
                    "Invalid tags: Tags must be a comma-separated list of alphanumeric values or underscores (e.g., 'tag1,tag2,tag3').",
                )

            # Split and process tags into a list
            tag_list = [tag.strip() for tag in tags.split(",")]

        body = {
            "server_group_id": server_group_id,
            "exception": exception,
            "tags": tag_list,
            **({"custom_name": custom_name} if custom_name is not None else {}),
        }

        # Serialize the body to JSON for proper formatting (else tags have single quotes around them)
        json_body = json.dumps(body)

        # make rest call
        ret_val, response = self._make_rest_call(
            endpoint, action_result, data=json_body, headers=self._headers, method="put"
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_organization_users_impl(self, action: AutomoxAction) -> int:
        """
        Handles both list_organization_users and get_organization_user actions.
        If user_id is provided in the params, fetches a single user, otherwise lists all users.

        Args:
            action (AutomoxAction): Action configuration object

        Returns:
            int: Action status code (success/failure)
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(action.params.to_dict()))
        endpoint = self._get_endpoint(action)

        # Check if we're getting a single user
        user_id = action.params.get_path_param_by_key("user_id")

        if user_id:
            ret_val, users = self._make_rest_call(
                endpoint, action_result, method="get", headers=self._headers
            )
            users = [users] if ret_val == phantom.APP_SUCCESS else []
        else:
            ret_val, users = self._fetch_paginated_data(
                endpoint=endpoint,
                params=action.params,
                action_result=action_result,
                headers=self._headers,
            )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for user in users:
            formatted_user = user.copy()

            # Combine first and last name
            if "firstname" in user and "lastname" in user:
                formatted_user["name"] = f"{user['firstname']} {user['lastname']}"

            # Format organizations with their IDs
            if "orgs" in user and user["orgs"]:
                org_names = [f"{org['name']} ({org['id']})" for org in user["orgs"]]
                formatted_user["orgs_formatted"] = ", ".join(org_names)

            # Format RBAC roles if present
            if "rbac_roles" in user and user["rbac_roles"]:
                role_info = [
                    f"{role['name']} ({role['organization_id']})"
                    for role in user["rbac_roles"]
                ]
                formatted_user["rbac_roles_formatted"] = ", ".join(role_info)

            if "tags" in user and user["tags"]:
                formatted_user["tags"] = ", ".join(user["tags"])

            action_result.add_data(formatted_user)

        if action.summary_key and not user_id:  # Only add summary for multiple users
            summary = action_result.update_summary({})
            summary[action.summary_key] = len(users)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_run_policy_impl(self, action: AutomoxAction) -> int:
        """
        Handles the run_policy action.
        Runs a policy on a specific device.

        Args:
            action (AutomoxAction): Action configuration object

        Returns:
            int: Action status code (success/failure)
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(action.params.to_dict()))
        endpoint = self._get_endpoint(action)

        device_id = action.params.get_aux_param_by_key(
            "device_id"
        )  # Get device_id from aux params

        body = {"action": "remediateAll", "serverId": device_id}

        ret_val, response = self._make_rest_call(
            endpoint=endpoint,
            action_result=action_result,
            data=json.dumps(body),
            headers=self._headers,
            method="post",
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS)

    # Action handlers

    # test_connectivity
    @action_handler(
        {
            "base_endpoint": AUTOMOX_USERS_SELF_ENDPOINT,
            "fetch_function": "_make_rest_call",
        }
    )
    def _handle_test_connectivity(self, param: Dict[str, Any]) -> int:
        """Handle test_connectivity action"""
        self.debug_print("Starting test connectivity action")
        self.save_progress("Testing connectivity to Automox API")
        return phantom.APP_SUCCESS

    # list_organizations
    @action_handler(
        {
            "base_endpoint": AUTOMOX_ORGS_LIST_ENDPOINT,
            "fetch_function": "_fetch_paginated_data",
            "summary_key": "total_organizations",
        }
    )
    def _handle_list_organizations(self, param: Dict[str, Any]) -> int:
        """Handle list_organizations action"""
        self.debug_print("Starting list_organizations action")
        self.save_progress("Listing all organizations")
        return phantom.APP_SUCCESS

    # list organization users
    @action_handler(
        {
            "base_endpoint": AUTOMOX_USERS_LIST_ENDPOINT,
            "handler_function": "_handle_list_organization_users_impl",
            "fetch_function": "_fetch_paginated_data",
            "params": {"query_params": ["org_id"]},
            "summary_key": "total_users",
        }
    )
    def _handle_list_organization_users(self, param: Dict[str, Any]) -> int:
        """Handle list_organization_users action"""
        self.debug_print("Starting list_organization_users action")
        self.save_progress("Listing all organization users")
        return phantom.APP_SUCCESS

    # get_organization_user
    @action_handler(
        {
            "base_endpoint": AUTOMOX_USERS_LIST_SPECIFIC_ENDPOINT,
            "handler_function": "_handle_list_organization_users_impl",
            "fetch_function": "_make_rest_call",
            "params": {"query_params": ["org_id"], "path_params": ["user_id"]},
        }
    )
    def _handle_get_organization_user(self, param: Dict[str, Any]) -> int:
        """Handle get_organization_user action"""
        self.debug_print("Starting get_organization_user action")
        self.save_progress("Getting organization user by ID")
        return phantom.APP_SUCCESS

    # remove_user_from_account
    @action_handler(
        {
            "base_endpoint": AUTOMOX_REMOVE_USER_FROM_ACCOUNT_ENDPOINT,
            "fetch_function": "_make_rest_call",
            "fetch_function_method": "delete",
            "params": {"path_params": ["account_uuid", "user_uuid"]},
        }
    )
    def _handle_remove_user_from_account(self, param: Dict[str, Any]) -> int:
        """Handle remove_user_from_account action"""
        self.debug_print("Starting remove_user_from_account action")
        self.save_progress("Removing user from account")
        return phantom.APP_SUCCESS

    # list_devices
    @action_handler(
        {
            "base_endpoint": AUTOMOX_DEVICE_LIST_ENDPOINT,
            "fetch_function": "_fetch_paginated_data",
            "params": {"query_params": ["org_id"]},
            "summary_key": "total_devices",
        }
    )
    def _handle_list_devices(self, param: Dict[str, Any]) -> int:
        """Handle list_devices action"""
        self.debug_print("Starting list_devices action")
        self.save_progress("Listing all devices")
        return phantom.APP_SUCCESS

    # get_device
    @action_handler(
        {
            "base_endpoint": AUTOMOX_DEVICE_SPECIFIC_ENDPOINT,
            "fetch_function": "_make_rest_call",
            "fetch_function_method": "get",
            "params": {"query_params": ["org_id"], "path_params": ["device_id"]},
            "summary_key": "total_devices",
        }
    )
    def _handle_get_device(self, param: Dict[str, Any]) -> int:
        """Handle get_device action"""
        self.debug_print("Starting get_device action")
        self.save_progress("Getting device by ID")
        return phantom.APP_SUCCESS

    # get_device_by_ip_address
    @action_handler(
        {
            "base_endpoint": AUTOMOX_DEVICE_LIST_ENDPOINT,
            "handler_function": "_handle_get_device_by_ip_address_impl",
            "fetch_function": "_fetch_paginated_data",
            "params": {
                "query_params": ["org_id"],
                "aux_params": ["ip_address"],
            },
            "summary_key": "total_devices",
        }
    )
    def _handle_get_device_by_ip_address(self, param: Dict[str, Any]) -> int:
        """Handle get_device_by_ip_address action"""
        self.debug_print("Starting get_device_by_ip_address action")
        self.save_progress("Getting device by IP address")
        return phantom.APP_SUCCESS

    # get_device_by_hostname
    @action_handler(
        {
            "base_endpoint": AUTOMOX_DEVICE_LIST_ENDPOINT,
            "handler_function": "_handle_get_device_by_hostname_impl",
            "fetch_function": "_fetch_paginated_data",
            "params": {
                "query_params": ["org_id"],
                "aux_params": ["hostname"],
            },
            "summary_key": "total_devices",
        }
    )
    def _handle_get_device_by_hostname(self, param: Dict[str, Any]) -> int:
        """Handle get_device_by_hostname action"""
        self.debug_print("Starting get_device_by_hostname action")
        self.save_progress("Getting device by hostname")
        return phantom.APP_SUCCESS

    # update_device
    @action_handler(
        {
            "base_endpoint": AUTOMOX_DEVICE_SPECIFIC_ENDPOINT,
            "handler_function": "_handle_update_device_impl",
            "fetch_function": "_make_rest_call",
            "fetch_function_method": "put",
            "params": {
                "query_params": ["org_id"],
                "path_params": ["device_id"],
                "aux_params": ["exception", "server_group_id", "tags", "custom_name"],
            },
        }
    )
    def _handle_update_device(self, param: Dict[str, Any]) -> int:
        """Handle update_device action"""
        self.debug_print("Starting update_device action")
        self.save_progress("Updating device")
        return phantom.APP_SUCCESS

    # delete_device
    @action_handler(
        {
            "base_endpoint": AUTOMOX_DEVICE_SPECIFIC_ENDPOINT,
            "fetch_function": "_make_rest_call",
            "fetch_function_method": "delete",
            "params": {
                "query_params": ["org_id"],
                "path_params": ["device_id"],
            },
        }
    )
    def _handle_delete_device(self, param: Dict[str, Any]) -> int:
        """Handle delete_device action"""
        self.debug_print("Starting delete_device action")
        self.save_progress("Deleting device")
        return phantom.APP_SUCCESS

    # get_device_software
    @action_handler(
        {
            "base_endpoint": AUTOMOX_DEVICE_LIST_PACKAGES_ENDPOINT,
            "fetch_function": "_make_rest_call",
            "fetch_function_method": "get",
            "params": {
                "query_params": ["org_id"],
                "path_params": ["device_id"],
            },
        }
    )
    def _handle_get_device_software(self, param: Dict[str, Any]) -> int:
        """Handle get_device_software action"""
        self.debug_print("Starting get_device_software action")
        self.save_progress("Getting device software")
        return phantom.APP_SUCCESS

    # list_software
    @action_handler(
        {
            "base_endpoint": AUTOMOX_PACKAGE_LIST_ALL_ENDPOINT,
            "fetch_function": "_fetch_paginated_data",
            "params": {"query_params": ["org_id"], "path_params": ["org_id"]},
            "summary_key": "total_software_packages",
        }
    )
    def _handle_list_software(self, param: Dict[str, Any]) -> int:
        """Handle list_software action"""
        self.debug_print("Starting list_software action")
        self.save_progress("Listing all software")
        return phantom.APP_SUCCESS

    # list_policies
    @action_handler(
        {
            "base_endpoint": AUTOMOX_POLICY_LIST_ENDPOINT,
            "fetch_function": "_fetch_paginated_data",
            "params": {
                "query_params": ["org_id"],
            },
            "summary_key": "total_policies",
        }
    )
    def _handle_list_policies(self, param: Dict[str, Any]) -> int:
        """Handle list_policies action"""
        self.debug_print("Starting list_policies action")
        self.save_progress("Listing all policies")
        return phantom.APP_SUCCESS

    # get_policy
    @action_handler(
        {
            "base_endpoint": AUTOMOX_POLICY_LIST_SPECIFIC_ENDPOINT,
            "fetch_function": "_make_rest_call",
            "fetch_function_method": "get",
            "params": {
                "query_params": ["org_id"],
                "path_params": ["policy_id"],
            },
        }
    )
    def _handle_get_policy(self, param: Dict[str, Any]) -> int:
        """Handle get_policy action"""
        self.debug_print("Starting get_policy action")
        self.save_progress("Getting policy")
        return phantom.APP_SUCCESS

    # run_policy
    @action_handler(
        {
            "base_endpoint": AUTOMOX_POLICY_RUN_ENDPOINT,
            "handler_function": "_handle_run_policy_impl",
            "params": {
                "query_params": ["org_id"],
                "path_params": ["policy_id"],
                "aux_params": ["device_id"],
            },
        }
    )
    def _handle_run_policy(self, param: Dict[str, Any]) -> int:
        """Handle run_policy action"""
        self.debug_print("Starting run_policy action")
        self.save_progress("Running policy")
        return phantom.APP_SUCCESS

    # list_groups
    @action_handler(
        {
            "base_endpoint": AUTOMOX_GROUPS_LIST_ENDPOINT,
            "fetch_function": "_fetch_paginated_data",
            "params": {
                "query_params": ["org_id"],
            },
            "summary_key": "total_groups",
        }
    )
    def _handle_list_groups(self, param: Dict[str, Any]) -> int:
        """Handle list_groups action"""
        self.debug_print("Starting list_groups action")
        self.save_progress("Listing all groups")
        return phantom.APP_SUCCESS

    # get_command_queues
    @action_handler(
        {
            "base_endpoint": AUTOMOX_COMMAND_QUEUE_LIST_ENDPOINT,
            "fetch_function": "_fetch_paginated_data",
            "params": {
                "query_params": ["org_id"],
                "path_params": ["device_id"],
            },
            "summary_key": "total_commands_in_queue",
        }
    )
    def _handle_get_command_queues(self, param: Dict[str, Any]) -> int:
        """Handle get_command_queues action"""
        self.debug_print("Starting get_command_queues action")
        self.save_progress("Getting command queues")
        return phantom.APP_SUCCESS

    def handle_action(self, param: Dict[str, Any]) -> int:
        """
        Main action handler for the connector. This is also where the action mapping/config is defined.

        Args:
            param (dict): Parameters for the action

        Returns:
            int: Action status code (success/failure)
        """
        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()
        self.debug_print("action_id ", action_id)

        if action_id == phantom.ACTION_ID_INGEST_ON_POLL:
            start_time = time.time()
            result = self._on_poll(param)
            end_time = time.time()
            diff_time = end_time - start_time
            human_time = str(timedelta(seconds=int(diff_time)))

            self.save_progress(f"Time taken: {human_time}")

            return result

        action_handler = getattr(self, self.ACTION_MAPPING.get(action_id, ""), None)
        if not action_handler:
            self.debug_print(f"No action handler found for action_id: {action_id}")
            return phantom.APP_ERROR

        return action_handler(param)

    def finalize(self) -> int:
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
    argparser.add_argument(
        "-v",
        "--verify",
        action="store_true",
        help="verify",
        required=False,
        default=False,
    )

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password
    verify = args.verify

    if username and not password:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            print("Accessing the Login page")
            r = requests.get(  # nosemgrep: python.requests.best-practice.use-timeout.use-timeout
                BaseConnector._get_phantom_base_url() + "login", verify=verify
            )
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = BaseConnector._get_phantom_base_url() + "login"

            print("Logging into Platform to get the session id")
            r2 = requests.post(  # nosemgrep: python.requests.best-practice.use-timeout.use-timeout
                BaseConnector._get_phantom_base_url() + "login",
                verify=verify,
                data=data,
                headers=headers,
            )
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print(f"Unable to get session id from the platform. Error: {str(e)}")
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = AutomoxConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)
