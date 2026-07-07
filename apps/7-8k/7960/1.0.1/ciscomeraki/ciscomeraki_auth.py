#!/usr/bin/python
# File: ciscomeraki_auth.py
#
# Copyright (c) 2025-2026 Splunk Inc.
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

import ciscomeraki_consts as consts


class CiscoMerakiAuth:
    """Class to handle authentication for Cisco Meraki API."""

    def __init__(self, connector):
        """Initialize the auth class.

        Args:
            connector: The connector instance
        """
        self._connector = connector
        self._api_key = None

    def validate_credentials(self, action_result):
        """Validate API key by making a test call.

        Args:
            action_result: ActionResult object to add status to

        Returns:
            bool: Success/failure
        """
        # Get API key from config
        config = self._connector.get_config()
        self._api_key = config.get("api_key")

        if not self._api_key:
            return action_result.set_status(phantom.APP_ERROR, "API key not found in asset configuration")

        # Test API key by listing organizations
        ret_val, response = self._connector._utils._make_rest_call(consts.LIST_ORGANIZATIONS, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return phantom.APP_SUCCESS

    def get_headers(self):
        """Get headers for API requests.

        Returns:
            dict: Headers including auth, or None if API key is not configured
        """

        # Get API key from config
        config = self._connector.get_config()
        self._api_key = config.get("api_key")

        if not self._api_key:
            self._connector.debug_print("API key not found in asset configuration")
            return None

        headers = {consts.AUTH_HEADER: self._api_key, "Content-Type": "application/json", "Accept": "application/json"}
        return headers
