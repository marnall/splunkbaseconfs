# File: whois_connector.py
#
# Copyright (c) 2016-2026 Splunk Inc.
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
# Phantom imports
import datetime
import ipaddress
import socket
import sys
import time
from urllib.parse import urlparse

import phantom.app as phantom
import pythonwhois
import simplejson as json
import tldextract
from charset_normalizer import detect
from ipwhois import IPDefinedError, IPWhois
from ipwhois.nir import NIR_WHOIS
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# THIS Connector imports
from whois_consts import *


# Workaround for https://github.com/secynic/ipwhois/issues/342
# Update the URL for KRNIC. Lookups for Korean IPs will fail without this.
NIR_WHOIS["krnic"]["url"] = "https://whois.kr/eng/whois.jsc"


TLD_LIST_CACHE_FILE_NAME = "public_suffix_list.dat"
ISO_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def monkey_patched_whois_request(domain, server, port=43):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server, port))
    sock.send((f"{domain}\r\n").encode())
    buff = b""
    while True:
        data = sock.recv(1024)
        if len(data) == 0:
            break
        buff += data

    encoding = detect(buff)["encoding"]
    return buff.decode(encoding)


# monkey patching internal pythonwhois method that throws decoding error
pythonwhois.net.whois_request = monkey_patched_whois_request


def _json_fallback(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    else:
        return obj


class WhoisConnector(BaseConnector):
    # actions supported by this script
    ACTION_ID_WHOIS_DOMAIN = "whois_domain"
    ACTION_ID_WHOIS_IP = "whois_ip"
    ACTION_ID_WHOIS_TEST_CONNECTIVITY = "test_connectivity"

    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state_file_path = None
        self._cache_file_path = None
        self._state = {}
        self._update_days = None

    def extract_hostname(self, url):
        parsed_url = urlparse(url)
        ip_address = parsed_url.hostname
        return ip_address

    def is_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    def _dump_error_log(self, error, message="Exception occurred."):
        self.error_print(message, dump_object=error)

    def _get_error_message_from_exception(self, e):
        """This method is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = None
        error_message = ERROR_MESSAGE_UNAVAILABLE

        self._dump_error_log(e, "Error occurred.")
        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except Exception as e:
            self.error_print(f"Error occurred while fetching exception information. Details: {e!s}")

        if not error_code:
            error_text = f"Error Message: {error_message}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_message}"

        return error_text

    def _validate_integer(self, action_result, parameter, key):
        """This method checks if the provided input parameter value is a non-zero positive integer.
        :param action_result: Action result or BaseConnector object
        :param parameter: input parameter
        :param key: input parameter message key
        :return: integer value of the parameter or None in case of failure
        """
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, INVALID_INTEGER_ERROR_MESSAGE.format(key)), None

                parameter = int(parameter)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, INVALID_INTEGER_ERROR_MESSAGE.format(key)), None

            if parameter <= 0:
                return action_result.set_status(phantom.APP_ERROR, INVALID_NON_NEGATIVE_INTEGER_ERROR_MESSAGE.format(key)), None

        return phantom.APP_SUCCESS, parameter

    def initialize(self):
        self._state = self.load_state()
        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}
        config = self.get_config()

        self._update_days = config["update_days"]
        status, self._update_days = self._validate_integer(self, self._update_days, "update_days")
        if phantom.is_fail(status):
            return self.get_status()

        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def replace_null_values(self, data):
        return json.loads(json.dumps(data).replace("\\u0000", "\\\\u0000"))

    def _response_no_data(self, response, obj):
        contacts = response["contacts"]

        # First check if the raw data contains any info
        raw_response = phantom.get_value(response, "raw")
        if raw_response:
            for line in raw_response:
                if line.lower().find("domain not found") != -1:
                    self.debug_print("Matched no data string. Domain not found")
                    return True
                if line.lower().find(f"no match for '{obj}'".lower()) != -1:
                    self.debug_print("Matched no data string. No match for domain")
                    return True

        # Check if none of the data that we need is present or not
        if (not contacts.get("admin")) and (not contacts.get("tech")) and (not contacts.get("registrant")) and (not contacts.get("billing")):
            return True

        return False

    def _handle_test_connectivity(self, param):
        ip = "1.1.1.1"

        action_result = self.add_action_result(ActionResult(dict(param)))

        action_result.set_param({phantom.APP_JSON_IP: ip})

        self.debug_print(f"Validating/Querying IP '{ip}'")

        self.save_progress("Querying...")

        try:
            obj_whois = IPWhois(ip)
            whois_response = obj_whois.lookup_whois(asn_methods=["whois", "dns", "http"])
        except IPDefinedError as e_defined:
            error_message = self._get_error_message_from_exception(e_defined)
            self.debug_print(f"Got IPDefinedError exception str: {error_message}")
            self.save_progress("Test Connectivity Failed")
            return action_result.set_status(phantom.APP_SUCCESS, error_message)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.debug_print(f"Got exception: type: {type(e).__name__}, str: {error_message}")
            self.save_progress("Test Connectivity Failed")
            return action_result.set_status(phantom.APP_ERROR, WHOIS_ERROR_QUERY, error_message)

        if not whois_response:
            self.save_progress("Test Connectivity Failed")
            return action_result.set_status(phantom.APP_ERROR, WHOIS_ERROR_QUERY_RETURNED_NO_DATA)

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _whois_ip(self, param):
        ip = param[phantom.APP_JSON_IP]

        action_result = self.add_action_result(ActionResult(dict(param)))

        # Validation for checking valid IP or not (IPV4 as well as IPV6)
        if not self._is_ip(ip):
            return action_result.set_status(phantom.APP_ERROR, "Please provide a valid IPV4 or IPV6 address")

        action_result.set_param({phantom.APP_JSON_IP: ip})

        # This sleep is required between two calls, else the server might
        # throttle the queries when done in quick succession, which leads
        # to a 'Connection reset by peer' error.
        time.sleep(1)

        self.debug_print(f"Validating/Querying IP '{ip}'")

        self.save_progress("Querying...")

        try:
            obj_whois = IPWhois(ip)
            whois_response = obj_whois.lookup_whois(asn_methods=["whois", "dns", "http"])
        except IPDefinedError as e_defined:
            error_message = self._get_error_message_from_exception(e_defined)
            self.debug_print(f"Got IPDefinedError exception str: {error_message}")
            return action_result.set_status(phantom.APP_SUCCESS, error_message)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.debug_print(f"Got exception: type: {type(e).__name__}, str: {error_message}")
            return action_result.set_status(phantom.APP_ERROR, WHOIS_ERROR_QUERY, error_message)

        if not whois_response:
            return action_result.set_status(phantom.APP_ERROR, WHOIS_ERROR_QUERY_RETURNED_NO_DATA)

        self.save_progress("Parsing response")

        action_result.add_data(whois_response)

        summary = action_result.update_summary({})
        message = ""

        # Create the summary and the message
        if "asn_registry" in whois_response:
            summary.update({WHOIS_JSON_ASN_REGISTRY: whois_response["asn_registry"]})
            message += f"Registry: {summary[WHOIS_JSON_ASN_REGISTRY]}"

        if "asn" in whois_response:
            summary.update({WHOIS_JSON_ASN: whois_response["asn"]})
            message += f"\nASN: {summary[WHOIS_JSON_ASN]}"

        if "asn_country_code" in whois_response:
            summary.update({WHOIS_JSON_COUNTRY_CODE: whois_response["asn_country_code"]})
            message += f"\nCountry: {summary[WHOIS_JSON_COUNTRY_CODE]}"

        if "nets" in whois_response:
            nets = whois_response["nets"]
            wanted_keys = ["range", "address"]
            summary[WHOIS_JSON_NETS] = []
            message += "\nNets:"
            for net in nets:
                summary_net = {x: net.get(x) for x in wanted_keys}
                summary[WHOIS_JSON_NETS].append(summary_net)
                message += "\nRange: {}".format(summary_net["range"])
                message += "\nAddress: {}".format(summary_net["address"])

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _is_ip(self, input_ip_address):
        """Function that checks given address and returns True if address is valid IPv4 or IPV6 address.

        :param input_ip_address: IP address
        :return: status (success/failure)
        """

        ip_address_input = input_ip_address

        try:
            try:
                ipaddress.ip_address(unicode(ip_address_input))
            except NameError:
                ipaddress.ip_address(str(ip_address_input))
        except Exception:
            return False

        return True

    def _should_update_cache(self):
        last_time = self._state.get(WHOIS_JSON_CACHE_UPDATE_TIME)

        if not last_time:
            return True

        try:
            last_time = datetime.datetime.strptime(last_time, ISO_TIME_FORMAT)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.debug_print(f"Exception while strptime {error_message}")
            return True

        current_time = datetime.datetime.utcnow()

        time_diff = current_time - last_time

        cache_exp_days = self._update_days

        if time_diff.days >= cache_exp_days:
            self.debug_print(f"Diff days {time_diff.days} >= cache exp days {cache_exp_days}")
            return True

        return False

    def _get_domain(self, hostname):
        extract = None

        should_update = self._should_update_cache()
        try:
            if should_update:
                self.debug_print("Will Update tld list on the current call")
                extract = tldextract.TLDExtract(cache_file=self._cache_file_path)
            else:
                extract = tldextract.TLDExtract(cache_file=self._cache_file_path, suffix_list_urls=None)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.debug_print(f"tldextract failed: {error_message}")
            # The caller of this function has a try..except for this one
            raise

        result = extract(hostname)

        if should_update:
            # Set the updated time
            self._state[WHOIS_JSON_CACHE_UPDATE_TIME] = datetime.datetime.utcnow().strftime(ISO_TIME_FORMAT)

        domain = ""
        if result.suffix and result.domain:
            domain = f"{result.domain}.{result.suffix}"  # pylint: disable=E1101
        elif result.suffix:
            domain = f"{result.suffix}"  # pylint: disable=E1101
        elif result.domain:
            domain = f"{result.domain}"  # pylint: disable=E1101
        return domain

    def _fetch_whois_info(self, action_result, domain, server):
        """
        This method fetches the whois information for the given domain based on the
        value of the server if provided or by using the default server of the pythonwhois library.
        """

        try:
            self.debug_print(f"Fetching the WHOIS information. Server is: {server}")
            if server:
                if self.is_url(server):
                    self.debug_print(f"Server value {server} is a URL")
                    server = self.extract_hostname(server)
                    self.debug_print(f"New server value is : {server}")
                else:
                    self.debug_print("Server is not a URL")
                try:
                    raw_whois_resp = pythonwhois.net.get_whois_raw(domain, server)
                except Exception as e:
                    error_message = self._get_error_message_from_exception(e)
                    self.debug_print(f"Failed to connect to whois server: {server}, {error_message}")
                    whois_response = pythonwhois.get_whois(domain)
                    if not whois_response:
                        action_result.set_status(phantom.APP_ERROR, WHOIS_ERROR_QUERY_RETURNED_NO_DATA)
                        return None

                    return whois_response
                whois_response = pythonwhois.parse.parse_raw_whois(raw_whois_resp)
            else:
                whois_response = pythonwhois.get_whois(domain)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            action_result.set_status(phantom.APP_ERROR, WHOIS_ERROR_QUERY, error_message)
            return None

        if not whois_response:
            action_result.set_status(phantom.APP_ERROR, WHOIS_ERROR_QUERY_RETURNED_NO_DATA)
            return None

        return whois_response

    def _whois_domain(self, param):
        config = self.get_config()
        server = config.get(phantom.APP_JSON_SERVER, None)

        domain = param[phantom.APP_JSON_DOMAIN]

        action_result = self.add_action_result(ActionResult(dict(param)))
        action_result.set_param({phantom.APP_JSON_DOMAIN: domain})
        if self._is_ip(domain):
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'domain' failed validation")

        # This sleep is required between two calls, else the server might
        # throttle the queries when done in quick succession, which leads
        # to a 'Connection reset by peer' error.
        # Sleep before doing anything (as opposed to after), so that even
        # if this action returns an error, the sleep will get executed and
        # the next call will get executed after this sleep
        time.sleep(1)

        try:
            domain = self._get_domain(domain)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, WHOIS_ERROR_PARSE_INPUT, error_message)

        self.debug_print(f"Validating/Querying Domain {domain!r}")

        action_result.update_summary({phantom.APP_JSON_DOMAIN: domain})

        self.save_progress("Querying...")

        pythonwhois.parse.registrant_regexes.extend(REGISTRANT_REGEXES)
        pythonwhois.parse.admin_contact_regexes.extend(ADMIN_CONTACT_REGEXES)
        pythonwhois.parse.tech_contact_regexes.extend(TECH_CONTACT_REGEXES)
        pythonwhois.parse.billing_contact_regexes.extend(BILLING_CONTACT_REGEXES)

        # 1. Attempting to fetch the whois information with the server
        # if provided or without it if not provided
        whois_response = self._fetch_whois_info(action_result, domain, server)

        if whois_response is None:
            return action_result.get_status()

        # 2. Attempting to fetch the whois information with the server obtained
        # in the output response of the first step above
        if whois_response.get("contacts") and not whois_response.get("contacts").get("registrant"):
            if whois_response.get("whois_server") and whois_response.get("whois_server")[0]:
                whois_response = self._fetch_whois_info(action_result, domain, whois_response.get("whois_server")[0])

                if whois_response is None:
                    return action_result.get_status()
            else:
                self.debug_print(WHOIS_NO_SEC_API)

        self.save_progress("Parsing response")

        try:
            # Need to work on the json, it contains certain fields that are not
            # parsable, so will need to go the 'fallback' way.
            # TODO: Find a better way to do this
            whois_response = json.dumps(whois_response, default=_json_fallback)
            whois_response = json.loads(whois_response)
            action_result.add_data(whois_response)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, WHOIS_ERROR_PARSE_REPLY, error_message)

        # Even if the query was successfull the data might not be available
        if self._response_no_data(whois_response, domain):
            return action_result.set_status(phantom.APP_SUCCESS, f"{WHOIS_SUCC_QUERY}, but, {WHOIS_ERROR_QUERY_RETURNED_NO_CONTACTS_DATA}.")
        else:
            # get the registrant
            if whois_response.get("contacts") and whois_response.get("contacts").get("registrant"):
                registrant = whois_response["contacts"]["registrant"]
                wanted_keys = ["organization", "name", "city", "country"]
                summary = {x: registrant[x] for x in wanted_keys if x in registrant}
                action_result.update_summary(self.replace_null_values(summary))
                action_result.set_status(phantom.APP_SUCCESS)
            else:
                action_result.set_status(phantom.APP_SUCCESS, f"{WHOIS_SUCC_QUERY}, but, {WHOIS_SUCC_QUERY_RETURNED_NO_REGISTRANT_DATA}.")

        return phantom.APP_SUCCESS

    def handle_action(self, param):
        """Function that handles all the actions

        :param param: dictionary which contains information about the actions to be executed
        :return: status (success/failure)
        """

        result = None
        action = self.get_action_identifier()

        if action == self.ACTION_ID_WHOIS_DOMAIN:
            result = self._whois_domain(param)
        elif action == self.ACTION_ID_WHOIS_IP:
            result = self._whois_ip(param)
        elif action == self.ACTION_ID_WHOIS_TEST_CONNECTIVITY:
            result = self._handle_test_connectivity(param)
        else:
            result = self.unknown_action()

        action_results = self.get_action_results()
        if len(action_results) > 0:
            action_result = action_results[-1]
            action_result._ActionResult__data = self.replace_null_values(action_result._ActionResult__data)
            action_result.set_status(result, self.replace_null_values(action_result.get_message()))

        return result


if __name__ == "__main__":
    import pudb

    pudb.set_trace()

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=" " * 4))

        connector = WhoisConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
