
# encoding = utf-8


import os
import sys
import time
from datetime import datetime, timedelta, timezone
import json
import splunklib.client as client
"""
    IMPORTANT
    Edit only collect_events function.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""

"""
#if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
"""

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# For information on the methods and how modular inputs work see:
# 
#   https://docs.splunk.com/DocumentationStatic/PythonSDK/1.6.11/modularinput.html
# 
# For information on the helper methods available see the above link and:
#
#   https://docs.splunk.com/Documentation/AddonBuilder/3.0.2/UserGuide/PythonHelperFunctions
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

CHECKPOINT_TIME = "intellipicheckpoint"
CHECKPOINT_EXPIRES = 'intelli_token_expires'

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
   
    session_key = helper.context_meta['session_key']
    args = {'token': session_key}
    service = client.connect(**args)
    
    storage_passwords = service.storage_passwords
   
    new_token = None
    returned_credential = None
    helper.log_info("Version 1.6.2 Builder version 4.4.1")
    # Retrieve a storage password (token) if there is one stored
    if len(storage_passwords) > 0:
        returned_credential = [k for k in storage_passwords if k.content.get('realm')=='IDaaS' and k.content.get('username')=='entrust']
        # Double check whether our data is there. There could be other data in storage
        if len(returned_credential) > 0:
            helper.log_info("Retrieve token from storage_passwords")
            auth_token = returned_credential[0].content.clear_password
        else:
            auth_token = None
    else:
        auth_token = None
    
    # Get the time checkpoint, initialize it if empty
    # Get the auth token and expiry time it it exists
    checkpoint_time = helper.get_check_point(CHECKPOINT_TIME)
    
    expires = helper.get_check_point(CHECKPOINT_EXPIRES)

    if expires is not None and auth_token is not None:
        helper.log_info("Found token")
        # There is datetime.timezone.utc in Python 3.2+
        now = datetime.now(timezone.utc)
        expires = datetime.strptime(expires, "%Y-%m-%dT%H:%M:%SZ")
        # expires is utc time, but naive object. Need to make to aware type before compare with another aware type
        expires = expires.replace(tzinfo=timezone.utc)
        if now > expires:
            helper.log_info("Token is expired")
            expires = None
            auth_token = None
        else:
            helper.log_info("Token is not expired. expires: %s" % expires)

    if (checkpoint_time is None):
        helper.log_info("Checkpoint is null")
        start_time = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        start_time = checkpoint_time
        helper.log_info("Got checkpoint time: %s" % start_time)
        # start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
    
    # Set end time to now
    end_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    helper.log_info("Start Time: %s" % start_time)
    helper.log_info("End Time: %s" % end_time)
      
    # Get the interval setting
    stanza = helper.get_input_stanza()
    input_settings = list(stanza.values())[0]
    interval = input_settings.get("interval")

    helper.log_info("Interval Value: %s" % interval)

    # Verify the interval value is set
    if interval is None:
        helper.log_error("interval value not set")
        return

    # Verify the interval value is not less than 30 seconds to query Identity as a Service 
    if int(interval) < 30:
        helper.log_error("interval must be at least 30 seconds but got %d" % interval)
        return
    
    # Get the application settings for authenticating to Intellitrust
    # This value is the a string containing the JSON application paramters from Identity as a Service
    secret = helper.get_global_setting("secret")

    if secret is None:
        helper.log_error("Identity as a Service application parameters not set. Check add-on configuration settings")
        return

    # Convert the string to JSON
    application_settings = json.loads(secret)

    # Get the account hostname
    hostname = application_settings.get("hostname")
    application_id = application_settings.get("applicationId")
    shared_secret = application_settings.get("sharedSecret")

    if hostname is None:
        helper.log_error("hostname missing from application settings. Check add-on configuration settings")
        return
    
    if application_id is None:
        helper.log_error("application ID missing from application settings. Check add-on configuration settings")
        return

    if shared_secret is None:
        helper.log_error("shared secret missing from application settings. Check add-on configuration settings")
        return

    helper.log_info("hostname: %s" % hostname)
    helper.log_info("applicationId: %s" % application_id)
   
    # Configure the HTTP request parameters

    if auth_token is None:
        new_token = bool(1)
        helper.log_info("Authenticating to Identity as a Service...")
        auth_url = "https://%s/api/web/v1/adminapi/authenticate" % hostname
        headers = { "Content-Type" : "application/json" }
        payload = { "applicationId": application_id, "sharedSecret": shared_secret }
        auth_response = helper.send_http_request(
            auth_url, 
            "POST", 
            None,
            payload,
            headers, 
            None, # cookies
            True, # Indicates whether the SSL certificate will be verified.
            None, # path to SSL client cert
            None, # timout
            False # Indicates whether to use a proxy. If True, the proxy in the Add-on Builder Configuration settings is used.
        )

        auth_response = auth_response.json()

        error_code = auth_response.get("errorCode")

        if error_code is not None:
            helper.log_error("Error authenticating to Identity as a Service: %s" % error_code)
            return
        else:
            helper.log_info("Got auth token")

        expires = auth_response.get("expirationTime")
        helper.log_info("Expires at: %s" % expires)
        if type(expires) is not str:
            expires = expires.strftime("%Y-%m-%dT%H:%M:%SZ")
        helper.save_check_point(CHECKPOINT_EXPIRES, expires)
        auth_token = auth_response.get("authToken")
    # end if

    headers = { 
        "Content-Type" : "application/json",
        "Authorization": auth_token
    }
    
    # Get Audits from Intellitrust
    # Send REST requests to paginated audit endpoint based on customer input configuration in Splunk

    payload = {
        "limit": 100,
        "searchByAttributes": [{
            "name": "startTime",
            "operator": "GREATER_THAN_OR_EQUAL", 
            "value": start_time 
        }, {
            "name": "endTime",
            "operator": "LESS_THAN_OR_EQUAL",
            "value": end_time
        }]
    }
    
    # Get the Add-on setting for the types of audits to fetch from Identity as a Service
    # 0 = Authentication
    # 1 = Management
    # 2 = Both
    include_events = helper.get_arg("include_events")

    if include_events != "2":
        event_type = "AUTHENTICATION" if include_events == "0" else "MANAGEMENT"
        payload.get("searchByAttributes").append({
            "name": "category",
            "operator": "EQUALS",
            "value": event_type
        })

    helper.log_info("Including events: %s" % "AUTHENTICATION" if include_events == "0" else "MANAGEMENT" if include_events == "1" else "BOTH")

    finished = False;
    cursor = None;
    event_count = 0
    
    while (finished == False):
        if cursor is not None:
            payload.update({ "cursor":  cursor })

        siem_response = helper.send_http_request(
            "https://%s/api/web/v1/reports/auditeventspaged/siem" % hostname, 
            "POST", 
            None,
           payload,
            headers, 
            None, # cookies
            True, # Indicates whether the SSL certificate will be verified.
            None, # path to SSL client cert
            None, # timout
            False # Indicates whether to use a proxy. If True, the proxy in the Add-on Builder Configuration settings is used.
        )

        siem_response = siem_response.json()

        error_code = siem_response.get("errorCode")

        if error_code is not None:
            helper.log_error("Error fetching audit events from Identity as a Service: %s" % error_code)
            # In the case add-on restart and previous token will be invalid, will error out as invalid token ex. We will have to miss one poll 
            if returned_credential is not None and len(returned_credential) > 0:
                storage_passwords.delete("entrust", "IDaaS")
            return

        results = siem_response.get("results")
        next_cursor = siem_response.get("paging").get("nextCursor")
        
        if results is not None:
            helper.log_info("Got %d events" % len(results))
            event_count += len(results)
            saveEvents(helper, ew, results)
            # Update the checkpoint time in each loop, in case next loop error out
            helper.log_info("Saving checkpoint time: %s" % end_time)
            helper.save_check_point(CHECKPOINT_TIME, end_time)
        if next_cursor is not None:
            cursor = next_cursor
        else:
            finished = True;
    # end while

    helper.log_info("Finished ingesting Identity as a Service audit events. Ingested %d events" % event_count)
    
    # This is the case previous token expired, we update new token in storage. There is no update api, so we delete and create
    if new_token is not None and returned_credential is not None and len(returned_credential) > 0:
        helper.log_info("Update token in storage_passwords")
        new_token = None
        storage_passwords.delete("entrust","IDaaS")
        storage_passwords.create(auth_token, "entrust", "IDaaS")
    
    # This is the case addon first starts, saving token first time
    if returned_credential is not None and len(returned_credential) == 0:
        helper.log_info("Create token in storage_passwords")
        storage_passwords.create(auth_token, "entrust", "IDaaS")



def saveEvents(helper, ew, data):    
    for oneData in data:
        # Create new Splunk  Event
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(oneData))
        ew.write_event(event)

