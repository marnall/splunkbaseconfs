import requests
import csv
import datetime
import gzip
import json
import urllib3
import sys
# Supress Cert warning for local Splunk REST calls
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

valid_actions =  ["pause", "unpause", "finalize", "cancel", "touch", "setttl", "setpriority", "enablepreview", "disablepreview", "setworkloadpool","save","unsave"]



def manage(payload, row):
    configuration = payload['configuration']
    action=""
    argument = ""
    headers = {}
    headers['Authorization'] = "Bearer {}".format(payload['session_key'])
    if "action" in row and len(row['action']) > 0:
        action = row['action']
        argument = row.get('argument')
    elif "action" in configuration:
        action = configuration['action']
        argument = configuration.get('argument')
    else:
        return False

    if action in valid_actions:
        body = {}
        if action in ["setttl","setpriority","setworkloadpool"]:
            if action == "setttl":
                body['ttl'] = argument
            elif action == "setpriority":
                body['priority'] = argument
            elif action == "setworkloadpool":
                body['workload_pool'] = argument
        body['action'] = action
        res = requests.post("{}/services/search/jobs/{}/control".format(payload['server_uri'], row['sid'] ), headers=headers, data=body, verify=False)
        return True
    else:
        raise Exception("action '{}' not in {}".format(action,valid_actions))

if len(sys.argv) > 1 and sys.argv[1] == "--execute":
    payload = json.load(sys.stdin)    
    configuration = payload['configuration']
    results = payload['result']

    if "sid" not in results:
        raise Exception("ERROR No sid field in results")
    with gzip.open(payload['results_file'], 'rt', newline='') as results_file:
        results = csv.DictReader(results_file)
        for row in results:
            if "sid" in row:
                manage(payload, row)
            else:
                raise KeyError(row.keys())


