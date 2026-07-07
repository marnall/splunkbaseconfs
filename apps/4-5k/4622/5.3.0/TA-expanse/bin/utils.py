import datetime
import sys

from splunklib.results import Message
from exceptions import AbortSyncException

if sys.version_info >= (3, 3):
    from functools import reduce

from constants import (LAST_RUN_ALERTS, ALERTS_TIME_FORMAT, ALERT_ID_PATH, SPLUNK_EVENT_TIME_FORMAT,
                       SPLUNK_CLIENT_PAGE_LIMIT)
from dateutil.parser import parse
from xpanse.client import XpanseClient

from six.moves.urllib.parse import quote_plus


def dict_to_kv_string(data):
    """Converts a dictionary to key=value string

    Arguments:
        data {dict} -- Dict to convert

    Returns:
        str -- string in key=value format
    """

    return reduce(
        lambda acc, val: "{} {}={}".format(acc, val[0], val[1]),
        list(data.items()),
        '',
    ).strip()


def get_proxy(helper):
    """Build proxy with input settings.

    Arguments:
        proxy_settings {dict} -- Dict contains Proxy type, Username, Password,
        Port and Url

    Returns:
        proxy -- proxy url dict
    """

    proxy_settings = helper.get_proxy()
    if proxy_settings:
        proxy_type = proxy_settings['proxy_type']
        proxy_username = quote_plus(proxy_settings.get('proxy_username')) \
            if proxy_settings.get('proxy_username') is not None else proxy_settings.get('proxy_username')
        proxy_password = quote_plus(proxy_settings.get('proxy_password')) \
            if proxy_settings.get('proxy_password') is not None else proxy_settings.get('proxy_password')
        if proxy_username and proxy_password:
            proxy = {
                'http': '{proxy_type}://{user}:{password}@{host}:{port}'.format(
                    proxy_type=proxy_type,
                    user=proxy_username,
                    password=proxy_password,
                    host=proxy_settings['proxy_url'],
                    port=proxy_settings['proxy_port'],
                ),
                'https': '{proxy_type}://{user}:{password}@{host}:{port}'.format(
                    proxy_type=proxy_type,
                    user=proxy_username,
                    password=proxy_password,
                    host=proxy_settings['proxy_url'],
                    port=proxy_settings['proxy_port'],
                ),
            }
        else:
            proxy = {
                'http': '{proxy_type}://{host}:{port}'.format(
                    proxy_type=proxy_type,
                    host=proxy_settings['proxy_url'],
                    port=proxy_settings['proxy_port'],
                ),
                'https': '{proxy_type}://{host}:{port}'.format(
                    proxy_type=proxy_type,
                    host=proxy_settings['proxy_url'],
                    port=proxy_settings['proxy_port'],
                ),
            }
        helper.log_debug(
            "Proxies will be used with the following proxy settings, settings={}".format(proxy))
    else:
        proxy = {}
        helper.log_debug("No proxy settings will be used.")

    return proxy


def get_configuration_settings(helper):
    """Build configuration settings from helper

    Args:
        helper (smi.Script): A helper object that controls logging and state

    Returns:
        str: The username from settings
        str: The password from settings
        str: The JWT Token from settings
        str: The base URL for Expansder V2 APIs
        bool: The use_advanced_auth configuration from settings
        str:
        str: The start date from settings
        str: The name of the input
        bool: True if Events is enabled, False otherwise
        bool: True if Assets is enabled, False otherwise
        bool: False for Exposures as we migrate to Issues
    """

    global_account = helper.get_arg('global_account')
    username = global_account.get('username', '')
    password = global_account.get('password', '')

    token = helper.get_arg('token')
    server_url = helper.get_arg('server_url')
    use_advanced_auth = helper.get_arg('use_advanced_auth') == '1'
    start_date = helper.get_arg('start_date_utc')
    input_name = helper.get_arg('name').lower()
    enable_alert_updates = helper.get_arg('enable_alert_updates')
    enable_assets = helper.get_arg('enable_assets')
    enable_services = helper.get_arg('enable_services')
    utc_offset = helper.get_arg('utc_offset')
    api_key_id = helper.get_arg('api_key_id')

    if start_date:
        helper.log_info('Start date: {} received'.format(start_date))

    helper.log_debug(
        'Configuration set with username={}, server_url={}, use_advanced_auth={}, api_key_id={}, start_date={}, '
        'enable_alert_updates={}, enable_assets={}, enable_services={}, '
        'utc_offset={}'
        .format(username, server_url, use_advanced_auth, api_key_id, start_date, enable_alert_updates,
                enable_assets, enable_services, utc_offset))

    # pylint: disable=bad-continuation
    return username, password, token, server_url, use_advanced_auth, api_key_id, start_date, enable_alert_updates, \
        enable_assets, enable_services, input_name, utc_offset


def get_expanse_client(helper, token, server_url, proxy, api_key_id, use_advanced_auth=False) -> XpanseClient:
    """Returns expanse connector

    Args:
        helper (smi.Script): A helper object that controls logging and state
        token (str): The JWT Token for hitting the APIs
        server_url (str): The base URL for Expanse APIs
        api_key_id (str): The id of the generated api key
        proxy (dict): Dictionary mapping protocol to the URL of the proxy
        use_advanced_auth: boolean for whether or not to use advanced auth

    Returns:
        XpanseClient: The Expanse Connector object
    """

    try:
        expanse = XpanseClient(api_key=token, url=server_url, use_advanced_auth=use_advanced_auth,
                               api_key_id=api_key_id, proxies=proxy)
    except Exception as e:
        helper.log_error("Error in initializing expanse. e={}".format(str(e)))
        raise e

    return expanse


def get_start_date(helper, input_name, start_date=None, utc_offset=None):
    """Calculate start and end dates.

    Args:
        helper (smi.Script): A helper object that controls logging and state
        input_name (str): Name of the input of splunk TA (allows for separation between multiple Xpanse TA inputs)
        start_date (str, optional): the start date for the run, defaulted to None
        utc_offset (str, optional): the utc offset of the splunk server (input from user-facing inputs). Defaulted None

    Returns:
        str: The start date in UTC
    """
    # Convert hours from input to minutes in offest, in case someone wants to do a 30 min offset
    offset = 0.0
    try:
        offset = float(utc_offset) * 60
    except (ValueError, TypeError) as e:
        helper.log_debug("Input value for offset {} is not valid. Defaulting to 0 utc offset. Error: {}".format(
            utc_offset, str(e)))
    now_with_offset = datetime.datetime.now() - datetime.timedelta(minutes=offset)

    last_run = helper.get_check_point("{}_{}".format(LAST_RUN_ALERTS, input_name))
    helper.log_debug("Last run date for input {}: {}".format(input_name, last_run))

    if last_run:
        start_datetime_utc = parse(last_run)
        helper.log_debug("Last complete run was found: {}".format(start_datetime_utc.strftime(ALERTS_TIME_FORMAT)))
    elif start_date:
        start_datetime_utc = parse(start_date)
    else:
        start_datetime_utc = (now_with_offset - datetime.timedelta(days=2))

    if start_datetime_utc < (now_with_offset - datetime.timedelta(days=90)):
        start_datetime_utc = (now_with_offset - datetime.timedelta(days=90))
        helper.log_debug("Start date set to earlier than 90 days ago. Pushing start date to {}."
                         .format(start_datetime_utc.strftime(ALERTS_TIME_FORMAT)))

    if start_datetime_utc + datetime.timedelta(minutes=5) > now_with_offset:
        helper.log_debug("Alerts data is up-to-date. Skipping")
        return None

    start_datetime_utc = start_datetime_utc.strftime(ALERTS_TIME_FORMAT)
    helper.log_debug("Start date utc: {}".format(start_datetime_utc))
    return start_datetime_utc


def fetch_existing_alerts(input_name, helper, start_date, splunk_client):
    """Method to fetch alert ids that already exist in splunk. The query looks for alerts with a
        server_creation_time of greater than 2 days ago from the start date. Start date is determined by the config
        of the integration on the first run, or the last processed alert on subsequent runs.

        Args:
            input_name (str): The name of the input for the integration.
            helper (smi.Script): A helper object that controls logging and state.
            start_date (str): The date for the most recently processed alert.
            splunk_client (bin.SplunkClient): The client for connecting to the splunk api to query and retrieve alerts.
        Returns:
            list(int): The alert ids that were found in splunk.
        """
    if start_date is None:
        return []

    try:
        helper.log_debug(f"start_date for input_name {input_name}: "
                         f"{parse(start_date).strftime(SPLUNK_EVENT_TIME_FORMAT)}")
        splunk_lookback = (parse(start_date) - datetime.timedelta(days=2)).strftime(SPLUNK_EVENT_TIME_FORMAT)
        query = (f"search index={helper.get_expander_index()} | spath input_name | search "
                 f"input_name={input_name} | spath server_creation_time | search "
                 f"server_creation_time>={splunk_lookback} | stats values({ALERT_ID_PATH})")
        job = splunk_client.query(query)
        ids = get_query_job_results(helper, job, input_name, splunk_client)
        helper.log_debug(f"Debugging deduplication: found alerts: {len(ids)}, {ids}")
        return ids
    except Exception as e:
        helper.log_error("Unable to query instance for duplicates.")
        helper.log_debug(f"Unable to query instance for duplicates with exception: {e}")
        raise AbortSyncException(f"Unable to query instance for duplicates with exception: {e}")


def get_query_job_results(helper, job, input_name, splunk_client):
    """
    Method to paginaate through query results and return the list of existing alert ids in splunk
    Note that the Splunk page limit is 50k

        Args:
            helper (smi.Script): A helper object that controls logging and state.
            job (splunklib.Job): Job object that represents the query job in splunk.
            input_name (str): The name of the input for the integration.
            splunk_client (bin.SplunkClient): The client for connecting to the splunk api to query and retrieve alerts.
        Returns:
            list(int): The alert ids that were found in splunk.
    """

    ids = []
    offset = 0

    splunk_client.wait_for_query_job_to_complete(helper, job, input_name)
    result_count = splunk_client.get_job_results_counts(job)
    while offset < int(result_count):
        kwargs = {"count": SPLUNK_CLIENT_PAGE_LIMIT,
                  "offset": offset}
        helper.log_debug(f"Debugging deduplication for {input_name}:"
                         f"Get next page of results from Splunk. Offset: {offset}")
        results_reader = splunk_client.get_query_results_reader(helper, job, input_name, **kwargs)
        ids = read_alert_ids_from_results(helper, results_reader, ids)
        offset += SPLUNK_CLIENT_PAGE_LIMIT
    return ids


def read_alert_ids_from_results(helper, results_reader, ids):
    """
    Method to extract reusted logic for parsing out the alert IDs from the Splunk Results reader
    Args:
            helper (smi.Script): A helper object that controls logging and state.
            results_reader (splunklib.results.JSONResultsReader): helper object that reads in results from the splunk
                            query job results.
            ids (list(int)): Existing list the alert IDs
        Returns:
            list(int): The alert ids that were found in the current splunk job ResultsReader.
    """
    for result in results_reader:
        if isinstance(result, Message):
            # Diagnostic messages may be returned in the results
            helper.log_error(f"{result.type}: {result.message}")
            raise Exception(f"{result.type}: {result.message}")
        elif isinstance(result, dict):
            helper.log_debug(f"Debugging deduplication: Result: {result}")
            ids.extend(result[f'values({ALERT_ID_PATH})'])
    return ids


def should_ingest_alerts(enable_alert_updates, alert_start_time):
    return enable_alert_updates == '1' and alert_start_time is not None
