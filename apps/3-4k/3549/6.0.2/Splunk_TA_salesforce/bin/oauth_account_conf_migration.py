#
# SPDX-FileCopyrightText: 2025 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import sys
from typing import Dict, Any, Set
import sfdc_utility as su
import sfdc_consts as sc

AUTH_TYPE_BASIC = "basic"
AUTH_TYPE_OAUTH = "oauth"
AUTH_TYPE_OAUTH_CLIENT_CREDENTIALS = "oauth_client_credentials"


def get_session_key() -> str:
    """
    Get the session key from stdin.

    :return: The session key value.
    """
    return sys.stdin.readline().strip()


class ConfMigration:
    """Class to handle migration of OAuth configurations to UCC standard.
    Due to some naming conflicts in TA versions 5.0.0 - 5.1.0"""

    def __init__(self):
        """Initialize the migration class with necessary utilities."""
        self._failed_account_migration: Set[str] = set()
        self.sfdc_utility = su.SFDCUtil(
            log_file="splunk_ta_salesforce_oauth_account_conf_migration",
            session_key=get_session_key(),
        )

    def _should_skip_account(self, stanza_name: str, stanza: Dict[str, Any]) -> bool:
        """
        Determine if an account should be skipped from migration.

        :param stanza_name: The name of the account stanza
        :param stanza: The stanza configuration dictionary
        :return: True if account should be skipped, False otherwise
        """
        if stanza.get("auth_type") == AUTH_TYPE_BASIC:
            return True

        is_migrated = int(stanza.get("is_migrated", 0))
        if is_migrated:
            self.sfdc_utility.logger.info(
                f"Skipping the already migrated account={stanza_name}"
            )
            return True

        return False

    def _migrate_single_account(self, stanza_name: str, stanza: Dict[str, Any]) -> None:
        """
        Migrate a single OAuth account to the new format.

        :param stanza_name: The name of the account stanza
        :param stanza: The stanza configuration dictionary
        """
        if not (
            stanza.get("auth_type") == AUTH_TYPE_OAUTH
            and not stanza.get("refresh_token")
        ):
            return

        self.sfdc_utility.logger.info(
            f"Migrating oauth client credentials conf for account '{stanza_name}'."
        )

        stanza["auth_type"] = AUTH_TYPE_OAUTH_CLIENT_CREDENTIALS
        stanza["client_id_oauth_credentials"] = stanza.pop("client_id")
        stanza["client_secret_oauth_credentials"] = stanza.pop("client_secret")

        fields_to_update = {
            "auth_type": stanza["auth_type"],
            "client_id_oauth_credentials": stanza["client_id_oauth_credentials"],
            "endpoint": stanza["endpoint"],
            "sfdc_api_version": stanza["sfdc_api_version"],
            "is_migrated": True,
        }

        try:
            self.sfdc_utility._delete_conf(
                conf_file=sc.ACCOUNT_CONF_FILE, stanza_name=stanza_name
            )
            self.sfdc_utility._update_conf(
                conf_file=sc.ACCOUNT_CONF_FILE,
                fields=fields_to_update,
                encrypted=False,
            )
            self.sfdc_utility._regenerate_oauth_access_tokens()
        except Exception as e:
            self._failed_account_migration.add(stanza_name)
            self.sfdc_utility.logger.error(
                f"Error: {e} while migrating account '{stanza_name}'", exc_info=True
            )

    def migrate_oauth_config(self) -> None:
        """Migrate all OAuth configurations to the new format."""
        stanzas = self.sfdc_utility.get_conf_data(sc.ACCOUNT_CONF_FILE)
        for stanza_name, stanza in list(stanzas.items()):
            self.sfdc_utility.account_info = stanza
            self.sfdc_utility.account_info["name"] = stanza_name

            if self._should_skip_account(stanza_name, stanza):
                continue

            self._migrate_single_account(stanza_name, stanza)

    def run(self) -> None:
        self.sfdc_utility.logger.info("Conf migration started")

        try:
            self.migrate_oauth_config()
        except Exception as e:
            self.sfdc_utility.logger.error(
                f"Error while migrating tenants: {e}", exc_info=True
            )

        if self._failed_account_migration:
            failed_accounts = ",".join(self._failed_account_migration)
            self.sfdc_utility.logger.error(
                f"Failed to migrate accounts: {failed_accounts}"
            )

        self.sfdc_utility.logger.info("Conf migration completed")


if __name__ == "__main__":
    conf_migration = ConfMigration()
    try:
        conf_migration.run()
    except Exception as e:
        conf_migration.sfdc_utility.logger.error(
            f"Error while migrating the conf: {e}", exc_info=True
        )
