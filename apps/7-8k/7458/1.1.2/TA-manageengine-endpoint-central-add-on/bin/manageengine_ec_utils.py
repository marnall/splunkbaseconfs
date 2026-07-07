from Constants import *
from datetime import datetime
import json
import os
import platform
import traceback

input_details = None
input_name = None

# Validates the interval given
def validate_interval(helper, interval):
    input_name = helper.get_input_type()
    helper.log_info("input name configured: " + input_name)
    if input_name == VULNERABILITY_MODULE:
        # To Change
        if int(interval) > 86400 or int(interval) < 3600:
            helper.log_error('Validation Error: Interval should be between 3600 and 86400 seconds both included.')
            raise ValueError('Interval should be between 3600 and 86400 seconds both included.')
    if input_name == AUDIT_MODULE:
        # To Change
        if int(interval) > 86400 or int(interval) < 300:
            helper.log_error('Validation Error: Interval should be between 300 and 86400 seconds both included.')
            raise ValueError('Interval should be between 300 and 86400 seconds both included.')
        

def set_input_details(helper):
    try:
        global input_details
        global input_name

        input_details = helper.get_input_stanza()

        input_name = helper.get_input_stanza_names()
        input_details["input_name"] = input_name
        #helper.log_info(input_details)       

      
        #helper.log_info(helper.get_input_type())
        #helper.log_info('Setting input details for: ' + input_name)
       
         
       
        if input_details[input_name][GLOBAL_ACCOUNT][SERVER_TYPE] == CLOUD_SERVER:
            helper.log_info("Entering Cloud Server Mode")
            isNewConfiguration = False
            try:
                isNewConfiguration = (input_details.get(input_name, {}).get(GLOBAL_ACCOUNT, {}).get(IS_NEW_CONFIGURATION, False))
            except Exception as e:
                helper.log_error("Error occurred while getting isNewConfiguration: " + str(e))
            helper.log_info("isNewConfiguration: " + str(isNewConfiguration))

            if input_details[input_name][GLOBAL_ACCOUNT][AUTH_TOKEN] == "dummy" or input_details.get(REGENERATE_TOKEN, "false") == "true":
                if isNewConfiguration:
                        helper.log_info("New configuration detected")
                        service_account = input_details[input_name][GLOBAL_ACCOUNT][SERVICE_ACCOUNT]
                        accounts_url = input_details[input_name][GLOBAL_ACCOUNT][ZOHO_ACCOUNTS_SERVER_URL]
                        service_account = json.loads(service_account)
                        if service_account:
                            client_id = service_account.get(CLIENET_ID, None)
                            client_secret = service_account.get(CLIENT_SECRET, None)
                            refresh_token = input_details[input_name][GLOBAL_ACCOUNT][REFRESH_TOKEN]
                        
                        else:
                            helper.log_error("Service account details are not provided in the configuration")
                        
                else:
                    helper.log_info("Existing configuration detected")
                    client_id = input_details[input_name][GLOBAL_ACCOUNT][CLIENET_ID]
                    client_secret = input_details[input_name][GLOBAL_ACCOUNT][CLIENT_SECRET]
                    refresh_token = input_details[input_name][GLOBAL_ACCOUNT][REFRESH_TOKEN]
                    accounts_url = input_details[input_name][GLOBAL_ACCOUNT][ZOHO_ACCOUNTS_SERVER_URL]

                if accounts_url[-1] == "/":
                    accounts_url = accounts_url[:-1]
                token_gen_url = accounts_url + "/oauth/v2/token?" + "refresh_token=" + refresh_token + "&client_id=" + client_id + "&client_secret=" + client_secret + "&grant_type=refresh_token"
                response = helper.send_http_request(url=token_gen_url, method=METHOD_POST, timeout=(10, 10))
                response = json.loads(response.content.decode())
               

                if "error" in response or ACCESS_TOKEN not in response:
                    helper.log_error("Auth Token Gen Error: Can't generate Auth Token")
                else:
                  
                    input_details[input_name][GLOBAL_ACCOUNT][AUTH_TOKEN] = response[ACCESS_TOKEN]
                    input_details[REGENERATE_TOKEN] = "false"
        else:
            helper.log_info("Entering On-Premise Server Mode")
           
    except Exception as error:
        helper.log_error('Error occurred in set_input_details' + str(error))
        helper.log_error(traceback.format_exc())

def get_input_details():
    global input_details
    return input_details



def construct_url(helper, api):
    try:
        global input_details
        # global input_nam
        input_details = get_input_details()
        if input_details[input_name][GLOBAL_ACCOUNT].get(IS_NEW_CONFIGURATION,False):
            if input_details[input_name][GLOBAL_ACCOUNT][SERVER_TYPE] == CLOUD_SERVER:
                server_url = input_details[input_name][GLOBAL_ACCOUNT][SERVER_URL]
            else:
                server_url = input_details[input_name][GLOBAL_ACCOUNT][OP_SERVER_URL]
        else:
            server_url = input_details[input_name][GLOBAL_ACCOUNT][SERVER_URL]
            

        if server_url[-1] != "/":
            server_url += "/"
        url = server_url + api
        #helper.log_info("Constructed URL: " + url)
        return url
    except Exception as error:
        helper.log_error('Error in construct_url' +  str(error))
        helper.log_error(traceback.format_exc())

def getcontenttype(helper,url):
    if helper.input_type == AUDIT_MODULE and AUDIT_API in url:
       return "application/auditlogsdata.v1+json"
    else:
         return "application/json"

def get_module_id(module):
    if module == VULNERABILITY_MODULE:
        return VULNERABILITY_MODULE_ID
    elif module == AUDIT_MODULE:
        return AUDIT_MODULE_ID
    else:
        VULNERABILITY_MODULE_ID


# Hits the URL and fetches the response
def  construct_endpoint(helper, url, method, filters=None, payload=None):
    retry_count = 3
    while retry_count != 0:
        try:
            global input_details
            global input_name
            auth_token = input_details[input_name][GLOBAL_ACCOUNT][AUTH_TOKEN]
            headers = {}
            headers["Content-Type"] =  getcontenttype(helper,url)
            if input_details[input_name][GLOBAL_ACCOUNT][SERVER_TYPE] == OP_SERVER:
                headers["Authorization"] = auth_token
            else:
                headers["Authorization"] = "Zoho-oauthtoken " + auth_token
            
            if input_details[input_name][GLOBAL_ACCOUNT][SERVER_TYPE] == OP_SERVER:
                current_working_directory = os.path.dirname(os.path.abspath(__file__))
                os_name = os.name
                system_name = platform.system()
            
                ca_bundle_file_path = str(current_working_directory) + "\\..\\certificates\ec.ca-bundle"
                # Checking the OS to set certificate in ec.ca-bundle
                if os_name == 'posix' or system_name == 'Linux':
                    ca_bundle_file_path = str(current_working_directory) + "/../certificates/ec.ca-bundle"
                
                os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(ca_bundle_file_path)
                
           

            response = helper.send_http_request(url, method, headers=headers, 
            payload=payload, timeout=(10, 10))
            check_res = json.loads(response.content.decode())           
 
            if "error" in check_res:
                retry_count = retry_count -1
                input_details[REGENERATE_TOKEN] = "true"
                set_input_details(helper=helper)
            else:
                retry_count = 0
                return response
        except Exception as error:
            retry_count = 0
            helper.log_error('Error in construct_endpoint url: ')
            helper.log_error(error)
            break

    helper.log_error('Error in construct_endpoint url: Retry Count Exceeded')


# Fetches the module name for module id
def get_input_name(module_id):
    if str(module_id) == "1":
        return VULNERABILITY_MODULE
    if( str(module_id) == "2"):
        return AUDIT_MODULE


# Fetches the source type for module id
def get_source_type(module_id):
    if module_id == "1":
        return ME_EC_VULNERABILITY_SOURCETYPE
    elif module_id == "2":
        return ME_EC_AUDIT_SOURCETYPE

def cleanup_dvc(helper, dvc):
    try:
        dvc = dvc.replace("https:", "")
        dvc = dvc.replace("http:", "")
        dvc = dvc.replace("/", "")
        return dvc
    except Exception as error:
        helper.log_error('Error occurred in cleanup_dvc' + str(error))
        return dvc
        
        
# Porcesses module data, creates events and post them
def process_module_data(helper, event_writer, data, module_id, metadata, status, prevMetaData):
    try:
        helper.log_info("------------ Starting to process Module data --------------")
        global input_details
        input_name = helper.get_input_stanza_names()
        config_name = input_details[input_name][GLOBAL_ACCOUNT][NAME]
        if input_details[input_name][GLOBAL_ACCOUNT][IS_NEW_CONFIGURATION]:
            if input_details[input_name][GLOBAL_ACCOUNT][SERVER_TYPE] == CLOUD_SERVER:
                dvc = input_details[input_name][GLOBAL_ACCOUNT][SERVER_URL]
            else:
                dvc = input_details[input_name][GLOBAL_ACCOUNT][OP_SERVER_URL]
        else:
            dvc = input_details[input_name][GLOBAL_ACCOUNT][SERVER_URL]

        dvc = cleanup_dvc(helper, dvc=dvc)
        EC_host_info = {}
        EC_host_info["config_name"] = config_name
        EC_host_info["dvc"] = dvc
        time = None
        helper.log_info('Data size: ' + str(len(data)))
        for json_data in data:
            time = json_data["updatedtime"]
            formatedTime = datetime.fromtimestamp(int(time)/1000)
            json_data["updatedtime"] = str(formatedTime)
            json_data["vendor_product"] = "ManageEngine EndpointCentral"
            json_data["ec_host_info"] = EC_host_info
            sourcetype = get_source_type(module_id=module_id)
            json_data = json.dumps(json_data)
            event = helper.new_event(data=json_data, time=formatedTime, sourcetype=sourcetype)
            event_writer.write_event(event)
        isNextPageAvailable = metadata["isNextPageAvailable"]
        if isNextPageAvailable == False or isNextPageAvailable == "False" or isNextPageAvailable == "false":
            vuln_check_point = input_name + "_" + VULNERABILITY_MODULE + "_" + status
            helper.save_check_point(vuln_check_point, str(time))
    except Exception as error:
        helper.log_error('Error occurred in process_module_data, Prev MetaData: ' + prevMetaData + ' Curr Meta Data: ' + metadata)
        helper.log_error('Error: ' + str(error))