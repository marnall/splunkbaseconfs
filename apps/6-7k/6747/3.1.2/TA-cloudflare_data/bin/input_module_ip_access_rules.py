
# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input,
uncomment this method.
def use_single_instance_mode():
    return True
'''


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza
    configurations
    """
    # This example accesses the modular input variable
    # checkbox = definition.parameters.get('checkbox', None)
    pass


def get_zones(auth_email, auth_key):

    try:
        response = requests.get(
            url='https://api.cloudflare.com/client/v4/zones/',
            params={
                "match": 'all',
            },
            headers={
                "X-Auth-Email": auth_email,
                "X-Auth-Key": auth_key,
                "Content-Type": "application/json",
            },
        )
        zones = response.content
    except requests.exceptions.RequestException:
        print('HTTP Request failed')
    return zones


def get_rules(zone_id, auth_email, auth_key, parameters):

    try:
        response = requests.get(
            url='https://api.cloudflare.com/client/v4/zones/' +
            zone_id + '/firewall/access_rules/rules',
            params=parameters,
            headers={
                "X-Auth-Email": auth_email,
                "X-Auth-Key": auth_key,
                "Content-Type": "application/json",
            },
        )
        rules = response.content
    except requests.exceptions.RequestException:
        print('HTTP Request failed')
    return rules


def collect_events(helper, ew):

    # get global variable configuration
    auth_key = helper.get_global_setting('x_auth_key')
    auth_email = helper.get_global_setting('x_auth_email')
    mode = helper.get_arg('mode')

    if mode == "all":
        parameters = {
            "per_page": 100
        }
    else:
        parameters = {
            "per_page": 100,
            "mode": mode,
            "match": "any"
        }

    response = get_zones(auth_email, auth_key)
    zones = json.loads(response)
    for zone in zones["result"]:
        zone_id = zone["id"]
        zone_name = zone["name"]
        response = get_rules(zone_id, auth_email, auth_key, parameters)
        rules = json.loads(response)
        for rule in rules["result"]:
            rule = json.dumps(rule)
            event = helper.new_event(source=zone_name,
                                     index=helper.get_output_index(),
                                     sourcetype=helper.get_sourcetype(),
                                     data=rule)
            ew.write_event(event)
