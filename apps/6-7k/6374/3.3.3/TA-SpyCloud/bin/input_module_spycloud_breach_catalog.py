# encoding = utf-8

import os
import sys
import json
import time
import datetime
from collections import OrderedDict
from requests import HTTPError
from requests.exceptions import ProxyError
import splunklib.client as client
import api
import common
from helpers import *
from ingestion import Ingestion

# Splunk's ExecProcessor can back off scheduling modular inputs that exit too
# quickly, even when successful. Keep a small minimum runtime to maintain cadence.
_MIN_RUNTIME_SECONDS = 5


def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    _start_time = time.monotonic()
    helper.log_info("input_module_spycloud_breach_catalog.py start")

    if not api.shouldRunOnThisSystem(helper):
        helper.log_info("Not running on this system")
        sys.exit(0)
    else:
        helper.log_info("Running on this system")

    common.check_api_key(helper, "input_module_spycloud_breach_catalog.py")

    # Retrieve input metadata and initialize KV Store
    input_metadata = helper.context_meta
    session_key = input_metadata.get("session_key")
    service = client.connect(token=session_key, app=helper.get_app_name(), owner='nobody')
    kvstore = service.kvstore['breach_catalog_v2_checkpoint']

    # Initialize ingestion handler
    ingestion = Ingestion(helper, kvstore)

    # Get ingestion parameters (since, until)
    # First run: since = 1970-01-01, until = now
    # Incremental: since = last_run + 1 second, until = now
    since, until = ingestion.get_ingestion_params()

    # Breach catalog API only accepts yyyy-mm-dd format — convert from ISO timestamp
    since_date = since[:10] if since else None
    helper.log_info(f"breach_catalog_ingestion_params since={since_date} until={until}")

    # Load current checkpoint for document tracking
    checkpoint = ingestion._load_checkpoint()

    events_processed = 0

    try:
        for result in api.breach_catalog(helper, since_date):
            # Use source_ids for deduplication (unique breach identifier)
            document_id = result.get("source_ids") or result.get("uuid") or result.get("id")
            if not document_id:
                helper.log_debug(f"Skipping result with no unique identifier: {result}")
                continue
            if document_id in checkpoint["documents"].keys():
                continue

            ingestion.track_document(
                checkpoint,
                document_id,
                result.get("breach_date")
            )
            events_processed += 1

            # Force timestamp to front of event
            ordered_result = OrderedDict()
            if "breach_date" in result:
                ordered_result["breach_date"] = result["breach_date"]
                del result["breach_date"]
            for key in result:
                ordered_result[key] = result[key]
            data = json.dumps(ordered_result)
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data, time=time.time())
            ew.write_event(event)

        helper.log_info(f"Successfully processed {events_processed} events")

        # Update checkpoint and last_run in a single save.
        ingestion.update_checkpoint_after_success(until, checkpoint)

    except ProxyError as p_err:
        log_and_exit(helper, proxy_error_to_message(p_err), "input_module_spycloud_breach_catalog.py")

    except HTTPError as http_err:
        if getattr(getattr(http_err, 'response', None), 'status_code', None) == 429:
            helper.log_warning(f"breach_catalog_rate_limited checkpoint_preserved will_retry_next_run error={http_err}")
            elapsed = time.monotonic() - _start_time
            remaining = _MIN_RUNTIME_SECONDS - elapsed
            if remaining > 0:
                helper.log_debug(f"minimum_runtime_sleep seconds={remaining:.2f}")
                time.sleep(remaining)
            return
        log_and_exit(helper, http_error_to_message(http_err), "input_module_spycloud_breach_catalog.py")

    except Exception as ex:
        msg = str(ex)
        if "proxy" in msg.lower():
            log_and_exit(helper, MSG_PROXY_GENERIC, "input_module_spycloud_breach_catalog.py")
        log_and_exit(helper, f"{MSG_UNEXPECTED_API} {msg}", "input_module_spycloud_breach_catalog.py")

    helper.log_info("input_module_spycloud_breach_catalog.py end")

    elapsed = time.monotonic() - _start_time
    remaining = _MIN_RUNTIME_SECONDS - elapsed
    if remaining > 0:
        helper.log_debug(f"minimum_runtime_sleep seconds={remaining:.2f}")
        time.sleep(remaining)
