import os
import json
import splunk.rest as rest
import sophos_consts

from log_manager import setup_logging
from solnlib import conf_manager
from six.moves.urllib.parse import quote
from splunk.clilib import cli_common as cli
from solnlib.credentials import CredentialManager, CredentialNotExistException
from solnlib.utils import is_true
from filelock import FileLock, Timeout

APP_NAME = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOGGER = setup_logging("sophos_common_utils")


def save_sophos_credentials(app_name, session_key, sophos_access_token):
    """Save new access token to passwords.conf.

    Args:
        app_name (str): Name of the app (package id).
        session_key (str): Splunk session key.
        sophos_access_token (str): Newly generated access token
    """
    manager = CredentialManager(
        session_key,
        app=app_name,
        realm="__REST_CREDENTIAL__#{0}#{1}".format(
            app_name,
            "configs/conf-ta_sophos_central_addon_for_splunk_settings"
        ),
    )
    manager.set_password("sophos_access_token", sophos_access_token)


def read_conf_file(session_key, conf_file, stanza=None):
    """
    Get conf file content with conf_manager
    :param session_key: Splunk session key
    :param conf_file: conf file name
    :param stanza: If stanza name is present then return only that stanza, otherwise return all stanza
    """
    conf_file = conf_manager.ConfManager(
        session_key,
        APP_NAME,
        realm='__REST_CREDENTIAL__#{}#configs/conf-{}'.format(APP_NAME, conf_file)
    ).get_conf(conf_file)
    if stanza:
        return conf_file.get(stanza)
    #Check PR 80 for description
    return conf_file.get_all(only_current_app=True)


def get_proxy_configuration(app_name, session_key):
    """Get proxy configuraton settings.

    Args:
        app_name (str): Name of the app (package id).
        session_key (str): Splunk session key.

    Returns:
        dict: proxxy configuration dict.
    """
    # get proxy configuration
    rest_endpoint = "/servicesNS/nobody/{}/TA_sophos_central_addon_for_splunk_settings/proxy".format(app_name)
    response, content = rest.simpleRequest(
        rest_endpoint,
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )
    return json.loads(content)["entry"][0]["content"]


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
                app_name, "configs/conf-ta_sophos_central_addon_for_splunk_settings"
            ),
        )
    except CredentialNotExistException:
        return None
    else:
        return json.loads(manager.get_password("proxy")).get("proxy_password")


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


def get_sophos_configs():
    """Get unencrypted secret key and access token from passwords.conf.

    Returns:
        dict : dictionary with sophos credentials fields and values
    """
    sophos_configs = cli.getConfStanza('ta_sophos_central_addon_for_splunk_settings', 'additional_parameters')
    return sophos_configs


def get_sophos_clear_tokens(app_name, session_key):
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
        realm="__REST_CREDENTIAL__#{0}#{1}".format(
            app_name,
            "configs/conf-ta_sophos_central_addon_for_splunk_settings"
        ),
    )
    client_secret = None
    access_token = None
    try:
        client_secret = json.loads(manager.get_password("additional_parameters")).get("client_secret")
        access_token = manager.get_password("sophos_access_token")
    except Exception as e:
        _LOGGER.error(str(e))
    return client_secret, access_token


def save_whoami_response(session_key, stanza, conf_file, data):
    """Save details from whoami API into ta_sophos_central_addon_for_splunk_settings.conf

    Args:
        session_key (str): Splunk session key.
        stanza (str): If stanza name from which whoami response will be fetched.
        conf_file (str): conf file name.
        data (dict): actual data which will be ingested under stanza given in parameter.
    """
    conf_file = conf_manager.ConfManager(session_key, APP_NAME, realm='__REST_CREDENTIAL__#{}#configs/conf-{}'.format(
        APP_NAME, conf_file
    )).get_conf(conf_file)
    conf_file.update(stanza, data)


def read_tenants(logger, mod_input_name):
    """To read tenants from tenant_data.json file.

    Args:
        logger (obj): Logger object
        mod_input_name (str): modular input name

    Returns:
        dict: Dictionary of the tenants.
    """
    tenant_file_lock = FileLock(os.path.join(os.path.dirname(__file__), "..", "local", "tenant_data.json.lock"))
    tenant_file = os.path.join(os.path.dirname(__file__), "..", "local", "tenant_data.json")
    bulk_tenants = {}
    try:
        with tenant_file_lock.acquire(
            timeout=sophos_consts.LOCK_TIMEOUT,
            poll_intervall=sophos_consts.LOCK_POLLING_INTERVAL
        ):
            logger.info("{} input has acquired lock on tenant_data.json.lock".format(mod_input_name))
            if os.path.exists(tenant_file):
                with open(tenant_file, "r") as fp:
                    bulk_tenants = json.load(fp)
            else:
                tenant_file_lock.release(force=True)
                logger.info("Could not found tenant_data.json. Please configure tenants input.")
                exit()
        tenant_file_lock.release(force=True)
        logger.info("{} input has released lock on tenant_data.json.lock".format(mod_input_name))
    except Timeout:
        logger.error("Failed to acquire lock on tenants_data.json in given timeout.")
        exit()
    except Exception as exception_for_tenant_read:
        logger.error(
            "Something went wrong while reading tenants. Message={}".format(str(exception_for_tenant_read))
        )
        tenant_file_lock.release(force=True)
        exit()
    return bulk_tenants

def get_sophos_config_params(session_key):
    """Get additional_parameters stanza from ta_sophos_central_addon_for_splunk_settings.conf
       which is basically a who am i API response.

    Args:
        session_key (str): Splunk session key.
    """
    return read_conf_file(session_key, "ta_sophos_central_addon_for_splunk_settings", "additional_parameters")

def delete_stanza(session_key, conf_file, stanza_name):
    """Delete stanza.
    :param session_key: Splunk session key
    :param conf_file: conf file name
    :param stanza_name: Stanza to delete
    """
    conf_file = conf_manager.ConfManager(
        session_key,
        APP_NAME,
        realm='__REST_CREDENTIAL__#{}#configs/conf-{}'.format(APP_NAME, conf_file)
    ).get_conf(conf_file)
    conf_file.delete(stanza_name)
