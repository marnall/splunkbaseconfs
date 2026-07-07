# encoding = utf-8
from armis_apiclient import APIClient
from log_manager import setup_logging
import re

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
    """Implement your own validation logic to validate the input stanza configurations."""
    # This example accesses the modular input variable
    pass


def collect_events(helper, ew):
    """To collect data for armis devices."""
    input_name = helper.get_input_stanza_names()
    account = helper.get_arg('global_account')
    logger = setup_logging('ta_armis_device_{}'.format(input_name))
    if not account:
        logger.error("input_name={} | message=invalid_account | Invalid global_account".format(input_name))
        return False

    try:
        interval = int(helper.get_arg('interval'))
    except Exception:
        logger.error('input_name={} | message=invalid_interval_value | Please enter valid interval value.'.format(input_name))
        return False
  
    if interval < 0:
        logger.error('input_name={} | message=invalid_interval_value | Please enter positive interval.'.format(input_name))
        return False

    aql_query = helper.get_arg('aql_query')
    if not re.search("timeFrame:", aql_query) or not re.search("in:devices", aql_query):
        logger.error("input_name={} | Device Query field must contain timeFrame and in:devices attributes".format(input_name))
        return False

    if not re.match("[\s\S]*timeFrame:\S\s*([1-9][0-9]*)", aql_query):
        logger.error("input_name={} | message=invalid_value | Please enter timeFrame value in the range of [1-90] days. Ex. timeFrame:\"30 days\"".format(input_name))
        return False

    if len(aql_query) > 1000:
        logger.error("input_name={} | message=invalid_value | Length of Device Query field should be between 1 and 1000.".format(input_name))
        return False

    logger.info('input_name={} | message=data_collection_started | Data collection for Armis device started.'.format(input_name))

    # Initializing object of APICLient
    api_client = APIClient(helper, ew, logger)
    # Calling of method for actual data collection and getting data
    # for armis devices and further for armis applicaion and checking for retry mechanism.
    api_client.get_data(ew)

    logger.info('input_name={} | message=data_collection_finished | Execution of script is finished.'.format(input_name))
