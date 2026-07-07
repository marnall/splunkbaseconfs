"""Get proxies if it is enabled or else return None."""

import sys
import os

import ta_armis_declare

from requests.compat import quote_plus
from solnlib import conf_manager
from splunk import admin

sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..")))
sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..", "..")))


TA_NAME = ta_armis_declare.ta_name


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


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
        TA_NAME,
        realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(TA_NAME, conf_file),
    ).get_conf(conf_file)

    if stanza:
        return conf_file.get(stanza, only_current_app=True)
    return conf_file.get_all(only_current_app=True)


def get_proxy_uri(proxy):
    """Return proxy uri from given proxy configs."""
    uri = None
    if proxy and proxy.get("proxy_url") and proxy.get("proxy_type"):
        uri = proxy["proxy_url"]
        if proxy.get("proxy_port"):
            uri = "{0}:{1}".format(uri, proxy.get("proxy_port"))
        if proxy.get("proxy_username") and proxy.get("proxy_password"):
            uri = "{0}://{1}:{2}@{3}/".format(
                proxy["proxy_type"],
                quote_plus(proxy["proxy_username"]),
                quote_plus(proxy["proxy_password"]),
                uri,
            )
        else:
            uri = "{0}://{1}".format(proxy["proxy_type"], uri)
    return uri


def get_proxies(proxy):
    """Return proxies dict which is accepted by reqeusts module."""
    proxies = None
    proxy_uri = get_proxy_uri(proxy)
    if proxy_uri:
        proxies = {"http": proxy_uri, "https": proxy_uri}
    return proxies


def read_proxies_from_conf(session_key=None):
    """Read proxies from conf file."""
    if session_key is None:
        session_key = GetSessionKey().session_key
    proxy_config = read_conf_file(session_key, "ta_armis_settings", stanza="proxy")
    proxies = None
    if proxy_config.get("proxy_enabled"):
        proxy_enabled = int(proxy_config.get("proxy_enabled"))
        if proxy_enabled:
            proxies = get_proxies(proxy_config)
    return proxies
