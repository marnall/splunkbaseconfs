# File: ciscomeraki_connector.py
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
from importlib import import_module

import phantom.app as phantom
from phantom.base_connector import BaseConnector

from actions import BaseAction
from ciscomeraki_auth import CiscoMerakiAuth
from ciscomeraki_utils import CiscoMerakiUtils


class CiscoMerakiConnector(BaseConnector):
    """Cisco Meraki Connector for Splunk SOAR."""

    def __init__(self):
        """Initialize the connector."""
        super().__init__()
        self._utils = None
        self._state = None
        self._auth = None

    def initialize(self):
        """Initialize the connector with configuration."""
        self._state = self.load_state()
        if not isinstance(self._state, dict):
            self.debug_print("Resetting state file with empty dictionary")
            self._state = {}

        # Initialize auth and utils
        self._auth = CiscoMerakiAuth(self)
        self._utils = CiscoMerakiUtils(self)

        return phantom.APP_SUCCESS

    def finalize(self):
        """Perform cleanup operations."""
        return phantom.APP_SUCCESS

    def handle_action(self, param):
        """Main action handler."""
        # Get the action identifier only once
        action_id = self.get_action_identifier()
        self.debug_print("action_id", action_id)

        action_name = f"actions.ciscomeraki_{action_id}"
        import_module(action_name, package="actions")

        base_action_sub_classes = BaseAction.__subclasses__()
        self.debug_print(f"Finding action module: {action_name}")
        for action_class in base_action_sub_classes:
            if action_class.__module__ == action_name:
                action = action_class(self, param)
                return action.execute()

        self.debug_print("Action not implemented")
        return phantom.APP_ERROR
