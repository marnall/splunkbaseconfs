# Copyright (c) 2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# File: cybereason_connector.py
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

import json
import traceback

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
from cybereason_consts import *
from cybereason_poller import CybereasonPoller
from cybereason_query_actions import CybereasonQueryActions
from cybereason_session import CybereasonSession


try:
    from urllib import unquote
except:
    from urllib.parse import unquote


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class CybereasonConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = {}

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None

    def _get_string_param(self, param):
        return param

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove the script, style, footer and navigation part from the HTML message
            for element in soup(["script", "style", "footer", "nav", "title"]):
                element.extract()
            soup.prettify()
            error_text = soup.get_text(separator="\n")
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"
        message = unquote(message)

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # Process an HTML response
        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _get_error_message_from_exception(self, e):
        """This method is used to get appropriate error messages from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = ERROR_CODE_MESSAGE
        error_message = ERROR_MESSAGE_UNAVAILABLE
        try:
            if e.args:
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except:
            pass

        return f"Error Code: {error_code}. Error Message: {error_message}"

    def _validate_integer(self, action_result, parameter, key):
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, INVALID_INTEGER_ERROR_MESSAGE.format(key)), None

                parameter = int(parameter)
            except:
                return action_result.set_status(phantom.APP_ERROR, INVALID_INTEGER_ERROR_MESSAGE.format(key)), None

            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, INVALID_NON_NEGATIVE_INTEGER_ERROR_MESSAGE.format(key)), None

        return phantom.APP_SUCCESS, parameter

    def _handle_test_connectivity(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Set up a session by logging in to the Cybereason console.
        cr_session = CybereasonSession(self)
        cookies = cr_session.get_session_cookies()
        if cookies.get("JSESSIONID"):
            # We have a session id cookie, so the authentication succeeded
            self.save_progress("Successfully connected to the Cybereason console and verified session cookie")
            return action_result.set_status(phantom.APP_SUCCESS, "Successfully connected to the Cybereason console and verified session cookie")
        else:
            self.debug_print("Failure to verify session cookie.")
            return action_result.set_status(phantom.APP_ERROR, "Connectivity failed. Unable to get session cookie from Cybereason console")

    def _get_delete_registry_key_body(self, cr_session, malop_id, machine_name, action_result):
        query = {
            "queryPath": [
                {
                    "requestedType": "MalopProcess",
                    "filters": [],
                    "guidList": [malop_id],
                    "connectionFeature": {"elementInstanceType": "MalopProcess", "featureName": "suspects"},
                },
                {"requestedType": "Process", "filter": [], "isResult": True},
            ],
            "totalResultLimit": 100,
            "perGroupLimit": 100,
            "perFeatureLimit": 100,
            "templateContext": "SPECIFIC",
            "queryTimeout": 120000,
            "customFields": ["ownerMachine", "hasAutorunEvidence"],
        }
        url = f"{self._base_url}/rest/visualsearch/query/simple"
        res = cr_session.post(url=url, json=query, headers=self._headers)

        if res.status_code < 200 or res.status_code >= 399:
            return self._process_response(res, action_result)

        results = res.json()
        remediate_body = {"malopId": malop_id, "actionsByMachine": {}, "initiatorUserName": ""}
        target_ids_added = set()
        for _, process_data in results["data"]["resultIdToElementDataMap"].items():
            if process_data["elementValues"].get("hasAutorunEvidence"):
                target_id = process_data["elementValues"]["hasAutorunEvidence"]["elementValues"][0]["guid"]
                matching_machines = list(
                    filter(
                        lambda machine: machine["name"].lower() == machine_name, process_data["elementValues"]["ownerMachine"]["elementValues"]
                    )
                )
                if len(matching_machines) > 0:
                    machine_id = matching_machines[0]["guid"]
                    if not remediate_body["actionsByMachine"].get(machine_id):
                        remediate_body["actionsByMachine"][machine_id] = []
                    if target_id not in target_ids_added:
                        remediate_body["actionsByMachine"][machine_id].append({"targetId": target_id, "actionType": "DELETE_REGISTRY_KEY"})
                        target_ids_added.add(target_id)

        return RetVal(phantom.APP_SUCCESS, remediate_body)

    def _handle_delete_registry_key(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        malop_id = self._get_string_param(param["malop_id"])
        machine_name = param["machine_name"].lower()

        # Get the remediation target
        cr_session = CybereasonSession(self).get_session()
        try:
            ret_val, remediate_body = self._get_delete_registry_key_body(cr_session, malop_id, machine_name, action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status()

            # Make the call to remediate the action
            res = cr_session.post(f"{self._base_url}/rest/remediate", json=remediate_body, headers=self._headers)

            if res.status_code < 200 or res.status_code >= 399:
                self._process_response(res, action_result)
                return action_result.get_status()

            result = res.json()
            action_result.add_data({"remediation_id": result["remediationId"], "initiating_user": result["initiatingUser"]})
        except Exception as e:
            error = self._get_error_message_from_exception(e)
            self.debug_print(f"Error occurred: {error}")
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_sensor_status(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        malop_id = self._get_string_param(param["malop_id"])

        try:
            # Set up a session by logging in to the Cybereason console.
            cr_session = CybereasonSession(self).get_session()
            url = f"{self._base_url}/rest/visualsearch/query/simple"
            post_data = {
                "queryPath": [
                    {
                        "requestedType": "MalopProcess",
                        "filters": [],
                        "guidList": [malop_id],
                        "connectionFeature": {"elementInstanceType": "MalopProcess", "featureName": "suspects"},
                    },
                    {
                        "requestedType": "Process",
                        "filters": [],
                        "connectionFeature": {"elementInstanceType": "Process", "featureName": "ownerMachine"},
                    },
                    {"requestedType": "Machine", "filters": [], "isResult": True},
                ],
                "totalResultLimit": 1000,
                "perGroupLimit": 1200,
                "perFeatureLimit": 1200,
                "templateContext": "SPECIFIC",
                "queryTimeout": 30,
                "customFields": ["isConnected", "elementDisplayName"],
            }
            res = cr_session.post(url=url, headers=self._headers, json=post_data)

            if res.status_code < 200 or res.status_code >= 399:
                self._process_response(res, action_result)
                return action_result.get_status()

            self.save_progress("Successfully fetched machine details from Cybereason console")
            machines_dict = res.json()["data"]["resultIdToElementDataMap"]

            for machine_id, machine_details in machines_dict.items():
                action_result.add_data(
                    {
                        "machine_id": machine_id,
                        "machine_name": machine_details["simpleValues"]["elementDisplayName"]["values"][0],
                        "status": "Online" if machine_details["simpleValues"]["isConnected"]["values"][0] == "true" else "Offline",
                    }
                )
        except Exception as e:
            error = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_add_malop_comment(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        malop_id = self._get_string_param(param["malop_id"])
        self.save_progress(f"MALOP ID  :{malop_id}")

        comment = param.get("comment", "")
        self.save_progress(f"COMMENT  :{comment}")

        try:
            cr_session = CybereasonSession(self).get_session()

            endpoint_url = "/rest/crimes/comment/"
            url = f"{self._base_url}{endpoint_url}{malop_id!s}"
            self.save_progress(f"Add malop comment URL: {url}")

            res = cr_session.post(url, data=comment.encode("utf-8"), headers=self._headers)

            if res.status_code < 200 or res.status_code >= 399:
                self._process_response(res, action_result)
                return action_result.get_status()
        except requests.exceptions.ConnectionError:
            error = "Error Details: Connection refused from the server"
            return action_result.set_status(phantom.APP_ERROR, error)
        except Exception as e:
            error = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}")

        return action_result.set_status(phantom.APP_SUCCESS, "Add malop comment action executed successfully")

    def _handle_update_malop_status(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        malop_id = self._get_string_param(param["malop_id"])

        soar_status = param["status"]
        cybereason_status = SOAR_TO_CYBEREASON_STATUS.get(soar_status)
        if not cybereason_status:
            self.save_progress("Invalid status selected")
            return action_result.set_status(phantom.APP_ERROR, "Invalid status. Please provide a valid value in the 'status' action parameter")

        try:
            cr_session = CybereasonSession(self).get_session()

            url = f"{self._base_url}/rest/crimes/status"
            self.save_progress(f"Update malop status URL: {url}")
            query = json.dumps({malop_id: cybereason_status})
            res = cr_session.post(url, data=query, headers=self._headers)

            if res.status_code < 200 or res.status_code >= 399:
                self._process_response(res, action_result)
                return action_result.get_status()

        except Exception as e:
            error = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}")

        return action_result.set_status(phantom.APP_SUCCESS, "Update malop status action executed successfully")

    def _handle_isolate_machine(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        malop_id = self._get_string_param(param["malop_id"])
        ret_val, sensor_ids = self._get_malop_sensor_ids(malop_id, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            cr_session = CybereasonSession(self).get_session()

            url = f"{self._base_url}/rest/monitor/global/commands/isolate"
            self.save_progress(f"Isolate machine URL: {url}")
            query = json.dumps({"pylumIds": sensor_ids, "malopId": malop_id})

            res = cr_session.post(url, data=query, headers=self._headers)

            if res.status_code < 200 or res.status_code >= 399:
                self._process_response(res, action_result)
                return action_result.get_status()

        except Exception as e:
            error = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_unisolate_machine(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        malop_id = self._get_string_param(param["malop_id"])
        ret_val, sensor_ids = self._get_malop_sensor_ids(malop_id, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            cr_session = CybereasonSession(self).get_session()

            url = f"{self._base_url}/rest/monitor/global/commands/un-isolate"
            self.save_progress(f"Unisolate machine URL: {url}")
            query = json.dumps({"pylumIds": sensor_ids, "malopId": malop_id})

            res = cr_session.post(url, data=query, headers=self._headers)

            if res.status_code < 200 or res.status_code >= 399:
                self._process_response(res, action_result)
                return action_result.get_status()

        except Exception as e:
            error = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_isolate_specific_machine(self, param):
        """
        Isolate the machine with specified name or ip. The machine with the id provided as parameter will be
        disconnected from the network
        Parameters:
            param: object containing either the machine name or ip

        Returns:
            Action results
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        machine_name_or_ip = self._get_string_param(param["machine_name_or_ip"])
        ret_val, sensor_ids = self._get_machine_sensor_ids(machine_name_or_ip, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            cr_session = CybereasonSession(self).get_session()

            url = f"{self._base_url}/rest/monitor/global/commands/isolate"
            self.save_progress(f"Isolate specific machine URL: {url}")
            query = json.dumps({"pylumIds": sensor_ids})

            res = cr_session.post(url, data=query, headers=self._headers)

            if res.status_code < 200 or res.status_code >= 399:
                self._process_response(res, action_result)
                return action_result.get_status()
            action_result.add_data({"response_code_from_server": res.status_code, "response_from_server": res.json()})
        except Exception as e:
            error = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_unisolate_specific_machine(self, param):
        """
        Un-isolate the machine with specified Name or IP. The machine with the id provided as parameter will be
        connected to the network again.
        Parameters:
            param: object containing either the machine name or IP
        Returns:
            Action results
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        machine_name_or_ip = self._get_string_param(param.get("machine_name_or_ip"))
        ret_val, sensor_ids = self._get_machine_sensor_ids(machine_name_or_ip, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            cr_session = CybereasonSession(self).get_session()

            url = f"{self._base_url}/rest/monitor/global/commands/un-isolate"
            self.save_progress(f"Unisolate specific machine URL: {url}")
            query = json.dumps({"pylumIds": sensor_ids})

            res = cr_session.post(url, data=query, headers=self._headers)
            if res.status_code < 200 or res.status_code >= 399:
                self._process_response(res, action_result)
                return action_result.get_status()
            action_result.add_data({"response_code_from_server": res.status_code, "response_from_server": res.json()})
        except Exception as e:
            error = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_kill_process(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        malop_id = self._get_string_param(param["malop_id"])
        machine_id = self._get_string_param(param["machine_id"])
        remediation_user = param["remediation_user"]
        process_id = self._get_string_param(param["process_id"])

        try:
            cr_session = CybereasonSession(self).get_session()
            url = f"{self._base_url}/rest/remediate"
            query = {
                "malopId": malop_id,
                "initiatorUserName": remediation_user,
                "actionsByMachine": {machine_id: [{"targetId": process_id, "actionType": "KILL_PROCESS"}]},
            }
            res = cr_session.post(url, json=query, headers=self._headers)

            if res.status_code < 200 or res.status_code >= 399:
                self._process_response(res, action_result)
                return action_result.get_status()

            result = res.json()
            if len(result["statusLog"]) > 0:
                action_result.add_data({"remediation_id": result["remediationId"], "remediation_status": result["statusLog"][0]["status"]})
        except Exception as e:
            error = self._get_error_message_from_exception(e)
            self.debug_print(error)
            self.debug_print(traceback.format_exc())
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_remediation_status(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        malop_id = self._get_string_param(param["malop_id"])
        remediation_user = param["remediation_user"]
        remediation_id = param["remediation_id"]

        try:
            cr_session = CybereasonSession(self).get_session()
            url = f"{self._base_url}/rest/remediate/progress/{remediation_user}/{malop_id}/{remediation_id}"
            res = cr_session.get(url)

            if res.status_code < 200 or res.status_code >= 399:
                self._process_response(res, action_result)
                return action_result.get_status()

            result = res.json()
            status_log_length = len(result["statusLog"])
            error_obj = result["statusLog"][status_log_length - 1]["error"]
            action_result.add_data(
                {
                    "remediation_status": result["statusLog"][status_log_length - 1]["status"],
                    "remediation_message": error_obj.get("message", "Unknown error") if error_obj is not None else "No error message",
                }
            )
        except requests.exceptions.ConnectionError:
            error = "Error Details: Connection refused from the server"
            return action_result.set_status(phantom.APP_ERROR, error)
        except Exception as e:
            error = self._get_error_message_from_exception(e)
            self.debug_print(error)
            self.debug_print(traceback.format_exc())
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_set_reputation(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        reputation_item = self._get_string_param(param.get("reputation_item_hash"))
        custom_reputation = param.get("custom_reputation")
        if custom_reputation not in CUSTOM_REPUTATION_LIST:
            return action_result.set_status(phantom.APP_ERROR, "Please provide a valid value for the 'custom_reputation' action parameter")

        try:
            cr_session = CybereasonSession(self).get_session()

            url = f"{self._base_url}/rest/classification/update"
            self.save_progress(f"Set reputation URL: {url}")
            if custom_reputation == "remove":
                reputation = json.dumps([{"keys": [reputation_item], "maliciousType": None, "prevent": False, "remove": True}])
            else:
                reputation = json.dumps([{"keys": [reputation_item], "maliciousType": custom_reputation, "prevent": False, "remove": False}])

            res = cr_session.post(url, data=reputation, headers=self._headers)
            if res.status_code < 200 or res.status_code >= 399:
                self._process_response(res, action_result)
                return action_result.get_status()

            self.save_progress(f"{custom_reputation}ed...")
        except Exception as e:
            error = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}")

        return action_result.set_status(phantom.APP_SUCCESS, "Set reputation action executed successfully")

    def _get_malop_sensor_ids(self, malop_id, action_result):
        sensor_ids = []
        try:
            cr_session = CybereasonSession(self).get_session()

            url = f"{self._base_url}/rest/visualsearch/query/simple"
            self.save_progress(f"Get malop sensor IDs URL: {url}")
            query_path = {
                "queryPath": [
                    {
                        "requestedType": "MalopProcess",
                        "filters": [],
                        "guidList": [malop_id],
                        "connectionFeature": {"elementInstanceType": "MalopProcess", "featureName": "suspects"},
                    },
                    {
                        "requestedType": "Process",
                        "filters": [],
                        "connectionFeature": {"elementInstanceType": "Process", "featureName": "ownerMachine"},
                    },
                    {"requestedType": "Machine", "filters": [], "isResult": True},
                ],
                "totalResultLimit": 1000,
                "perGroupLimit": 1200,
                "perFeatureLimit": 1200,
                "templateContext": "SPECIFIC",
                "queryTimeout": None,
                "customFields": ["pylumId", "elementDisplayName"],
            }
            self.save_progress(str(query_path))
            res = cr_session.post(url, json=query_path, headers=self._headers)

            if res.status_code < 200 or res.status_code >= 399:
                return self._process_response(res, action_result)

            self.save_progress("Got result from /rest/visualsearch/query/simple")
            machines_dict = res.json()["data"]["resultIdToElementDataMap"]
            for _, machine_details in machines_dict.items():
                sensor_ids.append(str(machine_details["simpleValues"]["pylumId"]["values"][0]))

        except Exception as e:
            error = self._get_error_message_from_exception(e)
            self.save_progress(error)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}"), None)

        return RetVal(action_result.set_status(phantom.APP_SUCCESS), sensor_ids)

    def _get_machine_sensor_ids(self, machine_name_or_ip, action_result):
        sensor_ids = []
        try:
            ret_val, sensors_by_name = self._get_pylumid_by_machine_name(machine_name_or_ip, action_result)
            if not (phantom.is_fail(ret_val) or len(sensors_by_name) == 0):
                sensor_ids.extend(sensors_by_name)

            ret_val, sensors_by_ip = self._get_pylumid_by_machine_ip(machine_name_or_ip, action_result)
            if not (phantom.is_fail(ret_val) or len(sensors_by_ip) == 0):
                sensor_ids.extend(sensors_by_ip)
            action_result.add_data({"sensor_ids_by_machine_ip": sensors_by_ip, "sensor_ids_by_machine_name": sensors_by_name})
        except Exception as e:
            error = self._get_error_message_from_exception(e)
            self.save_progress(error)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}"), [])

        return RetVal(action_result.set_status(phantom.APP_SUCCESS), sensor_ids)

    def _get_pylumid_by_machine_name(self, machine_name, action_result):
        sensor_ids = []
        try:
            cr_session = CybereasonSession(self).get_session()

            url = f"{self._base_url}/rest/sensors/query"
            self.save_progress(f"Sensors query URL: {url}")
            query_path = {"limit": 1000, "offset": 0, "filters": [{"fieldName": "machineName", "operator": "Equals", "values": [machine_name]}]}
            self.save_progress(f"Calling {url} with query {query_path!s}")
            res = cr_session.post(url, json=query_path, headers=self._headers)
            if res.status_code < 200 or res.status_code >= 399:
                return self._process_response(res, action_result)

            self.save_progress(f"Got result from {url}")
            totalResults = res.json()["totalResults"]
            if totalResults > 0:
                sensors = res.json()["sensors"]
                for sensor in sensors:
                    sensor_ids.append(sensor["pylumId"])

        except Exception as e:
            error = self._get_error_message_from_exception(e)
            self.save_progress(error)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}"), [])

        return RetVal(action_result.set_status(phantom.APP_SUCCESS), sensor_ids)

    def _get_pylumid_by_machine_ip(self, machine_ip, action_result):
        sensor_ids = []
        try:
            cr_session = CybereasonSession(self).get_session()

            url = f"{self._base_url}/rest/sensors/query"
            self.save_progress(f"Sensors query URL: {url}")
            query_path = {
                "limit": 1000,
                "offset": 0,
                "filters": [{"fieldName": "externalIpAddress", "operator": "Equals", "values": [machine_ip]}],
            }
            self.save_progress(f"Calling {url} with query {query_path!s}")
            res = cr_session.post(url, json=query_path, headers=self._headers)

            if res.status_code < 200 or res.status_code >= 399:
                return self._process_response(res, action_result)

            self.save_progress(f"Got result from {url}")
            totalResults = res.json()["totalResults"]
            if totalResults > 0:
                sensors = res.json()["sensors"]
                for sensor in sensors:
                    sensor_ids.append(sensor["pylumId"])

        except Exception as e:
            error = self._get_error_message_from_exception(e)
            self.save_progress(error)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}"), [])

        return RetVal(action_result.set_status(phantom.APP_SUCCESS), sensor_ids)

    def _handle_upgrade_sensor(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Get the parameters
        pylum_id = self._get_string_param(param["pylumid"])

        try:
            # Create a session to call the rest APIs
            cr_session = CybereasonSession(self).get_session()

            url = f"{self._base_url}/rest/sensors/action/upgrade"
            self.save_progress(f"Upgrade sensor URL: {url}")
            pylum_ids = []
            # Look for the multiple sensor ids
            if "," in pylum_id:
                filter_arr = pylum_id.strip().split(",")
                filter_arr = [each_id.strip() for each_id in filter_arr]
                pylum_ids.extend(filter_arr)
            else:
                pylum_ids.append(pylum_id)
            query = json.dumps({"filters": [{"fieldName": "pylumId", "operator": "ContainsIgnoreCase", "values": pylum_ids}]})
            res = cr_session.post(url, data=query, headers=self._headers)
            if res.status_code == 204:
                return action_result.set_status(
                    phantom.APP_ERROR, "Status Code:204. The sensor names are incorrect or the filters are not valid"
                )
            if res.status_code < 200 or res.status_code >= 399:
                self._process_response(res, action_result)
                return action_result.get_status()

            self.save_progress("Sensors Upgrade Requested")
            json_res = res.json()
            action_result.update_summary(json_res)
            # Data will typically be the raw JSON if we need to use it in a playbook
            action_result.add_data(json_res)

        except Exception as e:
            error = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}")

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully requested for sensor upgrade")

    def _handle_restart_sensor(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Get the parameters
        pylum_id = self._get_string_param(param["pylumid"])

        try:
            # Create a session to call the rest APIs
            cr_session = CybereasonSession(self).get_session()

            url = f"{self._base_url}/rest/sensors/action/restart"
            self.save_progress(f"Restart sensor URL: {url}")

            pylum_ids = []
            if "," in pylum_id:
                filter_arr = pylum_id.strip().split(",")
                filter_arr = [each_id.strip() for each_id in filter_arr]
                pylum_ids.extend(filter_arr)
            else:
                pylum_ids.append(pylum_id)
            query = json.dumps({"filters": [{"fieldName": "pylumId", "operator": "ContainsIgnoreCase", "values": pylum_ids}]})

            res = cr_session.post(url, data=query, headers=self._headers)
            if res.status_code == 204:
                return action_result.set_status(
                    phantom.APP_ERROR, "Status Code:204. The sensor names are incorrect or the filters are not valid"
                )
            if res.status_code < 200 or res.status_code >= 399:
                self._process_response(res, action_result)
                return action_result.get_status()

            json_res = res.json()
            self.save_progress("Sensors Restart Requested")
            action_result.update_summary(json_res)
            # Data will typically be the raw JSON if we need to use it in a playbook
            action_result.add_data(json_res)

        except Exception as e:
            error = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}")

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully requested for sensor restart")

    def _get_machine_name_by_machine_ip(self, machine_ip, action_result):
        machine_names = []
        try:
            cr_session = CybereasonSession(self).get_session()

            url = f"{self._base_url}/rest/sensors/query"
            self.save_progress(f"Sensors query URL: {url}")
            query_path = {
                "limit": 1000,
                "offset": 0,
                "filters": [{"fieldName": "externalIpAddress", "operator": "Equals", "values": [machine_ip]}],
            }
            self.save_progress(f"Calling {url} with query {query_path!s}")
            res = cr_session.post(url, json=query_path, headers=self._headers)

            if res.status_code < 200 or res.status_code >= 399:
                return self._process_response(res, action_result)

            self.save_progress(f"Got result from {url}")
            totalResults = res.json()["totalResults"]
            if totalResults > 0:
                sensors = res.json()["sensors"]
                for sensor_details in sensors:
                    machine_names.append(str(sensor_details["machineName"]))

        except Exception as e:
            error = self._get_error_message_from_exception(e)
            self.save_progress(error)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error occurred. {error}"), None)

        return RetVal(action_result.set_status(phantom.APP_SUCCESS), machine_names)

    def on_poll(self, param):
        self.save_progress("Entered the on_poll function")
        self.save_progress("processing")
        poller = CybereasonPoller()
        return poller.do_poll(self, param)

    def _handle_query_processes(self, param):
        self.save_progress("Entered the _handle_query_processes function")
        self.save_progress("processing")
        query_action = CybereasonQueryActions()
        return query_action._handle_query_processes(self, param)

    def _handle_query_machine(self, param):
        self.save_progress("Entered the _handle_query_machine function")
        self.save_progress("processing")
        query_action = CybereasonQueryActions()
        return query_action._handle_query_machine(self, param)

    def _handle_query_machine_ip(self, param):
        self.save_progress("Entered the _handle_query_machine_ip function")
        self.save_progress("processing")
        query_action = CybereasonQueryActions()
        return query_action._handle_query_machine_ip(self, param)

    def _handle_query_users(self, param):
        self.save_progress("Entered the _handle_query_users function")
        self.save_progress("processing")
        query_action = CybereasonQueryActions()
        return query_action._handle_query_users(self, param)

    def _handle_query_files(self, param):
        self.save_progress("Entered the _handle_query_files function")
        self.save_progress("processing")
        query_action = CybereasonQueryActions()
        return query_action._handle_query_files(self, param)

    def _handle_query_domain(self, param):
        self.save_progress("Entered the _handle_query_domain function")
        self.save_progress("processing")
        query_action = CybereasonQueryActions()
        return query_action._handle_query_domain(self, param)

    def _handle_query_connections(self, param):
        self.save_progress("Entered the _handle_query_connections function")
        self.save_progress("processing")
        query_action = CybereasonQueryActions()
        return query_action._handle_query_connections(self, param)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print(f"action_id: {self.get_action_identifier()}")

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "delete_registry_key":
            ret_val = self._handle_delete_registry_key(param)

        elif action_id == "get_sensor_status":
            ret_val = self._handle_get_sensor_status(param)

        elif action_id == "on_poll":
            ret_val = self.on_poll(param)

        elif action_id == "add_malop_comment":
            ret_val = self._handle_add_malop_comment(param)

        elif action_id == "update_malop_status":
            ret_val = self._handle_update_malop_status(param)

        elif action_id == "isolate_machine":
            ret_val = self._handle_isolate_machine(param)

        elif action_id == "unisolate_machine":
            ret_val = self._handle_unisolate_machine(param)

        elif action_id == "isolate_specific_machine":
            ret_val = self._handle_isolate_specific_machine(param)

        elif action_id == "unisolate_specific_machine":
            ret_val = self._handle_unisolate_specific_machine(param)

        elif action_id == "kill_process":
            ret_val = self._handle_kill_process(param)

        elif action_id == "get_remediation_status":
            ret_val = self._handle_get_remediation_status(param)

        elif action_id == "set_reputation":
            ret_val = self._handle_set_reputation(param)

        elif action_id == "upgrade_sensor":
            ret_val = self._handle_upgrade_sensor(param)

        elif action_id == "restart_sensor":
            ret_val = self._handle_restart_sensor(param)

        elif action_id == "query_processes":
            ret_val = self._handle_query_processes(param)

        elif action_id == "query_machine":
            ret_val = self._handle_query_machine(param)

        elif action_id == "query_machine_ip":
            ret_val = self._handle_query_machine_ip(param)

        elif action_id == "query_users":
            ret_val = self._handle_query_users(param)

        elif action_id == "query_files":
            ret_val = self._handle_query_files(param)

        elif action_id == "query_domain":
            ret_val = self._handle_query_domain(param)

        elif action_id == "query_connections":
            ret_val = self._handle_query_connections(param)

        return ret_val

    def initialize(self):
        self._state = self.load_state()
        if not self._state:
            self._state = {}

        # get the asset config
        config = self.get_config()

        self._base_url = config.get("base_url", "").rstrip("/")  # Remove trailing '/' characters (if any) from URL
        self._username = config.get("username")
        self._password = config.get("password")
        self._verify_server_cert = config.get("verify_server_cert", False)
        self._headers = {"Content-Type": "application/json"}
        self._headers.update({"User-Agent": "CybereasonPhantom/2.1.0 (target=unknown)"})
        return phantom.APP_SUCCESS

    def get_state(self):
        return self._state

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse
    import sys

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = CybereasonConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, timeout=DEFAULT_REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, data=data, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = CybereasonConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
