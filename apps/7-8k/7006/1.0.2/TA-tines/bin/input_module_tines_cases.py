# encoding = utf-8

import os
import sys
import time
import datetime
import json


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # per_page = definition.parameters.get('per_page', None)
    pass


def collect_events(helper, ew):
    global_tines_tenant_url = helper.get_global_setting("tines_tenant_url")
    global_tines_user_email_address = helper.get_global_setting("tines_user_email_address")
    global_tines_api_key = helper.get_global_setting("tines_api_key")

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-user-token": global_tines_api_key,
        "x-user-email": global_tines_user_email_address
    }

    payload = {
        "per_page": 500
    }

    url = global_tines_tenant_url + "/api/v1/cases"
    # data = []

    # The following examples send rest requests to some endpoint.
    while True:
        response = helper.send_http_request(url, "get", parameters=None, payload=payload, headers=headers, cookies=None,
                                            verify=True, cert=None, timeout=None, use_proxy=True)

        resp = json.loads(response.text)
        for item in resp["cases"]:
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(),
                                     sourcetype=helper.get_sourcetype(), data=json.dumps(item))
            ew.write_event(event)

        url = resp["meta"]["next_page"]
        if url is None:
            break

    # dict_event = {"audit_logs": data}
    # event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(),
    #                          sourcetype=helper.get_sourcetype(), data=json.dumps(dict_event))
    #
    # ew.write_event(event)
