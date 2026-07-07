
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import requests
from datetime import datetime, timedelta, timezone

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
    # etd_api_key = definition.parameters.get('etd_api_key', None)
    # client_id = definition.parameters.get('client_id', None)
    # client_pasword = definition.parameters.get('client_pasword', None)
    # dropdown_list = definition.parameters.get('dropdown_list', None)
    pass

def collect_events(helper, ew):


    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_etd_api_key = helper.get_arg('etd_api_key')
    opt_client_id = helper.get_arg('client_id')
    opt_client_password = helper.get_arg('client_password')
    opt_etd_region = helper.get_arg('etd_region')
    
    # Get the current UTC time
    utc_time = datetime.now(timezone.utc)
    current_time = utc_time

    # Subtract 31 days
    new_time_start = current_time - timedelta(minutes=1)
    new_time_end = current_time



    # Format the new time as a string
    start_date = new_time_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_date = new_time_end.strftime("%Y-%m-%dT%H:%M:%SZ")



    # Authenticatin and endpoint information

    bearer_token = None
    api_url = "https://api." + opt_etd_region + ".etd.cisco.com/v1/oauth/token"  # Replace with the API endpoint URL
    username = opt_client_id # Replace with the API Client ID
    password = opt_client_password # Replace with the API Client Secret

    # Prepare the authentication credentials to get the Access Token
    auth = (username, password)

    headers = {
        "Content-Type": "application/json",  # Assuming the content type of the body data is JSON
        "x-api-key": opt_etd_api_key
    }

    # Make the POST request to the API URL
    response = requests.post(api_url, auth=auth, headers=headers)

    if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            
            # Extract and print the accessToken object
            access_token = data.get('accessToken')
    else:
        print(f"Error: Failed to get access token. Status code: {response.status_code}")

    # Prepare to make the API query using the previous Access Token

    url2 = "https://api." + opt_etd_region + ".etd.cisco.com/v1/messages/search"  # Replace with the API endpoint URL
    body_data = {
        "timestamp": [f"{start_date}",f"{end_date}"],
        "verdicts": ["bec","scam","phishing","malicious","spam","graymail"],
        "pageSize":100
    # Add more key-value pairs for your body data if necessary
    }
        # Add more key-value pairs for your body data if necessary


    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",  # Assuming the content type of the body data is JSON
        "x-api-key": opt_etd_api_key
    }

    response = requests.post(url2, json=body_data, headers=headers)

    i = 0

    if response.status_code == 200:
            response_data = response.json()
            total_size = response_data.get("totalSize")
            nextPageToken = response_data.get("nextPageToken")

            if total_size != 0 and total_size <=100:
                for record in response_data["data"]["messages"]:
                    final = json.dumps(record)
                    event = helper.new_event(final, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
                    ew.write_event(event)

            elif total_size > 100:


                total_cycles = total_size/50
                x = 0
                missing_records = total_size
                data = ""
                #run through all cycles
                while x < total_cycles:
                    response = requests.post(url2, json=body_data, headers=headers)
                    response_data = response.json()
                    nextPageToken = response_data.get("nextPageToken")
                    body_data = {
                    "timestamp": [f"{start_date}",f"{end_date}"],
                    "verdicts": ["bec","scam","phishing","malicious","spam","graymail"],
                    "pageToken": f"{nextPageToken}",
                    "pageSize":50}
                    
                    missing_records = missing_records - 50
                    x +=1
                    for record in response_data["data"]["messages"]:
                        final = json.dumps(record)
                        event = helper.new_event(final, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
                        ew.write_event(event)
            else:
                print("No record found.")
    else:
        print(f"Request failed with status code {response.status_code}: {response.text}")
    
    
    
    
    
    
    
    # get the response headers
    r_headers = response.headers
    # get the response body as text
    r_text = response.text
    # get response body as json. If the body text is not a json string, raise a ValueError
    r_json = response.json()
    # get response cookies
    r_cookies = response.cookies
    # get redirect history
    historical_responses = response.history
    # get response status code
    r_status = response.status_code
    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()

    # The following examples show usage of check pointing related helper functions.
    # save checkpoint
    #helper.save_check_point(key, state)
    # delete checkpoint
    #helper.delete_check_point(key)
    # get checkpoint
    #state = helper.get_check_point(key)

    # To create a splunk event
    #helper.new_event(data, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)


    '''
    # The following example writes a random number as an event. (Multi Instance Mode)
    # Use this code template by default.
    import random
    data = str(random.randint(0,100))
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)
    '''

    '''
    # The following example writes a random number as an event for each input config. (Single Instance Mode)
    # For advanced users, if you want to create single instance mod input, please use this code template.
    # Also, you need to uncomment use_single_instance_mode() above.
    import random
    input_type = helper.get_input_type()
    for stanza_name in helper.get_input_stanza_names():
        data = str(random.randint(0,100))
        event = helper.new_event(source=input_type, index=helper.get_output_index(stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=data)
        ew.write_event(event)
    '''
