# encoding = utf-8

import os
import sys
import time
import datetime
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
    global_api_key = helper.get_global_setting("api_key")
    main_account_id = helper.get_global_setting("account_id")
    helper.log_info("----------------------------------------------")
    helper.log_info(f"Fetching account data")
    headers = {"Authorization": f"token {global_api_key}"}
    accounts_url = "https://api.adaptive-shield.com/api/v1/accounts"
    accounts_res = helper.send_http_request(accounts_url, "get", headers=headers, use_proxy=True)
    if accounts_res.status_code == 403:
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="as:internal", data=json.dumps({"error": "invalid api key"}))
        ew.write_event(event)
        helper.log_info(f'Failed: Invalid API key')
        return
    accounts = accounts_res.json()["data"]
    try:
        [main_account] = [account for account in accounts if account['id'] == main_account_id]  # find main account
    except ValueError:
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="as:internal", data=json.dumps({"error": "invalid account id"}))
        ew.write_event(event)
        helper.log_info(f'Failed: Invalid account ID')
        return
    else:
        account_name = main_account['name']
        helper.log_info(f'Account name: "{account_name}"')
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(main_account))
        ew.write_event(event)
        helper.log_info(f"Finished with {account_name}")

