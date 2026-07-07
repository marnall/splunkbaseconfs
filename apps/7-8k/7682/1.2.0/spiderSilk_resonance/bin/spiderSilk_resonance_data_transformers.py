import logging
from typing import List

import requests


def threats_data_transformer(logger: logging.Logger, input_data: dict) -> List[dict]:
    """
    Transforms the given threats API data by extracting relevant information
    or removing unnecessary keys from each threat record or enriching data.

    Parameters:
    logger : logging.Logger
        A logger instance for logging debug and error information.
    input_data (dict):
        A dictionary containing the assets API metadata & response data.

        input_data is a Python dictionary object like:
        {
            "api_meta": "<api_meta dict>",
            "api_data": "<[]dict>"
        }

    Returns:
    list[dict]
        A list of transformed threat data dictionaries.
    """
    api_type = "threats"
    api_meta = input_data['api_meta']
    api_data = input_data['api_data']

    api_headers = {"Authorization": f"Bearer {api_meta['secret']}"}
    api_headers.update(api_meta['extra_headers'] if 'headers' in api_meta else {})

    transformed_data = []

    keys_to_remove = ["id", "ip"]
    logger.debug(f"Running threats data transformer for Account {api_meta['account']}: Removing data with keys: "
                 f"{keys_to_remove}")

    for data in api_data:
        # Include account name in data
        data['profile_name'] = api_meta['account']

        try:
            # Remove unwanted data
            for key in keys_to_remove:
                if key in data:
                    del data[key]
        except Exception as e:
            logger.error(f"Error transforming data for resonance {api_type} api data, UUID: {data['uuid']}, Account: "
                         f"{api_meta['account']}. Error :{e}")
            continue

        transformed_data.append(data)

    logger.debug(f"Threats data transformation for Account : {api_meta['account']}: completed")

    return transformed_data


def darkweb_data_transformer(logger: logging.Logger, input_data: dict) -> List[dict]:
    """
    Transforms the given threats API data by extracting relevant information
    or removing unnecessary keys from each threat record or enriching data.

    Parameters:
    logger : logging.Logger
        A logger instance for logging debug and error information.
    input_data (dict):
        A dictionary containing the assets API metadata & response data.

        input_data is a Python dictionary object like:
        {
            "api_meta": "<api_meta dict>",
            "api_data": "<[]dict>"
        }

    Returns:
    list[dict]
        A list of transformed threat data dictionaries.
    """
    api_type = "darkweb"
    api_meta = input_data['api_meta']
    api_data = input_data['api_data']

    api_headers = {"Authorization": f"Bearer {api_meta['secret']}"}
    api_headers.update(api_meta['extra_headers'] if 'headers' in api_meta else {})

    transformed_data = []

    keys_to_keep = ["uuid", "key", "title", "sub_category", "status", "created_at", "leakage_at", "assignee"]
    credential_keys_to_keep = ["URL", "Username", "Application", "policy_validated_password"]

    logger.debug(f"Running darkweb data transformer for Account {api_meta['account']}: Only keeping data with keys:"
                 f" {keys_to_keep}")
    logger.debug(f"Running darkweb data transformer for Account {api_meta['account']}: Enrich data with new "
                 f"information's")

    for data in api_data:
        uuid = data["uuid"]

        # Include account name in data
        enriched_data = {'profile_name': api_meta['account']}

        try:
            # Remove unwanted data
            for key in list(data.keys()):
                if key in keys_to_keep:
                    enriched_data[key] = data[key]

            # Fetch more details for enrichment
            api_url = f"{api_meta['base_url']}/{uuid}"
            response = requests.get(api_url, headers=api_headers, timeout=10)
            response.raise_for_status()
            resp_data = response.json()
            more_details = resp_data['data']

            # Enrich data
            enriched_data['details'] = more_details['details']
            for cred in more_details['credentials']:
                credential = {"note": cred['note']}
                for cred_key in cred['data']:
                    if cred_key in credential_keys_to_keep:
                        credential[cred_key] = cred['data'][cred_key]
                enriched_data['credential'] = credential

                transformed_data.append(enriched_data.copy())

        except Exception as e:
            logger.error(f"Error transforming data for resonance {api_type} api data, UUID: {data['uuid']}, Account: "
                         f"{api_meta['account']}. Error :{e}")
            continue

    logger.debug(f"Darkweb data transformation for Account : {api_meta['account']}: completed")

    return transformed_data


def assets_data_transformer(logger: logging.Logger, input_data: dict) -> List[dict]:
    """
    Transforms the given threats API data by extracting relevant information
    or removing unnecessary keys from each threat record or enriching data.

    Parameters:
    logger (logging.Logger):
        A logger instance for logging debug and error information.
    input_data (dict):
        A dictionary containing the assets API metadata & response data.

        input_data is a Python dictionary object like:
        {
            "api_meta": "<api_meta dict>",
            "api_data": "<[]dict>"
        }

    Returns:
    dict[str, list[dict]]
        A list of transformed threat data dictionaries.
    """
    api_type = "assets"
    api_meta = input_data['api_meta']
    api_data = input_data['api_data']

    api_headers = {"Authorization": f"Bearer {api_meta['secret']}"}
    api_headers.update(api_meta['extra_headers'] if 'headers' in api_meta else {})

    transformed_data = []

    keys_to_remove = ["active_threats", "annotation_label"]
    keys_to_rename = {"asset_id": "uuid"}

    logger.debug(f"Running assets data transformer for Account {api_meta['account']}: Removing data with keys: "
                 f"{keys_to_remove}")
    logger.debug(f"Running assets data transformer for Account {api_meta['account']}: Renaming some data with "
                 f"keys: {keys_to_rename}")

    for data in api_data:
        # Include account name in data
        data['profile_name'] = api_meta['account']

        try:
            # Remove unwanted data
            for key in keys_to_remove:
                if key in data:
                    del data[key]

            # Rename Keys
            for old_key, new_key in keys_to_rename.items():
                if old_key in data:
                    data[new_key] = data.pop(old_key)
        except Exception as e:
            logger.error(f"Error transforming data for resonance {api_type} api data, UUID: {data['uuid']}, Account: "
                         f"{api_meta['account']}. Error :{e}")
            continue

        transformed_data.append(data)

    logger.debug(f"Assets data transformation for Account : {api_meta['account']}: completed")

    return transformed_data
