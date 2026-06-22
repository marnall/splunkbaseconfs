# File: infoblox_get_soc_insights_assets.py
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

import infoblox_consts as consts
from actions import BaseAction


class GetSOCInsightsAssets(BaseAction):
    """Class to handle get SOC insights assets action.

    This action retrieves assets associated with a specific Insight ID from Infoblox BloxOne.
    """

    def _validate_params(self):
        """Validate the parameters for the get SOC insights assets action.

        Checks that parameters are of the correct type and format.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        self._connector.debug_print("Validating parameters for get SOC insights assets action")

        # Validate asset_ip if provided - use the utility method from InfobloxUtils
        asset_ip = self._param.get("asset_ip")
        if asset_ip:
            self._connector.debug_print(f"Validating asset_ip parameter: {asset_ip}")
            if not self._connector.validator.validate_ip_address(asset_ip):
                self._connector.debug_print(f"IP validation failed for: {asset_ip}")
                return self._action_result.set_status(phantom.APP_ERROR, f"Invalid IP address format: {asset_ip}")
            self._connector.debug_print(f"IP validation successful for: {asset_ip}")

        # Validate mac_address if provided - use the utility method from InfobloxUtils
        mac_address = self._param.get("mac_address")
        if mac_address:
            self._connector.debug_print(f"Validating mac_address parameter: {mac_address}")
            if not self._connector.validator.validate_mac_address(mac_address):
                self._connector.debug_print(f"MAC address validation failed for: {mac_address}")
                return self._action_result.set_status(
                    phantom.APP_ERROR, f"Invalid MAC address format: {mac_address}. Expected format: AA:BB:CC:DD:EE:FF"
                )
            self._connector.debug_print(f"MAC address validation successful for: {mac_address}")

        # Validate limit if provided (must be a positive integer)
        limit = self._param.get("limit")
        if limit is not None:
            self._connector.debug_print(f"Validating limit parameter: {limit}")
            ret_val, limit = self._connector.validator.validate_integer(
                self._action_result, limit, "limit", allow_zero=False, allow_negative=False
            )
            if phantom.is_fail(ret_val):
                self._connector.debug_print(f"Limit validation failed: {self._action_result.get_message()}")
                return ret_val
            self._connector.debug_print(f"Limit validation successful: {limit}")

        # Validate 'from' and 'to' date format if provided
        from_date = self._param.get("from")
        if from_date:
            if not self._connector.validator.validate_datetime_format(from_date):
                self._connector.debug_print("From date format validation failed")
                return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_DATETIME_FORMAT.format(key="from"))
            self._connector.debug_print(f"From date validation successful: {from_date}")

        to_date = self._param.get("to")
        if to_date:
            if not self._connector.validator.validate_datetime_format(to_date):
                self._connector.debug_print("To date format validation failed")
                return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_DATETIME_FORMAT.format(key="to"))
            self._connector.debug_print(f"To date validation successful: {to_date}")

        self._connector.debug_print("Parameter validation completed successfully")
        return phantom.APP_SUCCESS

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Get SOC insights assets"))

    def __build_endpoint_and_params(self):
        """Build the endpoint and query parameters for the API call.

        Returns:
            tuple: (endpoint, params)
        """
        insight_id = self._param["insight_id"]
        asset_ip = self._param.get("asset_ip")
        mac_address = self._param.get("mac_address")
        os_version = self._param.get("os_version")
        user = self._param.get("user")
        limit = self._param.get("limit", 100)
        from_date = self._param.get("from")
        to_date = self._param.get("to")

        # Build the endpoint with the insight ID
        endpoint = f"{consts.SOC_INSIGHTS_ENDPOINT}/{insight_id}/assets"

        # Build the query parameters
        params = {}
        if asset_ip:
            params["qip"] = asset_ip
        if mac_address:
            params["cmac"] = mac_address
        if os_version:
            params["os_version"] = os_version
        if user:
            params["user"] = user
        if limit:
            params["limit"] = limit
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        self._connector.debug_print(f"Using endpoint: {endpoint} with params: {params}")

        return endpoint, params

    def __make_api_call(self, endpoint, params):
        """Make the API call to retrieve SOC insights assets.

        Args:
            endpoint (str): The API endpoint to call
            params (dict): The query parameters to include

        Returns:
            tuple: (status, response) - Status code and API response
        """
        self._connector.debug_print(f"Making API call to {endpoint} with params {params}")
        return self._connector.util.make_rest_call(endpoint=endpoint, action_result=self._action_result, method="get", params=params)

    def __process_response(self, response):
        """Process the API response and update action result.

        Args:
            response (dict): The API response to process

        Returns:
            int: phantom.APP_SUCCESS on successful processing
        """
        self._connector.debug_print(f"Processing response: {response}")

        # Extract assets from the response
        assets = []
        if isinstance(response, dict) and "assets" in response:
            assets = response.get("assets", [])
            self._connector.debug_print(f"Found {len(assets)} assets in the response")
        else:
            self._connector.debug_print("Response does not contain 'assets' key")
            # If for some reason the response format changes, try to handle it gracefully
            if isinstance(response, list):
                assets = response
            else:
                assets = [response] if response else []

        # Add each asset to the action result
        for asset in assets:
            self._action_result.add_data(asset)

        # Create summary
        total_assets = len(assets)
        summary = {"total_assets": total_assets}
        self._connector.debug_print(f"Total assets found: {total_assets}")

        # Set appropriate message based on asset count
        if total_assets == 1:
            message = consts.SUCCESS_GET_INSIGHTS_ASSETS_SINGLE
        else:
            message = consts.SUCCESS_GET_INSIGHTS_ASSETS_MULTIPLE.format(total_assets)

        # Update summary
        self._action_result.update_summary(summary)

        return self._action_result.set_status(phantom.APP_SUCCESS, message)

    def __handle_error(self, ret_val, response):
        """Handle error responses from the API.

        Args:
            ret_val (int): The return value from the API call
            response (dict): The error response from the API

        Returns:
            int: phantom.APP_ERROR with an appropriate error message
        """
        # Check if the error response contains a specific message about the insight not existing
        if isinstance(response, dict) and "error" in response:
            error_message = response.get("error", "")
            if "not found" in str(error_message).lower():
                return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_INSIGHT_NOT_FOUND)

        # Otherwise, return the status that was already set by the utility
        return self._action_result.get_status()

    def execute(self):
        """Execute get SOC insights assets action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Build endpoint and parameters
        Step 4: Make API call
        Step 5: Process response or handle errors
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters
        self._connector.save_progress("Validating parameters")
        ret_val = self._validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 3: Build endpoint and parameters
        endpoint, params = self.__build_endpoint_and_params()

        # Step 4: Make API call
        self._connector.save_progress("Retrieving insight assets from Infoblox")
        ret_val, response = self.__make_api_call(endpoint, params)

        # Step 5: Process response or handle errors
        if phantom.is_fail(ret_val):
            return self.__handle_error(ret_val, response)

        return self.__process_response(response)
