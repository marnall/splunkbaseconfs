import csv
import os
import sys
import requests
from splunk.rest import simpleRequest
import json
import re
import datetime
import urllib3

import logging
# set up logging suitable for splunkd consumption
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(formatter)
logging.root.addHandler(handler)

# Supress Cert warning for local Splunk REST calls
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def check_inputs(config):
    # Not Implemented. This handled within the individual integrations.
    return True

def get_o11y_creds(payload):
    configuration = payload['configuration']
    o11y_org = ""
    if "orgCred" in configuration and len(configuration['orgCred']) > 0:
        o11y_org = configuration.get('orgCred')
    else:
        logging.error("Error reason='o11y organisation not specified'")

    endpoint = "{}/servicesNS/-/o11y-metadata-updater/storage/passwords/{}?output_mode=json".format(
        payload['server_uri'],
        o11y_org)  
    meta, payload = simpleRequest(endpoint, method="GET", sessionKey=payload['session_key'])
    

    if meta.status >= 400:
        logging.error("Error code={} raised while retrieving password for {}".format(
            meta.status_code, o11y_org))
    else:
        try:
            json_res = json.loads(payload)
            api_token = json_res['entry'][0]['content']['clear_password']
            realm = json_res['entry'][0]['content']['realm']
        except Exception:
            logging.error("Unable to retrieve password for org:{}. Please check the password exists.".format(
                o11y_org))
    return api_token, realm


def send_request(payload):
    """ Retrieves the password from Splunk REST then uses that password to send a ServiceNow compatible JSON payload. """
    configuration = payload['configuration']
    results = payload['result']
    
    api_token, realm = get_o11y_creds(payload)

    sf_payload = {}
    custom_properties = {}
    sf_headers = {}
    sf_headers['X-SF-TOKEN'] = api_token
    matchKey = configuration.get("matchField")
    matchValue = results.get(matchKey)
    
    for key in results.keys():
        if key != matchKey:
            custom_properties[key] = results[key]
    sf_payload['customProperties'] = custom_properties

    if len(realm) is 0:
        sf_url = "https://api.signalfx.com/v2/dimension/{}/{}".format(matchKey,matchValue)
    else:
        sf_url = "https://api.{}.signalfx.com/v2/dimension/{}/{}".format(realm,matchKey,matchValue)
    r = requests.put(sf_url, json=sf_payload, verify=True, headers=sf_headers)
    
    if r.status_code >= 400:
        logging.error("Error code='{}' raised when creating ticket for key='{}' value='{}'".format(
            r.status_code, matchKey, matchValue))
    else:
        logging.info("code='{}' when attaching metadata key='{}' value='{}'".format(
            r.status_code, matchKey, matchValue))


if len(sys.argv) > 1 and sys.argv[1] == "--execute":
    payload = json.load(sys.stdin)
    if check_inputs(payload):
        send_request(payload)
