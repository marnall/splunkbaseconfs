# encoding = utf-8

import os
import sys
import time
import datetime
import ast
import json
import urllib
import re

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    #config the vars
    global_hostname_or_ip = helper.get_global_setting("hostname_or_ip")
    global_logon_endpoint = helper.get_arg("logon_endpoint_url")
    global_accounts_endpoint = helper.get_arg("accounts_endpoint_url")
    global_item_limit = helper.get_arg("item_limit")
    global_source = helper.get_input_type()
    global_source_type = helper.get_sourcetype()
    global_index = helper.get_output_index()
    global_account = helper.get_arg('global_account')
    dict_headers = {"Content-Type": "application/json"}
    dict_payload = {"username": global_account['username'], "password": global_account['password']}
    
    #get the logon
    try:
        login_response = helper.send_http_request("https://"+global_hostname_or_ip+global_logon_endpoint, "POST", parameters=None, payload=dict_payload, headers=dict_headers, cookies=None, verify=False, cert=None, timeout=180, use_proxy=False)
        #login_response.raise_for_status().text()
    except Exception as e:
        err = "Error during CyberArk login. Check credentials or URL.\nException: "+str(e)
        helper.log_error(err)
        #ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=err))
    
    #extract the key
    try:
        data = ast.literal_eval(login_response.text)
        dict_headers = {"Authorization":str(data)}
        dict_parameters = {"limit": global_item_limit}
    except Exception as e:
        err = "Cannot get CyberArkLogonResult in login response.\nException: "+str(e)
        helper.log_error(err)
    
    #get all accounts
    try:
            accounts_response = helper.send_http_request("https://"+global_hostname_or_ip+global_accounts_endpoint, "GET", parameters=dict_parameters, payload=None, headers=dict_headers, cookies=None, verify=False, cert=None, timeout=180, use_proxy=False)
            #accounts_response.raise_for_status()
            json_object_accounts = accounts_response.json()
            nextlink_raw=json_object_accounts['nextLink']
            nextlink=re.sub(r"^api/Accounts","",nextlink_raw)
            page_result=json_object_accounts['count']
            page_results="Results count:{}".format(page_result)
            helper.log_info(page_results)
            
    except Exception as e:
        err = "Error during CyberArk get all accounts method. Response cannot be converted to json. Check credentials or URL.\nException: "+str(e)
        helper.log_error(err)
        
            #extract the accounts events
    try:
        length = len(json_object_accounts['value'])
        for i in range(length):
            #build and write the safe events
            account_data = json.dumps(json_object_accounts['value'][i])
            account_event = helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=account_data)
            ew.write_event(account_event)
    except Exception as e:
        err = "Error during event construction. Response cannot be converted to json. Check credentials or URL.\nException: "+str(e)
        helper.log_error(err)
        
    
    try:  
        while True:
            try:

                accounts_response = helper.send_http_request("https://"+global_hostname_or_ip+global_accounts_endpoint+nextlink, "GET", parameters=None, payload=None, headers=dict_headers, cookies=None, verify=False, cert=None, timeout=180, use_proxy=False)
                #accounts_response.raise_for_status()
                json_object_accounts = accounts_response.json()
                length = len(json_object_accounts['value'])
                for i in range(length):
                    #build and write the safe events
                    account_data = json.dumps(json_object_accounts['value'][i])
                    account_event = helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=account_data)
                    ew.write_event(account_event)
        
                page_result=page_result+json_object_accounts['count']
                page_results="Results count:{}".format(page_result)
                helper.log_info(page_results)
                helper.log_info(page_result)
                nextlink_raw=json_object_accounts['nextLink']
                nextlink=re.sub(r"^api/Accounts","",nextlink_raw)
            except KeyError as e:
                err = "Nextlink was not found presume the end of loop"+str(e)
                helper.log_info(err)
                sys.exit()
            except Exception as e:
                err = "Error during CyberArk get all accounts method. Response cannot be converted to json. Check credentials or URL.\nException: "+str(e)
                helper.log_error(err)
                sys.exit()
    except Exception as e:
        err = "Error during event construction. Response cannot be converted to json. Check credentials or URL.\nException: "+str(e)
        helper.log_error(err)
        sys.exit()