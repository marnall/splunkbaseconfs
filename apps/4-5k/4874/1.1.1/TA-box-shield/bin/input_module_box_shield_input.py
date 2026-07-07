
# encoding = utf-8

import os
import sys
import time
import datetime
from box_shield_manager import BoxShieldManager
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
    if not definition.parameters.get('box_account'):
        helper.log_error("No Box account is configured")
        raise Exception("No Box account is configured")
    else:
        start_time = definition.parameters.get('start_time')
        if start_time:
            try:
                start_time = (datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S"))
            except Exception:
                msg = 'Invalid Start Time format.'
                helper.log_error("Error in start_time : {}".format(msg))
                raise Exception(msg)
            if start_time < (datetime.datetime.utcnow()-datetime.timedelta(days=364)) or start_time > datetime.datetime.utcnow():
                msg = 'Start Time should not be more than current time or less than one year of current time.'
                helper.log_error("Error: {}".format(msg))
                raise Exception(msg)
        

def collect_events(helper, ew):
    # Commenting the code to prevent data collection of smart access policy.
    # event_types = { "box:shield:alerts":["SHIELD_ALERT"], "box:shield:classification":["METADATA_INSTANCE_CREATE", "METADATA_INSTANCE_DELETE", "METADATA_INSTANCE_UPDATE", "METADATA_INSTANCE_COPY", "METADATA_TEMPLATE_CREATE","METADATA_TEMPLATE_DELETE","METADATA_TEMPLATE_UPDATE"], "box:shield:smartaccess:policy":["DOWNLOAD_ATTEMPT_BLOCKED", "SHARED_LINK_GENERATION_BLOCKED", "SHARED_LINK_ACCESS_BLOCKED", "EXTERNAL_COLLAB_INVITE_BLOCKED", "EXTERNAL_COLLAB_ACCESS_BLOCKED", "DOWNLOAD_JUSTIFIED", "EXTERNAL_COLLAB_INVITE_JUSTIFIED"] }
    event_types = { "box:shield:alerts":["SHIELD_ALERT"], "box:shield:classification":["METADATA_INSTANCE_CREATE", "METADATA_INSTANCE_DELETE", "METADATA_INSTANCE_UPDATE", "METADATA_INSTANCE_COPY", "METADATA_TEMPLATE_CREATE","METADATA_TEMPLATE_DELETE","METADATA_TEMPLATE_UPDATE"]}
    bsmanager = BoxShieldManager(helper, event_types)
    bsmanager.box_shield_start_collection()
