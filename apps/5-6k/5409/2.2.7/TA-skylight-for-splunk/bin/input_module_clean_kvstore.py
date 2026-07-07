
# encoding = utf-8

import os
import sys
import time
import json
import requests
import datetime
from requests.auth import HTTPBasicAuth
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    session_key = helper.context_meta['session_key']

    headers = {"Authorization": "Splunk {}".format(session_key), "Content-Type": "application/json"}
    
    ntime = int(time.time()) - (60*60*24)*30
    p = {"query":"{\"result._time\":{\"$lt\":\"" + str(ntime) + "\"}}", "fields":"id,result._time"}
    
    ip = "127.0.0.1"
    r = requests.get("https://{}:8089/servicesNS/nobody/skylight_security_for_splunk/storage/collections/data/incident_results".format(ip), params=p, verify=False, headers=headers)
    
    j = json.loads(r.text)
    for item in j:
        r = requests.delete("https://{}:8089/servicesNS/nobody/skylight_security_for_splunk/storage/collections/data/incident_results/{}".format(ip, item["id"]), params=p, verify=False, headers=headers)
