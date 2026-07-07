# File: ciscosecurefirewall_connector.py
#
# Copyright (c) 2025 Splunk Inc.
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
from typing import Any, Optional

import encryption_helper
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from requests.auth import HTTPBasicAuth
from requests.models import Response

from ciscosecurefirewall_consts import (
    ACCESS_POLICY_ENDPOINT,
    ACCESS_POLICY_ID_ENDPOINT,
    ACCESS_RULES_ENDPOINT,
    ACCESS_RULES_ID_ENDPOINT,
    CLOUD_HOST,
    DEFAULT_REQUEST_TIMEOUT,
    DEPLOY_DEVICES_ENDPOINT,
    DEPLOYMENT_STATUS_ENDPOINT,
    DEVICES_ENDPOINT,
    ENCRYPTION_ERR,
    GET_DEPLOYABLE_DEVICES_ENDPOINT,
    GET_HOSTS_ENDPOINT,
    HEADERS,
    INTRUSION_POLICY_ENDPOINT,
    INTRUSION_POLICY_ID_ENDPOINT,
    NETWORK_GROUPS_ENDPOINT,
    NETWORK_GROUPS_ID_ENDPOINT,
    NETWORK_OBJECT_ID_ENDPOINT,
    NETWORK_OBJECTS_ENDPOINT,
    OBJECT_TYPES,
    REFRESH_COUNT,
    REFRESH_ENDPOINT,
    REFRESH_TOKEN_KEY,
    STATE_FILE_CORRUPT_ERR,
    TOKEN_ENDPOINT,
    TOKEN_KEY,
)


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class FP_Connector(BaseConnector):
    def __init__(self):
        """
        Instance variables
        """
        # Call the BaseConnectors init first
        super().__init__()

        self.username = ""
        self.password = ""
        self.firepower_host = ""
        self.headers = HEADERS
        self.verify = False
        self.default_firepower_domain = None
        self.refresh_count = 0

    def _reset_state_file(self) -> None:
        """
        This method resets the state file.
        """
        self.debug_print("Resetting the state file with the default format")
        self._state = {"app_version": self.get_app_json().get("app_version")}
        self.save_state(self._state)

    def initialize(self) -> bool:
        """
        Initializes the global variables and validates them.

        This is an optional function that can be implemented by the
        AppConnector derived class. Since the configuration dictionary
        is already validated by the time this function is called,
        it's a good place to do any extra initialization of any internal
        modules. This function MUST return a value of either
        phantom.APP_SUCCESS or phantom.APP_ERROR.  If this function
        returns phantom.APP_ERROR, then AppConnector::handle_action
        will not get called.
        """
        self._state = self.load_state()
        config = self.get_config()
        action_result = ActionResult()

        if not isinstance(self._state, dict):
            self.debug_print(STATE_FILE_CORRUPT_ERR)
            self._reset_state_file()

        self.fmc_type = config["fmc_type"]

        if self.is_cloud_deployment():
            ret_val = self.authenicate_cloud_fmc(config)
        else:
            self.asset_id = self.get_asset_id()
            try:
                if TOKEN_KEY in self._state:
                    self.debug_print("Decrypting the token")
                    self._state[TOKEN_KEY] = encryption_helper.decrypt(self._state[TOKEN_KEY], self.asset_id)
                if "domains" in self._state:
                    self.domains = self._state["domains"]
            except Exception as e:
                self.debug_print(f"Error occurred while decrypting the token: {e!s}")
                self._reset_state_file()

            self.firepower_host = config["firepower_host"]
            self.username = config["username"]
            self.password = config["password"]
            self.default_firepower_domain = config.get("domain_name")
            self.verify = config.get("verify_server_cert", False)
            self.refresh_token = self._state.get(REFRESH_COUNT, 0)

            ret_val = self._get_token(action_result)

        if phantom.is_fail(ret_val):
            return self.get_status()

        return phantom.APP_SUCCESS

    def finalize(self) -> bool:
        """
        Performs some final operations or clean up operations.

        This function gets called once all the param dictionary
        elements are looped over and no more handle_action calls are
        left to be made. It gives the AppConnector a chance to loop
        through all the results that were accumulated by multiple
        handle_action function calls and create any summary if
        required. Another usage is cleanup, disconnect from remote
        devices etc.
        """
        try:
            if TOKEN_KEY in self._state:
                self.debug_print("Encrypting the token")
                self._state[TOKEN_KEY] = encryption_helper.encrypt(self._state[TOKEN_KEY], self.asset_id)
        except Exception as e:
            self.debug_print(f"{ENCRYPTION_ERR}: {e!s}")
            self._reset_state_file()

        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _update_state(self) -> None:
        """
        This method updates the state with the new values.
        """
        self._state[TOKEN_KEY] = self.token
        self._state[REFRESH_TOKEN_KEY] = self.refresh_token
        self._state[REFRESH_COUNT] = self.refresh_count
        self._state["domains"] = self.domains
        self.save_state(self._state)

    def authenicate_cloud_fmc(self, config: dict[str, Any]) -> bool:
        """
        This method updates the headers and sets the firepower host
        based on the users region when connecting to a cloud FMC.
        """
        region = config["region"]
        api_key = config["api_key"]
        self.firepower_host = CLOUD_HOST.format(region=region.lower())
        self.headers.update({"Authorization": f"Bearer {api_key}"})
        return phantom.APP_SUCCESS

    def _get_token(self, action_result: ActionResult) -> bool:
        """
        This method returns the cached or a new token based
        on the values present in the state file.
        """
        self.token = self._state.get(TOKEN_KEY)

        if self.token:
            self.headers[TOKEN_KEY] = self.token
            return phantom.APP_SUCCESS

        # Use refresh token
        if REFRESH_TOKEN_KEY in self._state and self.refresh_count < 3:
            self.refresh_count += 1
            self.headers[REFRESH_TOKEN_KEY] = self._state[REFRESH_TOKEN_KEY]
            self.headers[TOKEN_KEY] = self._state[TOKEN_KEY]
            ret_val, headers = self._make_rest_call("post", REFRESH_ENDPOINT, action_result, headers_only=True, first_try=False)
            if not phantom.is_fail(ret_val):
                self.token = headers.get(TOKEN_KEY)
                self.headers[TOKEN_KEY] = self.token
                self.headers.pop(REFRESH_TOKEN_KEY)
                self._update_state()
                return phantom.APP_SUCCESS

        # Generate a new token
        self.debug_print("Fetching a new token")
        self.headers.pop(REFRESH_TOKEN_KEY, None)
        auth = HTTPBasicAuth(self.username, self.password)
        ret_val, headers = self._make_rest_call("post", TOKEN_ENDPOINT, action_result, headers_only=True, first_try=True, auth=auth)
        if phantom.is_fail(ret_val):
            self.debug_print(f"Error {ret_val} while generating token with response {headers}")
            self._reset_state_file()
            return action_result.get_status()

        self.token = headers.get(TOKEN_KEY)
        self.refresh_token = headers.get(REFRESH_TOKEN_KEY)
        self.refresh_count = 0

        try:
            self.domains = json.loads(headers.get("DOMAINS"))
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Received unexpected response from the server")

        self.headers.update({"X-auth-access-token": self.token})
        self._update_state()

        return phantom.APP_SUCCESS

    def _process_empty_response(self, response, action_result) -> RetVal:
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"),
            None,
        )

    def _process_html_response(self, response, action_result) -> RetVal:
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

    def _process_json_response(self, r: Response, action_result: ActionResult) -> RetVal:
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Unable to parse JSON response. Error: {e!s}",
                ),
                None,
            )

        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r: Response, action_result: ActionResult) -> RetVal:
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
        msg = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, msg), None)

    def _make_rest_call(
        self,
        method: str,
        endpoint: str,
        action_result: ActionResult,
        json_body: Optional[dict[str, Any]] = None,
        headers_only: bool = False,
        first_try: bool = True,
        params: Optional[dict[str, Any]] = None,
        auth: HTTPBasicAuth = None,
    ) -> tuple[bool, Any]:
        """Function that makes the REST call to the app.
        :param method: REST method
        :param endpoint: REST endpoint to be called
        :param action_result: object of ActionResult class
        :param json_body: JSON object
        :param headers_only: wether to only return response headers
        :param headers: request headers
        :param first_try: if the request is eligible to be retried
        :param params: request parameters
        :param auth: basic auth if passed in. This is only needed with the generatetoken endpoint
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """
        request_method = getattr(requests, method)
        url = f"https://{self.firepower_host}{endpoint}"
        if json_body:
            self.headers.update({"Content-type": "application/json"})

        try:
            result = request_method(
                url, auth=auth, headers=self.headers, json=json_body, verify=self.verify, params=params, timeout=DEFAULT_REQUEST_TIMEOUT
            )
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error connecting to server. {e!s}"), None

        if not (200 <= result.status_code < 399):
            if result.status_code == 401 and first_try:
                self._reset_state_file()
                if not self.is_cloud_deployment():
                    ret_val = self._get_token(action_result)
                    if phantom.is_fail(ret_val):
                        return action_result.get_status(), None

                self.debug_print(f"Re-running endpoint that failed because of token error {endpoint}")
                return self._make_rest_call(method, endpoint, action_result, json_body, headers_only, first_try=False)

            message = "Error from server. Status Code: {} Data from server: {}".format(
                result.status_code, result.text.replace("{", "{{").replace("}", "}}")
            )
            return action_result.set_status(phantom.APP_ERROR, message), None

        if headers_only:
            return phantom.APP_SUCCESS, result.headers

        return self._process_response(result, action_result)

    def is_cloud_deployment(self) -> bool:
        """Helper to determine if user is connecting to cloud based fmc.
        Returns:
            bool: If connection is to cloud basd FMC
        """
        return self.fmc_type == "Cloud"

    def _handle_test_connectivity(self, param: dict[str, Any]) -> bool:
        action_result = ActionResult(dict(param))
        self.add_action_result(action_result)

        self.save_progress("Testing connectivity")

        url = GET_HOSTS_ENDPOINT.format(domain_id="default")
        ret_val, _ = self._make_rest_call("get", url, action_result)
        if phantom.is_fail(ret_val):
            self.save_progress("Connectivity test failed")
            return action_result.get_status()

        self.save_progress("Connectivity test passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def get_network_objects_of_type(self, object_type: str, domain_uuid: str, action_result: ActionResult, name: Optional[str] = None) -> bool:
        """Helper to get network objects of a particular type.
        Args:
            object_type (str): Network object type (Network, Host, Range)
            domain_uuid (str): Domain to be queried
            action_result (ActionResult): object of ActionResult class
            name (str): Name of the object
        Returns:
            bool: If lookup was successfull
        """
        url = NETWORK_OBJECTS_ENDPOINT.format(domain_id=domain_uuid, type=object_type.lower() + "s")

        offset = 0
        limit = 50
        params = {"limit": limit}
        while True:
            params["offset"] = offset
            ret_val, response = self._make_rest_call("get", url, action_result, params=params)
            if phantom.is_fail(ret_val):
                return action_result.get_status()

            try:
                network_obj_list = response.get("items", [])
                for item in network_obj_list:
                    if name and name != item["name"]:
                        continue

                    action_result.add_data(item)

            except Exception as e:
                message = "An error occurred while processing network objects"
                self.debug_print(f"{message}. {e!s}")
                return action_result.set_status(phantom.APP_ERROR, str(e))

            if "paging" in response and "next" in response["paging"]:
                offset += limit
            else:
                break

        return phantom.APP_SUCCESS

    def _handle_list_network_objects(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        domain_uuid = self.get_domain_id(param.get("domain_name"))
        obj_type = param.get("type")
        name = param.get("name")

        if obj_type:
            ret_val = self.get_network_objects_of_type(obj_type, domain_uuid, action_result, name)
            if phantom.is_fail(ret_val):
                return action_result.get_status()

        else:
            for object_type in OBJECT_TYPES:
                ret_val = self.get_network_objects_of_type(object_type, domain_uuid, action_result, name)
                if phantom.is_fail(ret_val):
                    return action_result.get_status()

        action_result.update_summary({"total_objects_returned": len(action_result.get_data())})

        return action_result.set_status(phantom.APP_SUCCESS)

    def get_network_object(self, domain_id: str, object_id: str) -> tuple[bool, dict[str, Any]]:
        """Helper to get a specfic network object.
        Args:
            domain_uuid (str): Domain to be queried
            object_id (str): Id of the object to retrieve
        Returns:
            tuple: If lookup was successfull and response object
        """
        url = NETWORK_OBJECT_ID_ENDPOINT.format(domain_id=domain_id, type="networks", object_id=object_id)
        ret_val, response = self._make_rest_call("get", url, self)
        return ret_val, response

    def _handle_create_network_object(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        name = param["name"]

        object_type = param["type"]
        payload = {"name": name, "type": object_type, "value": param["value"]}
        domain_uuid = self.get_domain_id(param.get("domain_name"))
        url = NETWORK_OBJECTS_ENDPOINT.format(domain_id=domain_uuid, type=object_type.lower() + "s")

        ret_val, response = self._make_rest_call("post", url, action_result, json_body=payload)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully created network object with name {name}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_network_object(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        object_id = param["object_id"]
        domain_uuid = self.get_domain_id(param.get("domain_name"))
        ret_val, curent_object = self.get_network_object(domain_uuid, object_id)
        if phantom.is_fail(ret_val):
            return self.get_status()

        name = param.get("name") or curent_object["name"]
        object_type = param.get("type") or curent_object["type"]
        value = param.get("value") or curent_object["value"]
        payload = {"id": object_id, "name": name, "type": object_type, "value": value}

        url = NETWORK_OBJECT_ID_ENDPOINT.format(domain_id=domain_uuid, type=object_type.lower() + "s", object_id=object_id)

        ret_val, response = self._make_rest_call("put", url, action_result, json_body=payload)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully updated network object with name {name}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_network_object(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        object_id = param["object_id"]
        object_type = param["type"]
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        url = NETWORK_OBJECT_ID_ENDPOINT.format(domain_id=domain_uuid, type=object_type.lower() + "s", object_id=object_id)
        ret_val, response = self._make_rest_call("delete", url, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully delete network object with id {object_id}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def get_domain_id(self, domain_name: str) -> str:
        """Helper to get a domain_name id.
        Args:
            domain_name (str): Name of domain
        Returns:
            str: domain_id
        """
        domain_name = domain_name or self.default_firepower_domain

        # multitenancy on cloud achieved through seperate tenants not domains
        if not domain_name or self.is_cloud_deployment():
            return "default"

        for domain in self.domains:
            leaf_domain = domain["name"].lower().split("/")[-1]
            if domain_name.lower() == leaf_domain:
                return domain["uuid"]

    def list_objects(self, url: str, action_result: ActionResult, expanded: bool = False) -> tuple[bool, list]:
        """Helper to get list any type of FMC objects (groups, policies, rules).
        Args:
            url (str): REST endpoint to query
            action_result (ActionResult): object of ActionResult class
            expanded (bool): Return detailed response of objects
        Returns:
            tuple: If lookup was successfull and list of objects retrieved
        """
        objects = []
        offset = 0
        limit = 50
        params = {"limit": limit, "expanded": str(expanded).lower()}
        while True:
            params["offset"] = offset
            ret_val, response = self._make_rest_call("get", url, action_result, params=params)
            if phantom.is_fail(ret_val):
                return action_result.get_status(), []

            try:
                objects.extend(response.get("items", []))

            except Exception as e:
                message = "An error occurred while processing network groups"
                self.debug_print(f"{message}. {e!s}")
                return action_result.set_status(phantom.APP_ERROR, message), []

            if "paging" in response and "next" in response["paging"]:
                offset += limit
            else:
                break

        return phantom.APP_SUCCESS, objects

    def _handle_get_network_groups(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        group_name = param.get("group_name")
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        url = NETWORK_GROUPS_ENDPOINT.format(domain_id=domain_uuid)
        ret_val, network_group_list = self.list_objects(url, action_result, True)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for item in network_group_list:
            if not group_name:
                action_result.add_data({"name": item["name"], "uuid": item["id"]})
            if group_name == item["name"]:
                action_result.add_data({"name": item["name"], "uuid": item["id"]})
                break

        action_result.update_summary({"total_groups_returned": len(action_result.get_data())})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_network_group(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        group_name = param["name"]
        object_ids = param.get("network_object_ids", "")
        objects = [{"id": item.strip()} for item in object_ids.split(",") if item.strip()]
        overridable = param.get("overridable", False)
        payload = {"name": group_name, "type": "NetworkGroup", "overridable": overridable}
        if objects:
            payload["objects"] = objects
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        url = NETWORK_GROUPS_ENDPOINT.format(domain_id=domain_uuid)

        ret_val, response = self._make_rest_call("post", url, action_result, json_body=payload)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully added network group with name {group_name}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def get_network_group(self, domain_uuid: str, group_id: str) -> tuple[bool, dict[str, Any]]:
        """Helper to get a specfic network group.
        Args:
            domain_uuid (str): Domain to be queried
            group_id (str): Id of the group to retrieve
        Returns:
            tuple: If lookup was successfull and response object
        """
        url = NETWORK_GROUPS_ID_ENDPOINT.format(domain_id=domain_uuid, group_id=group_id)
        ret_val, response = self._make_rest_call("get", url, self)
        return ret_val, response

    def _handle_update_network_group(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        group_id = param["network_group_id"]
        domain_uuid = self.get_domain_id(param.get("domain_name"))
        ret_val, resp = self.get_network_group(domain_uuid, group_id)
        if phantom.is_fail(ret_val):
            return self.get_status()

        if param.get("name"):
            resp["name"] = param["name"]

        current_network_objects = {obj["id"] for obj in resp.get("objects", [])}

        network_objects_to_add = param.get("network_object_ids_to_add", "")
        current_network_objects.update({item.strip() for item in network_objects_to_add.split(",") if item.strip()})

        network_objects_to_remove = param.get("network_object_ids_to_remove", "")
        current_network_objects.difference_update({item.strip() for item in network_objects_to_remove.split(",") if item.strip()})

        objects = [{"id": object_id} for object_id in current_network_objects]
        resp["objects"] = objects

        update_url = NETWORK_GROUPS_ID_ENDPOINT.format(domain_id=domain_uuid, group_id=group_id)
        ret_val, response = self._make_rest_call("put", update_url, action_result, json_body=resp)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully update network group with id {group_id}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_network_group(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        group_id = param["network_group_id"]
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        update_url = NETWORK_GROUPS_ID_ENDPOINT.format(domain_id=domain_uuid, group_id=group_id)
        ret_val, response = self._make_rest_call("delete", update_url, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully deleted network group with id {group_id}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_access_policies(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        policy_id = param.get("policy_id")
        domain_uuid = self.get_domain_id(param.get("domain_name"))
        url = ACCESS_POLICY_ENDPOINT.format(domain_id=domain_uuid)

        if policy_id:
            ret_val, policy_data = self.get_access_policy(domain_uuid, policy_id)
            if phantom.is_fail(ret_val):
                return self.get_status()
            action_result.add_data(policy_data)
            return action_result.set_status(phantom.APP_SUCCESS)

        ret_val, policies = self.list_objects(url, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for policy in policies:
            action_result.add_data({"name": policy["name"], "policy_id": policy["id"]})

        action_result.update_summary({"total_policies_returned": len(action_result.get_data())})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_access_policy(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        name = param["name"]
        payload = {"name": name, "type": "AccessPolicy", "defaultAction": {"action": param["action"].upper()}}
        if param.get("description"):
            payload["description"] = param["description"]

        url = ACCESS_POLICY_ENDPOINT.format(domain_id=domain_uuid)
        ret_val, response = self._make_rest_call("post", url, action_result, json_body=payload)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully created access policy with name {name}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def get_access_policy(self, domain_uuid: str, policy_id: str) -> tuple[bool, dict[str, Any]]:
        """Helper to get a specfic access policy.
        Args:
            domain_uuid (str): Domain to be queried
            policy_id (str): Id of the policy to retrieve
        Returns:
            tuple: If lookup was successfull and response object
        """
        url = ACCESS_POLICY_ID_ENDPOINT.format(domain_id=domain_uuid, policy_id=policy_id)
        ret_val, response = self._make_rest_call("get", url, self)
        return ret_val, response

    def _handle_update_access_policy(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        policy_id = param["policy_id"]
        ret_val, policy_data = self.get_access_policy(domain_uuid, policy_id)
        if phantom.is_fail(ret_val):
            return self.get_status()

        cur_action = policy_data["defaultAction"]
        payload = {
            "id": policy_data["id"],
            "name": param.get("name") or policy_data["name"],
            "type": "AccessPolicy",
            "defaultAction": cur_action,
            "description": policy_data.get("description", ""),
        }

        if param.get("description"):
            payload["description"] = param["description"]

        if param.get("action"):
            payload["defaultAction"]["action"] = param["action"].upper()

        url = ACCESS_POLICY_ID_ENDPOINT.format(domain_id=domain_uuid, policy_id=policy_id)
        ret_val, response = self._make_rest_call("put", url, action_result, json_body=payload)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully updated access policy with id {policy_id}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_access_policy(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        policy_id = param["policy_id"]

        url = ACCESS_POLICY_ID_ENDPOINT.format(domain_id=domain_uuid, policy_id=policy_id)
        ret_val, response = self._make_rest_call("delete", url, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully deleted access policy with id {policy_id}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_access_rules(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        policy_id = param["policy_id"]
        rule_id = param.get("rule_id")

        if rule_id:
            ret_val, response = self.get_access_control_rule(domain_uuid, policy_id, rule_id)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            action_result.add_data(response)
            summary = action_result.update_summary({})
            summary["Message"] = f"Retrieved access rule with id {rule_id}"
            return action_result.set_status(phantom.APP_SUCCESS)

        url = ACCESS_RULES_ENDPOINT.format(domain_id=domain_uuid, policy_id=policy_id)

        ret_val, rules = self.list_objects(url, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for rule in rules:
            action_result.add_data({"name": rule["name"], "rule_id": rule["id"]})

        action_result.update_summary({"total_rules_returned": len(action_result.get_data())})

        return action_result.set_status(phantom.APP_SUCCESS)

    def build_network_objects_list(self, network_ids: list, dommain_uuid: str) -> tuple[bool, Optional[list]]:
        """Helper that classifys and builds a list of network objects and groups.
        Args:
            network_ids (list): Ids of network objects and groups
            domain_uuid (str): Domain to be queried
        Returns:
            tuple: If lookup was successfull and list of network objects and groups
        """
        networks_objects = []
        for object_id in network_ids:
            ret_val, object_data = self.get_network_object(dommain_uuid, object_id)
            if not phantom.is_fail(ret_val):
                networks_objects.append({"type": object_data["type"], "id": object_id})
                continue
            ret_val, _ = self.get_network_group(dommain_uuid, object_id)
            if phantom.is_fail(ret_val):
                return self.get_status(), None
            networks_objects.append({"type": "NetworkGroup", "id": object_id})

        return phantom.APP_SUCCESS, networks_objects

    def _handle_create_access_rules(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        policy_id = param["policy_id"]
        name = param["name"]

        rule_payload = {
            "name": name,
            "action": param["action"],
            "enabled": param.get("enabled", False),
            "sourceNetworks": {"objects": []},
            "destinationNetworks": {"objects": []},
        }

        source_networks = param.get("source_networks", "")
        source_networks = [network.strip() for network in source_networks.split(",") if network.strip()]

        ret_val, source_networks_objects = self.build_network_objects_list(source_networks, domain_uuid)
        if phantom.is_fail(ret_val):
            return ret_val
        rule_payload["sourceNetworks"]["objects"] = source_networks_objects

        destination_networks = param.get("destination_networks", "")
        destination_networks = [network.strip() for network in destination_networks.split(",") if network.strip()]
        ret_val, destination_networks_objects = self.build_network_objects_list(destination_networks, domain_uuid)
        if phantom.is_fail(ret_val):
            return ret_val
        rule_payload["destinationNetworks"]["objects"] = destination_networks_objects

        url = ACCESS_RULES_ENDPOINT.format(domain_id=domain_uuid, policy_id=policy_id)
        ret_val, response = self._make_rest_call("post", url, action_result, json_body=rule_payload)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully added access control rule with name {name} to policy {policy_id}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def get_access_control_rule(self, domain_id: str, policy_id: str, rule_id: str) -> tuple[bool, dict[str, Any]]:
        """Helper to get a specfic access control rule belonging to a specfic access policy.
        Args:
            domain_id (str): Domain to be queried
            policy_id (str): Id of the policy to retrieve
            rule_id (str): Id of the rule to retrieve
        Returns:
            tuple: If lookup was successfull and response object
        """
        url = ACCESS_RULES_ID_ENDPOINT.format(domain_id=domain_id, policy_id=policy_id, rule_id=rule_id)
        ret_val, response = self._make_rest_call("get", url, self)
        return ret_val, response

    def _handle_update_access_rule(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        domain_uuid = self.get_domain_id(param.get("domain_name"))
        rule_id = param["rule_id"]
        policy_id = param["policy_id"]

        ret_val, rule_data = self.get_access_control_rule(domain_uuid, policy_id, rule_id)
        if phantom.is_fail(ret_val):
            return self.get_status()

        rule_payload = {
            "id": rule_data["id"],
            "name": param.get("name") or rule_data["name"],
            "action": param.get("action") or rule_data["action"],
            "type": rule_data["type"],
            "enabled": param.get("enabled") or rule_data["enabled"],
        }

        current_source_networks = rule_data.get("destinationNetworks", {}).get("objects", [])
        source_networks = param.get("source_networks_to_add", "")
        source_networks = [network.strip() for network in source_networks.split(",") if network.strip()]
        ret_val, source_networks_objects = self.build_network_objects_list(source_networks, domain_uuid)
        if phantom.is_fail(ret_val):
            return ret_val
        current_source_networks.extend(source_networks_objects)
        current_source_networks_dic = {network["id"]: network for network in current_source_networks}
        source_networks_to_remove = param.get("source_networks_to_remove", "")
        source_networks_to_remove = [network.strip() for network in source_networks_to_remove.split(",") if network.strip()]

        filtered_source_networks = [value for key, value in current_source_networks_dic.items() if key not in source_networks_to_remove]
        rule_payload["sourceNetworks"] = {"objects": filtered_source_networks}

        current_destination_networks = rule_data.get("destinationNetworks", {}).get("objects", [])
        destination_networks = param.get("destination_networks_to_add", "")
        destination_networks = [network.strip() for network in destination_networks.split(",") if network.strip()]
        ret_val, destination_networks_objects = self.build_network_objects_list(destination_networks, domain_uuid)
        if phantom.is_fail(ret_val):
            return ret_val
        current_destination_networks.extend(destination_networks_objects)
        current_destination_networks_dic = {network["id"]: network for network in current_destination_networks}
        destination_networks_to_remove = param.get("destination_networks_to_remove", "")
        destination_networks_to_remove = [network.strip() for network in destination_networks_to_remove.split(",") if network.strip()]

        filtered_destination_networks = [
            value for key, value in current_destination_networks_dic.items() if key not in destination_networks_to_remove
        ]
        rule_payload["destinationNetworks"] = {"objects": filtered_destination_networks}

        url = ACCESS_RULES_ID_ENDPOINT.format(domain_id=domain_uuid, policy_id=policy_id, rule_id=rule_id)
        ret_val, response = self._make_rest_call("put", url, action_result, json_body=rule_payload)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully updated access control rule with id {rule_id}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_access_rule(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        rule_id = param["rule_id"]
        policy_id = param["policy_id"]

        url = ACCESS_RULES_ID_ENDPOINT.format(domain_id=domain_uuid, policy_id=policy_id, rule_id=rule_id)
        ret_val, response = self._make_rest_call("delete", url, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully delete access control rule with id {rule_id}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_devices(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        url = DEVICES_ENDPOINT.format(domain_id=domain_uuid)

        ret_val, devices = self.list_objects(url, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for device in devices:
            action_result.add_data(device)

        action_result.update_summary({"total_deices_returned": len(action_result.get_data())})

        return action_result.set_status(phantom.APP_SUCCESS)

    def get_deployable_devices(self, domain_id: str, action_result) -> tuple[bool, Any]:
        """Helper that gets list of devices ready for deployment.
        Args:
            domain_id (str): Domain to be queried
            action_result (ActionResult): object of ActionResult class
        Returns:
            tuple: If lookup was successfull and list of devices
        """
        url = GET_DEPLOYABLE_DEVICES_ENDPOINT.format(domain_id=domain_id)
        device_lst = []
        ret_val, deployable_devices = self.list_objects(url, action_result, True)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), device_lst

        for device in deployable_devices:
            device_lst.append({"name": device["device"]["name"], "id": device["device"]["id"], "type": device["device"]["type"]})

        return phantom.APP_SUCCESS, device_lst

    def _handle_get_deployable_devices(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        ret_val, devices = self.get_deployable_devices(domain_uuid, action_result)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, "Unable to get deployable devices")

        for device in devices:
            action_result.add_data(device)

        action_result.update_summary({"total_deployable_deices_returned": len(action_result.get_data())})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_deploy_devices(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        devices_to_deploy = [device.strip() for device in param.get("devices", "").split(",") if device.strip()]
        if not devices_to_deploy:
            ret_val, devices = self.get_deployable_devices(domain_uuid, action_result)
            if phantom.is_fail(ret_val):
                return action_result.set_status(phantom.APP_ERROR, "Unable to get deployable devices")
            for device in devices:
                devices_to_deploy.append(device["id"])

        if not devices_to_deploy:
            summary = action_result.update_summary({})
            summary["Message"] = "No devices to deploy"
            return action_result.set_status(phantom.APP_SUCCESS)

        url = DEPLOY_DEVICES_ENDPOINT.format(domain_id=domain_uuid)
        body = {"type": "DeploymentRequest", "version": "0", "forceDeploy": True, "ignoreWarning": True, "deviceList": devices_to_deploy}

        ret_val, response = self._make_rest_call("post", url, action_result, body)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = "Successfully deployed devices"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_deployment_status(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        deployment_id = param["deployment_id"]

        url = DEPLOYMENT_STATUS_ENDPOINT.format(domain_id=domain_uuid, task_id=deployment_id)
        ret_val, response = self._make_rest_call("get", url, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully retrieved status for deployment {deployment_id}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def get_intrusion_policy(self, domain_uuid: str, policy_id: str) -> tuple[int, any]:
        """Helper to get a specfic intrusion policy.
        Args:
            domain_uuid (str): Domain to be queried
            policy_id (str): Id of the policy to retrieve
        Returns:
            tuple: If lookup was successfull and response object
        """
        url = INTRUSION_POLICY_ID_ENDPOINT.format(domain_id=domain_uuid, policy_id=policy_id)
        ret_val, response = self._make_rest_call("get", url, self)
        return ret_val, response

    def _handle_list_intrusion_policies(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        domain_uuid = self.get_domain_id(param.get("domain_name"))
        policy_id = param.get("policy_id")
        if policy_id:
            ret_val, policy_data = self.get_intrusion_policy(domain_uuid, policy_id)
            if phantom.is_fail(ret_val):
                return ret_val
            action_result.add_data(policy_data)
            return action_result.set_status(phantom.APP_SUCCESS)

        url = INTRUSION_POLICY_ENDPOINT.format(domain_id=domain_uuid)

        ret_val, policies = self.list_objects(url, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for policy in policies:
            action_result.add_data({"name": policy["name"], "policy_id": policy["id"]})

        action_result.update_summary({"total_policies_returned": len(action_result.get_data())})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_intrusion_policy(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        name = param["name"]
        base_policy = param["base_policy"]
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        payload = {"name": name, "basePolicy": {"id": base_policy, "type": "IntrusionPolicy"}, "type": "IntrusionPolicy"}
        description = param.get("description")
        if description:
            payload["description"] = description
        inspection_mode = param.get("inspection_mode")
        if inspection_mode:
            payload["inspectionMode"] = inspection_mode

        url = INTRUSION_POLICY_ENDPOINT.format(domain_id=domain_uuid)
        ret_val, response = self._make_rest_call("post", url, action_result, json_body=payload)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully added intrusion policy with name {name}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_intrusion_policy(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        policy_id = param["policy_id"]
        domain_uuid = self.get_domain_id(param.get("domain_name"))
        ret_val, policy_data = self.get_intrusion_policy(domain_uuid, policy_id)
        if phantom.is_fail(ret_val):
            return ret_val

        payload = {
            "id": policy_id,
            "name": param.get("name") or policy_data["name"],
            "description": param.get("description", "") or policy_data.get("description", ""),
            "inspectionMode": param.get("inspection_mode") or policy_data["inspectionMode"],
            "basePolicy": {"id": param.get("base_policy") or policy_data["basePolicy"]["id"]},
            "replicate_inspection_mode": param.get("replicate_inspection_mode", False),
        }
        url = INTRUSION_POLICY_ID_ENDPOINT.format(domain_id=domain_uuid, policy_id=policy_id)
        ret_val, response = self._make_rest_call("put", url, action_result, json_body=payload)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully updated intrusion policy with id {policy_id}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_intrusion_policy(self, param: dict[str, Any]) -> bool:
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        policy_id = param["policy_id"]
        domain_uuid = self.get_domain_id(param.get("domain_name"))

        url = INTRUSION_POLICY_ID_ENDPOINT.format(domain_id=domain_uuid, policy_id=policy_id)
        ret_val, response = self._make_rest_call("delete", url, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)
        summary = action_result.update_summary({})
        summary["Message"] = f"Successfully delete intrusion policy with id {policy_id}"
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param: dict[str, Any]) -> bool:
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)
        elif action_id == "list_network_objects":
            self._handle_list_network_objects(param)
        elif action_id == "create_network_object":
            self._handle_create_network_object(param)
        elif action_id == "update_network_object":
            self._handle_update_network_object(param)
        elif action_id == "delete_network_object":
            self._handle_delete_network_object(param)
        elif action_id == "get_network_groups":
            ret_val = self._handle_get_network_groups(param)
        elif action_id == "create_network_group":
            ret_val = self._handle_create_network_group(param)
        elif action_id == "update_network_group":
            ret_val = self._handle_update_network_group(param)
        elif action_id == "delete_network_group":
            ret_val = self._handle_delete_network_group(param)
        elif action_id == "get_access_policies":
            ret_val = self._handle_get_access_policies(param)
        elif action_id == "create_access_policy":
            ret_val = self._handle_create_access_policy(param)
        elif action_id == "update_access_policy":
            ret_val = self._handle_update_access_policy(param)
        elif action_id == "delete_access_policy":
            ret_val = self._handle_delete_access_policy(param)
        elif action_id == "get_access_rules":
            ret_val = self._handle_get_access_rules(param)
        elif action_id == "create_access_rules":
            ret_val = self._handle_create_access_rules(param)
        elif action_id == "update_access_rule":
            ret_val = self._handle_update_access_rule(param)
        elif action_id == "delete_access_rule":
            ret_val = self._handle_delete_access_rule(param)
        elif action_id == "list_devices":
            ret_val = self._handle_list_devices(param)
        elif action_id == "get_deployable_devices":
            ret_val = self._handle_get_deployable_devices(param)
        elif action_id == "deploy_devices":
            ret_val = self._handle_deploy_devices(param)
        elif action_id == "get_deployment_status":
            ret_val = self._handle_get_deployment_status(param)
        elif action_id == "list_intrusion_policies":
            ret_val = self._handle_list_intrusion_policies(param)
        elif action_id == "create_intrusion_policy":
            ret_val = self._handle_create_intrusion_policy(param)
        elif action_id == "update_intrusion_policy":
            ret_val = self._handle_update_intrusion_policy(param)
        elif action_id == "delete_intrusion_policy":
            ret_val = self._handle_delete_intrusion_policy(param)

        return ret_val


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    # input a json file that contains data like the configuration and action parameters
    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = FP_Connector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
