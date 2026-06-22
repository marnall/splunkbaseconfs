# File: infoblox_nios_ip_lookup.py
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

import phantom.app as phantom

import infoblox_nios_consts as consts
from actions import BaseAction


class IpLookupAction(BaseAction):
    """Class to handle IP lookup action."""

    def _validate_params(self):
        """
        Validate all action parameters comprehensively.

        Returns:
            int: phantom.APP_SUCCESS if all validations pass, phantom.APP_ERROR otherwise
        """
        # Check parameter combinations - only one group can be specified at a time
        ip_address = self._param.get("ip_address")
        network = self._param.get("network")
        from_ip = self._param.get("from_ip")
        to_ip = self._param.get("to_ip")

        # Count how many parameter groups are specified
        groups_specified = 0
        if ip_address:
            groups_specified += 1
        if network:
            groups_specified += 1
        if from_ip or to_ip:
            groups_specified += 1

        if groups_specified == 0:
            return self._action_result.set_status(
                phantom.APP_ERROR, "At least one parameter group must be specified: ip_address, network, or from_ip/to_ip range"
            )

        if groups_specified > 1:
            return self._action_result.set_status(
                phantom.APP_ERROR, "Only one parameter group can be specified at a time: ip_address, network, or from_ip/to_ip range"
            )

        # Validate IP range parameters - both must be provided together
        if (from_ip and not to_ip) or (to_ip and not from_ip):
            return self._action_result.set_status(phantom.APP_ERROR, "Both from_ip and to_ip must be provided together for IP range queries")

        # Validate IP address format
        if ip_address:
            if not self._connector.validator.validate_ip_address(ip_address):
                return self._action_result.set_status(phantom.APP_ERROR, f"Invalid IP address format: {ip_address}")

        # Validate network format
        if network:
            try:
                ipaddress.ip_network(network, strict=False)
            except ValueError:
                return self._action_result.set_status(phantom.APP_ERROR, f"Invalid network format: {network}. Expected format: 192.168.1.0/24")

        # Validate IP range format
        if from_ip and to_ip:
            try:
                from_ip_obj = ipaddress.ip_address(from_ip)
                to_ip_obj = ipaddress.ip_address(to_ip)

                # Check that both IPs are the same version (both IPv4 or both IPv6)
                if from_ip_obj.version != to_ip_obj.version:
                    return self._action_result.set_status(
                        phantom.APP_ERROR, f"from_ip and to_ip must be the same IP version (both IPv4 or both IPv6)"
                    )

                # Check that from_ip is less than or equal to to_ip
                if from_ip_obj > to_ip_obj:
                    return self._action_result.set_status(
                        phantom.APP_ERROR, f"from_ip ({from_ip}) must be less than or equal to to_ip ({to_ip})"
                    )

            except ValueError as e:
                return self._action_result.set_status(phantom.APP_ERROR, f"Invalid IP address in range: {e!s}")

        # Validate status parameter
        status = self._param.get("status")
        if status and status not in consts.IP_LOOKUP_STATUS_VALUES:
            return self._action_result.set_status(
                phantom.APP_ERROR, f"Invalid status value. Must be one of: {', '.join(consts.IP_LOOKUP_STATUS_VALUES)}"
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
        self._connector.save_progress(consts.IP_LOOKUP_START_MESSAGE)

    def __determine_ip_version_and_endpoint(self):
        """
        Determine the IP version and corresponding API endpoint.

        Returns:
            tuple: (ip_version, endpoint) where ip_version is 4 or 6, and endpoint is the API path
        """
        ip_address = self._param.get("ip_address")
        from_ip = self._param.get("from_ip")
        network = self._param.get("network")

        # Determine IP version from the provided parameters
        try:
            if ip_address:
                ip_obj = ipaddress.ip_address(ip_address)
                ip_version = ip_obj.version
            elif from_ip:
                ip_obj = ipaddress.ip_address(from_ip)
                ip_version = ip_obj.version
            elif network:
                net_obj = ipaddress.ip_network(network, strict=False)
                ip_version = net_obj.version
            else:
                # Default to IPv4 if no IP parameters provided
                ip_version = 4

        except ValueError:
            # Default to IPv4 if parsing fails
            ip_version = 4

        if ip_version == 6:
            return 6, consts.IP_LOOKUP_ENDPOINT_IPV6
        else:
            return 4, consts.IP_LOOKUP_ENDPOINT_IPV4

    def __build_query_params(self, ip_version):
        """
        Build query parameters for the API call based on IP version and input parameters.

        Args:
            ip_version (int): IP version (4 or 6)

        Returns:
            dict: Query parameters for the API call
        """
        params = {}

        # Set return fields based on IP version
        if ip_version == 6:
            params["_return_fields"] = consts.IPV6_RETURN_FIELDS
        else:
            params["_return_fields"] = consts.IPV4_RETURN_FIELDS

        # Set limit
        limit = self._param.get("limit", consts.DEFAULT_LIMIT)
        params["_max_results"] = int(limit)

        # Add IP-specific parameters
        ip_address = self._param.get("ip_address")
        network = self._param.get("network")
        from_ip = self._param.get("from_ip")
        to_ip = self._param.get("to_ip")

        if ip_address:
            params["ip_address"] = ip_address
        elif network:
            params["network"] = network
        elif from_ip and to_ip:
            params["ip_address>"] = from_ip
            params["ip_address<"] = to_ip

        # Add status parameter if provided
        status = self._param.get("status")
        if status:
            params["status"] = status

        # Add extended attributes filter if provided
        extended_attributes = self._param.get("extended_attributes")
        if extended_attributes:
            # Parse comma-separated key=value pairs
            for attr_pair in extended_attributes.split(","):
                attr_pair = attr_pair.strip()
                if "=" in attr_pair:
                    key, value = attr_pair.split("=", 1)
                    params[f"*{key.strip()}"] = value.strip()

        return params

    def __make_api_call(self):
        """
        Make the REST API call to retrieve IP information with pagination support.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        # Determine IP version and endpoint
        ip_version, endpoint = self.__determine_ip_version_and_endpoint()

        # Build query parameters
        params = self.__build_query_params(ip_version)

        # Get limit parameter (validation already done in _validate_params)
        limit = self._param.get("limit")

        self._connector.debug_print(f"Making paginated API call to {endpoint} with params: {params}, limit: {limit}")

        # Use paginated REST call from utils to fetch all results
        ret_val, results = self._connector.utils.make_paginated_rest_call(
            endpoint=endpoint, action_result=self._action_result, params=params, limit=limit
        )

        if phantom.is_fail(ret_val):
            # Pagination failed, return error
            return ret_val, None

        # Return success with paginated results
        return phantom.APP_SUCCESS, results

    def __process_response_data(self, results):
        """
        Process the response data to make it more suitable for table display.

        Args:
            results (list): List of IP address records from the API response

        Returns:
            list: Processed list of IP address records
        """
        processed_results = []

        for result in results:
            processed_result = result.copy()

            # Convert list fields to comma-separated strings for better table display
            list_fields = ["types", "names", "usage", "conflict_types"]
            for field in list_fields:
                if field in processed_result and isinstance(processed_result[field], list):
                    processed_result[field] = ", ".join(str(item) for item in processed_result[field]) if processed_result[field] else ""

            # Handle MAC Address/DUID consolidation - combine mac_address and duid into a single field
            # For IPv4: use mac_address, for IPv6: use duid
            mac_duid_value = ""
            if processed_result.get("mac_address"):
                mac_duid_value = processed_result["mac_address"]
            elif processed_result.get("duid"):
                mac_duid_value = processed_result["duid"]

            # Set the consolidated field that will be used for display
            processed_result["mac_address_duid"] = mac_duid_value

            # Handle extended attributes - convert to readable format
            if processed_result.get("extattrs"):
                extattrs_list = []
                for key, value_obj in processed_result["extattrs"].items():
                    if isinstance(value_obj, dict) and "value" in value_obj:
                        extattrs_list.append(f"{key}={value_obj['value']}")
                    else:
                        extattrs_list.append(f"{key}={value_obj!s}")
                processed_result["extattrs"] = "; ".join(extattrs_list)
            else:
                processed_result["extattrs"] = ""

            processed_results.append(processed_result)

        return processed_results

    def __handle_response(self, response):
        """
        Handle the API response and process the results.

        Args:
            response (list): The API response containing IP address records

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        if not isinstance(response, list):
            return self._action_result.set_status(phantom.APP_ERROR, f"Unexpected response format. Expected list, got {type(response)}")

        total_count = len(response)
        self._connector.debug_print(f"Processing {total_count} IP address records")

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

        network = self._param.get("network")
        if network:
            applied_filters.append(f"Network: {network}")

        from_ip = self._param.get("from_ip")
        to_ip = self._param.get("to_ip")
        if from_ip and to_ip:
            applied_filters.append(f"IP Range: {from_ip} - {to_ip}")

        status = self._param.get("status")
        if status:
            applied_filters.append(f"Status: {status}")

        extended_attributes = self._param.get("extended_attributes")
        if extended_attributes:
            applied_filters.append(f"Extended Attributes: {extended_attributes}")

        summary = {"total_ip_records": total_count, "filters_applied": "; ".join(applied_filters) if applied_filters else "None"}

        self._action_result.update_summary(summary)
        message = consts.IP_LOOKUP_SUCCESS_MESSAGE.format(total_count)
        return self._action_result.set_status(phantom.APP_SUCCESS, message)

    def execute(self):
        """
        Execute IP lookup action following the 6-step modular approach.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make REST call to get IP information
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

        # Step 3: Make REST call to get IP information
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 4: Handle response
        ret_val = self.__handle_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 5: Return results
        return phantom.APP_SUCCESS
