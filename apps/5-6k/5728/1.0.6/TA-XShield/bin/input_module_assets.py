# encoding = utf-8

import os
import sys
import time
import datetime
import base64

import requests, json
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # tenant_name = definition.parameters.get('tenant_name', None)
    pass

def collect_events(helper, ew):
    
     # get global variable configuration
    _url = helper.get_global_setting("spectrum_url")
    _token = helper.get_global_setting("api_token")
    _tenant = helper.get_global_setting("tenant_name")

    splunk_app_url = os.environ.get("SPLUNK_HOME")
    CONFIG_PATH = splunk_app_url + "/etc/apps/TA-XShield/xshield.conf"
    CA_CERT = splunk_app_url + "/etc/apps/TA-XShield/crts/ca.pem"
    KEY_CERT = splunk_app_url + "/etc/apps/TA-XShield/crts/key.pem"
    cert=(CA_CERT,KEY_CERT)

    base64_bytes_tenant = _tenant.encode("ascii")
    base64_bytes_tokens = _token.encode("ascii")
    encoded_tenant = base64.b64encode(base64_bytes_tenant)
    encoded_token = base64.b64encode(base64_bytes_tokens)

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
    
    API_PATH='assets'
    
    page = 1
    total_pages = 1
    records_per_page=100
    
    headers = {
      'x-api-token': f"{API_CLIENT_TOKEN}"
    }
     
    while(page <= total_pages):
        if "https" in HOST_NAME: 
          url = f"{HOST_NAME}/public/api/v1/{TENANT_NAME}/{API_PATH}?limit={records_per_page}&page={page}"
          response = requests.request("GET", url, headers=headers,verify=CA_CERT,cert=cert)
          responseJson = response.json()
          total_pages = responseJson['pagination']['totalPages']
          assets = responseJson['data']
          for asset in assets:
              if helper.get_check_point(asset['id']):
                   helper.log_debug(asset['id'] + " Id already present in the checkpoint")
              else:
                event = helper.new_event(data=json.dumps(asset), source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
                ew.write_event(event)
                helper.save_check_point(asset['id'], 'Y')
          page = page + 1
