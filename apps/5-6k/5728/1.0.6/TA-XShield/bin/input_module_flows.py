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
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

limit = str(5000)

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass

def collect_events(helper, ew):
    _lte = int(time() * 1000)
    lte = str(_lte - int(60 * 10 * 1000))
    PRESETS=None
    # get global variable configuration
    base_url = helper.get_global_setting("spectrum_url")
    token = helper.get_global_setting("api_token")
    tenant = helper.get_global_setting("tenant_name")

   
    splunk_app_url = os.environ.get("SPLUNK_HOME")
    CONFIG_PATH = splunk_app_url + "/etc/apps/TA-XShield/xshield.conf"
    PRESET_FILE = splunk_app_url + "/etc/apps/TA-XShield/xshield_flows.conf"
    CA_CERT = splunk_app_url + "/etc/apps/TA-XShield/crts/ca.pem"
    KEY_CERT = splunk_app_url + "/etc/apps/TA-XShield/crts/key.pem"
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

    gte = str(_lte - int(60 * 20 * 1000))
    f = open(PRESET_FILE, "w")
    PRESETS = { "gte": gte, "lte": lte }
    f.write(json.dumps(PRESETS))
    f.close()
        
    done = 0
    total = 1
    if "https" in base_url: 
      url = base_url + '/public/api/v1/' + tenant + '/analytics/flows?gte='+gte+'&lte='+lte+'&limit='+limit
      helper.log_debug(">>>> URL = " + url)
      s = requests.Session()
      retries = Retry(total=10, backoff_factor=1, status_forcelist=[ 500, 502, 503, 504 ])
      s.mount('https://', HTTPAdapter(max_retries=retries))
      r = s.get(url = url, headers={'x-api-token': token}, verify=CA_CERT,cert=cert)
    
    eventsArray = []
    while done < total:
        if "pagination" in r.json().keys():
            page_info = r.json()['pagination']
            helper.log_debug("PAGINATION_INFO: " + json.dumps(page_info))
            if "updatedDate" in page_info.keys():
                updatedDate = str(page_info['updatedDate'])
                skipUntil = page_info['skipUntil']
                total = page_info['total']
                itemCount = r.json()['itemCount']
                if "items" in r.json().keys():
                    for item in r.json()['items']:
                         if helper.get_check_point(item['flow_id']):
                            helper.log_debug(item['flow_id'] + " Id already present in the checkpoint")
                         else:
                           event = helper.new_event(data=json.dumps(item), source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
                           ew.write_event(event)
                           helper.log_debug(item['flow_id'] + " Id adding to the checkpoint")
                           helper.save_check_point(item['flow_id'], 'Y')
                    done = done + itemCount
                    f = open(PRESET_FILE, "w")
                    PRESETS['url'] = url
                    PRESETS['total'] = total
                    PRESETS['done'] = done
                    f.write(json.dumps(PRESETS))
                    f.close()
                    helper.log_debug("DONE :: " + str(done) + ", TOTAL = " + str(total))
                    if "https" in base_url: 
                       url = base_url + '/public/api/v1/' + tenant + '/analytics/flows?gte='+gte+'&lte='+lte+'&limit='+limit+'&updatedDate='+updatedDate+'&skipUntil='+skipUntil
                       helper.log_debug(">>>> URL = " + url)
                       r = s.get(url = url, headers={'x-api-token': token}, verify=CA_CERT,cert=cert)
                else:
                    helper.log_debug("EXITING-NO-ITEMS " + json.dumps(r.json()))
                    total = -1
            else:
                helper.log_debug("EXITING-NO-UPDATEDDATE " + json.dumps(r.json()))
                total = -1
        else:
            helper.log_debug("NO PAGINATION INFO IN RESPONSE")
            total = -1
            if "items" in r.json().keys():
                for item in r.json()['items']:
                    if helper.get_check_point(item['flow_id']) is None:
                        event = helper.new_event(data=json.dumps(item), source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
                        ew.write_event(event)
                        helper.save_check_point(item['flow_id'], 'Y')



