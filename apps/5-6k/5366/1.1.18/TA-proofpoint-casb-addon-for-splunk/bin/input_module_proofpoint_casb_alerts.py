
# encoding = utf-8

import os
import sys
import time
from datetime import datetime
import json
import logging
import base64
import casb_common

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
'''
ALERTLINK= 'https://app.explore.proofpoint.com/v2/apps/search/incidents/new/search?fqid={}&region={}'
ALERTFQID= 'oitroot-op1-casb-activity#alert_{}#alert_{}'
ALERTBASEURL = 'https://api{}.protect.proofpoint.com/v1/alerts'  # EU API Endpoint - match this with the DC
ALERTSYCPK='CASB_alerts_cpk'
ACCESSTOKEN='CASB_AT'
MAXPAGES = 100
DCLIST = ['EU','US','STG','AU']

def validate_input(helper, definition):
    
    pass

        
def collect_events(helper, ew):
    
    logging.info("CASB ALERTS TA - Start")
    # get global variable configuration
    user_name = helper.get_global_setting("client_id")
    password = helper.get_global_setting("client_secret")
    APIKey = helper.get_global_setting("api_key")
    dataCenter = helper.get_global_setting("data_center")
    if dataCenter not in DCLIST:
        logging.error("CASB ALERTS TA - {} is invalid data center".format(dataCenter))
        raise Exception("CASB ALERTS TA - {} is invalid data center".format(dataCenter))
     # get proxy setting configuration
    proxy_settings = helper.get_proxy()
    # get data input parameters
    ResetPointer = helper.get_arg('reset_checkpoint_warning')
    
    proxy_enabled = False
    if bool(proxy_settings):
        logging.debug("CASB ALERTS TA - proxy enabled")
        proxy_enabled = True
    
    cpk=None
    token=None
    
    if not ResetPointer:
        cpk = helper.get_check_point(ALERTSYCPK)
        token = helper.get_check_point(ACCESSTOKEN)
    else:
        logging.info("CASB ALERTS TA - Warning!! Running in reset checkpoint mode. Please uncheck the Reset Checpoint flag")
    j=0
    

    
    alertsarray = []
    nextPage=True
    totalAlerts=0
    url=casb_common.getURL(ALERTBASEURL,dataCenter)
    body = {'page':0,'time_range':{}}

    currentTime = int(time.time()*1000)-60000
    if cpk is not None:
        body['time_range']['from'] = (cpk)
        body['time_range']['to'] = (currentTime)
    else:
        body['time_range']['from'] = (currentTime-300000)
        body['time_range']['to'] = (currentTime)
        
    while nextPage:
        
        authorized = True
        nextPage=False
        
        logging.debug("CASB ALERTS TA - Calling ALERTS API with Body : {}".format(body))
        try:
            response = helper.send_http_request(url, 'POST' , parameters=None, payload=json.dumps(body),
                                            headers={"Authorization": token, 'x-api-key': APIKey,'Content-Type':'application/json' }, cookies=None, verify=True, cert=None,
                                            timeout=20, use_proxy=proxy_enabled)
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            logging.error("CASB ACTIVITY TA - HTTP request exception: {}".format(message))
            logging.error("CASB ACTIVITY TA - Please verify the proxy settings")
            raise SystemExit(ex)
        
        r_status = response.status_code
        logging.debug("CASB ALERTS TA - Got API Response {} for page number {}".format(r_status, str(body['page']+1)))
        
        try:
            response_text=response.text
            content_json = json.loads(response_text.replace('\t',""))
        except json.decoder.JSONDecodeError:
            logging.error("CASB ALERTS TA - Exception in parsing the response JSON, will continue to the next page")
            content_json={ "alerts": [] }
            body['page'] = int(body['page'])+1
            nextPage=True
        
        if r_status != 200:
        # Checking if access token is valid
            message=""
            if 'message' in content_json:
                message=content_json['message']
            elif 'error' in content_json:
                message=content_json['error']
            
            if r_status == 401:
                authorized=False
                nextPage = True
                token=casb_common.getAccessToken(helper,user_name,password,APIKey,dataCenter,proxy_enabled,"ALERTS")
                helper.save_check_point(ACCESSTOKEN, token)   
            elif r_status == 403:
                
                
                logging.error("CASB ALERTS TA - Failed to Get Alerts, error Message: {}. Please verify that the credentials and API Key entered are correct".format(message))
                raise Exception("CASB ALERTS TA - Failed to Get Alerts, error Message: {}. Please verify that the credentials and API Key entered are correct".format(message))
                
            else:
                logging.error("CASB ALERTS TA - Failed to Get Alerts, error Message: {}.".format(message))
                response.raise_for_status()
        
        # if access token is valid will try to consume the events    
        if authorized:
            
            
            logging.debug("CASB ALERTS TA - Processing API Response")
            i=0
            for alert in content_json ['alerts']:
                i=i+1
                if 'tenant_id' in alert and 'id' in alert:
                    alertFQID=ALERTFQID.format(alert['id'],alert['id'])
                    encoded_alertFQID = base64.b64encode(alertFQID.encode('utf-8'))
                    encoded_string_alertFQID = encoded_alertFQID.decode('utf-8')
                    alert['alert_link'] =  ALERTLINK.format(encoded_string_alertFQID,casb_common.getPlatfromRegion(dataCenter))
                alertsarray.append(alert)
                try:
                    flattened_alert = casb_common.flatten_json(alert)
                except Exception as ex:
                    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                    message = template.format(type(ex).__name__, ex.args)
                    logging.error("CASB ACTIVITY TA - exception: {}".format(message))
                    raise SystemExit(ex)

                event=helper.new_event(json.dumps(flattened_alert), time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
                ew.write_event(event)
                if i==50:
                    logging.debug ("CASB ALERTS TA - Found next page, Next page:{}".format(int(body['page'])+1))
                    body['page'] = int(body['page'])+1
                    nextPage=True
            logging.debug("CASB ALERTS TA - Completed Processing API Response")
                
            
            time.sleep(3)
            if int(body['page'])>=MAXPAGES:
                nextPage = False
                logging.debug("CASB ALERTS TA - Reached Maximum Pages per Run, Stopping the Loop. Max Pages:{}".format(MAXPAGES))

            j=j+i
    
   
    if int(j)>0:
        alertsarray.sort(reverse=True, key=casb_common.extract_alert_timestamp)
        cpk=alertsarray[0]['timestamp']+1
        helper.save_check_point(ALERTSYCPK, cpk)        
     
    
    logging.info("CASB ALERTS TA - End, Total {} pages, {} alerts, last page was {}".format(str(int(body['page'])+1),str(j),str(cpk)))
    

    
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_user_name = helper.get_arg('user_name')
    opt_password = helper.get_arg('password')
    opt_api_key = helper.get_arg('api_key')
    # In single instance mode, to get arguments of a particular input, use
    opt_user_name = helper.get_arg('user_name', stanza_name)
    opt_password = helper.get_arg('password', stanza_name)
    opt_api_key = helper.get_arg('api_key', stanza_name)

    # get input type
    helper.get_input_type()

    # The following examples get input stanzas.
    # get all detailed input stanzas
    helper.get_input_stanza()
    # get specific input stanza with stanza name
    helper.get_input_stanza(stanza_name)
    # get all stanza names
    helper.get_input_stanza_names()

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    loglevel = helper.get_log_level()
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()
    # get account credentials as dictionary
    account = helper.get_user_credential_by_username("username")
    account = helper.get_user_credential_by_id("account id")
    # get global variable configuration
    global_userdefined_global_var = helper.get_global_setting("userdefined_global_var")

    # The following examples show usage of logging related helper functions.
    # write to the log for this modular input using configured global log level or INFO as default
    helper.log("log message")
    # write to the log using specified log level
    helper.log_debug("log message")
    helper.log_info("log message")
    helper.log_warning("log message")
    helper.log_error("log message")
    helper.log_critical("log message")
    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    helper.set_log_level(log_level)

    # The following examples send rest requests to some endpoint.
    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
    # get the response headers
    r_headers = response.headers
    # get the response body as text
    r_text = response.text
    # get response body as json. If the body text is not a json string, raise a ValueError
    r_json = response.json()
    # get response cookies
    r_cookies = response.cookies
    # get redirect history
    historical_responses = response.history
    # get response status code
    r_status = response.status_code
    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()

    # The following examples show usage of check pointing related helper functions.
    # save checkpoint
    helper.save_check_point(key, state)
    # delete checkpoint
    helper.delete_check_point(key)
    # get checkpoint
    state = helper.get_check_point(key)

    # To create a splunk event
    helper.new_event(data, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
    """

    '''
    # The following example writes a random number as an event. (Multi Instance Mode)
    # Use this code template by default.
    import random
    data = str(random.randint(0,100))
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)
    '''

    '''
    # The following example writes a random number as an event for each input config. (Single Instance Mode)
    # For advanced users, if you want to create single instance mod input, please use this code template.
    # Also, you need to uncomment use_single_instance_mode() above.
    import random
    input_type = helper.get_input_type()
    for stanza_name in helper.get_input_stanza_names():
        data = str(random.randint(0,100))
        event = helper.new_event(source=input_type, index=helper.get_output_index(stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=data)
        ew.write_event(event)
    '''
    # import random
    # input_type = helper.get_input_type()
    # for stanza_name in helper.get_input_stanza_names():
    #     data = stanza_name
    #     event = helper.new_event(source=input_type, index=helper.get_output_index(stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=data)
    #     ew.write_event(event)
