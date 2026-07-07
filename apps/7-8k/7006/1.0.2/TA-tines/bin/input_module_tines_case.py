# encoding = utf-8

import datetime
import json
import os


def collect_events(helper, ew):
    global_tines_tenant_url = helper.get_global_setting("tines_tenant_url")
    global_tines_user_email_address = helper.get_global_setting("tines_user_email_address")
    global_tines_api_key = helper.get_global_setting("tines_api_key")
    start_date = helper.get_global_setting("start_date")

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-user-token": global_tines_api_key,
        "x-user-email": global_tines_user_email_address
    }

    url = global_tines_tenant_url + "/api/v1/cases"
    # data = []

    # The following examples send rest requests to some endpoint.
    start_date = helper.get_check_point("cases")

    if start_date is None:
        start_date = helper.get_global_setting("start_date")

    payload = {
        "per_page": 500,
        "filters": {
            "start_date": start_date
        }
    }

    # Set the cursor for the next time this code executes so there are no duplicate values
    helper.save_check_point("cases", datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))
    

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

