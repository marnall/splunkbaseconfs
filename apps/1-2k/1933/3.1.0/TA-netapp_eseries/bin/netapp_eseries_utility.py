import os  # noqa:E902
import io
import re
import json
import requests
import six.moves.configparser
import splunk.rest as rest
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.clilib import cli_common as cli
from splunk.clilib.control_exceptions import ParsingError


def registerArray(ip1, ip2, register_password, netappconnection):
    """Register Array."""
    request_data = {
        "controllerAddresses": [
            str(ip1), str(ip2)
        ],
        "validate": "true",
        "password": register_password
    }
    response = netappconnection.postEndpoint(json.dumps(request_data))
    if not response:
        raise Exception(
            "Unable to register the array! Please provide valid password.")
    array_id = response.get('id')
    return array_id


def monitorArray(helper, ew, index, system_id, netappconnection):
    """Monitor Array."""
    source = "ESeries-" + system_id
    host = system_id
    endpoints = ["graph", "analysed-volume-statistics", "analysed-drive-statistics", "mel-events", "failures",
                 "analysed-controller-statistics", "analysed-interface-statistics"]

    for endpoint in endpoints:
        if endpoint in ["analysed-volume-statistics", "analysed-drive-statistics", "analysed-controller-statistics",
                        "analysed-interface-statistics"]:
            sourcetype = "eseries:" + endpoint.split('-')[1] + "-stats"
        else:
            sourcetype = "eseries:" + endpoint
        stats_data = netappconnection.getEndpoint(system_id, endpoint)
        if not stats_data:
            continue
        if endpoint == "graph":
            event = helper.new_event(data=json.dumps(stats_data), host=host, source=source, sourcetype=sourcetype,
                                     index=index, unbroken=True)
            ew.write_event(event)
        else:
            for data in stats_data:
                event = helper.new_event(data=json.dumps(data), host=host, source=source, sourcetype=sourcetype,
                                         index=index, unbroken=True)
                ew.write_event(event)

    folder_data = netappconnection.getFolderData("folders")
    for data in folder_data:
        event = helper.new_event(data=json.dumps(data), host=host, source=source, sourcetype="eseries:webproxy",
                                 index=index, unbroken=True)
        ew.write_event(event)


def getProxySettings(my_app, entities):
    """
    Form Proxy URI.

    :param my_app: name of app
    :param entities: dict which will have clear password
    :return: proxy settings
    """
    config = six.moves.configparser.ConfigParser()
    proxy_settings_conf = os.path.join(make_splunkhome_path(["etc", "apps", my_app, "local",
                                                             "ta_netapp_eseries_settings.conf"]))
    proxies = {
        'http': None,
        'https': None
    }
    if os.path.isfile(proxy_settings_conf):
        with io.open(proxy_settings_conf, 'r', encoding='utf_8_sig') as inputconffp:
            config.readfp(inputconffp)
        proxy_settings = {}
        if config.has_section('proxy'):
            proxy_enabled = int(config.get('proxy', 'proxy_enabled'))
            if proxy_enabled:
                proxy_settings['proxy_port'] = config.get(
                    'proxy', 'proxy_port')
                proxy_settings['proxy_url'] = config.get('proxy', 'proxy_url')
                proxy_settings['proxy_username'] = config.get(
                    'proxy', 'proxy_username')
                proxy_settings['proxy_type'] = config.get(
                    'proxy', 'proxy_type')
                for ent, value in entities.items():
                    if value['username'].partition('`')[0] == 'proxy' and not value['clear_password'].startswith('`'):
                        cred = json.loads(value.get('clear_password', '{}'))
                        proxy_settings['proxy_password'] = cred.get(
                            'proxy_password', '')
                        break
        uri = None
        if proxy_settings and proxy_settings.get('proxy_url') and proxy_settings.get('proxy_type'):
            uri = proxy_settings['proxy_url']
            if proxy_settings.get('proxy_port'):
                uri = '{}:{}'.format(uri, proxy_settings.get('proxy_port'))
            if proxy_settings.get('proxy_username') and proxy_settings.get('proxy_password'):
                proxy_username = requests.compat.quote_plus(str(proxy_settings.get('proxy_username')), safe="")
                proxy_password = requests.compat.quote_plus(str(proxy_settings.get('proxy_password')), safe="")
                uri = '{}://{}:{}@{}/'.format(proxy_settings['proxy_type'], proxy_username,
                                              proxy_password, uri)
            else:
                uri = '{}://{}'.format(proxy_settings['proxy_type'], uri)

        proxies = {
            'http': uri,
            'https': uri
        }

    return proxies


def getPassword(entities, name):
    """
    Give password.

    :param entities: dict which will have clear password
    :param name: name of modular input
    :return: password and certificate key password
    """
    password = ''
    for ent, value in entities.items():
        if value['username'].partition('`')[0] == str(name) and not value.get('clear_password', '`').startswith('`'):
            cred = json.loads(value.get('clear_password', '{}'))
            password = cred.get('password', '')
            break
    return password


def validateIp(ip):
    """
    Validate IP address.

    :param ip: ip address
    :return: boolean if ip is valid or not
    """
    valid_ip4 = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]\
|25[0-5])$"
    valid_ip6 = "^((([0 - 9a - fA - F]{1, 4}:){7, 7}[0-9a-fA-F]{1, 4} | ([0-9a-fA-F]{1, 4}:){1, 7}: | \
([0 - 9a - fA - F]{1, 4}:){1, 6}:[0 - 9a - fA - F]{1, 4} | ([0 - 9a - fA - F]{1, 4}:){1, 5}\
(:[0 - 9a - fA - F]{1, 4}){1, 2} | ([0 - 9a - fA - F]{1, 4}:)\
{1, 4}(:[0 - 9a - fA - F]{1, 4}){1, 3} | ([0 - 9a - fA - F]{1, 4}:)\
{1, 3}(:[0 - 9a - fA - F]{1, 4}){1, 4} | ([0 - 9a - fA - F]{1, 4}:){1, 2}(:[0 - 9a - fA - F]\
{1, 4}){1, 5} | [0 - 9a - fA - F]\
{1, 4}:((:[0-9a-fA-F]{1, 4}){1, 6}) |:((:[0-9a-fA-F]{1, 4}){1, 7} |:) | fe80:(:[0-9a-fA-F]{0, 4})\
{0, 4} % [0 - 9a - zA - Z]{1, } |::(ffff(:0{1, 4})\
{0, 1}:){0, 1}((25[0 - 5] | (2[0 - 4] | 1{0, 1}[0-9]){0, 1}[0-9])\.){3, 3}(25[0 - 5] | (2[0 - 4] | 1{0, 1}[0-9])\
{0, 1}[0 - 9]) | ([0 - 9a - fA - F]{1, 4}:){1, 4}:((25[0 - 5] | (2[0 - 4] | 1{0, 1}[0-9]){0, 1}[0-9])\.)\
{3, 3}(25[0 - 5] | (2[0 - 4] | 1{0, 1}[0-9]){0, 1}[0 - 9])))$"
    if not re.match(valid_ip4, str(ip)) and not re.match(valid_ip6, str(ip)):
        return False
    return True


def confStanzas(my_app, file):
    """Get conf file Stanzas."""
    conf_parser = six.moves.configparser.ConfigParser()
    conf = os.path.join(make_splunkhome_path(
        ["etc", "apps", my_app, "local", file]))
    stanzas = []
    if os.path.isfile(conf):
        with io.open(conf, 'r', encoding='utf_8_sig') as conffp:
            conf_parser.readfp(conffp)
        stanzas = conf_parser.sections()
    return conf_parser, stanzas


def getAccountData(global_account, my_app):
    """Get account data."""
    accCheckParser, acc_stanzas = confStanzas(
        my_app, "ta_netapp_eseries_account.conf")

    account_dict = {}

    for stanza in acc_stanzas:
        if str(stanza) == global_account:
            account_dict["web_proxy"] = accCheckParser.get(stanza, 'web_proxy')
            if accCheckParser.has_option(stanza, 'verify_ssl'):
                account_dict["verify_ssl"] = accCheckParser.get(
                    stanza, 'verify_ssl')
            account_dict["username"] = accCheckParser.get(stanza, 'username')

    return account_dict


def run_saved_searches(index, session_key):
    """Run Saved Searches."""
    saved_searches = ["Update%20Array%20StorageDevices%20Map", "Update%20Component%20Map", "Update%20Controller%20Map",
                      "Update%20Drive%20Map", "Update%20Volume%20Groups%2FPools%20Map", "Update%20Volume%20Map"]
    for ss_name in saved_searches:
        rest.simpleRequest("/servicesNS/nobody/netapp_app_eseries_perf/saved/searches/" + ss_name + "/dispatch",
                           sessionKey=session_key, postargs={
                               "dispatch.adhoc_search_level": "smart"},
                           method="POST", raiseAllErrors=True)


def get_verify_ssl():
    """
    Get the verify_ssl value from ta_netapp_eseries_account.conf.

    :return: boolean value configured for verify_ssl. By default, it returns true.
    """
    try:
        account_conf = cli.getConfStanza(
            'ta_netapp_eseries_account', 'default')
        if account_conf:
            verify_ssl = str(account_conf.get('verify_ssl'))
            return False if verify_ssl in ["0", "False", "F", "false", "f"] else True
    except ParsingError:
        pass
    return True
