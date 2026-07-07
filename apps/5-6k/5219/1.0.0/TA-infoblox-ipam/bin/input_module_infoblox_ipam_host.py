
# encoding = utf-8

import os
import sys
import time
import datetime
import base64
import json



def parse_ipam(data):
    new = []
    for i in data['result']:
        for addr in i['ipv4addrs']:
            new.append({'hostname': addr['host'], 'ipv4addr': addr['ipv4addr'], 'view': i['view'], 'configure_for_dhcp': addr['configure_for_dhcp']})

    return new



def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    global_account = definition.parameters.get('global_account', None)
    infoblox_api_base_url = definition.parameters.get('infoblox_api_base_url', None)
    infoblox_api_base_url2 = definition.parameters.get('infoblox_api_base_url2', None)
    infoblox_api_version = definition.parameters.get('infoblox_api_version', None)
    disable_ssl_trust = definition.parameters.get('disable_ssl_trust', None)
    limit = definition.parameters.get('limit', None)



def collect_events(helper, ew):

    #helper.set_log_level("DEBUG")

    opt_global_account = helper.get_arg('global_account')
    opt_infoblox_api_base_url = helper.get_global_setting('infoblox_api_base_url')
    opt_infoblox_api_base_url2 = helper.get_global_setting('infoblox_api_base_url2')
    opt_infoblox_api_version = helper.get_global_setting('infoblox_api_version')
    opt_disable_ssl_trust = helper.get_global_setting('disable_ssl_trust')
    opt_limit = helper.get_arg('limit')

    input_type = helper.get_input_type()

    # Build Request
    usrPass = opt_global_account['username'] + ":" + opt_global_account['password']
    b64Val = base64.b64encode(usrPass.encode()).decode()
    
    try:
        url = opt_infoblox_api_base_url + "/wapi/v" + opt_infoblox_api_version + "/record:host"
        method = "GET"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Basic %s" % b64Val
        }
        
        parameters = {
            "_paging": "1",
            "_return_as_object": "1",
            "_max_results": 100
        }
        
        next_page_id = None
        c=0
        pid = None
        while True:
            
            if pid:
                parameters['_page_id'] = pid
                
            # Send HTTP Request
            response = helper.send_http_request(url, method, parameters=parameters,
                                                headers=headers, verify=not opt_disable_ssl_trust)
        
            dict_response = response.json()
    
    
            helper.log_debug(response.status_code)
            #helper.log_debug(response.text)
        
            parsed_data = parse_ipam(dict_response)
            
            for i in parsed_data:
                i['time'] = time.ctime()
                data = json.dumps(i)
                event = helper.new_event(source=input_type, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
                ew.write_event(event)
            
                
            if 'next_page_id' in dict_response:
                    pid = dict_response['next_page_id']
            else:
                    break
    
            if c > int(opt_limit):
                break
            c+=100
    except:
        
        helper.log_info("Connection to Primary Infoblox Server Failed. Attempting Secondary...")
        
        url = opt_infoblox_api_base_url2 + "/wapi/v" + opt_infoblox_api_version + "/record:host"
        method = "GET"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Basic %s" % b64Val
        }
        
        parameters = {
            "_paging": "1",
            "_return_as_object": "1",
            "_max_results": 100
        }
        
        next_page_id = None
        c=0
        pid = None
        while True:
            
            if pid:
                parameters['_page_id'] = pid
                
            # Send HTTP Request
            response = helper.send_http_request(url, method, parameters=parameters,
                                                headers=headers, verify=not opt_disable_ssl_trust)
        
            dict_response = response.json()
    
    
            helper.log_debug(response.status_code)
            #helper.log_debug(response.text)
        
            parsed_data = parse_ipam(dict_response)
            
            for i in parsed_data:
                i['time'] = time.ctime()
                data = json.dumps(i)
                event = helper.new_event(source=input_type, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
                ew.write_event(event)
            
                
            if 'next_page_id' in dict_response:
                    pid = dict_response['next_page_id']
            else:
                    break
    
            if c > int(opt_limit):
                break
            c+=100


