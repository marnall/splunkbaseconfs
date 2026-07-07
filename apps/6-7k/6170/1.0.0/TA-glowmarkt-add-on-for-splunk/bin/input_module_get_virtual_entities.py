import os
import sys
import time
import datetime
import json
import utils.auth as rauth
import utils.utils as utils
     
def validate_input(helper, definition):
	pass
	
def collect_events(helper, ew):
    global_account = helper.get_arg("global_account")
    username = global_account["username"]
    password = global_account["password"]
    applicationid = helper.get_arg("applicationid")
    resourceid = helper.get_arg("resourceid")
    
    access_token = rauth.get_access_token(username, password, applicationid)
    
    if(access_token):
        
        helper.log_debug("Calling glowmarkt API - get Virtual Entities")
        url = "https://api.glowmarkt.com/api/v0-1/virtualentity/"
        virtual_entities_response = utils.get_items(helper, access_token, url, applicationid)
        

        for ve in virtual_entities_response:
            helper.log_debug("Writing this VE: " + str(ve))
        
            event = helper.new_event(
                data=json.dumps(ve),
                source=helper.get_input_type(), 
                index=helper.get_output_index(),
                sourcetype=helper.get_sourcetype())
            ew.write_event(event)

    else:
        raise RuntimeError("Unable to obtain access token. Please check the username, password and applicationId")