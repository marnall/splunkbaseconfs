#!/usr/bin/env python
#
# Copyright (c) 2015-2017. CloudLock, LLC.  All rights reserved.
#
# This application is protected by contract law, copyright laws, and international treaties.
# Only authorized users of the CloudLock Service are authorized to use this application.
# This application includes Python, an open source component subject to the following notice:
#
# Copyright 2011-2014 Splunk, Inc. 
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may 
# not use this file except in compliance with the License. You may obtain 
# a copy of the License at 
# http://www.apache.org/licenses/LICENSE-2.0 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT 
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations 
# under the License.
#

from __future__ import print_function
import collections
import six
if six.PY2:
	from ConfigParser import ConfigParser, NoOptionError
else:
	from configparser import ConfigParser, NoOptionError
from contextlib import contextmanager
from datetime import datetime
import json
import os
import requests

#
# Put Cloudlock-specific stuff here
#
# Requests 2.7.0 has a problem with SSL certificate validation (it's integration with urllib3).
KEY_AND_VALUE_CHANGE = 3
KEY_CHANGE_ONLY = 2

EventIndex = collections.namedtuple('EventIndex', ['datetime', 'offset'])

class CLAPIClient(object):
    """
    CloudLock API Client
    """
    BASE_URL = 'https://api.cloudlock.com/api/v2'

    def __init__(self, token, base_url=BASE_URL):
        self.token = token
        self.base_url = base_url
        self.session = session = requests.session()
        # retries = Retry(total=100, status_forcelist=(429, 500, 502, 504), backoff_factor=0.1)
        # session.mount(self.BASE_URL, requests.adapters.HTTPAdapter(max_retries=retries))
        session.mount(self.BASE_URL, requests.adapters.HTTPAdapter())
        session.headers.update(
            {'Content-Type': 'application/json', 'Authorization': 'Bearer {}'.format(self.token)})

    @staticmethod
    def to_datetime(value):
        return datetime.strptime(value[:-6], '%Y-%m-%dT%H:%M:%S.%f')

    @staticmethod
    def get_latest_incident(results):
        latest_created_at = results[-1]['created_at']
        last_second = CLAPIClient.to_datetime(latest_created_at)
        offset = len(
            [x for x in results if last_second == CLAPIClient.to_datetime(x['created_at'])])
        return EventIndex(latest_created_at, offset)

    def _request(self, relative_url, params=None, data=None, method='GET', verify_ssl=False):
        relative_url = '/'.join((self.base_url, relative_url))
        response = self.session.request(method, relative_url, params=params, data=data,
                                        verify=verify_ssl)
        response.raise_for_status()

        return response.json()

    def get_incidents(self, **payload):
        return self._request('incidents', params=payload)['items']

    def get_incident(self, incident_id, **payload):
        r = self._request('incidents/%s' % incident_id, params=payload)
        incident = r['results'][0]
        return incident

    def update_incident(self, incident_id, status=None, severity=None, customer_key=None):
        data = {'incident_status': status, 'severity': severity, 'customer_key': customer_key}
        data = {(k, v) for k, v in data if v is not None}
        self._request('incidents/{}'.format(incident_id), data=json.dumps(data), method='PUT')

    def get_all_incidents(self, incident_index, limit=100):
        while True:
            logging.info('CloudLock: Getting last incidents from {} (offset {})'.format(*incident_index))
            results = self.get_incidents(created_after=incident_index.datetime,
                                         offset=incident_index.offset,
                                         limit=limit,
                                         order='created_at')
            if not results:
                logging.info('CloudLock: No new incidents found')
                raise StopIteration()

            logging.info('CloudLock: {} new incidents found'.format(len(results)))
            incident_index = self.get_latest_incident(results)
            yield incident_index, results

class Recorder(object):
    """
    stores latest polling data. implemented with python config parser.
    """
    config_section = 'CL_POLLING'

    def __init__(self, name):
        filename = 'cl_polling_' + name + '.ini'
        self.file = os.path.join(cache, filename)
        self.config = ConfigParser(allow_no_value=True)
        self.config.read(self.file)
        if not self.config.has_section(self.config_section):
            with open(self.file, 'w') as f:
                self.config.add_section(self.config_section)
                self.config.set(self.config_section, 'Empty', None)
                self.config.write(f)
            self.config.read(self.file)

    def save(self, key, value):
        with open(self.file, 'w') as f:
            self.config.set(self.config_section, str(key), str(value))
            self.config.write(f)

    def get(self, key, is_int=False):
        try:
            func = self.config.getint if is_int else self.config.get
            return func(self.config_section, key)
        except (NoOptionError, ValueError):
            return None

    def get_last_call(self):
        last_call = self.get('last_call')
        last_call = last_call if last_call and last_call != u'None' else None
        last_offset = self.get('last_offset', is_int=True)

        return EventIndex(last_call, last_offset)

    def save_last_call(self, event_index):
        self.save('last_call', event_index.datetime)
        self.save('last_offset', event_index.offset)


severity_mapping = {'INFO': 1, 'WARNING': 3, 'ALERT': 5, 'CRITICAL': 10}

mapping_types = {
    KEY_CHANGE_ONLY: lambda data, old_key, new_key: (new_key, data[old_key]),
    KEY_AND_VALUE_CHANGE: lambda data, old_key, new_key, convert: (new_key, convert(data[old_key]))
}

def flatten(d, parent_key='', sep='_'):
    items = []
    for k, v in six.iteritems(d):
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def transform_dict(mapping, data):
    flat_data = flatten(data, sep='.')
    for mapper in mapping:
        mapper_type = len(mapper)
        extract_fn = mapping_types[mapper_type]
        new_key, value = extract_fn(flat_data, *mapper)
        yield new_key, value

def get_token(sessionKey, base_uri=None):
    '''Get the token from the KV Store'''

    # Permit override of base URI in order to target a remote server.
    endpoint = '/servicesNS/nobody/cloudlock/storage/collections/data/cloudlock'
    if base_uri:
        repl_uri = base_uri + endpoint
    else:
        repl_uri = endpoint

    response, content = splunk.rest.simpleRequest(repl_uri,
        method='GET', sessionKey=sessionKey, raiseAllErrors=False)

    if response.status == 400:
        return (False, response.status, content)
    elif response.status != 200:
        return (False, response.status, content)
    return (True, response.status, content)

