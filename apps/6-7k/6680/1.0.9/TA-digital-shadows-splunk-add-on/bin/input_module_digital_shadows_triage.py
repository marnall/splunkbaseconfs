import json
import traceback
from searchlight.client import SearchLightTriagePoller
from searchlight_request_handler import SearchLightRequestHandler
from splunk_logger import SplunkLogger
from utils import constants
from utils.digital_shadows_utility import validate_since, get_config, parse_date


def validate_input(_helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # global_account = definition.parameters.get('global_account', None)
    since = definition.parameters.get('since', None)
    if not since:
        return
    validate_since(since)


def collect_events(helper, ew):
    splunk_logger = SplunkLogger(helper)
    config = get_config(helper)
    splunk_logger.debug("Triage Config: {}".format(config))
    validate_config(config)
    splunk_logger.info("config extraction done !!")

    start_ds_poller(config, ew, helper, splunk_logger)


def start_ds_poller(config, ew, helper, splunk_logger):
    input_name = helper.get_input_stanza_names()
    while True:
        try:
            checkpoint = helper.get_check_point(input_name) or dict()
            last_event_num = checkpoint.get(constants.LAST_EVENT_NUM) if checkpoint.get(constants.LAST_EVENT_NUM) else 0
            # initialise the last-known event num we processed (default: 0)
            # persists between executions, so we restart where we left off.
            search_light_request_handler = SearchLightRequestHandler(helper, config[constants.SEARCHLIGHT_API_BASE_URL],
                                                                     config[constants.API_ACCOUNT_ID],
                                                                     config[constants.SEARCHLIGHT_API_KEY],
                                                                     config[constants.SEARCHLIGHT_API_SECRET],
                                                                     use_proxy=config[constants.USE_PROXY])
            search_list_triage_poller = SearchLightTriagePoller(search_light_request_handler, splunk_logger)

            since = config[constants.SINCE]
            try:
                since = parse_date(since)
            except Exception as e:
                splunk_logger.error(
                    f"error while parsing since date: {since} ERROR: {str(e)}")
                raise e
            alert_risk_types = config[constants.RISK_TYPES]
            poll_result = search_list_triage_poller.poll_triage(event_num_start=last_event_num,
                                                                event_created_after=since, alert_risk_types=alert_risk_types)
            splunk_logger.debug(f"data polled successfully till : {poll_result.max_event_number}")

            if poll_result.max_event_number == last_event_num:
                splunk_logger.debug(f"Polling done. last_event_num: {last_event_num}")
                break

            data = poll_result.triage_data
            if data:
                write_to_splunk(data, ew, helper, config)
                splunk_logger.info(f"data written to splunk successfully till {poll_result.max_event_number}")

                # update last event no so that next iteration we should fetch further record to avoid duplication
                checkpoint[constants.LAST_EVENT_NUM] = poll_result.max_event_number
                helper.save_check_point(input_name, checkpoint)
            else:
                splunk_logger.debug(f"Polling done. last_event_num: {last_event_num}")
                break
        except Exception as e:
            splunk_logger.info(f"Error: {str(e)} \n trace: {traceback.format_exc()}")
            break


def write_to_splunk(data, ew, helper, config):
    for entry in data:
        _format_entry(entry)
        entry[constants.ACCOUNT_ID] = config[constants.API_ACCOUNT_ID]
        event = helper.new_event(json.dumps(entry), time=None, host=None, index=config[constants.INDEX],
                                 source=constants.DIGITAL_SHADOWS, sourcetype=constants.SOURCE_TYPE_TRIAGE, done=True, unbroken=True)
        ew.write_event(event)


def _format_entry(entry):
    desc, title = None, None
    if constants.ALERT in entry:
        desc = entry[constants.ALERT].pop(constants.DESCRIPTION, None)
        title = entry[constants.ALERT].pop(constants.TITLE, None)
    elif constants.INCIDENT in entry:
        desc = entry[constants.INCIDENT].pop(constants.DESCRIPTION, None)
        title = entry[constants.INCIDENT].pop(constants.TITLE, None)
    entry[constants.DESCRIPTION] = desc
    entry[constants.TITLE] = title


def validate_config(config):
    """Validate that the config settings are available."""
    assert config[constants.SEARCHLIGHT_API_BASE_URL] is not None
    assert config[constants.API_ACCOUNT_ID] is not None
    assert config[constants.SEARCHLIGHT_API_KEY] is not None
    assert config[constants.SEARCHLIGHT_API_SECRET] is not None
