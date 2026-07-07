import ta_cloudknox_declare  # noqa: F401
import json
import splunk.rest as rest

from log_manager import setup_logging
from six.moves.urllib.parse import quote
from splunk.clilib import cli_common as cli
from solnlib.credentials import CredentialManager, CredentialNotExistException
from solnlib.utils import is_true
import traceback


_LOGGER = setup_logging("cloudknox_utils")


def save_ck_credentials(app_name, session_key, cloudknox_access_token):
    """Save new access token to passwords.conf.

    Args:
        app_name (str): Name of the app (package id).
        session_key (str): Splunk session key.
        cloudknox_access_token (str): Newly generated access token
    """
    manager = CredentialManager(
        session_key,
        app=app_name,
        realm="__REST_CREDENTIAL__#{0}#{1}".format(app_name, "configs/conf-ta_cloudknox_settings"),
    )
    manager.set_password("cloudknox_access_token", cloudknox_access_token)


def get_cloudknox_configs():
    """Get unencrypted secret key and access token from passwords.conf.

    Returns:
        dict : dictionary with cloudknox credentials fields and values
    """
    ck_configs = cli.getConfStanza('ta_cloudknox_settings', 'cloudknox_credentials')
    return ck_configs


def get_ck_clear_tokens(app_name, session_key):
    """Get unencrypted secret key and access token from passwords.conf.

    Args:
        app_name (str): Name of the app (package id).
        session_key (str): Splunk session key.

    Returns:
        str, str: Secret key, Access key in clear text
    """
    manager = CredentialManager(
        session_key,
        app=app_name,
        realm="__REST_CREDENTIAL__#{0}#{1}".format(app_name, "configs/conf-ta_cloudknox_settings"),
    )
    secret_key = None
    access_token = None
    try:
        secret_key = json.loads(manager.get_password("cloudknox_credentials")).get("secret_key")
        access_token = manager.get_password("cloudknox_access_token")
    except Exception as e:
        _LOGGER.error(str(e))
    return secret_key, access_token


def get_proxy_clear_password(app_name, session_key):
    """Get clear password from splunk passwords.conf.

    Args:
        app_name (str): Name of the app (package id).
        session_key (str): Splunk session key.

    Returns:
        str/None: proxy password if available else None.
    """
    try:
        manager = CredentialManager(
            session_key,
            app=app_name,
            realm="__REST_CREDENTIAL__#{0}#{1}".format(
                app_name, "configs/conf-ta_cloudknox_settings"
            ),
        )
        return json.loads(manager.get_password("proxy")).get("proxy_password")
    except CredentialNotExistException:
        _LOGGER.warning("Error occurred while getting proxy password.")
        return None
    except Exception:
        _LOGGER.error("Error occurred while getting proxy password: {}".format(traceback.format_exc()))
        return None


def get_proxy_configuration(app_name, session_key):
    """Get proxy configuraton settings.

    Args:
        app_name (str): Name of the app (package id).
        session_key (str): Splunk session key.

    Returns:
        dict: proxxy configuration dict.
    """
    # get proxy configuration
    rest_endpoint = "/servicesNS/nobody/{}/TA_cloudknox_settings/proxy".format(app_name)
    response, content = rest.simpleRequest(
        rest_endpoint,
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )
    return json.loads(content)["entry"][0]["content"]


def get_proxy_uri(app_name, session_key, proxy_settings=None):
    """Generate proxy uri from provided configurations.

    Args:
        app_name (str): Name of the app (package id).
        session_key (str): Splunk session key.
        proxy_settings (dict, optional): Proxy configuration dict. Defaults to None.

    Returns:
        str/None: if proxy configuration available returns uri string else None.
    """
    if not proxy_settings:
        proxy_settings = get_proxy_configuration(app_name, session_key)

    if not(is_true(proxy_settings.get("proxy_enabled"))):
        return None

    if proxy_settings.get("proxy_username"):
        proxy_settings["proxy_password"] = get_proxy_clear_password(app_name, session_key)

    if all(
        [
            proxy_settings,
            is_true(proxy_settings.get("proxy_enabled")),
            proxy_settings.get("proxy_url"),
            proxy_settings.get("proxy_type"),
        ]
    ):
        uri = proxy_settings["proxy_url"]
        if proxy_settings.get("proxy_port"):
            uri = "{}:{}".format(uri, proxy_settings.get("proxy_port"))
        if proxy_settings.get("proxy_username") and proxy_settings.get("proxy_password"):
            uri = "{}://{}:{}@{}".format(
                proxy_settings["proxy_type"],
                quote(proxy_settings["proxy_username"], safe=""),
                quote(proxy_settings["proxy_password"], safe=""),
                uri,
            )
        else:
            uri = "{}://{}".format(proxy_settings["proxy_type"], uri)
        return uri
    else:
        return None
