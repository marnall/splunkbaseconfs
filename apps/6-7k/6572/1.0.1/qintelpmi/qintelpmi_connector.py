# File: qintelpmi_connector.py
#
# Copyright (c) Qintel, LLC, 2022
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

# /usr/bin/python

# Python 3 Compatibility imports
from __future__ import print_function, unicode_literals

import json
import os
import traceback
from datetime import datetime
from functools import reduce
from operator import getitem

# Phantom App imports
import phantom.app as phantom
from dateutil.parser import parse as parse_dt
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from qintelpmi_consts import *
from qintelpmi_helper import search_pmi


def reduce_item(record, path):
    if not isinstance(path, (list, tuple)):
        path = [path]

    try:
        value = reduce(getitem, path, record)
    except KeyError:
        return None

    if value in ['None', '']:
        return None

    return value


def make_timestamp(ts):
    if not ts:
        return

    if isinstance(ts, int):
        return datetime.fromtimestamp(ts)

    if isinstance(ts, str):
        return parse_dt(ts)


class QintelPmiConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(QintelPmiConnector, self).__init__()

        self._state = None
        self.remote = None
        self.client_id = None
        self.client_secret = None

    def _handle_test_connectivity(self, param):

        action_result = self.add_action_result(ActionResult())

        self.save_progress("Connecting to endpoint")

        try:
            res = search_pmi(None, 'ping', **self.client_args)
            self.debug_print(f'pmi test connectivity return: {res}')
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, ERR_TEST_CONN.format(err=str(e))
            )

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _process_cve_observations(self, data):

        observ = reduce_item(data, ('relationships', 'observations', 'data'))

        observations_data = []

        for obs in observ:
            obs_return = {}

            actor_label = reduce_item(obs, ('relationships', 'tags', 'data'))
            if actor_label:
                obs_return['actor'] = \
                    reduce_item(actor_label[0], ('attributes', 'label'))

            actor_type = reduce_item(obs, ('relationships', 'tags', 'data'))
            if actor_type:
                obs_return['actor_type'] = \
                    reduce_item(actor_type[0], ('attributes', 'tag_type'))

            obs_return['exploit_type'] = \
                reduce_item(obs, ('attributes', 'exploit_type'))

            obs_return['notes'] = reduce_item(obs, ('attributes', 'notes'))

            timestamps = reduce_item(obs, ('attributes', 'timestamps'))
            if timestamps:
                for t in timestamps:
                    if t['context'] == 'observed':
                        obs_return['observation_date'] = \
                            make_timestamp(t['value']).strftime(DATE_FORMAT)

            observations_data.append(obs_return)

        return observations_data

    def _process_cve_attributes(self, data, cve):

        ret_data = {}

        ret_data['cvss'] = reduce_item(data, ('attributes', 'base_score_v3'))

        ret_data['affected_system'] = \
            reduce_item(data, ('attributes', 'affected_system', 'name'))

        ret_data['affected_versions'] = \
            reduce_item(data, ('attributes', 'affected_system', 'versions'))

        if isinstance(ret_data['affected_versions'], list):
            ret_data['affected_versions'] = \
                ', '.join(ret_data['affected_versions'])

        ret_data['last_observed'] = \
            make_timestamp(
                reduce_item(data, ('attributes', 'last_observed'))
            ).strftime(DATE_FORMAT)  # noqa

        ret_data['pmi_url'] = CVE_URL.format(cve=cve)

        return ret_data

    def _handle_pmi_get_cve_intel(self, param):

        self.save_progress("In action handler for: {0}".format(
            self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        cve = param['cve']

        try:
            rv = search_pmi(cve, 'cve', **self.client_args)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, str(e))

        try:
            data = rv.get('data', [])
            if not data:
                ret_data = {'pmi_url': CVE_URL.format(cve=cve)}
                obvs_data = []

                action_result.add_data(ret_data)
            else:
                for d in data:
                    ret_data = self._process_cve_attributes(d, cve)

                    obvs_data = self._process_cve_observations(d)
                    ret_data['observations'] = obvs_data

                    action_result.add_data(ret_data)
        except Exception as e:
            self.error_print('data processing error', traceback.format_exc())
            return action_result.set_status(
                phantom.APP_ERROR, ERR_PROCESS_RV.format(err=str(e))
            )

        action_result.set_summary({
            'observation_count': len(obvs_data),
            'last_observed': ret_data.get('last_observed')
        })

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == 'pmi_get_cve_intel':
            ret_val = self._handle_pmi_get_cve_intel(param)

        if action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()

        self._proxies = {}
        env_vars = config.get('_reserved_environment_variables', {})
        if 'HTTP_PROXY' in env_vars:
            self._proxies['http'] = env_vars['HTTP_PROXY']['value']
        elif 'HTTP_PROXY' in os.environ:
            self._proxies['http'] = os.environ.get('HTTP_PROXY')

        if 'HTTPS_PROXY' in env_vars:
            self._proxies['https'] = env_vars['HTTPS_PROXY']['value']
        elif 'HTTPS_PROXY' in os.environ:
            self._proxies['https'] = os.environ.get('HTTPS_PROXY')

        self.client_args = {
            'remote': config.get('remote'),
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'user_agent': USER_AGENT,
            'logger': self.debug_print,
            'proxies': self._proxies
        }

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse
    import sys

    import requests

    timeout = 30

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
        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = QintelPmiConnector._get_phantom_base_url() + '/login'

            print("Accessing the Login page")
            r = requests.get(login_url, timeout=timeout)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken=' + csrftoken
            headers['Referer'] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, timeout=timeout,
                               data=data, headers=headers)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = QintelPmiConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json['user_session_token'] = session_id
            connector._set_csrf_info(csrftoken, headers['Referer'])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == '__main__':
    main()
