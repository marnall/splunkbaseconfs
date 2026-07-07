#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import import_declare_test

from typing import Dict, Any
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError
from palo_utils import logger_instance, get_proxy_settings, make_post_request
import logging

util.remove_http_proxy_env_vars()

AUTH_TOKEN_URL = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"

fields = [
    field.RestField(
        "tsg_id", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "client_id", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "client_secret", required=True, encrypted=True, default=None, validator=None
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    "splunk_ta_paloalto_networks_iot_account", model, config_name="iot_account"
)
logger = logger_instance("iot_account")


class IoTAccountHandler(AdminExternalHandler):
    def _get_access_token(
        self, client_id: str, client_secret: str, tsg_id: str, proxies: Dict[str, str]
    ) -> str:
        """
        Get OAuth2 access token from Strata Cloud Manager.

        :param client_id: Service account client ID.
        :param client_secret: Service account client secret.
        :param tsg_id: Tenant Service Group ID.
        :param proxies: Proxy configuration.
        :returns: Access token string.
        :raises RestError: If token retrieval fails.
        """
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = f"grant_type=client_credentials&scope=tsg_id:{tsg_id}"

        try:
            response = make_post_request(
                url=AUTH_TOKEN_URL,
                data=data,
                headers=headers,
                proxies=proxies,
                auth=(client_id, client_secret),
            )
            if not response.ok:
                raise RestError(
                    401,
                    f"Failed to obtain access token. Status: {response.status_code}. "
                    "Please verify your Client ID, Client Secret, and TSG ID are correct.",
                )
            token_data = response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise RestError(
                    401,
                    "Access token not found in response. Please verify your credentials.",
                )
            return access_token
        except RestError:
            raise
        except (ConnectionError, TimeoutError):
            raise RestError(
                400,
                "Connection failed. Please check your network settings and proxy configuration.",
            )
        except Exception:
            raise RestError(
                400,
                "Failed to obtain access token. Please verify your credentials and try again.",
            )

    def validate_iot_credentials(self) -> None:
        """
        Validate IoT Security credentials using Strata Cloud Manager OAuth2 authentication.
        """
        try:
            tsg_id = self.callerArgs.data["tsg_id"][0]
            client_id = self.callerArgs.data["client_id"][0]
            client_secret = self.callerArgs.data["client_secret"][0]
            proxy_config = get_proxy_settings(logger, self.getSessionKey())

            # Validate by obtaining OAuth2 access token
            self._get_access_token(client_id, client_secret, tsg_id, proxy_config)
        except RestError:
            raise
        except Exception:
            raise RestError(
                400,
                "Validation failed. Please check your configuration and try again.",
            )

    def handleCreate(self, confInfo: Dict[str, Any]) -> None:
        self.validate_iot_credentials()
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo: Dict[str, Any]) -> None:
        self.validate_iot_credentials()
        AdminExternalHandler.handleEdit(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=IoTAccountHandler,
    )
