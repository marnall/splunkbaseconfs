# File: infoblox_nios_create_host_record.py
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

import json
import re

import phantom.app as phantom

import infoblox_nios_consts as consts
from actions import BaseAction
from infoblox_nios_utils import Validator


class CreateHostRecordAction(BaseAction):
    """Create Host Record action."""

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.CREATE_HOST_RECORD_START_MESSAGE)
        name = self._param.get("name", "")
        self._connector.save_progress(consts.CREATE_HOST_RECORD_PROGRESS_MESSAGE.format(name=name))

    def __validate_parameters(self):
        """Validate input parameters.

        :return: tuple: (status, error_message) - Status code and error message if any
        """
        # Initialize validator instance
        validator = Validator()

        # Validate IPv4 and IPv6 addresses
        ipv4_addresses = self._param.get("ipv4_addresses", "")
        ipv6_addresses = self._param.get("ipv6_addresses", "")

        # Check if at least one IP address is provided
        if not ipv4_addresses and not ipv6_addresses:
            return phantom.APP_ERROR, consts.ERROR_HOST_RECORD_MISSING_IP

        # Validate IPv4 addresses if provided
        if ipv4_addresses:
            try:
                ipv4_list = json.loads(ipv4_addresses)

                # Validate each IPv4 address
                for item in ipv4_list:
                    # Check if ipv4addr is present
                    if "ipv4addr" not in item:
                        return phantom.APP_ERROR, "Missing 'ipv4addr' field in IPv4 address object"

                    # Validate IPv4 format
                    ipv4 = item["ipv4addr"]
                    # Use existing validator instead of regex pattern
                    if not validator.validate_ip_address(ipv4):
                        return phantom.APP_ERROR, consts.ERROR_HOST_RECORD_INVALID_IPV4.format(ipv4=ipv4)

                    # Validate MAC address if provided
                    if "mac" in item:
                        mac = item["mac"]
                        mac_pattern = r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
                        if not re.match(mac_pattern, mac):
                            return phantom.APP_ERROR, consts.ERROR_HOST_RECORD_INVALID_MAC.format(mac=mac)

                self._ipv4_list = ipv4_list
            except json.JSONDecodeError:
                return phantom.APP_ERROR, consts.ERROR_HOST_RECORD_INVALID_JSON.format(field="IPv4 Addresses")
        else:
            self._ipv4_list = []

        # Validate IPv6 addresses if provided
        if ipv6_addresses:
            try:
                ipv6_list = json.loads(ipv6_addresses)

                # Validate each IPv6 address
                for item in ipv6_list:
                    # Check if ipv6addr is present
                    if "ipv6addr" not in item:
                        return phantom.APP_ERROR, "Missing 'ipv6addr' field in IPv6 address object"

                    # Validate IPv6 format using existing validator
                    ipv6 = item["ipv6addr"]
                    if not validator.validate_ip_address(ipv6):
                        return phantom.APP_ERROR, consts.ERROR_HOST_RECORD_INVALID_IPV6.format(ipv6=ipv6)

                self._ipv6_list = ipv6_list
            except json.JSONDecodeError:
                return phantom.APP_ERROR, consts.ERROR_HOST_RECORD_INVALID_JSON.format(field="IPv6 Addresses")
        else:
            self._ipv6_list = []

        # Parse extended attributes if provided
        extended_attributes = self._param.get("extended_attributes", "")
        if extended_attributes:
            try:
                self._extattrs = self.__parse_extended_attributes(extended_attributes)
            except Exception as e:
                return phantom.APP_ERROR, f"{consts.ERROR_HOST_RECORD_INVALID_EXTATTRS}: {e!s}"
        else:
            self._extattrs = {}

        # Parse aliases if provided
        aliases = self._param.get("aliases", "")
        if aliases:
            self._aliases = [alias.strip() for alias in aliases.split(",")]
        else:
            self._aliases = []

        # Parse additional parameters if provided
        additional_params = self._param.get("additional_parameters", "")
        if additional_params:
            try:
                self._additional_params = json.loads(additional_params)
            except json.JSONDecodeError:
                return phantom.APP_ERROR, consts.ERROR_HOST_RECORD_INVALID_JSON.format(field="Additional Parameters")
        else:
            self._additional_params = {}

        return phantom.APP_SUCCESS, None

    def __parse_extended_attributes(self, extended_attributes):
        """Parse extended attributes from comma-separated key=value format.

        :param extended_attributes: String of comma-separated key=value pairs
        :return: Dictionary of extended attributes in Infoblox format
        """
        extattrs = {}

        # Split by comma, but not within quotes
        items = re.findall(r"([^,]+)(?:,|$)", extended_attributes)

        for item in items:
            # Split by first equals sign
            parts = item.strip().split("=", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid format in '{item}'. Expected 'key=value'")

            key = parts[0].strip()
            value = parts[1].strip()

            # Add to extattrs in Infoblox format
            extattrs[key] = {"value": value}

        return extattrs

    def __prepare_payload(self):
        """Prepare the payload for the API request.

        :return: Dictionary containing the payload
        """
        payload = {"name": self._param["name"], "ipv4addrs": self._ipv4_list, "ipv6addrs": self._ipv6_list}

        # Add optional parameters
        if self._aliases:
            payload["aliases"] = self._aliases

        if self._extattrs:
            payload["extattrs"] = self._extattrs

        # Add view if provided
        view = self._param.get("view")
        if view:
            payload["view"] = view

        # Add comment if provided
        comment = self._param.get("comment")
        if comment:
            payload["comment"] = comment

        # Add configure_for_dns if provided
        configure_for_dns = self._param.get("configure_for_dns")
        if configure_for_dns is not None:
            payload["configure_for_dns"] = configure_for_dns

        # Add additional parameters
        payload.update(self._additional_params)

        return payload

    def __make_api_call(self):
        """Make the REST API call to create the host record.

        :return: tuple: (status, response) - Status code and API response
        """
        # Prepare payload
        payload = self.__prepare_payload()

        # Make POST API call
        return self._connector.utils.make_rest_call(
            consts.CREATE_HOST_RECORD_ENDPOINT,
            self._action_result,
            method="post",
            data=payload,
            params={"_return_fields": consts.HOST_RECORD_RETURN_FIELDS},
        )

    def __handle_response(self, response):
        """Handle the API response for create host record.

        :param response: The API response
        :return: status (success/failure)
        """
        # Add the host record data to the action result
        self._action_result.add_data(response)

        # Set summary
        summary = self._action_result.update_summary({})
        summary["reference_id"] = response.get("_ref", "")
        summary["name"] = response.get("name", "")
        summary["view"] = response.get("view", "")
        summary["total_objects"] = 1
        summary["total_objects_successful"] = 1

        return self._action_result.set_status(
            phantom.APP_SUCCESS, consts.CREATE_HOST_RECORD_SUCCESS_MESSAGE.format(reference_id=response.get("_ref", ""))
        )

    def execute(self):
        """Execute the create host record action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make API call to create the host record
        Step 4: Handle the response

        :return: status (success/failure)
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters
        status, error_message = self.__validate_parameters()
        if phantom.is_fail(status):
            self._connector.save_progress(error_message)
            return self._action_result.set_status(phantom.APP_ERROR, error_message)

        # Step 3: Make API call to create the host record
        status, response = self.__make_api_call()

        if phantom.is_fail(status):
            error_message = self._action_result.get_message() or consts.ERROR_CREATE_HOST_RECORD
            self._connector.save_progress(error_message)
            return self._action_result.set_status(phantom.APP_ERROR, error_message)

        # Step 4: Handle the response
        return self.__handle_response(response)
