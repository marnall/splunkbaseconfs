# encoding = utf-8

import os
import sys
import time
import datetime
import traceback
from riskiqsis_client import RiskiqsisClient


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    pass


def collect_events(helper, ew):
    """Collect RiskIQ SIS data."""
    input_name = helper.get_input_stanza_names()
    helper.log_info("Starting data collection for input {}".format(input_name))
    try:
        riskiqsis_client = RiskiqsisClient(helper)
        riskiqsis_client.collect_data()
    except Exception as e:
        helper.log_error("Error occured while collecting data for input {}. Exception: {}".format(input_name, str(e)))
        helper.log_error(traceback.format_exc())
        sys.exit(1)

    helper.log_info("Data collection process is completed for input {}".format(input_name))
