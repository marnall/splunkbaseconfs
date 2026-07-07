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



    url = "https://anypoint.mulesoft.com/accounts/api/me/"

    access_token = rauth.get_access_token(client_id, client_secret)
    
    if(access_token):

        header = {
            'Authorization': 'Bearer ' + access_token,
        }

        r = requests.get(url, headers=header)
        
        if r.ok:

            response_json = r.json()
    
            memberOrgs = []
            for mo in response_json['user']['memberOfOrganizations']:
    
                url = "https://anypoint.mulesoft.com/accounts/api/organizations/"+mo['id']+"/environments"
    
                r_env = requests.get(url, headers=header)
                
                if r_env.ok:
    
                    response_env_json = r_env.json()
        
                    for environment in response_env_json['data']:
        
                        if mo['parentId']:
                            org_env_data = {
                                'orgID': mo['id'],
                                'orgName': mo['name'],
                                'envID': environment['id'],
                                'envName': environment['name'],
                                'parentOrgID': mo['parentId'],
                                'parentOrgName': mo['parentName'],
                                }
        
                        else:
                            org_env_data = {
                                'orgID': mo['id'],
                                'orgName': mo['name'],
                                'envID': environment['id'],
                                'envName': environment['name'],
                                }
        
                        event = helper.new_event(
                            data=json.dumps(org_env_data),
                            source="mulesoft:discovery",
                            index=helper.get_output_index(),
                            sourcetype="mulesoft:discovery")
                        ew.write_event(event)
                else:
                    h_err.handle_error(helper,url,r,"No_orgID","No_envID")

        else:
            h_err.handle_error(helper,url,r,"No_orgID","No_envID")

    else:
        raise RuntimeError("Unable to obtain access token.")
        
