# Copyright 2021 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License'): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

'''
This module provides cloud stack settings:
    - feature flag to determine Classic stack vs Noah stack
    - HEC elastic load balancer endpoints to forward HEC events
'''
import os
import sys
import logging
import requests

current_path = os.path.dirname(__file__)
sys.path.append(os.path.join(current_path, 'external'))

from solnlib.conf_manager import ConfManager, ConfManagerException

__all__ = ['StackInfo']


class StackInfo():
    '''Return stack settings related to HEC token workflow

    :param session_key: Splunk access token.
    :type session_key: ``string`

    Usage::

       >>> from solnlib import stack_info
       >>> ss = stack_type.StackInfo(session_key)
       >>> ss.is_noah_stack() -> True or False
       >>> ss.hec_elb() -> return HEC ELB to forward events
    '''

    def __init__(self, session_key):
        self._session_key = session_key
        self._is_noah_stack = None
        self._hec_elb = None

        self._retrieve_stack_info()

    def _retrieve_stack_info(self):
        """ Retrieve stack type and HEC elastic load balancer endpoint
        """
        noah_url = self._conf_stanza(
            '100-whisper-searchhead',
            'server',
            stanza_name='noahService',
            key='uri'
        )
        self._is_noah_stack = True if noah_url else False
        self._hec_elb = self._conf_stanza(
            '100-whisper-searchhead',
            'cloud',
            stanza_name='deployment',
            key='hecEndpoint'
        )
        logging.info('class=StackInfo, action=retrieve_stack_info, status=success, is_noah_stack={0}, hec_elb={1}'.format(self._is_noah_stack, self._hec_elb))

    def _conf_stanza(self, app, conf_filename, stanza_name=None, key=None):
        """ Return kvstore values by conf file and stanza

        :param app: App name of namespace.
        :type app: ``string``
        :param conf_filename: Conf file name.
        :type scheme: ``string``
        :param stanza_name: (optional) Stanza name, default is None.
        :type stanza_name: ``string``
        :param key: (optional) kvstore key name, default is None.
        :type key: ``string``

        """
        logging.debug('class=StackInfo, action=retrieve_conf_stanza, status=start, app={0}, conf_filename={1}, stanza={2}, key={3}'.format(app, conf_filename, stanza_name, key))

        try:
            cfm = ConfManager(self._session_key, app)
            conf = cfm.get_conf(conf_filename)
            if not conf.stanza_exist(stanza_name):
                return None

            stanza_values = conf.get(stanza_name)
            value = stanza_values.get(key)

            logging.info('class=StackInfo, action=retrieve_conf_stanza, status=success, stanza_values={0}, value={1}'.format(stanza_values, value))
            return value
        except Exception as e:
            logging.error('class=StackInfo, action=retrieve_conf_stanza, status=failed, reason={}'.format(str(e)))
            return None


    @property
    def is_noah_stack(self):
        return self._is_noah_stack

    @property
    def hec_elb(self):
        return self._hec_elb

    def send_hec_events(self, auth_token, events):
        """ Send HEC events by HEC elastic load balancer

        :param auth_token: Splunk auth token used to send HEC events.
        :type auth_token: ``string``
        :param events: HEC events.
        :type events: ``object``

        """
        logging.debug('class=StackInfo, action=send_hec_events, status=start, events={}'.format(events))
        try:
            token = 'Splunk {}'.format(auth_token)
            headers = {'Authorization': token}
            hec_endpoint = 'https://{}/services/collector'.format(self._hec_elb)
            resp = requests.post(hec_endpoint, headers=headers, data=events)
            logging.info('class=StackInfo, action=send_hec_events, status={}, content={}'.format(resp.json()['text'], resp.json()))
            return resp
        except Exception as e:
            logging.error('class=StackInfo, action=send_hec_events, status=error, reason={}'.format(str(e)))
            return e
