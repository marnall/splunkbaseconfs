#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import re
import logging
import requests
import traceback
import sys
import json
import base64
from typing import Dict, Any, Optional, Union
from urllib import parse
from solnlib import conf_manager, log

APP_NAME = "Splunk_TA_paloalto_networks"


def get_input_name_from_full_name(full_input_name: str) -> str:
    """
    Full input name is in form of "<input_type>://<input_name>.

    :param full_input_name: Input name defined by user in input configuration.
    :returns: input name.
    """
    return full_input_name.split("/")[-1]


def logger_instance(input_name: str) -> logging.Logger:
    """
    This function creates logger instance

    :param input_name: name used for logger.
    :returns: Logger object.
    """
    pattern = r"://"
    if re.search(pattern, input_name):
        input_name = get_input_name_from_full_name(input_name)
    return log.Logs().get_logger(f"{APP_NAME.lower()}_{input_name}")


def make_get_request(
    url: str,
    params: Optional[Dict[str, Union[str, int]]] = None,
    headers: Optional[Dict[str, str]] = None,
    proxies: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> requests.Response:
    """
    Makes get request and returns Response object.

    :param url: Url that will be called.
    :param params: Params used in request if provided.
    :param headers: Headers used in request if provided.
    :param proxies: Proxies used in request if provided.
    :param timeout: Timeout is the number of seconds, Requests will wait for client to establish a connection.
    :returns: Response from requested url.
    """
    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=timeout,
        proxies=proxies,
        verify=True,
    )
    return response


def make_post_request(
    url: str,
    data: Optional[Union[Dict[str, Any], str]] = None,
    headers: Optional[Dict[str, str]] = None,
    proxies: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    params: Optional[Dict[str, Union[str, int]]] = None,
    auth: Optional[tuple] = None,
) -> requests.Response:
    """
    Makes post request and returns Response object.

    :param url: Url that will be called.
    :param data: Data used in request if provided.
    :param headers: Headers used in request if provided.
    :param proxies: Proxies used in request if provided.
    :param timeout: Timeout is the number of seconds, Requests will wait for client to establish a connection.
    :param params: Params used in request if provided.
    :param auth: Tuple of (username, password) for Basic authentication.
    :returns: Response from requested url.
    """
    response = requests.post(
        url,
        data=data,
        headers=headers,
        timeout=timeout,
        proxies=proxies,
        params=params,
        auth=auth,
        verify=True,
    )
    return response


def get_settings(session_key: str) -> Dict[str, Any]:
    """
    Returns settings stored in the .conf file.

    :param session_key: Session key for particular modular input.
    :returns: dict with settings pairs inside
    """
    settings_cfm = conf_manager.ConfManager(
        session_key,
        APP_NAME,
        realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-splunk_ta_paloalto_networks_settings",
    )
    conf = settings_cfm.get_conf("splunk_ta_paloalto_networks_settings").get_all()
    return conf


def get_account_credentials(
    session_key: str, account_name: str, account_type: str, logger: logging.Logger
) -> Dict[str, str]:
    """
    Gets credentials for a specific account_name.

    :param session_key: session key for particular modular input.
    :param account_name: account name configured in the addon.
    :param account_type: type of account used in modular input.
    :param logger: Logger object instance.
    :returns: credentials for requested account.
    """
    cfm = conf_manager.ConfManager(
        session_key,
        APP_NAME,
        realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-splunk_ta_paloalto_networks_{account_type}",
    )
    try:
        account_conf_file = cfm.get_conf(f"splunk_ta_paloalto_networks_{account_type}")
        account = account_conf_file.get(account_name)
        if account_type == "iot_account":
            return {
                "tsg_id": account.get("tsg_id"),
                "client_id": account.get("client_id"),
                "client_secret": account.get("client_secret"),
            }
        elif account_type == "firewall_account":
            return {
                "username": account.get("username"),
                "password": account.get("password"),
            }
        elif account_type == "data_security_account":
            return {
                "client_id": account.get("client_id"),
                "client_secret": account.get("client_secret"),
                "region": account.get("region"),
            }
        return {
            "region": account.get("region"),
            "api_key_id": account.get("api_key_id"),
            "api_key": account.get("api_key"),
        }
    except Exception as e:
        log.log_configuration_error(
            logger,
            e,
            msg_before=f"Failed to fetch account {account_name} settings. Error: {e}",
        )
    return {}


def get_proxy_settings(
    logger: logging.Logger, session_key: str
) -> Optional[Dict[str, str]]:
    """
    This function creates proxy connection if proxies configured.

    :param logger: Logger object instance.
    :param session_key: Session key for particular modular input.
    :returns: proxy configuration or None if proxies are not configured
    """
    try:
        conf = get_settings(session_key)
        proxy_stanza = {}
        for k, v in conf["proxy"].items():
            proxy_stanza[k] = v

        proxy_enabled = proxy_stanza.get("proxy_enabled", 0)
        if proxy_enabled is None or int(proxy_enabled) == 0:
            logger.info("Proxy is disabled")
            return None
        proxy_url = proxy_stanza.get("proxy_url")
        proxy_port = proxy_stanza.get("proxy_port")
        proxy_type = proxy_stanza.get("proxy_type")
        proxy_username = proxy_stanza.get("username")
        proxy_password = proxy_stanza.get("password")
        proxy_rdns = proxy_stanza.get("proxy_rdns")
        if proxy_rdns and proxy_type == "socks5":
            proxy_type += "h"
        if proxy_username and proxy_password:
            parsed_proxy_username = parse.quote_plus(proxy_username)
            parsed_proxy_password = parse.quote_plus(proxy_password)
            return {
                "http": f"{proxy_type}://{parsed_proxy_username}:{parsed_proxy_password}@{proxy_url}:{proxy_port}",
                "https": f"{proxy_type}://{parsed_proxy_username}:{parsed_proxy_password}@{proxy_url}:{proxy_port}",
            }
        return {
            "http": f"{proxy_type}://{proxy_url}:{proxy_port}",
            "https": f"{proxy_type}://{proxy_url}:{proxy_port}",
        }
    except Exception:
        logger.critical(
            f"Failed to fetch proxy details from configuration. {traceback.format_exc()}"
        )
        sys.exit(1)


def get_access_token(logger, client_id, client_secret, url, proxies=None):
    auth_string = f"{client_id}:{client_secret}"
    auth = base64.b64encode(auth_string.encode("ascii")).decode("utf-8")
    headers = {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded; charset=ISO-8859-1",
    }
    payload = {"grant_type": "client_credentials", "scope": "api_access"}
    try:
        response = requests.post(url, headers=headers, data=payload, proxies=proxies)
        token = response.json().get("access_token")
        return token
    except Exception as e:
        log.log_exception(
            logger,
            e,
            "Credentials error",
            msg_before=f"Exception while getting token for Data Security. Error: {e}",
        )
