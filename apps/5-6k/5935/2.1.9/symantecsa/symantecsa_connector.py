# File: symantecsa_connector.py
#
# Copyright (c) 2019-2025 Splunk Inc.
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
import datetime
import os

import phantom.app as phantom
import requests
import simplejson as json
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault

import soleraconnector as solera
from symantecsa_consts import *


class SymantecsaConnector(BaseConnector):
    ACTION_ID_TEST_ASSET_CONNECTIVITY = "test_connectivity"
    ACTION_ID_GET_PACKET_DETAILS = "get_packet_details"

    def __init__(self):
        super().__init__()
        self._username = None
        self._apikey = None
        self._device_ip = None
        self._verify = None
        self._auth = None
        self._connector = None

    def initialize(self):
        """
        Initializes the authentication tuple that the REST call needs

        :return:
        """
        config = self.get_config()
        self._username = config[SYMANTECSA_CONFIG_USERNAME]
        self._apikey = config[SYMANTECSA_CONFIG_API_KEY]
        self._device_ip = config[SYMANTECSA_CONFIG_DEVICE_IP]
        self._verify = config[phantom.APP_JSON_VERIFY]
        self._auth = (self._username, self._apikey)
        try:
            self._connector = solera.SoleraConnector(self._username, self._apikey, self._device_ip, SYMANTECSA_API_VERSION, self._verify)
        except Exception as e:
            return self.set_status(phantom.APP_ERROR, e)
        return phantom.APP_SUCCESS

    def _get_error_message_from_exception(self, e):
        """This method is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        error_code = PHANTOM_ERROR_CODE_UNAVAILABLE
        error_message = PHANTOM_ERROR_MESSAGE_UNAVAILABLE
        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except:
            pass

        return f"Error Code: {error_code}. Error Message: {error_message}"

    def _make_rest_call(self, action_result, endpoint, data=None, test=False):
        """Calls the API v6 and returns the result

        :param endpoint: URI of the API endpoint
        :param params: Params, if any
        :param method: HTTP Method GET or POST
        :param test: If this is a test connectivity.  Default False
        :return: True or False, and Error Message or response result
        """
        # V6 is needed for the updated download query
        if data is None:
            data = {}
        url = f"https://{self._device_ip}{SYMANTECSA_ENDPOINT_BASE_URI}{endpoint}"
        if test:
            url = endpoint
        try:
            r = requests.get(url, auth=self._auth, verify=self._verify, data=data, timeout=SYMANTECSA_DEFAULT_REQUEST_TIMEOUT)
            resp_json = r.json()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error parsing response to JSON. Error : {error_message}"), None
        return phantom.APP_SUCCESS, resp_json

    def _test_connectivity(self):
        """Function that handles the test connectivity action, it is much simpler than other action handlers."""
        self.save_progress(SYMANTECSA_TEST_CONNECTIVITY_START, base_url=self._device_ip)
        endpoint = f"https://{self._device_ip}{SYMANTECSA_ENDPOINT_TEST_CONNECTIVITY}"
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, endpoint)

        action_result = ActionResult()
        self.save_progress("Making a test REST call")

        # Make the rest endpoint call
        ret_val, response = self._make_rest_call(action_result, endpoint, test=True)

        # Process errors
        if phantom.is_fail(ret_val) or (response.get("resultCode") != "API_SUCCESS_CODE"):
            self.debug_print(action_result.get_message())
            self.set_status(phantom.APP_ERROR, action_result.get_message())

            # Append the message to display
            self.append_to_message(SYMANTECSA_TEST_CONNECTIVITY_ERROR)

            self.save_progress(SYMANTECSA_TEST_CONNECTIVITY_FAILED)
            return phantom.APP_ERROR

        self.save_progress(SYMANTECSA_TEST_CONNECTIVITY_SUCCESS)
        return self.set_status_save_progress(phantom.APP_SUCCESS)

    def _get_packet_details(self, params):
        """
        Currently the only action that is supported by this app (aside from test connectivity).
        Retrieves a pcap file generated by Security Analytics.
        :param params: from the action_result handler
        :return: an action result
        """
        action_result = self.add_action_result(ActionResult(dict(params)))
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        start_time = params[SYMANTECSA_ACTION_PARAM_START_TIME]
        end_time = params[SYMANTECSA_ACTION_PARAM_END_TIME]
        name = params[SYMANTECSA_ACTION_PARAM_FILENAME]
        filter = params[SYMANTECSA_ACTION_PARAM_FILTER]

        # validation for start time and end time
        try:
            start = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
            end = datetime.datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S")
        except:
            return action_result.set_status(phantom.APP_ERROR, SYMANTECSA_TIME_FORMAT_ERROR)

        # validation for incorrect timespan
        now = datetime.datetime.now()
        if start >= end or start > now:
            return action_result.set_status(phantom.APP_ERROR, SYMANTECSA_TIME_RANGE_ERROR)

        path = f"/timespan/{start_time}_{end_time}"

        # Add custom_query to path
        if filter[0] != "/":
            return action_result.set_status(phantom.APP_ERROR, SYMANTECSA_FILTER_ERROR)

        custom_query = filter.replace("\\", "/")
        path = f"{path}{custom_query}/"

        # adding run timestamp in filename
        name = "{filename} {timestamp}".format(filename=name, timestamp=datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%dT%H:%M:%S"))

        kwargs = {"path": path, "name": name}

        # Vault support for NRI instances.
        if hasattr(Vault, "get_vault_tmp_dir"):
            temp_dir = f"{Vault.get_vault_tmp_dir()}/{name}"
        else:
            temp_dir = SYMANTECSA_PCAP_FILE_DOWNLOAD_LOCATION.format(NAME=name)

        try:
            self.debug_print("Calling API")
            resp = self._connector.callAPI("GET", SYMANTECSA_ENDPOINT_GET_PACKET_DETAILS, kwargs, temp_dir)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error : {error_message}")

        # Internal server error
        if resp.get("resultCode") and resp.get("resultCode") != "API_SUCCESS_CODE":
            resultCode = resp.get("resultCode")
            errorList = resp.get("errors")
            errorMsg = " ".join(str(x) for x in errorList)
            return action_result.set_status(phantom.APP_ERROR, SYMANTECSA_GET_PCAP_INVALID_INPUT.format(resultCode, errorMsg))

        # No filepath in response
        file_path = resp.get("download_file")
        if not file_path:
            return action_result.set_status(phantom.APP_ERROR, SYMANTECSA_GET_PCAP_PATH_NOT_FOUND)

        ret_val = self.is_empty_file(file_path, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()
        try:
            Vault.add_attachment(temp_dir, container_id=self.get_container_id(), file_name=name)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, VAULT_UNABLE_TO_ADD_FILE.format(error_message))

        action_result.add_data(resp)
        return action_result.set_status(phantom.APP_SUCCESS, SYMANTECSA_GET_PCAP_SUCCESS)

    def is_empty_file(self, file_path, action_result):
        # For file size zero
        try:
            with open(file_path, "rb") as temp_file:
                temp_file_data = temp_file.read()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, status_message=f"Error : {error_message}")

        # For empty file
        if (not os.path.getsize(file_path)) or temp_file_data == SYMANTECSA_EMPTY_FILE:
            # Delete file
            os.unlink(file_path)
            return action_result.set_status(phantom.APP_ERROR, status_message=SYMANTECSA_NO_DATA_FOUND_MESSAGE)
        return phantom.APP_SUCCESS

    def handle_action(self, params):
        action = self.get_action_identifier()
        ret_val = phantom.APP_SUCCESS
        if action == self.ACTION_ID_GET_PACKET_DETAILS:
            ret_val = self._get_packet_details(params)
        elif action == self.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity()
        return ret_val


if __name__ == "__main__":
    # Imports
    import sys

    import pudb

    # Breakpoint at runtime
    pudb.set_trace()

    # The first param is the input json file
    with open(sys.argv[1]) as f:
        # Load the input json file
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=" " * 4))

        # Create the connector class object
        connector = SymantecsaConnector()

        # Se the member vars
        connector.print_progress_message = True

        # Call BaseConnector::_handle_action(...) to kickoff action handling.
        ret_val = connector._handle_action(json.dumps(in_json), None)

        # Dump the return value
        print(ret_val)

    sys.exit(0)
