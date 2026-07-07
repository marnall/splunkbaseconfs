#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError
from typing import Dict, Any
import logging
from palo_utils import logger_instance, get_proxy_settings, get_access_token

util.remove_http_proxy_env_vars()

REGIONS = {
    "us": "https://api.aperture.paloaltonetworks.com",
    "apac": "https://api.aperture-apac.paloaltonetworks.com",
    "eu": "https://api.aperture-eu.paloaltonetworks.com",
    "uk": "https://api.aperture-uk.paloaltonetworks.com",
    "in1": "https://api.in1.prisma-saas.paloaltonetworks.com",
    "au1": "https://api.au1.prisma-saas.paloaltonetworks.com",
    "uk2": "https://api.uk2.prisma-saas.paloaltonetworks.com",
    "jp1": "https://api.jp1.prisma-saas.paloaltonetworks.com",
}

special_fields = [
    field.RestField(
        "name", required=True, encrypted=False, default=None, validator=None
    )
]

fields = [
    field.RestField(
        "client_id", required=True, encrypted=True, default=None, validator=None
    ),
    field.RestField(
        "region", required=True, encrypted=False, default="us", validator=None
    ),
    field.RestField(
        "client_secret", required=True, encrypted=True, default=None, validator=None
    ),
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    "splunk_ta_paloalto_networks_data_security_account",
    model,
    config_name="data_security_account",
    need_reload=False,
)

logger = logger_instance("data_security_account")


class DataSecurityHandler(AdminExternalHandler):
    def validate_data_security_creditentials(self) -> None:
        try:
            client_id = self.callerArgs.data["client_id"][0]
            client_secret = self.callerArgs.data["client_secret"][0]
            region = self.callerArgs.data["region"][0]
            logger.info("Validating Data Security credentials...")
            proxy_config = get_proxy_settings(logger, self.getSessionKey())
            token_url = f"{REGIONS.get(region)}/oauth/token"
            access_token = get_access_token(
                logger, client_id, client_secret, token_url, proxy_config
            )
            if not access_token:
                raise RestError(
                    407,
                    "Authentication to Data Security failed. "
                    "The Client ID or Client Secret appears to be invalid. "
                    "Please verify your API credentials. "
                    "If your connection requires a proxy, check Configuration => Proxy settings.",
                )
        except RestError:
            raise
        except Exception as e:
            raise RestError(
                400,
                "Unable to connect to Data Security. "
                "This could be caused by invalid region selection, network connectivity issues, "
                "or proxy misconfiguration. Please verify your settings and ensure the service is reachable. "
                "If your connection requires a proxy, check Configuration => Proxy settings.",
            ) from e

    def handleCreate(self, confInfo: Dict[str, Any]) -> None:
        self.validate_data_security_creditentials()
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo: Dict[str, Any]) -> None:
        self.validate_data_security_creditentials()
        AdminExternalHandler.handleEdit(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=DataSecurityHandler,
    )
