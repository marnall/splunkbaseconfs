#!/usr/bin/env python

import duckyeah
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from datetime import datetime
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(local=True)
class mandarin(GeneratingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """

    quack = Option(require=True, validate=None)
    session = Option(require=True, validate=None)

    def generate(self):
        api = duckyeah.duckYeahAPI(self.service, self.quack, self)

        response = api.queryAPI()

        resp = json.loads(response.read())

        if type(resp) is list and len(resp) > 0 and 'appinspect_id' in resp[0] and 'status' in resp[0] and resp[0]['status'] == 'processing':
            appinspect_processing = True

            while appinspect_processing:
                time.sleep(5)
                response = api.queryAPI()

                resp = json.loads(response.read())

                if type(resp) is list and len(resp) > 0 and not 'status' in resp[0]:
                    appinspect_processing = False

        if type(resp) is dict:
            event = resp

            event['_raw'] = json.dumps(event)
            event['_time'] = time.time()

            yield event

        elif type(resp) is list:
            for event in resp:
                event['_raw'] = json.dumps(event)
                event['_time'] = time.time()

                yield event

dispatch(mandarin, sys.argv, sys.stdin, sys.stdout, __name__)
