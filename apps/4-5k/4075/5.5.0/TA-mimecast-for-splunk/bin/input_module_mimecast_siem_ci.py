
# encoding = utf-8

import os
import sys
import time
import datetime
import mimecast

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
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""
    api = mimecast.MimecastApi(helper=helper, ew=ew)
    api.fetch_siem_ci_logs()
