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
import utils.handleError as h_err

def validate_input(helper, definition):
	pass

def collect_events(helper, ew):

    global_account = helper.get_arg("global_account")
    client_id = global_account["username"]
    client_secret = global_account["password"]
    access_token = rauth.get_access_token(client_id, client_secret)
    org_id = helper.get_arg("org_id")
    env_id = helper.get_arg("env_id")

    if(access_token):

        regions_url="https://anypoint.mulesoft.com/mq/admin/api/v1/organizations/"+org_id+"/environments/"+env_id+"/regions"
        header = {
            'Authorization': 'Bearer ' + access_token
        }

        #get list of regions
        regions = requests.get(regions_url, headers=header)
        #loop over list of regions, returning a list of region_ids
        regions_json = regions.json()
        
        if regions.ok:
    
            region_ids=[]
            for region in regions_json:
                region_id=region['regionId']
                region_ids.append(region_id)
    
    
            for region_id in region_ids:
                destinations_url="https://anypoint.mulesoft.com/mq/admin/api/v1/organizations/"+org_id+"/environments/"+env_id+"/regions/"+region_id+"/destinations"
    
                # get list of queues in each region (destination)
                destinations = requests.get(destinations_url, headers=header)
    
                #if there are queues in that region (destination), get queueId and add to queue_ids list
                destinations_json = destinations.json()
     
                if destinations.ok:
                    
                    queue_ids = []
                    for destination in destinations_json:
                        queue_ids.append(destination['queueId'])
    
                    for queue_id in queue_ids:
                        queue_url="https://anypoint.mulesoft.com/mq/admin/api/v1/organizations/"+org_id+"/environments/"+env_id+"/regions/"+region_id+"/destinations/queues/"+queue_id
                        
                        queue = requests.get(queue_url, headers=header)
                        
                        if queue.ok:
                            queues={
            	                "orgId":org_id,
            	                "envId":env_id,
            	                "regionId":region_id,
            	                "data":queue,
                                }
            
                            event = helper.new_event(
                                time=datetime.datetime.now(),
                                data=json.dumps(queues),
                                source="mulesoft:queuediscovery",
                                index=helper.get_output_index(),
                                sourcetype="mulesoft:queuediscovery")
                            ew.write_event(event)
                        
                        else:
                            h_err.handle_error=(helper,queue_url,queue,org_id,env_id)
                
                else:
                    h_err.handle_error(helper,destinations_url,destinations,org_id,env_id)
                    
        else:
            h_err.handle_error(helper,regions_url,regions,org_id,env_id)
            

    else:
        raise RuntimeError("Unable to obtain access token.")
