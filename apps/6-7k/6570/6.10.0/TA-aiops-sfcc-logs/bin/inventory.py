import requests

from re import match
from json import loads
from datetime import datetime
from functools import reduce
from collections import deque


def urljoin(*args):
    """
    Joins given arguments into an url. Trailing but not leading slashes are
    stripped for each argument.
    """

    return "/".join(map(lambda x: str(x).rstrip('/'), args))


def get_inventory_list_by_id(
    ocapi_url,
    inventory_id,
    token
):
    response = requests.get(
        urljoin(
            ocapi_url,
            "inventory_lists",
            inventory_id
        ),
        headers={"Authorization": f"Bearer {token}"},
        timeout=60
    )
    response.raise_for_status()
    content = response.json()

    return content


def get_product_inventory_records(
    ocapi_url,
    inventory_id,
    token
):
    response = requests.get(
        urljoin(
            ocapi_url,
            "inventory_lists",
            inventory_id,
            "product_inventory_records"
        ),
        headers={"Authorization": f"Bearer {token}"},
        params={"count": 200},
        timeout=60
    )
    response.raise_for_status()
    content = response.json()

    return content


def get_product_inventory_by_id(
    ocapi_url,
    inventory_id,
    product_id,
    token
):
    response = requests.get(
        urljoin(
            ocapi_url,
            "inventory_lists",
            inventory_id,
            "product_inventory_records",
            product_id
        ),
        headers={"Authorization": f"Bearer {token}"},
        timeout=60
    )
    response.raise_for_status()
    content = response.json()

    return content


def deep_get(dictionary, keys, default=None):
    return reduce(
        lambda d, key: d.get(key, default) if isinstance(d, dict) else default, keys.split("."),
        dictionary
    )


def is_sfcc_ocapi_data_empty(data):
    if "total" not in data or "hits" not in data:
        return True

    if not data['total'] or not data['hits'] or not len(data['hits']):
        return True

    return False


def has_next(data):
    return "next" in data


def paginate(data, access_token, helper, auth_func):
    page = 0
    total = data['total']
    count = len(data['data'])
    next_url = data['next']
    token = access_token["access_token"]

    with requests.Session() as requests_session:
        while True:
            datetime_now = datetime.now()
            token_expiry_minutes_diff = (datetime_now - access_token["expires_datetime"]).total_seconds() / 60.0

            if datetime.now() >= access_token["expires_datetime"] or token_expiry_minutes_diff >= 27:
                helper.log_info(
                    f'[Inventory] Renewing OCAPI Access Token'
                )
                access_token = auth_func(helper)
                token = access_token["access_token"]
                helper.log_info(
                    f'[Inventory] Successfully renewed OCAPI Access Token'
                )

            if match(r'^https://', next_url) is None:
                raise ValueError(f'[Inventory] Insecure URL url={next_url}')

            helper.log_info(
                f'[Inventory] Fetching Next Page url={next_url} page_count={page}'
            )

            response = requests_session.get(next_url, headers={"Authorization": f"Bearer {token}"},)
            response_data = response.json()
            total = response_data.get('total', -1)
            count += len(response_data['data'])
            yield response_data["data"]

            if (total and count >= total) or 'next' not in response_data:
                helper.log_info(
                    f'[Inventory] StopIteration: total={total} count={count} page={page}'
                )
                break
            page +=1
            next_url = response_data["next"]

    return None


def get_product_inventory_state(inventory_id, product_inventory, helper):
    try:
        state = helper.get_check_point(
            f"{inventory_id}_{product_inventory['product_id']}"
        )

        if not state:
            return None

        if isinstance(state, dict):
            return state

        state_parsed = loads(state)

        return state_parsed
    except KeyError as keyerr_exc:
        helper.log_error(f"Cannot find key data={product_inventory}")

        raise keyerr_exc
    except Exception as exc:
        raise exc


def is_product_inventory_state_changed(current_state, previous_state):
    return current_state != previous_state.get("resource_state")


def get_inventory_products_ids(inventory_id, data, helper):
    products_ids = deque([])
    for product_inventory in data:
        product_inventory_state = get_product_inventory_state(inventory_id, product_inventory, helper)
        if not product_inventory_state:
            products_ids.append(product_inventory.get("product_id"))
        elif product_inventory_state and is_product_inventory_state_changed(
            product_inventory.get("_resource_state"),
            product_inventory_state
        ):
            helper.log_info(f"[Inventory] Product Inventory state - [{product_inventory_state}]")
            helper.log_debug(
                f"Product ID [{product_inventory.get('product_id')}] inventory changed"
            )
            products_ids.append(product_inventory.get("product_id"))
        else:
            helper.log_debug(
                f"Product ID [{product_inventory.get('product_id')}] inventory not changed"
            )


    return products_ids


def get_product_inventory_details_records(url, access_token, inventory_id, products_ids, helper):
    products_inventories_events = deque([])
    for product_id in products_ids:
        helper.log_debug(f"Fetching Inventory for Product ID [{product_id}]...")
        product_inventory = get_product_inventory_by_id(url, inventory_id, product_id, access_token)
        products_inventories_events.append(product_inventory)

    return products_inventories_events


def transform_product_inventory_data(product_inventory):
    return {
        "list_id": product_inventory.get("inventory_list_id"),
        "product_id": product_inventory.get("product_id"),
        "last_modified": product_inventory.get("last_modified"),
        "allocation": product_inventory.get("allocation").get("amount") if "allocation" in product_inventory else 0,
        "preorder_backorder_allocation": product_inventory.get("pre_order_back_order_allocation", 0),
        "ats": product_inventory.get("ats"),
        "on_order": product_inventory.get("quantity_on_order"),
        "turnover": product_inventory.get("inventory_turnover"),
    }
