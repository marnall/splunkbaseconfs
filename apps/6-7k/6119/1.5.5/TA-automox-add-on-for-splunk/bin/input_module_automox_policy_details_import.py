
# encoding = utf-8

from automoxapiclient.api.policy_api import PolicyAPI
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

def collect_events(helper, ew):
    helper.log_info("Fetching Automox policy details")
    input_name = helper.get_input_stanza_names()

    # Retrieve connection details used for communicating to Automox console
    automox_conn = helper.get_arg("connection")
    api_key = automox_conn.get("api_key")
    org_id = automox_conn.get("org_id")
    helper.log_info(f"For policy import, connection found with api key {api_key} and org id {org_id}")

    # Set log level from global configuration
    log_level = helper.get_log_level()
    helper.set_log_level(log_level)

    # Initialize client
    api_client = ApiClient(api_key, org_id, helper=helper)
    policy_api = PolicyAPI(api_client)
    orgs_api = OrgsAPI(api_client)

    # Gather all orgs for mapping
    orgs = orgs_api.get_orgs()

    # Collect and process events
    total_count = 0

    policy_stats_dict = policy_api.get_policy_stats()

    start_time = time.time()

    try:
        for page, it in enumerate(policy_api.get_policies()):
            it_count = 0
            for e in it:
                # Add policy stats to policy
                e['stats'] = policy_stats_dict.get(e['id'])
                # Add organization name
                e['organization'] = orgs[e.get('organization_id', None)]
                e = policy_api.sanitize_policy(e)

                try:
                    policy = json.dumps(e)
                except TypeError as te:
                    helper.log_error(f"Unable to serialize event to send to splunk: {te}")
                    continue

                event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(),
                                        sourcetype=helper.get_sourcetype(), data=policy)
                ew.write_event(event)

                # Update counters
                it_count += 1
                total_count += 1

            helper.log_info(f"Events processed for page {page}: {it_count}")
        helper.log_info(f"Total Events processed for {input_name} input: {total_count}")

        end_time = time.time()
        elapsed_time = int(end_time - start_time)

        api_client.report_outcome("policy_input", api_client.SUCCESSFUL_OUTCOME, elapsed_time)
    except OutcomeException as err:
        end_time = time.time()
        elapsed_time = int(end_time - start_time)

        api_client.report_outcome("policy_input", api_client.FAILED_OUTCOME, elapsed_time, err.message)

