# File: vectrandr_utils.py
#
# Copyright (c) Vectra, 2024-2025
#
# This unpublished material is proprietary to Vectra.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Vectra.
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
import os
import time
import uuid

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.vault import Vault

import vectrandr_consts as consts


class RetVal(tuple):
    """This class returns the tuple of two elements."""

    def __new__(cls, val1, val2=None):
        """Create a new tuple object."""
        return tuple.__new__(RetVal, (val1, val2))


class VectraNDRUtils:
    """This class holds all the util methods."""

    def __init__(self, connector=None):
        """Util constructor method."""
        self._connector = connector
        self._api_token = None
        self._response_header = None
        self.file_path = None

        if connector:
            self._api_token = connector.config.get("api_token")

    def _get_error_message_from_exception(self, e):
        """Get an appropriate error message from the exception.

        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_message = consts.VECTRA_ERROR_MESSAGE_UNAVAILABLE

        self._connector.error_print("Error occurred.", e)
        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except Exception as e:
            self._connector.error_print(f"Error occurred while fetching exception information. Details: {e!s}")

        if not error_code:
            error_text = f"Error message: {error_message}"
        else:
            error_text = f"Error code: {error_code}. Error message: {error_message}"

        return error_text

    def _validate_integer(self, action_result, parameter, key, allow_zero=False, max_value=None):
        """Check if the provided input parameter value is valid.

        :param action_result: Action result or BaseConnector object
        :param parameter: Input parameter value
        :param key: Input parameter key
        :param allow_zero: Zero is allowed or not (default False)
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and parameter value itself.
        """
        try:
            if not float(parameter).is_integer():
                return action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_INVALID_INT_PARAM.format(key=key)), None

            parameter = int(parameter)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_INVALID_INT_PARAM.format(key=key)), None

        if parameter < 0:
            return action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_NEGATIVE_INT_PARAM.format(key=key)), None
        if not allow_zero and parameter == 0:
            return action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_ZERO_INT_PARAM.format(key=key)), None

        if max_value and parameter > max_value:
            return action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_MAX_INT_PARAM.format(max_value=max_value, key=key)), None

        return phantom.APP_SUCCESS, parameter

    # Parsing
    def _process_empty_response(self, response, action_result):
        """Process the empty response returned from the server.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and an empty dictionary
        """
        if response.status_code in consts.VECTRA_EMPTY_RESPONSE_STATUS_CODE:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_EMPTY_RESPONSE.format(response.status_code)))

    def _process_html_response(self, response, action_result):
        """Process the html response returned from the server.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_ERROR and the None value
        """
        # An html response, treat it like an error
        status_code = response.status_code
        if 200 <= status_code < 399:
            return RetVal(phantom.APP_SUCCESS, response.text)
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove the script, style, footer and navigation part from the HTML message
            for element in soup(["script", "style", "footer", "nav"]):
                element.extract()
            error_text = soup.text or "No data found"
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except Exception:
            error_text = "Cannot parse error details"

        message = consts.VECTRA_ERROR_GENERAL_HTML_MESSAGE.format(status_code, response.reason, error_text)
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
            return RetVal(action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_JSON_RESPONSE.format(error_message)))

        if 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        message = f"Error from server. Status code: {response.status_code}, Error message: {resp_json.get('error', resp_json)}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message))

    def _process_pcap_response(self, response, action_result):
        guid = uuid.uuid4()
        if hasattr(Vault, "get_vault_tmp_dir"):
            vault_tmp_dir = Vault.get_vault_tmp_dir().rstrip("/")
            local_dir = f"{vault_tmp_dir}/{guid}"
        else:
            local_dir = f"/opt/phantom/vault/tmp/{guid}"

        self._connector.save_progress(f"Using temp directory: {local_dir}")

        try:
            os.makedirs(local_dir)
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, "Unable to create temporary vault folder.", self._get_error_message_from_exception(e)
            )

        response_headers = response.headers
        filename = response_headers["Content-Disposition"].split("filename=")[-1]
        filename = filename.replace('"', "")
        file_path = f"{local_dir}/{filename}"
        self.file_path = file_path

        try:
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=5 * 1024 * 1024):
                    f.write(chunk)
        except Exception as e:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Unable to write file to disk. Error: {self._get_error_message_from_exception(e)}"),
                None,
            )

        if 200 <= response.status_code <= 399:
            return RetVal(phantom.APP_SUCCESS, None)

        message = "Error from server. Status Code: {} Data from server: {}".format(
            response.status_code, response.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, response, action_result, is_stream_download):
        """Process the response returned from the server.

        :param response: requests.Response object
        :param action_result: Action result or BaseConnector object
        :returns: phantom.APP_SUCCESS/phantom.APP_ERROR and the response dictionary
        """
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": response.status_code})
            if not is_stream_download:
                action_result.add_debug_data({"r_text": response.text})
            action_result.add_debug_data({"r_headers": response.headers})

        if "json" in response.headers.get("Content-Type", ""):
            return self._process_json_response(response, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in response.headers.get("Content-Type", ""):
            return self._process_html_response(response, action_result)

        if "force-download" in response.headers.get("Content-Type", ""):
            return self._process_pcap_response(response, action_result)

        # Process each 'Content-Type' of response separately
        # Process a json response
        # it's not content-type that is to be parsed, handle an empty response

        if not response.text:
            return self._process_empty_response(response, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. {}".format(
            consts.VECTRA_ERROR_GENERAL_MESSAGE.format(response.status_code, response.text.replace("{", "{{").replace("}", "}}"))
        )

        # Large HTML pages may be returned incase of 500 error from server.
        # Use default error message in place of large HTML page.
        if len(message) > 500:
            return RetVal(action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_HTML_RESPONSE))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message))

    def _common_message_handler_for_soar(self, response, operation):
        """
        Message handler.

        Parameters:
            response (object): The response object received from the API call.
            operation (str): The operation being performed.

        Returns:
            dict: The parsed response data.
        """
        data = {}
        try:
            data = json.loads(response.text)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self._connector.debug_print(f"Failed while parsing the response {error_message}")
            return data

        if isinstance(data, dict) and data.get("failed", False) and data.get("message"):
            self._connector.debug_print("Error occurred while {}: {}".format(operation, data.get("message")))

        return data

    def _get_artifact_of_container_id(self, container_id):
        """
        Retrieve the artifact associated with container.

        Args:
            container_id (str): The ID of the container.

        Returns:
            dict: A dictionary containing the artifact IDs as keys and the corresponding IDs as values.
            Returns an empty dictionary if no artifact is found.
        """
        url = consts.SPLUNK_SOAR_GET_CONTAINER_ARTIFACT_ENDPOINT.format(url=self._connector.get_phantom_base_url(), container_id=container_id)
        artifact_ids = {}
        page = 0
        while True:
            try:
                r = requests.get(url, verify=consts.VERIFY_SERVER_CERT_FAIL, params={"page": page})
            except Exception as e:
                self._connector.debug_print("Unable to query for artifact", e)
                return artifact_ids

            resp_json = self._common_message_handler_for_soar(r, "querying for artifact")

            if resp_json.get("count", 0) <= 0:
                self._connector.debug_print("No artifact matched")
                return artifact_ids

            try:
                artifact_ids.update({artifact.get("source_data_identifier"): artifact.get("id") for artifact in resp_json.get("data", [])})
            except Exception as e:
                self._connector.debug_print("Artifact results are not proper: ", e)
                return artifact_ids

            page += 1

            if page >= resp_json.get("num_pages"):
                break

        return artifact_ids

    def _delete_artifact(self, artifact_id):
        """
        Delete an artifact.

        Parameters:
            artifact_id (str): The ID of the artifact to be deleted.

        Returns:
            None
        """
        url = consts.SPLUNK_SOAR_ARTIFACT_ENDPOINT.format(url=self._connector.get_phantom_base_url(), artifact_id=artifact_id)
        self._connector.debug_print(f"Deleting artifact with id {artifact_id}")
        try:
            resp = requests.delete(url, verify=consts.VERIFY_SERVER_CERT_FAIL)
        except Exception as e:
            self._connector.debug_print("Unable to delete the artifact", e)

        self._common_message_handler_for_soar(resp, "deleting artifact")

    def _make_rest_call(self, endpoint, action_result, method="get", headers=None, params=None, **kwargs):
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

        # Create a URL to connect to
        next_page_url = kwargs.pop("next_page_url", None)
        url = next_page_url or f"{self._connector.config.get('base_url').rstrip('/')}{endpoint}"

        is_stream_download = kwargs.pop("is_stream_download", False)

        no_of_retries = consts.VECTRA_NO_OF_RETRIES

        user_agent = "VectraNDR-SplunkSOAR-{}".format(self._connector.get_app_json().get("app_version"))
        headers.update({"User-agent": user_agent})

        while no_of_retries:
            try:
                response = request_func(
                    url,
                    timeout=consts.VECTRA_REQUEST_TIMEOUT,
                    headers=headers,
                    params=params,
                    verify=self._connector.config.get("verify_server_certificate", False),
                    stream=is_stream_download,
                    **kwargs,
                )
            except Exception as e:
                error_message = self._get_error_message_from_exception(e)
                return RetVal(action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_REST_CALL.format(error_message)))

            if response.status_code not in [429, 500]:
                break

            self._connector.save_progress(f"Received {response.status_code} status code from the server")
            self._connector.save_progress(f"Retrying after {consts.VECTRA_WAIT_TIME_FOR_RETRY} second(s)...")
            time.sleep(consts.VECTRA_WAIT_TIME_FOR_RETRY)
            no_of_retries -= 1

        return self._process_response(response, action_result, is_stream_download=is_stream_download)

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

        if self._api_token:
            headers.update({"Authorization": f"Token {self._api_token}"})

        ret_val, resp_json = self._make_rest_call(endpoint, action_result, method, headers=headers, params=params, **kwargs)
        if phantom.is_fail(ret_val):
            return RetVal(action_result.get_status())

        return RetVal(phantom.APP_SUCCESS, resp_json)

    def _paginator(self, action_result, endpoint, params=None, limit=None):
        """Create an iterator that will paginate through responses from called methods.

        :param action_result: Object of ActionResult class
        :param endpoint: Endpoint for pagination
        :param params: Request parameters
        :param limit: Limit number of return items
        """
        list_items = []
        next_page_url = None

        while True:
            self._connector.debug_print(f"hitting url {endpoint}")

            ret_val, response = self._make_rest_call_helper(endpoint, action_result, method="get", params=params, next_page_url=next_page_url)
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            res_val = response.get("results")
            if res_val:
                list_items.extend(res_val)

            if limit and len(list_items) >= limit:
                list_items = list_items[:limit]
                break

            next_link = response.get("next")
            self._connector.debug_print(f"next_link url {next_link}")
            if next_link:
                next_page_url = next_link
                params.clear()
            else:
                break

        return phantom.APP_SUCCESS, list_items

    def _mark_detection(self, action_result, detection_ids, mark="True"):
        """
        Mark detection.

        Args:
            action_result (ActionResult): The result of the action.
            detection_ids (List[int]): A list of detection IDs.
            mark (str, optional): The mark to apply. Defaults to "True".

        Returns:
            Tuple[int, Any]: A tuple containing the status of the action and the response from the API.
        """
        url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_DETECTIONS_ENDPOINT}"
        payload = {"detectionIdList": detection_ids, "mark_as_fixed": mark}

        ret_val, response = self._make_rest_call_helper(url, action_result, "patch", json=payload)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, response

    def _extract_detection_id_from_entity_response(self, action_result, detection_set):
        """
        Extract detection from the entity.

        Parameters:
            action_result (ActionResult): The result of the action.
            detection_set (list): A list of URLs representing the detection set.

        Returns:
            tuple: A tuple containing the status and the list of detection IDs.
                - status (bool): The status of the operation.
                - detection_ids (list): A list of detection IDs.
        """
        try:
            detection_ids = [url.rsplit("/", 1)[1] for url in detection_set]
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Error occurred while extracting detection ids"), None
        return phantom.APP_SUCCESS, detection_ids

    def _extract_ids_from_params(self, action_result, param, ids, required=False, is_numeric=False):
        """
        Extract id from the parameter.

        Args:
            action_result (object): The result of the action.
            param (str): The name of the parameter.
            ids (str): The parameter string containing the ids.
            required (bool, optional): Whether the parameter is required. Defaults to False.
            is_numeric (bool, optional): Whether the ids are numeric. Defaults to False.

        Returns:
            tuple: A tuple containing the status and a list of extracted ids.
        """
        if is_numeric:
            ids_list = [int(id.strip()) for id in ids.split(",") if id.strip().isnumeric()]
        else:
            ids_list = [id.strip() for id in ids.split(",") if id.strip()]
        if not ids_list and required:  # If required param
            return action_result.set_status(phantom.APP_ERROR, f"Please provide a valid value in the '{param}' action parameter"), None
        return phantom.APP_SUCCESS, ids_list

    def _get_entity_related_tags(self, action_result, entity_id, entity_type):
        """
        Get the related tags for a given entity.

        Parameters:
            action_result (ActionResult): The result of the action.
            entity_id (int): The ID of the entity.
            entity_type (str): The type of the entity.

        Returns:
            tuple: A tuple containing the status of the action and a list of all related tags.
        """
        url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_ADD_REMOVE_TAGS_ENDPOINT.format(entity_type=entity_type, entity_id=entity_id)}"
        ret_val, response = self._make_rest_call_helper(url, action_result, method="get")
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        all_tags = response.get("tags", [])
        return phantom.APP_SUCCESS, all_tags

    def _add_remove_entity_related_tags(self, action_result, entity_id, entity_type, tags):
        """
        Add/remove tags from the entity.

        Parameters:
            action_result (ActionResult): The result of the action performed.
            entity_id (int): The ID of the entity to add/remove tags from.
            entity_type (str): The type of entity to add/remove tags from.
            tags (list): The list of tags to add/remove.

        Returns:
            tuple: A tuple containing the status of the action performed and the response from the Vectra platform.
        """
        url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_ADD_REMOVE_TAGS_ENDPOINT.format(entity_type=entity_type, entity_id=entity_id)}"
        payload = {"tags": tags}
        ret_val, response = self._make_rest_call_helper(url, action_result, method="patch", json=payload)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None
        return phantom.APP_SUCCESS, response

    def _get_outcome(self, action_result, outcome):
        """
        Get the outcome for a given action result.

        Parameters:
            action_result (ActionResult): The action result object.
            outcome (str): The desired outcome.

        Returns:
            tuple: A tuple containing the status code and the outcome ID if successful,
                otherwise a tuple containing the error status code, an error message, and None.
        """
        url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_OUTCOMES_ENDPOINT}"
        ret_val, response = self._paginator(action_result, url)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        outcomes_map = {result.get("title"): result.get("id") for result in response}
        if outcomes_map.get(outcome):
            return action_result.set_status(phantom.APP_SUCCESS), str(outcomes_map[outcome])

        return action_result.set_status(
            phantom.APP_ERROR, f"Invalid outcome has been provided. Please provide valid outcome value from {list(outcomes_map.keys())}"
        ), None

    def _create_critical_severity(self):
        """Create critical severity for splunk SOAR."""
        url = consts.SPLUNK_SOAR_CREATE_SEVERITY_ENDPOINT.format(url=self._connector.get_phantom_base_url())
        resp = None
        try:
            added_severity = [*consts.VECTRA_SEVERITY, {"color": "light_grey", "name": "default", "is_default": True}]
            resp = requests.post(url, verify=consts.VERIFY_SERVER_CERT_FAIL, data=json.dumps(added_severity))
            resp = requests.get(url, verify=consts.VERIFY_SERVER_CERT_FAIL)
            data = self._common_message_handler_for_soar(resp, "getting severity")
            data = data.get("data")
            vectra_sev = list()
            default_sid = None
            for item in data:
                if item.get("name", {}) in consts.DEFAULT_SEVERITY:
                    vectra_sev.append(item.get("id"))
                elif item.get("name", {}) == "default":
                    default_sid = item.get("id")
            for id in vectra_sev:
                _ = requests.delete(f"{url}/{id}", verify=consts.VERIFY_SERVER_CERT_FAIL)

            consts.VECTRA_SEVERITY[2]["is_default"] = True
            resp = requests.post(url, verify=consts.VERIFY_SERVER_CERT_FAIL, data=json.dumps(consts.VECTRA_SEVERITY))

            if default_sid:
                _ = requests.delete(f"{url}/{default_sid}", verify=consts.VERIFY_SERVER_CERT_FAIL)
        except Exception as e:
            self._connector.debug_print(f"Error occurred while calling the severity api {e!s}")
        if resp:
            self._common_message_handler_for_soar(resp, "creating severity")
