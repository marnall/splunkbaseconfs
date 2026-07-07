# File: akamaiwaf_connector.py
#
# Copyright (c) Robert Drouin, 2021-2026
#
# Licensed under Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt)
#
# Phantom App imports
import ipaddress
import json
import sys

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
from akamaiwaf_consts import *


try:
    from urllib import unquote
except:
    from urllib.parse import unquote
# Import Akamai Edgegrid authentication module
from akamai.edgegrid import EdgeGridAuth


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class AkamaiNetworkListsConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None
        self._base_url = None
        self._client_token = None
        self._client_secret = None
        self._access_token = None

    def _validate_integer(self, action_result, parameter, key):
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, VALID_INTEGER_MSG.format(key)), None

                parameter = int(parameter)
            except:
                return action_result.set_status(phantom.APP_ERROR, VALID_INTEGER_MSG.format(key)), None

            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, NON_NEGATIVE_INTEGER_MSG.format(key)), None

        return phantom.APP_SUCCESS, parameter

    def _get_error_message_from_exception(self, e):
        """This method is used to get appropriate error messages from the exception.
        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_message = None

        try:
            if e.args:
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_code = ERROR_CODE_MSG
                    error_message = e.args[0]
            else:
                error_code = ERROR_CODE_MSG
                error_message = ERROR_MSG_UNAVAILABLE
        except:
            error_code = ERROR_CODE_MSG
            error_message = ERROR_MSG_UNAVAILABLE

        try:
            error_message = error_message
        except TypeError:
            error_message = TYPE_ERROR_MSG
        except:
            error_message = ERROR_MSG_UNAVAILABLE

        try:
            if error_code in ERROR_CODE_MSG:
                error_text = f"Error Message: {error_message}"
            else:
                error_text = f"Error Code: {error_code}. Error Message: {error_message}"
        except:
            self.debug_print(PARSE_ERROR_MSG)
            error_text = PARSE_ERROR_MSG

        return error_text

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, f"Status Code: {response.status_code}. Empty response and no information in the header"),
            None,
        )

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            for element in soup(["script", "style", "footer", "nav"]):
                element.extract()
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{unquote(error_text)}\n"

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            error = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {error}"), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        if resp_json.get("detail"):
            message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, resp_json.get("detail"))
        else:
            message = "Error from server. Status Code: {} Data from server: {}".format(
                r.status_code, r.text.replace("{", "{{").replace("}", "}}")
            )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process each 'Content-Type' of response separately

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

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts
        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = f"{self._base_url}{AKAMAI_API_PATH}{endpoint}"

        try:
            r = requests.Session()
            r.auth = EdgeGridAuth(client_token=self._client_token, client_secret=self._client_secret, access_token=self._access_token)
            print(vars(r))
            r = request_func(url, auth=r.auth, verify=config.get("akamai_verify_ssl", False), **kwargs)
        except requests.exceptions.InvalidSchema:
            error_message = f"Error connecting to server. No connection adapters were found for {url}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), resp_json)
        except requests.exceptions.InvalidURL:
            error_message = f"Error connecting to server. Invalid URL {url}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), resp_json)
        except requests.exceptions.ConnectionError:
            error_message = "Error Details: Connection Refused from the Server"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), resp_json)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {error_message}"), resp_json)

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        """This function is used test connectivity to Akamai
        :param param: Dictionary of input parameters
        :return: status success/failure
        """
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to endpoint")

        # make rest call
        ret_val, response = self._make_rest_call(AKAMAI_NETWORK_LIST_ENDPOINT, action_result, params=None, headers=None)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_networks(self, param):
        """This function is used list out all the networks lists details. We can also search by name to get a specific network list.
        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        params = {}

        if param.get("includeelements"):
            params["includeElements"] = param.get("includeelements")
        if param.get("extended"):
            params["extended"] = param.get("extended")
        if param.get("search"):
            params["search"] = param.get("search")

        endpoint = self._process_parameters(AKAMAI_NETWORK_LIST_ENDPOINT, params)

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, params=None, headers=None)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_network(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        params = {}

        if param.get("includeelements"):
            params["includeElements"] = param.get("includeelements")
        if param.get("extended"):
            params["extended"] = param.get("extended")
        if param.get("networklistid"):
            param_networklistid = [x.strip() for x in param.get("networklistid").split(",")]
            param_networklistid = list([_f for _f in param_networklistid if _f])
            if not param_networklistid:
                return action_result.set_status(phantom.APP_ERROR, "Please provide valid input value in the 'networklistid' action parameter")

        # Loop through each Network ID to retrive the data.
        for networklist in param_networklistid:
            # Format the URI
            endpoint = self._process_parameters(f"{AKAMAI_NETWORK_LIST_ENDPOINT}/{networklist}", params)

            # make rest call
            ret_val, response = self._make_rest_call(endpoint, action_result, params=None, headers=None)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_add_element(self, param):
        # Use  POST /network-list/v2/network-lists/{networkListId}/append since you can add more than one element to a list.
        # Should be easier than using the 'Add an element' function which you can only add one at a time.

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        param_elements = [x.strip() for x in param.get("elements").split(",")]
        param_elements = list([_f for _f in param_elements if _f])
        if not param_elements:
            return action_result.set_status(phantom.APP_ERROR, "Please provide valid input value in the 'elements' action parameter")

        if len(param_elements) <= 1:
            # Create the param data to build the URI correctly. Only doing this to reuse code.
            # Can assign manually but it wont be as flexible if the API changes.
            params = {"element": param.get("elements")}

            endpoint = self._process_parameters("{}/{}/elements".format(AKAMAI_NETWORK_LIST_ENDPOINT, param.get("networklistid")), params)

            # make rest call
            ret_val, response = self._make_rest_call(endpoint, action_result, params=None, headers=None, method="put")
        else:
            data = {"list": []}
            # Rebuild the elements as JSON
            for element in param_elements:
                # Add element to the list
                data["list"].append(element)

            endpoint = "{}/{}/append".format(AKAMAI_NETWORK_LIST_ENDPOINT, param.get("networklistid"))

            # make rest call
            ret_val, response = self._make_rest_call(endpoint, action_result, params=None, headers=None, method="post", json=data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_remove_element(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        param_elements = [x.strip() for x in param.get("elements").split(",")]
        param_elements = list([_f for _f in param_elements if _f])
        if not param_elements:
            return action_result.set_status(phantom.APP_ERROR, "Please provide valid input value in the 'elements' action parameter")

        if len(param_elements) < 2:
            # Create the param data to build the URI correctly. Only doing this to reuse code.
            # Can assign manually but it wont be as flexible if the API changes.
            params = {"element": param.get("elements")}

            endpoint = self._process_parameters("{}/{}/elements".format(AKAMAI_NETWORK_LIST_ENDPOINT, param.get("networklistid")), params)

            # make rest call
            ret_val, response = self._make_rest_call(endpoint, action_result, params=None, headers=None, method="delete")
        else:
            # This is a hack to remove multiple elements at a time. I use the "Update a network list" API to be able to remove
            # multiple IP's / CIDR's.

            # Need to get the list of items before we can remove them. We also need other data to be able to update the network list.
            # Format the URI
            endpoint = "{}/{}".format(AKAMAI_NETWORK_LIST_ENDPOINT, param.get("networklistid"))

            # make rest call
            ret_val, response = self._make_rest_call(endpoint, action_result, params=None, headers=None)
            try:
                networkList = response["list"]
            except Exception as e:
                error_message = self._get_error_message_from_exception(e)
                return action_result.set_status(phantom.APP_ERROR, f"Error occurred while processing the response. {error_message}")
            # Loop through the parameters passed.
            for item in param_elements:
                # Index is used to pop the item from the list
                index = 0
                # Loop through the current list of addresses
                for network in networkList:  # nosemgrep
                    if item == network:
                        networkList.pop(index)
                    index += 1

            # Create the data we are going to update the list details with.
            # All fields here are required for the "Update a network list" API
            data = {
                "name": response.get("name", ""),
                "description": response.get("description", ""),
                "type": response.get("type", ""),
                "syncPoint": response.get("syncPoint", ""),
                "list": networkList,
            }

            # make rest call
            ret_val, response = self._make_rest_call(endpoint, action_result, params=None, headers=None, method="put", json=data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_network(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        ip_data = []

        ip_list = [x.strip() for x in param.get("list").split(",")]
        ip_list = list([_f for _f in ip_list if _f])
        if not ip_list:
            return action_result.set_status(phantom.APP_ERROR, "Please provide valid input value in the 'list' action parameter")

        for ip in ip_list:
            ip_data.append(ip)

        type = param.get("type")
        if type not in TYPE_VALUE_LIST:
            return action_result.set_status(phantom.APP_ERROR, f"Please provide valid input from {TYPE_VALUE_LIST} in 'type' action parameter")

        data = {"name": param.get("name"), "type": type, "description": param.get("description"), "list": ip_data}

        endpoint = f"{AKAMAI_NETWORK_LIST_ENDPOINT}"

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, params=None, headers=None, method="post", json=data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_network(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        endpoint = "{}/{}/details".format(AKAMAI_NETWORK_LIST_ENDPOINT, param.get("networklistid"))

        data = {"name": param.get("name"), "description": param.get("description")}

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, params=None, headers=None, method="put", json=data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_network(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        endpoint = "{}/{}".format(AKAMAI_NETWORK_LIST_ENDPOINT, param.get("networklistid"))

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, params=None, headers=None, method="delete")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_activate_network(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        data = {"comments": param.get("comments", "")}

        # Notification parameter is used
        if param.get("notification"):
            notifications = [x.strip() for x in param.get("notification").split(",")]
            notifications = list([_f for _f in notifications if _f])
            if not notifications:
                return action_result.set_status(phantom.APP_ERROR, "Please provide valid input value in the 'notification' action parameter")

            notificationEmails = []

            for notificationEmail in notifications:
                notificationEmails.append(notificationEmail)

            data["notification"] = notificationEmails

        environment = param.get("environment")
        if environment not in ENVIRONMENT_VALUE_LIST:
            return action_result.set_status(
                phantom.APP_ERROR, f"Please provide valid input from {ENVIRONMENT_VALUE_LIST} in 'environment' action parameter"
            )

        endpoint = "{}/{}/environments/{}/activate".format(AKAMAI_NETWORK_LIST_ENDPOINT, param.get("networklistid"), environment)

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, params=None, headers=None, method="post", json=data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_activation_status(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        environment = param.get("environment")
        if environment not in ENVIRONMENT_VALUE_LIST:
            return action_result.set_status(
                phantom.APP_ERROR, f"Please provide valid input from {ENVIRONMENT_VALUE_LIST} in 'environment' action parameter"
            )

        endpoint = "{}/{}/environments/{}/status".format(AKAMAI_NETWORK_LIST_ENDPOINT, param.get("networklistid"), environment)

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, params=None, headers=None)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_activation_snapshot(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        params = {"extended": param.get("extended", False)}

        ret_val, syncpoint = self._validate_integer(action_result, param.get("syncpoint"), SYNCPOINT_KEY)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        endpoint = self._process_parameters(
            "{}/{}/sync-points/{}/history".format(AKAMAI_NETWORK_LIST_ENDPOINT, param.get("networklistid"), syncpoint), params
        )

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, params=None, headers=None)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_activation_details(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val, activationid = self._validate_integer(action_result, param.get("activationid"), ACTIVATIONID_KEY)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        endpoint = f"{AKAMAI_ACTIVATIONS_ENDPOINT}/{activationid}"

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, params=None, headers=None)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_siteshields(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        # make rest call
        endpoint = "../../siteshield/v1/maps"
        ret_val, site_shields_data = self._make_rest_call(endpoint, action_result, params=None, headers=None)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Get ips from response. The full policy structure is required (policySettings[0] must be created)
        for site_shield in site_shields_data["siteShieldMaps"]:
            for ip_range in site_shield["currentCidrs"]:
                action_result.add_data({"cidr": ip_range})

        self.save_progress(f"Action handler for: {self.get_action_identifier()} ended")

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_data"] = action_result.get_data_size()

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        """This function gets current action identifier and calls member function of its own to handle the action.
        :param param: dictionary which contains information about the actions to be executed
        :return: status success/failure
        """
        self.debug_print(f"action_id: {self.get_action_identifier()}")

        action_mapping = {
            "test_connectivity": self._handle_test_connectivity,
            "list_networks": self._handle_list_networks,
            "get_network": self._handle_get_network,
            "create_network": self._handle_create_network,
            "update_network": self._handle_update_network,
            "add_element": self._handle_add_element,
            "remove_element": self._handle_remove_element,
            "delete_network": self._handle_delete_network,
            "activate_network": self._handle_activate_network,
            "activation_status": self._handle_activation_status,
            "activation_snapshot": self._handle_activation_snapshot,
            "activation_details": self._handle_activation_details,
            "list_siteshields": self._handle_list_siteshields,
        }

        action = self.get_action_identifier()
        action_execution_status = phantom.APP_SUCCESS

        if action in list(action_mapping.keys()):
            action_function = action_mapping[action]
            action_execution_status = action_function(param)
        return action_execution_status

    def _process_parameters(self, endpoint, params):
        """This function is used process the parameters and creates a valid endpoint URL.
        :param endpoint: The endpoint we want to send data to
        :param param: Dictionary of input parameters
        :return: endpoint
        """
        # Default values
        first_param = True

        if len(params) > 0:
            endpoint = "{}{}".format(endpoint, "?")

            for param, value in list(params.items()):
                if first_param:
                    endpoint = f"{endpoint}{param}={value}"
                    first_param = False
                else:
                    endpoint = f"{endpoint}&{param}={value}"
        else:
            endpoint = endpoint

        return endpoint

    def _validate_ip(self, input_ip_address):
        """
        Function that checks given address and return True if address is valid IPv4 or IPV6 address.

        :param input_ip_address: IP address
        :return: status (success/failure)
        """
        try:
            ipaddress.ip_address(input_ip_address)
        except Exception:
            return False
        return True

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # set validator for ip
        self.set_validator("ip", self._validate_ip)

        # get the asset config
        config = self.get_config()

        self._base_url = config.get("base_url").strip("/")
        self._client_token = config.get("client_token")
        self._client_secret = config.get("client_secret")
        self._access_token = config.get("access_token")

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == "__main__":
    import argparse

    import pudb

    pudb.set_trace()

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
            login_url = AkamaiNetworkListsConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=DEFAULT_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = AkamaiNetworkListsConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
