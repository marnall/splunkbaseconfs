
# encoding = utf-8

import os
import sys
import time
import datetime
import json
from absolute_client import Absolute as Absolute


'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

def validate_input(helper, definition):
    pass

def collect_events(input, ew):
    # TODO: ok, so... as if python itself wasn't painful enough, we can't just get all stanzas & iterate...
    # input.get_input_stanza_names()
    # -> if in single_instance_mode, then a list is returned (that's fine, the method is in fact plural)
    # -> if in multi_mode, then a string is returned instead (b/c '_names' is singular??!?)
    # ... get names & iterate? NO!
    # ... need logic to check which mode we're in before accessing the stanza(s)!!!
    #
    # ... dirty st00pid workaround is to hardcode the stanza name; needs to match in web UI/inputs.conf:
    stanza = input.get_input_stanza('devices')
    api = Absolute.API.Client('devices', stanza['absolute_account']['username'], stanza["absolute_account"]["password"])
    input.log_info(f'created an API client with headers: {";".join(api.request.headers.keys())}')
    devices = api.call()
    for device in devices:
        event = input.new_event(json.dumps(device), time=datetime.datetime.now().strftime("%FT%T %z"), host=Absolute.API.host)
        ew.write_event(event)
    input.log_info(f'finished writing {len(devices)} device events')
