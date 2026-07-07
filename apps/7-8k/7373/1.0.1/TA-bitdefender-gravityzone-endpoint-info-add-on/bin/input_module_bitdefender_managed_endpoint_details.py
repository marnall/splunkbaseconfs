# encoding = utf-8

import os
import sys
import time
import datetime
import json
import requests


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # bitdefender_api_key = definition.parameters.get('bitdefender_api_key', None)
    pass

def collect_events(helper, ew):


    # get configuration parameters
    
    bitdefender_api_key = helper.get_global_setting("bitdefender_api")
    
    bitdefender_api_url = "https://cloudgz.gravityzone.bitdefender.com/api/v1.0/jsonrpc/network"
    
    
    # get bitdefender root ID of the target company
    # https://www.bitdefender.com/business/support/en/77209-128483-getendpointslist.html
    
    json_getEndpointsList = '{"jsonrpc":"2.0","method":"getCustomGroupsList","id":"x"}'
    r_rootlist = requests.post(bitdefender_api_url, auth=(bitdefender_api_key,''), headers = {'Content-Type':'application/json' }, json=json.loads(json_getEndpointsList)) 
    
    if(r_rootlist.status_code==200):
        
        helper.log_info("btgz: api returned 200 - API key is OK")
        
        json_data_rootlist = r_rootlist.json()
        

        for rootlist in json_data_rootlist['result']:
            
            # get group ID
            if rootlist['name'] == "Computers and Groups":
                list_id = rootlist['id']
                
        
        # check if group ID has been set up
        if(list_id != ""):
            helper.log_info("btgz: found Computers and Groups id: "+list_id)
        else:
            helper.log_error("btgz: stage 1 - getCustomGroupsList Splunk cant get the list_id. It's searching for a grup called \"Computers and Groups\"")
            sys.exit(1)
                
                
                
    else:
        # usually if it crashes here, it means that the bitdefender gravityzone API key is incorrect or missing
        helper.log_error("btgz: stage 1 - getCustomGroupsList failed. Probably the API key is incorrect. Make sure to set bitdefender_api in \"Configuration\" > \"Add-on Settings\"")
        sys.exit(1)


    # get how many pages
    
    json_body_getEndpointsList_pages = '{"params":{"page":1,"perPage":100,"filters":{"depth":{"allItemsRecursively":true}}},"jsonrpc":"2.0","method":"getEndpointsList","id":"'+list_id+'"}'

    r = requests.post(bitdefender_api_url, auth=(bitdefender_api_key,''), headers = {'Content-Type':'application/json' }, json=json.loads(json_body_getEndpointsList_pages)) 


    if(r.status_code==200):
        
        
        
        json_data = r.json()
        #json_data = json.load(raw_data)
        endpoint_list_pages = json_data['result']['pagesCount']
        
        helper.log_info("btgz: found pages: "+str(endpoint_list_pages))
        
        page_number = 1
        for page in range(endpoint_list_pages):
            
            
            #json_body_getEndpointsList = '{"params":{"page":'+str(page_number)+',"perPage":50},"jsonrpc":"2.0","method":"getEndpointsList","id":"58e63c53097034761b8b4570"}'    
            json_body_getEndpointsList = '{"params":{"page":'+str(page_number)+',"perPage":100,"filters":{"depth":{"allItemsRecursively":true}}},"jsonrpc":"2.0","method":"getEndpointsList","id":"58e63c55097034761b8b4576"}'  


            r_list = requests.post(bitdefender_api_url, auth=(bitdefender_api_key,''), headers = {'Content-Type':'application/json' }, json=json.loads(json_body_getEndpointsList)) 

            json_endpoints = r_list.json()

            
            # get list of endpoints
            for item in json_endpoints['result']['items']:
                
                json_getEndpointsList = '{"params":{"endpointId":"'+item['id']+'","options":{"includeScanLogs":true}},"jsonrpc":"2.0","method":"getManagedEndpointDetails","id":"x"}'

                
                r_item = requests.post(bitdefender_api_url, auth=(bitdefender_api_key,''), headers = {'Content-Type':'application/json' }, json=json.loads(json_getEndpointsList))
                json_data_item = json.dumps(r_item.json())
                
                
                json_data_item_dict = r_item.json()
                
                
                # prevent crash if this event shows up
                # {"id": "x", "jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params", "data": {"details": "Invalid value for 'endpointId' parameter."}}}
                
                if not("error" in json_data_item_dict):
                    
                    #json_data_item_clean_dumps  = json.dumps(json_data_item_dict)
                    
                    json_data_item_dict_result = json_data_item_dict['result']
                
                    json_data_item_clean_dumps = json.dumps(json_data_item_dict_result)
                
                    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json_data_item_clean_dumps)
                ew.write_event(event)  

                

                


            # page increment
            page_number += 1
