
# encoding = utf-8

import os
import sys
from time import time
from datetime import datetime
from requests.adapters import HTTPAdapter
import os.path
from os import path
import base64

import requests, json
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning
from io import open
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

limit = str(100)
presentIndex = str(1)
sortColumn = 'hostname'
sortDirection = 'asc'

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass

def collect_events(helper, ew):
    PRESETS=None

    # get global variable configuration
    base_url = helper.get_global_setting("spectrum_url")
    token = helper.get_global_setting("api_token")
    tenant = helper.get_global_setting("tenant_name")

    splunk_app_url = os.environ.get("SPLUNK_HOME")
    CONFIG_PATH = splunk_app_url + "/etc/apps/TA-XProtect/xprotect.conf"
    PRESET_FILE = splunk_app_url + "/etc/apps/TA-XProtect/xprotect_hosts.conf"
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

    f = open(PRESET_FILE, "w")
    PRESETS = { "startIndex": presentIndex }
    f.write(json.dumps(PRESETS))
    f.close()

    done = 0
    total = 1
    if base_url.startswith('https'): 
        url = base_url + '/public/api/v1/'+ tenant + '/resources?limit='+limit+'&startIndex='+presentIndex+'&sortColumn='+sortColumn+'&sortDirection='+sortDirection
        helper.log_debug(">>>> URL = " + url)
        s = requests.Session()
        retries = Retry(total=10, backoff_factor=1, status_forcelist=[ 500, 502, 503, 504 ])
        s.mount('https://', HTTPAdapter(max_retries=retries))
        r = s.get(url = url, headers={'x-api-token': token}, verify=CA_CERT,cert=cert)

    
    while done < total:
        if "pagination" in list(r.json().keys()):
            page_info = r.json()['pagination']
            helper.log_debug("PAGINATION_INFO: " + json.dumps(page_info))
            startIndex = page_info['startIndex']
            total = page_info['total']
            itemCount = r.json()['itemCount']
            if "items" in list(r.json().keys()):
                    event = helper.new_event(data=json.dumps(r.json()['items']), source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
                    ew.write_event(event)
                    done = done + itemCount
                    f = open(PRESET_FILE, "w")
                    PRESETS['url'] = url
                    PRESETS['startIndex'] = startIndex
                    PRESETS['total'] = total
                    PRESETS['done'] = done
                    f.write(json.dumps(PRESETS))
                    f.close()
                    index = str(startIndex+1)
                    helper.log_debug("DONE :: " + str(done) + ", TOTAL = " + str(total))
                    if base_url.startswith('https'): 
                        url = base_url + '/public/api/v1/'+ tenant + '/resources?limit='+limit+'&startIndex='+index+'&sortColumn='+sortColumn+'&sortDirection='+sortDirection
                        helper.log_debug(">>>> URL = " + url)
                        r = s.get(url = url, headers={'x-api-token': token}, verify=CA_CERT,cert=cert)
            else:
                    helper.log_debug("EXITING-NO-ITEMS " + json.dumps(r.json()))
                    total = -1
        else:
            helper.log_debug("NO PAGINATION INFO IN RESPONSE")
            total = -1
            if "items" in list(r.json().keys()):
                event = helper.new_event(data=json.dumps(r.json()['items']), source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
                ew.write_event(event)


