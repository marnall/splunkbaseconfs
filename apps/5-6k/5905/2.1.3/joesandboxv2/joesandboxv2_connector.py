# File: joesandboxv2_connector.py
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
import json
import math
import os
import shutil
import sys
import time
import uuid

import phantom.app as phantom
import phantom.rules as ph_rules
import requests
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault


try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

from bs4 import BeautifulSoup

from joesandboxv2_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class JoeSandboxV2Connector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None
        self._verify_ssl = None

        # Initialize configuration parameters to None or default values
        self._base_url = None
        self._api_key = None

        self._detonate_timeout = JOE_TIME_DEFAULT
        self._analysis_time = JOE_TIME_DEFAULT

    def _parse_response(self, response):
        """This method is used to strip semicolons from response

        :param response: response to parse
        :return: parsed response
        """

        for key, value in list(response.items()):
            try:
                if isinstance(value, (unicode, str)):
                    response[key] = value.strip(";")
            except NameError:
                if isinstance(value, str):
                    response[key] = value.strip(";")

        return response

    def _dump_error_log(self, error, message="Exception occurred."):
        self.error_print(message, dump_object=error)

    @staticmethod
    def _process_empty_response(response, action_result):
        """This function is used to process empty response

        :param response: Response data
        :param action_result: Object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, f"Status code: {response.status_code}. Empty response and no information in the header"),
            None,
        )

    def _process_html_response(self, response, action_result):
        """This function is used to process html response

        :param response: Response data
        :param action_result: Object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove the script, style, footer and navigation part from the HTML message
            for element in soup(["script", "style", "footer", "nav"]):
                element.extract()
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except Exception:
            error_text = "Cannot parse error details"

        if not error_text:
            error_text = "Error message unavailable. Please check the asset configuration and|or the action parameters."
        message = JOE_ERR_INVALID_URL_MSG.format(status_code=status_code, error_msg=JOE_ERR_JSON_PARSE_MSG.format(raw_text=error_text))

        message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    @staticmethod
    def _get_err_msg(response, action_result):
        """This function is used to get appropriate error message from error response
        :param response: Response data
        :param action_result: Object of Action Result
        :return: error_message
        """

        error_message = ""
        if response.status_code not in (200, 399):
            try:
                err_resp_json = response.json()
            except Exception as e:
                return RetVal(
                    action_result.set_status(
                        phantom.APP_ERROR, JOE_ERR_JSON_PARSE_MSG.format(raw_text=response.text.replace("{", "{{").replace("}", "}}")), e
                    ),
                    None,
                )

            err_list = err_resp_json.get(JOE_JSON_ERRS, [])

            for error in err_list:
                error_message = "{}{}{}".format(error_message, JOE_JSON_OR, error.get(JOE_JSON_MSG, ""))

            error_message = error_message.lstrip(JOE_JSON_OR)

        return error_message

    def _process_json_response(self, response, action_result):
        """This function is used to process json response

        :param response: Response data
        :param action_result: Object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        response_data = None

        if response.status_code not in (200, 399):
            error_message = self._get_err_msg(response, action_result)
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, JOE_ERR_FROM_SERVER_MSG.format(status=response.status_code, reason=error_message)),
                response_data,
            )

        try:
            response_data = response.json()
        except Exception as e:
            self._dump_error_log(e)
            error_msg = JOE_ERR_JSON_PARSE_MSG.format(raw_text=response.text.replace("{", "{{").replace("}", "}}"))
            error_msg = f"{error_msg}. {self._get_err_msg_from_exception(e)}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_msg), response_data)

        if response.status_code == JOE_JSON_RESP_SUCCESS_RESPONSE:
            if response_data.get(JOE_JSON_ANALYSIS):
                # This is special handling for the API endpoint '/v2/analysis/download'
                return RetVal(
                    action_result.set_status(phantom.APP_SUCCESS),
                    {JOE_JSON_RESPONSE: response_data, JOE_JSON_RESPONSE_HEADERS: response.headers},
                )
            else:
                return RetVal(
                    action_result.set_status(phantom.APP_SUCCESS),
                    {JOE_JSON_RESPONSE: response_data.get(JOE_JSON_DATA, {}), JOE_JSON_RESPONSE_HEADERS: response.headers},
                )
        elif response.status_code in (201, 399):
            return RetVal(
                action_result.set_status(phantom.APP_SUCCESS), {JOE_JSON_RESPONSE: response_data, JOE_JSON_RESPONSE_HEADERS: response.headers}
            )

        # You should process the error returned in the json
        message = "Error from server. Status Code: {}, Detail: {} and Reason: {}".format(
            response.status_code, JOE_ERR_UNKNOWN_ERR_MSG, response.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        """This function is used to process api response

        :param r: Response data
        :param action_result: Object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # Special handling for 'get report' and 'get pcap' action
        if r.status_code in (200, 399) and self.get_action_identifier() in [JOE_ACTION_GET_REPORT, JOE_ACTION_GET_PCAP]:
            return RetVal(action_result.set_status(phantom.APP_SUCCESS), {JOE_JSON_RESPONSE: r.content, JOE_JSON_RESPONSE_HEADERS: r.headers})
        elif r.status_code not in (200, 399) and self.get_action_identifier() in [JOE_ACTION_GET_REPORT, JOE_ACTION_GET_PCAP]:
            error_message = self._get_err_msg(r, action_result)
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, JOE_ERR_FROM_SERVER_MSG.format(status=r.status_code, reason=error_message)), None
            )

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

    def _get_err_msg_from_exception(self, e):
        """This method is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = None
        error_msg = JOE_ERR_MSG_UNAVAILABLE

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except Exception as e:
            self.debug_print(f"Error occurred while fetching exception information. Details: {e!s}")

        if not error_code:
            error_text = f"Error Message: {error_msg}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_msg}"

        return error_text

    def _make_rest_call(self, endpoint, action_result, data=None, files=None, method="post"):
        """This function is used to make the REST call

        :param endpoint: REST URL endpoint that needs to be called
        :param action_result: Object of ActionResult class
        :param data: Request body
        :param files: files
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be POST)
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        response_data = None

        if not data:
            data = {}

        data[JOE_JSON_API_KEY] = self._api_key

        # All API calls supports POST request
        try:
            request_func = getattr(requests, method)
        except AttributeError as e:
            self._dump_error_log(e)
            return action_result.set_status(phantom.APP_ERROR, JOE_ERR_API_UNSUPPORTED_METHOD_MSG), response_data
        except Exception as e:
            self._dump_error_log(e)
            return action_result.set_status(phantom.APP_ERROR, e), response_data

        try:
            response = request_func(f"{self._base_url}{endpoint}", data=data, files=files, verify=self._verify_ssl)
        except Exception as error:
            self._dump_error_log(error)
            return action_result.set_status(
                phantom.APP_ERROR, JOE_ERR_SERVER_CONNECTION_MSG, self._get_err_msg_from_exception(error)
            ), response_data

        return self._process_response(response, action_result)

    def _handle_test_connectivity(self, param):
        """This function is used to handle the test connectivity action

        :param param: Dictionary of input parameters
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress(JOE_TEST_CONNECTIVITY_INIT_MSG)

        if self._detonate_timeout < JOE_TIME_MIN or self._detonate_timeout > JOE_TIME_MAX:
            self.save_progress(JOE_ERR_INVALID_DETONATION_TIME_MSG)
            return action_result.set_status(phantom.APP_ERROR, JOE_ERR_TEST_CONNECTIVITY_FAILED_MSG)

        if self._analysis_time < JOE_TIME_MIN or self._analysis_time > JOE_TIME_MAX:
            self.save_progress(JOE_ERR_INVALID_ANALYSIS_TIME_MSG)
            return action_result.set_status(phantom.APP_ERROR, JOE_ERR_TEST_CONNECTIVITY_FAILED_MSG)

        self.save_progress(JOE_TEST_CONNECTIVITY_PROGRESS_MSG.format(base_url=self._base_url))

        response_status, response = self._make_rest_call(JOE_TEST_CONNECTIVITY_ENDPOINT, action_result)

        if phantom.is_fail(response_status):
            self.save_progress(action_result.get_message())
            self.save_progress(JOE_ERR_TEST_CONNECTIVITY_FAILED_MSG)
            return action_result.set_status(phantom.APP_ERROR)

        self.save_progress(JOE_TEST_CONNECTIVITY_PASSED_MSG)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_detonate_file(self, param):
        """This function is used to submit a file for analysis on Joe Sandbox

        :param param: Dictionary of input parameters containing file's vault id and cookbook's vault id (optional)
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        if self._detonate_timeout < JOE_TIME_MIN or self._detonate_timeout > JOE_TIME_MAX:
            return action_result.set_status(phantom.APP_ERROR, JOE_ERR_CONFIG_TIMEOUT_MSG)

        if self._analysis_time < JOE_TIME_MIN or self._analysis_time > JOE_TIME_MAX:
            return action_result.set_status(phantom.APP_ERROR, JOE_ERR_ANALYSIS_TIME_MSG)

        file_params = {}
        data_params = {}
        file_name = None
        cookbook_name = None

        file_vault_id = param[JOE_JSON_FILE_VAULT_ID]
        cookbook_vault_id = param.get(JOE_JSON_COOKBOOK_VAULT_ID)

        # For custom analysis, type should be 'cookbook', else type should be 'file'
        if cookbook_vault_id:
            detonate_file_type = JOE_JSON_COOKBOOK
        else:
            detonate_file_type = JOE_JSON_FILE

        if param.get(JOE_JSON_INET_ACCESS):
            data_params[JOE_JSON_INTERNET_ACCESS] = 1

        if param.get(JOE_JSON_REPORT_CACHE):
            data_params[JOE_JSON_ENABLE_CACHE] = 1

        data_params.update({JOE_JSON_ANALYSIS_TIME: self._analysis_time})

        try:
            success, msg, files_array = ph_rules.vault_info(container_id=self.get_container_id())
            if not success:
                return (action_result.set_status(phantom.APP_ERROR, f"Unable to get Vault item details. Error details: {msg}"), None)

            files_array = list(files_array)
        except Exception as e:
            self._dump_error_log(e)
            return (
                action_result.set_status(
                    phantom.APP_ERROR, f"Unable to get Vault item details. Error details: {self._get_err_msg_from_exception(e)}"
                ),
                None,
            )

        for file_data in files_array:
            if file_data[JOE_JSON_FILE_VAULT_ID] == file_vault_id:
                # Getting filename to use if optional file name is not given
                file_obj = open(file_data["path"], "rb").read()
                # Obtain file name
                file_name = file_data[JOE_JSON_NAME]
                file_params[JOE_JSON_SAMPLE] = (quote(file_name), file_obj)

            elif file_data[JOE_JSON_FILE_VAULT_ID] == cookbook_vault_id and detonate_file_type == JOE_JSON_COOKBOOK:
                # Getting filename to use if optional file name is not given
                cookbook_obj = open(file_data["path"], "rb").read()
                # Obtain cookbook name
                cookbook_name = file_data[JOE_JSON_NAME]
                file_params[JOE_JSON_COOKBOOK] = (quote(cookbook_name), cookbook_obj)

            # If type = 'file', 'sample' key must be there in file_params dict
            # If type = 'cookbook', 'sample' and 'cookbook' keys must be there in file_params dict
            if (detonate_file_type == JOE_JSON_COOKBOOK and {JOE_JSON_SAMPLE, JOE_JSON_COOKBOOK}.issubset(file_params)) or (
                detonate_file_type == JOE_JSON_FILE and JOE_JSON_SAMPLE in file_params
            ):
                break

        if not file_params:
            return action_result.set_status(phantom.APP_ERROR, JOE_ERR_FILE_OR_COOKBOOK_NOT_FOUND_MSG)

        response_status, response_data = self._submit_sample(file_params, data_params, action_result)

        if phantom.is_fail(response_status):
            return action_result.get_status()

        # Overriding value of filename key from response_data with encoded file name
        response_data[JOE_JSON_FILENAME] = file_name

        # Removing unnecessary data from response
        if JOE_JSON_COMMENTS in response_data:
            del response_data[JOE_JSON_COMMENTS]

        # Add to summary
        summary_data.update({JOE_JSON_ANALYSIS_STATUS: response_data.get(JOE_JSON_STATUS), JOE_JSON_WEBID: response_data.get(JOE_JSON_WEBID)})

        if response_data.get(JOE_JSON_STATUS) == JOE_JSON_FINISHED:
            json_response_status, json_response_data = self._get_json_report(response_data.get(JOE_JSON_WEBID), action_result)

            if phantom.is_fail(json_response_status):
                return action_result.set_status(phantom.APP_SUCCESS)

            # Overriding value of keys containing file name and cookbook name with encoded file name and encoded
            # cookbook name respectively, try to be as safe as possible
            try:
                json_response_data[JOE_JSON_SYSTEM_BEHAVIOR][0][JOE_JSON_GENERAL][JOE_JSON_NAME] = file_name
            except Exception:
                pass

            try:
                json_response_data[JOE_JSON_GENERAL_INFO][JOE_JSON_TARGET][JOE_JSON_SAMPLE] = file_name
            except Exception:
                pass

            if json_response_data.get(JOE_JSON_FILE_INFO) and json_response_data[JOE_JSON_FILE_INFO].get(JOE_JSON_FILENAME):
                json_response_data[JOE_JSON_FILE_INFO][JOE_JSON_FILENAME] = file_name

            if detonate_file_type == JOE_JSON_COOKBOOK:
                try:
                    json_response_data[JOE_JSON_GENERAL_INFO][JOE_JSON_TARGET][JOE_JSON_COOKBOOK] = cookbook_name
                except Exception:
                    pass

            action_result.add_data({JOE_JSON_SAMPLE_STATUS: response_data, JOE_JSON_SAMPLE_DETAILS: json_response_data})
        else:
            action_result.add_data({JOE_JSON_SAMPLE_STATUS: response_data})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_pcap(self, param):
        """This method is used to get network pcap of submitted sample

        :param param: Dictionary of input parameters containing webid of sample
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # getting mandatory parameter
        webid = param[JOE_JSON_ID]

        data = {JOE_JSON_WEBID: webid, JOE_JSON_TYPE: "pcap"}

        # getting report data and saving it in vault
        response_status, response_data = self._get_report_data(data, action_result)

        if phantom.is_fail(response_status):
            return action_result.get_status()

        summary_data[JOE_JSON_DOWNLOAD_REPORT_DETAILS] = True
        action_result.add_data(response_data)

        return action_result.set_status(phantom.APP_SUCCESS, JOE_PCAP_REPORT_DOWNLOAD_MSG)

    def _handle_get_report(self, param):
        """This method is used to get report with specified format for a given webid

        :param param: Dictionary of input parameters containing webid of sample and type of report
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        webid = param[JOE_JSON_ID]
        report_type = param[JOE_JSON_TYPE]

        api_params = {JOE_JSON_WEBID: webid, JOE_JSON_TYPE: report_type}

        # getting report data and saving it in vault
        response_status, response_data = self._get_report_data(api_params, action_result)

        if phantom.is_fail(response_status):
            return action_result.get_status()

        summary_data[JOE_JSON_DOWNLOAD_REPORT_DETAILS] = True

        json_response_status, json_response_data = self._get_json_report(webid, action_result)

        if phantom.is_fail(json_response_status):
            return action_result.set_status(phantom.APP_SUCCESS)

        action_result.add_data({JOE_JSON_DOWNLOAD_REPORT_DETAILS: response_data, JOE_JSON_SAMPLE_DETAILS: json_response_data})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_report_data(self, api_data, action_result):
        """This is helper method to get report data and save report to vault, if sample with given webid is present on
        Joe Sandbox

        :param api_data: dictionary containing webid of sample and type of report to download
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        data = {JOE_JSON_WEBID: api_data[JOE_JSON_WEBID]}

        # Checking availability of webid
        response_status, response_data = self._make_rest_call(JOE_CHECK_STATUS_ENDPOINT, action_result, data=data)

        # In case of failure, action_result to be returned as is
        if phantom.is_fail(response_status):
            return action_result.get_status(), None

        # For 'get report' and 'get pcap' action response.content will be returned
        try:
            response_json = json.loads(response_data[JOE_JSON_RESPONSE]).get("data", {})
        except Exception as e:
            self._dump_error_log(e)
            return action_result.set_status(phantom.APP_ERROR, JOE_ERR_JSON_MSG.format(error=self._get_err_msg_from_exception(e))), None

        # Report of the sample will be downloaded only if analysis of sample is finished
        if response_json.get(JOE_JSON_STATUS) != JOE_JSON_FINISHED:
            self.debug_print(JOE_ERR_REPORT_UNAVAILABLE_MSG.format(webid=api_data[JOE_JSON_WEBID]))
            return action_result.set_status(phantom.APP_ERROR, JOE_ERR_REPORT_UNAVAILABLE_MSG.format(webid=api_data[JOE_JSON_WEBID])), None

        # Getting report data
        response_status, response = self._make_rest_call(JOE_REPORT_ENDPOINT, action_result, data=api_data)

        # In case of failure, action_result to be returned as is
        if phantom.is_fail(response_status):
            self.debug_print(JOE_ERR_REPORT_DOWNLOAD_MSG.format(webid=api_data[JOE_JSON_WEBID]))
            return action_result.get_status(), None

        # Saving report data in vault
        response_status, resp = self._save_report(response, self.get_container_id(), action_result)

        # In case of failure, action_result to be returned as is
        if phantom.is_fail(response_status):
            self.debug_print(JOE_ERR_SAVE_REPORT_MSG.format(webid=api_data[JOE_JSON_WEBID]))
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, resp

    def _save_report(self, response, container_id, action_result):
        """This is helper method used to create report file with given format

        :param response: response containing report data
        :param container_id: current container ID
        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # Getting file name or report from headers
        if JOE_JSON_CONTENT_DISPOSITION not in response[JOE_JSON_RESPONSE_HEADERS]:
            self.debug_print(JOE_ERR_REPORT_FILENAME_NOT_FOUND_MSG)
            return action_result.set_status(phantom.APP_ERROR, JOE_ERR_REPORT_FILENAME_NOT_FOUND_MSG), None

        filename = response[JOE_JSON_RESPONSE_HEADERS][JOE_JSON_CONTENT_DISPOSITION].split("filename=")[1][1:-2]

        return_val, vault_details = self._save_file_to_vault(filename, container_id, response[JOE_JSON_RESPONSE], action_result)

        # Something went wrong while moving file to vault
        if phantom.is_fail(return_val):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, vault_details

    def _save_file_to_vault(self, filename, container_id, content, action_result):
        """This is helper method used to save the file to vault using given filename and content

        :param filename: response containing report data
        :param container_id: current container ID
        :param content: content to be written in file
        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        if isinstance(content, bytes):
            open_mode = "wb"
        else:
            open_mode = "w"

        # Creating temporary directory and file
        try:
            temp_dir = os.path.join(Vault.get_vault_tmp_dir(), str(uuid.uuid4()))
            os.makedirs(temp_dir)
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, open_mode) as file_obj:
                file_obj.write(content)
        except OSError as e:
            error_msg = self._get_err_msg_from_exception(e)
            try:
                # Handling "Filename too long"/"File name too long"
                if "too long" in error_msg:
                    random_suffix = uuid.uuid4()
                    new_file_name = f"long_filename_{random_suffix}"
                    file_path = os.path.join(temp_dir, new_file_name)
                    self.debug_print(f"Original filename: {filename}")
                    self.debug_print(f"Modified filename: {new_file_name}")
                    with open(file_path, open_mode) as _temp_file:
                        _temp_file.write(content)
                else:
                    return action_result.set_status(
                        phantom.APP_ERROR, f"Error occurred while adding file to Vault. Error details: {self._get_err_msg_from_exception(e)}"
                    ), None
            except Exception as e:
                self._dump_error_log(e)
                return action_result.set_status(
                    phantom.APP_ERROR, f"Error occurred while adding file to Vault. Error details: {self._get_err_msg_from_exception(e)}"
                ), None
        except Exception as e:
            self._dump_error_log(e, JOE_ERR_FILE_MSG)
            return action_result.set_status(phantom.APP_ERROR, JOE_ERR_FILE_MSG, self._get_err_msg_from_exception(e)), None

        try:
            # Check if report with same file name is already available in vault
            _, _, vault_list = ph_rules.vault_info(container_id=container_id)
            if vault_list is None:
                vault_list = list()
            vault_list = list(vault_list)
        except Exception as e:
            self._dump_error_log(e)
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
            return (action_result.set_status(phantom.APP_ERROR, f"Unable to get vault item details from Splunk SOAR. Details: {e!s}"), None)

        # Iterate through each vault item in the container and compare name and size of file
        for vault in vault_list:
            if vault.get(JOE_JSON_NAME) == filename and vault.get(JOE_JSON_SIZE) == os.path.getsize(file_path):
                self.send_progress(JOE_REPORT_ALREADY_AVAILABLE_MSG)
                vault_details = {phantom.APP_JSON_VAULT_ID: vault.get(JOE_JSON_FILE_VAULT_ID), JOE_JSON_REPORT_FILE_NAME: filename}

                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass

                return phantom.APP_SUCCESS, vault_details

        # Calling move_file_to_vault to move downloaded file to current container's vault
        return_val, vault_details = self._move_file_to_vault(container_id, file_path, filename, action_result)

        if phantom.is_fail(return_val):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
            return action_result.set_status(phantom.APP_ERROR, JOE_ERR_ADDING_TO_VAULT_FAILED_MSG), None

        # Removing temporary directory created to download file
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            self._dump_error_log(e, JOE_ERR_REMOVE_DIRECTORY_MSG)
            return action_result.set_status(phantom.APP_ERROR, JOE_ERR_REMOVE_DIRECTORY_MSG, e), None

        return action_result.set_status(phantom.APP_SUCCESS), vault_details

    def _move_file_to_vault(self, container_id, local_file_path, filename, action_result):
        """This is helper method used to move downloaded file to vault

        :param container_id: ID of the container in which we need to add vault file
        :param local_file_path: path where file is stored
        :param filename: name of the file created
        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        self.send_progress(phantom.APP_PROG_ADDING_TO_VAULT)

        # Adding report to vault
        success, msg, vault_id = ph_rules.vault_add(file_location=local_file_path, container=container_id, file_name=filename)

        # Updating report data with vault details
        if success:
            vault_details = {phantom.APP_JSON_VAULT_ID: vault_id, JOE_JSON_REPORT_FILE_NAME: filename}
            return phantom.APP_SUCCESS, vault_details

        # Error while adding report to vault
        self.debug_print(f"Error adding file to vault: success={success}, message={msg}, vault_id={vault_id}")
        action_result.append_to_message(f". {msg}")

        # Set the action_result status to error, the handler function will most probably return as is
        return phantom.APP_ERROR, None

    def _handle_check_status(self, param):
        """This method is used to check status of sample submitted for analysis to Joe Sandbox

        :param param: webid of sample submitted
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # getting mandatory parameters
        webid = param[JOE_JSON_ID]

        # getting status of webid
        response_status, response_data = self._make_rest_call(JOE_CHECK_STATUS_ENDPOINT, action_result, data={JOE_JSON_WEBID: webid})

        if phantom.is_fail(response_status):
            return action_result.get_status()

        # Adding a new key in the data which contains the reputation of the file or URL, defined based on 'runs --> detection'
        # parameter available in data
        self.debug_print("Processing the response")
        reputation_detection_list = response_data.get(JOE_JSON_RESPONSE, {}).get(JOE_JSON_RUNS, [])

        if reputation_detection_list and len(reputation_detection_list) > 0:
            for reputation_item in reputation_detection_list:
                response_data[JOE_JSON_RESPONSE][JOE_JSON_REPUTATION_LABEL] = reputation_item.get(JOE_JSON_DETECTION, JOE_JSON_CLEAN)
        else:
            response_data[JOE_JSON_RESPONSE][JOE_JSON_REPUTATION_LABEL] = JOE_JSON_CLEAN

        summary_data.update({JOE_JSON_STATUS: response_data.get(JOE_JSON_RESPONSE, {}).get(JOE_JSON_STATUS)})

        response_data = self._parse_response(response_data.get(JOE_JSON_RESPONSE))

        # Removing unnecessary data from response
        if phantom.is_url(response_data.get(JOE_JSON_FILENAME, "")):
            response_data[JOE_JSON_URL] = response_data.pop(JOE_JSON_FILENAME)
            if JOE_JSON_MD_5 in response_data:
                del response_data[JOE_JSON_MD_5]
            if JOE_JSON_SHA_1 in response_data:
                del response_data[JOE_JSON_SHA_1]
            if JOE_JSON_SHA_256 in response_data:
                del response_data[JOE_JSON_SHA_256]

        if JOE_JSON_COMMENTS in response_data.get(JOE_JSON_SAMPLE_STATUS, ""):
            del response_data[JOE_JSON_COMMENTS]

        action_result.add_data(response_data)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_detonate_url(self, param):
        """This function is used to submit a URL for analysis on Joe Sandbox

        :param param: Dictionary of input parameters containing URL
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        if self._detonate_timeout < JOE_TIME_MIN or self._detonate_timeout > JOE_TIME_MAX:
            return action_result.set_status(phantom.APP_ERROR, JOE_ERR_INVALID_DETONATION_TIME_MSG)

        if self._analysis_time < JOE_TIME_MIN or self._analysis_time > JOE_TIME_MAX:
            return action_result.set_status(phantom.APP_ERROR, JOE_ERR_INVALID_ANALYSIS_TIME_MSG)

        file_params = {}
        data_params = {}

        sample = param[JOE_CONFIG_SERVER]

        if param.get(JOE_JSON_INET_ACCESS):
            data_params[JOE_JSON_INTERNET_ACCESS] = 1

        if param.get(JOE_JSON_REPORT_CACHE):
            data_params[JOE_JSON_ENABLE_CACHE] = 1

        data_params.update({JOE_CONFIG_SERVER: sample, JOE_JSON_ANALYSIS_TIME: self._analysis_time})

        self.debug_print(f"Detonation parameters: {data_params}")
        response_status, response_data = self._submit_sample(file_params, data_params, action_result)

        if phantom.is_fail(response_status):
            return action_result.get_status()

        summary_data.update({JOE_JSON_ANALYSIS_STATUS: response_data.get(JOE_JSON_STATUS), JOE_JSON_WEBID: response_data.get(JOE_JSON_WEBID)})

        if response_data.get(JOE_JSON_STATUS) == JOE_JSON_FINISHED:
            json_response_status, json_response_data = self._get_json_report(response_data.get(JOE_JSON_WEBID), action_result)

            if phantom.is_fail(json_response_status):
                return action_result.set_status(phantom.APP_SUCCESS)

            response = {JOE_JSON_SAMPLE_STATUS: response_data, JOE_JSON_SAMPLE_DETAILS: json_response_data}
        else:
            response = {JOE_JSON_SAMPLE_STATUS: response_data}

        # Removing unnecessary data from response
        if JOE_JSON_MD_5 in response[JOE_JSON_SAMPLE_STATUS]:
            del response[JOE_JSON_SAMPLE_STATUS][JOE_JSON_MD_5]
        if JOE_JSON_SHA_1 in response[JOE_JSON_SAMPLE_STATUS]:
            del response[JOE_JSON_SAMPLE_STATUS][JOE_JSON_SHA_1]
        if JOE_JSON_SHA_256 in response[JOE_JSON_SAMPLE_STATUS]:
            del response[JOE_JSON_SAMPLE_STATUS][JOE_JSON_SHA_256]
        if JOE_JSON_COMMENTS in response[JOE_JSON_SAMPLE_STATUS]:
            del response[JOE_JSON_SAMPLE_STATUS][JOE_JSON_COMMENTS]

        # Remove filename key from response
        response[JOE_JSON_SAMPLE_STATUS].pop(JOE_JSON_FILENAME)
        # Add url key in response and assign value of param url
        response[JOE_JSON_SAMPLE_STATUS][JOE_CONFIG_SERVER] = sample

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _submit_sample(self, file_params, api_params, action_result):
        """This is helper method used to submit file or URL to Joe Sandbox for analysis

        :param file_params: Dictionary containing file name and cookbook script (optional) to submit
        :param api_params: parameters that will be passed to detonate sample
        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # 'accept-tac' key is used for accepting the terms and conditions
        api_params.update({JOE_JSON_ACCEPT_TAC: 1})

        response_status, response_data = self._make_rest_call(JOE_DETONATE_SAMPLE_ENDPOINT, action_result, data=api_params, files=file_params)

        if phantom.is_fail(response_status):
            return action_result.get_status(), None

        if not response_data or not response_data.get(JOE_JSON_RESPONSE) or not response_data.get(JOE_JSON_RESPONSE).get(JOE_JSON_WEBIDS):
            return action_result.set_status(phantom.APP_ERROR, "The item could not be submitted for detonating successfully"), None

        # Extract the webid from the response object
        webids = response_data.get(JOE_JSON_RESPONSE).get(JOE_JSON_WEBIDS)
        webid = webids[0]

        # Calculating number of times polling should be done based on timeout seconds provided by user.
        # Polling will be done at an interval of 30 sec
        num_polls = math.ceil(self._detonate_timeout / JOE_SLEEP_SECS)

        polling_attempt = 0

        # Polling Joe Sandbox to check status of sample submitted
        # Polling interval will be calculated based on user defined values, provided during asset configuration
        while polling_attempt < num_polls:
            polling_attempt += 1
            # sleeping interval will be 30 sec for all polls except the last polling
            sleeping_interval = JOE_SLEEP_SECS

            # If given timeout is not multiple of 30, we need to find last sleeping interval by getting modulo
            # of given timeout and 30 sec
            if self._detonate_timeout % JOE_SLEEP_SECS != 0 and polling_attempt == num_polls:
                sleeping_interval = self._detonate_timeout % JOE_SLEEP_SECS

            time.sleep(sleeping_interval)
            self.save_progress(JOE_CHECK_STATUS_POLLING_MSG.format(polling_attempt=polling_attempt, total_count=int(num_polls)))

            response_status, response_data = self._make_rest_call(JOE_CHECK_STATUS_ENDPOINT, action_result, data={JOE_JSON_WEBID: webid})

            if phantom.is_fail(response_status):
                self.debug_print(JOE_ERR_CHECK_STATUS_MSG)
                return action_result.get_status(), None

            # Status will be JOE_JSON_FINISHED once analysis of file will be complete
            if response_data[JOE_JSON_RESPONSE][JOE_JSON_STATUS] == JOE_JSON_FINISHED:
                break

        return phantom.APP_SUCCESS, response_data.get(JOE_JSON_RESPONSE, {})

    def _get_json_report(self, webid, action_result):
        """This is helper method to get json report of sample

        :param webid: ID of sample
        :param action_result: Object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        json_data = {JOE_JSON_WEBID: webid, JOE_JSON_TYPE: JOE_JSON}
        response_status, response_data = self._make_rest_call(JOE_REPORT_ENDPOINT, action_result, data=json_data)

        if phantom.is_fail(response_status):
            return action_result.get_status(), None

        if JOE_JSON_RESPONSE in response_data:
            if isinstance(response_data[JOE_JSON_RESPONSE], (str, bytes)):
                try:
                    response_data[JOE_JSON_RESPONSE] = json.loads(response_data[JOE_JSON_RESPONSE])
                except Exception as e:
                    self._dump_error_log(e)
                    return action_result.set_status(phantom.APP_ERROR, JOE_ERR_JSON_MSG.format(error=self._get_err_msg_from_exception(e))), None

        # Required fields to be extracted from the response obtained
        overview_info_keys = {
            JOE_JSON_GENERAL_INFO: None,
            JOE_JSON_FILE_INFO: None,
            JOE_JSON_DOMAIN_INFO: JOE_JSON_DOMAIN,
            JOE_JSON_IP_INFO: JOE_JSON_IP,
            JOE_JSON_SIGNATURED_DETECTIONS: JOE_JSON_STRATEGY,
            JOE_JSON_DROPPED_INFO: JOE_JSON_HASH,
        }
        system_behavior_info_keys = {
            JOE_JSON_FILE_ACTIVITIES: [JOE_JSON_FILE_DELETED, JOE_JSON_FILE_MOVED],
            JOE_JSON_REGISTRY_ACTIVITIES: [JOE_JSON_KEY_CREATED, JOE_JSON_KEY_DELETED, JOE_JSON_KEY_VALUE_MODIFIED],
        }

        json_response_filter_data = dict()

        if response_data.get(JOE_JSON_RESPONSE):
            json_response_data = response_data[JOE_JSON_RESPONSE]

            for key, subkey in list(overview_info_keys.items()):
                # To check if each parent key's subkey that will be considered to display the widget, is a list. If
                # not, then it will be converted into list
                if json_response_data[JOE_JSON_ANALYSIS].get(key) and subkey:
                    if isinstance(json_response_data[JOE_JSON_ANALYSIS][key].get(subkey), dict):
                        json_response_data[JOE_JSON_ANALYSIS][key][subkey] = [json_response_data[JOE_JSON_ANALYSIS][key][subkey]]

                # Removing html format tags from the string of systemdescription key
                if key == JOE_JSON_GENERAL_INFO and json_response_data[JOE_JSON_ANALYSIS][key].get(JOE_JSON_SYSTEM_DESCRIPTION):
                    json_response_data[JOE_JSON_ANALYSIS][key][JOE_JSON_SYSTEM_DESCRIPTION] = (
                        json_response_data[JOE_JSON_ANALYSIS][key][JOE_JSON_SYSTEM_DESCRIPTION].replace("<b>", "").replace("</b>", "")
                    )

                json_response_filter_data[key] = json_response_data[JOE_JSON_ANALYSIS].get(key)

            json_response_filter_data[JOE_JSON_SYSTEM_BEHAVIOR] = []

            # If path to get system behavior data is available, then converting it into list if it is an object
            behavior_data = (
                json_response_data.get(JOE_JSON_ANALYSIS, {})
                .get(JOE_JSON_BEHAVIOR, {})
                .get(JOE_JSON_SYSTEM, {})
                .get(JOE_JSON_PROCESSES, {})
                .get(JOE_JSON_PROCESS, [])
            )
            if behavior_data:
                if isinstance(behavior_data, dict):
                    json_response_data[JOE_JSON_ANALYSIS][JOE_JSON_BEHAVIOR][JOE_JSON_SYSTEM][JOE_JSON_PROCESSES][JOE_JSON_PROCESS] = [
                        behavior_data
                    ]

                # Iterating over system behavior keys to get data related to file activities and registry activities
                for system_behavior_data in behavior_data:
                    # Getting general information of module
                    system_behavior_module_data = {JOE_JSON_GENERAL: system_behavior_data.get(JOE_JSON_GENERAL)}
                    for key, sub_key_list in list(system_behavior_info_keys.items()):
                        for sub_key in sub_key_list:
                            if system_behavior_data.get(key, {}).get(sub_key, {}).get(JOE_JSON_CALL):
                                # To check if each parent key's subkey that will be considered to display the widget
                                # , is a list. If not, then it will be converted into list
                                if isinstance(system_behavior_data[key][sub_key][JOE_JSON_CALL], dict):
                                    system_behavior_data[key][sub_key][JOE_JSON_CALL] = [system_behavior_data[key][sub_key][JOE_JSON_CALL]]
                                if key not in list(system_behavior_module_data.keys()):
                                    system_behavior_module_data[key] = dict()

                                system_behavior_module_data[key][sub_key] = system_behavior_data[key][sub_key][JOE_JSON_CALL]

                    json_response_filter_data[JOE_JSON_SYSTEM_BEHAVIOR].append(system_behavior_module_data)

        return phantom.APP_SUCCESS, json_response_filter_data

    def _handle_url_reputation(self, param):
        """This method is used to query Joe Sandbox to get URL details

        :param param: URL to search
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # getting mandatory parameter
        url = param[JOE_JSON_URL]

        api_params = {JOE_JSON_Q: url}

        response_status, response_data = self._make_rest_call(JOE_REPUTATION_SEARCH_ENDPOINT, action_result, data=api_params)

        if phantom.is_fail(response_status):
            return action_result.get_status()

        response_data = response_data.get(JOE_JSON_RESPONSE, {})

        if response_data and len(response_data) > 0:
            recent_web_id = response_data[0].get(JOE_JSON_WEBID)
        else:
            return action_result.set_status(phantom.APP_ERROR, JOE_URL_SEARCH_ANALYSIS_NOT_FOUND_MSG)

        # getting status of fetched recent webid
        response_status, response_data = self._make_rest_call(JOE_CHECK_STATUS_ENDPOINT, action_result, data={JOE_JSON_WEBID: recent_web_id})

        if phantom.is_fail(response_status):
            return action_result.get_status()

        # Adding a new key in the data which contains the reputation of the file or URL, defined based on 'runs --> detection'
        # parameter available in data
        self.debug_print("Processing the response")
        reputation_detection_list = response_data.get(JOE_JSON_RESPONSE, {}).get(JOE_JSON_RUNS, [])

        if reputation_detection_list and len(reputation_detection_list) > 0:
            for reputation_item in reputation_detection_list:
                response_data[JOE_JSON_RESPONSE][JOE_JSON_REPUTATION_LABEL] = reputation_item.get(JOE_JSON_DETECTION, JOE_JSON_CLEAN)
        else:
            response_data[JOE_JSON_RESPONSE][JOE_JSON_REPUTATION_LABEL] = JOE_JSON_CLEAN

        summary_data.update(
            {
                JOE_JSON_STATUS: response_data.get(JOE_JSON_RESPONSE, {}).get(JOE_JSON_STATUS),
                JOE_JSON_REPUTATION_LABEL: response_data[JOE_JSON_RESPONSE][JOE_JSON_REPUTATION_LABEL],
            }
        )

        response_data = self._parse_response(response_data.get(JOE_JSON_RESPONSE))

        # Removing unnecessary data from response
        if phantom.is_url(response_data.get(JOE_JSON_FILENAME, "")):
            response_data[JOE_JSON_URL] = response_data.pop(JOE_JSON_FILENAME)
            if JOE_JSON_MD_5 in response_data:
                del response_data[JOE_JSON_MD_5]
            if JOE_JSON_SHA_1 in response_data:
                del response_data[JOE_JSON_SHA_1]
            if JOE_JSON_SHA_256 in response_data:
                del response_data[JOE_JSON_SHA_256]

        if JOE_JSON_COMMENTS in response_data.get(JOE_JSON_SAMPLE_STATUS, ""):
            del response_data[JOE_JSON_COMMENTS]

        action_result.add_data(response_data)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_file_reputation(self, param):
        """This method is used to query Joe Sandbox to get file details

        :param param: URL to search
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # getting mandatory parameter
        hash = param[JOE_JSON_HASH]

        api_params = {JOE_JSON_Q: hash}

        response_status, response_data = self._make_rest_call(JOE_REPUTATION_SEARCH_ENDPOINT, action_result, data=api_params)

        if phantom.is_fail(response_status):
            return action_result.get_status()

        response_data = response_data.get(JOE_JSON_RESPONSE, {})

        if response_data and len(response_data) > 0:
            recent_web_id = response_data[0].get(JOE_JSON_WEBID)
        else:
            return action_result.set_status(phantom.APP_ERROR, JOE_HASH_SEARCH_ANALYSIS_NOT_FOUND_MSG)

        # getting status of fetched recent webid
        response_status, response_data = self._make_rest_call(JOE_CHECK_STATUS_ENDPOINT, action_result, data={JOE_JSON_WEBID: recent_web_id})

        if phantom.is_fail(response_status):
            return action_result.get_status()

        # Adding a new key in the data which contains the reputation of the file or URL, defined based on 'runs --> detection'
        # parameter available in data
        self.debug_print("Processing the response")
        reputation_detection_list = response_data.get(JOE_JSON_RESPONSE, {}).get(JOE_JSON_RUNS, [])

        if reputation_detection_list and len(reputation_detection_list) > 0:
            for reputation_item in reputation_detection_list:
                response_data[JOE_JSON_RESPONSE][JOE_JSON_REPUTATION_LABEL] = reputation_item.get(JOE_JSON_DETECTION, JOE_JSON_CLEAN)
        else:
            response_data[JOE_JSON_RESPONSE][JOE_JSON_REPUTATION_LABEL] = JOE_JSON_CLEAN

        summary_data.update(
            {
                JOE_JSON_STATUS: response_data.get(JOE_JSON_RESPONSE, {}).get(JOE_JSON_STATUS),
                JOE_JSON_REPUTATION_LABEL: response_data[JOE_JSON_RESPONSE][JOE_JSON_REPUTATION_LABEL],
            }
        )

        response_data = self._parse_response(response_data.get(JOE_JSON_RESPONSE))

        if JOE_JSON_COMMENTS in response_data.get(JOE_JSON_SAMPLE_STATUS, ""):
            del response_data[JOE_JSON_COMMENTS]

        action_result.add_data(response_data)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_cookbooks(self, param):
        """This method is used to fetch list of all cookbooks

        :param param: NA
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        response_status, response_data = self._make_rest_call(JOE_LIST_COOKBOOKS_ENDPOINT, action_result)

        if phantom.is_fail(response_status):
            self.save_progress(f"Error while fetching the cookbooks: {action_result.get_message()}")
            return action_result.get_status()

        response_data = response_data.get(JOE_JSON_RESPONSE)

        if response_data:
            for data in response_data:
                action_result.add_data(data)
        else:
            self.debug_print(f"Could not find {JOE_JSON_RESPONSE} in response data")

        summary_data.update({"total_cookbooks": action_result.get_data_size()})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_cookbook(self, param):
        """Function to fetch a particular cookbook and add it to vault

        :param param: Cookbook ID
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        cookbook_id = param[JOE_JSON_ID]

        json_data = {JOE_JSON_ID: cookbook_id}

        response_status, response_data = self._make_rest_call(JOE_GET_COOKBOOK_ENDPOINT, action_result, data=json_data)

        if phantom.is_fail(response_status):
            return action_result.get_status()

        response_data = response_data.get(JOE_JSON_RESPONSE, {})

        if not response_data:
            return action_result.set_status(phantom.APP_ERROR, "The requested cookbook does not exist")

        cookbook_code = response_data.get(JOE_JSON_CODE)
        cookbook_name = f"{response_data.get(JOE_JSON_NAME)}{JOE_JSON_JBS}"

        # Saving report data in vault
        response_status, vault_details = self._save_file_to_vault(cookbook_name, self.get_container_id(), cookbook_code, action_result)

        if phantom.is_fail(response_status):
            return action_result.get_status()

        response_data.update(
            {JOE_JSON_FILE_NAME: vault_details.get(JOE_JSON_REPORT_FILE_NAME), JOE_JSON_COOKBOOK_VAULT_ID: vault_details.get(JOE_JSON_VAULT_ID)}
        )
        action_result.add_data(response_data)

        return action_result.set_status(phantom.APP_SUCCESS, "The cookbook is successfully fetched and added to the vault")

    def handle_action(self, param):
        """This function gets current action identifier and calls member function of its own to handle the action

        :param param: dictionary which contains information about the actions to be executed
        :return: status(success/failure)
        """

        self.debug_print("action_id", self.get_action_identifier())

        # Mapping each action with its corresponding method in Dictionary
        action_mapping = {
            "test_connectivity": self._handle_test_connectivity,
            "detonate_file": self._handle_detonate_file,
            "get_pcap": self._handle_get_pcap,
            "get_report": self._handle_get_report,
            "check_status": self._handle_check_status,
            "detonate_url": self._handle_detonate_url,
            "url_reputation": self._handle_url_reputation,
            "file_reputation": self._handle_file_reputation,
            "list_cookbooks": self._handle_list_cookbooks,
            "get_cookbook": self._handle_get_cookbook,
        }

        action = self.get_action_identifier()
        action_execution_status = phantom.APP_SUCCESS

        if action in list(action_mapping.keys()):
            action_function = action_mapping[action]
            action_execution_status = action_function(param)

        return action_execution_status

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

        # get the asset config
        config = self.get_config()

        # Initialize configuration parameters
        self._base_url = config[JOE_CONFIG_SERVER].strip("/")
        self._api_key = config[JOE_CONFIG_API_KEY]
        self._verify_ssl = config[JOE_CONFIG_VERIFY_SSL]

        self._detonate_timeout = str(config.get(JOE_CONFIG_TIMEOUT, JOE_TIME_DEFAULT))
        self._analysis_time = str(config.get(JOE_CONFIG_ANALYSIS_TIME, JOE_TIME_DEFAULT))

        if not self._detonate_timeout.isdigit() or not self._analysis_time.isdigit():
            self.save_progress(JOE_ERR_INVALID_ANALYSIS_AND_DETONATION_TIME_MSG)
            return phantom.APP_ERROR
        else:
            self._detonate_timeout = int(self._detonate_timeout)
            self._analysis_time = int(self._analysis_time)

        return phantom.APP_SUCCESS

    def finalize(self):
        """This function gets called once all the param dictionary elements are looped over and no more handle_action
        calls are left to be made. It gives the AppConnector a chance to loop through all the results that were
        accumulated by multiple handle_action function calls and create any summary if required. Another usage is
        cleanup, disconnect from remote devices etc.

        :return: status (success/failure)
        """

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
            login_url = f"{BaseConnector._get_phantom_base_url()}login"
            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=JOE_DEFAULT_REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = f"csrftoken={csrftoken}"
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=JOE_DEFAULT_REQUEST_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print(f"Unable to get session id from the platform. Error: {e!s}")
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = JoeSandboxV2Connector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
