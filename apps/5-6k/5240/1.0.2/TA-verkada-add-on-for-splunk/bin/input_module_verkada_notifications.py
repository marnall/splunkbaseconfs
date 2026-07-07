
# encoding = utf-8

import os
import sys
import time
import json
from datetime import datetime, timedelta

from verkada_utils import get_notifications
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
    # organization_id = definition.parameters.get('organization_id', None)
    # api_key = definition.parameters.get('api_key', None)
    pass

def collect_events(helper, ew):
    organization_id = helper.get_arg('organization_id')
    api_key = helper.get_arg('api_key')
    check_point_key = "{}_notifications".format(organization_id)
    last_indexed_time = helper.get_check_point(check_point_key)

    if last_indexed_time:
        start_time = last_indexed_time
    else:
        start_time = int((datetime.now() - timedelta(minutes=5)).timestamp())

    end_time = int((datetime.now() - timedelta(seconds=5)).timestamp())
    notifications = get_notifications(helper, organization_id, api_key, start_time, end_time)
    for notification in notifications:
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(),
                                 sourcetype=helper.get_sourcetype(), data=json.dumps(notification))
        ew.write_event(event)
    helper.save_check_point(check_point_key, end_time)
