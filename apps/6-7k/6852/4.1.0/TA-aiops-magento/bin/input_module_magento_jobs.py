from uuid import uuid4

from datetime import datetime

import utils
import config
import splunk_utils

from api_client import MagentoJobsAPIClient


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    # Get filled Form fields
    data_input_name = helper.get_arg('name')
    credentials = helper.get_arg('credentials')
    hostname = helper.get_arg('hostname')
    endpoint = helper.get_arg('endpoint')
    version = helper.get_arg('version')
    start_time = helper.get_arg('start_time')
    # Validate the URL
    url = f"https://{hostname}"
    utils.is_url_secure(utils.urljoin(url, endpoint))
    unique_id      = str(uuid4())
    start          = splunk_utils.get_job_ingestion_ingestion_start_time(helper, data_input_name, start_time, version)
    to             = datetime.now().strftime(config.MAGENTO_DATETIME_FORMAT)
    magento_jobs = MagentoJobsAPIClient(url, credentials["username"], credentials["password"])
    helper.log_info(
        f'Starting Job ingestion data_input={data_input_name} id={unique_id} period_from={start} period_to={to}'
    )
    for jobs in magento_jobs.get_executed_jobs_within_period(
        start,
        to
    ):
        for job in jobs:
            splunk_utils.write_to_index(helper, ew, job, hostname, "jobs")
    splunk_utils.set_job_ingestion_next_start_time(helper, data_input_name, start_time, version, to)
    helper.log_info(
        f'Finished Job ingestion data_input={data_input_name} id={unique_id}'
    )
