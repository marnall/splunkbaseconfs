from __future__ import print_function

import os

import sys

import time

import datetime

import json

import requests

import random

from urllib.parse import urlparse



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



# Function to test if the url is https.

def is_https(helper, saviynt_url):

    scheme = urlparse(saviynt_url).scheme

    if scheme.lower() == 'https':

        helper.log_info("INFO Saviynt URL is HTTPS.")

        return True

    else:

        helper.log_error("ERROR Saviynt URL is not HTTPS.")

        return False





def getAuthToken(helper, tenant, username, password, use_proxy):

    creds = json.dumps({

      "username": username,

      "password": password

    })

    headers = {'Content-Type':'application/json'}

    uri = tenant + '/ECM/api/login'

    helper.log_info( 'Authentication API endpoint' +  str(uri)) 

    #resp = requests.post(uri, data=creds, headers=headers)

    resp= helper.send_http_request(url=uri, method='POST', parameters=None, payload=creds,

                                       headers=headers, cookies=None, verify=True, cert=None,

                                        timeout=None, use_proxy=use_proxy)



    if resp.status_code not in (200, 304):

        raise Exception("Problems getting a token from Saviynt for %s. %s %s" %(username, resp.status_code, resp))

    

    #helper.log_debug( 'Authentication API Response '+ str(resp.text))

    return resp.json()["access_token"]





def validate_input(helper, definition):

    # print('Hello World')

    """Implement your own validation logic to validate the input stanza configurations"""

    # This example accesses the modular input variable

    # saviynt_tenant = definition.parameters.get('saviynt_tenant', None)

    # username = definition.parameters.get('username', None)

    # password = definition.parameters.get('password', None)

    # analytics_name = definition.parameters.get('analytics_name', None)

    # saviynt_version = definition.parameters.get('saviynt_version', None)

    pass



def collect_events(helper, ew):

    #Implement your data collection logic here



    # The following examples get the arguments of this input.

    # Note, for single instance mod input, args will be returned as a dict.

    # For multi instance mod input, args will be returned as a single value.

    opt_saviynt_tenant = helper.get_arg('saviynt_tenant')

    opt_username = helper.get_arg('username')

    opt_password = helper.get_arg('password')

    opt_analytics_name = helper.get_arg('analytics_name')

    opt_max = helper.get_arg('max')

    opt_saviynt_version = helper.get_arg('saviynt_version')

    opt_time_interval = helper.get_arg('time_interval')

    opt_analytics_version = helper.get_arg('analytics_version')

    opt_http_request_timeout = helper.get_global_setting('http_request_timeout')

    

    try:

        reqTimeout = float(opt_http_request_timeout)

    except:

        helper.log_debug("Gloabl timeout setting not defined, Savint add-on using coded timeout value - 90")

        reqTimeout = float(90)

    

        # Check if identitynow_url is https.

    if not is_https(helper, opt_saviynt_tenant):

        return False

    # In single instance mode, to get arguments of a particular input, use

    #opt_saviynt_tenant = helper.get_arg('saviynt_tenant', stanza_name)

    #opt_username = helper.get_arg('username', stanza_name)

    #opt_password = helper.get_arg('password', stanza_name)

    #opt_analytics_name = helper.get_arg('analytics_name', stanza_name)

    #opt_saviynt_version = helper.get_arg('saviynt_version', stanza_name)

    

    # PROXY SETTINGS

    use_proxy = True if helper.get_proxy() else False

    

    token = getAuthToken(helper, opt_saviynt_tenant, opt_username, opt_password, use_proxy)

    

    payload = json.dumps({

      "analyticsname": opt_analytics_name,

      "attributes": {

        "timeFrame": opt_time_interval

      },

      "max": opt_max

    })

    

    accesstoken = 'Bearer ' + token

    

    headers = {

      'Content-Type': 'application/json',

      'Authorization': accesstoken

    }

    

    default_version = "v2"

    if (opt_analytics_version!=default_version):

        helper.log_info('Analytics v1 version used')

        analyticsURL =  opt_saviynt_tenant + '/ECM/api/v5/fetchRuntimeControlsData'

    else:

        helper.log_info('Analytics v2 version used')

        analyticsURL =  opt_saviynt_tenant + '/ECM/api/v5/fetchRuntimeControlsDataV2'

    

    helper.log_info('Analytics API used - ' + str(analyticsURL))

    # get input type

    helper.get_input_type()



    # The following examples get input stanzas.

    # get all detailed input stanzas

    # helper.get_input_stanza()

    # get specific input stanza with stanza name

    # helper.get_input_stanza(stanza_name)

    # get all stanza names

    # helper.get_input_stanza_names()



    # The following examples get options from setup page configuration.

    # get the loglevel from the setup page

    loglevel = helper.get_log_level()

    # get proxy setting configuration

    proxy_settings = helper.get_proxy()

    # get account credentials as dictionary

    #account = helper.get_user_credential_by_username("username")

    #account = helper.get_user_credential_by_id("account id")

    # get global variable configuration

    global_userdefined_global_var = helper.get_global_setting("userdefined_global_var")



    # The following examples show usage of logging related helper functions.

    # write to the log for this modular input using configured global log level or INFO as default

    #helper.log("log message")

    # write to the log using specified log level

    #helper.log_debug("log message")

    #helper.log_info("log message")

    #helper.log_warning("log message")

    #helper.log_error("log message")

    #helper.log_critical("log message")

    # set the log level for this modular input

    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)

    #helper.set_log_level(log_level)



    # The following examples send rest requests to some endpoint.

    response = helper.send_http_request(url=analyticsURL, method='POST', parameters=None, payload=payload,

                                       headers=headers, cookies=None, verify=True, cert=None,

                                        timeout=reqTimeout, use_proxy=use_proxy)

    

    #helper.log_debug( 'fetchRuntimeControlsData API Response '+ str(response.text))

    

    #response = helper.send_http_request(

    #    url=analyticsURL, 

    #    method='POST', 

    #    headers=headers, 

    #    payload=payload

    #)

    # get the response headers

    #r_headers = response.headers

    # get the response body as text

    r_status = response.status_code

    if r_status!=200:

        helper.log_error("Error in calling Saviynt APIs - " + str(response.json()["msg"]))

        response.raise_for_status()

    

    totalcount = 0;

    if (opt_analytics_version!=default_version):

        totalcount = response.json()["total"]

    else:

        totalcount = response.json()["totalcount"]

    

    displaycount = response.json()["displaycount"]

    

    helper.log_info('Total Count  - ' + str(totalcount) + ' Display Count - ' + str(displaycount))

    

    #set offset equal to max 

    offset = int(opt_max)

    

    if displaycount < totalcount:

        helper.log_debug('Total count is more than display count, pagination triggered with offset - ' + str(offset))

    

    if totalcount!=0:

        if (opt_analytics_version!=default_version):

            r_json = response.json()["result"]

        else:

            r_json = response.json()["results"]

        

        for item in r_json:

            #helper.log_info('Audit Event - ' + json.dumps(item))

            data = json.dumps(item)

            #data = re.sub(r'[\s\r\n]+'," ", data)

            #helper.log_debug('Audit Event - ' + data)

            #data = str(random.randint(0,100))

            event = helper.new_event(data=data, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())

            #helper.log_info('After new event')

            ew.write_event(event)

            helper.log_debug('Event to splunk - ' + json.dumps(item))

            #helper.log_info('After write event')

    

    

    while(offset < totalcount):

        helper.log_debug('Entering the pagination')

        offsetpayload = json.dumps({

          "analyticsname": opt_analytics_name,

          "offset": offset,

          "attributes": {

            "timeFrame": opt_time_interval

          },

          "max": opt_max

        })

            

        response = helper.send_http_request(url=analyticsURL, method='POST', parameters=None, payload=offsetpayload,headers=headers, cookies=None, verify=True, cert=None,timeout=reqTimeout, use_proxy=use_proxy)

        

        #helper.log_debug( 'fetchRuntimeControlsData API Response '+ str(response.text))

        

        if response.status_code!=200:

            helper.log_error("Error in calling Saviynt APIs - " + str(response.json()["msg"]))

            response.raise_for_status()



        if (opt_analytics_version!=default_version):

            totalcount = response.json()["total"]

        else:

            totalcount = response.json()["totalcount"]

        

        displaycount = response.json()["displaycount"]

    

        helper.log_info('Total Count  - ' + str(totalcount) + ' Display Count - ' + str(displaycount) + ' offset value - ' + str(offset))

    

        if (opt_analytics_version!=default_version):

            r_json = response.json()["result"]

        else:

            r_json = response.json()["results"]

        

        for item in r_json:

            #helper.log_debug('Audit Event - ' + json.dumps(item))

            data = json.dumps(item)

            #data = re.sub(r'[\s\r\n]+'," ", data)

            #helper.log_debug('Audit Event - ' + data)

            #data = str(random.randint(0,100))

            event = helper.new_event(data=data, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())

            #helper.log_info('After new event')

            ew.write_event(event)

            helper.log_debug('Event to splunk - ' + json.dumps(item))

        

        #Increase offset by max value

        offset += int(opt_max)

        helper.log_debug('Increment the offset by max value for the next run, offset value - ' + str(offset) )



    #r_text = response.text

    # get response body as json. If the body text is not a json string, raise a ValueError

    #r_json = response.json()

    # get response cookies

    #r_cookies = response.cookies

    # get redirect history

    #historical_responses = response.history

    # get response status code

    #r_status = response.status_code

    # check the response status, if the status is not sucessful, raise requests.HTTPError

    #response.raise_for_status()



    # The following examples show usage of check pointing related helper functions.

    # save checkpoint

    #helper.save_check_point(key, state)

    # delete checkpoint

    #helper.delete_check_point(key)

    # get checkpoint

    #state = helper.get_check_point(key)



    # To create a splunk event

    #helper.new_event(data, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)





    # The following example writes a random number as an event. (Multi Instance Mode)

    # Use this code template by default.

    #import random

    #data = str(random.randint(0,100))

    #event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)

    #ew.write_event(event)





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

