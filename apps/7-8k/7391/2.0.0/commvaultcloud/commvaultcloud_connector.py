# File: commvaultcloud_connector.py
#
# Copyright (c) Commvault Systems, 2024
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

import base64
import json
import re
from datetime import datetime, timedelta

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
import commvaultcloud_consts as Constants

# Usage of the consts file is recommended


class RetVal(tuple):

    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


def if_zero_set_none(value):
    """
    If the value is zero, return None
    """
    if value and int(value) > 0:
        return value
    return None


def extract_from_regex(
        message: str, default_value: str, *regex_string_args: str) -> str:
    """
    From the message, extract the strings matching the given patterns

    Args:
        message (str): The message from which to extract.
        default_value (str): The default value to return if no match is found.
        *regex_string_args (str): Variable number of regular expressions to match.

    Returns:
        str: The extracted string if a match is found, otherwise the default value.
    """
    for pattern in regex_string_args:
        matches = re.search(pattern, message, re.IGNORECASE)
        if matches and len(matches.groups()) > 0:
            return matches.group(1).strip()
    return default_value


def format_alert_description(msg: str) -> str:
    """
    Format alert description

    Args:
        msg (str): The message containing the alert description.

    Returns:
        str: The formatted alert description.
    """
    default_value = msg

    # Check if the message contains HTML tags
    if "<html>" in msg and "</html>" in msg:
        resp = msg[msg.find("<html>") + 6: msg.find("</html>")]
        msg = resp.strip()

        # Extract the alert message if it contains specific patterns
        if "Detected " in msg and " Please click " in msg:
            msg = msg[msg.find("Detected "): msg.find(" Please click ")]
            return msg
        if "Possible " in msg and "<span style=" in msg:
            msg = msg[msg.find("Possible "): msg.find("<span style=")]
            return msg
    return default_value


def field_mapper(field_name) -> str:
    """
    Map incoming fields

    Args:
        field_name (str): Query by field name.

    Returns:
        str: Return incoming field by field name.
    """
    field_map = {
        Constants.EVENT_TIME: "timeSource",
        Constants.EVENT_ID: "id",
        Constants.ORIGINATING_PROGRAM: "subsystem",
        Constants.ANOMALY_SUB_TYPE: "AnomalyType",
        Constants.JOB: "job",
        Constants.JOB_ID: "JobId",
        Constants.ORIGINATING_CLIENT: "client",
        Constants.AFFECTED_FILES_COUNT: "SuspiciousFileCount",
        Constants.MODIFIED_FILES_COUNT: "Modified",
        Constants.RENAMED_FILES_COUNT: "Renamed",
        Constants.CREATED_FILES_COUNT: "Created",
        Constants.DELETED_FILES_COUNT: "Deleted"
    }
    return field_map[field_name]


def get_backup_anomaly(anomaly_id: int) -> str:
    """
    Get Anomaly type from anomaly id

    Args:
        anomaly_id (int): The anomaly id.

    Returns:
        str: The type of anomaly corresponding to the given id, or "Undefined" if not found.
    """
    anomaly_dict = {
        0: Constants.ANOMALY_TYPE_UNDEFINED,
        1: Constants.ANOMALY_TYPE_1,
        2: Constants.ANOMALY_TYPE_2,
        3: Constants.ANOMALY_TYPE_3,
    }
    return anomaly_dict.get(anomaly_id, Constants.ANOMALY_TYPE_UNDEFINED)


def get_unique_guid():
    """
    Generate a unique GUID.

    Returns:
        str: The unique GUID.
    """
    import random
    import string
    allowed_chars = string.ascii_letters + string.digits
    unique_id = ''.join(random.choice(allowed_chars) for i in range(16))
    return unique_id


class CommvaultCloudConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(CommvaultCloudConnector, self).__init__()
        self._last_run_epoch = None
        self._current_run_epoch = None
        self._max_fetch = None
        self._state = None
        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None
        self._access_key = None
        self._headers = list()
        self._phantom_api_token = None

    def _process_empty_response(self, response, action_result):
        """
        Process empty response

        Args:
            response: The HTTP response object.
        Returns:
            RetVal: The return value containing the status and data.
        """
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(
                phantom.APP_ERROR, "Empty response and no information in the header"
            ), None
        )

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split('\n')
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = '\n'.join(split_lines)
        except Exception:
            error_text = "Cannot parse error details"
            return None
        message = "Status Code: {0}. Data from server:\n{1}\n".format(status_code, error_text)
        message = message.replace(u'{', '{{').replace(u'}', '}}')
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, "Unable to parse JSON response. Error: {0}".format(str(e))
                ), None
            )

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(
            r.status_code,
            r.text.replace(u'{', '{{').replace(u'}', '}}')
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, 'add_debug_data'):
            action_result.add_debug_data({'r_status_code': r.status_code})
            action_result.add_debug_data({'r_text': r.text})
            action_result.add_debug_data({'r_headers': r.headers})

        # Process each 'Content-Type' of response separately
        # Process a json response
        if 'json' in r.headers.get('Content-Type', ''):
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if 'html' in r.headers.get('Content-Type', ''):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
            r.status_code,
            r.text.replace('{', '{{').replace('}', '}}')
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, headers=None, data=None, method="get"):
        # **kwargs can be any additional parameters that requests.request accepts
        config = self.get_config()
        resp_json = None
        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, "Invalid method: {0}".format(method)),
                resp_json
            )

        # # Create a URL to connect to
        url = self._base_url + endpoint
        # self.debug_print('Calling endpoint [{}]'.format(url))
        try:
            r = request_func(
                url,
                # auth=(username, password),  # basic authentication
                data=data,
                headers=self._headers,
                verify=config.get('verify_server_cert', False)
            )
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, "Error Connecting to server. Details: {0}".format(str(e))
                ), resp_json
            )
        # print('Return from rest {}'.format(self._process_response(r, action_result)))
        return self._process_response(r, action_result)

    def get_events(
            self,
            action_result,
            show_minor="false",
            show_major="true",
            show_critical="true"
    ):
        """
        Get events

        Args:
            action_result: The action result object.
            fromtime: The starting time for events.
            show_minor (str): Whether to show minor events. Default is "false".
            show_major (str): Whether to show major events. Default is "true".
            show_critical (str): Whether to show critical events. Default is "true".

        Returns:
            list: List of events if available, otherwise None.
        """
        # print('Entered get_events()')
        event_url = (
            f"/events?level=10&showInfo=false&showMinor={show_minor}&"
            f"showMajor={show_major}&showCritical={show_critical}"
        )
        current_date = datetime.utcnow()
        # print('Current date [{}]'.format(current_date))
        epoch = datetime(1970, 1, 1)
        current_epoch = int((current_date - epoch).total_seconds())
        self._current_run_epoch = current_epoch
        event_endpoint = f"{event_url}&fromTime={self._last_run_epoch}&toTime={self._current_run_epoch}"
        ret_val, response = self._make_rest_call(
            event_endpoint, action_result, method='get'
        )
        if response and response.get("commservEvents"):
            return response.get("commservEvents")
        return None

    def get_events_list(self, action_result):
        """
        Function to get events

        Args:
            action_result: The action result object.

        Returns:
            list: List of events.
        """
        events = []
        critical_events = self.get_events(action_result, show_critical="true")
        major_events = self.get_events(action_result, show_major="true")
        if critical_events is not None:
            events.extend(critical_events)
        if major_events is not None:
            events.extend(major_events)
        return events

    def get_subclient_content_list(self, action_result, subclient_id):
        """
        Get content from subclient

        Args:
            action_result: The action result object.
            subclient_id: The subclient ID.

        Returns:
            str: The content from the subclient.
        """
        ret_val, response = self._make_rest_call(
            "/Subclient/" + str(subclient_id), action_result, method='get'
        )
        response = response.get("subClientProperties", [{}])[0].get("content")
        return response

    def define_severity(self, anomaly_sub_type):
        """
        Function to get severity from anomaly sub type

        Args:
            anomaly_sub_type (str): The anomaly sub type.

        Returns:
            str: The severity.
        """
        severity = None
        if anomaly_sub_type in ("File Type", "Threat Analysis"):
            severity = Constants.SEVERITY_HIGH
        elif anomaly_sub_type == "File Activity":
            severity = Constants.SEVERITY_MEDIUM
        return severity

    def fetch_file_details(self, action_result, job_id, subclient_id, anomaly_sub_type):
        """
        Function to fetch the scanned folders list during the backup job

        Args:
            action_result: The action result object.
            job_id: The job ID.
            subclient_id: The subclient ID.
            anomaly_sub_type: The Anomaly subtype

        Returns:
            tuple: A tuple containing lists of files and folders.
        """
        self.debug_print('Fetching file details')
        folders_list = []
        if job_id is None:
            return [], []
        files_list = self.get_files_list(action_result, job_id, anomaly_sub_type)
        folder_response = self.get_subclient_content_list(action_result, subclient_id)
        if folder_response is not None:
            for resp in folder_response:
                folders_list.append(resp[Constants.PATH_KEY])
        return files_list, folders_list

    def get_incident_details(self, action_result, message: str):
        """
        Function to get incident details from the alert description

        Args:
            action_result: The action result object.
            message (str): The message containing the alert description.

        Returns:
            dict: Dictionary containing incident details.
        """
        anomaly_sub_type = extract_from_regex(
            message,
            "0",
            rf"{field_mapper('anomaly_sub_type')}:\[(.*?)\]",
        )
        if anomaly_sub_type is None or anomaly_sub_type == "0":
            return None
        anomaly_sub_type = get_backup_anomaly(int(anomaly_sub_type))
        job_id = extract_from_regex(
            message,
            "0",
            rf"{field_mapper(Constants.JOB)} \[(.*?)\]",
        )
        if job_id == "0" or job_id is None:
            job_id = extract_from_regex(
                message,
                "0",
                rf"{field_mapper(Constants.JOB_ID)}:\[(.*?)\]",
            )

        description = format_alert_description(message)
        job_details = self.get_job_details(action_result, job_id)
        if job_details is None:
            self.debug_print(f"Invalid job [{job_id}]")
            return None
        job_start_time = int(
            job_details.get("jobs", [{}])[0].get("jobSummary", {}).get("jobStartTime")
        )
        job_end_time = int(
            job_details.get("jobs", [{}])[0].get("jobSummary", {}).get("jobEndTime")
        )
        subclient_id = (
            job_details.get("jobs", [{}])[0].get("jobSummary", {}).get("subclient", {}).get("subclientId")
        )
        # to-do
        if subclient_id != 0:
            files_list, scanned_folder_list = self.fetch_file_details(action_result, job_id, subclient_id,
                                                                      anomaly_sub_type)
            if anomaly_sub_type == Constants.ANOMALY_TYPE_3 or anomaly_sub_type == Constants.ANOMALY_TYPE_2:
                self.debug_print('There are [{}] files'.format(len(files_list)))
                files_list = [d['fullPath'] for d in files_list]
        else:
            files_list, scanned_folder_list = [], []

        details = {
            "subclient_id": subclient_id,
            "files_list": files_list,
            "scanned_folder_list": scanned_folder_list,
            "anomaly_sub_type": anomaly_sub_type,
            "severity": self.define_severity(anomaly_sub_type),
            "originating_client": extract_from_regex(
                message,
                "",
                r"{} \[(.*?)\]".format(field_mapper(Constants.ORIGINATING_CLIENT)),
            ),
            "affected_files_count": if_zero_set_none(
                extract_from_regex(
                    message,
                    None,
                    r"{}:\[(.*?)\]".format(
                        field_mapper(Constants.AFFECTED_FILES_COUNT)
                    ),
                )
            ),
            "modified_files_count": if_zero_set_none(
                extract_from_regex(
                    message,
                    None,
                    r"{}FileCount:\[(.*?)\]".format(
                        field_mapper(Constants.MODIFIED_FILES_COUNT)
                    ),
                )
            ),
            "deleted_files_count": if_zero_set_none(
                extract_from_regex(
                    message,
                    None,
                    r"{}FileCount:\[(.*?)\]".format(
                        field_mapper(Constants.DELETED_FILES_COUNT)
                    ),
                )
            ),
            "renamed_files_count": if_zero_set_none(
                extract_from_regex(
                    message,
                    None,
                    r"{}FileCount:\[(.*?)\]".format(
                        field_mapper(Constants.RENAMED_FILES_COUNT)
                    ),
                )
            ),
            "created_files_count": if_zero_set_none(
                extract_from_regex(
                    message,
                    None,
                    r"{}FileCount:\[(.*?)\]".format(
                        field_mapper(Constants.CREATED_FILES_COUNT)
                    ),
                )
            ),
            "job_start_time": datetime.utcfromtimestamp(job_start_time).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "job_end_time": datetime.utcfromtimestamp(job_end_time).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "job_id": job_id,
            "external_link": extract_from_regex(
                message, "", "href='(.*?)'", 'href="(.*?)"'
            ),
            "description": description,
        }
        return details

    def get_job_details(self, action_result, job_id):
        """
        Get job details by job Id

        Args:
            action_result: The action result object.
            job_id: The job ID.

        Returns:
            dict: Dictionary containing job details.
        """
        out = None
        ret_val, response = self._make_rest_call(
            "/Job/" + str(job_id), action_result, method='get'
        )
        if ("totalRecordsWithoutPaging" in response) and (
                int(response["totalRecordsWithoutPaging"]) > 0
        ):
            out = response
        return out

    def get_files_list(self, action_result, job_id, anomaly_sub_type):
        """
        Get file list from analysis job

        Args:
            action_result: The action result object.
            job_id: The job ID.
            anomaly_sub_type: Anomaly subtype

        Returns:
            list: List of files.
        """
        file_list = []
        # print('Anomaly type [{}]'.format(anomaly_sub_type))
        if anomaly_sub_type == Constants.ANOMALY_TYPE_2:
            base_payload = Constants.ANOMALY_TYPE_2_PAYLOAD
        elif anomaly_sub_type == Constants.ANOMALY_TYPE_3:
            base_payload = Constants.ANOMALY_TYPE_3_PAYLOAD
        else:
            # print('File listing is not supporting for anomaly sub type [{}]'.format(anomaly_sub_type))
            return file_list
        # print(base_payload)
        base_payload = base64.b64decode(base_payload).decode('utf-8')
        base_payload = json.loads(base_payload)
        base_payload["advOptions"]["advConfig"]["browseAdvancedConfigBrowseByJob"]["jobId"] = int(job_id)
        # print(base_payload)
        ret_val, resp = self._make_rest_call(
            "/DoBrowse", action_result, data=json.dumps(base_payload), method='post'
        )
        if resp is None:
            return file_list
        browse_responses = resp.get("browseResponses", [])
        # print('Browse response [{}]'.format(browse_responses))
        for browse_resp in browse_responses:
            if browse_resp.get("respType") == 0:
                browse_result = browse_resp.get("browseResult")
                if "dataResultSet" in browse_result:
                    for data_result_set in browse_result.get("dataResultSet"):
                        file = {}
                        filepath = data_result_set.get("path")
                        file["sizeinkb"] = data_result_set.get("size")
                        file["folder"] = "\\".join(filepath.split("\\")[:-1])
                        file["filename"] = data_result_set.get("displayName")
                        if anomaly_sub_type == Constants.ANOMALY_TYPE_2:
                            file["fullPath"] = data_result_set.get("displayPath")
                        file_list.append(file)
        # print('File list [{}]'.format(file_list))
        return file_list

    def get_client_id(self, action_result, client_name):
        """
        Get client id from the client name

        Args:
            action_result: The action result object.
            client_name: The client name.

        Returns:
            int: The client ID.
        """
        client_id = None
        if client_name is not None:
            ret_val, resp = self._make_rest_call(
                "/GetId?clientname=" + client_name, action_result, method='get'
            )
            client_id = resp.get("clientId")
            if client_id < 0:
                client_id = 0
        return client_id

    def _fetch_incidents(
            self, action_result, max_fetch=100):
        """
        Fetch incidents

        Args:
            action_result: The action result object.

        Returns:
            list: List of incidents.
        """
        if self._max_fetch is not None:
            max_fetch = self._max_fetch
        events = self.get_events_list(action_result)
        out = []
        if not len(events) > 0:
            self.debug_print("There are no events")
            return events
        domain = 'Dummy Domain'
        events = sorted(events, key=lambda d: d.get("timeSource"))
        for event in events:
            if event.get("eventCodeString") in Constants.SUPPORTED_EVENT_CODES:
                event_id = event[
                    field_mapper(Constants.EVENT_ID)
                ]
                event_time = event[
                    field_mapper(Constants.EVENT_TIME)
                ]
                incident = {
                    "facility": Constants.FACILITY,
                    "msg": None,
                    "msg_id": None,
                    "process_id": None,
                    "sd": {},
                    "host_name": domain,
                    "timestamp": datetime.utcnow().strftime(
                        "%Y-%m-%d %H:%M:%S"),
                    "occurred": None,
                    "event_id": event_id,
                    "event_time": datetime.fromtimestamp(event_time).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "originating_program": event[
                        field_mapper(
                            Constants.ORIGINATING_PROGRAM
                        )
                    ],
                }
                det = self.get_incident_details(action_result, event[Constants.DESCRIPTION])
                if det.get(Constants.ANOMALY_SUB_TYPE, "Undefined") in ["File Type", "Threat Analysis"]:
                    incident.update(det)
                    out.append(incident)
                    if len(out) == max_fetch:
                        break
        return out

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.

        Args:
            e: Exception object

        Returns:
            str: Error message.
        """
        error_code = None
        error_msg = Constants.ERR_MSG_UNAVAILABLE

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except Exception:
            return error_code
        if not error_code:
            error_text = "Error Message: {}".format(error_msg)
        else:
            error_text = "Error Code: {}. Error Message: {}".format(error_code, error_msg)

        return error_text

    def _add_container(self, event):
        """
        Add container

        Args:
            event: The event data.

        Returns:
            str: Container ID if successful, otherwise False.
        """
        headers = {
            "ph-auth-token": self._phantom_api_token
        }
        container_id = None
        url = "{0}rest/container".format(self.get_phantom_base_url())
        container_common = {
            "description": event[Constants.DESCRIPTION],
        }
        date_obj = datetime.now()
        date_str = date_obj.strftime("%d %B, %Y, %H:%M:%S")
        post_data = container_common.copy()
        post_data['name'] = 'Suspicious File Activity Detected at {}'.format(date_str)
        post_data['source_data_identifier'] = '{}_{}'.format(event[Constants.EVENT_ID], get_unique_guid())
        post_data['label'] = Constants.CONTAINER_LABEL
        post_data['sensitivity'] = Constants.SENSITIVITY_AMBER
        post_data['severity'] = event[Constants.SEVERITY].lower()
        post_data['status'] = Constants.CONTAINER_STATUS_OPEN
        json_blob = json.dumps(post_data)
        response = requests.post(url, data=json_blob, headers=headers, verify=False)
        # print(response)
        if response is None or response.status_code != 200:
            if response is None:
                self.debug_print('Could not create container/event.')
            else:
                self.debug_print('error {} {}'.format(response.status_code, json.loads(response.text)['message']))
            return False
        container_id = response.json().get('id')
        self.debug_print('Events with container id [{}] got created successfully'.format(container_id))
        return container_id

    def _add_artifact(self, container_id, event):
        """
        Add artifact

        Args:
            container_id: The container ID.
            event: The event data.

        Returns:
            bool: True if successful, otherwise False.
        """
        headers = {
            "ph-auth-token": self._phantom_api_token
        }
        artifact_id = get_unique_guid()
        url = '{}rest/artifact'.format(self.get_phantom_base_url())
        post_data = dict()
        post_data['name'] = 'artifact for {}'.format(Constants.FACILITY)
        post_data['label'] = Constants.CONTAINER_LABEL
        post_data['container_id'] = container_id
        post_data['source_data_identifier'] = artifact_id

        cef = {
            'deviceHostname': event[Constants.ORIGINATING_CLIENT],
            'deviceFacility': event['facility'],
            'fileName': event['files_list'],
            'destinationProcessName': event[Constants.ORIGINATING_PROGRAM],
            'src': event[Constants.ANOMALY_SUB_TYPE]
        }
        data = cef.copy()
        data[Constants.AFFECTED_FILES_COUNT] = event[Constants.AFFECTED_FILES_COUNT]
        data[Constants.MODIFIED_FILES_COUNT] = event[Constants.MODIFIED_FILES_COUNT]
        data[Constants.DELETED_FILES_COUNT] = event[Constants.DELETED_FILES_COUNT]
        data[Constants.RENAMED_FILES_COUNT] = event[Constants.RENAMED_FILES_COUNT]
        data[Constants.CREATED_FILES_COUNT] = event[Constants.CREATED_FILES_COUNT]
        post_data['cef'] = cef
        post_data['data'] = data
        json_blob = json.dumps(post_data)
        r = requests.post(url, data=json_blob, headers=headers, verify=False)
        if r is None or r.status_code != 200:
            if r is None:
                self.debug_print('Could not update artifact')
            else:
                error_msg = json.loads(r.text)
                self.debug_print('error {} {}'.format(r.status_code, error_msg['message']))
            return False
        resp_data = r.json()
        if 'id' not in resp_data:
            return False
        else:
            self.debug_print('Artifact is added.')
        return True

    def _handle_disable_user(self, param):
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))
        user_id = None
        try:
            user_email = param['user_email']
            # response = self.http_request("GET", "/User?level=10")
            ret_val, response = self._make_rest_call(
                "/User?level=10", action_result, method="get"
            )
            user_list = response["users"]
            current_user = next(
                (
                    user
                    for user in user_list
                    if user.get("email") == user_email or user.get("UPN") == user_email
                ),
                None,
            )
            if current_user:
                user_id = str(current_user.get("userEntity", {}).get("userId"))
                # response = self.http_request("GET", f"/User/{user_id}")
                ret_val, response = self._make_rest_call(
                    f"/User/{user_id}", action_result, method="get"
                )
                if ret_val:
                    if response.get("users", [{}])[0].get("enableUser"):
                        # response = self.http_request("PUT", f"/User/{user_id}/Disable")
                        ret_val, response = self._make_rest_call(
                            f"/User/{user_id}/Disable", action_result, method="put"
                        )
                        if phantom.is_fail(ret_val):
                            return action_result.get_status()

                        else:
                            if response.get("response", [{}])[0].get("errorCode") > 0:
                                error_msg = "Failed to disable user"
                                raise Exception(error_msg)
                            else:
                                action_result.add_data(response)
                    else:
                        self.save_progress("User [{}] is already disabled.".format(user_email))
            else:
                raise Exception("Could not find user with email [{}]".format(user_email))
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(
                phantom.APP_ERROR, "Error while disabling user: {}".format(error_message)
            )
        self.save_progress('User {} is disabled'.format(user_email))
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Connecting to endpoint")
        # make rest call
        ret_val, response = self._make_rest_call(
            '/events?level=1', action_result
        )
        self.debug_print('ret_val returned [{}]'.format(ret_val))
        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_on_poll(self, param):
        events = list()
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )
        self._max_fetch = param.get("container_count", "")
        action_result = self.add_action_result(ActionResult(dict(param)))
        last_run = self._state.get("last_run")
        last_run = None
        if last_run is None:
            self.debug_print("Run Mode: First Scheduled Poll")
            back_fill = datetime.utcnow().astimezone() - timedelta(days=30)
            self._last_run_epoch = int(back_fill.timestamp())
        else:
            self.debug_print("Run Mode: Scheduled Poll")
            self._last_run_epoch = last_run
            self.debug_print('Got last run as [{}] from state'.format(self._last_run_epoch))
        self.debug_print('Last run state [{}]'.format(self._last_run_epoch))
        if self.is_poll_now():
            self.debug_print("Run Mode: Poll Now")
        try:
            events = self._fetch_anomalous_events(param)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(
                phantom.APP_ERROR, "Error retrieving events during poll: {}".format(error_message)
            )

        self.debug_print(f"Total events retrieved {len(events)}")
        self.save_progress(f"Total events retrieved {len(events)}")
        self.debug_print(f"Total events retrieved {len(events)}")
        try:
            self._create_container_and_artifact(events)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, error_message)
        self.save_progress("Polling complete")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _create_container_and_artifact(self, events):
        """
        Create container and artifact for each event in the list.

        Args:
            events: List of events.
        """
        for event in events:
            # self.debug_print('Processing event [{}]'.format(event))
            container_id = self._add_container(event)
            if container_id is not None:
                if self._add_artifact(container_id, event):
                    self.debug_print('Container and artifact is added')

    def _fetch_anomalous_events(self, param):
        """
        Fetch anomalous events.

        Args:
            param: The parameters.

        Returns:
            list: List of events.
        """
        events = None
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))
        events = self._fetch_incidents(action_result)
        self.debug_print('Number of filtered events are [{}]'.format(len(events)))
        return events

    def _handle_disable_data_aging(self, param):
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))
        error_msg = None
        try:
            client_name = param.get('client_name', '')
            client_id = self.get_client_id(action_result, client_name)
            if int(client_id) != 0:
                body = {
                    "clientProperties": {
                        "Client": {"ClientEntity": {"clientId": int(client_id)}},
                        "clientProps": {
                            "clientActivityControl": {
                                "activityControlOptions": [
                                    {
                                        "activityType": 16,
                                        "enableActivityType": False,
                                        "enableAfterADelay": False,
                                    }
                                ]
                            }
                        },
                    }
                }
                # print(body)
                ret_val, response = self._make_rest_call(
                    "/Client/" + str(client_id), action_result, data=json.dumps(body), method="post"
                )
                # print('Response from data aging API {}'.format(response))
                if phantom.is_fail(ret_val):
                    return action_result.get_status()
                action_result.add_data(response)
                summary = action_result.update_summary({})
                if "errorCode" in response and int(response.get("errorCode")) != 0:
                    if response.get("errorMessage"):
                        error_msg = response.get("errorMessage")
                        raise Exception(error_msg)
                    summary['status'] = 'Data aging is disabled for client [{}]'.format(client_name)
            else:
                raise Exception('Invalid client [{}]'.format(client_name))
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(
                phantom.APP_ERROR, "Error while disabling data aging: {}".format(error_message)
            )
        self.save_progress('Data aging is disabled for client [{}]'.format(client_name))
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_disable_idp(self, param):
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))
        error_msg = None
        not_enable = False
        try:
            provider_name = param.get('provider_name', '')
            ret_val, response = self._make_rest_call(
                "/V4/SAML/{}".format(provider_name), action_result, method="get"
            )
            if "error" in response:
                raise Exception(response.get('error', {}).get('errorString', ''))
            if response.get("enabled"):
                self.save_progress(f"SAML is enabled for identity server [{provider_name}]. Going to disable it")
                body = {"enabled": not_enable, "type": "SAML"}
                ret_val, response = self._make_rest_call(
                    "/V4/SAML/{}".format(provider_name), action_result, data=body, method="put"
                )
                if phantom.is_fail(ret_val):
                    return action_result.get_status()
                action_result.add_data(response)
                if response.get("errorCode"):
                    error_msg = response.get("errorCode")
                    raise Exception(error_msg)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(
                phantom.APP_ERROR, "Error while disabling provider: {}".format(error_message)
            )
        self.save_progress('Provider {} is disabled'.format(provider_name))
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS
        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()
        self.debug_print("action_id", self.get_action_identifier())
        if action_id == 'disable_user':
            ret_val = self._handle_disable_user(param)

        if action_id == 'on_poll':
            ret_val = self._handle_on_poll(param)

        if action_id == 'disable_data_aging':
            ret_val = self._handle_disable_data_aging(param)

        if action_id == 'disable_idp':
            ret_val = self._handle_disable_idp(param)

        if action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)
        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()
        # get the asset config
        config = self.get_config()
        """
        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """
        self._base_url = config.get('CommvaultEndpoint').strip()
        self._access_key = config.get('CommvaultAccessToken').strip()
        self._phantom_api_token = config.get('PhantomAPIToken').strip()
        self._headers = {
            "authtoken": 'QSDK {}'.format(self._access_key),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self._state["last_run"] = self._current_run_epoch
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

    argparser = argparse.ArgumentParser()

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)
    argparser.add_argument(
        "-v",
        "--verify",
        action="store_true",
        help="verify",
        required=False,
        default=False,
    )

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
            login_url = CommvaultCloudConnector._get_phantom_base_url() + '/login'

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken=' + csrftoken
            headers['Referer'] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = CommvaultCloudConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json['user_session_token'] = session_id
            connector._set_csrf_info(csrftoken, headers['Referer'])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)


if __name__ == '__main__':
    main()
