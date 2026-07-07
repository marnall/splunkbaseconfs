# encoding = utf-8

from datetime import datetime, timezone
from socket import gaierror
import time

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from timestamp_utils import CheckpointManager, KVStoreUnavailableError, should_run_in_shc, should_trigger_full_sync
from vulns_collector import get_vulnerabilities

_APP_NAME = 'WizAddOnForSplunk'

log_location = make_splunkhome_path(['var', 'log', 'splunk', _APP_NAME])
HOST_POLLING = 'malicious-'
DIR_NAME_POLLING = 'malicious_data_input'
HOST_SYNC = 'last-sync-'
DIR_NAME_SYNC = 'last_sync_timestamp'


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass


def collect_events(helper, ew):
    if not should_run_in_shc(helper):
        return

    source = helper.get_arg('name')
    try:
        _collect_vulnerabilities(helper, ew, source)
    except KVStoreUnavailableError as e:
        helper.log_error(f"Source name = {source}. KVStore unavailable in cluster mode: {str(e)}")
        raise
    except gaierror:
        raise
    except Exception as e:
        helper.log_error(f"Source name = {source}. Got an error when trying to fetch vulnerabilities events: {str(e)}")


def _collect_vulnerabilities(helper, ew, source):
    start_time = time.time()
    before_timestamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    frequency_days = int(helper.get_arg('sync_frequency') or 0)

    checkpoint = CheckpointManager(
        helper, source, log_location,
        HOST_POLLING, DIR_NAME_POLLING,
        sync_host=HOST_SYNC, sync_dir_name=DIR_NAME_SYNC,
    )

    latest_polling_time = checkpoint.get_timestamp()
    latest_polling_timestamp_iso = latest_polling_time + 'Z' if latest_polling_time else None
    latest_full_sync_time = checkpoint.get_sync_timestamp(frequency_days)
    trigger_full_sync = should_trigger_full_sync(latest_full_sync_time, frequency_days)

    if trigger_full_sync:
        pull_mode = 'full_sync'
    elif latest_polling_timestamp_iso:
        pull_mode = 'incremental'
    else:
        pull_mode = 'initial'

    helper.log_info(
        f"Source name = {source}. Starting a new job! Last pulling timestamp = {latest_polling_timestamp_iso}. "
        f"Last full sync = {latest_full_sync_time}. Trigger full sync = {trigger_full_sync}. Pull mode = {pull_mode}"
    )

    count = get_vulnerabilities(helper, ew, latest_polling_timestamp_iso, trigger_full_sync)
    helper.log_info(f"Source name = {source}. Found {count} total vulnerabilities!")

    storage = checkpoint.set_timestamp(before_timestamp)
    if storage and (trigger_full_sync or not latest_polling_timestamp_iso or (frequency_days != 0 and not latest_full_sync_time)):
        checkpoint.set_sync_timestamp(before_timestamp)
    if storage:
        helper.log_info(
            f"input {source} execution took {(time.time() - start_time)} seconds, "
            f"cursor saved to {storage}: {before_timestamp}"
        )
    else:
        helper.log_info(
            f"input {source} execution took {(time.time() - start_time)} seconds, "
            f"cursor not saved: rewind blocked, existing cursor is newer than {before_timestamp}"
        )
