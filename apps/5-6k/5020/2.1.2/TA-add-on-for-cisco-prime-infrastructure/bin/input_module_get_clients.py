
# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json

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
    # api_version = definition.parameters.get('api_version', None)
    max_results = definition.parameters.get('max_results', None)
    
    if int(max_results) > 1000 :
        raise ValueError(
            "Max results should be 1000 or less, not {}.".format(interval))

    pass


def send_request(url, auth_values, first, max_results, connection_type):
    
    parameters = {
        ".full": 'true',
        ".firstResult": first,
        ".maxResults": max_results,
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
    
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_global_account = helper.get_arg('global_account')
    opt_connection_type = helper.get_arg('connection_type')
    opt_max_results = helper.get_arg('max_results')
    # In single instance mode, to get arguments of a particular input, use
    opt_global_account = helper.get_arg('global_account', stanza_name)
    opt_connection_type = helper.get_arg('connection_type', stanza_name)
    opt_max_results = helper.get_arg('max_results', stanza_name)

    # get input type
    helper.get_input_type()

    # The following examples get input stanzas.
    # get all detailed input stanzas
    helper.get_input_stanza()
    # get specific input stanza with stanza name
    helper.get_input_stanza(stanza_name)
    # get all stanza names
    helper.get_input_stanza_names()

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    loglevel = helper.get_log_level()
    
    # The following examples show usage of logging related helper functions.
    # write to the log for this modular input using configured global log level or INFO as default
    helper.log("log message")
    # write to the log using specified log level
    helper.log_debug("log message")
    helper.log_info("log message")
    helper.log_warning("log message")
    helper.log_error("log message")
    helper.log_critical("log message")
    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    helper.set_log_level(log_level)
    """

    endpoint = helper.get_global_setting('endpoint')
    account = helper.get_arg('global_account')
    
    username = account['username']
    password = account['password']
    auth_values = (username, password)
    max_results = helper.get_arg('max_results')
    connection_type = helper.get_arg('connection_type')

    first = 0
    last = 1
    count = last
    url = 'https://' + endpoint + '/webacs/api/v4/data/Clients.json'
    content_type = 'clientsDTO'

    if 'max_results' in locals():
        max_results = max_results
    else:
        max_results = 100

    while first < count:
        response = send_request(url, auth_values, first,
                                max_results, connection_type)
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
                for client in entity:
                    data = json.dumps(client[content_type])
                    event = helper.new_event(source=helper.get_input_type(
                    ), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
                    ew.write_event(event)
        else:
            first = count
