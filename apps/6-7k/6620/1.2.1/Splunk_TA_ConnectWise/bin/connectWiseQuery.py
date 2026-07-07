#!/Applications/Splunk/bin/python
# Modular input for ConnectWise Manage
# Written by Paul Stout @ bitsIO <pstout@bitsioinc.com>
#
# Remember kids, don't drink and rm - rf.

import base64
import datetime
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunk.clilib import cli_common as cli
from splunklib.client import *
from splunklib.modularinput import *

class CWManageModInput(Script):
    def get_scheme(self):
        scheme = Scheme("ConnectWise Manage")
        scheme.description = "Streams changes to ConnectWise Manage objects."

        endpoint_argument = Argument("endpoint")
        endpoint_argument.data_type = Argument.data_type_string
        endpoint_argument.description = "ConnectWise Manage endpoint to query"
        endpoint_argument.required_on_create = True
        endpoint_argument.validation = "object_type/object"
        scheme.use_external_validation = True
        scheme.add_argument(endpoint_argument)

        return scheme

    def validate_input(self, validation_definition):
        print(validation_definition)
        endpoint = validation_definition.parameters['endpoint']
        endpoint_match = re.match( r'[a-zA-Z0-9]+\/[a-zA-Z0-9]+', endpoint)

        if not endpoint_match:
            raise ValueError("Endpoint must follow the object_type/object pattern. [%s] provided." % endpoint)

    def stream_events(self, inputs, ew):
        for input_name, input_item in inputs.inputs.items():
            checkpoint_file = os.path.join(inputs.metadata['checkpoint_dir'], input_item['endpoint'].replace('/','_'))

            try:
                with open(checkpoint_file, 'r') as cf:
                    offset = cf.read()
            except:
                offset = False

            cwm_conf = cli.getConfStanza('connectwise', 'general');

            company_id = cwm_conf.get('company')
            client_id = cwm_conf.get('clientId')
            public_key = cwm_conf.get('publicKey')
            api_version = cwm_conf.get('version')
            base_uri = cwm_conf.get('url')
            release = cwm_conf.get('release')

            endpoint = input_item['endpoint']

            session_key = inputs.metadata['session_key']

            storage_client = Service(token=session_key)
            storage_passwords = storage_client.storage_passwords

            credential_name = "connectWiseQuery:%s:" % public_key
            credential = False

            for storage_password in storage_passwords.list():
                if storage_password.name == credential_name:
                    credential = storage_password

            private_key = credential.content['clear_password']

            manage_api = CWManage(company_id, client_id, base_uri, release, api_version, endpoint, public_key, private_key)
            manage_api.query(offset=offset)

            for event in manage_api.events:
                ev = Event()

                ev.stanza = input_name
                ev.data = json.dumps(event)

                ew.write_event(ev)

            if manage_api.checkpoint:
                with open(checkpoint_file, 'w') as cf:
                    cf.write(manage_api.checkpoint)

class CWManage:
    def __init__(self, company_id, client_id, base_uri, release, api_version, endpoint, public_key, private_key):
        auth_string = "%s+%s:%s" % (company_id, public_key, private_key)
        auth_header = base64.b64encode(auth_string.encode()).decode()

        self.construct_headers(auth_header, client_id)
        self.base_uri = "https://%s/%s/apis/%s/%s" % (base_uri, release, api_version, endpoint)
        self.checkpoint = ''
        self.events = []

    def construct_headers(self, auth_header, client_id):
        self.headers = {
            'Authorization': "Basic %s" % auth_header,
            'clientId': client_id,
            'Content-Type': 'application/json'
        }

    def query(self, uri=False, offset=False):
        if uri:
            request_uri = uri
        else:
            request_uri = self.base_uri + ("?conditions=lastUpdated>[%s]" % offset if offset else '' )

        req = urllib.request.Request(request_uri, headers=self.headers)

        with urllib.request.urlopen(req) as response:
            next_page = False
            response_headers = response.getheaders()

            for header in response_headers:            
                if header[0] == 'Link':
                    links = header[1].split(', ')

                    for link in links:
                        link_details = re.match( r'<(?P<link_uri>[^>]+)>;\srel="(?P<link_rel>[^"]+)"', link)

                        if link_details and link_details.group('link_rel') == 'next':
                            next_page = True
                            next_uri = link_details.group('link_uri')

            events = json.loads(response.read())

            for event in events:
                output_event = self.flatten_event(event)

                self.events.append(output_event)

                self.set_checkpoint(output_event['lastUpdated'])
        if next_page:
            self.query(next_uri)

    def flatten_event(self, event):
        flat_event = {}

        for key, value in event.items():
            if type(value) is dict and 'id' in value:
                flat_event["%sId" % key] = value['id']
            elif type(value) is dict and key=='_info':
                if 'lastUpdated' in value:
                    flat_event['lastUpdated'] = value['lastUpdated']

                if 'updatedBy' in value:
                    flat_event['updatedBy'] = value['updatedBy']

                if 'dateEntered' in value:
                    flat_event['dateEntered'] = value['dateEntered']

                if 'enteredBy' in value:
                    flat_event['enteredBy'] = value['enteredBy']
            else:
                if key != 'notes' and key !='signature':
                    # These cause significant truncation issues if HTML formamtting is present.
                    flat_event[key] = value

        return flat_event

    def set_checkpoint(self, timestamp):
        if not self.checkpoint:
            self.checkpoint = timestamp
        else:
            checkpoint = datetime.datetime.strptime(self.checkpoint, '%Y-%m-%dT%H:%M:%S%z')
            event_time = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S%z')

            if event_time > checkpoint:
                self.checkpoint = timestamp

if __name__=='__main__':
    sys.exit(CWManageModInput().run(sys.argv))
