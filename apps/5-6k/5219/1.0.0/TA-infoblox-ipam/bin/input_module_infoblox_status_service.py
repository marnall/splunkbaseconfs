
# encoding = utf-8

import os
import sys
import time
import datetime
import base64
import json




def parse_service(data):

    new = []
    for i in data['result']:
        d = {}
        for s in i['service_status']:
            if 'description' in s:
                l = {"service_status_"+s['service'].lower()+"_status": s['status'], "service_status_"+s['service'].lower()+"_description": s['description']}
            else:
                l = {"service_status_"+s['service'].lower()+"_status": s['status']}
            d.update(l)

        new_dict = i
        new_dict.update(d)
        del new_dict['service_status']
        new.append(new_dict)

    return new




def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    global_account = definition.parameters.get('global_account', None)
    infoblox_api_base_url = definition.parameters.get('infoblox_api_base_url', None)
    infoblox_api_version = definition.parameters.get('infoblox_api_version', None)
    disable_ssl_trust = definition.parameters.get('disable_ssl_trust', None)
    



def collect_events(helper, ew):

    #helper.set_log_level("DEBUG")

    opt_global_account = helper.get_arg('global_account')
    opt_infoblox_api_base_url = helper.get_global_setting('infoblox_api_base_url')
    opt_infoblox_api_version = helper.get_global_setting('infoblox_api_version')
    opt_disable_ssl_trust = helper.get_global_setting('disable_ssl_trust')
    

    input_type = helper.get_input_type()

    # Build Request
    usrPass = opt_global_account['username'] + ":" + opt_global_account['password']
    b64Val = base64.b64encode(usrPass.encode()).decode()
    
    try:
        url = opt_infoblox_api_base_url + "/wapi/v" + opt_infoblox_api_version + "/member"
        method = "GET"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Basic %s" % b64Val
        }
        parameters = {
            "_return_fields+": "service_status",
            "_return_as_object": "1"
        }
        
        # Send HTTP Request
        response = helper.send_http_request(url, method, parameters=parameters,
                                            headers=headers, verify=not opt_disable_ssl_trust)

    except:
        helper.log_info("Connection to Primary Infoblox Server Failed. Attempting Secondary...")
        url = opt_infoblox_api_base_url2 + "/wapi/v" + opt_infoblox_api_version + "/member"
        method = "GET"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Basic %s" % b64Val
        }
        parameters = {
            "_return_fields+": "service_status",
            "_return_as_object": "1"
        }
        
        # Send HTTP Request
        response = helper.send_http_request(url, method, parameters=parameters,
                                            headers=headers, verify=not opt_disable_ssl_trust)



    
    #helper.log_debug(response.status_code)
    #helper.log_debug(response.text)
    dict_response = parse_service(response.json())


    for i in dict_response:
        i['time'] = time.ctime()
        data = json.dumps(i)
        event = helper.new_event(source=input_type, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
        ew.write_event(event)
        
    
    
    