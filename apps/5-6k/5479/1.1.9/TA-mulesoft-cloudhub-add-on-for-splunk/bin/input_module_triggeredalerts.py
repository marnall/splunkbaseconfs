import os
import sys
import time
from datetime import datetime
import json
import utils.auth as rauth
import utils.utils2 as utils
import utils.getAppName as gan
import utils.writeEvent as wev
import utils.retrieveData as rd
import requests
import utils.handleError as h_err


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):

    global_account = helper.get_arg("global_account")
    client_id = global_account["username"]
    client_secret = global_account["password"]
    org_id = helper.get_arg("org_id")
    env_id = helper.get_arg("env_id")

    url = "https://anypoint.mulesoft.com/cloudhub/api/v2/alerts/"

    access_token = rauth.get_access_token(client_id, client_secret)
    
    if(access_token):

        header = {
            'Authorization': 'Bearer ' + access_token,
            'X-ANYPNT-ENV-ID': env_id
        }

        r = requests.get(url, headers=header)

        response_json = r.json()

        if r.ok:

            if response_json is not None and 'data' in response_json:
    
                for m_alert in response_json['data']:
    
                    sub_url = "https://anypoint.mulesoft.com/cloudhub/api/v2/alerts/"+m_alert['id']+"/history"
    
                    sub_r = requests.get(sub_url,headers=header)
                    sub_response_json = sub_r.json()
                    alerts = sub_response_json['data']
                    sortedResponse = sorted(alerts, key=lambda x: x['triggeredAt'])
                    helper.log_info(sortedResponse)
    
                    for t_alert in sortedResponse:
    
                        lastCheckpointTimestamp = helper.get_check_point('alerts_'+env_id+"_"+m_alert['id'])
    
                        if lastCheckpointTimestamp is None:
                            lastCheckpointTimestamp = 0
    
                        triggeredAtTimestamp = int(t_alert['triggeredAt'])
    
                        if lastCheckpointTimestamp < triggeredAtTimestamp:
    
                            t_alert['environmentId'] = env_id
                            t_alert['organizationId'] = org_id
                            t_alert['alertId'] = m_alert['id']
    
                            event = helper.new_event(
                                    data=json.dumps(t_alert),
                                    source="mulesoft:triggeredalerts",
                                    index=helper.get_output_index(),
                                    sourcetype="mulesoft:triggeredalerts")
                            ew.write_event(event)
    
                            # save checkpoint
                            key = 'alerts_'+env_id+"_"+m_alert['id']
                            state = t_alert['triggeredAt']
                            helper.save_check_point(key, state)
                            
        else:
            h_err.handle_error(helper,url,r,"No_orgID",env_id)

    else:
        raise RuntimeError("Unable to obtain access token.")



