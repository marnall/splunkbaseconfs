# encoding = utf-8
import os
import splunk.appserver.mrsparkle.lib.util as util
import os
import sys
import time
import datetime
import json
import string

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    ti_url = helper.get_arg('ti_url')
    context = helper.get_arg('context')
    method = 'GET'

    response = helper.send_http_request(ti_url, method, parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=10.0, use_proxy=True)
    r_text = response.text.splitlines()
    for row in r_text:
        if (row.startswith("#")
            or row.startswith("/")
            or 255 < len(row) < 4
            or '.' not in row
            or row[0] not in string.ascii_letters):
            pass
        else:
            d = {
                'context': context,
                'ti_domain': row,
                'url': ti_url
            }
            event = helper.new_event(
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=helper.get_sourcetype(),
                data=json.dumps(d),
                done=True,
                unbroken=True)
        
            ew.write_event(event)
