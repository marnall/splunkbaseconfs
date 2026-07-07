from datetime import datetime, timezone, timedelta

import constants
import log as logging
from client import AkamaiMfaClient, ApiResponseAction
from baseconfig import AuthsConfig
from common import normalize_iso_datetime

LOG = logging.getLogger(__name__)


def main():
    LOG.info(f"Started auths script: app_version={constants.app_version}")
    client = AkamaiMfaClient()

    mfa_server_time = client.mfa_server_time()
    if mfa_server_time is None:
        LOG.error("Could not get MFA server time. Stopping auths script.")
        return

    auths_config = AuthsConfig.load_from_file()
    LOG.info(f"Auths config loaded: after={auths_config.after}, min_time={auths_config.min_time}, max_time={auths_config.max_time}, page_size={auths_config.page_size}, continuation_token={auths_config.continuation_token}")

    min_time = auths_config.min_time
    max_time = auths_config.max_time
    try:
        if min_time == "":
            max_time_dt = mfa_server_time - timedelta(minutes=constants.delay_interval_minutes)
            max_time = max_time_dt.strftime(constants.date_format)

            after = auths_config.after
            if after == "":
                min_time_dt = max_time_dt - timedelta(days=constants.historic_data_days)
                min_time = min_time_dt.strftime(constants.date_format)
            else:
                min_time = normalize_iso_datetime(after)
                min_time_dt = datetime.strptime(min_time, constants.date_format).replace(tzinfo=timezone.utc)

            # Older versions of the Splunk app did not add constants.delay_interval_minutes to the query. When migrating
            # from an older version, the new script will need to keep retrying until that delay interval has passed.
            if min_time_dt >= max_time_dt:
                LOG.info(f"Stopping auths script to wait for max_time to exceed min_time: min_time={min_time} max_time={max_time}")
                return

            page_size = constants.auths_page_size

            LOG.info(f"Initializing AuthsConfig with min_time={min_time}, max_time={max_time}, page_size={page_size}, continuation_token={None}")
            auths_config = AuthsConfig(after="", min_time=min_time, max_time=max_time, page_size=page_size, continuation_token=None)
            auths_config.save_to_file()
        else:
            min_time = normalize_iso_datetime(min_time)
            if max_time:
                max_time = normalize_iso_datetime(max_time)
            else:
                max_time_dt = mfa_server_time - timedelta(minutes=constants.delay_interval_minutes)
                max_time = max_time_dt.strftime(constants.date_format)

    except Exception as e:
        LOG.error(f"Stopping auth script due to invalid date in auths.json. Exception: {e}")
        return

    min_time_dt = datetime.strptime(min_time, constants.date_format).replace(tzinfo=timezone.utc)
    max_time_dt = datetime.strptime(max_time, constants.date_format).replace(tzinfo=timezone.utc)
    window_size = timedelta(days=constants.sliding_window_days)

    while min_time_dt < max_time_dt:
        window_end = min(min_time_dt + window_size, max_time_dt)
        min_time_str = min_time_dt.strftime(constants.date_format)
        max_time_str = window_end.strftime(constants.date_format)

        params = {
            'min_time': min_time_str,
            'max_time': max_time_str,
            'page_size': auths_config.page_size,
            'data_order': constants.order_direction_oldest_first
        }

        result = client.auths(params, auths_config.continuation_token)

        while result.action == ApiResponseAction.MoreDataPresent:
            result = client.auths(params, str(result.token))

        min_time_dt = window_end

    LOG.info("Completed auths script")


if __name__ == "__main__":
    main()
