
# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json

def isCheckpoint(check_file, log):
    with open(check_file, 'r') as file:
        log_list = file.read().splitlines()
        return (log in log_list)

def write2Checkpoint(check_file, log):
    with open(check_file,'a') as file:
        file.writelines(log + '\n')

def write2Splunk(helper, ew, timestamp, data):
    data = json.dumps(data)
    timestamp = json.dumps(timestamp)
    event = helper.new_event(data, time=timestamp, host=None, done=True, unbroken=True)

    try:
        ew.write_event(event)
    except Exception as e:
        raise e

def getEvents(global_datadog_search_endpoint, headers, filters):
    response = requests.post(global_datadog_search_endpoint, headers=headers, data=filters)
    return response.json()

def validate_input(helper, definition):
    datadog_search_endpoint = definition.parameters.get('datadog_search_endpoint', None)
    datadog_api_key = definition.parameters.get('datadog_api_key', None)
    datadog_app_key = definition.parameters.get('datadog_app_key', None)
    time_preset = definition.parameters.get('time_preset', None)
    datadog_query = definition.parameters.get('datadog_query', None)

def collect_events(helper, ew):

    # get global variable configuration
    global_datadog_search_endpoint = helper.get_global_setting("datadog_search_endpoint")
    global_datadog_api_key = helper.get_global_setting("datadog_api_key")
    global_datadog_app_key = helper.get_global_setting("datadog_app_key")

    # get inputs variables configuration
    opt_time_preset = helper.get_arg('time_preset')
    opt_datadog_query = helper.get_arg('datadog_query')

    # Path para el archivo de checkpoint utilizado por eventos console
    check_file = os.path.join('/', os.path.dirname(os.path.abspath(__file__)), 'checkpoint', 'checkpointDD')

    headers = {
        'Content-Type': 'application/json',
    'DD-API-KEY': global_datadog_api_key,
    'DD-APPLICATION-KEY': global_datadog_app_key,
    }

    limit = "1000"
    filters = '{"filter": { "from": "now-'+opt_time_preset+'", "to": "now", "query": "'+opt_datadog_query+'" }, "page": { "limit": "'+limit+'" } }'

    getLogs = getEvents(global_datadog_search_endpoint, headers, filters)

    # Check data exists
    logsComing = len(getLogs["data"])

    # While data exists
    if logsComing > 0:
        for logs in getLogs["data"]:
                # Si no existe en el archivo de checkpoint, entonces guardo el contenido de "checkline" en el archivo
            logID = logs["id"]
            timestamp = logs["attributes"]["timestamp"]
            
            if not isCheckpoint(check_file, logID):
                write2Checkpoint(check_file, logID)

                write2Splunk(helper, ew, timestamp, logs)

        while logsComing > 0:
            after = json.dumps(getLogs["meta"]["page"]["after"])

            filters = '{"filter": { "from": "now-'+opt_time_preset+'", "to": "now", "query": "'+opt_datadog_query+'" }, "page": { "cursor": '+after+',"limit": "'+limit+'" } }'
            getLogs = getEvents(global_datadog_search_endpoint, headers, filters)

            for logs in getLogs["data"]:
                # Si no existe en el archivo de checkpoint, entonces guardo el contenido de "checkline" en el archivo
                logID = logs["id"]
                timestamp = logs["attributes"]["timestamp"]
                
                if not isCheckpoint(check_file, logID):
                    write2Checkpoint(check_file, logID)

                    write2Splunk(helper, ew, timestamp, logs)

            logsComing = len(getLogs["data"])
