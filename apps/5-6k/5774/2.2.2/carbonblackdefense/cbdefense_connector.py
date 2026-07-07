# File: cbdefense_connector.py
#
# Copyright (c) 2018-2025 Splunk Inc.
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
# Phantom App imports
import ipaddress
import json
import time

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from cbdefense_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class CarbonBlackDefenseConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None
        self._base_url = None
        self._api_auth = None
        self._siem_auth = None
        self._custom_api_auth = None
        self._org_key = None
        self._status_code = None

    def initialize(self):
        self._state = self.load_state()

        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}
            return self.set_status(phantom.APP_ERROR, CBD_STATE_FILE_CORRUPT_ERROR)

        config = self.get_config()

        self._base_url = config["api_url"].strip("/")

        if "api_key" in config and "api_connector_id" in config:
            self._api_auth = "{}/{}".format(config["api_key"], config["api_connector_id"])
        if "siem_key" in config and "siem_connector_id" in config:
            self._siem_auth = "{}/{}".format(config["siem_key"], config["siem_connector_id"])
        if "custom_api_key" in config and "custom_api_connector_id" in config:
            self._custom_api_auth = "{}/{}".format(config["custom_api_key"], config["custom_api_connector_id"])
        if "org_key" in config:
            self._org_key = config["org_key"]

        self.set_validator("ipv6", self._is_ip)

        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _is_ip(self, input_ip_address):
        """Function that checks given address and return True if address is valid IPv4 or IPV6 address.

        :param input_ip_address: IP address
        :return: status (success/failure)
        """

        ip_address_input = input_ip_address

        try:
            ipaddress.ip_address(str(ip_address_input))
        except Exception as e:
            self.debug_print(EXCEPTION_OCCURRED, self._get_error_message_from_exception(e))
            return False

        return True

    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    action_result.set_status(phantom.APP_ERROR, INVALID_INT.format(param=key))
                    return None

                parameter = int(parameter)
            except Exception:
                action_result.set_status(phantom.APP_ERROR, INVALID_INT.format(param=key))
                return None

            if parameter < 0:
                action_result.set_status(phantom.APP_ERROR, ERROR_NEGATIVE_INT_PARAM.format(param=key))
                return None

            if not allow_zero and parameter == 0:
                action_result.set_status(phantom.APP_ERROR, NON_ZERO_ERROR.format(param=key))
                return None

        return parameter

    def _get_error_message_from_exception(self, e):
        """This function is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        error_msg = ERROR_MSG_EXCEPTION
        error_code = ERROR_CODE_EXCEPTION
        try:
            if e.args:
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_code = ERROR_CODE_EXCEPTION
                    error_msg = e.args[0]
            else:
                error_code = ERROR_CODE_EXCEPTION
                error_msg = ERROR_MSG_EXCEPTION
        except Exception:
            error_code = ERROR_CODE_EXCEPTION
            error_msg = ERROR_MSG_EXCEPTION

        return f"Error Code: {error_code}. Error Message: {error_msg}"

    def _process_empty_reponse(self, response, action_result):
        if response.status_code == 200 or response.status_code == 204:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, CBD_EMPTY_RESPONSE_NO_HEADER), None)

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except Exception:
            error_text = CBD_ERROR_TEXT

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
                    phantom.APP_ERROR, f"Unable to parse JSON response. Error: {self._get_error_message_from_exception(e)}"
                ),
                None,
            )

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        if "message" in resp_json:
            message = resp_json["message"]
        else:
            message = "Error from server. Status Code: {} Data from server: {}".format(
                r.status_code, r.text.replace("{", "{{").replace("}", "}}")
            )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        self._status_code = r.status_code

        self.debug_print("Processing API response")
        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        # Process an HTML resonse, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_reponse(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, method="get", is_new_api=False):
        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = self._base_url + endpoint

        if "notification" in endpoint:
            if not self._siem_auth:
                return RetVal(action_result.set_status(phantom.APP_ERROR, CBD_SIEM_ERROR))
            auth_header = {"X-Auth-Token": self._siem_auth}
        elif is_new_api:
            if not self._custom_api_auth:
                return RetVal(action_result.set_status(phantom.APP_ERROR, CBD_CUSTOM_API_ERROR))
            if not self._org_key:
                return RetVal(action_result.set_status(phantom.APP_ERROR, CBD_ORG_KEY_ERROR))
            auth_header = {"X-Auth-Token": self._custom_api_auth}
        else:
            if not self._api_auth:
                return RetVal(action_result.set_status(phantom.APP_ERROR, CBD_API_ERROR))
            auth_header = {"X-Auth-Token": self._api_auth}

        if headers:
            headers.update(auth_header)
        else:
            headers = auth_header

        self.debug_print("Making API call")
        try:
            r = request_func(
                url,
                json=data,
                headers=headers,
                verify=config.get("verify_server_cert", False),
                params=params,
                timeout=CBD_DEFAULT_REQUEST_TIMEOUT,
            )
        except Exception as e:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {self._get_error_message_from_exception(e)}"),
                resp_json,
            )

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Querying policies to test connectivity")

        ret_val, response = self._make_rest_call(CBD_POLICY_API, action_result)

        if phantom.is_fail(ret_val):
            self.save_progress(TEST_CONNECTIVITY_FAILED)
            return ret_val

        self.save_progress(TEST_CONNECTIVITY_PASSED)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_policies(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val, response = self._make_rest_call(CBD_POLICY_API, action_result)

        if phantom.is_fail(ret_val):
            return ret_val

        results = response.get("results", [])

        for result in results:
            action_result.add_data(result)

        action_result.set_summary({"num_policies": len(results)})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        body = {
            "policyInfo": {
                "name": param["name"],
                "description": param["description"],
                "priorityLevel": param["priority"],
                "version": 2,  # This is required to be 2 by the API
            }
        }

        try:
            policy_info = json.loads(param.get("json_fields", '{"sensorSettings": []}'))
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Could not parse JSON from 'json_fields' parameter: {e}")
        body["policyInfo"]["policy"] = policy_info

        ret_val, response = self._make_rest_call(CBD_POLICY_API, action_result, data=body, method="post")

        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response)
        action_result.set_summary({"policy_id": response.get("policyId", "UNKNOWN")})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        policy_id = param["id"]

        ret_val, response = self._make_rest_call(CBD_POLICY_API_DEL.format(policy_id), action_result, method="delete")

        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response)
        action_result.set_summary({"policy_id": policy_id})

        return action_result.set_status(phantom.APP_SUCCESS, CBD_POLICY_DELETED)

    def _handle_add_rule(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            rule_info = json.loads(param["rules"])
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, f"Could not parse JSON from rules parameter: {self._get_error_message_from_exception(e)}"
            )

        body = {"ruleInfo": rule_info}

        ret_val, response = self._make_rest_call(CBD_ADD_RULE_API.format(param["id"]), action_result, data=body, method="post")

        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response)
        action_result.set_summary({"rule_id": response.get("ruleId", "UNKNOWN")})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_rule(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        rule_id = param["rule_id"]
        ret_val, response = self._make_rest_call(CBD_DEL_RULE_API.format(param["policy_id"], rule_id), action_result, method="delete")

        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response)
        action_result.set_summary({"rule_id": rule_id})

        return action_result.set_status(phantom.APP_SUCCESS, CBD_RULE_DELETED)

    def _handle_list_devices(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        params = {}
        if "start" in param:
            start = self._validate_integer(action_result, param.get("start", None), "start", allow_zero=True)
            if start is None:
                return action_result.get_status()
            params["start"] = start
        if "limit" in param:
            limit = self._validate_integer(action_result, param.get("limit", None), "limit", allow_zero=False)
            if limit is None:
                return action_result.get_status()
            params["rows"] = limit

        list_devices_api = CBD_LIST_DEVICE_API.format(self._org_key)
        ret_val, response = self._make_rest_call(list_devices_api, action_result, data=params, method="post", is_new_api=True)

        if phantom.is_fail(ret_val):
            return ret_val

        results = response.get("results", [])

        for result in results:
            action_result.add_data(result)

        action_result.set_summary({"num_devices": len(results)})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_device(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        device_id = param["device_id"]
        policy_id = param["policy_id"]

        body = {"action_type": "UPDATE_POLICY", "device_id": [device_id], "options": {"policy_id": policy_id}}

        update_policy_api = CBD_UPDATE_DEVICE_API.format(self._org_key)
        ret_val, response = self._make_rest_call(update_policy_api, action_result, data=body, method="post", is_new_api=True)

        if phantom.is_fail(ret_val):
            return ret_val
        action_result.add_data(response)
        action_result.set_summary({"device_id": device_id})

        return action_result.set_status(phantom.APP_SUCCESS, CBD_UPDATED_DEVICE_POLICY)

    def create_process_request(self, param, params, query, result_params):
        if "ip" in param:
            ip = param["ip"]
            ip = ipaddress.ip_address(ip).exploded
            query += f"(device_external_ip:{ip} OR device_internal_ip:{ip})"
        if "host_name" in param:
            query_added = "device_name:{}".format(param["host_name"])
            if query:
                query += " AND " + query_added
            else:
                query += query_added
        if "owner" in param:
            query_added = "device_installed_by:{}".format(param["owner"])
            if query:
                query += " AND " + query_added
            else:
                query += query_added

        if "search_span" in param:
            search_span_val = param["search_span"]
            if "one day" in search_span_val or "one week" in search_span_val or "two weeks" in search_span_val or "one month" in search_span_val:
                span_map = {"one day": "-1d", "one week": "-1w", "two weeks": "-2w", "one month": "-30d"}
                search_span_val = span_map[search_span_val]
            else:
                search_span_val = "-" + search_span_val

            params["time_range"] = {"window": search_span_val}
        params["query"] = query

        return params, query, result_params

    def _handle_list_processes(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        params = {}
        query = ""
        result_params = {}

        params, query, result_params = self.create_process_request(param, params, query, result_params)
        if "start" in param:
            start = self._validate_integer(action_result, param["start"], "start", allow_zero=True)
            if start is None:
                return action_result.get_status()
            result_params["start"] = params["start"] = start
        if "limit" in param:
            limit = self._validate_integer(action_result, param.get("limit", None), "limit", allow_zero=False)
            if limit is None:
                return action_result.get_status()
            result_params["rows"] = params["rows"] = limit

        if not query:
            return action_result.set_status(phantom.APP_ERROR, CBD_REQUIRED_FIELD_MSG_PROCESS)

        get_job_id_api = CBD_LIST_PROCESS_GET_JOB_API.format(self._org_key)
        ret_val, resp_json_job_id = self._make_rest_call(get_job_id_api, action_result, data=params, method="post", is_new_api=True)

        if phantom.is_fail(ret_val):
            return ret_val
        job_id = resp_json_job_id.get("job_id")
        job_name = "process_jobs"
        ret_val, is_completed_eq_contacted = self.retry_search_event(job_id, action_result, job_name)

        if phantom.is_fail(ret_val):
            return ret_val

        get_result_api = CBD_LIST_PROCESS_RESULT_API.format(self._org_key, job_id)
        ret_val, resp_json = self._make_rest_call(get_result_api, action_result, params=result_params, is_new_api=True)

        if phantom.is_fail(ret_val):
            return ret_val

        results = resp_json.get("results", [])

        for result in results:
            action_result.add_data(result)
        total_result = len(results)
        summary = action_result.update_summary({})
        summary["num_results"] = total_result
        message = f"Num results: {total_result}"
        if not is_completed_eq_contacted:
            message += CBD_COMPLETED_NOT_EQ_CONTACTED
        return action_result.set_status(phantom.APP_SUCCESS, message)

    def create_events_data(self, param, params, query):
        if "ip" in param:
            ip = param["ip"]
            ip = ipaddress.ip_address(ip).exploded
            query += f"(device_external_ip:{ip} OR device_internal_ip:{ip})"
        if "host_name" in param:
            query_added = "device_name:{}".format(param["host_name"])
            if query:
                query += " AND " + query_added
            else:
                query += query_added
        if "owner" in param:
            query_added = "device_installed_by:{}".format(param["owner"])
            if query:
                query += " AND " + query_added
            else:
                query += query_added
        if "application" in param:
            query_added = "process_original_filename:{}".format(param["application"])
            if query:
                query += " AND " + query_added
            else:
                query += query_added
        if "event_type" in param:
            query_added = "enriched_event_type:{}".format(param["event_type"])
            if query:
                query += " AND " + query_added
            else:
                query += query_added
        if "hash" in param:
            query_added = "process_hash:{}".format(param["hash"])
            if query:
                query += " AND " + query_added
            else:
                query += query_added
        if "search_span" in param:
            search_span_val = param["search_span"]
            if "one day" in search_span_val or "one week" in search_span_val or "two weeks" in search_span_val:
                span_map = {"one day": "-1d", "one week": "-1w", "two weeks": "-2w"}
                search_span_val = span_map[search_span_val]
            else:
                search_span_val = "-" + search_span_val

            params["time_range"] = {"window": search_span_val}

        params["query"] = query

        return params, query

    def _handle_list_events(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        params = {}
        query = ""

        params, query = self.create_events_data(param, params, query)

        if not query:
            return action_result.set_status(phantom.APP_ERROR, CBD_REQUIRED_FIELD_MSG)

        ret_val, resp_json = self._make_rest_call(
            CBD_LIST_EVENT_GET_JOB_API.format(self._org_key), action_result, data=params, method="post", is_new_api=True
        )
        if phantom.is_fail(ret_val):
            return ret_val

        job_id = resp_json.get("job_id")
        job_name = "search_jobs"
        ret_val, is_completed_eq_contacted = self.retry_search_event(job_id, action_result, job_name)
        if phantom.is_fail(ret_val):
            return ret_val

        ret_val, resp_json_search_result = self._make_rest_call(
            CBD_EVENT_JOB_RESULT_API.format(job_id, self._org_key, job_name), action_result, is_new_api=True
        )

        if phantom.is_fail(ret_val):
            return ret_val

        results = resp_json_search_result.get("results", [])

        for result in results:
            action_result.add_data(result)
        total_result = len(results)
        summary = action_result.update_summary({})
        summary["num_results"] = total_result

        message = f"Num results: {total_result}"
        if not is_completed_eq_contacted:
            message += CBD_COMPLETED_NOT_EQ_CONTACTED
        return action_result.set_status(phantom.APP_SUCCESS, message)

    def retry_search_event(self, job_id, action_result, job_name):
        max_retry = 3
        resp_json_search_event = None
        ret_val = None
        status = False
        while max_retry > 0:
            max_retry -= 1
            if job_name == "search_jobs":
                ret_val, resp_json_search_event = self._make_rest_call(
                    CBD_EVENT_JOB_SEARCH_API.format(job_id, self._org_key, job_name), action_result, is_new_api=True
                )
            elif job_name == "detail_jobs":
                ret_val, resp_json_search_event = self._make_rest_call(
                    CBD_EVENT_JOB_DETAILS_API.format(job_id, self._org_key, job_name), action_result, is_new_api=True
                )
            elif job_name == "process_jobs":
                ret_val, resp_json_search_event = self._make_rest_call(
                    CBD_LIST_PROCESS_VERIFY_JOB_API.format(self._org_key, job_id), action_result, is_new_api=True
                )

            if phantom.is_fail(ret_val):
                return ret_val, False

            if resp_json_search_event.get("completed") != resp_json_search_event.get("contacted"):
                time.sleep(5)
                status = False
            else:
                return ret_val, True

        return ret_val, status

    def _handle_get_event(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        params = {}
        my_list = list(filter(None, param["id"].split(",")))
        params["event_ids"] = my_list
        self.debug_print("query parameters for getEvent are", format(params))

        ret_val, resp_json = self._make_rest_call(
            CBD_GET_EVENT_API.format(self._org_key), action_result, data=params, method="post", is_new_api=True
        )

        if phantom.is_fail(ret_val):
            return ret_val
        job_id = resp_json.get("job_id")
        job_name = "detail_jobs"
        ret_val, is_completed_eq_contacted = self.retry_search_event(job_id, action_result, job_name)

        if phantom.is_fail(ret_val):
            return ret_val

        ret_val, resp_json_search_result = self._make_rest_call(
            CBD_EVENT_JOB_RESULT_API.format(job_id, self._org_key, job_name), action_result, is_new_api=True
        )

        if phantom.is_fail(ret_val):
            return ret_val
        results = resp_json_search_result.get("results", [])

        for result in results:
            action_result.add_data(result)
        total_result = len(results)
        summary = action_result.update_summary({})
        summary["num_results"] = total_result

        message = f"Num results: {total_result}"
        if not is_completed_eq_contacted:
            message += CBD_COMPLETED_NOT_EQ_CONTACTED
        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _handle_get_alert(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        id = param["id"]
        ret_val, resp_json = self._make_rest_call(CBD_GET_ALERT_API.format(id, self._org_key), action_result, is_new_api=True)

        if phantom.is_fail(ret_val):
            if self._status_code != 404:
                return ret_val

            # The id provided might be legacy id. Search for it.
            data = {
                "criteria": {
                    "create_time": {"range": "all"},
                },
                "query": f"alert_id:{id}",
            }
            ret_val, resp_json = self._make_rest_call(
                CBD_SEARCH_ALERT_API.format(self._org_key), action_result, method="post", data=data, is_new_api=True
            )

            if phantom.is_fail(ret_val):
                return ret_val

            results = resp_json.get("results", [])

            if not results:
                return action_result.set_status(phantom.APP_ERROR, f"Alert ID '{id}' does not exist")

            resp_json = results[0]

        action_result.add_data(resp_json)
        summary = action_result.set_summary({})
        summary["device"] = resp_json.get("device_name", "UNKNOWN")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_notifications(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val, resp_json = self._make_rest_call(CBD_NOTIFICATION_API, action_result)

        if phantom.is_fail(ret_val):
            return ret_val

        notifications = resp_json.get("notifications", [])

        for notification in notifications:
            action_result.add_data(notification)

        action_result.set_summary({"num_notifications": len(notifications)})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(param))
        policy_id = param["policy_id"]
        endpoint = CBD_POLICY_API + str(policy_id)

        try:
            data = json.loads(param["policy"])
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, f"Policy needs to be valid JSON data: {self._get_error_message_from_exception(e)}"
            )

        if "policyInfo" not in data:
            data = {"policyInfo": data}

        if "id" not in data.get("policyInfo", {}):
            try:
                data["policyInfo"]["id"] = policy_id
            except TypeError:
                return action_result.set_status(phantom.APP_ERROR, CBD_JSON_FORMAT_ERROR)

        ret_val, response = self._make_rest_call(endpoint, action_result, data=data, method="put")

        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response)
        action_result.set_summary({"policy_id": policy_id})

        return action_result.set_status(phantom.APP_SUCCESS, CBD_POLICY_UPDATED_SUCCESS)

    def _handle_get_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(param))
        policy_id = param["policy_id"]
        endpoint = CBD_POLICY_API + str(policy_id)
        ret_val, response = self._make_rest_call(endpoint, action_result)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, f"Error retrieving policy: {response}")
        action_result.add_data(response)
        action_result.set_summary({"policy_id": policy_id})

        return action_result.set_status(phantom.APP_SUCCESS, CBD_POLICY_RETRIEVED_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)
        elif action_id == "get_notifications":
            ret_val = self._handle_get_notifications(param)
        elif action_id == "list_processes":
            ret_val = self._handle_list_processes(param)
        elif action_id == "list_policies":
            ret_val = self._handle_list_policies(param)
        elif action_id == "create_policy":
            ret_val = self._handle_create_policy(param)
        elif action_id == "delete_policy":
            ret_val = self._handle_delete_policy(param)
        elif action_id == "update_device":
            ret_val = self._handle_update_device(param)
        elif action_id == "list_devices":
            ret_val = self._handle_list_devices(param)
        elif action_id == "list_events":
            ret_val = self._handle_list_events(param)
        elif action_id == "delete_rule":
            ret_val = self._handle_delete_rule(param)
        elif action_id == "get_event":
            ret_val = self._handle_get_event(param)
        elif action_id == "get_alert":
            ret_val = self._handle_get_alert(param)
        elif action_id == "add_rule":
            ret_val = self._handle_add_rule(param)
        elif action_id == "get_policy":
            ret_val = self._handle_get_policy(param)
        elif action_id == "update_policy":
            ret_val = self._handle_update_policy(param)

        return ret_val


if __name__ == "__main__":
    import argparse
    from sys import exit

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument("-v", "--verify", action="store_true", help="verify", required=False, default=False)

    args = argparser.parse_args()
    session_id = None
    csrftoken = None
    headers = None
    username = args.username
    password = args.password
    verify = args.verify

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")
    if username and password:
        try:
            print("Accessing the Login page")
            login_url = BaseConnector._get_phantom_base_url() + "/login"
            r = requests.get(login_url, verify=verify, timeout=CBD_DEFAULT_REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=CBD_DEFAULT_REQUEST_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platfrom. Error: " + str(e))
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = CarbonBlackDefenseConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)
