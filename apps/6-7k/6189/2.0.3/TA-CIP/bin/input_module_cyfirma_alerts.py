"""Input module for cyfirma alerts."""
# encoding = utf-8
import ta_cip_declare

from splunk.clilib import cli_common as cli
from collector.constants.default import (
    ADDITIONAL_PARAMTERS_CONFIG,
    ADDITIONAL_PARAMTERS_STANZA,
    DEFAULT_NUMBER_OF_RETRIES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SLEEP_TIME,
    ADDITIONAL_PARAM_NUMBER_OF_RETRIES,
    ADDITIONAL_PARAM_PAGE_SIZE,
    ADDITIONAL_PARAM_SLEEP_TIME,
)
from collector.constants.general import STANZA
from collector.constants.api import API_URL, API_KEY, GLOBAL_ACCOUNT


def validate_input(helper, definition):  # pylint: disable=W0613
    """Implement your own validation logic to validate the input stanza configurations."""
    # This example accesses the modular input variable
    # global_account = definition.parameters.get('global_account', None)
    pass  # pylint: disable=W0107


def collect_events(helper, ew,session_key):  # pylint: disable=C0103
    """Implement your own validation logic to validate the input stanza configurations.

    :param helper: Splunk helper for loggiing, interval, etc.
    :type helper: BaseModInput
    :param definition: The parameters for the proposed input passed by splunk .
    :type definition: Any
    """
    from collector.alerts_api import process_events  # pylint: disable=C0415

    # Fetching account information
    global_account = helper.get_arg(GLOBAL_ACCOUNT)
    api_key = global_account.get(API_KEY)
    api_url = global_account.get(API_URL)

    # Fetching Input name
    stanza_name = str(helper.get_input_stanza_names())

    # Fetching proxy data
    proxy_settings = helper.get_proxy()

    # Storing necessary data into dictionary
    config_details = {}
    helper.log_info(
        cli.getConfStanza(ADDITIONAL_PARAMTERS_CONFIG, ADDITIONAL_PARAMTERS_STANZA)
    )
    configs = cli.getConfStanza(
        ADDITIONAL_PARAMTERS_CONFIG, ADDITIONAL_PARAMTERS_STANZA
    )
    config_details[ADDITIONAL_PARAM_PAGE_SIZE] = (
        int(configs.get(ADDITIONAL_PARAM_PAGE_SIZE))
        if configs.get(ADDITIONAL_PARAM_PAGE_SIZE)
        else DEFAULT_PAGE_SIZE
    )
    config_details[ADDITIONAL_PARAM_NUMBER_OF_RETRIES] = (
        int(configs.get(ADDITIONAL_PARAM_NUMBER_OF_RETRIES))
        if configs.get(ADDITIONAL_PARAM_NUMBER_OF_RETRIES)
        else DEFAULT_NUMBER_OF_RETRIES
    )
    config_details[ADDITIONAL_PARAM_SLEEP_TIME] = (
        int(configs.get(ADDITIONAL_PARAM_SLEEP_TIME))
        if configs.get(ADDITIONAL_PARAM_SLEEP_TIME)
        else DEFAULT_SLEEP_TIME
    )
    config_details[STANZA] = stanza_name

    process_events(api_url, api_key, proxy_settings, config_details, helper, ew,session_key)
