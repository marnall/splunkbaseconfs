# encoding = utf-8

import os
import sys
import time
import datetime
import base64
import hashlib
import json
import urllib3

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
WHL_DIR = SPLUNK_HOME + "/etc/apps/Apex-One-as-a-Service/bin/"

for filename in os.listdir(WHL_DIR):
    if filename.endswith(".whl"):
        sys.path.append(WHL_DIR + filename)

import jwt
import requests

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass

def create_checksum(http_method, raw_url, headers, request_body):
        string_to_hash = http_method.upper() + '|' + raw_url.lower() + '|' + headers + '|' + request_body
        base64_string = base64.b64encode(hashlib.sha256(str.encode(string_to_hash)).digest()).decode('utf-8')
        return base64_string

def create_jwt_token(application_id, api_key, http_method, raw_url, headers, request_body,
                    iat=time.time(), algorithm='HS256', version='V1'):
    payload = {'appid': application_id,
            'iat': iat,
            'version': version,
            'checksum': create_checksum(http_method, raw_url, headers, request_body)}
    token = jwt.encode(payload, api_key, algorithm=algorithm)#.decode('utf-8')
    return token 

def collect_events(helper, ew):

    urllib3.disable_warnings()
    polling = helper.get_arg('polling_interval')
    helper.log_info("[ApexOne] Polling Interval: %s" % polling)
    dtStartTime = datetime.datetime.now() - datetime.timedelta(seconds=int(polling))
    helper.log_info("[ApexOne] Query Start Time: %s" % dtStartTime)
    global_api_key = helper.get_global_setting('api_key')
    global_application_id = helper.get_global_setting('application_id')
    global_web_url = helper.get_global_setting('apex_one_as_a_service_url')
    use_url_base = 'https://' + global_web_url
    helper.log_debug("[ApexOne] Using Application ID: %s" % global_application_id)
    helper.log_debug("[ApexOne] Connecting To Apex One URL: %s" % use_url_base)

    """Implement your data collection logic here
    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value."""

    useQueryString="?output_format=CEF&page_token=0&since_time=" + str(int(time.mktime(dtStartTime.timetuple())))
    helper.log_debug("[ApexOne] Query String: %s" % useQueryString)
    canonicalRequestHeaders = ''
    useRequestBody = ''
    data = []

    logArray = [
        'officescan_virus',
        'data_loss_prevention', 
        'device_access_control', 
        'behaviormonitor_rule',
        'spyware',
        'web_security',
        'security',
        'ncie',
        'cncdetection',
        'filehashdetection',
        'Predictive_Machine_Learning',
        'Sandbox_Detection_Log',
        'EACV_Information',
        'Attack_Discovery_Detections',
        'intrusion_prevention'
        ]

    for logtype in logArray:
        productAgentAPIPath = '/WebApp/api/v1/Logs/' + logtype
        jwt_token = create_jwt_token(global_application_id, global_api_key, 'GET',
                                productAgentAPIPath + useQueryString,
                                canonicalRequestHeaders, useRequestBody, iat=time.time())

        header = {'Authorization': 'Bearer ' + jwt_token , 'Content-Type': 'application/json;charset=utf-8'}

        response = requests.get(use_url_base + productAgentAPIPath + useQueryString,
                        headers=header, verify=False)

        r_json = response.json()
        r_text = response.text
        r_json = response.json()

        response.raise_for_status()

        helper.log_debug("[ApexOne]: %s logs retrieved" % logtype)

        for item in r_json['Data']['Logs'] or []:
            data.append(item)

    helper.log_info("[ApexOne]: Number of Events Retrieved: %s" % len(data))
    helper.new_event(data, time=datetime.datetime.now(), host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)

    for d in data:
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=d)
        ew.write_event(event)