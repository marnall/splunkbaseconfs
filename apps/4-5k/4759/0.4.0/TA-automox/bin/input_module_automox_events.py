""" Modular input for Automox events """
# encoding = utf-8

from collections import OrderedDict
import json
from datetime import datetime
from datetime import timedelta
import requests


def validate_input(helper, definition): #pylint: disable=unused-argument
    """ Input validation """
    return

def get_orgs(api_key):
    """ Retrieve list of organization IDs for use with devices endpoint"""
    headers = {"Authorization": "Bearer %s" % api_key}
    response = requests.get("https://console.automox.com/api/orgs",
                            headers=headers)
    response.raise_for_status()
    orgs = {}
    for org in response.json():
        org_id = org["id"]
        name = org["name"]
        orgs[org_id] = name
    return orgs

def get_server_groups(api_key, org_id):
    """ Retrieve server groups. Used to resolve server group ID in events """
    headers = {"Authorization": "Bearer %s" % api_key}
    response = requests.get("https://console.automox.com/api/servergroups",
                            headers=headers,
                            params={"o": org_id})
    response.raise_for_status()
    groups = {}
    for group in response.json():
        group_id = group["id"]
        name = group["name"]
        groups[group_id] = name
    return groups

def get_events(checkpoint, api_key, org_id):
    """ Retrieve events """
    headers = {"Authorization": "Bearer %s" % api_key}
    end_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    params = {"startDate": checkpoint,
              "endDate": end_date,
              "o": org_id}
    response = requests.get("https://console.automox.com/api/events",
                            headers=headers,
                            params=params)
    response.raise_for_status()
    events = response.json()
    return events


def collect_events(helper, ew): #pylint: disable=invalid-name
    """ Collect events """
    api_key = helper.get_global_setting("api_key")
    checkpoint = helper.get_check_point("automox_events")
    if not checkpoint:
        checkpoint = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")
    if checkpoint == (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d"):
        return
    orgs = get_orgs(api_key)

    for org_id in orgs:
        events = get_events(checkpoint, api_key, org_id)

        for event in events:
            event_dict = OrderedDict()
            event_dict["create_time"] = event["create_time"]
            for field in event:
                event_dict[field] = event[field]
            event = helper.new_event(source=helper.get_input_type(),
                                     index=helper.get_output_index(),
                                     sourcetype="automox:events",
                                     data=json.dumps(event_dict))
            ew.write_event(event)
    helper.save_check_point("automox_events",
                            (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d"))
