# encoding = utf-8

import os
import sys
import time
import datetime


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # auscert_api_key = definition.parameters.get('auscert_api_key', None)
    pass

def collect_events(helper, ew):

    opt_auscert_api_key = helper.get_arg('auscert_api_key')

    proxy_settings = helper.get_proxy()

    helper.log_info("Retrieving AusCERT 7-day phishing feed")

    url = "https://www.auscert.org.au/api/v1/malurl/phishing-7-txt"
    headers = {'API-Key': opt_auscert_api_key}

    # The following examples send rest requests to some endpoint.
    response = helper.send_http_request(url, method="GET", parameters=None, payload=None,
                                        headers=headers, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)

    response.raise_for_status()

    for data in response.text.splitlines():
        event = helper.new_event(data, index=helper.get_output_index(), source=url, sourcetype=helper.get_sourcetype())
        ew.write_event(event)