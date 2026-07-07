# File: cylance_connector.py
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
import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timedelta
from zipfile import ZipFile

import jwt
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault as Vault

# Usage of the consts file is recommended
from cylance_consts import *


DEFAULT_REQUEST_TIMEOUT = 30  # in seconds


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class CylanceConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None
        self._access_token = None
        self._region_code = None
        self._tenant_id = None
        self._application_id = None
        self._application_secret = None

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        message = f"Status code: {response.status_code}. Empty response and no information in the header"

        if response.status_code == 404:
            message = "{}. {}".format(message, "Please verify the provided input parameters")
        elif response.status_code == 401:
            message = "{}. {}".format(message, "Unauthorized")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

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

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
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
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _download_file_to_vault(self, action_result, url, file_name):
        """Download a file and add it to the vault"""

        guid = uuid.uuid4()

        if hasattr(Vault, "get_vault_tmp_dir"):
            local_dir = Vault.get_vault_tmp_dir()
        else:
            local_dir = "/opt/phantom/vault/tmp"

        tmp_dir = local_dir + f"/{guid}"
        zip_path = f"{tmp_dir}/{file_name}"

        try:
            os.makedirs(tmp_dir)
        except Exception as e:
            msg = f"Unable to create temporary folder '{tmp_dir}': "
            return action_result.set_status(phantom.APP_ERROR, msg, e)

        try:
            r = requests.get(url, timeout=DEFAULT_REQUEST_TIMEOUT)
        except:
            return action_result.set_status(phantom.APP_ERROR, "Error downloading file")

        with open(zip_path, "wb") as f:
            f.write(r.content)
            f.close()

        zf = ZipFile(zip_path)
        ex_name = zf.namelist()[0]
        vault_path = f"{tmp_dir}/{ex_name}"

        try:
            # All the zip files are encrypted with the password 'infected'
            zf.extractall(tmp_dir, pwd=b"infected")
        except:
            return action_result.set_status(phantom.APP_ERROR, "Error extracting zip file")

        vault_ret = Vault.add_attachment(vault_path, self.get_container_id(), file_name=ex_name)
        if vault_ret.get("succeeded"):
            action_result.set_status(phantom.APP_SUCCESS, "Transferred file")
            summary = {
                phantom.APP_JSON_VAULT_ID: vault_ret[phantom.APP_JSON_HASH],
                phantom.APP_JSON_NAME: ex_name,
                phantom.APP_JSON_SIZE: vault_ret.get(phantom.APP_JSON_SIZE),
            }
            action_result.update_summary(summary)
            action_result.set_status(phantom.APP_SUCCESS, "Successfully added file to vault")
        else:
            action_result.set_status(phantom.APP_ERROR, "Error adding file to vault")

        shutil.rmtree(tmp_dir)

        return action_result.get_status()

    def _get_access_token(self, action_result):
        """
        An auth token is first generated using the tenant's unique id, application's unique id, and application's secret
        A call to the /token endpoint is then made, using the auth token, to generate an access token with a timeout
        The code in _get_access_token() provided by Cylance and modified by Phantom
        """

        config = self.get_config()
        self.save_progress("Creating auth token")

        timeout = 1800  # 30 minutes from now
        now = datetime.utcnow()
        timeout_datetime = now + timedelta(seconds=timeout)
        epoch_time = int((now - datetime(1970, 1, 1)).total_seconds())
        epoch_timeout = int((timeout_datetime - datetime(1970, 1, 1)).total_seconds())
        jti_val = str(uuid.uuid4())

        self._tenant_id = config[CYLANCE_JSON_TENANT_ID]
        self._application_id = config[CYLANCE_JSON_APPLICATION_ID]
        self._application_secret = config[CYLANCE_JSON_APPLICATION_SECRET]

        auth_url = self._base_url + "/auth/v2/token"
        claims = {
            "exp": epoch_timeout,
            "iat": epoch_time,
            "iss": "http://cylance.com",
            "sub": self._application_id,
            "tid": self._tenant_id,
            "jti": jti_val,
        }

        try:
            encoded = jwt.encode(claims, self._application_secret, algorithm="HS256")
        except:
            return action_result.set_status(phantom.APP_ERROR, CYLANCE_AUTH_TOKEN_ERR)

        payload = {"auth_token": encoded}
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        self.save_progress("Creating access token")

        try:
            resp = requests.post(auth_url, headers=headers, json=payload, timeout=DEFAULT_REQUEST_TIMEOUT)
            access_token = json.loads(resp.text)["access_token"]
        except:
            return action_result.set_status(phantom.APP_ERROR, CYLANCE_ACCESS_TOKEN_ERR)

        self._state["_access_token"] = access_token
        self._access_token = access_token
        self.save_state(self._state)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _make_rest_call_helper(self, endpoint, action_result, headers=None, params=None, json=None, data=None, method="get"):
        url = f"{self._base_url}{endpoint}"

        if not self._access_token:
            ret_val = self._get_access_token(action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

        headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {self._access_token}"}

        ret_val, resp_json = self._make_rest_call(url, action_result, headers=headers, params=params, data=data, json=json, method=method)

        # If token is expired, generate a new token
        msg = action_result.get_message()

        if msg and "Unauthorized" in msg:
            ret_val = self._get_access_token(action_result)

            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            headers.update({"Authorization": f"Bearer {self._access_token}"})

            ret_val, resp_json = self._make_rest_call(url, action_result, headers=headers, params=params, data=data, json=json, method=method)

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, resp_json

    def _make_rest_call(self, url, action_result, headers=None, params=None, json=None, data=None, method="get"):
        resp_json = None

        try:
            kwargs = {
                "json": json,
                "data": data,
                "headers": headers,
                "params": params,
            }
            r = requests.request(method, url, **kwargs)
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {e!s}"), resp_json)

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to the server")

        ret_val = self._get_access_token(action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()
        # make rest call
        ret_val, response = self._make_rest_call_helper("/users/v2", action_result, params=None, headers=None)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _paginator(self, endpoint, action_result, params=None, limit=None):
        items_list = list()

        page = 0

        if limit == 0 or (limit and (not str(limit).isdigit() or limit <= 0)):
            action_result.set_status(phantom.APP_ERROR, CYLANCE_ERR_INVALID_PARAM.format(param="limit"))
            return None

        while True:
            if not params:
                params = dict()
            page = page + 1
            params["page"] = page
            params["page_size"] = DEFAULT_MAX_RESULTS

            ret_val, response = self._make_rest_call_helper(endpoint, action_result, params=params, headers=None)

            if phantom.is_fail(ret_val):
                return None

            items_list.extend(response.get("page_items"))

            if limit and len(items_list) >= limit:
                return items_list[:limit]

            if len(response.get("page_items")) < DEFAULT_MAX_RESULTS:
                break

        return items_list

    def _handle_list_endpoints(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        # Optional values should use the .get() function
        limit = param.get("limit")

        url = "/devices/v2"

        # make rest call
        endpoints = self._paginator(url, action_result, limit=limit)

        if endpoints is None:
            return action_result.get_status()

        for endpoint in endpoints:
            action_result.add_data(endpoint)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_endpoints"] = len(endpoints)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_threats(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        unique_device_id = param["unique_device_id"]
        limit = param.get("limit")

        url = f"/devices/v2/{unique_device_id}/threats"

        # make rest call
        threats = self._paginator(url, action_result, limit=limit)

        if threats is None:
            return action_result.get_status()

        for threat in threats:
            action_result.add_data(threat)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_threats"] = len(threats)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_system_info(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        # Required values can be accessed directly
        unique_device_id = param["unique_device_id"]

        # make rest call
        ret_val, response = self._make_rest_call_helper(f"/devices/v2/{unique_device_id}", action_result, params=None, headers=None)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["is_safe"] = response["is_safe"]

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_hunt_file(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        sha256_hash = param["hash"]
        limit = param.get("limit")

        url = f"/threats/v2/{sha256_hash}/devices"

        # make rest call
        items = self._paginator(url, action_result, limit=limit)

        if items is None:
            return action_result.get_status()

        for item in items:
            action_result.add_data(item)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_items"] = len(items)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_global_list(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        list_type_id = param.get("list_type_id")
        limit = param.get("limit")

        params = dict()

        if list_type_id == "GlobalQuarantine":
            params["listTypeId"] = 0
        elif list_type_id == "GlobalSafe":
            params["listTypeId"] = 1

        url = "/globallists/v2"

        # make rest call
        items = self._paginator(url, action_result, params=params, limit=limit)

        if items is None:
            return action_result.get_status()

        for item in items:
            action_result.add_data(item)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_items"] = len(items)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_unblock_hash(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        sha256_hash = param["hash"]
        list_type = param["list_type"]

        request = {"sha256": sha256_hash, "list_type": list_type}

        # make rest call
        ret_val, response = self._make_rest_call_helper("/globallists/v2", action_result, params=None, json=request, method="delete")

        if phantom.is_fail(ret_val):
            message = action_result.get_message()
            if "There's no entry for this threat" in message:
                return action_result.set_status(phantom.APP_SUCCESS, CYLANCE_UNBLOCK_HASH_ALREADY_UNBLOCKED_SUCC)
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, CYLANCE_UNBLOCK_HASH_SUCC)

    def _handle_block_hash(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        sha256_hash = param["hash"]
        reason = param["reason"]
        list_type = param["list_type"]
        category = param.get("category", "None")

        request = {"sha256": sha256_hash, "list_type": list_type, "category": category, "reason": reason}

        # make rest call
        ret_val, response = self._make_rest_call_helper("/globallists/v2", action_result, json=request, method="post")

        if phantom.is_fail(ret_val):
            message = action_result.get_message()
            if "There's already an entry for this threat" in message:
                return action_result.set_status(phantom.APP_SUCCESS, CYLANCE_BLOCK_HASH_ALREADY_BLOCKED_SUCC)
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, CYLANCE_BLOCK_HASH_SUCC)

    def _handle_get_file(self, param):
        """Get a file and download it to the vault. Cylance will give the URL"""

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        sha256_hash = param["hash"]

        # make rest call
        ret_val, response = self._make_rest_call_helper(f"/threats/v2/download/{sha256_hash}", action_result, headers=None)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        url = response["url"]
        file_name = f"{sha256_hash}.zip"

        ret_val = self._download_file_to_vault(action_result, url, file_name)

        if phantom.is_fail(ret_val):
            msg = action_result.get_message()
            action_result.set_status(phantom.APP_ERROR, f"Failed to add file to vault: {msg}")
            return self.set_status(phantom.APP_ERROR)

        return self.set_status(phantom.APP_SUCCESS, "Successfully added file to vault")

    def _handle_get_file_info(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Required values can be accessed directly
        sha256_hash = param["hash"]

        # make rest call
        ret_val, response = self._make_rest_call_helper(f"/threats/v2/{sha256_hash}", action_result, params=None, headers=None)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["classification"] = response["classification"]

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_zones(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Optional values should use the .get() function
        limit = param.get("limit")

        url = "/zones/v2"

        # make rest call
        items = self._paginator(url, action_result, limit=limit)

        if items is None:
            return action_result.get_status()

        for item in items:
            action_result.add_data(item)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_zones"] = len(items)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_zone(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Required values can be accessed directly
        unique_zone_id = param["unique_zone_id"]
        name = param["name"]
        policy_id = param["policy_id"]
        criticality = param["criticality"]

        request = {"name": name, "policy_id": policy_id, "criticality": criticality}

        # make rest call
        ret_val, response = self._make_rest_call_helper(f"/zones/v2/{unique_zone_id}", action_result, json=request, method="put")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, CYLANCE_UPDATE_ZONE_SUCC)

    def _handle_get_policies(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Optional values should use the .get() function
        limit = param.get("limit")

        url = "/policies/v2"

        # make rest call
        items = self._paginator(url, action_result, limit=limit)

        if items is None:
            return action_result.get_status()

        for item in items:
            action_result.add_data(item)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["num_policies"] = len(items)

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "list_endpoints":
            ret_val = self._handle_list_endpoints(param)

        elif action_id == "get_threats":
            ret_val = self._handle_get_threats(param)

        elif action_id == "get_system_info":
            ret_val = self._handle_get_system_info(param)

        elif action_id == "hunt_file":
            ret_val = self._handle_hunt_file(param)

        elif action_id == "get_global_list":
            ret_val = self._handle_get_global_list(param)

        elif action_id == "unblock_hash":
            ret_val = self._handle_unblock_hash(param)

        elif action_id == "block_hash":
            ret_val = self._handle_block_hash(param)

        elif action_id == "get_file":
            ret_val = self._handle_get_file(param)

        elif action_id == "get_file_info":
            ret_val = self._handle_get_file_info(param)

        elif action_id == "get_zones":
            ret_val = self._handle_get_zones(param)

        elif action_id == "update_zone":
            ret_val = self._handle_update_zone(param)

        elif action_id == "get_policies":
            ret_val = self._handle_get_policies(param)

        return ret_val

    def initialize(self):
        self._state = self.load_state()
        config = self.get_config()
        self._region_code = config[CYLANCE_JSON_REGION_CODE]

        region_code_formatted = CYLANCE_REGION_CODES.get(self._region_code)

        self._base_url = f"https://protectapi{region_code_formatted}.cylance.com"
        self._access_token = self._state.get("_access_token", "")

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved accross actions and app upgrades
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
            print("Accessing the Login page")
            r = requests.get(BaseConnector._get_phantom_base_url() + "login", verify=verify, timeout=DEFAULT_REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = BaseConnector._get_phantom_base_url() + "login"

            print("Logging into Platform to get the session id")
            r2 = requests.post(
                BaseConnector._get_phantom_base_url() + "login", verify=verify, data=data, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT
            )
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platfrom. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = CylanceConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
