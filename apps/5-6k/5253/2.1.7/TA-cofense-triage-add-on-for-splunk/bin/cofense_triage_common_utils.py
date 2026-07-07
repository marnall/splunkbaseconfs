import input_module_cofense_triage  # noqa: F401
import json
import os
from log_manager import setup_logging

from requests.compat import quote_plus

import splunk.rest as rest
from solnlib.credentials import CredentialManager, CredentialNotExistException
from solnlib.utils import is_true


_LOGGER = setup_logging("ta_cofense_triage_common_utils")
APP_NAME = __file__.split(os.sep)[-3]


def get_proxy_clear_password(session_key):
    """
    Get clear password from splunk passwords.conf.

    :return: str/None: proxy password if available else None.
    """
    _LOGGER.debug("Reading proxy password in clear text.")
    try:
        manager = CredentialManager(
            session_key,
            app=APP_NAME,
            realm="__REST_CREDENTIAL__#{0}#{1}".format(
                APP_NAME, "configs/conf-ta_cofense_triage_add_on_for_splunk_settings"
            ),
        )
    except CredentialNotExistException:
        return None
    else:
        _LOGGER.debug("Proxy password found. Returning.")
        return json.loads(manager.get_password("proxy")).get("proxy_password")


def get_proxy_configuration(session_key):
    """
    Get proxy configuration settings.

    :return: proxy configuration dict.
    """
    rest_endpoint = "/servicesNS/nobody/{}/TA_cofense_triage_add_on_for_splunk_settings/proxy".format(APP_NAME)
    _LOGGER.debug("Reading proxy details from REST Endpoint: {}".format(rest_endpoint))

    _, content = rest.simpleRequest(
        rest_endpoint,
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )

    _LOGGER.debug("Returning proxy details.")
    return json.loads(content)["entry"][0]["content"]


def get_proxy_uri(session_key, proxy_settings=None):
    """
    Generate proxy uri from provided configurations.

    :param session_key: Splunk Session Key
    :param proxy_settings: Proxy configuration dict. Defaults to None.
    :return: if proxy configuration available returns uri string else None.
    """
    _LOGGER.debug("Reading proxy configurations.")

    if not proxy_settings:
        proxy_settings = get_proxy_configuration(session_key)

    if proxy_settings.get("proxy_username"):
        proxy_settings["proxy_password"] = get_proxy_clear_password(session_key)

    if all(
        [
            proxy_settings,
            is_true(proxy_settings.get("proxy_enabled")),
            proxy_settings.get("proxy_url"),
            proxy_settings.get("proxy_type"),
        ]
    ):
        _LOGGER.debug("Proxy is enabled. Using proxy server.")
        http_uri = proxy_settings["proxy_url"]

        if proxy_settings.get("proxy_port"):
            http_uri = "{}:{}".format(http_uri, proxy_settings.get("proxy_port"))

        if proxy_settings.get("proxy_username") and proxy_settings.get(
            "proxy_password"
        ):
            http_uri = "{}:{}@{}".format(
                quote_plus(proxy_settings["proxy_username"], safe=""),
                quote_plus(proxy_settings["proxy_password"], safe=""),
                http_uri,
            )

        http_uri = "{}://{}".format(proxy_settings['proxy_type'], http_uri)

        proxy_data = {"http": http_uri, "https": http_uri}

        _LOGGER.info("Returning proxy configurations.")

        return proxy_data
    else:
        _LOGGER.info("Proxy is disabled or not configured. Skipping proxy.")
        return None
