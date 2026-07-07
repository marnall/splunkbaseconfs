import os
import sys
import time
import datetime
import json
import utils.auth as rauth
import utils.utils2 as utils
import utils.getAppName as gan
import utils.writeEvent as wev
import utils.retrieveData as rd

 
def validate_input(helper, definition):
	pass
	
def collect_events(helper, ew):
    
    global_account = helper.get_arg("global_account")
    client_id = global_account["username"]
    client_secret = global_account["password"]
    org_id = helper.get_arg("org_id")
    env_id = helper.get_arg("env_id")
    access_token = rauth.get_access_token(client_id, client_secret)
    
    
    app_names = gan.get_application_name(access_token,env_id,helper)
    
    if(access_token):
        
        endpoint = "networkIn"
        
        for app_name in app_names:
            x =  rd.get_data(helper, app_name, env_id, endpoint, access_token, utils.get_items)
        
            wev.write_to_index(helper,app_name, org_id, env_id, endpoint,x,ew)

    else:
        raise RuntimeError("Unable to obtain access token.")
