# File: ciscoumbrella_connector.py
#
# Copyright (c) 2021-2025 Splunk Inc.
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
import time
from datetime import datetime

import phantom.app as phantom
import requests
import simplejson as json
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from ciscoumbrella_consts import *


class CiscoumbrellaConnector(BaseConnector):
    # actions supported by this script
    ACTION_ID_LIST_BLOCKED_DOMAINS = "list_blocked_domains"
    ACTION_ID_BLOCK_DOMAIN = "block_domain"
    ACTION_ID_UNBLOCK_DOMAIN = "unblock_domain"

    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, CISCOUMB_VALID_INT_MSG.format(param=key)), None

                parameter = int(parameter)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, CISCOUMB_VALID_INT_MSG.format(param=key)), None

            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, CISCOUMB_NON_NEG_INT_MSG.format(param=key)), None
            if not allow_zero and parameter == 0:
                return action_result.set_status(phantom.APP_ERROR, CISCOUMB_NON_NEG_NON_ZERO_INT_MSG.format(param=key)), None

        return phantom.APP_SUCCESS, parameter

    def initialize(self):
        # Base URL
        self._base_url = CISCOUMB_REST_API_URL
        if self._base_url.endswith("/"):
            self._base_url = self._base_url[:-1]

        self._host = self._base_url[self._base_url.find("//") + 2 :]

        self._base_url = f"{self._base_url}/{CISCOUMB_REST_API_VER}"

        config = self.get_config()
        self._key = config[CISCOUMB_JSON_CUSTKEY]

        self._number_of_retries = config.get("retry_count", CISCOUMB_DEFAULT_NUMBER_OF_RETRIES)
        ret_val, self._number_of_retries = self._validate_integer(
            self, self._number_of_retries, "'Maximum attempts to retry the API call' asset configuration"
        )
        if phantom.is_fail(ret_val):
            return self.get_status()

        self._retry_wait_time = config.get("retry_wait_time", CISCOUMB_DEFAULT_RETRY_WAIT_TIME)
        ret_val, self._retry_wait_time = self._validate_integer(
            self, self._retry_wait_time, "'Delay in seconds between retries' asset configuration"
        )
        if phantom.is_fail(ret_val):
            return self.get_status()

        return phantom.APP_SUCCESS

    def _get_error_message(self, resp_json, response):
        ret_val = ""

        if not resp_json:
            return ret_val

        ret_val = resp_json.get("message", "")

        if response.status_code == 500:
            ret_val += ". The service may be down or your license may have expired."

        return ret_val

    def _paginator(self, endpoint, action_result, params=None, limit=0):
        if not isinstance(params, dict):
            params = dict()

        data = list()
        params["limit"] = CISCOUMB_DEFAULT_DOMAIN_LIMIT
        page = 1
        while True:
            params["page"] = page

            status, response = self._make_rest_call(endpoint, action_result, request_params=params)
            if phantom.is_fail(status):
                return action_result.get_status(), data

            data.extend(response.get("data", []))

            if limit and len(data) >= limit:
                return phantom.APP_SUCCESS, data[:limit]

            if not response.get("meta", {}).get("next"):
                break

            page += 1

        return phantom.APP_SUCCESS, data

    def _make_rest_call(self, endpoint, action_result, request_params=None, method="get", data=None):
        if request_params is None:
            request_params = {}

        request_params.update({"customerKey": self._key})

        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        resp_json = None

        # get or post or delete, whatever the caller asked us to use, if not specified the default will be 'get'
        request_func = getattr(requests, method)

        # handle the error in case the caller specified a non-existent method
        if not request_func:
            return action_result.set_status(phantom.APP_ERROR, f"Unsupported method {method}"), resp_json

        if data:
            data = json.dumps(data)

        for retry in range(self._number_of_retries + 1):
            # Make the call
            try:
                r = request_func(
                    f"{self._base_url}{endpoint}",
                    headers=headers,
                    params=request_params,
                    verify=True,
                    data=data,
                    timeout=CISCOUMB_DEFAULT_TIMEOUT,
                )
            except Exception as e:
                self.error_print(CISCOUMB_ERR_SERVER_CONNECTION, e)
                return action_result.set_status(phantom.APP_ERROR, CISCOUMB_ERR_SERVER_CONNECTION, e), resp_json

            # Retry wait mechanism for the rate limit exceeded error
            if r.status_code != 429:
                break
            self.debug_print("Received 429 status code from the server")
            if retry != self._number_of_retries:
                self.debug_print(f"Retrying after {self._retry_wait_time} second(s)...")
                time.sleep(self._retry_wait_time)

        if r.status_code == 204:  # success, return from here, requests treats 204 as !ok
            return phantom.APP_SUCCESS, resp_json

        try:
            resp_json = r.json()
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Response is not a valid json"), resp_json

        if r.status_code == 202:  # success, return from here, requests treats 202 as !ok
            return phantom.APP_SUCCESS, resp_json

        if r.status_code != requests.codes.ok:  # pylint: disable=E1101
            return action_result.set_status(
                phantom.APP_ERROR, CISCOUMB_ERR_FROM_SERVER, status=r.status_code, message=self._get_error_message(resp_json, r)
            ), resp_json

        return phantom.APP_SUCCESS, resp_json

    def _test_connectivity(self, param):
        # Progress
        self.save_progress(CISCOUMB_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        endpoint = "/domains"

        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress(CISCOUMB_MSG_GET_DOMAIN_LIST_TEST)

        ret_val, _ = self._make_rest_call(endpoint, action_result, {"page": 1, "limit": 1})

        if phantom.is_fail(ret_val):
            self.save_progress(CISCOUMB_ERR_CONNECTIVITY_TEST)
            return action_result.get_status()

        self.save_progress(CISCOUMB_SUCC_CONNECTIVITY_TEST)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _list_blocked_domains(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Progress
        self.save_progress(CISCOUMB_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        endpoint = "/domains"

        domain_limit = param.get(CISCOUMB_JSON_DOMAIN_LIMIT)
        ret_val, domain_limit = self._validate_integer(action_result, domain_limit, "'limit'")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, domain_list = self._paginator(endpoint, action_result, limit=domain_limit)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.update_summary({CISCOUMB_JSON_TOTAL_DOMAINS: len(domain_list)})

        for domain in domain_list:
            action_result.add_data(domain)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _unblock_domain(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Progress
        self.save_progress(CISCOUMB_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        endpoint = "/domains"

        domain = param[CISCOUMB_JSON_DOMAIN]

        request_params = {"where[name]": domain}

        ret_val, response = self._make_rest_call(endpoint, action_result, request_params, method="delete")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, "Domain successfully unblocked")

    def _block_domain(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Progress
        self.save_progress(CISCOUMB_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        ret_val, container_info, _ = self.get_container_info()

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, "Unable to get container information")

        endpoint = "/events"

        events = []

        domain = param[CISCOUMB_JSON_DOMAIN]

        event = {
            "deviceId": self.get_product_installation_id(),
            "deviceVersion": self.get_product_version(),
            "eventTime": datetime.strptime(container_info["create_time"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%dT%H:%M:%S.0Z"),
            "alertTime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.0Z"),
            "dstDomain": domain,
            "dstUrl": f"http://{domain}/",
            "protocolVersion": "1.0a",
            "providerName": "Security Platform",
            "disableDstSafeguards": param.get(CISCOUMB_JSON_DISABLE_SAFEGUARDS, False),
            "eventType": container_info["label"],
            "eventSeverity": container_info["severity"],
        }

        events.append(event)

        ret_val, response = self._make_rest_call(endpoint, action_result, method="post", data=events)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, CISCOUMB_LIST_UPDATED_WITH_GUID.format(id=response["id"]))

    def handle_action(self, param):
        """Function that handles all the actions"""

        # Get the action that we are supposed to carry out, set it in the connection result object
        action = self.get_action_identifier()

        ret_val = phantom.APP_SUCCESS

        if action == self.ACTION_ID_LIST_BLOCKED_DOMAINS:
            ret_val = self._list_blocked_domains(param)
        elif action == self.ACTION_ID_BLOCK_DOMAIN:
            ret_val = self._block_domain(param)
        elif action == self.ACTION_ID_UNBLOCK_DOMAIN:
            ret_val = self._unblock_domain(param)
        elif action == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity(param)

        return ret_val


if __name__ == "__main__":
    import argparse
    import sys

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
            login_url = BaseConnector._get_phantom_base_url() + "login"
            r = requests.get(login_url, verify=verify, timeout=CISCOUMB_DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = BaseConnector._get_phantom_base_url() + "login"

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=CISCOUMB_DEFAULT_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = CiscoumbrellaConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
