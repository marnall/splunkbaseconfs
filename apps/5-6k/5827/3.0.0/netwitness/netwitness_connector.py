# File: netwitness_connector.py
#
# Copyright (c) 2017-2024 Splunk Inc.
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
import hashlib
import json
import os
import re
import shutil
import signal
import sys
import tempfile
import uuid
from datetime import datetime

# Phantom imports
import phantom.app as phantom
import phantom.rules as ph_rules
import requests

# Local imports
import netwitness_consts as consts

error_resp_dict = {
    consts.NETWITNESS_REST_RESP_BAD_REQUEST: consts.NETWITNESS_REST_RESP_BAD_REQUEST_MSG,
    consts.NETWITNESS_REST_RESP_UNAUTHORIZED: consts.NETWITNESS_REST_RESP_UNAUTHORIZED_MSG,
    consts.NETWITNESS_REST_RESP_RESOURCE_NOT_FOUND: consts.NETWITNESS_REST_RESP_RESOURCE_NOT_FOUND_MSG,
}


def timeout_handler(signum, frame):
    raise Timeout()


class Timeout(Exception):
    pass


class NetWitnessConnector(phantom.BaseConnector):
    """This is AppConnector class that inherits the BaseConnector class. It implements various actions supported by
    RSA SA device and helper methods required to run the actions.
    """

    def __init__(self):

        # Call the BaseConnector's init first
        super(NetWitnessConnector, self).__init__()
        self._base_url = None
        self._api_username = None
        self._api_password = None
        return

    def initialize(self):
        """This is an optional function that can be implemented by the AppConnector derived class. Since the
        configuration dictionary is already validated by the time this function is called, it's a good place to do any
        extra initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS or
        phantom.APP_ERROR. If this function returns phantom.APP_ERROR, then AppConnector::handle_action will not get
        called.
        """

        config = self.get_config()

        # Initialize parameters
        self._verify = config.get(consts.NETWITNESS_CONFIG_VERIFY, False)
        self._base_url = config[consts.NETWITNESS_CONFIG_SERVER].strip("/")
        self._api_username = config[consts.NETWITNESS_CONFIG_API_USERNAME]
        self._api_password = config[consts.NETWITNESS_CONFIG_API_PASSWORD]

        self.set_validator("netwitness session ids", self._verify_session_ids)

        return phantom.APP_SUCCESS

    def _verify_session_ids(self, param):
        """This function validates the session_ids parameter. It makes sure it is a list of IDs or an ID range"""

        match = re.match("^ *[0-9]+ *(, *[0-9]+ *)*$|^ *[0-9]+ *- *[0-9]+ *$", param)

        return bool(match)

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = None
        error_msg = consts.NETWITNESS_ERR_MSG_UNAVAILABLE

        self.error_print("Error occurred.", e)

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except Exception as e:
            self.error_print("Error occurred while fetching exception information. Details: {}".format(str(e)))

        if not error_code:
            error_text = "Error Message: {}".format(error_msg)
        else:
            error_text = "Error Code: {}. Error Message: {}".format(error_code, error_msg)

        return error_text

    def _make_rest_call(self, action_result, endpoint=None, data=None, method="get", files=None, timeout=consts.NETWITNESS_DEFAULT_REST_TIMEOUT):
        """Function that makes the REST call to the device. It's a generic function that can be called from various
        action handlers.

        :param action_result: object of ActionResult class
        :param endpoint: REST endpoint that needs to appended to the base url
        :param data: request body
        :param method: get/post/put/delete
        :return: status success/failure(along with appropriate message) and response obtained by making an API call
        """

        api_url = "{}{}".format(self._base_url, endpoint) if endpoint else self._base_url
        if files is None:
            files = {}

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        # Make the call
        try:
            kwargs = {"auth": (self._api_username, self._api_password), "data": data, "verify": self._verify, "files": files}
            rest_resp = requests.request(method, api_url, **kwargs)  # nosemgrep: python.requests.best-practice.use-timeout.use-timeout
        except Timeout:
            return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_ERR_TIMEOUT), None
        except Exception as e:
            if "Connection timed out" in str(e):
                self.error_print(consts.NETWITNESS_ERR_TIMEOUT, e)
                return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_ERR_TIMEOUT), None
            self.error_print(consts.NETWITNESS_ERR_SERVER_CONNECTION, e)
            return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_ERR_SERVER_CONNECTION, e), None
        finally:
            signal.alarm(0)

        # store the response text in debug data, it will get dumped in the logs if an error occurs
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": rest_resp.status_code})
            action_result.add_debug_data({"r_text": rest_resp.text})
            action_result.add_debug_data({"r_headers": rest_resp.headers})

        if rest_resp.status_code in error_resp_dict:
            self.debug_print(
                consts.NETWITNESS_ERR_FROM_SERVER.format(status=rest_resp.status_code, detail=error_resp_dict[rest_resp.status_code])
            )
            return (
                action_result.set_status(
                    phantom.APP_ERROR,
                    consts.NETWITNESS_ERR_FROM_SERVER,
                    status=rest_resp.status_code,
                    detail=error_resp_dict[rest_resp.status_code],
                ),
                rest_resp,
            )

        if rest_resp.status_code == consts.NETWITNESS_REST_RESP_SUCC:
            return phantom.APP_SUCCESS, rest_resp

        # All other rest_resp codes from Rest call are errors
        return (
            action_result.set_status(
                phantom.APP_ERROR,
                consts.NETWITNESS_ERR_FROM_SERVER,
                status=rest_resp.status_code,
                detail=consts.NETWITNESS_REST_RESP_OTHER_ERR_MSG,
            ),
            rest_resp,
        )

    def _test_connectivity(self, param):
        """This function tests the connectivity with RSA SA with the provided credentials.

        :param param:
        :return: status success/failure
        """

        action_result = self.add_action_result(phantom.ActionResult(dict(param)))
        self.save_progress(consts.NETWITNESS_CONNECTION_TEST_MSG)
        self.save_progress("Configured URL: {}".format(self._base_url))

        rest_ret_val, _ = self._make_rest_call(
            action_result, endpoint=consts.NETWITNESS_ENDPOINT_GET_CAP, timeout=consts.NETWITNESS_DEFAULT_TEST_TIMEOUT
        )

        if phantom.is_fail(rest_ret_val):
            self.save_progress(action_result.get_message())
            self.set_status(phantom.APP_ERROR, consts.NETWITNESS_TEST_CONNECTIVITY_FAIL)
            return action_result.get_status()

        self.save_progress(consts.NETWITNESS_TEST_CONNECTIVITY_PASS)

        return action_result.set_status(phantom.APP_SUCCESS, consts.NETWITNESS_TEST_CONNECTIVITY_PASS)

    def _move_file_to_vault(self, container_id, file_size, type_str, local_file_path, action_result):
        """Moves the downloaded file to vault.

        :param container_id: ID of the container in which we need to add vault file
        :param file_size: size of file
        :param type_str: file type
        :param local_file_path: path where file is stored
        :param action_result: object of ActionResult class
        :return: status success/failure
        """

        self.send_progress(phantom.APP_PROG_ADDING_TO_VAULT)

        if not file_size:
            file_size = os.path.getsize(local_file_path)

        file_details = {phantom.APP_JSON_SIZE: file_size, phantom.APP_JSON_TYPE: type_str}

        vault_details = {
            phantom.APP_JSON_CONTAINS: [type_str],
            phantom.APP_JSON_ACTION_NAME: self.get_action_name(),
            phantom.APP_JSON_APP_RUN_ID: self.get_app_run_id(),
        }

        vault_details.update(file_details)

        file_name = os.path.basename(local_file_path)

        # Adding file to vault
        try:
            success, message, vault_id = ph_rules.vault_add(
                file_location=local_file_path, container=container_id, file_name=file_name, metadata=vault_details
            )
        except Exception as e:
            msg = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_ERR_VAULT_INFO.format(msg))

        # Updating report data with vault details
        if success:
            file_details[phantom.APP_JSON_VAULT_ID] = vault_id
            file_details[consts.NETWITNESS_JSON_FILE_NAME] = file_name
            action_result.add_data(file_details)
            self.send_progress(consts.NETWITNESS_SUCC_FILE_ADD_TO_VAULT, vault_id=vault_id)
            return phantom.APP_SUCCESS

        # Error while adding file to vault
        self.debug_print("ERROR: Adding file to vault:", message)
        action_result.append_to_message(". {}".format(message))

        # set the action_result status to error, the handler function
        # will most probably return as is
        return phantom.APP_ERROR

    def _check_for_bad_cap(self, cap):
        """The API sometimes returns an empty or corrupted capture when there is no capture data"""

        if not cap:
            return True

        cap_size = sys.getsizeof(cap)

        if not cap_size:
            return True

        if cap_size not in consts.NETWITNESS_BAD_CAP_SIZES:
            return False

        if hashlib.sha256(cap).hexdigest() in consts.NETWITNESS_BAD_CAP_HASHES:
            return True

        return False

    def _get_capture(self, param, cap_type):
        """Download a capture file from RSA NetWitness based on given criteria"""

        action_result = self.add_action_result(phantom.ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Check for optional input parameters
        query = param.get(consts.NETWITNESS_JSON_QUERY)
        time2 = param.get(consts.NETWITNESS_JSON_END_TIME)
        time1 = param.get(consts.NETWITNESS_JSON_START_TIME)
        filename = param.get(consts.NETWITNESS_JSON_FILE_NAME)
        session_id = param.get(consts.NETWITNESS_JSON_SESSION_ID)

        # Need either a session ID, or a complete timeframe
        if not (session_id or query or (time1 and time2)):
            return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_ERR_BAD_PARAMS)

        if session_id and "-" in session_id:
            num_list = list(map(int, session_id.split("-")))
            if num_list[0] > num_list[1]:
                return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_ERR_BAD_RANGE)

        if session_id:

            data = {"sessions": session_id}

            if query:
                data["where"] = query

            # Set filename
            if not filename:
                filename = "netwitness-{0}".format(session_id.replace(",", "_")[:50])

        elif query:

            if time1 and time2:

                try:
                    datetime.strptime(time1, "%Y-%m-%d %H:%M:%S")
                    datetime.strptime(time2, "%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_INVALID_PARAM.format(message=e))

                query += ' && time="{0}"-"{1}"'.format(time1, time2)

            data = {"where": query}

            # Set filename
            if not filename:
                filename = "netwitness-{0}".format(uuid.uuid4())

        elif time1 and time2:

            try:
                datetime.strptime(time1, "%Y-%m-%d %H:%M:%S")
                datetime.strptime(time2, "%Y-%m-%d %H:%M:%S")
            except Exception as e:
                return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_INVALID_PARAM.format(message=e))

            if time1 > time2:
                return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_ERR_REVERSE_TIMES)

            # Prepare request body
            data = {"time1": time1, "time2": time2}

            # Set filename
            if not filename:
                filename = ("netwitness-{0}_{1}".format(time1, time2)).replace("/", "-")

        if not (filename.endswith(".pcap") or filename.endswith(".json")):
            filename = "{0}.{1}".format(filename, consts.NETWITNESS_FILE_TYPE_DICT[cap_type])

        # Set the cap type in the request body
        data["render"] = consts.NETWITNESS_CAP_TYPE_DICT[cap_type]

        rest_ret_val, resp = self._make_rest_call(action_result, endpoint=consts.NETWITNESS_ENDPOINT_GET_CAP, data=data)

        # Something went wrong with the request
        if phantom.is_fail(rest_ret_val):
            return rest_ret_val

        # Check content-type of response
        content_type = resp.headers["content-type"]
        if content_type.find("application/octet-stream") != -1 or content_type.find("application/json") != -1:
            rest_resp = resp.content
        else:
            return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_GET_PCAPS_FAIL)

        if self._check_for_bad_cap(rest_resp):
            summary_data["file_availability"] = False
            return action_result.set_status(phantom.APP_SUCCESS, consts.NETWITNESS_ERR_BAD_CAP)

        # Creating file
        try:
            temp_dir = tempfile.mkdtemp()
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, "wb") as file_obj:
                file_obj.write(rest_resp)
        except Exception as e:
            self.error_print(consts.NETWITNESS_FILE_ERR, e)
            shutil.rmtree(temp_dir)
            return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_FILE_ERR, e)

        container_id = self.get_container_id()

        # Check if file with same file name and size is available in vault and save only if it is not available
        try:
            _, _, vault_meta_info = ph_rules.vault_info(container_id=container_id)
        except Exception as e:
            msg = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_ERR_VAULT_INFO.format(msg))

        # Iterate through each vault item in the container and compare name and size of file
        for vault in vault_meta_info:
            if vault.get("name") == filename and vault.get("size") == os.path.getsize(file_path):
                self.send_progress(consts.NETWITNESS_REPORT_ALREADY_AVAILABLE)
                vault_details = {
                    phantom.APP_JSON_SIZE: vault.get("size"),
                    phantom.APP_JSON_TYPE: consts.NETWITNESS_FILE_TYPE_DICT[cap_type],
                    phantom.APP_JSON_VAULT_ID: vault.get(phantom.APP_JSON_VAULT_ID),
                    consts.NETWITNESS_JSON_FILE_NAME: filename,
                }
                summary_data["file_availability"] = True

                shutil.rmtree(temp_dir)
                action_result.add_data(vault_details)
                return action_result.set_status(phantom.APP_SUCCESS)

        return_val = self._move_file_to_vault(
            container_id, os.path.getsize(file_path), consts.NETWITNESS_FILE_TYPE_DICT[cap_type], file_path, action_result
        )
        shutil.rmtree(temp_dir)

        # Something went wrong while moving file to vault
        if phantom.is_fail(return_val):
            return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_ERR_VAULT)

        summary_data["file_availability"] = True
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_pcap(self, param):

        return self._get_capture(param, consts.NETWITNESS_CAP_TYPE_PACKET)

    def _get_log_capture(self, param):

        return self._get_capture(param, consts.NETWITNESS_CAP_TYPE_LOG)

    def _upload_file(self, param):
        """This method uploads a parser from the vault to a NetWitness decoder"""

        self.debug_print(param)
        action_result = self.add_action_result(phantom.ActionResult(dict(param)))

        vault_id = param[phantom.APP_JSON_VAULT_ID]

        # check the vault for a file with the supplied ID
        try:
            success, message, vault_meta_info = ph_rules.vault_info(vault_id=vault_id)
            if not success:
                return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_ERR_VAULT_INFO.format(message))
            file_info = list(vault_meta_info)[0]
            file_path = file_info.get("path")
        except Exception as e:
            msg = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_ERR_VAULT_INFO.format(msg))

        if not file_path:
            return action_result.set_status(phantom.APP_ERROR, consts.NETWITNESS_ERR_NOT_IN_VAULT)

        upfile = open(file_path, "rb")
        endpoint = "/decoder/parsers/upload"

        ret_val, _ = self._make_rest_call(action_result, endpoint=endpoint, files={"file": (file_info["name"], upfile)}, method="post")

        if not ret_val:
            return ret_val

        return action_result.set_status(phantom.APP_SUCCESS, consts.NETWITNESS_SUCC_UPLOAD)

    def _restart_device(self, param):
        """This method restarts the configured device"""

        action_result = self.add_action_result(phantom.ActionResult(dict(param)))

        endpoint = "/sys?msg=shutdown"

        ret_val, _ = self._make_rest_call(action_result, endpoint=endpoint)

        if phantom.is_fail(ret_val):
            return ret_val

        return action_result.set_status(phantom.APP_SUCCESS, consts.NETWITNESS_SUCC_RESTART)

    def handle_action(self, param):
        """This function gets current action identifier and calls member function of it's own to handle the action.

        :param param: dictionary which contains information about the actions to be executed
        :return: status success/failure
        """

        # Dictionary containing function name of each action
        action_details = {
            "test_asset_connectivity": self._test_connectivity,
            "get_log_capture": self._get_log_capture,
            "restart_device": self._restart_device,
            "upload_file": self._upload_file,
            "get_pcap": self._get_pcap,
        }

        action = self.get_action_identifier()
        return_value = phantom.APP_SUCCESS

        if action in action_details:
            action_function = action_details[action]
            return_value = action_function(param)

        return return_value


if __name__ == "__main__":
    # import pudb
    # pudb.set_trace()

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)
    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))
        connector = NetWitnessConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
