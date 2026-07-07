""" Modular input for Automox device info """
# encoding = utf-8

from collections import OrderedDict
import json
from datetime import datetime
import requests


def validate_input(helper, definition): #pylint: disable=unused-argument
    """ Input validation """
    if definition.parameters["pending_patches"] not in ["yes", "no", "both"]:
        raise ValueError("pending_patches must be 'yes', 'no', or 'both'")
    if definition.parameters["exclude_patched_devices"] not in ["0", "1"]:
        raise ValueError("exclude_patched_devices must be '0' or '1'")
    if definition.parameters["exclude_exceptions"] not in ["0", "1"]:
        raise ValueError("exclude_exceptions must be '0' or '1'")

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

def get_devices(api_key, org_id, pending_patches, exclude_patched_devices,
                exclude_exceptions):
    """ Retrieve devices for a given organization """
    headers = {"Authorization": "Bearer %s" % api_key}
    # Page length 50, starting with page 0
    params = {"l": 50,
              "p": 0,
              "o": org_id}
    if pending_patches == "yes":
        params["pending"] = 1
    elif pending_patches == "no":
        params["pending"] = 0
    elif pending_patches == "both":
        pass

    if exclude_patched_devices:
        params["patchStatus"] = "missing"

    if exclude_exceptions:
        params["exception"] = 0

    while True:
        response = requests.get("https://console.automox.com/api/servers",
                                headers=headers,
                                params=params)
        response.raise_for_status()
        devices = response.json()["results"]
        for device in devices:
            yield device

        if len(devices) < 50:
            break
        params["p"] += 1


def collect_events(helper, ew): #pylint: disable=invalid-name
    """ Collect events """
    api_key = helper.get_global_setting("api_key")
    pending_patches = helper.get_arg("pending_patches")
    exclude_patched_devices = helper.get_arg("exclude_patched_devices")
    exclude_exceptions = helper.get_arg("exclude_exceptions")

    timestamp = datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
    orgs = get_orgs(api_key)

    for org_id in orgs:
        groups = get_server_groups(api_key, org_id)
        for device in get_devices(api_key, org_id, pending_patches,
                                  exclude_patched_devices, exclude_exceptions):
            event_dict = OrderedDict()
            event_dict['time'] = timestamp
            for field in device:
                event_dict[field] = device[field]
                if field == "organization_id" and device[field] in orgs.keys():
                    event_dict["organization"] = orgs[device[field]]
                if field == "server_group_id" and device[field] in groups.keys():
                    event_dict["server_group"] = groups[device[field]]
            event = helper.new_event(source=helper.get_input_type(),
                                     index=helper.get_output_index(),
                                     sourcetype="automox:devices",
                                     data=json.dumps(event_dict))
            ew.write_event(event)
