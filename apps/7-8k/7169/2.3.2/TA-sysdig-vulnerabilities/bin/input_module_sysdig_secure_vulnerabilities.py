# encoding = utf-8

import datetime
import json
import sysdig_core

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

VULN_DETAIL_PAGE_SIZE = 250
MIN_EXECUTION_PERIOD = 86400


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    sysdig_secure_url = definition.parameters.get("sysdig_secure_url", None)
    # sysdig_secure_token = definition.parameters.get('sysdig_secure_token', None)
    if sysdig_secure_url.startswith("https"):
        pass
    else:
        raise ValueError("Please include protocol (https) in the URL")


def collect_events(helper, ew):

    # TODO: Clean up logging; include a runGuid.
    helper.log_info(
        "Starting sysdig_secure_vulnerabilities://{}".format(
            helper.get_input_stanza_names()
        )
    )

    # Get existing checkpoint for this input & initilize variables
    checkpoint = helper.get_check_point(helper.get_input_stanza_names())
    helper.log_info(
        "Got checkpoint value {} for {}".format(
            checkpoint, helper.get_input_stanza_names()
        )
    )

    # Checkpoint logic
    if checkpoint is None or helper.get_input_stanza_names() == "aob_test":
        # Reset checkpoint if no previous one
        helper.log_info("No previous checkpoint. Setting to now.")
        checkpoint = int(datetime.datetime.now().timestamp())
    else:
        checkpoint += MIN_EXECUTION_PERIOD

    if checkpoint < int(datetime.datetime.now().timestamp()) - 60:
        # or if we missed some executions
        helper.log_info("Time drift. Reset checkpoint to now")
        checkpoint = int(datetime.datetime.now().timestamp())
    elif checkpoint > int(datetime.datetime.now().timestamp()) + 60:
        # Abort in case it is too early
        remaining = checkpoint - int(datetime.datetime.now().timestamp())
        helper.log_info(
            "Skipping execution: next run scheduled at {} (in {}s / {})".format(
                datetime.datetime.fromtimestamp(checkpoint).isoformat(),
                remaining,
                datetime.timedelta(seconds=remaining),
            )
        )
        return

    helper.log_info("Checkpoint value is {}".format(checkpoint))

    events_written = 0

    sdc_url = helper.get_arg("sysdig_secure_url")
    token = helper.get_arg("sysdig_secure_token")
    nvd_api_key = helper.get_arg("nvd_api_key")
    selected_fields = helper.get_arg("vulnerability_details")
    # Limit to max_images
    max_images = helper.get_arg("max_images")

    def new_event(fulltag, data):
        nonlocal events_written

        # Build and Write the event
        event = helper.new_event(
            time=checkpoint,
            host=fulltag,
            source="sysdig_secure_vulnerabilities://{}".format(helper.get_input_stanza_names()),
            index=helper.get_output_index(),
            sourcetype=helper.get_sourcetype(),
            data=json.dumps(data))
        ew.write_event(event)
        events_written += 1


    sysdig_core.configure_retries(helper)

    sysdig_core.fetch_vulnerabilities(
        sdc_url, token, nvd_api_key, selected_fields, max_images, new_event, helper
    )

    # Save checkpoint if events were written
    helper.log_info("{} events written for {}".format(events_written, helper.get_input_stanza_names()))
    helper.save_check_point(helper.get_input_stanza_names(), checkpoint)
    helper.log_info("Saved checkpoint value {} for {}".format(checkpoint, helper.get_input_stanza_names()))


