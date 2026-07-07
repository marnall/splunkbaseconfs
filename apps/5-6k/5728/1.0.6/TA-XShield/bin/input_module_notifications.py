# encoding = utf-8

import os
import sys
import datetime
from pathlib import Path
from time import time
import requests, json
import base64
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # tenant_name = definition.parameters.get('tenant_name', None)
    pass

def collect_events(helper, ew):
    
    _lte = int(time() * 1000)
    _gte = _lte - int(30 * 24 * 60 * 60 * 1000)
    
     # get global variable configuration
    _url = helper.get_global_setting("spectrum_url")
    _token = helper.get_global_setting("api_token")
    _tenant = helper.get_global_setting("tenant_name")
    
    splunk_app_url = os.environ.get("SPLUNK_HOME")
    CONFIG_PATH = splunk_app_url + "/etc/apps/TA-XShield/xshield.conf"
    PRESET_FILE = splunk_app_url + "/etc/apps/TA-XShield/xshield_alerts.conf"
    CA_CERT = splunk_app_url + "/etc/apps/TA-XShield/crts/ca.pem"
    KEY_CERT = splunk_app_url + "/etc/apps/TA-XShield/crts/key.pem"
    cert=(CA_CERT,KEY_CERT)
    
    if Path(PRESET_FILE).is_file():
        f = open (PRESET_FILE, "r")
        if os.path.getsize(PRESET_FILE) > 0 :
             data = json.loads(f.read())
             _gte=data['lte']
             f.close()
        
    
    lte = str(_lte)
    gte = str(_gte)

    base64_bytes_tenant = _tenant.encode("ascii")
    base64_bytes_token = _token.encode("ascii")
    encoded_tenant = base64.b64encode(base64_bytes_tenant)
    encoded_token = base64.b64encode(base64_bytes_token)

    f = open(CONFIG_PATH, "w")
    f.write(_url    +'|')
    f.write(str(encoded_token)  +'|')
    f.write(str(encoded_tenant))
    f.close()
    
    # Name of the tenant Example: mycompany
    TENANT_NAME=_tenant
    
    #Spectrum hostname. Example: mycompany.spectrum.colortokens.com
    HOST_NAME=_url
    
    # API Client Token generated from API Manager
    API_CLIENT_TOKEN=_token
    
    API_PATH='alerts/splunk'
    
    page = 1
    total_pages = 1
    records_per_page=100
    
    headers = {
      'x-api-token': f"{API_CLIENT_TOKEN}"
    }
    
    done = 0
    total = 1
    while(page <= total_pages):
      if "https" in HOST_NAME: 
         url = f"{HOST_NAME}/public/api/v1/{TENANT_NAME}/{API_PATH}?limit={records_per_page}&page={page}"
         helper.log_debug(">>>> URL = " + url)
         response = requests.request("GET", url, headers=headers, verify=CA_CERT, cert=cert)
         responseJson = response.json()
         page_info = responseJson['pagination']
         helper.log_debug("PAGINATION_INFO: " + json.dumps(page_info))
         total_pages = page_info['totalPages']
         total = page_info['totalElements']
         notifications = responseJson['data']
         for notification in notifications:
            if helper.get_check_point(notification['id']) is None:
                event = helper.new_event(data=json.dumps(notification), source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
                ew.write_event(event)
                helper.save_check_point(notification['id'], 'Y')
         page = page + 1
         done = done + 100
         helper.log_debug("DONE :: " + str(done) + ", TOTAL = " + str(total))
    
    if done >= total:
        helper.log_debug(">>>> STORING PRESESTS")
        f = open(PRESET_FILE, "w")
        PRESETS = { "gte": _gte, "lte": _lte }
        f.write(json.dumps(PRESETS))
    else:
        helper.log_debug(">>>> OLD PRESESTS RETAINED")

