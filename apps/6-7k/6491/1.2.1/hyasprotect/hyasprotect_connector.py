#!/usr/bin/python
# -----------------------------------------
# Phantom sample App Connector python file
# -----------------------------------------

# File: hyasprotect_connector.py
#
# Copyright (c) Hyas, 2022-2025
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


# Python 3 Compatibility imports

import json
import re

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# import constant file
from hyasprotect_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class HyasProtectConnector(BaseConnector):
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

        return RetVal(action_result.set_status(phantom.APP_ERROR, EMPTY_RESPONSE), None)

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = ERROR_TEXT

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

        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
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

    def _validating_ioc(self, ioc, ioc_value):
        if ioc == "ip":
            return bool(re.fullmatch(IOC_NAME[ioc], ioc_value)) or bool(re.fullmatch(IPV6_REG, ioc_value))
        else:
            return bool(re.fullmatch(IOC_NAME[ioc], ioc_value))

    def _make_rest_call(
        self,
        param,
        endpoint,
        action_result,
        ioc,
        params=None,
        body=None,
        headers=None,
        method="get",
    ):
        # **kwargs can be any additional parameters that requests.request
        # accepts
        # url = BASE_URL + endpoint
        self.save_progress(HYAS_MESSAGE_CREATED_URL)
        try:
            request_func = getattr(requests, method)
        except AttributeError:
            # Set the action_result status to error, the handler function
            # will most probably return as is
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Unsupported method: {method}"),
                None,
            )
        except Exception as e:
            # Set the action_result status to error, the handler function
            # will most probably return as is
            error_message = self._get_error_message_from_exception(e)
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Handled exception: {error_message}"),
                None,
            )

        # Create a URL to connect to

        if endpoint == DOMAIN_TEST_ENDPOINT:
            url = f"{BASE_URL}{endpoint}{DOMAIN_TEST_VALUE}"
        elif endpoint == BLOCK_DNS_ENDPOINT:
            url = f"{BASE_URL}{endpoint}"
        else:
            url = f"{BASE_URL}{endpoint}{ioc}"

        try:
            response = request_func(url, params=params, data=body, headers=headers)
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

    def indicator_data_points(self, results: dict):
        verdict = results.get("verdict")
        reason = results.get("reasons")
        if len(reason) == 0:
            reason = "N/A"
        row = {"Verdict": verdict, "Reasons": reason}
        return row

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent
        # the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # NOTE: test connectivity does _NOT_ take any parameters
        # i.e. the param dictionary passed to this handler will be empty.
        # Also typically it does not add any data into an action_result either.
        # The status and progress messages are more important.

        self.save_progress("Connecting to endpoint")
        endpoint = f"{DOMAIN_TEST_ENDPOINT}"
        ioc = DOMAIN_TEST_VALUE
        # make rest call
        ret_val, response = self._make_rest_call(param, endpoint, action_result, ioc, headers=self._headers)
        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action
            # result should contain all the error details
            # for now the return is commented out, but after implementation,
            # return from here
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()

            # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_ip_verdict(self, param):
        ip_response = {}
        action_id = self.get_action_identifier()
        self.save_progress(f"In action handler for: {action_id}")
        # Add an action result object to self (BaseConnector)
        # to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            endpoint = IP_REPUTATION_ENDPOINT
            ipaddress = param["ip"]
            validating_ioc = self._validating_ioc("ip", ipaddress)
            if validating_ioc:
                ret_val, response = self._make_rest_call(param, endpoint, action_result, ipaddress, headers=self._headers)

                if phantom.is_fail(ret_val):
                    return ret_val

                try:
                    ip_response["ip"] = self.indicator_data_points(response)
                    action_result.add_data(ip_response)
                    return action_result.set_status(phantom.APP_SUCCESS)
                except:
                    return action_result.set_status(
                        phantom.APP_ERROR,
                        UNABLE_TO_FLATTEN_JSON,
                        None,
                    )

            else:
                return action_result.set_status(phantom.APP_ERROR, HYAS_ASSET_ERROR_MESSAGE, None)

        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Unable to retrieve actions results. Error: {e!s}",
                None,
            )

    def _handle_domain_verdict(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the
        # platform
        domain_response = {}
        action_id = self.get_action_identifier()
        self.save_progress(f"In action handler for: {action_id}")
        # Add an action result object to self (BaseConnector)
        # to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            endpoint = DOMAIN_REPUTATION_ENDPOINT
            domain_value = param["domain"]
            validating_ioc = self._validating_ioc("domain", domain_value)
            if validating_ioc:
                ret_val, response = self._make_rest_call(param, endpoint, action_result, domain_value, headers=self._headers)

                if phantom.is_fail(ret_val):
                    return ret_val

                try:
                    domain_response["domain"] = self.indicator_data_points(response)
                    action_result.add_data(domain_response)
                    return action_result.set_status(phantom.APP_SUCCESS)
                except:
                    return action_result.set_status(
                        phantom.APP_ERROR,
                        UNABLE_TO_FLATTEN_JSON,
                        None,
                    )

            else:
                return action_result.set_status(phantom.APP_ERROR, HYAS_ASSET_ERROR_MESSAGE, None)

        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Unable to retrieve actions results. Error: {e!s}",
                None,
            )

    def _handle_fqdn_verdict(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the
        # platform
        fqdn_response = {}
        action_id = self.get_action_identifier()
        self.save_progress(f"In action handler for: {action_id}")
        # Add an action result object to self (BaseConnector)
        # to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            endpoint = FQDN_REPUTATION_ENDPOINT
            fqdn_value = param["fqdn"]
            validating_ioc = self._validating_ioc("fqdn", fqdn_value)
            if validating_ioc:
                ret_val, response = self._make_rest_call(param, endpoint, action_result, fqdn_value, headers=self._headers)

                if phantom.is_fail(ret_val):
                    return ret_val

                try:
                    fqdn_response["fqdn"] = self.indicator_data_points(response)
                    action_result.add_data(fqdn_response)
                    return action_result.set_status(phantom.APP_SUCCESS)
                except:
                    return action_result.set_status(
                        phantom.APP_ERROR,
                        UNABLE_TO_FLATTEN_JSON,
                        None,
                    )

            else:
                return action_result.set_status(phantom.APP_ERROR, HYAS_ASSET_ERROR_MESSAGE, None)

        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Unable to retrieve actions results. Error: {e!s}",
                None,
            )

    def _handle_nameserver_verdict(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the
        # platform
        nameserver_response = {}
        action_id = self.get_action_identifier()
        self.save_progress(f"In action handler for: {action_id}")
        # Add an action result object to self (BaseConnector)
        # to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            endpoint = NAMESERVER_REPUTATION_ENDPOINT
            nameserver_value = param["nameserver"]
            validating_ioc = self._validating_ioc("nameserver", nameserver_value)
            if validating_ioc:
                ret_val, response = self._make_rest_call(param, endpoint, action_result, nameserver_value, headers=self._headers)

                if phantom.is_fail(ret_val):
                    return ret_val

                try:
                    nameserver_response["nameserver"] = self.indicator_data_points(response)
                    action_result.add_data(nameserver_response)
                    return action_result.set_status(phantom.APP_SUCCESS)
                except:
                    return action_result.set_status(
                        phantom.APP_ERROR,
                        UNABLE_TO_FLATTEN_JSON,
                        None,
                    )

            else:
                return action_result.set_status(phantom.APP_ERROR, HYAS_ASSET_ERROR_MESSAGE, None)

        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Unable to retrieve actions results. Error: {e!s}",
                None,
            )

    def _handle_block_dns(self, param):
        block_dns_response = {}
        action_id = self.get_action_identifier()
        self.save_progress(f"In action handler for: {action_id}")
        # Add an action result object to self (BaseConnector) to represent
        # the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))
        domain = param["domain"]
        try:
            if self._validating_ioc("domain", domain):
                dns_endpoint = BLOCK_DNS_ENDPOINT
                get_params = {"datatype": "domain", "enabled": "true", "type": "deny"}
                ret_val, dns_list_response = self._make_rest_call(
                    param,
                    dns_endpoint,
                    action_result,
                    "",
                    headers=self._headers,
                    params=get_params,
                )
                if phantom.is_fail(ret_val):
                    return ret_val
                deny_list = dns_list_response.get("local", [])
                list_id = ""
                for deny in deny_list:
                    if deny.get("name") == SPLUNK_SOAR_LIST:
                        list_id = deny.get("id")
                        self.save_progress("deny list id found")
                        break

                if not list_id:
                    self.save_progress("Adding deny list to block dns")
                    body = {
                        "type": "DENY",
                        "datatype": "DOMAIN",
                        "name": SPLUNK_SOAR_LIST,
                        "notes": SPLUNK_SOAR_LIST_NOTES,
                        "enabled": "true",
                    }
                    post_param = {"dryrun": "false"}
                    ret_val, deny_response = self._make_rest_call(
                        param,
                        dns_endpoint,
                        action_result,
                        "",
                        method="post",
                        headers=self._headers,
                        params=post_param,
                        body=json.dumps(body),
                    )
                    if phantom.is_fail(ret_val):
                        return ret_val
                    list_id = deny_response.get("listId")
                self.save_progress("Adding domain to deny list")
                block_dns_endpoint = f"{BLOCK_DNS_ENDPOINT}/{list_id}"
                body = {
                    "value": domain,
                    "notes": "Added by splunk soar",
                    "enabled": "true",
                }
                ret_val, dns_response = self._make_rest_call(
                    param,
                    block_dns_endpoint,
                    action_result,
                    "",
                    domain,
                    method="post",
                    headers=self._headers,
                    body=json.dumps(body),
                )
                if phantom.is_fail(ret_val):
                    return ret_val
                block_dns_response["block_dns"] = {"message": f"{domain} added successfully to deny list: {SPLUNK_SOAR_LIST}"}
                action_result.add_data(block_dns_response)
                return action_result.set_status(phantom.APP_SUCCESS)
            else:
                return action_result.set_status(phantom.APP_ERROR, HYAS_ASSET_ERROR_MESSAGE, None)

        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Unable to retrieve actions results. Error: {e!s}",
                None,
            )

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == IP_VERDICT:
            ret_val = self._handle_ip_verdict(param)

        if action_id == DOMAIN_VERDICT:
            ret_val = self._handle_domain_verdict(param)

        if action_id == FQDN_VERDICT:
            ret_val = self._handle_fqdn_verdict(param)

        if action_id == NAMESERVER_VERDICT:
            ret_val = self._handle_nameserver_verdict(param)

        if action_id == BLOCK_DNS:
            ret_val = self._handle_block_dns(param)

        if action_id == TEST_CONNECTIVITY:
            ret_val = self._handle_test_connectivity(param)

        return ret_val

    def initialize(self):
        """
        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        try:
            config = self.get_config()
            self._apikey = config[API_KEY]
            # self.debug_print(self._apikey)
            self._headers = {
                APIKEY_HEADER: self._apikey,
                "accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Splunk SOAR",
            }
            # self.debug_print(self._headers)
        except Exception:
            return phantom.APP_ERROR

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
    argparser.add_argument("-v", "--verify", action="store_true", help="verify", required=False, default=False)

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
            login_url = HyasProtectConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=HYAS_DEFAULT_REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=HYAS_DEFAULT_REQUEST_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = HyasProtectConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
