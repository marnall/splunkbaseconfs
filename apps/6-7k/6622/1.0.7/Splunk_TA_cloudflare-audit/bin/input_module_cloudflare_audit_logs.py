# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json
import csv

def writeEvent(helper,ew,data=None):
    if data == None:
        helper.log_critical("No data passed to writeEvent()")
        quit()
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)  
    
def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # api_key = definition.parameters.get('api_key', None)
    pass

def collect_events(helper, ew):
    key = str(helper.get_arg('key'))
    email = str(helper.get_arg('email'))
    reset = helper.get_arg('reset_state')
    timeout = float(helper.get_arg('timeout'))
    audit_url="https://api.cloudflare.com/client/v4/user/audit_logs/?export=true"
    headers={"X-Auth-Key":key,"X-Auth-Email":email,"Content-type":"application/json"}
    
    # Read state. If exists, parse last and lastID from checkpoint, and append "since=" query params to url
    # If reset_state is true, reset state prior
    # lastID was required to stop data pull from always grabbing last event
    stanza = helper.get_input_stanza_names()
    lastID = "first_pull"
    if reset:
        helper.delete_check_point(stanza)
        lastID = "reset_state"
    if helper.get_check_point(stanza) != None:
        last = helper.get_check_point(stanza).split("||")[0]
        lastID = helper.get_check_point(stanza).split("||")[1]
        helper.log_debug(helper.get_check_point(stanza))
        audit_url=audit_url+"&since="+last

    try:
        # Make the request for audit data
        r = helper.send_http_request(audit_url,"GET",headers=headers,verify=True,use_proxy=True,timeout=timeout)
        
        # Find last event, extract the timestamp and ID and send that to the checkpointer
        # Expected data fields are in order as follows: 'Time,ID,Action,Success,Actor Type,Actor ID,Actor IP,Owner ID,Resource Type,Interface,Resource ID,Metadata,NewValue,OldValue'
        latestEventTimeStamp = (r.text).split('\n')[:2][1].split(',')[0]
        latestEventID = (r.text).split('\n')[:2][1].split(',')[1]
        state = latestEventTimeStamp + "||" + latestEventID
        if state != None and len(state)>0 and lastID not in latestEventID:
            # Split the response by new lines and discard the first line, then run for loop to write events
            for data in (r.text).split('\n')[1:]:
                if lastID in data:
                    helper.log_debug("Skipping "+str(data)+" because event_id: "+str(lastID)+" has already been ingested.")
                    pass
                else:
                    writeEvent(helper, ew, data)
            helper.save_check_point(key, state)
            helper.log_debug("Updated latest checkpoint to %s" % (state))
        else:
            helper.log_debug("No new events returned from %s" % (audit_url))
        

    except Exception as e:
        helper.log_error(str(e))