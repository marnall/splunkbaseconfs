# File: fireeyeetp_connector.py
#
# Copyright (c) Robert Drouin, 2021-2025
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

import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timedelta
from urllib.parse import unquote

import phantom.app as phantom
import pytz
import requests
from bs4 import BeautifulSoup
from phantom import vault
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
from fireeyeetp_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class FireeyeEtpConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None
        self._verify_server_cert = True

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = None
        error_msg = ERR_MSG_UNAVAILABLE

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except Exception:
            pass

        if not error_code:
            error_text = f"Error Message: {error_msg}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_msg}"

        return error_text

    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
        """This method is to check if the provided input parameter value
        is a non-zero positive integer and returns the integer value of the parameter itself.
        :param action_result: Action result or BaseConnector object
        :param parameter: input parameter
        :param key: action parameter key
        :param allow_zero: action parameter allowed zero value or not
        :return: integer value of the parameter or None in case of failure
        """

        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, VALID_INTEGER_MSG.format(key)), None

                parameter = int(parameter)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, VALID_INTEGER_MSG.format(key)), None

            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, NON_NEGATIVE_INTEGER_MSG.format(key)), None

            if not allow_zero and parameter == 0:
                return action_result.set_status(phantom.APP_ERROR, POSITIVE_INTEGER_MSG.format(key)), None

        return phantom.APP_SUCCESS, parameter

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200 or response.status_code == 204:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(
                phantom.APP_ERROR, f"Status Code: {response.status_code}. Error: Empty response and no information in the header"
            ),
            None,
        )

    def _process_html_response(self, response, action_result):
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

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"
        message = unquote(message)

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            err = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {err}"), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_file_response(self, r, action_result):
        # Try to parse the file data with the .content
        try:
            resp_json = r.content
        except Exception as e:
            err = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse response. Error: {err}"), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Check to see if we are downloading a file.
        # Files are still showing a Content-Type of JSON although there is no JSON data.
        if r.headers.get("Content-Disposition"):
            return self._process_file_response(r, action_result)

        # Process each 'Content-Type' of response separately

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

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        try:
            # Create a URL to connect to
            url = f"{self._base_url}{endpoint}"
        except Exception:
            err = "Please provide valid asset configuration and|or the action parameters"
            return RetVal(action_result.set_status(phantom.APP_ERROR, err), resp_json)
        try:
            r = request_func(url, verify=self._verify_server_cert, headers=self._header, **kwargs)
        except requests.exceptions.InvalidSchema:
            err = f"Error connecting to server. No connection adapters were found for {url}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, err), resp_json)
        except requests.exceptions.InvalidURL:
            err = f"Error connecting to server. Invalid URL {url}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, err), resp_json)
        except Exception as e:
            err = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {err}"), resp_json)

        return self._process_response(r, action_result)

    def _save_file_to_vault(self, data, filename, container_id, action_result):
        # Creating temporary directory and file
        try:
            if hasattr(vault, "get_vault_tmp_dir"):
                temp_dir = vault.get_vault_tmp_dir()
            else:
                temp_dir = "/opt/phantom/vault/tmp/"

            temp_dir = f"{temp_dir}/{uuid.uuid4()}"

            os.makedirs(temp_dir)

            file_path = os.path.join(temp_dir, filename)

            with open(file_path, "wb") as file_obj:
                file_obj.write(data)
        except Exception as e:
            err = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, "Error while writing to temporary file", err), None

        # Adding pcap to vault
        success, message, vault_id = vault.vault_add(container_id, file_path, filename)

        # Removing temporary directory created to download file
        try:
            os.rmdir(temp_dir)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Unable to remove temporary directory"), None

        # Updating data with vault details
        if success:
            vault_details = {phantom.APP_JSON_VAULT_ID: vault_id, "file_name": filename}
            return phantom.APP_SUCCESS, vault_details

        # Error while adding report to vault
        self.debug_print(f"Error adding file to vault: {message}")
        action_result.append_to_message(f". {message}")

        # Set the action_result status to error, the handler function will most probably return as is
        return phantom.APP_ERROR, None

    def _paginator(self, endpoint, action_result, data, method="get", **kwargs):
        """This function is used to handle the gathering of alerts for the list alerts action.
            Note: the parameters need to be valid Python Requests parameters

        :param endpoint: API endpoint to use to get the alerts
        :param action results: Action results for Phantom
        :param data: dict of parameters to send to the API endpoint
        :param method: HTTP method to use when calling the API endpoint
        :param **kwargs: Optional and additional arguments to use for calling the API endpoint.
        :return: a list of alerts
        """
        items_list = list()

        while True:
            ret_val, items = self._make_rest_call(endpoint, action_result, json=data, method=method, **kwargs)

            if phantom.is_fail(ret_val):
                return action_result.get_status(), None
            else:
                try:
                    limit = items.get("meta", {}).get("total") - len(items_list)
                except Exception:
                    return action_result.set_status(phantom.APP_ERROR, "Unable to process response"), None

            if items.get("data"):
                for item in items.get("data"):
                    items_list.append(item)
            else:
                break

            try:
                if limit and items.get("meta", {}).get("total") >= limit:
                    if endpoint == FIREETEETP_LIST_ALERTS_ENDPOINT:
                        data["fromLastModifiedOn"] = items.get("meta", {}).get("fromLastModifiedOn", {}).get("end")
                    elif endpoint == FIREEYEETP_LIST_QUARANTINED_EMAILS_ENDPOINT:
                        data["attributes"]["date"]["to_date"] = items.get("meta", {}).get("timestamp_quarantine")
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Unable to process response"), None

            if limit <= 0:
                break

        return phantom.APP_SUCCESS, items_list

    def _paginator2(self, endpoint, action_result, data, limit=None, method="get", **kwargs):
        """This function is used to handle the gathering of alerts for the on_poll action.
            Note: these parameters need to be valid Python Requests parameters

        :param endpoint: API endpoint to use to get the alerts
        :param action results: Action results for Phantom
        :param data: dict of parameters to send to the API endpoint
        :param limit: The number of alerts to ingest
        :param method: HTTP method to use when calling the API endpoint
        :param **kwargs: Optional and additional arguments to use for calling the API endpoint.
        :return: a list of alerts
        """

        items_list = list()

        while limit > 0:
            ret_val, items = self._make_rest_call(endpoint, action_result, json=data, method=method, **kwargs)

            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            if items.get("data"):
                for item in items.get("data"):
                    items_list.append(item)
            else:
                break

            try:
                if limit and items.get("meta", {}).get("total") >= limit:
                    limit = limit - items.get("meta", {}).get("total")
                    data["fromLastModifiedOn"] = items.get("meta", {}).get("fromLastModifiedOn", {}).get("end")

                if items.get("meta", {}).get("total") < limit:
                    break
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Unable to access attributes of items response"), None

        return phantom.APP_SUCCESS, items_list

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        # NOTE: test connectivity does _NOT_ take any parameters
        # i.e. the param dictionary passed to this handler will be empty.
        # Also typically it does not add any data into an action_result either.
        # The status and progress messages are more important.

        self.save_progress("Connecting to endpoint")

        data = {}

        data["size"] = 1

        endpoint = FIREETEETP_LIST_ALERTS_ENDPOINT

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, method="post", data=data)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_alerts(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        data = {}
        data["attributes"] = {}

        # Check the 'size' parameter
        ret_val, size = self._validate_integer(action_result, param.get("size"), SIZE_KEY)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        if size > 200:
            size = 200
        data["size"] = size

        # Check the 'legacy_id' parameter
        ret_val, legacy_id = self._validate_integer(action_result, param.get("legacy_id"), LEGACY_ID_KEY, True)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        if legacy_id:
            data["attributes"]["legacy_id"] = legacy_id

        # Check the message id parameter
        message_id_param = param.get("message_id")
        if message_id_param:
            data["attributes"]["etp_message_id"] = message_id_param

        # Check the email status parmater
        email_status_param = param.get("email_status")
        if email_status_param:
            data["attributes"]["email_status"] = email_status_param

        # Check the 'num_days' parameter
        ret_val, num_days = self._validate_integer(action_result, param.get("num_days"), NUM_DAYS_KEY, True)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        # Check and calculate the timestamp to filter by
        try:
            if num_days:
                timestamp = datetime.utcnow() - timedelta(days=num_days)
                date = timestamp.strftime("%Y-%m-%dT%H:%M:%S.000")
                data["fromLastModifiedOn"] = date
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'num_days' action parameter")

        endpoint = FIREETEETP_LIST_ALERTS_ENDPOINT

        # make rest call
        ret_val, response = self._paginator(endpoint, action_result, data, method="post")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        if isinstance(response, list):
            for alert in response:
                action_result.add_data(alert)
        else:
            action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_alert(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            endpoint = FIREETEETP_GET_ALERT_ENDPOINT.format(alertId=param.get("alert_id"))
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'alert_id' action parameter")

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_email_attributes(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        data = {}

        # Check the 'size' parameter
        ret_val, size = self._validate_integer(action_result, param.get("size"), SIZE_KEY)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        if size > 200:
            size = 200
        data["size"] = size
        endpoint = FIREETEETP_LIST_MESSAGE_ATTRIBUTES_ENDPOINT

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, json=data, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_email_attributes(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        etp_message_id_param = param["etp_message_id"]
        try:
            endpoint = FIREETEETP_GET_MESSAGE_ATTRIBUTES_ENDPOINT.format(etp_message_id=etp_message_id_param)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'etp_message_id' action parameter")

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_trace_message(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        params = {}
        original_message_id_param = param.get("original_message_id")
        if original_message_id_param:
            params["original_message_id"] = original_message_id_param

        downstream_message_id_param = param.get("downstream_message_id")
        if downstream_message_id_param:
            params["downstream_message_id"] = downstream_message_id_param

        # Check the 'size' parameter
        ret_val, size = self._validate_integer(action_result, param.get("size"), SIZE_KEY, True)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        if size > 300:
            size = 300
        params["size"] = size

        endpoint = FIREETEETP_GET_MESSAGE_TRACE_ENDPOINT

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_trace_email(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        params = {"attributes": {}}
        modified_date_param = param.get("modified_date")

        if modified_date_param:
            # Make sure the datetime supplied is a valid
            try:
                lastModifiedDateTime = modified_date_param.strip()
                lastModifiedDateTime = datetime.strptime(lastModifiedDateTime, "%Y-%m-%dT%H:%M:%S")
                params["attributes"]["lastModifiedDateTime"] = {"value": lastModifiedDateTime.strftime("%Y-%m-%dT%H:%M:%S"), "filter": ">="}
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, ERR_ISO_FORMAT.format("modified_date"))

        recipients_param = param.get("recipients")
        if recipients_param:
            try:
                recipients = [x.strip() for x in recipients_param.split(",")]
                recipients = [_f for _f in recipients if _f]
                if not recipients:
                    return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'recipients' action parameter")
                params["attributes"]["recipients"] = {"value": recipients, "filter": "in", "includes": ["SMTP", "HEADER"]}
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'recipients' action parameter")

        sender_param = param.get("sender")
        if sender_param:
            try:
                sender = [x.strip() for x in sender_param.split(",")]
                sender = [_f for _f in sender if _f]
                if not sender:
                    return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'sender' action parameter")
                params["attributes"]["fromEmail"] = {"value": sender, "filter": "in", "includes": ["SMTP", "HEADER"]}
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'sender' action parameter")

        status_param = param.get("status")
        if status_param:
            try:
                status = [x.strip() for x in status_param.split(",")]
                status = [_f for _f in status if _f]
                if not status:
                    return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'status' action parameter")
                params["attributes"]["status"] = {"value": status, "filter": "in"}
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'status' action parameter")

        tags_param = param.get("tags")
        if tags_param:
            try:
                tags = [x.strip() for x in tags_param.split(",")]
                tags = [_f for _f in tags if _f]
                if not tags:
                    return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'tags' action parameter")
                params["attributes"]["tags"] = {"value": tags, "filter": "in"}
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'tags' action parameter")

        subject_param = param.get("subject")
        if subject_param:
            subject = subject_param.strip()
            params["attributes"]["subject"] = {"value": [subject], "filter": "in"}

        # Check the 'domain' parameter
        domains_param = param.get("domains")
        if domains_param:
            try:
                domains = [x.strip() for x in domains_param.split(",")]
                domains = [_f for _f in domains if _f]
                if not domains:
                    return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'domains' action parameter")
                params["attributes"]["domains"] = domains
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'domains' action parameter")

        # Check the 'size' parameter
        ret_val, size = self._validate_integer(action_result, param.get("size"), SIZE_KEY, True)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        if size > 300:
            size = 300
        params["size"] = size

        endpoint = FIREETEETP_LIST_MESSAGE_ATTRIBUTES_ENDPOINT

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, method="post", json=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_download_email(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        etp_message_id_param = param["etp_message_id"]

        # Set the file name for the vault
        try:
            filename = f"raw_email_{etp_message_id_param}.txt"
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'etp_message_id' action parameter")

        endpoint = FIREETEETP_GET_EMAIL_ENDPOINT.format(etp_message_id=etp_message_id_param)

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, vault_details = self._save_file_to_vault(response, filename, self.get_container_id(), action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_download_pcap(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        alert_id_param = param["alert_id"]

        data = {}

        # Set the file name for the vault
        try:
            filename = f"{alert_id_param}_pcap.zip"
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'alert_id' action parameter")

        endpoint = FIREETEETP_GET_ALERT_PCAP_FILES_ENDPOINT.format(alertId=alert_id_param)

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, method="post", json=data, stream=True)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, vault_details = self._save_file_to_vault(response, filename, self.get_container_id(), action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_download_malware_files(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        alert_id_param = param["alert_id"]

        data = {}

        # Set the file name for the vault
        try:
            filename = f"{alert_id_param}_malware.zip"
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'alert_id' action parameter")

        endpoint = FIREETEETP_GET_ALERT_MALWARE_FILES_ENDPOINT.format(alertId=alert_id_param)

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, method="post", json=data, stream=True)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, vault_details = self._save_file_to_vault(response, filename, self.get_container_id(), action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_download_case_files(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        alert_id_param = param["alert_id"]

        data = {}

        # Set the file name for the vault
        try:
            filename = f"{alert_id_param}_case.zip"
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'alert_id' action parameter")

        endpoint = FIREETEETP_GET_ALERT_CASE_FILES_ENDPOINT.format(alertId=alert_id_param)

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, method="post", json=data, stream=True)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, vault_details = self._save_file_to_vault(response, filename, self.get_container_id(), action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_remediate_emails(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        data = {}
        action_override_param = param.get("action_override")
        move_to_param = param.get("move_to")

        if action_override_param:
            data["action_override"] = action_override_param

            if not move_to_param:
                action_result.set_status(
                    phantom.APP_ERROR, "If the parameter 'action_override' is enabled the 'move_to' parameter also needs to be filled out"
                )
                return action_result.get_status()
            else:
                data["move_to"] = move_to_param

        try:
            data["message_ids"] = ",".join(param["etp_message_ids"])
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'etp_message_ids' action parameter")

        endpoint = FIREETEETP_REMEDIATE_EMAILS_ENDPOINT

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, method="post", json=data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_quarantined_email(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        etp_message_id_param = param["etp_message_id"]
        # Set the file name for the vault
        try:
            filename = f"quarantined_email_{etp_message_id_param}.txt"
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'etp_message_id' action parameter")

        endpoint = FIREEYEETP_GET_QUARANTINED_EMAIL_ENDPOINT.format(etp_message_id=etp_message_id_param)

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, vault_details = self._save_file_to_vault(response, filename, self.get_container_id(), action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_unquarantine_email(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        data = {}

        etp_message_id_param = param.get("etp_message_id")
        try:
            ids = [x.strip() for x in etp_message_id_param.split(",")]
            ids = [_f for _f in ids if _f]
            if not ids:
                return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'etp_message_id' action parameter")
            if len(ids) > 1:
                data["message_ids"] = ",".join(ids)
                endpoint = FIREEYEETP_BULK_RELEASE_QUARANTINE_EMAILS_ENDPOINT
            else:
                endpoint = FIREEYEETP_RELEASE_QUARANTINED_EMAIL_ENDPOINT.format(etp_message_id=ids)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'etp_message_id' action parameter")

        is_not_spam_param = param.get("is_not_spam")
        if is_not_spam_param:
            data["is_not_spam"] = is_not_spam_param

        headers_only_param = param.get("headers_only")
        if headers_only_param:
            data["headers_only"] = headers_only_param

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, method="post", json=data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_quarantined_email(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        data = {}

        etp_message_id_param = param.get("etp_message_id")
        try:
            ids = [x.strip() for x in etp_message_id_param.split(",")]
            ids = [_f for _f in ids if _f]
            if not ids:
                return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'etp_message_id' action parameter")
            if len(ids) > 1:
                data["message_ids"] = ",".join(ids)
                endpoint = FIREEYEETP_BULK_DELETE_QUARANTINE_EMAILS_ENDPOINT
            else:
                endpoint = FIREEYEETP_DELETE_QUARANTINED_EMAIL_ENDPOINT.format(etp_message_id=ids)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'etp_message_id' action parameter")

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, method="post", json=data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        resp_data = response

        # Normalize output data so it matches for both actions.
        # The endpoint called when you are delete 1 specific email produces different output data
        try:
            if resp_data.get("data", {}).get("deleted"):
                resp_data["data"]["successful_message_ids"] = resp_data.get("data", {}).get("message_ids")
                resp_data["data"]["operation"] = "delete"
                resp_data["data"]["failed_message_ids"] = []
                del resp_data["data"]["message_ids"]
                del resp_data["data"]["deleted"]
            else:
                resp_data["data"]["failed_message_ids"] = resp_data.get("data", {}).get("message_ids")
                resp_data["data"]["operation"] = "delete"
                resp_data["data"]["successful_message_ids"] = []
                del resp_data["data"]["message_ids"]
                del resp_data["data"]["deleted"]
        except Exception:
            self.debug_print("Failed to normalize output data")

        action_result.add_data(resp_data)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_quarantined_emails(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        data = {}
        data["attributes"] = {}

        # Check the 'size' parameter
        ret_val, size = self._validate_integer(action_result, param.get("size"), SIZE_KEY)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        if size > 200:
            size = 200
        data["size"] = size

        # Check the 'from_date' parameter
        from_date_param = param.get("from_date")
        if from_date_param:
            # Make sure the datetime supplied is a valid. Should be ISO8601 compliant
            try:
                from_date = from_date_param.strip()
                from_date = datetime.strptime(from_date, "%Y-%m-%dT%H:%M:%S")
                from_date = from_date.strftime("%Y-%m-%dT%H:%M:%S")

                data["attributes"]["date"] = {}
                data["attributes"]["date"]["from_date"] = from_date
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, ERR_ISO_FORMAT.format("from_date"))

            # Check the 'to_date' parameter
            to_date_param = param.get("to_date")
            # Since the 'from_date' and 'to_date' need to be supplied together check it here
            if to_date_param:
                # Make sure the datetime supplied is a valid. Should be ISO8601 compliant
                try:
                    to_date = to_date_param.strip()
                    to_date = datetime.strptime(to_date, "%Y-%m-%dT%H:%M:%S")
                    to_date = to_date.strftime("%Y-%m-%dT%H:%M:%S")

                    data["attributes"]["date"] = {}
                    data["attributes"]["date"]["to_date"] = to_date
                except Exception:
                    return action_result.set_status(phantom.APP_ERROR, ERR_ISO_FORMAT.format("to_date"))

        # Check the 'domain' parameter
        domains_param = param.get("domains")
        if domains_param:
            try:
                domains = [x.strip() for x in domains_param.split(",")]
                domains = [_f for _f in domains if _f]
                if not domains:
                    return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'domains' action parameter")
                data["attributes"]["domains"] = domains
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'domains' action parameter")

        # Check the 'email_server' parameter
        email_server_param = param.get("email_server")
        if email_server_param:
            data["attributes"]["email_server"] = email_server_param

        # Check the from 'email_address' parameter
        from_param = param.get("from")
        if from_param:
            try:
                data["attributes"]["from"] = from_param.strip()
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'from' action parameter")

        # Check the 'reason' parameter
        reason_param = param.get("reason")
        if reason_param:
            try:
                reason = [x.strip() for x in reason_param.split(",")]
                reason = [_f for _f in reason if _f]
                if not reason:
                    return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'reason' action parameter")
                data["attributes"]["reason"] = reason
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'reason' action parameter")

        # Check the 'recipients' parameter
        recipients_param = param.get("recipients")
        if recipients_param:
            try:
                recipients = [x.strip() for x in recipients_param.split(",")]
                recipients = [_f for _f in recipients if _f]
                if not recipients:
                    return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'recipients' action parameter")
                data["attributes"]["recipients"] = recipients
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'recipients' action parameter")

        # Check the 'sender_domain' parameter
        sender_domain_param = param.get("sender_domain")
        if sender_domain_param:
            try:
                data["attributes"]["sender_domain"] = sender_domain_param.strip()
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'sender_domain' action parameter")

        # Check the 'subject' parameter
        subject_param = param.get("subject")
        if subject_param:
            try:
                data["attributes"]["subject"] = subject_param.strip()
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'subject' action parameter")

        # Check the 'tags' parameter
        tags_param = param.get("tags")
        if tags_param:
            try:
                tags = [x.strip() for x in tags_param.split(",")]
                tags = [_f for _f in tags if _f]
                if not tags:
                    return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'tags' action parameter")
                data["attributes"]["tags"] = {}
                data["attributes"]["tags"]["value"] = tags
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value in 'tags' action parameter")

        endpoint = FIREEYEETP_LIST_QUARANTINED_EMAILS_ENDPOINT

        # make rest call
        ret_val, response = self._paginator(endpoint, action_result, data, method="post")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_on_poll(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.debug_print("In on_poll")
        self.debug_print(f"state: {self._state}")

        # Parameters for the API
        data = {}

        # This is the maximum results per request we can get
        data["size"] = 200

        # Get config
        config = self.get_config()

        try:
            # Get the endtime from Phantom which is when the action was ran
            timestamp = datetime.utcfromtimestamp(param.get(phantom.APP_JSON_END_TIME) / 1000.0)
        except Exception:
            self.debug_print("'end_time' in Phantom could not be converted correctly. Use alternative time equal to datetime.utcnow()")
        else:
            timestamp = datetime.utcnow()

        # If it is a manual poll or first run
        if self.is_poll_now() or self._state.get("first_run", True):
            try:
                # Check the 'container_count' parameter
                # If container count is not present just get 1
                ret_val, limit = self._validate_integer(action_result, param.get(phantom.APP_JSON_CONTAINER_COUNT, 1), CONTAINER_COUNT_KEY)
                if phantom.is_fail(ret_val):
                    return action_result.get_status()
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "The maximum containers is invalid")

            date = (timestamp - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
            data["fromLastModifiedOn"] = date

        # If it is a scheduled poll, ingest from last_ingestion_time
        else:
            limit = data["size"]
            try:
                # Get the ingestion interval
                # If interval is not present just get the last 15 minutes
                interval_mins = int(config.get("ingest", {}).get("interval_mins", 15))
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Ingestion interval is invalid")

            # Try to get the last_ingestion_time from the state file
            # If not get the last x minutes which is determined by the interval
            date = self._state.get(
                "last_ingestion_time", (datetime.utcnow() - timedelta(minutes=interval_mins)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
            )
            data["fromLastModifiedOn"] = date

        endpoint = FIREETEETP_LIST_ALERTS_ENDPOINT

        # make rest call
        ret_val, response = self._paginator2(endpoint, action_result, data, limit=limit, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Start creating events and artifacts
        if response:
            if self.is_poll_now() or self._state.get("first_run", True):
                # If we want to get a limited of alerts then just return the list with that number of items
                response = response[-limit:]

            self.save_progress(f"Ingesting {len(response)} alerts")

            for alert in response:
                # Create a container for each alert
                container_dict = self._create_container(action_result, alert)
                artifacts = self._create_artifacts(alert=alert)
                container_dict["artifacts"] = artifacts

                container_creation_status, container_creation_msg, container_id = self.save_container(container=container_dict)

                if phantom.is_fail(container_creation_status):
                    self.debug_print(container_creation_msg)
                    self.save_progress(
                        "Error while creating container for alert {alert_name}. {error_message}".format(
                            alert_name=container_dict["name"], error_message=container_creation_msg
                        )
                    )
                    return action_result.set_status(phantom.APP_ERROR), None

        else:
            self.save_progress("No alerts found")

        # Mark the first_run as False once the scheduled or ingestion polling
        # first run or every run has been successfully completed
        if not self.is_poll_now():
            self._state["first_run"] = False

        self._state["last_ingestion_time"] = data["fromLastModifiedOn"]

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _convert_timestamp_to_string(self, timestamp, tz):
        """This function is used to handle of timestamp converstion for on_poll action.
        :param timestamp: Epoch time stamp
        :param tz: Timezone configured in the Asset
        :return: datetime string
        """

        date_time = datetime.fromtimestamp(timestamp, pytz.timezone(tz))

        return date_time.strftime("%Y-%m-%dT%H:%M:%S:%fZ")

    def _create_container(self, action_result, alert):
        """This function is used to create the container in Phantom using alert data.
        :param alert: Data of single alert
        :return: status(success/failure), container_id
        """
        container_dict = dict()

        # Creating a description and name for the alert
        # ETP does not provide good data to create a name or description so I am manually creating a standardized convention

        description = "Fireeye ETP alert on the email with the subject {} due to {} going to the user {}.".format(
            alert.get("attributes", {}).get("email", {}).get("headers", {}).get("subject"),
            alert.get("attributes", {}).get("meta", {}).get("last_malware"),
            alert.get("attributes", {}).get("email", {}).get("headers", {}).get("to"),
        )

        name = "Fireeye ETP Alert - {}".format(alert.get("attributes", {}).get("meta", {}).get("last_malware"))

        container_dict["name"] = f"{name}"
        container_dict["source_data_identifier"] = self._create_dict_hash(alert)
        container_dict["description"] = description

        return container_dict

    def _create_artifacts(self, alert):
        """This function is used to create artifacts in given container using alert data.
        :param alert: Data of single alert
        :param container_id: ID of container in which we have to create the artifacts
        :return: status(success/failure), message
        """
        artifacts_list = []
        temp_dict = {}
        cef = {}

        # Add the contains data to the artifact
        cef_types = {
            "malware_md5": ["fileHashMd5"],
            "source_ip": ["sourceAddress"],
            "etp_message_id": ["fireeyeetp message id"],
            "legacy_id": ["fireeyeetp legacy id"],
            "id": ["fireeyeetp alert id"],
            "rcpt_to": ["email"],
            "mail_from": ["email"],
            "to": ["email"],
            "cc": ["email"],
            "from": ["email"],
        }

        # Flatten the alert data
        cef = self.flatten_json(alert)

        # Add into artifacts dictionary if it is available
        if cef:
            temp_dict["cef"] = cef
            temp_dict["cef_types"] = cef_types
            temp_dict["name"] = alert.get("attributes", {}).get("meta", {}).get("last_malware")
            temp_dict["source_data_identifier"] = self._create_dict_hash(temp_dict)

        artifacts_list.append(temp_dict)
        return artifacts_list

    def _get_fips_enabled(self):
        try:
            from phantom_common.install_info import is_fips_enabled
        except ImportError:
            return False

        fips_enabled = is_fips_enabled()

        if fips_enabled:
            self.debug_print("FIPS is enabled")
        else:
            self.debug_print("FIPS is not enabled")

        return fips_enabled

    def _create_dict_hash(self, input_dict):
        """This function is used to generate the hash from dictionary.
        :param input_dict: Dictionary for which we have to generate the hash
        :return: hash
        """
        if not input_dict:
            return None

        try:
            input_dict_str = json.dumps(input_dict, sort_keys=True)
        except Exception as e:
            err = self._get_error_message_from_exception(e)
            self.debug_print("Handled exception in _create_dict_hash", err)
            return None

        if self._get_fips_enabled():
            return hashlib.sha256(input_dict_str).hexdigest()
        else:
            return hashlib.md5(input_dict_str).hexdigest()

    def flatten_json(self, y):
        """This function is used to generate a new JSON dictionary so the data flattened to the top most values.
        Helps with readability of the artifacts in the GUI.
        :param y: JSON Dictionary of the data to flatten
        :return out: new JSON dictionary
        """
        out = {}

        def flatten(x, name=""):
            if type(x) is dict:
                for a in x:
                    flatten(x[a], a)
            elif type(x) is list:
                i = 0
                for a in x:
                    flatten(a, name)
                    i += 1
            else:
                out[name] = x

        flatten(y)
        return out

    def handle_action(self, param):
        """This function gets current action identifier and calls member function of its own to handle the action.
        :param param: dictionary which contains information about the actions to be executed
        :return: status success/failure
        """

        action_mapping = {
            "test_connectivity": self._handle_test_connectivity,
            "list_alerts": self._handle_list_alerts,
            "get_alert": self._handle_get_alert,
            "list_email_attributes": self._handle_list_email_attributes,
            "get_email_attributes": self._handle_get_email_attributes,
            "trace_message": self._handle_trace_message,
            "trace_email": self._handle_trace_email,
            "download_email": self._handle_download_email,
            "download_pcap": self._handle_download_pcap,
            "download_malware_files": self._handle_download_malware_files,
            "download_case_files": self._handle_download_case_files,
            "remediate_emails": self._handle_remediate_emails,
            "get_quarantined_email": self._handle_get_quarantined_email,
            "unquarantine_email": self._handle_unquarantine_email,
            "delete_quarantined_email": self._handle_delete_quarantined_email,
            "list_quarantined_emails": self._handle_list_quarantined_emails,
            "on_poll": self._handle_on_poll,
        }

        # Get the action that we are supposed to execute for this App Run
        action = self.get_action_identifier()
        action_execution_status = phantom.APP_SUCCESS

        if action in list(action_mapping.keys()):
            action_function = action_mapping[action]
            action_execution_status = action_function(param)
        return action_execution_status

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions

        # Check for load_state API, use it if it is present
        if hasattr(self, "load_state"):
            self._state = self.load_state()
        else:
            self._state = self._load_state()
        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}
            return self.set_status(phantom.APP_ERROR, FIREEYEETP_STATE_FILE_CORRUPT_ERR)

        # Fetching the Python major version
        try:
            self._python_version = int(sys.version_info[0])
        except Exception:
            return self.set_status(phantom.APP_ERROR, "Error occurred while getting the Phantom server's Python major version")

        # get the asset config
        config = self.get_config()

        """
        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """

        self._verify_server_cert = config.get("verify_server_cert", True)

        api_key = config.get("api_key", "")
        if isinstance(api_key, str) and api_key.strip():
            self._header = {"x-fireeye-api-key": api_key.strip()}
        else:
            self._header = self.authenticate(config)

        # Check to see which instance the user selected. Use the appropriate URL.
        base_url = config.get("base_url").rstrip("/")

        self._base_url = f"{base_url}/{FIREETEETP_API_PATH}"

        return phantom.APP_SUCCESS

    def authenticate(self, config):
        """Authenticate using client id and secret, return the header with bearer token"""
        if not config.get("client_id") or not config.get("client_secret") or not config.get("auth_scopes"):
            raise ValueError("One or more of client_id, client_secret or auth_scopes was left unset. Unable to get authentication token.")

        auth_scopes_split_re = re.compile(r"[\s,]+")
        auth_scopes_str = " ".join(auth_scopes_split_re.split(config.get("auth_scopes", "").strip()))
        auth_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        auth_data = {"grant_type": "client_credentials", "scope": auth_scopes_str}
        response = requests.post(
            FIREEYEETP_AUTH_URL,
            headers=auth_headers,
            auth=(config.get("client_id"), config.get("client_secret")),
            data=auth_data,
            verify=self._verify_server_cert,
        )

        response_data = response.json()
        if response.status_code != 200:
            raise ValueError(f"Authentication error: status_code={response.status_code}, data={response_data}")
        return {"Authorization": f"{response_data['token_type']} {response_data['access_token']}"}

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    # import pudb
    import argparse

    # pudb.set_trace()

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
            login_url = FireeyeEtpConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=FIREETEETP_DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=FIREETEETP_DEFAULT_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = FireeyeEtpConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
