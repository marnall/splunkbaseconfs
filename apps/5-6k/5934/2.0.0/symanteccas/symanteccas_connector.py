# File: symanteccas_connector.py
#
# Copyright (c) 2016-2022 Splunk Inc.
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
import ssl
import sys

import phantom.app as phantom
import requests
import websocket
from bs4 import UnicodeDammit
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault

from symanteccas_consts import *


class SymanteccasConnector(BaseConnector):

    def __init__(self):

        # Calling the BaseConnector's init function
        super(SymanteccasConnector, self).__init__()
        self._api_key = None
        self._url = None
        self._websocket_url = None
        self._verify_server_cert = False
        self._timeout = SYMANTECCAS_DEFAULT_TIMEOUT
        self._headers = None
        self._websocket_conn = None
        self._server_request_id = None
        return

    def _handle_py_ver_compat_for_input_str(self, input_str, always_encode=False):
        """
        This method returns the encoded|original string based on the Python version.
        :param input_str: Input string to be processed
        :return: input_str (Processed input string based on following logic 'input_str - Python 3; encoded input_str - Python 2')
        """

        try:
            if input_str and (self._python_version < 3 or always_encode):
                input_str = UnicodeDammit(input_str).unicode_markup.encode('utf-8')
        except:
            self.debug_print("Error occurred while handling python 2to3 compatibility for the input string")

        return input_str

    def initialize(self):

        """
        This is an optional function that can be implemented by the AppConnector derived class. Since the configuration
        dictionary is already validated by the time this function is called, it's a good place to do any extra
        initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS or
        phantom.APP_ERROR. If this function returns phantom.APP_ERROR, then AppConnector::handle_action will not get
        called.
        """
        try:
            self._python_version = int(sys.version_info[0])
        except:
            return self.set_status(phantom.APP_ERROR, "Error occurred while getting the Phantom server's Python major version")

        config = self.get_config()
        self._api_key = self._handle_py_ver_compat_for_input_str(config[SYMANTECCAS_JSON_API_KEY])
        self._url = self._handle_py_ver_compat_for_input_str(config[SYMANTECCAS_JSON_URL].strip('/'))
        self._verify_server_cert = config.get(SYMANTECCAS_JSON_VERIFY_SERVER_CERT, False)
        self._timeout = config.get(SYMANTECCAS_JSON_TIMEOUT_SECS, SYMANTECCAS_DEFAULT_TIMEOUT)
        self._headers = {SYMANTECCAS_X_API_TOKEN: self._api_key}
        url_components = self._url.split("://")

        if len(url_components) > 1:
            protocol = url_components[0]
            device_address = url_components[1]
            if protocol == 'https':
                self._websocket_url = "wss://" + device_address
            elif protocol == 'http':
                self._websocket_url = "ws://" + device_address
            else:
                self._websocket_url = self._url
        else:
            self._websocket_url = self._url

        return phantom.APP_SUCCESS

    def _get_error_message_from_exception(self, e):
        """ This method is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        try:
            if e.args:
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_code = ERR_CODE_MSG
                    error_msg = e.args[0]
            else:
                error_code = ERR_CODE_MSG
                error_msg = ERR_MSG_UNAVAILABLE
        except:
            error_code = ERR_CODE_MSG
            error_msg = ERR_MSG_UNAVAILABLE

        try:
            error_msg = self._handle_py_ver_compat_for_input_str(error_msg)
        except TypeError:
            error_msg = TYPE_ERR_MSG
        except:
            error_msg = ERR_MSG_UNAVAILABLE

        return error_code, error_msg

    # Function that makes the REST call to the device,
    # generic function that can be called from various action handlers
    def _make_rest_call(self, endpoint, action_result, method="post", files=None):

        rest_resp = None

        error_resp_dict = {
            SYMANTECCAS_REST_RESP_RESOURCE_INCORRECT: SYMANTECCAS_REST_RESP_RESOURCE_INCORRECT_MSG,
            SYMANTECCAS_REST_RESP_ACCESS_DENIED: SYMANTECCAS_REST_RESP_ACCESS_DENIED_MSG,
            SYMANTECCAS_REST_RESP_RESOURCE_NOT_FOUND: SYMANTECCAS_REST_RESP_RESOURCE_NOT_FOUND_MSG
        }

        # get or post or put, whatever the caller asked us to use,
        # if not specified the default will be 'post'
        try:
            request_func = getattr(requests, method)
        except:
            self.save_progress(SYMANTECCAS_ERR_API_UNSUPPORTED_METHOD, method=method)
            # set the action_result status to error, the handler function
            # will most probably return as is
            return action_result.set_status(phantom.APP_ERROR, SYMANTECCAS_ERR_API_UNSUPPORTED_METHOD,
                                            method=str(method)), rest_resp

        # Make the call
        try:

            response = request_func(SYMANTECCAS_BASE_URL.format(url=self._url) + endpoint,
                                    headers=self._headers, files=files, verify=self._verify_server_cert)

        except Exception as e:
            error_code, error_msg = self._get_error_message_from_exception(e)
            error_text = "{0}. Error Code:{1}. Error Message:{2}".format(
                SYMANTECCAS_ERR_SERVER_CONNECTION,
                error_code,
                error_msg
            )
            self.debug_print(error_text)
            # set the action_result status to error, the handler function
            # will most probably return as is
            return action_result.set_status(phantom.APP_ERROR, error_text), rest_resp

        if response.status_code in error_resp_dict.keys():
            self.debug_print(SYMANTECCAS_ERR_FROM_SERVER.format(status=response.status_code,
                                                                detail=error_resp_dict[response.status_code]))
            # set the action_result status to error, the handler function
            # will most probably return as is
            return action_result.set_status(phantom.APP_ERROR, SYMANTECCAS_ERR_FROM_SERVER, status=response.status_code,
                                            detail=error_resp_dict[response.status_code]), rest_resp

        # Try parsing the json, even in the case of an HTTP error the data
        # might contain a json of details 'message'
        if response.status_code == SYMANTECCAS_REST_RESP_SUCCESS:
            content_type = response.headers['content-type']
            if content_type.find('json') != -1:
                try:
                    rest_resp = response.json()
                except Exception as e:
                    # response.text is guaranteed to be NON None, it will be empty,
                    # but not None
                    msg_string = SYMANTECCAS_ERR_JSON_PARSE.format(raw_text=response.text)
                    self.debug_print(msg_string)
                    return action_result.set_status(phantom.APP_ERROR, msg_string, e), rest_resp

            # If error in response
            result = rest_resp.get('result', {})
            if result.get(SYMANTECCAS_JSON_RESP_STATUS) == SYMANTECCAS_STATUS_ERROR:
                error_msg = result.get(SYMANTECCAS_JSON_RESP_ERROR)
                self.debug_print(SYMANTECCAS_ERR_UNABLE_FULFILL_REQ_WITH_ERROR.format(error=error_msg))
                return action_result.set_status(phantom.APP_ERROR,
                                                SYMANTECCAS_ERR_UNABLE_FULFILL_REQ_WITH_ERROR.format(error=error_msg)),\
                       rest_resp

            return phantom.APP_SUCCESS, rest_resp

        # All other response codes from Rest call are failures
        # The HTTP response doesnt return error message in case of unknown error code
        self.debug_print(SYMANTECCAS_ERR_FROM_SERVER.format(status=response.status_code,
                                                            detail=SYMANTECCAS_REST_RESP_OTHER_ERROR_MSG))

        # set the action_result status to error, the handler function
        # will most probably return as is
        return action_result.set_status(phantom.APP_ERROR, SYMANTECCAS_ERR_FROM_SERVER, status=response.status_code,
                                        detail=SYMANTECCAS_REST_RESP_OTHER_ERROR_MSG), rest_resp

    def _test_connectivity(self, param):

        """
        Called when the user depresses the test connectivity button on the Phantom UI.
        Use a basic query to determine if the source IP, port and API key is correct

        Initiate a websocket and start listening to it
        In a normal scenario we do not expect any message over socket and wait until timeout
        If we receive message "Access Denied" or any other exception its a failure
        """

        action_result = ActionResult()
        self.save_progress(SYMANTECCAS_TEST_CONN_LOGIN)
        response = None

        # Querying endpoint to detonate empty file
        self.save_progress(SYMANTECCAS_CONNECTION_TEST_MSG)
        self.save_progress("Configured URL: {}".format(self._url))
        self.save_progress("Configured WebSocket URL: {}".format(self._websocket_url))

        ret_val, json_resp = self._make_rest_call(SYMANTECCAS_DETONATE_FILE_ENDPOINT, action_result)

        # Since no file is uploaded, make rest call should fail with message "No file uploaded"
        if phantom.is_fail(ret_val) and "No file uploaded" not in action_result.get_message():
            self.save_progress(action_result.get_message())
            return action_result.get_status()

        # Querying endpoint to check websocket connection to device
        self.save_progress("Creating websocket connection")
        ret_val = self._create_web_socket(action_result)

        # If websocket connection is not successful
        if phantom.is_fail(ret_val):
            self.save_progress(action_result.get_message())
            return action_result.get_status()

        # Opening websocket connection to listen for traffic
        try:
            # To get response from websocket
            response = self._websocket_conn.recv()

            # If we get Access denied in response, it means unauthorised connection
            if response == SYMANTECCAS_SOCKET_ERR_ACCESS_DENIED:
                self.debug_print(SYMANTECCAS_SOCKET_ERR_ACCESS_DENIED)
                self.save_progress("Access denied. Check the credentials.")
                self.set_status(phantom.APP_ERROR, SYMANTECCAS_CONNECTIVITY_FAIL)
                return action_result.set_status(phantom.APP_ERROR)

        except websocket.WebSocketTimeoutException:
            # Success scenario
            # If we will not get any response until time out, its success.
            if response != SYMANTECCAS_SOCKET_ERR_ACCESS_DENIED:
                self.set_status_save_progress(phantom.APP_SUCCESS, SYMANTECCAS_CONNECTIVITY_SUCC)
                return action_result.set_status(phantom.APP_SUCCESS)

        except Exception as e:
            # In case of any other error scenarios
            self.debug_print(SYMANTECCAS_CONNECTIVITY_FAIL, e)
            self.set_status_save_progress(phantom.APP_ERROR, SYMANTECCAS_CONNECTIVITY_FAIL, e)
            return action_result.set_status(phantom.APP_ERROR)

        # In all other cases return success
        self.set_status_save_progress(phantom.APP_SUCCESS, SYMANTECCAS_CONNECTIVITY_SUCC)
        return action_result.set_status(phantom.APP_SUCCESS)

    # This function is used for websocket connection with sandbox
    def _create_web_socket(self, action_result):

        # Validating if timeout parameter is positive integer
        if not (str(self._timeout).isdigit() and int(self._timeout) > 0):
            self.debug_print(SYMANTECCAS_JSON_INVALID_TIMEOUT)
            self.save_progress(SYMANTECCAS_JSON_INVALID_TIMEOUT)
            return action_result.set_status(phantom.APP_ERROR, SYMANTECCAS_JSON_INVALID_TIMEOUT)

        # In case of test_asset_connectivity, ignoring the actual timeout as it may be too high.
        # Overriding timeout to 5 secs
        if phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            self.save_progress(SYMANTECCAS_TEST_CONN_OVERRIDE_TIMEOUT)
            time_out = SYMANTECCAS_TEST_CONN_TIMEOUT
        else:
            time_out = self._timeout

        try:
            # Calling endpoint as per verify server certificate input parameter
            # For secure connection using wss, else ws
            if self._verify_server_cert:
                self._websocket_conn = websocket.create_connection(SYMANTECCAS_TEST_CONN_ENDPOINT.format(
                    websocket_url=self._websocket_url), header=self._headers, timeout=int(time_out),
                    sslopt={"ca_certs": self.get_ca_bundle(), "cert_reqs": ssl.CERT_REQUIRED})
            else:
                self._websocket_conn = websocket.create_connection(SYMANTECCAS_TEST_CONN_ENDPOINT.format(
                    websocket_url=self._websocket_url), header=self._headers, timeout=int(time_out),
                    sslopt={"cert_reqs": ssl.CERT_NONE})

        except Exception as e:
            self.debug_print(SYMANTECCAS_ERR_SERVER_CONNECTION, e)
            return action_result.set_status(phantom.APP_ERROR, SYMANTECCAS_ERR_SERVER_CONNECTION, e)

        return phantom.APP_SUCCESS

    def _detonate_file(self, param):

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Initiating websocket connection
        ret_val = self._create_web_socket(action_result)

        # If websocket connection is unsuccessful
        if phantom.is_fail(ret_val):
            self.set_status(phantom.APP_ERROR, SYMANTECCAS_CONNECTIVITY_FAIL)
            return action_result.get_status()

        # Call for detonate file scan over REST
        return_val, json_resp = self._query_file(param, action_result)

        # If something went wrong
        if phantom.is_fail(return_val):
            return action_result.get_status()

        # If response is None
        if not json_resp:
            self.debug_print(SYMANTECCAS_ERR_UNABLE_FULFILL_REQ)
            return action_result.set_status(phantom.APP_ERROR, SYMANTECCAS_ERR_UNABLE_FULFILL_REQ)

        # Get the server generated request id to match with websocket response id
        result = json_resp.get(SYMANTECCAS_JSON_RESP_RESULT)
        self._server_request_id = result[SYMANTECCAS_JSON_RESP_ID]

        # Wait for websocket response
        status, json_resp = self._wait_for_report(action_result)

        if phantom.is_fail(status):
            return action_result.get_status()

        # Add score and status in summary
        if json_resp.get(SYMANTECCAS_JSON_RESP_SCORE) or json_resp.get(SYMANTECCAS_JSON_RESP_SCORE) == 0:
            summary_data["global_score"] = json_resp[SYMANTECCAS_JSON_RESP_SCORE]
        if json_resp.get(SYMANTECCAS_JSON_RESP_STATUS):
            summary_data["global_status"] = json_resp[SYMANTECCAS_JSON_RESP_STATUS]

        action_result.add_data(json_resp)

        action_result.set_status(phantom.APP_SUCCESS)
        return action_result.get_status()

    def _query_file(self, param, action_result):

        # Mandatory input parameter
        vault_id = self._handle_py_ver_compat_for_input_str(param[SYMANTECCAS_JSON_VAULT_ID])

        try:
            file_obj = open(Vault.get_file_path(vault_id), 'rb')
            filename = (Vault.get_file_info(vault_id=vault_id, file_name=None, container_id=None)[0])['name']
        except:
            self.debug_print(SYMANTECCAS_UNKNOWN_VAULT_ID.format(vault_id=vault_id))
            return action_result.set_status(phantom.APP_ERROR,
                                            SYMANTECCAS_UNKNOWN_VAULT_ID.format(vault_id=vault_id)), None

        # Optional input parameter
        file = param.get(SYMANTECCAS_JSON_FILE_NAME, filename)

        files = {filename: (file, file_obj)}

        return self._make_rest_call(SYMANTECCAS_DETONATE_FILE_ENDPOINT, action_result, files=files)

    def _wait_for_report(self, action_result):

        """
        This function is used to wait for response from websocket. We will compare server generated id with id in
        received response If both ids are matched we will return json response.
        """

        # Poll for 10 times if response is not received
        for polling_attempt in range(SYMANTECCAS_STATUS_MAX_POLLING_COUNT):

            try:
                # Wait for websocket response
                response = self._websocket_conn.recv()
            except websocket._exceptions.WebSocketTimeoutException as wse:
                self.debug_print(SYMANTECCAS_ERR_WEBSOCKET_TIMEOUT)
                return action_result.set_status(phantom.APP_ERROR, SYMANTECCAS_ERR_WEBSOCKET_TIMEOUT, wse), None
            except Exception as e:
                self.debug_print(SYMANTECCAS_ERR_WEBSOCKET, e)
                return action_result.set_status(phantom.APP_ERROR, SYMANTECCAS_ERR_WEBSOCKET, e), None

            # If we get response before timeout
            if response:

                try:
                    # Convert string type response in json
                    json_resp = json.loads(response)
                except Exception as e:
                    self.debug_print(SYMANTECCAS_ERR_WAITING_REPORT.format(raw_text=response))
                    return action_result.set_status(phantom.APP_ERROR, SYMANTECCAS_ERR_WAITING_REPORT.format(
                        raw_text=response), e), None

                # Check if received response is complete(status 1) or partially complete(status 3) and check if server
                # generated request id is matched or not with current response
                if json_resp.get(SYMANTECCAS_JSON_RESP_STATUS) in \
                        [SYMANTECCAS_STATUS_COMPLETE, SYMANTECCAS_STATUS_COMPLETE_WITH_ERROR] \
                        and json_resp[SYMANTECCAS_JSON_RESP_ID] == self._server_request_id:
                    return phantom.APP_SUCCESS, json_resp

        self.debug_print(SYMANTECCAS_ERR_WEBSOCKET_NO_RESPONSE)
        return action_result.set_status(phantom.APP_ERROR, SYMANTECCAS_ERR_WEBSOCKET_NO_RESPONSE), None

    def finalize(self):

        """
        This function gets called once all the param dictionary elements are looped over and no more handle_action calls
        are left to be made. It gives the AppConnector a chance to loop through all the results that were accumulated by
        multiple handle_action function calls and create any summary if required. Another usage is cleanup, disconnect
        from remote devices etc.

        Purpose of this function is to close websocket connection
        """

        if self._websocket_conn:
            self._websocket_conn.close()

    def handle_action(self, param):

        """
        This function implements the main functionality of the AppConnector. It gets called for every param dictionary
        element in the parameters array. In it's simplest form it gets the current action identifier and then calls a
        member function of it's own to handle the action. This function is expected to create the results of the action
        run that get added to the connector run. The return value of this function is mostly ignored by the
        BaseConnector. Instead it will just loop over the next param element in the parameters array and call
        handle_action again.

        We create a case structure in Python to allow for any number of actions to be easily added.
        """

        # Supported actions by app
        supported_actions = {
            'test_asset_connectivity': self._test_connectivity,
            'detonate_file': self._detonate_file,
        }

        action = self.get_action_identifier()

        try:
            run_action = supported_actions[action]
        except:
            raise ValueError('action %r is not supported' % action)

        return run_action(param)


if __name__ == '__main__':

    import pudb

    pudb.set_trace()
    if len(sys.argv) < 2:
        print('No test json specified as input')
        sys.exit(0)
    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))
        connector = SymanteccasConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))
    sys.exit(0)
