# encoding = utf-8

from datetime import datetime, timedelta, timezone
from socket import gaierror
import time

from audit_collector import get_user_audit_logs
from timestamp_utils import CheckpointManager, KVStoreUnavailableError, should_run_in_shc, try_parse_wiz_timestamp

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
        start_time = time.time()
        opt_historical_polling_days = int(helper.get_arg("historical_polling_days") or 0)
        interval = int(helper.get_arg('interval') or 60)
        window_multiplier = int(helper.get_arg('window_multiplier') or 60)
        if window_multiplier < 1:
            helper.log_warning(
                f"Source name = {source}. window_multiplier={window_multiplier} is below 1; clamping to 1."
            )
            window_multiplier = 1
        elif window_multiplier > 1440:
            helper.log_warning(
                f"Source name = {source}. window_multiplier={window_multiplier} is above 1440; clamping to 1440."
            )
            window_multiplier = 1440
        max_window_seconds = interval * window_multiplier

        checkpoint = CheckpointManager(helper, source, log_location, HOST_POLLING, DIR_NAME_POLLING)

        latest_polling_time = checkpoint.get_timestamp()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if not latest_polling_time:
            if opt_historical_polling_days > 0:
                latest_polling_time = (now - timedelta(days=opt_historical_polling_days)).isoformat()
            else:
                helper.log_warning(
                    f"Source name = {source}. historical_polling_days is missing or not positive; "
                    "starting audit collection from midnight UTC today."
                )
                latest_polling_time = now.replace(hour=0, minute=0, second=0, microsecond=1).isoformat()

        # Cap per-poll window so cursor advances even when pagination can't finish before restart.
        before_timestamp = now.isoformat()
        latest_dt = try_parse_wiz_timestamp(latest_polling_time + 'Z', nudge=False)
        if latest_dt is not None:
            proposed_end = latest_dt + timedelta(seconds=max_window_seconds)
            if proposed_end < now:
                before_timestamp = proposed_end.isoformat()
                helper.log_info(
                    f"Source name = {source}. Audit window bounded: "
                    f"[{latest_polling_time}, {before_timestamp}] "
                    f"(interval={interval}s x window_multiplier={window_multiplier})"
                )
            else:
                helper.log_debug(
                    f"Source name = {source}. Audit window unbounded "
                    f"(last_cursor within {max_window_seconds}s of now)"
                )
        else:
            helper.log_warning(
                f"Source name = {source}. Could not parse audit cursor {latest_polling_time!r}; "
                "audit window is unbounded for this poll."
            )

        latest_polling_timestamp_iso = latest_polling_time + 'Z'
        helper.log_info(f"Source name = {source}. Starting a new job! Last pulling timestamp = {latest_polling_timestamp_iso}")
        user_audit_logs_num = get_user_audit_logs(helper, latest_polling_timestamp_iso, ew, before_timestamp)
        helper.log_info(f"Source name = {source}. Fetched {user_audit_logs_num} User Audit Logs!")
        storage = checkpoint.set_timestamp(before_timestamp)
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
    except KVStoreUnavailableError as e:
        helper.log_error(f"Source name = {source}. KVStore unavailable in cluster mode: {str(e)}")
        raise
    except gaierror:
        raise
    except Exception as e:
        helper.log_error(f"Source name = {source}. Got an error when trying to fetch audit logs events: {str(e)}")
