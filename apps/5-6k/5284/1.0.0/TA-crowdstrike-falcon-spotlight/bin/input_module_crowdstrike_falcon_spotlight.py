# encoding = utf-8
import time
import json
import urllib
import re
import sys

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
return True
'''

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass

def collect_events(helper, ew):
    #Variables are set as follow
    opt_global_account = helper.get_arg('global_account')
    username = opt_global_account['username']
    password = opt_global_account['password']
    opt_api_v1_endpoint = helper.get_arg('api_v1_endpoint')
    opt_api_v2_endpoint = helper.get_arg('api_v2_endpoint')
    opt_access_token_endpoint = helper.get_arg('access_token_endpoint')
    api_fqdn = helper.get_global_setting('hostname_or_ip')
    global_source = helper.get_input_type()
    global_source_type = helper.get_sourcetype()
    global_index = helper.get_output_index()
    headers_token = {'Content-Type': 'application/x-www-form-urlencoded', "accept": "application/json"}
    data = "client_id={}&client_secret={}&grant_type=client_credentials".format(username, password)
    key = global_source_type + username
    last_checkpoint_time = helper.get_check_point(key)
    updated_timestamp=helper.get_arg('updated_timestamp')
    logged_by_account="|Logged by Account:{}|".format(username)
    opt_limit=str(helper.get_arg('limit'))
    #Starting point validations
    
    try:
        if bool(updated_timestamp and bool((re.search("^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})",updated_timestamp)))) and (isinstance(last_checkpoint_time, (type(None)))) == True:
            starting_first_time=logged_by_account+"|No checkpoint has been found.Initial run, is starting from date:{}|".format(updated_timestamp)
            helper.log_info(starting_first_time)
        elif last_checkpoint_time:    
            updated_timestamp=last_checkpoint_time
            starting_from_checkpoint=logged_by_account+"|A checkpoint has been found.Starting from date:{}|".format(updated_timestamp)
            helper.log_info(starting_from_checkpoint)
        elif bool(not updated_timestamp and (isinstance(last_checkpoint_time, (type(None))))) == True:
            err=logged_by_account+"Starting date is missing: The addon needs at least updated_timestamp OR last_checkpoint_time value"
            helper.log_error(err)
            sys.exit()
        elif not updated_timestamp or bool(re.search("^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})",updated_timestamp)) == False:
            err = "Input configuration validation error. Wrong updated_timestamp format or missing value"
            helper.log_error(err)
            sys.exit()
    except Exception as e:
        err=logged_by_account+"Erorr during starting point initialization.Please report that execption"
        helper.log_error(err)
        sys.exit()
        
    #Filters url encoded
    ts_filter = "updated_timestamp:>'{}Z'".format(updated_timestamp)
    ts_filter_encoded = urllib.parse.quote(ts_filter)
    sort_filter="updated_timestamp|asc"
    sort_filter_encoded=urllib.parse.quote(sort_filter)

    #Obtain First Token and set timer for renew.
    try:
        response = helper.send_http_request("https://"+str(api_fqdn)+str(opt_access_token_endpoint),"POST",parameters=None,payload=data,headers=headers_token,cookies=None,verify=False,cert=None,timeout=180,use_proxy=False)
        response_json = response.json()
        api_token = (response.json()["access_token"])
        headers = {'Authorization': 'Bearer {0}'.format(api_token)}
        response.status = response.status_code
        access_token_expiration = time.time() + 1300
    except Exception as e:
        helper.log_error(response_text)
        err = logged_by_account+"Error during Crowdstrike Falcon initial access token obtaining.Check the error code and credentials respectively\nException:"+str(e)
        helper.log_error(err)
        sys.exit()

    #Start Getting vulnerability's ID
    try:
        hosts_response = helper.send_http_request("https://"+api_fqdn+opt_api_v1_endpoint+"?sort="+str(sort_filter_encoded)+"&filter="+str(ts_filter_encoded)+"&limit="+opt_limit, "GET", parameters=None, payload=None, headers=headers, cookies=None, verify=False, cert=None, timeout=180, use_proxy=False)
        hosts_json = hosts_response.json()
        after_page=hosts_json['meta']['pagination']['after']
        total_results=hosts_json['meta']['pagination']['total']
        results_of_total=len(hosts_json['resources'])
        page_counter=1
        log_page=logged_by_account+"Page_Number:"+str(page_counter)+"  "+"Page_ID:"+str(after_page) + "  " + "Result of Totals:" + str(results_of_total) + "/" +str(total_results)
        helper.log_info(log_page)
        if (int(total_results) - int(page_counter)*int(opt_limit) <= 2000) == True:
            stop_at_log_page=logged_by_account+"Page distance has been reached - current page * {} should not be less than or equal to 2000.Give another try later.Stopped at 1st cycle".format(opt_limit)
            helper.log_info(stop_at_log_page)
            sys.exit()
    except Exception as e:
        err = logged_by_account+"Error During Crowdstrike Falcon Spotlight GET api/v1/ids Details First Try.\nException: "+str(e)
        helper.log_error(err)
        sys.exit()
        
    try:
        join_length = (hosts_json['resources'])
        page_ids = '&ids='.join(join_length)
        response = helper.send_http_request("https://"+api_fqdn+opt_api_v2_endpoint+"?ids="+page_ids,"GET",parameters=None,payload=None,headers=headers,cookies=None,verify=False,cert=None,timeout=180,use_proxy=False)
        json_response = response.json()
        length =len(json_response['resources'])
        try:
            for i in range(length):
                ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=json.dumps(json_response['resources'][i])))
            last_id_updated_timestamp_json=(json_response['resources'][-1]['updated_timestamp'])
            last_id_updated_timestamp=re.sub(r"Z$","",last_id_updated_timestamp_json)
            helper.save_check_point(key, last_id_updated_timestamp)
        except Exception as e:
                err = logged_by_account+"Error During Crowdstrike Falcon First Cycle Events Writing.Please check logs..\nException: "+str(e)
                helper.log_error(err)
                sys.exit()
    except Exception as e:
        err = logged_by_account+"Error During Crowdstrike Falcon Spotlight GET api/v2/ids Details First Try .\nException: "+str(e)
        helper.log_error(err)
        sys.exit()
        
    while True:
        try:
            if time.time() > access_token_expiration:
                response = helper.send_http_request("https://"+api_fqdn+opt_access_token_endpoint,"POST",parameters=None,payload=data,headers=headers_token,cookies=None,verify=False,cert=None,timeout=180,use_proxy=False)
                response_json = response.json()
                api_token = (response.json()["access_token"])
                headers = {'Authorization': 'Bearer {0}'.format(api_token)}
                response.status = response.status_code
                access_token_expiration = time.time() + 1300
        except Exception as e:
            err = logged_by_account+"Error during Crowdstrike Falcon Spotlight refresh token...\nException: "+str(e)
            helper.log_error(err)
            sys.exit()
        try:
            hosts_response = helper.send_http_request("https://"+api_fqdn+opt_api_v1_endpoint+"?sort="+sort_filter_encoded+"&filter="+ts_filter_encoded+"&limit="+opt_limit+"&after="+after_page, "GET", parameters=None, payload=None, headers=headers, cookies=None, verify=False, cert=None, timeout=180, use_proxy=False)
            hosts_json = hosts_response.json()
            page_counter += 1
            total_results=hosts_json['meta']['pagination']['total']
            results_of_total=results_of_total+len(hosts_json['resources']) 
            log_page=logged_by_account+"===>Page_Number:"+str(page_counter)+"  "+"Page_ID:"+str(after_page) + "  " + "Result of Totals:" + str(results_of_total) + "/" +str(total_results)+"<==="
            helper.log_info(log_page)
        except Exception as e:
            err = logged_by_account+"Error During Crowdstrike Falcon Spotlight GET api/v1/ids while loop.\nException: "+str(e)
            helper.log_error(err)
            sys.exit()
        try:
            join_length = (hosts_json['resources'])
            page_ids = '&ids='.join(join_length)
            response = helper.send_http_request("https://"+api_fqdn+opt_api_v2_endpoint+"?ids="+page_ids,"GET",parameters=None,payload=None,headers=headers,cookies=None,verify=False,cert=None,timeout=180,use_proxy=False)
            json_response = response.json()
            length =len(json_response['resources'])
            try:    
                for i in range(length):
                    ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=json.dumps(json_response['resources'][i])))
                last_id_updated_timestamp_json=(json_response['resources'][-1]['updated_timestamp'])
                last_id_updated_timestamp=re.sub(r"Z$","",last_id_updated_timestamp_json)
                helper.save_check_point(key, last_id_updated_timestamp)
            except Exception as e:
                        err = logged_by_account+"Error During Crowdstrike Falcon Second Cycle while loop.Please check logs..\nException: "+str(e)
                        helper.log_error(err)
                        sys.exit()
        except Exception as e:
            err = logged_by_account+"Error During Crowdstrike Falcon Spotlight GET api/v2/ids Details while loop.\nException: "+str(e)
            helper.log_error(err)
            sys.exit()
        try:
            after_page=hosts_json['meta']['pagination']['after']
            if (int(total_results) - int(page_counter)*int(opt_limit) <= 2000) == True:
                stop_at_log_page=logged_by_account+"Page distance has been reached.The result of (total_pages - current page * {} ) should not be less than or equal 2000.Give another try later.End of cycle".format(opt_limit)
                last_id=(json_response['resources'][-1]['id'])
                last_id_updated_timestamp_json=(json_response['resources'][-1]['updated_timestamp'])
                last_id_updated_timestamp=re.sub(r"Z$","",last_id_updated_timestamp_json)
                end_of_cycle_log=logged_by_account+"END OF CYCLE with Result of Totals:"+str(results_of_total)
                helper.log_info(end_of_cycle_log)
                last_recorded_id=logged_by_account+"Last recorderd ID:{}  ".format(last_id)
                last_recorded_time_stamp=logged_by_account+"Last recorded Timestamp:{}  ".format(last_id_updated_timestamp)
                helper.log_info(stop_at_log_page)
                helper.log_info(last_recorded_id)
                helper.log_info(last_recorded_time_stamp)
                helper.save_check_point(key, last_id_updated_timestamp)
                sys.exit()
        except Exception as e:
            err = logged_by_account+"Error during obtain next page.\nException: "+str(e)
            helper.log_error(err)
            sys.exit()
