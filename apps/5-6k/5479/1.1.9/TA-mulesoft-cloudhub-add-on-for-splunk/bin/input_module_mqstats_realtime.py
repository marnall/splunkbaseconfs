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

    region = helper.get_arg("region")

    destinations = helper.get_arg("destination_id")


    access_token = rauth.get_access_token(client_id, client_secret)

    if(access_token):

        header = {
            'Authorization': 'Bearer ' + access_token,

        }

        destinations = destinations.replace(" ","")

        url = "https://anypoint.mulesoft.com/mq/stats/api/v1/organizations/"+org_id+"/environments/"+env_id+"/regions/"+region+"/queues?destinationIds="+destinations


        r = requests.get(url, headers=header)
        
        if r.ok:

            response_json = r.json()
    
            json_check = json.dumps(response_json)
    
            if "Destination not found" in json_check:
                helper.log_error("given destination not found")
            else:
                for message_set in response_json:
    
                    message_set['org_id'] = org_id
                    message_set['env_id'] = env_id
                    message_set['region'] = region
    
                    event = helper.new_event(
                        time=datetime.datetime.now(),
                        data=json.dumps(message_set),
                        source="mulesoft:mqstats:realtime",
                        index=helper.get_output_index(),
                        sourcetype="mulesoft:mqstats:realtime")
                    ew.write_event(event)
        
        else:
            h_err.handle_error(helper,url,r,org_id,env_id)

    else:
        raise RuntimeError("Unable to obtain access token.")
