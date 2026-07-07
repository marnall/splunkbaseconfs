# encoding = utf-8

import os
import sys
import time
import datetime
import json


def validate_input(helper, definition):
    return True


def collect_events(helper, ew):
    helper.log_info("Starting")
    print "starting"

    url = "https://api.perception-point.io/api/get_siem_logs/"
    method = "GET"
    opt_api_key = helper.get_arg('api_key')
    headers = {"Authorization": "Token {}".format(opt_api_key)}
    last_timestamp = helper.get_check_point('last_timestamp') or 0
    parameters = {'start': last_timestamp}

    while url:
        response = helper.send_http_request(url, method, parameters=parameters, payload=None,
                                            headers=headers, cookies=None, verify=True, cert=None,
                                            timeout=None, use_proxy=True)
        response.raise_for_status()
        r_json = response.json()
        url = r_json["next"]

        for r in r_json['results']:
            last_timestamp = max(r['timestamp'], last_timestamp)
            event = helper.new_event(json.dumps(r), sourcetype=helper.get_sourcetype() or 'ppsiemlogs')
            ew.write_event(event)

    helper.save_check_point('last_timestamp', last_timestamp)

