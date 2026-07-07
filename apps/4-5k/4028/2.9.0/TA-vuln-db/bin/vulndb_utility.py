import io
import os
import json
from six.moves import configparser as ConfigParser
import requests
from solnlib import conf_manager
from solnlib.server_info import ServerInfo
from splunk.clilib.bundle_paths import make_splunkhome_path

APP_NAME = __file__.split(os.sep)[-3]


def get_splunk_version(helper, session_key):
    """Return the current Splunk Version."""
    try:
        server_info = ServerInfo(session_key)
        helper.log_debug("Splunk version is {}".format(server_info.version))
        return server_info.version
    except Exception as e:
        helper.log_error("Error while fetching Splunk version : {}".format(str(e)))
        return None


def get_conf_file(helper, session_key, conf_file, stanza=None):
    """Read Conf file and return the requested stanza values."""
    try:
        conf_file = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, conf_file),
        ).get_conf(conf_file)
        if stanza:
            return conf_file.get(stanza)
        return conf_file.get_all()
    except Exception as e:
        helper.log_error("Error while fetching conf file content : {}".format(str(e)))
        return None


def get_proxy_settings(my_app, entities):
    """
    Give proxy uri.

    :param my_app: name of app
    :param entities: dict which will have clear password
    :return: proxy settings
    """
    config = ConfigParser.ConfigParser()
    proxy_settings_conf = os.path.join(make_splunkhome_path(
        ["etc", "apps", my_app, "local", "ta_vuln_db_settings.conf"]))
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
                proxy_settings['proxy_type'] = config.get('proxy', 'proxy_type')

                try:
                    proxy_settings['proxy_username'] = config.get('proxy', 'proxy_username')
                    for ent, value in entities.items():
                        if value['username'].partition('`')[0] == 'proxy' and not value['clear_password'].startswith('`'):  # noqa: E501
                            cred = json.loads(value.get('clear_password', '{}'))
                            proxy_settings['proxy_password'] = cred.get('proxy_password', '')
                            break
                except Exception:
                    pass
        uri = None
        if proxy_settings and proxy_settings.get('proxy_url') and proxy_settings.get('proxy_type'):
            uri = proxy_settings['proxy_url']
            if proxy_settings.get('proxy_port'):
                uri = '{}:{}'.format(uri, proxy_settings.get('proxy_port'))
            if proxy_settings.get('proxy_username') and proxy_settings.get('proxy_password'):
                uri = '{}://{}:{}@{}/'.format(
                    proxy_settings['proxy_type'],
                    requests.compat.quote_plus(proxy_settings['proxy_username']),
                    requests.compat.quote_plus(proxy_settings['proxy_password']),
                    uri)
            else:
                uri = '{}://{}'.format(proxy_settings['proxy_type'], uri)
        if uri:
            proxies = {
                'http': uri,
                'https': uri
            }

        return proxies
