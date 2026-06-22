# File: infoblox_nios_dhcp_lease_lookup.py
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

import re

import phantom.app as phantom

import infoblox_nios_consts as consts
from actions import BaseAction


class DhcpLeaseLookupAction(BaseAction):
    """Class to handle DHCP lease lookup action."""

    def _validate_params(self):
        """
        Validate all action parameters comprehensively.

        Returns:
            int: phantom.APP_SUCCESS if all validations pass, phantom.APP_ERROR otherwise
        """
        # Validate IP address format if provided
        ip_address = self._param.get("ip_address")
        if ip_address:
            if not self._connector.validator.validate_ip_address(ip_address):
                return self._action_result.set_status(phantom.APP_ERROR, f"Invalid IP address format: {ip_address}")

        # Validate MAC address format if provided
        hardware = self._param.get("hardware")
        if hardware:
            # Basic MAC address pattern validation (supports various formats)
            mac_patterns = [
                r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",  # xx:xx:xx:xx:xx:xx or xx-xx-xx-xx-xx-xx
                r"^([0-9A-Fa-f]{4}[.]){2}([0-9A-Fa-f]{4})$",  # xxxx.xxxx.xxxx
                r"^([0-9A-Fa-f]{12})$",  # xxxxxxxxxxxx
            ]
            is_valid_mac = any(re.match(pattern, hardware) for pattern in mac_patterns)
            if not is_valid_mac and not hardware.startswith("~"):  # Allow regex patterns starting with ~
                self._connector.debug_print(f"MAC address '{hardware}' may not be in standard format, but allowing as regex search is supported")

        # Validate protocol parameter
        protocol = self._param.get("protocol")
        if protocol and protocol not in [consts.PROTOCOL_BOTH, consts.PROTOCOL_IPV4, consts.PROTOCOL_IPV6]:
            return self._action_result.set_status(
                phantom.APP_ERROR,
                f"Invalid protocol value. Must be one of: {consts.PROTOCOL_BOTH}, {consts.PROTOCOL_IPV4}, {consts.PROTOCOL_IPV6}",
            )

        # Validate limit parameter using common validator
        limit = self._param.get("limit")
        if limit is not None:
            ret_val, _validated_limit = self._connector.validator.validate_integer(
                self._action_result,
                limit,
                "limit",
                allow_zero=False,
                allow_negative=False,
            )
            if phantom.is_fail(ret_val):
                return ret_val

        return phantom.APP_SUCCESS

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.DHCP_LEASE_START_MESSAGE)

    def __build_query_params(self):
        """
        Build query parameters for the API call based on input parameters.

        Returns:
            dict: Query parameters for the API call
        """
        params = {}

        # Set limit
        limit = self._param.get("limit", consts.DEFAULT_LIMIT)
        params["_max_results"] = int(limit)

        # Set return fields
        params["_return_fields"] = consts.DHCP_LEASE_RETURN_FIELDS

        # Add filtering parameters
        ip_address = self._param.get("ip_address")
        if ip_address:
            params["address"] = ip_address

        hardware = self._param.get("hardware")
        if hardware:
            params["hardware"] = hardware

        hostname = self._param.get("hostname")
        if hostname:
            params["client_hostname"] = hostname

        ipv6_duid = self._param.get("ipv6_duid")
        if ipv6_duid:
            params["ipv6_duid"] = ipv6_duid

        protocol = self._param.get("protocol")
        if protocol and protocol != consts.PROTOCOL_BOTH:
            params["protocol"] = protocol

        fingerprint = self._param.get("fingerprint")
        if fingerprint:
            params["fingerprint"] = fingerprint

        username = self._param.get("username")
        if username:
            params["username"] = username

        return params

    def __make_api_call(self):
        """
        Make the REST API call to retrieve DHCP lease information with pagination support.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        # Build query parameters
        params = self.__build_query_params()

        # Get limit parameter (validation already done in _validate_params)
        limit = self._param.get("limit")

        self._connector.debug_print(f"Making paginated API call to {consts.DHCP_LEASE_ENDPOINT} with params: {params}, limit: {limit}")

        # Make the paginated API call
        return self._connector.utils.make_paginated_rest_call(
            endpoint=consts.DHCP_LEASE_ENDPOINT, action_result=self._action_result, params=params, limit=limit
        )

    def __process_response_data(self, results):
        """
        Process the response data to make it more suitable for table display.

        Args:
            results (list): List of DHCP lease records from the API response

        Returns:
            list: Processed list of DHCP lease records
        """
        processed_results = []

        for result in results:
            processed_result = result.copy()

            # Convert timestamp fields to human-readable format if needed
            timestamp_fields = ["cltt", "ends", "starts", "tsfp", "tstp"]
            for field in timestamp_fields:
                if field in processed_result and processed_result.get(field):
                    # Keep the original timestamp but you could add conversion here if needed
                    # For now, keeping the raw timestamp for consistency with MD file output
                    pass

            # Handle boolean fields to ensure they display properly
            boolean_fields = ["never_ends", "never_starts", "is_invalid_mac"]
            for field in boolean_fields:
                if field in processed_result:
                    processed_result[field] = bool(processed_result.get(field, False))

            # Ensure string fields are properly handled
            string_fields = ["hardware", "client_hostname", "fingerprint", "protocol", "network", "uid", "variable"]
            for field in string_fields:
                if field in processed_result and processed_result[field] is None:
                    processed_result[field] = ""

            processed_results.append(processed_result)

        return processed_results

    def __handle_response(self, response):
        """
        Handle the API response and process the results.

        Args:
            response (list): The API response containing DHCP lease records

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        if not isinstance(response, list):
            return self._action_result.set_status(phantom.APP_ERROR, f"Unexpected response format. Expected list, got {type(response)}")

        total_count = len(response)
        self._connector.debug_print(f"Processing {total_count} DHCP lease records")

        # Process the response data
        processed_results = self.__process_response_data(response)

        # Add processed data to action result
        for result in processed_results:
            self._action_result.add_data(result)

        # Generate summary with applied filters information
        applied_filters = []

        ip_address = self._param.get("ip_address")
        if ip_address:
            applied_filters.append(f"IP Address: {ip_address}")

        hardware = self._param.get("hardware")
        if hardware:
            applied_filters.append(f"Hardware: {hardware}")

        hostname = self._param.get("hostname")
        if hostname:
            applied_filters.append(f"Hostname: {hostname}")

        ipv6_duid = self._param.get("ipv6_duid")
        if ipv6_duid:
            applied_filters.append(f"IPv6 DUID: {ipv6_duid}")

        protocol = self._param.get("protocol")
        if protocol and protocol != consts.PROTOCOL_BOTH:
            applied_filters.append(f"Protocol: {protocol}")

        fingerprint = self._param.get("fingerprint")
        if fingerprint:
            applied_filters.append(f"Fingerprint: {fingerprint}")

        username = self._param.get("username")
        if username:
            applied_filters.append(f"Username: {username}")

        summary = {"total_lease_records": total_count, "filters_applied": "; ".join(applied_filters) if applied_filters else "None"}

        self._action_result.update_summary(summary)
        message = consts.DHCP_LEASE_SUCCESS_MESSAGE.format(total_count)
        return self._action_result.set_status(phantom.APP_SUCCESS, message)

    def execute(self):
        """
        Execute DHCP lease lookup action following the 6-step modular approach.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make REST call to get DHCP lease information
        Step 4: Handle response
        Step 5: Return results

        Returns:
            int: phantom.APP_SUCCESS or phantom.APP_ERROR
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters
        ret_val = self._validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 3: Make REST call to get DHCP lease information
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 4: Handle response
        ret_val = self.__handle_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 5: Return results
        return phantom.APP_SUCCESS
