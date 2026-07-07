# File: wildfire_connector.py
#
# Copyright (c) 2016-2025 Splunk Inc.
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
import inspect
import json

# Other imports used by this connector
import os
import re
import shutil
import time
import uuid

import magic
import phantom.app as phantom
import phantom.rules as ph_rules
import phantom.utils as ph_utils
import requests
import xmltodict
from bs4 import BeautifulSoup
from phantom.app import ActionResult, BaseConnector
from phantom.vault import Vault

from wildfire_consts import *


class WildfireConnector(BaseConnector):
    # The actions supported by this connector
    ACTION_ID_DETONATE_FILE = "detonate_file"
    ACTION_ID_DETONATE_URL = "detonate_url"
    ACTION_GET_URL_REPUTATION = "get_url_reputation"
    ACTION_ID_GET_REPORT = "get_report"
    ACTION_ID_GET_SAMPLE = "get_sample"
    ACTION_ID_GET_PCAP = "get_pcap"
    ACTION_ID_SAVE_REPORT = "save_report"
    ACTION_ID_TEST_ASSET_CONNECTIVITY = "test_asset_connectivity"

    MAGIC_FORMATS = [
        (re.compile("^PE.* Windows"), ["pe file"], ".exe"),
        (re.compile("^MS-DOS executable"), ["pe file"], ".exe"),
        (re.compile("^PDF "), ["pdf"], ".pdf"),
        (re.compile("^MDMP crash"), ["process dump"], ".dmp"),
        (re.compile("^Macromedia Flash"), ["flash"], ".flv"),
        (re.compile("^tcpdump capture"), ["pcap"], ".pcap"),
    ]

    FILE_UPLOAD_ERROR_DESC = {
        "401": "API key invalid",
        "405": "HTTP method Not Allowed",
        "413": "Sample file size over max limit",
        "418": "Sample file type is not supported",
        "419": "Max number of uploads per day exceeded",
        "422": "URL download error",
        "500": "Internal error",
        "513": "File upload failed",
    }

    GET_REPORT_ERROR_DESC = {
        "401": "API key invalid",
        "404": "The report was not found",
        "405": "HTTP method Not Allowed",
        "419": "Request report quota exceeded",
        "420": "Insufficient arguments",
        "421": "Invalid arguments",
        "500": "Internal error",
    }

    GET_SAMPLE_ERROR_DESC = {
        "401": "API key invalid",
        "403": "Permission Denied",
        "404": "The sample was not found",
        "405": "HTTP method Not Allowed",
        "419": "Request sample quota exceeded",
        "420": "Insufficient arguments",
        "421": "Invalid arguments",
        "500": "Internal error",
    }

    GET_PCAP_ERROR_DESC = {
        "401": "API key invalid",
        "403": "Permission Denied",
        "404": "The pcap was not found",
        "405": "HTTP method Not Allowed",
        "419": "Request sample quota exceeded",
        "420": "Insufficient arguments",
        "421": "Invalid arguments",
        "500": "Internal error",
    }

    PLATFORM_ID_MAPPING = {
        "Default": None,
        "Windows XP, Adobe Reader 9.3.3, Office 2003": 1,
        "Windows XP, Adobe Reader 9.4.0, Flash 10, Office 2007": 2,
        "Windows XP, Adobe Reader 11, Flash 11, Office 2010": 3,
        "Windows 7 32-bit, Adobe Reader 11, Flash11, Office 2010": 4,
        "Windows 7 64-bit, Adobe Reader 11, Flash 11, Office 2010": 5,
        "Android 2.3, API 10, avd2.3.1": 201,
        "PDF Static Analyzer": 100,
        "DOC/CDF Static Analyzer": 101,
        "Java/Jar Static Analyzer": 102,
        "Office 2007 Open XML Static Analyzer": 103,
        "Adobe Flash Static Analyzer": 104,
        "PE Static Analyzer": 204,
        "Archives (RAR and 7-Zip files)": 800,
        "Windows XP, Internet Explorer 8, Flash 11": 6,
        "Windows 7, Flash 11, Office 2010": 21,
        "Mac OSX Mountain Lion": 50,
        "Windows 10 64-bit, Adobe Reader 11, Flash 22, Office 2010": 66,
        "RTF Static Analyzer": 105,
        "Max OSX Static Analyzer": 110,
        "APK Static Analyzer": 200,
        "Android 4.1, API 16, avd4.1.1 X86": 202,
        "Android 4.1, API 16, avd4.1.1 ARM": 203,
        "Phishing Static Analyzer": 205,
        "Android 4.3, API 18, avd4.3 ARM": 206,
        "Script Static Analyzer": 207,
        "Windows XP, Internet Explorer 8, Flash 13.0.0.281, Flash 16.0.0.305, Elink Analyzer": 300,
        "Windows 7, Internet Explorer 9, Flash 13.0.0.281, Flash 17.0.0.169, Elink Analyzer": 301,
        "Windows 7, Internet Explorer 10, Flash 16.0.0.305, Flash 17.0.0.169, Elink Analyzer": 302,
        "Windows 7, Internet Explorer 11, Flash 16.0.0.305, Flash 17.0.0.169, Elink Analyzer": 303,
        "Linux (ELF Files)": 400,
        "Linux Script Dynamic Analyzer": 403,
        "Linux Script Static Analyzer": 404,
        "BareMetal Windows 7 x64, Adobe Reader 11, Flash 11, Office 2010": 501,
    }

    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._api_token = None
        self._proxy = None

    def initialize(self):
        config = self.get_config()

        ret_val, self.timeout = self._validate_integer(
            self, config.get(WILDFIRE_JSON_POLL_TIMEOUT_MINS, WILDFIRE_MAX_TIMEOUT_DEF), WILDFIRE_TIMEOUT
        )
        if phantom.is_fail(ret_val):
            return self.get_status()

        # Base URL
        self._base_url = config[WILDFIRE_JSON_BASE_URL]
        if self._base_url.endswith("/"):
            self._base_url = self._base_url[:-1]

        self._host = self._base_url[self._base_url.find("//") + 2 :]

        self._base_url += "/publicapi"

        self._proxy = {}
        env_vars = config.get("_reserved_environment_variables", {})
        if "HTTP_PROXY" in env_vars:
            self._proxy["http"] = env_vars["HTTP_PROXY"]["value"]
        elif "HTTP_PROXY" in os.environ:
            self._proxy["http"] = os.environ.get("HTTP_PROXY")

        if "HTTPS_PROXY" in env_vars:
            self._proxy["https"] = env_vars["HTTPS_PROXY"]["value"]
        elif "HTTPS_PROXY" in os.environ:
            self._proxy["https"] = os.environ.get("HTTPS_PROXY")

        self._req_sess = requests.Session()

        return phantom.APP_SUCCESS

    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, WILDFIRE_INVALID_INT.format(param=key)), None

                parameter = int(parameter)
            except:
                return action_result.set_status(phantom.APP_ERROR, WILDFIRE_INVALID_INT.format(param=key)), None

            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, WILDFIRE_ERR_NEGATIVE_INT_PARAM.format(param=key)), None
            if not allow_zero and parameter == 0:
                return action_result.set_status(phantom.APP_ERROR, WILDFIRE_ERR_INVALID_PARAM.format(param=key)), None

        return phantom.APP_SUCCESS, parameter

    def _get_error_message_from_exception(self, e):
        """This function is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        error_message = "Unknown error occurred. Please check the asset configuration and|or action parameters."
        error_code = "Error code unavailable"
        try:
            if e.args:
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_code = "Error code unavailable"
                    error_message = e.args[0]
            else:
                error_code = "Error code unavailable"
                error_message = "Unknown error occurred. Please check the asset configuration and|or action parameters."
        except:
            error_code = "Error code unavailable"
            error_message = "Unknown error occurred. Please check the asset configuration and|or action parameters."

        return f"Error Code: {error_code}. Error Message: {error_message}"

    def _parse_report_status_message(self, response, action_result):
        task_info = response.get("task_info", None)

        if not task_info:
            return None

        reports = task_info.get("report", None)

        if not reports:
            return None

        if not isinstance(reports, list):
            reports = [reports]

        response["task_info"]["report"] = reports

        for report in reports:
            report["network"] = self._normalize_children_into_list(report.get("network", {}))
            report["timeline"] = self._normalize_children_into_list(report.get("timeline", {}))
            report["process"] = self._normalize_children_into_list(report.get("process_created", {}))
            # self._normalize_into_list(report, 'process_list')
            self._normalize_into_list(report, "process_tree")
            report["summary"] = self._normalize_children_into_list(report.get("summary", {}))
            report["process_list"] = self._normalize_children_into_list(report.get("process_list", {}))

            try:
                processes = report["process_list"]["process"]
            except Exception:
                processes = []

            for process in processes:
                process["service"] = self._normalize_children_into_list(process.get("service", {}))
                process["registry"] = self._normalize_children_into_list(process.get("registry", {}))
                process["file"] = self._normalize_children_into_list(process.get("file", {}))
                process["mutex"] = self._normalize_children_into_list(process.get("mutex", {}))

            # need to modify the summary to contain a dictionary
            summary = report.get("summary", None)
            if not summary:
                sum_entries = None
            else:
                sum_entries = summary.get("entry", None)

            if sum_entries:
                for i, entry in enumerate(sum_entries):
                    if not isinstance(entry, dict):
                        sum_entries[i] = {"#text": entry, "@details": "N/A", "@score": "N/A", "@id": "N/A"}

            report["registry"] = self._normalize_children_into_list(report.get("registry", {}))
            report["file"] = self._normalize_children_into_list(report.get("file", {}))

        return response

    def _parse_error(self, response, result, error_desc):
        status_code = response.status_code
        detail = response.text

        if "xml" in response.headers.get("Content-Type", ""):
            xml = response.text

            try:
                response_dict = xmltodict.parse(xml)
                response_dict = json.loads(json.dumps(response_dict))
                error = response_dict.get("error", None)
                if error:
                    detail = error.get("error-message", None)
                else:
                    detail = None
            except:
                detail = None

        if "html" in response.headers.get("Content-Type", ""):
            try:
                soup = BeautifulSoup(response.text, "html.parser")
                # Remove the script, style, footer and navigation part from the HTML message
                for element in soup(["script", "style", "footer", "nav"]):
                    element.extract()
                error_text = soup.text
                error_text_list = list(filter(None, error_text.split("\n")))
                detail = error_text_list[0]
            except:
                detail = "Cannot parse error details"

        if detail:
            return result.set_status(phantom.APP_ERROR, WILDFIRE_ERR_REST_API.format(status_code=status_code, detail=detail))

        if not error_desc:
            return result.set_status(phantom.APP_ERROR, WILDFIRE_ERR_REST_API.format(status_code=status_code, detail="N/A"))

        detail = error_desc.get(str(status_code), None)

        if not detail:
            # no detail
            return result.set_status(phantom.APP_ERROR, WILDFIRE_ERR_REST_API.format(status_code=status_code, detail="N/A"))

        return result.set_status(phantom.APP_ERROR, WILDFIRE_ERR_REST_API.format(status_code=status_code, detail=detail))

    def _make_rest_call(
        self, endpoint, result, error_desc, method="get", params={}, data=None, files=None, parse_response=True, additional_succ_codes={}
    ):
        url = f"{self._base_url}{endpoint}"

        if not data:
            data = {}

        config = self.get_config()

        request_func = getattr(self._req_sess, method)

        if not request_func:
            return result.set_status(phantom.APP_ERROR, f"Invalid method call: {method} for requests module"), None

        data.update({"apikey": config[WILDFIRE_JSON_API_KEY]})

        try:
            r = request_func(url, params=params, data=data, files=files, verify=config[phantom.APP_JSON_VERIFY], proxies=self._proxy)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return result.set_status(phantom.APP_ERROR, "REST Api to server failed", error_message), None

        # It's ok if r.text is None, dump that
        if hasattr(result, "add_debug_data"):
            result.add_debug_data({"r_text": r.text if r else "r is None"})

        if r.status_code in additional_succ_codes:
            response = additional_succ_codes[r.status_code]
            return phantom.APP_SUCCESS, response if response is not None else r.text

        # Look for errors
        if r.status_code != requests.codes.ok:  # pylint: disable=E1101
            self._parse_error(r, result, error_desc)
            return result.get_status(), r.text

        if not parse_response:
            return phantom.APP_SUCCESS, r

        xml = r.text

        try:
            response_dict = xmltodict.parse(xml)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.save_progress(WILDFIRE_ERR_UNABLE_TO_PARSE_REPLY)
            return result.set_status(phantom.APP_ERROR, WILDFIRE_ERR_UNABLE_TO_PARSE_REPLY, error_message), None

        if "wildfire" not in response_dict:
            return result.set_status(phantom.APP_ERROR, WILDFIRE_ERR_REPLY_FORMAT_KEY_MISSING.format(key="wildfire"))

        response_dict = json.loads(json.dumps(response_dict))

        return phantom.APP_SUCCESS, response_dict["wildfire"]

    def _get_file_dict(self, param, action_result):
        vault_id = param["vault_id"]

        filename = param.get("file_name")
        if not filename:
            filename = vault_id

        try:
            success, message, vault_info = ph_rules.vault_info(vault_id=vault_id, container_id=self.get_container_id(), trace=False)
            vault_info = next(iter(vault_info))
        except IndexError:
            return action_result.set_status(phantom.APP_ERROR, "Vault file could not be found with supplied Vault ID"), None
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Vault ID not valid"), None

        if not vault_info:
            return action_result.set_status(
                phantom.APP_ERROR, "Error while fetching the vault information of the vault id: '{}'".format(param.get("vault_id"))
            )

        vault_path = vault_info.get("path", None)
        if vault_path is None:
            return action_result.set_status(phantom.APP_ERROR, "Could not find a path associated with the provided vault ID")
        try:
            payload = open(vault_path, "rb")
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Unable to open vault file: {error_message}")

        files = {"file": (filename, payload)}

        return phantom.APP_SUCCESS, files

    def _test_connectivity(self, param):
        # get the file from the app directory
        dirpath = os.path.dirname(inspect.getfile(self.__class__))
        filename = WILDFIRE_TEST_PDF_FILE

        filepath = f"{dirpath}/{filename}"

        try:
            payload = open(filepath, "rb")
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.set_status(phantom.APP_ERROR, f'Test pdf file not found at "{filepath}"', error_message)
            self.append_to_message("Test Connectivity failed")
            return self.get_status()

        self.save_progress("Detonating test pdf file for checking connectivity")

        files = {"file": (filename, payload)}

        ret_val, response = self._make_rest_call("/submit/file", self, self.FILE_UPLOAD_ERROR_DESC, method="post", files=files)

        if phantom.is_fail(ret_val):
            self.append_to_message("Test Connectivity Failed")
            return self.get_status()

        self.save_progress("Test Connectivity Passed")
        return self.set_status(phantom.APP_SUCCESS)

    def _normalize_into_list(self, input_dict, key):
        if not input_dict:
            return None

        if key not in input_dict:
            return None

        if not isinstance(input_dict[key], list):
            input_dict[key] = [input_dict[key]]
        input_dict[key.lower()] = input_dict.pop(key)

        return input_dict

    def _normalize_children_into_list(self, input_dict):
        if not input_dict:
            return {}

        output_dict = {}
        for key in input_dict:
            if not isinstance(input_dict[key], list):
                output_dict[key] = [input_dict[key]]
            else:
                output_dict[key] = input_dict[key]
            output_dict[key.lower()] = output_dict.pop(key)

        return output_dict

    def _check_detonated_report(self, task_id, action_result):
        """This function is different than other functions that get the report
        since it is supposed to check just once and return, also treat a 404 as error
        """

        data = {"format": "xml", "hash": task_id}

        ret_val, response = self._make_rest_call("/get/report", action_result, self.GET_REPORT_ERROR_DESC, method="post", data=data)

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        # parse if successful
        response = self._parse_report_status_message(response, action_result)

        if response:
            return phantom.APP_SUCCESS, response

        return phantom.APP_ERROR, None

    def _poll_task_status(self, action_result, task_id=None, url=None):
        if not (task_id or url):
            return action_result.set_status(phantom.APP_ERROR, "Please provide 'task_id' or 'url'"), None

        polling_attempt = 0

        max_polling_attempts = (int(self.timeout) * 60) / WILDFIRE_SLEEP_SECS

        if task_id:
            data = {"format": "xml", "hash": task_id}
        else:
            data = {"url": url}

        while polling_attempt < max_polling_attempts:
            polling_attempt += 1

            self.save_progress(f"Polling attempt {polling_attempt} of {max_polling_attempts}")

            ret_val, response = self._make_rest_call(
                "/get/report",
                action_result,
                self.GET_REPORT_ERROR_DESC,
                method="post",
                data=data,
                additional_succ_codes={404: WILDFIRE_MESSAGE_REPORT_PENDING},
                parse_response=False if url else True,
            )

            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            if WILDFIRE_MESSAGE_REPORT_PENDING in response:
                time.sleep(WILDFIRE_SLEEP_SECS)
                continue

            if phantom.is_success(ret_val):
                if url:
                    try:
                        response = response.json()
                    except Exception as e:
                        error_message = self._get_error_message_from_exception(e)
                        return action_result.set_status(phantom.APP_ERROR, "Unable to parse response as JSON", error_message), None

                    result = response.get("result", None)
                    if result:
                        report = result.get("report", {})
                        report = dict(json.loads(str(report)))
                        response["result"].update({"report": report})
                else:
                    # parse if successfull and url is none
                    response = self._parse_report_status_message(response, action_result)

                if response:
                    return phantom.APP_SUCCESS, response

            time.sleep(WILDFIRE_SLEEP_SECS)

        self.save_progress("Reached max polling attempts.")

        return action_result.set_status(phantom.APP_ERROR, WILDFIRE_MESSAGE_MAX_POLLS_REACHED), None

    def _get_report(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        task_id = param[WILDFIRE_JSON_TASK_ID]
        response = {}

        ret_val, verdict_data = self._get_verdict(action_result, task_id=task_id)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if verdict_data["verdict_code"] >= 0:
            summary_available = True
            # Now poll for the result
            ret_val, response = self._poll_task_status(action_result, task_id=task_id)

            if phantom.is_fail(ret_val):
                return action_result.get_status()
        else:
            summary_available = False

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["verdict_code"] = verdict_data["verdict_code"]
        summary["verdict"] = verdict_data["verdict_message"]
        summary["summary_available"] = summary_available

        return action_result.set_status(phantom.APP_SUCCESS)

    def _save_file_to_vault(self, action_result, response, sample_hash):
        # Create a tmp directory on the vault partition
        guid = uuid.uuid4()

        if hasattr(Vault, "get_vault_tmp_dir"):
            temp_dir = Vault.get_vault_tmp_dir()
        else:
            temp_dir = "/vault/tmp"

        local_dir = f"{temp_dir}/{guid}"
        self.save_progress(f"Using temp directory: {guid}")

        try:
            os.makedirs(local_dir)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, "Unable to create temporary folder '/vault/tmp'.", error_message)

        file_path = f"{local_dir}/{sample_hash}"

        # open and download the file
        try:
            with open(file_path, "wb") as f:
                f.write(response.content)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Unable to open file: {error_message}")

        contains = []
        file_ext = ""
        magic_str = magic.from_file(file_path)
        for regex, cur_contains, extension in self.MAGIC_FORMATS:
            if regex.match(magic_str):
                contains.extend(cur_contains)
                if not file_ext:
                    file_ext = extension

        file_name = f"{sample_hash}{file_ext}"

        # move the file to the vault
        try:
            success, message, vault_id = ph_rules.vault_add(
                self.get_container_id(), file_path, file_name=file_name, metadata={"contains": contains}
            )
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, error_message)
        curr_data = {}
        if success:
            curr_data[phantom.APP_JSON_VAULT_ID] = vault_id
            curr_data[phantom.APP_JSON_NAME] = file_name
            action_result.add_data(curr_data)
            wanted_keys = [phantom.APP_JSON_VAULT_ID, phantom.APP_JSON_NAME]
            summary = {x: curr_data[x] for x in wanted_keys}
            if contains:
                summary.update({"file_type": ",".join(contains)})
            action_result.update_summary(summary)
            action_result.set_status(phantom.APP_SUCCESS)
        else:
            action_result.set_status(phantom.APP_ERROR, phantom.APP_ERR_FILE_ADD_TO_VAULT)
            action_result.append_to_message(message)

        # remove the /tmp/<> temporary directory
        shutil.rmtree(local_dir)

        return action_result.get_status()

    def _get_sample(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        sample_hash = param[WILDFIRE_JSON_HASH]

        self.save_progress("Getting file from WildFire")

        ret_val, response = self._make_rest_call(
            "/get/sample",
            action_result,
            self.GET_SAMPLE_ERROR_DESC,
            method="post",
            data={"hash": sample_hash},
            parse_response=False,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return self._save_file_to_vault(action_result, response, sample_hash)

    def _save_report(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        sample_hash = param[WILDFIRE_JSON_TASK_ID]

        self.save_progress("Getting report from WildFire")

        data = {"hash": sample_hash, "format": "pdf"}

        ret_val, response = self._make_rest_call(
            "/get/report", action_result, self.GET_REPORT_ERROR_DESC, method="post", data=data, parse_response=False
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return self._save_file_to_vault(action_result, response, sample_hash)

    def _get_platform_id(self, param):
        platform = param.get(WILDFIRE_JSON_PLATFORM)

        if not platform:
            return phantom.APP_SUCCESS, None

        if platform not in self.PLATFORM_ID_MAPPING:
            return phantom.APP_ERROR, None

        return phantom.APP_SUCCESS, self.PLATFORM_ID_MAPPING[platform]

    def _get_pcap(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        sample_hash = param[WILDFIRE_JSON_HASH]
        rest_data = {"hash": sample_hash}

        ret_val, platform_id = self._get_platform_id(param)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, "Please provide valid platform name")

        if platform_id:
            rest_data.update({"platform": platform_id})

        self.save_progress("Getting pcap from WildFire")

        ret_val, response = self._make_rest_call(
            "/get/pcap",
            action_result,
            self.GET_PCAP_ERROR_DESC,
            method="post",
            data=rest_data,
            parse_response=False,
        )

        if phantom.is_fail(ret_val):
            if platform_id in [2, 5]:
                platform_id = 60 if platform_id == 2 else 61
                rest_data.update({"platform": platform_id})
                ret_val, response = self._make_rest_call(
                    "/get/pcap", action_result, self.GET_PCAP_ERROR_DESC, method="post", data=rest_data, parse_response=False
                )

                if phantom.is_fail(ret_val):
                    if platform_id == 60:
                        platform_id = 20
                        rest_data.update({"platform": platform_id})
                        ret_val, response = self._make_rest_call(
                            "/get/pcap", action_result, self.GET_PCAP_ERROR_DESC, method="post", data=rest_data, parse_response=False
                        )

                        if phantom.is_fail(ret_val):
                            return action_result.get_status()

                        return self._save_file_to_vault(action_result, response, sample_hash)

                    return action_result.get_status()

                return self._save_file_to_vault(action_result, response, sample_hash)

            return action_result.get_status()

        return self._save_file_to_vault(action_result, response, sample_hash)

    def _get_verdict(self, action_result, task_id=None, url=None):
        if not (task_id or url):
            return action_result.set_status(phantom.APP_ERROR, "Please provide 'task_id' or 'url'"), None

        self.save_progress(f"Getting verdict for: {task_id if task_id else url}")

        # make rest call to get verdict whether URL is in wildfire db
        if not task_id:
            ret_val, response = self._make_rest_call(
                "/get/verdict", action_result, self.FILE_UPLOAD_ERROR_DESC, method="post", files={"url": ("", url)}
            )
        else:
            ret_val, response = self._make_rest_call(
                "/get/verdict", action_result, self.FILE_UPLOAD_ERROR_DESC, method="post", files={"hash": ("", task_id)}
            )

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        # get verdict value
        if task_id:
            try:
                verdict_code = int(response["get-verdict-info"]["verdict"])
                verdict_sha256 = response["get-verdict-info"]["sha256"]
                verdict_md5 = response["get-verdict-info"]["md5"]
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Verdict could not be retrieved"), None

            verdict_data = {"verdict_code": verdict_code, "verdict_sha256": verdict_sha256, "verdict_md5": verdict_md5}
        else:
            try:
                verdict_code = int(response["get-verdict-info"]["verdict"])
                verdict_analysis_time = response["get-verdict-info"]["analysis_time"]
                verdict_url = response["get-verdict-info"]["url"]
                verdict_valid = response["get-verdict-info"]["valid"]
            except:
                return action_result.set_status(phantom.APP_ERROR, "Verdict could not be retrieved"), None

            verdict_data = {
                "verdict_code": verdict_code,
                "verdict_analysis_time": verdict_analysis_time,
                "verdict_url": verdict_url,
                "verdict_valid": verdict_valid,
            }

        if verdict_code == 0:
            verdict = "benign"
        elif verdict_code == 1:
            verdict = "malware"
        elif verdict_code == 2:
            verdict = "grayware"
        elif verdict_code == 4:
            verdict = "phishing"
        elif verdict_code == -100:
            verdict = "pending, the sample exists, but there is currently no verdict"
        elif verdict_code == -101:
            verdict = "error"
        elif verdict_code == -102:
            verdict = "unknown, cannot find sample record in the WildFire database"
        elif verdict_code == -103:
            verdict = "invalid hash value"
        else:
            verdict = "unknown verdict code"

        verdict_data.update({"verdict_message": verdict})

        return phantom.APP_SUCCESS, verdict_data

    def _detonate_url(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        # add an http to url if not present
        url = param["url"]
        response = {}

        if not ph_utils.is_url(url):
            return action_result.get_status()

        is_file = param.get("is_file", False)

        if is_file:
            endpoint = "/submit/url"
            files = {"url": ("", url)}
            r_path = "upload-file-info"
            # make rest call to get sha256 and md5
            ret_val, response = self._make_rest_call(endpoint, action_result, self.FILE_UPLOAD_ERROR_DESC, method="post", files=files)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            # get sha256 and md5 hashes
            try:
                task_id = response[r_path]["sha256"]
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Task id not part of response, can't continue")

            # time to reflect on server in case of new file for wildfire database
            time.sleep(1)

            ret_val, verdict_data = self._get_verdict(action_result, task_id=task_id)
        else:
            ret_val, verdict_data = self._get_verdict(action_result, url=url)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if verdict_data["verdict_code"] >= 0:
            summary_available = True
            # Now poll for the result
            if is_file:
                ret_val, response = self._poll_task_status(action_result, task_id=task_id)
            else:
                ret_val, response = self._poll_task_status(action_result, url=url)

            if phantom.is_fail(ret_val):
                return action_result.get_status()
        else:
            summary_available = False

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["verdict_code"] = verdict_data["verdict_code"]
        summary["verdict"] = verdict_data["verdict_message"]
        summary["summary_available"] = summary_available

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_url_reputation(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        # add an http to url if not present
        url = param["url"]

        ret_val, verdict_data = self._get_verdict(action_result, url=url)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(verdict_data)

        summary = action_result.update_summary({})
        summary["success"] = True

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_vault_file_sha256(self, vault_id, action_result):
        self.save_progress("Getting the sha256 of the file")

        sha256 = None
        metadata = None

        try:
            success, message, vault_meta_info = ph_rules.vault_info(container_id=self.get_container_id(), vault_id=vault_id, trace=False)
            if not vault_meta_info:
                self.debug_print(f"Error while fetching meta information for vault ID: {vault_id}, message: {message}")
                return action_result.set_status(phantom.APP_ERROR, WILDFIRE_ERR_FILE_NOT_FOUND_IN_VAULT), None

            if not isinstance(vault_meta_info, list):
                vault_meta_info = list(vault_meta_info)
            metadata = vault_meta_info[0]["metadata"]

        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Could not get file path for vault item"), None

        if not metadata:
            return action_result.set_status(phantom.APP_ERROR, "Unable to get meta info of vault file"), None

        try:
            sha256 = metadata["sha256"]
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, "Unable to get meta info of vault file", error_message), None

        return phantom.APP_SUCCESS, sha256

    def _detonate_file(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val, files = self._get_file_dict(param, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # get the sha256 of the file
        vault_id = param["vault_id"]
        ret_val, sha256 = self._get_vault_file_sha256(vault_id, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        data = action_result.add_data({})
        self.save_progress("Checking for prior detonations")

        ret_val, response = self._check_detonated_report(sha256, action_result)

        if phantom.is_fail(ret_val):
            # Was not detonated before
            self.save_progress("Uploading the file")

            ret_val, response = self._make_rest_call("/submit/file", action_result, self.FILE_UPLOAD_ERROR_DESC, method="post", files=files)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            # The first part is the uploaded file info
            data.update(response)

            # get the sha256
            upload_file_info = response.get("upload-file-info", None)
            if upload_file_info:
                task_id = upload_file_info.get("sha256", None)
            else:
                task_id = None

            if not task_id:
                upload_file_info = response.get("upload-file-info", None)
                if upload_file_info:
                    task_id = upload_file_info.get("md5", None)
                else:
                    task_id = None

            if task_id is None:
                return action_result.get_status()

            # Now poll for the result
            ret_val, response = self._poll_task_status(action_result, task_id=task_id)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

        # Add the report
        data.update(response)

        file_info = response.get("file_info", None)
        if file_info:
            malware = file_info.get("malware", "no")
        else:
            malware = "no"

        action_result.update_summary({WILDFIRE_JSON_MALWARE: malware})

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this connector run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == self.ACTION_ID_DETONATE_FILE:
            ret_val = self._detonate_file(param)
        elif action_id == self.ACTION_ID_DETONATE_URL:
            ret_val = self._detonate_url(param)
        elif action_id == self.ACTION_GET_URL_REPUTATION:
            ret_val = self._get_url_reputation(param)
        elif action_id == self.ACTION_ID_GET_REPORT:
            ret_val = self._get_report(param)
        elif action_id == self.ACTION_ID_GET_SAMPLE:
            ret_val = self._get_sample(param)
        elif action_id == self.ACTION_ID_GET_PCAP:
            ret_val = self._get_pcap(param)
        elif action_id == self.ACTION_ID_SAVE_REPORT:
            ret_val = self._save_report(param)
        elif action_id == self.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity(param)

        return ret_val


def main():
    import argparse
    import sys

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
            login_url = WildfireConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify)  # nosemgrep: python.requests.best-practice.use-timeout.use-timeout
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(  # nosemgrep: python.requests.best-practice.use-timeout.use-timeout
                login_url, verify=verify, data=data, headers=headers
            )
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = WildfireConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
