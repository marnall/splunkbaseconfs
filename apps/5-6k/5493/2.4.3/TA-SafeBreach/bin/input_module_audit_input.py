
# encoding = utf-8
import ta_safebreach_declare  # noqa: F401

import os
import sys
import time
import datetime
import re

from ta_safebreach_audit_collector import AuditCollector
import TA_SafeBreach_startdate_validation
import ta_safebreach_const

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
    # safebreach_account = definition.parameters.get('safebreach_account', None)
    # start_date_time = definition.parameters.get('start_date_time', None)
    pass

def collect_audit_data(helper, ew):
    audit_event_collector = AuditCollector(helper,ew)
    audit_event_collector.collect_data()

def collect_events(helper, ew):
    input_name = helper.get_input_stanza_names()
    helper.log_info("Starting data collection for input {}".format(input_name))
    
    account = helper.get_arg('safebreach_account')
    if not account:
        raise Exception("Invalid safebreach_account for input '{}'.".format(input_name))

    start_date_time = helper.get_arg('start_date_time')
    try:
        formatted_start_date = datetime.datetime.strptime(
            start_date_time, ta_safebreach_const.START_DATETIME_FORMAT
        )
        if formatted_start_date >= datetime.datetime.utcnow():
            msg = "Please enter Start DateTime less than current DateTime."
            helper.log_error(msg)
            sys.exit()
    except ValueError:
        msg = "Please enter correct UTC date of format('YYYY-MM-DDTHH:MM:SSZ)."
        helper.log_error(msg)
        sys.exit()
    

    interval = helper.get_arg('interval')
    try:
        interval = int(interval)
    except:
        msg = "Interval must be an integer."
        helper.log_error(msg)
        sys.exit()
    if int(interval) < 60:
        msg = "Minimum value for input interval is 60"
        helper.log_error(msg)
        sys.exit()

    collect_audit_data(helper, ew)
