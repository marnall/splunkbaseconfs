# encoding = utf-8
import os
import sys
import time
import datetime
import json
from functools import wraps


def validate_input(helper, definition):
    pass


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
    res = helper.send_http_request(url, "get", parameters=params, headers=headers, use_proxy=True, timeout=15.0)
    res.raise_for_status()
    return res


def collect_events(helper, ew):
    TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

    global_api_key = helper.get_global_setting("api_key")
    main_account_id = helper.get_global_setting("account_id")
    helper.log_info("----------------------------------------------")
    helper.log_info("Fetching alerts")
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
        account_id = main_account_id
        account_name = main_account["name"]
        alerts_id_key = f"ADAPTIVE_ALERTS_ID-{account_id}"
        api_base_url = main_account["api_base_url"]
        helper.log_info(f'Account name: "{account_name}"')

        # use checkpoint to only fetch alerts generated after last alert
        last_id = helper.get_check_point(alerts_id_key)
        params = {"limit": 500, "ascending": True}

        if last_id:
            params["last_id"] = last_id

        alerts_url = f"{api_base_url}/accounts/{account_id}/alerts"
        alerts_res = get(alerts_url, helper, headers=headers, params=params)
        alerts = alerts_res.json()["data"]
        next_page_uri = alerts_res.json().get("next_page_uri", None)

    def create_event(alert_log):
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(alert))
        ew.write_event(event)

    page = 0
    helper.log_info(f"num of alerts - {len(alerts)}")
    for alert in alerts:
        create_event(alert)
    if alerts:
        last_id = alerts[-1]["id"]
        helper.save_check_point(alerts_id_key, last_id)
    while next_page_uri:
        page += 1
        if page >= 5:
            break
        alerts_res = get(next_page_uri, helper, headers=headers)
        alerts = alerts_res.json()["data"]
        helper.log_info(f"num of alerts - {len(alerts)}")
        next_page_uri = alerts_res.json().get("next_page_uri", None)
        for alert in alerts:
            create_event(alert)
        last_id = alerts[-1]["id"]
        helper.save_check_point(alerts_id_key, last_id)
    helper.log_info(f"Finished with {account_name}")

