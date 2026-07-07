#
# SPDX-FileCopyrightText: 2026 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test
import json
import logging
from urllib.parse import urlparse

# solnlib.CredentialManager replaces splunktalib for credential storage; get_splunkd_uri provides the Splunkd URI for constructing the manager
from solnlib.credentials import CredentialManager
from solnlib.splunkenv import get_splunkd_uri
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError
from Splunk_TA_jboss_account_validator import ServerValidator

import jboss_consts as c


fields = [
    field.RestField(
        "jmx_url",
        required=True,
        encrypted=False,
        default="",
        validator=validator.Pattern(
            regex=r"""^service:jmx.*$""",
        ),
    ),
    field.RestField(
        "username",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=255,
            min_len=1,
        ),
    ),
    field.RestField(
        "password",
        required=True,
        encrypted=True,
        default=None,
        validator=ServerValidator(),
    ),
]

model = RestModel(fields, name=None)


endpoint = SingleModel("splunk_ta_jboss_account", model, config_name="account")


class JBossAccountHandler(AdminExternalHandler):
    """
    Custom REST handler for the JBoss account endpoint.

      Before fix: UCC's bare AdminExternalHandler wrote passwords into passwords.conf
                  using splunktalib's internal CRED_REALM format. jboss_config.py read
                  them back with get_clear_password(), which is not available in solnlib.
      After fix:  this handler explicitly calls solnlib's crm.set_password() on create
                  and edit, storing the password as a JSON string {"password": "<value>"}.
                  jboss_config.py reads it back with crm.get_password() + json.loads(),
                  and handleRemove() cleans up the entry to avoid stale credentials.

    Ticket: ADDON-86488
    """

    PASSWORD_MAGIC = (
        "******"  # UCC sentinel value meaning "password unchanged" — skip re-saving
    )
    # UCC-standard realm format; must match the realm used in jboss_config.py CredentialManager
    UCC_CRED_REALM = "__REST_CREDENTIAL__#{app_name}#{endpoint}"
    UCC_ACCOUNT_ENDPOINT = "Splunk_TA_jboss_account"

    def _get_ucc_credential_manager(self):
        # Builds a solnlib CredentialManager scoped to the UCC realm so set/get/delete
        # all target the same passwords.conf entry that jboss_config.py reads at runtime.
        splunkd_info = urlparse(get_splunkd_uri())
        return CredentialManager(
            self.getSessionKey(),
            c.MODINPUT_NAME,
            owner="nobody",
            realm=self.UCC_CRED_REALM.format(
                app_name=c.MODINPUT_NAME,
                endpoint=self.UCC_ACCOUNT_ENDPOINT,
            ),
            scheme=splunkd_info.scheme,
            host=splunkd_info.hostname,
            port=splunkd_info.port,
        )

    def _sync_runtime_password(self, password):
        # Skip if password is empty or the UCC "unchanged" sentinel — no update needed
        if not password or password == self.PASSWORD_MAGIC:
            return

        crm = self._get_ucc_credential_manager()
        # Store as JSON so jboss_config.py can deserialize with json.loads and extract c.PASSWORD key
        crm.set_password(
            self.callerArgs.id,
            json.dumps({c.PASSWORD: password}),
        )

    def handleCreate(self, conf_info):
        password = self.payload.get(c.PASSWORD)
        super().handleCreate(conf_info)
        self._sync_runtime_password(password)

    def handleEdit(self, conf_info):
        password = self.payload.get(c.PASSWORD)
        super().handleEdit(conf_info)
        self._sync_runtime_password(password)

    def handleRemove(self, conf_info):
        stanza_name = self.callerArgs.id
        super().handleRemove(conf_info)
        try:
            # Clean up the stored password from passwords.conf when account is deleted;
            # silenced because the credential may not exist if it was never saved
            self._get_ucc_credential_manager().delete_password(stanza_name)
        except Exception:
            pass


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=JBossAccountHandler,  # replaced bare AdminExternalHandler to hook create/edit/remove for password sync
    )
