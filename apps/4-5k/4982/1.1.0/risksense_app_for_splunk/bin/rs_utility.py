# encoding utf-8
"""
rs_utility.py
Helper file containing useful methods
"""
import rs_declare
import json
import logging
import re
import os
import io

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from six.moves.configparser import ConfigParser

import splunk.entity as entity
import splunk.rest
from splunk.clilib.bundle_paths import make_splunkhome_path

TA_NAME = "TA-risksense"
HOSTS_ENDPOINT = "/api/v1/client/{client_id}/hostFinding/search"
APPS_ENDPOINT = "/api/v1/client/{client_id}/applicationFinding/search"
REQUESTS_TIMEOUT = 60
VERIFY_SSL = True


def validate_client_and_asset_id(name, id):
    """
    Checks if the given parameter is a non-negative integer or not

    :param name: Client Id OR Asset Id
    :param id: Client Id or Asset Id
    """
    if not id and name == "asset_id":
        return
    try:
        id = int(id)
        if id < 0:
            raise Exception("Negative {} found".format(name))
    except Exception as e:
        raise Exception("{} must be a non-negative integer. Error -> {}".format(name, e))

def validate_severity(severity):
    """
    Validates if the severity value is among the allowed values only

    :param severity: Severity value
    """

    if severity not in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "TOTAL"]:
        raise Exception("Severity must be a from [ CRITICAL | HIGH | MEDIUM | LOW | INFO | TOTAL]")

def validate_asset_type(asset_type):
    """
    Validates if the asset type value is among the allowed values only

    :param asset_type: Asset Type
    """

    if asset_type not in ["HOSTFINDINGS", "APPLICATIONFINDINGS"]:
        raise Exception("Asset type must be from [ hostFindings | applicationFindings ]")

def validate_asset_names(host, app):
    """
    Validates if hostname and appname are both empty or not
    
    :param host: Hostname
    :param app: Application Name
    """
    if not host and not app:
        raise Exception("Please provide Hostname or Application Name.")

def validate_operator(operator):
    """
    Validates if the given operator is present in allowed list of operators

    :param operator: Operator string
    """

    if operator not in ("EXACT", "WILDCARD"):
        raise Exception("Only EXACT/WILDCARD is allowed in operator. To provide custom filters use 'filters' argument.")
    

def validate_filters(filters):
    """
    Validates the custom filters

    :param filters: Filters in form of field1=value1:OPERATOR1
    """
    if not filters:
        return
    if not re.match(r"^([a-zA-Z0-9_-]+=[^;]+:[a-zA-Z]+;)*([a-zA-Z0-9_-]+=[^;]+:[a-zA-Z]+)+$", filters):
        raise Exception("Filters must be in the form of field1=value1:OPERATOR1;field2=value2:OPERATOR2...")

def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 429),
    session=None
):
    """
    Create and return a session object
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
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def is_true(val):
    """
    Check truthy value of the given parameter
    :param val: Parameter of which truthy value is to be checked

    :return: True / False
    """
    value = str(val).strip().upper()
    if value in ("1", "TRUE", "T", "Y", "YES"):
        return True
    return False


def create_uri(proxy_enabled, proxy_settings):
    """
    Creates proxy url from the given proxy settings
    :param proxy_enabled: True if Proxy config is enabled. False otherwise
    :param proxy_settings: Proxy metadata

    :return: Proxy URI
    """
    uri = None
    if is_true(proxy_enabled) and proxy_settings.get('proxy_url') and proxy_settings.get('proxy_type'):
        uri = proxy_settings['proxy_url']
        if proxy_settings.get('proxy_port'):
            uri = '{}:{}'.format(uri, proxy_settings.get('proxy_port'))
        if proxy_settings.get('proxy_username') and proxy_settings.get('proxy_password'):
            uri = '{}://{}:{}@{}/'.format(proxy_settings['proxy_type'],
                                          requests.compat.quote_plus(str(proxy_settings['proxy_username'])),
                                          requests.compat.quote_plus(str(proxy_settings['proxy_password'])), uri)
        else:
            uri = '{}://{}'.format(proxy_settings['proxy_type'], uri)
    return uri


def create_requests_proxy_dict(proxy_enabled, proxy_settings):
    """
    Creates proxy dictionary used in requests module
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

def get_proxy_settings(entities):
        '''
        Gives information of proxy if proxy is enabled
        :return: dictionary having proxy information
        '''

        config = ConfigParser()
        proxy_settings_conf = os.path.join(make_splunkhome_path(
            ["etc", "apps", TA_NAME, "local", "ta_risksense_settings.conf"]))
        default_proxy_settings_conf = os.path.join(make_splunkhome_path(
            ["etc", "apps", TA_NAME, "default", "ta_risksense_settings.conf"]))
        proxy_settings = {}
        proxy_enabled = 0

        # Read from default folder if local is not available
        if not os.path.isfile(proxy_settings_conf):
            proxy_settings_conf = default_proxy_settings_conf

        if os.path.isfile(proxy_settings_conf):
            # Parse the conf file
            with io.open(proxy_settings_conf, 'r', encoding='utf_8_sig') as inputconffp:
                config.readfp(inputconffp)
            if config.has_section('proxy') and config.has_option('proxy', 'proxy_enabled'):
                proxy_enabled = int(config.get('proxy', 'proxy_enabled'))
                if proxy_enabled:
                    proxy_settings['proxy_port'] = config.get(
                        'proxy', 'proxy_port')
                    proxy_settings['proxy_url'] = config.get(
                        'proxy', 'proxy_url')
                    proxy_settings['proxy_type'] = config.get(
                        'proxy', 'proxy_type')
                    try:
                        proxy_settings['proxy_username'] = config.get(
                            'proxy', 'proxy_username')
                        proxy_settings['proxy_password'] = ''
                        for _, value in list(entities.items()):
                            if value['username'].partition('`')[0] == 'proxy' and not value['clear_password'].startswith('`'):
                                cred = json.loads(
                                    value.get('clear_password', '{}'))
                                proxy_settings['proxy_password'] = cred.get(
                                    'proxy_password', '')
                                break
                    except:
                        pass
        return proxy_enabled, proxy_settings

def get_configuration(file, folder="local", my_app=TA_NAME):
    """
    Returns the config object and stanzas of a given conf file
    :param file: Name of the conf file
    :param folder: Folder where the file resides
    :param my_app: App context of the file

    :return: Config_Parser Object, Stanzas
    """

    conf_parser = ConfigParser()
    conf = os.path.join(make_splunkhome_path(
        ["etc", "apps", my_app, folder, file]))
    default_conf  = os.path.join(make_splunkhome_path(
        ["etc", "apps", my_app, "default", file]))
    stanzas = []

    # Read the default folder if local is not available
    if not os.path.isfile(conf):
        conf = default_conf

    if os.path.isfile(conf):
        with io.open(conf, 'r', encoding='utf_8_sig') as conffp:
            conf_parser.readfp(conffp)
        stanzas = conf_parser.sections()
    return conf_parser, stanzas

def get_account_data(client_id, my_app=TA_NAME):
    """
    Fetches Global Account information for the given client_id
    :param client_id: Client id to search for
    :param my_app: App Context

    :return: Global Account dict
    """

    account_config, account_stanzas = get_configuration("ta_risksense_account.conf")
    account_dict = {}

    for stanza in account_stanzas:
        clients = account_config.get(stanza, 'client_id')
        if client_id in clients:
            account_dict["stanza"] = str(stanza)
            account_dict["platform_url"] = account_config.get(stanza, 'platform_url')
            break
    return account_dict

def get_password(entities, name, type):
    '''
    Give password
    :param entities: dict which will have clear password
    :param name: name of modular input
    :return: password and certificate key password
    '''
    password = ''
    for _, value in list(entities.items()):
        if value['username'].partition('`')[0] == str(name) and not value.get('clear_password', '`').startswith('`'):
            cred = json.loads(value.get('clear_password', '{}'))
            password = cred.get('token', '') if type == "account" else cred.get('proxy_password', '')
            break
    return password

def prepare_filters(logger, severity, asset_id, asset_type, host_name, app_name, operator, filters):
        '''
        Prepare request filters 
        [
            {
                "field": "field1",
                "operator": "IN",
                "value": "value1"
            }
        ]

        :param logger: Logger object
        :param severity: Severity associated with the asset
        :param asset_id: hostId or application.id
        :param asset_type: HOSTFINDINGS / APPLICATIONFINDINGS
        :param host_name: Hostname
        :param app_name: Application Name
        :param operator: Operator string
        :param filters: Filters string i.e. key=value:operator

        :return : Array of Filters
        '''
        filters_list = prepare_severity_filter(severity, asset_id, asset_type, host_name, app_name, operator)
        if filters:

            try:
                filters = filters.split(";")
                for filter in filters:
                    key_value, operator = filter.rsplit(":", 1)
                    key, value = key_value.split("=", 1)
                    field_filter = {
                        "field": key,
                        "operator": operator,
                        "value": value
                    }
                    filters_list.append(field_filter)

            except Exception as e:
                logger.error("Error while creating request filters {}".format(e))
                raise Exception(e)

        logger.info("Prepared request filters are {}".format(filters_list))
        return filters_list

def prepare_severity_filter(severity, asset_id, asset_type, host, app, operator):
    """
    Prepares severity and asset specific filters

    :param severity: Severity associated with the asset
    :param asset_id: hostId or application.id
    :param asset_type: HOSTFINDINGS / APPLICATIONFINDINGS
    :param host: Hostname
    :param app: Application Name
    :param operator: Operator string

    :return: Array of Filters
    """
    filters = []

    severity_filter = {"operator": "EXACT"}

    asset_filter = {"operator": "EXACT"}

    generic_filter = {"field": "generic_state", "exclusive": "false", "operator": "EXACT", "value": "Open"}
    
    if host:
        host_filter = {"field": "hostName", "operator": "EXACT", "value": host.strip()}
        if operator:
            host_filter["operator"] = operator
        filters.append(host_filter)
    
    if app:
        app_filter = {"field": "application.name", "operator": "EXACT", "value": app.strip()}
        if operator:
            app_filter["operator"] = operator
        filters.append(app_filter)

    if asset_type == "HOSTFINDINGS":
        fieldname = "hostId"
    else:
        fieldname = "application.id"
    
    severity_filter["field"] = "severity_group"
    severity_filter["value"] = severity

    asset_filter["field"] = fieldname
    asset_filter["value"] = asset_id

    if severity and severity!= "TOTAL":
        filters.append(severity_filter)

    if asset_id:
        filters.append(asset_filter)

    filters.append(generic_filter)
    return filters

def make_risksense_url(platform_url, finding_type, client_id):
    '''
    Build API URL from given parameters

    :param platform_url: URL to connect to RiskSense Platform.
    :param client_id: Client ID to collect data of.
    :param finding_type: Type of finding hosts / Applications
    '''

    if finding_type == "hostFindings":
        endpoint = HOSTS_ENDPOINT

    else:
        endpoint = APPS_ENDPOINT

    client_endpoint = endpoint.format(client_id=client_id)
    url = "https://{url}{endpoint}".format(url=platform_url, endpoint=client_endpoint)

    return url

def get_log_level(session_key):
    """
    Returns the log level from the RiskSense Addon config

    :param session_key: Session Key to authencticate Rest request

    :return: log level
    """
    # Get configuration file from the helper method defined in utility
    conf, sections = get_configuration('ta_risksense_settings')
    level = "INFO"

    if not sections:
        return level

    # Get logging stanza from the settings
    logging_config = conf.get("logging", {})
    logging_level = logging_config.get("loglevel", 'INFO')
    if logging_level == 'INFO':
        level = logging.INFO
    elif logging_level == 'DEBUG':
        level = logging.DEBUG
    elif logging_level == 'WARNING':
        level = logging.WARNING
    elif logging_level == 'ERROR':
        level = logging.ERROR
    elif logging_level == 'CRITICAL':
        level = logging.CRITICAL

    return level

def setup_logger(logger=None, log_format='%(asctime)s log_level=%(levelname)s, pid=%(process)d, tid=%(threadName)s, func_name=%(funcName)s, code_line_no=%(lineno)d | ',
                 level=logging.INFO, logger_name="risksense_get_findings", session_key=None, log_context='risksense_app_for_splunk'):
    if logger is None:
        logger = logging.getLogger(logger_name)
    
    # Get the logging level
    level = get_log_level(session_key)

    # Prevent the log messages from being duplicated in the python.log file
    logger.propagate = False
    logger.setLevel(level)

    log_name = logger_name + '.log'
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(
        ['var', 'log', 'splunk', log_name]), maxBytes=2500000, backupCount=5)
    
    # Adding the source of the logs to the log format
    log_format = log_format + '[{log_context}] %(message)s'.format(log_context=log_context)
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)

    logger.handlers = []
    logger.addHandler(file_handler)

    return logger

def get_account_details(session_key, logger, client_id):
    """
    Returns the API token configured by the user from the Splunk enpoint
    :param session_key: Session Key to authencticate Rest request
    :param logger: Logger Object
    :param client_id: Client Id corresponding to global account

    :return: API Token
    """
    try:
        # Get configuration file from the helper method defined in utility
        entities = entity.getEntities(['admin', 'passwords'], namespace=TA_NAME,
                                            owner='nobody', sessionKey=session_key, search=TA_NAME, count=-1)
        
        global_account = get_account_data(client_id)
        api_key_stanza = global_account.get("stanza")
        
        api_key = get_password(entities, api_key_stanza, "account")
        
        if not api_key:
            message = "No API Token found for the given client_id"
            make_error_message(message, session_key, logger)
            raise Exception(message)

        return api_key, global_account.get("platform_url")

    except Exception as e:
        msg = "Error while fetching account details. Please check RiskSense Addon Configuration. Cause -> {}".format(e)
        logger.error(msg)
        raise Exception(msg)

def get_proxy(session_key, logger):
    """
    Get Proxy settings
    :param session_key: Session Key to authencticate Rest request
    :param logger: Logger Object

    return: Proxy dict
    """
    try:
        entities = entity.getEntities(['admin', 'passwords'], namespace=TA_NAME,
                                            owner='nobody', sessionKey=session_key, search=TA_NAME, count=-1)
        
        proxy_enabled, proxy_settings = get_proxy_settings(entities)

        proxies = create_requests_proxy_dict(proxy_enabled, proxy_settings)

        return proxies

    except Exception as e:
        msg = "Error while getting proxy settings. Make sure you have installed and configured RiskSense Addon for Splunk."
        raise Exception(msg)
        
def make_error_message(message, session_key, logger):
    """
    Generates Splunk Error Message
    :param message:
    :param session_key:
    :param filename:
    :return: error message
    """
    try:
        splunk.rest.simpleRequest(
            '/services/messages/new',
            postargs={'name': TA_NAME, 'value': '%s' % (message),
                    'severity': 'error'}, method='POST', sessionKey=session_key
        )
    except Exception as e:
        logger.error("Error occurred while generating error message for Splunk, Error: {}".format(str(e)))
    