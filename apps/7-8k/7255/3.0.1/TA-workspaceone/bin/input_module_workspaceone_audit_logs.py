
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import dateutil.parser


def get_start_date(helper, check_point_key):

    # Try to get a date from the check point first
    d = helper.get_check_point(check_point_key)

    # If there was a check point date, retun it.
    if (d not in [None,'']):
        return d["end_date"]
    else:
        # No check point date, so look if a start date was specified as an argument
        d = helper.get_arg("since_date")
        helper.log_debug("start_date(since_date)={}".format(d))
        if (d not in [None,'']):
            return d
        else:
            # If there was no start date specified, default to 7 days ago
            start_date = ((round((datetime.datetime.utcnow()).timestamp())) - int(7*86400))*1000
            
            helper.log_debug("user input for since_date is None,defaulting since date to last 7 days. start_date={}".format(start_date))
            return start_date
            
def isAccessTokenValid(helper,check_point_acstoken):
    acstok = helper.get_check_point(check_point_acstoken)
    helper.log_debug("get access token called")
    #acstok = ''
    
    # If there was a check point access token, return it
    if (acstok not in [None,'']):
        #helper.log_debug("access token is found,access_token={}".format(acstok))
        access_token_cpt = acstok.get("access_token")
        gentime_epoch,access_token = access_token_cpt.split("::")
        #helper.log_debug("gentime={},access_token={}".format(gentime_epoch,access_token))
        #gentitmeconvert = parser.parse(gentime)
        #helper.log_debug("Tokent generated last time:{}".format(gentime_epoch))
        elapsed_time = (round((datetime.datetime.utcnow()).timestamp())) - int(gentime_epoch)
        helper.log_debug("Token elapsed time(in seconds): {}".format(elapsed_time))
        expires_in = acstok.get("expires_in")
        helper.log_debug("cpt_expires_in={}".format(expires_in))
        if int(elapsed_time) < (int(expires_in) - 300):
            helper.log_debug("access token is valid from last rest call,hence using it")
            return access_token
            
def get_access_token(helper,login_url,client_id,client_secret,check_point_acstoken):
        try:
            access_token = isAccessTokenValid(helper,check_point_acstoken)
            if access_token:
                helper.log_debug("access token is found from method:isAccessTokenValid")
                return access_token
            else:
                helper.log_debug("access token is not found or expired, hence requesting for new token")
                payload = f"client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials"
                headers = {
                            'Content-Type': 'application/x-www-form-urlencoded'
                }
                
                #helper.log_debug("login_url={},payload={},headers={}".format(login_url,payload,headers))
                
                response = helper.send_http_request(url=login_url, method="POST", parameters=None, payload=payload,
                                        headers=headers, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True) 
                                        
                if not response.ok:
                    helper.log_error("Error in getting access token, response={}".format(json.loads(response.content)))
                    sys.exi()
                else:
                    
                    checkpoint_data = {}
                    
                    access_token = json.loads(response.content)['access_token']
                    expires_in = json.loads(response.content)['expires_in']
                    
                    time_now = round((datetime.datetime.utcnow()).timestamp())
                    checkpoint_data["access_token"] = str(time_now)+"::"+str(access_token)
                    checkpoint_data["expires_in"] = expires_in
                    helper.save_check_point(check_point_acstoken,checkpoint_data)
                    #helper.log_debug("access_check_point_data={}".format(checkpoint_data))
                        
                    return access_token
                    
        except Exception as e:
            helper.log_error("exception={} in function:get_access_token".format(e))
            sys.exit()

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    
    loglevel = helper.get_log_level()
    
    checkpoint_data = {}
    opt_auth_url = helper.get_arg('auth_url')
    helper.log_debug("auth_url={}".format(opt_auth_url))
    opt_data_url = helper.get_arg('data_url')
    helper.log_debug("data_url={}".format(opt_data_url))
    opt_since_date = helper.get_arg('since_date')
    helper.log_debug("user input since_date={}".format(opt_since_date))
    
    #start_date = str(get_str_date(helper,definition))
    #helper.log_debug("start_date={}".format(start_date)
    end_date = round((datetime.datetime.utcnow()).timestamp()) * 1000
    helper.log_debug("end_date={}".format(end_date))
    
    global_account = helper.get_arg("global_account")
    client_id = global_account["username"]
    client_secret = global_account["password"]
    
    check_point_acstoken = "%s_accesstoken" % helper.get_input_stanza_names()
    
    access_token = get_access_token(helper,opt_auth_url,client_id,client_secret ,check_point_acstoken)
    
    if access_token:
        
        helper.log_debug("returned_access_token is success")
        headers = {
            'Authorization': 'Bearer ' + access_token,
            'Content-Type': 'application/json'
        }
        
        check_point_key = "%s_logs_checkpoint" % helper.get_input_stanza_names()

        start_date = str(get_start_date(helper,check_point_key))
        helper.log_debug("start_date={}".format(start_date))
        if int(end_date) > int(start_date):
            url = f"{opt_data_url}/analytics/reports/audit?fromMillis={start_date}&toMillis={end_date}"
            helper.log_debug("data_url={}".format(url))
            
            response = helper.send_http_request(url, method="GET", parameters=None, payload=None,
                                    headers=headers, cookies=None, verify=True, cert=None,
                                    timeout=None, use_proxy=True)

            if response.ok:
                response_data = response.json()['data']
                for record in response_data:
                    #data = json.dumps(record)
                    data = str(record)
                    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
                    ew.write_event(event)
                checkpoint_data["end_date"] = str(end_date)
                helper.log_debug("saving checkpoint for input={} and end_date={}".format(check_point_key,checkpoint_data))
                helper.save_check_point(check_point_key,checkpoint_data)
                helper.log_info("ingested all events successfully")
            else:
                helper.log_error("error in collecting events. response={}".format(response.json()))            

        else:
            helper.log_info("start_date is greater than end_date. exiting")
            
    else:
        helper.log_info("access is not returned. exiting")
                    
    
