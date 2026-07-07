
# encoding = utf-8

import os
import json
import sys
import time
import datetime
import base64
import csv
import io

#from urlparse import urlparse
from six.moves.urllib import parse as urllib_parse


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
    # This example accesses the modular input variable
    # api_uri_base = definition.parameters.get('api_uri_base', None)
    # api_version = definition.parameters.get('api_version', None)
    # username = definition.parameters.get('username', None)
    # password = definition.parameters.get('password', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_api_uri_base = helper.get_arg('api_uri_base')
    opt_api_version = helper.get_arg('api_version')
    opt_username = helper.get_arg('username')
    opt_password = helper.get_arg('password')
    
    
    

    # get input type
    helper.get_input_type()

    # The following examples get input stanzas.
    # get all detailed input stanzas
    helper.get_input_stanza()
    # get specific input stanza with stanza name
   # helper.get_input_stanza(stanza_name)
    # get all stanza names
    helper.get_input_stanza_names()

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    loglevel = helper.get_log_level()
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()
    # get account credentials as dictionary
    #account = helper.get_user_credential_by_username("username")



    
    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)

    helper.log_info("Start download for Infoblox IPAM Networks")
    helper.log_info("uri base: " + opt_api_uri_base)
    helper.log_info("api version: " + opt_api_version)
    helper.log_info("username: " + opt_username)



    client_id = opt_username #opt_global_account['username']
    secret = opt_password #opt_global_account['password'

    auth = base64.encodestring('{0}:{1}'.format(client_id, secret)).replace('\n', '')
    
    headers = {'Authorization': 'Basic ' + auth,'Content-Type': 'application/json'}
    #userAndPass = b64encode(b"opt_username:opt_password").decode("ascii")
    #headers = { 'Authorization' : 'Basic %s' %  userAndPass }
    #helper.log_info("headers: " + headers)
    
    url = opt_api_uri_base + "/wapi/" + opt_api_version +"/fileop?_function=csv_export"
    helper.log_info("url: " + url)
    method = "POST"
    payload={"_object": "network"}


    # The following examples send rest requests to some endpoint.
    response = helper.send_http_request(url, method, parameters=None, payload=payload,
                                        headers=headers, cookies=None, verify=False, cert=None,
                                        timeout=300, use_proxy=True)
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
    
    original_hostname=urlparse(url).hostname # prints www.website.com
    
    if r_status == 200:
        helper.log_debug('Token received')
        token = str(r_json['token'].replace('\n', ''))
        url = r_json['url']
    response.raise_for_status()

    # rewrite URL correctly based on paramters, not returned url
    returned_hostname=urlparse(url).hostname # prints www.website.com
    url=url.replace(returned_hostname,original_hostname)


    method = "GET"
    headers = {'Authorization': 'Basic ' + token, 'Content-Type': 'application/json'}
    
    response2 = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=headers, cookies=None, verify=False, cert=None,
                                        timeout=300, use_proxy=True)    
                                        
    
    r_text = response2.text
    r_headers = response2.headers
    r_status = response2.status_code
    response.raise_for_status()
    
    #event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=r_text)
    #ew.write_event(event)
    
    

    reader_list = csv.DictReader(io.StringIO(r_text))

    for row in reader_list:
        try:
            data = json.dumps(row)
            data = data.replace("*\":","\":")
        except:
           helper.log_info("Unable to dump this row: " + row)
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data,unbroken=True)
        ew.write_event(event)
           
