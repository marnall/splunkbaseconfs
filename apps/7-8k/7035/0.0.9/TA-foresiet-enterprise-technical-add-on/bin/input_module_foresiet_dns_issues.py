
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import foresiet_constants as const
'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''

# For advanced users, if you want to create single instance mod input, uncomment this method.
# def use_single_instance_mode():
#     return True

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    interval                = definition.parameters['interval']
    
    if interval is not None:
        helper.log_info("Interval input is - {}".format(interval))
        try:
            if int(interval) < 3600:
                raise ValueError("The interval need to be greater than 3600 seconds (60 Minutes)")  
        except ValueError:
            raise ValueError("The interval need to be greater than 3600 seconds (60 Minutes")
        

def collect_events(helper, ew):
    # Setting for input type 
    stanza_name = "foresiet_app_misconfiguration"
    index = helper.get_output_index()
    source = helper.get_input_type()
    sourcetype = helper.get_sourcetype()
    
    url = "https://ext.foresiet.com/digirisk/api/v1/vulnerability/dns/list"
    current_page_number = 1

    
    # Get the API key and Client secret key
    opt_foresiet_api_key = helper.get_arg('foresiet_api_key')
    opt_foresiet_client_secret = helper.get_arg('foresiet_client_secret')

    # Set log level as per the global level seeting
    log_level = helper.get_log_level()
    helper.set_log_level(log_level)
    headers     = { "Authorization": opt_foresiet_api_key, "X-Client-Key": opt_foresiet_client_secret, "User-Agent":const.USER_AGENT }
    method      = "GET"
    
    
    
    while not current_page_number is None: 
        parameters  = { "page" : current_page_number}
        helper.log_info("Fetching results from {} page.".format( current_page_number ))
        # The following examples send rest requests to some endpoint.
        response = helper.send_http_request(
                                            url         =   url, 
                                            method      =   method, 
                                            parameters  =   parameters, 
                                            payload     =   None,
                                            headers     =   headers, 
                                            cookies     =   None, 
                                            verify      =   True, 
                                            cert        =   None,
                                            timeout     =   None, 
                                            use_proxy   =   True
                                        )
        # get the response headers
        r_headers = response.headers
    
        # get response status code
        r_status = response.status_code
        
        
        # get response body as json. If the body text is not a json string, raise a ValueError
        r_json = response.json()
        
        # check the response status, if the status is not sucessful, raise requests.HTTPError    
        if r_status not in  [ 200 ]:
            helper.log_error("Error while fetching information from the API. HTTP Status code - {}".format(r_status))
            
            if r_status == 403:
                helper.log_error("Error while fetching information from the API. Authentication Failed. HTTP Status code - {}".format(r_status))
                break
                                  
            if r_status == 429:
                wait_for_seconds = r_headers.get('X-Throttle-Wait-Seconds',None)
                
                if not wait_for_seconds is None:
                    helper.log_warning("HTTP Status code - {}. Too Many Requests, Rate limited by the API. Waiting for {} seconds ".format(r_status, wait_for_seconds ))
                    time.sleep(wait_for_seconds)
            
            #response.raise_for_status()
        else:
            
    
            results_to_push = []
            
            
            for data in r_json["results"]["data"]:
                # Key name for the checkpoint
                key = "{}_{}".format("dns",data['_id'])
        
                if helper.get_check_point(key) is None:
                    results_to_push.append(data)
                    helper.save_check_point(key, "Indexed")
                   
                # Comment out for production build 
                # helper.delete_check_point(key)
            
            if not len(results_to_push):
                helper.log_info("No results are pending to ingest into {} index.".format(  index ))
                current_page_number = None
                break
            else:
                helper.log_info("Ingesting {} data into {} index.".format(len(results_to_push), index ))
                
                # To create a splunk event
                event = helper.new_event(
                            data        =   json.dumps(results_to_push), 
                            time        =   None, 
                            host        =   None, 
                            index       =   index,
                            source      =   source, 
                            sourcetype  =   sourcetype,
                            done        =   True, 
                            unbroken    =   True
                        )
                ew.write_event(event)  
            
                current_page_number = r_json['next']
            
        time.sleep(const.DEFAULT_SLEEP_TIME)
