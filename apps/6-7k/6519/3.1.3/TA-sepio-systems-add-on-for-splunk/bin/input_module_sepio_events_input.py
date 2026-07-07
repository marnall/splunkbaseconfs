
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import random


'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # category = definition.parameters.get('category', None)
    # from = definition.parameters.get('from', None)
    pass

def collect_events(helper, ew):
    
    opt_log_type = helper.get_arg('log_type')
    account_name = helper.get_arg('sepio_platform')
    
    global_host_url = account_name['username']
    opt_token = account_name['password']
    
    if not global_host_url.startswith("https"):
        raise Exception("The  Sepio Platform Url must use https protocol, e.g https://example.com")
    
    if global_host_url.endswith('/'):
        global_host_url = global_host_url[:-1]
    
    #query the GetEventsIntegration api
    r_json = query_get_data(helper,global_host_url,opt_token,opt_log_type)
    
    ingest_Integrations(helper,ew,r_json,global_host_url,opt_log_type)
    

def query_get_data(helper,host_url,opt_token,opt_log_type):
    
    payload = None
    
    opt_min_severity = helper.get_arg('min_severity')
    
    url = "{}/prime/webui/Events/Get{}".format(host_url,opt_log_type)
    
    header = {
        'Content-Type': 'application/json',
        'Authorization':'Bearer {}'.format(opt_token)
        }
    
    if opt_log_type == "EventsIntegration":
        
        eventid = helper.get_check_point('eventID-{}'.format(helper.get_input_stanza_names()))
        
        if eventid == None:
            
            FromDate = helper.get_check_point('FromDate-{}'.format(helper.get_input_stanza_names()))
            
            if FromDate == None:
                FromDate = str((datetime.datetime.now()  - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"))
                helper.save_check_point('FromDate-{}'.format(helper.get_input_stanza_names()),str(FromDate))
                next_eventid = None
            else:
                next_eventid = None
        else:
            FromDate = None
            next_eventid = eventid
        
        
        params={
            'MinimumSeverity': opt_min_severity,
            'PageSize': 10000,
            'FromDate': FromDate,
            'FromEventId': next_eventid
            }
            
    elif opt_log_type == "AuditsIntegration":

        audit_id = helper.get_check_point('auditTrailID-{}'.format(helper.get_input_stanza_names()))
        
        if audit_id == None:
            
            FromDate = helper.get_check_point('FromDate-{}'.format(helper.get_input_stanza_names()))
            
            if FromDate == None:
                FromDate = str((datetime.datetime.now()  - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"))
                helper.save_check_point('FromDate-{}'.format(helper.get_input_stanza_names()),str(FromDate))
                next_AuditTrailId = None
            else:
                next_AuditTrailId = None
        else:
            FromDate = None
            next_AuditTrailId = audit_id
            
        params={
            'MinimumSeverity': opt_min_severity,
            'PageSize': 10000,
            'FromDate': FromDate,
            'FromAuditTrailId': next_AuditTrailId
            }
    else:
        params={}
    
    #api call to /prime/webui/Events/GetEventsIntegration endpoint
    response = api_call(helper,url,'GET',params,header,payload)
    
    # get response status code
    r_status = response.status_code
    
    if r_status != 200:
        helper.log_info("{}: api query responded with {}".format(opt_log_type,r_status))
        response.raise_for_status()
        
    response_json = response.json()
    
    data = response_json['data']
    
    return data


def api_call(helper,url,method,params,header,payload):
    
    proxy_setup = helper.get_proxy()
    proxy_setting = proxy_setup is not None
    
    isVerify = helper.get_global_setting('is_verify')  # Checkbox setting for SSL verification
    cert_path = str(helper.get_global_setting('cert_path'))  # Path to custom certificate 
    
    response = helper.send_http_request(
        url, 
        method, 
        parameters=params, 
        payload=payload,
        headers=header, 
        cookies=None, 
        verify=cert_path if isVerify else False,
        timeout=(10.0, 30.0), 
        use_proxy=proxy_setting
    )
    return response
    

def ingest_Integrations(helper,ew,r_json,global_host_url,opt_log_type):
    
    if len(r_json)>0:
        
        results = []
        
        if opt_log_type == "EventsIntegration":
            eventid = ''
            
            for event in reversed(r_json):
                
                key = '{}-{}'.format(r_json[r_json.index(event)]["eventID"],helper.get_input_stanza_names())
                
                state = helper.get_check_point(key)
                
                if state is None:
                    results.append(event)
                    helper.save_check_point(key,"indexed")
                    eventid = r_json[r_json.index(event)]["eventID"] + 1
                
                """
                delete this after testing
                """    
                #helper.delete_check_point(key)
            if eventid != '':
                helper.save_check_point('eventID-{}'.format(helper.get_input_stanza_names()),str(eventid))
                """
                delete this after testing
                """
                #helper.delete_check_point('eventID-{}'.format(helper.get_input_stanza_names()))
        
        elif opt_log_type == "AuditsIntegration":
            
            audittrailid = ''
            
            for event in reversed(r_json):
                
                key = '{}-{}'.format(r_json[r_json.index(event)]["auditTrailID"],helper.get_input_stanza_names())
                
                state = helper.get_check_point(key)
                
                if state is None:
                    results.append(event)
                    helper.save_check_point(key,"indexed")
                    audittrailid = r_json[r_json.index(event)]["auditTrailID"] + 1
                    
                """
                delete this after testing
                """
                #helper.delete_check_point(key)
            
            if audittrailid != '':
                helper.save_check_point('auditTrailID-{}'.format(helper.get_input_stanza_names()),str(audittrailid))
                """
                delete this after testing
                """
                #helper.delete_check_point('auditTrailID-{}'.format(helper.get_input_stanza_names()))
        
        if len(results) == 0:
            helper.log_info("No new events")
            
        else:
            data =json.dumps(results)
            
            extract_host = (global_host_url.rsplit('://'))[1].rsplit('.')[0]
            s_type = "sepio:system:events"
            
            if opt_log_type == "AuditsIntegration":
                s_type = "sepio:audit"
            
            #define new events
            events = helper.new_event(data, time=None, host=extract_host, index=None, source=helper.get_input_type(), sourcetype=s_type, done=True, unbroken=True)
            
            #index/ingest data
            ew.write_event(events)
            helper.log_info("{} new events has been indexed".format(len(results)))
    else:
        helper.log_info("No new events found")
