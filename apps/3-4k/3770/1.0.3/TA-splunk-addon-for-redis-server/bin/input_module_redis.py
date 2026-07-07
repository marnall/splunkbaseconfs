
# encoding = utf-8

import os
import sys
import time
import datetime
import redis
import json

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # redis_host = definition.parameters.get('redis_host', None)
    # redis_port = definition.parameters.get('redis_port', None)
    # authentication = definition.parameters.get('authentication', None)
    # password = definition.parameters.get('password', None)
    pass

def collect_events(helper, ew):
    opt_redis_host = helper.get_arg('redis_host')
    opt_redis_port = helper.get_arg('redis_port')
    opt_authentication = helper.get_arg('authentication')
    opt_password = helper.get_arg('password')
    
    if not opt_password:
        opt_password=None
    try:
        r = redis.StrictRedis(host=opt_redis_host, port=opt_redis_port,password=opt_password)
    
    except Exception,e:
        return null
    
    data=json.dumps(r.info())
    
    event = helper.new_event(source=helper.get_input_type(), host=opt_redis_host, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)