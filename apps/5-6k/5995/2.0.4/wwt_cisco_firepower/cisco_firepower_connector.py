# File: cisco_firepower_connector.py
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

import encryption_helper
import phantom.app as phantom
import requests
import simplejson as json
from netaddr import ZEROFILL, IPAddress, IPNetwork
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from cisco_firepower_consts import *


class FP_Connector(BaseConnector):
    def __init__(self):
        """
        Instance variables
        """
        # Call the BaseConnectors init first
        super().__init__()

        self.username = ""
        self.password = ""
        self.firepower_host = ""
        self.firepower_devices = []
        self.firepower_deployable_devices = []
        self.network_group_object = ""
        self.domain_name = ""
        self.destination_network = ""
        self.destination_dict = {}
        self.token = ""
        self.api_path = ""
        self.network_group_list = []
        self.domain_uuid = ""
        self.netgroup_uuid = ""
        self.headers = HEADERS
        self.verify = False
        self.nothing_to_deploy = False
        self.ip_version = None
        self.generate_new_token = False

    def _reset_state_file(self):
        """
        This method resets the state file.
        """
        self.debug_print("Resetting the state file with the default format")
        self._state = {"app_version": self.get_app_json().get("app_version")}

    def initialize(self):
        """
        Initializes the global variables and validates them.

        This is an optional function that can be implemented by the
        AppConnector derived class. Since the configuration dictionary
        is already validated by the time this function is called,
        it's a good place to do any extra initialization of any internal
        modules. This function MUST return a value of either
        phantom.APP_SUCCESS or phantom.APP_ERROR.  If this function
        returns phantom.APP_ERROR, then AppConnector::handle_action
        will not get called.
        """
        config = self.get_config()
        self._state = self.load_state()

        if not isinstance(self._state, dict):
            self.debug_print(STATE_FILE_CORRUPT_ERR)
            self._reset_state_file()

        self.asset_id = self.get_asset_id()
        try:
            if TOKEN_KEY in self._state:
                self.debug_print("Decrypting the token")
                self._state[TOKEN_KEY] = encryption_helper.decrypt(self._state[TOKEN_KEY], self.asset_id)
        except Exception as e:
            self.debug_print(f"Error occurred while decrypting the token: {e!s}")
            self._reset_state_file()

        self.firepower_host = config["firepower_host"]
        self.username = config["username"]
        self.password = config["password"]
        self.domain_name = config["domain_name"].lower()
        self.network_group_object = config["network_group_object"]
        self.verify = config.get("verify_server_cert", False)

        force = True if self.get_action_identifier() == "test_connectivity" else False
        ret_val = self._get_token(self, force=force)
        if phantom.is_fail(ret_val):
            return self.get_status()

        ret_val = self._get_group_object_uuid()
        if phantom.is_fail(ret_val):
            return self.get_status()

        return phantom.APP_SUCCESS

    def finalize(self):
        """
        Performs some final operations or clean up operations.

        This function gets called once all the param dictionary
        elements are looped over and no more handle_action calls are
        left to be made. It gives the AppConnector a chance to loop
        through all the results that were accumulated by multiple
        handle_action function calls and create any summary if
        required. Another usage is cleanup, disconnect from remote
        devices etc.
        """
        try:
            if TOKEN_KEY in self._state:
                self.debug_print("Encrypting the token")
                self._state[TOKEN_KEY] = encryption_helper.encrypt(self._state[TOKEN_KEY], self.asset_id)
        except Exception as e:
            self.debug_print(f"{ENCRYPTION_ERR}: {e!s}")
            self._reset_state_file()

        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _get_group_object_uuid(self):
        """
        This method is responsible for getting the UUID associated with
        the network group object specified in the app config and setting
        the netgroup_uuid variable.
        """
        self.api_path = NETWORK_GROUPS_ENDPOINT.format(self.domain_uuid)
        self.debug_print(f"api_path: {self.api_path}")

        offset = 0
        limit = 50
        params = {"limit": limit}
        while True:
            params["offset"] = offset
            ret_val, response = self._api_run("get", self.api_path, self, params=params)
            if phantom.is_fail(ret_val):
                return self.get_status()
            self.debug_print(f"the response is {response}")

            try:
                network_group_list = response["items"]
                for item in network_group_list:
                    if item["name"] == self.network_group_object:
                        self.netgroup_uuid = item["id"]
            except Exception as e:
                message = "An error occurred while processing network groups"
                self.debug_print(f"{message}. {e!s}")
                return self.set_status(phantom.APP_ERROR, message)

            if self.netgroup_uuid:
                return phantom.APP_SUCCESS

            if "paging" in response and "next" in response["paging"]:
                offset += limit
            else:
                break

        return self.set_status(phantom.APP_ERROR, "Please provide a valid value in the 'Network Group Object' parameter")

    def _get_group_object_networks(self, action_result):
        """
        This method fetches the network groups for the
        network group object specified in the app config and
        sets the network_group_list variable.
        """
        # Get the current list of static routes from the Target Host
        self.api_path = HOST_NETWORK_GROUPS_ENDPOINT.format(self.domain_uuid, self.netgroup_uuid)
        self.debug_print(f"api_path: {self.api_path}")

        ret_val, response = self._api_run("get", self.api_path, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.network_group_list = response.get("literals", [])
        return phantom.APP_SUCCESS

    def _get_firepower_deployable_devices(self, action_result):
        """
        This method is fetches the deployable devices and
        adds them to the firepower_deployable_devices variable.
        """
        # Get the current list of devices in the domain
        self.api_path = DEPLOYABLE_DEVICES_ENDPOINT.format(self.domain_uuid, LIMIT, EXPANDED)
        self.debug_print(f"api_path: {self.api_path}")

        ret_val, response = self._api_run("get", self.api_path, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            items = response.get("items")
            if not items:
                self.nothing_to_deploy = True
                return phantom.APP_SUCCESS
            for item in items:
                self.firepower_deployable_devices.append({"name": item["device"]["name"], "id": item["device"]["id"]})
        except Exception as e:
            message = "An error occurred while processing deployable devices"
            self.debug_print(f"{message}. {e!s}")
            return action_result.set_status(phantom.APP_ERROR, message)

        return phantom.APP_SUCCESS

    def _update_state(self):
        """
        This method updates the state with the new values.
        """
        self._state[TOKEN_KEY] = self.token
        self._state[DOMAIN_UUID_KEY] = self.domain_uuid
        self._state[DOMAIN_NAME_KEY] = self.domain_name

    def _get_token(self, action_result, force=False):
        """
        This method returns the cached or a new token based
        on the values present in the state file.
        """
        self.token = self._state.get(TOKEN_KEY)
        self.domain_uuid = self._state.get(DOMAIN_UUID_KEY)
        self.domain = self._state.get(DOMAIN_NAME_KEY)

        if not force and self.token and self.domain_uuid and self.domain_name == self.domain.lower():
            self.headers.update({"X-auth-access-token": self.token})
            return phantom.APP_SUCCESS

        # Generate a new token
        self.generate_new_token = True
        self.debug_print("Fetching a new token")
        ret_val, headers = self._api_run("post", TOKEN_ENDPOINT, action_result, headers_only=True, first_try=False)
        if phantom.is_fail(ret_val):
            self._reset_state_file()
            return action_result.get_status()

        self.token = headers.get("X-auth-access-token")
        self.domain_uuid = None
        try:
            domains = json.loads(headers.get("DOMAINS"))
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Received unexpected response from the server")

        for domain in domains:
            if self.domain_name in domain["name"].lower():
                self.domain_uuid = domain["uuid"]
                break

        if not self.domain_uuid:
            return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in the 'Firepower Domain' parameter")

        self.headers.update({"X-auth-access-token": self.token})
        self._update_state()

        return phantom.APP_SUCCESS

    def _api_run(self, method, resource, action_result, json_body=None, headers_only=False, first_try=True, params=None):
        """
        This method makes a REST call to the API
        """
        request_method = getattr(requests, method)
        url = f"https://{self.firepower_host}{resource}"
        if json_body:
            self.headers.update({"Content-type": "application/json"})

        auth = None
        if self.generate_new_token:
            auth = requests.auth.HTTPBasicAuth(self.username, self.password)
            self.generate_new_token = False

        try:
            result = request_method(
                url, auth=auth, headers=self.headers, json=json_body, verify=self.verify, params=params, timeout=DEFAULT_REQUEST_TIMEOUT
            )
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error connecting to server. {e!s}"), None

        if not (200 <= result.status_code < 399):
            if result.status_code == 401 and first_try:
                ret_val = self._get_token(action_result, True)
                if phantom.is_fail(ret_val):
                    return action_result.get_status(), None

                return self._api_run(method, resource, action_result, json_body, headers_only, first_try=False)

            message = "Error from server. Status Code: {} Data from server: {}".format(
                result.status_code, result.text.replace("{", "{{").replace("}", "}}")
            )

            return action_result.set_status(phantom.APP_ERROR, message), None

        if headers_only:
            return phantom.APP_SUCCESS, result.headers

        resp_json = None
        try:
            resp_json = result.json()
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. {e!s}"), None

        if not resp_json:
            return (
                action_result.set_status(phantom.APP_ERROR, f"Status code: {result.status_code}. Received empty response from the server"),
                None,
            )

        return phantom.APP_SUCCESS, resp_json

    def _validate_ip(self):
        """
        This method validates the IP
        """
        try:
            # Shorten the IP address
            network_parts = self.destination_network.lower().split("/")
            ip = IPAddress(network_parts[0], flags=ZEROFILL)
            self.ip_version = ip.version
            network_parts[0] = str(ip)
            self.destination_network = "/".join(network_parts)

            ip_net = IPNetwork(self.destination_network)
        except Exception:
            return False
        if ip_net.network != ip_net.ip:
            self.destination_network = f"{ip_net.network}/{ip_net.prefixlen}"
        return True

    def _gen_network_dict(self):
        """
        This method generates a network dictionary
        from the ip parameter value.
        """
        ip_and_mask = self.destination_network.split("/")
        if (
            len(ip_and_mask) == 1
            or (self.ip_version == 4 and int(ip_and_mask[1]) == 32)
            or (self.ip_version == 6 and int(ip_and_mask[1]) == 128)
        ):
            self.debug_print("IP is type Host")
            self.destination_dict = {"type": "Host", "value": str(self.destination_network)}
        elif len(ip_and_mask) == 2:
            self.debug_print("IP is type Network")
            self.destination_dict = {"type": "Network", "value": str(self.destination_network)}
        self.debug_print("Network Dictionary: {str(self.destination_dict)}")

    def _deploy_config(self, action_result):
        """
        This method creates a deploy request for the deployable devices present in the firepower_deployable_devices list.
        """
        ret_val = self._get_firepower_deployable_devices(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if self.nothing_to_deploy:
            self.debug_print("Nothing to deploy")
            return phantom.APP_SUCCESS

        deployable_device_UUIDs = [device["id"] for device in self.firepower_deployable_devices]

        self.api_path = DEPLOYMENT_REQUESTS_ENDPOINT.format(self.domain_uuid)
        self.debug_print(f"api_path: {self.api_path}")

        body = {
            "type": "DeploymentRequest",
            "version": "0",
            "forceDeploy": True,
            "ignoreWarning": True,
            "deviceList": (deployable_device_UUIDs),
        }

        ret_val, response = self._api_run("post", self.api_path, action_result, body)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.network_group_list = response.get("literals", [])
        return phantom.APP_SUCCESS

    def _handle_test_connectivity(self, param):
        """
        Called when the user presses the test connectivity
        button on the Phantom UI.
        """
        # Add an action result to the App Run
        action_result = ActionResult(dict(param))
        self.add_action_result(action_result)

        self.save_progress("Testing connectivity")

        if self.token:
            self.save_progress("Connectivity test passed")
            return action_result.set_status(phantom.APP_SUCCESS)

        self.save_progress("Connectivity test failed")
        return action_result.set_status(phantom.APP_ERROR)

    def _handle_list_networks(self, param):
        """
        This method lists currently blocked networks
        of a network group.
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result to the App Run
        action_result = ActionResult(dict(param))
        self.add_action_result(action_result)

        # Initializes the current networks and sets the URL
        ret_val = self._get_group_object_networks(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            if self.network_group_list:
                for net in self.network_group_list:
                    action_result.add_data({"network": net["value"]})
        except Exception as e:
            message = "An error occurred while processing the networks"
            self.debug_print(f"{message}. {e!s}")
            return action_result.set_status(phantom.APP_ERROR, message)

        summary = {"total_routes": len(self.network_group_list)}
        action_result.update_summary(summary)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_block_ip(self, param):
        """
        This method blocks an IP/network.
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result to the App Run
        action_result = ActionResult(dict(param))
        self.add_action_result(action_result)

        # Initializes the current networks and sets the URL
        ret_val = self._get_group_object_networks(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.destination_network = param["ip"]

        if self._validate_ip():
            self._gen_network_dict()
        else:
            return action_result.set_status(phantom.APP_ERROR, f"Invalid IP: {self.destination_network}")

        if self.destination_dict in self.network_group_list:
            return action_result.set_status(phantom.APP_SUCCESS, f"{self.destination_network} is already present in the blocklist")

        self.network_group_list.append(self.destination_dict)

        body = {"id": self.netgroup_uuid, "name": self.network_group_object, "literals": (self.network_group_list)}

        ret_val, _ = self._api_run("put", self.api_path, action_result, body)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val = self._deploy_config(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully added {self.destination_network}")

    def _handle_unblock_ip(self, param):
        """
        This method unblocks an IP/network.
        """
        # Add an action result to the App Run
        action_result = ActionResult(dict(param))
        self.add_action_result(action_result)

        # Initializes the current networks and sets the URL
        ret_val = self._get_group_object_networks(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.destination_network = param["ip"]

        if self._validate_ip():
            self._gen_network_dict()
        else:
            return action_result.set_status(phantom.APP_ERROR, f"Invalid IP: {self.destination_network}")

        if self.destination_dict not in self.network_group_list:
            return action_result.set_status(phantom.APP_SUCCESS, f"{self.destination_network} is not present in the blocklist")

        self.network_group_list.remove(self.destination_dict)

        body = {"id": self.netgroup_uuid, "name": self.network_group_object, "literals": (self.network_group_list)}

        ret_val, _ = self._api_run("put", self.api_path, action_result, body)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val = self._deploy_config(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully deleted {self.destination_network}")

    def handle_action(self, param):
        """
        This function implements the main functionality of the AppConnector.
        It gets called for every param dictionary element in the parameters
        array. In it's simplest form it gets the current action identifier
        and then calls a member function of it's own to handle the action.
        This function is expected to create the results of the action run
        that get added to the connector run. The return value of this function
        is mostly ignored by the BaseConnector. Instead it will just loop
        over the next param element in the parameters array and call
        handle_action again.

        We create a case structure in Python to allow for any number of
        actions to be easily added.
        """
        # action_id determines what function to execute
        action_id = self.get_action_identifier()
        self.debug_print(f"action_id: {action_id}")

        supported_actions = {
            "test_connectivity": self._handle_test_connectivity,
            "list_networks": self._handle_list_networks,
            "block_ip": self._handle_block_ip,
            "unblock_ip": self._handle_unblock_ip,
        }

        run_action = supported_actions[action_id]

        return run_action(param)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    # input a json file that contains data like the configuration and action parameters
    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = FP_Connector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
