from datetime import datetime
from settings import APP_ID
from splunklib import client

ENABLED = "1"


def get_service(session_key):
    """Connect to splunk service
    Args:
      session_key (str): splunk user session key

    Returns:
      An instance of splunk service
    """
    return client.connect(
        host="localhost",
        port="8089",
        verify=False,
        owner="nobody",
        app=APP_ID,
        token=session_key,
    )


def get_credentials(session_key, service=None):
    """Pull dt credentials from kvstore

    Returns:
      (dict) username and api key for dt api
    """
    if not service:
        service = get_service(session_key)

    user = ""
    key = ""
    farsight_key = ""
    proxy_username = ""
    proxy_password = ""

    credentials = service.storage_passwords
    for credential in credentials:
        if credential.realm == "DomainTools":
            user = credential.username
            key = credential.clear_password
        if credential.realm == "Farsight":
            farsight_key = credential.clear_password
        if credential.realm == "DomainToolsProxy":
            proxy_username = credential.username
            proxy_password = credential.clear_password

    return {
        "user": user,
        "key": key,
        "farsight_key": farsight_key,
        "proxy_username": proxy_username,
        "proxy_password": proxy_password,
    }


def get_client_info(session_key, service=None):
    """
    Retrieves client info for swclient and version.
    """
    if not service:
        service = get_service(session_key)

    stanzas = service.confs["app"].list()
    for stanza in stanzas:
        if stanza.name == "launcher":
            version = stanza["version"]
        elif stanza.name == "ui":
            swclient = stanza["label"]

    return swclient, version


def get_conf_stanzas(session_key, conf_file, stanza_name, service=None):
    """Pull any conf file's stanza by name

    Returns:
      stanza object
    """
    if not service:
        service = get_service(session_key)

    stanzas = service.confs[conf_file].list()
    for stanza in stanzas:
        if stanza.name == stanza_name:
            return stanza
    return None


def get_proxy(session_key, service=None):
    config = get_conf_stanzas(session_key, "domaintools", "domaintools", service)
    credentials = get_credentials(session_key, service)

    proxy_username = credentials["proxy_username"]
    proxy_password = credentials["proxy_password"]

    proxy_server = config["proxy_server"]
    proxy_port = config["proxy_port"]
    proxy_enabled = config["proxy_enabled"]
    proxy_authentication = config["proxy_authentication"]

    if proxy_enabled != ENABLED:
        return

    proxy_url = f"{proxy_server}:{proxy_port}"

    if proxy_authentication == ENABLED:
        split_url = proxy_url.split("://")
        protocol = "http"
        if len(split_url) == 2:
            protocol = split_url[0]
            server_address = split_url[1]
        else:
            server_address = proxy_url

        proxy_url = f"{protocol}://{proxy_username}:{proxy_password}@{server_address}"

    return proxy_url


def convert_to_iso_format_date(date: int):
    try:
        return datetime.strptime(str(date), "%Y%m%d").date().isoformat()
    except:
        return str(date) or ""
