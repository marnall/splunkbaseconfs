from datetime import datetime, timezone, timedelta

import constants
import log as logging
from baseconfig import SessionHistoryConfig
from client import AkamaiMfaClient, ApiResponseAction
from common import normalize_iso_datetime

LOG = logging.getLogger(__name__)


def main():
    LOG.info(f"Started session history script: app_version={constants.app_version}")
    client = AkamaiMfaClient()

    mfa_server_time = client.mfa_server_time()
    if mfa_server_time is None:
        LOG.error("Could not get MFA server time. Stopping session history script.")
        return

    session_history_config = SessionHistoryConfig.load_from_file()
    LOG.info(f"Session history config loaded: min_time={session_history_config.min_time}, max_time={session_history_config.max_time}, max_items={session_history_config.max_items}, page={session_history_config.page}")

    min_time = session_history_config.min_time
    max_time = session_history_config.max_time
    try:
        if min_time == "":
            max_time_dt = mfa_server_time - timedelta(minutes=constants.delay_interval_minutes)
            max_time = max_time_dt.strftime(constants.date_format)
            min_time_dt = max_time_dt - timedelta(days=constants.historic_data_days)
            min_time = min_time_dt.strftime(constants.date_format)
            max_items = constants.session_history_page_size

            LOG.info(f"Initializing SessionHistoryConfig with min_time={min_time}, max_time={max_time}, max_items={max_items}, page=1")
            session_history_config = SessionHistoryConfig(min_time=min_time, max_time=max_time, max_items=max_items, page=1)
            session_history_config.save_to_file()
        else:
            min_time = normalize_iso_datetime(min_time)
            if max_time:
                max_time = normalize_iso_datetime(max_time)
            else:
                max_time_dt = mfa_server_time - timedelta(minutes=constants.delay_interval_minutes)
                max_time = max_time_dt.strftime(constants.date_format)

    except Exception as e:
        LOG.error(f"Stopping session history script due to invalid date in resource.json. Exception: {e}")
        return

    min_time_dt = datetime.strptime(min_time, constants.date_format).replace(tzinfo=timezone.utc)
    max_time_dt = datetime.strptime(max_time, constants.date_format).replace(tzinfo=timezone.utc)
    window_size = timedelta(days=constants.sliding_window_days)
    page = session_history_config.page

    while min_time_dt < max_time_dt:
        window_end = min(min_time_dt + window_size, max_time_dt)
        min_time_str = min_time_dt.strftime(constants.date_format)
        max_time_str = window_end.strftime(constants.date_format)

        params = {
            'min_time': min_time_str,
            'max_time': max_time_str,
            'page': page,
            'max_items': session_history_config.max_items,
            'outcome': constants.exclude_incomplete_events,
            'order_by': constants.order_by_end_time,
            'direction': constants.order_direction_oldest_first
        }

        result = client.session_history(params)

        while result.action == ApiResponseAction.MoreDataPresent:
            page = page + 1
            params['page'] = page
            result = client.session_history(params)

        min_time_dt = window_end

    LOG.info("Completed session history script")


if __name__ == "__main__":
    main()
