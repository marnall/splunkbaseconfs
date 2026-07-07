import sys
import os

from requests.utils import requote_uri

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunk.clilib import cli_common
from splunklib import client


from vt_constants import (
    APP_NAME,
    SECRET_REALM,
    SECRET_NAME_API_KEY,
    SECRET_NAME_PROXY_PASSWORD,
    SETTINGS_FILE,
    SETTINGS_FILE_PROXY_STANZA,
    SETTINGS_FILE_GENERAL_STANZA
)
from vt_utils import str_to_bool


def get_api_key(service):
    """
    Fetch the apikey from Splunk storage
    """
    service.namespace = client.namespace(app=APP_NAME, sharing="app")
    api_key = service.storage_passwords[SECRET_REALM + ":" + SECRET_NAME_API_KEY + ":"]

    return api_key.clear_password


def get_proxies(service):
    """
    Load Proxy settings
    """
    proxy_settings = cli_common.getConfStanza(SETTINGS_FILE, SETTINGS_FILE_PROXY_STANZA)

    proxy_enabled = str_to_bool(proxy_settings.get("proxy_enabled", '0'))
    proxy_protocol = proxy_settings.get("proxy_protocol")
    proxy_host = proxy_settings.get("proxy_host")
    proxy_port = proxy_settings.get("proxy_port")
    proxy_require_auth = str_to_bool(proxy_settings.get("proxy_require_auth", '0'))
    proxy_username = proxy_settings.get("proxy_username")

    proxies = {}

    if proxy_enabled and proxy_require_auth:
        service.namespace = client.namespace(app=APP_NAME, sharing="app")
        proxy_password = service.storage_passwords[
            SECRET_REALM + ":" + SECRET_NAME_PROXY_PASSWORD + ":"
        ]

        proxy_auth = f"{requote_uri(proxy_username)}:{requote_uri(proxy_password.clear_password)}"
        proxies['http'] = f"{proxy_protocol}://{proxy_auth}@{proxy_host}:{proxy_port}"
        proxies['https'] = f"{proxy_protocol}://{proxy_auth}@{proxy_host}:{proxy_port}"
    elif proxy_enabled:
        proxies['http'] = f"{proxy_protocol}://{proxy_host}:{proxy_port}"
        proxies['https'] = f"{proxy_protocol}://{proxy_host}:{proxy_port}"
    else:
        proxies = None

    return proxies


def get_proxy(service):
    """
    Load Proxy settings
    """
    proxy_settings = cli_common.getConfStanza(SETTINGS_FILE, SETTINGS_FILE_PROXY_STANZA)

    proxy_enabled = str_to_bool(proxy_settings.get("proxy_enabled", '0'))
    proxy_protocol = proxy_settings.get("proxy_protocol")
    proxy_host = proxy_settings.get("proxy_host")
    proxy_port = proxy_settings.get("proxy_port")
    proxy_require_auth = str_to_bool(proxy_settings.get("proxy_require_auth", '0'))
    proxy_username = proxy_settings.get("proxy_username")

    proxy = None

    if proxy_enabled and proxy_require_auth:
        service.namespace = client.namespace(app=APP_NAME, sharing="app")
        proxy_password = service.storage_passwords[
            SECRET_REALM + ":" + SECRET_NAME_PROXY_PASSWORD + ":"
        ]

        proxy_auth = f"{requote_uri(proxy_username)}:{requote_uri(proxy_password.clear_password)}"
        proxy = f"{proxy_protocol}://{proxy_auth}@{proxy_host}:{proxy_port}"
    elif proxy_enabled:
        proxy = f"{proxy_protocol}://{proxy_host}:{proxy_port}"

    return proxy


def get_fields_custom_prefix(service):
    """
    Load fields_custom_prefix config
    """

    general_settings = cli_common.getConfStanza(SETTINGS_FILE, SETTINGS_FILE_GENERAL_STANZA)
    fields_custom_prefix = general_settings.get("fields_custom_prefix")

    return fields_custom_prefix
