""" Modular input for Automox device software """
# encoding = utf-8

from collections import OrderedDict
import json
from datetime import datetime
import requests


def validate_input(helper, definition): #pylint: disable=unused-argument
    """ Input validation """
    if definition.parameters["exclude_utd"] not in ["0", "1"]:
        raise ValueError("exclude_utd must be '0' or '1'")

def get_orgs(api_key):
    """ Retrieve list of organization IDs for use with packages endpoint"""
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

def get_devices(api_key, org_id):
    """ Retrieve devices for a given organization """
    headers = {"Authorization": "Bearer %s" % api_key}
    # Page length 50, starting with page 0
    params = {"l": 50,
              "p": 0,
              "o": org_id}

    devices = {}
    while True:
        response = requests.get("https://console.automox.com/api/servers",
                                headers=headers,
                                params=params)
        response.raise_for_status()
        devices_json = response.json()["results"]
        for device in devices_json:
            devices[device["id"]] = device["name"]

        if len(devices_json) < 50:
            break
        params["p"] += 1
    return devices

def get_software(api_key, org_id, device_id, exclude_utd):
    """ Retrieve software packages for a given device """
    headers = {"Authorization": "Bearer %s" % api_key}
    params = {"o": org_id}
    response = requests.get("https://console.automox.com/api/servers/%d/packages" % device_id,
                            params=params,
                            headers=headers)

    for package in response.json():
        if not package["installed"] or not exclude_utd:
            yield package

def collect_events(helper, ew): #pylint: disable=invalid-name
    """ Collect events """
    api_key = helper.get_global_setting("api_key")
    exclude_utd = helper.get_arg("exclude_utd")
    exclude_utd = exclude_utd in [1, "1", "true", True]

    timestamp = datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
    orgs = get_orgs(api_key)

    for org_id in orgs:
        devices = get_devices(api_key, org_id)
        for device in devices:
            for package in get_software(api_key, org_id, device, exclude_utd):
                event_dict = OrderedDict()
                event_dict['time'] = timestamp
                event_dict['server_name'] = devices[device]
                for field in package:
                    event_dict[field] = package[field]
                event = helper.new_event(source=helper.get_input_type(),
                                         index=helper.get_output_index(),
                                         sourcetype="automox:software",
                                         data=json.dumps(event_dict))
                ew.write_event(event)
