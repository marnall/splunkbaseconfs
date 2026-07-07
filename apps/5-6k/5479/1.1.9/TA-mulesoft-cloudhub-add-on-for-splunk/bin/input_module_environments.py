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
import utils.handleError as h_err
import requests
     
def validate_input(helper, definition):
	pass
	
def collect_events(helper, ew):
    
    global_account = helper.get_arg("global_account")
    client_id = global_account["username"]
    client_secret = global_account["password"]
    org_id = helper.get_arg("org_id")
    
    
    
    
    
    url = "https://anypoint.mulesoft.com/accounts/api/organizations/"+org_id+"/environments"

    access_token = rauth.get_access_token(client_id, client_secret)
    
    
    if(access_token):

        header = {
            'Authorization': 'Bearer ' + access_token,
        }

        r = requests.get(url, headers=header)

        if r.ok:
 
            response_json = r.json()
    
    
            if(response_json is not None):
                for m_env in response_json['data']:
    
                    event = helper.new_event(
                        data=json.dumps(m_env),
                        source="mulesoft:environments",
                        index=helper.get_output_index(),
                        sourcetype="mulesoft:environments")
                    ew.write_event(event)
        else:
            h_err.handle_error(helper,url,r,org_id,"No_envID")
        


    else:
        raise RuntimeError("Unable to obtain access token.")
