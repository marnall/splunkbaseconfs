
# encoding = utf-8

import os
import sys
import time
import datetime
import base64
import json

def validate_input(helper, definition):
    requested_fields = definition.parameters.get('requested_fields', None)
    item_limit = definition.parameters.get('item_limit', None)
    global_account = definition.parameters.get('global_account', None)
    if (requested_fields == None or item_limit == None or global_account == None):
        err = "Error during validation of input configuration. Please check your settings. Exitting..."
        helper.log_error(err)
        sys.exit(0)
    pass

def collect_events(helper, ew):
    #config the vars
    opt_global_account = helper.get_arg('global_account')
    opt_global_timeout = float(helper.get_global_setting('http_request_timeout'))
    global_source = helper.get_input_type()
    global_source_type = helper.get_sourcetype()
    global_index = helper.get_output_index()
    global_next_page = 0
    global_resource = helper.get_global_setting("rest_api_home")+"/record:host_ipv4addr?_paging=1&_return_as_object=1&_max_results="+helper.get_arg('item_limit')+"&_return_fields="+helper.get_arg('requested_fields')
    global_paged_resource = global_resource+"&_page_id="
    dict_headers = {"Authorization": "Basic "+base64.b64encode(opt_global_account['username'].encode()+":"+opt_global_account['password'].encode())}
    
    
    #get the first page object
    try:
        ipv4_response = helper.send_http_request(global_resource, "GET", parameters=None, payload=None, headers=dict_headers, cookies=None, verify=False, cert=None, timeout=opt_global_timeout, use_proxy=False)
        ipv4_json = ipv4_response.json()
        
    except Exception as e:
        err = "Error during Infoblox get /record:host_ipv4addr method. Response cannot be converted to json. Check credentials or URL.\nException: "+str(e)
        helper.log_error(err)
        #ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=err))
    
    
    #loop through the items in the object
    try:
        length = len(ipv4_json['result'])
        for i in range(length):
            ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=json.dumps(ipv4_json['result'][i])))
    
    except Exception as e:
        err = "Error during json object loop.\nException: "+str(e)
        helper.log_error(err)
        #ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=err))
    
    
    #get the next page id
    try:
        global_next_page = ipv4_json['next_page_id']
        
    except Exception as e:
        err = "Error during next page id retrieval. Probably there are no more objects to retrieve...\nException: "+str(e)
        helper.log_error(err)
        #ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=err))
        #sys.exit(0)
    
    
    #loop until page references are returned
    while global_next_page != 0:
        #prepare request
        try:
            ipv4_response = helper.send_http_request(global_paged_resource+global_next_page, "GET", parameters=None, payload=None, headers=dict_headers, cookies=None, verify=False, cert=None, timeout=opt_global_timeout, use_proxy=False)
            ipv4_json = ipv4_response.json()
        
        except Exception as e:
            err = "Error during Infoblox get next page of /record:host_ipv4 method. Response cannot be converted to json. Check credentials or URL.\nException: "+str(e)
            helper.log_error(err)
            #ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=err))
        
        #loop through the items in the object
        try:
            length = len(ipv4_json['result'])
            for i in range(length):
                ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=json.dumps(ipv4_json['result'][i])))
        
        except Exception as e:
            err = "Error during json object loop in next page.\nException: "+str(e)
            helper.log_error(err)
            #ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=err))
        
        #get the next page id
        try:
            global_next_page = ipv4_json['next_page_id']
            
        except Exception as e:
            err = "Error during next page id retrieval. Probably there are no more objects to retrieve...\nException: "+str(e)
            helper.log_error(err)
            #ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=err))
            global_next_page = 0
    
    