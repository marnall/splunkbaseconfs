# File: hyasinsight_connector.py
#
# Copyright (c) HYAS, 2022-2025
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

# Python 3 Compatibility imports

import json
import re

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
from hyasinsight_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class HyasInsightConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    def _process_html_response(self, response, action_result):
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {e!s}"), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if
        # the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})
        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def flatten_json(self, response):
        json_flatten = {}

        def flatten(json_data, name=""):
            # If the Nested key-value
            # pair is of dict type
            if isinstance(json_data, dict):
                for json_data_in in json_data:
                    flatten(json_data[json_data_in], name + json_data_in + "_")
            # If the Nested key-value
            # pair is of list type
            elif isinstance(json_data, list):
                if len(json_data) > 0:
                    for json_data_in in json_data:
                        if isinstance(json_data_in, dict):
                            flatten(json_data_in, name)
                        else:
                            json_flatten[name[:-1]] = json_data
                else:
                    flatten("", name)
            else:
                json_flatten[name[:-1]] = json_data

        flatten(response)
        return json_flatten

    def get_flatten_json_response(self, raw_api_response, endpoint):
        """

        :param raw_api_response: raw_api response from the API
        :param endpoint: Endpoint
        :return: Flatten Json response

        """
        flatten_json_response = []
        if raw_api_response:
            for obj in raw_api_response:
                if endpoint == OS_INDICATOR:
                    data = json.loads(obj.get("data", "{}"))
                    obj = {**obj, **data}
                flatten_json_response.append(self.flatten_json(obj))

        return flatten_json_response

    def _get_error_message_from_exception(self, error):
        """This function is used to get appropriate error message from the
        exception.
        :param e: Exception object
        :return: error message
        """
        try:
            if error.args:
                if len(error.args) > 1:
                    error_code = error.args[0]
                    error_message = error.args[1]
                elif len(error.args) == 1:
                    error_code = HYAS_ERROR_CODE_MESSAGE
                    error_message = error.args[0]
            else:
                error_code = HYAS_ERROR_CODE_MESSAGE
                error_message = HYAS_ERROR_MESSAGE_UNAVAILABLE
        except:
            error_code = HYAS_ERROR_CODE_MESSAGE
            error_message = HYAS_ERROR_MESSAGE_UNAVAILABLE

        try:
            if error_code in HYAS_ERROR_CODE_MESSAGE:
                error_text = f"Error Message: {error_message}"
            else:
                error_text = f"Error Code: {error_code}. Error Message: {error_message}"

        except:
            error_text = HYAS_PARSE_ERROR_MESSAGE

        return error_text

    def _make_rest_call(self, endpoint, action_result, data=None, headers=None, method="post"):
        try:
            request_func = getattr(requests, method)

        except AttributeError:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Unsupported method: {method}"),
                None,
            )

        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Handled exception: {error_message}"),
                None,
            )

        # Create a URL to connect to
        if endpoint == CURRENT_WHOIS:
            url = f"{CURRENT_WHOIS_BASE_URL}{endpoint}"
        else:
            url = f"{HYAS_BASE_URL}{endpoint}"

        try:
            response = request_func(url, data=data, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT)

        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Error connecting: {error_message}"),
                None,
            )
        if response.status_code == 401:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, HYAS_INVALID_APIKEY_ERROR),
                None,
            )

        return self._process_response(response, action_result)

    def validating_ioc(self, action_result, ioc, val):
        """
        Function that checks given ioc and return IOC_NAME if ioc is valid
        IP/Domain/Email/Phone/SHA256.
        :param ioc: IP address/Email/Phone/SHA256/Domain
        :return: status (success/failure)
        """
        ioc_type = ioc
        ioc_names_list = IOC_NAME

        try:
            if ioc_type in ioc_names_list.keys():
                if ioc_type == "ip":
                    ip_dict = ioc_names_list[ioc_type]
                    for key, value in ip_dict.items():
                        regex = value
                        if re.fullmatch(regex, val):
                            ioc_name = key + "_regex"
                            return ioc_name

                elif ioc_type == "hash":
                    hash_dict = ioc_names_list["hash"]
                    for key, value in hash_dict.items():
                        regex = value
                        if re.fullmatch(regex, val):
                            ioc_name = key + "_regex"
                            return ioc_name
                    return None

                else:
                    regex = ioc_names_list[ioc_type]
                    if re.fullmatch(regex, val):
                        ioc_name = ioc_type + "_regex"
                        return ioc_name
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, "Unable to locate ioc type."),
                None,
            )
        except:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, "Error while Validating the ioc"),
                None,
            )

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector)
        # to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # NOTE: test connectivity does _NOT_ take any parameters
        # i.e. the param dictionary passed to this handler will be empty.
        # Also typically it does not add any data into an action_result either.
        # The status and progress messages are more important.
        payload = json.dumps({"applied_filters": {HYAS_TEST_PAYLOAD_KEY: HYAS_TEST_PAYLOAD_VALUE}})

        self.save_progress("Connecting to endpoint")

        # make rest call
        ret_val, response = self._make_rest_call(
            HYAS_TEST_PASSIVEHASH_ENDPOINT,
            action_result,
            data=payload,
            headers=self._headers,
        )

        if phantom.is_fail(ret_val):
            self.save_progress(HYAS_TEST_CONN_FAILED)
            return action_result.get_status()

        self.save_progress(HYAS_TEST_CONN_PASSED)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_lookup_command_and_control_domain(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = DOMAIN
        endpoint = C2ATTRIBUTION
        ioc_dict = C2ATTRIBUTION_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_command_and_control_email(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = EMAIL
        endpoint = C2ATTRIBUTION
        ioc_dict = C2ATTRIBUTION_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_command_and_control_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = IP
        endpoint = C2ATTRIBUTION
        ioc_dict = C2ATTRIBUTION_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_whois_domain(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = DOMAIN
        endpoint = WHOIS
        ioc_dict = WHOIS_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_whois_email(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = EMAIL
        endpoint = WHOIS
        ioc_dict = WHOIS_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_whois_phone(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = PHONE
        endpoint = WHOIS
        ioc_dict = WHOIS_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_dynamicdns_email(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = EMAIL
        endpoint = DYNAMICDNS
        ioc_dict = DYNAMIC_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_dynamicdns_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = IP
        endpoint = DYNAMICDNS
        ioc_dict = DYNAMIC_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_dynamicdns_domain(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = DOMAIN
        endpoint = DYNAMICDNS
        ioc_dict = DYNAMIC_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_sinkhole_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = IPV4
        endpoint = SINKHOLE
        ioc_dict = SINKHOLE_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_passivehash_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = IPV4
        endpoint = PASSIVEHASH
        ioc_dict = PASSIVEHASH_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_passivehash_domain(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = DOMAIN
        endpoint = PASSIVEHASH
        ioc_dict = PASSIVEHASH_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_ssl_certificate_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = IP
        endpoint = SSL
        ioc_dict = SSL_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_passivedns_domain(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = DOMAIN
        endpoint = PASSIVEDNS
        ioc_dict = PASSIVE_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_current_whois_domain(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = DOMAIN
        endpoint = CURRENT_WHOIS
        ioc_dict = WHOIS_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_passivedns_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = IPV4
        endpoint = PASSIVEDNS
        ioc_dict = PASSIVE_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_mobile_geolocation_information_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = IP
        endpoint = DEVICEGEO
        ioc_dict = DEVICE_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_malware_information_hash(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = HASH
        endpoint = SAMPLE_INFORMATION
        ioc_dict = SAMPLE_INFORMATION_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_malware_record_hash(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = HASH
        endpoint = SAMPLE
        ioc_dict = SAMPLE_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_malware_record_domain(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = DOMAIN
        endpoint = SAMPLE
        ioc_dict = SAMPLE_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_malware_record_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = IPV4
        endpoint = SAMPLE
        ioc_dict = SAMPLE_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_command_and_control_hash(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = HASH
        endpoint = C2ATTRIBUTION
        ioc_dict = C2ATTRIBUTION_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_os_indicator_hash(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = HASH
        endpoint = OS_INDICATOR
        ioc_dict = OS_INDICATOR_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_os_indicator_domain(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = DOMAIN
        endpoint = OS_INDICATOR
        ioc_dict = OS_INDICATOR_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_os_indicator_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = IP
        endpoint = OS_INDICATOR
        ioc_dict = OS_INDICATOR_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_ssl_certificate_hash(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = HASH
        endpoint = SSL
        ioc_dict = SSL_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def _handle_lookup_ssl_certificate_domain(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        indicator_type = DOMAIN
        endpoint = SSL
        ioc_dict = SSL_IOC
        self.save_progress("Checking the Indicator value")
        self.handle_all_actions(indicator_type, action_result, ioc_dict, endpoint, param)

    def handle_all_actions(self, indicator_type, action_result, ioc_dict, endpoint, param):
        all_response = {}
        indicator_value = param[indicator_type]

        validated_ioc_name = self.validating_ioc(action_result, indicator_type, indicator_value)
        self.save_progress("Creating Payload")
        if validated_ioc_name is not None:
            if validated_ioc_name in ioc_dict.keys():
                param_name = ioc_dict[validated_ioc_name]
                if endpoint == CURRENT_WHOIS:
                    payload = json.dumps(
                        {
                            "applied_filters": {
                                param_name: indicator_value,
                                "current": True,
                            }
                        }
                    )
                else:
                    payload = json.dumps({"applied_filters": {param_name: indicator_value}})

                ret_val, response = self._make_rest_call(
                    endpoint,
                    action_result,
                    data=payload,
                    headers=self._headers,
                )

                if phantom.is_fail(ret_val):
                    return ret_val

                try:
                    if endpoint != SSL and endpoint != CURRENT_WHOIS and endpoint != SAMPLE_INFORMATION:
                        all_response[endpoint] = self.get_flatten_json_response(response, endpoint)
                    elif endpoint == SSL:
                        response = response.get(SSL_CERTS)
                        all_response[endpoint] = self.get_flatten_json_response(response, endpoint)

                    elif endpoint == CURRENT_WHOIS:
                        response = response.get(ITEMS)
                        endpoint = CURRENT_WHOIS_NAME
                        all_response[endpoint] = self.get_flatten_json_response(response, endpoint)
                    elif endpoint == SAMPLE_INFORMATION:
                        response = response.get(SCAN_RESULT)
                        all_response[SAMPLE_INFORMATION_NAME] = self.get_flatten_json_response(response, endpoint)
                    self.save_progress("Saving Response")
                    action_result.add_data(all_response)
                    return action_result.set_status(phantom.APP_SUCCESS)
                except:
                    return action_result.set_status(
                        phantom.APP_ERROR,
                        "unable to flatten json response.",
                        None,
                    )

        return action_result.set_status(phantom.APP_ERROR, HYAS_ERROR_MESSAGE_INVALID_INDICATOR_VALUE)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        call_action = getattr(self, f"_handle_{action_id}")
        ret_val = call_action(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        try:
            config = self.get_config()
        except Exception:
            return phantom.APP_ERROR
        """
        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """
        try:
            self._apikey = config[HYAS_JSON_APIKEY]
        except KeyError as ke:
            return self._initialize_error(
                HYAS_ERROR_ASSET_API_KEY_,
                Exception(f"KeyError: {ke}"),
            )

        self._headers = {HYAS_JSON_APIKEY_HEADER: self._apikey, "Content-Type": "application/json", "User-Agent": "Splunk SOAR"}

        # self._base_url = config.get('base_url')

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse
    import sys

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = HyasInsightConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, timeout=DEFAULT_REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, data=data, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = HyasInsightConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
