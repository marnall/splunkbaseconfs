from datetime import datetime, timezone, timedelta

import constants
import log as logging
from baseconfig import ResourceConfig
from client import AkamaiMfaClient, ApiResponseAction
from common import normalize_iso_datetime

LOG = logging.getLogger(__name__)


def main():
    LOG.info(f"Started resource script: app_version={constants.app_version}")
    client = AkamaiMfaClient()

    mfa_server_time = client.mfa_server_time()
    if mfa_server_time is None:
        LOG.error("Could not get MFA server time. Stopping resource script.")
        return

    resource_config = ResourceConfig.load_from_file()
    LOG.info(f"Resource config loaded: min_time={resource_config.min_time}, max_time={resource_config.max_time}, max_items={resource_config.max_items}, page={resource_config.page}")

    min_time = resource_config.min_time
    max_time = resource_config.max_time
    try:
        if min_time == "":
            max_time_dt = mfa_server_time - timedelta(minutes=constants.delay_interval_minutes)
            max_time = max_time_dt.strftime(constants.date_format)
            min_time_dt = max_time_dt - timedelta(days=constants.historic_data_days)
            min_time = min_time_dt.strftime(constants.date_format)
            max_items = constants.resource_page_size

            LOG.info(f"Initializing ResourceConfig with min_time={min_time}, max_time={max_time}, max_items={max_items}, page=1")
            resource_config = ResourceConfig(min_time=min_time, max_time=max_time, max_items=max_items, page=1)
            resource_config.save_to_file()
        else:
            min_time = normalize_iso_datetime(min_time)
            if max_time:
                max_time = normalize_iso_datetime(max_time)
            else:
                max_time_dt = mfa_server_time - timedelta(minutes=constants.delay_interval_minutes)
                max_time = max_time_dt.strftime(constants.date_format)

    except Exception as e:
        LOG.error(f"Stopping resource script due to invalid date in resource.json. Exception: {e}")
        return

    min_time_dt = datetime.strptime(min_time, constants.date_format).replace(tzinfo=timezone.utc)
    max_time_dt = datetime.strptime(max_time, constants.date_format).replace(tzinfo=timezone.utc)
    window_size = timedelta(days=constants.sliding_window_days)
    page = resource_config.page

    while min_time_dt < max_time_dt:
        window_end = min(min_time_dt + window_size, max_time_dt)
        min_time_str = min_time_dt.strftime(constants.date_format)
        max_time_str = window_end.strftime(constants.date_format)

        params = {
            'min_time': min_time_str,
            'max_time': max_time_str,
            'page': page,
            'max_items': resource_config.max_items,
            'order': constants.order_direction_oldest_first
        }

        result = client.resource(params)

        while result.action == ApiResponseAction.MoreDataPresent:
            page = page + 1
            params['page'] = page
            result = client.resource(params)

        min_time_dt = window_end

    LOG.info("Completed resource script")


if __name__ == "__main__":
    main()
