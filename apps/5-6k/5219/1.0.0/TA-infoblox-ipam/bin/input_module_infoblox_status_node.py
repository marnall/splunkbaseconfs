
# encoding = utf-8

import os
import sys
import time
import datetime
import base64
import json
import collections



def flatten(d,sep="_"):

    obj = collections.OrderedDict()

    def recurse(t,parent_key=""):

        if isinstance(t,list):
            for i in range(len(t)):
                recurse(t[i],parent_key + sep + str(i) if parent_key else str(i))
        elif isinstance(t,dict):
            for k,v in t.items():
                recurse(v,parent_key + sep + k if parent_key else k)
        else:
            obj[parent_key] = t

    recurse(d)

    return obj





def parse_node(data):

    new = []
    for i in data['result']:
        d = {}

        for k,v in i['node_info'][0].items():
            if k == 'service_status':
                new_services = {}
                for s in v:
                    if 'description' in s:
                        l = {"service_status_"+s['service'].lower()+"_status": s['status'], "service_status_"+s['service'].lower()+"_description": s['description']}
                    else:
                        l = {"service_status_"+s['service'].lower()+"_status": s['status']}
                    new_services.update(l)
                d.update(new_services)
            else:
                d[k] = v

        d2 = flatten(d)

        new_dict = i
        new_dict.update(d2)
        del new_dict['node_info']
        new.append(new_dict)

    return new




def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    global_account = definition.parameters.get('global_account', None)
    infoblox_api_base_url = definition.parameters.get('infoblox_api_base_url', None)
    infoblox_api_base_url2 = definition.parameters.get('infoblox_api_base_url2', None)
    infoblox_api_version = definition.parameters.get('infoblox_api_version', None)
    disable_ssl_trust = definition.parameters.get('disable_ssl_trust', None)




def collect_events(helper, ew):

    #helper.set_log_level("DEBUG")

    opt_global_account = helper.get_arg('global_account')
    opt_infoblox_api_base_url = helper.get_global_setting('infoblox_api_base_url')
    opt_infoblox_api_base_url2 = helper.get_global_setting('infoblox_api_base_url2')
    opt_infoblox_api_version = helper.get_global_setting('infoblox_api_version')
    opt_disable_ssl_trust = helper.get_global_setting('disable_ssl_trust')
    

    input_type = helper.get_input_type()

    # Build Request
    usrPass = opt_global_account['username'] + ":" + opt_global_account['password']
    b64Val = base64.b64encode(usrPass.encode()).decode()
    
    # Try Primary
    try:
        url = opt_infoblox_api_base_url + "/wapi/v" + opt_infoblox_api_version + "/member"
        method = "GET"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Basic %s" % b64Val
        }
        parameters = {
            "_return_fields+": "node_info",
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
            "_return_fields+": "node_info",
            "_return_as_object": "1"
        }
        
        # Send HTTP Request
        response = helper.send_http_request(url, method, parameters=parameters,
                                            headers=headers, verify=not opt_disable_ssl_trust)


    #helper.log_debug(response.status_code)
    #helper.log_debug(response.text)
    dict_response = parse_node(response.json())
    
    for i in dict_response:
        i['time'] = time.ctime()
        data = json.dumps(i)
        
        event = helper.new_event(source=input_type, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
        ew.write_event(event)
        
    