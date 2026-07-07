##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunk_ta_rsa_securid_cas_account_validation import account_validation
from solnlib import log
import logging

logger = log.Logs().get_logger("splunk_ta_rsa_securid_cas_account_validation")

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "adminRestApiUrl", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "access_id_of_api", required=True, encrypted=True, default=None, validator=None
    ),
    field.RestField(
        "api_access_key", required=True, encrypted=True, default=None, validator=None
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    "splunk_ta_rsa_securid_cas_account", model, config_name="account"
)


class RsaSecurIdCasAccountExternalHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        account_validation(
            self.payload.get("adminRestApiUrl"),
            self.payload.get("api_access_key"),
            self.payload.get("access_id_of_api"),
            logger,
            self.getSessionKey(),
        )
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        account_validation(
            self.payload.get("adminRestApiUrl"),
            self.payload.get("api_access_key"),
            self.payload.get("access_id_of_api"),
            logger,
            self.getSessionKey(),
        )
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        AdminExternalHandler.handleRemove(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=RsaSecurIdCasAccountExternalHandler,
    )
