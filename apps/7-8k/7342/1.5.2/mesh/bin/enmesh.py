#!/usr/bin/env python

import base64
import json
import meshapi
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators


@Configuration()
class enmesh(StreamingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """

    query = Option(require=False, validate=None)
    method = Option(require=False, validate=None)
    origin = Option(require=False, validate=None)

    view_id = Option(require=False, validate=None)
    view_session = Option(require=False, validate=None)

    def stream(self, events):
        # To connect with Splunk, use the instantiated service object which is created using the server-uri and
        # other meta details and can be accessed as shown below
        # Example:-
        #    service = self.service

        # Put your reporting implementation

        if not self.query:
            self.query = 'data'

        if not self.method:
            self.method = 'POST'

        if not self.origin:
            self.origin = 'adhoc'

        api = meshapi.meshAPI(self.service, self.query, self, method=self.method)

        meshit = False

        if api.settings['mesh_health_telemetry'] == "1" and self.query == 'data':
            meshit = True

        elif self.origin=='autohealthcheck' and api.settings['mesh_health_tickets'] == "1":
            meshit = True

        elif not self.query == 'data':
            meshit = True

        for event in events:
            if meshit:
                response = api.queryAPI(event)

                if response.status==200:
                    resp = json.loads(response.read())

                    event['meshed'] = True
                    event['resp'] = resp

                    try:
                        if isinstance(resp, list) and 'id' in resp[0]:
                            event['id'] = resp[0]['id']

                    except IndexError:
                        pass
                else:
                    resp = json.loads(response.read())

                    if 'title' in resp:
                        resp_message = resp['title']
                    elif 'message' in resp:
                        resp_message = resp['message']
                    else:
                        resp_message = "HTTP %s" % response.status

                    event['meshed'] = False
                    event['api_error'] = response.status
                    event['api_message'] = resp_message
            else:
                event['meshed'] = False

            yield event

dispatch(enmesh, sys.argv, sys.stdin, sys.stdout, __name__)
