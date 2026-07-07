
import json
import sys
import time
import common.const as const
import common.utility as utility
import common.log as log
import pytz
from dateutil import tz
from solnlib.utils import is_true
from ta_sonrai_client import SonraiTicketClient
from datetime import datetime, timedelta
from solnlib.modular_input.event_writer import ClassicEventWriter


'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
FILTER_OP = {
    "swimlaneSrns": "IN_LIST",
    "cloudType": "IN_LIST",
    "environment": "IN_LIST",
    "severityCategory": "IN_LIST",
    "severityNumeric": "GTE"
}


def make_filter_string(filters):
    """Functionto create Filter for the Rest API call."""
    filter_str = ''
    for key in filters:
        if filters.get(key):
            if FILTER_OP.get(key) != "IN_LIST":
                filter_str += ', {"' + key + '": {"op": "' + FILTER_OP.get(key) + '", \
                "value": ' + str(filters[key]) + '}}'
            else:
                filter_str += ', {"' + key + '": {"op": "' + FILTER_OP.get(key) + '", \
                "values": ' + str(filters[key]) + '}}'
    return filter_str.replace("'", '"')


def create_json_body(limit, offset, from_time, until_time, filters, helper, logger):
    """Function to create JSON body for the Sonrai Ticket request."""
    try:
        from_time = datetime.strftime(datetime.utcfromtimestamp(float(from_time)), '%Y-%m-%dT%H:%M:%S')
        until_time = datetime.strftime(datetime.utcfromtimestamp(float(until_time)), '%Y-%m-%dT%H:%M:%S')
        filter_str = '{"and": [{"lastModified": { "op": "LT", "value": "' + until_time + '" }}, \
        {"lastModified": { "op": "GTE", "value": "' + from_time + '" }} \
        ' + make_filter_string(filters) + ']}'
        payload = {"query": const.FETCH_TICKET.format(limit, offset),
                   "variables": '{"filter": ' + filter_str + '}'}
        return json.dumps(payload)
    except Exception as e:
        logger.error("Something went wrong while creating request payload. \
        Hence Data collection not completed successfully. Error: {}".format(str(e)))


def validate_input(helper, definition, logger=None):
    """Implement your own validation logic to validate the input stanza configurations."""
    if "parameters" in dir(definition):
        return True
    parameters = definition
    interval = parameters.get("interval", 0).strip()
    severity_category = parameters.get("severity_category", [])
    index = parameters.get("index", "")
    sonrai_account = parameters.get("sonrai_account")

    if not sonrai_account:
        logger.error("Sonrai account is not selected for the input name: {}.".format(parameters.get("name", "")))
        return False
    elif type(sonrai_account) == dict and not sonrai_account.get("organization_id"):
        logger.error("Organization Id is not found for selected account of input name: {} \
        ".format(parameters.get("name", "")))
        return False

    if not index:
        logger.error("Index value not found for the input name: {}. \
        ".format(parameters.get("name", "")))
        return False

    try:
        interval = int(interval)
        assert interval >= 1200 and interval <= 7200
    except ValueError:
        logger.error("Invalid Interval found for the input name: {}. Interval should be integer value \
        ".format(parameters.get("name", "")))
        return False
    except AssertionError:
        logger.error("Invalid Interval found for the input name: {}. Interval should be between 1200 and 7200. \
        ".format(parameters.get("name", "")))
        return False

    try:
        for category in severity_category:
            assert category in const.SEVERITY_CATEGORY
    except AssertionError:
        logger.error("Invalid Severity Category found for the input name: {}. Severity Category should be from {} \
        ".format(parameters.get("name", ""), const.SEVERITY_CATEGORY))
        return False

    return True


def make_api_call(request_object, sonrai):
    """This method is used to make the api call to the sonrai platform."""
    response = sonrai.post(request_object)
    return response.json()


def create_splunk_event_objects_list(response, sonrai_host, helper, ew, logger):
    """This method is used to create the splunk events objects."""
    event_obj_list = []
    try:
        if response.get("data"):
            for event in response.get("data", {}).get("Tickets", {}).get("items", []):
                event["sonraiUrl"] = sonrai_host
                event_obj = ew.create_event(
                    source=helper.get_input_type(),
                    index=helper.get_output_index(),
                    sourcetype=str("sonrai:sec:tickets"), data=json.dumps(event))
                event_obj_list.append(event_obj)
    except Exception as e:
        logger.error("Error occured while creating objects: {}".format(e))

    return event_obj_list


def update_checkpoint(stanza_name, checkpoint_data, helper, logger):
    """This method is used to update the checkpoint value."""
    try:
        logger.debug("Updating checkpoint with value: {}".format(checkpoint_data))
        helper.save_check_point(stanza_name, json.dumps(checkpoint_data))
        logger.debug("checkpoint updated")
    except Exception as e:
        logger.error("Error while saving the checkpoint: {}".format(e))


def get_filters_from_input(input_stanza):
    """Function to get Filters for the query."""
    return {
        "swimlaneSrns": input_stanza.get("swimlane_srns"),
        "cloudType": input_stanza.get("cloud_type"),
        "environment": input_stanza.get("environment"),
        "severityCategory": input_stanza.get("severity_category")
    }


def collect_events(helper, ew):
    """Collect Data for Sonrai Ticket."""
    log_file_name = "ta_{}_{}".format(helper.input_type, helper.get_input_stanza_names())
    logger = log.get_logger(log_file_name)
    helper.set_log_level(helper.get_log_level())
    stanza_name = helper.get_input_stanza_names()
    input_stanza = helper.get_input_stanza(stanza_name)
    try:
        # Call validate_input function to validate input before starting data collection.
        if not validate_input(helper, input_stanza, logger):
            sys.exit()
    except Exception:
        sys.exit()

    session_key = helper.context_meta["session_key"]

    # Get detail from Sonrai Account
    organization_id = helper.get_arg("sonrai_account").get("organization_id").strip().lower()
    server_name = helper.get_arg("sonrai_account").get("name")
    verify_certs = is_true(helper.get_arg("sonrai_account").get("verify_certs"))
    sonrai_host = helper.get_arg("sonrai_account").get("sonrai_host")
    filters = get_filters_from_input(input_stanza)

    # Set variable require to make request and ingest data
    start_time = helper.get_arg("start_time")
    cew = ClassicEventWriter()
    offset = 0
    limit = const.PAGE_SIZE

    try:
        utility.wait_for_kvstore(session_key, helper, logger)
    except Exception as e:
        logger.error(str(e))
        return

    # Initialize SonraiTicketClient to make requests
    try:
        sonrai = SonraiTicketClient(
            organization_id,
            sonrai_host,
            helper,
            verify_certs,
            const.FETCH_TICKET_QUERY_NAME,
            logger)
        if not sonrai.session.headers:
            sys.exit(1)
    except Exception as e:
        logger.error("Exception occured while initializing Sonrai client: {}".format(e))
        sys.exit(1)

    api_call = True
    input_start_time = time.time()

    # Initialize checkpoint stanza name
    checkpoint_stanza_name = "_".join([stanza_name, server_name, "sonrai_tickets"])
    try:
        checkpoint_response = helper.get_check_point(checkpoint_stanza_name)
        local_zone = tz.tzlocal()
        if checkpoint_response:
            checkpoint_value = json.loads(checkpoint_response)
            logger.info("{}:: Checkpoint value is: {}".format(stanza_name, checkpoint_value))
            if int(checkpoint_value.get("from_time")):
                from_time = int(checkpoint_value.get("from_time"))
                until_time = int(checkpoint_value.get("until_time"))
            else:
                from_time = int(checkpoint_value.get("until_time"))
                until_time = int(datetime.now().timestamp())
            offset = int(checkpoint_value.get("offset", 0))
        else:
            if start_time:
                validation_flag, msg = utility.validate_start_time(start_time)
                if not validation_flag:
                    logger.error("{}:: {}".format(stanza_name, msg))
                    return False
            if input_stanza.get("start_time", ""):
                from_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=pytz.UTC)
                from_time = int(from_time.astimezone(local_zone).timestamp())
            else:
                from_time = int((datetime.now() - timedelta(seconds=3600)).timestamp())
            until_time = int(datetime.now().timestamp())
    except Exception as e:
        logger.error("{}:: Something went wrong while intializing checkpoint values. Error: {}".format(stanza_name, e))
        sys.exit(1)

    logger.info("Starting data collection for input {}, From Time: {}, Until Time: {} \
    ".format(
        stanza_name,
        datetime.utcfromtimestamp(int(from_time)).strftime('%Y-%m-%d %H:%M:%S'),
        datetime.utcfromtimestamp(int(until_time)).strftime('%Y-%m-%d %H:%M:%S')))

    checkpoint_data = {"from_time": from_time, "until_time": until_time}
    # Start data collection
    while api_call:
        try:
            request_object = create_json_body(limit, offset, from_time, until_time, filters, helper, logger)
            logger.debug("{}:: Request Payload is: {}".format(stanza_name, request_object))
            response = make_api_call(request_object, sonrai)
            if response:
                if response.get("errors") and "Response too large" in response.get("errors")[0].get("message"):
                    logger.warn("Response too large to fetch. Reducing the limit to {}".format(int(limit / 2)))
                    limit = int(limit / 2)
                    continue

                event_obj_list = create_splunk_event_objects_list(response, sonrai_host, helper, cew, logger)
                ingested_events = utility.ingest_splunk_event(event_obj_list, cew, logger)
                logger.info("{}:: Received total {} events from response and indexed total {} \
events into the splunk for processing cycle, offset = {}, limit = {} \
                ".format(stanza_name, len(event_obj_list), ingested_events, offset, limit))
                api_call = True if len(event_obj_list) == int(limit) else False
                offset += int(limit)
                limit = const.PAGE_SIZE
                if api_call:
                    checkpoint_data["offset"] = offset
                else:
                    checkpoint_data["from_time"] = "0"
                    checkpoint_data["offset"] = "0"
                    checkpoint_data["until_time"] = until_time
            else:
                api_call = False
                checkpoint_data["from_time"] = "0"
                checkpoint_data["offset"] = "0"
                checkpoint_data["until_time"] = until_time
            update_checkpoint(checkpoint_stanza_name, checkpoint_data, helper, logger)
        except Exception as e:
            logger.error("Something went wrong while collecting the data for the input: {}, \
            Error: {}".format(stanza_name, e))
            api_call = False
            checkpoint_data["from_time"] = from_time
            checkpoint_data["until_time"] = until_time
            checkpoint_data["offset"] = offset
            update_checkpoint(checkpoint_stanza_name, checkpoint_data, helper, logger)
            sys.exit(1)
    if checkpoint_data:
        update_checkpoint(checkpoint_stanza_name, checkpoint_data, helper, logger)
    total_seconds = round(time.time() - input_start_time, 2)
    logger.info(f"Data collection was completed successfully for input {stanza_name}. \
    Total time taken: {total_seconds} seconds")
