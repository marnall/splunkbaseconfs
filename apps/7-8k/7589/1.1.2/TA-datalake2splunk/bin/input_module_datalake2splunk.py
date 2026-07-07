
# encoding = utf-8

import os
import sys
import time
import datetime
from pathlib import Path
import csv

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
    query_hash = definition.parameters.get("query_hash", None)
    global_account = definition.parameters.get("global_account", None)
    source_type = definition.parameters.get("source_type", None)
    use_proxy = definition.parameters.get("use_proxy", None)
    pass


def collect_events(helper, ew):
    TIME_TO_WAIT = 75  # in seconds
    N_TRIES = 18
    # Get arguments of a particular input
    input_name = helper.get_arg("name")
    opt_index=helper.get_output_index()
    opt_query_hash = helper.get_arg("query_hash")
    # opt_token = helper.get_arg("token")
    opt_source_type = helper.get_arg("source_type")
    use_proxy = helper.get_arg("use_proxy")
    # Get global variable configuration
    app_name = helper.get_app_name()
    global_account = helper.get_arg('global_account')

    # Get const arguments
    url = "https://datalake.cert.orangecyberdefense.com/"
    create_bulk_search_url = f"{url}api/v2/mrti/bulk-search/"
    get_bulk_search_results_url = f"{url}api/v2/mrti/bulk-search/task/"
    headers = {
        "accept": "application/json",
        "Authorization": f"Token {global_account['password']}",
    }
    query_fields = [
        "atom_type",
        "atom_value",
        "first_seen",
        "last_updated",
        "threat_hashkey",
        "threat_types",
        "threat_scores",
        "sources",
        "tags"
    ]
    data = {"query_hash": opt_query_hash, "query_fields": query_fields}

    helper.log_info("Function collect_events starts")


    # Connecting to the API and create bulk search
    helper.log_info(f"Sending request to {create_bulk_search_url}")
    response = helper.send_http_request(
        url=create_bulk_search_url,
        method="POST",
        headers=headers,
        payload=data,
        use_proxy=use_proxy,
        timeout=120
    )
    response_json = response.json()
    task_uuid = response_json.get("task_uuid")

    if response.status_code != 200 or task_uuid is None:
        helper.log_error(f"Creating bulk search failed with status code={response.status_code}")
        response.raise_for_status()

    helper.log_info("Bulk Search was created successfully")

    # Fetching the results
    for _ in range(N_TRIES):
        time.sleep(TIME_TO_WAIT)
        response = helper.send_http_request(
            url=f"{get_bulk_search_results_url}{task_uuid}/",
            method="GET",
            headers=headers,
            use_proxy=use_proxy,
            timeout=120
        )
        if response.status_code == 202:
            helper.log_info("Search was not done yet")
        elif response.status_code != 200:
            helper.log_error("Getting the bulk search results failed")
            response.raise_for_status()
        else:
            helper.log_info("Results were fetched successfully")
            break
    else:
        helper.log_error(f"ABORTING. Waiting for the bulk search results was too long. {N_TRIES * TIME_TO_WAIT} seconds")
        response.raise_for_status()

    data = response.json()

    # Result processing (json to csv)
    helper.log_info("Results are being processed")


    if opt_source_type == "use_custom_lookup":

        helper.log_info("Custom Lookup is being saved")
        path = Path(__file__).parent.parent / f"lookups/datalake_{input_name}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="") as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=",")
            csvwriter.writerow(query_fields)
            results = data.get("results", [])
            csvwriter.writerows(results)

        helper.log_info(f"Custom Lookup saved! Filename={path.name}")


    elif opt_source_type == "lookup":
        helper.log_info("Lookups are being saved")
        results = {}
        # Group by atom_type (email, ip, ...)
        for atom_type, *values in data.get("results", []):
            results.setdefault(atom_type, []).append(values)
        for lookup_name, values_rows in results.items():
            path = Path(__file__).parent.parent / f"lookups/datalake_{lookup_name}.csv"
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", newline="") as csvfile:
                csvwriter = csv.writer(csvfile, delimiter=",")
                csvwriter.writerow([lookup_name] + query_fields[2:])
                csvwriter.writerows(values_rows)

            helper.log_info(f"Lookup file saved! Filename={path.name}")


    elif opt_source_type == "indexed":
        # Saving events
        helper.log_info("Data is being indexed")
        n_events_processed = 0
        for result in data.get("results", []):
            event = helper.new_event(data=str(result), source=app_name, sourcetype=input_name, index=opt_index)
            ew.write_event(event)
            n_events_processed += 1

        helper.log_info(f"Number of events processed: {n_events_processed}")
