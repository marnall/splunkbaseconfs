# File: qrcode_connector.py
#
# Copyright (c) Splunk, 2023
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

# Python 3 Compatibility imports
from __future__ import print_function, unicode_literals

import json

import cv2
# Phantom App imports
import phantom.app as phantom
import phantom.rules as prules
import requests
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
# from qrcode_consts import *


class RetVal(tuple):

    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class QrCodeConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(QrCodeConnector, self).__init__()

        self._state = None

    def _handle_test_connectivity(self, param):
        self.debug_print('Test connectivity starts...')

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Return success
        # self.save_progress("Test Connectivity Passed")
        # return action_result.set_status(phantom.APP_SUCCESS)

        self.debug_print('Test connectivity finished.')
        # For now return Error with a message, in case of success we don't set the message, but use the summary
        return action_result.set_status(phantom.APP_ERROR, 'Action Not Implemented')

    def _handle_decode_qr_code(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress('In action handler for: {0}'.format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Required values can be accessed directly
        vault_id = param['vault_id']

        success, _, vault_info = prules.vault_info(vault_id=vault_id)
        if not success:
            self._error('Unable to find vault info')
            return action_result.set_status(
                phantom.APP_ERROR, 'Invalid Vault ID'
            )

        file_info = vault_info[0]
        file_path = file_info['path']

        try:
            # read the QRCODE image
            image = cv2.imread(file_path)
            # initialize the cv2 QRCode detector
            detector = cv2.QRCodeDetector()
            # detect and decode
            data, vertices_array, binary_qrcode = detector.detectAndDecode(image)
            # if there is a QR code
            # print the data
            if vertices_array is not None:
                action_result.add_data({'output': data})
            else:
                self.debug_print('Error reading QR code')
        except:
            return self.set_status(phantom.APP_ERROR, 'Unable to read file')
        # Add a dictionary that is made up of the most important values from data into the summary

        self.debug_print('Action decode qr code finished.')
        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print('action_id', self.get_action_identifier())

        if action_id == 'decode_qr_code':
            ret_val = self._handle_decode_qr_code(param)

        if action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        """
        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """
        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

    argparser = argparse.ArgumentParser()

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if username is not None and password is None:

        # User specified a username but not a password, so ask
        import getpass
        password = getpass.getpass('Password: ')

    if username and password:
        try:
            login_url = QrCodeConnector._get_phantom_base_url() + '/login'

            print('Accessing the Login page')
            r = requests.get(login_url, verify=False)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken=' + csrftoken
            headers['Referer'] = login_url

            print('Logging into Platform to get the session id')
            r2 = requests.post(login_url, verify=False, data=data, headers=headers)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print('Unable to get session id from the platform. Error: ' + str(e))
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = QrCodeConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json['user_session_token'] = session_id
            connector._set_csrf_info(csrftoken, headers['Referer'])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)


if __name__ == '__main__':
    main()
