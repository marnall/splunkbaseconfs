
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
    check_point_key = "{}_insights".format(org_id)
    last_indexed_time = helper.get_check_point(check_point_key)


    # get last indexed time
    if last_indexed_time:
        start_time = last_indexed_time
    else:
        start_time = int((datetime.now() - timedelta(seconds=interval*2)).timestamp())
    end_time = int((datetime.now() - timedelta(seconds=interval)).timestamp())
    helper.log_info(f"Start running object count jobs: {org_id}/{start_time}:{end_time}")
    
    # start calling verkada vpublicapi
    cameras = get_cameras(helper, api_key)
    if cameras == None:
        helper.log_error(f"error getting cameraids from vpublicapi for org:{org_id}")
        helper.save_check_point(check_point_key, end_time)
        return
    
    for camera in cameras:
        object_counts = get_object_counts(helper, api_key, camera["camera_id"], start_time, end_time)
        if object_counts == None:
            helper.log_error(f'error getting object_counts from vpublicapi for camera:{camera["camera_id"]} under org:{org_id}')
            continue 
        
        for object_count in object_counts:
            object_count['camera_id'] = camera['camera_id']
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(),
                                     sourcetype=helper.get_sourcetype(), data=json.dumps(object_count))
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

def get_cameras(helper, api_key: str) -> dict:
    """
    Gets all cameras for an organization
    Args:
        org_id: Organization ID
        api_key: API Key of the organization
    Returns:
        Dictionary that contains every camera. Mapped with camera ID
    """
    cameras = []
    api_key_map = {'x-api-key':api_key}
    if not api_key.startswith("vkd_"):
        token = get_v2_token(helper, api_key)
        api_key_map = {'x-verkada-auth':token}

    proxies = get_proxy(helper, "requests")
    url = "https://api.verkada.com/cameras/v1/devices"
    paradict = {
        'headers':api_key_map,
        'params': {
            'page_size': 200,
        },
        'proxies':proxies
    }
    resp = retry(url, paradict)
    if isinstance(resp, list):
        helper.log_error(f"error calling get cameras, request error:{resp[-1]}")
        return None

    cameras.extend(resp.json()["cameras"])
    next_page_token = resp.json()["next_page_token"]
    while next_page_token:
        paradict = {
            'headers':api_key_map,
            'params': {
                'page_size': 200,
                'page_token': next_page_token,
            },
            'proxies':proxies
        }
        resp = retry(url, paradict)
        if isinstance(resp, list):
            helper.log_error(f"error calling get cameras, request error:{resp[-1]}")
            return None

        cameras.extend(resp.json()["cameras"])
        next_page_token = resp.json()["next_page_token"]
            
    return cameras


def get_object_counts(helper,
                      api_key: str,
                      camera_id: str,
                      start_time: int,
                      end_time: int) -> list:
    """
    Gets all notifications for the past minute and returns them as a list
    Args:
        org_id: Organization ID
        api_key: API Key of the organization
        camera_id: Id of the camera
        start_time: Start of time range
        end_time: End of time range

    Returns:
        List of dictionaries where each entry is a object_count
    """
    object_counts = []
    api_key_map = {'x-api-key':api_key}
    if not api_key.startswith("vkd_"):
        token = get_v2_token(helper, api_key)
        api_key_map = {'x-verkada-auth':token}
        
    proxies = get_proxy(helper, "requests")
    url = "https://api.verkada.com/cameras/v1/analytics/object_counts"
    paradict = {
        'headers':api_key_map,
        'params':{
            "camera_id": camera_id,
            "start_time": start_time,
            "end_time": end_time,
            "page_size": 200,
        },
        'proxies':proxies,
    }
    resp = retry(url, paradict)
    if isinstance(resp, list):
        helper.log_error(f"error calling get object counts: {url}/{camera_id}/{start_time}:{end_time}, request error:{resp[-1]}")
        return None
    
    object_counts.extend(resp.json()["object_counts"])
    next_page_token = resp.json()["next_page_token"]
    while next_page_token:
        paradict = {
            'headers':api_key_map,
            'params':{
                "camera_id": camera_id,
                "start_time": start_time,
                "end_time": end_time,
                "page_size": 200,
                "page_token": next_page_token,
            },
            'proxies':proxies,
        }
        resp = retry(url, paradict)
        if isinstance(resp, list):
            helper.log_error(f"error calling get object counts: {url}/{camera_id}/{start_time}:{end_time}, request error:{resp[-1]}")
            return None
        object_counts.extend(resp.json()["object_counts"])
        next_page_token = resp.json()["next_page_token"]
    return object_counts

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