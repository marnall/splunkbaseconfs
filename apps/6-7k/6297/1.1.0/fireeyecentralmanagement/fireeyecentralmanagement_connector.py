# File: fireeyecentralmanagement_connector.py
#
# Copyright (c) 2022-2024 Splunk Inc.
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

# Python 3 Compatibility imports
from __future__ import print_function, unicode_literals

import json
import sys
from datetime import datetime, timedelta

import dateutil
# Phantom App imports
import phantom.app as phantom
import phantom.rules as phantom_rules
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault

from fireeyecentralmanagement_consts import *

CM_PRODUCTS_MAP_REVERSE = {value: key for key, value in CM_PRODUCTS_MAP.items()}


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class FireeyeCentralManagementConnector(BaseConnector):
    def __init__(self):
        super(FireeyeCentralManagementConnector, self).__init__()

        self._state = None

        self._base_url = None
        self._verify_ssl = None
        self._username = None
        self._password = None
        self._client_token = None
        self._auth_token = None

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = None
        error_message = ERROR_MESSAGE_UNAVAILABLE

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except:
            pass

        if not error_code:
            error_text = "Error Message: {}".format(error_message)
        else:
            error_text = "Error Code: {}. Error Message: {}".format(
                error_code, error_message
            )

        return error_text

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200 or response.status_code == 204:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(
                phantom.APP_ERROR,
                "Status Code {}. Empty response and no information in the header".format(
                    response.status_code
                ),
            ),
            None,
        )

    def get_auth_token(self, action_result):
        login_endpoint = "{}{}".format(self._base_url, CM_AUTH_LOGIN_URL)

        try:
            response = requests.post(
                login_endpoint,
                auth=(self._username, self._password),
                verify=self._verify_ssl,
                timeout=60,
            )
        except requests.exceptions.InvalidURL as e:
            self.debug_print(self._get_error_message_from_exception(e))
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, CM_ERROR_INVALID_URL), None
            )
        except requests.exceptions.InvalidSchema as e:
            self.debug_print(self._get_error_message_from_exception(e))
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, CM_ERROR_INVALID_SCHEMA), None
            )
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), None)

        if 200 <= response.status_code < 399:
            try:
                auth_token = response.headers[CM_TOKEN_HEADER]
                self._auth_token = auth_token
                return RetVal(phantom.APP_SUCCESS, auth_token)
            except KeyError as e:
                error_message = self._get_error_message_from_exception(e)
                message = (
                    "Could not extract auth token from response header: {msg}".format(
                        msg=error_message
                    )
                )
                return RetVal(
                    action_result.set_status(phantom.APP_ERROR, message), None
                )

        message = "Could not retrieve auth token"
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def release_auth_token(self):
        logout_endpoint = "{}{}".format(self._base_url, CM_AUTH_LOGOUT_URL)

        headers = {CM_TOKEN_HEADER: self._auth_token}

        if self._client_token:
            headers[CM_CLIENT_TOKEN_HEADER] = self._client_token

        response = requests.post(
            logout_endpoint, headers=headers, verify=self._verify_ssl, timeout=60
        )

        if response.status_code == 204:
            return phantom.APP_SUCCESS

        return phantom.APP_ERROR

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
        except:
            error_text = "Cannot parse error details"

        message = "Status Code: {0}. Data from server: {1}".format(
            status_code, error_text
        )

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            err = self._get_error_message_from_exception(e)
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    "Unable to parse JSON response. Error: {0}".format(err),
                ),
                None,
            )

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_file_response(self, r, action_result):

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, r)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in r.headers.get("Content-Type", "") and r.text:
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

        if "octet-stream" in r.headers.get("Content-Type", ""):
            return self._process_file_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, "Invalid method: {0}".format(method)
                ),
                resp_json,
            )

        # Create a URL to connect to
        url = "{}{}".format(self._base_url, endpoint)

        if not self._auth_token:
            ret_val, token = self.get_auth_token(action_result)
            if phantom.is_fail(ret_val):
                self.save_progress("Could not retrieve auth token.")
                return RetVal(action_result.get_status(), None)

        if not kwargs.get("headers"):
            kwargs["headers"] = {}

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            CM_TOKEN_HEADER: self._auth_token,
        }

        headers.update(kwargs["headers"])

        del kwargs["headers"]

        if self._client_token:
            headers[CM_CLIENT_TOKEN_HEADER] = self._client_token

        try:
            r = request_func(url, verify=self._verify_ssl, headers=headers, **kwargs)
        except Exception as e:
            err = self._get_error_message_from_exception(e)
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    "Error Connecting to server. Details: {0}".format(err),
                ),
                resp_json,
            )

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to endpoint")
        ret_val, token = self.get_auth_token(action_result)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        self.save_progress("Successfully retrieved token")

        ret_val = self.release_auth_token()

        if phantom.is_fail(ret_val):
            self.save_progress("Could not release auth token")
            return action_result.get_status()

        self.save_progress("Released token")

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _retrieve_alerts(self, action_result, since, limit):
        date = since.astimezone().isoformat(timespec="milliseconds")

        params = {"start_time": date, "duration": "48_hours", "info_level": "concise"}

        if self._include_riskware:
            params["include_riskware"] = "true"

        ret_val, response = self._make_rest_call(
            CM_ALERTS_URL, action_result, params=params, headers=None
        )

        if phantom.is_fail(ret_val) or "alert" not in response:
            action_result_message = action_result.get_message()
            if action_result_message:
                message = f"Error retrieving alerts: {action_result_message}"
            else:
                message = "Error retrieving alerts"
            return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

        return ret_val, response["alert"][:limit]

    def _search_alert_container(self, alert):
        "Find the phantom container corresponding to the redmine ticket"

        alert_id = alert["id"]

        url = '{0}rest/container?_filter_source_data_identifier="{1}"&_filter_asset={2}'.format(
            self.get_phantom_base_url(), alert_id, self.get_asset_id()
        )
        try:
            r = requests.get(url, verify=self._verify_ssl)  # nosemgrep
            resp_json = r.json()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.debug_print(f"Unable to query Phantom for containers: {error_message}")
            return

        if resp_json.get("count", 0) <= 0:
            self.debug_print("No container matched")
            return
        try:
            container_id = resp_json.get("data", [])[0]["id"]
            self.debug_print(f"Found container id: {container_id}")
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.debug_print(f"Container results are not proper: {error_message}")
            return

        return container_id

    def _gen_alert_container_title(self, alert):
        """Generate title for the new phantom container based on ticket information"""

        primary = alert["id"]
        secondary = alert.get("name")
        tertiary = CM_PRODUCTS_MAP_REVERSE.get(alert["product"], alert["product"])
        return "{} - {} - {}".format(primary, secondary, tertiary)

    def _create_alert_container_json(self, alert):
        """Creates a new phantom container based on alert information"""
        alert_container = {
            "name": self._gen_alert_container_title(alert),
            "label": self.get_config().get("ingest", {}).get("container_label"),
            "source_data_identifier": alert["id"],
            "description": alert["name"],
            "data": json.dumps(alert),
        }
        return alert_container

    def _update_alert_container(self, container_id, alert):

        updated_container = self._create_alert_container_json(alert)
        url = "{0}rest/container/{1}".format(self.get_phantom_base_url(), container_id)

        try:
            requests.post(
                url,
                data=(json.dumps(updated_container)),
                verify=self._verify_ssl,
                timeout=60,
            )
        except Exception as e:
            err = self._get_error_message_from_exception(e)
            self.debug_print(f"Error while updating the container: {err}")

    def _create_alert_artifacts(self, alert, container_id):

        artifacts = []

        product = CM_PRODUCTS_MAP_REVERSE.get(alert["product"], alert["product"])

        if product == "NX":
            artifact = self._create_nx_artifact(alert, container_id)
        elif product == "EX":
            artifact = self._create_ex_artifact(alert, container_id)
        else:
            artifact = self._create_fallback_artifact(alert, container_id)

        artifacts.append(artifact)

        return artifacts

    def _create_nx_artifact(self, alert, container_id):
        nx_artifact = {
            "container_id": container_id,
            "name": "Fireeye Artifact",
            "label": "Fireeye NX",
            "source_data_identifier": alert["id"],
        }
        artifact_cef = {}
        artifact_cef = alert

        nx_artifact["cef"] = artifact_cef
        nx_artifact["cef_types"] = {
            "id": ["fireeye cm alert id"],
        }

        return nx_artifact

    def _create_ex_artifact(self, alert, container_id):
        ex_artifact = {
            "container_id": container_id,
            "name": "Fireeye Artifact",
            "label": "Fireeye EX",
            "source_data_identifier": alert["id"],
        }
        artifact_cef = {}
        artifact_cef = alert

        ex_artifact["cef"] = artifact_cef
        ex_artifact["cef_types"] = {
            "id": ["fireeye cm alert id"],
        }

        return ex_artifact

    def _create_fallback_artifact(self, alert, container_id):
        artifact = {
            "container_id": container_id,
            "name": "Fireeye Artifact",
            "label": "Fireeye {}".format(alert["product"]),
            "source_data_identifier": alert["id"],
        }
        artifact["cef"] = alert
        artifact["cef_types"] = {
            "id": ["fireeye cm alert id"],
        }

        return artifact

    def _save_alert_container(self, action_result, alert):

        container_id = self._search_alert_container(alert)

        if container_id:
            self.debug_print("Updating existing alert container")
            ret_val = self._update_alert_container(container_id, alert)
            alert_artifacts = self._create_alert_artifacts(alert, container_id)
            self.save_artifacts(alert_artifacts)
            return RetVal(phantom.APP_SUCCESS)

        alert_container = self._create_alert_container_json(alert)
        ret_val, message, container_id = self.save_container(alert_container)

        if not ret_val:
            self.debug_print("Could not save new ticket container")
            return RetVal(phantom.APP_ERROR)
        else:
            alert_artifacts = self._create_alert_artifacts(alert, container_id)
            self.debug_print(len(alert_artifacts))
            self.save_artifacts(alert_artifacts)
            return RetVal(phantom.APP_SUCCESS)

    def _handle_on_poll(self, param):
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )
        action_result = self.add_action_result(ActionResult(dict(param)))

        container_count = param.get("container_count", "")

        last_run = self._state.get("last_run")
        backfill = datetime.utcnow().astimezone() - timedelta(days=2)
        product_filter = []

        if self._product_filter:
            product_filter_list = [
                value.strip()
                for value in self._product_filter.split(",")
                if value.strip()
            ]
            if not product_filter_list:
                return action_result.set_status(
                    phantom.APP_ERROR, CM_ERROR_INVALID_FIELD.format(key="product filter")
                )

            for product in product_filter_list:
                product_filter.append(CM_PRODUCTS_MAP.get(product, product))

        self.debug_print("Configured Product filter", product_filter)

        if self.is_poll_now():
            self.debug_print("Run Mode: Poll Now")
            last_run = backfill
        else:
            if not last_run:
                self.debug_print("Run Mode: First Scheduled Poll")
                last_run = backfill
            else:
                self.debug_print("Run Mode: Scheduled Poll")
                last_run = dateutil.parser.isoparse(last_run)

        alerts = []

        try:
            self.debug_print("Retrieving alerts last_run={}".format(last_run))
            ret_val, alerts = self._retrieve_alerts(
                action_result, last_run, container_count
            )
            if phantom.is_fail(ret_val):
                return action_result.get_status()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(
                phantom.APP_ERROR,
                "Error retrieving alerts during poll: {}".format(error_message),
            )

        self.debug_print(f"Total alerts retrieved {len(alerts)}")
        self.save_progress(f"Total alerts retrieved {len(alerts)}")

        try:
            for alert in alerts:
                if self._product_filter:
                    if alert.get("product", []) not in product_filter:
                        self.debug_print(
                            "Received alert for product which is not included in product filter, ignoring.."
                        )
                        continue
                self._save_alert_container(action_result, alert)
        except Exception as e:
            err = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, err)

        self.save_progress("Polling complete")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_quarantined_emails(self, param):
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )
        action_result = self.add_action_result(ActionResult(dict(param)))

        start_time = param.get("start_time")
        end_time = param.get("end_time")
        mail_from = param.get("from")
        mail_subject = param.get("subject")
        appliance_id = param.get("appliance_id")

        params = {}

        if (start_time and not end_time) or (end_time and not start_time):
            return action_result.set_status(
                phantom.APP_ERROR, "Must provide both start and end time filters"
            )

        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if mail_from:
            params["from"] = mail_from
        if mail_subject:
            params["subject"] = mail_subject
        if appliance_id:
            params["appliance_id"] = appliance_id

        # make rest call
        ret_val, emails = self._make_rest_call(
            CM_EMAILMGMT_QUARANTINE, action_result, params=params
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if isinstance(emails, list):
            for email in emails:
                action_result.add_data(email)

        summary = action_result.update_summary({})
        summary["num_emails"] = len(emails) if isinstance(emails, list) else 0

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_quarantined_email(self, param):
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )
        action_result = self.add_action_result(ActionResult(dict(param)))

        id = param["queue_id"]
        sensor_name = param["sensor_name"]

        endpoint = "{}/{}".format(CM_EMAILMGMT_QUARANTINE, id)

        params = {"sensorName": sensor_name}

        headers = {"Accept": "application/octet-stream"}

        ret_val, response = self._make_rest_call(
            endpoint, action_result, params=params, headers=headers
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        vault_tmp_dir = Vault.get_vault_tmp_dir()
        local_dir = "{}/".format(vault_tmp_dir)
        file_name = "{}.eml".format(id)

        with open(local_dir + file_name, "wb") as f_out:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f_out.write(chunk)

        try:
            success, message, vault_id = phantom_rules.vault_add(
                container=self.get_container_id(),
                file_location="{}{}".format(local_dir, file_name),
                file_name=file_name,
                metadata={"mime_type": "message/rfc822"},
            )
            summary = action_result.update_summary({})
            summary["vault_id"] = vault_id

        except Exception as e:
            err = self._get_error_message_from_exception(e)
            return action_result.set_status(
                phantom.APP_ERROR,
                "Unable to store file in Phantom Vault. {0}".format(err),
            )

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_release_quarantined_emails(self, param):
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )
        action_result = self.add_action_result(ActionResult(dict(param)))

        sensor_name = param["sensor_name"]
        queue_ids = param["queue_ids"].split(",")

        if len(queue_ids) > 100:
            return action_result.set_status(
                phantom.APP_ERROR, CM_ERROR_TOO_MANY_QUEUE_IDS
            )

        endpoint = CM_EMAILMGMT_QUARANTINE_RELEASE

        params = {"sensorName": sensor_name}
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        payload = {"queue_ids": queue_ids}

        ret_val, response = self._make_rest_call(
            endpoint,
            action_result,
            params=params,
            headers=headers,
            method="post",
            json=payload,
        )

        if phantom.is_fail(ret_val):
            action_result.add_data(response)
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_alert(self, param):
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )
        action_result = self.add_action_result(ActionResult(dict(param)))

        id = param["id"]

        endpoint = "{}{}".format(CM_ALERT_URL, id)

        ret_val, response = self._make_rest_call(
            endpoint, action_result, params=None, headers=None
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        alerts = response.get("alert", [])
        for alert in alerts:
            action_result.add_data(alert)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_alerts(self, param):
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )
        action_result = self.add_action_result(ActionResult(dict(param)))

        duration = param["duration"]
        info_level = param["info_level"]

        start_time = param.get("start_time")
        end_time = param.get("end_time")
        callback_domain = param.get("callback_domain")
        file_name = param.get("file_name")
        malware_name = param.get("malware_name")
        malware_type = param.get("malware_type")
        md5 = param.get("md5")
        recipient_email = param.get("recipient_email")
        sender_email = param.get("sender_email")
        src_ip = param.get("src_ip")
        dst_ip = param.get("dst_ip")
        url = param.get("url")

        if start_time and end_time:
            return action_result.set_status(phantom.APP_ERROR, ERROR_START_AND_END_TIME)

        if not start_time and not end_time:
            end_time = datetime.utcnow().astimezone().isoformat(timespec="milliseconds")

        params = {
            "duration": duration,
            "info_level": info_level,
            "start_time": start_time,
            "end_time": end_time,
        }

        if callback_domain:
            params["callback_domain"] = callback_domain
        if file_name:
            params["file_name"] = file_name
        if malware_name:
            params["malware_name"] = malware_name
        if malware_type:
            params["malware_type"] = malware_type
        if md5:
            params["md5"] = md5
        if recipient_email:
            params["recipient_email"] = recipient_email
        if sender_email:
            params["sender_email"] = sender_email
        if src_ip:
            params["src_ip"] = src_ip
        if dst_ip:
            params["dst_ip"] = dst_ip
        if url:
            params["url"] = url
        if self._include_riskware:
            params["include_riskware"] = "true"

        ret_val, response = self._make_rest_call(
            CM_ALERTS_URL, action_result, params=params, headers=None
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        alerts = response.get("alert", [])
        for alert in alerts:
            action_result.add_data(alert)

        summary = action_result.update_summary({})
        summary["num_alerts"] = len(alerts)
        summary["msg"] = response.get("msg")

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "on_poll":
            ret_val = self._handle_on_poll(param)

        elif action_id == "get_quarantined_email":
            ret_val = self._handle_get_quarantined_email(param)

        elif action_id == "list_quarantined_emails":
            ret_val = self._handle_list_quarantined_emails(param)

        elif action_id == "get_alert":
            ret_val = self._handle_get_alert(param)

        elif action_id == "list_alerts":
            ret_val = self._handle_list_alerts(param)

        elif action_id == "release_quarantined_emails":
            ret_val = self._handle_release_quarantined_emails(param)

        return ret_val

    def initialize(self):
        self._state = self.load_state()

        self._this_run = (
            datetime.utcnow().astimezone().isoformat(timespec="milliseconds")
        )

        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}
            return self.set_status(phantom.APP_ERROR, CM_STATE_FILE_CORRUPT_ERROR)

        config = self.get_config()

        self._base_url = config["server_url"].rstrip("/")
        self._verify_ssl = config.get("verify_ssl", False)
        self._username = config["username"]
        self._password = config["password"]
        self._client_token = config.get("client_token")
        self._product_filter = config.get("product_filter")
        self._include_riskware = config.get("include_riskware", False)

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades

        if self._auth_token:
            self.release_auth_token()

        self._state["last_run"] = self._this_run
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument('-v', '--verify', action='store_true', help='verify', required=False, default=False)

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
            login_url = (
                FireeyeCentralManagementConnector._get_phantom_base_url() + "/login"
            )

            print("Accessing the Login page")
            r = requests.get(login_url, timeout=60)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(  # nosemgrep
                login_url, verify=verify, data=data, headers=headers, timeout=60
            )
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = FireeyeCentralManagementConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
