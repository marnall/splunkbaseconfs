
# encoding = utf-8

import os
import sys
import time
import datetime
import boto
import json
import socket

from datetime import datetime
from boto.sqs.message import RawMessage

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
    # aws_access_key_id = definition.parameters.get('aws_access_key_id', None)
    pass

def TimestampMillisec64():
    return int((datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)

def collect_events(helper, ew):
    
    opt_aws_access_key_id = helper.get_arg('aws_access_key_id')
    opt_aws_access_key_id = str(opt_aws_access_key_id).strip()
    opt_aws_secret_access_key = helper.get_arg('aws_secret_access_key')
    opt_aws_secret_access_key = str(opt_aws_secret_access_key).strip()
    opt_sqs_queue_name = helper.get_arg('sqs_queue_name')
    opt_sqs_queue_name = str(opt_sqs_queue_name).strip()
    opt_sqs_queue_aws_region = helper.get_arg('sqs_queue_aws_region')
    opt_sqs_queue_aws_region = str(opt_sqs_queue_aws_region).strip()
        
    if None == opt_aws_access_key_id or 0 == len(opt_aws_access_key_id) :
        helper.log_error("[RL SQS Poller] [Queue Name: " + opt_sqs_queue_name + "]: provided empty Access Key ID. Will try again in 5 minutes. Exiting.")
        return
        
    if None == opt_aws_secret_access_key or 0 == len(opt_aws_secret_access_key) :
        helper.log_error("[RL SQS Poller] [Queue Name: " + opt_sqs_queue_name + "]: provided empty Secret Access Key. Will try again in 5 minutes. Exiting.")
        return
        
    if None == opt_sqs_queue_name or 0 == len(opt_sqs_queue_name) :
        helper.log_error("[RL SQS Poller] [Queue Name: " + opt_sqs_queue_name + "]: provided empty SQS Queue Name. Will try again in 5 minutes. Exiting.")
        return
    
    if None == opt_sqs_queue_name or 0 == len(opt_sqs_queue_name) :
        helper.log_error("[RL SQS Poller] [Queue Name: " + opt_sqs_queue_name + "]: provided empty SQS Queue Name. Will try again in 5 minutes. Exiting.")
        return   
        
    if None == opt_sqs_queue_aws_region or 0 == len(opt_sqs_queue_aws_region) :
        helper.log_error("[RL SQS Poller] [Queue Name: " + opt_sqs_queue_name + "]: provided empty SQS Queue AWS region. Will try again in 5 minutes. Exiting.")
        return  
    
    helper.log_info("[RL SQS Poller] [Queue Name: " + opt_sqs_queue_name+ "]: Will try to connect to queue in region " + opt_sqs_queue_aws_region);
    
    conn = boto.sqs.connect_to_region(
        opt_sqs_queue_aws_region,
        aws_access_key_id=opt_aws_access_key_id,
        aws_secret_access_key=opt_aws_secret_access_key)
    
    q = conn.get_queue(opt_sqs_queue_name)
    if None == q:
        helper.log_error("[RL SQS Poller] [Queue Name: " + opt_sqs_queue_name + "]: Unable to get the queue using provided credentials. Will try again in 5 minutes. Exiting.")
        return 
    # q.set_message_class(RawMessage)
    
    startTime = datetime.now() 
    MAX_WORKER_UPTIME_SECONDS = 60 
    
    while True:
        notifications_count = 0
        try:
            notifications = q.get_messages(10, wait_time_seconds=20,attributes=['All'],message_attributes=['All'])
            notifications_count = len(notifications)
            
            helper.log_info("[RL SQS Poller] [Queue Name: " + opt_sqs_queue_name + "]: We found " + str(notifications_count) + " messages in the queue in current polling.")
            
            for notification in notifications:
                try:
                    
                    splunk_redLock_alert = {}
                    message_body = json.loads(notification.get_body())
                    
                    if 'sender' not in message_body:
                                        
                        attributes = notification.attributes
                        if None != attributes:
                            splunk_redLock_alert['sentTs'] = int(attributes['ApproximateFirstReceiveTimestamp'])
                        else:
                            splunk_redLock_alert['sentTs'] = TimestampMillisec64()
                            
                        splunk_redLock_alert['sender'] = "RedLock Alert Notification"
                        splunk_redLock_alert['message'] = message_body
                    else:
                        splunk_redLock_alert = message_body
                    
                    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=(json.dumps(splunk_redLock_alert)))
                    
                    ew.write_event(event)
                    
                except Exception, exp:
                    helper.log_critical("[RL SQS Poller] [Queue Name: " + opt_sqs_queue_name + "]: Unable to write event pulled due to exception " + str(exp) + ". Will be skipping delete of the message from queue")
                finally:
                    notification.delete()
                    pass
            
        except (socket.gaierror):
            time.sleep(30)
        except Exception, e:
            helper.log_info("[RL SQS Poller] [Queue Name: " + opt_sqs_queue_name + "]: Unexpected error. Will try again in 60 seconds " + str(e))
            time.sleep(60)
        finally:
            if (datetime.now() - startTime).total_seconds() > MAX_WORKER_UPTIME_SECONDS:
                helper.log_info("[RL SQS Poller] [Queue Name: " + opt_sqs_queue_name + "]: Have been running pas time. Will retry in 5 minutes. Exiting.")
                break;
            if notifications_count==0:
                helper.log_warning("[RL SQS Poller] [Queue Name: " + opt_sqs_queue_name + "]: Queue is empty. Will retry in 5 minutes. Exiting.")
                break;
    
    
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_aws_access_key_id = helper.get_arg('aws_access_key_id')
    opt_aws_secret_access_key = helper.get_arg('aws_secret_access_key')
    opt_sqs_queue_name = helper.get_arg('sqs_queue_name')
    opt_sqs_queue_aws_region = helper.get_arg('sqs_queue_aws_region')
    # In single instance mode, to get arguments of a particular input, use
    opt_aws_access_key_id = helper.get_arg('aws_access_key_id', stanza_name)
    opt_aws_secret_access_key = helper.get_arg('aws_secret_access_key', stanza_name)
    opt_sqs_queue_name = helper.get_arg('sqs_queue_name', stanza_name)
    opt_sqs_queue_aws_region = helper.get_arg('sqs_queue_aws_region', stanza_name)

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
