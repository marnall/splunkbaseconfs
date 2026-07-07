# encoding = utf-8
import ast
import json
import urllib

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    #config the vars
    global_hostname_or_ip = helper.get_global_setting("hostname_or_ip")
    global_logon_endpoint = helper.get_arg("logon_endpoint_url")
    global_safes_endpoint = helper.get_arg("safes_endpoint_url")
    global_source = helper.get_input_type()
    global_source_type = helper.get_sourcetype()
    global_index = helper.get_output_index()
    global_account = helper.get_arg('global_account')
    dict_headers = {"Content-Type": "application/json"}
    dict_payload = {"username": global_account['username'], "password": global_account['password']}
    
    #get the logon
    try:
        response = helper.send_http_request("https://"+global_hostname_or_ip+global_logon_endpoint, "POST", parameters=None, payload=dict_payload, headers=dict_headers, cookies=None, verify=False, cert=None, timeout=180, use_proxy=False)
    except Exception as e:
        err = "Error during CyberArk login. Check credentials or URL.\nException: "+str(e)
        helper.log_error(err)
        
        
    #extract the key
    try:
        data = ast.literal_eval(response.text)
        dict_headers = {"Authorization": data}
    except Exception as e:
        err = "Cannot get CyberArkLogonResult in login response.\nException: "+str(e)
        helper.log_error(err)
        
        
    #get all safes
    try:
        safes_response = helper.send_http_request("https://"+global_hostname_or_ip+global_safes_endpoint, "GET", parameters=None, payload=None, headers=dict_headers, cookies=None, verify=False, cert=None, timeout=180, use_proxy=False)
        json_object_safes = safes_response.json()
    except Exception as e:
        err = "Error during CyberArk get safes method. Response cannot be converted to json. Check credentials or URL.\nException: "+str(e)
        helper.log_error(err)
        
        
    #extract the safe events
    try:
        for i in range(len(json_object_safes['GetSafesSlashResult'])):
            safe_name = urllib.parse.quote(json_object_safes['GetSafesSlashResult'][i]['SafeName'])
            
            #build and write the safe events
            safe_data = json.dumps(json_object_safes['GetSafesSlashResult'][i])
            safe_event = helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=safe_data)
            ew.write_event(safe_event)
            
            #get all members
            members_response = helper.send_http_request("https://"+global_hostname_or_ip+global_safes_endpoint+safe_name+"/members", "GET", parameters=None, payload=None, headers=dict_headers, cookies=None, verify=False, cert=None, timeout=180, use_proxy=False)

            #extract all the member events
            try:
                json_object_members = members_response.json()
                for y in range(len(json_object_members['members'])):
                    json_object_members['members'][y]['SafeName'] = safe_name
                    
                    #build and write the member events
                    member_data = json.dumps(json_object_members['members'][y])
                    member_event = helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=member_data)
                    ew.write_event(member_event)
                    
            except Exception as e:
                err = "Members for SafeName="+safe_name+" cannot be extracted due to error!\nException: "+str(e)
                helper.log_error(err)
                

    except Exception as e:
        err = "Error during event construction. Response cannot be converted to json. Check credentials or URL.\nException: "+str(e)
        helper.log_error(err)
        