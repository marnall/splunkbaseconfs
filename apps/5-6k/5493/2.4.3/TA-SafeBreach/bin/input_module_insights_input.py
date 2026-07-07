
# encoding = utf-8

import os
import sys
import time
import datetime

from ta_safebreach_insights_collector import InsightsCollector
import ta_safebreach_const
'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
def collect_insights_data(helper, ew):
    insights_event_collector = InsightsCollector(helper,ew)
    insights_event_collector.collect_data()

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # safebreach_account = definition.parameters.get('safebreach_account', None)
    # start_date_time = definition.parameters.get('start_date_time', None)
    pass

def collect_events(helper, ew):
    input_name = helper.get_input_stanza_names()
    helper.log_info("Starting data collection for input {}".format(input_name))

    account = helper.get_arg('safebreach_account')
    if not account:
        raise Exception("Invalid safebreach_account for input '{}'.".format(input_name))

    interval = helper.get_arg('interval')
    try:
        interval = int(interval)
    except:
        msg = "Interval must be an integer."
        helper.log_error(msg)
        sys.exit()
    if int(interval) < 600:
        msg = "Minimum value for input interval is 600"
        helper.log_error(msg)
        sys.exit()

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

    collect_insights_data(helper, ew)
