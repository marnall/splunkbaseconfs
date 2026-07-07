# encoding = utf-8

import os
import sys
import datetime
import time
import requests, urllib3
import json

def get_token(url, resource, username, password):
    payload = {
        'grant_type': 'client_credentials',
        'client_id': username,
        'client_secret': password,
        'Content-Type': 'x-www-form-urlencoded',
        'resource': resource,
        }
    
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    ApiReturn = requests.post(url, data=payload, verify=False)
    ApiToken = json.loads(ApiReturn.content)["access_token"]
    
    return {
        'Authorization': 'Bearer ' + ApiToken, 
        'Content-Type': 'application/json'
        }

def validate_input(helper, definition):
    tenant_id = definition.parameters.get('tenant_id', None)
    client_id = definition.parameters.get('client_id', None)
    client_secret = definition.parameters.get('client_secret', None)
    log_analytics_workspace_id = definition.parameters.get('log_analytics_workspace_id', None)
    log_analytics_query = definition.parameters.get('log_analytics_query', None)
    cust_source_type = definition.parameters.get('cust_source_type', None)
    output_format = definition.parameters.get('output_format', None)

def collect_events(helper, ew):
    opt_tenant_id = helper.get_arg('tenant_id')
    opt_client_id = helper.get_arg('client_id')
    opt_client_secret = helper.get_arg('client_secret')
    opt_log_analytics_workspace_id = helper.get_arg('log_analytics_workspace_id')
    opt_log_analytics_query = helper.get_arg('log_analytics_query')
    opt_cust_source_type = helper.get_arg('cust_source_type')
    opt_output_format = helper.get_arg('output_format')
    
    if opt_cust_source_type == '':
        opt_cust_source_type = 'kql'
    
    try:
        loginURL = "https://login.microsoftonline.com/" + opt_tenant_id + "/oauth2/token"
        resource = "https://api.loganalytics.io"
        url = "https://api.loganalytics.io/v1/workspaces/" + opt_log_analytics_workspace_id + "/query"
        
        Headers = get_token(loginURL, resource, opt_client_id, opt_client_secret)
        params = {
            "query": opt_log_analytics_query
            }
        
        result = requests.get(url, params=params, headers=Headers, verify=False)
        
        if opt_output_format == 'csv':
        
            rows = len(result.json()["tables"][0]["rows"])
        
            for row in range(0, rows):
                data = json.dumps(result.json()["tables"][0]["rows"][row]).strip("[]").replace("'","")
                
                event = helper.new_event(data, host=None, source=None, sourcetype=opt_cust_source_type, done=True, unbroken=True)
        
                try:
                    ew.write_event(event)
                except Exception as e:
                    raise e
        
        elif opt_output_format == 'json':
            columns = result.json()["tables"][0]["columns"]
            column_length = len(result.json()["tables"][0]["columns"])
            
            for row in result.json()["tables"][0]["rows"]:
                data = {}
                
                for i in range(0,column_length):
                    data[columns[i]['name']] = row[i]
                
                data = json.dumps(data)

                event = helper.new_event(data, host=None, source=None, sourcetype=opt_cust_source_type, done=True, unbroken=True)
                try:
                    ew.write_event(event)
                except Exception as e:
                    raise e        

    except Exception as e:
        raise e