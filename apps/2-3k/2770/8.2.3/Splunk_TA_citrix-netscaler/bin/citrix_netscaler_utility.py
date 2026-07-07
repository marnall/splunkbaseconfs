#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import base64
import logging
import requests
import urllib.parse
import traceback
import splunk.admin as admin

from solnlib.utils import is_true


def make_request(url, method, config, _LOGGER, headers=None, timeout=120, data=None):
    """
    @return: repsonse object recieved by the request.
    """
    sslconfig = False
    proxy_info = build_proxy_info(config, _LOGGER)
    ca_certs_path = config.get("ca_certs_path") or ""
    if not is_true(config.get("disable_ssl_certificate_validation")):
        if ca_certs_path != "":
            sslconfig = ca_certs_path
        else:
            sslconfig = True
    _LOGGER.debug(f"SSL configured is : {sslconfig}")
    _LOGGER.info(f"Info for config : {sslconfig}")
    if config.get("username") and config.get("password"):
        credentials = base64.urlsafe_b64encode(
            ("%s:%s" % (config.get("username"), config.get("password"))).encode("UTF-8")
        ).decode("ascii")
        headers = {"Authorization": "Basic %s" % credentials}
    _LOGGER.debug(
        "Found %s value for disable_ssl_certificate_validation parameter",
        config.get("disable_ssl_certificate_validation"),
    )
    return requests.request(
        url=url,
        method=method,
        headers=headers,
        timeout=timeout,
        proxies=proxy_info,
        verify=sslconfig,
        data=data,
    )


def build_proxy_info(config, _LOGGER):
    proxy_type = config.get("proxy_type")
    proxy_info = {}

    if not is_true(config.get("proxy_enabled")):
        _LOGGER.debug(f"Proxy is not configured for {config.get('proxy_url')}")
        return None

    if proxy_type not in ("http", "socks5"):
        _LOGGER.warn(
            "Value of 'proxy_type' parameter Invalid/missing. Using default value='http' to continue data collection."
        )
        proxy_type = "http"

    if is_true(config.get("proxy_rdns")) and proxy_type == "socks5":
        proxy_type = "socks5h"

    if config.get("proxy_username") and config.get("proxy_password"):
        proxy_username = requests.compat.quote_plus(config["proxy_username"])
        proxy_password = requests.compat.quote_plus(config["proxy_password"])
        proxy_info["http"] = (
            f"{proxy_type}://{proxy_username}:{proxy_password}"
            f'@{config["proxy_url"]}:{int(config["proxy_port"])}'
        )
    else:
        proxy_info = {
            "http": f'{proxy_type}://{config["proxy_url"]}:{int(config["proxy_port"])}'
        }
    proxy_info["https"] = proxy_info["http"]

    return proxy_info
