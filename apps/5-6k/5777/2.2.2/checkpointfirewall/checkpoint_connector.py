# File: checkpoint_connector.py
#
# Copyright (c) 2017-2025 Splunk Inc.
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
# Phantom imports
import re
import socket
import struct
import time

import phantom.app as phantom
import requests
import simplejson as json
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# imports specific to this connector
from checkpoint_consts import *


# Define the App Class
class CheckpointConnector(BaseConnector):
    # The actions supported by this connector
    ACTION_ID_LOGOUT_SESSION = "logout_session"
    ACTION_ID_DELETE_HOST = "delete_host"
    ACTION_ID_LIST_HOSTS = "list_hosts"
    ACTION_ID_ADD_HOST = "add_host"
    ACTION_ID_BLOCK_IP = "block_ip"
    ACTION_ID_UNBLOCK_IP = "unblock_ip"
    ACTION_ID_LIST_LAYERS = "list_layers"
    ACTION_ID_LIST_POLICIES = "list_policies"
    ACTION_ID_ADD_NETWORK = "add_network"
    ACTION_ID_DELETE_NETWORK = "delete_network"
    ACTION_ID_UPDATE_GROUP_MEMBERS = "update_group_members"
    ACTION_ID_INSTALL_POLICY = "install_policy"
    ACTION_ID_ADD_USER = "add_user"
    ACTION_ID_DELETE_USER = "delete_user"
    ACTION_ID_TEST_CONNECTIVITY = "test_connectivity"

    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._base_url = None
        self._headers = None
        self._state = None

    def initialize(self):
        config = self.get_config()
        self._state = self.load_state()

        # Base URL
        base_url = config[phantom.APP_JSON_URL]
        base_url = base_url + ("" if base_url.endswith("/") else "/")
        self._base_url = f"{base_url}web_api/"

        # Headers will always need content-Type
        self._headers = {"content-Type": "application/json"}

        self.set_validator("ip", self._is_ip)

        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _get_net_size(self, net_mask):
        net_mask = net_mask.split(".")

        binary_str = ""
        for octet in net_mask:
            binary_str += bin(int(octet))[2:].zfill(8)

        return str(len(binary_str.rstrip("0")))

    def _get_net_mask(self, net_size):
        host_bits = 32 - int(net_size)

        net_mask = socket.inet_ntoa(struct.pack("!I", (1 << 32) - (1 << host_bits)))

        return net_mask

    def _break_ip_addr(self, ip_addr):
        ip = None
        net_size = None
        net_mask = None

        if "/" in ip_addr:
            ip, net_size = ip_addr.split("/")
            net_mask = self._get_net_mask(net_size)
        elif " " in ip_addr:
            ip, net_mask = ip_addr.split()
            net_size = self._get_net_size(net_mask)
        else:
            ip = ip_addr
            net_size = "32"
            net_mask = "255.255.255.255"

        return (ip, net_size, net_mask)

    # Function that checks given address and return True if address is valid ip address or (ip address and subnet)
    def _is_ip(self, ip_addr):
        try:
            ip, net_size, net_mask = self._break_ip_addr(ip_addr)
        except Exception as e:
            self.debug_print("Validation for ip_addr failed", e)
            return False

        # Validate ip address
        if not phantom.is_ip(ip):
            return False

        # Regex to validate the subnet
        reg_exp = re.compile(
            "^((128|192|224|240|248|252|254).0.0.0)|(255.(((0|128|192|224|240|248|252|254).0.0)"
            "|(255.(((0|128|192|224|240|248|252|254).0)|255.(0|128|192|224|240|248|252|254|255)))))$"
        )

        # Validate subnet
        if net_mask:
            if not reg_exp.match(net_mask):
                return False

        if net_size:
            try:
                net_size = int(net_size)
            except Exception:
                self.debug_print(f"net_size: {net_size} invalid int")
                return False

            if not (0 < net_size <= 32):
                return False

        return True

    def _make_rest_call(self, endpoint, body, action_result):
        config = self.get_config()

        url = self._base_url + endpoint

        try:
            response = requests.post(
                url,
                data=json.dumps(body),
                headers=self._headers,
                verify=config[phantom.APP_JSON_VERIFY],
                timeout=CHECKPOINT_DEFAULT_REQUEST_TIMEOUT,
            )
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, CHECKPOINT_ERR_DEVICE_CONNECTIVITY.format(e)), None

        try:
            resp_json = response.json()
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, CHECKPOINT_ERR_DEVICE_CONNECTIVITY_NOFORMAT), None

        if response.status_code != 200:
            action_result.set_status(phantom.APP_ERROR, CHECKPOINT_ERR_DEVICE_CONNECTIVITY.format(resp_json.get("message")))

            if resp_json.get("warnings"):
                for warning in resp_json.get("warnings"):
                    action_result.append_to_message("\nWARNING: {}".format(warning.get("message")))

            if resp_json.get("errors"):
                for error in resp_json.get("errors"):
                    action_result.append_to_message("\nERROR: {}".format(error.get("message")))

            if resp_json.get("blocking-errors"):
                for error in resp_json.get("blocking-errors"):
                    action_result.append_to_message("\nERROR: {}".format(error.get("message")))

            return action_result.get_status(), None

        return phantom.APP_SUCCESS, resp_json

    def _set_auth_sid(self, action_result):
        if not self._state.get("sid"):
            auth_status = self._login(action_result)
        else:
            self._headers["X-chkp-sid"] = self._state.get("sid")
            ret_val, resp_json = self._make_rest_call("show-session", {}, action_result)
            if not ret_val:
                auth_status = self._login(action_result)
            else:
                auth_status, resp_json = self._make_rest_call("keepalive", {}, action_result)

        return auth_status

    def _login(self, action_result):
        config = self.get_config()

        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._base_url)
        username = config[phantom.APP_JSON_USERNAME]
        password = config[phantom.APP_JSON_PASSWORD]
        domain = config.get(phantom.APP_JSON_DOMAIN)

        data = {"user": username, "password": password}

        if domain:
            data["domain"] = domain

        ret_val, resp_json = self._make_rest_call("login", data, action_result)

        if not ret_val:
            return action_result.get_status()

        self._state["sid"] = resp_json.get("sid")

        self._headers["X-chkp-sid"] = self._state.get("sid")

        self.save_state(self._state)

        return phantom.APP_SUCCESS

    def _logout(self, action_result):
        ret_val, resp_json = self._make_rest_call("logout", {}, action_result)

        if phantom.is_fail(ret_val):
            self.save_progress(f"Failed to logout: {action_result.get_status_message()}")
            return action_result.get_status(), action_result.get_status_message()

        return phantom.APP_SUCCESS, "Successfully logged out of session"

    def _logout_session(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._set_auth_sid(action_result):
            return action_result.get_status()

        sid_to_logout = param.get("session_id", self._state.get("sid"))

        self._headers["X-chkp-sid"] = sid_to_logout

        ret_val, msg = self._logout(self)

        self._headers["X-chkp-sid"] = self._state.get("sid")

        self.save_progress(msg)

        return action_result.set_status(phantom.APP_SUCCESS if ret_val else phantom.APP_ERROR, msg)

    def _publish_and_wait(self, action_result):
        MAX_ITER = 10
        SLEEP_TIME = 6

        ret_val, resp_json = self._make_rest_call("publish", {}, action_result)

        if not ret_val and not resp_json:
            return action_result.get_status()

        task_id = resp_json.get("task-id")

        count = 0
        while True:
            if count >= MAX_ITER:
                return False

            time.sleep(SLEEP_TIME)
            count += 1

            ret_val, resp_json = self._make_rest_call("show-task", {"task-id": task_id}, action_result)

            if not ret_val and not resp_json:
                continue

            if resp_json.get("tasks", [{}])[0].get("status") == "succeeded":
                return True

    def _check_for_object(self, name, ip, length, action_result):
        endpoint = "show-hosts"
        if length != "32":
            endpoint = "show-networks"

        body = {"details-level": "full"}

        ret_val, resp_json = self._make_rest_call(endpoint, body, action_result)

        if not ret_val:
            return None

        found_name = False
        found_object = False
        for net_obj in resp_json.get("objects"):
            if name == net_obj.get("name"):
                found_name = True
                break

            if length == "32":
                if ip == net_obj.get("ipv4-address"):
                    found_object = True
                    name = net_obj.get("name")
                    break

            else:
                if ip == net_obj.get("subnet4") and length == net_obj.get("mask-length4"):
                    found_object = True
                    name = net_obj.get("name")
                    break

        if found_name or found_object:
            return name

        return ""

    def _check_for_rule(self, name, layer, action_result):
        endpoint = "show-access-rulebase"

        body = {"name": layer}

        ret_val, resp_json = self._make_rest_call(endpoint, body, action_result)

        if not ret_val:
            return None

        for rule in resp_json.get("rulebase"):
            if name == rule.get("name"):
                return True

        return False

    def _test_connectivity(self, param):
        # Progress
        self.save_progress(CHECKPOINT_PROG_USING_BASE_URL, base_url=self._base_url)

        status = self._set_auth_sid(self)

        if phantom.is_fail(status):
            self.append_to_message(CHECKPOINT_ERR_CONNECTIVITY_TEST)
            return self.get_status()

        return self.set_status_save_progress(phantom.APP_SUCCESS, CHECKPOINT_SUCC_CONNECTIVITY_TEST)

    def _list_policies(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._set_auth_sid(action_result):
            return action_result.get_status()

        endpoint = "show-packages"

        ret_val, resp_json = self._make_rest_call(endpoint, {}, action_result)

        if not ret_val:
            return action_result.get_status()

        policy_list = []

        for policy in resp_json.get("packages"):
            policy_list.append(policy.get("name"))

        num_policies = len(policy_list)

        if num_policies:
            message = "Successfully found {} polic{}".format(num_policies, "y" if num_policies == 1 else "ies")
            action_result.add_data(resp_json)

        else:
            message = "Found no policies"

        self.save_progress(message)

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _list_layers(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._set_auth_sid(action_result):
            return action_result.get_status()

        endpoint = "show-access-layers"

        ret_val, resp_json = self._make_rest_call(endpoint, {}, action_result)

        if not ret_val:
            return action_result.get_status()

        layer_list = []

        for layer in resp_json.get("access-layers"):
            layer_list.append(layer.get("name"))

        num_layers = len(layer_list)

        if num_layers:
            message = "Successfully found {} layer{}".format(num_layers, "" if num_layers == 1 else "s")
            action_result.add_data(resp_json)

        else:
            message = "Found no layers"

        self.save_progress(message)

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _block_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._set_auth_sid(action_result):
            return action_result.get_status()

        ip, length, mask = self._break_ip_addr(param.get(phantom.APP_JSON_IP))

        layer = param.get("layer")
        policy = param.get("policy")
        skip_install_policy = param.get("skip_install_policy")
        object_name_param = param.get("object_name")

        object_name = f"phantom - {ip}/{length}"

        new_name = self._check_for_object(object_name, ip, length, action_result)

        if new_name is None:
            return action_result.get_status()

        if new_name == object_name:
            self.save_progress(f"{object_name} object already exist.")
        else:
            if new_name != "":
                object_name = new_name

            if object_name_param:
                object_name = object_name_param

            else:
                body = {"name": object_name}

                endpoint = "add-host"
                json_field = "ip-address"

                if length != "32":
                    endpoint = "add-network"
                    json_field = "subnet"
                    body["mask-length"] = length

                body[json_field] = ip

                ret_val, resp_json = self._make_rest_call(endpoint, body, action_result)

                if not ret_val and not resp_json:
                    return action_result.get_status()

        ret_val = self._check_for_rule(object_name, layer, action_result)

        if ret_val is None:
            return action_result.get_status()

        if ret_val:
            self.save_progress("IP already blocked. Taking no action.")
            return action_result.set_status(phantom.APP_SUCCESS, "IP already blocked. Taking no action.")

        body = {"position": "top", "layer": layer, "action": "Drop", "destination": object_name, "name": object_name}

        ret_val, resp_json = self._make_rest_call("add-access-rule", body, action_result)

        if not ret_val and not resp_json:
            return action_result.get_status()

        action_result.add_data(resp_json)

        if not self._publish_and_wait(action_result):
            return action_result.set_status(phantom.APP_ERROR, "Could not publish session after changes")

        if not skip_install_policy:
            ret_val, resp_json = self._make_rest_call("install-policy", {"policy-package": policy}, action_result)

            if not ret_val and not resp_json:
                return action_result.get_status()

        self.save_progress("Successfully blocked {}".format("subnet" if length != "32" else "IP"))

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully blocked {}".format("subnet" if length != "32" else "IP"))

    def _unblock_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._set_auth_sid(action_result):
            return action_result.get_status()

        ip, length, mask = self._break_ip_addr(param.get(phantom.APP_JSON_IP))

        layer = param.get("layer")
        policy = param.get("policy")

        object_name = f"phantom - {ip}/{length}"

        ret_val = self._check_for_rule(object_name, layer, action_result)

        if ret_val is None:
            return action_result.get_status()

        if not ret_val:
            self.save_progress("IP not blocked. Taking no action.")
            return action_result.set_status(phantom.APP_SUCCESS, "IP not blocked. Taking no action.")

        body = {"layer": layer, "name": object_name}

        ret_val, resp_json = self._make_rest_call("delete-access-rule", body, action_result)

        if not ret_val and not resp_json:
            return action_result.get_status()

        action_result.add_data(resp_json)

        if not self._publish_and_wait(action_result):
            return action_result.set_status(phantom.APP_ERROR, "Could not publish session after changes")

        ret_val, resp_json = self._make_rest_call("install-policy", {"policy-package": policy}, action_result)

        if not ret_val and not resp_json:
            return action_result.get_status()

        self.save_progress("Successfully unblocked {}".format("subnet" if length != "32" else "IP"))

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully unblocked {}".format("subnet" if length != "32" else "IP"))

    def _list_hosts(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._set_auth_sid(action_result):
            return action_result.get_status()

        endpoint = "show-hosts"

        ret_val, resp_json = self._make_rest_call(endpoint, {}, action_result)

        if not ret_val and not resp_json:
            return action_result.get_status()

        action_result.add_data(resp_json)

        total_num_hosts = 0

        if resp_json.get("total"):
            total_num_hosts = resp_json.get("total")
            action_result.update_summary({"total_number_of_hosts": total_num_hosts})
            message = "Successfully found {} host{}".format(total_num_hosts, "" if total_num_hosts == 1 else "s")
        else:
            message = "Found no hosts"

        self.save_progress(message)

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _add_host(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._set_auth_sid(action_result):
            return action_result.get_status()

        ip = param.get(phantom.APP_JSON_IP)
        ipv4 = param.get("ipv4")
        ipv6 = param.get("ipv6")
        name = param["name"]
        comments = param.get("comments")
        groups = param.get("groups")

        endpoint = "add-host"

        body = {"name": name}

        if comments:
            body["comments"] = comments

        if groups:
            groups_list = [x.strip() for x in groups.split(",")]
            groups_list = list(filter(None, groups_list))
            if groups_list:
                body["groups"] = groups_list

        if ip:
            body["ip-address"] = ip
        elif ipv4 and ipv6:
            body["ipv4-address"] = ipv4
            body["ipv6-address"] = ipv6
        elif ipv4:
            body["ipv4-address"] = ipv4
        elif ipv6:
            body["ipv6-address"] = ipv6
        else:
            return action_result.set_status(phantom.APP_ERROR, "You must specify an ip address")

        ret_val, resp_json = self._make_rest_call(endpoint, body, action_result)

        if not ret_val and not resp_json:
            return action_result.get_status()

        action_result.add_data(resp_json)

        if not self._publish_and_wait(action_result):
            return action_result.set_status(phantom.APP_ERROR, "Could not publish session after changes")

        message = "Successfully added host"

        self.save_progress(message)

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _delete_host(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._set_auth_sid(action_result):
            return action_result.get_status()

        name = param.get("name")
        uid = param.get("uid")

        endpoint = "delete-host"

        if uid:
            ret_val, resp_json = self._make_rest_call(endpoint, {"uid": uid}, action_result)
        elif name:
            ret_val, resp_json = self._make_rest_call(endpoint, {"name": name}, action_result)
        else:
            return action_result.set_status(phantom.APP_ERROR, "You must specify the host name or unique identifier")

        if not ret_val and not resp_json:
            return action_result.get_status()

        action_result.add_data(resp_json)

        if not self._publish_and_wait(action_result):
            return action_result.set_status(phantom.APP_ERROR, "Could not publish session after changes")

        message = "Successfully deleted host"

        self.save_progress(message)

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _update_group_members(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._set_auth_sid(action_result):
            return action_result.get_status()

        name = param.get("name")
        uid = param.get("uid")
        members = param["members"]
        action = param["action"]

        members = [x.strip() for x in members.split(",")]
        members = list(filter(None, members))
        if members:
            members_object = {action: members} if action in ["add", "remove"] else members
            members_payload = {"members": members_object}
        else:
            return action_result.set_status(phantom.APP_ERROR, "Please enter valid members")

        endpoint = "set-group"

        if uid:
            ret_val, resp_json = self._make_rest_call(endpoint, {**members_payload, "uid": uid}, action_result)
        elif name:
            ret_val, resp_json = self._make_rest_call(endpoint, {**members_payload, "name": name}, action_result)
        else:
            return action_result.set_status(phantom.APP_ERROR, "You must specify the host name or unique identifier")

        if not ret_val and not resp_json:
            return action_result.get_status()

        action_result.add_data(resp_json)

        if not self._publish_and_wait(action_result):
            return action_result.set_status(phantom.APP_ERROR, "Could not publish session after changes")

        message = "Successfully updated group"

        self.save_progress(message)

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _add_network(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._set_auth_sid(action_result):
            return action_result.get_status()

        name = param["name"]

        subnet = param.get("subnet")
        subnet_v4 = param.get("subnet_v4")
        subnet_v6 = param.get("subnet_v6")

        subnet_mask_length = param.get("subnet_mask_length")
        subnet_mask_length_v4 = param.get("subnet_mask_length_v4")
        subnet_mask_length_v6 = param.get("subnet_mask_length_v6")

        subnet_mask = param.get("subnet_mask")
        comments = param.get("comments")
        groups = param.get("groups")

        endpoint = "add-network"

        body = {"name": name}

        if comments:
            body["comments"] = comments

        if groups:
            groups_list = [x.strip() for x in groups.split(",")]
            groups_list = list(filter(None, groups_list))
            if groups_list:
                body["groups"] = groups_list

        if subnet:
            body["subnet"] = subnet
        elif subnet_v4 and subnet_v6:
            body["subnet4"] = subnet_v4
            body["subnet6"] = subnet_v6
        elif subnet_v4:
            body["subnet4"] = subnet_v4
        elif subnet_v6:
            body["subnet6"] = subnet_v6
        else:
            return action_result.set_status(phantom.APP_ERROR, "You must specify a subnet")

        if subnet_mask_length:
            body["mask-length"] = subnet_mask_length
        elif subnet_mask_length_v4 and subnet_mask_length_v6:
            body["mask-length4"] = subnet_mask_length_v4
            body["mask-length6"] = subnet_mask_length_v6
        elif subnet_mask_length_v4:
            body["mask-length4"] = subnet_mask_length_v4
        elif subnet_mask_length_v6:
            body["mask-length6"] = subnet_mask_length_v6
        elif subnet_mask:
            body["subnet-mask"] = subnet_mask
        else:
            return action_result.set_status(phantom.APP_ERROR, "You must specify a subnet mask length or subnet mask")

        ret_val, resp_json = self._make_rest_call(endpoint, body, action_result)

        if not ret_val and not resp_json:
            return action_result.get_status()

        action_result.add_data(resp_json)

        if not self._publish_and_wait(action_result):
            return action_result.set_status(phantom.APP_ERROR, "Could not publish session after changes")

        message = "Successfully added network"

        self.save_progress(message)

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _delete_network(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._set_auth_sid(action_result):
            return action_result.get_status()

        name = param.get("name")
        uid = param.get("uid")

        endpoint = "delete-network"

        if uid:
            ret_val, resp_json = self._make_rest_call(endpoint, {"uid": uid}, action_result)
        elif name:
            ret_val, resp_json = self._make_rest_call(endpoint, {"name": name}, action_result)
        else:
            return action_result.set_status(phantom.APP_ERROR, "You must specify the network name or unique identifier")

        if not ret_val and not resp_json:
            return action_result.get_status()

        action_result.add_data(resp_json)

        if not self._publish_and_wait(action_result):
            return action_result.set_status(phantom.APP_ERROR, "Could not publish session after changes")

        message = "Successfully deleted network"

        self.save_progress(message)

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _install_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._set_auth_sid(action_result):
            return action_result.get_status()

        policy = param["policy"]
        targets = param["targets"]
        access = param.get("access")

        targets = [x.strip() for x in targets.split(",")]
        targets = list(filter(None, targets))
        if targets:
            body = {"policy-package": policy, "targets": targets}
        else:
            return action_result.set_status(phantom.APP_ERROR, "Please enter valid targets")

        endpoint = "install-policy"

        if access:
            body["access"] = access

        ret_val, resp_json = self._make_rest_call(endpoint, body, action_result)

        action_result.add_data(resp_json)

        if not ret_val and not resp_json:
            return action_result.get_status()

        message = "Successfully submitted policy installation"

        self.save_progress(message)

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _add_user(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._set_auth_sid(action_result):
            return action_result.get_status()

        name = param["name"]
        template = param["template"]
        email = param.get("email")
        phone_number = param.get("phone_number")
        comments = param.get("comments")

        endpoint = "add-user"

        body = {"name": name, "template": template}

        if email:
            body["email"] = email
        if phone_number:
            body["phone-number"] = phone_number
        if comments:
            body["comments"] = comments

        ret_val, resp_json = self._make_rest_call(endpoint, body, action_result)

        action_result.add_data(resp_json)

        if not ret_val and not resp_json:
            return action_result.get_status()

        if not self._publish_and_wait(action_result):
            return action_result.set_status(phantom.APP_ERROR, "Could not publish session after changes")

        message = "Successfully created user"

        self.save_progress(message)

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _delete_user(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if not self._set_auth_sid(action_result):
            return action_result.get_status()

        name = param.get("name")
        uid = param.get("uid")

        endpoint = "delete-user"

        if uid:
            ret_val, resp_json = self._make_rest_call(endpoint, {"uid": uid}, action_result)
        elif name:
            ret_val, resp_json = self._make_rest_call(endpoint, {"name": name}, action_result)
        else:
            return action_result.set_status(phantom.APP_ERROR, "You must specify the user name or unique identifier")

        if not ret_val and not resp_json:
            return action_result.get_status()

        action_result.add_data(resp_json)

        if not self._publish_and_wait(action_result):
            return action_result.set_status(phantom.APP_ERROR, "Could not publish session after changes")

        message = "Successfully deleted user"

        self.save_progress(message)

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def handle_action(self, param):
        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()
        result = None

        self._param = param

        if action_id == self.ACTION_ID_TEST_CONNECTIVITY:
            result = self._test_connectivity(param)
        elif action_id == self.ACTION_ID_BLOCK_IP:
            result = self._block_ip(param)
        elif action_id == self.ACTION_ID_UNBLOCK_IP:
            result = self._unblock_ip(param)
        elif action_id == self.ACTION_ID_LIST_LAYERS:
            result = self._list_layers(param)
        elif action_id == self.ACTION_ID_LIST_POLICIES:
            result = self._list_policies(param)
        elif action_id == self.ACTION_ID_LOGOUT_SESSION:
            result = self._logout_session(param)
        elif action_id == self.ACTION_ID_DELETE_HOST:
            result = self._delete_host(param)
        elif action_id == self.ACTION_ID_LIST_HOSTS:
            result = self._list_hosts(param)
        elif action_id == self.ACTION_ID_ADD_HOST:
            result = self._add_host(param)
        elif action_id == self.ACTION_ID_ADD_NETWORK:
            result = self._add_network(param)
        elif action_id == self.ACTION_ID_DELETE_NETWORK:
            result = self._delete_network(param)
        elif action_id == self.ACTION_ID_INSTALL_POLICY:
            result = self._install_policy(param)
        elif action_id == self.ACTION_ID_ADD_USER:
            result = self._add_user(param)
        elif action_id == self.ACTION_ID_DELETE_USER:
            result = self._delete_user(param)
        elif action_id == self.ACTION_ID_UPDATE_GROUP_MEMBERS:
            result = self._update_group_members(param)

        return result


if __name__ == "__main__":
    import sys

    # import pudb
    # pudb.set_trace()

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = CheckpointConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
