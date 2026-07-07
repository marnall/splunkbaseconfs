# encoding = utf-8

import os
import sys
import time
import datetime

from virustotal.core import inputs

"""
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""
"""
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
"""


def validate_input(helper, definition):
  """Implement your own validation logic to validate the input stanza configurations"""
  # This example accesses the modular input variable
  # threat_lists_category = definition.parameters.get('ioc_stream_filter', None)
  pass


def collect_events(helper, ew):
  inputs.collect_ioc_stream_events(
      helper, ew, helper.get_arg('ioc_stream_filter')
  )
