
# encoding = utf-8

import os
import sys
from time import time
import datetime
from pathlib import Path
import requests, json
from urllib3.exceptions import InsecureRequestWarning
from io import open
import base64
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass

def collect_events(helper, ew):
    
    # get global variable configuration
    base_url = helper.get_global_setting("spectrum_url")
    token = helper.get_global_setting("api_token")
    tenant = helper.get_global_setting("tenant_name")

    splunk_app_url = os.environ.get("SPLUNK_HOME")
    CONFIG_PATH = splunk_app_url + "/etc/apps/TA-XProtect/xprotect.conf"
    CA_CERT = splunk_app_url + "/etc/apps/TA-XProtect/crts/ca.pem"
    KEY_CERT = splunk_app_url + "/etc/apps/TA-XProtect/crts/key.pem"
    cert=(CA_CERT,KEY_CERT)

    base64_bytes_tenant = tenant.encode("ascii")
    base64_bytes_tokens = token.encode("ascii")
    encoded_tenant = base64.b64encode(base64_bytes_tenant)
    encoded_token = base64.b64encode(base64_bytes_tokens)

    f = open(CONFIG_PATH, "w")
    f.write(base_url    +'|')
    f.write(str(encoded_token)  +'|')
    f.write(str(encoded_tenant))
    f.close()

    if base_url.startswith('https'): 
        r = requests.get(url = base_url + '/public/api/v1/'+ tenant + '/statistics',
                    headers={'x-api-token': token}, verify=CA_CERT,cert=cert)

    if "items" in list(r.json().keys()):
        event = helper.new_event(data=json.dumps(r.json()['items']), source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
        ew.write_event(event)

