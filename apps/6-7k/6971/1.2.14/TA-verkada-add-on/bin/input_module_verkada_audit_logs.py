
# encoding = utf-8

import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # organization_id = definition.parameters.get('organization_id', None)
    # api_key = definition.parameters.get('api_key', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""
    
    # get args from input setting
    org_id = helper.get_arg('organization_id')
    api_key = helper.get_arg('api_key')
    interval = int(helper.get_arg('interval'))
    check_point_key = "{}_audit_logs".format(org_id)
    last_indexed_time = helper.get_check_point(check_point_key)

    # get last indexed time
    if last_indexed_time:
        start_time = last_indexed_time
    else:
        start_time = int((datetime.now() - timedelta(seconds=interval*2)).timestamp())
    end_time = int((datetime.now() - timedelta(seconds=interval)).timestamp())

    seconds_of_30_min = 60 * 30
    query_start_time, query_end_time = start_time - seconds_of_30_min, end_time - seconds_of_30_min
    helper.log_info(f"Start running audit log jobs: {org_id}/{query_start_time}:{query_end_time}")
    
    # start calling verkada vpublicapi
    audit_logs = get_audit_logs(helper, api_key, query_start_time, query_end_time)
    if audit_logs == None:
        helper.log_error(f"error getting audit_logs from vpublicapi for org:{org_id}")
        helper.save_check_point(check_point_key, end_time)
        return

    for audit_log in audit_logs:
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(),
                                 sourcetype=helper.get_sourcetype(), data=json.dumps(audit_log))
        ew.write_event(event)
    helper.save_check_point(check_point_key, end_time)


def get_v2_token(helper, api_key:str) -> str:
    url = "https://api.verkada.com/token"
    headers = {
        "content-type": "application/json",
        "x-api-key": api_key
    }

    for i in range(3):
        try:
            response = requests.post(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                token = data.get('token')
                return token
            else:
                error_message = f"Unexpected status code {response.status_code} on attempt {i + 1}"
                error_messages.append(error_message)
        except requests.exceptions.HTTPError as e:
            error_message = f"HTTP error on attempt {i + 1}: {e}"
            error_messages.append(error_message)
        except requests.exceptions.ConnectionError as e:
            error_message = f"Connection error on attempt {i + 1}: {e}"
            error_messages.append(error_message)
        except requests.exceptions.Timeout as e:
            error_message = f"Timeout error on attempt {i + 1}: {e}"
            error_messages.append(error_message)
        except requests.exceptions.TooManyRedirects as e:
            error_message = f"Too many redirects on attempt {i + 1}: {e}"
            error_messages.append(error_message)
        time.sleep(3)
            
    helper.log_error(f"error getting v2 token for api key:{api_key}, error:{error_messages[-1]}")
    return None

def get_audit_logs(
    helper, api_key: str, start_time: int, end_time: int
) -> list:
    """
    Gets all audit_logs for the past minute and returns them as a list
    Args:
        org_id: Organization ID
        api_key: API Key of the organization
        notification_types: Types of audit_logs to look for

    Returns:
        List of dictionaries where each entry is a notification
    """
    api_key_map = {'x-api-key':api_key}
    if not api_key.startswith("vkd_"):
        token = get_v2_token(helper, api_key)
        api_key_map = {'x-verkada-auth':token}

    proxies = get_proxy(helper, "requests")
    url = "https://api.verkada.com/core/v1/audit_log"
    paradict = {
        'headers':api_key_map,
        'params':{
            "start_time": start_time,
            "end_time": end_time,
            "use_processed_timestamp": True,
            "page_size": 200,
        },
        'proxies':proxies,
    }

    resp = retry(url, paradict)
    if isinstance(resp, list):
        helper.log_error(f"error calling get audit_logs: {url}/{start_time}:{end_time}, request error:{resp[-1]}")
        return None
    audit_logs: list = resp.json()["audit_logs"]
    next_page_token = resp.json()["next_page_token"]
    while next_page_token:
        paradict = {
            'headers':api_key_map,
            'params':{
                "start_time": start_time,
                "end_time": end_time,
                "use_processed_timestamp": True,
                "page_size": 200,
                "page_token": next_page_token,
            },
            'proxies':proxies,
        }
        resp = retry(url, paradict)
        if isinstance(resp, list):
            helper.log_error(f"error calling get audit_logs: {url}/{start_time}:{end_time}, request error:{resp[-1]}")
            return None
        
        audit_logs.extend(resp.json()["audit_logs"])
        next_page_token = resp.json()["next_page_token"]
        
    return audit_logs


def retry(url, paradict, retries=5, backoff=1):
    error_messages = []
    for i in range(retries):
        try:
            response = requests.get(url, **paradict)
            if response.status_code == 200:
                return response
            else:
                error_message = f"Unexpected status code {response.status_code} on attempt {i + 1}"
                error_messages.append(error_message)
        except requests.exceptions.HTTPError as e:
            error_message = f"HTTP error on attempt {i + 1}: {e}"
            error_messages.append(error_message)
        except requests.exceptions.ConnectionError as e:
            error_message = f"Connection error on attempt {i + 1}: {e}"
            error_messages.append(error_message)
        except requests.exceptions.Timeout as e:
            error_message = f"Timeout error on attempt {i + 1}: {e}"
            error_messages.append(error_message)
        except requests.exceptions.TooManyRedirects as e:
            error_message = f"Too many redirects on attempt {i + 1}: {e}"
            error_messages.append(error_message)
        time.sleep(backoff * (2 ** i))
        
    return error_messages

def get_proxy(helper, proxy_type="requests"):
    proxies = None
    helper.log_debug("_Splunk_ Getting proxy server.")
    proxy = helper.get_proxy()

    if proxy:
        helper.log_debug("_Splunk_ Proxy is enabled: %s:%s" % (proxy["proxy_url"], proxy["proxy_port"]))
        if proxy_type.lower() == "requests":
            proxy_url = "%s:%s" % (proxy["proxy_url"], proxy["proxy_port"])
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }
        elif proxy_type.lower() == "event hub":
            proxies = {
                'proxy_hostname': proxy["proxy_url"],
                'proxy_port': int(proxy["proxy_port"]),
                'username': proxy["proxy_username"],
                'password': proxy["proxy_password"]
            }

    return proxies
