# encoding = utf-8

import logging

logger = logging.getLogger()

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
    """Validate the input."""
    pass


def collect_events(helper, ew):
    """
    Netskope Data collection.

    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class

    Step 1: Create a NetskopeWtClient object and set connection properties using input params.
    Step 2: Downloads bucket object files and stores in $SPLUNK_HOME/var/spool/splunk folder.
    """
    logger.info("This input is deprecated. Please use 'Web Transaction V2' input to get Web Transaction data.")
    return
