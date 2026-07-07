# encoding = utf-8

import os
import sys
import time
import datetime

from gti.core import inputs

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
  # risk_rating = definition.parameters.get('risk_rating', None)
  # exploitation_state = definition.parameters.get('exploitation_state', None)
  pass


def collect_events(helper, ew):
  inputs.collect_vulns_events(
      helper,
      ew,
      helper.get_arg('exploitation_state'),
      helper.get_arg('risk_rating'),
  )
