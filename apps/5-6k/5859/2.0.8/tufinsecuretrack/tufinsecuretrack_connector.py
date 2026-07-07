# File: tufinsecuretrack_connector.py
#
# Copyright (c) 2018-2025 Splunk Inc.
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
import json
import re
import string

import phantom.app as phantom
import requests
import xmltodict
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Local imports
import tufinsecuretrack_consts as consts


# Dictionary that maps each error code with its corresponding message
ERROR_RESPONSE_DICT = {
    consts.TUFINSECURETRACK_REST_RESP_UNAUTHORIZED: consts.TUFINSECURETRACK_REST_RESP_UNAUTHORIZED_MSG,
    consts.TUFINSECURETRACK_REST_RESP_BAD_REQUEST: consts.TUFINSECURETRACK_REST_RESP_BAD_REQUEST_MSG,
    consts.TUFINSECURETRACK_REST_RESP_NOT_FOUND: consts.TUFINSECURETRACK_REST_RESP_NOT_FOUND_MSG,
    consts.TUFINSECURETRACK_REST_RESP_FORBIDDEN: consts.TUFINSECURETRACK_REST_RESP_FORBIDDEN_MSG,
}


def _break_ip_address(cidr_ip_address):
    """Function divides the input parameter into IP address and network mask.

    :param cidr_ip_address: IP address in format of IP/prefix_size
    :return: IP, prefix_size
    """

    if "/" in cidr_ip_address:
        ip_address, prefix_size = cidr_ip_address.split("/")
    else:
        ip_address = cidr_ip_address
        prefix_size = 0

    return ip_address, prefix_size


class TufinSecureTrackConnector(BaseConnector):
    """This is an AppConnector class that inherits the BaseConnector class. It implements various actions supported by
    tufin and helper methods required to run the actions.
    """

    def __init__(self):
        # Calling the BaseConnector's init function
        super().__init__()
        self._url = None
        self._username = None
        self._password = None
        self._verify_server_cert = None

        return

    def initialize(self):
        """This is an optional function that can be implemented by the AppConnector derived class. Since the
        configuration dictionary is already validated by the time this function is called, it's a good place to do any
        extra initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS or
        phantom.APP_ERROR. If this function returns phantom.APP_ERROR, then AppConnector::handle_action will not get
        called.
        """

        config = self.get_config()
        self._url = config[consts.TUFINSECURETRACK_CONFIG_URL]
        self._username = config[consts.TUFINSECURETRACK_CONFIG_USERNAME]
        self._password = config[consts.TUFINSECURETRACK_CONFIG_PASSWORD]
        self._verify_server_cert = config.get(consts.TUFINSECURETRACK_CONFIG_VERIFY_SSL, False)

        # Custom validation for IP address
        self.set_validator("ip", self._is_ip)

        return phantom.APP_SUCCESS

    def _is_ip(self, cidr_ip_address):
        """Function that checks given address and return True if address is valid IPv4 address.

        :param cidr_ip_address: IP address
        :return: status (success/failure)
        """

        try:
            ip, net_mask = _break_ip_address(cidr_ip_address)
        except Exception as e:
            self.debug_print(consts.TUFINSECURETRACK_IP_VALIDATION_FAILED, e)
            return False

        # Validate IP address
        if not phantom.is_ip(ip):
            self.debug_print(consts.TUFINSECURETRACK_IP_VALIDATION_FAILED)
            return False

        if net_mask:
            if len(net_mask) <= 3:
                # Check if net mask is out of range
                if "." in ip and int(net_mask) not in list(range(0, 33)):
                    self.debug_print(consts.TUFINSECURETRACK_IP_VALIDATION_FAILED)
                    return False
            else:
                # Regex to validate the subnet
                reg_exp = re.compile(
                    "^((128|192|224|240|248|252|254).0.0.0)|(255.(((0|128|192|224|240|248|252|254).0.0)"
                    "|(255.(((0|128|192|224|240|248|252|254).0)|255.(0|128|192|224|240|248|252|254|255)))"
                    "))$"
                )
                if not reg_exp.match(net_mask):
                    return False
        return True

    def _make_rest_call(self, endpoint, action_result, params=None, method="get", timeout=None):
        """Function that makes the REST call to the device. It is a generic function that can be called from various
        action handlers.

        :param endpoint: REST endpoint that needs to appended to the service address
        :param action_result: object of ActionResult class
        :param params: request parameters if method is get
        :param method: get/post/put/delete ( Default method will be 'get' )
        :param timeout: timeout for request
        :return: status success/failure(along with appropriate message), response obtained by making an API call
        """

        response_data = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            self.debug_print(consts.TUFINSECURETRACK_ERR_API_UNSUPPORTED_METHOD.format(method=method))
            # set the action_result status to error, the handler function will most probably return as is
            return action_result.set_status(
                phantom.APP_ERROR, consts.TUFINSECURETRACK_ERR_API_UNSUPPORTED_METHOD.format(method=method)
            ), response_data
        except Exception as e:
            self.debug_print(consts.TUFINSECURETRACK_EXCEPTION_OCCURRED, e)
            # set the action_result status to error, the handler function will most probably return as is
            return action_result.set_status(phantom.APP_ERROR, consts.TUFINSECURETRACK_EXCEPTION_OCCURRED, e), response_data

        # Make the call
        try:
            response = request_func(
                f"{self._url}{endpoint}", params=params, auth=(self._username, self._password), verify=self._verify_server_cert, timeout=timeout
            )

            # store the r_text in debug data, it will get dumped in the logs if an error occurs
            if hasattr(action_result, "add_debug_data"):
                if response is not None:
                    action_result.add_debug_data({"r_status_code": response.status_code})
                    action_result.add_debug_data({"r_text": response.text})
                    action_result.add_debug_data({"r_headers": response.headers})
                else:
                    action_result.add_debug_data({"r_text": "r is None"})

        except Exception as e:
            self.debug_print(consts.TUFINSECURETRACK_ERR_SERVER_CONNECTION, e)
            # set the action_result status to error, the handler function will most probably return as is
            return action_result.set_status(phantom.APP_ERROR, consts.TUFINSECURETRACK_ERR_SERVER_CONNECTION, e), response_data

        # Try parsing the json
        try:
            content_type = response.headers.get("content-type", "")
            if "json" in content_type:
                response_data = response.json()
            elif "xml" in content_type:
                response_data = xmltodict.parse(response.text)
            elif "html" in content_type:
                response_data = self._process_html_response(response)
            else:
                response_data = response.text
        except Exception as e:
            # r.text is guaranteed to be NON None, it will be empty, but not None
            msg_string = consts.TUFINSECURETRACK_ERR_JSON_PARSE.format(raw_text=response.text)
            self.debug_print(msg_string, e)
            # set the action_result status to error, the handler function will most probably return as is
            return action_result.set_status(phantom.APP_ERROR, msg_string, e), response_data

        if response.status_code in ERROR_RESPONSE_DICT:
            message = ERROR_RESPONSE_DICT[response.status_code]

            # overriding message if available in response
            if isinstance(response_data, dict):
                message = response_data.get("result", {}).get("message", message)

            self.debug_print(consts.TUFINSECURETRACK_ERR_FROM_SERVER.format(status=response.status_code, detail=message))
            # set the action_result status to error, the handler function will most probably return as is
            return action_result.set_status(
                phantom.APP_ERROR, consts.TUFINSECURETRACK_ERR_FROM_SERVER, status=response.status_code, detail=message
            ), response_data

        # In case of success scenario
        if response.status_code == consts.TUFINSECURETRACK_REST_RESP_SUCCESS:
            # If response obtained is not in json format
            if not isinstance(response_data, dict):
                self.debug_print(consts.TUFINSECURETRACK_UNEXPECTED_RESPONSE)
                return action_result.set_status(phantom.APP_ERROR, consts.TUFINSECURETRACK_UNEXPECTED_RESPONSE), response_data

            response_data = {consts.TUFINSECURETRACK_REST_RESPONSE: response_data}
            return phantom.APP_SUCCESS, response_data

        # If response code is unknown
        message = consts.TUFINSECURETRACK_REST_RESP_OTHER_ERR_MSG

        # overriding message if available in response
        if isinstance(response_data, dict):
            message = response_data.get("result", {}).get("message", message)

        # If response code is unknown
        self.debug_print(consts.TUFINSECURETRACK_ERR_FROM_SERVER.format(status=response.status_code, detail=message))
        # All other response codes from REST call
        # Set the action_result status to error, the handler function will most probably return as is
        return action_result.set_status(
            phantom.APP_ERROR, consts.TUFINSECURETRACK_ERR_FROM_SERVER, status=response.status_code, detail=message
        ), response_data

    def _process_html_response(self, response):
        """This function is used to parse html response.

        :param response: actual response
        :return: error message
        """

        # An html response, treat it like an error

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        error_text = "".join([x for x in error_text if x in string.printable])
        message = f"{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")

        message = {"result": {"message": message}}

        return message

    def _test_asset_connectivity(self, param):
        """This function tests the connectivity of an asset with given credentials.

        :param param: (not used in this method)
        :return: status success/failure
        """

        action_result = ActionResult()

        self.save_progress(consts.TUFINSECURETRACK_CONNECTION_TEST_MSG)
        self.save_progress(f"Configured URL: {self._url}{consts.TUFINSECURETRACK_TEST_CONNECTIVITY_ENDPOINT}")

        # making call
        ret_value, _ = self._make_rest_call(consts.TUFINSECURETRACK_TEST_CONNECTIVITY_ENDPOINT, action_result, timeout=30)

        # something went wrong
        if phantom.is_fail(ret_value):
            self.save_progress(action_result.get_message())
            self.set_status(phantom.APP_ERROR, consts.TUFINSECURETRACK_TEST_CONNECTIVITY_FAILED)
            return action_result.get_status()

        self.set_status_save_progress(phantom.APP_SUCCESS, consts.TUFINSECURETRACK_TEST_CONNECTIVITY_PASS)

        return action_result.get_status()

    def _lookup_ip(self, param):
        """Function that lookup for given IP or subnet.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Getting mandatory parameter
        ip_address = param[consts.TUFINSECURETRACK_JSON_IP_ADDRESS]

        status, network_ids = self._get_network_ids(ip_address, action_result)

        # something went wrong
        if phantom.is_fail(status):
            return action_result.get_status()

        # when no match of given IP/subnet found
        if not network_ids:
            self.debug_print(consts.TUFINSECURETRACK_JSON_INVALID_IP_ADDRESS)
            return action_result.set_status(phantom.APP_ERROR, consts.TUFINSECURETRACK_JSON_INVALID_IP_ADDRESS)

        rules_list = []
        is_blocked = False

        for network_id, device_id in list(network_ids.items()):
            # Getting rules that IP/subnet falls in
            res_rule_status, rule_response = self._make_rest_call(
                consts.TUFINSECURETRACK_NETWORK_RULES_ENDPOINT.format(id=network_id), action_result
            )

            # something went wrong
            if phantom.is_fail(res_rule_status):
                return action_result.get_status()

            rule = rule_response[consts.TUFINSECURETRACK_REST_RESPONSE]["rules"].get("rule", {})
            dict_to_list = ["dst_network", "src_network", "additional_parameter", "install", "dst_service", "application", "users"]

            if rule and isinstance(rule, dict):
                rule = [rule]
            for data in rule:
                data["device_id"] = device_id
                for keys in dict_to_list:
                    if data.get(keys) and isinstance(data[keys], dict):
                        data[keys] = [data[keys]]
                if data.get("disabled") is False:
                    rules_list.append(data)

        sorted_rule_list = sorted(rules_list, key=lambda k: k["order"])

        if sorted_rule_list:
            if sorted_rule_list[0]["action"].lower() == "accept":
                is_blocked = False
            else:
                is_blocked = True

        for data in sorted_rule_list:
            action_result.add_data(data)

        if not action_result.get_data_size():
            return action_result.set_status(phantom.APP_SUCCESS, consts.TUFINSECURETRACK_NO_FIREWALL_RULE_CONFIGURED)

        # Update summary data
        summary_data["is_blocked"] = is_blocked
        summary_data["total_rules"] = action_result.get_data_size()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _check_connectivity(self, param):
        """This function is used to check connectivity between source and destination network.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Getting mandatory parameter
        src_ip = param.get(consts.TUFINSECURETRACK_JSON_SOURCE_IP_ADDRESS, "any")
        dest_ip = param.get(consts.TUFINSECURETRACK_JSON_DESTINATION_IP_ADDRESS, "any")
        protocol = (param.get(consts.TUFINSECURETRACK_JSON_PROTOCOL, "any")).lower()

        if src_ip == "any" and dest_ip == "any":
            return action_result.set_status(phantom.APP_ERROR, consts.TUFINSECURETRACK_MANDATORY_IP_PARAM)

        # Getting optional parameter
        port = param.get(consts.TUFINSECURETRACK_JSON_PORT)

        if port:
            try:
                port = int(port)
            except:
                return action_result.set_status(phantom.APP_ERROR, "Invalid port value.")

            if port < 0:
                return action_result.set_status(phantom.APP_ERROR, "Port values cannot be negative numbers. Please specify a valid port value.")

            protocol = f"{protocol}:{port}"

        # Set params to get firewall rules that allow traffic
        params = {"device_ids": "any", "sources": src_ip, "destinations": dest_ip, "services": protocol}

        status, is_allowed_traffic = self._get_matching_rule(params, action_result)

        if phantom.is_fail(status):
            return action_result.get_status()

        summary_data["allowed_traffic"] = is_allowed_traffic
        summary_data["total_rules"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_matching_rule(self, params, action_result):
        """This function is used to get matching rules.

        :param params: dictionary of input parameters
        :param action_result: object of ActionResult class
        :return: status success/failure
        """

        is_allowed_traffic = None

        # Querying endpoint to get firewall rule
        ip_res_status, ip_response = self._make_rest_call(consts.TUFINSECURETRACK_MATCHING_RULE_ENDPOINT, action_result, params=params)

        # something went wrong
        if phantom.is_fail(ip_res_status):
            return action_result.get_status(), is_allowed_traffic

        ip_response = ip_response[consts.TUFINSECURETRACK_REST_RESPONSE]

        res_device_and_bindings = (
            ip_response.get("policy_analysis_query_result", {}).get("devices_and_bindings", {}).get("device_and_bindings", {})
        )

        dict_to_list = ["dst_network", "src_network", "dst_service", "application", "users", "install"]

        if isinstance(res_device_and_bindings, dict):
            res_device_and_bindings = [res_device_and_bindings]

        rules_list = []

        for devices in res_device_and_bindings:
            device_name = devices.get("device", {}).get("name", "")
            device_id = devices.get("device", {}).get("id", "")
            bindings = devices.get("bindings_and_rules", {}).get("binding_and_rules", {})
            if isinstance(bindings, dict) and bindings:
                bindings = [bindings]
            for binding in bindings:
                rules = binding["rules"]["rule"]
                if isinstance(rules, dict) and rules:
                    rules = [rules]
                for data in rules:
                    for keys in dict_to_list:
                        if data.get(keys) and isinstance(data[keys], dict):
                            data[keys] = [data[keys]]
                    data["device_name"] = device_name
                    data["device_id"] = device_id
                    if data.get("disabled") is False:
                        rules_list.append(data)

        sorted_rule_list = sorted(rules_list, key=lambda k: k["order"])

        is_allowed_traffic = True
        if sorted_rule_list:
            if not sorted_rule_list[0]["action"].lower() == "accept":
                is_allowed_traffic = False

        for data in sorted_rule_list:
            action_result.add_data(data)

        return phantom.APP_SUCCESS, is_allowed_traffic

    def _get_network_ids(self, ip_address, action_result):
        """This function is used to query network object records.

        :param params: dictionary of input parameters
        :param action_result: object of ActionResult class
        :param ip_address: IP address
        :return: status success/failure
        """

        network_ids = {}

        if "/" not in ip_address:
            ip_address += "/32"

        for query_param in ["contains", "contained_in"]:
            params = {}
            params.update({"filter": "subnet", query_param: ip_address})

            res_status, response = self._make_rest_call(consts.TUFINSECURETRACK_NETWORK_OBJECT_ENDPOINT, action_result, params=params)

            # something went wrong
            if phantom.is_fail(res_status):
                return action_result.get_status(), None

            network_object = response[consts.TUFINSECURETRACK_REST_RESPONSE]["network_objects"].get("network_object", [])

            # Getting network IDs to fetch corresponding rule
            for nw_object in network_object:
                try:
                    network_ids.update({nw_object["id"]: nw_object["device_id"]})
                except:
                    pass

            # Handling data more than 100
            curr_cnt = response[consts.TUFINSECURETRACK_REST_RESPONSE]["network_objects"]["count"]
            total = response[consts.TUFINSECURETRACK_REST_RESPONSE]["network_objects"]["total"]

            while curr_cnt < total:
                params["start"] = curr_cnt
                res_status, response = self._make_rest_call(consts.TUFINSECURETRACK_NETWORK_OBJECT_ENDPOINT, action_result, params=params)
                # something went wrong
                if phantom.is_fail(res_status):
                    return action_result.get_status(), None

                network_objects = response[consts.TUFINSECURETRACK_REST_RESPONSE]["network_objects"].get("network_object", [])

                # Getting network IDs to fetch corresponding rule
                for nw_object in network_objects:
                    try:
                        network_ids.update({nw_object["id"]: nw_object["device_id"]})
                    except:
                        pass

                curr_cnt += response[consts.TUFINSECURETRACK_REST_RESPONSE]["network_objects"]["count"]

        return phantom.APP_SUCCESS, network_ids

    def handle_action(self, param):
        """This function gets current action identifier and calls member function of its own to handle the action.

        :param param: dictionary which contains information about the actions to be executed
        :return: status success/failure
        """

        # Dictionary mapping each action with its corresponding actions
        action_mapping = {
            "test_asset_connectivity": self._test_asset_connectivity,
            "check_connectivity": self._check_connectivity,
            "lookup_ip": self._lookup_ip,
        }

        action = self.get_action_identifier()
        try:
            run_action = action_mapping[action]
        except:
            raise ValueError(f"action {action} is not supported")

        return run_action(param)


if __name__ == "__main__":
    import sys

    import pudb

    pudb.set_trace()
    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)
    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))
        connector = TufinSecureTrackConnector()
        connector.print_progress_message = True
        return_value = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(return_value), indent=4))

    sys.exit(0)
