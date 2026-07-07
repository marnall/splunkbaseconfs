import os
import json
from solnlib import conf_manager
from splunk.clilib.bundle_paths import make_splunkhome_path

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

APP = __file__.split(os.sep)[-3]
CLIENT_ENDPOINT = "/api/v1/client"
HOSTS_ENDPOINT = "/api/v1/client/{client_id}/host/search"
APPS_ENDPOINT = "/api/v1/client/{client_id}/application/search"
REQUESTS_TIMEOUT = 60
VERIFY_SSL = True
RISKSENSE_SETTINGS_CONF = "ta_risksense_settings"
RISKSENSE_ACCOUNTS_CONF = "ta_risksense_account"


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

def read_conf_file(session_key, conf_file, stanza=None):
    """
    Get conf file content with conf_manager
    :param session_key: Splunk session key
    :param conf_file: conf file name
    :param stanza: If stanza name is present then return only that stanza, otherwise return all stanza
    """
    conf_file = conf_manager.ConfManager(session_key, APP, realm='__REST_CREDENTIAL__#{}#configs/conf-{}'.format(APP, conf_file)).get_conf(conf_file)
    if stanza:
        return conf_file.get(stanza)
    return conf_file.get_all()

def get_proxy_settings(proxy_config, entities):
    '''
    Gives information of proxy if proxy is enabled
    :return: dictionary having proxy information
    '''
    proxy_settings = {}
    proxy_enabled = 0

    if proxy_config.get('proxy_enabled'):
        proxy_enabled = int(proxy_config.get('proxy_enabled'))
        if proxy_enabled:
            proxy_settings['proxy_port'] = proxy_config.get('proxy_port')
            proxy_settings['proxy_url'] = proxy_config.get('proxy_url')
            proxy_settings['proxy_type'] = proxy_config.get('proxy_type')
            try:
                proxy_settings['proxy_username'] = proxy_config.get('proxy_username')
                proxy_settings['proxy_password'] = get_password(entities, name='proxy', type='proxy')
            except:
                pass

    return proxy_settings, proxy_enabled


def get_account_data(session_key, entities, global_account, my_app=APP):
    '''
    Returns Account information

    :param session_key: Session Key used to call rest handlers
    :param entities: Entity Object
    :param global_account: Global Account Name

    '''

    account_config = read_conf_file(session_key, RISKSENSE_ACCOUNTS_CONF)
    account_dict = {}

    for stanza in account_config:
        if str(stanza) == global_account:
            account_dict["platform_url"] = account_config.get(stanza).get('platform_url')
            account_dict["client_id"] = account_config.get(stanza).get('client_id')
            break
    
    account_dict['token'] = get_password(entities, global_account, "account")
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

def make_risksense_url(platform_url, finding_type, client_ids=None):
        '''
        Build API URL from given parameters

        :param platform_url: URL to connect to Risksense Platform.
        :param client_id: Client ID to collect data of.
        :param finding_type: Type of finding hosts / Applications
        '''
        urls = []

        if finding_type == "hosts":
            endpoint = HOSTS_ENDPOINT
        
        elif finding_type == "clients":
            endpoint = CLIENT_ENDPOINT
            return ["https://{url}{endpoint}".format(url=platform_url, endpoint=endpoint)]

        else:
            endpoint = APPS_ENDPOINT

        for client_id in client_ids:    
            client_endpoint = endpoint.format(client_id=client_id)
            url = "https://{url}{endpoint}".format(url=platform_url, endpoint=client_endpoint)
            urls.append(url)

        return urls

def prepare_filters(helper, filters):
        '''
        Prepare request filters 
        [
            {
                "field": "field1",
                "operator": "IN",
                "value": "value1"
            }
        ]

        :param helper: object of BaseModInput class
        :param filters: Filters string i.e. key=value:operator
        '''

        filters_list = []
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
                if helper:
                    helper.log_error("Error while creating request filters {}".format(e))
                raise Exception(e)
        if helper:
            helper.log_debug("Prepared request filters are {}".format(filters_list))
        return filters_list


def prepare_client_event(event):
    new_event = {}
    new_event["client_id"] = event.get("id")
    new_event["client_name"] = event.get("name")
    new_event["rs3"] = event.get("rs3")
    return new_event
