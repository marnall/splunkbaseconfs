# File: infoblox_nios_list_host_info.py
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

import phantom.app as phantom

import infoblox_nios_consts as consts
from actions import BaseAction


class ListHostInfoAction(BaseAction):
    """Class to handle list host info action.

    This action retrieves host records from Infoblox including hostname, associated IPv4/IPv6 addresses
    (A/AAAA records), PTR records, DNS view information, and any configured extensible attributes.
    """

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("List Host Info"))

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

        # Validate IPv4 address parameter if provided
        ipv4_address = self._param.get("ipv4_address")
        if ipv4_address:
            if not self._connector.validator.validate_ip_address(ipv4_address):
                return self._action_result.set_status(phantom.APP_ERROR, f"Invalid IP address format: {ipv4_address}")

        # Validate IPv6 address parameter if provided
        ipv6_address = self._param.get("ipv6_address")
        if ipv6_address:
            if not self._connector.validator.validate_ip_address(ipv6_address):
                return self._action_result.set_status(phantom.APP_ERROR, f"Invalid IP address format: {ipv6_address}")

        return phantom.APP_SUCCESS

    def __build_query_params(self):
        """
        Build query parameters for the API call based on input parameters.

        Returns:
            dict: Query parameters for the API call
        """
        params = {}

        # Add return fields to get all necessary information
        params["_return_fields"] = consts.LIST_HOST_INFO_RETURN_FIELDS

        # Add search criteria based on provided parameters
        name = self._param.get("name")
        if name:
            params["name"] = name

        ipv4_address = self._param.get("ipv4_address")
        if ipv4_address:
            params["ipv4addr"] = ipv4_address

        ipv6_address = self._param.get("ipv6_address")
        if ipv6_address:
            params["ipv6addr"] = ipv6_address

        # Add extended attributes filter if provided
        extended_attributes = self._param.get("extended_attributes")
        if extended_attributes:
            # Parse comma-separated key=value pairs
            for attr_pair in extended_attributes.split(","):
                attr_pair = attr_pair.strip()
                if "=" in attr_pair:
                    key, value = attr_pair.split("=", 1)
                    params[f"*{key.strip()}"] = value.strip()

        # Add limit parameter
        limit = self._param.get("limit", consts.LIST_HOST_INFO_DEFAULT_LIMIT)
        params["_max_results"] = limit

        return params, None

    def __make_api_call(self):
        """
        Make the API call to retrieve host records.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        # Build query parameters using the dedicated method
        params, error_msg = self.__build_query_params()
        if params is None:
            return self._action_result.set_status(phantom.APP_ERROR, error_msg), None

        # Get limit for API call
        limit = self._param.get("limit", consts.LIST_HOST_INFO_DEFAULT_LIMIT)

        # Make the GET API call
        endpoint = consts.LIST_HOST_INFO_ENDPOINT
        self._connector.debug_print(f"Query parameters: {params}")

        return self._connector.utils.make_paginated_rest_call(endpoint=endpoint, action_result=self._action_result, params=params, limit=limit)

    def __handle_response(self, response):
        """
        Handle the API response and process the host records data.
        Uses .get() method for safe dictionary access to avoid KeyError exceptions.

        Args:
            response (list): The API response containing host records

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        # Validate response structure using .get() for safe access
        if not isinstance(response, list):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: expected JSON array")

        self._connector.debug_print("Processing host records response")
        total_records = len(response)
        self._connector.debug_print(f"response : {response}")
        # Process the response data
        processed_records = self.__process_response_data(response)

        # Add the processed records to results
        for record in processed_records:
            self._action_result.add_data(record)
        self._connector.debug_print(f"processed_records : {processed_records}")
        # Extract applied filters for summary
        name = self._param.get("name", "")
        ipv4_address = self._param.get("ipv4_address", "")
        ipv6_address = self._param.get("ipv6_address", "")
        extended_attributes = self._param.get("extended_attributes", "")
        limit = self._param.get("limit", consts.LIST_HOST_INFO_DEFAULT_LIMIT)

        # Generate comprehensive summary
        summary = {
            "total_objects": total_records,
            "total_objects_successful": total_records,
            "limit": limit,
            "name_filter_applied": bool(name),
            "ipv4_filter_applied": bool(ipv4_address),
            "ipv6_filter_applied": bool(ipv6_address),
            "extended_attributes_filter_applied": bool(extended_attributes),
        }

        self._action_result.update_summary(summary)

        # Generate success message
        success_message = consts.LIST_HOST_INFO_SUCCESS_MESSAGE.format(count=total_records)

        return self._action_result.set_status(phantom.APP_SUCCESS, success_message)

    def __process_response_data(self, response):
        """
        Process the response data to make it more suitable for table display.

        Args:
            response (list): List of host records from the API response

        Returns:
            list: Processed list of host records with display-friendly fields
        """
        processed_records = []

        # Process each host record in the response
        for host_record in response:
            if not isinstance(host_record, dict):
                continue

            # Create a processed copy for display purposes
            processed_record = dict(host_record)

            # Process IPv4 addresses for display
            ipv4addrs = host_record.get("ipv4addrs", [])
            if isinstance(ipv4addrs, list) and ipv4addrs:
                ipv4_display = []
                for addr in ipv4addrs:
                    if isinstance(addr, dict) and addr.get("ipv4addr"):
                        ipv4_display.append(addr["ipv4addr"])
                processed_record["ipv4addrs_display"] = ", ".join(ipv4_display)
            else:
                processed_record["ipv4addrs_display"] = ""

            # Process IPv6 addresses for display
            ipv6addrs = host_record.get("ipv6addrs", [])
            if isinstance(ipv6addrs, list) and ipv6addrs:
                ipv6_display = []
                for addr in ipv6addrs:
                    if isinstance(addr, dict) and addr.get("ipv6addr"):
                        ipv6_display.append(addr["ipv6addr"])
                processed_record["ipv6addrs_display"] = ", ".join(ipv6_display)
            else:
                processed_record["ipv6addrs_display"] = ""

            # Process extended attributes for display
            extattrs = host_record.get("extattrs", {})
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

            # Only append valid records with content to avoid None entries
            if processed_record:
                processed_records.append(processed_record)

        return processed_records

    def execute(self):
        """
        Execute list host info action following the modular approach.

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
        self._connector.save_progress("Retrieving host records")
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 4: Handle response
        ret_val = self.__handle_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 5: Return results
        self._connector.save_progress("Host records retrieved successfully")
        return phantom.APP_SUCCESS
