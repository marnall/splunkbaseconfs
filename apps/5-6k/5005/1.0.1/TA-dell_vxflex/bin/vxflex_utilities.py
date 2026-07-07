import logging
from six.moves.urllib.parse import quote
import json
import os

from solnlib import conf_manager
from splunk import entity
from splunk import rest
from splunk import admin

from solnlib.utils import is_true

from logger_manager import setup_logging


APP_NAME = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SETTING_CONF_FILE = 'ta_dell_vxflex_settings'
PROXY_STANZA = 'proxy'
LOGGING_STANZA = 'logging'
VXFLEX_ADDITIONAL_PARAMETERS = 'vxflex_additional_parameters'
VXFLEX_ENDPOINTS = 'vxflex_endpoints'
SYSTEMS_CONF_FILE = 'ta_dell_vxflex_systems'

AUTH_URL = '/api/login'
SYSTEM_ENDPOINT = "/api/types/System/instances"


def get_accounts(session_key):
    """
    Gets all the accounts (systems) configured from SYSTEMS_CONF_FILE conf file
    :param session_key: Splunk session key
    """
    accounts_info = read_conf_file(session_key, SYSTEMS_CONF_FILE)
    return accounts_info


def get_log_level(session_key):
    """
    Retrieves the log_level from SETTING_CONF_FILE conf file
    :param session_key: Splunk session key
    """
    logging_info = read_conf_file(session_key, SETTING_CONF_FILE, LOGGING_STANZA)
    log_level = logging_info.get('loglevel', 'INFO')
    return logging.getLevelName(log_level)


def get_additional_parameters(session_key):
    """
    Retrieves the ssl verification enable/disable from SETTING_CONF_FILE conf file
    :param session_key: Splunk session key
    """
    additional_info = read_conf_file(session_key, SETTING_CONF_FILE, VXFLEX_ADDITIONAL_PARAMETERS)
    ssl_verification = is_true(additional_info.get('ssl_verification', '1'))
    http_scheme = additional_info.get("http_scheme", "https")
    return ssl_verification, http_scheme


def singletonlogger(class_):
    """
    logger object should only be created once for same logger name
    """
    instances = {}
    def getinstance(*args, **kwargs):
        logger_name = args[0]
        if logger_name not in instances:
            instances[logger_name] = class_(*args, **kwargs)
        return instances[logger_name]
    return getinstance

@singletonlogger
class VLogger(object):
    """
    Create singleton logger
    """
    def __init__(self, name, session_key, account_name, input_name=None):
        log_level = get_log_level(session_key)
        self.logger = setup_logging(name, account_name, input_name, log_level)
        self.logger.info("Logger: log level set to {}".format(log_level))

def get_logger(session_key, name, account_name, input_name=None):
    """
    Returns the logger object
    :param session_key: Splunk session key
    :param name: logger name (creates log file with this name in $SPLUNK_HOME/var/log/splunk/ directory)
    """
    return VLogger(name, session_key, account_name, input_name).logger


def get_proxy_uri(session_key, logger):
    """
    Return proxy uri dict
    :param session_key: Splunk session key
    :return: dict object containing proxy uris
    """
    proxy_info_dict = get_proxy_settings(session_key, logger)

    if not proxy_info_dict:
        return None

    # Quote username and password if available
    user_pass = ''
    if proxy_info_dict.get('proxy_username') and proxy_info_dict.get('proxy_password'):
        username = quote(proxy_info_dict['proxy_username'], safe='')
        password = quote(proxy_info_dict['proxy_password'], safe='')
        user_pass = '{user}:{password}@'.format(user=username, password=password)

    # Prepare proxy string
    proxy = '{proxy_type}://{user_pass}{host}:{port}'.format(proxy_type=proxy_info_dict["proxy_type"],
                                                                user_pass=user_pass,
                                                                host=proxy_info_dict['proxy_hostname'],
                                                                port=proxy_info_dict['proxy_port'])
    proxies = {
        'http': proxy,
        'https': proxy,
    }
    return proxies


def get_proxy_settings(session_key, logger):
    """
    Retrieves the proxy settings from SETTING_CONF_FILE conf file
    :param session_key: Splunk session key
    :return: dict obj with proxy configuration, if proxy is enabled
    """
    proxy_info = read_conf_file(session_key, SETTING_CONF_FILE, PROXY_STANZA)
    if is_true(proxy_info.get('proxy_enabled', '0')):
        logger.info("Proxy is enabled.")
        if not proxy_info.get('proxy_port') or not proxy_info.get('proxy_url'):
            logger.warning("Invalid proxy configuration, ignoring proxy settings.")
            return None

        proxy_info_dict = {
            'proxy_hostname': proxy_info.get('proxy_url'),
            'proxy_port': proxy_info.get('proxy_port'),
            'proxy_username': proxy_info.get('proxy_username', ''),
            'proxy_password': CredentialManager(session_key).get_credential('proxy').get('proxy_password', ''),
            'proxy_type': proxy_info.get('proxy_type', 'http')
        }
        return proxy_info_dict
    else:
        logger.info("proxy is not enabled.")

    return None


def read_conf_file(session_key, conf_file, stanza=None):
    """
    Get conf file content with conf_manager
    :param session_key: Splunk session key
    :param conf_file: conf file name
    :param stanza: If stanza name is present then return only that stanza, otherwise return all stanza
    """
    conf_file = conf_manager.ConfManager(session_key, APP_NAME, realm='__REST_CREDENTIAL__#{}#configs/conf-{}'.format(APP_NAME, conf_file)).get_conf(conf_file)
    if stanza:
        return conf_file.get(stanza)
    return conf_file.get_all()


def create_vxflex_input(system_name, stanzas, session_key, logger):
    logger.debug("Creating modular input stanzas.")

    for stanza_name in list(stanzas.keys()):
        # Get all information related to endpoint
        stanza = stanzas.get(stanza_name)
        input_type = stanza.get('input_type')
        
        modular_input_type = "vxflex_os_instance"
        if input_type == "statistics":
            modular_input_type = "vxflex_os_statistics"
        
        input_name = "{}://{}_{}".format(modular_input_type, system_name, stanza.get('input_prefix'))

        # Creating dict for input details
        final_input = {
                    "name": input_name,
                    "index": [stanza.get('index')],
                    "sourcetype": [stanza.get('sourcetype')],
                    "system": [system_name],
                    "method": [stanza.get('method')],
                    "disabled": "1"
                }

        final_input.update({"instances_rest_endpoint": [stanza.get('instance_endpoint')]})
        if stanza.get('statistic_endpoint'):
           final_input.update({"statistics_rest_endpoint": [stanza.get('statistic_endpoint')]})

        if stanza.get('interval'):
            final_input.update({'interval': [stanza.get('interval')]})

        logger.debug("Creating modular input stanza: {}".format(input_name))

        # Using Splunk internal API to create input
        rest.simpleRequest(
            "/servicesNS/nobody/{}/configs/conf-inputs".format(APP_NAME), session_key, postargs=final_input, method='POST', raiseAllErrors=True)
        logger.info("Created modular input stanzas.")

class CredentialManager(object):
    '''
    Credential manager to store and retrieve password
    '''
    def __init__(self, session_key):
        '''
        Init for credential manager
        :param session_key: Splunk session key
        '''
        self.session_key = session_key

    def get_credential(self, username):
        '''
        Searches passwords using username and returns tuple of username and password if credentials are found else tuple of empty string
        :param username: Username used to search credentials.
        :return: username, password
        '''
        # list all credentials
        entities = entity.getEntities(["admin", "passwords"], search=APP_NAME, count=-1, namespace=APP_NAME, owner="nobody",
                                    sessionKey=self.session_key)

        # return first set of credentials
        for _, value in list(entities.items()):
            # if str(value["eai:acl"]["app"]) == APP_NAME and value["username"] == username:
            if value['username'].partition('`')[0] == username and not value.get('clear_password', '`').startswith('`'):
                try:
                    return json.loads(value.get('clear_password', '{}').replace("'", '"'))
                except:
                    return value.get('clear_password', '')

    def store_password(self, username, password):
        '''
        Updates password if password is already stored with given username else create new password.
        :param username: Username to be stored.
        :param password: Password to be stored.
        :return: None
        '''
        old_password = self.get_credential(username)
        username = username + "``splunk_cred_sep``1"

        if old_password:
            postargs = {
                "password": json.dumps(password) if isinstance(password, dict) else password
            }
            username = username.replace(":", r"\:")
            realm = quote(APP_NAME + ":" + username + ":", safe='')

            rest.simpleRequest(
                "/servicesNS/nobody/{}/storage/passwords/{}?output_mode=json".format(APP_NAME, realm),
                self.session_key, postargs=postargs, method='POST', raiseAllErrors=True)

            return True
        else:
            # when there is no existing password
            postargs = {
                "name": username,
                "password": json.dumps(password) if isinstance(password, dict) else password,
                "realm": APP_NAME
            }
            rest.simpleRequest("/servicesNS/nobody/{}/storage/passwords/?output_mode=json".format(APP_NAME),
                                    self.session_key, postargs=postargs, method='POST', raiseAllErrors=True)


class GetSessionKey(admin.MConfigHandler):
    """
    The class is useful to get Splunk session key
    """
    def __init__(self):
        self.session_key = self.getSessionKey()
