#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # noqa

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from solnlib import log
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from Splunk_TA_okta_identity_cloud_proxy_validation import ProxyValidation
import logging
import ipaddress

util.remove_http_proxy_env_vars()


fields_additional_parameters = [
    field.RestField(
        "user_limit",
        required=True,
        encrypted=False,
        default="200",
        validator=validator.Number(max_val=200, min_val=20, is_int=True),
    ),
    field.RestField(
        "group_limit",
        required=True,
        encrypted=False,
        default="300",
        validator=validator.Number(max_val=10000, min_val=5, is_int=True),
    ),
    field.RestField(
        "app_limit",
        required=True,
        encrypted=False,
        default="200",
        validator=validator.Number(max_val=200, min_val=20, is_int=True),
    ),
    field.RestField(
        "log_limit",
        required=True,
        encrypted=False,
        default="1000",
        validator=validator.Number(max_val=1000, min_val=10, is_int=True),
    ),
    field.RestField(
        "rate_limit_pct",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            max_val=100,
            min_val=0,
        ),
    ),
    field.RestField(
        "dynamic_rate_enabled",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
]
model_additional_parameters = RestModel(
    fields_additional_parameters, name="additional_parameters"
)


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
        validator=validator.Number(max_val=65535, min_val=1, is_int=True),
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
]
model_proxy = RestModel(fields_proxy, name="proxy")


fields_logging = [
    field.RestField(
        "loglevel", required=True, encrypted=False, default=None, validator=None
    )
]
model_logging = RestModel(fields_logging, name="logging")


endpoint = MultipleModel(
    "splunk_ta_okta_identity_cloud_settings",
    models=[model_additional_parameters, model_proxy, model_logging],
)


class OKTAIdentityCloudExternalHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        log_filename = "splunk_ta_okta_identity_cloud_settings"
        self.logger = log.Logs().get_logger(log_filename)
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)
        if confInfo.get("proxy") and "proxy_url" in confInfo["proxy"]:
            confInfo["proxy"]["proxy_url"] = confInfo["proxy"]["proxy_url"].strip("[]")

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
        handler=OKTAIdentityCloudExternalHandler,
    )
