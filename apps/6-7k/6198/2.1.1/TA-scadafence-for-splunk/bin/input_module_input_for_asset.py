
# encoding = utf-8

import os
import sys
import time
import datetime

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
    # retrive_data_from = definition.parameters.get('retrive_data_from', None)
    # organization_route = definition.parameters.get('organization_route', None)
    # scadafence_server = definition.parameters.get('scadafence_server', None)
    # site_id = definition.parameters.get('site_id', None)
    # api_key = definition.parameters.get('api_key', None)
    # api_secret = definition.parameters.get('api_secret', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""

    opt_retrive_data_from = helper.get_arg('retrive_data_from')
    opt_organization_route = helper.get_arg('organization_route')
    opt_scadafence_server = helper.get_arg('scadafence_server')
    opt_site_id = helper.get_arg('site_id')
    opt_api_key = helper.get_arg('api_key')
    opt_api_secret = helper.get_arg('api_secret')
    
    endpoint_for_platfrom:str = "/externalApi/assets"
    endpoint_for_multi_site:str = "/api/assets"
    

    if(opt_retrive_data_from == "platform"):
        endpoint:str = endpoint_for_platfrom
    else:
        endpoint:str = endpoint_for_multi_site

    if opt_scadafence_server[:5]=="http":
        url_parser= urlparse(opt_scadafence_server)
        opt_scadafence_server="https://"+url_parser.netloc+endpoint
        helper.log_info(opt_scadafence_server)
    else:
        opt_scadafence_server=opt_scadafence_server+endpoint
        helper.log_info(opt_scadafence_server)
    
    opt_page=1
    opt_size=10
    final_assets=[]
    while True:
    # The following examples send rest requests to some endpoint.
        url = opt_scadafence_server
        parameters={"page":opt_page,"size":opt_size}
        accept="application/json"
        headers={"x-api-key":opt_api_key,
                 "x-api-secret":opt_api_secret,
                 "accept":accept}
                 
        if(opt_retrive_data_from == "multi_site"):
            parameters["order"] = "ip"
            parameters["sort"] = "asc"
            headers['x-org'] = opt_organization_route
        # The following examples send rest requests to some endpoint.
        response = helper.send_http_request(url, "GET", parameters=parameters, payload=None,
                                            headers=headers, cookies=None, verify=True, cert=None,
                                            timeout=None, use_proxy=False)
       
        r_json = response.json()

        helper.log_info(f"parameters used to retrived the assets are : {parameters}")
        helper.log_debug("response : ")
        helper.log_info(r_json)

        # get response status code
        r_status = response.status_code
        if r_status != 200:
            '''check the response status, if the status is not sucessful, raise requests.HTTPError'''
            response.raise_for_status()
            helper.log_debug("Http status code : {}".format(r_status))
            break
        if len(r_json) == 0:
            helper.log_debug("No assets in page number {}".format(opt_page))
            break
        '''The following show usage of check pointing related helper functions.'''
        for asset in r_json:
            final_assets.append(asset)
        opt_page = opt_page + 1
        
         # To create a splunk event
    for asset in final_assets:
        single_event = ""
        for key, val in asset.items():
            single_event += key + "=" + str(val) + "\t"
            #helper.log_info(single_event)
        single_event+="site id="+opt_site_id+"\t"
        #helper.log_info(single_event)
        event = helper.new_event(single_event, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
        ew.write_event(event)
