# File: protectwise_connector.py
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
import json
import os
import tempfile
import time
from datetime import datetime, timedelta

import phantom.app as phantom
import phantom.rules as ph_rules
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault

from protectwise_consts import *


class RetVal2(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal2, (val1, val2))


class ProtectWiseConnector(BaseConnector):
    def __init__(self):
        # Call the super class
        super().__init__()

        self._headers = None

        self._base_url = PROTECTWISE_BASE_URL

        self._state = {}

    def is_positive_non_zero_int(self, value):
        try:
            value = int(value)
            return True if value > 0 else False
        except Exception:
            return False

    def initialize(self):
        self._state = self.load_state()
        config = self.get_config()
        self._headers = {"X-Access-Token": config[PROTECTWISE_JSON_AUTH_TOKEN]}
        self._display_dup_artifacts = config.get(PROTECTWISE_JSON_ALLOW_ARTIFACT_DUPLICATES)
        self._display_dup_containers = config.get(PROTECTWISE_JSON_ALLOW_CONTAINER_DUPLICATES)
        self._number_of_retries = config.get("retry_count", PROTECTWISE_DEFAULT_NUMBER_OF_RETRIES)
        ret_val, self._number_of_retries = self._validate_integer(
            self, self._number_of_retries, "'Maximum attempts to retry the API call in case of rate limit' asset configuration", allow_zero=True
        )
        if phantom.is_fail(ret_val):
            return self.get_status()

        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _get_sensor_list(self, action_result):
        ret_val, resp_json = self._make_rest_call("/sensors", action_result, exception_error_codes=[])

        if phantom.is_fail(ret_val):
            return (action_result.get_status(), None)

        return (phantom.APP_SUCCESS, resp_json)

    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, PROTECTWISE_ERR_INVALID_INT.format(msg="", param=key)), None

                parameter = int(parameter)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, PROTECTWISE_ERR_INVALID_INT.format(msg="", param=key)), None

            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, PROTECTWISE_ERR_INVALID_INT.format(msg="non-negative", param=key)), None
            if not allow_zero and parameter == 0:
                return action_result.set_status(phantom.APP_ERROR, PROTECTWISE_ERR_INVALID_INT.format(msg="non-zero positive", param=key)), None

        return phantom.APP_SUCCESS, parameter

    def _get_error_message_from_exception(self, e):
        """This method is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        error_code = PROTECTWISE_ERR_CODE_UNAVAILABLE
        error_msg = PROTECTWISE_ERR_MSG_UNAVAILABLE
        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except Exception as e:
            self.debug_print(f"Error occurred while fetching exception information. Details: {e!s}")

        return f"Error Code: {error_code}. Error Message: {error_msg}"

    def _get_error_details(self, resp_json):
        # The device that this app talks to does not sends back a simple message,
        # so this function does not need to be that complicated
        err_message = resp_json.get("error")
        message = "Error message is unavailable"
        if not err_message:
            return message
        return err_message.get("info", err_message.get("message", message))

    def _process_html_response(self, response, exception_error_codes, action_result):
        # An html response, is bound to be an error
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

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        # In 2.0 the platform does not like braces in messages, unless it's format parameters
        message = message.replace("{", " ").replace("}", " ")

        if status_code in exception_error_codes:
            return RetVal2(action_result.set_status(phantom.APP_SUCCESS, message), response)

        return RetVal2(action_result.set_status(phantom.APP_ERROR, message), response)

    def _process_json_response(self, response, exception_error_codes, action_result):
        # Try a json parse
        try:
            resp_json = response.json()
        except Exception as e:
            return RetVal2(
                action_result.set_status(
                    phantom.APP_ERROR, PROTECTWISE_ERR_PARSE_JSON_RESPONSE.format(self._get_error_message_from_exception(e))
                ),
                response,
            )

        if isinstance(resp_json, list):
            # Let's not parse it here
            return RetVal2(phantom.APP_SUCCESS, resp_json)

        failed = resp_json.get("failed", False)

        if failed:
            return RetVal2(
                action_result.set_status(
                    phantom.APP_ERROR, PROTECTWISE_ERR_SERVER.format(response.status_code, self._get_error_details(resp_json))
                ),
                resp_json,
            )

        if 200 <= response.status_code < 399 or response.status_code in exception_error_codes:
            return RetVal2(phantom.APP_SUCCESS, resp_json)

        return RetVal2(
            action_result.set_status(phantom.APP_ERROR, PROTECTWISE_ERR_SERVER.format(response.status_code, self._get_error_details(resp_json))),
            None,
        )

    def _process_response(self, response, exception_error_codes, action_result):
        # store the r_text in debug data, it will get dumped in the logs if an error occurs
        if hasattr(action_result, "add_debug_data"):
            if response is not None:
                action_result.add_debug_data({"r_text": response.text})
                action_result.add_debug_data({"r_headers": response.headers})
                action_result.add_debug_data({"r_status_code": response.status_code})
            else:
                action_result.add_debug_data({"r_text": "response is None"})

        self.debug_print(f"Response headers: {response.headers}")
        # There are just too many differences in the response to handle all of them in the same function
        if ("json" in response.headers.get("Content-Type", "")) or ("javascript" in response.headers.get("Content-Type")):
            return self._process_json_response(response, exception_error_codes, action_result)

        if "html" in response.headers.get("Content-Type", ""):
            return self._process_html_response(response, exception_error_codes, action_result)

        # it's not an html or json, handle if it is a successful empty response
        if ((200 <= response.status_code < 399) and (not response.text)) or response.status_code in exception_error_codes:
            return RetVal2(phantom.APP_SUCCESS, response)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            response.status_code, response.text.replace("{", " ").replace("}", " ")
        )

        return RetVal2(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, method="get", exception_error_codes=[]):
        """Function that makes the REST call to the device, generic function that can be called from various action handlers
        Needs to return two values, 1st the phantom.APP_[SUCCESS|ERROR], 2nd the response
        """
        if headers is None:
            headers = {}

        # Get the config
        config = self.get_config()

        # Create the headers
        headers.update(self._headers)

        if method in ["put", "post"]:
            headers.update({"Content-Type": "application/json"})

        # get or post or put, whatever the caller asked us to use, if not specified the default will be 'get'
        request_func = getattr(requests, method)

        # handle the error in case the caller specified a non-existant method
        if not request_func:
            action_result.set_status(phantom.APP_ERROR, PROTECTWISE_ERR_API_UNSUPPORTED_METHOD, method=method)

        self.save_progress(f"Making {method} call to {endpoint} endpoint")
        # Make the call
        for attempt_idx in range(self._number_of_retries + 1):
            try:
                r = request_func(
                    self._base_url + endpoint,  # The complete url is made up of the base_url, the api url and the endpiont
                    data=json.dumps(data) if data else None,  # the data, converted to json string format if present, else just set to None
                    headers=headers,  # The headers to send in the HTTP call
                    verify=config.get(phantom.APP_JSON_VERIFY, True),  # should cert verification be carried out?
                    params=params,
                    timeout=PROTECTWISE_DEFAULT_TIMEOUT,
                )  # uri parameters if any
            except Exception as e:
                return (action_result.set_status(phantom.APP_ERROR, PROTECTWISE_ERR_SERVER_CONNECTION, e), None)
            # The Protectwise API rate limit is 10 requests per 120 seconds, \
            # and once the limit is exceeded it throws 429 error with text response Rate limit exceeded
            # Retry wait mechanism for the rate limit exceeded error
            if r.status_code != 429:
                break
            self.save_progress("Received 429 status code from the server")
            # Don't save_progress and sleep on the last attempt
            if attempt_idx != self._number_of_retries:
                self.save_progress(f"Retrying after {PROTECTWISE_WAIT_NUMBER_OF_SECONDS} second(s)...")
                time.sleep(PROTECTWISE_WAIT_NUMBER_OF_SECONDS)
        return self._process_response(r, exception_error_codes, action_result)

    def _test_connectivity(self, param):
        self.save_progress("Attempting to connect to API endpoint...")
        self.save_progress("Querying sensor list to validate config")

        action_result = self.add_action_result(ActionResult(param))

        ret_val, resp_json = self._get_sensor_list(action_result)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_packets(self, param):
        action_result = self.add_action_result(ActionResult(param))

        packet_type = param[PROTECTWISE_JSON_TYPE]
        object_id = param[PROTECTWISE_JSON_ID]
        sensor_id = param.get(PROTECTWISE_JSON_SENSOR_ID)

        packet_type = packet_type.lower()

        if packet_type not in VALID_PROTECTWISE_TYPES:
            return action_result.set_status(phantom.APP_ERROR, "Invalid type")

        info_endpoint = f"/pcaps/{packet_type}s/{object_id}/info"
        file_endpoint = f"/pcaps/{packet_type}s/{object_id}"

        if packet_type == "observation":
            if not sensor_id:
                return action_result.set_status(phantom.APP_ERROR, f"{PROTECTWISE_JSON_SENSOR_ID} is required when type is observation")

            info_endpoint = f"/pcaps/{packet_type}s/{sensor_id}/{object_id}/info"
            file_endpoint = f"/pcaps/{packet_type}s/{sensor_id}/{object_id}"

        ret_val, file_info = self._make_rest_call(info_endpoint, action_result, exception_error_codes=[404, 505])
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if not file_info:
            return action_result.set_status(phantom.APP_SUCCESS, "File not present")

        if "not found" in file_info.get("error", {}).get("message", "").lower():
            return action_result.set_status(phantom.APP_SUCCESS, "File not present")

        action_result.add_data(file_info)

        # Now download the file
        file_name = f"{object_id}.pcap"

        if hasattr(Vault, "get_vault_tmp_dir"):
            tmp = tempfile.NamedTemporaryFile(dir=Vault.get_vault_tmp_dir())
        else:
            tmp = tempfile.NamedTemporaryFile(dir="/vault/tmp/", delete=False)

        params = {"filename": file_name}

        estimated_size = file_info.get("estimatedSize", None)

        ret_val = self._download_file(file_endpoint, action_result, tmp.name, params, estimated_size)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # MOVE the file to the vault
        vault_attach_dict = {}

        self.debug_print(f"Vault file name: {file_name}")

        vault_attach_dict[phantom.APP_JSON_ACTION_NAME] = self.get_action_name()
        vault_attach_dict[phantom.APP_JSON_APP_RUN_ID] = self.get_app_run_id()
        vault_attach_dict["contains"] = ["pcap"]

        try:
            success, message, vault_id = ph_rules.vault_add(self.get_container_id(), tmp.name, file_name, vault_attach_dict)
        except Exception as e:
            self.debug_print(phantom.APP_ERR_FILE_ADD_TO_VAULT.format(e))
            return action_result.set_status(phantom.APP_ERROR, "Failed to add the file to Vault", e)

        if not success:
            self.debug_print(f"Failed to add file to Vault: {message}")
            return action_result.set_status(phantom.APP_ERROR, f"Failed to add the file to Vault: {message}")

        action_result.set_summary({"vault_id": vault_id})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _parse_time(self, param_name, time_str, action_result):
        ret_val = None
        try:
            dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            dt_tt = dt.timetuple()
            ret_val = int(time.mktime(dt_tt)) * 1000
        except Exception as e:
            action_result.set_status(phantom.APP_ERROR, f"Unable to parse {param_name} value {time_str}, Error: {e!s}")

        return ret_val

    def _handle_time_interval(self, param, action_result):
        start_time = param.get(PROTECTWISE_JSON_START_TIME)
        end_time = param.get(PROTECTWISE_JSON_END_TIME)

        # handle the case where start time is not given and end time is given
        if start_time is None and end_time is not None:
            return (
                action_result.set_status(phantom.APP_ERROR, "Please specify start_time, it is required if end_time is specified"),
                None,
                None,
            )

        # if start time is specified, process it
        if start_time:
            start_time = self._parse_time(PROTECTWISE_JSON_START_TIME, start_time, action_result)
            if start_time is None:
                return (action_result.get_status(), None, None)

        # if end time is specified, process it
        if end_time:
            end_time = self._parse_time(PROTECTWISE_JSON_END_TIME, end_time, action_result)
            if end_time is None:
                return (action_result.get_status(), None, None)

        # if start time is not specified, get the default value
        if start_time is None:
            # get the start time to use, i.e. current - hours in seconds
            start_time = int(time.time() - (int(PROTECTWISE_N_DAYS_HOURS) * (60 * 60)))

            # convert it to milliseconds
            start_time = start_time * 1000

        # if end time is not specified, get the default value
        if end_time is None:
            end_time = self._time_now()

        if end_time <= start_time:
            return (
                action_result.set_status(phantom.APP_ERROR, "Invalid time range, end_time cannot be less than or equal to start_time"),
                None,
                None,
            )

        return (phantom.APP_SUCCESS, start_time, end_time)

    def _hunt_file(self, param):
        self.save_progress("Querying hunt file")
        action_result = self.add_action_result(ActionResult(param))

        file_hash = param[PROTECTWISE_JSON_HASH]

        ret_val, start_time, end_time = self._handle_time_interval(param, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        endpoint = f"/reputations/files/{file_hash}"

        params = {
            # 'details': 'threat,ip,domain,device',
            "start": start_time,
            "end": end_time,
        }

        ret_val, response = self._make_rest_call(endpoint, action_result, params=params, exception_error_codes=[404, 505])
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        info = response.get("info")

        summary = action_result.update_summary({})

        summary["file_type"] = info.get("type")
        summary["id"] = info.get("id")
        summary["detected_type"] = info.get("detectedType")
        summary["observation_count"] = response.get("observations", {}).get("count", 0)

        self.save_progress("Querying hunt file succeeded")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _hunt_domain(self, param):
        self.save_progress("Querying hunt domain")
        action_result = self.add_action_result(ActionResult(param))

        domain = param[PROTECTWISE_JSON_DOMAIN]

        ret_val, start_time, end_time = self._handle_time_interval(param, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        endpoint = f"/reputations/domains/{domain}"

        params = {"details": "threat,domain,device", "include": "netflows", "start": start_time, "end": end_time}

        ret_val, response = self._make_rest_call(endpoint, action_result, params=params, exception_error_codes=[404, 505])
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        domain_info = response.get("domain")
        events = response.get("threat", {}).get("events")

        summary = action_result.update_summary({})
        if domain_info:
            summary.update({"domain_organization": domain_info.get("organization", "")})
        if events:
            summary.update({"event_count": events.get("count", {}).get("total", "")})
        else:
            summary.update({"event_count": 0})

        self.save_progress("Querying hunt domain succeeded")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _hunt_ip(self, param):
        self.save_progress("Querying hunt ip")
        action_result = self.add_action_result(ActionResult(param))

        ip = param[PROTECTWISE_JSON_IP]

        ret_val, start_time, end_time = self._handle_time_interval(param, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        endpoint = f"/reputations/ips/{ip}"

        params = {"details": "threat,ip,device", "include": "netflows", "start": start_time, "end": end_time}

        ret_val, response = self._make_rest_call(endpoint, action_result, params=params, exception_error_codes=[404, 505])
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        ip_info = response.get("ip")
        events = response.get("threat", {}).get("events")

        summary = action_result.update_summary({})
        if ip_info:
            summary.update({"ip_organization": ip_info.get("organization", "")})
        if events:
            summary.update({"event_count": events.get("count", {}).get("total", "")})
        else:
            summary.update({"event_count": 0})

        self.save_progress("Querying hunt ip succeeded")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_first_start_time(self, action_result):
        config = self.get_config()

        # Get the poll hours
        poll_hours = config[PROTECTWISE_JSON_POLL_HOURS]

        if not self.is_positive_non_zero_int(poll_hours):
            self.save_progress("Please provide a positive integer in 'Ingest events in last N hours'")
            return action_result.set_status(phantom.APP_ERROR, "Please provide a positive integer in 'Ingest events in last N hours'"), None

        # get the start time to use, i.e. current - poll hours in seconds
        start_time = int(time.time() - (int(poll_hours) * (60 * 60)))

        # convert it to milliseconds
        start_time = start_time * 1000

        return phantom.APP_SUCCESS, start_time

    def _time_now(self):
        return int(time.time() * 1000)

    def _get_query_params(self, param, action_result):
        # function to separate on poll and poll now
        config = self.get_config()

        limit = config[PROTECTWISE_JSON_MAX_CONTAINERS]

        if not self.is_positive_non_zero_int(limit):
            self.save_progress("Please provide a positive integer in 'Maximum events for scheduled polling'")
            return (
                action_result.set_status(phantom.APP_ERROR, "Please provide a positive integer in 'Maximum events for scheduled polling'"),
                None,
            )

        query_params = dict()
        last_time = self._state.get(PROTECTWISE_JSON_LAST_DATE_TIME)

        if self.is_poll_now():
            limit = param.get("container_count", 100)
            ret_val, query_params["start"] = self._get_first_start_time(action_result)

            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

        elif self._state.get("first_run", True):
            self._state["first_run"] = False
            limit = config.get("first_run_max_events", 100)

            if not self.is_positive_non_zero_int(limit):
                self.save_progress("Please provide a positive integer in 'Maximum events to poll first time'")
                return (
                    action_result.set_status(phantom.APP_ERROR, "Please provide a positive integer in 'Maximum events to poll first time'"),
                    None,
                )

            ret_val, query_params["start"] = self._get_first_start_time(action_result)

            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

        elif last_time:
            query_params["start"] = last_time

        else:
            ret_val, query_params["start"] = self._get_first_start_time(action_result)

            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

        query_params["maxLimit"] = limit
        query_params["minLimit"] = limit
        query_params["end"] = self._time_now()

        if not self.is_poll_now():
            self._state[PROTECTWISE_JSON_LAST_DATE_TIME] = query_params["end"]

        return phantom.APP_SUCCESS, query_params

    def _get_artifact_name(self, observation):
        default_name = "Observation Artifact"

        try:
            return observation["data"]["idsEvent"]["description"]
        except:
            pass

        try:
            return "{} Observation from {}".format(observation["killChainStage"], observation["source"])
        except:
            pass

        try:
            return "Observation from {}".format(observation["source"])
        except:
            pass

        return default_name

    def _download_file(self, url_to_download, action_result, local_file_path, params, estimated_size=None):
        """Function that downloads the file from a url

        Args:
            url_to_download: the url of the file to download
            action_result: The ActionResult object to hold the status
            local_file_path: The local file path that was created.

        Return:
            A status code of the type phantom.APP_[SUCC|ERR]_XXX.
            The size in bytes of the file downloaded.
        """

        content_size = 0

        # Which percent chunks will the download happen for big files
        percent_block = 10

        # size that sets a file as big.
        # A big file will be downloaded in chunks of percent_block else it will be a synchronous download
        big_file_size_bytes = 20 * (1024 * 1024)

        self.save_progress(f"Downloading file from {url_to_download} to {local_file_path}")

        self.debug_print("Complete URL", url_to_download)

        try:
            r = requests.get(
                self._base_url + url_to_download, headers=self._headers, params=params, stream=True, timeout=PROTECTWISE_DEFAULT_TIMEOUT
            )
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Error downloading file", e)

        if r.status_code != requests.codes.ok:  # pylint: disable=E1101
            return action_result.set_status(phantom.APP_ERROR, f"Server returned status_code: {r.status_code}")

        # get the content length
        content_size = r.headers.get("content-length")

        if not content_size and estimated_size is not None:
            content_size = estimated_size

        if not content_size:
            return action_result.set_status(phantom.APP_ERROR, "Unable to get content length")

        self.save_progress(phantom.APP_PROG_FILE_SIZE, value=content_size, type="bytes")

        bytes_to_download = int(content_size)

        # init to download the whole file in a single read
        block_size = bytes_to_download

        # if the file is big then download in % increments
        if bytes_to_download > big_file_size_bytes:
            block_size = (bytes_to_download * percent_block) / 100

        bytes_downloaded = 0

        try:
            with open(local_file_path, "wb") as file_handle:
                for chunk in r.iter_content(chunk_size=block_size):
                    if chunk:
                        bytes_downloaded += len(chunk)
                        file_handle.write(chunk)
                        file_handle.flush()
                        os.fsync(file_handle.fileno())
                        self.send_progress(PROTECTWISE_PROG_FINISHED_DOWNLOADING_STATUS, float(bytes_downloaded) / float(bytes_to_download))
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Error downloading file", e)

        return phantom.APP_SUCCESS

    def _create_artifacts_for_event(self, event, action_result, container_index):
        artifacts = []

        observation_count = event.get("observationCount")

        if not observation_count:
            return artifacts

        event_id = event["id"]

        # we need to get the details of the event
        ret_val, resp_json = self._make_rest_call(f"/events/{event_id}", action_result)
        if phantom.is_fail(ret_val):
            return self.set_status(phantom.APP_ERROR, f"Failed to get events: {action_result.get_message()}")

        observations = resp_json.get("observations")

        if not observations:
            return artifacts

        for i, observation in enumerate(observations):
            self.send_progress(f"Processing Container # {container_index} Artifact # {i}")

            artifact = dict()

            artifact["data"] = observation
            artifact["source_data_identifier"] = observation["id"]
            artifact["name"] = self._get_artifact_name(observation)

            connection_info = observation.get("connectionInfo")

            artifact["cef"] = cef = dict()
            artifact["cef_types"] = PROTECTWISE_CEF_CONTAINS

            hashes = {}

            try:
                hashes = observation["data"]["fileReputation"]["hashes"]
            except:
                pass

            if hashes:
                # add the md5 in the hash key, everything else in it's own key
                # this is to keep things happy in 2.0 and 2.1
                if "md5" in hashes:
                    cef["fileHash"] = hashes["md5"]
                    cef["fileHashMd5"] = hashes["md5"]
                if "sha256" in hashes:
                    cef["fileHashSha256"] = hashes["sha256"]
                if "sha512" in hashes:
                    cef["fileHashSha512"] = hashes["sha512"]
                if "sha1" in hashes:
                    cef["fileHashSha1"] = hashes["sha1"]

            if connection_info:
                cef["sourceAddress"] = connection_info.get("srcIp")
                cef["destinationAddress"] = connection_info.get("dstIp")

                cef["sourcePort"] = connection_info.get("srcPort")
                cef["destinationPort"] = connection_info.get("dstPort")

                cef["sourceMacAddress"] = connection_info.get("srcMac")
                cef["destinationMacAddress"] = connection_info.get("dstMac")

                cef["transportProtocol"] = connection_info.get("layer4Proto")
                cef["observationId"] = observation["id"]
                cef["sensorId"] = observation["sensorId"]

            if self._display_dup_artifacts is True:
                cef["receiptTime"] = self._get_str_from_epoch(round(time.time() * 1000))

            artifacts.append(artifact)

        return artifacts

    def _get_str_from_epoch(self, epoch_milli):
        # 2015-07-21T00:27:59Z
        return datetime.fromtimestamp(int(epoch_milli) / 1000.0).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def _save_results(self, results):
        containers_processed = 0
        for i, result in enumerate(results):
            # result is a dictionary of a single container and artifacts
            if "container" not in result:
                continue

            if "artifacts" not in result:
                # igonore containers without artifacts
                continue

            if len(result["artifacts"]) == 0:
                # igonore containers without artifacts
                continue

            containers_processed += 1

            self.send_progress(f"Adding Container # {i}")
            ret_val, response, container_id = self.save_container(result["container"])
            self.debug_print(f"save_container returns, value: {ret_val}, reason: {response}, id: {container_id}")

            if phantom.is_fail(ret_val):
                continue

            if not container_id:
                continue

            if "artifacts" not in result:
                continue

            artifacts = result["artifacts"]

            # get the length of the artifact, we might have trimmed it or not
            len_artifacts = len(artifacts)

            for j, artifact in enumerate(artifacts):
                # if it is the last artifact of the last container
                if (j + 1) == len_artifacts:
                    # mark it such that active playbooks get executed
                    artifact["run_automation"] = True

                artifact["container_id"] = container_id
                self.send_progress(f"Adding Container # {i}, Artifact # {j}")
                ret_val, status_string, artifact_id = self.save_artifact(artifact)
                self.debug_print(f"save_artifact returns, value: {ret_val}, reason: {status_string}, id: {artifact_id}")

        return containers_processed

    def _on_poll(self, param):
        action_result = ActionResult(param)

        # Get the requests based on the type of poll
        ret_val, query_params = self._get_query_params(param, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, resp_json = self._make_rest_call("/events", action_result, params=query_params)

        if phantom.is_fail(ret_val):
            return self.set_status(phantom.APP_ERROR, f"Failed to get events: {action_result.get_message()}")

        self.save_progress("Total events: {}".format(resp_json.get("count", "NA")))

        events = resp_json.get("events", [])
        no_of_events = len(events)
        self.save_progress(f"Processing {no_of_events} events")

        results = []

        for i, event in enumerate(events):
            self.send_progress(f"Processing Container # {i}")

            container = dict()

            container["data"] = event
            container["source_data_identifier"] = event["id"]
            if self._display_dup_containers is True:
                container["source_data_identifier"] = "{} container_created:{}".format(
                    container["source_data_identifier"], self._get_str_from_epoch(round(time.time() * 1000))
                )
            container["name"] = event["message"]
            container["start_time"] = self._get_str_from_epoch(event["startedAt"])
            container["end_time"] = self._get_str_from_epoch(event["endedAt"])
            container["id"] = event["id"]

            tags = event.get("tags")
            if tags is not None:
                container["tags"] = tags.split(",")

            artifacts = self._create_artifacts_for_event(event, action_result, i)

            results.append({"container": container, "artifacts": artifacts})

        self.send_progress("Done Processing")
        self._save_results(results)

        # store the date time of the last event
        if (no_of_events) and (not self.is_poll_now()):
            config = self.get_config()

            last_date_time = events[0]["startedAt"]

            self._state[PROTECTWISE_JSON_LAST_DATE_TIME] = last_date_time

            date_strings = [x["startedAt"] for x in events]

            date_strings = set(date_strings)

            if len(date_strings) == 1:
                self.debug_print(
                    "Getting all containers with the same date, down to the millisecond."
                    " That means the device is generating"
                    f" max_containers=({config[PROTECTWISE_JSON_MAX_CONTAINERS]}) per second."
                    " Skipping to the next second to not get stuck."
                )
                self._state[PROTECTWISE_JSON_LAST_DATE_TIME] = int(self._state[PROTECTWISE_JSON_LAST_DATE_TIME]) + 1

        return self.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        action = self.get_action_identifier()

        if action == phantom.ACTION_ID_INGEST_ON_POLL:
            start_time = time.time()
            result = self._on_poll(param)
            end_time = time.time()
            diff_time = end_time - start_time
            human_time = str(timedelta(seconds=int(diff_time)))
            self.save_progress(f"Time taken: {human_time}")
        elif action == ACTION_ID_TEST_ASSET_CONNECTIVITY:
            result = self._test_connectivity(param)
        elif action == ACTION_ID_GET_PACKETS:
            result = self._get_packets(param)
        elif action == ACTION_ID_HUNT_IP:
            result = self._hunt_ip(param)
        elif action == ACTION_ID_HUNT_DOMAIN:
            result = self._hunt_domain(param)
        elif action == ACTION_ID_HUNT_FILE:
            result = self._hunt_file(param)
        else:
            action_result = ActionResult(param)
            result = action_result.set_status(phantom.APP_ERROR, f"Unsupported action: {action}")

        return result


if __name__ == "__main__":
    import argparse
    import sys

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-", "--username", help="username", required=False)
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
        login_url = BaseConnector._get_phantom_base_url() + "login"
        try:
            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=PROTECTWISE_DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=PROTECTWISE_DEFAULT_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platfrom. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = ProtectWiseConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
