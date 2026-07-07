
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
    helper.log_debug("input_module_spycloud_compass.py start")

    if not api.shouldRunOnThisSystem(helper):
        helper.log_info("Not running on this system")
        sys.exit(0)
    else:
        helper.log_info("Running on this system")

    enable_compass = helper.get_global_setting('enable_compass')
    enable_compass_normalized = str(enable_compass).strip().lower()
    compass_enabled = enable_compass in (1, True) or enable_compass_normalized in (
        '1',
        'true',
        'yes',
        'on',
    )
    helper.log_debug(
        "enable_compass="
        + str(enable_compass)
        + " normalized="
        + enable_compass_normalized
        + " enabled="
        + str(compass_enabled)
    )
    if not compass_enabled:
        helper.log_info("SpyCloud Compass is disabled. Enable Compass in the SpyCloud config to load Compass data")
        helper.log_info("input_module_spycloud_compass.py end")
        return

    helper.log_debug("SpyCloud Compass is Enabled")
    common.check_api_key(helper, "input_module_spycloud_compass.py")

    # Retrieve input metadata and initialize KV Store
    input_metadata = helper.context_meta
    session_key = input_metadata.get("session_key")
    service = client.connect(token=session_key, app=helper.get_app_name(), owner='nobody')
    kvstore = service.kvstore['compass_v2_checkpoint']

    # Load checkpoint from KV Store
    try:
        kv_checkpoint = kvstore.data.query_by_id('checkpoint')
        checkpoint = json.loads(kv_checkpoint['value']) if kv_checkpoint else {}
    except Exception:
        helper.log_debug("KV Store checkpoint not found, starting load at 14 days ago")
        checkpoint = {}

    if not isinstance(checkpoint, dict):
        checkpoint = {}
    if "documents" not in checkpoint or not isinstance(checkpoint["documents"], dict):
        checkpoint["documents"] = {}

    now_utc = datetime.datetime.utcnow()
    today_utc = now_utc.date()
    yesterday = (today_utc - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    first_run_since = (today_utc - datetime.timedelta(days=14)).strftime("%Y-%m-%d")

    today = common.date_stamp()
    helper.log_debug("today=" + str(today))

    last_processed_date = checkpoint.get("last_processed_date")
    if not last_processed_date and checkpoint.get("last_run"):
        # Backward compatibility with older checkpoints that only stored last_run.
        last_processed_date = str(checkpoint.get("last_run"))[:10]

    until = None
    if not checkpoint.get("last_run"):
        since = first_run_since
        until = yesterday
        should_run = True
        helper.log_info(f"compass_mode=first_run since={since} until={until}")
    elif last_processed_date == yesterday:
        since = yesterday
        until = yesterday
        should_run = False
        helper.log_info(f"compass_mode=skip_already_processed yesterday={yesterday} last_processed_date={last_processed_date}")
    else:
        since = yesterday
        until = yesterday
        should_run = True
        helper.log_info(f"compass_mode=daily_incremental since={since} last_processed_date={last_processed_date}")

    if not should_run:
        helper.log_info("Compass already processed yesterday; skipping this run")
        helper.log_info("input_module_spycloud_compass.py end")
        return

    helper.log_info(f"compass_ingestion_params since={since} until={until}")
    window_start = datetime.datetime.strptime(since, "%Y-%m-%d").date()
    window_end = datetime.datetime.strptime(until, "%Y-%m-%d").date() if until else today_utc
    skipped_out_of_window = 0
    try:
        for result in api.compass(helper, since, until):
            publish_date_raw = result.get("spycloud_publish_date")
            if publish_date_raw:
                try:
                    publish_date = datetime.datetime.strptime(str(publish_date_raw)[:10], "%Y-%m-%d").date()
                    if publish_date < window_start or publish_date > window_end:
                        skipped_out_of_window += 1
                        continue
                except Exception:
                    helper.log_debug(f"compass_publish_date_parse_failed value={publish_date_raw}")

            document_id = result["document_id"]
            if document_id in checkpoint["documents"].keys():
                continue
            # Add to checkpoint object
            checkpoint["documents"][document_id] = today
            # Force timestamp to front of event
            ordered_result = OrderedDict()
            if "spycloud_publish_date" in result:
                ordered_result["spycloud_publish_date"] = result[
                    "spycloud_publish_date"
                ]
                del result["spycloud_publish_date"]
            for key in result:
                ordered_result[key] = result[key]
            data=json.dumps(ordered_result)
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data, time=time.time())
            ew.write_event(event)

        if skipped_out_of_window > 0:
            helper.log_info(f"compass_skipped_out_of_window_records count={skipped_out_of_window} since={since} until={until}")

    except ProxyError as p_err:
        log_and_exit(helper, proxy_error_to_message(p_err), "input_module_spycloud_compass.py")

    except HTTPError as http_err:
        if getattr(getattr(http_err, 'response', None), 'status_code', None) == 429:
            helper.log_warning(f"compass_rate_limited checkpoint_preserved will_retry_next_run error={http_err}")
            return
        log_and_exit(helper, http_error_to_message(http_err), "input_module_spycloud_compass.py")

    except Exception as ex:
        msg = str(ex)
        if "proxy" in msg.lower():
            log_and_exit(helper, MSG_PROXY_GENERIC, "input_module_spycloud_compass.py")
        log_and_exit(helper, f"{MSG_UNEXPECTED_API} {msg}", "input_module_spycloud_compass.py")

    # last_run tracks data watermark, not execution timestamp.
    checkpoint["last_run"] = until if until else yesterday
    checkpoint["last_processed_date"] = yesterday

    # Save updated checkpoint to both KV Store and local file
    try:
        kvstore.data.update('checkpoint', json.dumps({"value": json.dumps(checkpoint)}))
    except client.HTTPError as e:
        if e.status == 404:
            # If not found, insert a new checkpoint
            try:
                kvstore.data.insert({'_key': 'checkpoint', "value": json.dumps(checkpoint)})
            except Exception as insert_error:
                helper.log_error(f"Failed to insert new checkpoint: {str(insert_error)}")
        else:
            helper.log_error(f"Failed to update checkpoint in KV Store: {str(e)}")
    except Exception as general_error:
        helper.log_error(f"An unexpected error occurred: {str(general_error)}")
    
    #helper.log_debug("finish_checkpoint=" + str(checkpoint))
    helper.log_info("input_module_spycloud_compass.py end")
