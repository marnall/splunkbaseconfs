# File: tenableio_connector.py
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


import json
from datetime import datetime, timezone

import backoff
import phantom.app as phantom
import requests
from dateutil.parser import ParserError, parse as dateutil_parse
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from restfly import errors
from tenable.io import TenableIO

from tenableio_consts import *


class TenableioConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

    @staticmethod
    def _parse_datetime(value):
        if value.isdigit():
            return datetime.fromtimestamp(int(value), timezone.utc)

        return dateutil_parse(value)

    @staticmethod
    def _validate_scan_timeout(action_result, value):
        try:
            if value >= TENABLE_IO_MIN_PARAM_SCAN_TIMEOUT and value <= TENABLE_IO_MAX_PARAM_SCAN_TIMEOUT:
                return phantom.APP_SUCCESS
        except:
            pass

        return action_result.set_status(
            phantom.APP_ERROR,
            TENABLE_IO_MESSAGE_INVALID_VALUE,
            None,
            TENABLE_IO_PARAM_SCAN_TIMEOUT,
            TENABLE_IO_MIN_PARAM_SCAN_TIMEOUT,
            TENABLE_IO_MAX_PARAM_SCAN_TIMEOUT,
        )

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            self.save_progress(TENABLE_IO_MESSAGE_CONNECTING_TO_ENDPOINT)
            self._client.scans.list(None, datetime.now())
        except Exception as ex:
            self.save_progress(str(ex))
            return action_result.set_status(phantom.APP_ERROR, TENABLE_IO_MESSAGE_TEST_CONNECTIVITY_FAILED)

        self.save_progress(TENABLE_IO_MESSAGE_TEST_CONNECTIVITY_PASSED)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_policies(self, param):
        self.debug_print("Start _handle_list_policies")
        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            policies = self._client.policies.list()

            for curr_item in policies:
                action_result.add_data(curr_item)

            summary = action_result.update_summary({})
            summary[TENABLE_IO_OUTPUT_POLICY_COUNT] = len(policies)

            self.debug_print("End _handle_list_policies")
            return action_result.set_status(phantom.APP_SUCCESS)
        except:
            return action_result.set_status(phantom.APP_ERROR, TENABLE_IO_MESSAGE_LIST_POLICIES_FAILED)

    def _handle_list_scans(self, param):
        self.debug_print("Start _handle_list_scans")
        action_result = self.add_action_result(ActionResult(dict(param)))

        folder_id = param.get(TENABLE_IO_PARAM_FOLDER_ID)
        last_modified = param.get(TENABLE_IO_PARAM_LAST_MODIFIED)

        try:
            if last_modified:
                last_modified = self._parse_datetime(last_modified)

            scans = self._client.scans.list(folder_id, last_modified)

            for curr_item in scans:
                action_result.add_data(curr_item)

            summary = action_result.update_summary({})
            summary[TENABLE_IO_OUTPUT_SCAN_COUNT] = len(scans)

            self.debug_print("End _handle_list_scans")
            return action_result.set_status(phantom.APP_SUCCESS)
        except (OverflowError, ParserError):
            return action_result.set_status(phantom.APP_ERROR, TENABLE_IO_MESSAGE_INVALID_DATETIME)
        except:
            return action_result.set_status(phantom.APP_ERROR, TENABLE_IO_MESSAGE_LIST_SCANS_FAILED)

    def _handle_list_scanners(self, param):
        self.debug_print("Start _handle_list_scanners")
        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            scanners = self._client.scanners.allowed_scanners()

            for curr_item in scanners:
                action_result.add_data(curr_item)

            summary = action_result.update_summary({})
            summary[TENABLE_IO_OUTPUT_SCANNER_COUNT] = len(scanners)

            self.debug_print("End _handle_list_scanners")
            return action_result.set_status(phantom.APP_SUCCESS)
        except:
            return action_result.set_status(phantom.APP_ERROR, TENABLE_IO_MESSAGE_LIST_SCANNERS_FAILED)

    def _handle_delete_scan(self, param):
        self.debug_print("Start _handle_delete_scan")
        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            scan_id = param[TENABLE_IO_PARAM_SCAN_ID]
            self._client.scans.delete(scan_id)

            action_result.add_data({TENABLE_IO_OUTPUT_SCAN_ID: scan_id, TENABLE_IO_OUTPUT_DELETE_STATUS: True})
            summary = action_result.update_summary({})
            summary[TENABLE_IO_OUTPUT_DELETE_STATUS] = True

            self.debug_print("End _handle_delete_scan")
            return action_result.set_status(phantom.APP_SUCCESS, TENABLE_IO_MESSAGE_DELETE_SCAN_COMPLETED)
        except:
            return action_result.set_status(phantom.APP_ERROR, TENABLE_IO_MESSAGE_DELETE_SCAN_FAILED)

    def _handle_scan_host(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            # Create scan
            scan_name = param.get(TENABLE_IO_PARAM_SCAN_NAME, TENABLE_IO_DEFAULT_SCAN_NAME)
            scan_timeout = param.get(TENABLE_IO_PARAM_SCAN_TIMEOUT, TENABLE_IO_DEFAULT_SCAN_RUNNING_TIMEOUT)
            scanner_id = param.get(TENABLE_IO_PARAM_SCANNER_ID)
            target_to_scan = param[TENABLE_IO_PARAM_TARGET_TO_SCAN]
            policy_id = param[TENABLE_IO_PARAM_POLICY_ID]
            if policy_id.isdigit():
                policy_id = int(policy_id)

            ret_val = self._validate_scan_timeout(action_result, scan_timeout)
            if phantom.is_fail(ret_val):
                return action_result.get_status()

            self.save_progress(TENABLE_IO_MESSAGE_CREATING_SCAN, target_to_scan)
            scan = self._client.scans.create(name=scan_name, policy=policy_id, targets=[target_to_scan], scanner=scanner_id)

            summary = action_result.update_summary({})
            summary[TENABLE_IO_OUTPUT_SCAN_ID] = scan["id"]

            # Launch scan
            self.save_progress(TENABLE_IO_MESSAGE_LAUNCHING_SCAN, target_to_scan, scan["id"])
            scan_instance_uuid = self._client.scans.launch(scan["id"])

            # Poll until scan status indicates complete or timeout
            @backoff.on_exception(backoff.expo, errors.TooManyRequestsError, max_time=TENABLE_IO_DEFAULT_SCAN_STATUS_RATE_LIMITING_TIMEOUT)
            @backoff.on_predicate(
                backoff.constant,
                lambda status: status not in TENABLE_IO_TERMINAL_SCAN_STATUS,
                interval=TENABLE_IO_DEFAULT_SCAN_STATUS_POLLING_INTERVAL,
                max_time=scan_timeout,
            )
            def get_scan_status(scan_id):
                status = self._client.scans.status(scan_id)
                self.save_progress(TENABLE_IO_MESSAGE_WAITING_FOR_SCAN, status)
                return status

            scan_status = get_scan_status(scan["id"])
            error_messages = []
            if scan_status == TENABLE_IO_SCAN_STATUS_COMPLETE:
                self.save_progress(TENABLE_IO_MESSAGE_SCAN_COMPLETED)
            else:
                error_messages.append(TENABLE_IO_MESSAGE_SCAN_DID_NOT_COMPLETE.format(scan_timeout, scan_status))

            # Get scan details
            self.save_progress(TENABLE_IO_MESSAGE_GETTING_SCAN_DETAILS, scan["id"], scan_instance_uuid)
            scan_details = self._client.scans.results(scan["id"], None, scan_instance_uuid)
            hosts = scan_details.get("hosts", [])

            # Generate output
            if hosts:
                for host in hosts:
                    action_result.add_data(host)

                last_host = hosts[-1]
                summary[TENABLE_IO_OUTPUT_TOTAL_VULNS] = sum([last_host[sev] for sev in TENABLE_IO_VULNERABILITY_SEVERITIES_FOR_SUMMARY])
            else:
                error_messages.append(TENABLE_IO_MESSAGE_SCAN_RESPONSE_IS_EMPTY)

            if error_messages:
                return action_result.set_status(phantom.APP_ERROR, " ".join(error_messages))

            return action_result.set_status(phantom.APP_SUCCESS)

        except Exception as e:
            message = " ".join([TENABLE_IO_MESSAGE_SCAN_ENDPOINT_FAILED, str(e)])[:TENABLE_IO_MAX_ERROR_MESSAGE_LENGTH]
            return action_result.set_status(phantom.APP_ERROR, message)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == TENABLE_IO_ACTION_ID_TEST_CONNECTIVITY:
            ret_val = self._handle_test_connectivity(param)
        elif action_id == TENABLE_IO_ACTION_ID_LIST_SCANS:
            ret_val = self._handle_list_scans(param)
        elif action_id == TENABLE_IO_ACTION_ID_LIST_SCANNERS:
            ret_val = self._handle_list_scanners(param)
        elif action_id == TENABLE_IO_ACTION_ID_LIST_POLICIES:
            ret_val = self._handle_list_policies(param)
        elif action_id == TENABLE_IO_ACTION_ID_SCAN_HOST:
            # Note: "action": "scan endpoint" -> "identifier": "scan_host" is a carry-over from original nessus app
            ret_val = self._handle_scan_host(param)
        elif action_id == TENABLE_IO_ACTION_ID_DELETE_SCAN:
            ret_val = self._handle_delete_scan(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        config = self.get_config()
        self._access_key = config[TENABLE_IO_CONFIG_ACCESS_KEY]
        self._secret_key = config[TENABLE_IO_CONFIG_SECRET_KEY]

        if not (self._access_key and self._secret_key):
            return self.set_status(phantom.APP_ERROR, TENABLE_IO_MESSAGE_BAD_ASSET_CONFIG)

        return self._create_client()

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _create_client(self):
        try:
            self.debug_print(TENABLE_IO_MESSAGE_CREATING_CLIENT)
            self._client = TenableIO(self._access_key, self._secret_key)
        except Exception as e:
            return self.set_status(phantom.APP_ERROR, TENABLE_IO_MESSAGE_FAILED_TO_CREATE_CLIENT, e)

        return phantom.APP_SUCCESS


def main():
    import argparse
    import sys

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
            login_url = TenableioConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=TENABLE_IO_DEFAULT_REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=TENABLE_IO_DEFAULT_REQUEST_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = TenableioConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
