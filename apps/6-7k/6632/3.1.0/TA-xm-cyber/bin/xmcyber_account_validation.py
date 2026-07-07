"""Module for validating XM Cyber account credentials and connectivity."""
import import_declare_test  # noqa: F401 # isort: skip

import requests
from xmcyber.exceptions import APIKeyError
from xmcyber_constants import (
    PROTOCOL,
    ALL_ENTITIES_ENDPOINT,
    OAUTH_ENDPOINT,
    VERIFY,
    API_REQUEST_TIMEOUT
)
from xmcyber_utils import get_proxy_info


def account_validation_basic(api_key, session_key, base_url, logger):
    """Validate the XM Cyber account using basic authentication.

    This function attempts to connect to the XM Cyber API using the provided API key
    and base URL. It verifies the connection by making a request to the All Entities endpoint.

    Args:
        api_key (str): The API key for authentication.
        session_key (str): The Splunk session key.
        base_url (str): The base URL of the XM Cyber API.
        logger (logging.Logger): Logger object for logging messages.

    Returns:
        dict: The JSON response from the API if successful.
    """
    logger.info(
        "Verifying API key for the basic authication"
    )
    proxy = get_proxy_info(session_key, logger)
    headers = {
        'x-api-key': api_key
    }
    url = f"{PROTOCOL}://{base_url}{ALL_ENTITIES_ENDPOINT}"
    try:
        response = requests.get(url, headers=headers, verify=VERIFY, proxies=proxy, timeout=API_REQUEST_TIMEOUT)
    except requests.exceptions.ProxyError as e:
        logger.error(f"Proxy Error: {e}.")
        raise Exception(
            "Proxy Error occured, Please verify the configured proxy details."
        )
    except requests.exceptions.SSLError as e:
        logger.error(f"SSL Error: {e}.")
        raise Exception(
            "SSL Error occured, Please verify the certificate for provided configuration."
        )
    if response.status_code == 200:
        return response.json()
    elif response.status_code in (401, 419):
        response = response.json()
        msg = (
            f"Unauthorized Error: Please check your API key. Error: {response.get('message')}")
        logger.error(msg)
        raise APIKeyError(msg)
    elif response.status_code == 400:
        resp = response.json()
        logger.error(f"Error occurred from endpoint: {resp.get('message')}.")
        raise Exception("Bad Request.")
    elif response.status_code == 404:
        logger.error("Error occurred from endpoint: Resource not found.")
        raise Exception("Resource not found.")
    elif response.status_code == 429:
        logger.error("Error occurred from endpoint: API rate limit exceeded.")
        raise Exception("API rate limit exceeded.")
    elif response.status_code == 403:
        logger.error("Error occurred from endpoint: Insufficient permission.")
        raise Exception("Insufficient permission.")
    elif response.status_code == 502:
        # This indicates that the base URL is incorrect.
        logger.error("Error occurred from endpoint: Bad Gateway or incorrect base URL.")
        raise APIKeyError(
            f"Error may be due to Bad Gateway or incorrect base URL. Please verify your base URL {base_url}"
        )
    else:
        logger.error(
            f"Error occured from endpoint. Response status code: {response.status_code}."
        )
        raise Exception(
            f"Response status code : {response.status_code}."
        )


def account_validation_oauth(api_key, session_key, base_url, logger):
    """Validate the XM Cyber account using OAuth authentication.

    This function attempts to connect to the XM Cyber API using the provided API key
    and base URL. It verifies the connection by making a request to the OAuth endpoint.

    Args:
        api_key (str): The API key for authentication.
        session_key (str): The Splunk session key.
        base_url (str): The base URL of the XM Cyber API.
        logger (logging.Logger): Logger object for logging messages.

    Returns:
        dict: The JSON response from the API if successful.
    """
    logger.info(
        "Verifying API key for the oauth authication"
    )
    proxy = get_proxy_info(session_key, logger)
    headers = {
        'x-api-key': api_key
    }
    url = f"{PROTOCOL}://{base_url}{OAUTH_ENDPOINT}"
    try:
        response = requests.post(url, headers=headers, verify=VERIFY, proxies=proxy, timeout=API_REQUEST_TIMEOUT)
    except requests.exceptions.ProxyError as e:
        logger.error(f"Proxy Error: {e}.")
        raise Exception(
            "Proxy Error occured, Please verify the configured proxy details."
        )
    except requests.exceptions.SSLError as e:
        logger.error(f"SSL Error: {e}.")
        raise Exception(
            "SSL Error occured, Please verify the certificate for provided configuration."
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        raise Exception(
            f"Error occured while trying to validate the Base URL and API Key: {e}"
        )
    if response.status_code == 200:
        return response.json()
    elif response.status_code in (401, 419):
        response = response.json()
        msg = (
            f"Unauthorized Error: Please check your API key and the Base URL. Error: {response.get('message')}")
        logger.error(msg)
        raise APIKeyError(msg)
    elif response.status_code == 400:
        resp = response.json()
        logger.error(f"Error occurred from endpoint: {resp.get('message')}.")
        raise Exception("Bad Request.")
    elif response.status_code == 404:
        logger.error("Error occurred from endpoint: Resource not found.")
        raise Exception("Resource not found.")
    elif response.status_code == 429:
        logger.error("Error occurred from endpoint: API rate limit exceeded.")
        raise Exception("API rate limit exceeded.")
    elif response.status_code == 403:
        logger.error("Error occurred from endpoint: Insufficient permission.")
        raise Exception("Insufficient permission.")
    else:
        logger.error(
            f"Error occured from endpoint. Response status code: {response.status_code}."
        )
        raise Exception(
            f"Response status code : {response.status_code}."
        )
