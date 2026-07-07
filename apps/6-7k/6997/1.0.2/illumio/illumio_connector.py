# File: illumio_connector.py
#
# Copyright (c) Illumio, 2023-2025
#
# This unpublished material is proprietary to Illumio.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Illumio.
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
import sys
from datetime import datetime

# Phantom App imports
import phantom.app as phantom
import pytz
import requests
from dateutil.parser import parse
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

import illumio
from illumio_consts import *


class IllumioConnector(BaseConnector):
    """Represent a connector module that implements the actions that are provided by the app."""

    def __init__(self):
        """Initialize class variables."""
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None
        self._api_key = None
        self._api_secret = None
        self._hostname = None
        self._port = None
        self._org_id = None
        self._pce = None

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Connecting to PCE")

        if self.connect_pce(action_result):
            self.save_progress("Connectivity Test Passed")
            return action_result.set_status(phantom.APP_SUCCESS)
        else:
            self.save_progress("Connectivity Test Failed")
            return action_result.set_status(phantom.APP_ERROR)

    def _handle_get_traffic_analysis(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val, end_time = self.parse_and_validate_date(param["end_time"], action_result, "end_time")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, start_time = self.parse_and_validate_date(param["start_time"], action_result, "start_time")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if self.check_starttime_greater_than_endtime(start_time, end_time):
            return action_result.set_status(
                phantom.APP_ERROR,
                "The 'end_time' parameter must be greater than 'start_time' parameter",
            )

        ret_val, port = self._validate_integer(action_result, param["port"], "port", max=PORT_MAX_VALUE)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        protocol = param["protocol"].lower()
        if protocol not in PROTOCOL_LIST:
            return action_result.set_status(phantom.APP_ERROR, ILLUMIO_INVALID_PROTOCOL_MSG)

        policy_decisions_string = param["policy_decisions"].lower()

        ret_val = self.connect_pce(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            policy_decisions_list = self.handle_comma_seperated_string(policy_decisions_string)

            traffic_query = illumio.TrafficQuery.build(
                start_date=start_time.isoformat(),
                end_date=end_time.isoformat(),
                include_services=[{"port": port, "proto": protocol}],
                policy_decisions=policy_decisions_list,
            )

            traffic_flow_list = self._pce.get_traffic_flows_async(
                query_name="phantom_block_port_traffic_query",
                traffic_query=traffic_query,
            )
        except Exception as e:
            self.error_print(f"Traffic query failed: {e!s}")
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Encountered error while running traffic query: {e}",
            )

        traffic_list_length = len(traffic_flow_list)

        self.debug_print(f"Found {traffic_list_length} records for the specified time range")

        result = {"traffic_flows": [self.convert_object_to_json(flow, action_result) for flow in traffic_flow_list]}
        action_result.add_data(result)
        if traffic_list_length == 0:
            return action_result.set_status(phantom.APP_SUCCESS, "No traffic found for the specified time range")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully fetched traffic flow list")

    def _handle_create_virtual_service(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val, port = self._validate_integer(action_result, param["port"], "port", max=PORT_MAX_VALUE)
        if phantom.is_fail(ret_val):
            return self.get_status()

        protocol = param["protocol"].lower()
        if protocol not in PROTOCOL_LIST:
            return action_result.set_status(phantom.APP_ERROR, ILLUMIO_INVALID_PROTOCOL_MSG)

        service_name = param["name"]
        virtual_service = None

        ret_val = self.connect_pce(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            self.debug_print(f"Creating virtual service '{service_name}'")
            virtual_service = illumio.VirtualService(
                name=service_name,
                service_ports=[illumio.ServicePort(port=port, proto=protocol)],
            )
            virtual_service = self._pce.virtual_services.create(virtual_service)
            action_result.set_status(phantom.APP_SUCCESS, "Successfully created virtual service")
        except Exception as e:
            err_msg = f"Encountered error creating virtual service: {e!s}"
            self.debug_print(err_msg)
            if ILLUMIO_EXISTING_VIRTUAL_SERVICE_MSG in str(e):
                service_list = self._pce.virtual_services.get(params={"name": service_name})
                for service in service_list:
                    if service_name == service.name:
                        virtual_service = service
                        action_result.set_status(
                            phantom.APP_SUCCESS,
                            f"Found existing virtual service with name {service_name}",
                        )
                        break
            else:
                return action_result.set_status(phantom.APP_ERROR, err_msg)

        result = self.convert_object_to_json(virtual_service, action_result)
        action_result.add_data(result)
        return action_result.get_status()

    def _handle_provision_objects(self, param):
        hrefs = param["hrefs"]
        self.debug_print(f"Provisioning HREFs: {hrefs}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val = self.connect_pce(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            hrefs_list = self.handle_comma_seperated_string(hrefs)

            provisioned_virtual_service_obj = self._pce.provision_policy_changes(
                change_description="Object provisioning.",
                hrefs=hrefs_list,
            )
        except Exception as e:
            self.error_print(f"Failed to provision objects: {e!s}")
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Encountered error provisioning object: {e}",
            )

        result = self.convert_object_to_json(provisioned_virtual_service_obj, action_result)
        provisioned_href_list = [illumio.convert_draft_href_to_active(href) for href in hrefs_list]
        result["provisioned_href"] = provisioned_href_list
        action_result.add_data(result)
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully provisioned object")

    def _handle_get_ip_lists(self, param):
        name = param.get("name")
        description = param.get("description")
        fqdn = param.get("fqdn")
        ip_address = param.get("ip_address")

        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val = self.connect_pce(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            ip_list = self._pce.ip_lists.get(
                params={
                    "name": name,
                    "description": description,
                    "fqdn": fqdn,
                    "ip_address": ip_address,
                }
            )
            self.debug_print(f"Found {len(ip_list)} IP lists")
            output_msg = "Successfully fetched IP List" if ip_list else "No Data Found"
            action_result.set_status(phantom.APP_SUCCESS, output_msg)
        except Exception as e:
            self.error_print(f"Failed to get IP lists: {e!s}")
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Encountered error fetching IP List: {e}",
            )

        result = {"ip_lists": [self.convert_object_to_json(lists, action_result) for lists in ip_list]}
        action_result.add_data(result)
        return action_result.get_status()

    def _handle_create_ruleset(self, param):
        name = param["name"]

        action_result = self.add_action_result(ActionResult(dict(param)))

        rule_set = None

        ret_val = self.connect_pce(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            self.debug_print(f"Creating ruleset '{name}'")
            rule_set = illumio.RuleSet(name=name, scopes=[illumio.LabelSet(labels=[])])
            rule_set = self._pce.rule_sets.create(rule_set)
            action_result.set_status(phantom.APP_SUCCESS, "Successfully created ruleset")
        except Exception as e:
            err_msg = f"Encountered error creating ruleset: {e!s}"
            self.debug_print(err_msg)
            if ILLUMIO_EXISTING_OBJECT_MSG in str(e):
                ruleset_list = self._pce.rule_sets.get(params={"name": name})
                for ruleset in ruleset_list:
                    if name == ruleset.name:
                        rule_set = ruleset
                        action_result.set_status(
                            phantom.APP_SUCCESS,
                            f"Found existing ruleset with name {name}",
                        )
                        break

            else:
                return action_result.set_status(phantom.APP_ERROR, err_msg)

        result = self.convert_object_to_json(rule_set, action_result)
        action_result.add_data(result)
        return action_result.get_status()

    def handle_comma_seperated_string(self, comma_str):
        """
        Convert comma seperated string into list.

        :param comma_str: comma seperated string
        :return : list
        """
        str_to_list = [x.strip() for x in comma_str.split(",") if x]
        return str_to_list

    def _handle_create_rule(self, param):
        providers_list = self.handle_comma_seperated_string(param["providers"])
        consumers_list = self.handle_comma_seperated_string(param["consumers"])
        ruleset_href = param["ruleset_href"]
        resolve_consumers_as_list = self.handle_comma_seperated_string(param.get("resolve_consumers_as", "workloads"))
        resolve_providers_as_list = self.handle_comma_seperated_string(param.get("resolve_providers_as", "workloads"))
        ingress_services = self.handle_comma_seperated_string(param.get("ingress_services", ""))

        action_result = self.add_action_result(ActionResult(dict(param)))
        rule_data = None

        ingress_services_list = [{"href": ingress_service} for ingress_service in ingress_services]

        ret_val = self.connect_pce(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            self.debug_print(f"Creating rule in ruleset '{ruleset_href}'")
            message = "Successfully created rule"
            rule = illumio.Rule.build(
                providers=providers_list,
                consumers=consumers_list,
                resolve_providers_as=resolve_providers_as_list,
                resolve_consumers_as=resolve_consumers_as_list,
                ingress_services=ingress_services_list,
            )

            list_of_existing_rules_in_ruleset = self._pce.rule_sets.get_by_reference(ruleset_href).rules

            for rule_obj in list_of_existing_rules_in_ruleset:
                if (
                    (rule_obj.providers == rule.providers)
                    and (rule_obj.consumers == rule.consumers)
                    and (rule_obj.resolve_labels_as == rule.resolve_labels_as)
                    and (rule_obj.ingress_services == rule.ingress_services)
                ):
                    rule_data = rule_obj
                    message = "Found existing rule"
                    break

            if not rule_data:
                rule_data = self._pce.rules.create(rule, parent=ruleset_href)

            action_result.set_status(phantom.APP_SUCCESS, message)
        except Exception as e:
            self.error_print(f"Failed to create rule: {e!s}")
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Encountered error creating rule: {e}",
            )

        result = self.convert_object_to_json(rule_data, action_result)
        action_result.add_data(result)
        return action_result.get_status()

    def _handle_create_service_binding(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        workload_hrefs_list = self.handle_comma_seperated_string(param["workload_hrefs"])
        virtual_service_href = illumio.convert_draft_href_to_active(param["virtual_service_href"])

        ret_val = self.connect_pce(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            self.debug_print("Bindings workloads '{}' to virtual service '{}'".format(param["workload_hrefs"], virtual_service_href))
            service_bindings = self._pce.service_bindings.create(
                [
                    {
                        "workload": {"href": workload_href},
                        "virtual_service": {"href": virtual_service_href},
                        "port_overrides": [],
                    }
                    for workload_href in workload_hrefs_list
                ]
            )

            action_result.set_status(phantom.APP_SUCCESS, "Successfully bound workloads with virtual service")
        except Exception as e:
            err_msg = f"Encountered error creating service binding: {e}"
            self.error_print(err_msg)
            if ILLUMIO_INVALID_VIRTUAL_SERVICE_HREF in str(e):
                err_msg = "Invalid virtual service HREF or HREF needs to be provisioned"
            return action_result.set_status(
                phantom.APP_ERROR,
                err_msg,
            )

        service_bindings["service_bindings"] = [sb.to_json() for sb in service_bindings["service_bindings"]]

        action_result.add_data(service_bindings)
        return action_result.get_status()

    def _handle_create_enforcement_boundary(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        providers_list = self.handle_comma_seperated_string(param["providers"])
        consumers_list = self.handle_comma_seperated_string(param["consumers"])

        ret_val, port = self._validate_integer(action_result, param["port"], "port", max=PORT_MAX_VALUE)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        protocol = param["protocol"].lower()
        if protocol not in PROTOCOL_LIST:
            return action_result.set_status(phantom.APP_ERROR, ILLUMIO_INVALID_PROTOCOL_MSG)

        name = param["name"]
        enforcement_boundary = None

        ret_val = self.connect_pce(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            self.debug_print(f"Creating enforcement boundary '{name}'")
            enforcement_boundary = illumio.EnforcementBoundary.build(
                name=name,
                providers=providers_list,
                consumers=consumers_list,
                ingress_services=[{"port": port, "proto": protocol}],
            )
            enforcement_boundary = self._pce.enforcement_boundaries.create(enforcement_boundary)
            action_result.set_status(phantom.APP_SUCCESS, "Successfully created enforcement boundary")
        except Exception as e:
            err_msg = f"Encountered error creating enforcement boundary: {e!s}"
            self.debug_print(err_msg)
            if ILLUMIO_EXISTING_OBJECT_MSG in str(e):
                enforcement_boundary_list = self._pce.enforcement_boundaries.get(params={"name": name})
                for enforcement in enforcement_boundary_list:
                    if name == enforcement.name:
                        enforcement_boundary = enforcement
                        action_result.set_status(
                            phantom.APP_SUCCESS,
                            f"Found existing enforcement boundary with name {name}",
                        )
                        break
            else:
                return action_result.set_status(phantom.APP_ERROR, err_msg)

        result = self.convert_object_to_json(enforcement_boundary, action_result)
        action_result.add_data(result)
        return action_result.get_status()

    def _handle_get_workloads(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        enforcement_mode = param.get("enforcement_mode")
        if enforcement_mode:
            enforcement_mode = enforcement_mode.lower()
            if enforcement_mode not in ENFORCEMENT_MODE_LIST:
                return action_result.set_status(
                    phantom.APP_ERROR,
                    "Please enter a valid value for 'enforcement_mode' parameter",
                )
        ret_val, max_results = self._validate_integer(action_result, param.get("max_results", 500), "max_results")
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        online = param.get("online")
        if online:
            online = online == "True"
            if str(online) not in BOOLEAN_LIST:
                return action_result.set_status(
                    phantom.APP_ERROR,
                    "Please enter a valid value for 'online' parameter",
                )
        managed = param.get("managed")
        if managed:
            managed = managed == "True"
            if str(managed) not in BOOLEAN_LIST:
                return action_result.set_status(
                    phantom.APP_ERROR,
                    "Please enter a valid value for 'managed' parameter",
                )
        labels = self.handle_comma_seperated_string(param.get("labels", ""))

        ret_val = self.connect_pce(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            workloads_list = self._pce.workloads.get(
                params={
                    "managed": managed,
                    "enforcement_mode": enforcement_mode,
                    "online": online,
                    "name": param.get("name"),
                    "labels": "[{}]".format(str(labels).replace("'", '"')),
                    "ip_address": param.get("public_ip_address"),
                    "description": param.get("description"),
                    "hostname": param.get("hostname"),
                    "os_id": param.get("os_id"),
                    "max_results": max_results,
                },
            )
            self.debug_print(f"Found {len(workloads_list)} workloads")
        except Exception as e:
            self.error_print(f"Failed to get workloads: {e!s}")
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Encountered error fetching workloads: {e}",
            )

        result = {"workloads": [self.convert_object_to_json(workload, action_result) for workload in workloads_list]}
        action_result.add_data(result)
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully fetched workloads")

    def _handle_update_enforcement_mode(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        workload_hrefs_list = self.handle_comma_seperated_string(param["workload_hrefs"])
        enforcement_mode = param.get("enforcement_mode", "")
        enforcement_mode = enforcement_mode.lower()
        if not enforcement_mode or enforcement_mode not in ENFORCEMENT_MODE_LIST:
            return action_result.set_status(
                phantom.APP_ERROR,
                "Please enter a valid value for 'enforcement_mode' parameter",
            )

        ret_val = self.connect_pce(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            self.debug_print(f"Updating enforcement for {len(workload_hrefs_list)} workloads")
            response = self._pce.workloads.bulk_update(
                [
                    {
                        "enforcement_mode": enforcement_mode,
                        "href": workload,
                    }
                    for workload in workload_hrefs_list
                ]
            )

            action_result.set_status(phantom.APP_SUCCESS, "Successfully updated workloads")
        except Exception as e:
            self.error_print(f"Failed to update enforcement: {e!s}")
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Encountered error updating enforcement mode: {e}",
            )

        action_result.add_data(response)
        return action_result.get_status()

    def handle_action(self, param):
        """Get current action identifier and call member function of its own to handle the action."""
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)
        elif action_id == "get_traffic_analysis":
            ret_val = self._handle_get_traffic_analysis(param)
        elif action_id == "create_virtual_service":
            ret_val = self._handle_create_virtual_service(param)
        elif action_id == "provision_objects":
            ret_val = self._handle_provision_objects(param)
        elif action_id == "get_ip_lists":
            ret_val = self._handle_get_ip_lists(param)
        elif action_id == "create_ruleset":
            ret_val = self._handle_create_ruleset(param)
        elif action_id == "create_rule":
            ret_val = self._handle_create_rule(param)
        elif action_id == "create_service_binding":
            ret_val = self._handle_create_service_binding(param)
        elif action_id == "create_enforcement_boundary":
            ret_val = self._handle_create_enforcement_boundary(param)
        elif action_id == "get_workloads":
            ret_val = self._handle_get_workloads(param)
        elif action_id == "update_enforcement_mode":
            ret_val = self._handle_update_enforcement_mode(param)

        return ret_val

    def initialize(self):
        """Initialize the global variables with its value and validate it."""
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()
        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}

        # get the asset config
        config = self.get_config()
        self._api_key = config["api_key"]
        self._api_secret = config["api_secret"]
        self._hostname = config["hostname"]

        ret_val, self._port = self._validate_integer(self, config["port"], "port", max=PORT_MAX_VALUE)
        if phantom.is_fail(ret_val):
            return self.get_status()

        ret_val, self._org_id = self._validate_integer(self, config["org_id"], "org_id", min=1)
        if phantom.is_fail(ret_val):
            return self.get_status()

        self.set_validator("ipv6", self._is_ip)
        return phantom.APP_SUCCESS

    def _is_ip(self, input_ip_address):
        """Check given address and return True if address is valid IPv4 or IPV6 address.

        :param input_ip_address: IP address
        :return: status (success/failure)
        """
        try:
            ipaddress.ip_address(input_ip_address)
        except:
            return False

        return True

    def check_for_future_datetime(self, datetime_obj):
        """
        Check the given datetime str is a future date or not.

        :param datetime_obj: datetime object
        :return : bool
        """
        return datetime_obj > datetime.now(tz=pytz.utc)

    def parse_and_validate_date(self, dt_str, action_result, key):
        """
        Convert input date to iso8601 datetime.

        :param dt_str: datetime string
        :param action_result: action result object
        :param key: input parameter key
        :return : status and datetime object
        """
        try:
            date_time = parse(dt_str)
            if not date_time.tzinfo:
                date_time = date_time.replace(tzinfo=pytz.utc)
            date_time = date_time.astimezone(pytz.utc)
            if self.check_for_future_datetime(date_time):
                return (
                    action_result.set_status(
                        phantom.APP_ERROR,
                        f"The provided time is a future datetime. Please provide a valid value for parameter '{key}'",
                    ),
                    None,
                )
        except Exception:
            return (
                action_result.set_status(phantom.APP_ERROR, f"Parameter '{key}' is invalid"),
                None,
            )

        return (phantom.APP_SUCCESS, date_time)

    def check_starttime_greater_than_endtime(self, datetime_start, datetime_end):
        """
        Check if the starttime is greater than endtime or not.

        :param datetime_start: start datetime obj
        :param datetime_end: end datetime obj
        :return : bool
        """
        return datetime_start > datetime_end

    def connect_pce(self, action_result):
        """
        Connect to the PCE server.

        :return: pce obj value
        """
        try:
            self._pce = illumio.PolicyComputeEngine(self._hostname, port=str(self._port), org_id=str(self._org_id))
            self._pce.set_credentials(self._api_key, self._api_secret)
            self._pce.must_connect()
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Encountered error while conecting to PCE: {e}",
            )

        return phantom.APP_SUCCESS

    def convert_object_to_json(self, obj, action_result):
        """
        Convert result object to json.

        :param obj: result object
        :return : json
        """
        try:
            json_data = obj.to_json()
        except Exception as e:
            action_result.set_status(
                phantom.APP_ERROR,
                f"Encountered error while processing response: {e}",
            )
            return {}
        return json_data

    def _validate_integer(self, action_result, parameter, key, min=0, max=sys.maxsize):
        """
        Check if the provided input parameter value is a integer and returns the integer value of the parameter itself.

        :param action_result: Action result or BaseConnector object
        :param parameter: input parameter
        :param key: input parameter message key
        :param min: minimum allowed integer value
        :param max: maximum allowed integer value
        :return: integer value of the parameter or None in case of failure
        """
        error_message = f"Please provide a valid integer value for the '{key}' parameter"
        if parameter is not None:
            try:
                parameter = int(parameter)
                if min <= parameter <= max:
                    return phantom.APP_SUCCESS, parameter
                else:
                    error_message = f"Invalid integer value for parameter {key}. Please enter value between {min} and {max}"
            except Exception as e:
                self.debug_print(f"Encountered error validating integer: {e}")
        return action_result.set_status(phantom.APP_ERROR, error_message), None

    def finalize(self):
        """Perform some final operations or clean up operations."""
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

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

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = IllumioConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=DEFAULT_REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(
                login_url,
                verify=verify,
                data=data,
                headers=headers,
                timeout=DEFAULT_REQUEST_TIMEOUT,
            )
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = IllumioConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
