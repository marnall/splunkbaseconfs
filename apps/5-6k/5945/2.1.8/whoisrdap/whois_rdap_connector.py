# File: whois_rdap_connector.py
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
import ipaddress
import json

import phantom.app as phantom
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from whois_rdap_consts import *


try:
    from urllib2 import ProxyHandler, build_opener
except ImportError:
    from urllib.request import ProxyHandler, build_opener

from os import environ

from ipwhois import IPDefinedError, IPWhois


class WhoisRDAPConnector(BaseConnector):
    # actions supported by this script
    ACTION_ID_WHOIS_IP = "whois_ip"
    ACTION_ID_TEST_CONNECTIVITY = "test_connectivity"

    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

    def _is_valid_ip(self, input_ip_address):
        """Function that checks given address and return True if address is valid IPv4 or IPV6 address.

        :param input_ip_address: IP address
        :return: status (success/failure)
        """

        try:
            ipaddress.ip_address(input_ip_address)
        except Exception:
            return False

        return True

    def initialize(self):
        # use this to store data that needs to be accessed across actions
        self._state = self.load_state()
        self.set_validator("ipv6", self._is_valid_ip)
        return phantom.APP_SUCCESS

    def _whois_ip(self, param):
        ip = param[phantom.APP_JSON_IP]

        action_result = self.add_action_result(ActionResult(dict(param)))

        action_result.set_param({phantom.APP_JSON_IP: ip})

        self.debug_print(f"Validating/Querying IP '{ip}'")

        self.save_progress("Querying...")

        status, whois_response = self._lookup_rdap(action_result, ip)

        if phantom.is_fail(status):
            return action_result.get_status()

        self.save_progress("Parsing response")

        # the format screws with the object model since the keys change with every run
        # but the keys aren't needed since they are also stored in object.[key].handle
        # changing this to a list

        if whois_response.get("objects"):
            objects = whois_response["objects"]
            new_objects = [objects[key] for key in objects]
            whois_response["objects"] = new_objects

        action_result.add_data(whois_response)

        summary = action_result.update_summary({})

        # Create the summary and the message
        if "asn_registry" in whois_response:
            summary.update({WHOIS_JSON_ASN_REGISTRY: whois_response["asn_registry"]})

        if "asn" in whois_response:
            summary.update({WHOIS_JSON_ASN: whois_response["asn"]})

        if "asn_country_code" in whois_response:
            summary.update({WHOIS_JSON_COUNTRY_CODE: whois_response["asn_country_code"]})

        if "network" in whois_response:
            nets = whois_response["network"]
            wanted_keys = ["start_address", "end_address"]
            summary[WHOIS_JSON_NETS] = []
            summary_net = {x: nets[x] for x in wanted_keys}
            summary[WHOIS_JSON_NETS].append(summary_net)

        action_result.set_status(phantom.APP_SUCCESS)

    def _handle_test_connectivity(self, param):
        ip = "8.8.8.8"

        self.debug_print(f"Validating/Querying IP '{ip}'")

        self.save_progress("Querying...")

        status, whois_response = self._lookup_rdap(self, ip)
        if not status:
            return status

        self.save_progress("Parsing response")

        if whois_response.get("query") and whois_response.get("query") == ip:
            self.debug_print("identity test passed")
            return self.set_status_save_progress(phantom.APP_SUCCESS, WHOIS_SUCCESS_CONNECTIVITY_TEST)

        self.debug_print("identity test failed")
        return self.set_status_save_progress(phantom.APP_ERROR, WHOIS_ERROR_CONNECTIVITY_TEST)

    def _lookup_rdap(self, action_result, ip):
        proxy = {}
        if environ.get("HTTP_PROXY"):
            proxy["http"] = environ["HTTP_PROXY"]
        if environ.get("HTTPS_PROXY"):
            proxy["https"] = environ["HTTPS_PROXY"]

        try:
            if proxy:
                self.debug_print("Found proxy env. Using proxy for connection.")
                handler = ProxyHandler(proxy)
                opener = build_opener(handler)
                obj_whois = IPWhois(ip, proxy_opener=opener)
            else:
                obj_whois = IPWhois(ip)
            whois_response = obj_whois.lookup_rdap(inc_nir=False)
            return phantom.APP_SUCCESS, whois_response
        except IPDefinedError as e_defined:
            self.error_print("Got IPDefinedError: ", e_defined)
            action_result.set_status(phantom.APP_SUCCESS, str(e_defined))
            return phantom.APP_ERROR, None
        except Exception as e:
            self.error_print("Got exception object: ", e)
            return action_result.set_status(phantom.APP_ERROR, WHOIS_ERROR_QUERY.format(e)), None

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def handle_action(self, param):
        """Function that handles all the actions

        Args:

        Return:
            A status code
        """

        result = None
        action = self.get_action_identifier()

        if action == self.ACTION_ID_WHOIS_IP:
            result = self._whois_ip(param)
        elif action == self.ACTION_ID_TEST_CONNECTIVITY:
            self._handle_test_connectivity(param)
        else:
            result = self.unknown_action()

        return result


if __name__ == "__main__":
    import sys

    import pudb

    pudb.set_trace()

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=" " * 4))

        connector = WhoisRDAPConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
