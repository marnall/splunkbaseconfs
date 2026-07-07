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
import requests
import utils.checkpoint as cp
import utils.handleError as h_err

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):

    global_account = helper.get_arg("global_account")
    client_id = global_account["username"]
    client_secret = global_account["password"]
    env_id = helper.get_arg("env_id")
    

    url = "https://anypoint.mulesoft.com/cloudhub/api/notifications?limit=0"
    
    #url = "https://anypoint.mulesoft.com/cloudhub/api/applications/"+domain+"/notifications?limit=0"

    access_token = rauth.get_access_token(client_id, client_secret)

    if(access_token):

        header = {
            'Authorization': 'Bearer ' + access_token,
            'X-ANYPNT-ENV-ID': env_id
        }

        r = requests.get(url, headers=header)

        response_json = r.json()
        
        if r.ok:

            if response_json is not None:
    
    
                for m_not in response_json['data']:
    
                    
                    createdAtTimestamp = m_not['createdAt']
                    datetime_format = '%Y-%m-%dT%H:%M:%S.%fZ'
                    convertTimestamp = datetime.datetime.strptime(createdAtTimestamp, datetime_format)
                    epochTimestamp = (convertTimestamp - datetime.datetime(1970, 1, 1)).total_seconds()

                    m_not['createdAt'] = epochTimestamp
    
                sortedResponse = sorted(response_json['data'], key=lambda x: x['createdAt'])
                
                #key = "notifications_"+str(env_id)
                #helper.delete_check_point(key)
                
                lastCheckpointTimestamp = helper.get_check_point("notifications_"+str(env_id))
                
                if lastCheckpointTimestamp is None:
                    lastCheckpointTimestamp = 0
    
                for m_not in sortedResponse:
    
                    createdAtTimestamp = float(m_not['createdAt'])
    
                    if lastCheckpointTimestamp < createdAtTimestamp:
    
                        event = helper.new_event(
                            data=json.dumps(m_not),
                            source="mulesoft:notifications",
                            index=helper.get_output_index(),
                            sourcetype="mulesoft:notifications")
                        ew.write_event(event)
    
                key = "notifications_"+str(env_id)
                state = m_not['createdAt']
                helper.save_check_point(key, state)        
        
        else:
            h_err.handleError(helper,url,response,"No_orgID",env_id)

    else:
        raise RuntimeError("Unable to obtain access token.")
