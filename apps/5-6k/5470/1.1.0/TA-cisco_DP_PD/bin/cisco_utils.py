from future import standard_library
standard_library.install_aliases()
from builtins import str
import six
import json
import requests
import splunk
import os
import splunk.entity as entity
from splunk import admin

try:
    from urllib.parse import quote_plus
except Exception:
    from urllib.parse import quote_plus

from requests.exceptions import RequestException
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from solnlib import conf_manager
try:
    from splunk.clilib import cli_common as cli
except ImportError:
    pass

CISCO_API_VERSION = "v1"
OAUTH_ENDPOINT = "oauth/token"
CP_ENDPOINT = "cp"
REQUESTS_TIMEOUT = 180
VERIFY_SSL = True
APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]
CISCO_SETTINGS_CONF = "ta_cisco_settings"
CISCO_ACCOUNT_CONF = "ta_cisco_account"
CISCO_HOSTNAME = "api.agari.com"

class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()

def is_true(val):
    """
    Check truthy value of the given parameter.

    :param val: Parameter of which truthy value is to be checkeds

    :return: True / False
    """
    value = str(val).strip().upper()
    if value in ("1", "TRUE", "T", "Y", "YES"):
        return True
    return False

def get_verify_flag():
    cfg = cli.getConfStanza('cisco_settings', 'cisco_configs')
    verify = cfg.get('verify', True)
    ca_bundle_path = cfg.get('ca_bundle_path', "")
    if ca_bundle_path.strip()!="":
        if ca_bundle_path != "" and not os.path.exists(ca_bundle_path):
            return True
        return ca_bundle_path
    elif str(verify).lower() in ["t", "true", "1"]:
       return True
    else:
       return False

def read_conf_file(session_key, conf_file, stanza=None):
    """
    Get conf file content with conf_manager.

    :param session_key: Splunk session key
    :param conf_file: conf file name
    :param stanza: If stanza name is present then return only that stanza,
                    otherwise return all stanza
    """
    conf_file = conf_manager.ConfManager(
        session_key,
        APP_NAME,
        realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, conf_file),
    ).get_conf(conf_file)

    if stanza:
        return conf_file.get(stanza)
    return conf_file.get_all()

def create_uri(proxy_enabled, proxy_settings):
    """
    Create proxy url from the given proxy settings.

    :param proxy_enabled: True if Proxy config is enabled. False otherwise
    :param proxy_settings: Proxy metadata

    :return: Proxy URI
    """
    uri = None
    if (
        is_true(proxy_enabled)
        and proxy_settings.get("proxy_url")
        and proxy_settings.get("proxy_type")
    ):
        uri = proxy_settings["proxy_url"]
        if proxy_settings.get("proxy_port"):
            uri = "{}:{}".format(uri, proxy_settings.get("proxy_port"))
        if proxy_settings.get("proxy_username") and proxy_settings.get("proxy_password"):
            uri = "{}://{}:{}@{}/".format(
                proxy_settings["proxy_type"],
                requests.compat.quote_plus(str(proxy_settings["proxy_username"])),
                requests.compat.quote_plus(str(proxy_settings["proxy_password"])),
                uri,
            )
        else:
            uri = "{}://{}".format(proxy_settings["proxy_type"], uri)
    return uri

def get_password(entities, name, type):
    """
    Give password.

    :param entities: dict which will have clear password
    :param name: name of modular input

    :return: password and certificate key password
    """
    password = ""
    for _, value in list(entities.items()):
        if value["username"].partition("`")[0] == str(name) and not value.get(
            "clear_password", "`"
        ).startswith("`"):
            cred = json.loads(value.get("clear_password", "{}"))
            password = (
                cred.get("client_secret", "") if type == "account" else cred.get("proxy_password", "")
            )
            break
    return password

def create_requests_proxies_helper(proxy_enabled, proxy_settings):
    """
    Create proxy dictionary used in requests module.

    :param proxy_enabled: True if Proxy config is enabled. False otherwise
    :param proxy_settings: Proxy metadata

    :return: Proxy dict
    """
    proxies = {}
    proxy_uri = create_uri(proxy_enabled, proxy_settings)
    if proxy_uri:
        proxies = {
            'http': proxy_uri,
            'https': proxy_uri
        }
    return proxies

def get_proxy_settings(proxy_config, entities):
    """
    Give information of proxy if proxy is enabled.

    :return: dictionary having proxy information
    """
    proxy_settings = {}
    proxy_enabled = 0

    if proxy_config.get("proxy_enabled"):
        proxy_enabled = int(proxy_config.get("proxy_enabled"))
        if proxy_enabled:
            proxy_settings["proxy_port"] = proxy_config.get("proxy_port")
            proxy_settings["proxy_url"] = proxy_config.get("proxy_url")
            proxy_settings["proxy_type"] = proxy_config.get("proxy_type")
            try:
                proxy_settings["proxy_username"] = proxy_config.get("proxy_username")
                proxy_settings["proxy_password"] = get_password(
                    entities, name="proxy", type="proxy"
                )
            except Exception:
                pass

    return proxy_settings, proxy_enabled


def get_proxy_config():
    """
    Give information of proxy if proxy is enabled.

    :return: dictionary having proxy information
    """
    # Get proxy configurations
    proxy_configuration = read_conf_file(
        GetSessionKey().session_key, CISCO_SETTINGS_CONF, stanza="proxy"
    )

    entities = entity.getEntities(
        ["admin", "passwords"],
        namespace=APP_NAME,
        owner="nobody",
        sessionKey=GetSessionKey().session_key,
        search=APP_NAME,
        count=-1,
    )
    return get_proxy_settings(proxy_configuration, entities)

def create_requests_proxy_dict():
    """
    Create proxy dictionary used in requests module.

    :return: Proxy dict
    """
    proxies = {}
    proxy_settings, proxy_enabled = get_proxy_config()
    
    # Create Proxy URL
    proxy_uri = create_uri(proxy_enabled, proxy_settings)
    if proxy_uri:
        proxies = {"http": proxy_uri, "https": proxy_uri}

    return proxies

def requests_retry_session(
    retries=3, backoff_factor=0.3, status_forcelist=(500, 429), session=None
):
    """
    Create and return a session object.

    :param retries: Maximum number of retries to attempt
    :param backoff_factor: Backoff factor used to calculate time between retries.
    :param status_forcelist: A tuple containing the response status codes that should trigger a retry.
    :param session: Session object

    :return: Session Object
    """
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def make_cisco_url(platform_url, endpoint, api_version=CISCO_API_VERSION):
    """Create Cisco URL."""
    if not (
        platform_url and endpoint
        and isinstance(endpoint, six.string_types)
        and isinstance(platform_url, six.string_types)
    ):
        return None
    if not (api_version and isinstance(api_version, six.string_types)):
        api_version = CISCO_API_VERSION
    return "https://{}/{}/{}/{}".format(
        platform_url.strip(), api_version.strip(), CP_ENDPOINT, endpoint.strip()
    )