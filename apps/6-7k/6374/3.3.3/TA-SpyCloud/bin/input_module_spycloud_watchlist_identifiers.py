
# encoding = utf-8

import os
import sys
import json
import time
from datetime import datetime, timezone

# Splunk's ExecProcessor backs off scheduling modular inputs that exit too
# quickly, even on success. The identifiers API is fast (sub-second), so we
# enforce a minimum process lifetime to prevent the scheduler backing off.
_MIN_RUNTIME_SECONDS = 5
from collections import OrderedDict

from requests import HTTPError
from requests.exceptions import ProxyError
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
    _start_time = time.monotonic()
    helper.log_debug("input_module_spycloud_watchlist_identifiers.py start")
    
    if not api.shouldRunOnThisSystem(helper):
        helper.log_info("Not running on this system")
        sys.exit(0)
    else:
        helper.log_info("Running on this system")
    
    common.check_api_key(helper, "input_module_spycloud_watchlist_identifiers.py")

    # Identifiers API does not use since/until for filtering, but we still maintain
    # last_run so the schedule status reflects successful hourly/daily executions.
    ingestion = None
    since = None
    until = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    try:
        input_metadata = helper.context_meta
        session_key = input_metadata.get("session_key")
        service = client.connect(token=session_key, app=helper.get_app_name(), owner='nobody')
        kvstore = service.kvstore['watchlist_identifiers_v2_checkpoint']
        ingestion = Ingestion(helper, kvstore)
        since, until = ingestion.get_ingestion_params()
        helper.log_info(f"watchlist_identifiers_ingestion_params since={since} until={until}")
    except Exception as checkpoint_error:
        helper.log_warning(
            f"watchlist_identifiers_checkpoint_unavailable proceeding_without_checkpoint error={checkpoint_error}"
        )
        helper.log_info(f"watchlist_identifiers_ingestion_params since={since} until={until}")

    events_processed = 0
        
    try:
        for result in api.identifiers(helper):
            # Identifiers aren't time-indexed so add pull time as a field
            ordered_result = OrderedDict()
            ordered_result["export_time"] = datetime.now().strftime(
                "%Y-%m-%dT%H:%M:%S.%f"
            )
            for key in result:
                ordered_result[key] = result[key]
            data=json.dumps(ordered_result)
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data, time=time.time())
            ew.write_event(event)
            events_processed += 1

        helper.log_info(f"Successfully processed {events_processed} identifier events")

        # Update identifiers last_run after successful ingestion cycle.
        if ingestion is not None:
            ingestion.update_checkpoint_after_success(until)
        else:
            helper.log_warning("Skipping identifiers checkpoint update because checkpoint storage is unavailable")

    except ProxyError as p_err:
        log_and_exit(helper, proxy_error_to_message(p_err), "input_module_spycloud_watchlist_identifiers.py")

    except HTTPError as http_err:
        if getattr(getattr(http_err, 'response', None), 'status_code', None) == 429:
            helper.log_warning(f"watchlist_identifiers_rate_limited checkpoint_preserved will_retry_next_run error={http_err}")
            return
        log_and_exit(helper, http_error_to_message(http_err), "input_module_spycloud_watchlist_identifiers.py")

    except Exception as ex:
        msg = str(ex)
        if "proxy" in msg.lower():
            log_and_exit(helper, MSG_PROXY_GENERIC, "input_module_spycloud_watchlist_identifiers.py")
        log_and_exit(helper, f"{MSG_UNEXPECTED_API} {msg}", "input_module_spycloud_watchlist_identifiers.py")

    #helper.log_debug("finish_checkpoint=" + str(checkpoint))
    helper.log_info("input_module_spycloud_watchlist_identifiers.py end")

    elapsed = time.monotonic() - _start_time
    remaining = _MIN_RUNTIME_SECONDS - elapsed
    if remaining > 0:
        helper.log_debug(f"minimum_runtime_sleep seconds={remaining:.2f}")
        time.sleep(remaining)
