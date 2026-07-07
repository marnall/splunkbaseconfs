
# encoding = utf-8

import json
import sys
import time

from extrahop_common import ExtraHopClient, get_detection_stanza
from solnlib.modular_input.event_writer import ClassicEventWriter
from splunk.clilib import cli_common as cli
from ta_extrahop_addon_declare import (
    DEFAULT_DETECTION_INTERVAL,
    DEFAULT_DETECTION_PAGE_SIZE,
    DETECTIONS_STANZA,
)

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
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # text = definition.parameters.get('text', None)
    # password = definition.parameters.get('password', None)
    # checkbox = definition.parameters.get('checkbox', None)
    parameters = definition.parameters if "parameters" in dir(definition) else definition
    interval = parameters.get("interval", 0).strip()

    try:
        interval = int(interval)
        assert interval > 0
    except ValueError:
        helper.log_error("Invalid Interval found for the input name: {}. Interval should be integer value".format(parameters.get("name", "")))
        return False
    except AssertionError:
        helper.log_error("Invalid Interval found for the input name: {}. Interval should be greater than 0".format(parameters.get("name", "")))
        return False
    return True


def create_json_body(detection_category, detection_status, detection_page_size, mod_time, offset_value):
    """This method is used to create the request body."""
    request_object = {}
    status_list = []
    request_object["filter"] = {}
    request_object_sorting_fields = ["mod_time", "id"]
    sorting_objects_list = []
    for sort_field in request_object_sorting_fields:
        sorting_dict_object = {}
        sorting_dict_object["direction"] = "asc"
        sorting_dict_object["field"] = "{}".format(sort_field)
        sorting_objects_list.append(sorting_dict_object)
    if detection_status:
        for status in detection_status:
            status_list.append(status.strip())
    if detection_category:
        detection_category = detection_category.split(",")
        detection_category = [each_category.strip(" \"'") for each_category in detection_category]
        request_object["filter"]["categories"] = detection_category
    else:
        request_object["filter"]["categories"] = ["sec.attack"]

    request_object["mod_time"] = mod_time
    request_object["filter"]["status"] = status_list
    request_object["limit"] = detection_page_size
    request_object["offset"] = offset_value
    request_object["sort"] = sorting_objects_list

    return request_object


def make_api_call(request_object, extrahop):
    """This method is used to make the api call to the extrahop platform."""
    api_endpoint = "detections/search"
    response = extrahop.post(api_endpoint, json.dumps(request_object))

    return response.json()


def process_response(response, limit):
    """This method is used to process the response for the next api call."""
    if len(response) < limit:
        return True

    return False


def create_splunk_event_objects_list(response, helper, ew):
    """This method is used to create the splunk events objects."""
    classic_ew_event_obj_list = []
    try:
        for event in response:
            classic_ew_event_obj = ew.create_event(source=helper.get_input_type(), index=helper.get_output_index(
                ), sourcetype=str("extrahop:detection"), data=json.dumps(event))
            classic_ew_event_obj_list.append(classic_ew_event_obj)
    except Exception as e:
        helper.log_error("Error occured while creating objects: {}".format(e))

    return classic_ew_event_obj_list


def update_checkpoint(input_name, stanza_name, data, helper):
    """This method is used to update the checkpoint value."""
    try:
        helper.log_info("{}: Updating checkpoint with value: {}".format(input_name, data))
        helper.save_check_point(stanza_name, json.dumps(data))
        helper.log_info("{}: Checkpoint successfully updated".format(input_name))
    except Exception as e:
        helper.log_error("Error occurred while saving the checkpoint for the input {}. Error: {}".format(input_name, e))
        raise e


def ingest_splunk_event(classic_event_objects_list, ew):
    """This method is used to ingest the events in Splunk."""
    if classic_event_objects_list:
            try:
                ew.write_events(classic_event_objects_list)
            except Exception as e:
                raise Exception(e)


def get_last_event_mod_time(response):
    last_event = response[-1]
    last_event_mod_time = last_event.get("mod_time")

    return last_event_mod_time


def collect_events(helper, ew):
    input_starttime = time.time()
    session_key = helper.context_meta["session_key"]
    helper.set_log_level(helper.get_log_level())

    stanza_name = helper.get_input_stanza_names()
    input_stanza = helper.get_input_stanza(stanza_name)
    try:
        assert validate_input(helper, input_stanza) == True
    except AssertionError:
        sys.exit()

    detection_category = helper.get_arg("detection_category")
    detection_status = helper.get_arg("status")
    detection_stanza = get_detection_stanza(session_key, DETECTIONS_STANZA, helper)
    detection_page_size = DEFAULT_DETECTION_PAGE_SIZE
    detection_time_interval = DEFAULT_DETECTION_INTERVAL
    ingest_all_data = True
    if detection_stanza:
        detection_page_size = int(detection_stanza.get("page_size"))
        detection_time_interval = int(detection_stanza.get("detection_interval"))

    checkpoint_stanza_name = stanza_name + "_detections"
    stanza_name = helper.get_input_stanza_names()
    hostname = helper.get_arg("global_account").get("hostname").strip().lower()
    server_name = helper.get_arg("global_account").get("name")
    checkpoint_stanza_name = "_".join([stanza_name, server_name, "post_v912", "detections"])
    cew = ClassicEventWriter()
    helper.log_info("Starting data collection for input {}.".format(stanza_name))
    helper.log_debug("{}:: Detection Category: {}, Status: {}".format(stanza_name, detection_category, detection_status))
    checkpoint_response = helper.get_check_point(checkpoint_stanza_name)
    offset_value = 0
    now = int(time.time()) * 1000

    if checkpoint_response:
        checkpoint_value = json.loads(checkpoint_response)
        helper.log_info("{}:: Checkpoint value is: {}".format(stanza_name, checkpoint_value))
        if int(checkpoint_value.get("offset_value")):
            offset_value = int(checkpoint_value.get("offset_value"))
            mod_time = int(checkpoint_value.get("mod_time"))
        else:
            mod_time = int(checkpoint_value.get("mod_time"))
    else:
        mod_time = now - (detection_time_interval * 1000)
        helper.log_info(
            f"{stanza_name}:: did not find the checkpoint time, defaulting to {mod_time}"
        )

    request_object = create_json_body(detection_category, detection_status, detection_page_size, mod_time, offset_value)

    verify_certs = cli.getConfStanza('ta_extrahop_addon_settings', 'additional_parameters').get(
        'validate_ssl_certificates', '1')
    verify_certs = False if verify_certs in ["False", "0", "false"] else True

    try:
        extrahop = ExtraHopClient(
            hostname,
            helper,
            verify_certs=bool(verify_certs)
        )
    except Exception as e:
        helper.log_error("Exception occured while initializing Extrahop client: {}".format(e))
        sys.exit(1)

    # If there is no response with the mod_time value, we can use the same value for the next invocation of the input.
    last_event_mod_time = int(request_object["mod_time"])
    is_all_data_collected = False
    while not is_all_data_collected:
        data = {}
        helper.log_info("{}:: Request Payload is: {}".format(stanza_name, request_object))
        try:
            response = make_api_call(request_object, extrahop)
            if response:
                classic_event_objects_list = create_splunk_event_objects_list(response, helper, cew)
                ingest_splunk_event(classic_event_objects_list, cew)
                helper.log_info("{}:: Received total {} events from response and indexed total {} events into the splunk for processing cycle, offset = {}, limit = {} ".format(stanza_name, len(classic_event_objects_list), len(classic_event_objects_list), request_object["offset"], request_object["limit"]))
                data["offset_value"] = request_object["offset"]
                data["mod_time"] = request_object["mod_time"]
                last_event_mod_time = get_last_event_mod_time(response)

            is_all_data_collected = process_response(response, detection_page_size)

            if is_all_data_collected:
                data["offset_value"] = "0"
                data["mod_time"] = int(last_event_mod_time) + 1
            else:
                request_object["offset"] += detection_page_size
            update_checkpoint(stanza_name, checkpoint_stanza_name, data, helper)
        except Exception as e:
            helper.log_error("Something went wrong while collecting the data for the input: {}, Error: {}".format(stanza_name, e))
            break

    total_seconds =  round(time.time() - input_starttime, 2)
    helper.log_info(f"Data collection was completed for input {stanza_name}. Total time taken: {total_seconds} seconds")
