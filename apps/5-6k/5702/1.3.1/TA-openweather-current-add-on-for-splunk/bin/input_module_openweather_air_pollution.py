
# encoding = utf-8

import os
import sys
import time
import datetime
import requests, json

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
    # global_account = definition.parameters.get('global_account', None)
    
    # lat,lon
    geolocalization_str = definition.parameters.get('geolocalization', None)
    geolocalization = geolocalization_str.split(',')
    
    if float(geolocalization[0]) < -90 or float(geolocalization[0]) > 90:
        raise ValueError("Wrong latitude error. Must be a value between -90 and 90 (Inclusive)")
    
    if float(geolocalization[1]) < -180 or float(geolocalization[1]) > 180:
        raise ValueError("Wrong longitude error. Must be a value between -180 and 180 (Inclusive)")
    
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""
    helper.log_debug("action=start, function="+collect_events.__name__)
    
    # gets results from API calls
    res = get_openweather_air_pollution_current(helper)
    
    # write event in JSON format 
    event = helper.new_event(source=helper.get_input_stanza_names(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=res)
    try:
        ew.write_event(event)
    except Exception as e:
        raise e
    
    helper.log_info("action=success")
    return

def get_openweather_air_pollution_current(helper):
    helper.log_debug("action=start, function="+get_openweather_air_pollution_current.__name__)
    
    # input parameters
    opt_global_account = helper.get_arg('global_account')
    opt_geolocalization = helper.get_arg('geolocalization')
    
    # API Key
    api_key = opt_global_account.get("password")
    
    # base_url variable to store url
    base_url = "https://api.openweathermap.org/data/2.5/air_pollution?"
    
    # Geplocalization
    geo_coord=opt_geolocalization.split(',')
    search="&lat="+geo_coord[0]+"&lon="+geo_coord[1]
    
    # complete url address
    complete_url= base_url
    complete_url+= "&appid=" + api_key 
    complete_url+= search
    
    # return response object
    response = requests.get(complete_url)
    
    helper.log_debug("action=collect, status="+str(response.raise_for_status())+", function="+get_openweather_air_pollution_current.__name__)

    return response.text