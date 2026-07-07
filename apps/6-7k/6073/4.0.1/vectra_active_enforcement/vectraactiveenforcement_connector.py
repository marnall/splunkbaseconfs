# File: vectraactiveenforcement_connector.py
#
# Copyright Vectra 2017-2025
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

import json
from time import gmtime, strftime

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from vectraactiveenforcement_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class VectraActiveEnforcementConnector(BaseConnector):
    def __init__(self):
        super().__init__()
        self._state = None
        self._base_url = None

    def _process_empty_reponse(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    def _process_html_response(self, response, action_result):
        status_code = response.status_code
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = ("\n").join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"
        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, (f"Unable to parse JSON response. Error: {e!s}")), None)

        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)
        else:
            message = (
                "Error from server. Status Code: {} Data from \
                       server: {}"
            ).format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))
            return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)
        else:
            if "html" in r.headers.get("Content-Type", ""):
                return self._process_html_response(r, action_result)
            if not r.text:
                return self._process_empty_reponse(r, action_result)
            message = (
                "Can't process response from server. Status Code: {} \
                       Data from server: {}"
            ).format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))
            return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, method="get"):
        config = self.get_config()
        resp_json = None
        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, (f"Invalid method: {method}")), resp_json)

        url = self._base_url + endpoint
        try:
            r = request_func(
                url,
                auth=(self.username, self.password),
                json=data,
                headers=headers,
                verify=config.get("verify_server_cert", False),
                params=params,
            )
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, (f"Error Connecting to server. Details: {e!s}")), resp_json)

        return self._process_response(r, action_result)

    def _process_hosts(self, search_type, action_result, request_params, host_dict):
        """
        Returns dictionary of hosts retrieved and appends quest type to reason field for host
        """
        ret_val, response = self._make_rest_call("/hosts", action_result, params=request_params)
        if phantom.is_fail(ret_val):
            self.save_progress(f"Atttempt to retrive host failed. Error: {action_result.get_message()}")
            return action_result.get_status()
        else:
            if response == []:
                response = {"count": 0, "results": []}
            if search_type in ("tags", "scores", "detections"):
                for host in response["results"]:
                    if host["name"] in host_dict.keys():
                        host_dict[host["name"]].add_reason(search_type)
                    else:
                        host_dict.update({host["name"]: VectraHost(host)})
                        host_dict[host["name"]].add_reason(search_type)

                self.save_progress("Saved hosts: " + search_type)
                return
            for host in response["results"]:
                host_dict.update({host["name"]: VectraHost(host)})

            self.save_progress("Saved retrieved hosts")
            return

    def _process_detections(self, action_result, request_params):
        """
        Returns dict of detections and set of ips associated with detections
        """
        ret_val, response = self._make_rest_call("/detections", action_result, params=request_params)
        if phantom.is_fail(ret_val):
            self.save_progress(f"Atttempt to retrive host failed. Error: {action_result.get_message()}")
            return (action_result.get_status(), None, None)
        else:
            if response == []:
                response = {"count": 0, "results": []}
            detection_dict = {}
            ip_list = []
            for detection in response["results"]:
                detection_dict.update({detection["id"]: VectraDetection(detection)})
                ip_list.append(detection["src_ip"])

            self.save_progress("Saved detections: " + request_params["type_vname"])
            return (phantom.APP_SUCCESS, detection_dict, ip_list)

    def _converts_object_to_json(self, json_dict):
        converted_objects = {}
        if not json_dict:
            json_dict = dict()
        for key in json_dict:
            converted_objects.update({key: json_dict[key].summary()})

        return converted_objects

    def _manage_containers(self, action_result, host_dict, unblock_list):
        self.save_progress("Retrieving currently blocked hosts list...")
        phantom_base_url = self.get_phantom_base_url()
        try:
            blocked_hosts = requests.get(url=phantom_base_url + "rest/decided_list/blocked_hosts", verify=False)
            blocked_hosts = blocked_hosts.json()
        except requests.RequestException as rerr:
            return action_result.set_status(
                phantom.APP_ERROR,
                (
                    f"Unable to retrieve list of currently blocked hosts.\
                                                                 Error: {rerr!s}"
                ),
            )
        except Exception:
            return action_result.set_status(
                phantom.APP_ERROR,
                (
                    f"Unable to retrieve list of currently \
                                    blocked hosts.\r\nCode: {blocked_hosts.status_code}\r\nContent:{blocked_hosts.content}"
                ),
            )

        if blocked_hosts.get("failed"):
            try:
                ret_val = self._clear_blocked_hosts_list(action_result)
                if phantom.is_fail(ret_val):
                    return action_result.get_status()
                blocked_hosts = requests.get(url=phantom_base_url + "rest/decided_list/blocked_hosts", verify=False)
                blocked_hosts = blocked_hosts.json()
            except requests.RequestException:
                return action_result.set_status(phantom.APP_ERROR, "Unable to retrieve list of currently blocked hosts")
            except Exception:
                return action_result.set_status(
                    phantom.APP_ERROR,
                    (
                        f"Unable to retrieve list of currently blocked hosts.\r\nCode:\
                                         {blocked_hosts.status_code}\r\nContent:{blocked_hosts.content}"
                    ),
                )

        self.save_progress("Retrieved currently blocked hosts list...")
        if blocked_hosts["content"][0][0] == "empty" and len(host_dict) == 0:
            return self.save_progress("No hosts requested to (un)block")
        if blocked_hosts["content"][0][0] == "empty" and len(host_dict) >= 1:
            for host in host_dict:
                self._block_host(host_dict[host])

            return self.save_progress(f"Successfully created containers for {len(host_dict)} hosts")
        if blocked_hosts["content"][0][0] != "empty" and len(host_dict) == 0:
            for host in blocked_hosts["content"]:
                if len(host) < 2:
                    continue
                self._unblock_host(host)
                unblock_list.append(host[0])

            ret_val = self._clear_blocked_hosts_list(action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            return self.save_progress(("Successfully created containers for {} hosts").format(len(blocked_hosts["content"])))
        if blocked_hosts["content"][0][0] != "empty" and len(host_dict) >= 1:
            for host in blocked_hosts["content"]:
                if len(host) < 2:
                    continue
                if host[1] not in host_dict.keys():
                    self._unblock_host(host)
                    unblock_list.append(host[0])

            for host in host_dict:
                if not any(list_host[1] == host for list_host in blocked_hosts["content"] if len(list_host) >= 2):
                    self._block_host(host_dict[host])

        return action_result.set_status(phantom.APP_SUCCESS)

    def _clear_blocked_hosts_list(self, action_result):
        phantom_base_url = self.get_phantom_base_url()
        try:
            requests.post(
                url=(f"{phantom_base_url}rest/decided_list"), verify=False, data=json.dumps({"name": "blocked_hosts", "content": [["empty"]]})
            )
            return self.save_progress("Cleared currently blocked hosts list")
        except requests.RequestException:
            return action_result.set_status(phantom.APP_ERROR, "Unable to clear list of currently blocked hosts")
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, (f"Unable to clear list of currently blocked hosts. Error:{e}"))

    def _block_host(self, host):
        config = self.get_config()
        name = ("Block request: {ip} [{name}]").format(ip=host.get("ip", ""), name=host.get("name", ""))
        identifier = ("vectra_block_request {ip} {time}").format(ip=host.get("ip", ""), time=strftime("%m/%d/%Y %H:%M", gmtime()))
        artifact = create_artifact(host, "block", config["severity"])
        container_ret_val, message, self._block_container_id = self.save_container(
            create_container(name, identifier, artifact, config["severity"])
        )
        self.save_progress(f"Successfully saved container: {self._block_container_id}")

    def _unblock_host(self, host):
        config = self.get_config()
        name = f"Unblock request: {host[0]} [{host[1]}]"
        identifier = ("vectra_unblock_request {ip} {time}").format(ip=host[0], time=strftime("%m/%d/%Y %H:%M", gmtime()))
        artifact = {
            "name": host[1],
            "cef": {"act": "unblock", "dvc": host[0], "dvchost": host[1]},
            "run_automation": False,
            "label": "incident",
            "severity": config["severity"],
            "source_data_identifier": "vectra",
        }
        container_ret_val, message, self._block_container_id = self.save_container(
            create_container(name, identifier, artifact, config["severity"])
        )
        self.save_progress(f"Successfully unblocked {host[0]}")

    def _update_lists(self, action_result, host_dict):
        phantom_base_url = self.get_phantom_base_url()
        content = []
        for host in host_dict:
            content.append([host_dict[host].ip, host])

        if len(content) >= 1:
            try:
                requests.post(
                    url=phantom_base_url + "rest/decided_list/blocked_hosts",
                    verify=False,
                    data=json.dumps({"name": "blocked_hosts", "content": content}),
                )
            except requests.RequestException:
                action_result.set_status(phantom.APP_ERROR, "Unable to update list of currently blocked hosts")

        return self.save_progress("Successfully updated block list")

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Connecting to endpoint")
        ret_val, response = self._make_rest_call("", action_result)
        if phantom.is_fail(ret_val):
            self.save_progress(f"Test Connectivity Failed. Error: {action_result.get_message()}")
            return action_result.get_status()
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_lookup_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        retrieved_hosts = {}
        request_params = {"last_source": param["ip"]}
        self._process_hosts(None, action_result, request_params, retrieved_hosts)
        summary_dict = self._converts_object_to_json(retrieved_hosts)
        action_result.add_data(summary_dict)
        summary = action_result.update_summary({})
        summary["retrieved_hosts"] = len(summary_dict)
        return action_result.set_status(phantom.APP_SUCCESS, (f"Successfully retrieved {len(retrieved_hosts)} hosts"))

    def _handle_get_detections(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        all_detections = {}
        all_ips = set()
        for detection in param["dettypes"].split(","):
            request_params = {
                "src_ip": param.get("src_ip", ""),
                "dst_port": param.get("dst_port", None),
                "type_vname": detection.strip(),
                "state": param["state"],
                "page_size": "all",
            }
            _, retrieved_detections, retrieved_ips = self._process_detections(action_result, request_params)
            if retrieved_detections:
                all_detections.update(retrieved_detections)
            if retrieved_ips:
                all_ips.update(retrieved_ips)

        summary_detections = self._converts_object_to_json(all_detections)
        action_result.add_data(summary_detections)
        summary = action_result.update_summary({})
        summary["retrieved_detections"] = len(summary_detections)
        summary["ip_list"] = list(all_ips)
        return action_result.set_status(phantom.APP_SUCCESS, (f"Successfully retrieved {len(summary_detections)} detections"))

    def _handle_get_scored_hosts(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        retrieved_hosts = {}
        request_params = {"c_score_gte": param["cscore"], "t_score_gte": param["tscore"], "page_size": "all"}
        self._process_hosts(None, action_result, request_params, retrieved_hosts)
        summary_dict = self._converts_object_to_json(retrieved_hosts)
        action_result.add_data(summary_dict)
        summary = action_result.update_summary({})
        summary["retrieved_hosts"] = len(summary_dict)
        return action_result.set_status(phantom.APP_SUCCESS, (f"Successfully retrieved {len(retrieved_hosts)} hosts"))

    def _handle_get_tagged_hosts(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        retrieved_hosts = {}
        request_params = {"tags": param["dtags"], "page_size": "all"}
        self._process_hosts(None, action_result, request_params, retrieved_hosts)
        summary_dict = self._converts_object_to_json(retrieved_hosts)
        action_result.add_data(summary_dict)
        summary = action_result.update_summary({})
        summary["retrieved_hosts"] = len(summary_dict)
        return action_result.set_status(phantom.APP_SUCCESS, (f"Successfully retrieved {len(retrieved_hosts)} hosts"))

    def _handle_on_poll(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        config = self.get_config()
        retrieved_hosts = {}
        retrieved_detections = {}
        unblocked_hosts = []
        if config["tags"]:
            request_params = {"tags": config.get("dtags", "block"), "page_size": "all"}
            self._process_hosts("tags", action_result, request_params, retrieved_hosts)
        if config["scores"]:
            request_params = {"c_score_gte": config.get("cscore", 50), "t_score_gte": config.get("tscore", 50), "page_size": "all"}
            self._process_hosts("scores", action_result, request_params, retrieved_hosts)
        if config["detections"]:
            if len(config.get("dettypes", "")) == 0:
                return action_result.set_status(phantom.APP_ERROR, "Detections enabled. No detection types defined")
            for dettype in config.get("dettypes", "").split(","):
                request_params = {"type_vname": dettype.strip(), "state": "active", "page_size": "all"}
                _, detections, detection_ips = self._process_detections(action_result, request_params)
                if detections:
                    retrieved_detections.update(detections)
                if detection_ips:
                    for ip in set(detection_ips):
                        request_params = {"last_source": ip, "state": "active", "page_size": "all"}
                        self._process_hosts("detections", action_result, request_params, retrieved_hosts)

        summary_host_dict = self._converts_object_to_json(retrieved_hosts)
        summary_detection_dict = self._converts_object_to_json(retrieved_detections)
        action_result.add_data(summary_host_dict)
        action_result.add_data(summary_detection_dict)
        ret_val = self._manage_containers(action_result, retrieved_hosts, unblocked_hosts)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        self._update_lists(action_result, retrieved_hosts)
        summary = action_result.update_summary({})
        summary["retrieved_hosts"] = len(retrieved_hosts)
        summary["retrieved_detections"] = len(retrieved_detections)
        summary["unblocked_hosts"] = len(unblocked_hosts)
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS
        action_id = self.get_action_identifier()
        self.debug_print("action_id", self.get_action_identifier())
        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)
        elif action_id == "lookup_ip":
            ret_val = self._handle_lookup_ip(param)
        elif action_id == "get_detections":
            ret_val = self._handle_get_detections(param)
        elif action_id == "get_scored_hosts":
            ret_val = self._handle_get_scored_hosts(param)
        elif action_id == "get_tagged_hosts":
            ret_val = self._handle_get_tagged_hosts(param)
        elif action_id == "on_poll":
            ret_val = self._handle_on_poll(param)
        return ret_val

    def initialize(self):
        self._state = self.load_state()
        config = self.get_config()
        device_ip_hostname = config["device"]
        device_ip_hostname = device_ip_hostname.strip("/")
        device_ip_hostname = device_ip_hostname.strip("\\")
        device_ip_hostname = device_ip_hostname.strip("/")
        self._base_url = "https://" + device_ip_hostname + "/api"
        self.username = config["username"]
        self.password = config["password"]
        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == "__main__":
    import sys

    import pudb

    pudb.set_trace()
    phantom_base_url = BaseConnector._get_phantom_base_url()
    r = requests.get(phantom_base_url + "login", verify=False)
    csrftoken = r.cookies["csrftoken"]
    data = {"username": "admin", "password": "password", "csrfmiddlewaretoken": csrftoken}  # pragma: allowlist secret
    headers = {"Cookie": (f"csrftoken={csrftoken}"), "Referer": phantom_base_url + "login"}
    r2 = requests.post(phantom_base_url + "login", verify=False, data=data, headers=headers)
    sessionid = r2.cookies["sessionid"]
    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)
    with open(sys.argv[1]) as (f):
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))
        connector = VectraActiveEnforcementConnector()
        connector.print_progress_message = True
        in_json["user_session_token"] = sessionid
        result = connector._handle_action(json.dumps(in_json), None)
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))
    sys.exit(0)
