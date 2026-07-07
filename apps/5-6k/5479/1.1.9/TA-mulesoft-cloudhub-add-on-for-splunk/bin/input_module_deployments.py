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
    env_id = helper.get_arg("env_id")
    
    access_token = rauth.get_access_token(client_id, client_secret) 
    
    
    app_names = gan.get_application_name(access_token,env_id,helper)
    
    if(access_token):
        for app in app_names:
        
            url = "https://anypoint.mulesoft.com/cloudhub/api/v2/applications/"+app+"/deployments"
      
            header = {
                'Authorization': 'Bearer ' + access_token,
                'X-ANYPNT-ENV-ID': env_id
            }
    
            r = requests.get(url, headers=header)
            
            if r.ok:
            
                response_json = r.json()
                
                if response_json is not None:
                    for m_dep in response_json['data']:
        
                        m_dep['domain'] = app
        
                        event = helper.new_event(
                            time=datetime.datetime.now(),
                            data=json.dumps(m_dep),
                            source="mulesoft:deployments",
                            index=helper.get_output_index(),
                            sourcetype="mulesoft:deployments")
                        ew.write_event(event)
            else:
                h_err.handle_error(helper,url,r,org_id,env_id)
 
        


    else:
        raise RuntimeError("Unable to obtain access token.")
