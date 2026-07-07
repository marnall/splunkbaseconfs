import copy
import datetime

import netaddr
from constants import LAST_REFRESH_IP_RANGES, CIDR_PATH, LAST_RUN_ALERTS, \
    IP_RANGE, CERTIFICATES, DOMAINS, SERVICES, IP_RANGE_DATA_COLLECTION_NAME, RESPONSIVE_IP, DEDUP_ALERT_IDS, \
    RETRY_ALERT_IDS, CLOUD_ASSETS
from dateutil.parser import parse
from kv_store import KVStore
from mapping_constants import get_mapping_constants
from state_refresh import StateRefresh
from xpanse.client import XpanseClient
from xpanse.const import AssetType


def refresh_ip_range_kv_store(helper, expanse_client, kvstore, input_name):
    """Refreshes assets data in kv store.

    Args:
        helper (smi.Script): A helper object that controls logging and state
        expanse_client: The object to connect Expanse data
        kvstore: The object to connect to Splunk server
        input_name (str): input name defined in splunk
    """
    refresh_kv_store(data_type=IP_RANGE, get_data=_get_ip_range_data, helper=helper,
                     expanse_client=expanse_client, kv_store=kvstore,
                     input_name=input_name)


def refresh_certificates_kv_store(helper, expanse_client, kvstore, input_name):
    """Refreshes certificate data in kv store.

    Args:
        helper (smi.Script): A helper object that controls logging and state
        expanse_client: The object to connect Expanse data
        kvstore: The object to connect to Splunk server
        input_name (str): input name defined in splunk
    """
    refresh_kv_store(data_type=CERTIFICATES, get_data=_get_certificates_data, helper=helper,
                     expanse_client=expanse_client,
                     kv_store=kvstore,
                     input_name=input_name)


def refresh_domains_kv_store(helper, expanse_client, kvstore, input_name):
    """Refreshes domains data in kv store.

    Args:
        helper (smi.Script): A helper object that controls logging and state
        expanse_client: The object to connect Expanse data
        kvstore: The object to connect to Splunk server
        input_name (str): input name defined in splunk
    """
    refresh_kv_store(data_type=DOMAINS, get_data=_get_domain_data, helper=helper,
                     expanse_client=expanse_client,
                     kv_store=kvstore,
                     input_name=input_name)


def refresh_services_kv_store(helper, expanse_client, kvstore, input_name):
    """Refreshes services data in kv store.

    Args:
        helper (smi.Script): A helper object that controls logging and state
        expanse_client: The object to connect Expanse data
        kvstore: The object to connect to Splunk server
        input_name (str): input name defined in splunk
    """
    refresh_kv_store(data_type=SERVICES, get_data=_get_service_data, helper=helper,
                     expanse_client=expanse_client,
                     kv_store=kvstore,
                     input_name=input_name)


def refresh_unassociated_responsive_ip_kv_store(helper, expanse_client, kvstore, input_name):
    """Refreshes services data in kv store.

    Args:
        helper (smi.Script): A helper object that controls logging and state
        expanse_client: The object to connect Expanse data
        kvstore: The object to connect to Splunk server
        input_name (str): input name defined in splunk
    """
    refresh_kv_store(data_type=RESPONSIVE_IP,
                     get_data=_get_unassociated_responsive_ip_data,
                     helper=helper,
                     expanse_client=expanse_client,
                     kv_store=kvstore,
                     input_name=input_name)


def refresh_cloud_assets_kv_store(helper, expanse_client, kvstore, input_name):
    """Refreshes services data in kv store.

    Args:
        helper (smi.Script): A helper object that controls logging and state
        expanse_client: The object to connect Expanse data
        kvstore: The object to connect to Splunk server
        input_name (str): input name defined in splunk
    """
    refresh_kv_store(data_type=CLOUD_ASSETS,
                     get_data=_get_cloud_asset_data,
                     helper=helper,
                     expanse_client=expanse_client,
                     kv_store=kvstore,
                     input_name=input_name)


def should_refresh_assets(helper, input_name, asset_type=None):
    """Calculate whether assets or exposures data is stale.

    Args:
        helper (smi.Script): A helper object that controls logging and state
        input_name (str): input name defined in splunk
        asset_type: Optional input describing asset type.

    Returns:
        bool: True if assets should refresh, False otherwise
    """
    mapping_constants = get_mapping_constants(input_name)
    try:
        state_refresh = mapping_constants[asset_type]
    except KeyError:
        helper.log_warning("Unknown data type {} checkpointing, using defaults".format(asset_type))
        state_refresh = StateRefresh(1, "{}_{}".format(input_name, LAST_REFRESH_IP_RANGES),
                                     IP_RANGE_DATA_COLLECTION_NAME)

    last_refresh = helper.get_check_point(state_refresh.check_point_name)
    if last_refresh:
        next_refresh = parse(last_refresh) + datetime.timedelta(days=state_refresh.refresh_rate_days)
        should_refresh = next_refresh < datetime.datetime.now()
    else:
        should_refresh = True

    helper.log_debug(
        "Date of last_refresh={}, should_refresh={}".format(last_refresh, should_refresh))

    return should_refresh


def get_prior_alerts_update_state(helper, input_name):
    """Get the checkpoints from the previous run

    Args:
        helper (smi.Script): A helper object that controls logging and state
        input_name (str): the input name

    Returns:
        dict: checkpoint state for last run time, dedup_ids, and retry_ids
    """

    return (helper.get_check_point("{}_{}".format(LAST_RUN_ALERTS, input_name)),
            helper.get_check_point("{}_{}".format(RETRY_ALERT_IDS, input_name)) or [])


def update_alert_checkpoints(helper, input_name, date, failure_ids):
    """Updates the alert checkpoints to set the last_run date, the ids to dedup and the ids to retry

    Args:
        helper (smi.Script): A helper object that controls logging and state
        input_name (str): The input name
        failure_ids (list): the ids of the alerts that failed to sync
        date (str): The dateTime of the event
    """

    helper.save_check_point("{}_{}".format(LAST_RUN_ALERTS, input_name), date)
    helper.save_check_point("{}_{}".format(RETRY_ALERT_IDS, input_name), failure_ids)


def get_check_point_name(date, endpoint, input_name):
    """Converts date to checkpoint key.

    Arguments:
        date {date} - Event date

    Returns:
        str - Name of checkpoint
    """

    return 'expanse_{}_{}_{}'.format(endpoint.value, input_name, str(date).replace('-', '_'))


def refresh_kv_store(data_type, get_data, helper, expanse_client: XpanseClient, kv_store: KVStore, input_name: str):
    """Generic - refreshes any data in kv store.

    Args:
        data_type (str): The type of data to refresh - used in Checkpointing lookups
        get_data (function): Function used to get the get and transform data that will be uploaded to the kv store.
        helper (smi.Script): A helper object that controls logging and state
        expanse_client: The object to connect Expanse data
        kv_store: The object to connect to Splunk server
        input_name (str): input name defined in splunk
    """
    should_refresh = should_refresh_assets(helper, input_name, data_type)

    if should_refresh:
        try:
            helper.log_info('{} data is stale for input {}. Refreshing.'.format(data_type, input_name))

            data = get_data(helper, expanse_client, input_name) or []
            data = (KVStore.flatten_json(entry) for entry in data)

            mapping_const = get_mapping_constants(input_name)[data_type]

            kv_store.create_collection(collection=mapping_const.collection_name)
            kv_store.clear_collection(helper, collection=mapping_const.collection_name, input_name=input_name)
            result = kv_store.update_kv_store_data(collection=mapping_const.collection_name, kv_data=data,
                                                   helper=helper)
            helper.save_check_point(mapping_const.check_point_name, str(datetime.datetime.now().date()))

            return result
        except Exception as e:
            helper.log_error("{} refresh failed error: {}".format(data_type, repr(e)))


def _get_ip_range_data(helper, expanse_client: XpanseClient, input_name):
    """Function to update the key value store to hold the appropriate CIDRs for the IP Range

    There are multiple Last Refresh variables - one for all types. All assets are
    updated daily, instead of weekly as done in <= v2.3.

    Args:
        helper (smi.Script): A helper object that controls logging and state
        expanse_client: The object to connect Expanse data
        input_name (str): input name defined in splunk

    Returns:
        data: transformed data
    """

    def _get_cidrs(ip_range):
        try:
            start = ip_range['first_ip'] or ip_range['first_ipv6']
            end = ip_range['last_ip'] or ip_range['last_ipv6']
            return netaddr.iprange_to_cidrs(start, end)
        except BaseException:
            return ['Error in IP range']

    try:
        result = expanse_client.owned_ip_ranges.list()
        temp_ip_range_list = _update_kv_entries(result.dump(), input_name, 'range_id')
        helper.log_info(f"Received {result.total} ip ranges")
        for ip_range in temp_ip_range_list:
            cidrs = _get_cidrs(ip_range)
            for cidr in cidrs:
                range_copy = copy.deepcopy(ip_range)
                cidr_str = KVStore.cidr_to_str(cidr)
                key = f"{ip_range['input_name']}_{cidr_str}"
                range_copy.update({CIDR_PATH: str(cidr)})
                range_copy.update({KVStore.KV_KEY_PATH: key})
                yield range_copy
    except Exception as e:
        helper.log_error("Error in fetching ip ranges: {}".format(repr(e)))
        raise e


def _get_certificates_data(helper, expanse_client: XpanseClient, input_name):
    """Function to update the key value store to hold certificate data

    There are multiple Last Refresh variables - one for all types. All assets are
    updated daily, instead of weekly as done in <= v2.3.

    Args:
        helper (smi.Script): A helper object that controls logging and state
        expanse_client: The object to connect Expanse data
        input_name (str): input name defined in splunk

    Returns:
        kv_store.KVStore: The store with updated CIDRs
    """
    try:
        result = expanse_client.assets.list(asset_types={AssetType.CERTIFICATE})
        helper.log_info(f"Received {result.total} certificate")
        return _update_kv_entries(result.dump(), input_name, 'asm_ids')
    except Exception as e:
        helper.log_error("Error in fetching certificates: {}".format(repr(e)))
        raise e


def _get_domain_data(helper, expanse_client: XpanseClient, input_name):
    """Function to update the key value store to hold domain data

    There are multiple Last Refresh variables - one for all types. All assets are
    updated daily, instead of weekly as done in <= v2.3.

    Args:
        helper (smi.Script): A helper object that controls logging and state
        expanse_client: The object to connect Expanse data
        input_name (str): input name defined in splunk
    Returns:
        kv_store.KVStore: The store with updated CIDRs
    """
    try:
        result = expanse_client.assets.list(asset_types={AssetType.DOMAIN})
        helper.log_info(f"Received {result.total} domains")
        return _update_kv_entries(result.dump(), input_name, 'asm_ids')
    except Exception as e:
        helper.log_error("Error in fetching domains: {}".format(repr(e)))
        raise e


def _get_service_data(helper, expanse_client, input_name):
    """Function to update the key value store to hold services data

    Args:
        helper (smi.Script): A helper object that controls logging and state
        expanse_client: The object to connect Expanse data
        input_name (str): input name defined in splunk

    Returns:
        kv_store.KVStore: The store with updated data
    """
    try:
        result = expanse_client.services.list()
        helper.log_info(f"Received {result.total} services")
        return _update_kv_entries(result.dump(), input_name, 'service_id')
    except Exception as e:
        helper.log_error("Error in fetching services: {}".format(repr(e)))
        raise e


def _get_unassociated_responsive_ip_data(helper, expanse_client, input_name):
    """Function to update the key value store to unassociated_responsive_ip data
    Args:
        helper (smi.Script): A helper object that controls logging and state
        expanse_client: The object to connect Expanse data
        input_name (str): input name defined in splunk
    Returns:
        kv_store.KVStore: The store with updated data
    """
    try:
        result = expanse_client.assets.list(
            asset_types={AssetType.OWNED_RESPONSIVE_IP})
        helper.log_info(f"Received {result.total} unassociated_responsive_ip")
        return _update_kv_entries(result.dump(), input_name, 'asm_ids')
    except Exception as e:
        helper.log_error("Error in fetching services: {}".format(repr(e)))
        raise e


def _get_cloud_asset_data(helper, expanse_client: XpanseClient, input_name):
    """Function to update the key value store to hold cloud asset data

    There are multiple Last Refresh variables - one for all types. All assets are
    updated daily, instead of weekly as done in <= v2.3.

    Args:
        helper (smi.Script): A helper object that controls logging and state
        expanse_client: The object to connect Expanse data
        input_name (str): input name defined in splunk
    Returns:
        kv_store.KVStore: The store with updated CIDRs
    """
    try:
        result = expanse_client.assets.list(
            asset_types={AssetType.CLOUD_RESOURCES, AssetType.PRISMA_CLOUD_RESOURCE})
        helper.log_info(f"Received {result.total} cloud assets")
        return _update_kv_entries(result.dump(), input_name, 'asm_ids')
    except Exception as e:
        helper.log_error("Error in fetching domains: {}".format(repr(e)))
        raise e


def _update_kv_entries(iter, input_name, key_column):
    for entry in iter:
        entry.update({"_key": f"{input_name}_{entry[key_column]}"})
        entry.update({"input_name": input_name})
        yield entry
