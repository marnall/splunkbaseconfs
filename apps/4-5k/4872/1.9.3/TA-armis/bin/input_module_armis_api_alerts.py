# encoding = utf-8
from armis_apiclient import APIClient
import time
from log_manager import setup_logging

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    # This example accesses the modular input variable
    # global_account = definition.parameters.get('global_account', None)
    pass


def collect_events(helper, ew):
    """To collect data for armis alerts."""
    input_name = helper.get_input_stanza_names()
    account = helper.get_arg('global_account')
    logger = setup_logging('ta_armis_api_alert_{}'.format(input_name))
    if not account:
        logger.error("input_name={} | message=invalid_account | Invalid global_account for input.".format(input_name))
        return False
    try:
        interval = int(helper.get_arg('interval'))
    except Exception:
        logger.error('input_name={} | message=invalid_interval_value | Please enter valid interval value.'.format(input_name))
        return False
  
    if interval < 60 or interval > 86400:
        logger.error('input_name={} | message=invalid_interval_value | Interval value should be between 60 to 86400 seconds.'.format(input_name))
        return False
    try:
        interval = int(helper.get_arg('lookback_days'))
    except Exception:
        logger.error('input_name={} | message=invalid_lookback_value | Please enter valid lookback days value.'.format(input_name))
        return False
  
    st_time = time.time()
    logger.info('input_name={} | message=data_collection_started |Data collection for Armis device started.'.format(input_name))
    logger.info('input_name={} | message=start_time | Data collection start time: {}'.format(input_name, st_time))
    # Initializing object of APICLient
    api_client = APIClient(helper, ew, logger)
    # Calling of method for actual data collection and getting CVEs
    # for armis vulnerability and checking for retry mechanism.
    api_client.get_alerts(ew)
    logger.info('input_name={} | message=end_time | Data collection completed. End time: {}'.format(input_name, time.time()-st_time))
    logger.info('input_name={} | message=data_collection_done | Execution of script is finished'.format(input_name))