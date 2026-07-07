
# encoding = utf-8

import os
import sys
import time
import datetime
import re
from idaptive import idaptive_client
from idaptive.restapi import RestSync

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
    tenant_url = definition.parameters.get('tenant_url', None)
    client_id = definition.parameters.get('client_id', None)
    client_password = definition.parameters.get('client_password', None)
    oauth_app_id = definition.parameters.get('oauth_app_id', None)
    scope = definition.parameters.get('scope', None)

    if tenant_url is None or len(tenant_url.strip()) == 0:
        raise ValueError("Tenant URL is required")
    else:
        try:
            helper.log_debug("Parsing tenant URL")
            # Parse tenant name from url
            pattern = '(?:http.*://)+(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'
            match = re.search(pattern, tenant_url.strip())
            tenant = match.group('host')
        except Exception as e:
            raise ValueError("Tenant URL seems incorrect. Try again")
    if client_id is None or len(client_id.strip()) == 0:
        raise ValueError("Client Id is required") 
    if client_password is None or len(client_password.strip()) == 0:
        raise ValueError("Client Password value is required") 
    if oauth_app_id is None or len(oauth_app_id.strip()) == 0:
        raise ValueError("Oauth App Id is required") 
    if scope is None or len(scope.strip()) == 0:
        raise ValueError("Scope is required") 
    try:
        interval = int(definition.parameters.get('interval'))
    except:
        raise ValueError("Interval must be a number")
    if interval <= 0:
        raise ValueError("The Interval must be > 0")

    try:
        rollback = int(definition.parameters.get('rollback'))
    except:
        raise ValueError("Rollback must be a number")
    if rollback <= 0:
        raise ValueError("The Rollback must be > 0")

    try:
        batch_size = int(definition.parameters.get('batch_size'))
    except:
        raise ValueError("Batch size must be a number")
    if batch_size <= 0:
        raise ValueError("The Batch size must be > 0")

def collect_events(helper, ew):
    try:
        helper.log_info("collect_events() triggered")
        restsync = RestSync(helper)
        tenant_url = helper.get_arg("tenant_url")
        if not restsync.is_tenant_accessible(tenant_url.strip()):
            helper.log_error("Tenant URL is not accessible. Please verify. (Also verify the proxy settings, if it is required)")   
            return        

        helper.log_debug("Invoking Idaptive client\'s run()")
        idaptive_client.run(helper, ew) 
    except Exception as e:
        helper.log_error(str(e))