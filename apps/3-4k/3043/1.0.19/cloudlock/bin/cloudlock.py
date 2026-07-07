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
import six
import collections
if six.PY2:
	from ConfigParser import ConfigParser, NoOptionError
else:
	from configparser import ConfigParser, NoOptionError
from contextlib import contextmanager
from datetime import datetime, timedelta
if six.PY2:
	import httplib
else:
	import http.client as httpliib
import json
import logging
import logging.handlers
import os
import requests
import splunk.rest
import sys
from time import sleep
#import urllib2
import dateutil.parser
import pytz

from splunklib.modularinput import *

# set up logging suitable for splunkd comsumption
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)
session_key = ''

#
# Put Cloudlock-specific stuff here
#
# Requests 2.7.0 has a problem with SSL certificate validation (it's integration with urllib3).
KEY_AND_VALUE_CHANGE = 3
KEY_CHANGE_ONLY = 2

EventIndex = collections.namedtuple('EventIndex', ['datetime', 'offset'])

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
cache = SPLUNK_HOME + "/etc/apps/cloudlock/cache"

class CLAPIClient(object):
    """
    CloudLock API Client
    """

    def __init__(self, token, base_url):
        self.token = token
        self.base_url = base_url
        self.session = session = requests.session()

        session.mount(self.base_url, requests.adapters.HTTPAdapter())
        session.headers.update(
            {'Content-Type': 'application/json', 'Authorization': 'Bearer {}'.format(self.token)})

    @staticmethod
    def to_datetime(value):
        #return datetime.strptime(value[:-6], '%Y-%m-%dT%H:%M:%S.%f')
        ts_tz_aware = dateutil.parser.parse(value)
        try:
            utc_ts = ts_tz_aware.astimezone(pytz.timezone('UTC')).replace(tzinfo=None)
        except Exception:
            utc_ts = ts_tz_aware
        return utc_ts

    @staticmethod
    def get_latest_incident(results):
        latest_updated_at = results[-1]['updated_at']
        last_second = CLAPIClient.to_datetime(latest_updated_at)
        offset = len(
            [x for x in results if last_second == CLAPIClient.to_datetime(x['updated_at'])])
        return EventIndex(latest_updated_at, offset)

    def _request(self, relative_url, params=None, data=None, method='GET', verify_ssl=False):
        global session_key
        relative_url = '/'.join((self.base_url, relative_url))
        response = self.session.request(method, relative_url, params=params, data=data,
                                        verify=verify_ssl)

        logging.info("Received HTTP Code: " + str(response.status_code))
        if response.status_code == 888:
            msg = "There is a new version of the CloudLock Splunk Application. In order to continue receiving CloudLock information, please upgrade the Application."
            logging.error(msg)

            endpoint = '/services/messages'
            postArgs = {'name':'message', 'severity': 'warn','value':msg  }
            response2, content2 = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=session_key, raiseAllErrors=False, postargs=postArgs)

            logging.error("Disabling 'cloudlock/incidents': will cause a broken pipe - ignore")
            endpoint = '/servicesNS/nobody/cloudlock/data/inputs/cloudlock/incidents/disable'
            response2, content2 = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=session_key, raiseAllErrors=False)


        response.raise_for_status()

        return response.json()


    def get_incidents(self, **payload):
        return self._request('incidents?count_total=false', params=payload)['items']

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
            results = self.get_incidents(updated_after=incident_index.datetime,
                                         offset=incident_index.offset,
                                         limit=limit,
                                         order='updated_at')
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
        print (v)
        if isinstance(v, collections.MutableMapping):
            items.extend(list(six.iteritems(flatten(v, new_key, sep=sep))))
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


class MyScript(Script):
    """All modular inputs should inherit from the abstract base class Script
    from splunklib.modularinput.script.
    They must override the get_scheme and stream_events functions, and,
    if the scheme returned by get_scheme has Scheme.use_external_validation
    set to True, the validate_input function.
    """
    def get_scheme(self):
        """When Splunk starts, it looks for all the modular inputs defined by
        its configuration, and tries to run them with the argument --scheme.
        Splunkd expects the modular inputs to print a description of the
        input in XML on stdout. The modular input framework takes care of all
        the details of formatting XML and printing it. The user need only
        override get_scheme and return a new Scheme object.

        :return: scheme, a Scheme object
        """
        scheme = Scheme("CloudLock Incident Extraction")

        scheme.description = "Access CloudLock Incidents"
        # If you set external validation to True, without overriding validate_input,
        # the script will accept anything as valid. Generally you only need external
        # validation if there are relationships you must maintain among the
        # parameters, such as requiring min to be less than max in this example,
        # or you need to check that some resource is reachable or valid.
        # Otherwise, Splunk lets you specify a validation string for each argument
        # and will run validation internally using that string.
        scheme.use_external_validation = True
        #scheme.use_single_instance = True
        scheme.use_single_instance = False

        user_argument = Argument("user")
        user_argument.data_type = Argument.data_type_string
        user_argument.description = "CloudLock User"
        user_argument.required_on_create = True
        # If you are not using external validation, you would add something like:
        #
        # scheme.validation = "owner==splunk"
        scheme.add_argument(user_argument)

        url_argument = Argument("url")
        url_argument.data_type = Argument.data_type_string
        url_argument.description = "URL of the CloudLock Server"
        url_argument.required_on_create = True
        scheme.add_argument(url_argument)

        return scheme

    def validate_input(self, validation_definition):
        """In this example we are using external validation to verify that the Github
        repository exists. If validate_input does not raise an Exception, the input
        is assumed to be valid. Otherwise it prints the exception as an error message
        when telling splunkd that the configuration is invalid.

        When using external validation, after splunkd calls the modular input with
        --scheme to get a scheme, it calls it again with --validate-arguments for
        each instance of the modular input in its configuration files, feeding XML
        on stdin to the modular input to do validation. It is called the same way
        whenever a modular input's configuration is edited.

        :param validation_definition: a ValidationDefinition object
        """
        # Get the values of the parameters, and test to make sure it's all good
        user = validation_definition.parameters["user"]
        url = validation_definition.parameters["url"]

        if user == '':
            raise ValueError("User must not be null.")

        if url == '':
            raise ValueError("URL must not be null.")

    def stream_events(self, inputs, ew):
        global session_key
        """This function handles all the action: splunk calls this modular input
        without arguments, streams XML describing the inputs to stdin, and waits
        for XML on stdout describing events.

        If you set use_single_instance to True on the scheme in get_scheme, it
        will pass all the instances of this input to a single instance of this
        script.

        :param inputs: an InputDefinition object
        :param ew: an EventWriter object
        """

        session_key = inputs.metadata["session_key"]
        (worked, response, content) = get_token(session_key, None)
        if worked == False:
            logging.error('CloudLock: Error getting KVStore token table')
            sys.exit(1)

        # Go through each input for this modular input
        for input_name, input_item in six.iteritems(inputs.inputs):
            # Get fields from the InputDefinition object
            user = input_item["user"].strip()
            url = input_item["url"].strip()

            # Get the token from the KVStore
            token = ''
            j = json.loads(content)
            for row in j:
                if row["name"] == user:
                    if row["url"] == url:
                        token = row["token"]
                    elif row["url"] == "*" and token == '':
                        token = row["token"]

            if token == '':
                logging.error("CloudLock: Can't find token for user=" + user + " url=" + url)
                sys.exit(1)
            
            cl_client = CLAPIClient(token, url)
            recorder = Recorder(input_name.split("//")[1])
            theRecord = recorder.get_last_call()
            oldDateString = theRecord.datetime
            oldDate = cl_client.to_datetime(oldDateString)
            newDate = oldDate + timedelta(milliseconds=1)
            newDateString = newDate.strftime('%Y-%m-%dT%H:%M:%S.%f+00:00')
            last_event = EventIndex(newDateString,0)


            logging.info('CloudLock: Polling from {}'.format(last_event.datetime or 'first known event'))

        
            # Create an Event object, and set its fields
            event = Event(sourcetype="incident")
            event.stanza = input_name
            
            for last_date, incidents in cl_client.get_all_incidents(last_event):
                for item in incidents:
                    event.data = json.dumps(flatten(item))
                    ew.write_event(event)
                recorder.save_last_call(last_date)


if __name__ == "__main__":
    sys.exit(MyScript().run(sys.argv))
