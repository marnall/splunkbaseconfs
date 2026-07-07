# encoding = utf-8

from armis_alerts_enrichment import ArmisAlert
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
    logger = setup_logging('ta_armis_alert_{}'.format(input_name))
    if not account:
        logger.error("input_name={} | message=invalid_account | Invalid global_account.".format(input_name))
        return False

    try:
        interval = int(helper.get_arg('interval'))
    except Exception:
        logger.error('input_name={} | message=invalid_interval_value | Please enter valid interval value.'.format(input_name))
        return False

    if interval < 0:
        logger.error('input_name={} | message=invalid_interval_value | Please enter positive interval.'.format(input_name))
        return False

    logger.info('input_name={} | message=data_collection_started | Data collection for Armis alerts started for input'.format(input_name))

    # Initializing object of ArmisAlert
    armis_alert = ArmisAlert(helper, ew, logger)
    # Calling get_alerts method for actual data collection
    armis_alert.get_alerts()
    logger.info('input_name={} | message=data_collection_finished | Execution of script is finished for input'.format(input_name))
