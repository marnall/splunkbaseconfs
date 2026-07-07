import concurrent.futures
import datetime
from concurrent.futures import ALL_COMPLETED

from splunk_client import SplunkClient
from exceptions import AbortSyncException
from deduplication import AlertDeduplicationProcessor
from kv_store import KVStore
from process_alerts import process_alerts
from state_utils import (refresh_certificates_kv_store, refresh_domains_kv_store,
                         refresh_services_kv_store, refresh_ip_range_kv_store,
                         refresh_unassociated_responsive_ip_kv_store, refresh_cloud_assets_kv_store)
from utils import (get_proxy, get_configuration_settings,
                   get_expanse_client, get_start_date, should_ingest_alerts, fetch_existing_alerts)

TASK_TIMEOUT_SECONDS = 23 * 60 * 3600


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    """
    The high level method to collect events from the Expanse APIs, push
    them into Splunk, and save the state of the run.

    Args:
        helper (smi.Script): Helper object used to log and handle state
        ew (EventWriter): Object to write events into Splunk
    """
    helper.log_info("Process started at {}".format(datetime.datetime.now()))

    # Get configuration
    username, password, token, server_url, use_advanced_auth, api_key_id, start_date, enable_alert_updates, \
        enable_assets, enable_services, input_name, utc_offset = get_configuration_settings(helper)

    helper.log_info("Process running for {}".format(input_name))

    # Reformat input name
    input_name = input_name.lower().replace('.', '-').replace('/', '_').strip().replace(' ', '')

    # Find proxy details
    proxy = get_proxy(helper)

    # Get expanse client
    expanse = get_expanse_client(helper=helper, token=token, server_url=server_url, proxy=proxy,
                                 use_advanced_auth=use_advanced_auth, api_key_id=api_key_id)
    helper.log_info("about to start kv store client")
    kvstore = KVStore(username, password, input_name=input_name)
    # Calculate startDateUtc for Alerts
    alert_start_date_utc = get_start_date(helper, input_name, start_date, utc_offset)

    # Initialize the AlertDeduplicationProcessor, which will fetch the alerts that are already in splunk
    # from the past 2 days
    alert_deduplication_processor = None
    if should_ingest_alerts(enable_alert_updates, alert_start_date_utc):
        try:
            existing_alert_ids = fetch_existing_alerts(input_name, helper, start_date, SplunkClient(username, password))
            alert_deduplication_processor = AlertDeduplicationProcessor(dedup_ids=existing_alert_ids)
            helper.log_debug(f"Debugging deduplication: Found {len(existing_alert_ids)} "
                             f"existing alerts over the past 2 days: {existing_alert_ids}")
        except AbortSyncException as e:
            helper.log_error(f"Error occurred before importing Xpanse data on input {input_name}."
                             f" Stopping process. Exception: {str(e)}")
            return

    # Continue processing in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(lambda: None)]

        if should_ingest_alerts(enable_alert_updates, alert_start_date_utc) and \
                alert_deduplication_processor is not None:
            futures.append(executor.submit(sync_alerts(helper, ew, expanse, alert_deduplication_processor,
                                                       alert_start_date_utc, input_name)))

        # Refresh domain, certs, ip range, resp IPs, cloud assets if stale
        if enable_assets == '1':
            futures.append(executor.submit(refresh_certificates_kv_store(helper, expanse, kvstore, input_name)))
            futures.append(executor.submit(refresh_domains_kv_store(helper, expanse, kvstore, input_name)))
            futures.append(executor.submit(refresh_ip_range_kv_store(helper, expanse, kvstore, input_name)))
            futures.append(executor.submit(refresh_unassociated_responsive_ip_kv_store(
                helper, expanse, kvstore, input_name)))
            futures.append(executor.submit(refresh_cloud_assets_kv_store(
                helper, expanse, kvstore, input_name)))

        if enable_services == '1':
            futures.append(executor.submit(refresh_services_kv_store(helper, expanse, kvstore, input_name)))

        concurrent.futures.wait(futures, timeout=TASK_TIMEOUT_SECONDS, return_when=ALL_COMPLETED)

    helper.log_info("Process finished for input {} at {}".format(input_name, datetime.datetime.now()))


def sync_alerts(helper, event_writer, expanse_client, alert_deduplication_processor, start_date, input_name):
    helper.log_info('Initiating alerts data ingest for input_name {}'.format(input_name))
    helper.log_debug("Start date: {}".format(start_date))

    # Write issues updates to index in json format
    is_complete, success_count, failure_count = process_alerts(
        helper, event_writer, expanse_client, alert_deduplication_processor, start_date, input_name)

    helper.log_info("{} alerts were added to Splunk index for input {}.".format(success_count, input_name))

    if is_complete:
        helper.log_info('All alerts for input {} starting at {} were written successfully: alert_count={}'
                        .format(input_name, start_date, success_count))
    else:
        helper.log_error(
            'There were errors after writing {} alerts to input {}; {} updates failed to write'
            .format(success_count, input_name, failure_count))
    return is_complete
