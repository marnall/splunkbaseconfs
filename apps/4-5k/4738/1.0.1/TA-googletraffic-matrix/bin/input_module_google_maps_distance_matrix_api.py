
# encoding = utf-8

import os
import sys
import time
import datetime
import json

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
    # traffic_model = definition.parameters.get('traffic_model', None)
    # origin = definition.parameters.get('origin', None)
    # destination = definition.parameters.get('destination', None)
    pass

def collect_events(helper, ew):
    
    # Define our collection variables
    opt_traffic_model = helper.get_arg('traffic_model')
    opt_origin = helper.get_arg('origin')
    opt_destination = helper.get_arg('destination') 
    
    # get google maps api key
    global_google_maps_api_key = helper.get_global_setting("google_maps_api_key")
    
    # Assign REST variables
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    method = "GET"
    parameters = "traffic_model=" + opt_traffic_model + "&departure_time=now&units=imperial&origins=" + opt_origin + "&destinations=" + opt_destination + "&key=" + global_google_maps_api_key

    # write to the log using specified log level
    helper.log_info("Start call to Google Maps")
    
    # The following code sends rest requests to the Google endpoint.
    response = helper.send_http_request(url, method, parameters)   
    
    # This is where we would handle any errors (status!=200) returned by our API call
    
    # Initialise the variable routes and assign it the value of the JSON response 
    routes = response.json()
    
    i = 0
    for origin in routes['origin_addresses']:
        record = {}
        record['Origin'] = origin

        for details in routes['rows'][i]['elements']:
            record['distance_text'] = details['distance']['text']
            record['distance_val'] = details['distance']['value']
            record['duration_text'] = details['duration']['text']
            record['duration_val'] = details['duration']['value']
            record['traffic_text'] = details['duration_in_traffic']['text']
            record['traffic_val'] = details['duration_in_traffic']['value']
        i = i+1
        write_json = json.dumps(record)
        # Create and write our Splunk event
        event = helper.new_event(
            data=write_json,
            index=helper.get_output_index(),
            source=helper.get_input_type(),
            sourcetype=helper.get_sourcetype()
            )
        ew.write_event(event)