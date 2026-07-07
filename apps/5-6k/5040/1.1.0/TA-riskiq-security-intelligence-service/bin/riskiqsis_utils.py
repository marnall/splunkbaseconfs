"""General Utilities."""

import json
import requests
import os
import boto3
import re

from splunk import rest
from solnlib import conf_manager
import splunk.entity as entity
from splunk import admin

from botocore.config import Config

APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]
RISKIQSIS_SETTINGS_CONF = "ta_riskiq_security_intelligence_service_settings"
RISKIQSIS_ACCOUNT_CONF = "ta_riskiq_security_intelligence_service_account"

DATA_TYPE_MAPPING = {
    "newly_observed_domain": "sis-new-observations",
    "newly_observed_host": "sis-new-observations",
    "malware_blacklist": "riq-sis-blacklist-malware",
    "phishing_blacklist": "riq-sis-blacklist-phish",
    "scam_blacklist": "riq-sis-blacklist-scam",
    "content_blacklist": "riq-sis-blacklist-content",
}

FRONTEND_DATATYPE_MAPPING = {
    "newly_observed_domain": "Newly Observed Domain",
    "newly_observed_host": "Newly Observed Host",
    "malware_blacklist": "Malware Blacklist",
    "phishing_blacklist": "Phishing Blacklist",
    "scam_blacklist": "Scam Blacklist",
    "content_blacklist": "Content Blacklist"
}

DATA_TYPE_PREFIX = {
    "newly_observed_domain": "domains",
    "newly_observed_host": "hosts",
    "malware_blacklist": "malware_list",
    "phishing_blacklist": "phish_list",
    "scam_blacklist": "scam_list",
    "content_blacklist": "content_list",
}

INPUT_NAME = "riskiq_security_intelligence_service"


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


def make_client(client_type, access_key, secret_key, proxies):
    """Return the client object for the given client_type."""
    client_object = boto3.client(
        client_type,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(proxies=proxies)
    )
    return client_object


def reload_batch_input(sessionKey):
    """
    Reload the inputs present under data/inputs/monitor.

    :param sessionKey: sessionKey for Splunk Authentication
    """
    try:
        rest.simpleRequest(
            '/servicesNS/nobody/{}/data/inputs/monitor/_reload'.format(APP_NAME),
            sessionKey,
            method="POST",
            raiseAllErrors=True,
        )
    except Exception as e:
        raise Exception("Error while reloading batch stanza: {}".format(e))


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
                cred.get("secretkey", "") if type == "account" else cred.get("proxy_password", "")
            )
            break
    return password


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


def get_entities():
    """Give information about entities object."""
    entities = entity.getEntities(
        ["admin", "passwords"],
        namespace=APP_NAME,
        owner="nobody",
        sessionKey=GetSessionKey().session_key,
        search=APP_NAME,
        count=-1,
    )
    return entities


def get_proxy_config():
    """
    Give information of proxy if proxy is enabled.

    :return: dictionary having proxy information
    """
    # Get proxy configurations
    proxy_configuration = read_conf_file(
        GetSessionKey().session_key, RISKIQSIS_SETTINGS_CONF, stanza="proxy"
    )

    entities = get_entities()

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


def get_input_checkpoint_keys(session_key, input_name):
    """
    Return checkpoint keys present for given input.

    :session_key: Session key
    :input_name: find keys for given input name

    :return: Proxy dict
    """
    keys = []
    account_data = read_conf_file(session_key, "inputs", "riskiq_security_intelligence_service://{}".format(input_name))
    checkpoint_key = "{}_{}".format(account_data['global_account'], input_name)
    ckpt_url = "/servicesNS/nobody/{}/storage/collections/data/{}_checkpointer".format(
        APP_NAME, APP_NAME.replace("-", "_")
    )
    try:
        res, data = rest.simpleRequest(
            ckpt_url,
            sessionKey=session_key,
            method="GET",
            getargs={"output_mode": "json"},
            raiseAllErrors=True,
        )
        data = json.loads(data.decode("utf-8"))

        for ckpt in data:
            key = ckpt['_key']
            if re.match("{}_day=".format(checkpoint_key), key):
                keys.append(key)

            elif checkpoint_key == key:
                keys.append(key)

        return keys
    except Exception:
        return
