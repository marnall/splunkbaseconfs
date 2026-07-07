# File: forcepoint_connector.py
#
# Copyright Martin Ohl 2021-2023
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

import phantom.app as phantom
# Usage of the consts file is recommended
# from forcepoint_consts import *
import requests
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector


class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class ForcepointConnector(BaseConnector):

    def __init__(self):

        super(ForcepointConnector, self).__init__()

        self._state = None
        self._base_url = None

    def _make_rest_call(self, action_result):

        self.save_progress('Creating Forcepoint API session...')
        config = self.get_config()
        self._force_url = config.get('base_url')
        self._force_port = config.get('base_port')
        self._force_version = config.get('base_version')
        self._force_auth_key = config.get('auth_key')
        self._verify = config.get(phantom.APP_JSON_VERIFY, False)

        self.url = 'http://' + self._force_url + ':' + self._force_port + '/' + self._force_version

        session = requests.session()

        self.h = {'accept': 'application/json', 'content-type': 'application/json'}
        login_params = {"authenticationkey": self._force_auth_key}

        try:
            r = session.post(
                self.url + '/login',
                data=json.dumps(login_params),
                headers=self.h,
                verify=self._verify)
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, u"Error Connecting to server. Details: {0}".format(str(e))), None)

        return RetVal(action_result.set_status(phantom.APP_SUCCESS, r))

    def _logout(self, action_result, session):

        r = session.put(
            self.url + '/logout')

        r.raise_for_status()

        return RetVal(phantom.APP_SUCCESS, r)

    def _handle_test_connectivity(self, param):

        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to the Forcepoint SMC")
        ret_val, session = self._make_rest_call(action_result)

        if (phantom.is_fail(ret_val)):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        self._logout(action_result, session)

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_block_ip(self, param):

        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        self.save_progress("Connecting to the Forcepoint SMC")
        ret_val, session = self._make_rest_call(action_result)

        if (phantom.is_fail(ret_val)):
            self.save_progress("Error creating SMC Session!")
            return action_result.get_status()

        try:
           group = param['group']
           new_list = {"name": group, "comment": "BadIPList from Phantom"}
           new_list_content = {"ip": [param['ip']]}

           r = session.get(self.url + "/elements/ip_list", data=json.dumps(new_list), headers=self.h)
           r.raise_for_status()
           ip_lists = r.json()["result"]
           for entry in ip_lists:
              if entry["name"] == new_list["name"]:
                 elem_url = entry["href"]
                 break
           else:
              r = session.post(self.url + "/elements/ip_list", data=json.dumps(new_list), headers=self.h)
              r.raise_for_status()
              elem_url = r.headers["location"]

           r = session.get(elem_url, headers=self.h)
           r.raise_for_status()
           elem_content_url = [entry["href"]
                              for entry in r.json()["link"]
                              if entry["rel"] == "ip_address_list"][0]

           r = session.get(elem_content_url, headers=self.h)
           r.raise_for_status()
           list_content = r.json()
           a = json.dumps(list_content)
           check = json.loads(a)
           new_list_content = json.loads(a)
           new_list_content['ip'].append(param['ip'])

           for ip in check['ip']:
              if ip == param['ip']:
                 print("This IP is already in the SMC IP-List")
                 self._logout(action_result, session)
                 r.raise_for_status()
                 return action_result.set_status(phantom.APP_SUCCESS)
              else:
                 pass

           r = session.post(elem_content_url, data=json.dumps(new_list_content), headers=self.h)
           r.raise_for_status()
           self._logout(action_result, session)

        except:
           self.set_status(phantom.APP_ERROR, "Couldn't update the IP List")
           self.append_to_message("Couldn't update the Forcepoint SMC")
           action_result.set_status(phantom.APP_ERROR, "Couldn't updat ethe Forcepoint SMC")
           return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):

        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)

        elif action_id == 'block_ip':
            ret_val = self._handle_block_ip(param)

        return ret_val

    def initialize(self):

        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        """
        # get the asset config
        config = self.get_config()

        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """

        return phantom.APP_SUCCESS

    def finalize(self):

        # Save the state, this data is saved accross actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == '__main__':

    import sys

    import pudb
    pudb.set_trace()

    if (len(sys.argv) < 2):
        print("No test json specified as input")
        exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = ForcepointConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)
