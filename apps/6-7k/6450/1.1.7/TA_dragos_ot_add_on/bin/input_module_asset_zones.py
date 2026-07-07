# encoding = utf-8


from dragoslib import platform_input_utils as dragos_platform_input_utils


def submit_request_to_platform_api(session, page_number, preferred_batch_size):
    return session.post("/assets/api/v4/getZones", json={})


def write_splunk_item(dic_rest, helper, ew, dragos_input_utils):
    helper.logger.info("Writing {0} events to Splunk".format(len(dic_rest)))

    # Create a splunk event
    for item in dic_rest:
        obj_data = obj_data = dragos_input_utils.format_individual_data_item_for_splunk(item)

        event = dragos_input_utils.new_event_for_slunk(helper, obj_data)
        ew.write_event(event)

    return 1 # We don't paginate asset zones

def validate_input(helper, definition):
    # We don't have access to the credentials the user has selected so there is minimal
    # validation that we can do. Just do some basics to make sure everything looks
    # broadly OK
    dragos_platform_input_utils.PlatformInputUtils().validate_certificate_filename_and_existence(
        definition.parameters,
        helper.logger
    )


def collect_events(helper, ew):
    dragos_platform_input_utils.PlatformInputUtils().collect_events_from_api(helper, ew, submit_request_to_platform_api, write_splunk_item)