#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import sys
import traceback

import import_declare_test
from typing import Optional

from attrs import define, field
from azure.identity import KnownAuthorities, ClientSecretCredential
from azure.mgmt.security import SecurityCenter
from azure.core.exceptions import HttpResponseError
from splunktaucclib.alert_actions_base import ModularAlertBase

from splunk_ta_mscs.app.context import AppContext
from splunk_ta_mscs.config.accounts import AzureAccountConfig, AzureAccountReference
from splunk_ta_mscs.config.settings import ProxyConfig
from splunk_ta_mscs.utils.validators import validate_non_empty_string

APP_NAME = "Splunk_TA_MS_Security"
AZURE_PUBLIC_MANAGEMENT_URL = "https://management.azure.com"
API_VERSION = "2021-01-01"


@define
class DismissAzureAlertConfig:
    alert_location: str = field(validator=validate_non_empty_string)
    alert_name: str = field(validator=validate_non_empty_string)
    subscription_id: str = field(validator=validate_non_empty_string)
    account_name: Optional[str] = None


class DismissAzureAlertAction(ModularAlertBase):
    def __init__(self, ta_name, alert_name):
        super().__init__(ta_name, alert_name)
        self._app_context = AppContext(
            splunk_app_name=APP_NAME,
            rest_session_key=self.session_key,
        )

    def process_event(self, *args, **kwargs) -> int:
        try:
            self.log_debug(f"Processing alert with configuration: {self.configuration}")
            alert_config = DismissAzureAlertConfig(**self.configuration)

            self.log_info(
                f"Dismissing alert {alert_config.alert_name} in location {alert_config.alert_location}"
            )
            security_center = self._create_security_center(alert_config)
            security_center.alerts.update_subscription_level_state_to_dismiss(
                alert_config.alert_location,
                alert_config.alert_name,
            )
            self.log_info(
                f"Successfully dismissed alert {alert_config.alert_name} in location {alert_config.alert_location}"
            )
        except (ValueError, TypeError) as e:
            self.log_error(f"Invalid configuration: {str(e)}")
            self.log_error("Alert failed.")
            return 3
        except HttpResponseError as e:
            self.log_error(
                f"Unexpected Azure API error while dismissing alert: {str(e)}",
            )
            self.log_error(traceback.format_exc())
            self.log_error("Alert failed.")
            return 4
        except Exception as e:
            self.log_error(f"Unexpected error while dismissing alert: {str(e)}")
            self.log_error(traceback.format_exc())
            self.log_error("Alert failed.")
            return 5
        return 0

    def _create_security_center(
        self, config: DismissAzureAlertConfig
    ) -> SecurityCenter:
        azure_account = self._get_specified_or_first_azure_account(
            self._app_context, config.account_name
        )
        credential = self._create_azure_credential(
            azure_account, self._app_context.conf_proxy
        )
        return SecurityCenter(
            credential=credential,
            subscription_id=config.subscription_id,
            base_url=AZURE_PUBLIC_MANAGEMENT_URL,
            api_version=API_VERSION,
        )

    @staticmethod
    def _get_specified_or_first_azure_account(
        app_context: AppContext, account_name: Optional[str]
    ) -> AzureAccountConfig:
        if account_name:
            return app_context.conf_azure_account(
                AzureAccountReference(azure_app_account=account_name)
            )
        else:
            accounts = app_context.conf_all_azure_accounts
            if accounts:
                return next(iter(accounts.values()))
            else:
                raise ValueError("No Azure accounts configured.")

    @staticmethod
    def _create_azure_credential(
        account: AzureAccountConfig, proxy_config: ProxyConfig
    ) -> ClientSecretCredential:
        return ClientSecretCredential(
            tenant_id=account.tenant_id,
            client_id=account.client_id,
            client_secret=account.client_secret,
            proxies=proxy_config.azure_proxy_config,
            authority=KnownAuthorities.AZURE_PUBLIC_CLOUD,
        )

    def get_log_level(self):
        return self._app_context.conf_global_log_level


if __name__ == "__main__":
    exitcode = DismissAzureAlertAction(
        "Splunk_TA_MS_Security", "defender_dismiss_azure_alert"
    ).run(sys.argv)
    sys.exit(exitcode)
