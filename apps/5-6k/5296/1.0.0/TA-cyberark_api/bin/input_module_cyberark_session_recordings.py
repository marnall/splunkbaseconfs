# encoding = utf-8
import sys
import time
import ast
import json
import re
import datetime

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    #config the vars
    opt_global_account = helper.get_arg('global_account')
    username = opt_global_account['username']
    global_hostname_or_ip = helper.get_global_setting("hostname_or_ip")
    global_logon_endpoint = helper.get_arg("logon_endpoint_url")
    global_recording_endpoint = helper.get_arg("recording_endpoint_url")
    global_item_limit = helper.get_arg("item_limit")
    global_source = helper.get_input_type()
    global_source_type = helper.get_sourcetype()
    global_index = helper.get_output_index()
    global_account = helper.get_arg('global_account')
    dict_headers = {"Content-Type": "application/json"}
    dict_payload = {"username": global_account['username'], "password": global_account['password']}
    global_from_time_date=helper.get_arg("fromtime")
    datetime_check = datetime.datetime.strptime(global_from_time_date,"%Y-%m-%dT%H:%M:%S")
    global_from_time = time.mktime(datetime_check.timetuple())
    global_to_time_datetime=datetime.datetime.fromtimestamp(float(global_from_time))
    global_to_time_datetime_delta = global_to_time_datetime + datetime.timedelta(hours=1)
    global_to_time_epoch = time.mktime(global_to_time_datetime_delta.timetuple())
    global_to_time=int(global_to_time_epoch)
    global_from_time=int(global_from_time)
    access_token_expiration = time.time() + 300
    key = global_source_type + username
    last_checkpoint_time = helper.get_check_point(key)
    
    #Datetime checks
    try:
        if bool(datetime_check and bool((re.search("^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})",str(datetime_check))))) and (isinstance(last_checkpoint_time, (type(None)))) == True:
            starting_first_time="|Starting for first Time:{}|".format(datetime_check)
            helper.log_info(starting_first_time)
        elif last_checkpoint_time:
            global_from_time=last_checkpoint_time
            starting_from_checkpoint="|Starting from last known checkpoint:{}|".format(global_from_time)
            helper.log_info(starting_from_checkpoint)
            global_to_time_datetime=datetime.datetime.fromtimestamp(float(global_from_time))
            global_to_time_datetime_delta = global_to_time_datetime + datetime.timedelta(hours=1)
            global_to_time_epoch = time.mktime(global_to_time_datetime_delta.timetuple())
            global_to_time=int(global_to_time_epoch)
            global_from_time=int(global_from_time)
        elif bool(not global_from_time_date and (isinstance(last_checkpoint_time, (type(None))))) == True:
            err="Missing:(FromTime and last_checkpoint_time), program can`t run without starting point"
            helper.log_error(err)
            sys.exit()
        elif not global_from_time_date or bool(re.search("^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})",str(global_from_time_date))) == False:
            err = "Input configuration validation error. Wrong updated_timestamp format or missing value (FromTime)"
            helper.log_error(err)
            sys.exit()
    except Exception as e:
        err="Erorr during starting point initialization" + str(e)
        helper.log_error(err)
        sys.exit()
        
    #get the logon
    try:
        login_response = helper.send_http_request("https://"+global_hostname_or_ip+global_logon_endpoint ,"POST", parameters=None, payload=dict_payload, headers=dict_headers, cookies=None, verify=False, cert=None, timeout=180, use_proxy=False)
    except Exception as e:
        err = "Error during CyberArk login. Check credentials or URL.\nException: "+str(e)
        helper.log_error(err)
        sys.exit()
    #extract the key
    try:
        data = ast.literal_eval(login_response.text)
        dict_headers = {"Authorization":str(data)}
        dict_parameters = {"limit": global_item_limit}
    except Exception as e:
        err = "Cannot get CyberArkLogonResult in login response.\nException: "+str(e)
        helper.log_error(err)
        sys.exit()
        
    #Looping
    try:
        while True:
            if  time.time() > access_token_expiration:
                #get the logon
                try:
                    login_response = helper.send_http_request("https://"+global_hostname_or_ip+global_logon_endpoint ,"POST", parameters=None, payload=dict_payload, headers=dict_headers, cookies=None, verify=False, cert=None, timeout=180, use_proxy=False)
                    access_token_expiration = time.time() + 300
                except Exception as e:
                    err = "Error during CyberArk login. Check credentials or URL.Loop part\nException: "+str(e)
                    helper.log_error(err)
                    sys.exit()
                #extract the key
                
                try:
                    data = ast.literal_eval(login_response.text)
                    dict_headers = {"Authorization":str(data)}
                    dict_parameters = {"limit": global_item_limit}
                except Exception as e:
                    err = "Cannot get CyberArkLogonResult in login response. Loop part\nException: "+str(e)
                    helper.log_error(err)
                    sys.exit()

            #get all accounts
            try:
                    accounts_response = helper.send_http_request("https://"+global_hostname_or_ip+global_recording_endpoint+"?FromTime="+str(global_from_time)+"&ToTime="+str(global_to_time)+"&limit=1000", "GET", parameters=dict_parameters, payload=None, headers=dict_headers, cookies=None, verify=False, cert=None, timeout=180, use_proxy=False)
                    json_object_recording = accounts_response.json()
                    recordings_total=json_object_recording['Total']
                    if recordings_total == 0 and time.time() - global_to_time < 3600:
                        helper.save_check_point(key,global_from_time)
                        info = "Newly recorderd sessions were not found at this time. Total = 0"
                        helper.log_info(info)
                        sys.exit()
                    info_date_from_time=datetime.datetime.fromtimestamp(float(global_from_time))
                    info_date_to_time=datetime.datetime.fromtimestamp(float(global_to_time))
                    a = "(( FROM:"+str(info_date_from_time)+" => "+" TO:"+str(info_date_to_time)+" TOTAL="+str(recordings_total)+" ))"
                    helper.log_info(a)
                    length =len(json_object_recording['Recordings'])
                    for i in range(length):
                        ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=json.dumps(json_object_recording['Recordings'][i])))
                    #Re-configure the time
                    global_from_time=global_to_time
                    global_to_time_datetime=datetime.datetime.fromtimestamp(global_from_time)
                    global_to_time_datetime_delta = global_to_time_datetime + datetime.timedelta(hours=1)
                    global_to_time_epoch=time.mktime(global_to_time_datetime_delta.timetuple())
                    global_to_time=int(global_to_time_epoch)
                    helper.save_check_point(key,global_from_time)
            except Exception as e:
                err = "Error during CyberArk get all accounts method. Response cannot be converted to json. Check credentials or URL.\nException: "+str(e)
                helper.log_error(err)
                sys.exit()
                
    except Exception as e:
        err = "Error during event construction. Response cannot be converted to json. Check credentials or URL.\nException: "+str(e)
        helper.log_error(err)
        sys.exit()
