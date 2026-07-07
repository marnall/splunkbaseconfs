
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
    """To collect the assets data the collection logic will be start from here."""
    script_start_time = time.time()
    input_name = helper.get_arg('name')
    cycognito_account = helper.get_arg('cycognito_account')
    asset_types = helper.get_arg('asset_types')

    logger = setup_logging('ta_cycognito_{}'.format(input_name))

    logger.info("CyCognito Data_Collection: Script Status=Invoked for "
                "input_name={}".format(input_name))

    # validate input params
    validate = utils.validate_input_params(helper, logger, "asset_types")
    if not validate:
        logger.info("CyCognito Data_Collection: Execution of the script is finished for "
                    "input_name={}. time_taken={} minutes.".format(input_name, (time.time() - script_start_time) / 60))
        return

    if asset_types == ["*"]:
        list_of_types = constants.ASSET_TYPES
    else:
        list_of_types = asset_types
    logger.info("CyCognito Data_Collection:  Script Status=Invoked "
                "cycognito_account={} & asset_type={}".format(cycognito_account['name'], list_of_types))

    # initialize the object
    cycognito_object = CycognitoClient(helper, ew, logger, "assets")

    # pagination
    for type in list_of_types:
        logger.info(
            "CyCognito Data_Collection: Type=Assets Status=\"Collection Started\" for"
            " asset_type={}".format(type))
        no_of_events = 0
        page = 0
        while True:
            url = 'https://' + \
                cycognito_account['platform_url'] + \
                constants.ASSETS_ENDPOINT + '/' + type
            response = cycognito_object.collect_cycognito_data(url, page)
            if response:
                sourcetype = helper.get_sourcetype() + ":" + type
                event_count = cycognito_object.write_events_to_splunk(
                    response, sourcetype)
                no_of_events += event_count
                logger.debug("CyCognito Data_Collection: asset_type={} page_number={} event_count={} ".format(
                    type, page, event_count))
                page += 1
            else:
                logger.debug(
                    "CyCognito Data_Collection: No {} assets events are collected from"
                    " page_number={}.".format(type, page))
                break

        removed_assets_count = 0
        page_num = 0
        collect_removed_assets = is_true(helper.get_arg('collect_removed_assets'))
        if collect_removed_assets:
            data = [{"op": "in", "field": "status", "values": ["removed"]}]
            while True:
                removed_assets_url = 'https://' + \
                    cycognito_account['platform_url'] + \
                    constants.ASSETS_ENDPOINT + '/' + type
                response = cycognito_object.collect_cycognito_data(removed_assets_url, page_num, data=data)
                if response:
                    sourcetype = helper.get_sourcetype() + ":" + type
                    removed_assets_count_per_page = cycognito_object.write_events_to_splunk(
                        response, sourcetype)
                    removed_assets_count += removed_assets_count_per_page
                    logger.debug("CyCognito Removed Assets Data_Collection: asset_type={} page_number={} event_count={} ".format(
                        type, page_num, removed_assets_count_per_page))
                    page_num += 1
                else:
                    logger.debug(
                        "CyCognito Removed Assets Data_Collection: No {} assets events are collected from"
                        " page_number={}.".format(type, page_num))
                    break
        
        logger.info("CyCognito Data_Collection: Total no. of collected events for input_name={} & asset_type={}:"
                    " event_count={}".format(
                        input_name, type, no_of_events + removed_assets_count))

    logger.info(
        "CyCognito Data_Collection: Execution of the script is finished for input_name={}. time_taken={} "
        "minutes.".format(input_name, (time.time() - script_start_time) / 60))
