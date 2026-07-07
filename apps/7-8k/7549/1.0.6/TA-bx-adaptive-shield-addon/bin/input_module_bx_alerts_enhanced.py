# encoding = utf-8

import os
import time
import json
from functools import wraps

def retry(exception_to_check, tries=5, delay=3, backoff=2):
    # retry decorator
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exception_to_check as e:
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry
    return deco_retry

@retry(Exception)
def get(url, helper, params=None, headers=None):
    if not params:
        params = {}
    if not headers:
        headers = {}
    res = helper.send_http_request(url, "get", parameters=params, headers=headers, use_proxy=True)
    res.raise_for_status()
    return res

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    # Fetch API key and account ID from input parameters
    api_key = helper.get_arg('api_key')  # Use input parameter for API key
    account_id = helper.get_arg('account_id')  # Use input parameter for account ID

    helper.log_info("----------------------------------------------")
    helper.log_info(f"Fetching alerts data for account ID: {account_id}")

    headers = {"Authorization": f"Token {api_key}"}
    alerts_url = f"https://api.adaptive-shield.com/api/v1/accounts/{account_id}/alerts"
    
    params = {"limit": 500}  # Adjust limit as needed
    
    # Fetch alerts data
    try:
        alerts_res = get(alerts_url, helper, headers=headers, params=params)
        alerts = alerts_res.json()["data"]
        next_page_uri = alerts_res.json().get('next_page_uri', None)
    except Exception as e:
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="as:internal", data=json.dumps({"error": str(e)}))
        ew.write_event(event)
        helper.log_info(f'Failed to fetch alerts: {str(e)}')
        return

    def create_event(alert):
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(alert))
        ew.write_event(event)

    # Create events for the first page of results
    for alert in alerts:
        create_event(alert)

    # Handle pagination if more data exists
    while next_page_uri:
        try:
            alerts_res = get(next_page_uri, helper, headers=headers)
            alerts = alerts_res.json()["data"]
            next_page_uri = alerts_res.json().get('next_page_uri', None)
        except Exception as e:
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="as:internal", data=json.dumps({"error": str(e)}))
            ew.write_event(event)
            helper.log_info(f'Failed during pagination: {str(e)}')
            return

        for alert in alerts:
            create_event(alert)

    helper.log_info(f"Finished fetching alerts data for account ID: {account_id}")
