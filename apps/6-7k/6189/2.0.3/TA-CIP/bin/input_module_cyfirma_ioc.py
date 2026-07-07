
# encoding = utf-8
import ta_cip_declare
import traceback
from splunk.clilib import cli_common as cli
from collector.constants.default import (ADDITIONAL_PARAMTERS_CONFIG, ADDITIONAL_PARAMTERS_STANZA, DEFAULT_NUMBER_OF_RETRIES,
                                         DEFAULT_PAGE_SIZE, DEFAULT_SLEEP_TIME, ADDITIONAL_PARAM_NUMBER_OF_RETRIES, ADDITIONAL_PARAM_PAGE_SIZE, ADDITIONAL_PARAM_SLEEP_TIME)
from collector.constants.general import STANZA
from collector.constants.api import IOC_API_ENDPOINT, API_URL, API_KEY, GLOBAL_ACCOUNT
'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # global_account = definition.parameters.get('global_account', None)
    pass


def collect_events(helper, ew,session_key):  # pylint: disable=C0103
    """Implement your own validation logic to validate the input stanza configurations
    :param helper: Splunk helper for loggiing, interval, etc.
    :type helper: BaseModInput
    :param definition: The parameters for the proposed input passed by splunk .
    :type definition: Any
    """

    from collector.ioc_api import process_events
    # Fetching account information
    global_account = helper.get_arg(GLOBAL_ACCOUNT)
    api_key = global_account.get(API_KEY)
    api_url = global_account.get(API_URL)
    api_url += IOC_API_ENDPOINT

    # Fetching Input name
    stanza_name = str(helper.get_input_stanza_names())
    helper.log_info(stanza_name)

    # Fetching proxy data
    proxy_settings = helper.get_proxy()

    # Fetching lookup name
    index = helper.get_arg("index")

    # Storing necessary data into dictionary
    config_details = {}
    config_details["index"] = index
   
    configs = cli.getConfStanza(
        ADDITIONAL_PARAMTERS_CONFIG, ADDITIONAL_PARAMTERS_STANZA)
    config_details[ADDITIONAL_PARAM_PAGE_SIZE] = int(configs.get(
        ADDITIONAL_PARAM_PAGE_SIZE)) if configs.get(ADDITIONAL_PARAM_PAGE_SIZE) else DEFAULT_PAGE_SIZE
    config_details[ADDITIONAL_PARAM_NUMBER_OF_RETRIES] = int(configs.get(ADDITIONAL_PARAM_NUMBER_OF_RETRIES)) if configs.get(
        ADDITIONAL_PARAM_NUMBER_OF_RETRIES) else DEFAULT_NUMBER_OF_RETRIES
    config_details[ADDITIONAL_PARAM_SLEEP_TIME] = int(configs.get(
        ADDITIONAL_PARAM_SLEEP_TIME)) if configs.get(ADDITIONAL_PARAM_SLEEP_TIME) else DEFAULT_SLEEP_TIME
    config_details[STANZA] = stanza_name

    try:
        process_events(api_url, api_key, proxy_settings,
                   config_details, helper, ew)
    except Exception as err:
        helper.log_info(err)
        helper.log_info(traceback.format_exc()) 
        raise err