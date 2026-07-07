
# encoding = utf-8

import time

import ta_cycognito_constants as constants
import ta_cycognito_utils as utils
from ta_cycognito_apiclient import CycognitoClient
from ta_cycognito_logger_manager import setup_logging
from solnlib.utils import is_true

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    pass


def collect_events(helper, ew):
    """To collect the issues data the collection logic will be start from here."""
    script_start_time = time.time()
    no_of_events = 0
    page = 0

    input_name = helper.get_arg('name')
    cycognito_account = helper.get_arg('cycognito_account')
    logger = setup_logging('ta_cycognito_{}'.format(input_name))
    logger.info("CyCognito Data_Collection: Script Status=Invoked for input_name={}".
                format(input_name))

    # validate input params
    validate = utils.validate_input_params(helper, logger)
    if not validate:
        logger.info("CyCognito Data_Collection: Execution of the script is finished for "
                    "input_name={}. time_taken={} minutes.".format(input_name, (time.time() - script_start_time) / 60))
        return

    url = 'https://' + \
        cycognito_account['platform_url'] + constants.ISSUES_ENDPOINT

    resolved_issues_url = 'https://' + \
        cycognito_account['platform_url'] + constants.RESOLVED_ISSUES_ENDPOINT

    # initialize the object
    cycognito_object = CycognitoClient(helper, ew, logger, "issues")

    # pagination
    logger.info(
        "CyCognito Data_Collection: Type=Issues Status=\"Collection Started\" for"
        " cycognito_account={} ".format(cycognito_account['name']))
    while True:
        response = cycognito_object.collect_cycognito_data(url, page)
        if response:
            event_count = cycognito_object.write_events_to_splunk(response)
            no_of_events += event_count
            logger.debug("CyCognito Data_Collection: page_number={} event_count={}".format(
                page, event_count))
            page += 1
        else:
            logger.debug(
                "CyCognito Data_Collection: No issues events are collected from page_number={}.".format(page))
            break

    page_num = 0
    no_of_resolved_issues = 0
    collect_resolved_issues = is_true(helper.get_arg('collect_resolved_issues'))
    if collect_resolved_issues:
        while True:
            response = cycognito_object.collect_cycognito_data(resolved_issues_url, page_num)
            if response:
                no_of_resolved_issues_per_page = cycognito_object.write_events_to_splunk(response)
                no_of_resolved_issues += no_of_resolved_issues_per_page
                logger.debug("CyCognito Resolved Issues Data_Collection: page_number={} event_count={}".format(
                    page_num, no_of_resolved_issues_per_page))
                page_num += 1
            else:
                logger.debug(
                    "CyCognito Resolved Issues Data_Collection: No issues events are collected from page_number={}.".format(page))
                break
    logger.info("CyCognito Data_Collection: Total no. of collected events for issues having input_name={}:"
                " event_count={}".format(
                    input_name, no_of_events + no_of_resolved_issues))

    logger.info(
        "CyCognito Data_Collection: Execution of the script is finished for input_name={}. time_taken={} "
        "minutes.".format(input_name, (time.time() - script_start_time) / 60))
