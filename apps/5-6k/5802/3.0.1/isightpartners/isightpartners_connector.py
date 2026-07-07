# File: isightpartners_connector.py
#
# Copyright (c) 2014-2025 Splunk Inc.
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
import email
import hashlib
import hmac
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timedelta
from operator import itemgetter

import phantom.app as phantom
import phantom.rules as ph_rules
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# THIS Connector imports
from isightpartners_consts import *


ARTIFACT_LABEL = "artifact"

# dictionary that contains the comman keys in the container
_container_common = {
    "description": "Container added by Phantom iSightPartners App",
    "run_automation": False,  # Don't run any playbooks, when this artifact is added
}

_artifact_common = {
    "label": ARTIFACT_LABEL,
    "type": "network",
    "description": "Artifact added by Phantom iSightPartners App",
    "run_automation": False,  # Don't run any playbooks, when this artifact is added
}


class IsightpartnersConnector(BaseConnector):
    # The actions supported by this connector
    ACTION_ID_HUNT_FILE = "hunt_file"
    ACTION_ID_HUNT_DOMAIN = "hunt_domain"
    ACTION_ID_HUNT_URL = "hunt_url"
    ACTION_ID_HUNT_IP = "hunt_ip"
    ACTION_ID_RUN_QUERY = "run_query"
    ACTION_ID_GET_REPORT = "get_report"

    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._api_url = None
        self._api_key = None
        self._secret = None
        self._python_version = None

    def initialize(self):
        config = self.get_config()

        # Base URL
        self._api_url = config[ISIGHTPARTNERS_JSON_API_URL]

        if self._api_url.endswith("/"):
            self._api_url = self._api_url[:-1]

        try:
            self._python_version = int(sys.version_info[0])
        except:
            return self.set_status(phantom.APP_ERROR, "Error occurred while getting the Phantom server's Python major version.")

        self._api_key = config[ISIGHTPARTNERS_JSON_API_KEY]
        self._secret = config[ISIGHTPARTNERS_JSON_SECRET]

        return phantom.APP_SUCCESS

    def _set_cef_key(self, src_dict, src_key, dst_dict, dst_key):
        src_value = phantom.get_value(src_dict, src_key)

        # Ignore if None
        if src_value is None:
            return False

        dst_dict[dst_key] = src_value

        return True

    def _get_uri(self, endpoint, query_params=None):
        if not query_params:
            return endpoint

        return endpoint + "?" + "&".join([f"{k}={v}" for k, v in query_params.items()])

    def _get_headers(self, uri, accept_header="application/json"):
        time_stamp = email.utils.formatdate()
        new_data = uri + "2.0" + accept_header + time_stamp

        # hmac does not accept unicode
        if self._python_version < 3:
            hashed = hmac.new(str(self._secret), str(new_data), hashlib.sha256)
        else:
            hashed = hmac.new(self._secret.encode("utf-8"), new_data.encode("utf-8"), hashlib.sha256)
        headers = {
            "Accept": accept_header,
            "Accept-Version": "2.0",
            "X-Auth": self._api_key,
            "X-Auth-Hash": hashed.hexdigest(),
            "X-App-Name": "phantom-isightpartners-app",
            "Date": time_stamp,
        }

        return headers

    def _get_hash_type(self, hash_val):
        hash_types = [
            {"regex": "^[0-9a-fA-F]{32}$", "hash_type": "md5"},
            {"regex": "^[0-9a-fA-F]{40}$", "hash_type": "sha1"},
            {"regex": "^[0-9a-fA-F]{64}$", "hash_type": "sha256"},
        ]

        match = [x for x in hash_types if re.match(x["regex"], hash_val)]

        if match:
            return match[0]["hash_type"]

        return None

    def _make_rest_call(self, endpoint, query_params, action_result):
        # Create the uri
        uri = self._get_uri(endpoint, query_params)

        # Create the headers
        headers = self._get_headers(uri)
        resp_json = None

        config = self.get_config()

        try:
            r = requests.get(self._api_url + uri, headers=headers, verify=config[phantom.APP_JSON_VERIFY], timeout=DEFAULT_TIMEOUT)
        except Exception as e:
            return (action_result.set_status(phantom.APP_ERROR, ISIGHTPARTNERS_ERR_SERVER_CONNECTION, e), resp_json)

        # If 204, don't even bother about parsing the reply
        if r.status_code == 204:
            action_result.set_status(phantom.APP_SUCCESS, ISIGHTPARTNERS_MSG_NO_RESULTS)
            return (phantom.APP_ERROR, resp_json)

        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            # r.text is guaranteed to be NON None, it will be empty
            msg_string = ISIGHTPARTNERS_ERR_JSON_PARSE.format(raw_text=r.text)
            return (action_result.set_status(phantom.APP_ERROR, msg_string, e), None)

        # Look for errors
        if r.status_code != requests.codes.ok:  # pylint: disable=maybe-no-member
            # init the message dict
            message = {}

            # fill it if present
            if "message" in resp_json:
                message = resp_json["message"]

            # create the string from the data that we got
            msg_string = ISIGHTPARTNERS_ERR_FROM_SERVER.format(
                error=message.get("error", "Not specified"), description=message.get("description", "Not specified")
            )

            return (action_result.set_status(phantom.APP_ERROR, msg_string), None)

        # The call was OK, return the parsed response json
        return (phantom.APP_SUCCESS, resp_json)

    def _parse_response_message_dict(self, message, summary_key, action_result):
        if not message:
            return

        # Convert the ThreatScape list to comma separated values
        message["threatscape_info"] = ",".join(message.get("ThreatScape", []))
        published_date = message["publishDate"]
        if published_date:
            message[ISIGHTPARTNERS_JSON_PUBLISHED_DATE] = time.strftime("%b %d %Y, %H:%M:%S %Z", time.localtime(published_date))
        action_result.add_data(message)

        return

    def _parse_response_message_list(self, messages, summary_key, action_result):
        if not messages:
            return

        action_result.set_summary({summary_key: len(messages)})

        for message in messages:
            self._parse_response_message_dict(message, summary_key, action_result)

    def _parse_response_message(self, resp_json, summary_key, action_result):
        if resp_json is None:
            return

        messages = resp_json.get("message")

        if messages is None:
            return

        if isinstance(messages, dict):
            return self._parse_response_message_dict(messages, summary_key, action_result)

        if isinstance(messages, list):
            return self._parse_response_message_list(messages, summary_key, action_result)

    def _hunt_domain(self, param):
        action_result = self.add_action_result(ActionResult(param))

        # Progress
        self.save_progress(ISIGHTPARTNERS_USING_API_URL, api_url=self._api_url)

        url = self._api_url
        host = url[url.find("//") + 2 :]

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, host)

        endpoint = "/search/basic"
        query_params = {"domain": param[ISIGHTPARTNERS_JSON_DOMAIN]}

        ret_val, resp_json = self._make_rest_call(endpoint, query_params, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self._parse_response_message(resp_json, ISIGHTPARTNERS_JSON_REPORTS_MATCHED, action_result)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _hunt_url(self, param):
        action_result = self.add_action_result(ActionResult(param))

        # Progress
        self.save_progress(ISIGHTPARTNERS_USING_API_URL, api_url=self._api_url)

        url = self._api_url
        host = url[url.find("//") + 2 :]

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, host)

        endpoint = "/search/basic"
        query_params = {"url": param[ISIGHTPARTNERS_JSON_URL]}

        ret_val, resp_json = self._make_rest_call(endpoint, query_params, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self._parse_response_message(resp_json, ISIGHTPARTNERS_JSON_REPORTS_MATCHED, action_result)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_report_details(self, report_id, action_result):
        endpoint = f"/report/{report_id}"

        query_params = {"detail": "full"}

        ret_val, resp_json = self._make_rest_call(endpoint, query_params, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if resp_json:
            message = resp_json.get("message")

            if message:
                action_result.add_data(message)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_report(self, param):
        action_result = self.add_action_result(ActionResult(param))

        # Progress
        self.save_progress(ISIGHTPARTNERS_USING_API_URL, api_url=self._api_url)

        url = self._api_url
        host = url[url.find("//") + 2 :]

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, host)
        report_id = param[ISIGHTPARTNERS_JSON_REPORT_ID]

        ret_val = self._get_report_details(report_id, action_result)

        if phantom.is_fail(ret_val):
            return ret_val

        if param.get(ISIGHTPARTNERS_JSON_DOWNLOAD_REPORT, False):
            ret_val = self._download_report_pdf(report_id, self.get_container_id(), action_result)
        else:
            action_result.set_status(phantom.APP_SUCCESS, ISIGHTPARTNERS_SUCC_GOT_REPORT_DETAILS)

        return ret_val

    def _hunt_ip(self, param):
        action_result = self.add_action_result(ActionResult(param))

        # Progress
        self.save_progress(ISIGHTPARTNERS_USING_API_URL, api_url=self._api_url)

        url = self._api_url
        host = url[url.find("//") + 2 :]

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, host)

        endpoint = "/search/basic"
        query_params = {"ip": param[ISIGHTPARTNERS_JSON_IP]}

        ret_val, resp_json = self._make_rest_call(endpoint, query_params, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self._parse_response_message(resp_json, ISIGHTPARTNERS_JSON_REPORTS_MATCHED, action_result)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _hunt_file(self, param):
        action_result = self.add_action_result(ActionResult(param))

        # Progress
        self.save_progress(ISIGHTPARTNERS_USING_API_URL, api_url=self._api_url)

        url = self._api_url
        host = url[url.find("//") + 2 :]

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, host)

        # get the type of hash
        hash_val = param[ISIGHTPARTNERS_JSON_HASH]
        hash_type = self._get_hash_type(hash_val)

        if hash_type is None:
            return action_result.set_status(phantom.APP_ERROR, ISIGHTPARTNERS_ERR_INVALID_HASH)

        endpoint = "/search/basic"
        query_params = {hash_type: hash_val}

        ret_val, resp_json = self._make_rest_call(endpoint, query_params, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self._parse_response_message(resp_json, ISIGHTPARTNERS_JSON_REPORTS_MATCHED, action_result)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _test_connectivity(self, param):
        # Progress
        self.save_progress(ISIGHTPARTNERS_USING_API_URL, api_url=self._api_url)

        url = self._api_url
        host = url[url.find("//") + 2 :]

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, host)

        endpoint = "/test"

        # Create the headers
        headers = self._get_headers(endpoint)

        config = self.get_config()

        try:
            r = requests.get(self._api_url + endpoint, headers=headers, verify=config[phantom.APP_JSON_VERIFY], timeout=DEFAULT_TIMEOUT)
        except Exception as e:
            self.set_status(phantom.APP_ERROR, ISIGHTPARTNERS_ERR_SERVER_CONNECTION, e)
            self.append_to_message(ISIGHTPARTNERS_ERR_CONNECTIVITY_TEST)
            return self.get_status()

        try:
            response = r.json()
        except:
            self.set_status(phantom.APP_ERROR, "Reply not a valid JSON")
            self.append_to_message(ISIGHTPARTNERS_ERR_CONNECTIVITY_TEST)
            return self.get_status()

        # Check if the key is present in the response that we got
        if "success" not in response:
            self.set_status(phantom.APP_ERROR, ISIGHTPARTNERS_ERR_REPLY_FORMAT)
            self.append_to_message(ISIGHTPARTNERS_ERR_CONNECTIVITY_TEST)
            return self.get_status()

        # key is present
        if not response["success"]:
            # Failed
            self.set_status(phantom.APP_ERROR)

            # Try to add any more info if possible
            if "message" in response:
                message = response["message"]
                self.append_to_message(
                    ISIGHTPARTNERS_ERR_FROM_SERVER.format(
                        error=message.get("error", "Not specified"), description=message.get("description", "Not specified")
                    )
                )

            # set the last message
            self.append_to_message(ISIGHTPARTNERS_MSG_SET_CORRECT_TIME)
            self.append_to_message(ISIGHTPARTNERS_ERR_CONNECTIVITY_TEST)
            return self.get_status()

        return self.set_status_save_progress(phantom.APP_SUCCESS, ISIGHTPARTNERS_SUCC_CONNECTIVITY_TEST)

    def _parse_file_node(self, file_node, artifact_id, container_id):
        if not file_node:
            return phantom.APP_ERROR

        artifact = {}
        cef = dict()

        # Each one of these will overwrite the other, if present
        self._set_cef_key(file_node, "sha1", cef, "fileHash")
        self._set_cef_key(file_node, "sha256", cef, "fileHash")
        self._set_cef_key(file_node, "md5", cef, "fileHash")

        self._set_cef_key(file_node, "fileName", cef, "fileName")
        self._set_cef_key(file_node, "fileSize", cef, "fileSize")

        if not cef:
            return None

        artifact.update(_artifact_common)
        artifact["source_data_identifier"] = artifact_id
        artifact["name"] = "File Object"
        artifact["cef"] = cef

        artifact["container_id"] = container_id

        return artifact

    def _parse_network_node(self, network_node, artifact_id, container_id):
        if not network_node:
            return phantom.APP_ERROR

        artifact = {}
        cef = dict()

        self._set_cef_key(network_node, "url", cef, "requestURL")
        self._set_cef_key(network_node, "ip", cef, "destinationAddress")
        self._set_cef_key(network_node, "domain", cef, "destinationDnsDomain")

        if "asn" in network_node:
            cef["cs1Label"] = "asn"
            cef["cs1"] = network_node["asn"]

        if not cef:
            return None

        artifact.update(_artifact_common)
        artifact["source_data_identifier"] = artifact_id
        artifact["name"] = "Network Object"
        artifact["cef"] = cef

        artifact["container_id"] = container_id

        return artifact

    def _set_artifact_label(self, report_details):
        products = []
        artifact_labels = []

        # get the list of products
        try:
            products = report_details["ThreatScape"]["product"]
        except:
            return False

        if not products:
            return False

        # stript and remove the prefix for each product
        for product in products:
            artifact_label = product.lstrip("ThreatScape").strip()

            if not artifact_label:
                continue

            artifact_labels.append(artifact_label)

        if not artifact_labels:
            return False

        # join them
        _artifact_common["label"] = ",".join(artifact_labels)

        return True

    def _parse_report(self, report_details, report_id, artifact_count):
        container_id = None

        # first save the container
        container = {}
        container.update(_container_common)
        container["source_data_identifier"] = report_id
        container["description"] += f". Generated via report: {report_id}"
        container["name"] = report_details["title"]
        container["data"] = report_details
        ret_val, response, container_id = self.save_container(container)

        self.debug_print(f"save_container returns, value: {ret_val}, reason: {response}, id: {container_id}")

        if not container_id:
            return (phantom.APP_ERROR, container_id)

        # Now download the pdf, need to do this before the artifacts are added, so that if a playbook is fired on artifact creation
        # the pdf is available on the container
        config = self.get_config()
        if config.get(ISIGHTPARTNERS_JSON_DOWNLOAD_REPORT, False):
            action_result = ActionResult()
            ret_val = self._download_report_pdf(report_id, container_id, action_result)

        # Now parse the various artifact based nodes
        tag_section = report_details.get("tagSection")
        if tag_section is None:
            self.save_progress(ISIGHTPARTNERS_MSG_NO_OBSERVABLES_FOUND)
            return (phantom.APP_SUCCESS, container_id)

        # Looks like we have data that will be converted to artifacts
        # Set the artifact label that will be used
        self._set_artifact_label(report_details)

        artifact_index = 0

        artifacts = []

        # get the files list
        files = tag_section.get("files")
        if files is not None:
            file_list = files.get("file")
            if file_list is not None:
                for file in file_list:
                    if artifact_index >= artifact_count:
                        break
                    artifact = self._parse_file_node(file, artifact_index, container_id)
                    if artifact:
                        artifacts.append(artifact)
                        artifact_index += 1

        # get the networks node
        networks = tag_section.get("networks")
        if networks is not None:
            network_list = networks.get("network")
            if network_list is not None:
                for network in network_list:
                    if artifact_index >= artifact_count:
                        break
                    artifact = self._parse_network_node(network, artifact_index, container_id)
                    if artifact:
                        artifacts.append(artifact)
                        artifact_index += 1

        if not artifacts:
            self.save_progress(ISIGHTPARTNERS_MSG_NO_OBSERVABLES_FOUND)
            return (phantom.APP_SUCCESS, container_id)

        self.save_progress(f"Created {len(artifacts)} artifacts")

        # The artifacts list will only contain the artifacts that should be added
        # Add all the artifacts except the last one
        for artifact in artifacts[:-1]:
            ret_val, status_string, artifact_id = self.save_artifact(artifact)
            self.debug_print(f"save_artifact returns, value: {ret_val}, reason: {status_string}, id: {artifact_id}")

        # Get the last one, to be handled separately, the run_automation is to be set to true
        artifact = artifacts[-1]
        artifact["run_automation"] = True
        ret_val, status_string, artifact_id = self.save_artifact(artifact)
        self.debug_print(f"save_artifact returns, value: {ret_val}, reason: {status_string}, id: {artifact_id}")

        return (phantom.APP_SUCCESS, container_id)

    def _get_str_from_epoch(self, epoch_secs):
        if not epoch_secs:
            return "Unavailable"

        # 2015-07-21T00:27:59Z
        return datetime.fromtimestamp(int(epoch_secs)).strftime("%Y-%m-%dT%H:%M:%S %Z")

    def _on_poll(self, param):
        # Get the param values
        start_time = param.get(phantom.APP_JSON_START_TIME)
        end_time = param.get(phantom.APP_JSON_END_TIME)
        container_count = int(param.get(phantom.APP_JSON_CONTAINER_COUNT, ISIGHTPARTNER_DEFAULT_CONTAINER_COUNT))
        artifact_count = int(param.get(phantom.APP_JSON_ARTIFACT_COUNT, ISIGHTPARTNER_DEFAULT_ARTIFACT_COUNT))

        if self.is_poll_now():
            end_time = int(time.mktime(datetime.utcnow().timetuple())) * 1000
            num_days = int(self.get_app_config().get(ISIGHTPARTNERS_JSON_DEF_NUM_DAYS, ISIGHTPARTNERS_NUMBER_OF_DAYS_BEFORE_ENDTIME))
            start_time = end_time - (ISIGHTPARTNERS_MILLISECONDS_IN_A_DAY * num_days)
        else:
            curr_epoch_msecs = int(time.mktime(datetime.utcnow().timetuple())) * 1000
            end_time = curr_epoch_msecs if end_time is None else int(end_time)
            num_days = int(self.get_app_config().get(ISIGHTPARTNERS_JSON_DEF_NUM_DAYS, ISIGHTPARTNERS_NUMBER_OF_DAYS_BEFORE_ENDTIME))
            start_time = end_time - (ISIGHTPARTNERS_MILLISECONDS_IN_A_DAY * num_days) if start_time is None else int(start_time)

        # validate the time
        if end_time < start_time:
            return self.set_status(phantom.APP_ERROR, ISIGHTPARTNERS_ERR_END_TIME_LT_START_TIME)

        self.debug_print(f"start_time: {start_time} end_time: {end_time}")
        start_time = start_time // 1000
        end_time = end_time // 1000
        self.debug_print(f"start_time in secs: {start_time} end_time in secs: {end_time}")

        if (end_time - start_time) > ISIGHTPARTNERS_MAX_DAYS_SECONDS:
            return self.set_status(phantom.APP_ERROR, ISIGHTPARTNERS_ERR_RANGE_MORE_THAN_MAX.format(ISIGHTPARTNERS_MAX_DAYS_RANGE))

        # Progress
        self.save_progress(ISIGHTPARTNERS_USING_API_URL, api_url=self._api_url)

        url = self._api_url
        host = url[url.find("//") + 2 :]

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, host)

        self.save_progress(
            ISIGHTPARTNERS_USING_TIMERANGE, start_time=self._get_str_from_epoch(start_time), end_time=self._get_str_from_epoch(end_time)
        )

        endpoint = "/report/index"
        query_params = {"startDate": start_time, "endDate": end_time}

        report_list_action_result = ActionResult()

        ret_val, resp_json = self._make_rest_call(endpoint, query_params, report_list_action_result)

        if phantom.is_fail(ret_val):
            self.save_progress(report_list_action_result.get_message())
            return self.set_status(report_list_action_result.get_status())

        self._parse_response_message(resp_json, ISIGHTPARTNERS_JSON_REPORTS_MATCHED, report_list_action_result)

        number_of_reports = report_list_action_result.get_data_size()

        if number_of_reports == 0:
            self.save_progress(ISIGHTPARTNERS_MSG_NO_RESULTS)
            return self.set_status(phantom.APP_SUCCESS)

        reports = report_list_action_result.get_data()

        self.save_progress(ISIGHTPARTNERS_MSG_GOT_REPORTS.format(number_of_reports=number_of_reports))

        container_id = param.get(phantom.APP_JSON_CONTAINER_ID)

        if container_id is None:
            # check if we need to sort things
            if number_of_reports > container_count:
                self.save_progress(ISIGHTPARTNERS_MSG_GETTING_MOST_N_RECENT.format(number_of_reports=container_count))
                # need to sort in order to get the latest
                reports = sorted(reports, key=itemgetter("publishDate"), reverse=True)

                # ignore the rest of the containers
                reports = reports[:container_count]
        else:
            # Need to get a specific report
            reports = [x for x in reports if x["reportId"] == container_id]
            if len(reports) == 0:
                self.save_progress(ISIGHTPARTNERS_MSG_NO_RESULTS_CONTAINER_ID)
                return self.set_status(phantom.APP_SUCCESS)
            self.save_progress(ISIGHTPARTNERS_MSG_RESULTS_CONTAINER_ID)

        # Loop through the list of reports
        for report in reports:
            report_action_result = ActionResult(report)
            report_id = report.get("reportId")
            if not report_id:
                message = "ID not found in report details."
                self.save_progress(message)
                continue

            self.save_progress(
                ISIGHTPARTNERS_MSG_GETTING_REPORT.format(report_id=report_id, published_on=self._get_str_from_epoch(report.get("publishDate")))
            )

            ret_val = self._get_report_details(report_id, report_action_result)
            if phantom.is_fail(ret_val):
                self.save_progress(ISIGHTPARTNERS_ERR_GETTING_REPORT.format(report_id=report_id, error_str=report_action_result.get_message()))
                continue

            report_data = report_action_result.get_data()

            if not report_data:
                self.debug_print("Report data is None or empty")
                self.save_progress(ISIGHTPARTNERS_ERR_REPORT_FORMAT)
                continue

            if len(report_data) != 1:
                self.debug_print(f"Len of report data is not 1, it's {len(report_data)}")
                self.save_progress(ISIGHTPARTNERS_ERR_REPORT_FORMAT)
                continue

            report_details = report_data[0].get("report")
            if report_details is None:
                self.debug_print("report details not found")
                self.save_progress(ISIGHTPARTNERS_ERR_REPORT_FORMAT)
                continue

            # Now parse it
            ret_val, container_id = self._parse_report(report_details, report_id, artifact_count)

        return self.set_status(phantom.APP_SUCCESS)

    def _normalize_reply(self, reply):
        try:
            soup = BeautifulSoup(reply, "html.parser")
            return soup.text
        except Exception as e:
            self.debug_print("Handled exception", e)
            return "Unparsable Reply. Please see the log files for the response text."

        return ""

    def _download_report_pdf(self, report_id, container_id, action_result):
        self.send_progress(ISIGHTPARTNERS_MSG_DOWNLOADING_REPORT)

        endpoint = f"/report/{report_id}"
        query_params = {"detail": "full", "format": "pdf"}

        uri = self._get_uri(endpoint, query_params)

        # Create the headers
        headers = self._get_headers(uri, accept_header="application/pdf")

        config = self.get_config()

        try:
            r = requests.get(self._api_url + uri, headers=headers, verify=config[phantom.APP_JSON_VERIFY], timeout=DEFAULT_TIMEOUT)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, ISIGHTPARTNERS_ERR_SERVER_CONNECTION, e)

        if r.status_code == 204:
            return action_result.set_status(phantom.APP_SUCCESS, ISIGHTPARTNERS_MSG_NO_RESULTS)

        if r.status_code != requests.codes.ok:  # pylint: disable=maybe-no-member
            content_type = r.headers["content-type"]

            if content_type.find("json") != -1:
                try:
                    response = r.json()
                except:
                    response = {}

                if "message" in response:
                    message = response["message"]
                    msg_string = ISIGHTPARTNERS_ERR_FROM_SERVER.format(
                        error=message.get("error", "Not specified"), description=message.get("description", "Not specified")
                    )
            else:
                msg_string = self._normalize_reply(r.text)

            self.save_progress(f"Error Downloading report. {msg_string}")

            return (action_result.set_status(phantom.APP_ERROR, msg_string), None)

        if r.status_code == requests.codes.ok:  # pylint: disable=maybe-no-member
            temp_dir = tempfile.mkdtemp()
            file_name = f"isight_report_{report_id}.pdf"
            file_path = os.path.join(temp_dir, file_name)
            with open(file_path, "wb") as f:
                f.write(r.content)

            self._move_file_to_vault(container_id, os.path.getsize(file_path), ISIGHTPARTNER_REPORT_FILE_TYPE, file_path, action_result)
            shutil.rmtree(temp_dir)

        return phantom.APP_SUCCESS

    def _move_file_to_vault(self, container_id, file_size, type_str, local_file_path, action_result):
        self.save_progress(phantom.APP_PROG_ADDING_TO_VAULT)

        # lets move the data into the vault
        vault_details = action_result.add_data({})
        if not file_size:
            file_size = os.path.getsize(local_file_path)

        vault_details[phantom.APP_JSON_SIZE] = file_size
        vault_details[phantom.APP_JSON_TYPE] = type_str
        vault_details[phantom.APP_JSON_CONTAINS] = ["pdf", type_str]
        vault_details[phantom.APP_JSON_ACTION_NAME] = self.get_action_name()
        vault_details[phantom.APP_JSON_APP_RUN_ID] = self.get_app_run_id()

        file_name = os.path.basename(local_file_path)
        success, message, vault_id = ph_rules.vault_add(
            file_location=local_file_path, container=container_id, file_name=file_name, metadata=vault_details
        )

        if success:
            vault_details[phantom.APP_JSON_VAULT_ID] = vault_id
            vault_details[phantom.APP_JSON_NAME] = file_name
            action_result.set_status(phantom.APP_SUCCESS, ISIGHTPARTNERS_SUCC_FILE_ADD_TO_VAULT, vault_id=vault_id)
        else:
            self.debug_print(f"Error Adding file to vault: success={success}, message={message}, vault_id={vault_id}")
            action_result.set_status(phantom.APP_ERROR, phantom.APP_ERR_FILE_ADD_TO_VAULT)
            action_result.append_to_message(f". {message}")

        return vault_details

    def handle_action(self, param):
        result = None
        action = self.get_action_identifier()

        if action == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            result = self._test_connectivity(param)
        elif action == self.ACTION_ID_HUNT_FILE:
            result = self._hunt_file(param)
        elif action == self.ACTION_ID_HUNT_DOMAIN:
            result = self._hunt_domain(param)
        elif action == self.ACTION_ID_HUNT_URL:
            result = self._hunt_url(param)
        elif action == self.ACTION_ID_HUNT_IP:
            result = self._hunt_ip(param)
        elif action == self.ACTION_ID_GET_REPORT:
            result = self._get_report(param)
        elif action == phantom.ACTION_ID_INGEST_ON_POLL:
            start_time = time.time()
            result = self._on_poll(param)
            end_time = time.time()
            diff_time = end_time - start_time
            human_time = str(timedelta(seconds=int(diff_time)))
            self.save_progress(f"Time taken: {human_time}")

        return result


if __name__ == "__main__":
    try:
        import simplejson as json
    except:
        pass
    import pudb

    pudb.set_trace()

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=" " * 4))

        connector = IsightpartnersConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(ret_val)

    sys.exit(0)
