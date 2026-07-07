
# encoding = utf-8

import os
import sys
import time
import requests
import json
from datetime import date, timedelta, datetime

requests.packages.urllib3.disable_warnings()

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
    # global_account = definition.parameters.get('global_account', None)
    # connection_type = definition.parameters.get('connection_type', None)
    # max_results = definition.parameters.get('max_results', None)
    max_results = definition.parameters.get('max_results', None)
    
    if int(max_results) > 1000 :
        raise ValueError(
            "Max results should be 1000 or less, not {}.".format(interval))

    pass


def send_request(url, auth_values, first, connection_type, max_results, interval):

    d = (datetime.utcnow() - timedelta(seconds=interval)).strftime('%s.%f')
    ts = str(int(float(d)*1000))
    
    parameters = {
        ".full": 'true',
        ".firstResult": first,
        ".maxResults": max_results,
        "sessionStartTime": "gt(\"" + ts + "Z\")",
    }
    if connection_type != "ALL":
        parameters['connectionType'] = connection_type

    try:
        response = requests.get(
            url=url,
            params=parameters,
            auth=auth_values,
            headers={
                "Content-Type": "application/json",
            },
            verify=False,
        )
        results = json.loads(response.text)
        return results
    except requests.exceptions.RequestException:
        print('HTTP Request failed')
        

def collect_events(helper, ew):
    # Implement your data collection logic here

    
    # get global variable configuration
    account = helper.get_arg('global_account')
    endpoint = helper.get_global_setting('endpoint')
    
    username = account['username']
    password = account['password']
    auth_values = (username, password)
    connection_type = helper.get_arg('connection_type')
    max_results = helper.get_arg('max_results')
    interval = 3600

    first = 0
    last = 1
    count = last
    url = 'https://' + endpoint + '/webacs/api/v4/data/ClientSessions.json'
    content_type = 'clientSessionsDTO'

    if 'max_results' in locals():
        max_results = max_results
    else:
        max_results = 100
        
    while first < count:
        response = send_request(url, auth_values, first, connection_type, max_results, interval)
        if "queryResponse" in response:
            response = response['queryResponse']
            if "@count" in response:
                count = response['@count']
            if "@last" in response:
                last = response['@last']
                first = int(last) + 1
            else:
                first = count
            if "entity" in response:
                entity = response['entity']
                for clientsession in entity:
                    data = json.dumps(clientsession[content_type])
                    event = helper.new_event(source=helper.get_input_type(
                    ), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
                    ew.write_event(event)
        else:
            first = count
    
