
from uuid import uuid4

from datetime import datetime

import utils
import config
import splunk_utils

from api_client import MagentoOrdersAPIClient


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    # Get filled Form fields
    data_input_name = helper.get_arg('name')
    credentials     = helper.get_arg('global_account')
    hostname        = helper.get_arg('hostname')
    endpoint        = helper.get_arg('endpoint')
    version         = helper.get_arg('version')
    start_time      = helper.get_arg('start_time')
    end_time        = helper.get_arg('end_time')
    time_buffer     = helper.get_arg('time_buffer')
    # Validate the URL
    url = f"https://{hostname}"
    utils.is_url_secure(utils.urljoin(url, endpoint))
    unique_id      = str(uuid4())
    start          = splunk_utils.get_order_updates_ingestion_start_time(helper, data_input_name, start_time, version)
    to             = datetime.now().strftime(config.MAGENTO_DATETIME_FORMAT)
    magento_orders = MagentoOrdersAPIClient(url, credentials["username"], credentials["password"])
    helper.log_info(
        f'Starting Order Updates ingestion data_input={data_input_name} id={unique_id} period_from={start} period_to={to}'
    )
    for orders in magento_orders.get_updated_orders_within_period(
        start,
        to
    ):
        for order in orders:
            modified_order = utils.drop_dict_keys(
                order,
                "billing_address",
                "extension_attributes",
            )
            splunk_utils.write_to_index(helper, ew, modified_order, hostname, "orders_updated")
    splunk_utils.set_order_updates_ingestion_next_start_time(helper, data_input_name, start_time, version, to)
    helper.log_info(
        f'Finished Order Updates ingestion data_input={data_input_name} id={unique_id}'
    )

