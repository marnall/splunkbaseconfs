# encoding = utf-8
import os
import sys
import time
import datetime
import json
from functools import wraps

def retry(ExceptionToCheck, tries=5, delay=3, backoff=2):
    # retry decorator
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
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
    res = helper.send_http_request(url, "get", parameters=params, headers=headers, use_proxy=True, timeout=15.0)
    res.raise_for_status()
    return res

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    # Fetch API key and account ID from input parameters
    api_key = helper.get_arg('api_key')  # Use input parameter
    account_id = helper.get_arg('account_id')  # Use input parameter

    # Set headers and base URL
    headers = {"Authorization": f"token {api_key}"}
    security_checks_url = f"https://api.adaptive-shield.com/api/v1/accounts/{account_id}/security_checks"
    
    params = {"limit": 500}  # Adjust limit as needed
    helper.log_info(f"Fetching security checks for account ID: {account_id}")
    
    # Fetch the first page of security checks
    security_checks_res = get(security_checks_url, helper, headers=headers, params=params)
    security_checks = security_checks_res.json()['data']
    next_page_uri = security_checks_res.json().get('next_page_uri', None)

    def create_event(security_check):
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(security_check))
        ew.write_event(event)

    # Create events for the first page of results
    for security_check in security_checks:
        create_event(security_check)

    # Handle pagination
    while next_page_uri:
        security_checks_res = get(next_page_uri, helper, headers=headers)
        security_checks = security_checks_res.json()['data']
        next_page_uri = security_checks_res.json().get('next_page_uri', None)
        for security_check in security_checks:
            create_event(security_check)

    helper.log_info(f'Finished fetching security checks for account ID: {account_id}')
