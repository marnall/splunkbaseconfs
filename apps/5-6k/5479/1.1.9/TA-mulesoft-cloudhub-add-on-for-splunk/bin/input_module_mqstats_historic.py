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

    #Read user input values as variables
    global_account = helper.get_arg("global_account")
    client_id = global_account["username"]
    client_secret = global_account["password"]
    org_id = helper.get_arg("org_id")
    env_id = helper.get_arg("env_id")
    region = helper.get_arg("region")
    destinations = helper.get_arg("destination_id")

    #Obtain the access token
    access_token = rauth.get_access_token(client_id, client_secret)

    if(access_token):

        #Define the header
        header = {
            'Authorization': 'Bearer ' + access_token,
        }

        #Remove any extraneous spaces from the destinations list
        destinations = destinations.replace(" ","")
        destinations = destinations.split(",")

        #Loop over each destination
        for destination in destinations:
            
            #Read the checkpoint for the current desintation
            lastCheckpointTimestamp = helper.get_check_point("mqstats_historic_"+str(org_id)+"_"+str(destination))
            
            
            #If there is no checkpoint then set a start time of 1st of March 2021
            if lastCheckpointTimestamp is None:
                
                '''
                lastCheckpointTimestamp = "2021-03-01T00:00:00.000Z"
                datetime_format = '%Y-%m-%dT%H:%M:%S.%fZ'
                convertTimestamp = datetime.datetime.strptime(createdAtTimestamp, datetime_format)
                lastCheckpointTimestamp = (convertTimestamp - datetime.datetime(1970, 1, 1)).total_seconds() - 
                '''
                lastCheckpointTimestamp = datetime.datetime.now().timestamp() - 60
            
            
            #datetime.datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S.%f')
            
            #2016-02-28T16:41:41.090Z
            
            #Defined the start and end times (and the period)
            startDate_epoch = lastCheckpointTimestamp
            endDate_epoch = datetime.datetime.now().timestamp()
            #Convert these to a format that is usable by the API
            
            #Fri, 11 Jul 2015 08:49:37 GMT
            
            #startDate = datetime.datetime.fromtimestamp(startDate_epoch).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            
            
            
            #endDate = datetime.datetime.fromtimestamp(endDate_epoch).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            
            startDate = datetime.datetime.fromtimestamp(startDate_epoch).strftime("%a, %e %b %Y %H:%M:%S")+" BST"
            
            endDate = datetime.datetime.fromtimestamp(endDate_epoch).strftime("%a, %e %b %Y %H:%M:%S")+" BST"
            
            
            period = 60

            #startDate.replace("  "," ")

            #startDate = startDate[:-4]+"Z"
            #endDate = endDate[:-4]+"Z"

            #Create the URL for the current destination
            url = "https://anypoint.mulesoft.com/mq/stats/api/v1/organizations/"+org_id+"/environments/"+env_id+"/regions/"+region+"/queues/"+destination+"?startDate="+startDate+"&endDate="+endDate
    
            #Make the request
            r = requests.get(url, headers=header)
            
            #If the request does not contain an error
            if r.ok:
    
                #Get the json from the response object
                response_json = r.json()
                json_check = json.dumps(response_json)
                
                #If the destination doesn't exist then log an error message
                if "Destination not found" in json_check:
                    helper.log_error("given destination not found")
                else:
                    
                    #Read date 

                    message_set['org_id'] = org_id
                    message_set['env_id'] = env_id
                    message_set['region'] = region
        
                    event = helper.new_event(
                        time=datetime.datetime.now(),
                        data=json.dumps(message_set),
                        source="mulesoft:mqstats:historic",
                        index=helper.get_output_index(),
                        sourcetype="mulesoft:mqstats:historic")
                    ew.write_event(event)
                    
                    key = "mqstats_historic_"+str(org_id)+"_"+str(destination)
                    state = endDate_epoch
                    helper.save_check_point(key, state) 
            
            else:
                h_err.handle_error(helper,url,r,org_id,env_id)

    else:
        raise RuntimeError("Unable to obtain access token.")

    

