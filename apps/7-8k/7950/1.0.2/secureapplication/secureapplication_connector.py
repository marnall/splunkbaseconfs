# Copyright (c) 2025-2026 Splunk Inc.
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

# Secure Application Connector

# Phantom App imports
import json
import time

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from secureapplication_consts import ENDPOINT_PREFIX, POLICYCONFIGS_ENDPOINT_PREFIX


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class SecureApplicationConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        self._base_url = None

        # Policy type to policyTypeId
        self._policy_type_map = {
            "Command execution": 1,
            "Filesystem access": 2,
            "Network or socket access": 3,
            "Database queries": 4,
            "Libraries loaded at runtime": 5,
            "Unhandled exceptions": 6,
            "Headers in http transactions": 7,
            "Cookies in outgoing http response": 8,
            "Class deserialization at runtime": 9,
        }

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, f"Empty response and no information in the header"), None)

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
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {e!s}"), None)

        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

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
        message = "Error: Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = self._base_url + endpoint

        try:
            r = request_func(url, verify=config.get("verify_server_cert", False), **kwargs)
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {e!s}"), resp_json)

        # Handle 204 No Content
        if r.status_code == 204:
            return RetVal(action_result.set_status(phantom.APP_SUCCESS), {})

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = ENDPOINT_PREFIX + "libraries"
        headers = self._get_rest_api_headers(token=self._token)

        # make REST call - list all libaries
        ret_val, response = self._make_rest_call(endpoint, action_result, headers=headers, method="get")
        if self._debug:
            self.debug_print(f"Test connectivity response: {response}")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, f"Test connectivity successful")

    def _handle_create_new_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        required_params = ["type", "application_id", "tier_id", "default_action", "enable_policy"]
        missing = []

        for p in required_params:
            if not param.get(p):
                missing.append(p)

        if missing:
            missing_str = ", ".join(missing)
            return action_result.set_status(phantom.APP_ERROR, f"Missing required parameter({missing_str})")

        policy_type = param["type"]
        application_id = param["application_id"]
        if application_id.lower() == "all":
            application_id = None
        tier_id = param["tier_id"]
        if tier_id.lower() == "all":
            tier_id = None
        default_action = param["default_action"]
        if default_action.lower() == "ignore":
            default_action = "NONE"
        enable_policy = param["enable_policy"]
        policy_type_id = self._policy_type_map.get(policy_type)
        if not policy_type_id:
            return action_result.set_status(phantom.APP_ERROR, f"Unsupported policy type: {policy_type}")

        status = "ON" if enable_policy.upper() == "YES" else "OFF"

        payload = {
            "action": default_action,
            "applicationId": application_id,
            "tierId": tier_id,
            "status": status,
            "policyTypeId": policy_type_id,
            "operativePolicyTypeId": policy_type_id,
        }

        headers = self._get_rest_api_headers(token=self._token)
        # make rest call
        ret_val, response = self._make_rest_call(POLICYCONFIGS_ENDPOINT_PREFIX, action_result, json=payload, headers=headers, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_new_policy_for_http_transaction_header(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        required_params = ["application_id", "tier_id", "default_action", "enable_policy"]
        missing = []

        for p in required_params:
            if not param.get(p):
                missing.append(p)

        if missing:
            missing_str = ", ".join(missing)
            return action_result.set_status(phantom.APP_ERROR, f"Missing required parameter({missing_str})")

        policy_type = "Headers in http transactions"
        policy_type_id = self._policy_type_map.get(policy_type)

        application_id = param["application_id"]
        if application_id.lower() == "all":
            application_id = None

        tier_id = param["tier_id"]
        if tier_id.lower() == "all":
            tier_id = None

        default_action = param["default_action"]
        if default_action.lower() == "ignore":
            default_action = "NONE"

        enable_policy = param["enable_policy"]
        status = "ON" if enable_policy.upper() == "YES" else "OFF"

        headers_to_check = ["Strict-Transport-Security", "X-Frame-Options", "X-XSS-Protection", "X-Content-Type-Options"]

        config_rules = []
        for header in headers_to_check:
            action_key = f"action for {header}"
            patch_key = f"patch value for {header}"

            rule_action = param.get(action_key)
            patch_value = param.get(patch_key)

            if not rule_action:
                rule_action = "DETECT"

            if rule_action.lower() == "ignore":
                rule_action = "NONE"
            else:
                rule_action = rule_action.upper()

            rule = {
                "action": rule_action,
                "header": header,
                "value": patch_value,
            }
            config_rules.append(rule)

        config_details = {"header": {"header": config_rules}}

        payload = {
            "action": default_action,
            "applicationId": application_id,
            "tierId": tier_id,
            "status": status,
            "policyTypeId": policy_type_id,
            "operativePolicyTypeId": policy_type_id,
            "configDetails": self._encode_config_details(config_details),
        }

        headers = self._get_rest_api_headers(token=self._token)
        # make rest call
        ret_val, response = self._make_rest_call(POLICYCONFIGS_ENDPOINT_PREFIX, action_result, json=payload, headers=headers, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        policy_id = param.get("policy_id")
        if not policy_id:
            return action_result.set_status(phantom.APP_ERROR, f"Missing or empty 'policy_id' parameter")

        endpoint = POLICYCONFIGS_ENDPOINT_PREFIX + f"/{policy_id}"
        headers = self._get_rest_api_headers(token=self._token)
        # REST CALL - delete
        ret_val, response = self._make_rest_call(endpoint, action_result, headers=headers, method="delete")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data({"message": "Policy deleted successfully", "policy_id": policy_id})
        return action_result.set_status(phantom.APP_SUCCESS, f"Policy deleted successfully.")

    def _handle_get_policy_by_id(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        policy_id = param.get("policy_id")
        if not policy_id:
            return action_result.set_status(phantom.APP_ERROR, f"Missing or empty 'policy_id' parameter")

        ret_val, response = self._get_policy_by_id(policy_id, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if self._debug:
            self.debug_print(f"Delete policy response: {response}")

        action_result.add_data(response)
        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully retrieved policy")

    def _handle_list_policies(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        headers = self._get_rest_api_headers(token=self._token)

        limit = 10  # Adjust based on API default or max
        offset = 0
        all_policies = []
        total = None

        while True:
            self.debug_print(f"Fetching policies with offset {offset} and limit {limit}")
            url = f"{POLICYCONFIGS_ENDPOINT_PREFIX}?limit={limit}&offset={offset}"
            ret_val, response = self._make_rest_call(url, action_result, headers=headers, method="get")

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            if not isinstance(response, dict):
                return action_result.set_status(phantom.APP_ERROR, f"Unexpected API response format")
            items = response.get("items", [])
            total = response.get("total", total)

            self.debug_print(f"Retrieved {len(items)} items, total so far: {len(all_policies)} / {total}")
            all_policies.extend(items)

            if total is None or len(all_policies) >= total:
                break

            offset += limit

        for policy in all_policies:
            if policy.get("applicationId") is None or str(policy["applicationId"]).lower() in ["null", "none", ""]:
                policy["applicationId"] = "All"
            if policy.get("tierId") is None or str(policy["tierId"]).lower() in ["null", "none", ""]:
                policy["tierId"] = "All"
            action_result.add_data(policy)

        action_result.set_summary({"total_policies": len(all_policies)})
        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully retrieved policies")

    def _handle_update_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        policy_id = param.get("policy_id")
        if not policy_id:
            return action_result.set_status(phantom.APP_ERROR, f"Missing 'policy_id' parameter")

        policy_status = None
        enable_policy = param.get("enable_policy")
        if enable_policy:
            policy_status = "ON" if enable_policy.upper() == "YES" else "OFF"

        # Get existing policy
        status, existing_policy = self._get_policy_by_id(policy_id, action_result)
        if phantom.is_fail(status):
            return action_result.get_status()

        if not existing_policy:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to retrieve existing policy")

        updated_policy = existing_policy.copy()

        # Apply updates
        if "enable_policy" in param:
            updated_policy["status"] = policy_status

        if "default_action" in param:
            if param["default_action"].lower() == "ignore":
                updated_policy["action"] = "NONE"
            else:
                updated_policy["action"] = param["default_action"]

        if "tier_id" in param:
            updated_policy["tierId"] = param["tier_id"]
            if updated_policy["tierId"].lower() == "all":
                updated_policy["tierId"] = None

        if "application_id" in param:
            updated_policy["applicationId"] = param["application_id"]
            if updated_policy["applicationId"].lower() == "all":
                updated_policy["applicationId"] = None

        # rest call - update policy
        endpoint = POLICYCONFIGS_ENDPOINT_PREFIX + f"/{policy_id}"
        headers = self._get_rest_api_headers(token=self._token)

        ret_val, response = self._make_rest_call(endpoint, action_result, json=updated_policy, headers=headers, method="patch")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        action_result.set_summary({"updated_policy_id": policy_id})
        return action_result.set_status(phantom.APP_SUCCESS, f"Policy updated successfully")

    def _handle_add_a_rule_to_command_execution_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        policyType = self._policy_type_map.get("Command execution")
        status = self._send_updated_policy_with_rule_change(param, action_result, True, False, policyType)
        if phantom.is_success(status):
            policy_id = param.get("policy_id")
            if policy_id:
                status, rules, _ = self._get_rules_from_policy(policy_id, action_result)
                if phantom.is_success(status):
                    for rule in rules:
                        action_result.add_data(rule)
                    action_result.update_summary({"total_rules": len(rules)})
            return action_result.set_status(status, f"Rule added to Command execution policy successfully")

        return status

    def _handle_add_a_rule_to_filesystem_access_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        policyType = self._policy_type_map.get("Filesystem access")
        status = self._send_updated_policy_with_rule_change(param, action_result, True, False, policyType)
        if phantom.is_success(status):
            policy_id = param.get("policy_id")
            if policy_id:
                status, rules, _ = self._get_rules_from_policy(policy_id, action_result)
                if phantom.is_success(status):
                    for rule in rules:
                        action_result.add_data(rule)
                    action_result.update_summary({"total_rules": len(rules)})
            return action_result.set_status(status, f"Rule added to Command execution policy successfully")

        return status

    def _handle_add_a_rule_to_network_or_socket_access_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        policyType = self._policy_type_map.get("Network or socket access")
        status = self._send_updated_policy_with_rule_change(param, action_result, True, False, policyType)
        if phantom.is_success(status):
            policy_id = param.get("policy_id")
            if policy_id:
                status, rules, _ = self._get_rules_from_policy(policy_id, action_result)
                if phantom.is_success(status):
                    for rule in rules:
                        action_result.add_data(rule)
                    action_result.update_summary({"total_rules": len(rules)})
            return action_result.set_status(status, f"Rule added to Command execution policy successfully")

        return status

    def _handle_delete_a_rule_from_command_execution_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        status = self._send_updated_policy_with_rule_change(param, action_result, False, True, self._policy_type_map.get("Command execution"))
        if phantom.is_success(status):
            policy_id = param.get("policy_id")
            if policy_id:
                status, rules, _ = self._get_rules_from_policy(policy_id, action_result)
                if phantom.is_success(status):
                    for rule in rules:
                        action_result.add_data(rule)
                    action_result.update_summary({"total_rules": len(rules)})
            return action_result.set_status(status, f"Rule added to Command execution policy successfully")

        return status

    def _handle_delete_a_rule_from_filesystem_access_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        status = self._send_updated_policy_with_rule_change(param, action_result, False, True, self._policy_type_map.get("Filesystem access"))
        if phantom.is_success(status):
            policy_id = param.get("policy_id")
            if policy_id:
                status, rules, _ = self._get_rules_from_policy(policy_id, action_result)
                if phantom.is_success(status):
                    for rule in rules:
                        action_result.add_data(rule)
                    action_result.update_summary({"total_rules": len(rules)})
            return action_result.set_status(status, f"Rule added to Command execution policy successfully")

        return status

    def _handle_delete_a_rule_from_network_or_socket_access_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        status = self._send_updated_policy_with_rule_change(
            param, action_result, False, True, self._policy_type_map.get("Network or socket access")
        )
        if phantom.is_success(status):
            policy_id = param.get("policy_id")
            if policy_id:
                status, rules, _ = self._get_rules_from_policy(policy_id, action_result)
                if phantom.is_success(status):
                    for rule in rules:
                        action_result.add_data(rule)
                    action_result.update_summary({"total_rules": len(rules)})
            return action_result.set_status(status, f"Rule added to Command execution policy successfully")

        return status

    def _handle_list_all_rules(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        policy_id = param.get("policy_id")

        if not policy_id:
            return action_result.set_status(phantom.APP_ERROR, "Missing policy ID")

        status, rules, message = self._get_rules_from_policy(policy_id, action_result)
        if phantom.is_fail(status):
            return action_result.set_status(phantom.APP_ERROR, message)

        for rule in rules:
            action_result.add_data(rule)

        action_result.update_summary({"total_rules": len(rules)})
        return action_result.set_status(status, message)

    def _get_policy_by_id(self, policy_id, action_result):
        endpoint = POLICYCONFIGS_ENDPOINT_PREFIX + f"/{policy_id}"

        headers = self._get_rest_api_headers(token=self._token)

        ret_val, response = self._make_rest_call(endpoint, action_result, headers=headers, method="get")

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, response

    def _get_policy_by_id_from_list(self, policy_id, action_result):
        headers = self._get_rest_api_headers(token=self._token)

        ret_val, response = self._make_rest_call(POLICYCONFIGS_ENDPOINT_PREFIX, action_result, headers=headers, method="get")

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        policies = response.get("items")

        if not isinstance(policies, list):
            return action_result.set_status(phantom.APP_ERROR, f"Unexpected response format while retrieving policies"), None

        for policy in policies:
            if policy.get("id") == policy_id:
                return phantom.APP_SUCCESS, policy

        return action_result.set_status(phantom.APP_ERROR, f"Policy with ID {policy_id} not found"), None

    # Helper function to decode configDetails from policy into a dict
    def _decode_config_details(self, config_details_str):
        if config_details_str:
            return json.loads(config_details_str)
        return {"permission": {"filter": []}}

    # Helper functiom to add a rule to configDetails
    def _append_rule_to_config(self, config_dict, rule):
        config_dict.setdefault("permission", {}).setdefault("filter", []).append(rule)
        return config_dict

    # Helper function to delete a rule from configDetails
    # {\"permission\":{\"filter\":[{\"action\":\"DETECT\",\"targetMatch\":      {\"matchType\":\"EQUALS\",\"value\":\"aaaaaaa.exe\"},\"name\":\"detect aaaaaaa.exe\"}]}}
    def _delete_rule_from_config(self, config_dict, rule_to_delete):
        filters = config_dict.get("permission", {}).get("filter", [])
        updated_filters = []
        rule_found = False

        if "targetMatch" in rule_to_delete:
            match_field = "targetMatch"
        else:
            match_field = "stackMatch"

        # Build a new list excluding the rule(s) to be deleted
        for rule in filters:
            self.debug_print("Comparing rule:", rule)
            self.debug_print("With rule_to_delete:", rule_to_delete)

            if match_field not in rule:
                updated_filters.append(rule)
                continue

            rule_filter = rule.get(match_field, {})
            delete_rule_filter = rule_to_delete.get(match_field, {})

            if (
                rule.get("action") == rule_to_delete.get("action")
                and rule_filter.get("matchType") == delete_rule_filter.get("matchType")
                and rule_filter.get("value") == delete_rule_filter.get("value")
            ):
                rule_found = True
                continue

            updated_filters.append(rule)

        config_dict.setdefault("permission", {})["filter"] = updated_filters
        return config_dict, rule_found

    # Helper function to encode the configDetails dict to json
    def _encode_config_details(self, config_dict):
        return json.dumps(config_dict)

    # Helper function to  add/delete rule
    def _send_updated_policy_with_rule_change(self, param, action_result, add, delete, policyType):
        required_params = ["policy_id", "action", "value", "operation", "type"]
        missing = []

        for p in required_params:
            if not param.get(p):
                missing.append(p)

        if missing:
            missing_str = ", ".join(missing)
            return action_result.set_status(phantom.APP_ERROR, f"Missing required parameter({missing_str})")
        policy_id = param["policy_id"]
        rule_action = param["action"]
        rule_value = param["value"]
        rule_operation = param["operation"]
        rule_type = param["type"]

        # Get existing policy
        status, existing_policy = self._get_policy_by_id(policy_id, action_result)
        if phantom.is_fail(status):
            return action_result.get_status()

        if not existing_policy:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to retrieve existing policy")

        if existing_policy["policyTypeId"] != policyType:
            return action_result.set_status(phantom.APP_ERROR, f"Incorrect action chosen for the policy type")

        # Parse configDetails
        config_details = self._decode_config_details(existing_policy.get("configDetails"))

        # Build the new rule
        operation_map = {"equals": "EQUALS", "contains": "SUBSTRING", "matches regex": "REGEX", "starts with": "STARTSWITH"}

        match_type = operation_map.get(rule_operation.lower())
        if match_type is None:
            return action_result.set_status(phantom.APP_ERROR, f"Unsupported match operation: {rule_operation}")

        match_field = None
        if rule_type == "stack trace":
            match_field = "stackMatch"
        elif rule_type in ("filename", "hostname", "process"):
            match_field = "targetMatch"
        else:
            return action_result.set_status(phantom.APP_ERROR, f"Unsupported rule type: {rule_type}")

        if rule_action.lower() == "ignore":
            action = "NONE"
        else:
            action = rule_action.upper()

        rule = {"action": action, match_field: {"matchType": match_type, "value": rule_value}, "name": f"{rule_action.lower()} {rule_value}"}

        updated_config = config_details
        if add:
            # Add rule to the json dict retrieved for configDetails
            updated_config = self._append_rule_to_config(config_details, rule)

        if delete:
            # Delete a rule from the json dict retrieved for configDetails
            updated_config, rule_found = self._delete_rule_from_config(config_details, rule)
            if not rule_found:
                action_result.set_status(phantom.APP_ERROR, f"Specified rule not found in config")
                return action_result.get_status()

        # Encode configDetails dict into json
        existing_policy["configDetails"] = self._encode_config_details(updated_config)

        # Patch the updated policy
        endpoint = POLICYCONFIGS_ENDPOINT_PREFIX + f"/{policy_id}"
        headers = self._get_rest_api_headers(token=self._token)
        self.debug_print(f"Sending updated policy:\n{json.dumps(existing_policy, indent=2)}")

        ret_val, response = self._make_rest_call(endpoint, action_result, json=existing_policy, headers=headers, method="patch")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # action_result.add_data(response)
        return phantom.APP_SUCCESS

    def _get_rules_from_policy(self, policy_id, action_result):
        status, existing_policy = self._get_policy_by_id(policy_id, action_result)
        if phantom.is_fail(status) or not existing_policy:
            return (phantom.APP_ERROR, [], f"Failed to retrieve policy")

        policy_type = existing_policy.get("policyTypeId")
        config_details = self._decode_config_details(existing_policy.get("configDetails"))

        rules = config_details.get("permission", {}).get("filter", [])
        if not rules:
            return (phantom.APP_SUCCESS, [], f"No rules found in policy")

        reverse_operation_map = {"EQUALS": "equals", "STARTSWITH": "starts with", "SUBSTRING": "contains", "REGEX": "matches regex"}

        formatted_rules = []
        for rule in rules:
            if not ("stackMatch" in rule or "targetMatch" in rule):
                continue

            entry = {"name": rule.get("name", "")}
            action = rule.get("action", "").upper()
            entry["action"] = "ignore" if action == "NONE" else action.lower()

            match = rule.get("stackMatch") or rule.get("targetMatch")
            if "stackMatch" in rule:
                entry["type"] = "stack trace"
            elif "targetMatch" in rule:
                if self._policy_type_map.get("Command execution") == policy_type:
                    entry["type"] = "process"
                elif self._policy_type_map.get("Filesystem access") == policy_type:
                    entry["type"] = "filename"
                elif self._policy_type_map.get("Network or socket access") == policy_type:
                    entry["type"] = "hostname"

            entry["operation"] = reverse_operation_map.get(match.get("matchType"), "unknown")
            entry["value"] = match.get("value")

            formatted_rules.append(entry)

        return (phantom.APP_SUCCESS, formatted_rules, f"Successfully retrieved rules from policy")

    def _get_authentication_token(self, url, account, api_key, api_secret):
        # Load the saved token to check its ttl to see if it can be used
        state = self.get_state()
        current_time = int(time.time())

        token = state.get("access_token")
        expiry = state.get("token_expiry", 0)

        # Reuse token if it's still valid
        if token and current_time < expiry:
            self._token = token
            self.debug_print(f"Reusing access token from state. Token expires in {expiry - current_time} seconds.")
            return token

        self.debug_print("Access token expired or missing. Requesting new token...")
        try:
            response = requests.post(
                f"{url}/controller/api/oauth/access_token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "client_credentials", "client_id": f"{api_key}@{account}", "client_secret": api_secret},
                verify=False,
                timeout=15,
            )
        except Exception as e:
            raise Exception(f"Access token request failed: {e}")

        action_result = ActionResult(dict())  # temporary

        ret_val, r_json = self._process_response(response, action_result)
        if phantom.is_fail(ret_val):
            raise Exception(f"Token request failed: {action_result.get_message()}")

        # Get token and calculate its expiration time
        token = r_json["access_token"]
        expires = r_json.get("expires_in", 1800)
        if not token:
            raise Exception(f"Token response received, but access_token is missing")

        # Set new token and expiry with buffer (60 seconds)
        expiry = current_time + int(expires) - 60

        # Save to state
        state["access_token"] = token
        state["token_expiry"] = expiry
        self.save_state(state)
        self._token = token

        return self._token

    def _get_rest_api_headers(self, token=None):
        if token is None:
            token = self._get_authentication_token(self._base_url, self._account_id, self._api_key, self._api_key_secret)

        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        action_mapping = {
            "create_new_policy": self._handle_create_new_policy,
            "create_new_policy_for_http_transaction_header": self._handle_create_new_policy_for_http_transaction_header,
            "delete_policy": self._handle_delete_policy,
            "get_policy_by_id": self._handle_get_policy_by_id,
            "list_policies": self._handle_list_policies,
            "update_policy": self._handle_update_policy,
            "add_a_rule_to_command_execution_policy": self._handle_add_a_rule_to_command_execution_policy,
            "add_a_rule_to_filesystem_access_policy": self._handle_add_a_rule_to_filesystem_access_policy,
            "add_a_rule_to_network_or_socket_access_policy": self._handle_add_a_rule_to_network_or_socket_access_policy,
            "delete_a_rule_from_command_execution_policy": self._handle_delete_a_rule_from_command_execution_policy,
            "delete_a_rule_from_filesystem_access_policy": self._handle_delete_a_rule_from_filesystem_access_policy,
            "delete_a_rule_from_network_or_socket_access_policy": self._handle_delete_a_rule_from_network_or_socket_access_policy,
            "list_all_rules": self._handle_list_all_rules,
            "test_connectivity": self._handle_test_connectivity,
        }

        action = self.get_action_identifier()
        action_execution_status = phantom.APP_SUCCESS

        action_keys = list(action_mapping.keys())
        if action in action_keys:
            action_function = action_mapping[action]
            action_execution_status = action_function(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()

        self._base_url = config.get("base_url")
        self._account_id = config.get("account_id")
        self._api_key = config.get("api_key")
        self._api_key_secret = config.get("api_key_secret")
        self._token = None

        # debug turned on to connect to CI environment
        self._debug = False

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

    argparser = argparse.ArgumentParser()
    argparser.add_argument("input_test_json", help="Input Test JSON file")

    args = argparser.parse_args()
    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = SecureApplicationConnector()
        connector.print_progress_message = True

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)


if __name__ == "__main__":
    main()
