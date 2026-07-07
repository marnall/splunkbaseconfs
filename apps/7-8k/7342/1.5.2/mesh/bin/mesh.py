#!/usr/bin/env python

import json
import meshapi
import os
import pytz
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from datetime import datetime
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(local=True)
class mesh(GeneratingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """

    query = Option(require=True, validate=None)

    view_id = Option(require=False, validate=None)
    view_session = Option(require=False, validate=None)
    method = Option(require=False, validate=None)

    argument = False

    def generate(self):
        if not self.method:
            self.method = "GET"

        # yield { "e": vars(self.service).items()}

        api = meshapi.meshAPI(self.service, self.query, self, method=self.method)

        response = api.queryAPI()

        # TODO: Fail gracefully if not 200
        # print(response.status, response.reason)

        if type(response) is dict:
            if not response:
                yield { "e": "No response." }
            else:
                yield response

        else:
            if response.status==200:
                data = json.loads(response.read())

                for event in data:
                    if type(event) is str:
                        event = {'_raw': event}
                    else:
                        event['_raw'] = json.dumps(event)

                    if '_info' in event and 'dateEntered' in event['_info']:
                        formatted_time = event['_info']['dateEntered'].replace('Z', '+0000')
                        event['_time'] = time.mktime(datetime.strptime(formatted_time, '%Y-%m-%dT%H:%M:%S%z').timetuple())

                    if 'dateCreated' in event:
                        formatted_time = event['dateCreated'].replace('Z', '+0000')
                        event['_time'] = time.mktime(datetime.strptime(formatted_time, '%Y-%m-%dT%H:%M:%S%z').timetuple())

                    if 'source' in event:
                        event['eventSource'] = event['source']

                    if 'status' in event and 'name' in event['status']:
                        event['statusId'] = event['status']['id']
                        event['statusOrder'] = event['status']['Sort']
                        event['status'] = event['status']['name']

                    if 'owner' in event and 'name' in event['owner']:
                        event['ownerId'] = event['owner']['id']
                        event['owner'] = event['owner']['name']

                    if 'company' in event and 'name' in event['company']:
                        event['companyId'] = event['company']['id']
                        event['company'] = event['company']['name']

                    if 'priority' in event and 'name' in event['priority']:
                        event['priorityId'] = event['priority']['id']
                        event['priority'] = event['priority']['name']

                    event['host'] = api.host
                    event['source'] = 'meshAPI'
                    event['sourcetype'] = 'mesh:customer:%s' % self.query

                    yield event
            else:
                data = json.loads(response.read())

                self.error_exit("error", "HTTP %s: %s" % (response.status, data[0]['message']))

dispatch(mesh, sys.argv, sys.stdin, sys.stdout, __name__)
