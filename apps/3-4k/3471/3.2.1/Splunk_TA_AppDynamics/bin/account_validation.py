"""
Account credential validation for AppDynamics controller.
Extracted so it can be unit tested without importing REST handler classes.
"""
import requests

from splunktaucclib.rest_handler import error
from ucc_utils import Util
from appdynamics_utils import normalize_controller_url, get_account_name_from_controller_url


def validate_account_credentials(controller_url, client_name, client_secret, session_key, logger=None):
    """
    Validate controller URL and credentials via OAuth and applications API.
    Raises splunktaucclib.rest_handler.error.RestError on failure.
    """
    controller_url = normalize_controller_url(controller_url)
    account_name = get_account_name_from_controller_url(controller_url)

    proxy = Util.get_proxy(session_key)
    request_timeout = Util.get_timeout(session_key)
    verify_ssl = Util.get_verify_ssl(session_key)

    response = requests.post(
        url=f"{controller_url}/controller/api/oauth/access_token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        auth=(client_name, client_secret),
        data={
            "grant_type": "client_credentials",
            "client_id": f"{client_name}@{account_name}",
            "client_secret": client_secret,
        },
        timeout=request_timeout,
        proxies=proxy,
        verify=verify_ssl,
    )
    status = response.status_code
    if logger:
        logger.info("adding status: %s", status)
    if status > 300:
        raise error.RestError(status, "Invalid API Key or Secret for this controller, please verify your credentials.")

    token = response.json()["access_token"]

    response = requests.get(
        url=f"{controller_url}/controller/restui/applicationManagerUiBean/getApplicationsAllTypes",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
        },
        timeout=request_timeout,
        proxies=proxy,
        verify=verify_ssl,
    )
    if response.status_code > 300:
        raise error.RestError(response.status_code, f"Problem with API Key, error trying to list applications: {response.text}")

    applications = response.json()
    all_attributes_none = all(
        value is None or (isinstance(value, list) and len(value) == 0)
        for value in applications.values()
    )
    if all_attributes_none:
        raise error.RestError(500, "Problem with API Key, it has no permissions for any applications")
