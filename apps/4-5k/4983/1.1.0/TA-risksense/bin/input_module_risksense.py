
# encoding = utf-8
import json
import sys
import splunk.entity as entity

from risksense_collect import RisksenseCollect


def validate_input(helper, definition):
    """
    Validate the input
    """
    pass


def collect_events(helper, ew):
    
    """
    Risksense Data collection

    :param helper: object of BaseModInput class
	:param ew: object of EventWriter class

    Step 1: Create a RisksenseCollect object and get input params.
    Step 2: Initialize a RisksenseConnect object and set connection properties i.e url, proxies, headers etc.
    Step 3: Collect and index events into splunk events using collect_risksense_events method.
    """

    input_name = helper.get_input_stanza_names()
    helper.log_info("Initiating data collection for input {}".format(input_name))

    try:
        rs_collect = RisksenseCollect(helper, ew)
        rs_collect.collect_risksense_events()
    except Exception as e:
        helper.log_error("Error occured while collecting data for input {} {}".format(input_name, e))
        sys.exit(1)

    helper.log_info("Successfully completed data collection for input {}".format(input_name))
