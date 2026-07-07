# encoding = utf-8

import proofpoint_utility as utility


def validate_input(helper, definition):
    """
    Calls validate_input method of utility
    :param helper: object of BaseModInput class
	:param definition: object containing input parameters
    """
    utility.validate_input(helper, definition, "message")


def collect_events(helper, ew):
    """
    Calls collect_events method of utility
    :param helper: object of BaseModInput class
	:param ew: object of EventWriter class
    """
    utility.collect_events(helper, ew, "message")
