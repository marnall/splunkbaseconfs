#!/usr/bin/python
# File: ciscomeraki_update_l3_firewall_rules.py
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

import ipaddress
import json

import phantom.app as phantom

import ciscomeraki_consts as consts
from actions import BaseAction


class UpdateL3FirewallRules(BaseAction):
    """Class to handle the update L3 firewall rules action."""

    def _validate_ip_cidr(self, ip_cidr):
        """Validate IP CIDR notation."""
        try:
            ipaddress.ip_network(ip_cidr)
            return True
        except ValueError:
            return False

    def _validate_port(self, port):
        """Validate port number or range."""
        try:
            if "-" in str(port):
                start, end = map(int, str(port).split("-"))
                return 1 <= start <= 65535 and 1 <= end <= 65535 and start <= end
            else:
                port_num = int(port)
                return 1 <= port_num <= 65535
        except (ValueError, TypeError):
            return False

    def _validate_rule(self, rule):
        """Validate firewall rule parameters."""
        # Check required fields
        for field in consts.L3_RULE_REQUIRED_FIELDS:
            if field not in rule:
                return False, f"Missing required field: {field}"

        # Validate policy
        if rule["policy"] not in consts.VALID_POLICIES:
            return False, f"Invalid policy. Must be one of: {', '.join(consts.VALID_POLICIES)}"

        # Validate protocol
        if rule["protocol"] not in consts.VALID_PROTOCOLS:
            return False, f"Invalid protocol. Must be one of: {', '.join(consts.VALID_PROTOCOLS)}"

        # Validate ports
        if not self._validate_port(rule["srcPort"]):
            return False, "Invalid source port"
        if not self._validate_port(rule["destPort"]):
            return False, "Invalid destination port"

        # Validate CIDRs
        if not self._validate_ip_cidr(rule["srcCidr"]):
            return False, "Invalid source CIDR"
        if not self._validate_ip_cidr(rule["destCidr"]):
            return False, "Invalid destination CIDR"

        return True, ""

    def execute(self):
        """Execute the update L3 firewall rules action.

        Returns:
            bool: Success/failure
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("update_l3_firewall_rules"))

        # Validate required parameters
        network_id = self._param.get("network_id")
        rules = self._param.get("rules")

        if not network_id:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_REQUIRED_PARAM.format(key="network_id"))

        if not rules:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_REQUIRED_PARAM.format(key="rules"))

        # Parse rules if provided as string
        try:
            if isinstance(rules, str):
                rules = json.loads(rules)

            if not isinstance(rules, list):
                return self._action_result.set_status(phantom.APP_ERROR, "Rules must be a list of rule objects")

            # Validate each rule
            for rule in rules:
                is_valid, error_msg = self._validate_rule(rule)
                if not is_valid:
                    return self._action_result.set_status(phantom.APP_ERROR, f"Invalid rule: {error_msg}")

        except json.JSONDecodeError:
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid JSON in rules parameter")

        # Make REST call
        ret_val, response = self._connector._utils._make_rest_call(
            endpoint=consts.UPDATE_L3_FIREWALL_RULES.format(network_id=network_id),
            action_result=self._action_result,
            method="put",
            json={"rules": rules},
        )

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        # Process response
        self._action_result.add_data({"rules_updated": True, "rules": response})

        summary = {"total_rules_updated": len(rules)}
        self._action_result.update_summary(summary)

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_SUCCESS_RESPONSE.format(
                action=" ".join([i.capitalize() if idx > 0 else i for idx, i in enumerate(self._connector.get_action_identifier().split("_"))])
            ),
        )
