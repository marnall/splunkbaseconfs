# File: zerofox_connector.py
#
# Copyright (c) ZeroFox, 2024
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
import sys
from datetime import datetime, timedelta

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from zerofox_consts import ZEROFOX_API_URL


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class AlertMapper:
    def __init__(self, _container_label, app_id):
        self._container_label = _container_label
        self.app_id = app_id

    def _phantom_severity_transform(self, severity):
        """
        Map ZeroFOX severity to Phantom severity.

        :param severity: ZeroFOX Severity: 5, 4, 3, 2, 1
        :return: Phantom Severity: high, medium, low
        """
        return {5: "high", 4: "high", 3: "medium", 2: "low", 1: "low"}.get(severity)

    def build_artifact(self, container_id, alert):
        """
        Artifacts are JSON objects that are stored in a container.
        Artifacts are objects that are associated with a container and serve as
        corroboration or evidence related to the container. Much like the
        container schema, the artifact schema has a common header that can be
        operated on, and also contains a Common Event Format (CEF) body and
        raw data body to store elements that can be accessed by Splunk Phantom
        playbooks as shown in the following code. The fields in the code are
        defined in the table immediately following the code:

        {
          "id": 1,
          "version": 1,
          "name": "test",
          "label": "event",
          "source_data_identifier": "140a7ae0-9da5-4ee2-b06c-64faa313e94a",
          "create_time": "2016-01-18T19:26:39.053087Z",
          "start_time": "2016-01-18T19:26:39.058797Z",
          "end_time": null,
          "severity": "low",
          "type": null,
          "kill_chain": null,
          "hash": "EXAMPLEHASH",
          "cef": {
            "sourceAddress": "1.1.1.1"
          },
          "container": 1,
          "description": null,
          "tags": [""],
          "data": {}
        }

        Create an artifact from a ZeroFOX alert.

        :param container_id: int
        :param alert: ZeroFOX alert
        :return: dict
        """
        now = datetime.now()

        try:
            perp_name = alert["perpetrator"]["name"]
        except KeyError:
            perp_name = "Concealed Perpetrator"

        try:
            perp_content = alert["perpetrator"]["name"]
        except KeyError:
            perp_content = None

        artifact = dict()
        artifact["container_id"] = container_id
        artifact["label"] = "alert"
        artifact["name"] = alert["rule_name"]
        artifact["description"] = alert["offending_content_url"]
        artifact["severity"] = self._phantom_severity_transform(alert["severity"])
        artifact["label"] = "event"
        artifact["type"] = alert["network"]
        artifact["tags"] = [alert["network"]]
        artifact["start_time"] = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        artifact["source_data_identifier"] = alert["id"]
        artifact["run_automation"] = True

        # get screenshot from metadata
        try:
            alert_metadata = alert["metadata"]
        except KeyError:
            alert_metadata = None

        if alert_metadata:
            try:
                m_data = json.loads(alert_metadata)
                screenshot_url = m_data["alert_modal"]["screenshot"]
            except KeyError:
                screenshot_url = None

        artifact["cef"] = dict()
        artifact["cef"]["alert_id"] = alert["id"]
        artifact["cef"]["zerofox_url"] = f"https://cloud.zerofox.com/alerts/{alert['id']}"
        artifact["cef"]["alert_type"] = alert["alert_type"]
        artifact["cef"]["offending_content_url"] = alert["offending_content_url"]
        artifact["cef"]["screenshot_url"] = screenshot_url
        artifact["cef"]["entity"] = alert["entity"]["name"]
        artifact["cef"]["perpetrator_name"] = perp_name
        artifact["cef"]["perpetrator_url"] = alert["perpetrator"]["url"]
        artifact["cef"]["perpetrator_type"] = alert["perpetrator"]["type"]
        artifact["cef"]["perpetrator_content"] = perp_content
        artifact["cef"]["rule_name"] = alert["rule_name"]
        artifact["cef"]["rule_id"] = alert["rule_id"]
        artifact["cef"]["notes"] = alert["notes"]
        artifact["cef"]["reviewed"] = alert["reviewed"]
        artifact["cef"]["escalated"] = alert["escalated"]

        return artifact

    def prepare_alert_container(self, alert):
        """
        The contents of the container header and associated container data are
        exposed to the Splunk Phantom platform as JSON objects. Playbooks
        operate on these elements in order to make decisions and apply logic.
        The following code shows an example of the container schema, and the
        table immediately after the code defines the fields present in the code:

        {
          "id": 107,
          "version": "1",
          "label": "incident",
          "name": "my_test_incident",
          "source_data_identifier": "64c2a9a4-d6ef-4da8-ad6f-982d785f14b2",
          "description": "this is my test incident",
          "status": "open",
          "sensitivity": "amber",
          "severity": "medium",
          "create_time": "2016-01-16 07:18:46.631897+00",
          "start_time": "2016-01-16 07:18:46.636966+00",
          "end_time": "",
          "due_time": "2016-01-16 19:18:00+00",
          "close_time": "",
          "kill_chain": "",
          "owner": "admin",
          "hash": "EXAMPLEHASH",
          "tags": [""],
          "asset_name": "",
          "artifact_update_time": "2016-01-16 07:18:46.631875+00",
          "container_update_time": "2016-01-16 07:19:12.359376+00",
          "ingest_app_id": "",
          "data": {},
          "artifact_count": 8
        }

        Create a container from ZeroFOX alert.
        """

        container = dict()

        container["label"] = self._container_label
        container["name"] = "ZeroFOX Alert: {}".format(alert["rule_name"])
        container["description"] = "{}, {}".format(alert["network"].title().replace("_", " "), alert["alert_type"])
        container["sensitivity"] = "white"
        container["custom_fields"] = dict()
        container["custom_fields"]["alert_type"] = str(alert["alert_type"])
        container["custom_fields"]["alert_url"] = f"https://cloud.zerofox.com/alerts/{alert['id']}"

        container["severity"] = self._phantom_severity_transform(alert["severity"])
        container["source_data_identifier"] = alert["id"]
        container["asset_name"] = alert["entity"]["name"]
        container["tags"] = alert["tags"]
        date_time_obj = datetime.strptime(alert["timestamp"], "%Y-%m-%dT%H:%M:%S+00:00")
        container["start_time"] = date_time_obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        container["ingest_app_id"] = self.app_id

        return container


class ZeroFoxClient:
    def __init__(self, token, username) -> None:
        self.token = token
        self.username = username

    def _get_app_headers(self):
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
            "zf-source": "Splunk-SOAR",
        }

    def fetch_alerts(self):
        pass


class ZerofoxAlertsConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super(ZerofoxAlertsConnector, self).__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = ZEROFOX_API_URL

    def _get_app_headers(self):
        return {
            "Authorization": f"Token {self._api_key}",
            "Content-Type": "application/json",
            "zf-source": "splunk",
        }

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"),
            None,
        )

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    "Unable to parse JSON response. Error: {0}".format(str(e)),
                ),
                None,
            )

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

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
        message = f"Can't process response from server. Status Code: {r.status_code}\
              Data from server: {r.text.replace('{', '{{').replace('}', '}}')}"
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"),
                resp_json,
            )

        # Create a URL to connect to
        if "https://api.zerofox.com" in endpoint:
            url = endpoint
        else:
            url = self._base_url + endpoint

        try:
            r = request_func(url, verify=config.get("verify_server_cert", False), **kwargs)
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    "Error Connecting to server. Details: {0}".format(str(e)),
                ),
                resp_json,
            )

        return self._process_response(r, action_result)

    def _test_connectivity(self, param):
        self.save_progress("Checking ZeroFOX API Credentials...")
        self.save_progress(f"token={self._api_key}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        headers = self._get_app_headers()

        endpoint = "/1.0/users/me/"
        url = ZEROFOX_API_URL + endpoint

        ret_val, _ = self._make_rest_call(url, action_result, params=None, headers=headers)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _phantom_daterange(self, param):
        """
        Extract Phantom start time and end time as datetime objects.
        Divide by 1000 to resolve milliseconds.

        :param param: dict
        :return: start_time, end_time
        """
        try:
            start_time_param = float(param.get("start_time"))
            end_time_param = float(param.get("end_time"))
        except TypeError:
            self.error_print("start time or end time not specified")
            return None, None

        return datetime.fromtimestamp(start_time_param / 1000.0), datetime.fromtimestamp(end_time_param / 1000.0)

    def _save_alert(self, alert):
        self.debug_print("----------------------------------------")
        self.debug_print("PREPARE ALERT CONTAINER")
        self.debug_print("----------------------------------------")

        container = self.mapper.prepare_alert_container(alert)
        self.debug_print(f"container: {container}")

        status, message, container_id = self.save_container(container)

        if status == phantom.APP_SUCCESS and message != "Duplicate container found":
            alert_artifacts = self.mapper.build_artifact(container_id, alert)
            self.save_artifact(alert_artifacts)
            self.save_progress("Created the alert `successfully`")
            return status, message, container_id
        else:
            return status, message, container_id

    def _on_poll(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        self.debug_print(f"Param: {param}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.debug_print("----------------------------------------")
        self.debug_print("ON POLL CONNECTOR")
        self.debug_print("----------------------------------------")

        start_time, end_time = self._phantom_daterange(param)

        if start_time is None or end_time is None:
            action_result.set_status(phantom.APP_ERROR, status_message="start time or end time not specified")

        else:
            self.save_progress("Start to create alerts")
            self.save_progress(f"incident interval_days: {self._history_days_interval}")

            history_date = datetime.utcnow() - timedelta(int(self._history_days_interval))

            # reformat date to use with last_modified_min_date
            interval_startdate = history_date.strftime("%Y-%m-%d %H:%M:%S")

            self.save_progress(f"incident interval_startdate: {interval_startdate}")

            alert_types = []
            alert_types.append({"type": "ALL", "subTypes": "ALL"})

            self.debug_print("----------------------------------------")
            self.debug_print("Get All Alerts")
            self.debug_print("----------------------------------------")

            # check if we have a last_checked
            self.debug_print(f"self._state: {self._state}")
            self.debug_print(f"self._state type: {type(self._state)}")

            try:
                last_checked_alert_time = self._state["last_polled"]
                last_checked_alert_time = last_checked_alert_time.strftime("%Y-%m-%d %H:%M:%S")
            except:
                last_checked_alert_time = interval_startdate

            self.debug_print("last_checked_alert_time: {}".format(last_checked_alert_time))

            if self.is_poll_now():
                self.debug_print("POLL NOW")
                self.debug_print(param.get("artifact_count", 0))

                alert_params = {
                    "status": "open,escalated,investigation_completed",
                    "limit": "%s" % str(param.get("artifact_count", 0)),
                    "last_modified_min_date": "%s" % str(last_checked_alert_time),
                }

            else:
                self.debug_print("NORMAL POLL")

                alert_params = {
                    "status": "open,escalated,investigation_completed",
                    "last_modified_min_date": "%s" % str(last_checked_alert_time),
                }

            if self._reviewed:
                alert_params["reviewed"] = "true"

            # build call
            endpoint = "/1.0/alerts/"

            headers = self._get_app_headers()

            self.debug_print(f"token={self._api_key}")
            self.debug_print(f"params={alert_params}")

            # make rest call
            ret_val, response = self._make_rest_call(endpoint, action_result, params=alert_params, headers=headers)

            if phantom.is_fail(ret_val):
                # the call to the 3rd party device or service failed, action result should contain all the error details
                # for now the return is commented out, but after implementation, return from here
                return action_result.get_status()

            self.debug_print("----------------------------------------")

            if self.is_poll_now():
                alert_total = param.get("artifact_count", 0)
            else:
                alert_total = response["count"]

            self.debug_print(f"count: {alert_total}")
            self.debug_print(f"num_pages: {response['num_pages']}")
            self.debug_print(f"next_url: {response['next']}")
            self.debug_print("----------------------------------------")

            num_processed = 0
            next_url = response["next"]

            self.debug_print("parsing through list of alerts...")

            for alert in response["alerts"]:
                alert_id = alert["id"]

                self.debug_print("alert_id: {}".format(alert_id))

                # create container
                status, message, container_id = self._save_alert(alert)

                if status == phantom.APP_SUCCESS:
                    num_processed += 1
                    self.save_progress(f"ZeroFOX Alert {alert_id} ingested ({num_processed} of {alert_total})")
                else:
                    self.error_print(f"Did not ingest alert {alert_id}")
                    action_result.set_status(phantom.APP_ERROR, message)
                    self.add_action_result(action_result)
                    return action_result.get_status()

                # dont continue to get more than max if polling now
                if not self.is_poll_now():
                    while next_url:
                        self.debug_print("next_url: {}".format(next_url))

                        alert_params = None

                        # make rest call
                        ret_val, response = self._make_rest_call(next_url, action_result, params=None, headers=headers)

                        if phantom.is_fail(ret_val):
                            # the call to the 3rd party device or service failed, action result should contain all the error details
                            # for now the return is commented out, but after implementation, return from here
                            return action_result.get_status()

                        next_url = response["next"]

                        for alert in response["alerts"]:
                            alert_id = alert["id"]

                            self.debug_print(f"alert_id: {alert_id}")

                            # create container
                            status, message, container_id = self._save_alert(alert)

                            if status == phantom.APP_SUCCESS:
                                num_processed += 1
                                self.save_progress(f"ZeroFOX Alert {alert_id} ingested ({num_processed} of {alert_total})")
                            else:
                                self.error_print(f"Did not ingest alert {alert_id}")
                                action_result.set_status(phantom.APP_ERROR, message)
                                self.add_action_result(action_result)
                                return action_result.get_status()

            # set state
            if not self.is_poll_now() and alert_total > 0:
                state_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
                self.debug_print("updating _state to {}".format(state_time))

                self._state["last_polled"] = state_time
                self.debug_print(f"saved state: {self._state}")

            self.save_progress("Ingesting ZeroFOX Alerts Completed.")

            if num_processed != alert_total:
                action_result.set_status(
                    phantom.APP_ERROR,
                    status_message="Did not receive all the alerts from ZeroFOX",
                )
            else:
                action_result.set_status(phantom.APP_SUCCESS)

        self.debug_print("*** ENDING ***")
        self.debug_print(f"updating to {action_result.get_status()}")

        self.add_action_result(action_result)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_alert_by_id(self, param):
        self.debug_print("----------------------------------------")
        self.debug_print("get_alert_by_id")
        self.debug_print("----------------------------------------")
        self.debug_print(f"Param: {param}")

        action_result = ActionResult(dict(param))
        self.add_action_result(action_result)
        self.debug_print("Initial action_result dictionary: {}".format(action_result.get_dict()))

        alert_id = param.get("alert_id", 0.0)

        try:
            if isinstance(alert_id, float):
                return action_result.set_status(
                    phantom.APP_ERROR,
                    "Please provide a valid integer value in the 'alert_id' parameter",
                )
            alert_id = int(alert_id)
        except:
            return action_result.set_status(
                phantom.APP_ERROR,
                "Please provide a valid integer value in the 'alert_id' parameter",
            )

        if alert_id < 0:
            return action_result.set_status(
                phantom.APP_ERROR,
                "Please provide a valid non-negative integer value in the 'alert_id' parameter",
            )

        endpoint = f"/1.0/alerts/{alert_id}/"

        headers = self._get_app_headers()

        self.debug_print(f"token={self._api_key}")

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, params=None, headers=headers)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        self.debug_print(f"response={response}")

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["alert_found"] = True
        summary["alert_type"] = response["alert"]["alert_type"]

        self.debug_print("Updating the action_result summary.")
        action_result.update_summary(summary)

        # Return success, no need to set the message, only the status
        self.save_progress("Get Alert Passed")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _modify_alert_tag(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        self.debug_print(f"Param: {param}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        alert_id = param.get("alert_id")
        alert_tag = param.get("alert_tag")
        tag_action = param.get("tag_action", "add")

        self.save_progress(f"Adding tag {alert_tag} to alert {alert_id}")

        endpoint = "/1.0/alerttagchangeset/"

        headers = self._get_app_headers()
        changes = {"alert": alert_id}
        if tag_action == "add":
            changes["added"] = [alert_tag]
            changes["removed"] = []
        else:
            changes["added"] = []
            changes["removed"] = [alert_tag]

        params = {"changes": [changes]}

        self.debug_print(f"token={self._api_key}")
        self.debug_print(f"params={params}")

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, method="post", json=params, headers=headers)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            return action_result.get_status()

        if phantom.is_fail(ret_val):
            action_result.set_status(
                phantom.APP_ERROR,
                f"Error adding tag {alert_tag} on alert for: {alert_id}",
            )
            self.debug_print(f"Interim action_result dictionary after adding FAILURE status: {action_result.get_dict()}")
            summary = action_result.update_summary({})
            summary["status"] = "failed"
            return action_result.set_status(phantom.APP_ERROR)

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_alerts"] = 1
        summary["status"] = "success"

        # Return success, no need to set the message, only the status
        self.save_progress("Alert Tag Passed")

        self.debug_print("--------------------")
        self.debug_print(f"{self._banner} response: {response}")
        self.debug_print("--------------------")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _threat_submit(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        self.debug_print(f"Param: {param}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        source = param.get("source")
        alert_type = param.get("alert_type")
        violation = param.get("violation")
        asset_id = param.get("asset_id")

        self.save_progress(f"Threat submission {source} to asset {asset_id}")

        endpoint = "/2.0/threat_submit/"

        headers = self._get_app_headers()

        params = {
            "source": source,
            "alert_type": alert_type,
            "violation": violation,
            "entity_id": asset_id,
        }

        self.debug_print(f"token={self._api_key}")
        self.debug_print(f"params={params}")

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, method="post", json=params, headers=headers)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            return action_result.get_status()

        if phantom.is_fail(ret_val):
            action_result.set_status(
                phantom.APP_ERROR,
                f"Error adding threat {source} on entity for: {asset_id}",
            )
            self.debug_print(f"Interim action_result dictionary after adding FAILURE status: {action_result.get_dict()}")
            summary = action_result.update_summary({})
            summary["status"] = "failed"
            return action_result.set_status(phantom.APP_ERROR)

        # Add the response into the data section
        action_result.add_data(response)

        self.debug_print(f"threat_response={response}")

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_alerts"] = 1
        summary["status"] = "success"
        summary["alert_id"] = response["alert_id"]

        # Return success, no need to set the message, only the status
        self.save_progress("Threat Submit Passed")

        self.debug_print("--------------------")

        self.debug_print("%s response: %s" % (self._banner, response))
        self.debug_print("--------------------")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _modify_notes(self, param):
        self.debug_print(f"Param: {param}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        alert_id = param.get("alert_id")

        endpoint = f"/1.0/alerts/{alert_id}/"
        headers = self._get_app_headers()

        ret_val, response = self._make_rest_call(endpoint, action_result, method="get", headers=headers)

        if phantom.is_fail(ret_val):
            action_result.set_status(
                phantom.APP_ERROR,
                f"Error fetching alert with id: {alert_id}",
            )
            self.debug_print(f"Interim action_result dictionary after adding FAILURE status: {action_result.get_dict()}")
            summary = action_result.update_summary({})
            summary["status"] = "failed"
            return action_result.set_status(phantom.APP_ERROR)

        alert = response.get("alert", {})

        if not alert:
            self.debug_print(f"Failed to obtain data of alert id: {alert_id}")
            summary = action_result.update_summary({})
            summary["status"] = "failed"
            return action_result.set_status(phantom.APP_ERROR)

        action = param.get("modify_action", "append")
        previous_notes = alert.get("notes", "")
        notes = param.get("notes", "")
        new_notes = ""
        if action == "replace":
            new_notes = notes
        elif action == "append":
            new_notes = notes if not previous_notes else f"{previous_notes}\n{notes}"
        else:
            self.debug_print(f"Modify notes failed because it found action: {action}")
            summary = action_result.update_summary({})
            summary["status"] = "failed"
            return action_result.set_status(phantom.APP_ERROR)

        ret_val, response = self._make_rest_call(
            endpoint,
            action_result,
            method="post",
            json={"notes": new_notes},
            headers=headers,
        )

        if phantom.is_fail(ret_val):
            action_result.set_status(
                phantom.APP_ERROR,
                f"Error changing notes on alert for {alert_id}, with notes {notes}",
            )
            self.debug_print(f"Interim action_result dictionary after adding FAILURE status: {action_result.get_dict()}")
            summary = action_result.update_summary({})
            summary["status"] = "failed"
            return action_result.set_status(phantom.APP_ERROR)

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_alerts"] = 1
        summary["status"] = "success"

        self.save_progress("Notes Modified Succesfully")
        self.debug_print(f"{self._banner} response: {response}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _take_alert_action(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        self.debug_print(f"Param: {param}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        alert_id = param.get("alert_id")
        alert_action = param.get("alert_action", "close")

        self.save_progress(f"Issuing {alert_action} on alert {alert_id}")
        endpoint = f"/1.0/alerts/{alert_id}/{alert_action}/"

        headers = self._get_app_headers()

        params = {"actor": "%s" % self._actor}

        self.debug_print(f"token={self._api_key}")
        self.debug_print(f"params={params}")

        # make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, method="post", json=params, headers=headers)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            return action_result.get_status()

        if phantom.is_fail(ret_val):
            action_result.set_status(
                phantom.APP_ERROR,
                f"Error taking {alert_action} action on alert data for: {alert_id}",
            )
            self.debug_print(f"Interim action_result dictionary after adding FAILURE status: {action_result.get_dict()}")
            summary = action_result.update_summary({})
            summary["status"] = "failed"
            return action_result.set_status(phantom.APP_ERROR)

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_alerts"] = 1
        summary["status"] = "success"

        # Return success, no need to set the message, only the status
        self.save_progress("Alert Action Passed")

        self.debug_print("--------------------")
        self.debug_print("%s response: %s" % (self._banner, response))
        self.debug_print("--------------------")

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())
        self.debug_print(f"Ingesting handle action in: {param}")

        if action_id == "test_connectivity":
            ret_val = self._test_connectivity(param)

        elif action_id == "get_alert_by_id":
            ret_val = self._get_alert_by_id(param)

        elif action_id == "take_alert_action":
            ret_val = self._take_alert_action(param)

        elif action_id == "modify_alert_tag":
            ret_val = self._modify_alert_tag(param)

        elif action_id == "threat_submit":
            ret_val = self._threat_submit(param)

        elif action_id == "modify_notes":
            ret_val = self._modify_notes(param)

        elif action_id == "on_poll":
            ret_val = self._on_poll(param)

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

        self._base_url = ZEROFOX_API_URL
        self._api_key = config.get("zerofox_api_token")
        self._history_days_interval = config.get("history_days_interval")
        self._reviewed = config.get("reviewed")
        self._container_label = config["ingest"]["container_label"]
        self._actor = config.get("username")
        self._banner = "ZeroFOX Alerts Connector"
        self.zf_client = ZeroFoxClient(token=config.get("zerofox_api_token"), username=config.get("username"))
        self.mapper = AlertMapper(self._container_label, self.get_app_id())

        return phantom.APP_SUCCESS

    def finalize(self):
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
            login_url = ZerofoxAlertsConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = f"csrftoken={csrftoken}"
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print(f"Unable to get session id from the platform. Error: {e}")
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = ZerofoxAlertsConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
