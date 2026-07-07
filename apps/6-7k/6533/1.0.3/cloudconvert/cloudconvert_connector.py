# File: cloudconvert_connector.py
#
# Copyright (c) 2022-2025 Splunk Inc.
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
# Phantom App imports

import json
import os
import time
import uuid

import phantom.app as phantom
import phantom.rules as ph_rules
import requests
import xmltodict
from bs4 import UnicodeDammit
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault
from phantom_common import paths

# Usage of the consts file is recommended
from cloudconvert_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class CloudConvertConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None
        self._headers = dict()
        self._api_key = None
        self._stream_file_data = False
        self._base_url = None
        self._timeout = None

    def _get_error_message_from_exception(self, e):
        """This function is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        error_msg = CLOUDCONVERT_ERROR_MSG
        error_code = CLOUDCONVERT_ERROR_CODE_MSG
        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_code = CLOUDCONVERT_ERROR_CODE_MSG
                    error_msg = e.args[0]
        except Exception as ex:
            self.debug_print(f"Exception: {ex}")
            pass

        if not error_code:
            error_text = f"Error Message: {error_msg}"
        else:
            error_text = CLOUDCONVERT_ERROR_MSG_FORMAT.format(error_code, error_msg)

        return error_text

    def _validate_integers(self, action_result, parameter, key, allow_zero=False):
        """This method is to check if the provided input parameter value
        is a non-zero positive integer and returns the integer value of the parameter itself.
        :param action_result: Action result or BaseConnector object
        :param parameter: input parameter
        :return: integer value of the parameter or None in case of failure
        """

        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, CLOUDCONVERT_VALIDATE_INTEGER_MSG.format(key=key)), None
                parameter = int(parameter)

            except Exception:
                return action_result.set_status(phantom.APP_ERROR, CLOUDCONVERT_VALIDATE_INTEGER_MSG.format(key=key)), None

            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, CLOUDCONVERT_VALIDATE_NON_NEGATIVE_INTEGER_MSG.format(key=key)), None
            if not allow_zero and parameter == 0:
                return action_result.set_status(phantom.APP_ERROR, CLOUDCONVERT_VALIDATE_NON_ZERO_POSITIVE_INTEGER_MSG.format(key=key)), None

        return phantom.APP_SUCCESS, parameter

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, f"Status code: {response.status_code}. Empty response and no information in the header"),
            None,
        )

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Unable to parse JSON response. Error: {error_message}",
                ),
                None,
            )

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        if resp_json.get("code") and resp_json.get("message"):
            error_code = resp_json.get("code", "No code found")
            error_message = resp_json.get("message", "No details found")
            message = f"Error from server. Error Code: {error_code} Data from server: {error_message}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, message), resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_xml_response(self, r, action_result):
        resp_xml = None
        try:
            if r.text:
                resp_xml = xmltodict.parse(r.text)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse XML response. Error: {error_message}"))

        if 200 <= r.status_code < 400:
            return RetVal(phantom.APP_SUCCESS, resp_xml)
        error_code = resp_xml.get("Error", {}).get("Code")
        error_message = resp_xml.get("Error", {}).get("Message")

        message = f"Error from server. Status Code: {r.status_code} Data from server: {error_code}. {error_message}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), resp_xml)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            if not self._stream_file_data:
                action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        if self._stream_file_data and 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, r)

        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        if "xml" in r.headers.get("Content-Type", ""):
            return self._process_xml_response(r, action_result)

        if not r.text:
            return self._process_empty_response(r, action_result)

        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, url, action_result, headers=None, files=None, data=None, method="get", empty_headers=False, **kwargs):
        resp_json = None
        if headers:
            headers.update(self._headers)
        else:
            headers = self._headers
        if empty_headers:
            headers = {}
        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json

        try:
            requests_response = request_func(
                url,
                headers=headers,
                data=data,
                files=files,
                **kwargs,
            )
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, f"Error connecting to server. Details: {self._get_error_message_from_exception(e)}"
            ), resp_json

        return self._process_response(requests_response, action_result)

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress(CLOUDCONVERT_CONNECTION_MSG)
        ret_val, _ = self._make_rest_call(url=TEST_CONNECTIVITY_URL, action_result=action_result, method="get")

        if phantom.is_fail(ret_val):
            self.save_progress(CLOUDCONVERT_CONNECTIVITY_FAIL_MSG)
            return action_result.get_status()
        self.save_progress(CLOUDCONVERT_CONNECTIVITY_PASS_MSG)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_file_info_from_vault(self, action_result, vault_id, input_filename=None):
        file_info = {}

        # Check for file in vault
        try:
            _, _, vault_meta = ph_rules.vault_info(container_id=self.get_container_id(), vault_id=vault_id)
            if not vault_meta:
                self.debug_print(f"Error while fetching meta information for vault ID: {vault_id}")
                return action_result.set_status(phantom.APP_ERROR, CLOUDCONVERT_ERROR_FILE_NOT_IN_VAULT), None
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, CLOUDCONVERT_ERROR_FILE_NOT_IN_VAULT), None

        vault_meta = list(vault_meta)
        vault_meta_dict = {}
        if input_filename:
            for vault_data in vault_meta:
                if vault_data.get("name") == input_filename:
                    vault_meta_dict.update(vault_data)
                    break
            if not vault_meta_dict:
                return action_result.set_status(phantom.APP_ERROR, CLOUDCONVERT_ERROR_FILENAME_NOT_IN_VAULT), None
        else:
            vault_meta_dict = vault_meta[0]

        file_info["path"] = vault_meta_dict["path"]
        file_info["name"] = vault_meta_dict["name"]

        return action_result.set_status(phantom.APP_SUCCESS, "File info fetched successfully"), file_info

    def _handle_convert_file(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        vault_id = param["vault_id"]
        input_filename = param.get("input_filename")

        ret_val, file_info = self._get_file_info_from_vault(action_result, vault_id, input_filename)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if not input_filename:
            input_filename = file_info["name"]
        filepath = file_info["path"]

        ret_val, payload, job_id = self._initialize_job(param, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val = self._import_task(param, action_result, payload, filepath, input_filename)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, link = self._get_link(param, action_result, job_id)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, vault_info = self._get_converted_file(param, action_result, link, input_filename)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Vault Artifact
        cef_artifact = dict()
        container_id = vault_info["container_id"]
        output_filename = vault_info["name"]

        if output_filename:
            cef_artifact.update({"fileName": output_filename})
        if vault_info["vault_id"]:
            cef_artifact.update({"vaultId": vault_info["vault_id"], "cs6": vault_info["vault_id"], "cs6Label": "Vault ID"})
            self._add_vault_hashes_to_dictionary(cef_artifact, vault_info["vault_id"], container_id)
        if not cef_artifact:
            pass

        artifact = {}
        artifact["name"] = "Vault Artifact"
        artifact["cef"] = cef_artifact
        artifact["container_id"] = vault_info["container_id"]

        self.debug_print("Adding Source Data Identifier to the Vault artifact")

        ret_val, message, _ = self.save_artifacts([artifact])
        self.debug_print(f"save_artifacts returns, value: {ret_val}, reason: {message}")

        if phantom.is_fail(ret_val):
            message = f"Failed to save ingested artifacts, error msg: {message}"
            return action_result.set_status(phantom.APP_ERROR, message)
        action_result.add_data({"vault_id": vault_info["vault_id"], "converted_file": output_filename, "file_size": cef_artifact["fileSize"]})
        return action_result.set_status(phantom.APP_SUCCESS, "File converted successfully")

    def _add_vault_hashes_to_dictionary(self, cef_artifact, vault_id, container_id):
        try:
            _, _, vault_info = ph_rules.vault_info(vault_id=vault_id, container_id=container_id)
            cef_artifact["fileSize"] = vault_info[0].get("size")
        except Exception:
            return phantom.APP_ERROR, "Could not retrieve vault file"

        if not vault_info:
            return (phantom.APP_ERROR, "Vault ID not found")

        # The return value is a list, each item represents an item in the vault
        # matching the vault id, the info that we are looking for (the hashes)
        # will be the same for every entry, so just access the first one
        try:
            metadata = vault_info[0].get("metadata")
        except Exception:
            return (phantom.APP_ERROR, "Failed to get vault item metadata")

        try:
            cef_artifact["fileHashSha256"] = metadata["sha256"]
        except Exception:
            pass

        try:
            cef_artifact["fileHashMd5"] = metadata["md5"]
        except Exception:
            pass

        try:
            cef_artifact["fileHashSha1"] = metadata["sha1"]
        except Exception:
            pass

        return (phantom.APP_SUCCESS, "Mapped hash values")

    def _get_dictionary(self, param, action_result):
        url = GET_DICTIONARY_URL
        valid_input_output_format_dict = {}

        ret_val, response = self._make_rest_call(url=url, action_result=action_result, method="get")
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        for format_dict in response.get("data"):
            if format_dict["input_format"] not in valid_input_output_format_dict.keys():
                valid_input_output_format_dict.update({format_dict["input_format"]: []})
            if format_dict["output_format"] not in valid_input_output_format_dict[format_dict["input_format"]]:
                valid_input_output_format_dict[format_dict["input_format"]].append(format_dict["output_format"])

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully created a list of valid formats"), valid_input_output_format_dict

    def _handle_get_valid_filetypes(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        input_filetype = param["filetype"]
        resulting_dict = dict()
        self.save_progress(f"Fetching valid output file formats for .{input_filetype} input file")

        ret_val, valid_format_dict = self._get_dictionary(param, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for input_format in valid_format_dict:
            if input_format == input_filetype:
                resulting_dict = {"input_format": input_format, "output_format": valid_format_dict[input_format]}
        action_result.add_data(resulting_dict)
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully fetched valid output formats")

    def _get_converted_file(self, param, action_result, link, filename):
        url = link
        output_filetype = param["filetype"]
        filename = filename.split(".")[0]
        self._stream_file_data = True

        ret_val, response = self._make_rest_call(url=url, action_result=action_result, method="get", empty_headers=True)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        guid = uuid.uuid4()

        if hasattr(Vault, "get_vault_tmp_dir"):
            vault_tmp_dir = Vault.get_vault_tmp_dir().rstrip("/")
            local_dir = f"{vault_tmp_dir}/{guid}"
        else:
            local_dir = os.path.join(paths.PHANTOM_VAULT, "tmp", guid)
        output_filename = f"{filename}.{output_filetype}"

        self.save_progress(f"Using temp directory: {guid}")
        self.debug_print(f"Using temp directory: {guid}")

        try:
            os.makedirs(local_dir)
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, "Unable to create temporary vault folder.", self._get_error_message_from_exception(e)
            ), None

        compressed_file_path = f"{local_dir}/{output_filename}"

        # Try to stream the response to a file
        if response.status_code == 200:
            try:
                compressed_file_path = UnicodeDammit(compressed_file_path).unicode_markup
                with open(compressed_file_path, "wb") as f:
                    if self._stream_file_data:
                        for chunk in response.iter_content(chunk_size=10 * 1024 * 1024):
                            f.write(chunk)
                    else:
                        f.write(response.content)
            except OSError as e:
                error_message = self._get_error_message_from_exception(e)
                if "File name too long" in error_message:
                    new_file_name = "ph_long_file_name_temp"
                    compressed_file_path = f"{local_dir}/{new_file_name}"
                    self.debug_print(f"Original filename : {filename}")
                    self.debug_print(f"Modified filename : {new_file_name}")
                    with open(compressed_file_path, "wb") as f:
                        if self._stream_file_data:
                            for chunk in response.iter_content(chunk_size=10 * 1024 * 1024):
                                f.write(chunk)
                        else:
                            f.write(response.content)
                else:
                    return action_result.set_status(
                        phantom.APP_ERROR, f"Unable to write file to disk. Error: {self._get_error_message_from_exception(e)}"
                    ), None

            except Exception as e:
                return action_result.set_status(
                    phantom.APP_ERROR, f"Unable to write file to disk. Error: {self._get_error_message_from_exception(e)}"
                ), None

        try:
            vault_results = ph_rules.vault_add(container=self.get_container_id(), file_location=compressed_file_path, file_name=output_filename)
            if vault_results[0]:
                try:
                    _, _, vault_result_information = ph_rules.vault_info(
                        vault_id=vault_results[2], container_id=self.get_container_id(), file_name=output_filename
                    )
                    if not vault_result_information:
                        vault_result_information = None
                        # If filename contains special characters, vault_info will return None when passing filename as argument,
                        # hence this call is executed
                        _, _, vault_info = ph_rules.vault_info(vault_id=vault_results[2], container_id=self.get_container_id())
                        if vault_info:
                            for vault_meta_info in vault_info:
                                if vault_meta_info["name"] == output_filename:
                                    vault_result_information = [vault_meta_info]
                                    break
                    vault_info = next(iter(vault_result_information))
                except IndexError:
                    return action_result.set_status(phantom.APP_ERROR, "Vault file could not be found with supplied Vault ID"), None
                except Exception as e:
                    return action_result.set_status(phantom.APP_ERROR, f"Vault ID not valid: {self._get_error_message_from_exception(e)}"), None
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, f"Unable to store file in Phantom Vault. Error: {self._get_error_message_from_exception(e)}"
            ), None
        return action_result.set_status(phantom.APP_SUCCESS, "File converted successfully"), vault_info

    def _get_link(self, param, action_result, job_id):
        url = f"{GET_LINK_URL}{job_id}"
        result_dict = None
        timeout = self._timeout
        counter = 0
        sleep_seconds = 30

        timeout_in_sec = 60 * timeout
        import_task, convert_task, export_task = None, None, None

        while counter < timeout_in_sec:
            ret_val, response = self._make_rest_call(url=url, action_result=action_result, method="get")
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None
            counter += sleep_seconds
            for task in response.get("data"):
                if task.get("job_id") == job_id:
                    if task.get("name") == "import":
                        import_task = task
                        continue
                    if task.get("name") == "task":
                        convert_task = task
                        continue
                    if task.get("name") == "export":
                        export_task = task
                        continue
                    if import_task and convert_task and export_task:
                        break
            if import_task.get("status") == "error":
                return action_result.set_status(
                    phantom.APP_ERROR,
                    "Error while uploading a file. {}".format(
                        CLOUDCONVERT_ERROR_MSG_FORMAT.format(
                            import_task.get("code", "No error code found"), import_task.get("message", "No error message found")
                        )
                    ),
                ), None
            elif convert_task.get("status") == "error":
                if convert_task.get("code") == "INVALID_CONVERSION_TYPE":
                    return action_result.set_status(
                        phantom.APP_ERROR,
                        "Error while converting a file. {}. Please run the 'get valid filetypes' action to get valid output file formats".format(
                            CLOUDCONVERT_ERROR_MSG_FORMAT.format(
                                convert_task.get("code", "No error code found"), convert_task.get("message", "No error message found")
                            )
                        ),
                    ), None
                return action_result.set_status(
                    phantom.APP_ERROR,
                    "Error while converting a file. {}".format(
                        CLOUDCONVERT_ERROR_MSG_FORMAT.format(
                            convert_task.get("code", "No error code found"), convert_task.get("message", "No error message found")
                        )
                    ),
                ), None
            elif export_task.get("status") == "error":
                return action_result.set_status(
                    phantom.APP_ERROR,
                    "Error while downloading the converted file. {}".format(
                        CLOUDCONVERT_ERROR_MSG_FORMAT.format(
                            export_task.get("code", "No error code found"), export_task.get("message", "No error message found")
                        )
                    ),
                ), None
            else:
                result_dict = export_task.get("result")
            if result_dict:
                break
            time.sleep(sleep_seconds)
            if counter >= timeout_in_sec:
                return action_result.set_status(
                    phantom.APP_ERROR,
                    """Timeout has finished. File is not converted yet.
                     Please configure higher value of 'Number of minutes to poll for converted file'
                     asset parameter to convert the file successfully""",
                ), None

        files_dict = result_dict.get("files")
        files_dict_list = files_dict[0]
        link = files_dict_list.get("url")

        return action_result.set_status(phantom.APP_SUCCESS, "Link fetched successfully"), link

    def _import_task(self, param, action_result, payload, filepath, filename):
        url = IMPORT_TASK_URL
        files = [("file", (filename, open(filepath, "rb")))]

        ret_val, _ = self._make_rest_call(url=url, action_result=action_result, data=payload, files=files, method="post")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "File imported successfully")

    def _initialize_job(self, param, action_result):
        output_filetype = param["filetype"]
        url = INITIALIZE_JOB_URL
        headers = {"Content-Type": "application/json"}

        payload = json.dumps(
            {
                "tasks": {
                    "import": {"operation": "import/upload"},
                    "task": {
                        "operation": "convert",
                        "input": ["import"],
                        "output_format": output_filetype,
                    },
                    "export": {
                        "operation": "export/url",
                        "input": ["task"],
                        "inline": False,
                        "archive_multiple_files": False,
                    },
                },
                "tag": "jobbuilder",
            }
        )

        ret_val, response = self._make_rest_call(url=url, action_result=action_result, headers=headers, data=payload, method="post")
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None, None

        get_task = response.get("data", {}).get("tasks", {})
        get_import_task = get_task[0]
        get_import_task_parameters = get_import_task.get("result", {}).get("form", {}).get("parameters", {})
        get_import_task_job_id = get_import_task.get("job_id")
        payload = get_import_task_parameters

        return action_result.set_status(phantom.APP_SUCCESS, "Job initialized successfully"), payload, get_import_task_job_id

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        if action_id == "get_valid_filetypes":
            ret_val = self._handle_get_valid_filetypes(param)

        if action_id == "convert_file":
            ret_val = self._handle_convert_file(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()
        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {}

        config = self.get_config()
        ret_val, self._timeout = self._validate_integers(self, config.get("timeout", 1), "timeout")
        if phantom.is_fail(ret_val):
            return self.get_status()
        self._api_key = config["api_key"]
        self._headers = {"Authorization": f"Bearer {self._api_key}"}
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
            login_url = CloudConvertConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=DEFAULT_TIMEOUT_SECONDS)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=DEFAULT_TIMEOUT_SECONDS)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = CloudConvertConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
