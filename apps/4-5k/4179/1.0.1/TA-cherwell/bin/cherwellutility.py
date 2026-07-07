import requests
from splunk.clilib.bundle_paths import make_splunkhome_path
import ConfigParser
import io
import os
import json


def is_true(val):
    value = str(val).strip().upper()
    if value in ("1", "TRUE", "T", "Y", "YES"):
        return True
    return False


def validate_credentials(url_scheme=None, ipaddress=None, username=None, password=None, clientid=None, ssl_verify=None,
                         proxies=None):
    """ This method is used to validate credentials of the Cherwell account.

    :param url_scheme: HTTP scheme
    :param ipaddress: Cherwell instance IP or Hostname
    :param username: Username for the Cherwell account
    :param password: Password for the username
    :param clientid: Client ID for the user
    :param ssl_verify: Cert validation value
    :param proxies: Proxy information
    :return: True/False, message
    """

    url = str(url_scheme) + "://" + str(ipaddress) + "/CherwellApi/token?auth_mode=internal"

    headers = {'Accept': "application/json", 'Content-Type': "application/x-www-form-urlencoded"}

    payload = ({'Accept': "application/json", "grant_type": "password", "client_id": str(clientid),
               "username": str(username), "password": str(password)})

    try:
        response = requests.post(url, headers=headers, data=payload, verify=is_true(ssl_verify), proxies=proxies)
        if response.status_code != 200:
            error = ""
            error_description = ""
            if "error" in response.json():
                error_description = response.json().get("error_description", "")
                error = response.json().get("error", "")
            raise Exception("[api_connection] Validation Failed :Status code is not 200: status_code={}"
                            " error_description:{} error:{}".format(response.status_code, error_description, error))
        else:
            return True, "Authentication Sucessful"
    except requests.exceptions.SSLError as e:
        return False, "Failed to authenticate user {} on {} Exception: {}".format(username, ipaddress, e)
    except Exception as e:
        return False, "Failed to authenticate user {} on {} Exception: {}".format(username, ipaddress, e)


def get_access_token(url_scheme=None, ipaddress=None, username=None, password=None, clientid=None, ssl_verify=None,
                     proxy_uri=None):
    """

    :param url_scheme:
    :param ipaddress:
    :param username:
    :param password:
    :param clientid:
    :param ssl_verify:
    :param proxy_uri:
    :return:
    """

    proxies = None
    if proxy_uri:
        proxies = {
           "http": proxy_uri,
           "https": proxy_uri,
        }

    url = str(url_scheme) + "://" + str(ipaddress) + "/CherwellApi/token?auth_mode=internal"

    headers = {'Accept': "application/json", 'Content-Type': "application/x-www-form-urlencoded"}
    payload = ({'Accept': "application/json", "grant_type": "password", "client_id": str(clientid),
                "username": str(username), "password": str(password)})

    auth_response = requests.post(url, headers=headers, data=payload, verify=is_true(ssl_verify), proxies=proxies)

    if auth_response.status_code != 200:
        raise Exception("[cherwellutility] Failed to authenticate: Status code is not 200 : status_code=%d"
                        % auth_response.status_code)

    return auth_response.json().get('access_token')


def post_api_call_response(url_scheme=None, ipaddress=None, api_endpoint=None, auth_token=None, data=None,
                           clientid=None, ssl_verify=None, proxy_uri=None):
    """

    :param url_scheme:
    :param ipaddress:
    :param api_endpoint:
    :param auth_token:
    :param data:
    :param clientid:
    :param ssl_verify:
    :param proxy_uri:
    :return:
    """

    proxies = None
    if proxy_uri:
        proxies = {
           "http": proxy_uri,
           "https": proxy_uri,
        }

    url = str(url_scheme) + "://" + str(ipaddress) + "/CherwellAPI/api/V1/" + str(api_endpoint)\
        + "?api_key=" + str(clientid)

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json',
               "Authorization": "Bearer " + auth_token}

    response = requests.post(url, data=data, headers=headers, verify=is_true(ssl_verify), proxies=proxies)

    if response.status_code != 200:
        raise Exception("[cherwellutility] Failed rest_call to %s :Status code is not 200 : status_code=%d"
                        % (api_endpoint, response.status_code))

    return response.json()


def get_api_call_response(url_scheme=None, ipaddress=None, api_endpoint=None, auth_token=None, data=None, clientid=None,
                          ssl_verify=None, proxy_uri=None):
    """

    :param url_scheme:
    :param ipaddress:
    :param api_endpoint:
    :param auth_token:
    :param data:
    :param clientid:
    :param ssl_verify:
    :param proxy_uri:
    :return:
    """

    proxies = None
    if proxy_uri:
        proxies = {
           "http": proxy_uri,
           "https": proxy_uri,
        }

    url = str(url_scheme) + "://" + str(ipaddress) + "/CherwellAPI/api/V1/" + str(api_endpoint) + "?api_key=" +\
        str(clientid)

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json',
               "Authorization": "Bearer " + auth_token}

    response = requests.get(url, data=data, headers=headers, verify=is_true(ssl_verify), proxies=proxies)

    if response.status_code != 200:
        raise Exception("[cherwellutility] Failed rest_call to %s :Status code is not 200 : status_code=%d"
                        % (api_endpoint, response.status_code))
    return response.json()


def getProxySettings(my_app, entities):
    """ Give proxy uri

    :param my_app: name of app
    :param entities: dict which will have clear password
    :return: proxy settings
    """

    config = ConfigParser.ConfigParser()
    proxy_settings_conf = os.path.join(make_splunkhome_path(["etc", "apps", my_app, "local",
                                                             "ta_cherwell_settings.conf"]))
    proxies = {}
    if os.path.isfile(proxy_settings_conf):
        with io.open(proxy_settings_conf, 'r', encoding='utf_8_sig') as inputconffp:
            config.readfp(inputconffp)

        proxy_settings = {}

        if config.has_section('proxy'):
            proxy_enabled = int(config.get('proxy', 'proxy_enabled'))
            if proxy_enabled:
                proxy_settings['proxy_port'] = config.get('proxy', 'proxy_port')
                proxy_settings['proxy_url'] = config.get('proxy', 'proxy_url')
                proxy_settings['proxy_username'] = config.get('proxy', 'proxy_username')
                proxy_settings['proxy_type'] = config.get('proxy', 'proxy_type')
                for ent, value in entities.iteritems():
                    if value['username'].partition('`')[0] == 'proxy' and not value['clear_password'].startswith('`'):
                        cred = json.loads(value.get('clear_password', '{}'))
                        proxy_settings['proxy_password'] = cred.get('proxy_password', '')
                        break
        uri = None

        if proxy_settings and proxy_settings.get('proxy_url') and proxy_settings.get('proxy_type'):
            uri = proxy_settings['proxy_url']
            if proxy_settings.get('proxy_port'):
                uri = '{}:{}'.format(uri, proxy_settings.get('proxy_port'))
            if proxy_settings.get('proxy_username') and proxy_settings.get('proxy_password'):
                uri = '{}://{}:{}@{}/'.format(proxy_settings['proxy_type'], proxy_settings['proxy_username'],
                                              proxy_settings['proxy_password'], uri)
            else:
                uri = '{}://{}'.format(proxy_settings['proxy_type'], uri)
        if uri:
            proxies = {
                'http': uri,
                'https': uri
            }
        return proxies
