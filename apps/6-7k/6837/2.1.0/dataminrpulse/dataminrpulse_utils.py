# File: dataminrpulse_utils.py
#
# Copyright (c) 2023-2026 Dataminr
#
# This unpublished material is proprietary to Dataminr.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Dataminr.
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


import datetime
import time

import encryption_helper
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.utils import config as ph_config

import dataminrpulse_consts as consts


class RetVal(tuple):
    """This class returns the tuple of two elements."""

    def __new__(cls, val1, val2=None):
        """Create a new tuple object."""
        return tuple.__new__(RetVal, (val1, val2))


class DataminrPulseUtils:
    """This class holds all the util methods."""

    def __init__(self, connector=None):
        """Util constructor method."""
        self._connector = connector
        self._dma_token = None
        self._refresh_token = None
        self._expiration_time = 0
        self._api_version = self._connector.config.get("api_version", "v3")

        if connector:
            # Decrypt the state file
            connector.state = self._decrypt_state(connector.state)
            self._dma_token = connector.state.get(consts.DATAMINRPULSE_STATE_TOKEN, {}).get(consts.DATAMINRPULSE_STATE_DMA_TOKEN, None)
            self._refresh_token = connector.state.get(consts.DATAMINRPULSE_STATE_TOKEN, {}).get(consts.DATAMINRPULSE_STATE_REFRESH_TOKEN, None)
            self._expiration_time = connector.state.get(consts.DATAMINRPULSE_STATE_TOKEN, {}).get(consts.DATAMINRPULSE_STATE_EXPIRE, 0)

    def _get_error_message_from_exception(self, e):
        """Get an appropriate error message from the exception.

        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_msg = consts.DATAMINRPULSE_ERROR_MSG_UNAVAILABLE

        self._connector.error_print("Error occurred.", e)
        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except Exception as e:
            self._connector.error_print(f"Error occurred while fetching exception information. Details: {e!s}")

        if not error_code:
            error_text = f"Error message: {error_msg}"
        else:
            error_text = f"Error code: {error_code}. Error message: {error_msg}"

        return error_text

    # Validations
    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
        """Check if the provided input parameter value is valid.

        :param action_result: Action result or BaseConnector object
        :param parameter: Input parameter value
        :param key: Input parameter key
        :param allow_zero: Zero is allowed or not (default False)
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and parameter value itself.
        """
        try:
            if not float(parameter).is_integer():
                return action_result.set_status(phantom.APP_ERROR, consts.DATAMINRPULSE_ERROR_INVALID_INT_PARAM.format(key=key)), None

            parameter = int(parameter)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, consts.DATAMINRPULSE_ERROR_INVALID_INT_PARAM.format(key=key)), None

        if parameter < 0:
            return action_result.set_status(phantom.APP_ERROR, consts.DATAMINRPULSE_ERROR_NEGATIVE_INT_PARAM.format(key=key)), None
        if not allow_zero and parameter == 0:
            return action_result.set_status(phantom.APP_ERROR, consts.DATAMINRPULSE_ERROR_ZERO_INT_PARAM.format(key=key)), None

        return phantom.APP_SUCCESS, parameter

    # Parsing
    def _process_empty_response(self, response, action_result):
        """Process the empty response returned from the server.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and an empty dictionary
        """
        if response.status_code in consts.DATAMINRPULSE_EMPTY_RESPONSE_STATUS_CODE:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, consts.DATAMINRPULSE_ERROR_EMPTY_RESPONSE.format(response.status_code)))

    def _process_html_response(self, response, action_result):
        """Process the html response returned from the server.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_ERROR and the None value
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

        message = consts.DATAMINRPULSE_ERROR_GENERAL_MSG.format(status_code, error_text)
        message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message))

    def _process_json_response(self, response, action_result):
        """Process the json response returned from the server.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and the response dictionary
        """
        try:
            resp_json = response.json()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, consts.DATAMINRPULSE_ERROR_JSON_RESPONSE.format(error_message)))
        # Please specify the status codes here
        if 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        if "errors" in resp_json:
            error_messages = []
            for err in resp_json.get("errors", {}):
                error_code = err.get("code", "")
                error_message = err.get("message", "")
                error_messages.append(f"Error code: {error_code}. Error message: {error_message}")

            message = "Error from server. {}".format(", ".join(error_messages))

            return RetVal(action_result.set_status(phantom.APP_ERROR, message))

        if "error" in resp_json:
            error_message = resp_json.get("error", "")
            message = f"Error from server. Error message: {error_message}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, message))

        message = f"Error from server. {resp_json}"
        return RetVal(action_result.set_status(phantom.APP_ERROR, message))

    def _process_response(self, response, action_result):
        """Process the response returned from the server.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and the response dictionary
        """
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": response.status_code})
            action_result.add_debug_data({"r_text": response.text})
            action_result.add_debug_data({"r_headers": response.headers})

        # Process each 'Content-Type' of response separately
        # Process a json response
        if "json" in response.headers.get("Content-Type", ""):
            return self._process_json_response(response, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in response.headers.get("Content-Type", ""):
            return self._process_html_response(response, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not response.text:
            return self._process_empty_response(response, action_result)

        # everything else is actually an error at this point
        message = consts.DATAMINRPULSE_ERROR_GENERAL_MSG.format(response.status_code, response.text.replace("{", "{{").replace("}", "}}"))

        # Large HTML pages may be returned incase of 500 error from server.
        # Use default error message in place of large HTML page.
        if len(message) > 500:
            return RetVal(action_result.set_status(phantom.APP_ERROR, consts.DATAMINRPULSE_ERROR_HTML_RESPONSE))

        message = f"Can't process response from server. {message}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message))

    def _make_rest_call(self, url, action_result, method="get", headers=None, params=None, **kwargs):
        """Make an REST API call and passes the response to the process method.

        :param endpoint: The endpoint string to make the REST API request
        :param action_result: Action result or BaseConnector object
        :param method: The HTTP method for API request
        :param headers: The headers to pass in API request
        :param params: The params to pass in API request
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and the response dictionary returned by the process response method
        """
        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"))

        time_in_seconds_429 = 120
        time_in_seconds_500 = 15
        no_of_retries_429 = 6
        no_of_retries_500 = 3

        while no_of_retries_500 or no_of_retries_429:
            try:
                response = request_func(
                    url,
                    timeout=consts.DATAMINRPULSE_REQUEST_TIMEOUT,
                    headers=headers,
                    params=params,
                    verify=self._connector.config.get("verify_server_cert", False),
                    **kwargs,
                )
            except Exception as e:
                error_message = self._get_error_message_from_exception(e)
                return RetVal(action_result.set_status(phantom.APP_ERROR, consts.DATAMINRPULSE_ERROR_REST_CALL.format(error_message)))

            if response.status_code not in [429, 500]:
                break

            # Retry wait mechanism for the internal server error
            if response.status_code == 500:
                no_of_retries_500 -= 1
                self._connector.save_progress("Received 500 status code from the server")
                if not no_of_retries_500:
                    return self._process_response(response, action_result)
                self._connector.save_progress(f"Retrying after {time_in_seconds_500} second(s)...")
                time.sleep(time_in_seconds_500)

            # Retry wait mechanism for the rate limit exceeded error
            if response.status_code == 429:
                no_of_retries_429 -= 1
                self._connector.save_progress("Received 429 status code from the server")
                if not no_of_retries_429:
                    return self._process_response(response, action_result)
                self._connector.save_progress(f"Retrying after {time_in_seconds_429} second(s)...")
                time.sleep(time_in_seconds_429)

        return self._process_response(response, action_result)

    def _generate_token(self, action_result, refresh_token=False):
        """Generate a new dmaToken using the provided credentials and stores it to the state file.

        :param action_result: Action result or BaseConnector object
        :param refresh_token: To generate dmaToken using refresh token if marked True
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        self._connector.is_state_updated = True

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        data = {"client_id": self._connector.config["client_id"], "client_secret": self._connector.config["client_secret"]}
        if refresh_token and self._api_version == "v3":
            data.update({"refresh_token": self._refresh_token, "grant_type": "refresh_token"})
        else:
            headers.update({"X-Application-Name": "splunk_soar"})
            data.update({"grant_type": "api_key"})

        # Get the API version from the asset configuration and replace the {api_version} with the actual version
        if self._api_version == "v3":
            endpoint = consts.DATAMINRPULSE_ENDPOINT_TOKEN.format(api_version=2)
        elif self._api_version == "v4":
            endpoint = consts.DATAMINRPULSE_ENDPOINT_TOKEN.format(api_version="v1")

        if self._api_version == "v3":
            base_url = consts.DATAMINRPULSE_BASE_URL.format(api_version="gateway")
        elif self._api_version == "v4":
            base_url = consts.DATAMINRPULSE_BASE_URL.format(api_version="api")
        url = f"{base_url}{endpoint}"
        ret_val, resp_json = self._make_rest_call(url, action_result, data=data, method="post", headers=headers)

        if refresh_token:
            # If refresh token is expired, generate a new token
            msg = action_result.get_message()

            if msg and ("Invalid refresh token" in msg):
                data.clear()
                data = {
                    "client_id": self._connector.config["client_id"],
                    "client_secret": self._connector.config["client_secret"],
                    "grant_type": "api_key",
                }

                endpoint_ref = consts.DATAMINRPULSE_ENDPOINT_TOKEN.format(api_version=2)
                base_url_ref = consts.DATAMINRPULSE_BASE_URL.format(api_version="gateway")
                url_ref = f"{base_url_ref}{endpoint_ref}"
                ret_val, resp_json = self._make_rest_call(url_ref, action_result, data=data, method="post", headers=headers)

        if phantom.is_fail(ret_val):
            self._connector.state.pop(consts.DATAMINRPULSE_STATE_TOKEN, None)
            return action_result.get_status()

        try:
            self._dma_token = resp_json[consts.DATAMINRPULSE_STATE_DMA_TOKEN]
            if self._api_version == "v3":
                try:
                    self._refresh_token = resp_json[consts.DATAMINRPULSE_STATE_REFRESH_TOKEN]
                except KeyError:
                    return action_result.set_status(
                        phantom.APP_ERROR, f"Unable to retrieve refresh token for v3 API. {consts.DATAMINR_V3_V4_API_ERROR_MSG}"
                    )
            self._expiration_time = resp_json[consts.DATAMINRPULSE_STATE_EXPIRE]
        except KeyError:
            self._connector.debug_print("Unable to find the DMA Token (Authentication Token) from the returned response")
            self._connector.state.pop(consts.DATAMINRPULSE_STATE_TOKEN, None)
            return action_result.set_status(phantom.APP_ERROR, "Token generation failed")

        self._connector.state[consts.DATAMINRPULSE_STATE_TOKEN] = resp_json

        self._connector.debug_print("Token generated successfully")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _use_refresh_token(self):
        """Check if current time is about to expire, then generate token via refresh token"""
        current_datetime = datetime.datetime.now()
        current_datetime = current_datetime.replace(microsecond=0)
        current_epoch = int(current_datetime.timestamp() * 1000)

        if self._connector.state.get(consts.DATAMINRPULSE_STATE_TOKEN) and self._expiration_time:
            # We want to expire the token 30 seconds before it's expiration time to avoid rare corner cases when the token is expired,
            # but an action was just started. This 30 second buffer will help us avoid such issues.
            if (self._expiration_time - 30000) < current_epoch:  # 30s
                return False
            else:
                return True

        return False

    def _make_rest_call_helper(self, endpoint, action_result, method="get", headers=None, params=None, **kwargs):
        """Make the REST API call and generates new token if required.

        :param endpoint: The endpoint string to make the REST API request
        :param action_result: Action result or BaseConnector object
        :param method: The HTTP method for API request
        :param headers: The headers to pass in API request
        :param params: The params to pass in API request
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and the response dictionary
        """
        if not headers:
            headers = {}

        if self._dma_token:
            if self._api_version == "v4":
                headers.update({"Authorization": f"Bearer {self._dma_token}", "X-Application-Name": "splunk_soar"})
            else:
                headers.update({"Authorization": f"Dmauth {self._dma_token}"})

        if self._api_version == "v3":
            base_url = consts.DATAMINRPULSE_BASE_URL.format(api_version="gateway")
        elif self._api_version == "v4":
            base_url = consts.DATAMINRPULSE_BASE_URL.format(api_version="api")
        url = f"{base_url}{endpoint}"

        ret_val, resp_json = self._make_rest_call(url, action_result, method, headers=headers, params=params, **kwargs)

        # If token is expired, generate a new token
        msg = action_result.get_message()

        if msg and (
            "Invalid refresh token" in msg
            or "Invalid token" in msg
            or "Token has expired" in msg
            or "Token has been revoked" in msg
            or "Access token was not provided" in msg
        ):
            ret_val = self._generate_token(action_result, self._use_refresh_token())
            if phantom.is_fail(ret_val):
                return RetVal(action_result.get_status())

            if self._api_version == "v4":
                headers.update({"Authorization": f"Bearer {self._dma_token}", "X-Application-Name": "splunk_soar"})
            else:
                headers.update({"Authorization": f"Dmauth {self._dma_token}"})

            ret_val, resp_json = self._make_rest_call(url, action_result, method, headers=headers, params=params, **kwargs)
        if phantom.is_fail(ret_val):
            return RetVal(action_result.get_status())

        return RetVal(phantom.APP_SUCCESS, resp_json)

    def _get_list_id(self, action_result, all_lists=False):
        """Get the list ids of respective list names"""
        list_names = self._connector.config.get("list_names", None)
        valid_list = []

        if self._api_version == "v4":
            endpoint = consts.DATAMINRPULSE_GET_LISTS_V4
        elif self._api_version == "v3":
            endpoint = consts.DATAMINRPULSE_GET_LISTS

        ret_val, response = self._connector.util._make_rest_call_helper(endpoint, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if self._api_version == "v4":
            resp_data = response.get("lists", {})
        elif self._api_version == "v3":
            resp_data = response.get("watchlists", {})

        if list_names and not all_lists:
            # list_name may be present if a poll is configured, but if all_lists is True,
            # ignore list_name and return all list IDs
            list_names = list_names.split(",")
            for list_name in list_names:
                for _, watchlist_type in resp_data.items():
                    for list_dict in watchlist_type:
                        if list_name == list_dict["name"]:
                            valid_list.append(str(list_dict["id"]))
        else:
            # If list_names is None, empty, or all_lists is True, add all IDs from resp_data
            for _, watchlist_type in resp_data.items():
                for list_dict in watchlist_type:
                    valid_list.append(str(list_dict["id"]))

        list_id = ",".join(valid_list)
        if list_id:
            return list_id

    def _process_alert_data(self, action_result, alert):
        """
        Process alert data.

        :param action_result: Action result or BaseConnector object
        :param alerts: Alerts to process
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS with status message
        """
        container = {}
        regen_ai = False
        if self._api_version == "v4":
            if len(alert.get("intelAgents", [])) >= 1 or alert.get("liveBrief"):
                regen_ai = True
                container["name"] = "✨ " + alert.get("headline")
            else:
                container["name"] = alert.get("headline") or alert["alertId"]
            container["severity"] = alert.get("alertType", {}).get("name", "Alert")
            container["source_data_identifier"] = alert.get("linkedAlerts", [{}])[0].get("parentAlertId") or alert.get("alertId")
        elif self._api_version == "v3":
            container["name"] = alert.get("caption") or alert["alertId"]
            container["severity"] = alert.get("alertType", {}).get("name", "Alert")
            container["source_data_identifier"] = alert.get("parentAlertId") or alert["alertId"]

        ret_val, message, container_id = self._connector.save_container(container)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, message)

        if consts.DATAMINRPULSE_DUPLICATE_CONTAINER_FOUND_MSG in message.lower():
            self._connector.debug_print("Duplicate container found")
            if regen_ai:
                self._connector.debug_print("Updating existing artifacts with latest regen AI information")
                artifacts = self._get_artifacts(container_id)
                for artifact in artifacts:
                    self._update_artifact(artifact, intel_agents=alert.get("intelAgents"), live_brief=alert.get("liveBrief"))

        self._connector.debug_print("Creating alert artifacts")
        alert_artifacts = self._create_alert_artifacts(container_id, alert)

        ret_val, message, _ = self._connector.save_artifacts(alert_artifacts)
        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, message)

        return phantom.APP_SUCCESS

    def _get_artifacts(self, container_id):
        """
        Get artifacts for a container.

        :param container_id: container ID
        :return: artifacts list
        """
        response = requests.get(
            f"{self._connector.get_phantom_base_url()}/rest/container/{container_id}/artifacts",
            verify=ph_config.platform_strict_tls,
        )
        return response.json().get("data", [])

    def _update_artifact(self, artifact, intel_agents=None, live_brief=None):
        """
        Update artifact.

        :param artifact: artifact to update
        """
        artifact_id = artifact.get("id")
        if intel_agents:
            artifact["cef"]["intelAgents"] = intel_agents
        if live_brief:
            artifact["cef"]["liveBrief"] = live_brief
        response = requests.post(
            f"{self._connector.get_phantom_base_url()}/rest/artifact/{artifact_id}",
            verify=ph_config.platform_strict_tls,
            json=artifact,
        )
        return response.json()

    def _create_alert_artifacts(self, container_id, alert, artifact_id=None):
        """
        Create alert artifacts.

        :param container_id: container ID
        :param alert: alert content
        :param artifact_id: artifact ID
        :return: extracted artifacts list
        """
        artifacts = []

        alert_artifact = {}
        alert_artifact["severity"] = alert.get("alertType", {}).get("name", "Alert")
        alert_artifact["label"] = "alert"
        alert_artifact["name"] = "Alert Artifact"
        alert_artifact["container_id"] = container_id

        if alert.get("alertId"):
            artifact_id = alert["alertId"]

            # Set alert artifact contains
            alert_artifact["cef_types"] = {
                "alertId": ["dataminrpulse alert id"],
                "parentAlertId": ["dataminrpulse alert id"],
                "eventMapLargeURL": ["url"],
                "eventMapSmallURL": ["url"],
                "url": ["url"],
                "relatedTermsQueryURL": ["url"],
                "expandAlertURL": ["url"],
                "expandMapURL": ["url"],
            }

        alert_artifact["source_data_identifier"] = artifact_id
        alert_artifact["data"] = alert.get("metadata", {})

        alert_artifact["cef"] = self._add_cef(alert)

        if alert_artifact["cef"].get("eventTime"):
            event_time = alert_artifact["cef"]["eventTime"]
            alert_artifact["cef"]["eventTime"] = self._epoch_to_utc(event_time)

        if alert_artifact["cef"].get("post", {}).get("timestamp"):
            timestamp = alert_artifact["cef"]["post"]["timestamp"]
            alert_artifact["cef"]["post"]["timestamp"] = self._epoch_to_utc(timestamp)

        # Create artifacts for all cyber values
        cyber_dict = alert.get("metadata", {}).get("cyber", {})
        if cyber_dict:
            for cyber_key, _ in cyber_dict.items():
                cyber_values = self._extract_cyber_values(alert, cyber_key)
                for cyber_value in cyber_values:
                    cyber_artifact = {}

                    cyber_artifact["name"] = f"{cyber_key.capitalize()} Artifact"
                    cyber_artifact["label"] = "artifact"
                    cyber_artifact["cef"] = cyber_value
                    cyber_artifact["container_id"] = container_id
                    cyber_artifact["severity"] = alert.get("alertType", {}).get("name", "Alert")
                    cyber_artifact["source_data_identifier"] = artifact_id
                    # Set the contains
                    cyber_artifact["cef_types"] = {"ip": ["ip"], "value": ["hash", "md5", "sha1", "sha256"], "asn": ["asn"]}
                    artifacts.append(cyber_artifact)

        artifacts.append(alert_artifact)

        return artifacts

    def _epoch_to_utc(self, parameter):
        """Convert epoch to datetime in UTC format"""
        parameter = datetime.datetime.utcfromtimestamp(int(parameter) / 1000).strftime("%Y-%m-%d %H:%M:%S")
        parameter = "{} {}".format(parameter, "UTC")
        return parameter

    def _add_cef(self, alert):
        """Add cef data to alert artifact preserving original structure."""
        cef = {}

        for key, value in alert.items():
            self._connector.debug_print(f"Adding CEF data to alert artifact for key: {key}")
            try:
                # Include all key-value pairs as they are without modification
                if key == "metadata":
                    self._connector.debug_print(f"upating value form dict to list of dict: {key}")
                    value = [value]
                cef[key] = value
            except Exception:
                self._connector.debug_print(f"Exception occurred for {key} while adding CEF data to alert artifact")
                cef[key] = value

        return cef

    def _add_list_value_to_cef(self, cef, key, value):
        """Add values to CEF if it is list of dictionaries."""
        index_watchlist = 0
        index_category = 0
        index_sector = 0
        index_company = 0
        for value_dict in value:
            if isinstance(value_dict, dict):
                if key == "watchlistsMatchedByType":
                    index_watchlist = index_watchlist + 1
                    cef[key][f"watchlist name {index_watchlist}"] = value_dict["name"]

                elif key == "categories":
                    index_category = index_category + 1
                    cef[key][f"category {index_category}"] = value_dict["name"]

                elif key == "sectors":
                    index_sector = index_sector + 1
                    cef[key][f"sector {index_sector}"] = value_dict["name"]

                elif key == "companies":
                    index_company = index_company + 1
                    cef[key][f"company {index_company}"] = value_dict["name"]

                elif key == "relatedTerms":
                    cef[key][value_dict["text"]] = value_dict["url"]

                else:
                    cef[key] = value_dict

            else:
                cef[key] = value
        return

    def _extract_cyber_values(self, file_data, cyber_key):
        """Extract values from each key of cyber dictionary to create artifacts."""
        cyber_values = []
        file_data = file_data.get("metadata", {}).get("cyber", {}).get(cyber_key, [])
        for data in file_data:
            if data and isinstance(data, dict):
                # Handle key mapping for addresses (ip -> sourceAdress and name -> requestURL)
                if cyber_key == "addresses" and "ip" in data:
                    updated_data = data.copy()
                    updated_data["sourceAddress"] = updated_data.pop("ip")
                    cyber_values.append(updated_data)
                elif cyber_key == "URL" and "name" in data:
                    updated_data = data.copy()
                    updated_data["requestURL"] = updated_data.pop("name")
                    cyber_values.append(updated_data)
                else:
                    cyber_values.append(data)
            elif data and isinstance(data, str):
                if cyber_key == "URLs" or cyber_key == "URL":
                    cyber_values.append({"requestURL": data})
                elif cyber_key == "hashes":
                    cyber_values.append({"fileHash": data})
                elif cyber_key == "asns":
                    cyber_values.append({"asn": data})
                elif cyber_key == "addresses":
                    cyber_values.append({"SourceAddress": data})
                else:
                    cyber_values.append({cyber_key: data})

        return cyber_values

    def _encrypt_state(self, state):
        """Encrypt the state file.

        :param state: state dictionary to be encrypted
        :return: state dictionary with encrypted token
        """
        dma_token = state.get(consts.DATAMINRPULSE_STATE_TOKEN, {}).get(consts.DATAMINRPULSE_STATE_DMA_TOKEN)
        refresh_token = state.get(consts.DATAMINRPULSE_STATE_TOKEN, {}).get(consts.DATAMINRPULSE_STATE_REFRESH_TOKEN)
        try:
            if dma_token:
                state[consts.DATAMINRPULSE_STATE_TOKEN][consts.DATAMINRPULSE_STATE_DMA_TOKEN] = encryption_helper.encrypt(
                    dma_token, self._connector.get_asset_id()
                )
            if refresh_token:
                state[consts.DATAMINRPULSE_STATE_TOKEN][consts.DATAMINRPULSE_STATE_REFRESH_TOKEN] = encryption_helper.encrypt(
                    refresh_token, self._connector.get_asset_id()
                )
        except Exception as e:
            self._connector.debug_print("Error occurred while encrypting the state file.", e)
            state.pop(consts.DATAMINRPULSE_STATE_TOKEN, None)
        return state

    def _decrypt_state(self, state):
        """Decrypt the state file.

        :param state: state dictionary to be decrypted
        :return: state dictionary with decrypted token
        """
        dma_token = state.get(consts.DATAMINRPULSE_STATE_TOKEN, {}).get(consts.DATAMINRPULSE_STATE_DMA_TOKEN)
        refresh_token = state.get(consts.DATAMINRPULSE_STATE_TOKEN, {}).get(consts.DATAMINRPULSE_STATE_REFRESH_TOKEN)
        try:
            if dma_token:
                state[consts.DATAMINRPULSE_STATE_TOKEN][consts.DATAMINRPULSE_STATE_DMA_TOKEN] = encryption_helper.decrypt(
                    dma_token, self._connector.get_asset_id()
                )
            if refresh_token:
                state[consts.DATAMINRPULSE_STATE_TOKEN][consts.DATAMINRPULSE_STATE_REFRESH_TOKEN] = encryption_helper.decrypt(
                    refresh_token, self._connector.get_asset_id()
                )
        except Exception as e:
            self._connector.debug_print("Error occurred while decrypting the state file.", e)
            state.pop(consts.DATAMINRPULSE_STATE_TOKEN, None)
        return state
