"""File consisting of helper methods."""

# Handle python 2/3 absolute imports
try:
    import ta_riskiq_passivetotal_declare
except ImportError:
    from . import ta_riskiq_passivetotal_declare
import logging
import logging.handlers
import csv
import io
import os
import six
import copy
import json
import requests
import splunk.entity as entity
import splunk.rest as rest
import collections

try:
    from urllib.parse import quote_plus
except Exception:
    from urllib import quote_plus

from splunk import admin
from splunk.clilib.bundle_paths import make_splunkhome_path
from solnlib import conf_manager
from solnlib.utils import is_true

APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]
APP_LABEL = "RiskIQ PassiveTotal Add-on"
CSV_EXTENSION = ".csv"
CSV_STORAGE_PATH = make_splunkhome_path(
    ["etc", "apps", APP_NAME, "local", "indicators"])

# API Constants
ACCOUNT_ENDPOINT = "/v2/account"
BASE_URL = "https://api.passivetotal.org"
EVENTS_PER_PAGE = 2000
PAGE_LIMIT = 5
DATASETS = ["passivedns", "whois", "certificates", "subdomains",
            "trackers", "components", "hostpairs", "cookies", "services", "osint", "hashes", "tags"]

MAX_WORKER_THREADS = 3
PASSIVETOTAL_SETTINGS_CONF = "ta_riskiq_passivetotal_settings"
COMMON_SOURCETYPE = "riskiq:passivetotal"
API_ERRORS_STANZA = "api_errors"

# Logging configs
LOG_FILE_NAME = 'ta_riskiq_passivetotal_custom_commands.log'
LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
LOG_MAX_BYTES = 25000000
LOG_BACKUP_COUNT = 5
DEFAULT_LOG_LEVEL = logging.INFO
LOG_LEVEL_MAPPING = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'NOTSET': logging.NOTSET,
}


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


def post_message(session_key, severity, message):
    """
    Post a message to splunk's services/messages endpoint.

    :param session_key: Session key used to authenticate rest endpoint
    :param severity: Severity of message info/error/warning
    :param message: Message to show in Messages section

    :return: None
    """
    postargs = {
        'severity': severity,
        'name': APP_NAME,
        'value': "{}: {}".format(APP_LABEL, message)
    }

    rest.simpleRequest('/services/messages',
                       session_key, postargs=postargs)


def setup_logging(
        name='passivetotal', filename=LOG_FILE_NAME, level=DEFAULT_LOG_LEVEL, max_bytes=LOG_MAX_BYTES,
        backup_count=LOG_BACKUP_COUNT, logformat=LOGGING_FORMAT, session_key=None):
    """Build a logger for debugging purposes."""
    if session_key:
        pt_configs = read_conf_file(
            session_key, PASSIVETOTAL_SETTINGS_CONF, stanza="logging")
        level = pt_configs.get('loglevel')
        if not level:
            level = DEFAULT_LOG_LEVEL
        else:
            level = LOG_LEVEL_MAPPING.get(level.upper(), DEFAULT_LOG_LEVEL)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    # Prevent the log messages from being duplicated in the python.log file
    logger.propagate = False

    # Prevent re-adding handlers to the logger object, which can cause duplicate log lines
    log_file_path = make_splunkhome_path(['var', 'log', 'splunk', filename])
    handler_exists = any(
        [True for h in logger.handlers if getattr(h, 'baseFilename', '') == log_file_path])

    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path, mode='a', maxBytes=max_bytes, backupCount=backup_count)
        file_handler.setFormatter(logging.Formatter(logformat))
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

    return logger


def get_pt_config(session_key=None):
    """
    Retrun passivetotal configurations.

    :param conf_file_name: Name of the configuration file
    :param section: Section to read from the configuration
    :return: Dict of parsed configuration section
    """
    if not session_key:
        session_key = GetSessionKey().session_key

    pt_configs = read_conf_file(
        session_key, PASSIVETOTAL_SETTINGS_CONF, stanza="passivetotal_account"
    )
    username = pt_configs.get('passivetotal_username')

    if isinstance(username, six.string_types) and username.strip():
        entities = entity.getEntities(
            ["admin", "passwords"],
            namespace=APP_NAME,
            owner="nobody",
            sessionKey=session_key,
            search=APP_NAME,
            count=-1,
        )
        password = get_password(
            entities, name="passivetotal_account", _type="account")

        return (username, password)
    return (None, None)


def gen_label(item):
    """
    Generate a friendly looking label based on a string.

    :param item: Str value to clean up
    :return: Cleaned up label based on a key
    """
    output = list()
    for idx, chr in enumerate(item):
        if chr.isupper():
            output.append(' ')
        if idx == 0:
            chr = chr.upper()
        output.append(chr)
    return ''.join(output)


def remove_keys(obj, keys=[]):
    """Remove a set of keys from a dict."""
    obj = copy.deepcopy(obj)
    for key in keys:
        obj.pop(key, None)
    return obj


def keep_keys(obj, keys=[]):
    """Keep only given set of keys from a dict."""
    data = dict()
    for key in keys:
        if key in obj:
            data[key] = obj.get(key)
    return data


def create_requests_proxy_dict(session_key=None):
    """
    Create proxy dictionary used in requests module.

    :return: Proxy dict
    """
    proxies = {}
    proxy_settings, proxy_enabled = get_proxy_config(session_key)

    # Create Proxy URL
    proxy_uri = create_proxy_uri(proxy_enabled, proxy_settings)
    if proxy_uri:
        proxies = {"http": proxy_uri, "https": proxy_uri}

    return proxies


def get_proxy_config(session_key=None):
    """
    Give information of proxy if proxy is enabled.

    :return: dictionary having proxy information
    """
    if not session_key:
        session_key = GetSessionKey().session_key

    # Get proxy configurations
    proxy_configuration = read_conf_file(
        session_key, PASSIVETOTAL_SETTINGS_CONF, stanza="proxy"
    )

    entities = entity.getEntities(
        ["admin", "passwords"],
        namespace=APP_NAME,
        owner="nobody",
        sessionKey=session_key,
        search=APP_NAME,
        count=-1,
    )
    return get_proxy_settings(proxy_configuration, entities)


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
        realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(
            APP_NAME, conf_file),
    ).get_conf(conf_file)

    if stanza:
        return conf_file.get(stanza)
    return conf_file.get_all()


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
                proxy_settings["proxy_username"] = proxy_config.get(
                    "proxy_username")
                proxy_settings["proxy_password"] = get_password(
                    entities, name="proxy", _type="proxy"
                )
            except Exception:
                pass

    return proxy_settings, proxy_enabled


def create_requests_proxies_helper(proxy_enabled, proxy_settings):
    """
    Create proxy dictionary used in requests module.

    :param proxy_enabled: True if Proxy config is enabled. False otherwise
    :param proxy_settings: Proxy metadata

    :return: Proxy dict
    """
    proxies = {}
    proxy_uri = create_proxy_uri(proxy_enabled, proxy_settings)
    if proxy_uri:
        proxies = {
            'http': proxy_uri,
            'https': proxy_uri
        }
    return proxies


def get_password(entities, name, _type):
    """
    Give password.

    :param entities: dict which will have clear password
    :param name: name of stanza

    :return: password and certificate key password
    """
    password = ""
    for _, value in list(entities.items()):
        if value["username"].partition("`")[0] == str(name) and not value.get(
            "clear_password", "`"
        ).startswith("`"):
            cred = json.loads(value.get("clear_password", "{}"))
            password = (
                cred.get("passivetotal_password", "") if _type == "account" else cred.get(
                    "proxy_password", "")
            )
            break
    return password


def create_proxy_uri(proxy_enabled, proxy_settings):
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
                requests.compat.quote_plus(
                    str(proxy_settings["proxy_username"])),
                requests.compat.quote_plus(
                    str(proxy_settings["proxy_password"])),
                uri,
            )
        else:
            uri = "{}://{}".format(proxy_settings["proxy_type"], uri)
    return uri


def return_indicators_from_file(csv_file, helper):
    """
    Return list of indicators by reading the csv file.

    :param csv_file: Path to the csv file
    :param helper: BaseModInput Object

    :return: List of indicators
    """
    try:
        # Using io.open as its more safe
        with io.open(csv_file) as f:
            reader = csv.reader(f)
            indicators = list(reader)

        # Filter empty strings
        indicators = list(filter(None, ["".join(x) for x in indicators]))
        indicators = list(set(indicators[1:]))
        return indicators

    except Exception as e:
        helper.log_error("Error reading file {}".format(e))
        return []


def nested_dict_iter(data, prefix=''):
    """
    Convert event to splunk compatible event.

    This is a dict inside a list so we assume something like:
        [{port : <port_1>, proto : <proto_1}, {port : <port_2>, proto : <proto_2}]
    We want something like this for Splunk:
        [{port : [<port_1>, <port_2>]},{proto : [<proto_1>, <proto_2>]}]
    """
    parsed = {}

    def _nested_dict_iter(data_, prefix=''):
        """Return processed indivisual element."""
        if not data_:
            return

        if(isinstance(data_, list)):
            if prefix:
                prefix = prefix + r'{}'
            for item in data_:
                _nested_dict_iter(item, prefix)

        elif(isinstance(data_, dict)):
            if prefix:
                prefix = '{}.'.format(prefix)
            for key, val in data_.items():
                _nested_dict_iter(val, prefix + key)

        else:
            res = parsed.get(prefix)

            if(isinstance(res, list)):
                parsed[prefix].append(data_)
            elif(res is None):
                parsed[prefix] = data_
            else:
                parsed[prefix] = [res, data_]

    _nested_dict_iter(data)
    return parsed
