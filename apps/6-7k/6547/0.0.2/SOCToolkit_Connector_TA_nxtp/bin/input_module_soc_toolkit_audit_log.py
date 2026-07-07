# encoding = utf-8

import json
from datetime import datetime
from soctoolkit_connector_ta_nxtp.soctoolkit import ManagementConnection, Request


"""
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""
"""
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
"""


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    start_from = definition.parameters.get("start_from", None)
    start_from = datetime.strptime(start_from, "%Y-%m-%d %H:%M:%S")


def collect_events(helper, ew):
    api_manager = ManagementConnection(helper)
    # DEBUG uncomment below:
    # helper.save_check_point("last_fetch", 0)
    last_fetch = helper.get_check_point("last_fetch")
    # Default to index all one for first run
    if last_fetch is None:
        last_fetch = datetime.timestamp(
            datetime.strptime(helper.get_arg("start_from"), "%Y-%m-%d %H:%M:%S")
        )
    helper.save_check_point("last_fetch", datetime.timestamp(datetime.now()))
    helper.log_info(f"Fetching event log from {last_fetch} till {datetime.now()}.")
    for event in Request(
        management_connection=api_manager,
        endpoint="auditlog",
        http_request="GET",
        input_params={"start_datetime": datetime.fromtimestamp(last_fetch)},
    ).paged_request(items_per_page=5):
        ew.write_event(
            helper.new_event(json.dumps(event), host=helper.get_global_setting("domain"))
        )
