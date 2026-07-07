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
    env_id = helper.get_arg("env_id")



    url = "https://anypoint.mulesoft.com/cloudhub/api/v2/applications/"

    global_account = helper.get_arg("global_account")
    access_token = rauth.get_access_token(client_id, client_secret)

    if(access_token):

        header = {
            'Authorization': 'Bearer ' + access_token,
            'X-ANYPNT-ENV-ID': env_id
        }

        r = requests.get(url, headers=header)
        
        if r.ok:

            response_json = r.json()
    
            if not response_json:
                helper.log_info("No applications found in environment " + env_id)
            else:
                for m_app in response_json:
                    m_app['environmentId'] = env_id
    
                    event = helper.new_event(
                        time=datetime.datetime.now(),
                        data=json.dumps(m_app),
                        source="mulesoft:mulesoftapplications",
                        index=helper.get_output_index(),
                        sourcetype="mulesoft:mulesoftapplications")
                    ew.write_event(event)
                    
        else: 
            h_err.handle_error(helper,url,r,"No_orgID",env_id)

    else:
        raise RuntimeError("Unable to obtain access token.")
