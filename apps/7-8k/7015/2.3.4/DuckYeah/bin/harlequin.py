#!/usr/bin/env python

import duckyeah
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators


@Configuration()
class harlequin(StreamingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """

    quack = Option(require=True, validate=None)
    method = Option(require=False, validate=None)
    session = Option(require=True, validate=None)

    def stream(self, events):
        # To connect with Splunk, use the instantiated service object which is created using the server-uri and
        # other meta details and can be accessed as shown below
        # Example:-
        #    service = self.service

        # Put your reporting implementation

        if not self.method:
            self.method = 'POST'

        api = duckyeah.duckYeahAPI(self.service, self.quack, self, method=self.method)

        for event in events:
            complex_query = self.quack.split("/")

            if complex_query[-1] == 'file':
                event['session_id'] = complex_query[-2]
                api.process_upload(event)

                if 'json' in event:
                    resp = api.response

                    if type(resp) is list:
                        for item in resp:
                            for key, value in item.items():
                                event[key] = value
                    else:
                        for key, value in resp.items():
                            event[key] = value

                else:
                    event['packaged'] = 1

            else:
                response = api.queryAPI(event)

                if response.status == 200:
                    resp = json.loads(response.read())

                    event['entranced'] = True
                    event['resp'] = resp

                    try:
                        if isinstance(resp, list) and 'id' in resp[0]:
                            event['id'] = resp[0]['id']

                    except IndexError:
                        pass
                else:
                    resp = json.loads(response.read())

                    event['entranced'] = False
                    event['api_error'] = response.status
                    event['api_message'] = resp[0]['message']

            yield event

dispatch(harlequin, sys.argv, sys.stdin, sys.stdout, __name__)
