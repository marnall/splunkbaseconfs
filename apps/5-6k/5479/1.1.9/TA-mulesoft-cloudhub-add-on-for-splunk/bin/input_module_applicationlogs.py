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
import utils.getInstanceIDs as gii
import utils.handleError as h_err

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):

    #Read varialbes from inputs
    global_account = helper.get_arg("global_account")
    client_id = global_account["username"]
    client_secret = global_account["password"]
    domain = helper.get_arg("domain")
    env_id = helper.get_arg("env_id")

    #Obtain the access token
    access_token = rauth.get_access_token(client_id, client_secret)
    
    #If a valid access token has been obtained then proceed
    if(access_token):
    
        deployment_url = "https://anypoint.mulesoft.com/cloudhub/api/v2/applications/"+domain+"/deployments"
        
        instanceIDs = gii.get_instance_ids(access_token,domain,env_id,helper)
        previous_count = 0
        current_count = len(instanceIDs)
        
        header = {
            'Authorization': 'Bearer ' + access_token,
            'X-ANYPNT-ENV-ID': env_id
        }
        
        #Keep iterating so long as no new ids are discovered during the course of the API call
        while previous_count!=current_count:
            
            previous_count = current_count
            
            #Loop over each id in the latest set of instanceIDs
            for i_id in instanceIDs:
                
                
                #helper.delete_check_point("applicationlogs_"+env_id+"_"+i_id)
                offset = helper.get_check_point("applicationlogs_"+env_id+"_"+i_id)
            
                if offset is None:
                    offset = 0
                    
                #Assume initially that not all possible messages are going to be returned by the call
                need_additional_iterations = True
                
                while need_additional_iterations:
                    
                    url = "https://anypoint.mulesoft.com/cloudhub/api/v2/applications/"+domain+"/instances/"+i_id+"/logs?limit=2000&tail=false&offset="+str(offset)    
            
                    #Make the GET request and jsonify the response
                    r = requests.get(url,headers=header)
                    response = r.json()
                    
                    if r.ok:
         
                        if 'data' in response:
                            #Sort the response based on the timestamp key
                            sortedResponse = sorted(response['data'], key=lambda x: x['timestamp'])
                            
                            #For each line in the sortedResponse
                            for d_item in sortedResponse:
                                    
                                d_item['env_id']=env_id
                                d_item['domain']=domain
                                        
                                event = helper.new_event(
                                    time=datetime.datetime.now(),
                                    data=json.dumps(d_item),
                                    source="mulesoft:applicationlogs",
                                    index=helper.get_output_index(),
                                    sourcetype="mulesoft:applicationlogs")
                                ew.write_event(event)
                    
                            #If there were fewer than 2000 results returned then assume there is nothing further to return in this API call
                            if len(sortedResponse)<2000:
                                need_additional_iterations = False
                            
                            else:
                            #If the max number of messages was returned then need to fetch the next block of messages and process those
                                offset+=2000
                                
                        else:
                            need_additional_iterations = False
                            
                    else:
                        h_err.handle_error(helper,url,r,"No_orgID" ,env_id)
                        need_additional_iterations = False
                
                if len(sortedResponse)>0:
                    key = "applicationlogs_"+env_id+"_"+i_id
                    state = offset+len(sortedResponse)
                    #state = sortedResponse[-1]['timestamp']
                    helper.save_check_point(key, state)
                      
            #Once events have been written check to see if any further deployments have been added since the call was made
            instanceIDs = gii.get_instance_ids(access_token,domain,env_id,helper)
            current_count = len(instanceIDs)
   
    else:
        raise RuntimeError("Unable to obtain access token.")
            

