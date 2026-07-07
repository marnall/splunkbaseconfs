# File: resilient_connector.py
#
# Copyright (c) 2022-2025 Splunk Inc.
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

import calendar
import datetime

# Usage of the consts file is recommended
# from resilient_consts import *
import json
import math
import sys
import time
import traceback

import dateutil.parser
import phantom.app as phantom
from phantom import vault
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from resilient_client import ResilientClient


# get string value: return "" if key not in dictionary, otherwise value
# deprecated use dict.get(key, "")
def getsv(dic, key):
    if key in dic:
        return dic[key]
    else:
        return ""


# add key as target_key to target dictionary if key exists in source dictionary
def addifkey(dic, key, tdic, tkey):
    if key in dic:
        tdic[tkey] = dic[key]


RESILIENT_SEVERITY_CODE_MAPPING = {4: "low", 5: "medium", 6: "high"}


class ResilientConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None

    def get_resilient_client(self):
        config = self.get_config()
        client_kwargs = {"org_name": config["org_id"], "base_url": config["base_url"], "verify": config.get("verify", False)}
        if config.get("user") is not None and config.get("password") is not None:
            client_kwargs.update({"username": config["user"], "password": config["password"]})
            self.log_to_both("Will authenticate with username and password.")
        elif config.get("api_key_id") is not None and config.get("api_key_secret") is not None:
            client_kwargs.update({"api_key_id": config["api_key_id"], "api_key_secret": config["api_key_secret"]})
            self.log_to_both("Will authenticate with API Key.")
        else:
            raise ValueError("No credentials (email & password) or API Key (ID & Secret) provided.")
        return ResilientClient(**client_kwargs)

    def _handle_test_connectivity(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        self.log_to_both(f"Param is {param}")

        self.get_resilient_client().authenticate()
        self.log_to_both("Connection successful.")

    def _handle_list_tickets(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        return self.get_resilient_client().list_incidents(closed=param["want_closed"])

    def _handle_get_ticket(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        return self.get_resilient_client().get_incident(incident_id=param["incident_id"])

    def _handle_create_ticket(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")

        client = self.get_resilient_client().simple_client
        call = "/incidents?want_full_data={}&want_tasks={}".format(param.get("want_full_data", True), param.get("want_tasks", False))

        fullincidentdatadto = getsv(param, "fullincidentdatadto")
        if len(fullincidentdatadto) > 1:
            payload = json.loads(fullincidentdatadto)
            if not isinstance(payload, dict):
                err = f"{action_id} failed. fullincidentdatadto field is not valid json object."
                raise ValueError(err)
        else:
            payload = dict()

        if "name" not in payload:
            addifkey(param, "incident_name", payload, "name")
        if "description" not in payload:
            addifkey(param, "incident_description", payload, "description")
        if "discovered_date" not in payload:
            payload["discovered_date"] = calendar.timegm(time.gmtime()) * 1000

        if "name" not in payload:
            raise ValueError("json payload does not have required 'name' key")
        if "description" not in payload:
            raise ValueError("json payload does not have required 'description' key")
        if "discovered_date" not in payload:
            raise ValueError("json payload does not have required 'discovered_date' key")

        self.log_to_both(f"POST {call}")
        self.log_to_both(f"BODY {payload}")
        resp = client.post(call, payload)
        self.log_to_both(f"{action_id} successful.")
        return resp

    def _handle_update_ticket(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        client = self.get_resilient_client().simple_client

        # validate incoming json
        fullincidentdatadto = param["fullincidentdatadto"]
        if len(fullincidentdatadto) > 1:
            payload = json.loads(fullincidentdatadto)
            if not isinstance(payload, dict):
                raise ValueError(f"{action_id} failed. fullincidentdatadto field is not valid json object.")
        else:
            payload = dict()

        call = "/incidents/{}".format(param["incident_id"])

        def apply(arg):
            arg.update(payload)
            return arg

        self.log_to_both(f"GET_PUT {call}")
        self.log_to_both(f"PAYLOAD {payload}")
        resp = client.get_put(call, apply)
        self.log_to_both(f"{action_id} successful.")
        return resp

    def _handle_search_tickets(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")

        client = self.get_resilient_client().simple_client
        if param.get("handle_format_is_name"):
            client.headers["handle_format"] = "names"

        querydto = getsv(param, "querydto")
        if len(querydto) > 1:
            payload = json.loads(querydto)
            if not isinstance(payload, dict):
                raise ValueError("querydto field is not valid JSON dict.")
        else:
            payload = dict()

        if "filters" in payload:
            filters = payload["filters"]
        else:
            filters = list()
            payload["filters"] = filters

        conditions = list()
        if param.get("add_condition_all_active_tickets", False) is True:
            conditions.append({"field_name": "plan_status", "method": "equals", "value": "A"})
        if param.get("add_condition_created_in_last_24_hours", False) is True:
            conditions.append(
                {
                    "field_name": "create_date",
                    "method": "gte",
                    "value": calendar.timegm((datetime.datetime.utcnow() - datetime.timedelta(days=1)).utctimetuple()) * 1000,
                }
            )
        if param.get("add_condition_closed_in_last_24_hours", False) is True:
            conditions.append(
                {
                    "field_name": "end_date",
                    "method": "gte",
                    "value": calendar.timegm((datetime.datetime.utcnow() - datetime.timedelta(days=1)).utctimetuple()) * 1000,
                }
            )

        for con in ["1st", "2nd", "3rd", "4th", "5th"]:
            try:
                name = getsv(param, f"{con}_condition_field_name")
                value = getsv(param, f"{con}_condition_field_value")
                method = getsv(param, f"{con}_condition_comparison_method")
                isdate = param.get(f"{con}_condition_value_is_datetime", False)

                ln = len(name)
                lv = len(value)
                lm = len(method)

                # no condition, skip
                if (ln + lv + lm) == 0:
                    self.log_to_both(f"{con} condition is not complete")
                    continue

                if isdate:
                    try:
                        value = calendar.timegm(dateutil.parser.parse(value).utctimetuple()) * 1000
                    except Exception as e:
                        self.log_to_both(f"Warning: {con} condition value is not a datetime as expected: {e}, skipping")
                        continue

                conditions.append({"field_name": name, "method": method, "value": value})
            except Exception as e:
                self.log_to_both(f"Warning: {con} condition not valid, skipping: {e}.")

        if len("conditions") == 0:
            self.log_to_both("json payload does not have 'conditions' key.")
            raise ValueError("json payload does not have 'conditions' key.")

        filters.append({"conditions": conditions})

        call = "/incidents/query?return_level=full"
        self.log_to_both(f"POST {call}")
        self.log_to_both(f"BODY {payload}")
        resp = client.post(call, payload)
        self.log_to_both(f"{action_id} successful.")
        return resp

    def _handle_list_artifacts(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        return self.get_resilient_client().list_artifcats_for_incident(incident_id=param["incident_id"])

    def _handle_get_artifact(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        return self.get_resilient_client().get_artifact(incident_id=param["incident_id"], artifact_id=param["artifact_id"])

    def _handle_create_artifact(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        client = self.get_resilient_client().simple_client

        incident_id = param["incident_id"]
        call = f"/incidents/{incident_id}/artifacts"

        incidentartifactdto = getsv(param, "incidentartifactdto")
        if len(incidentartifactdto) > 1:
            payload = json.loads(incidentartifactdto)
            if not isinstance(payload, dict):
                raise ValueError(f"{action_id} failed. incidentartifactdto field is not valid json.")
        else:
            payload = dict()

        if "description" not in payload:
            description = getsv(param, "description")
            if len(description) > 0:
                payload["description"] = description
                # addifkey(param, 'incident_description', payload, 'description')
                # payload['description'] = dict()
                # payload['description']['format'] = "text"
                # payload['description']['content'] = getsv(param, 'description')
        if "type" not in payload:
            type = getsv(param, "type").lower()
            if type == "url":
                type = 3
            elif type == "domain":
                type = 2
            elif type == "file":
                type = 13
            else:
                try:
                    type = int(type)
                except:
                    raise ValueError(f"{action_id} failed. Type is not recognized or not an integer")
            if type > 0:
                payload["type"] = type
        if "value" not in payload:
            addifkey(param, "value", payload, "value")

        if "type" not in payload:
            raise ValueError("json payload does not have required 'type' key")
        if "value" not in payload:
            raise ValueError("json payload does not have required 'value' key")
        if "description" not in payload:
            raise ValueError("json payload does not have required 'description' key")

        self.log_to_both(f"POST {call}")
        self.log_to_both(f"BODY {payload}")
        resp = client.post(call, payload)
        self.log_to_both(f"{action_id} successful.")
        return resp

    def _handle_update_artifact(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")

        client = self.get_resilient_client().simple_client
        incident_id = param["incident_id"]
        artifact_id = param["artifact_id"]
        call = f"/incidents/{incident_id}/artifacts/{artifact_id}"

        incidentartifactdto = getsv(param, "incidentartifactdto")
        if len(incidentartifactdto) > 1:
            payload = json.loads(incidentartifactdto)
            if not isinstance(payload, dict):
                raise ValueError(f"{action_id} failed. incidentartifactdto field is not valid json object.")
        else:
            payload = dict()

        if "type" not in payload:
            raise ValueError("json payload does not have 'type' key, payload should be result of get_artifact")
        if "value" not in payload:
            raise ValueError("json payload does not have 'value' key, payload should be result of get_artifact")
        if "description" not in payload:
            raise ValueError("json payload does not have 'description' key, payload should be result of get_artifact")

        self.log_to_both(f"PUT {call}")
        self.log_to_both(f"BODY {payload}")
        resp = client.put(call, payload)
        self.log_to_both(f"{action_id} successful.")
        return resp

    def _handle_list_comments(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        return self.get_resilient_client().list_comments_for_incident(incident_id=param["incident_id"])

    def _handle_get_comment(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        return self.get_resilient_client().get_comment(incident_id=param["incident_id"], comment_id=param["comment_id"])

    def _handle_create_comment(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        client = self.get_resilient_client().simple_client
        if param.get("handle_format_is_name"):
            client.headers["handle_format"] = "names"
        incident_id = param["incident_id"]
        call = f"/incidents/{incident_id}/comments"

        incidentcommentdto = getsv(param, "incidentcommentdto")
        if len(incidentcommentdto) > 1:
            payload = json.loads(incidentcommentdto)
            if not isinstance(payload, dict):
                raise ValueError(f"{action_id} failed. incidentcommentdto field is not valid json.")
        else:
            payload = dict()

        if "text" not in payload:
            addifkey(param, "text", payload, "text")
        if "parent_id" not in payload:
            addifkey(param, "parent_id", payload, "parent_id")

        if "text" not in payload:
            raise ValueError("json payload does not have required 'text' key")

        self.log_to_both(f"POST {call}")
        self.log_to_both(f"BODY {payload}")
        resp = client.post(call, payload)
        self.log_to_both(f"{action_id} successful.")
        return resp

    def _handle_update_comment(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        client = self.get_resilient_client().simple_client

        if param.get("handle_format_is_name"):
            client.headers["handle_format"] = "names"
        incident_id = self._handle_py_ver_compat_for_input_str(param["incident_id"])
        comment_id = self._handle_py_ver_compat_for_input_str(param["comment_id"])
        call = f"/incidents/{incident_id}/comments/{comment_id}"

        try:
            payload = json.loads(param["incidentcommentdto"])
            assert isinstance(payload, dict)
        except Exception:
            raise ValueError(f"{action_id} failed. incidentcommentdto field is not valid json.")

        if "text" not in payload:
            raise ValueError("json payload does not have required 'text' key, payload should be result of get comment")

        self.log_to_both(f"PUT {call}")
        self.log_to_both(f"BODY {payload}")
        resp = client.put(call, payload)
        self.log_to_both(f"{action_id} successful.")
        return resp

    def _handle_list_tables(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        return self.get_resilient_client().list_tables_for_incident(
            incident_id=param["incident_id"], use_handle_format_names=param["handle_format_is_name"]
        )

    def _handle_get_table(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        return self.get_resilient_client().get_table(
            incident_id=param["incident_id"], table_id=param["table_id"], use_handle_format_names=param["handle_format_is_name"]
        )

    def _handle_add_table_row(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        client = self.get_resilient_client().simple_client
        if param.get("handle_format_is_name"):
            client.headers["handle_format"] = "names"
        incident_id = param["incident_id"]
        table_id = param["table_id"]
        call = f"/incidents/{incident_id}/table_data/{table_id}/row_data"

        datatablerowdatadto = param.get("datatablerowdatadto", "")
        if len(datatablerowdatadto) > 1:
            try:
                payload = json.loads(datatablerowdatadto)
                assert isinstance(payload, dict)
            except Exception:
                raise ValueError(f"{action_id} failed. datatablerowdatadto field is not valid json.")
        else:
            payload = dict()

        for col in ["1st", "2nd", "3rd", "4th", "5th"]:
            key = param.get(f"{col}_cell_property", "")
            value = param.get(f"{col}_cell_value", "")
            if len(key) > 1 and len(value) > 1:
                payload["cells"][key] = value
            elif len(key) > 1 or len(value) > 1:
                self.log_to_both(f"{col} cell specification is not complete")
                continue

        self.log_to_both(f"POST {call}")
        self.log_to_both(f"BODY {payload}")
        retval = client.post(call, payload)
        self.log_to_both(f"{action_id} successful.")
        return retval

    def _handle_update_table_row(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        client = self.get_resilient_client().simple_client

        if param.get("handle_format_is_name"):
            client.headers["handle_format"] = "names"
        incident_id = self._handle_py_ver_compat_for_input_str(param["incident_id"])
        table_id = self._handle_py_ver_compat_for_input_str(param["table_id"])
        row_id = self._handle_py_ver_compat_for_input_str(param["row_id"])
        call = f"/incidents/{incident_id}/table_data/{table_id}/row_data/{row_id}"

        datatablerowdatadto = param.get("datatablerowdatadto", "")
        if len(datatablerowdatadto) > 1:
            try:
                payload = json.loads(datatablerowdatadto)
                assert isinstance(payload, dict)
            except Exception:
                raise ValueError(f"{action_id} failed. datatablerowdatadto field is not valid json.")
        else:
            payload = dict()

        for col in ["1st", "2nd", "3rd", "4th", "5th"]:
            key = param.get(f"{col}_cell_property", "")
            value = param.get(f"{col}_cell_value", "")
            if len(key) > 1 and len(value) > 1:
                payload["cells"][key] = value
            elif len(key) > 1 or len(value) > 1:
                self.log_to_both(f"{col} cell specification is not complete")
                continue

        self.log_to_both(f"PUT {call}")
        self.log_to_both(f"BODY {payload}")
        retval = client.put(call, payload)
        self.log_to_both(f"{action_id} successful.")
        return retval

    def _handle_update_table_row_with_key(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        client = self.get_resilient_client().simple_client
        if param.get("handle_format_is_name"):
            client.headers["handle_format"] = "names"

        datatablerowdatadto = param.get("datatablerowdatadto", "")
        if len(datatablerowdatadto) > 1:
            try:
                payload = json.loads(datatablerowdatadto)
                assert isinstance(payload, dict)
            except Exception:
                raise ValueError(f"{action_id} failed. datatablerowdatadto field is not valid json.")
        else:
            raise ValueError(f"{action_id} failed. datatablerowdatadto field is empty string.")

        # get table first
        incident_id = param["incident_id"]
        table_id = param["table_id"]
        call = f"/incidents/{incident_id}/table_data/{table_id}"
        self.log_to_both(f"GET {call}")
        retval = client.get(call)
        self.log_to_both("GET successful")

        def find_row(table, key, value):
            for row in table["rows"]:
                if key in row["cells"]:
                    if str(row["cells"][key]["value"]) == str(value):
                        return row["id"]
            return None

        key = param["key"]
        value = param["value"]
        rowid = find_row(retval, key, value)

        if rowid is None:
            raise ValueError(f"{action_id} failed. Cannot match {key}/{value} key/value.")

        call = f"/incidents/{incident_id}/table_data/{table_id}/row_data/{rowid}"
        self.log_to_both(f"PUT {call}")
        self.log_to_both(f"BODY {payload}")
        put_resp = client.put(call, payload)
        self.log_to_both(f"{action_id} successful.")
        return put_resp

    def _handle_list_tasks(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        client = self.get_resilient_client().simple_client
        if param.get("handle_format_is_name"):
            client.headers["handle_format"] = "names"
        call = "/tasks"
        self.log_to_both(f"GET {call}")
        resp = client.get(call)
        self.log_to_both(f"{action_id} successful.")
        return resp

    def _handle_get_task(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        client = self.get_resilient_client().simple_client
        if param.get("handle_format_is_name"):
            client.headers["handle_format"] = "names"
        call = f"/tasks/{param['task_id']}"
        self.log_to_both(f"GET {call}")
        resp = client.get(call)
        self.log_to_both(f"{action_id} successful.")
        return resp

    def _handle_update_task(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        client = self.get_resilient_client().simple_client
        taskdto = param.get("taskdto", "")
        if len(taskdto) > 1:
            try:
                payload = json.loads(taskdto)
                if not isinstance(payload, dict):
                    raise Exception
            except Exception:
                raise ValueError(f"{action_id} failed. taskdto field is not valid json.")
        else:
            payload = dict()

        if param.get("handle_format_is_name"):
            client.headers["handle_format"] = "names"
        task_id = param["task_id"]
        call = f"/tasks/{task_id}"

        def apply(arg):
            arg.update(payload)
            return arg

        self.log_to_both(f"GET_PUT {call}")
        self.log_to_both(f"PAYLOAD {payload}")
        retval = client.get_put(call, apply)
        self.log_to_both(f"{action_id} successful.")
        return retval

    def _handle_close_task(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        client = self.get_resilient_client().simple_client
        task_id = param["task_id"]
        call = f"/tasks/{task_id}"

        def apply(arg):
            arg["status"] = "C"
            return arg

        retval = client.get_put(call, apply)
        self.log_to_both(f"{action_id} successful.")
        return retval

    def _handle_list_attachments(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        return self.get_resilient_client().list_attachments_for_incident(
            incident_id=param["incident_id"], use_handle_format_names=param["handle_format_is_name"]
        )

    def _handle_get_attachment(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")
        return self.get_resilient_client().get_attachment(
            incident_id=param["incident_id"], attachment_id=param["attachment_id"], use_handle_format_names=param["handle_format_is_name"]
        )

    def _handle_add_attachment(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"In action handler for: {action_id}")

        success, message, vault_info = vault.vault_info(vault_id=param["vault_id"], container_id=self.get_container_id())
        self.log_to_both(f"Vault info resp: {success} {message} {vault_info}")
        if not success:
            err = "{} failed. {}: vault_id not valid.".format(action_id, param["vault_id"])
            self.log_to_both(err)
            raise ValueError(err)
        path = vault_info[0]["path"]
        name = vault_info[0]["name"]
        return self.get_resilient_client().post_attachment(incident_id=param["incident_id"], filepath=path, filename=name)

    @staticmethod
    def parse_resilient_severity(severity_code: int):
        return RESILIENT_SEVERITY_CODE_MAPPING.get(severity_code, "medium")

    @staticmethod
    def make_container(incident: dict, container_label: str, severity: str, run_automation: bool) -> dict:
        return {
            "name": incident["name"],
            "description": incident["description"],
            "label": container_label,
            "data": incident,
            "source_data_identifier": incident["id"],
            "severity": severity,
            "run_automation": run_automation,
        }

    @staticmethod
    def make_artifact(container_id: int, artifact: dict, severity: str) -> dict:
        return {
            "container_id": container_id,
            "source_data_identifier": artifact["id"],
            "data": artifact,
            "description": artifact["description"],
            "cef": artifact,
            "severity": severity,
        }

    def log_to_both(self, msg):
        self.debug_print(msg)
        self.save_progress(msg)

    def update_state_end_time(self, end_time):
        # state end_time used for state management for polling
        self._state["end_time"] = end_time
        self.save_state(self._state)
        self.log_to_both(f"Saved state: {self.load_state()}")

    @staticmethod
    def now_epoch_ms():
        return time.time_ns() // 1_000_000

    def _handle_on_poll(self, param):
        self.log_to_both("In action handler for: on_poll")
        self.log_to_both(f"Param={param}")
        max_timespan_ms = 1000 * 60 * 60 * 6  # 6 hours

        # When trigger as 'poll now', container_count is populated based on user input
        # When scheduled/interval, container_count is set to 4294967295 (max 32-bit int)
        # Using .get as safeguard.
        max_containers = param.get("container_count", math.inf)
        container_label = self.get_config()["ingest"]["container_label"]
        client = self.get_resilient_client()
        use_mock = False
        container_count = 0

        start_time = param.get("start_time")
        if "end_time" in self._state:
            start_time = self._state["end_time"]
            self.log_to_both("Using state to set start_time.")
        end_time = param.get("end_time")
        self.log_to_both(f"start_time={start_time}, end_time={end_time}")

        assert end_time <= self.now_epoch_ms()

        for incident in client.get_incidents_in_timerange_with_paging(
            start_epoch_timestamp_ms=start_time, end_epoch_timestamp_ms=end_time, max_timespan_in_ms_per_request=max_timespan_ms, mock=use_mock
        ):
            # https://docs.splunk.com/Documentation/SOAR/current/PlatformAPI/RESTContainers
            # See POST /rest/container
            severity = self.parse_resilient_severity(incident["severity_code"])
            container_count += 1
            incident_id = incident["id"]

            artifacts = client.list_artifcats_for_incident(incident_id=incident_id, mock=use_mock)

            _, _, container_id = self.save_container(
                # Force automation to run on container creation if no artifacts.
                self.make_container(incident, container_label, severity, run_automation=(len(artifacts) == 0))
            )
            create_date_epoch = incident["create_date_original"]
            self.log_to_both(f"New container: {container_id}, incident_id={incident_id}, create_date={create_date_epoch}")
            if len(artifacts) > 0:
                # The save_container and save_artifacts APIs set the run_automation key to 'False' for all except the
                # last artifact, so as to run the playbook once per container when all the artifacts are ingested.
                # https://docs.splunk.com/Documentation/Phantom/4.10.7/DevelopApps/AppDevAPIRef#Active_playbooks
                soar_artifacts = [self.make_artifact(container_id=container_id, artifact=art, severity=severity) for art in artifacts]
                artifact_save_success, _, artifact_ids = self.save_artifacts(soar_artifacts)
                if not artifact_save_success:
                    raise RuntimeError(f"""Failed to save artifacts: ids={artifact_ids}
                                           for incident_id={incident_id}, container_id={container_id}""")
                self.log_to_both(f"Saved artifacts: ids={artifact_ids} for incident_id={incident_id}, container_id={container_id}")
            else:
                self.log_to_both(f"No artifacts found for incident_id={incident_id}, container_id={container_id}")

            self.update_state_end_time(end_time=create_date_epoch)
            if container_count >= max_containers:
                self.log_to_both(f"Max containers reached: {container_count}")
                break
        else:
            # We have pulled all incidents up to create_date <= end_time
            self.update_state_end_time(end_time=end_time)

    def handle_action(self, param):
        action_id = self.get_action_identifier()
        self.log_to_both(f"Handling action: {action_id}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        try:
            if action_id == "test_connectivity":
                self._handle_test_connectivity(param)
            else:
                handler_name = f"_handle_{action_id}"
                if hasattr(self, handler_name):
                    resp = getattr(self, handler_name)(param)
                    num_results = 1
                    if isinstance(resp, list):
                        num_results = len(resp)
                        for r in resp:
                            action_result.add_data(r)
                    else:
                        action_result.add_data(resp)
                    action_result.update_summary(
                        {
                            "total_objects": num_results,
                            "total_objects_successful": num_results,
                        }
                    )
                else:
                    raise RuntimeError(f"Unknown action: {action_id}")
            return action_result.set_status(phantom.APP_SUCCESS)

        except (Exception, SystemExit) as e:
            return action_result.set_status(phantom.APP_ERROR, f"ERROR: {e} -> {traceback.format_exc()}")

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()
        self.log_to_both(f"Loaded state: {self._state}")

        version = self.get_app_json()["app_version"]
        self.log_to_both(f"App version: {version}")
        """
        # get the asset config
        config = self.get_config()

        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == "__main__":
    # import pudb
    # pudb.set_trace()

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = ResilientConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
