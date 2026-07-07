
# encoding = utf-8

from automoxapiclient.api.endpoints_api import EndpointsAPI
from automoxapiclient.api.servergroups_api import ServerGroupsAPI
from automoxapiclient.api.orgs_api import OrgsAPI
from automoxapiclient.api_client import ApiClient, OutcomeException

import json
import time

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
    # global_account = definition.parameters.get('global_account', None)
    pass

def import_endpoints(api_client, helper, ew):
    servergroups_api = ServerGroupsAPI(api_client)
    orgs_api = OrgsAPI(api_client)
    endpoints_api = EndpointsAPI(api_client)

    start_time = time.time()

    # Gather all orgs for mapping
    orgs = orgs_api.get_orgs()
    server_groups = servergroups_api.get_server_groups()

    endpoints = []
    try:
        for page, it in enumerate(endpoints_api.get_endpoints()):
            for e in it:
                # Update endpoint with additional details
                e['server_group'] = server_groups[e.get('server_group_id', None)]
                e['organization'] = orgs[e.get('organization_id', None)]

                endpoints.append(e['id'])

                try:
                    device = json.dumps(e)
                except TypeError as te:
                    helper.log_error(f"Unable to serialize event to send to splunk: {te}")
                    continue

                event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=device)
                ew.write_event(event)

        end_time = time.time()
        elapsed_time = int(end_time - start_time)

        it_count = len(endpoints)

        api_client.report_outcome("endpoint_input", api_client.SUCCESSFUL_OUTCOME, elapsed_time)
        helper.log_info(f"Events processed for page {page}: {it_count}")
    except OutcomeException as err:
        end_time = time.time()
        elapsed_time = int(end_time - start_time)

        api_client.report_outcome("endpoint_input", api_client.FAILED_OUTCOME, elapsed_time, err.message)

    return endpoints

def import_software(api_client, helper, ew, endpoints):
    endpoints_api = EndpointsAPI(api_client)

    start_time = time.time()

    try:
        for i in range(len(endpoints)):
            device_id = endpoints[i]

            # Get Software for device and publish
            for s_page, s_it in enumerate(endpoints_api.get_endpoint_software(device_id)):
                for s in s_it:
                    try:
                        device_software = json.dumps(s)
                    except TypeError as s_te:
                        helper.log_error(f"Unable to serialize event to send to splunk: {s_te}")
                        continue

                    s_event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(),
                                                sourcetype=f"{helper.get_sourcetype()}:software", data=device_software)
                    ew.write_event(s_event)

        end_time = time.time()
        elapsed_time = int(end_time - start_time)

        api_client.report_outcome("software_input", api_client.SUCCESSFUL_OUTCOME, elapsed_time)
    except OutcomeException as err:
        end_time = time.time()
        elapsed_time = int(end_time - start_time)

        api_client.report_outcome("software_input", api_client.FAILED_OUTCOME, elapsed_time, err.message)

def collect_events(helper, ew):
    helper.log_info("Fetching Automox console devices")
    input_name = helper.get_input_stanza_names()

    # Retrieve connection details used for communicating to Automox console
    page_size = helper.get_arg("page_size") or ApiClient.DEFAULT_PAGE_SIZE
    retrieve_software = helper.get_arg("retrieve_software") == "1"
    automox_conn = helper.get_arg("connection")
    api_key = automox_conn.get("api_key")
    org_id = automox_conn.get("org_id")
    helper.log_info(f"For endpoint import, connection found with api key {api_key} and org id {org_id}")

    # Set log level from global configuration
    log_level = helper.get_log_level()
    helper.set_log_level(log_level)

    # Initialize client
    api_client = ApiClient(api_key, org_id, helper=helper, page_size=page_size)

    endpoints = import_endpoints(api_client, helper, ew)

    if len(endpoints) > 0 and retrieve_software:
        import_software(api_client, helper, ew, endpoints)

    # Update counters
    total_count = len(endpoints)

    helper.log_info(f"Total Events processed for {input_name} input: {total_count}")
