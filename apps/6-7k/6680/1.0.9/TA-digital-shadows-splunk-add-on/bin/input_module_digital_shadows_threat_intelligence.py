# encoding = utf-8
import json
from datetime import datetime, timedelta

from searchlight.client import SearchLightIndicatorsPoller
from digitalshadows.client import DigitalShadowsIntelIncidentPoller
from searchlight_request_handler import SearchLightRequestHandler
from ds_request_handler import DigitalShadowsRequestHandler
from splunk_logger import SplunkLogger
from utils import constants
from utils.digital_shadows_utility import validate_since, get_config, parse_date
from utils.kv_store import get_ioc_kv_store_manager
import traceback


def validate_input(_helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    since = definition.parameters.get(constants.SINCE, None)
    if not since:
        return
    validate_since(since)


def collect_events(helper, ew):
    splunk_logger = SplunkLogger(helper)
    config = get_config(helper)
    splunk_logger.debug("{} Config: {}".format(constants.THREAT_INTELLIGENCE, config))
    splunk_logger.info("{} config extraction done !!".format(constants.THREAT_INTELLIGENCE))
    start_poller(config, helper, splunk_logger, ew)
    splunk_logger.info("{} polling completed !!".format(constants.THREAT_INTELLIGENCE))


def start_poller(config, helper, splunk_logger, ew):
    """
    start data poller for intelligence
    @param config: config required to poll data
    @param helper: splunk helper
    @param splunk_logger: logger
    @param ew: splunk ew object
    """
    is_indicators_polling_done = False
    is_intel_incidents_polling_done = False
    ioc_kv_store_manager = None
    if config.get('threat_intelligence_updates'):
        splunk_logger.info(f"{constants.THREAT_INTELLIGENCE}: Intel Updates polling started !!")
        ds_intel_incidents_poller = get_intel_incidents_poller(config, helper, splunk_logger)
        while not is_intel_incidents_polling_done:
            try:
                is_intel_incidents_polling_done = intel_incident_poller(helper, config, splunk_logger,
                                                                        ds_intel_incidents_poller, ew)
            except Exception as e:
                splunk_logger.error(
                    f"{constants.THREAT_INTELLIGENCE}: Intel Updates Polling failed with error: {str(e)} \n trace: {traceback.format_exc()}")
                break
        splunk_logger.info(f"{constants.THREAT_INTELLIGENCE}: Intel Updates polling done !!")
    if config.get('ingesting_iocs'):
        try:
            splunk_logger.info(f"{constants.THREAT_INTELLIGENCE}: IOCs polling started !!")
            ioc_kv_store_manager = get_ioc_kv_store_manager(helper)
            search_light_indicators_poller = get_indicators_poller(config, helper, splunk_logger)
        except Exception as e:
            splunk_logger.error(
                "{} Error while getting kv store manager: {}".format(constants.THREAT_INTELLIGENCE, str(e)))
        if ioc_kv_store_manager:
            while not is_indicators_polling_done:
                try:
                    is_indicators_polling_done = indicators_poller(helper, config, ioc_kv_store_manager,
                                                                   splunk_logger,
                                                                   search_light_indicators_poller, ew)
                except Exception as e:
                    splunk_logger.error(
                        f"{constants.THREAT_INTELLIGENCE}: IOC Polling failed with error: {str(e)} \n trace: {traceback.format_exc()}")
                    break
            splunk_logger.info(f"{constants.THREAT_INTELLIGENCE}: IOCs polling done !!")


def get_indicators_poller(config, helper, splunk_logger):
    search_light_request_handler = SearchLightRequestHandler(helper, config[constants.SEARCHLIGHT_API_BASE_URL],
                                                             config[constants.API_ACCOUNT_ID],
                                                             config[constants.SEARCHLIGHT_API_KEY],
                                                             config[constants.SEARCHLIGHT_API_SECRET],
                                                             use_proxy=config[constants.USE_PROXY])
    search_light_indicators_poller = SearchLightIndicatorsPoller(search_light_request_handler,
                                                                 splunk_logger)
    return search_light_indicators_poller


def get_intel_incidents_poller(config, helper, splunk_logger):
    ds_request_handler = DigitalShadowsRequestHandler(helper, config[constants.DS_API_BASE_URL],
                                                      config[constants.API_ACCOUNT_ID],
                                                      config[constants.SEARCHLIGHT_API_KEY],
                                                      config[constants.SEARCHLIGHT_API_SECRET],
                                                      use_proxy=config[constants.USE_PROXY])
    intel_incidents_poller = DigitalShadowsIntelIncidentPoller(ds_request_handler,
                                                               splunk_logger)
    return intel_incidents_poller


def indicators_poller(helper, config, kv_store_manager, splunk_logger, search_light_indicators_poller, ew):
    """Perform a poll of SearchLight API for indicators of compromise

    Args:
        helper: Splunk helper
        config: input configuration
        kv_store_manager: KV store manager used to ingest IOCs
        splunk_logger (SplunkLogger): logger instance
        search_light_indicators_poller (_type_): _description_
        ew: Splunk event writer

    Returns:
        bool: True if no new results have been found this poll. False otherwise.
    """
    input_name = helper.get_input_stanza_names()
    checkpoint = helper.get_check_point(input_name) or dict()
    last_event_num = checkpoint.get(constants.IOC_LAST_EVENT_NUM, 0)
    # initialise the last-known event num we processed (default: 0)
    # persists between executions, so we restart where we left off.

    since = config[constants.SINCE]
    if since:
        try:
            since = parse_date(since)
        except Exception as e:
            splunk_logger.error(
                f"{constants.THREAT_INTELLIGENCE}: error while parsing since date: {since} ERROR: {str(e)}")
            raise e
    poll_result = search_light_indicators_poller.poll_indicators(event_num_start=last_event_num,
                                                                 event_created_after=since)
    splunk_logger.debug(
        f"{constants.THREAT_INTELLIGENCE}: data polled successfully till : {poll_result.max_event_number}")
    if poll_result.max_event_number == last_event_num:
        splunk_logger.info(
            f"{constants.THREAT_INTELLIGENCE}: IOC Polling done. last_event_num: {last_event_num}")
        return True
    data = poll_result.data

    if data:
        # write to events
        write_to_splunk(data, ew, helper, config, constants.SOURCE_TYPE_IOC)
        splunk_logger.debug(
            f"{constants.THREAT_INTELLIGENCE}: events written to splunk till : {poll_result.max_event_number}")
        # write to kv store
        kv_store_manager.add_batch(data)
        splunk_logger.debug(
            f"{constants.THREAT_INTELLIGENCE}: events written to kv store till : {poll_result.max_event_number}")

    # update last event no so that next iteration we should fetch further record to avoid duplication
    splunk_logger.debug(
        f"{constants.THREAT_INTELLIGENCE}: Saving checkpoint for IOC updates: {checkpoint}")
    checkpoint[constants.IOC_LAST_EVENT_NUM] = poll_result.max_event_number
    helper.save_check_point(input_name, checkpoint)
    return False


def intel_incident_poller(helper, config, splunk_logger, search_light_intel_incident_poller, ew):
    """Perform a poll of Digital Shadows intelligence incidents.

    Uses the stored state of the last known 'start date' of polling and polls for any intel incidents
    created between that date and a week after.

    Args:
        helper: Splunk helper
        config: input configuration
        splunk_logger (SplunkLogger): logger instance
        search_light_intel_incident_poller (DigitalShadowsIntelIncidentPoller): client responsible for retrieving intel incidents from Digital Shadows API
        ew: Splunk event writer

    Raises:
        e: exceptions, most likely arising from calling to the Digital Shadows API.

    Returns:
        bool: True if we have retrieved no new data and are thus finished on this cycle, False otherwise
    """
    input_name = helper.get_input_stanza_names()
    since = config[constants.SINCE]

    checkpoint = helper.get_check_point(input_name) or dict()
    start_date = checkpoint.get(constants.INTEL_INCIDENT_START_DATE, since)
    try:
        start_date_datetime = parse_date(start_date)
    except Exception as e:
        splunk_logger.error(
            f"{constants.THREAT_INTELLIGENCE}: error while parsing since date: {start_date} ERROR: {str(e)}")
        raise e

    end_date = start_date_datetime + timedelta(weeks=1)

    end_iso = str(end_date.isoformat()) + 'Z'
    date_range = f"{start_date}/{end_iso}"
    max_event_date = start_date

    up_to_date = end_date > datetime.now()
    try:
        # Poll starting from offset 0 and increasing by the page-size each time
        # stop once we get 0 results for the given page
        offset = 0
        limit = 100
        while True:
            poll_result = search_light_intel_incident_poller.poll_intel_incidents(incident_offset=offset,
                                                                                  date_range=date_range,
                                                                                  limit=limit)
            # walk the limit forward, even if it takes us beyond the end of the known total
            offset += limit
            splunk_logger.debug(
                f"{constants.THREAT_INTELLIGENCE}: Intel data polled successfully till : {offset}"
                f" for date range : {date_range}")
            data = poll_result.data
            if data:
                max_event_date = max([x['modified'] for x in data])
                write_to_splunk(data, ew, helper, config, constants.SOURCE_TYPE_INTEL_INCIDENTS)
                splunk_logger.info(
                    f"{constants.THREAT_INTELLIGENCE}: {constants.INTEL_INCIDENT_OFFSET} Intel data written till "
                    f"{offset}")
            else:
                if max_event_date == start_date and not up_to_date:
                    # whilst catching up, have this exception where we allow
                    # the window to walk forward if there was no data in the 1w window given
                    max_event_date = end_iso
                splunk_logger.info(
                    f"{constants.THREAT_INTELLIGENCE}: Intel Polling done.")
                break
    except Exception as e:
        # if anything fail saving checkpoint to restart application with previous state
        checkpoint[constants.INTEL_INCIDENT_START_DATE] = max_event_date
        helper.save_check_point(input_name, checkpoint)
        raise e

    checkpoint[constants.INTEL_INCIDENT_START_DATE] = max_event_date
    splunk_logger.debug(
        f"{constants.THREAT_INTELLIGENCE}: Saving checkpoint for intel updates: {checkpoint}")
    helper.save_check_point(input_name, checkpoint)
    if up_to_date:
        # finished if our end-date of our polling is newer than the current datetime
        return True
    else:
        return False


def write_to_splunk(data, ew, helper, config, source_type):
    for entry in data:
        event = helper.new_event(json.dumps(entry), time=None, host=None, index=config[constants.INDEX],
                                 source=constants.DIGITAL_SHADOWS, sourcetype=source_type, done=True,
                                 unbroken=True)
        ew.write_event(event)
