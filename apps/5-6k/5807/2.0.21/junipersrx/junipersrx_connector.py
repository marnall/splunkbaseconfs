# File: junipersrx_connector.py
#
# Copyright (c) 2016-2025 Splunk Inc.
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
#
#
import re

import phantom.app as phantom
import xmltodict
from jsonpath_ng import parse as jsparse
from ncclient import manager
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from junipersrx_consts import *


class JuniperConnector(BaseConnector):
    # The actions supported by this connector
    ACTION_ID_BLOCK_APPLICATION = "block_application"
    ACTION_ID_UNBLOCK_APPLICATION = "unblock_application"
    ACTION_ID_BLOCK_IP = "block_ip"
    ACTION_ID_UNBLOCK_IP = "unblock_ip"
    ACTION_ID_LIST_APPS = "list_apps"

    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._conn = None

    def _get_conn(self):
        if self._conn is not None:
            # conn already created for this call
            return phantom.APP_SUCCESS

        config = self.get_config()
        port = str(config.get(phantom.APP_JSON_PORT, DEFAULT_PORT))
        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, config[phantom.APP_JSON_DEVICE])
        username = config[phantom.APP_JSON_USERNAME]
        password = config[phantom.APP_JSON_PASSWORD]
        self.save_progress("Using port " + port + "...")
        try:
            conn = manager.connect(
                host=config[phantom.APP_JSON_DEVICE],
                port=port,
                username=username,
                password=password,
                timeout=DEFAULT_TIMEOUT,
                device_params={"name": "junos"},
                hostkey_verify=False,
            )
        except Exception as e:
            self.debug_print(JUNIPERSRX_ERR_DEVICE_CONNECTIVITY, e)
            return self.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_DEVICE_CONNECTIVITY, e)

        self._conn = conn

        return phantom.APP_SUCCESS

    def _test_connectivity(self, param):
        status = self._get_conn()

        if phantom.is_fail(status):
            self.append_to_message(JUNIPERSRX_ERR_TEST_CONNECTIVITY_FAILED)
            return self.get_status()

        return self.set_status_save_progress(phantom.APP_SUCCESS, JUNIPERSRX_SUCC_TEST_CONNECTIVITY_PASSED)

    def _get_application_set_apps(self, param, action_result):
        apps = []
        get_app_set = f"show configuration applications application-set {JUNIPERSRX_APP_SET} | display xml"

        try:
            response = self._conn.command(command=get_app_set, format="xml")
        except Exception as e:
            self.debug_print(f"command Exception: {e!s}")
            return (action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_COMMAND_EXEC, e), apps)

        response_dict = None

        try:
            response_dict = xmltodict.parse(response.tostring)
        except Exception as e:
            self.debug_print(f"parse Exception: {e!s}")
            return (action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_PARSE_RESPONSE, e), apps)

        if not response_dict:
            return (action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_EMPTY_RESPONSE), apps)

        apps = jsparse("rpc-reply.configuration.applications.application-set.application").find(response_dict)

        if len(apps) == 0:
            # Success because there is no apps
            return (phantom.APP_SUCCESS, apps)

        get_list = lambda x: x if type(x) is list else [x]

        # there should be only one
        apps = get_list(apps[0].value)

        return (phantom.APP_SUCCESS, apps)

    def _get_address_set_addresses(self, param, action_result):
        addresses = []
        get_address_set = (
            f"show configuration security address-book {JUNIPERSRX_ADDRESS_BOOK} address-set {JUNIPERSRX_ADDRESS_SET} | display xml"
        )

        try:
            response = self._conn.command(command=get_address_set, format="xml")
        except Exception as e:
            self.debug_print(f"command Exception: {e!s}")
            return (action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_COMMAND_EXEC, e), addresses)

        response_dict = None

        try:
            response_dict = xmltodict.parse(response.tostring)
        except Exception as e:
            self.debug_print(f"parse Exception: {e!s}")
            return (action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_PARSE_RESPONSE, e), addresses)

        if not response_dict:
            return (action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_EMPTY_RESPONSE), addresses)

        addresses = jsparse("rpc-reply.configuration.security.address-book.address-set.address").find(response_dict)

        if len(addresses) == 0:
            # Success because there is no addresses
            return (phantom.APP_SUCCESS, addresses)

        get_list = lambda x: x if type(x) is list else [x]

        # there should be only one
        addresses = get_list(addresses[0].value)

        return (phantom.APP_SUCCESS, addresses)

    def _get_first_allow_policy(self, param, action_result):
        policy_name = None

        from_zone = param[JUNIPERSRX_JSON_FROM_ZONE]

        to_zone = param[JUNIPERSRX_JSON_TO_ZONE]

        get_config_cmd = f"show security policies from-zone {from_zone} to-zone {to_zone} | display xml"

        try:
            response = self._conn.command(command=get_config_cmd, format="xml")
        except Exception as e:
            self.debug_print(f"command Exception: {e!s}")
            return (action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_COMMAND_EXEC, e), policy_name)

        response_dict = None

        try:
            response_dict = xmltodict.parse(response.tostring)
        except Exception as e:
            self.debug_print(f"parse Exception: {e!s}")
            return (action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_PARSE_RESPONSE, e), policy_name)

        if not response_dict:
            return (action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_EMPTY_RESPONSE), policy_name)

        policies = jsparse("rpc-reply.security-policies.security-context.policies").find(response_dict)

        if len(policies) == 0:
            return (action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_NO_ALLOW_POLICY_ENTRIES_FOUND), policy_name)

        get_list = lambda x: x if type(x) is list else [x]

        # there should be only one
        policies = get_list(policies[0].value)

        lowest_seq_number = len(policies) + 1

        for i, policy in enumerate(policies):
            self.debug_print(f"Policy[{i}]:", policy)
            seq_no = policy["policy-information"]["policy-sequence-number"]
            action = policy["policy-information"]["policy-action"]["action-type"]

            self.debug_print(f"Lowest Seq No: {lowest_seq_number}, Seq No: {seq_no}, Action: {action}")

            if action != "permit":
                self.debug_print(f"{action} != permit, continue")
                # ignore
                continue

            if int(seq_no) >= int(lowest_seq_number):
                self.debug_print(f"{seq_no} >= {lowest_seq_number}, continue")
                continue

            lowest_seq_number = seq_no
            policy_name = policy["policy-information"]["policy-name"]
            self.debug_print(f"Got a lower permit, now Lowest Seq #: {lowest_seq_number} of Name: {policy_name}")

        if policy_name is None:
            return (action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_NO_ALLOW_POLICY_ENTRIES_FOUND), policy_name)

        return (phantom.APP_SUCCESS, policy_name)

    def _unblock_application(self, param):
        status = self._get_conn()

        if phantom.is_fail(status):
            return self.get_status()

        action_result = self.add_action_result(ActionResult(dict(param)))

        block_app = param[JUNIPERSRX_JSON_APPLICATION]

        from_zone = param[JUNIPERSRX_JSON_FROM_ZONE]

        to_zone = param[JUNIPERSRX_JSON_TO_ZONE]

        self.debug_print("Locking the Running config")

        self._conn.lock()
        self.debug_print("Locked")
        config_cmd = []

        # First get all the applications from the application set
        status, apps = self._get_application_set_apps(param, action_result)
        if phantom.is_fail(status):
            return action_result.get_status()

        app_name = None
        for app in apps:
            # check if any of them match the one that we are trying to remove
            if app["name"] == block_app:
                app_name = app["name"]
                break

        if app_name is None:
            # Not an error condition
            return action_result.set_status(phantom.APP_SUCCESS, JUNIPERSRX_SUCC_APP_NOT_FOUND)

        # Check if the policy needs to be changed
        remove_policy = True if len(apps) == 1 else False

        # remove the app from the app-set
        app_set_line = f"delete applications application-set {JUNIPERSRX_APP_SET} application {app_name}"
        config_cmd.append(app_set_line)

        # remove the policy if needed
        if remove_policy:
            policy_line = f"delete security policies from-zone {from_zone} to-zone {to_zone} policy {JUNIPERSRX_APP_POLICY}"
            config_cmd.append(policy_line)

        self.send_progress(JUNIPERSRX_MSG_REMOVING_POLICY)

        # Commit the config
        status = self._apply_config(config_cmd, action_result)
        if phantom.is_fail(status):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully unblock application")

    def _block_application(self, param):
        status = self._get_conn()

        if phantom.is_fail(status):
            return self.get_status()

        action_result = self.add_action_result(ActionResult(dict(param)))

        block_app = param[JUNIPERSRX_JSON_APPLICATION]

        from_zone = param[JUNIPERSRX_JSON_FROM_ZONE]

        to_zone = param[JUNIPERSRX_JSON_TO_ZONE]

        self.debug_print("Locking the Running config")

        self._conn.lock()
        self.debug_print("Locked")
        config_cmd = []

        # First Add the application to the application set
        app_set = f"set applications application-set {JUNIPERSRX_APP_SET} application {block_app}"
        config_cmd.append(app_set)

        # create policy
        policy_line = f"set security policies from-zone {from_zone} to-zone {to_zone} policy {JUNIPERSRX_APP_POLICY} match source-address any "

        policy_line += f"destination-address any application {JUNIPERSRX_APP_SET}"

        config_cmd.append(policy_line)

        # Set the actions for the policy
        policy_line = f"set security policies from-zone {from_zone} to-zone {to_zone} policy {JUNIPERSRX_APP_POLICY} then reject"
        config_cmd.append(policy_line)

        policy_line = f"set security policies from-zone {from_zone} to-zone {to_zone} policy {JUNIPERSRX_APP_POLICY} then log session-init"

        config_cmd.append(policy_line)

        self.send_progress(JUNIPERSRX_MSG_ADDING_POLICY)

        status, permit_rule = self._get_first_allow_policy(param, action_result)

        self.debug_print(f"Got first rule: {permit_rule}, status: {status}")

        if phantom.is_fail(status):
            return action_result.get_status()

        insert_line = (
            f"insert security policies from-zone {from_zone} to-zone {to_zone} policy {JUNIPERSRX_APP_POLICY} before policy {permit_rule}"
        )

        config_cmd.append(insert_line)

        # Commit the config
        ret_val = self._apply_config(config_cmd, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully blocked application")

    def _get_addr_name(self, ip):
        # Remove the slash in the ip if present
        rem_slash = lambda x: re.sub(r"(.*)/(.*)", r"\1-\2", x)

        name = f"{rem_slash(ip)}"

        return name

    def _add_address(self, block_ip, config_cmd, action_result):
        type = None
        name = None

        container_id = self.get_container_id()

        description = f"Last updated by container {container_id}"

        name = self._get_addr_name(block_ip)
        value = block_ip

        # Try to figure out the type of ip
        if block_ip.find("-") != -1:
            type = "range-address"
            value = block_ip.replace("-", " to ")
        elif phantom.is_hostname(block_ip):
            type = "dns-name"
        else:
            type = " "

        address_book_line = f'set security address-book {JUNIPERSRX_ADDRESS_BOOK} address {name} description "{description}" {type} {value}'
        config_cmd.append(address_book_line)

        address_set_line = f"set security address-book {JUNIPERSRX_ADDRESS_BOOK} address-set {JUNIPERSRX_ADDRESS_SET} address {name}"
        config_cmd.append(address_set_line)

        return (phantom.APP_SUCCESS, name)

    def _unblock_ip(self, param):
        status = self._get_conn()

        if phantom.is_fail(status):
            return self.get_status()

        action_result = self.add_action_result(ActionResult(dict(param)))

        block_ip = param[JUNIPERSRX_JSON_IP]

        from_zone = param[JUNIPERSRX_JSON_FROM_ZONE]

        to_zone = param[JUNIPERSRX_JSON_TO_ZONE]

        self.debug_print("Locking the Running config")

        self._conn.lock()
        self.debug_print("Locked")
        config_cmd = []

        # First get all the addresses from the address set
        status, addresses = self._get_address_set_addresses(param, action_result)
        if phantom.is_fail(status):
            return action_result.get_status()

        addr_name = None
        for address in addresses:
            # check if any of them match the one that we are trying to remove
            if address["name"] == self._get_addr_name(block_ip):
                addr_name = address["name"]
                break

        if addr_name is None:
            # Not an error condition
            return action_result.set_status(phantom.APP_SUCCESS, JUNIPERSRX_SUCC_ADDRESS_NOT_FOUND)

        # Check if the policy needs to be changed
        remove_policy = True if len(addresses) == 1 else False

        # remove the address from the address-set
        address_set_line = f"delete security address-book {JUNIPERSRX_ADDRESS_BOOK} address-set {JUNIPERSRX_ADDRESS_SET} address {addr_name}"
        config_cmd.append(address_set_line)

        # remove the address from the address book
        address_book_line = f"delete security address-book {JUNIPERSRX_ADDRESS_BOOK} address {addr_name}"
        config_cmd.append(address_book_line)

        # remove the policy if needed
        if remove_policy:
            policy_line = f"delete security policies from-zone {from_zone} to-zone {to_zone} policy {JUNIPERSRX_ADDRESS_POLICY}"
            config_cmd.append(policy_line)

        self.send_progress(JUNIPERSRX_MSG_REMOVING_POLICY)

        # Commit the config
        status = self._apply_config(config_cmd, action_result)
        if phantom.is_fail(status):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully unblocked ip")

    def _apply_config(self, config_cmd, action_result):
        self.debug_print("config_cmd: ", config_cmd)

        try:
            self._conn.load_configuration(action="set", config=config_cmd)
        except Exception as e:
            self.debug_print(f"load_configuration Exception: {e!s}")
            return action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_CONFIG_LOAD_FAILED, e)

        try:
            self._conn.validate()
        except Exception as e:
            self.debug_print(f"validate Exception: {e!s}")
            return action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_CONFIG_VALIDATION_FAILED, e)

        # Now Commit the config
        try:
            self._conn.commit()
        except Exception as e:
            self.debug_print(f"commit Exception: {e!s}")
            return action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_CONFIG_COMMIT_FAILED, e)

        return phantom.APP_SUCCESS

    def _block_ip(self, param):
        status = self._get_conn()

        if phantom.is_fail(status):
            return self.get_status()

        action_result = self.add_action_result(ActionResult(dict(param)))

        block_ip = param[JUNIPERSRX_JSON_IP]

        from_zone = param[JUNIPERSRX_JSON_FROM_ZONE]

        to_zone = param[JUNIPERSRX_JSON_TO_ZONE]

        self.debug_print("Locking the Running config")

        self._conn.lock()
        self.debug_print("Locked")
        config_cmd = []

        # First Add the ip to the address group
        status = self._add_address(block_ip, config_cmd, action_result)

        if phantom.is_fail(status):
            return action_result.get_status()

        # get the address book and it's attached zones, we can't add zones to an address book without checking
        # for them first else it spits an error.

        # create policy
        policy_line = (
            f"set security policies from-zone {from_zone} to-zone {to_zone} policy {JUNIPERSRX_ADDRESS_POLICY} match source-address any "
        )

        policy_line += f"destination-address {JUNIPERSRX_ADDRESS_SET} application any"

        config_cmd.append(policy_line)

        # Set the actions for the policy
        policy_line = f"set security policies from-zone {from_zone} to-zone {to_zone} policy {JUNIPERSRX_ADDRESS_POLICY} then reject"
        config_cmd.append(policy_line)

        policy_line = f"set security policies from-zone {from_zone} to-zone {to_zone} policy {JUNIPERSRX_ADDRESS_POLICY} then log session-init"

        config_cmd.append(policy_line)

        self.send_progress(JUNIPERSRX_MSG_ADDING_POLICY)

        status, permit_rule = self._get_first_allow_policy(param, action_result)

        self.debug_print(f"Got first rule: {permit_rule}, status: {status}")

        if phantom.is_fail(status):
            return action_result.get_status()

        insert_line = (
            f"insert security policies from-zone {from_zone} to-zone {to_zone} policy {JUNIPERSRX_ADDRESS_POLICY} before policy {permit_rule}"
        )

        config_cmd.append(insert_line)

        # Commit the config
        ret_val = self._apply_config(config_cmd, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully blocked ip")

    def _list_apps(self, param):
        status = self._get_conn()

        if phantom.is_fail(status):
            return self.get_status()

        action_result = self.add_action_result(ActionResult(dict(param)))

        apps = []
        get_app_set = "show configuration groups junos-defaults applications | display xml"

        try:
            response = self._conn.command(command=get_app_set, format="xml")
        except Exception as e:
            self.debug_print(f"command Exception: {e!s}")
            return (action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_COMMAND_EXEC, e), apps)

        response_dict = None

        try:
            response_dict = xmltodict.parse(response.tostring)
        except Exception as e:
            self.debug_print(f"parse Exception: {e!s}")
            return (action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_PARSE_RESPONSE, e), apps)

        if not response_dict:
            return (action_result.set_status(phantom.APP_ERROR, JUNIPERSRX_ERR_EMPTY_RESPONSE), apps)

        get_list = lambda x: x if type(x) is list else [x]

        # app_sets = jsparse('rpc-reply.configuration.groups.applications.application-set').find(response_dict)

        total_apps = 0
        # if len(app_sets) > 0:
        #     # there should be only one
        #     apps = get_list(app_sets[0].value)
        #     total_apps += len(apps)
        #     for app in apps:
        #         action_result.add_data({'name': app['name'], 'type': 'set'})

        apps = jsparse("rpc-reply.configuration.groups.applications.application").find(response_dict)

        if len(apps) > 0:
            # there should be only one
            apps = get_list(apps[0].value)
            total_apps += len(apps)
            for app in apps:
                action_result.add_data({"name": app["name"], "type": "app"})

        action_result.set_summary({JUNIPERSRX_JSON_TOTAL_APPLICATIONS: total_apps})

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully recived application list")

    def _close_session(self):
        if self._conn is not None:
            try:
                self._conn.unlock()
            except:
                pass

            if self._conn.connected:
                self._conn.close_session()

        return phantom.APP_SUCCESS

    def finalize(self):
        return self._close_session()

    def handle_exception(self, exception):
        return self._close_session()

    def validate_parameters(self, param):
        """This app will do it's own parameter validation"""
        return phantom.APP_SUCCESS

    def handle_action(self, param):
        result = None
        action = self.get_action_identifier()

        self._param = param

        if action == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            result = self._test_connectivity(param)
        elif action == self.ACTION_ID_BLOCK_APPLICATION:
            result = self._block_application(param)
        elif action == self.ACTION_ID_UNBLOCK_APPLICATION:
            result = self._unblock_application(param)
        elif action == self.ACTION_ID_BLOCK_IP:
            result = self._block_ip(param)
        elif action == self.ACTION_ID_UNBLOCK_IP:
            result = self._unblock_ip(param)
        elif action == self.ACTION_ID_LIST_APPS:
            result = self._list_apps(param)

        return result


if __name__ == "__main__":
    import sys

    try:
        import simplejson as json
    except:
        pass
    import pudb

    pudb.set_trace()

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=" " * 4))

        connector = JuniperConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(ret_val)

    sys.exit(0)
