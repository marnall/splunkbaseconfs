# File: infoblox_nios_list_network_info.py
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


class ListNetworkInfoAction(BaseAction):
    """Class to handle list network info action.

    Lists defined IPv4/IPv6 networks and subnets in IPAM.
    """

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("List Network Info"))

    def _validate_params(self):
        """
        Validate action parameters for format/content.
        Note: Required parameter validation is handled by SOAR's built-in JSON schema validation.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        # Validate limit parameter
        limit = self._param.get("limit")
        if limit is not None:
            ret_val, limit = self._connector.validator.validate_integer(
                self._action_result,
                limit,
                "limit",
                allow_zero=False,
                allow_negative=False,
            )
            if phantom.is_fail(ret_val):
                return ret_val

        # Validate network parameter if provided (must be in CIDR notation)
        network = self._param.get("network")
        if network:
            try:
                # Use ipaddress module to validate CIDR notation
                ipaddress.ip_network(network, strict=False)
            except ValueError as e:
                return self._action_result.set_status(
                    phantom.APP_ERROR, f"Invalid network format: {e!s}. Network must be in CIDR notation (e.g., '192.168.1.0/24')"
                )

        return phantom.APP_SUCCESS

    def __make_api_call(self):
        """
        Make the API call to retrieve network records.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        # Build query parameters
        params = self.__build_query_params()

        # Get endpoint and limit
        limit = self._param.get("limit", consts.LIST_NETWORK_INFO_DEFAULT_LIMIT)

        self._connector.debug_print(f"Query parameters: {params}")

        # Make the paginated API call
        return self._connector.utils.make_paginated_rest_call(
            endpoint=consts.LIST_NETWORK_INFO_ENDPOINT, action_result=self._action_result, params=params, limit=limit
        )

    def __build_query_params(self):
        """
        Build query parameters for the API call based on input parameters.

        Returns:
            dict: Query parameters for the API call
        """
        params = {}

        # Add return fields to get all necessary information
        params["_return_fields"] = consts.LIST_NETWORK_INFO_RETURN_FIELDS

        # Add search criteria based on provided parameters
        network = self._param.get("network")
        if network:
            params["network"] = network

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

    def __handle_response(self, response):
        """
        Handle the API response and process the network records data.

        Args:
            response (list): The API response containing network records

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        # Validate response structure
        if not isinstance(response, list):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: expected JSON array")

        self._connector.debug_print("Processing network records response")
        total_records = len(response)

        # Process the response data
        processed_records = self.__process_response_data(response)

        # Add processed records to action results
        for record in processed_records:
            self._action_result.add_data(record)

        # Extract applied filters for summary
        network = self._param.get("network", "")
        extended_attributes = self._param.get("extended_attributes", "")
        limit = self._param.get("limit", consts.LIST_NETWORK_INFO_DEFAULT_LIMIT)

        # Generate comprehensive summary
        summary = {
            "total_objects": total_records,
            "total_objects_successful": total_records,
            "limit": limit,
            "network_filter_applied": bool(network),
            "extended_attributes_filter_applied": bool(extended_attributes),
        }

        self._action_result.update_summary(summary)

        # Generate success message
        success_message = consts.LIST_NETWORK_INFO_SUCCESS_MESSAGE.format(count=total_records)

        return self._action_result.set_status(phantom.APP_SUCCESS, success_message)

    def __process_response_data(self, results):
        """
        Process the response data to make it more suitable for table display.

        Args:
            results (list): List of network records from the API response

        Returns:
            list: Processed list of network records
        """
        processed_records = []

        for network_record in results:
            if not isinstance(network_record, dict):
                continue

            # Create a processed copy for display purposes
            processed_record = dict(network_record)

            # Process extended attributes for display
            extattrs = network_record.get("extattrs", {})
            if isinstance(extattrs, dict) and extattrs:
                extattr_display = []
                for key, value_obj in extattrs.items():
                    if isinstance(value_obj, dict) and "value" in value_obj:
                        extattr_display.append(f"{key}={value_obj['value']}")
                    else:
                        extattr_display.append(f"{key}={value_obj!s}")
                processed_record["extattrs_display"] = ", ".join(extattr_display)
            else:
                processed_record["extattrs_display"] = ""

            # Process members array for display (if present)
            members = network_record.get("members", [])
            if isinstance(members, list) and members:
                member_display = []
                for member in members:
                    if isinstance(member, dict):
                        member_name = member.get("name", "")
                        member_ipv4 = member.get("ipv4addr", "")
                        member_ipv6 = member.get("ipv6addr", "")
                        if member_name:
                            display_str = member_name
                            if member_ipv4:
                                display_str += f" ({member_ipv4})"
                            elif member_ipv6:
                                display_str += f" ({member_ipv6})"
                            member_display.append(display_str)
                processed_record["members_display"] = ", ".join(member_display)
            else:
                processed_record["members_display"] = ""

            # Process options array for display (if present)
            options = network_record.get("options", [])
            if isinstance(options, list) and options:
                options_display = []
                for option in options:
                    if isinstance(option, dict):
                        option_name = option.get("name", "")
                        option_num = option.get("num", "")
                        option_value = option.get("value", "")
                        if option_name or option_num:
                            display_str = option_name or f"Option {option_num}"
                            if option_value:
                                display_str += f"={option_value}"
                            options_display.append(display_str)
                processed_record["options_display"] = ", ".join(options_display)
            else:
                processed_record["options_display"] = ""

            # Add the processed record to results list
            processed_records.append(processed_record)

        return processed_records

    def execute(self):
        """
        Execute list network info action following the modular approach.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make API call
        Step 4: Handle response
        Step 5: Return results

        Returns:
            int: phantom.APP_SUCCESS on successful execution, phantom.APP_ERROR otherwise
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters (format/content only, required validation handled by SOAR)
        self._connector.save_progress("Validating parameters")
        ret_val = self._validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 3: Make API call
        self._connector.save_progress("Retrieving network records")
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 4: Handle response
        ret_val = self.__handle_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 5: Return results
        self._connector.save_progress("Network records retrieved successfully")
        return phantom.APP_SUCCESS
