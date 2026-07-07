# encoding = utf-8

import os
import sys
import datetime
import time
import requests, urllib3
import json

def get_token(url, username, password):                                                                                                                     
    payload = {"username": username, "password": password, "clientContext": 1}   
    headers = {'Content-Type': 'application/json', 'Accept-Charset': 'UTF-8'}
    ApiReturn = requests.post(url, data=json.dumps(payload), headers=headers)
    ApiToken = json.loads(ApiReturn.content)
    token = ApiToken["token"]
    
    return {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

def validate_input(helper, definition):
    url = definition.parameters.get('ucmdb_server_url', None)
    user = definition.parameters.get('user', None)
    password = definition.parameters.get('password', None)
    request_type = definition.parameters.get('request_type', None)
    ci_class_id = definition.parameters.get('ci_class_id', None)
    cust_source_type = definition.parameters.get('cust_source_type', None)
    
def collect_events(helper, ew):
    opt_url = helper.get_arg('ucmdb_server_url')
    opt_user = helper.get_arg('user')
    opt_password = helper.get_arg('password')
    opt_request_type = helper.get_arg('request_type')
    opt_ci_class_id = helper.get_arg('ci_class_id')
    opt_cust_source_type = helper.get_arg('cust_source_type')
    
    if (opt_cust_source_type == ''):
        opt_cust_source_type = 'ucmdb'
    
    authURL = opt_url + "/rest-api/authenticate"

    Headers = get_token(authURL, opt_user, opt_password) 
    cHeader = eval(json.dumps(Headers))

    queryURL = opt_url + "/rest-api/topologyQuery"
    
    queryPayload = {"nodes": [{"type": opt_ci_class_id, "queryIdentifier": "%", "visible": "true", "layout": ["name"],}], "relations": []}
    
    queryResult = requests.post(queryURL, data=json.dumps(queryPayload), headers=cHeader)
    jsonResult = json.loads(queryResult.content)

    try:
        if opt_request_type == 'ci':
            urlCI = opt_url + "/rest-api/dataModel/" + opt_request_type + "/"
            
            for c in jsonResult['cis']:
                urlCI = opt_url + "/rest-api/dataModel/" + opt_request_type + "/"
                param = c['ucmdbId']
                urlCI = urlCI + param
                
                queryCI = requests.get(urlCI, headers=cHeader)
                jsonCI = json.loads(queryCI.content)
    
                data = " ".join(["=".join([key, str(val)]) for key, val in jsonCI['properties'].items()])
                
                event = helper.new_event(data, host=None, source=None, sourcetype=opt_cust_source_type, done=True, unbroken=True)
                
                ew.write_event(event)
                
        else:
            urlCI = opt_url + "/rest-api/dataModel/" + opt_request_type + "/" + opt_ci_class_id
    
            queryCI = requests.get(urlCI, headers=cHeader)
            relatedCIs = json.loads(queryCI.content)
            
            for r in relatedCIs['cis']:
                data = " ".join(["=".join([key, str(val)]) for key, val in r['properties'].items()])
                
                event = helper.new_event(data, host=None, source=None, sourcetype=opt_cust_source_type, done=True, unbroken=True)
                    
                ew.write_event(event)
    except Exception as e:
        raise e