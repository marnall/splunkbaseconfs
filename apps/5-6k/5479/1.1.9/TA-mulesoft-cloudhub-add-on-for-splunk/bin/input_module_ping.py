
# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json
import re


def validate_input(helper, definition):

    dummy = definition.parameters.get('dummy', None)
    
    pass


def collect_events(helper, ew):

    url = 'https://anypoint.mulesoft.com/cloudhub/api/ping'
    start = time.clock()
    req = requests.get(url)
    end = time.clock() - start
    endMs = end*1000

    capture_status = re.search('\{\"status\"\:([^}]*)', str(req.text))
    status = str(capture_status.group(1))
    json_obj = '{"responseCode":"'+str(req.status_code)+'", "responseTimeMs":"'+str(endMs)+'", "status":'+str(status)+'}'
    json_dump = json.dumps(json_obj)
    json_load = json.loads(json_dump)

    event = helper.new_event(data=json_load,
                                     time=None,
                                     host=None,
                                     index=helper.get_output_index(),
                                     source="mulesoft:ping",
                                     sourcetype="mulesoft:ping",
                                     done=True,
                                     unbroken=True)

    ew.write_event(event)