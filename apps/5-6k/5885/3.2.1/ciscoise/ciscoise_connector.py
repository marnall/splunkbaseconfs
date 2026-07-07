# File: ciscoise_connector.py
#
# Copyright (c) 2014-2025 Splunk Inc.
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
# Phantom imports
import json
import sys

import phantom.app as phantom
import requests
import xmltodict
from cerberus import Validator
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from requests.auth import HTTPBasicAuth

# THIS Connector imports
from ciscoise_consts import *


class CiscoISEConnector(BaseConnector):
    # actions supported by this script
    ACTION_ID_LIST_SESSIONS = "list_sessions"
    ACTION_ID_TERMINATE_SESSION = "terminate_session"
    ACTION_ID_LOGOFF_SYSTEM = "logoff_system"
    ACTION_ID_LIST_ENDPOINTS = "list_endpoints"
    ACTION_ID_GET_ENDPOINT = "get_endpoint"
    ACTION_ID_UPDATE_ENDPOINT = "update_endpoint"
    ACTION_ID_LIST_RESOURCES = "list_resources"
    ACTION_ID_GET_RESOURCES = "get_resources"
    ACTION_ID_DELETE_RESOURCE = "delete_resource"
    ACTION_ID_CREATE_RESOURCE = "create_resource"
    ACTION_ID_UPDATE_RESOURCE = "update_resource"
    ACTION_ID_APPLY_POLICY = "apply_policy"
    ACTION_ID_CLEAR_POLICY = "clear_policy"
    ACTION_ID_LIST_POLICIES = "list_policies"
    ACTION_ID_CREATE_POLICY = "add_policy"
    ACTION_ID_DELETE_POLICY = "delete_policy"
    ACTION_ID_LIST_ANC_ENDPOINTS = "list_anc_endpoints"
    ACTION_ID_GET_ANC_ENDPOINT = "get_anc_endpoint"

    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._base_url = None
        self._auth = None
        self._ha_device = None
        self._ers_auth = None

    def initialize(self):
        config = self.get_config()

        self._auth = HTTPBasicAuth(config[phantom.APP_JSON_USERNAME], config[phantom.APP_JSON_PASSWORD])
        ers_user = config.get("ers_user", None)
        self._ha_device = config.get("ha_device", None)
        if ers_user is not None:
            self._ers_auth = HTTPBasicAuth(config.get("ers_user"), config.get("ers_password"))
        self._base_url = f"https://{config[phantom.APP_JSON_DEVICE]}"

        if self._ha_device:
            self._ha_device_url = f"https://{self._ha_device}"
            self._call_ers_api = self._ha_device_wrapper(self._call_ers_api)
            self._call_rest_api = self._ha_device_wrapper(self._call_rest_api)

        return phantom.APP_SUCCESS

    def _validate_integers(self, action_result, parameter, key, allow_zero=False):
        """This method is to check if the provided input parameter value
        is a non-zero positive integer and returns the integer value of the parameter itself.
        :param action_result: Action result or BaseConnector object
        :param parameter: input parameter
        :return: integer value of the parameter or None in case of failure
        """

        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, CISCOISE_ERROR_INVALID_PARAM.format(key)), None
                parameter = int(parameter)

            except Exception:
                return action_result.set_status(phantom.APP_ERROR, CISCOISE_ERROR_INVALID_PARAM.format(key)), None

            if parameter < 0:
                return (
                    action_result.set_status(phantom.APP_ERROR, f"Please provide a valid non-negative integer value in the {key} parameter"),
                    None,
                )
            if not allow_zero and parameter == 0:
                return action_result.set_status(phantom.APP_ERROR, f"Please provide non-zero positive integer in {key}"), None

        return phantom.APP_SUCCESS, parameter

    def _ha_device_wrapper(self, func):
        def make_another_call(*args, **kwargs):
            self.debug_print("Making call to primary device")
            ret_val, ret_data = func(*args, **kwargs)

            if phantom.is_fail(ret_val) and self._ha_device:
                self.debug_print(f"Call to first device failed. Data returned: {ret_data}")
                self.debug_print("Making call to secondary device")
                ret_val, ret_data = func(try_ha_device=True, *args, **kwargs)

            return ret_val, ret_data

        return make_another_call

    # Wrapped by ha_device_wrapper in initialize(), need pylint E0202 to suppress method-hidden warnings
    def _call_ers_api(self, endpoint, action_result, data=None, allow_unknown=True, method="get", try_ha_device=False, params=None):  # pylint: disable=E0202
        auth_method = self._ers_auth or self._auth
        if not auth_method:
            return action_result.set_status(phantom.APP_ERROR, CISCOISE_ERS_CRED_MISSING), None
        url = f"{self._base_url}{endpoint}"
        if try_ha_device:
            url = f"{self._ha_device_url}{endpoint}"

        self.debug_print(f"url for calling an ERS API: {url}")

        ret_data = None

        config = self.get_config()
        verify = config[phantom.APP_JSON_VERIFY]
        try:
            request_func = getattr(requests, method)
        except AttributeError as e:
            self.debug_print(f"Exception occurred: {e}")
            return action_result.set_status(phantom.APP_ERROR, CISCOISE_ERROR_REST_API, e), ret_data
        try:
            headers = {"Content-Type": "application/json", "ACCEPT": "application/json"}
            resp = request_func(  # nosemgrep: python.requests.best-practice.use-timeout.use-timeout
                url, json=data, verify=verify, headers=headers, auth=auth_method, params=params
            )

        except Exception as e:
            self.debug_print(f"Exception occurred: {e}")
            return action_result.set_status(phantom.APP_ERROR, CISCOISE_ERROR_REST_API, e), ret_data

        if not (200 <= resp.status_code < 399):
            error_message = resp.text
            if resp.status_code == 401:
                error_message = "The request has not been applied because it lacks valid authentication credentials for the target resource."
            elif resp.status_code == 404:
                error_message = "Resource not found"
            return (
                action_result.set_status(phantom.APP_ERROR, CISCOISE_REST_API_ERROR_CODE, code=resp.status_code, message=error_message),
                ret_data,
            )

        if not resp.text:
            return (action_result.set_status(phantom.APP_SUCCESS, "Empty response and no information in the header"), None)

        ret_data = json.loads(resp.text)

        return phantom.APP_SUCCESS, ret_data

    # Wrapped by ha_device_wrapper in initialize(), need pylint E0202 to suppress method-hidden warnings
    def _call_rest_api(self, endpoint, action_result, schema=None, data=None, allow_unknown=True, try_ha_device=False):  # pylint: disable=E0202
        url = f"{self._base_url}{endpoint}"
        if try_ha_device:
            url = f"{self._ha_device_url}{endpoint}"

        ret_data = None

        config = self.get_config()
        verify = config[phantom.APP_JSON_VERIFY]

        try:
            resp = requests.get(url, verify=verify, auth=self._auth)  # nosemgrep: python.requests.best-practice.use-timeout.use-timeout
        except Exception as e:
            self.debug_print(f"Exception occurred: {e}")
            return action_result.set_status(phantom.APP_ERROR, CISCOISE_ERROR_REST_API, e), ret_data

        if resp.status_code != 200:
            return (
                action_result.set_status(
                    phantom.APP_ERROR,
                    CISCOISE_REST_API_ERROR_CODE,
                    code=resp.status_code,
                    message=resp.text,
                ),
                ret_data,
            )

        action_result.add_debug_data(resp.text)
        xml = resp.text

        try:
            response_dict = xmltodict.parse(xml)
        except Exception as e:
            self.debug_print(f"Exception occurred: {e}")
            return action_result.set_status(phantom.APP_ERROR, CISCOISE_ERROR_UNABLE_TO_PARSE_REPLY, e), ret_data

        ret_data = response_dict

        if schema is not None:
            v = Validator(schema, allow_unknown=allow_unknown)
            if v.validate(ret_data) is False:
                action_result.set_status(phantom.APP_ERROR, CISCOISE_ERROR_UNABLE_TO_PARSE_REPLY)
                action_result.append_to_message(v.errors)
                return action_result.get_status(), ret_data

        return phantom.APP_SUCCESS, ret_data

    def _map_resource_type(self, resource_type, action_result, *args):
        try:
            return MAP_RESOURCE[resource_type][0]
        except Exception as ex:
            return action_result.set_status(phantom.APP_ERROR, "Invalid resource type")

    def _list_sessions(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        summary = action_result.update_summary({CISCOISE_JSON_TOTAL_SESSIONS: 0})

        ret_val, ret_data = self._call_rest_api(ACTIVE_LIST_REST, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if "activeList" not in ret_data:
            return action_result.set_status(phantom.APP_SUCCESS)

        active_sessions = ret_data["activeList"].get("activeSession")

        if active_sessions is None:
            return action_result.set_status(phantom.APP_SUCCESS)

        # Convert the dict into list, so the rest of the code is the same
        if isinstance(active_sessions, dict):
            act_sess_list = []
            act_sess_list.append(active_sessions)
            active_sessions = act_sess_list

        for session in active_sessions:
            action_result.add_data(session)

            # Init the value of the quarantine status of the session to unknown
            session["is_quarantined"] = "Unknown"

            # Get the quarantined state of the mac address
            is_quarantined_rest = "{}/{}".format(IS_MAC_QUARANTINED_REST, session["calling_station_id"])

            ret_val, ret_data = self._call_rest_api(is_quarantined_rest, action_result, IS_MAC_QUARAN_RESP_SCHEMA)

            if phantom.is_fail(ret_val):
                continue

            # Can safely access the members of ret_data, since they have been parsed as by the rules of
            # IS_MAC_QUARAN_RESP_SCHEMA
            session["is_quarantined"] = "Yes" if ret_data["EPS_RESULT"]["userData"] == "true" else "No"

        summary.update({CISCOISE_JSON_TOTAL_SESSIONS: len(active_sessions)})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _list_endpoints(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = ERS_ENDPOINT_REST

        mac_filter = param.get("mac_address")
        if mac_filter is not None:
            endpoint = ERS_ENDPOINT_REST + "?filter=mac.EQ." + mac_filter

        ret_val, ret_data = self._call_ers_api(endpoint, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        total = ret_data["SearchResult"]["total"]

        action_result.update_summary({"endpoints_found": total})

        action_result.add_data(ret_data)

        return action_result.set_status(phantom.APP_SUCCESS, CISCOISE_SUCC_LIST_ENDPOINTS.format(total))

    def _get_endpoint(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = ERS_ENDPOINT_REST + "/" + param["endpoint_id"]

        ret_val, ret_data = self._call_ers_api(endpoint, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(ret_data)

        return action_result.set_status(phantom.APP_SUCCESS, CISCOISE_SUCC_GET_ENDPOINT)

    def _update_endpoint(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = ERS_ENDPOINT_REST + "/" + param["endpoint_id"]
        attribute = param.get("attribute", None)
        attribute_value = param.get("attribute_value", None)
        custom_attribute = param.get("custom_attribute", None)
        custom_attribute_value = param.get("custom_attribute_value", None)

        final_data = {"ERSEndPoint": {}}

        if not (attribute or custom_attribute or attribute_value or custom_attribute_value):
            return action_result.set_status(phantom.APP_ERROR, "Please specify attribute or custom attribute")

        if (attribute is not None) ^ (attribute_value is not None):
            return action_result.set_status(phantom.APP_ERROR, "Please specify both attribute and attribute value")
        elif attribute and attribute_value:
            final_data["ERSEndPoint"][attribute] = attribute_value

        if (custom_attribute is not None) ^ (custom_attribute_value is not None):
            return action_result.set_status(phantom.APP_ERROR, "Please specify both custom attribute and custom attribute value")
        elif custom_attribute and custom_attribute_value:
            custom_attribute_dict = {"customAttributes": {custom_attribute: custom_attribute_value}}
            final_data["ERSEndPoint"]["customAttributes"] = custom_attribute_dict

        ret_val, ret_data = self._call_ers_api(endpoint, action_result, data=final_data, method="put")
        action_result.add_data(ret_data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Endpoint Updated")

    def _logoff_system(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        server = param[CISCOISE_JSON_SERVER]
        mac_address = param[CISCOISE_JSON_MACADDR]
        port = 2  # 0 is default, 1 is bounce, 2 is shutdown

        endpoint = f"{REAUTH_MAC_REST}/{server}/{mac_address}/{port}"

        ret_val, ret_data = self._call_rest_api(endpoint, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(ret_data)

        remote_coa = ret_data.get("remoteCoA")

        if remote_coa is None:
            return action_result.set_status(phantom.APP_ERROR, CISCOISE_ERROR_PARSE_REPLY)

        result = remote_coa.get("results")

        if result is None:
            return action_result.set_status(phantom.APP_ERROR, CISCOISE_ERROR_PARSE_REPLY)

        if result == "false":
            return action_result.set_status(phantom.APP_ERROR, CISCOISE_ERROR_LOGOFF_SYSTEM)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _terminate_session(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        mac_address = param[phantom.APP_JSON_MACADDRESS]
        port = 2  # 0 is default, 1 is bounce, 2 is shutdown

        # First try to find the server that we should use
        endpoint = f"{MAC_SESSION_DETAILS_REST}/{mac_address}"

        ret_val, ret_data = self._call_rest_api(endpoint, action_result, MAC_SESSION_RESP_SCHEMA)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        acs_server = ret_data["sessionParameters"]["acs_server"]

        # now terminate the session
        endpoint = f"{DISCONNECT_MAC_REST}/{acs_server}/{mac_address}/{port}"

        ret_val, ret_data = self._call_rest_api(endpoint, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        remote_coa = ret_data.get("remoteCoA")

        if remote_coa is None:
            return action_result.set_status(phantom.APP_ERROR, CISCOISE_ERROR_PARSE_REPLY)

        result = remote_coa.get("results")

        if result is None:
            return action_result.set_status(phantom.APP_ERROR, CISCOISE_ERROR_PARSE_REPLY)

        if result == "false":
            return action_result.set_status(phantom.APP_ERROR, CISCOISE_ERROR_TERMINATE_SESSION)

        return action_result.set_status(phantom.APP_SUCCESS, CISCOISE_SUCC_SESSION_TERMINATED)

    def _paginator(self, endpoint, action_result, limit=None):
        items_list = list()
        params = {}
        if limit:
            params["size"] = min(DEFAULT_MAX_RESULTS, limit)
        else:
            params["size"] = DEFAULT_MAX_RESULTS

        while True:
            ret_val, items = self._call_ers_api(endpoint, action_result, params=params)
            if phantom.is_fail(ret_val):
                self.debug_print("Call to ERS API Failed")
                return None
            items_from_page = items.get("SearchResult", {}).get("resources", [])

            items_list.extend(items_from_page)
            self.debug_print(f"Retrieved {len(items_from_page)} records from the endpoint {endpoint}")

            next_page_dict = items.get("SearchResult", {}).get("nextPage")

            if limit and len(items_list) >= limit:
                self.debug_print("Maximum limit reached")
                return items_list[:limit]
            else:
                if not next_page_dict:
                    self.debug_print("No more records left to retrieve")
                    return items_list
                else:
                    endpoint = next_page_dict.get("href").replace(self._base_url, "")
                    self.debug_print("Next page available")

    def _list_resources(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        resource = self._map_resource_type(param["resource"], action_result)
        ret_val, max_result = self._validate_integers(action_result, param.get("max_results"), "max results")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        endpoint = ERS_RESOURCE_REST.format(resource=resource)

        resources = self._paginator(endpoint, action_result, limit=max_result)

        if resources is None:
            return action_result.get_status()

        for resource in resources:
            action_result.add_data(resource)

        summary = action_result.update_summary({})
        summary["resources_returned"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_resources(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        resource = MAP_RESOURCE[param["resource"]][0]
        resource_id = param.get("resource_id")
        key = param.get("key")
        value = param.get("value")

        if not resource_id and not key:
            return action_result.set_status(
                phantom.APP_ERROR,
                "Please enter either 'resource id' or 'key' and 'value' to get the details of a particular resource",
            )
        elif key and not value:
            return action_result.set_status(phantom.APP_ERROR, "Please enter value for the key")
        if not resource_id and (key and value):
            resource_filter = f"filter={key}.EQ.{value}"
            endpoint = f"{ERS_RESOURCE_REST.format(resource=resource)}?{resource_filter}"

            resources = self._paginator(endpoint, action_result)

            if resources is None:
                return action_result.get_status()

            for resource in resources:
                action_result.add_data(resource)

            summary = action_result.update_summary({})
            summary["resources_returned"] = len(resources)

            return action_result.set_status(phantom.APP_SUCCESS)

        endpoint = f"{ERS_RESOURCE_REST.format(resource=resource)}/{resource_id}"

        ret_val, resp = self._call_ers_api(endpoint, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        summary = action_result.update_summary({})
        summary["resource_id"] = resource_id

        action_result.add_data(resp.get(MAP_RESOURCE[param["resource"]][1]))

        return action_result.set_status(phantom.APP_SUCCESS)

    def _delete_resource(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        resource = MAP_RESOURCE[param["resource"]][0]
        resource_id = param["resource_id"]

        endpoint = f"{ERS_RESOURCE_REST.format(resource=resource)}/{resource_id}"

        ret_val, resp = self._call_ers_api(endpoint, action_result, method="delete")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Resource deleted successfully")

    def _create_resource(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        resource = MAP_RESOURCE[param["resource"]][0]
        try:
            resource_json = json.loads(param["resource_json"])
        except Exception as ex:
            return action_result.set_status(phantom.APP_ERROR, "Error parsing json")

        endpoint = f"{ERS_RESOURCE_REST.format(resource=resource)}"

        ret_val, resp = self._call_ers_api(endpoint, action_result, data=resource_json, method="post")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Resource created successfully")

    def _update_resource(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        resource = MAP_RESOURCE[param["resource"]][0]
        resource_key = MAP_RESOURCE[param["resource"]][1]
        resource_id = param["resource_id"]
        key = param["key"]
        value = param["value"]

        endpoint = f"{ERS_RESOURCE_REST.format(resource=resource)}/{resource_id}"

        data_dict = {resource_key: {}}
        data_dict[resource_key][key] = value
        ret_val, resp = self._call_ers_api(endpoint, action_result, data=data_dict, method="put")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Resource updated successfully")

    def _handle_policy_change(self, action_result, param, change_type="apply"):
        ret_data = None
        policy_name = param.get("policy_name", None)
        ip_mac_address = param.get("ip_mac_address", None)

        payload = {
            "OperationAdditionalData": {
                "additionalData": [
                    {"name": "macAddress", "value": ip_mac_address},
                    {"name": "policyName", "value": policy_name},
                ]
            }
        }

        if phantom.is_mac(ip_mac_address):
            payload["OperationAdditionalData"]["additionalData"][0]["name"] = "macAddress"
        elif phantom.is_ip(ip_mac_address):
            payload["OperationAdditionalData"]["additionalData"][0]["name"] = "ipAddress"
        else:
            return (
                action_result.set_status(phantom.APP_ERROR, CISCOISE_ERROR_MAC_AND_IP_NOT_SPECIFIED),
                ret_data,
            )

        endpoint = ERS_ENDPOINT_ANC_APPLY
        if change_type == "clear":
            endpoint = ERS_ENDPOINT_ANC_CLEAR

        ret_val, ret_data = self._call_ers_api(endpoint, action_result, data=payload, method="put")

        if phantom.is_fail(ret_val):
            return action_result.get_status(), ret_data

        return action_result.set_status(phantom.APP_SUCCESS), ret_data

    def _apply_policy(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        ret_val, ret_data = self._handle_policy_change(action_result, param, "apply")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(ret_data)
        return action_result.set_status(phantom.APP_SUCCESS, "Policy applied")

    def _clear_policy(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        ret_val, ret_data = self._handle_policy_change(action_result, param, "clear")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(ret_data)
        return action_result.set_status(phantom.APP_SUCCESS, "Policy cleared")

    def _list_policies(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = ERS_POLICIES

        ret_val, ret_data = self._call_ers_api(endpoint, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        total = ret_data["SearchResult"]["total"]
        policies = ret_data["SearchResult"]["resources"]

        for policy in policies:
            endpoint = f"{ERS_POLICIES}/{policy['id']}"

            ret_val, ret_data = self._call_ers_api(endpoint, action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            data = ret_data["ErsAncPolicy"]
            data["actions"] = ", ".join(data["actions"])
            action_result.add_data(data)

        action_result.update_summary({"policies_found": total})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _delete_policy(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = f"{ERS_POLICIES}/{param['policy_name']}"

        ret_val, ret_data = self._call_ers_api(endpoint, action_result, method="delete")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Policy deleted")

    def _add_policy(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        body = {"ErsAncPolicy": {"name": param["name"], "actions": [param["action_type"]]}}

        endpoint = f"{ERS_POLICIES}"

        ret_val, ret_data = self._call_ers_api(endpoint, action_result, method="post", data=body)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Policy created")

    def _test_connectivity_to_device(self, base_url, verify=True):
        try:
            rest_endpoint = f"{base_url}{ACTIVE_LIST_REST}"
            self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, base_url)
            resp = requests.get(  # nosemgrep: python.requests.best-practice.use-timeout.use-timeout
                rest_endpoint, auth=self._auth, verify=verify
            )
        except Exception as e:
            return False, str(e)

        if resp.status_code == 200:
            return True, ""

        return False, resp.text

    def _test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        config = self.get_config()
        verify = config[phantom.APP_JSON_VERIFY]
        result, message = self._test_connectivity_to_device(self._base_url, verify)

        if not result:
            self.save_progress("Error occurred while connecting to primary device")
            self.save_progress(str(message))
            self.save_progress(CISCOISE_ERROR_TEST_CONNECTIVITY_FAILED_PRIMARY_DEVICE)
            action_result.set_status(phantom.APP_ERROR)
        else:
            self.save_progress(CISCOISE_SUCC_TEST_CONNECTIVITY_PASSED_1)
            action_result.set_status(phantom.APP_SUCCESS, CISCOISE_SUCC_TEST_CONNECTIVITY_PASSED_1)

        if self._ha_device:
            result, message = self._test_connectivity_to_device(self._ha_device_url, verify)

            if not result:
                self.save_progress("Error occurred while connecting to high availability device")
                self.save_progress(str(message))
                self.save_progress(CISCOISE_ERROR_TEST_CONNECTIVITY_FAILED_HA_DEVICE)
            else:
                self.save_progress(CISCOISE_SUCC_TEST_CONNECTIVITY_PASSED_2)

        return action_result.get_status()

    def _list_anc_endpoints(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = ERS_ENDPOINT_ANC

        ret_val, ret_data = self._call_ers_api(endpoint, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        total = ret_data.get("SearchResult", {}).get("total")

        action_result.update_summary({"endpoints_found": total})

        action_result.add_data(ret_data)

        return action_result.set_status(phantom.APP_SUCCESS, CISCOISE_SUCC_LIST_ENDPOINTS.format(total))

    def _get_anc_endpoint(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = ERS_ENDPOINT_ANC + "/" + param["endpoint_id"]

        ret_val, ret_data = self._call_ers_api(endpoint, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(ret_data)

        return action_result.set_status(phantom.APP_SUCCESS, CISCOISE_SUCC_GET_ENDPOINT)

    def handle_action(self, param):
        result = None
        action = self.get_action_identifier()

        if action == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            result = self._test_connectivity(param)
        elif action == self.ACTION_ID_LIST_SESSIONS:
            result = self._list_sessions(param)
        elif action == self.ACTION_ID_TERMINATE_SESSION:
            result = self._terminate_session(param)
        elif action == self.ACTION_ID_LOGOFF_SYSTEM:
            result = self._logoff_system(param)
        elif action == self.ACTION_ID_LIST_ENDPOINTS:
            result = self._list_endpoints(param)
        elif action == self.ACTION_ID_GET_ENDPOINT:
            result = self._get_endpoint(param)
        elif action == self.ACTION_ID_UPDATE_ENDPOINT:
            result = self._update_endpoint(param)
        elif action == self.ACTION_ID_LIST_RESOURCES:
            result = self._list_resources(param)
        elif action == self.ACTION_ID_GET_RESOURCES:
            result = self._get_resources(param)
        elif action == self.ACTION_ID_DELETE_RESOURCE:
            result = self._delete_resource(param)
        elif action == self.ACTION_ID_CREATE_RESOURCE:
            result = self._create_resource(param)
        elif action == self.ACTION_ID_UPDATE_RESOURCE:
            result = self._update_resource(param)
        elif action == self.ACTION_ID_APPLY_POLICY:
            result = self._apply_policy(param)
        elif action == self.ACTION_ID_CLEAR_POLICY:
            result = self._clear_policy(param)
        elif action == self.ACTION_ID_LIST_POLICIES:
            result = self._list_policies(param)
        elif action == self.ACTION_ID_CREATE_POLICY:
            result = self._add_policy(param)
        elif action == self.ACTION_ID_DELETE_POLICY:
            result = self._delete_policy(param)
        elif action == self.ACTION_ID_LIST_ANC_ENDPOINTS:
            result = self._list_anc_endpoints(param)
        elif action == self.ACTION_ID_GET_ANC_ENDPOINT:
            result = self._get_anc_endpoint(param)

        return result


if __name__ == "__main__":
    import argparse

    import pudb

    pudb.set_trace()

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
        login_url = BaseConnector._get_phantom_base_url() + "login"
        try:
            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=30)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=30)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platfrom. Error: " + str(e))
            sys.exit(1)

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = CiscoISEConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
