
# encoding = utf-8

import os
import sys
import json
import time
import datetime
from collections import OrderedDict

from requests import HTTPError
from requests.exceptions import ProxyError
from solnlib.modular_input import checkpointer
import splunklib.client as client
import api
import common
from helpers import *
from ingestion import Ingestion

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
    # notes = definition.parameters.get('notes', None)
    pass

def collect_events(helper, ew):
    helper.log_debug("input_module_spycloud_watchlist.py start")

    if not api.shouldRunOnThisSystem(helper):
        helper.log_info("Not running on this system")
        sys.exit(0)
    else:
        helper.log_info("Running on this system")

    common.check_api_key(helper, "input_module_spycloud_watchlist.py")

    # Retrieve input metadata and initialize KV Store
    input_metadata = helper.context_meta
    session_key = input_metadata.get("session_key")
    service = client.connect(token=session_key, app=helper.get_app_name(), owner='nobody')
    kvstore = service.kvstore['watchlist_v2_checkpoint']

    # Ingestion logic
    # Scheduling is handled by JavaScript frontend (ingest_schedule.js)
    # Reset/reload is handled by spycloud_reset.py (clears checkpoint before calling this)

    # Initialize ingestion handler
    ingestion = Ingestion(helper, kvstore)

    # Get ingestion parameters (since, until)
    # This will automatically handle first run (no checkpoint) vs incremental (has checkpoint)
    since, until = ingestion.get_ingestion_params()
    helper.log_info(f"watchlist_ingestion_params since={since} until={until}")

    # Load current checkpoint for document tracking
    checkpoint = ingestion._load_checkpoint()

    # Track number of events processed
    events_processed = 0

    def process_results(results):
        nonlocal events_processed
        for result in results:
            document_id = result["document_id"]
            if document_id in checkpoint["documents"].keys():
                continue

            # Track document IDs by publish date so retention can keep only recent IDs.
            ingestion.track_document(
                checkpoint,
                document_id,
                result.get("spycloud_publish_date")
            )
            events_processed += 1

            # Force timestamp to front of event
            ordered_result = OrderedDict()
            if "spycloud_publish_date" in result:
                ordered_result["spycloud_publish_date"] = result[
                    "spycloud_publish_date"
                ]
                del result["spycloud_publish_date"]
            for key in result:
                ordered_result[key] = result[key]
            data = json.dumps(ordered_result)
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data, time=time.time())
            ew.write_event(event)

    try:
        helper.log_info("watchlist_query phase=standard")
        process_results(api.watchlist(helper, since, until))

        helper.log_info("watchlist_query phase=modification_date")
        process_results(api.modified_watchlist(helper, since, until))

        helper.log_info(f"Successfully processed {events_processed} events")

        checkpoint["last_since"] = since
        checkpoint["last_until"] = until
        checkpoint["last_since_modification_date"] = since
        checkpoint["last_until_modification_date"] = until

        # Update checkpoint and last_run in a single save.
        ingestion.update_checkpoint_after_success(until, checkpoint)

    except ProxyError as p_err:
        log_and_exit(helper, proxy_error_to_message(p_err), "input_module_spycloud_watchlist.py")

    except HTTPError as http_err:
        if getattr(getattr(http_err, 'response', None), 'status_code', None) == 429:
            helper.log_warning(f"watchlist_rate_limited checkpoint_preserved will_retry_next_run error={http_err}")
            return
        log_and_exit(helper, http_error_to_message(http_err), "input_module_spycloud_watchlist.py")

    except Exception as ex:
        msg = str(ex)
        if "proxy" in msg.lower():
            log_and_exit(helper, MSG_PROXY_GENERIC, "input_module_spycloud_watchlist.py")
        log_and_exit(helper, f"{MSG_UNEXPECTED_API} {msg}", "input_module_spycloud_watchlist.py")

    helper.log_info("input_module_spycloud_watchlist.py end")
