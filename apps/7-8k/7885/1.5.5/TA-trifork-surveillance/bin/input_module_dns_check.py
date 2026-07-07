
# encoding = utf-8

import os
import sys
import time
import datetime
import lxml.etree as ET
from urllib.parse import urlsplit
import splunklib.client as client
import json
import socket
import dns.resolver
import dns.exception
import dns.name

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
    # check_host = definition.parameters.get('check_host', None)
    # check_rr = definition.parameters.get('check_rr', None)
    # nameserver = definition.parameters.get('nameserver', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_check_host = helper.get_arg('check_host')
    opt_check_rr = helper.get_arg('check_rr')
    opt_nameserver = helper.get_arg('nameserver')
    # In single instance mode, to get arguments of a particular input, use
    opt_check_host = helper.get_arg('check_host', stanza_name)
    opt_check_rr = helper.get_arg('check_rr', stanza_name)
    opt_nameserver = helper.get_arg('nameserver', stanza_name)

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
    global_executor_kv = helper.get_global_setting("executor_kv")

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
    
    #connect to splunk
    scheme, netloc, _, _, _ = urlsplit(helper.context_meta['server_uri'], allow_fragments=False)
    splunkd_host, splunkd_port = netloc.split(':')
    service = client.connect(scheme=scheme, host=splunkd_host, port=splunkd_port, token=helper.context_meta['session_key'], owner="nobody")
    
    #variables
    myHostname = service.settings.content['host']  
    myRole = myKvRole(helper,service)
    
    check_host = helper.get_arg('check_host')  
    check_rr = helper.get_arg('check_rr')
    check_ns = helper.get_arg('check_ns')
    
    executer = "thisServer"
    if (helper.get_global_setting('executer_kv')):
      executer = "kv"
      
    if (executer == "kv" and myRole.lower() != "kv store captain"):
      helper.log_info("Only kvstore captain can run this, and thats not me, skipping")
      return   

    helper.log_info("DNS - Checking: {} ({}) @ {}, results to index: {}".format(check_host, check_rr, check_ns,helper.get_output_index()))
   
    try:
      resolver = dns.resolver.Resolver()
      resolver.nameservers=[check_ns]
      
      start = time.perf_counter()
      
      answer = []
      for rdata in resolver.query(check_host, check_rr) :
        answer.append(str(rdata))   
        
      duration = time.perf_counter()-start
      error = ""
        
    except Exception as e:
      answer = ""
      error = e
      duration = 0
      
    data = { "entity": check_host, "rr": check_rr, "ns": check_ns, "answer": answer, "error": error, "duration": duration }
    
    helper.log_info(data)
    
    event = helper.new_event(source="triforksurveillance", index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(data))
    ew.write_event(event)
    
def myKvRole(helper,service):
  try:
    data = service.request("/services/kvstore/status", method='GET')
    root = ET.fromstring(data.body.read())
    helper.log_info(root)
    replicationStatus = root.xpath('//*[local-name()="key" and @name="current"]//*[local-name()="key" and @name="replicationStatus"]/text()')
    return replicationStatus[0]
    
  except Exception as e:
    helper.log_info("Error when trying to get my role from url /services/kvstore/status: {}".format(e))
    return False
