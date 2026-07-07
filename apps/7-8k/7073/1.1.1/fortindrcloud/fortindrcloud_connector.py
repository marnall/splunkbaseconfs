# File: fortindrcloud_connector.py
#
# Copyright (c) 2018-2025 Fortinet Inc.
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

import collections
import json
import sys

import phantom.app as phantom
import requests
from fnc import FncClient, FncClientError
from fnc.api import ApiContext, EndpointKey, FncApiClient
from fnc.logger import FncClientLogger
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from fortindrcloud_consts import HISTORY_LIMIT, INTEGRATION_NAME, TRAINING_ACC


# Usage of the consts file is recommended


class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class FncSplunkSOARLogger(FncClientLogger):
    def __init__(self, connector):
        self.connector = connector

    def set_helper(self, connector):
        self.connector = connector

    def get_level(self):
        return "DEBUG"

    def set_level(self, level):
        if level.upper() != "DEBUG":
            self.debug("Only debug level is supported.")

    def critical(self, log: str):
        self.connector.error_print(log)

    def error(self, log: str):
        self.connector.error_print(log)

    def warning(self, log: str):
        self.connector.error_print(log)

    def info(self, log: str):
        self.connector.debug_print(log)

    def debug(self, log: str):
        self.connector.debug_print(log)


class FortiNDRCloudConnector(BaseConnector):
    client: FncApiClient = None

    def __init__(self):
        self.logger = FncSplunkSOARLogger(connector=self)

        super().__init__()
        self._state = None
        self._python_version = None
        self.client = None

    def initialize(self):
        self.logger.debug("Initializing FortiNDR Cloud Connector")

        try:
            self._python_version = int(sys.version_info[0])
        except Exception:
            m = "Error occurred while getting the Phantom server's"
            m += " Python major version."
            self.logger.error(f"FortiNDR Cloud Connector's initialization failed [{m}].")
            return self.set_status(phantom.APP_ERROR, m)

        self._state = self.load_state()
        config = self.get_config()

        try:
            api_key = config.get("api_key", "")
            domain = config.get("domain", "")
            self.client = FncClient.get_api_client(name=INTEGRATION_NAME, api_token=api_key, domain=domain, logger=self.logger)
        except FncClientError as e:
            self.logger.error(f"FortiNDR Cloud Connector's initialization failed [ {e} ].")
            return self.set_status(phantom.APP_ERROR, str(e))

        self.save_progress("FortiNDR Cloud Connector successfully initialized")
        self.logger.info("FortiNDR Cloud Connector successfully initialized")
        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _map_severity(self, severity) -> int:
        if severity == "high":
            return "high"
        elif severity == "moderate":
            return "medium"
        elif severity == "low":
            return "low"
        else:
            return severity

    def _map_confidence(self, confidence) -> int:
        if confidence == "high":
            return "red"
        elif confidence == "moderate":
            return "amber"
        elif confidence == "low":
            return "green"
        else:
            return "white"

    def _create_container(self, detection):
        # Create a container and add necessary fields from the detection
        rule_name = ""
        rule_description = ""
        rule_severity = ""
        rule_confidence = ""
        rule_category = ""
        created = ""
        first_seen = ""
        last_seen = ""
        status = ""
        uuid = ""

        if "rule_name" in detection:
            rule_name = detection["rule_name"]
        if "rule_description" in detection:
            rule_description = detection["rule_description"]
        if "rule_severity" in detection:
            rule_severity = self._map_severity(detection["rule_severity"])
        if "rule_confidence" in detection:
            rule_confidence = self._map_confidence(detection["rule_confidence"])
        if "rule_category" in detection:
            rule_category = detection["rule_category"]
        if "created" in detection:
            created = detection["created"]
        if "first_seen" in detection:
            first_seen = detection["first_seen"]
        if "last_seen" in detection:
            last_seen = detection["last_seen"]
        if "status" in detection:
            status = detection["status"]
        if "uuid" in detection:
            uuid = detection["uuid"]
        if "rule_primary_attack_id" in detection:
            rule_primary_attack_id = detection["rule_primary_attack_id"]
        if "rule_secondary_attack_id" in detection:
            rule_secondary_attack_id = detection["rule_secondary_attack_id"]
        if "rule_url" in detection:
            rule_url = detection["rule_url"]

        # self.logger.debug(f"Creating Container for detection {uuid}.")

        container = {}
        container["name"] = "Fortinet FortiNDR Cloud - "
        container["name"] += rule_name
        container["description"] = rule_description
        container["severity"] = self._map_severity(rule_severity)
        container["sensitivity"] = self._map_confidence(rule_confidence)
        container["data"] = json.dumps(detection)
        container["custom_fields"] = {
            "fnc_category": rule_category,
            "fnc_created": created,
            "fnc_first_seen": first_seen,
            "fnc_last_seen": last_seen,
            "fnc_severity": rule_severity,
            "fnc_confidence": rule_confidence,
            "fnc_status": status,
            "fnc_detection_id": uuid,
            "fnc_detection": json.dumps(detection),
            "fnc_rule_primary_attack_id": rule_primary_attack_id,
            "fnc_rule_secondary_attack_id": rule_secondary_attack_id,
            "fnc_rule_url": rule_url,
        }
        # container["run_automation"] = True

        return container

    def _create_artifact(self, cid, detection):
        # Create a container and add necessary fields from the detection
        device_ip = ""
        sensor_id = ""
        rule_severity = ""
        rule_confidence = ""
        rule_category = ""
        created = ""
        first_seen = ""
        last_seen = ""
        status = ""
        uuid = ""

        if "device_ip" in detection:
            device_ip = detection["device_ip"]
        if "sensor_id" in sensor_id:
            sensor_id = detection["sensor_id"]
        if "rule_severity" in detection:
            rule_severity = self._map_severity(detection["rule_severity"])
        if "rule_confidence" in detection:
            rule_confidence = self._map_confidence(detection["rule_confidence"])
        if "rule_primary_attack_id" in detection:
            rule_primary_attack_id = detection["rule_primary_attack_id"]
        if "rule_secondary_attack_id" in detection:
            rule_secondary_attack_id = detection["rule_secondary_attack_id"]
        if "rule_url" in detection:
            rule_url = detection["rule_url"]
        if "rule_category" in detection:
            rule_category = detection["rule_category"]
        if "created" in detection:
            created = detection["created"]
        if "first_seen" in detection:
            first_seen = detection["first_seen"]
        if "last_seen" in detection:
            last_seen = detection["last_seen"]
        if "status" in detection:
            status = detection["status"]
        if "uuid" in detection:
            uuid = detection["uuid"]

        # self.logger.debug(
        #     f"Creating Artifact for detection {uuid} to be added in container {cid}.")

        artifact = {}
        artifact["container_id"] = cid

        artifact["name"] = uuid
        artifact["label"] = "FNC_Detection"
        artifact["create_time"] = created
        artifact["start_time"] = first_seen
        artifact["end_time"] = last_seen
        artifact["severity"] = self._map_severity(rule_severity)

        artifact["cef"] = {
            "fnc_first_seen": first_seen,
            "fnc_last_seen": last_seen,
            "fnc_severity": rule_severity,
            "fnc_category": rule_category,
            "fnc_confidence": rule_confidence,
            "fnc_status": status,
            "fnc_detection_id": uuid,
            "fnc_device_ip": device_ip,
            "fnc_sensor_id": sensor_id,
            "fnc_rule_primary_attack_id": rule_primary_attack_id,
            "fnc_rule_secondary_attack_id": rule_secondary_attack_id,
            "fnc_rule_url": rule_url,
            "fnc_detection": json.dumps(detection),
        }

        return artifact

    def _split_multivalue_args(self, args, multiple_values: list = []):
        """Update the arguments contained in the multiple_values list
        from a comma separated string into a list of string.
        :parm Dict[str, Any] args: Arguments to be processed
        :parm List[str] multiple_values: Arguments with multiple values
        :return the processed list of arguments
        :rtype str
        """
        for arg in multiple_values:
            if arg in args:
                self.logger.error(f"SPLITTING ARGUMENT {arg}= {args[arg]}")
                value = args[arg].split(",")
                value = [v.strip() for v in value if v.strip()]
                self.logger.error(f"SPLITTED VALUE {value}")
                args[arg] = value

            self.logger.error(f"FINAL ARGUMENTS {args}")

        return args

    # This function flattens all the nested dictionary elements into simple
    # dictionary key:value pairs.
    def _flatten_nested_dict(self, d, parent_key="", sep="."):
        items = []
        for k, v in d.items():
            new_key = parent_key + sep + k if parent_key else k
            if isinstance(v, collections.MutableMapping):
                items.extend(self._flatten_nested_dict(v, new_key, sep=sep).items())
            elif type(v) is list:
                continue
            else:
                items.append((new_key, v))
        return dict(items)

    def _get_poll_detections_request_params(self) -> dict:
        self.logger.info("Retrieving params for Detections polling.")

        config = self.get_config()
        request_params = {
            "include_signature": True,
            "include_description": True,
            "start_date": config.get("first_poll", ""),
            "polling_delay": config.get("polling_delay", ""),
            "account_uuid": config.get("account_uuid", ""),
            "status": config.get("status", ""),
            "pull_muted_rules": config.get("muted_rule", False),
            "pull_muted_devices": config.get("muted_device", False),
            "pull_muted_detections": config.get("muted", False),
            "filter_training_detections": True,
        }

        self.logger.debug("Arguments retrieved.")
        return request_params

    def validate_request(self, response, request_summary, exception, summary, action_result, request):
        self.logger.info("Validating request.")
        # Check if the request failed
        if request_summary and hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data(request_summary)

        if summary is not None:
            action_result.update_summary(summary)

        if exception is not None:
            em = f"The {request} request failed "
            em += f"with message: {exception!s}."

            self.save_progress(em)
            self.logger.error(em)

            return RetVal(action_result.set_status(phantom.APP_ERROR, str(exception)), None)

        # Return success
        m = f"The {request} request was successfully completed."
        self.logger.info(m)

        # Add response to the action result and update the status

        if response is not None:
            action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, f"{request} request successfully handled.")

    def _send_to_splunk(self, detections: list):
        c = 0
        if detections and len(detections) > 0:
            self.logger.debug(f"{len(detections)} containers will be created.")

            cf = 0
            af = 0
            for d in detections:
                c = c + 1
                # logger.debug(f"creating container [{c} of {len(detections)}]")
                container = self._create_container(d)
                ret_val, message, cid = self.save_container(container)
                if phantom.is_fail(ret_val):
                    em = f"Unable to publish container for detection [{d['uuid']}]: ({message})"
                    self.save_progress(em)
                    self.logger.error(em)
                    cf = cf + 1
                else:
                    artifact = self._create_artifact(cid, d)
                    ret_val, message, aid = self.save_artifacts([artifact])
                    if phantom.is_fail(ret_val):
                        em = f"Unable to publish artifact for detection [{d['uuid']}]: ({message})"
                        self.save_progress(em)
                        self.logger.error(em)
                        af = af + 1
            tf = cf + af
            if tf > 0:
                em = f"{tf} of {len(detections)} containers failed to be correctly published."
                if af > 0:
                    em += f" {af} of them, where published without artifacts. The rest were not published at all."
                self.logger.error(em)
            self.logger.debug(f"[{c} of {len(detections)}] containers successfully published.")
        return c

    def _handle_test_connectivity(self, param):
        request = "Test Connectivity"

        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Testing connectivity to FortiNDR.")
        self.logger.info("Testing connectivity to FortiNDR Cloud's services.")

        response = None
        exception = None
        request_summary = {"status": "", "error": "", "info": ""}

        try:
            if self.client:
                self.save_progress(f"Sending request to: {EndpointKey.GET_SENSORS.value} endpoint.")
                _ = self.client.call_endpoint(endpoint=EndpointKey.GET_SENSORS, args=param)
                self.save_progress("Request successfully completed.")
                request_summary.update({"status": "SUCCESS"})
                request_summary.update({"info": "Connection to the FortiNDR Cloud services successfully stablish."})
            else:
                self.logger.error(f"{request} request failed. [FncApiClient was not properly created.]")
                request_summary.update({"status": "FAILURE"})
                request_summary.update({"error": "FncApiClient was not properly created"})
                exception = Exception("FncApiClient was not properly created")
        except FncClientError as e:
            self.logger.error(f"{request} request failed. [{e!s}]")
            request_summary.update({"status": "FAILURE"})
            request_summary.update({"error": str(e)})
            exception = e

        result = {"sensors": response}

        summary = {"response_count": 1, "request": request}

        self.debug_print("Validating result.")
        return self.validate_request(
            response=result, request_summary=request_summary, exception=exception, summary=summary, action_result=action_result, request=request
        )

    def _handle_on_poll(self, param):
        self.logger.info("Starting to retrieve Detections.")
        # Add an action result object to self (BaseConnector) to represent
        # the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        params = self._get_poll_detections_request_params()

        last_detection = self._state.get("last_poll", None)
        if last_detection:
            self.logger.info(f"Last checkpoint was: {last_detection}.")

        history = {}
        last_history = self._state.get("last_history", None)
        if last_history:
            self.logger.info(f"Last history was: {last_history}.")
            history = json.loads(last_history)

        rcs = 0
        rhs = 0
        try:
            # We restore the context using the persisted values of the
            # last_detection(checkpoint) and the history if they exist
            # Otherwise, we initialize them by calling the get splitted
            # context method.

            context: ApiContext = None
            h_context: ApiContext = None

            if last_detection:
                self.logger.info("Restoring the Context")
                context = ApiContext()
                context.update_checkpoint(checkpoint=last_detection)
                h_context = ApiContext()
                h_context.update_history(history=history)
            else:
                self.logger.info("Initializing the Context")
                h_context, context = self.client.get_splitted_context(params)

            # Pull current detections
            self.logger.info("Polling current detections.")
            for response in self.client.continuous_polling(context=context, args=params):
                detections = response.get("detections", [])
                detections = list(filter(lambda d: (d["account_uuid"] != TRAINING_ACC), detections))

                if detections:
                    rcs = self._send_to_splunk(detections=detections)
            context.clear_args()

            # Pull next piece of the history data
            self.logger.info("Polling historical data.")

            params.update({"limit": HISTORY_LIMIT})
            for response in self.client.poll_history(context=h_context, args=params):
                detections = response.get("detections", [])
                detections = list(filter(lambda d: (d["account_uuid"] != TRAINING_ACC), detections))

                if detections:
                    rhs = self._send_to_splunk(detections=detections)

            h_context.clear_args()

            # checkpoint for the first Detection iteration
            last_poll = context.get_checkpoint()
            history = h_context.get_remaining_history()

            self.logger.debug("Updating last poll checkpoint.")
            self._state["last_poll"] = last_poll

            last_history = json.dumps(history)
            self.logger.debug("Updating last history checkpoint.")
            self._state["last_history"] = last_history

            self.logger.info(f"Last poll checkpoint set at {last_poll}")
            self.logger.info(f"Last history checkpoint set at {last_history}")

            self.logger.info("Completed processing Detections")
        except FncClientError as e:
            self.logger.error("Exception occurred while processing Detections")
            self.logger.error(f"[{e!s}]")
            self.error_print(f"Unable to retrieve detections. [{e!s}]")
            return RetVal(action_result.set_status(phantom.APP_ERROR, str(e)), None)

        return action_result.set_status(phantom.APP_SUCCESS, f"Created {rcs + rhs} containers")

    def _handle_fnc_endpoint(self, endpoint: EndpointKey, param: dict):
        self.logger.info(f"Handling {endpoint.value} Request.")

        # Add an action result object to self (BaseConnector) to represent
        # the action for this param
        param.pop("context", None)

        response = None
        exception = None
        request_summary = {"status": "", "error": "", "info": ""}

        try:
            response = self.client.call_endpoint(endpoint=endpoint, args=param)

            self.logger.info(f"{endpoint.value} successfully completed.")
            request_summary.update({"status": "SUCCESS"})
            request_summary.update({"info": f"{len(response)} items retrieved."})
        except FncClientError as e:
            self.logger.error(f"{endpoint.value} Request Failed. [{e!s}]")
            request_summary.update({"status": "FAILURE"})
            request_summary.update({"error": str(e)})
            exception = e

        return {"response": response, "request_summary": request_summary, "exception": exception}

    #  Actions for Sensors API

    def _handle_fnc_get_sensors(self, param):
        self.debug_print("Handling get_sensors command.")
        # Add an action result object to self (BaseConnector) to represent
        # the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.GET_SENSORS
        key = "sensors"

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        sensors = []
        response = result["response"]

        if response and key in response:
            sensors = response.pop(key)

        summary = {
            "response_count": len(sensors),
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"sensors": sensors},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def _handle_fnc_get_devices(self, param):
        self.debug_print("Handling get_devices command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.GET_DEVICES
        key = "devices"

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        devices = []
        response = result["response"]
        if response and key in response:
            devices = response.pop(key)

        summary = {
            "response_count": len(devices),
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"devices": devices["device_list"]},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def _handle_fnc_get_tasks(self, param):
        self.debug_print("Handling get_tasks command.")
        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint: EndpointKey = EndpointKey.GET_TASKS
        key = "pcaptasks"
        taskid = param.pop("task_uuid", "")

        if taskid:
            endpoint = EndpointKey.GET_TASK
            key = "pcap_task"
            param.update({"task_id": taskid})

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)
        response = result["response"]

        tasks = []
        if response and key in response:
            tasks = response.pop(key)

        if taskid:
            tasks = [tasks]

        summary = {
            "response_count": len(tasks),
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"tasks": tasks},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def _handle_fnc_create_task(self, param):
        self.debug_print("Handling create_task command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.CREATE_TASK
        key = "pcaptask"

        if "sensor_ids" in param:
            param = self._split_multivalue_args(param, ["sensor_ids"])
        else:
            param.update({"sensor_ids": []})

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        task = {}
        response = result["response"]
        if response and key in response:
            task = response.pop(key)

        summary = {
            "response_count": 1 if task else 0,
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"task": task},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def _handle_fnc_get_telemetry_events(self, param):
        self.debug_print("Handling get_telemetry_events command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.GET_TELEMETRY_EVENTS
        key = "data"
        header_key = "columns"

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        telemetry = []
        response = result["response"]
        if response and key in response:
            data = response.pop(key)
            headers = response.pop(header_key)
            telemetry = [dict(zip(headers, values)) for values in data]

        summary = {
            "response_count": len(telemetry),
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"telemetry_events": telemetry},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def _handle_fnc_get_telemetry_network(self, param):
        self.debug_print("Handling get_telemetry_network command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.GET_TELEMETRY_NETWORK
        key = "network_usage"

        latest_each_month = param.pop("latest_each_month", False)
        if latest_each_month:
            param.update({"latest_each_month": True})

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        telemetry = []
        response = result["response"]
        if response and key in response:
            telemetry = response.pop(key)

        summary = {
            "response_count": len(telemetry),
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"network_usage": telemetry},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def _handle_fnc_get_telemetry_packetstats(self, param):
        self.debug_print("Handling get_telemetry_packetstats command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.GET_TELEMETRY_PACKETSTATS
        key = "data"

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        telemetry = []
        response = result["response"]
        if response and key in response:
            telemetry = response.pop(key)

        summary = {
            "response_count": len(telemetry),
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"packetstats": telemetry},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    #  Actions for Entity API

    def _handle_fnc_get_entity_summary(self, param):
        self.debug_print("Handling get_entity_summary command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.GET_ENTITY_SUMMARY
        key = "summary"

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        entity_summary = {}
        response = result["response"]
        if response and key in response:
            entity_summary = response.pop(key)

        summary = {
            "response_count": 1 if entity_summary else 0,
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"entity_summary": entity_summary},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def _handle_fnc_get_entity_pdns(self, param):
        self.debug_print("Handling get_entity_pdns command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.GET_ENTITY_PDNS
        key = "passivedns"

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        entity_pdns = []
        response = result["response"]
        if response and key in response:
            entity_pdns = response.pop(key)

        summary = {
            "response_count": len(entity_pdns),
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"entity_pdns": entity_pdns},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def _handle_fnc_get_entity_dhcp(self, param):
        self.debug_print("Handling get_entity_dhcp command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.GET_ENTITY_DHCP
        key = "dhcp"

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        entity_dhcp = []
        response = result["response"]
        if response and key in response:
            entity_dhcp = response.pop(key)

        summary = {
            "response_count": len(entity_dhcp),
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"entity_dhcp": entity_dhcp},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def _handle_fnc_get_entity_vs(self, param):
        self.debug_print("Handling get_entity_vs command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.GET_ENTITY_VIRUS_TOTAL
        key = "vt_response"

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        entity_vs = []
        response = result["response"]
        if response and key in response:
            entity_vs = response.pop(key)

        summary = {
            "response_count": len(entity_vs),
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"entity_vs": entity_vs},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def _handle_fnc_get_entity_file(self, param):
        self.debug_print("Handling get_entity_file command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.GET_ENTITY_FILE
        key = "file"

        hash = param.pop("hash", "")
        param.update({"entity": hash})

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        entity_file = {}
        response = result["response"]
        if response and key in response:
            entity_file = response.pop(key)

        summary = {
            "response_count": 1 if entity_file else 0,
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"entity_file": entity_file},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    #  Actions for Detections API

    def _handle_fnc_get_detections(self, param):
        self.debug_print("Handling get_detections command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.GET_DETECTIONS
        key = "detections"

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        detections = []
        response = result["response"]
        if response and key in response:
            detections = response.pop(key)

        summary = {
            "response_count": len(detections),
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"detections": detections},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def _handle_fnc_get_detection_rules(self, param):
        self.debug_print("Handling get_detection_rules command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.GET_RULES
        key = "rules"

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        rules = []
        response = result["response"]
        if response and key in response:
            rules = response.pop(key)

        summary = {
            "response_count": len(rules),
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"rules": rules},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def _handle_fnc_resolve_detection(self, param):
        self.debug_print("Handling resolve_detections command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.RESOLVE_DETECTION

        detection = param.pop("detection_uuid", "")
        param.update({"detection_id": detection})

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        summary = {
            "response_count": 0,
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response=result["response"],
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def _handle_fnc_get_rule_events(self, param):
        self.debug_print("Handling get_rule_events command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.GET_RULE_EVENTS
        key = "events"

        rule = param.pop("rule_uuid", "")
        param.update({"rule_id": rule})
        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        events = []
        response = result["response"]
        if response and key in response:
            events = response.pop(key)

        summary = {
            "response_count": len(events),
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"rule_events": events},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def _handle_fnc_get_detection_events(self, param):
        self.debug_print("Handling get_detection_events command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.GET_DETECTION_EVENTS
        key = "events"

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        detection_events = []
        events = []
        response = result["response"]
        if response and key in response:
            events = response.pop(key)
        detection = param.get("detection_uuid", "")

        for e in events:
            event = self._flatten_nested_dict(d=e["event"], sep="_")
            # Filter training events
            event.update({"rule_uuid": e["rule_uuid"]})
            event.update({"detection_uuid": detection})
            event.update({"raw_event": json.dumps(e)})
            detection_events.append(event)

        summary = {
            "response_count": len(detection_events),
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"detection_events": detection_events},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def _handle_fnc_create_detection_rule(self, param):
        self.debug_print("Handling create_detection_rule command.")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = EndpointKey.CREATE_RULE
        key = "rule"

        if "run_account_uuids" in param:
            param = self._split_multivalue_args(param, ["run_account_uuids"])

        if "device_ip_fields" in param:
            param = self._split_multivalue_args(param, ["device_ip_fields"])
        else:
            param.update({"device_ip_fields": ["DEFAULT"]})

        if "indicator_fields" in param:
            param = self._split_multivalue_args(param, ["indicator_fields"])

        result = self._handle_fnc_endpoint(endpoint=endpoint, param=param)

        rule = {}
        response = result["response"]
        if response and key in response:
            rule = response.pop(key)

        summary = {
            "response_count": 1 if rule else 0,
            "request": endpoint.value,
        }

        self.debug_print("Validating result.")
        return self.validate_request(
            response={"rule": rule},
            request_summary=result["request_summary"],
            exception=result["exception"],
            summary=summary,
            action_result=action_result,
            request=endpoint.value,
        )

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("Handling action: ", self.get_action_identifier())

        if action_id == "on_poll":
            ret_val = self._handle_on_poll(param)
        elif action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)
        elif action_id == "fnc_get_sensors":
            ret_val = self._handle_fnc_get_sensors(param)
        elif action_id == "fnc_get_devices":
            ret_val = self._handle_fnc_get_devices(param)
        elif action_id == "fnc_get_tasks":
            ret_val = self._handle_fnc_get_tasks(param)
        elif action_id == "fnc_create_task":
            ret_val = self._handle_fnc_create_task(param)
        elif action_id == "fnc_get_telemetry_events":
            ret_val = self._handle_fnc_get_telemetry_events(param)
        elif action_id == "fnc_get_telemetry_packetstats":
            ret_val = self._handle_fnc_get_telemetry_packetstats(param)
        elif action_id == "fnc_get_telemetry_network":
            ret_val = self._handle_fnc_get_telemetry_network(param)
        elif action_id == "fnc_get_entity_summary":
            ret_val = self._handle_fnc_get_entity_summary(param)
        elif action_id == "fnc_get_entity_pdns":
            ret_val = self._handle_fnc_get_entity_pdns(param)
        elif action_id == "fnc_get_entity_dhcp":
            ret_val = self._handle_fnc_get_entity_dhcp(param)
        elif action_id == "fnc_get_entity_file":
            ret_val = self._handle_fnc_get_entity_file(param)
        elif action_id == "fnc_get_detections":
            ret_val = self._handle_fnc_get_detections(param)
        elif action_id == "fnc_get_detection_rules":
            ret_val = self._handle_fnc_get_detection_rules(param)
        elif action_id == "fnc_resolve_detection":
            ret_val = self._handle_fnc_resolve_detection(param)
        elif action_id == "fnc_get_rule_events":
            ret_val = self._handle_fnc_get_rule_events(param)
        elif action_id == "fnc_get_detection_events":
            ret_val = self._handle_fnc_get_detection_events(param)
        elif action_id == "fnc_create_detection_rule":
            ret_val = self._handle_fnc_create_detection_rule(param)

        return ret_val


def main():
    import argparse

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
            login_url = FortiNDRCloudConnector._get_phantom_base_url()
            login_url += "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            em = f"Unable to get session id from the platform. Error: {e!s}"
            print(em)
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = FortiNDRCloudConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
