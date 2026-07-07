# File: googlesheets_connector.py

# Copyright (c) Splunk, 2024

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

# Python 3 Compatibility imports
from __future__ import print_function, unicode_literals

import json
import re

# Phantom App imports
import phantom.app as phantom
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
from googlesheets_consts import *


class RetVal(tuple):

    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class GoogleSheetsConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(GoogleSheetsConnector, self).__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None
        self._service_email = None
        self._service_creds = None

    def _create_service(self, action_result, service_type, service_version, scope):
        if all(val is not None for val in [service_type, service_version, scope]):
            credentials = service_account.Credentials.from_service_account_info(self._service_creds, scopes=scope)
            try:
                service = build(service_type, service_version, credentials=credentials)
            except Exception:
                msg = SERVICE_CREATION_ERROR.format(service_type, service_version)
                self.save_progress(msg)
                return RetVal(action_result.set_status(phantom.APP_ERROR, msg))

            self.save_progress(SERVICE_SUCCESS.format(service_type))
            return RetVal(phantom.APP_SUCCESS, service)
        else:
            self.save_progress(SERVICE_PARAM_MISSING_ERROR)
            return RetVal(action_result.set_status(phantom.APP_ERROR, SERVICE_PARAM_MISSING_ERROR))

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))
        scope = [IAM_SCOPE]
        self.save_progress("Getting service account details.")
        ret_val, service = self._create_service(action_result, "iam", "v1", scope)

        if phantom.is_fail(ret_val):
            self.save_progress(TEST_CONNECTIVITY_FAILED)
            return action_result.get_status()

        _ = service.projects().serviceAccounts().get(name=PROJECT_NAME_PATH + self._service_email).execute()
        # Return success
        self.save_progress(TEST_CONNECTIVITY_PASSED)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_add_new_rows(self, param):
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))
        sheet_id = param['google_sheet_id']
        try:
            rows = eval(param['rows'])
        except Exception:
            return RetVal(action_result.set_status(phantom.APP_ERROR, INVALID_ROW_DATA))

        range_name = param['sheet_name']
        scope = [SHEETS_SCOPE]
        ret_val, service = self._create_service(action_result, "sheets", "v4", scope)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        _ = service.spreadsheets()
        try:
            response = service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range=range_name,
                body={
                    "majorDimension": "ROWS",
                    "values": rows
                },
                valueInputOption="USER_ENTERED").execute()
        except Exception:
            return RetVal(action_result.set_status(phantom.APP_ERROR, ADD_ROWS_ERROR.format(range_name)))

        msg = ADD_ROWS_SUCCESS.format(response['updates']['updatedRows'])
        self.save_progress(msg)
        action_result.add_data(response)
        return action_result.set_status(phantom.APP_SUCCESS, msg)

    def _validate_email(self, email):
        pat = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        if re.match(pat, email):
            return True
        return False

    def _handle_create_spreadsheet(self, param):
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))
        scope = [SHEETS_SCOPE, DRIVE_AUTH_SCOPE]
        file_name = param['file_name']
        user_emails = param['user_emails'].replace(" ", "").split(",")
        for each in user_emails:
            if not self._validate_email(each):
                msg = INVALID_EMAIL.format(each)
                self.save_progress(msg)
                return RetVal(action_result.set_status(phantom.APP_ERROR, msg))

        ret_val, service = self._create_service(action_result, "sheets", "v4", scope)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        spreadsheet = {
            'properties': {
                'title': file_name
            }
        }
        try:
            spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        except Exception:
            return RetVal(action_result.set_status(phantom.APP_ERROR, SPREADSHEET_CREATE_FAILED.format(file_name)))

        ret_val, service = self._create_service(action_result, "drive", "v3", scope)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for each in user_emails:
            permission_values = {
                'type': param['permission_type'],
                'role': param['role'],
                'emailAddress': each
            }
            service.permissions().create(fileId=spreadsheet.get('spreadsheetId'), body=permission_values).execute()

        action_result.add_data(spreadsheet)
        msg = SPREADSHEET_CREATE_SUCCESS.format(spreadsheet.get('spreadsheetId'))
        return action_result.set_status(phantom.APP_SUCCESS, msg)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == 'add_new_rows':
            ret_val = self._handle_add_new_rows(param)

        if action_id == 'create_spreadsheet':
            ret_val = self._handle_create_spreadsheet(param)

        if action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()
        """
        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """

        self._base_url = config.get('base_url')
        self._service_email = config.get('service_account_email')
        cred_str = config.get('service_account_credentials').replace("'", "\"")
        self._service_creds = json.loads(cred_str)
        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse
    import sys

    argparser = argparse.ArgumentParser()

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)
    argparser.add_argument('-v', '--verify', action='store_true', help='verify', required=False, default=False)

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
            login_url = GoogleSheetsConnector._get_phantom_base_url() + '/login'

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken=' + csrftoken
            headers['Referer'] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = GoogleSheetsConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json['user_session_token'] = session_id
            connector._set_csrf_info(csrftoken, headers['Referer'])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == '__main__':
    main()
