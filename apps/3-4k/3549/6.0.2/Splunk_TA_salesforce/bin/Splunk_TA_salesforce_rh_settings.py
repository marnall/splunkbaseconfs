#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This file contains certain ignores for certain linters.

* isort ignores:
- isort: skip = Particular import must be the first import or it is conflicting with the black linter formatting.

* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""
from typing import Dict, Any

import import_declare_test  # isort: skip # noqa: F401

import logging
import ipaddress

from Splunk_TA_salesforce_rh_proxy_validation import ProxyValidation, ProxyURLValidation
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    MultipleModel,
    RestModel,
    field,
    validator,
)
from solnlib import log

util.remove_http_proxy_env_vars()


fields_proxy = [
    field.RestField(
        "proxy_enabled", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "proxy_type",
        required=True,
        encrypted=False,
        default="http",
        validator=validator.Enum(
            ("socks5", "http"),
        ),
    ),
    field.RestField(
        "proxy_url",
        required=True,
        encrypted=False,
        default=None,
        validator=ProxyURLValidation(),
    ),
    field.RestField(
        "proxy_port",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Number(
            max_val=65535,
            min_val=1,
            is_int=True,
        ),
    ),
    field.RestField(
        "proxy_username",
        required=False,
        encrypted=False,
        default=None,
        validator=ProxyValidation(),
    ),
    field.RestField(
        "proxy_password",
        required=False,
        encrypted=True,
        default=None,
        validator=ProxyValidation(),
    ),
    field.RestField(
        "proxy_rdns", required=False, encrypted=False, default=None, validator=None
    ),
]
model_proxy = RestModel(fields_proxy, name="proxy")


fields_logging = [
    field.RestField(
        "loglevel", required=True, encrypted=False, default="INFO", validator=None
    )
]
model_logging = RestModel(fields_logging, name="logging")


endpoint = MultipleModel(
    "splunk_ta_salesforce_settings",
    models=[model_proxy, model_logging],
)


class SettingsHandler(AdminExternalHandler):
    """
    Manage Settings Details.
    """

    def __init__(self, *args, **kwargs):
        log_filename = "splunk_ta_salesforce_settings"
        self.logger = log.Logs().get_logger(log_filename)
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo: Dict[str, Any]) -> None:
        AdminExternalHandler.handleList(self, confInfo)
        if confInfo.get("proxy") and "proxy_url" in confInfo["proxy"]:
            confInfo["proxy"]["proxy_url"] = confInfo["proxy"]["proxy_url"].strip("[]")

    def handleEdit(self, confInfo: Dict[str, Any]) -> None:
        """
        Managing IPv6 address in proxy host.
        """
        if self.payload.get("proxy_url") and self.is_ipv6(
            self.payload.get("proxy_url")
        ):
            self.payload["proxy_url"] = f'[{self.payload.get("proxy_url")}]'
            self.logger.debug(
                f'Added the square brackets around the proxy host: {self.payload.get("proxy_url")}'
            )
        AdminExternalHandler.handleEdit(self, confInfo)

    def is_ipv6(self, ipv6_address: str) -> bool:
        try:
            ipaddress.IPv6Address(ipv6_address)
            self.logger.debug("proxy_url contains IPv6 address.")
            return True
        except ipaddress.AddressValueError:
            self.logger.debug(f"Not a valid IPv6 address: {ipv6_address}.")
            return False


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=SettingsHandler,
    )
