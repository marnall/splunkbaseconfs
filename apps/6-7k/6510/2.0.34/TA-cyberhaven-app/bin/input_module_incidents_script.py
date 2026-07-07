# encoding = utf-8

import os
import sys
import base64
import random
import requests
import time
import json
import copy
from datetime import datetime, timedelta
import format_event

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

def current_time_ms():
    return round(time.time() * 1000)

now = current_time_ms()

# verify ssl certificate
VERIFY = True

AUTH_PATH = "/user-management/auth/token"
ALERTS_PATH = "/api/rest/v1/incidents/list"
PARSE_EVENT_CONFIG_PATH = "/api/rest/v1/splunk/config"

# HOST and AUTH

old_time = "2001-01-01T00:00:00Z"
nowTimeISO = datetime.utcnow().isoformat() + "Z"
EVENT_TIME_SORT = "event_time"
TRIGGER_TIME_SORT = "timestamp"
time_to_exec = 55_000

# incidents default request data
incidents_request_data = {
    # amount of entities to fetch
    "page_size": 500,
    "sort_desc": False,
    "sort_by": TRIGGER_TIME_SORT,
    "filters": {
        "times_filter": {
            "end_time": "2090-09-01T23:59:59Z",
            "time_field": "trigger_time",
            #             "start_time": nowTimeISO
        }
    }
}


def get_date_pagination_key():
    if incidents_request_data['sort_by'] == TRIGGER_TIME_SORT:
        return 'trigger_time'
    return 'event_time'

def is_finished():
    global now
    global time_to_exec
    return current_time_ms() - now >= time_to_exec


def authenticate_request(base64_creds, API_PATH, HOST, helper):
    """request to fetch auth token"""
    creds = None
    try:
        creds_json = base64.decodebytes(bytes(base64_creds, 'utf8'))
        creds = json.loads(creds_json)
    except:
        helper.log_error(
            "Auth token is not valid, make sure you copy/paste it as is from the dahboard /preferences/api-tokens page")
        raise ValueError("Auth token is not valid")
    r = requests.post(url=API_PATH + AUTH_PATH,
                      verify=VERIFY,
                      data=creds, headers={'HOST': HOST})
    r.raise_for_status()
    return r.content.decode("utf-8")


def incidents_request(token, start_time, size, search_after="", API_PATH="", helper=None):
    """
    request to fetch incidents
    token is authentication token returned by auth request
    page_id is pagination cursor
    """
    request_data = copy.deepcopy(incidents_request_data)
    request_data.update({'page_id': search_after, 'page_size': size})

    request_data["filters"]["times_filter"]["start_time"] = start_time or old_time

    if search_after:
        request_data["filters"]["times_filter"]["start_time"] = old_time

    auth_header = 'Bearer {}'.format(token)

    r = requests.post(url=API_PATH + ALERTS_PATH, json=request_data,
                      verify=VERIFY,
                      headers={'authorization': auth_header, 'content-type': 'application/json;;charset=UTF-8'})
    if r.status_code == 401:
        helper.log_error("Not authenticated")
    if r.status_code == 400 and incidents_request_data['sort_by'] == TRIGGER_TIME_SORT:
        incidents_request_data['sort_by'] = EVENT_TIME_SORT
        return incidents_request(token, start_time, size, search_after, API_PATH, helper)
    if r.status_code == 400 and incidents_request_data['sort_by'] == EVENT_TIME_SORT and request_data["filters"]["times_filter"]["time_field"]:
        request_data["filters"]["times_filter"]["time_field"] = ''
        return incidents_request(token, start_time, size, search_after, API_PATH, helper)
    if r.status_code >= 400:
        helper.log_info(r.text)
        exit(0)
    json_data = r.json()
    records = json_data.get("incidents", None)
    return {
        'alerts': records,
        'next_page_id': json_data.get('next_page_id', '')
    }


def config_request(token, API_PATH, helper):
    auth_header = 'Bearer {}'.format(token)
    r = requests.post(url=API_PATH + PARSE_EVENT_CONFIG_PATH, json={},
                      verify=VERIFY,
                      headers={'authorization': auth_header, 'content-type': 'application/json;;charset=UTF-8'})

    if r.status_code >= 400:
        helper.log_error("cannot load config " + r.text)
        return None

    json_res = r.json()
    return json_res.get('config')

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    host_url = definition.parameters.get('host_url', None)
    start_date = definition.parameters.get('start_date', None)

    try:
        datetime.strptime(start_date, "%d-%m-%Y-%H:%M:%S")
    except:
        raise ValueError(
            'Invalid start date, format should be DD-MM-YYYY-HH:MM:SS example: 01-01-2022-15:59:02')

    pass


def log_events(events, helper, ew, parse_schema):
    for event in events:
        data = json.dumps(format_event.format_event(event, parse_schema))
        event = helper.new_event(source=helper.get_input_type(
        ), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
        ew.write_event(event)


one_ms = timedelta(0, 0, 1000)

def parse_nano_date(str):
    arr = str.replace("Z", "").split(".")
    d = datetime.fromisoformat(arr[0])
    if (len(arr) > 1):
        msStr = arr[1]
        msStr = msStr + "0" * (6 - len(msStr))
        ms = int(msStr[0:6])
        d = d.replace(microsecond=ms)
    return d

def collect_events(helper, ew):
    global time_to_exec
    opt_host_url = helper.get_arg('host_url').replace(
        "https://", "").replace("http://", "").replace("/", "")  # replace https://
    opt_auth_token = helper.get_arg('auth_token')
    start_date_raw = helper.get_arg('start_date')
    interval = int(helper.get_arg('interval') or 60) * 1000

    time_to_exec = interval * 0.95

    start_date = datetime.strptime(
        start_date_raw, "%d-%m-%Y-%H:%M:%S").isoformat() + 'Z'
    start_time_key = 'start_time' + opt_host_url + start_date_raw
    search_after_key = 'search_after' + opt_host_url + start_date_raw

    API_PATH = "https://" + opt_host_url
    token = None
    try:
        token = authenticate_request(
            opt_auth_token, API_PATH, opt_host_url, helper)
    except Exception as err:
        helper.log_error("Cannot authenticate request")
        raise err

    parse_schema = config_request(token, API_PATH, helper)

    while True:
        start_time = helper.get_check_point(start_time_key)
        search_after = helper.get_check_point(search_after_key)

        # START_DATE
        events = incidents_request(token, start_time or start_date, size=500,
                                   search_after=search_after, API_PATH=API_PATH, helper=helper)
        alerts = events["alerts"]

        if len(alerts) == 0 or is_finished():
            # helper.delete_check_point('start_time')
            # helper.delete_check_point('search_after')
            break

        helper.log_info(parse_nano_date(
            alerts[-1][get_date_pagination_key()]) + one_ms)

        if not start_time:
            d = parse_nano_date(alerts[-1][get_date_pagination_key()]) + one_ms
            result_date = d.isoformat() + "Z"
            helper.save_check_point(start_time_key, result_date)

        if events["next_page_id"] == '':
            # take date, remove Z at the end and add one second and then bring back Z at the end
            # api and python iso formats are different
            # in case we reached end of the list we want to store time of last event and use it in order to continue pagination
            d = parse_nano_date(alerts[-1][get_date_pagination_key()]) + one_ms
            result_date = d.isoformat() + "Z"
            helper.save_check_point(start_time_key, result_date)
            helper.save_check_point(search_after_key, events["next_page_id"])
        else:
            helper.save_check_point(start_time_key, start_time)
            helper.save_check_point(search_after_key, events["next_page_id"])

        log_events(alerts, helper, ew, parse_schema)

