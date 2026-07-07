# encoding = utf-8

import json
from datetime import datetime, timezone, timedelta
from socket import gaierror
import time

from detections_collector import get_detections
from timestamp_utils import CheckpointManager, KVStoreUnavailableError, should_run_in_shc


from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

_APP_NAME = 'WizAddOnForSplunk'

log_location = make_splunkhome_path(['var', 'log', 'splunk', _APP_NAME])
HOST_POLLING = 'malicious-'
DIR_NAME_POLLING = 'malicious_data_input'

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass

def collect_events(helper, ew):
    if not should_run_in_shc(helper):
        return

    source = helper.get_arg('name')
    try:
        start_time = time.monotonic()
        checkpoint = CheckpointManager(helper, source, log_location, HOST_POLLING, DIR_NAME_POLLING)

        latest_polling_cursor = checkpoint.get_cursor()
        historical_polling_days = int(helper.get_arg("historical_polling_days") or 0)

        helper.log_info(f"Source name = {source}. Starting a new job! Days back = {historical_polling_days}, last polling cursor = {latest_polling_cursor}.")

        last_saved_cursor = None
        last_cursor_storage = None

        def save_latest_cursor(cursor_value):
            nonlocal last_saved_cursor, last_cursor_storage
            last_cursor_storage = checkpoint.set_cursor(cursor_value)
            last_saved_cursor = cursor_value
        detections_num = get_detections(helper, ew, historical_polling_days, latest_polling_cursor, save_cursor_callback=save_latest_cursor)
        helper.log_info(f"Source name = {source}. Found {detections_num} detections!")
        elapsed = time.monotonic() - start_time
        if last_saved_cursor is not None:
            helper.log_info(
                f"input {source} execution took {elapsed} seconds, "
                f"cursor saved to {last_cursor_storage}: {last_saved_cursor}"
            )
        else:
            helper.log_info(
                f"input {source} execution took {elapsed} seconds, "
                f"no new cursor saved (unchanged: {latest_polling_cursor})"
            )
    except KVStoreUnavailableError as e:
        helper.log_error(f"Source name = {source}. KVStore unavailable in cluster mode: {str(e)}")
        raise
    except Exception as e:
        if isinstance(e, gaierror):
            raise e
        helper.log_error(f"Source name = {source}. Got an error when trying to fetch detections events: {str(e)}")
