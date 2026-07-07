from uuid import uuid4

from datetime import datetime, timedelta

import utils
import config
import splunk_utils

from api_client import MagentoLogsAPIClient


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    data_input_name = helper.get_arg("name")
    credentials     = helper.get_arg("credentials")
    threshold       = helper.get_arg("threshold")
    pattern         = helper.get_arg("pattern")
    hostname        = helper.get_arg("hostname")
    # Validate the URL
    url = f"https://{hostname}"
    utils.is_url_secure(url)
    unique_id              = str(uuid4())
    date_threshold         = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=int(threshold))
    to                     = datetime.now().strftime(config.MAGENTO_DATETIME_FORMAT)
    magento_logs           = MagentoLogsAPIClient(url, credentials["username"], credentials["password"])
    server, log_files      = magento_logs.list_log_files()
    filtered_log_files     = magento_logs.filter_log_files_by_date(log_files, date_threshold)
    helper.log_info(
        f'Starting Log ingestion data_input={data_input_name} id={unique_id} '
    )
    for log_file_obj in filtered_log_files:
        fpath           = log_file_obj.get("path")
        fname           = log_file_obj.get("displayname")
        current_fsize   = log_file_obj.get("size")
        log_file_state  = splunk_utils.get_or_create_log_file_state(helper, log_file_obj, server=server)
        bytes_read      = log_file_state.get("bytes_read")

        if current_fsize == bytes_read:
            continue

        byte_range = f"{bytes_read}-{current_fsize}"
        log_file = magento_logs.get_log_file(fpath, byte_range)
        file_served_from = log_file["server"]
        file_content_raw = log_file["content"]
        file_content_cleaned = file_content_raw.lstrip('"').rstrip('"')
        for line in file_content_cleaned.splitlines():
            event = helper.new_event(
                line,
                host=hostname,
                index=helper.get_output_index(),
                source=fname,
            )
            ew.write_event(event)
        splunk_utils.save_log_file_state(helper, log_file_obj, server=file_served_from)
    helper.log_info(
        f'Finished Log ingestion data_input={data_input_name} id={unique_id}'
    )