import ta_elysiumanalytics_declare  # noqa: F401
import requests
import json
import traceback
import elysiumanalytics_const as const
import elysiumanalytics_common_utils as utils
from log_manager import setup_logging
import os
from urllib.parse import quote
import itertools
import base64
import splunklib.client as client
import xmltodict
import sys
import re
import datetime

_LOGGER = setup_logging("elysiumanalytics_com")
APP_NAME = const.APP_NAME


def get_clear_token(splunkd_uri,name,session_key):
    _LOGGER.info('entered into get_clear_token method')
    
    try:
        service = client.connect(token=session_key, autologin=True)
        secrets = service.storage_passwords 
        try:
            mysecret = next(secret for secret in secrets if (secret.username == name)).clear_password
        except Exception as e:        
            raise Exception("The access token doesn't exist for the user you have mentioned")
        return mysecret  
    except Exception as e:        
        raise Exception(str(e))
    
    


def oauth_key_gen(name,splunkd_uri,session_key,client_id,client_secret,snowflake_refresh_token,snowflake_instance):
    _LOGGER.info("entered into oauth_key_gen method ")
    
    authorize_url = "https://"+snowflake_instance+"/oauth/token-request"
    encodedData = base64.b64encode(bytes(f"{client_id}:{client_secret}", "ISO-8859-1")).decode("ascii")
    authorize_data = { 
                "grant_type": "refresh_token", 
                "refresh_token" : snowflake_refresh_token
                }

    # authorize_headers = {'Content-Type': 'application/x-www-form-urlencoded','Accept-Charset':'utf-8'}
    authorize_headers = {'Content-Type': 'application/x-www-form-urlencoded','Accept-Charset':'utf-8','Authorization': 'Basic '+encodedData}

    r = requests.post(authorize_url, headers=authorize_headers,data=authorize_data)
    authorize_json_data = r.text
    t1 = json.loads(authorize_json_data)
    

    try:
        gen_access_token = t1['access_token']
         
        try:
            service = client.connect(token=session_key, autologin=True)
            secrets = service.storage_passwords 
            storage_password = secrets.create(gen_access_token, name)
            try:
                mysecret = next(secret for secret in secrets if (secret.username == name)).clear_password
            except Exception as e:        
                raise Exception("The access token doesn't exist for the user you have mentioned")
            return mysecret  
        except Exception as e:        
            raise Exception(str(e))
        
        
    except Exception as e:
        if 'error' in t1:
            if t1['error'] == 'invalid_grant':
                raise Exception('Refresh token Validity is expired. Please generate the new refresh token and re-configure the same in the configuration page')
            else:
                raise Exception(str(e))            
        else:
            raise Exception(str(e))
        
        # raise Exception(str(e))
        return 'False'  
       
        # raise Exception(str(e))
        # return 'False'
        
        
        
def oauth_key_gen_390318(method,name,splunkd_uri,session_key,client_id,client_secret,snowflake_refresh_token,snowflake_instance,data=None,args=None):
    _LOGGER.info("entered into oauth_key_gen_390318 oauth method ")
        
    authorize_url = "https://"+snowflake_instance+"/oauth/token-request"
    encodedData = base64.b64encode(bytes(f"{client_id}:{client_secret}", "ISO-8859-1")).decode("ascii")
    authorize_data = { 
                "grant_type": "refresh_token", 
                "refresh_token" : snowflake_refresh_token
                }

    # authorize_headers = {'Content-Type': 'application/x-www-form-urlencoded','Accept-Charset':'utf-8'}
    authorize_headers = {'Content-Type': 'application/x-www-form-urlencoded','Accept-Charset':'utf-8','Authorization': 'Basic '+encodedData}

    r = requests.post(authorize_url, headers=authorize_headers,data=authorize_data)
    authorize_json_data = r.text
    t1 = json.loads(authorize_json_data)

    try:
        # if 'access_token' in t1:
        gen_access_token = t1['access_token']
        
        try:
            service = client.connect(token=session_key, autologin=True)
            storage_passwords = service.storage_passwords 
            storage_passwords.delete(name)
            storage_passwords.create(gen_access_token, name)              
            
        except Exception as e:
            raise Exception(str(e))
        
    
        # Prepare URL
        request_url = "{}{}{}".format("https://", snowflake_instance.strip("/"), const.CLUSTER_ENDPOINT)

        if args:
            request_url = "?".join([request_url, "&".join(["{}={}".format(k, v) for k, v in args.items()])])

        
        snowflake_oauth_token = gen_access_token
        


        if not all([snowflake_instance, snowflake_oauth_token]):
            raise Exception("Addon is not configured. Navigate to addon's configuration page to configure the addon.")


        headers = {
            "Authorization": "Bearer {}".format(snowflake_oauth_token),
            # "X-Snowflake-Authorization-Token-Type" : "KEYPAIR_JWT",
            "Content-Type": "application/json",
            "User-Agent": const.USER_AGENT_CONST,
            "Accept-Encoding" : "utf-8",
            "Accept-Charset": "utf-8"
        }

        try:
            if method.lower() == "get":
              
                response = requests.get(
                    request_url, headers=headers
                )
            elif method.lower() == "post":
               
                response = requests.post(
                    request_url,
                    headers=headers,
                    data=json.dumps(data),
                )


            t2 = response.json()
            

           
            return response.json()
        except Exception as e:
            raise Exception(str(e))

    # except Exception as e:
        
        # raise Exception(str(e))
    # return True

    except Exception as e:
        if 'error' in t1:
            if t1['error'] == 'invalid_grant':
                raise Exception('Refresh token Validity is expired. Please generate the new refresh token and re-configure the same in the configuration page')
            else:
                raise Exception(str(e))            
        else:
            raise Exception(str(e))
        
        # raise Exception(str(e))
        return 'False'       


def elysiumanalytics_api(method, oauth_response, endpoint, splunk_session_key, data=None, args=None):

    _LOGGER.info("enterd into elysiumanalytics_api  key")
        
    # Get user configuration
    
    snowflake_instance = utils.get_elysiumanalytics_configs().get("snowflake_instance")
    snowflake_instance = snowflake_instance+'.snowflakecomputing.com'
    
    # Prepare URL
    request_url = "{}{}{}".format("https://", snowflake_instance.strip("/"), endpoint)

    if args:
        request_url = "?".join([request_url, "&".join(["{}={}".format(k, v) for k, v in args.items()])])
        
    snowflake_oauth_token = oauth_response

    if not all([snowflake_instance, snowflake_oauth_token]):
        raise Exception("Addon is not configured. Navigate to addon's configuration page to configure the addon.")


    headers = {
        "Authorization": "Bearer {}".format(snowflake_oauth_token),
        # "X-Snowflake-Authorization-Token-Type" : "KEYPAIR_JWT",
        "Content-Type": "application/json",
        "User-Agent": const.USER_AGENT_CONST,
        "Accept-Encoding" : "utf-8",
        "Accept-Charset": "utf-8"
    }
    
    try:
        if method.lower() == "get":
          
            response = requests.get(
                request_url, headers=headers
            )
        elif method.lower() == "post":
           
            response = requests.post(
                request_url,
                headers=headers,
                data=json.dumps(data),
            )

        t1 = response.json()
        if t1['code'] == '390318':
     
            return response.json()
        else:
            return response.json()
    except Exception as e:
        
        msg = "Unable to request snowflake instance. "\
              "Please validate the provided snowflake configurations or check the network connectivity."
        if "response" in locals():
            status_code_messages = {
                400: response.json().get("message", "Bad request. The request is malformed."),
                403: "Invalid access token. Please enter the valid access token.",
                404: "Invalid API endpoint.",
                429: "API limit exceeded. Please try again after some time.",
                500: response.json().get("error", "Internal server error."),
            }

            msg = status_code_messages.get(response.status_code, msg)

        
        raise Exception(str(e))
        
        
def partitions_response(response,oauth_response):       
   
    key_list_1 = []
    for key in response:
        key_list_1.append(key)
    try:
        if 'resultSetMetaData' in key_list_1:
            test_p =  response['resultSetMetaData']['numRows']
            _LOGGER.info(test_p)
            partitions = response['resultSetMetaData']['partitionInfo']
            _LOGGER.info(len(partitions))
            
            # if test_p <= 100000:
                
                # partitions_len = len(partitions)
            
            # else:
                
                # if len(partitions)  > 20:
                    # partitions_len = 1
                # elif 10 <= len(partitions) <= 19:
                    # partitions_len = 5
                # else:
                    # partitions_len = len(partitions)
            partitions_len = len(partitions)
            partioned_data = []
            
            _LOGGER.info(partitions_len)
           
            for h in range(0, partitions_len):
                
                snowflake_instance = utils.get_elysiumanalytics_configs().get("snowflake_instance")
                snowflake_instance = snowflake_instance+'.snowflakecomputing.com'
                # Prepare URL
                request_url = "{}{}{}{}{}{}{}".format("https://", snowflake_instance.strip("/"), const.CLUSTER_ENDPOINT,"/",response.get("statementHandle"),"?partition=",h)
               
                snowflake_oauth_token = oauth_response 
                
                headers = {
                        "Authorization": "Bearer {}".format(snowflake_oauth_token),
                        # "X-Snowflake-Authorization-Token-Type" : "KEYPAIR_JWT",
                        "Content-Type": "application/json",
                        "User-Agent": const.USER_AGENT_CONST,
                        "Accept-Encoding" : "gzip",
                        "Accept" : "*/*"
                        # "Accept-Charset": "utf-8"
                    }
                    

                partitioned_response = requests.get(
                    request_url,
                    headers=headers,
                    data=json.dumps(response),
                )
                # _LOGGER.info(partitioned_response)
                # _LOGGER.info("=====================================")
                # _LOGGER.info(partitioned_response.json())
                partitioned_res_data = partitioned_response.json()
                partioned_data.append(partitioned_res_data['data'])
            final_data = list(itertools.chain.from_iterable(partioned_data))
                
         
            return final_data
    except Exception as e:
        raise Exception(str(e))
    
    
    
def query_extraction(t1,earliest_time_epoch,latest_time_epoch):

    stmnt_from = re.search(r"\s+from\s+[aA-zZ-]*|\s+where\s+",t1).group(0)
    stmnt_split = re.split(r"\s+from\s+[aA-zZ-]*|\s+where\s+",t1)


    earliest_time = datetime.datetime.fromtimestamp(earliest_time_epoch)
    latest_time = datetime.datetime.fromtimestamp(latest_time_epoch)
    
    try:
        if len(stmnt_split) > 2:
            final_stmnt = stmnt_split[0]+" "+stmnt_from+ " where event_time between "+"'"+str(earliest_time)+"'"+ " and "+"'"+str(latest_time)+"'"+ " and "+ stmnt_split[2]
            return final_stmnt
        elif len(stmnt_split) == 2:
            final_stmnt = stmnt_split[0]+" "+stmnt_from+ " "+ " where event_time between "+"'"+str(earliest_time)+"'"+ " and "+"'"+str(latest_time)+"'" + stmnt_split[1]
            return final_stmnt
        else:
            final_stmnt = stmnt_split[0]+" "+stmnt_from + " where event_time between "+"'"+str(earliest_time)+"'"+ " and "+"'"+str(latest_time)+"'"
            return final_stmnt
            
        _LOGGER.info(final_stmnt)
    except Exception as e:
        raise Exception(str(e))
        
        
        
def query_extraction_timecolumn(t1,earliest_time_epoch,latest_time_epoch,timecolumn): 
    stmnt_from = re.search(r"\s+from\s+[aA-zZ-]*|\s+where\s+",t1).group(0)
    stmnt_split = re.split(r"\s+from\s+[aA-zZ-]*|\s+where\s+",t1)

    _LOGGER.info("------------- query extraacion timecolumn method --------------")
    # _LOGGER.info(stmnt_from)
    
    earliest_time = datetime.datetime.fromtimestamp(earliest_time_epoch)
    latest_time = datetime.datetime.fromtimestamp(latest_time_epoch)
    
    
    try:
        if len(stmnt_split) > 2:
            final_stmnt = stmnt_split[0]+" "+stmnt_from+" where " + timecolumn+ " between "+"'"+str(earliest_time)+"'"+ " and "+"'"+str(latest_time)+"'"+ " and "+ stmnt_split[2]
            _LOGGER.info(final_stmnt)
            return final_stmnt
        elif len(stmnt_split) == 2:
            final_stmnt = stmnt_split[0]+" "+stmnt_from+ " "+ " where " + timecolumn+ " between "+"'"+str(earliest_time)+"'"+ " and "+"'"+str(latest_time)+"'"+ stmnt_split[1]
            _LOGGER.info(final_stmnt)
            return final_stmnt
        else:
            final_stmnt = stmnt_split[0]+" "+stmnt_from + " where " + timecolumn+ " between "+"'"+str(earliest_time)+"'"+ " and "+"'"+str(latest_time)+"'"
            _LOGGER.info(final_stmnt)
            return final_stmnt
            
        _LOGGER.info(final_stmnt)
    except Exception as e:
        raise Exception(str(e))
        
        
def query_extraction_without_timefilter(t1):
    
    stmnt_from = re.search(r"\s+from\s+[aA-zZ-]*|\s+where\s+",t1).group(0)
    stmnt_split = re.split(r"\s+from\s+[aA-zZ-]*|\s+where\s+",t1)

    _LOGGER.info("------------- query extraacion without_timefilter method --------------")
    
    try:
        if len(stmnt_split) > 2:
            final_stmnt = stmnt_split[0]+" "+stmnt_from +" where " + stmnt_split[2]            
            _LOGGER.info(final_stmnt)
            return final_stmnt
        elif len(stmnt_split) == 2:
            final_stmnt = stmnt_split[0]+" "+stmnt_from +" "+stmnt_split[1]
            _LOGGER.info(final_stmnt)
            return final_stmnt
        else:
            final_stmnt = stmnt_split[0]+" "+stmnt_from 
            _LOGGER.info(final_stmnt)
            return final_stmnt
            
        _LOGGER.info(final_stmnt)
    except Exception as e:
        raise Exception(str(e))
        
        
# def query_extraction_without_timefilter(t1,timecolumn):
    
    # stmnt_from = re.search(r"\s+from\s+[aA-zZ-]*|\s+where\s+",t1).group(0)
    # stmnt_split = re.split(r"\s+from\s+[aA-zZ-]*|\s+where\s+",t1)
    

    # _LOGGER.info("------------- query extraacion without_timefilter method --------------")
    # _LOGGER.info(stmnt_split)
    # try:
        # if len(stmnt_split) > 2:
            # _LOGGER.info("inside if")
            # if timecolumn == None:
                # final_stmnt = stmnt_split[0]+" "+stmnt_from +" where " + stmnt_split[2]    
                # _LOGGER.info(final_stmnt)
                # return final_stmnt
            # else:
                # final_stmnt = stmnt_split[0]+" "+stmnt_from +" where " +timecolumn+ " is not null and "+ stmnt_split[2]  
                # _LOGGER.info(final_stmnt)
                # return final_stmnt
            
            # final_stmnt = stmnt_split[0]+" "+stmnt_from +" where " +timecolumn+ " is not null and "+ stmnt_split[2]            
            # _LOGGER.info(final_stmnt)
            # return final_stmnt
        # elif len(stmnt_split) == 2:
            # _LOGGER.info("inside elif")
            # if timecolumn == None:
                # final_stmnt = stmnt_split[0]+" "+stmnt_from +" "+stmnt_split[1]
                # _LOGGER.info(final_stmnt)
                # return final_stmnt
            # else:
                # final_stmnt = stmnt_split[0]+" "+stmnt_from +" where " +timecolumn+ " is not null  "+stmnt_split[1]
                # _LOGGER.info(final_stmnt)
                # return final_stmnt
        # else:
            # _LOGGER.info("inside else")
            # if timecolumn == None:
                # final_stmnt =  stmnt_split[0]+" "+stmnt_from 
                # _LOGGER.info(final_stmnt)
                # return final_stmnt
            # else:
                # final_stmnt =  stmnt_split[0]+" "+stmnt_from + " where "+timecolumn+ " is not null "
                # _LOGGER.info(final_stmnt)
                # return final_stmnt

            
        # _LOGGER.info(final_stmnt)
    # except Exception as e:
        # raise Exception(str(e))

  
    

  
 