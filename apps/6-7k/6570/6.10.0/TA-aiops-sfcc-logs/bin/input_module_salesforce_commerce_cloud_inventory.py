# encoding = utf-8

import json

from uuid import uuid4
from collections import deque
from datetime import datetime

import utils
import license
import inventory


def validate_input(helper, definition):
    return None


def create_product_inventory_state(product_inventory, inventory_id, helper):
    try:
        state = {"resource_state": product_inventory.get("_resource_state", None)}
        state_str = json.dumps(state)

        return {"_key": f"{inventory_id}_{product_inventory['product_id']}", "state": state_str}
    except KeyError as keyerr_exc:
        helper.log_error(f"Cannot find key data={product_inventory}")

        raise keyerr_exc
    except Exception as exc:
        raise exc


def write_to_index(ew, source, data, helper, ocapi_hostname):
    event = helper.new_event(
        data=json.dumps(data),
        host=ocapi_hostname,
        index=helper.get_output_index(),
        source=source,
        sourcetype='inventory'
    )
    ew.write_event(event)


def write_to_kvstore(states, helper, data_input_name, inventory_id, unique_id):
    batch_count = 500
    states_len = len(states)
    # Split Order States in batches of small size
    batch_states = utils.split_into_batches(states, batch_count)
    helper.log_info(
        f'Start writing to KVStore data_input={data_input_name} inventory_id={inventory_id} id={unique_id} batch={batch_count} count={states_len}'
    )
    # Save Order States to KVStore in batches
    utils.batch_save_kvstore(helper, batch_states)
    helper.log_info(
        f'End writing to KVStore data_input={data_input_name} inventory_id={inventory_id} id={unique_id} batch={batch_count} count={states_len}'
    )


def ingest_inventory(
    access_token,
    inventory_id,
    data,
    helper,
    url,
    ew,
    ocapi_hostname,
    data_input_name,
    unique_id
):
    products_ids = inventory.get_inventory_products_ids(inventory_id, data, helper)
    helper.log_info(
        f'[Inventory] Fetching Product Inventories data_input={data_input_name} inventory_id={inventory_id} id={unique_id} count={len(products_ids)}'
    )
    products_inventories_events = inventory.get_product_inventory_details_records(url, access_token, inventory_id, products_ids, helper)
    helper.log_info(
        f'[Inventory] Fetched Product Inventories data_input={data_input_name} inventory_id={inventory_id} id={unique_id} count={len(products_ids)}'
    )
    products_inventories_states = deque([])
    helper.log_info(
        f'[Inventory] Start Write Product Inventories to Index data_input={data_input_name} inventory_id={inventory_id} id={unique_id} count={len(products_inventories_events)}'
    )
    for product_inventory_event in products_inventories_events:
        product_inventory = inventory.transform_product_inventory_data(product_inventory_event)
        write_to_index(ew, inventory_id, product_inventory, helper, ocapi_hostname)
        try:
            product_inventory_state = create_product_inventory_state(product_inventory_event, inventory_id, helper)
            products_inventories_states.append(product_inventory_state)
        except Exception as exc:
            helper.log_error(f"Failed to create a state data={product_inventory_event}")
            helper.log_error(f"Failed with exception message={str(exc)}")
    helper.log_info(
        f'[Inventory] Finish Write Product Inventories to Index data_input={data_input_name} inventory_id={inventory_id} id={unique_id} count={len(products_inventories_states)}'
    )

    if products_inventories_states:
        write_to_kvstore(products_inventories_states, helper, data_input_name, inventory_id, unique_id)


@license.license_required
def collect_events(helper, ew):
    ocapi_hostname = helper.get_arg('ocapi_hostname')
    ocapi_data_api_endpoint = helper.get_arg('ocapi_data_api_endpoint')
    inventory_ids_str = helper.get_arg('list_of_inventory_ids')
    access_token = utils.obtain_access_token(helper)
    inventory_ids = inventory_ids_str.split(',')

    for inventory_id in inventory_ids:
        try:
            from_datetime, to_datetime = collect_events_for_inventory(
                inventory_id,
                ocapi_hostname,
                ocapi_data_api_endpoint,
                access_token,
                ew,
                helper
            )
        except utils.HTTPForbiddenError as e:
            helper.log_error(e.errorMessage)


def collect_events_for_inventory(inventory_id, ocapi_hostname, ocapi_data_endpoint_url, access_token, ew, helper):
    unique_id = str(uuid4())
    data_input_name = helper.get_arg('name')
    utils.init_program_termination_handlers(unique_id, data_input_name, helper)
    url = 'https://%s/s/%s' % (ocapi_hostname, ocapi_data_endpoint_url)
    utils.enforce_secure_connection(url)
    auth_token = access_token["access_token"]
    helper.log_info(
        f'Starting Inventory ingestion data_input={data_input_name} inventory_id={inventory_id} id={unique_id}'
    )
    product_inventory_response = inventory.get_product_inventory_records(
        url,
        inventory_id,
        auth_token
    )
    helper.log_info(
        f'Total Inventory records to ingest data_input={data_input_name} inventory_id={inventory_id} count={product_inventory_response["total"]}'
    )
    product_inventory_records = inventory.deep_get(product_inventory_response, "data")

    if product_inventory_records:
        ingest_inventory(auth_token, inventory_id, product_inventory_records, helper, url, ew, ocapi_hostname, data_input_name, unique_id)

    if inventory.has_next(product_inventory_response):
        for data in inventory.paginate(product_inventory_response, access_token, helper, utils.obtain_access_token):
            datetime_now = datetime.now()
            token_expiry_minutes_diff = (datetime_now - access_token["expires_datetime"]).total_seconds() / 60.0
            if datetime.now() >= access_token["expires_datetime"] or token_expiry_minutes_diff >= 27:
                helper.log_info("Renewing access token")
                access_token = utils.obtain_access_token(helper)
                auth_token = access_token["access_token"]

            ingest_inventory(auth_token, inventory_id, data, helper, url, ew, ocapi_hostname, data_input_name, unique_id)

    helper.log_info(
        f'Finish Inventory ingestion data_input={data_input_name} inventory_id={inventory_id} id={unique_id}'
    )

    return None, None
