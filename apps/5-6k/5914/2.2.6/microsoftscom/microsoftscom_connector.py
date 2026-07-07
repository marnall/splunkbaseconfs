# File: microsoftscom_connector.py
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
# Standard library imports
import ipaddress
import json

# Phantom App imports
import phantom.app as phantom
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from requests import exceptions
from winrm.exceptions import InvalidCredentialsError, WinRMTransportError
from winrm.protocol import Protocol

# Usage of the consts file is recommended
from microsoftscom_consts import *


class MicrosoftScomConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Configuration variables
        self._server_url = None
        self._username = None
        self._password = None
        self._verify_server_cert = False

    def _handle_test_connectivity(self, param):
        """This function tests the connectivity of an asset with given credentials.

        :param param: (not used in this method)
        :return: status success/failure
        """

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress(MSSCOM_CONNECTING_ENDPOINT_MSG)
        # Execute power shell command
        status, response = self._execute_ps_command(action_result, MSSCOM_PS_COMMAND.format(command="ls"))

        # Something went wrong
        if phantom.is_fail(status):
            self.debug_print(action_result.get_message())
            self.save_progress(MSSCOM_TEST_CONNECTIVITY_FAIL)
            return action_result.get_status()

        # Return success
        self.save_progress(MSSCOM_TEST_CONNECTIVITY_PASS)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_fips_enabled(self):
        try:
            from phantom_common.install_info import is_fips_enabled
        except ImportError:
            return False

        fips_enabled = is_fips_enabled()
        if fips_enabled:
            self.debug_print("FIPS is enabled")
        else:
            self.debug_print("FIPS is not enabled")
        return fips_enabled

    def _execute_ps_command(self, action_result, ps_command):
        """This function is used to execute power shell command.

        :param action_result: object of ActionResult class
        :param ps_command: power shell command
        :return: output of executed power shell command
        """

        resp_output = None
        server_cert_validation = "ignore"
        transport = "ntlm"

        if self._get_fips_enabled():
            transport = "basic"

        if self._verify_server_cert:
            server_cert_validation = "validate"

        protocol = Protocol(
            endpoint=MSSCOM_SERVER_URL.format(url=self._server_url),
            transport=transport,
            username=self._username,
            password=self._password,
            server_cert_validation=server_cert_validation,
        )

        try:
            shell_id = protocol.open_shell()
        except InvalidCredentialsError as credentials_error:
            # In case of invalid credentials
            self.debug_print(MSSCOM_INVALID_CREDENTIAL_ERROR, credentials_error)
            return action_result.set_status(phantom.APP_ERROR, MSSCOM_INVALID_CREDENTIAL_ERROR, credentials_error), resp_output
        except exceptions.SSLError as ssl_error:
            # In case of SSL error
            self.debug_print(MSSCOM_ERROR_BAD_HANDSHAKE, ssl_error)
            return action_result.set_status(phantom.APP_ERROR, MSSCOM_ERROR_BAD_HANDSHAKE, ssl_error), resp_output
        except exceptions.ConnectionError as conn_error:
            # In case of connection error
            self.debug_print(MSSCOM_ERROR_SERVER_CONNECTION, conn_error)
            return action_result.set_status(phantom.APP_ERROR, MSSCOM_ERROR_SERVER_CONNECTION, conn_error), resp_output
        except WinRMTransportError as transport_error:
            self.debug_print(MSSCOM_TRANSPORT_ERROR, transport_error)
            return action_result.set_status(phantom.APP_ERROR, MSSCOM_TRANSPORT_ERROR, transport_error), resp_output
        except Exception as e:
            self.debug_print(MSSCOM_EXCEPTION_OCCURRED, e)
            return action_result.set_status(phantom.APP_ERROR, MSSCOM_EXCEPTION_OCCURRED, e), resp_output

        try:
            # Execute command
            command_id = protocol.run_command(shell_id, ps_command)
            resp_output, resp_error, status_code = protocol.get_command_output(shell_id, command_id)
            protocol.cleanup_command(shell_id, command_id)
            protocol.close_shell(shell_id)
        except Exception as err:
            self.debug_print(MSSCOM_EXCEPTION_OCCURRED, err)
            return action_result.set_status(phantom.APP_ERROR, MSSCOM_EXCEPTION_OCCURRED, err), resp_output

        # In case of error in command execution
        if status_code:
            return action_result.set_status(phantom.APP_ERROR, MSSCOM_EXCEPTION_OCCURRED, resp_error), resp_output

        return action_result.set_status(phantom.APP_SUCCESS), resp_output

    def _handle_list_endpoints(self, param):
        """This function is used to list all endpoints.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Optional values should use the .get() function
        domain = param.get(MSSCOM_PARAM_DOMAIN, "*")

        # Prepare power shell command
        command = f"{MSSCOM_GET_SCOM_AGENT_COMMAND} -DNSHostName *.{domain} | {MSSCOM_CONVERT_TO_CSV_JSON_COMMAND}"

        # Execute power shell command
        status, response = self._execute_ps_command(action_result, MSSCOM_PS_COMMAND.format(command=command))

        # Something went wrong while executing power shell command
        if phantom.is_fail(status):
            self.debug_print(action_result.get_message())
            return action_result.get_status()

        try:
            if response:
                response = json.loads(response)
                # Add data to action_result
                if isinstance(response, dict):
                    action_result.add_data(response)
                else:
                    for item in response:
                        action_result.add_data(item)
        except Exception as e:
            self.debug_print(MSSCOM_JSON_FORMAT_ERROR)
            return action_result.set_status(phantom.APP_ERROR, MSSCOM_JSON_FORMAT_ERROR, e)

        # Update summary
        summary = action_result.update_summary({})
        summary["total_endpoints"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_alerts(self, param):
        """This function is used to get system's health information.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Optional values should use the .get() function
        computer_name = param.get(MSSCOM_PARAM_COMPUTER_NAME)

        # Prepare power shell command to execute
        if computer_name:
            command = f'{MSSCOM_GET_SCOM_ALERT_COMMAND} -ComputerName "{computer_name}" | {MSSCOM_CONVERT_TO_CSV_JSON_COMMAND}'
        else:
            command = f"{MSSCOM_GET_SCOM_ALERT_COMMAND} | {MSSCOM_CONVERT_TO_CSV_JSON_COMMAND}"

        # Execute power shell command
        status, response = self._execute_ps_command(action_result, MSSCOM_PS_COMMAND.format(command=command))

        # Something went wrong
        if phantom.is_fail(status):
            self.debug_print(action_result.get_message())
            return action_result.get_status()

        # Add data to action_result
        try:
            if response:
                response = json.loads(response)
                # Getting response as dict object when only one alert is available
                # Therefore converting the dict to list of dictionary to avoid AttributeError
                if isinstance(response, dict):
                    # Override the resp_ans from dict to list
                    response = [response]
                for item in response:
                    if item.get("ResolutionState") != "255":
                        action_result.add_data(item)
        except Exception as e:
            self.debug_print(MSSCOM_JSON_FORMAT_ERROR)
            return action_result.set_status(phantom.APP_ERROR, MSSCOM_JSON_FORMAT_ERROR, e)

        # Update summary
        summary = action_result.update_summary({})
        summary["total_alerts"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _validate_ip(self, input_ip_address):
        """
        Function that checks given address and return True if address is valid IPv4 or IPV6 address.

        :param input_ip_address: IP address
        :return: status (success/failure)
        """
        try:
            ipaddress.ip_address(input_ip_address)
        except Exception as e:
            self.error_print("Error while validating IP.", e)
            return False
        return True

    def _handle_get_device_info(self, param):
        """This function is used to list all endpoints.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Optional values should use the .get() function
        ip_address = param.get("ip")
        computer_name = param.get("computer_name")

        if not (ip_address or computer_name):
            self.debug_print(MSSCOM_PARAM_NOT_SPECIFIED.format("ip", "computer_name"))
            return action_result.set_status(phantom.APP_ERROR, MSSCOM_PARAM_NOT_SPECIFIED.format("ip", "computer_name"))

        # Prepare power shell command
        command = f"{MSSCOM_GET_SCOM_AGENT_COMMAND} -DNSHostName *.* | {MSSCOM_CONVERT_TO_CSV_JSON_COMMAND}"

        # Execute power shell command
        status, response = self._execute_ps_command(action_result, MSSCOM_PS_COMMAND.format(command=command))

        # Something went wrong while executing power shell command
        if phantom.is_fail(status):
            self.debug_print(action_result.get_message())
            return action_result.get_status()

        try:
            if response:
                response = json.loads(response)
                # Add data to action_result
                if isinstance(response, dict):
                    # If both parameters are present, priority is given to IP
                    if ip_address:
                        ip_list = response["IPAddress"].replace(" ", "").split(",")
                        for value in ip_list:
                            if ip_address == value:
                                action_result.add_data(response)
                                break
                    elif computer_name == response["ComputerName"]:
                        action_result.add_data(response)
                else:
                    for item in response:
                        # If both parameters are present, priority is given to IP
                        if ip_address:
                            ip_list = item["IPAddress"].replace(" ", "").split(",")
                            for value in ip_list:
                                if ip_address == value:
                                    action_result.add_data(item)
                                    break
                        elif computer_name == item["ComputerName"]:
                            action_result.add_data(item)
                            break
        except Exception as e:
            self.debug_print(MSSCOM_JSON_FORMAT_ERROR)
            return action_result.set_status(phantom.APP_ERROR, MSSCOM_JSON_FORMAT_ERROR, e)

        if not action_result.get_data_size():
            return action_result.set_status(phantom.APP_ERROR, "Device not found")

        return action_result.set_status(phantom.APP_SUCCESS, "Device found")

    def handle_action(self, param):
        """This function gets current action identifier and calls member function of its own to handle the action.

        :param param: dictionary which contains information about the actions to be executed
        :return: status success/failure
        """

        # Dictionary mapping each action with its corresponding actions
        action_mapping = {
            "test_connectivity": self._handle_test_connectivity,
            "list_endpoints": self._handle_list_endpoints,
            "list_alerts": self._handle_list_alerts,
            "get_device_info": self._handle_get_device_info,
        }
        action = self.get_action_identifier()
        try:
            run_action = action_mapping[action]
        except Exception as e:
            self.debug_print(e)
            raise ValueError(f"action {action} is not supported")

        return run_action(param)

    def initialize(self):
        """This is an optional function that can be implemented by the AppConnector derived class. Since the
        configuration dictionary is already validated by the time this function is called, it's a good place to do any
        extra initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS or
        phantom.APP_ERROR. If this function returns phantom.APP_ERROR, then AppConnector::handle_action will not get
        called.
        """

        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()
        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}

        # Get the asset config
        config = self.get_config()
        self.set_validator("ipv6", self._validate_ip)
        # Required config parameter
        self._server_url = config[MSSCOM_CONFIG_SERVER_URL].strip("/")
        self._username = config[MSSCOM_CONFIG_USERNAME]
        self._password = config[MSSCOM_CONFIG_PASSWORD]

        # Optional config parameter
        self._verify_server_cert = config.get(MSSCOM_CONFIG_VERIFY_SSL, False)

        return phantom.APP_SUCCESS

    def finalize(self):
        """This function gets called once all the param dictionary elements are looped over and no more handle_action
        calls are left to be made. It gives the AppConnector a chance to loop through all the results that were
        accumulated by multiple handle_action function calls and create any summary if required. Another usage is
        cleanup, disconnect from remote devices etc.
        """

        # Save the state
        self.save_state(self._state)
        return phantom.APP_SUCCESS


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

        connector = MicrosoftScomConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
