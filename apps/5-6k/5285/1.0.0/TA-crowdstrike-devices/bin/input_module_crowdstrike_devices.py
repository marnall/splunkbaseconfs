#encoding = utf-8
import sys
import json

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
    opt_global_account = helper.get_arg('global_account')
    username = opt_global_account['username']
    password = opt_global_account['password']
    opt_api_queries_endpoint  = helper.get_arg('api_queries_endpoint')
    opt_api_entities_endpoint = helper.get_arg('api_entities_endpoint')
    opt_access_token_endpoint = helper.get_arg('access_token_endpoint')
    api_fqdn = helper.get_global_setting('hostname_or_ip')
    global_source = helper.get_input_type()
    global_source_type = helper.get_sourcetype()
    global_index = helper.get_output_index()
    headers_token = {'Content-Type': 'application/x-www-form-urlencoded', "accept": "application/json"}
    data = "client_id={}&client_secret={}&grant_type=client_credentials".format(username, password)

    #Obtain Token
    try:
        response = helper.send_http_request("https://"+str(api_fqdn)+str(opt_access_token_endpoint),"POST",parameters=None,payload=data,headers=headers_token,cookies=None,verify=False,cert=None,timeout=180,use_proxy=False)
        response_json = response.json()
        api_token = (response.json()["access_token"])
        headers = {'Authorization': 'Bearer {0}'.format(api_token)}
        response.status = response.status_code
    except Exception as e:
        err = "Logged by account:" + username + ":" + "Error During Crowdstrike Falcon Obtain Token. Check the logs and login part respectivley\nException: "+str(e)
        helper.log_error(err)
        sys.exit()


    #Start Getting vulnerability's ID
    try:
        hosts_response = helper.send_http_request("https://"+api_fqdn+opt_api_queries_endpoint+"?limit=1000", "GET", parameters=None, payload=None, headers=headers, cookies=None, verify=False, cert=None, timeout=180, use_proxy=False)
        hosts_json = hosts_response.json()
        total=hosts_json['meta']['pagination']['total']
        offset=hosts_json['meta']['pagination']['offset']
        results_of_total=len(hosts_json['resources'])
        info = "Logged by account:" + username + ":"  + "Offset:"+ str(offset)+" "+"Total:"+" "+str(total)
        helper.log_info(info)
    except Exception as e:
        err = "Logged by account:" + username + ":" + "Error During Crowdstrike Devices GET api/v1/ids Details First Try.\nException: "+str(e)
        helper.log_error(err)
        sys.exit()
        

    try:
        join_length = (hosts_json['resources'])
        page_ids = '&ids='.join(join_length)
        response = helper.send_http_request("https://"+api_fqdn+opt_api_entities_endpoint+"?ids="+page_ids,"GET",parameters=None,payload=None,headers=headers,cookies=None,verify=False,cert=None,timeout=180,use_proxy=False)
        json_response = response.json()
        length =len(json_response['resources'])
        try:
            for i in range(length):
                ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=json.dumps(json_response['resources'][i])))
        except Exception as e:
                err = "Logged by account:" + username + ":" + "Error During Crowdstrike Devices First Cycle Events Writes.Please check logs..\nException: "+str(e)
                helper.log_error(err)
                sys.exit()
    except Exception as e:
        err = "Logged by account:"  + username + ":" + "Error During Crowdstrike Devices GET api/v1/ids Details First Try .\nException: "+str(e)
        helper.log_error(err)
        sys.exit()
            
    while int(total) > int(offset):
        try:
            hosts_response = helper.send_http_request("https://"+api_fqdn+opt_api_queries_endpoint+"?limit=1000"+"&"+"offset="+str(offset), "GET", parameters=None, payload=None, headers=headers, cookies=None, verify=False, cert=None, timeout=180, use_proxy=False)
            hosts_json = hosts_response.json()
            total=hosts_json['meta']['pagination']['total']
            offset=hosts_json['meta']['pagination']['offset']
            results_of_total=len(hosts_json['resources'])
            info = "Offset:"+str(offset)+" "+"Total:"+" "+str(total)
            helper.log_info(info)
        except Exception as e:
            err = "Logged by account:" + username + ":" + "Error During Crowdstrike Devices GET api/v1/ids Details Loop .\nException: "+str(e)
            helper.log_error(err)
            sys.exit()
            
        
        try:
            join_length = (hosts_json['resources'])
            page_ids = '&ids='.join(join_length)
            response = helper.send_http_request("https://"+api_fqdn+opt_api_entities_endpoint+"?ids="+str(page_ids),"GET",parameters=None,payload=None,headers=headers,cookies=None,verify=False,cert=None,timeout=180,use_proxy=False)
            json_response = response.json()
            length =len(json_response['resources'])
            try:
                for i in range(length):
                    ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=json.dumps(json_response['resources'][i])))
            except Exception as e:
                    err = "Logged by account:" + username + ":" + "Error During Crowdstrike Devices Loop Cycle Events Writes.Please check logs..\nException: "+str(e)
                    helper.log_error(err)
                    sys.exit()
        except Exception as e:
            err = "Logged by account:" + username + ":" + "Error During Crowdstrike Devices GET api/v1/ids Details Loop Try .\nException: "+str(e)
            helper.log_error(err)
            sys.exit()
