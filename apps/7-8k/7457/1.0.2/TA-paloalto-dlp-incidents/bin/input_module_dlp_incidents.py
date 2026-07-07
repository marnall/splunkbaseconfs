
# encoding = utf-8

import os
import sys
import time
import datetime
import base64
import json


def validate_input(helper, definition):
    pass

def isAccessTokenValid(helper,check_point_acstoken):
    acstok = helper.get_check_point(check_point_acstoken)
    helper.log_debug("get access token called")
    #acstok = ''
    
    # If there was a check point access token, return it
    if (acstok not in [None,'']):
        #helper.log_debug("access token is found,access_token={}".format(acstok))
        access_token_cpt = acstok.get("access_token")
        gentime_epoch,access_token = access_token_cpt.split("::")
        elapsed_time = (round((datetime.datetime.utcnow()).timestamp())) - int(gentime_epoch)
        helper.log_debug("Token elapsed time(in seconds): {}".format(elapsed_time))
        expires_in = acstok.get("expires_in")
        helper.log_debug("token_expires_in={} seconds from API".format(expires_in))
        if int(elapsed_time) < (int(expires_in) - 100):
            helper.log_debug("access token is valid from last rest call,hence using it")
            return access_token
            
def get_access_token(helper,check_point_acstoken):
        try:
            access_token = isAccessTokenValid(helper,check_point_acstoken)
            if access_token:
                helper.log_debug("access token is found from method:isAccessTokenValid")
                return access_token
            else:
                helper.log_debug("access token is not found or expired, hence requesting for new token")
                
                username = helper.get_arg("global_account").get("username")
                password = helper.get_arg("global_account").get("password")

                helper.log_debug("username={}".format(username))
                
                credentials = f"{username}:{password}"

                # Encode the credentials to base64
                encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
                
                login_url = "https://auth.apps.paloaltonetworks.com/auth/v1/oauth2/access_token"
                payload = "grant_type=client_credentials"
                headers = {
                  'Content-Type': 'application/x-www-form-urlencoded',
                  'Accept': 'application/json',
                  'Authorization': f'Basic {encoded_credentials}' 
                }
                response = helper.send_http_request(url=login_url, method="POST", parameters=None, payload=payload,
                                        headers=headers, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True) 
                                        
                if not response.ok:
                    helper.log_error("Error in getting access token, response={}".format(json.loads(response.content)))
                    sys.exit()
                else:
                    
                    checkpoint_data = {}
                    
                    access_token = json.loads(response.content)['access_token']
                    expires_in = json.loads(response.content)['expires_in']
                    
                    time_now = round((datetime.datetime.utcnow()).timestamp())
                    checkpoint_data["access_token"] = str(time_now)+"::"+str(access_token)
                    checkpoint_data["expires_in"] = expires_in
                    helper.save_check_point(check_point_acstoken,checkpoint_data)
                    return access_token
        except Exception as e:
            helper.log_error("exception={} in function:get_access_token".format(e))
            sys.exit()
            
def get_start_time(helper,check_point_key):

    # check if check_point_key exists. it exists if the input was already run before successfully
    d=helper.get_check_point(check_point_key)

    if (d not in [None,'']):
        return d["end_time"]
    else:
        #No check_point_key is available. check if user has entered 'Start Time(start_time)' in input
        helper.log_debug("No checkpoint key available")
        d = helper.get_arg("start_time")
        if (d not in [None,'']):
            helper.log_debug("user input of Start Time(start_time):{}".format(d))
            return d
        else:
            seven_days_ago = datetime.datetime.now()  - datetime.timedelta(days=7)
            d = seven_days_ago.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            return d

def fetch_incident_details(helper,ew,domain,incident_id,access_token,check_point_key):
    try:
        payload={}
        headers = {
          'Accept': 'application/json',
          'Authorization': 'Bearer ' + access_token
        }
        # Function to fetch incident details using incident_id
        incident_url = f"{domain}/{incident_id}"
        response = helper.send_http_request(incident_url, method="GET", parameters=None, payload=payload,
                            headers=headers, cookies=None, verify=True, cert=None,
                            timeout=None, use_proxy=True)
        if response.ok:
            opt_custom_sourcetype = helper.get_arg('custom_sourcetype')
            #helper.log_debug(response.content)
            
            data_str = (response.content).decode('utf-8')
            #helper.log_debug(data_str)
            
            # converted to json because getting incident_creation_time from response 
            response_json = json.loads(response.content)
            
            
            
            #response_data = ()
            #helper.log_debug(response_data)
            #data = response_data
            #helper.log_debug(data)
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=opt_custom_sourcetype if opt_custom_sourcetype else helper.get_sourcetype(), data=data_str)
            ew.write_event(event)
            
            # delete below lines 
            #return
            #sys.exit()
            
            checkpoint_data = {}
            
            formatted_end_date = datetime.datetime.strptime(response_json["incident_creation_time"], "%Y-%b-%d %H:%M:%S %Z").strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            #incident_creation_time_plus_1ms = incident_creation_time + datetime.timedelta(milliseconds=1)
            
            #formatted_end_date = incident_creation_time_plus_1ms.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            checkpoint_data["end_time"] = str(formatted_end_date)
            helper.log_debug("saving checkpoint for input={} and end_time={}".format(check_point_key,checkpoint_data))
            helper.save_check_point(check_point_key,checkpoint_data)
        else:
            helper.log_error("error in function:fetch_incident_details. response={}".format(response.content)) 
        
    except Exception as e:
            helper.log_error("exception={} in function:fetch_incident_details".format(e))
            sys.exit()

def collect_events(helper, ew):
    
    
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)

    # For multi instance mod input, args will be returned as a single value.
    opt_start_time = helper.get_arg('start_time')
    opt_page_size = helper.get_arg('page_size')
    
    
    if int(opt_page_size) > 249:
        helper.log_error("page_size is greater than 249. Make sure page_size is less than 249 to continue")
        sys.exit()

    # get all stanza names
    input_name = helper.get_input_stanza_names()
    helper.log_debug("input_name={}".format(input_name))

    check_point_key = "%s_obj_checkpoint" % input_name
    helper.log_debug("check_point_key={}".format(check_point_key))

    check_point_acstoken = "%s_accesstoken" % helper.get_input_stanza_names()
    
    access_token = get_access_token(helper,check_point_acstoken)

    if access_token:
        try:
            helper.log_debug("returned_access_token is success")
            check_point_key = "%s_logs_checkpoint" % helper.get_input_stanza_names()
            
            start_time = get_start_time(helper,check_point_key)
            helper.log_debug("start_time={}".format(start_time))
            
            end_time = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            helper.log_debug("end_time={}".format(end_time))
            
            parsed_end_time = datetime.datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S.%fZ')
            end_time_epoch = int(parsed_end_time.timestamp())
            parsed_start_time = datetime.datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S.%fZ')
            start_time_epoch = int(parsed_start_time.timestamp())
            
            if int(end_time_epoch) > int(start_time_epoch):
                domain = "https://api.dlp.paloaltonetworks.com/v2/api/incidents"
                page_number = 1
                total_pages = 1  # Initialize to enter the loop
                total_events_pointer = 0

                while page_number <= total_pages:
                    url = f"{domain}?ascending=true&end_time={end_time}&page_size={opt_page_size}&start_time={start_time}&page_number={page_number}"
                    payload={}
                    headers = {
                      'Accept': 'application/json',
                      'Authorization': 'Bearer ' + access_token
                    }
                    response = helper.send_http_request(url, method="GET", parameters=None, payload=payload,
                            headers=headers, cookies=None, verify=True, cert=None,
                            timeout=None, use_proxy=True)
                    data = response.json()
            
                    # Extract page and resources information
                    page_info = data.get("page", {})
                    helper.log_debug("page_info={}".format(page_info))
                    resources = data.get("resources", [])
            
                    # Update total_pages from response
                    total_pages = page_info.get("total_pages", 1)
                    total_events = page_info.get("total_elements", 1)
                    
                    if int(total_events) == 1 and page_number == 1:
                        helper.log_debug("No events found. exiting..")
                        break
            
                    for resource in resources:
                        
                        incident_id = resource.get("incident_id")
                        if incident_id:
                            incident_details = fetch_incident_details(helper,ew,domain,incident_id,access_token,check_point_key)
                            total_events_pointer +=1
                        access_token = get_access_token(helper ,check_point_acstoken)
                        # delete below commented lines   
                        #break
            
                    # Increment page number for the next loop iteration
                    page_number += 1
                if  total_events_pointer == total_events:
                    helper.log_info("total_events={} collected successfully".format(total_events))
                    
                else:
                    if not (int(total_events) == 1 and page_number == 1):
                        helper.log_error("modular input not collected all events. total_events={}, collected_events={}. don't worry remaining events will be collected in next schedule".format(total_events,total_events_pointer))
                
                
        except Exception as e:
            helper.log_error("exception={} in function:collect_events".format(e))
            sys.exit()
            