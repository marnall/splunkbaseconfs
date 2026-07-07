#
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunk_ta_jira_cloud_proxy_validation import ProxyValidation
import logging
import jira_cloud_utils as utils
import jira_cloud_consts as jcc
import ipaddress

util.remove_http_proxy_env_vars()


fields_proxy = [
    field.RestField(
        "proxy_enabled", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "proxy_url",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=4096,
            min_len=0,
        ),
    ),
    field.RestField(
        "proxy_port",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            max_val=65535,
            min_val=1,
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
        "proxy_type", required=True, encrypted=False, default="http", validator=None
    ),
]
model_proxy = RestModel(fields_proxy, name="proxy")


fields_logging = [
    field.RestField(
        "loglevel", required=False, encrypted=False, default="INFO", validator=None
    )
]
model_logging = RestModel(fields_logging, name="logging")

endpoint = MultipleModel(
    "splunk_ta_jira_cloud_settings",
    models=[model_proxy, model_logging],
)


class JiraCloudExternalHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        session_key = self.getSessionKey()
        self.logger = utils.set_logger(session_key, jcc.JIRA_CLOUD_RH_SETTINGS)

    def handleList(self, conf_info):
        AdminExternalHandler.handleList(self, conf_info)
        if conf_info.get("proxy") and "proxy_url" in conf_info["proxy"]:
            conf_info["proxy"]["proxy_url"] = conf_info["proxy"]["proxy_url"].strip(
                "[]"
            )

    def handleEdit(self, conf_info):
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
        AdminExternalHandler.handleEdit(self, conf_info)

    def is_ipv6(self, ipv6_address):
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
        handler=JiraCloudExternalHandler,
    )
