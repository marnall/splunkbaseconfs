import io
import os
import json
import requests
import six.moves.configparser

from splunk.clilib.bundle_paths import make_splunkhome_path


def get_app_version(my_app):
    config, stanza = get_configuration(my_app, 'app.conf', folder='default')
    return '{}-b{}'.format(
        config.get('launcher', 'version'),
        config.get('install', 'build')
    )


def get_configuration(my_app, file, folder="local"):
    conf_parser = six.moves.configparser.ConfigParser()
    conf = os.path.join(make_splunkhome_path(
        ["etc", "apps", my_app, folder, file]))
    stanzas = []
    if os.path.isfile(conf):
        with io.open(conf, 'r', encoding='utf_8_sig') as conffp:
            conf_parser.readfp(conffp)
        stanzas = conf_parser.sections()
    return conf_parser, stanzas


def is_true(val):

    value = str(val).strip().upper()
    if value in ("1", "TRUE", "T", "Y", "YES"):
        return True
    return False


def create_uri(proxy_enabled, global_account_dict):

    uri = None
    if is_true(proxy_enabled) and global_account_dict.get('proxy_url') and global_account_dict.get('proxy_type'):
        uri = global_account_dict['proxy_url']
        if global_account_dict.get('proxy_port'):
            uri = '{}:{}'.format(uri, global_account_dict.get('proxy_port'))
        if global_account_dict.get("proxy_username") and global_account_dict.get(
            "proxy_password"
        ):
            uri = "{}://{}:{}@{}/".format(
                global_account_dict["proxy_type"],
                requests.compat.quote_plus(global_account_dict["proxy_username"]),
                requests.compat.quote_plus(global_account_dict["proxy_password"]), uri,
            )
        else:
            uri = '{}://{}'.format(global_account_dict['proxy_type'], uri)
    return uri


def get_proxy_settings(global_account_dict=None, global_account_name=None, app=None, entities=None):
    '''
    Give proxy uri
    :param global_account_dict: global account dictionary
    :param global_account_name: global account name
    :param app: name of app
    :param entities: dict which will have clear password
    :return: proxy settings
    '''
    proxies = {}
    if not global_account_dict:
        return proxies

    if global_account_dict.get('proxy_username') and entities:
        for _, value in entities.items():
            if value['username'].partition('`')[0] == global_account_name and not value.get('clear_password', '`').startswith('`'):
                cred = json.loads(value.get('clear_password', '{}'))
                global_account_dict['proxy_password'] = cred.get(
                    'proxy_password', '')
                break

    proxy_enabled = global_account_dict.get('proxy_enabled')

    uri = create_uri(proxy_enabled, global_account_dict)

    if uri:
        proxies = {
            'http': uri,
            'https': uri
        }
    return proxies
