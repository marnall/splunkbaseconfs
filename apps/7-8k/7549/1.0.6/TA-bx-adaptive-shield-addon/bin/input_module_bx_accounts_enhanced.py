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
    # Fetch API key from input parameters
    api_key = helper.get_arg('api_key')  # Use input parameter for API key

    helper.log_info("----------------------------------------------")
    helper.log_info("Fetching accounts data")

    headers = {"Authorization": f"Token {api_key}"}
    accounts_url = "https://api.adaptive-shield.com/api/v1/accounts"
    
    # Fetch account data
    try:
        accounts_res = get(accounts_url, helper, headers=headers)
        accounts = accounts_res.json()["data"]
    except Exception as e:
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="as:internal", data=json.dumps({"error": str(e)}))
        ew.write_event(event)
        helper.log_info(f'Failed to fetch accounts: {str(e)}')
        return

    # Create events for each account
    for account in accounts:
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(account))
        ew.write_event(event)

    helper.log_info(f"Finished fetching account data for {len(accounts)} accounts")
