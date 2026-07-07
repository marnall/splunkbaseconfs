# encoding = utf-8
import os
import splunk.appserver.mrsparkle.lib.util as util
import os
import sys
import time
import datetime
import json
import string
import csv
import re


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    ti_url = helper.get_arg('ti_url')
    context = helper.get_arg('context')
    input_format = helper.get_arg('format')
    method = 'GET'

    response = helper.send_http_request(ti_url, method, parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=10.0, use_proxy=True)
    if input_format == 'plaintext':
        feed_handler = handle_plaintext_feed
    elif input_format == 'csv':
        feed_handler = handle_csv_feed
    else:
        return None
        helper.log_error(
            'Unknown feed format provided. Only plaintext(line by line), csv and json are supported.')
    for ip in feed_handler(response):
        data = {
            'context': context,
            'ti_ip': ip,
            'url': ti_url
        }
        event = helper.new_event(
            source=helper.get_input_type(),
            index=helper.get_output_index(),
            sourcetype=helper.get_sourcetype(),
            data=json.dumps(data),
            done=True,
            unbroken=True)

        ew.write_event(event)

    def handle_plaintext_feed(response):
        r_text = response.text.splitlines()
        for row in r_text:
            if row.startswith("#") or row.startswith("/") or row == "" or row[0] not in string.hexdigits or len(row)>40:
                pass
            else:
                yield row


    def handle_csv_feed(response):
        r_text = response.text.splitlines()
        reader = csv.reader(r_text)
        ip_pattern = r'(?:(?:25[0-5]|2[0-4[0-9]|[01]?[0-9][0-9]?)[-.]){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
        ip_regex = re.compile(ip_pattern)
        column = None
        for row in reader:
            if row[0].startswith('#') or row[0].startswith('/') or row == []:
                continue
            else:
                if column is None:
                    for index, field in enumerate(row):
                        if ip_regex.match(field):
                            column = index
            if column is not None:
                ip = row[column]
                yield ip